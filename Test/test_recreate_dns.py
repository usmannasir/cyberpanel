#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""Unit checks for full Recreate DNS (PowerDNS repair + Cloudflare status)."""
from __future__ import print_function

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')


class UpsertSpfForNameTests(unittest.TestCase):
    def setUp(self):
        from plogical.dnsUtilities import DNS
        self.DNS = DNS

    def test_empty_hostname(self):
        changed, err = self.DNS.UpsertSpfForName('')
        self.assertEqual(changed, 0)
        self.assertEqual(err, 'Empty hostname')

    def test_recreate_missing_domain(self):
        admin = mock.Mock()
        status, message = self.DNS.RecreateDNSForDomain('', admin)
        self.assertEqual(status, 0)
        self.assertIn('Missing', message)

    def test_upsert_updates_wrong_spf(self):
        Domains = mock.Mock()
        Records = mock.Mock()
        zone = mock.Mock()
        Domains.objects.filter.return_value.first.return_value = zone

        wrong = mock.Mock()
        wrong.content = 'v=spf1 include:spf.cyberpersons.com ~all'
        Records.objects.filter.return_value = [wrong]

        with mock.patch.object(self.DNS, '_powerdns_models', return_value=(Domains, Records)):
            with mock.patch.object(self.DNS, 'buildSpfRecord', return_value='v=spf1 a mx ip4:203.0.113.10 ~all'):
                with mock.patch.object(self.DNS, 'bumpSOASerial'):
                    changed, err = self.DNS.UpsertSpfForName('example.com')

        self.assertIsNone(err)
        self.assertGreaterEqual(changed, 1)
        self.assertEqual(wrong.content, 'v=spf1 a mx ip4:203.0.113.10 ~all')
        wrong.save.assert_called()


class CloudflareStatusTests(unittest.TestCase):
    def test_pending_zone_requests_activation_and_lists_ns(self):
        from plogical import dns_recreate

        admin = mock.Mock()
        admin.userName = 'admin'

        dns_inst = mock.Mock()
        dns_inst.loadCFKeys.return_value = 1
        dns_inst.status = 'Enable'
        dns_inst.email = 'a@b.c'
        dns_inst.key = 'token'
        dns_inst.cfTemplate.return_value = (1, None)

        cf = mock.Mock()
        cf.zones.get.return_value = {
            'id': 'zid',
            'name': 'fuprip.com',
            'status': 'pending',
            'name_servers': ['josh.ns.cloudflare.com', 'lovisa.ns.cloudflare.com'],
        }

        with mock.patch('plogical.dnsUtilities.DNS', return_value=dns_inst):
            with mock.patch(
                    'plogical.cloudflare_dns_sync.CloudflareDnsSync.resolve_zone',
                    return_value=('zid', 'fuprip.com')):
                with mock.patch(
                        'plogical.cloudflareClient.get_cloudflare_client',
                        return_value=cf):
                    info = dns_recreate.cloudflare_sync_and_status(
                        'fuprip.com', admin)

        self.assertTrue(info['enabled'])
        self.assertTrue(info['synced'])
        self.assertEqual(info['zone_status'], 'pending')
        self.assertIn('josh.ns.cloudflare.com', info['name_servers'])
        self.assertTrue(info['activation_check'])
        self.assertIn('registrar', info['message'].lower())
        cf.zones.activation_check.post.assert_called_once_with('zid')

    def test_upsert_simple_updates_wrong_a(self):
        from plogical import dns_recreate
        from plogical.dnsUtilities import DNS

        Records = mock.Mock()
        zone = mock.Mock()
        row = mock.Mock()
        row.content = '1.2.3.4'
        row.prio = 0
        Records.objects.filter.return_value = [row]

        with mock.patch.object(DNS, 'bumpSOASerial'):
            changed = dns_recreate._upsert_simple(
                Records, DNS, zone, 'example.com', 'A', '84.247.184.182')

        self.assertEqual(changed, 1)
        self.assertEqual(row.content, '84.247.184.182')
        row.save.assert_called()


if __name__ == '__main__':
    unittest.main()
