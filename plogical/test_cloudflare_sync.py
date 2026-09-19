"""Cloudflare sync regression tests with a stateful API double, no credentials."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def load_dns():
    spec = importlib.util.spec_from_file_location(
        'dns_cloudflare_test', Path(__file__).with_name('dnsUtilities.py'))
    module = importlib.util.module_from_spec(spec)
    stubs = {'django': SimpleNamespace(setup=lambda: None),
             'CloudFlare': SimpleNamespace(),
             'plogical.processUtilities': SimpleNamespace(ProcessUtilities=Mock())}
    with patch.dict(sys.modules, stubs), patch.dict(__import__('os').environ):
        spec.loader.exec_module(module)
    return module


module = load_dns()
DNS = module.DNS


class RecordsAPI:
    def __init__(self, records=()):
        self.records = [dict(record) for record in records]
        self.writes = []
        self.pages = []

    def get(self, zone, params):
        self.pages.append(params['page'])
        found = [record.copy() for record in self.records
                 if record['type'] == params['type']
                 and record['name'].rstrip('.').lower() == params['name']]
        start = (params['page'] - 1) * params['per_page']
        return found[start:start + params['per_page']]

    def post(self, zone, data):
        self.writes.append(('post', data.copy()))
        item = dict(data, id=str(len(self.records) + 1))
        self.records.append(item)
        return item.copy()

    def patch(self, zone, record_id, data):
        self.writes.append(('patch', record_id, data.copy()))
        item = next(record for record in self.records if record['id'] == record_id)
        item.update(data)
        return item.copy()


def record(value, name='_dmarc.example.test', kind='TXT', **extra):
    return dict(dict(id='one', name=name, type=kind, content=value, ttl=3600), **extra)


class CloudflareSyncTests(unittest.TestCase):
    def client(self, records=()):
        api = RecordsAPI(records)
        return SimpleNamespace(zones=SimpleNamespace(dns_records=api)), api

    def sync(self, cf, value='v=DMARC1; p=reject', name='_dmarc.example.test',
             kind='TXT', priority=0, ttl=3600):
        return DNS.createDNSRecordCloudFlare(cf, 'zone', name, kind, value, priority, ttl)

    def test_repeated_policy_sync_creates_once(self):
        cf, api = self.client()
        self.sync(cf)
        self.sync(cf)
        self.assertEqual(len(api.records), 1)
        self.assertEqual([write[0] for write in api.writes], ['post'])
        self.assertNotIn('priority', api.records[0])

    def test_changed_policy_updates_same_record_without_losing_metadata(self):
        cf, api = self.client([record('v=DMARC1; p=none', comment='keep', tags=['owner:me'])])
        self.sync(cf)
        self.assertEqual(api.writes, [('patch', 'one', {'content': 'v=DMARC1; p=reject'})])
        self.assertEqual(api.records[0]['comment'], 'keep')
        self.assertEqual(api.records[0]['tags'], ['owner:me'])

    def test_dkim_key_rotation_updates_each_selector_in_place(self):
        for selector in ('default', 'mail2026'):
            name = selector + '._domainkey.example.test'
            with self.subTest(selector=selector):
                cf, api = self.client([record('v=DKIM1; p=old', name=name)])
                self.sync(cf, '"v=DKIM1; p="\n\t"new"', name=name)
                self.sync(cf, '"v=DKIM1; p="\n\t"new"', name=name)
                self.assertEqual(len(api.records), 1)
                self.assertEqual(api.records[0]['content'], 'v=DKIM1; p=new')
                self.assertEqual(len(api.writes), 1)

    def test_existing_multiple_policies_fail_without_mutating(self):
        for name in ('_dmarc.example.test', 'default._domainkey.example.test'):
            for second_value in ('v=DMARC1; p=reject', 'v=DMARC1; p=none'):
                with self.subTest(name=name, value=second_value):
                    cf, api = self.client([record('v=DMARC1; p=reject', name=name),
                                          record(second_value, name=name, id='two')])
                    with self.assertRaisesRegex(ValueError, 'reconcile'):
                        self.sync(cf, name=name)
                    self.assertEqual(api.writes, [])

    def test_multiple_addresses_are_preserved_and_new_address_added_once(self):
        cf, api = self.client([record('192.0.2.1', name='www.example.test', kind='A'),
                              record('192.0.2.2', name='www.example.test', kind='A', id='two')])
        for value in ('192.0.2.1', '192.0.2.3', '192.0.2.3'):
            self.sync(cf, value, name='www.example.test', kind='A')
        self.assertEqual([r['content'] for r in api.records], ['192.0.2.1', '192.0.2.2', '192.0.2.3'])
        self.assertEqual(len(api.writes), 1)

    def test_unrelated_txt_values_and_case_are_preserved(self):
        cf, api = self.client([record('verification=AbC', name='example.test')])
        self.sync(cf, 'verification=abc', name='example.test')
        self.sync(cf, 'verification=abc', name='example.test')
        self.assertEqual([r['content'] for r in api.records], ['verification=AbC', 'verification=abc'])

    def test_mx_identity_includes_priority_and_normalizes_hostname(self):
        cf, api = self.client([record('MAIL.Example.Test.', name='example.test', kind='MX', priority=10)])
        self.sync(cf, 'mail.example.test', name='EXAMPLE.TEST.', kind='MX', priority=10)
        self.sync(cf, 'mail.example.test', name='example.test', kind='MX', priority=20)
        self.sync(cf, 'backup.example.test', name='example.test', kind='MX', priority=30)
        self.assertEqual(len(api.records), 3)
        self.assertEqual(len(api.writes), 2)

    def test_quoted_txt_is_equivalent_without_making_another_record(self):
        cf, api = self.client([record('v=DMARC1; p=reject')])
        self.sync(cf, '"v=DMARC1; p=reject"')
        self.assertEqual(api.writes, [])

    def test_pagination_finds_existing_record_on_later_page(self):
        records = [record('token=%s' % i, name='example.test', id=str(i)) for i in range(101)]
        cf, api = self.client(records)
        self.sync(cf, 'token=100', name='example.test')
        self.assertEqual(api.pages, [1, 2])
        self.assertEqual(api.writes, [])

    def test_failed_lookup_does_not_create_record(self):
        cf, api = self.client()
        api.get = Mock(side_effect=RuntimeError('lookup failed'))
        with self.assertRaisesRegex(RuntimeError, 'lookup failed'):
            self.sync(cf)
        self.assertEqual(api.writes, [])

    def test_failed_update_does_not_create_record(self):
        cf, api = self.client([record('v=DMARC1; p=none')])
        api.patch = Mock(side_effect=RuntimeError('update failed'))
        with self.assertRaisesRegex(RuntimeError, 'update failed'):
            self.sync(cf)
        self.assertEqual(api.writes, [])

    def test_ttl_is_updated_without_changing_proxy_status(self):
        for proxied in (True, False):
            with self.subTest(proxied=proxied):
                cf, api = self.client([record('192.0.2.1', name='www.example.test', kind='A',
                                              ttl=1, proxied=proxied)])
                self.sync(cf, '192.0.2.1', name='www.example.test', kind='A')
                self.assertEqual(api.records[0]['proxied'], proxied)
                self.assertEqual(api.records[0]['ttl'], 1 if proxied else 3600)

    def test_soa_is_not_sent_to_cloudflare(self):
        cf, api = self.client()
        self.sync(cf, 'ns hostmaster 1 2 3 4 5', name='example.test', kind='SOA')
        self.assertEqual(api.pages, [])
        self.assertEqual(api.writes, [])

    def test_zone_sync_surfaces_record_failure_without_creating_another_zone(self):
        cf, api = self.client([record('v=DMARC1; p=none'), record('v=DMARC1; p=reject', id='two')])
        cf.zones.get = Mock(return_value=[{'id': 'zone', 'name': 'example.test'}])
        cf.zones.post = Mock()
        local = SimpleNamespace(name='_dmarc.example.test', type='TXT',
                                content='v=DMARC1; p=reject', prio=0, ttl=3600)
        dns = DNS()
        dns.email, dns.key = 'test@example.test', 'not-a-key'
        with patch.object(DNS, 'loadCFKeys', return_value=1), \
                patch.object(module.CloudFlare, 'CloudFlare', return_value=cf, create=True), \
                patch.object(module, 'Domains', SimpleNamespace(objects=Mock(get=Mock(return_value=SimpleNamespace(id=1)))), create=True), \
                patch.object(module, 'Records', SimpleNamespace(objects=Mock(filter=Mock(return_value=[local]))), create=True), \
                patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            success, error = dns.cfTemplate('example.test', Mock())
        self.assertEqual(success, 0)
        self.assertIn('reconcile', error)
        cf.zones.post.assert_not_called()
        self.assertEqual(api.writes, [])

    def test_automatic_record_sync_keeps_ttl_in_correct_argument_position(self):
        cf, api = self.client()
        cf.zones.get = Mock(return_value=[{'id': 'zone', 'name': 'example.test'}])
        records_model = Mock()
        records_model.objects.filter.return_value.count.return_value = 0
        zone = SimpleNamespace(name='example.test', id=1, admin=Mock())

        def keys(dns):
            dns.email, dns.key, dns.status = 'test@example.test', 'not-a-key', 'Enable'
            return 1

        with patch.object(DNS, 'loadCFKeys', keys), \
                patch.object(DNS, 'incrementSOASerial'), \
                patch.object(module.CloudFlare, 'CloudFlare', return_value=cf, create=True), \
                patch.object(module, 'Records', records_model, create=True):
            DNS.createDNSRecord(zone, 'example.test', 'A', '192.0.2.1', 0, 3600)
        self.assertEqual(len(api.records), 1)
        self.assertEqual(api.records[0]['ttl'], 3600)

    def test_zone_lookup_failure_never_attempts_zone_creation(self):
        cf, api = self.client()
        cf.zones.get = Mock(side_effect=RuntimeError('permission denied'))
        cf.zones.post = Mock()
        dns = DNS()
        dns.email, dns.key = 'test@example.test', 'not-a-key'
        with patch.object(DNS, 'loadCFKeys', return_value=1), \
                patch.object(module.CloudFlare, 'CloudFlare', return_value=cf, create=True), \
                patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            self.assertEqual(dns.cfTemplate('example.test', Mock()), (0, 'permission denied'))
        cf.zones.post.assert_not_called()
        self.assertEqual(api.writes, [])


if __name__ == '__main__':
    unittest.main()
