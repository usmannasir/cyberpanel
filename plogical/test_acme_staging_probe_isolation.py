"""The acme.sh staging dry-run must never touch the domain's real acme.sh config."""
import ast
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


SOURCE = Path(__file__).with_name('sslUtilities.py')
DOMAIN = 'fixture.example.invalid'


def load_ssl_utilities(namespace):
    module = ast.parse(SOURCE.read_text())
    cls = next(node for node in module.body
               if isinstance(node, ast.ClassDef) and node.name == 'sslUtilities')
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['sslUtilities']


class StagingProbeIsolationTests(unittest.TestCase):
    def run_fallback(self, staging_rc=0, production_rc=1):
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            if ' --staging' in command:
                rc = staging_rc
            elif ' --issue' in command:
                rc = production_rc
            else:
                rc = 0
            return SimpleNamespace(returncode=rc, stdout='', stderr='')

        failing_acme = mock.Mock()
        failing_acme.return_value.issue_certificate.return_value = False
        fakes = {
            'plogical.acl': ModuleType('plogical.acl'),
            'plogical.sslv2': ModuleType('plogical.sslv2'),
            'plogical.customACME': ModuleType('plogical.customACME'),
        }
        fakes['plogical.acl'].ACLManager = object
        fakes['plogical.sslv2'].sslUtilities = object
        fakes['plogical.customACME'].CustomACME = failing_acme

        namespace = {
            'os': SimpleNamespace(path=SimpleNamespace(exists=lambda path: True), environ=os.environ),
            're': __import__('re'), 'shlex': shlex, 'shutil': shutil, 'tempfile': tempfile,
            'subprocess': SimpleNamespace(run=run, call=lambda *a, **k: 0, PIPE=None),
            'socket': SimpleNamespace(gethostname=lambda: 'fixture-host'),
            'logging': SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(
                writeToFile=lambda *a, **k: None, SendEmail=lambda *a, **k: None)),
            'ProcessUtilities': SimpleNamespace(normalExecutioner=lambda c: None,
                                                executioner=lambda c: None),
            'Websites': SimpleNamespace(objects=SimpleNamespace(
                get=mock.Mock(side_effect=LookupError('no site')))),
        }
        ssl = load_ssl_utilities(namespace)
        ssl.CheckIfSSLNeedsToBeIssued = staticmethod(lambda domain: ssl.ISSUE_SSL)
        ssl.PatchVhostConf = staticmethod(lambda domain: None)
        ssl.checkDNSRecords = staticmethod(lambda domain: False)
        with mock.patch.dict(sys.modules, fakes):
            result = ssl.obtainSSLForADomain(DOMAIN, 'admin@fixture.invalid', '/unused')
        return result, commands

    def test_staging_probe_uses_a_throwaway_config_home(self):
        result, commands = self.run_fallback(staging_rc=0, production_rc=1)
        self.assertEqual(0, result)
        staging = [c for c in commands if ' --staging' in c]
        self.assertEqual(1, len(staging))
        home = shlex.split(staging[0])[shlex.split(staging[0]).index('--config-home') + 1]
        self.assertTrue(home.startswith(tempfile.gettempdir()))
        self.assertFalse(os.path.exists(home), 'probe config home must be removed')
        for command in commands:
            if command is not staging[0]:
                self.assertNotIn('--config-home', command)
                self.assertNotIn('--staging', command)

    def test_production_issue_still_follows_a_successful_probe(self):
        result, commands = self.run_fallback(staging_rc=0, production_rc=0)
        self.assertEqual(1, result)
        production = [c for c in commands if ' --issue' in c and ' --staging' not in c]
        self.assertEqual(1, len(production))
        self.assertIn('--server letsencrypt', production[0])
        self.assertTrue(any('--install-cert' in c for c in commands))

    def test_failed_probe_skips_production(self):
        result, commands = self.run_fallback(staging_rc=1)
        self.assertEqual(0, result)
        self.assertFalse(any(' --issue' in c and ' --staging' not in c for c in commands))


def make_cert(path, organization, days=60):
    from datetime import datetime, timedelta, timezone
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = ec.generate_private_key(ec.SECP256R1())
    issuer = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                        x509.NameAttribute(NameOID.COMMON_NAME, 'Fixture Issuer')])
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, DOMAIN)])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
            .public_key(key.public_key()).serial_number(1)
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=days))
            .sign(key, hashes.SHA256()))
    Path(path).write_bytes(cert.public_bytes(serialization.Encoding.PEM))


class StagingCertificateHealTests(unittest.TestCase):
    def issue(self, organization, days=60):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        cert = Path(temp.name) / 'fullchain.pem'
        make_cert(cert, organization, days)
        live = '/etc/letsencrypt/live/' + DOMAIN + '/fullchain.pem'
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            return SimpleNamespace(returncode=0, stdout='', stderr='')

        utility = SimpleNamespace(
            acmeEnvironment=lambda: {}, checkDNSRecords=lambda d: False,
            lswsReloadCmd='fixture-reload', installSSLForDomain=lambda *a: 1,
            obtainSSLForADomain=mock.Mock(side_effect=AssertionError('fell through')),
            parseACMEError=lambda output: output)
        namespace = {
            'sslUtilities': utility,
            'logging': SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=lambda *a, **k: None)),
            'os': SimpleNamespace(path=SimpleNamespace(exists=lambda p: p in (live, '/root/.acme.sh/acme.sh') or p.startswith('/etc/letsencrypt/live/'))),
            'subprocess': SimpleNamespace(run=run, call=lambda *a, **k: 0, PIPE=None),
            'open': lambda path, mode='r': open(cert if path == live else path, mode),
        }
        module = ast.parse(SOURCE.read_text())
        func = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'issueSSLForDomain')
        exec(compile(ast.Module(body=[func], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        result = namespace['issueSSLForDomain'](DOMAIN, 'admin@fixture.invalid', '/unused')
        return result, [c for c in commands if ' --issue' in c or ' --renew' in c]

    def test_valid_staging_certificate_is_reissued_against_production(self):
        result, acme = self.issue("(STAGING) Let's Encrypt", days=60)
        self.assertEqual(1, result[0])
        self.assertEqual(1, len(acme))
        self.assertIn(' --issue ', acme[0])
        self.assertIn('--server letsencrypt', acme[0])
        self.assertNotIn('--renew', acme[0])

    def test_production_certificate_still_renews_in_place(self):
        result, acme = self.issue("Let's Encrypt", days=10)
        self.assertEqual(1, result[0])
        self.assertIn(' --renew ', acme[0])


class RenewStagingTests(unittest.TestCase):
    def test_renew_cron_reissues_staging_certificate_before_expiry(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        cert = Path(temp.name) / 'fullchain.pem'
        make_cert(cert, "(STAGING) Let's Encrypt", days=60)
        live = '/etc/letsencrypt/live/' + DOMAIN + '/fullchain.pem'
        import OpenSSL
        from datetime import datetime
        issue = mock.Mock(return_value=[1, 'None'])
        namespace = {
            'os': SimpleNamespace(path=SimpleNamespace(exists=lambda p: p == live)),
            'open': lambda path, mode='r': open(cert if path == live else path, mode),
            'OpenSSL': OpenSSL, 'datetime': datetime,
            'logging': SimpleNamespace(writeToFile=lambda *a, **k: None),
            'virtualHostUtilities': SimpleNamespace(issueSSL=issue),
            'Union': object, 'Optional': object,
        }
        source = SOURCE.with_name('renew.py')
        module = ast.parse(source.read_text())
        cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'Renew')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_check_and_renew_ssl')
        method.decorator_list = []
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
        namespace['_check_and_renew_ssl'](None, DOMAIN, '/home/' + DOMAIN, 'admin@fixture.invalid')
        issue.assert_called_once_with(DOMAIN, '/home/' + DOMAIN, 'admin@fixture.invalid')


if __name__ == '__main__':
    unittest.main(verbosity=2)
