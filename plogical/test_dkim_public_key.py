import ast
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from plogical.dkimPublicKey import parse_dkim_public_key


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = 'default._domainkey IN TXT ( "v=DKIM1; k=rsa; " "p=QUJDRA==" ) ; comment'


def extract_method(path, class_name, method_name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    method.decorator_list = []
    module = ast.Module(body=[method], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
    return namespace[method_name]


class DKIMPublicKeyTests(unittest.TestCase):
    def test_wrapped_and_single_line_txt_join_the_same_value(self):
        expected = 'v=DKIM1; k=rsa; p=QUJDRA=='
        for value in (PUBLIC, '"v=DKIM1; k=rsa; p=QUJDRA=="', expected):
            self.assertEqual(expected, parse_dkim_public_key(value))

    def test_missing_key_command_errors_and_revoked_keys_are_rejected(self):
        for value in ('', None, 'cat: default.txt: No such file', '"v=DKIM1; p="',
                      '"v=DKIM1; p=invalid!"', '"v=DKIM2; p=QUJDRA=="'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'DKIM public key'):
                    parse_dkim_public_key(value)

    def manager_fixture(self):
        namespace = {'json': json, 'parse_dkim_public_key': parse_dkim_public_key,
                     'HttpResponse': lambda content: SimpleNamespace(content=content)}
        for name in ('ACLManager', 'Administrator', 'ProcessUtilities', 'DNS',
                     'dnsDomains', 'dnsRecords', 'virtualHostUtilities'):
            namespace[name] = MagicMock()
        namespace['ACLManager'].currentContextPermission.return_value = 1
        namespace['ACLManager'].checkOwnership.return_value = 1
        namespace['DNS'].createDKIMRecords.return_value = 1
        namespace['ProcessUtilities'].outputExecutioner.side_effect = ['1,None', PUBLIC]
        namespace['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'
        extractor = MagicMock()
        extractor.TLDExtract.return_value.return_value = SimpleNamespace(
            domain='example', suffix='com', subdomain='mail')
        manager = SimpleNamespace(request=SimpleNamespace(
            session={'userID': 1}, body=json.dumps({'domainName': 'mail.example.com'})))
        return namespace, extractor, manager

    def test_child_generation_reads_parent_key_and_does_not_add_a_second_txt_row(self):
        namespace, extractor, manager = self.manager_fixture()
        generate = extract_method('mailServer/mailserverManager.py', 'MailServerManager',
                                  'generateDKIMKeys', namespace)
        with patch.dict('sys.modules', {'tldextract': extractor}):
            response = json.loads(generate(manager).content)
        self.assertEqual(1, response['generateStatus'])
        commands = [call.args[0] for call in namespace['ProcessUtilities'].outputExecutioner.call_args_list]
        self.assertIn('cat /etc/opendkim/keys/example.com/default.txt', commands)
        namespace['DNS'].createDKIMRecords.assert_called_once_with('mail.example.com')
        namespace['dnsRecords'].assert_not_called()

    def test_missing_public_key_or_dns_failure_cannot_be_generation_success(self):
        for output, dns_status in (('', 1), ('cat: missing file', 1), (PUBLIC, 0)):
            namespace, extractor, manager = self.manager_fixture()
            namespace['ProcessUtilities'].outputExecutioner.side_effect = ['1,None', output]
            namespace['DNS'].createDKIMRecords.return_value = dns_status
            generate = extract_method('mailServer/mailserverManager.py', 'MailServerManager',
                                      'generateDKIMKeys', namespace)
            with patch.dict('sys.modules', {'tldextract': extractor}):
                response = json.loads(generate(manager).content)
            self.assertEqual(0, response['generateStatus'])
            self.assertNotIn('substring', response['error_message'])

    def test_fetch_does_not_read_or_return_private_key_after_public_key_failure(self):
        namespace, extractor, manager = self.manager_fixture()
        namespace['ProcessUtilities'].outputExecutioner.side_effect = ['cat: missing file']
        fetch = extract_method('mailServer/mailserverManager.py', 'MailServerManager',
                               'fetchDKIMKeys', namespace)
        with patch.dict('sys.modules', {'tldextract': extractor}):
            response = json.loads(fetch(manager).content)
        self.assertEqual(0, response['keysAvailable'])
        self.assertNotIn('privateKey', response)
        self.assertIn('DKIM public key', response['error_message'])
        self.assertEqual(1, namespace['ProcessUtilities'].outputExecutioner.call_count)

    def test_existing_duplicate_txt_rows_are_updated_without_get_or_new_row(self):
        import shlex
        namespace = {'shlex': shlex}
        for name in ('Domains', 'Records', 'subprocess', 'ProcessUtilities', 'logging', 'DNS'):
            namespace[name] = MagicMock()
        namespace['Records'].objects.filter.return_value.count.return_value = 2
        namespace['subprocess'].check_output.return_value = PUBLIC.encode()
        namespace['DNS'].return_value.loadCFKeys.return_value = False
        namespace['ProcessUtilities'].decideDistro.return_value = 'other'
        extractor = MagicMock()
        extractor.TLDExtract.return_value.return_value = SimpleNamespace(
            domain='example', suffix='com', subdomain='mail')
        create = extract_method('plogical/dnsUtilities.py', 'DNS', 'createDKIMRecords', namespace)
        with patch.dict('sys.modules', {'tldextract': extractor}):
            self.assertEqual(1, create('mail.example.com'))
        namespace['Records'].objects.get.assert_not_called()
        namespace['Records'].assert_not_called()
        self.assertEqual(2, namespace['Records'].objects.filter.return_value.update.call_count)


@unittest.skipUnless(os.environ.get('CYBERPANEL_TEST_OPENDKIM') == '1' and
                     shutil.which('opendkim-genkey'),
                     'requires an explicitly selected OpenDKIM test host')
class OpenDKIMIntegrationTests(unittest.TestCase):
    def test_real_generated_keys_child_path_and_fail_before_service_restart(self):
        with tempfile.TemporaryDirectory(prefix='cp-dkim-gate-') as temporary:
            base = Path(temporary) / 'opendkim'
            (base / 'keys').mkdir(parents=True)
            tree = ast.parse((ROOT / 'plogical/mailUtilities.py').read_text())
            cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'mailUtilities')
            method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'setupDKIM')
            method.decorator_list = []
            # Redirect only filesystem literals; the actual generation code runs.
            for node in ast.walk(method):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    node.value = node.value.replace('/etc/opendkim', str(base))
            process = MagicMock()
            process.decideDistro.return_value = 'ubuntu'

            def normal_execution(command):
                args = shlex.split(command)
                if args[0] in ('mkdir', 'opendkim-genkey', '/usr/sbin/opendkim-genkey', 'chmod'):
                    return subprocess.run(args, check=True, capture_output=True).returncode
                if args[0] == 'chown':
                    return 0  # The disposable files are already readable by this test user.
                raise AssertionError('Unexpected fixture command: ' + args[0])

            process.normalExecutioner.side_effect = normal_execution
            service_calls = MagicMock()
            namespace = {'os': os, 'shlex': shlex, 'ProcessUtilities': process,
                         'subprocess': SimpleNamespace(call=service_calls), 'logging': MagicMock()}
            module = ast.Module(body=[method], type_ignores=[])
            exec(compile(ast.fix_missing_locations(module), 'setupDKIM-test', 'exec'), namespace)
            extractor = MagicMock()
            extractor.TLDExtract.return_value.return_value = SimpleNamespace(
                domain='example', suffix='com', subdomain='mail')
            with patch.dict('sys.modules', {'tldextract': extractor}):
                self.assertEqual((1, 'None'), namespace['setupDKIM']('mail.example.com'))
            public_file = base / 'keys/example.com/default.txt'
            self.assertTrue(parse_dkim_public_key(public_file.read_text()).startswith('v=DKIM1;'))
            self.assertFalse((base / 'keys/mail.example.com').exists())
            self.assertIn(str(base / 'keys/example.com/default.private'), (base / 'KeyTable').read_text())
            original_table = (base / 'KeyTable').read_bytes()
            public_file.write_text('missing or invalid key')
            service_calls.reset_mock()
            with patch.dict('sys.modules', {'tldextract': extractor}):
                result = namespace['setupDKIM']('mail.example.com')
            self.assertEqual(0, result[0])
            self.assertIn('DKIM public key', result[1])
            service_calls.assert_not_called()
            self.assertEqual(original_table, (base / 'KeyTable').read_bytes())


if __name__ == '__main__':
    unittest.main()
