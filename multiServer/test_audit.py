"""The audit trail: fixed events, typed fields, and nothing that could be a body or a secret."""
import ast
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

from multiServer import audit, schema

LINK = 'a1' * 16
COLUMNS = dict(next(table for table in schema.TABLES if table.name == 'ms_audit').columns)

# What a careless caller might hand over: none of it may reach a row.
PAIRING_CODE = 'CPMS1.' + 'Zm9vYmFy' * 24
TICKET = 'f3' * 32
SIGNATURE = '9c' * 64
PASSWORD = 'correct horse battery staple'
# Thirty-two hexadecimal digits are refused everywhere except as a link id, whose form they share.
NONCE_SIZED = 'e7' * 16
SECRETS = (PAIRING_CODE, TICKET, SIGNATURE, PASSWORD, NONCE_SIZED, '12345678', '654321',
           'gAAAAABn' + 'Qx7_' * 30, b'{"password": "hunter2"}', '{"password": "hunter2"}')


class Recorder(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for patcher in (patch.object(audit, '_write', side_effect=self.rows.append),
                        patch.object(audit.time, 'time', return_value=1795000000.9)):
            patcher.start()
            self.addCleanup(patcher.stop)


class RecordTests(Recorder):
    def test_one_row_with_the_time_the_event_and_an_ok_outcome(self):
        self.assertIs(True, audit.record('link_pause'))
        self.assertEqual([{'event': 'link_pause', 'outcome': 'ok', 'dropped': 0, 'at': 1795000000}], self.rows)

    def test_every_known_field_is_stored_as_given(self):
        self.assertIs(True, audit.record(
            'request', outcome='refused', reason='replay', link_id=LINK, actor='admin', source_ip='203.0.113.9',
            method='POST', path='/websites/submitWebsiteCreation', status=403, size=2048))
        self.assertEqual([{
            'event': 'request', 'outcome': 'refused', 'reason': 'replay', 'link_id': LINK, 'actor': 'admin',
            'source_ip': '203.0.113.9', 'method': 'POST', 'path': '/websites/submitWebsiteCreation',
            'status': 403, 'size': 2048, 'dropped': 0, 'at': 1795000000}], self.rows)

    def test_an_event_outside_the_list_writes_nothing(self):
        for event in ('request_body', 'REQUEST', '', 'request ', None, 7, b'request', ['request'], {},
                      PASSWORD, TICKET):
            self.assertIs(False, audit.record(event, actor='admin'), repr(event))
        self.assertEqual([], self.rows)

    def test_an_outcome_outside_the_list_writes_nothing_rather_than_ok(self):
        for outcome in ('denied', 'OK', '', None, 1, True, PASSWORD):
            self.assertIs(False, audit.record('request', outcome=outcome), repr(outcome))
        self.assertEqual([], self.rows)

    def test_the_caller_cannot_set_the_time_or_the_count_of_refused_fields(self):
        self.assertIs(True, audit.record('role', at=5, dropped=-3, id=9, event='licence'))
        self.assertEqual([{'event': 'role', 'outcome': 'ok', 'dropped': 4, 'at': 1795000000}], self.rows)
        self.assertIs(False, audit.record())
        self.assertIs(False, audit.record('role', 'licence'))
        self.assertIs(False, audit.record(event='role'))
        self.assertEqual(1, len(self.rows))

    def test_never_raises(self):
        with patch.object(audit, '_write', side_effect=RuntimeError('no such table')):
            self.assertIs(False, audit.record('licence', outcome='error', reason='internal'))
        with patch.object(audit, 'entry', side_effect=RuntimeError('unexpected')):
            self.assertIs(False, audit.record('licence'))

        class Hostile(str):
            def __eq__(self, other):
                raise RuntimeError('compared')
            __hash__ = str.__hash__
        self.assertIs(False, audit.record(Hostile('licence')))
        self.assertIs(True, audit.record('licence', actor=Hostile('admin')))
        self.assertEqual(1, self.rows[-1]['dropped'])


class BudgetTests(Recorder):
    def test_unverified_endpoints_share_a_rolling_budget_but_decisions_and_verified_calls_do_not(self):
        with patch.object(audit, '_unverified', audit._MinuteBudget(2)), patch.object(
                audit.time, 'monotonic', side_effect=[0, 5, 59, 60, 61, 65]):
            self.assertTrue(audit.record_unverified('request', reason='link', outcome='refused'))
            self.assertTrue(audit.record_unverified('pairing', reason='format', outcome='refused'))
            self.assertFalse(audit.record_unverified('request', reason='signature', outcome='refused'))
            self.assertTrue(audit.record('link_approve'))
            self.assertTrue(audit.record('request', actor='admin'))
            self.assertTrue(audit.record_unverified('pairing', reason='size', outcome='refused'))
            self.assertFalse(audit.record_unverified('request', reason='link', outcome='refused'))
            self.assertTrue(audit.record_unverified('request', reason='link', outcome='refused'))
        self.assertEqual(6, len(self.rows))


class RefusalTests(Recorder):
    def row(self, **fields):
        self.assertIs(True, audit.record('request', **fields))
        return self.rows[-1]

    def assert_refused(self, **fields):
        row = self.row(**fields)
        self.assertEqual({'event': 'request', 'outcome': 'ok', 'dropped': len(fields), 'at': 1795000000}, row,
                         fields)

    def test_there_is_no_field_for_a_body_a_password_a_code_a_ticket_or_a_signature(self):
        self.assert_refused(body=b'{"password": "hunter2"}', password=PASSWORD, code='12345678', ticket=TICKET,
                            signature=SIGNATURE, token=TICKET, detail='free text', message='free text',
                            request='{}', response='{}', query='a=b', headers={'Cookie': 'x'}, nonce='c3' * 16)

    def test_a_secret_put_in_any_field_never_reaches_the_row(self):
        for secret in SECRETS:
            for name in ('reason', 'link_id', 'actor', 'source_ip', 'method', 'path', 'status', 'size',
                         'body', 'note'):
                if (name, secret) != ('link_id', NONCE_SIZED):
                    self.assert_refused(**{name: secret})
            text = secret.decode() if isinstance(secret, bytes) else secret
            for path in ('/' + text, '/sso/' + text, '/sso/' + text + '/landing', '/x/ticket-' + text):
                row = self.row(path=path)
                self.assertNotIn(text, repr(row))

    def test_a_query_string_is_cut_from_a_path(self):
        self.assertEqual('/websites/listWebsites', self.row(path='/websites/listWebsites?ticket=' + TICKET)['path'])
        self.assertEqual('/websites/listWebsites', self.row(path='/websites/listWebsites#' + PASSWORD)['path'])
        self.assertEqual('/', self.row(path='/?page=2')['path'])
        self.assertEqual(0, self.rows[-1]['dropped'])

    def test_a_path_is_kept_whole_or_not_at_all(self):
        for path in ('/', '/base/', '/websites/example.com/manage', '/dataBases/submitDatabaseDeletion',
                     '/email/enableDisableIndividualEmailLimits', '/websites/12345',
                     '/' + '/'.join(['abcde'] * 42)):
            self.assertEqual(path, self.row(path=path)['path'])
        for path in ('', 'websites', '//', '/a//b', '/a b', '/a\nb', '/a/../b', '/a/./b', '/..', '/' + 'a' * 41,
                     '/' + '/'.join(['abcde'] * 43), '/a/' + '0123456789abcdef', '/a/ABCDEF0123456789',
                     '/a/123456', '/a/x123456y', '/a/%2e%2e', '/a;b', '/a\x00', '/a/é', 7, None, b'/a',
                     ['/a']):
            self.assert_refused(path=path)

    def test_an_actor_is_a_panel_user_name_and_nothing_longer_or_stranger(self):
        for actor in ('admin', 'ops.team@example.com', 'A_b-9', 'x' * 50):
            self.assertEqual(actor, self.row(actor=actor)['actor'])
        for actor in ('', 'x' * 51, 'two words', 'admin\n', "admin'--", 'deadbeefdeadbeef', 'user0123456', 7,
                      None, b'admin', True):
            self.assert_refused(actor=actor)

    def test_a_source_address_is_stored_in_its_one_canonical_form(self):
        for given, stored in (('203.0.113.9', '203.0.113.9'), ('2001:DB8:0:0:0:0:0:1', '2001:db8::1'),
                              ('::1', '::1')):
            self.assertEqual(stored, self.row(source_ip=given)['source_ip'])
        for address in ('', '203.0.113', '203.0.113.9 ', '203.0.113.9, 10.0.0.1', '203.0.113.0/24', 'localhost',
                        'fe80::1%eth0', 'fe80::1%' + PASSWORD, '1' * 46, 3405803785, None, b'203.0.113.9'):
            self.assert_refused(source_ip=address)

    def test_link_method_status_and_size_have_one_exact_form(self):
        for name, good, bad in (
                ('link_id', (LINK,), (LINK.upper(), LINK[:-1], LINK + 'a', 'g' * 32, '', None, 1, TICKET)),
                ('method', ('GET', 'POST'), ('get', 'PUT', 'DELETE', '', None, 'GET ')),
                ('status', (100, 200, 404, 599), (99, 600, -1, '200', 200.0, True, None)),
                ('size', (0, 1, 2 ** 40), (-1, 2 ** 40 + 1, '10', 1.5, False, None)),
                ('reason', audit.REASONS, ('Replay', 'because', '', None, PASSWORD))):
            for value in good:
                self.assertEqual(value, self.row(**{name: value})[name])
            for value in bad:
                self.assert_refused(**{name: value})


class VocabularyTests(unittest.TestCase):
    def test_every_word_and_every_accepted_value_fits_its_column(self):
        def width(column):
            return int(re.match(r'varchar\((\d+)\)', COLUMNS[column]).group(1))
        for column, words in (('event', audit.EVENTS), ('outcome', audit.OUTCOMES), ('reason', audit.REASONS),
                              ('method', audit.METHODS)):
            self.assertEqual(len(words), len(set(words)))
            for word in words:
                self.assertTrue(re.fullmatch(r'[a-z_]+|GET|POST', word), word)
                self.assertLessEqual(len(word), width(column), word)
        self.assertEqual(32, width('link_id'))
        self.assertEqual(50, width('actor'))
        self.assertEqual(45, width('source_ip'))
        self.assertEqual(audit.MAX_PATH, width('path'))
        self.assertLess(audit.MAX_SIZE, 2 ** 63)

    def test_a_row_has_only_columns_of_the_audit_table(self):
        row = audit.entry('request', dict(outcome='ok', reason='replay', link_id=LINK, actor='admin',
                                          source_ip='::1', method='GET', path='/', status=200, size=0))
        self.assertEqual(set(COLUMNS) - {'id', 'at'}, set(row))
        self.assertEqual(set(audit._FIELDS), set(COLUMNS) - {'id', 'at', 'event', 'dropped'})


class CompatibilityTests(unittest.TestCase):
    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_source_parses_as_python_3_6(self):
        ast.parse(Path(audit.__file__).read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
