"""An MX or SRV record is stored as PowerDNS serves it: the priority apart, the rest as content."""
import ast
import builtins
import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical.dnsRecordContent import (MX_EXPECTED, PRIORITY_EXPECTED, SRV_EXPECTED, mx_record_content,
                                       record_priority, srv_record_content)

ROOT = Path(__file__).resolve().parents[1]


def method_of(source, class_name, name, scope):
    """One method of a panel class, run in ``scope`` instead of the module that needs Django."""
    tree = ast.parse((ROOT / source).read_text(encoding='utf-8'))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name)
    method.decorator_list = []
    exec(compile(ast.Module(body=[method], type_ignores=[]), source, 'exec'), scope)
    return scope[name]


class Reply(object):
    def __init__(self, content):
        self.content = content


class SRVContentTests(unittest.TestCase):

    def refused(self, content, priority=10):
        with self.assertRaises(ValueError) as refusal:
            srv_record_content(content, priority)
        return str(refusal.exception)

    def test_weight_port_and_target_are_stored_as_given(self):
        self.assertEqual('5 8080 marker.panelqa.test', srv_record_content('5 8080 marker.panelqa.test', 10))
        self.assertEqual('0 0 a', srv_record_content('0 0 a', 0))
        self.assertEqual('65535 65535 _x.sip-1.example.com', srv_record_content('65535 65535 _x.sip-1.example.com', 65535))

    def test_spacing_and_leading_zeros_do_not_reach_the_record(self):
        self.assertEqual('5 8080 sip.example.com', srv_record_content('  05\t8080   sip.example.com \n', 10))

    def test_the_dot_that_ends_a_full_name_is_not_stored(self):
        self.assertEqual('5 8080 sip.example.com', srv_record_content('5 8080 sip.example.com.', 10))
        self.assertIn('Target must be a host name', self.refused('5 8080 sip.example.com..'))

    def test_a_single_dot_says_the_service_is_not_offered(self):
        self.assertEqual('0 0 .', srv_record_content('0 0 .', 0))

    def test_the_whole_record_is_taken_when_its_priority_is_the_one_of_the_field(self):
        self.assertEqual('60 5060 server.example.com', srv_record_content('10 60 5060 server.example.com', 10))
        self.assertEqual('5 8080 marker.panelqa.test', srv_record_content('010 5 8080 marker.panelqa.test.', 10))

    def test_the_whole_record_with_another_priority_is_refused(self):
        message = self.refused('20 60 5060 server.example.com', 10)
        self.assertEqual('The content begins with the priority 20, but the Priority field holds 10. '
                         + SRV_EXPECTED, message)
        self.assertIn('weight, port and target', message)
        self.assertIn('"5 5060 sip.example.com"', message)

    def test_too_few_or_too_many_parts_are_refused(self):
        for content in ('', '   ', 'sip.example.com', '5060 sip.example.com', '10 60 5060 server.example.com extra',
                        '5 5060 sip.example.com sip2.example.com', 'ten 60 5060 server.example.com',
                        '10 sixty 5060 server.example.com', None, 5060, ['5', '5060', 'sip.example.com']):
            self.assertEqual(SRV_EXPECTED, self.refused(content), repr(content))

    def test_weight_and_port_must_be_numbers(self):
        for content, name in (('five 5060 sip.example.com', 'Weight'), ('5 sip 5060', 'Port'),
                              ('-1 5060 sip.example.com', 'Weight'), ('5 50.60 sip.example.com', 'Port'),
                              ('5 0x50 sip.example.com', 'Port'), ('٥ 5060 sip.example.com', 'Weight')):
            self.assertEqual('%s must be a whole number from 0 to 65535. %s' % (name, SRV_EXPECTED),
                             self.refused(content), content)

    def test_weight_and_port_must_fit_the_record(self):
        for content, name in (('65536 5060 sip.example.com', 'Weight'), ('5 65536 sip.example.com', 'Port'),
                              ('5 100000 sip.example.com', 'Port'), ('123456 5060 sip.example.com', 'Weight')):
            self.assertEqual('%s must be a whole number from 0 to 65535. %s' % (name, SRV_EXPECTED),
                             self.refused(content), content)

    def test_the_target_must_be_a_host_name(self):
        for target in ('@', 'sip..example.com', '.sip.example.com', 'sip.example.com:5060', 'sip/example.com',
                       '"sip.example.com"', 'sïp.example.com', 'a' * 64 + '.example.com',
                       '.'.join(['a' * 60] * 5), '..'):
            self.assertIn('Target must be a host name', self.refused('5 5060 ' + target), target)
        self.assertEqual('5 5060 ' + 'a' * 63 + '.example.com',
                         srv_record_content('5 5060 ' + 'a' * 63 + '.example.com', 10))


class PriorityTests(unittest.TestCase):

    def test_numbers_and_their_spelling_are_taken(self):
        for sent, priority in ((0, 0), (10, 10), (65535, 65535), ('10', 10), (' 010 ', 10)):
            self.assertEqual(priority, record_priority(sent))

    def test_anything_else_is_refused(self):
        for sent in (None, '', 'ten', '1.5', 1.5, 10.0, -1, '-1', 65536, '65536', True, False, [10], {}):
            with self.assertRaises(ValueError, msg=repr(sent)) as refusal:
                record_priority(sent)
            self.assertEqual(PRIORITY_EXPECTED, str(refusal.exception))


class MXContentTests(unittest.TestCase):

    def test_the_mail_host_is_stored_as_given(self):
        for host in ('mail.example.com', 'mail.example.com.', '.'):
            self.assertEqual(host, mx_record_content(' %s ' % host, 10))

    def test_a_repeated_priority_is_dropped_and_another_one_refused(self):
        self.assertEqual('mail.example.com', mx_record_content('10 mail.example.com', 10))
        with self.assertRaises(ValueError) as refusal:
            mx_record_content('20 mail.example.com', 10)
        self.assertEqual('The content begins with the priority 20, but the Priority field holds 10. ' + MX_EXPECTED,
                         str(refusal.exception))

    def test_anything_but_one_host_is_refused(self):
        for content in ('', 'mail.example.com mail2.example.com', '10 20 mail.example.com', None):
            with self.assertRaises(ValueError, msg=repr(content)) as refusal:
                mx_record_content(content, 10)
            self.assertEqual(MX_EXPECTED, str(refusal.exception))


class AddRecordTests(unittest.TestCase):
    """The request of the DNS Records page and of the cloud API."""

    def setUp(self):
        self.acl = mock.Mock()
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnershipZone.return_value = 1
        self.zone = SimpleNamespace(name='panelqa.test')
        self.dns = mock.Mock()
        scope = {
            'ACLManager': self.acl,
            'Administrator': mock.Mock(),
            'Domains': SimpleNamespace(objects=SimpleNamespace(get=lambda name: self.zone)),
            'DNS': self.dns, 'HttpResponse': Reply, 'json': json,
            'match': re.match, 'M': re.M, 'I': re.I,
            'record_priority': record_priority, 'srv_record_content': srv_record_content,
            'mx_record_content': mx_record_content,
        }
        self.add = method_of('dns/dnsManager.py', 'DNSManager', 'addDNSRecord', scope)

    def reply(self, **record):
        data = dict({'selectedZone': 'panelqa.test', 'ttl': 3600}, **record)
        return json.loads(self.add(None, 1, data).content)

    def stored(self):
        self.dns.createDNSRecord.assert_called_once()
        return self.dns.createDNSRecord.call_args[0]

    def test_srv_is_stored_as_weight_port_and_target_beside_its_priority(self):
        reply = self.reply(recordType='SRV', recordName='_marker._tcp', priority=10,
                           recordContentSRV='5 8080 marker.panelqa.test')
        self.assertEqual({'status': 1, 'add_status': 1, 'error_message': 'None'}, reply)
        self.assertEqual((self.zone, '_marker._tcp.panelqa.test', 'SRV', '5 8080 marker.panelqa.test', 10, 3600),
                         self.stored())

    def test_the_old_example_with_its_priority_repeated_is_stored_servable(self):
        self.assertEqual(1, self.reply(recordType='SRV', recordName='_sip._tcp', priority=10,
                                       recordContentSRV='10 60 5060 server.example.com')['add_status'])
        self.assertEqual((self.zone, '_sip._tcp.panelqa.test', 'SRV', '60 5060 server.example.com', 10, 3600),
                         self.stored())

    def test_srv_that_names_another_priority_is_refused_and_nothing_is_stored(self):
        reply = self.reply(recordType='SRV', recordName='_sip._tcp', priority=10,
                           recordContentSRV='20 60 5060 server.example.com')
        self.assertEqual(0, reply['add_status'])
        self.assertEqual('The content begins with the priority 20, but the Priority field holds 10. ' + SRV_EXPECTED,
                         reply['error_message'])
        self.dns.createDNSRecord.assert_not_called()

    def test_srv_without_a_usable_priority_is_refused(self):
        for priority in ({}, {'priority': None}, {'priority': ''}, {'priority': 70000}):
            reply = self.reply(recordType='SRV', recordName='_sip._tcp',
                               recordContentSRV='5 5060 sip.example.com', **priority)
            self.assertEqual((0, PRIORITY_EXPECTED), (reply['add_status'], reply['error_message']), priority)
        self.dns.createDNSRecord.assert_not_called()

    def test_srv_content_of_another_shape_is_refused(self):
        for content in ('sip.example.com', '5 99999 sip.example.com', '5 5060 sip..example.com'):
            reply = self.reply(recordType='SRV', recordName='_sip._tcp', priority=10, recordContentSRV=content)
            self.assertEqual(0, reply['add_status'], content)
            self.assertIn(SRV_EXPECTED, reply['error_message'])
        self.dns.createDNSRecord.assert_not_called()

    def test_mx_is_stored_as_its_host_beside_its_priority(self):
        self.assertEqual(1, self.reply(recordType='MX', recordName='@', priority='10',
                                       recordContentMX='10 mail.panelqa.test')['add_status'])
        self.assertEqual((self.zone, 'panelqa.test', 'MX', 'mail.panelqa.test', 10, 3600), self.stored())

    def test_mx_that_names_another_priority_is_refused(self):
        reply = self.reply(recordType='MX', recordName='@', priority=10, recordContentMX='20 mail.panelqa.test')
        self.assertEqual(0, reply['add_status'])
        self.assertIn(MX_EXPECTED, reply['error_message'])
        self.dns.createDNSRecord.assert_not_called()

    def test_records_without_a_priority_field_are_stored_as_before(self):
        self.assertEqual(1, self.reply(recordType='TXT', recordName='@', recordContentTXT='10 20 30 text')['add_status'])
        self.assertEqual((self.zone, 'panelqa.test', 'TXT', '10 20 30 text', 0, 3600), self.stored())


class EditRecordTests(unittest.TestCase):
    """The inline edit of a stored record."""

    def setUp(self):
        self.acl = mock.Mock()
        self.acl.loadedACL.return_value = {'admin': 1}
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnershipZone.return_value = 1
        self.zone = SimpleNamespace(name='panelqa.test')
        self.record = SimpleNamespace(type='SRV', name='_sip._tcp.panelqa.test', ttl=3600, prio=10,
                                      content='10 60 5060 server.example.com', save=mock.Mock())
        self.dns = mock.Mock()
        scope = {
            'ACLManager': self.acl, 'Administrator': mock.Mock(),
            'Records': SimpleNamespace(objects=SimpleNamespace(get=lambda pk: self.record)),
            'DNS': self.dns, 'HttpResponse': Reply, 'json': json,
            'record_priority': record_priority, 'srv_record_content': srv_record_content,
            'mx_record_content': mx_record_content,
        }
        self.update = method_of('dns/dnsManager.py', 'DNSManager', 'updateRecord', scope)

    def reply(self, **changed):
        data = dict({'selectedZone': 'panelqa.test', 'id': 5, 'nameNow': None, 'ttlNow': None,
                     'priorityNow': None, 'contentNow': None}, **changed)
        manager = SimpleNamespace(_record_zone=lambda record: self.zone)
        return json.loads(self.update(manager, 1, data).content)

    def test_a_stored_record_is_left_alone_by_an_edit_of_its_other_fields(self):
        self.assertEqual(1, self.reply(ttlNow=300)['status'])
        self.assertEqual(('10 60 5060 server.example.com', 10, 300),
                         (self.record.content, self.record.prio, self.record.ttl))
        self.record.save.assert_called_once_with()

    def test_a_new_srv_content_is_stored_beside_the_priority_of_the_record(self):
        self.assertEqual(1, self.reply(contentNow='5 8080 marker.panelqa.test.')['status'])
        self.assertEqual(('5 8080 marker.panelqa.test', 10), (self.record.content, self.record.prio))

    def test_priority_and_content_changed_together_agree_with_each_other(self):
        self.assertEqual(1, self.reply(priorityNow=20, contentNow='20 5 8080 marker.panelqa.test')['status'])
        self.assertEqual(('5 8080 marker.panelqa.test', 20), (self.record.content, self.record.prio))

    def test_an_unservable_srv_content_is_refused_and_nothing_is_saved(self):
        for content in ('20 60 5060 server.example.com', 'server.example.com', '5 99999 server.example.com'):
            reply = self.reply(contentNow=content)
            self.assertEqual(0, reply['status'], content)
            self.assertIn(SRV_EXPECTED, reply['error_message'])
        self.record.save.assert_not_called()
        self.dns.incrementSOASerial.assert_not_called()

    def test_a_priority_that_does_not_fit_is_refused(self):
        reply = self.reply(priorityNow=70000)
        self.assertEqual((0, PRIORITY_EXPECTED), (reply['status'], reply['error_message']))
        self.record.save.assert_not_called()

    def test_a_new_mx_content_follows_the_same_rule(self):
        self.record.type, self.record.content = 'MX', 'mail.panelqa.test'
        self.assertEqual(1, self.reply(contentNow='10 mail2.panelqa.test')['status'])
        self.assertEqual('mail2.panelqa.test', self.record.content)
        self.assertEqual(0, self.reply(contentNow='mail2.panelqa.test mail3.panelqa.test')['status'])
        self.assertEqual('mail2.panelqa.test', self.record.content)

    def test_other_record_types_are_edited_as_before(self):
        self.record.type, self.record.content, self.record.prio = 'TXT', 'old', 0
        self.assertEqual(1, self.reply(contentNow='10 20 30 text', priorityNow='7')['status'])
        self.assertEqual(('10 20 30 text', 7), (self.record.content, self.record.prio))


class CommandLineTests(unittest.TestCase):

    def setUp(self):
        self.dns = mock.Mock()
        self.status = mock.Mock()
        extract = lambda name: SimpleNamespace(domain='panelqa', suffix='test')

        def inert_import(name, *args, **kwargs):
            if name != 'tldextract':
                raise AssertionError('Unexpected import: ' + name)
            return SimpleNamespace(TLDExtract=lambda cache_dir: extract)

        scope = {
            '__builtins__': dict(vars(builtins), __import__=inert_import),
            'DNS': self.dns, 'logger': mock.Mock(), 'stack': lambda: [[None, None, None, 'createDNSRecord']],
            'record_priority': record_priority, 'srv_record_content': srv_record_content,
            'mx_record_content': mx_record_content,
        }
        create = method_of('cli/cyberPanel.py', 'cyberPanel', 'createDNSRecord', scope)
        self.create = lambda *record: create(SimpleNamespace(printStatus=self.status), 'panelqa.test', *record)

    def test_srv_value_is_weight_port_and_target(self):
        self.create('_sip._tcp.panelqa.test', 'SRV', '5 5060 sip.panelqa.test', '10', '3600')
        self.dns.createDNSRecord.assert_called_once_with(
            self.dns.getZoneObject.return_value, '_sip._tcp.panelqa.test', 'SRV', '5 5060 sip.panelqa.test', 10, 3600)
        self.status.assert_called_once_with(1, 'None')

    def test_srv_value_that_names_another_priority_is_refused(self):
        self.create('_sip._tcp.panelqa.test', 'SRV', '10 5 5060 sip.panelqa.test', '0', '3600')
        self.dns.createDNSRecord.assert_not_called()
        self.status.assert_called_once_with(
            0, 'The content begins with the priority 10, but the Priority field holds 0. ' + SRV_EXPECTED)

    def test_other_records_are_created_as_before(self):
        self.create('panelqa.test', 'A', '192.0.2.1', '0', '3600')
        self.dns.createDNSRecord.assert_called_once_with(
            self.dns.getZoneObject.return_value, 'panelqa.test', 'A', '192.0.2.1', 0, 3600)


class FormExampleTests(unittest.TestCase):
    """The example a form shows is a content the server stores unchanged."""

    PAGES = ('addDeleteDNSRecords.html', 'addDeleteDNSRecordsCloudFlare.html')

    def examples(self, page, model):
        text = (ROOT / 'dns' / 'templates' / 'dns' / page).read_text(encoding='utf-8')
        found = []
        for field in re.findall(r'<input[^>]*ng-model="%s"[^>]*>' % model, text):
            found.append(re.search(r'placeholder=(["\'])(.*?)\1', field).group(2))
        self.assertTrue(found, page)
        return found

    def test_the_srv_example_is_weight_port_and_target(self):
        for page in self.PAGES:
            for example in self.examples(page, 'recordContentSRV'):
                self.assertEqual(3, len(example.split()), page)
                for priority in (10, 0, 5):
                    self.assertEqual(example, srv_record_content(example, priority), page)

    def test_the_mx_example_is_the_mail_host(self):
        for page in self.PAGES:
            for example in self.examples(page, 'recordContentMX'):
                self.assertEqual(example, mx_record_content(example, 10), page)

    def test_the_srv_field_is_named_for_what_it_takes(self):
        page = (ROOT / 'dns' / 'templates' / 'dns' / 'addDeleteDNSRecords.html').read_text(encoding='utf-8')
        form = page[page.index('<!-- SRV Record -->'):page.index('<!-- CAA Record -->')]
        self.assertIn('<label>{% trans "Weight, Port and Target" %}</label>', form)
        self.assertIn('<label>{% trans "Priority" %}</label>', form)
        self.assertNotIn('10 60 5060', page)

    def test_the_srv_name_example_is_a_name_the_zone_is_added_to(self):
        page = (ROOT / 'dns' / 'templates' / 'dns' / 'addDeleteDNSRecords.html').read_text(encoding='utf-8')
        form = page[page.index('<!-- SRV Record -->'):page.index('<!-- CAA Record -->')]
        self.assertIn('placeholder="_service._proto"', form)


class OldestPythonTests(unittest.TestCase):

    def test_changed_modules_parse_on_python_3_6(self):
        options = {'feature_version': (3, 6)} if sys.version_info >= (3, 8) else {}
        for source in ('plogical/dnsRecordContent.py', 'dns/dnsManager.py', 'cli/cyberPanel.py',
                       'dns/test_prioritised_record_content.py'):
            ast.parse((ROOT / source).read_text(encoding='utf-8'), **options)


if __name__ == '__main__':
    unittest.main()
