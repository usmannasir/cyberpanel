"""Actual ACME methods with inert providers; no CA, DNS or system actions."""
import ast
import base64
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

SOURCE = Path(os.environ.get('ACME_TEST_SOURCE_PATH', str(Path(__file__).parent)))
DOMAIN = 'fixture.example.invalid'
PRODUCTION = 'https://acme-v02.api.letsencrypt.org/directory'
STAGING = 'https://acme-staging-v02.api.letsencrypt.org/directory'


def forbidden(*args, **kwargs):
    raise AssertionError('Unexpected external provider')


def load_actual(path, wanted, env):
    """Execute exact nodes; omit unrelated application imports/bootstrap only."""
    tree = ast.parse(path.read_text(), filename=str(path))
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted:
            selected.append(node)
    assert {node.name for node in selected} == set(wanted)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), env)
    return env


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='acme-environment-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs = []
        self.network = []
        self.orders = []
        self.accounts = []
        self.processes = []
        self.logger = SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(
            writeToFile=lambda *args: self.logs.append(args), SendEmail=forbidden))
        self.requests = SimpleNamespace(post=forbidden, get=forbidden, head=forbidden)
        self.env = load_actual(SOURCE / 'customACME.py', {'_atomic_write', 'CustomACME'}, {
            'os': os, 'tempfile': tempfile, 'logging': self.logger,
            'requests': self.requests, 'json': json, 'base64': base64,
            'x509': x509, 'rsa': rsa, 'hashes': hashes,
            'serialization': serialization, 'default_backend': default_backend,
            'time': SimpleNamespace(sleep=forbidden), 'socket': SimpleNamespace(),
        })
        self.cls = self.env['CustomACME']
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.old_key = self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, DOMAIN)])
        issuer = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, 'Private fixture issuer')])
        self.old_cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
            .public_key(self.key.public_key()).serial_number(1)
            .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=10))
            .sign(self.key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM))
        self.cert_dir = self.root / 'certificates'
        self.cert_dir.mkdir()
        (self.cert_dir / 'fullchain.pem').write_bytes(self.old_cert)
        (self.cert_dir / 'privkey.pem').write_bytes(self.old_key)
        (self.cert_dir / 'privkey.pem').chmod(0o600)
        self.before = self.snapshot()

    def snapshot(self):
        return {p.name: (p.read_bytes(), stat.S_IMODE(p.stat().st_mode), p.stat().st_ino)
                for p in self.cert_dir.iterdir()}

    def client(self, staging=False, provider='letsencrypt', statuses=None):
        # Exact constructor selection, but no /etc setup; every later write is private.
        with mock.patch.object(os, 'makedirs'), mock.patch.object(os, 'chmod'):
            obj = self.cls(DOMAIN, 'admin@fixture.invalid', staging=staging, provider=provider)
        obj.cert_path = str(self.cert_dir)
        obj.account_key_path = str(self.root / ('account-' + provider + '.key'))
        obj.account_key = self.key
        obj._load_account_key = mock.Mock(return_value=True)
        obj._generate_account_key = mock.Mock(side_effect=forbidden)
        obj._check_dns_record = mock.Mock(return_value=True)
        obj._get_nonce = mock.Mock(return_value=True)
        obj._create_jws = mock.Mock(return_value='fixture-jws')
        obj._save_account_key = mock.Mock(return_value=True)
        def directory():
            self.accounts.append(obj.acme_directory)
            obj.directory = {'newAccount': obj.acme_directory + '/account'}
            return True
        obj._get_directory = mock.Mock(side_effect=directory)
        directory()
        self.accounts.clear()
        sequence = list(statuses) if statuses is not None else None
        def post(url, **kwargs):
            self.network.append((obj.staging, obj.provider, url))
            if url.endswith('/account'):
                status = sequence.pop(0) if sequence else (201 if obj.staging else 500)
                return SimpleNamespace(status_code=status, headers={'Location': 'https://fixture.invalid/account'},
                                       text='badNonce' if status == 400 else 'failure')
            if url == 'https://fixture.invalid/auth':
                return SimpleNamespace(status_code=200, json=lambda: {'challenges': []})
            if url == 'https://fixture.invalid/order':
                return SimpleNamespace(status_code=200, json=lambda: {'identifiers': [{'value': DOMAIN}]})
            if url == 'https://fixture.invalid/certificate':
                return SimpleNamespace(status_code=200, content=self.old_cert)
            return forbidden()
        self.requests.post = post
        def order(domains):
            self.orders.append((obj.staging, obj.provider, tuple(domains)))
            obj.authorizations = ['https://fixture.invalid/auth']
            obj.order_url = 'https://fixture.invalid/order'
            obj.certificate_url = 'https://fixture.invalid/certificate'
            return True
        obj._create_order = mock.Mock(side_effect=order)
        obj._finalize_order = mock.Mock(return_value=True)
        obj._wait_for_order_processing = mock.Mock(return_value=True)
        return obj

    def test_production_account_429_stops_without_environment_change_or_retry(self):
        obj = self.client(statuses=[429, 201])
        self.assertFalse(obj._create_account())
        self.assertFalse(obj.staging)
        self.assertEqual(PRODUCTION, obj.acme_directory)
        self.assertEqual(1, len(self.network))
        obj._get_directory.assert_not_called()
        obj._get_nonce.assert_not_called()
        obj._save_account_key.assert_not_called()

    def test_explicit_staging_rate_limit_does_not_recurse(self):
        obj = self.client(staging=True, statuses=[429, 201])
        self.assertFalse(obj._create_account())
        self.assertTrue(obj.staging)
        self.assertEqual(STAGING, obj.acme_directory)
        self.assertEqual(1, len(self.network))

    def test_bad_nonce_retry_keeps_requested_environment(self):
        obj = self.client(statuses=[400, 201])
        self.assertTrue(obj._create_account())
        self.assertFalse(obj.staging)
        self.assertEqual(2, len(self.network))
        obj._get_nonce.assert_called_once()

    def test_production_account_failure_does_not_order_or_replace_existing_material(self):
        obj = self.client()
        self.assertFalse(obj.issue_certificate([DOMAIN]))
        self.assertFalse(obj.staging)
        self.assertEqual([], self.orders)
        self.assertEqual(self.before, self.snapshot())
        self.assertEqual([PRODUCTION], self.accounts)

    def test_production_rate_limit_does_not_order_or_replace_existing_material(self):
        obj = self.client(statuses=[429, 201])
        self.assertFalse(obj.issue_certificate([DOMAIN]))
        self.assertEqual([], self.orders)
        self.assertEqual(self.before, self.snapshot())
        self.assertEqual(1, len(self.network))

    def test_zerossl_account_failure_keeps_production(self):
        obj = self.client(provider='zerossl')
        self.assertFalse(obj.issue_certificate([DOMAIN]))
        self.assertFalse(obj.staging)
        self.assertEqual('https://acme.zerossl.com/v2/DV90', obj.acme_directory)
        self.assertEqual([], self.orders)
        self.assertEqual(self.before, self.snapshot())

    def test_jws_failure_preserves_existing_material(self):
        obj = self.client()
        obj._create_jws.return_value = None
        self.assertFalse(obj.issue_certificate([DOMAIN]))
        self.assertFalse(obj.staging)
        self.assertEqual([], self.orders)
        self.assertEqual([], self.network)
        self.assertEqual(self.before, self.snapshot())

    def test_production_success_still_writes_only_private_fixture_files(self):
        obj = self.client(statuses=[201])
        self.assertTrue(obj.issue_certificate([DOMAIN]))
        self.assertFalse(obj.staging)
        self.assertEqual([(False, 'letsencrypt', (DOMAIN,))], self.orders)
        self.assertEqual(self.old_cert, (self.cert_dir / 'fullchain.pem').read_bytes())
        self.assertEqual(0o600, stat.S_IMODE((self.cert_dir / 'privkey.pem').stat().st_mode))

    def test_explicit_staging_success_remains_explicit(self):
        obj = self.client(staging=True, statuses=[201])
        self.assertTrue(obj.issue_certificate([DOMAIN]))
        self.assertTrue(obj.staging)
        self.assertEqual([STAGING], self.accounts)
        self.assertEqual([(True, 'letsencrypt', (DOMAIN,))], self.orders)
        self.assertEqual(self.old_cert, (self.cert_dir / 'fullchain.pem').read_bytes())

    def caller(self, secondary_success=False):
        source = ast.parse((SOURCE / 'sslUtilities.py').read_text())
        klass = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'sslUtilities')
        obtain = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == 'obtainSSLForADomain')
        obtain.decorator_list = []
        issue = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'issueSSLForDomain')
        def factory(domain, email, staging, provider):
            self.assertFalse(staging)
            return self.client(staging=staging, provider=provider,
                statuses=[201] if secondary_success and provider == 'zerossl' else None)
        prefix = '/etc/letsencrypt/live/' + DOMAIN
        def path(value):
            value = os.fspath(value)
            return str(self.cert_dir) + value[len(prefix):] if value.startswith(prefix) else value
        def exists(value):
            value = os.fspath(value)
            if value.startswith(prefix):
                return os.path.exists(path(value))
            if value == '/usr/local/lsws/Example/html/.well-known/acme-challenge':
                return True
            if value == '/root/.acme.sh/acme.sh':
                return False
            return False
        def run(command, **kwargs):
            self.processes.append(command)
            # Existing acme.sh test step succeeds, production step fails: no install.
            return SimpleNamespace(returncode=0 if '--staging' in command else 1, stdout='', stderr='fixture failure')
        utility = SimpleNamespace(ISSUE_SSL=1, CheckIfSSLNeedsToBeIssued=lambda *_: 1,
            PatchVhostConf=lambda *_: None, checkDNSRecords=lambda *_: False,
            acmeEnvironment=lambda: {}, installSSLForDomain=mock.Mock(return_value=1),
            lswsReloadCmd='fixture-no-reload')
        env = {'sslUtilities': utility, 'logging': self.logger, 'CustomACME': factory,
            'ProcessUtilities': SimpleNamespace(executioner=lambda *a: None, normalExecutioner=forbidden),
            'Websites': SimpleNamespace(objects=SimpleNamespace(get=mock.Mock(side_effect=LookupError))),
            'subprocess': SimpleNamespace(PIPE=-1, call=lambda *a, **k: 1, run=run),
            'os': SimpleNamespace(path=SimpleNamespace(exists=exists, lexists=exists)),
            'shlex': shlex, 'open': lambda name, mode: open(path(name), mode)}
        exec(compile(ast.Module(body=[obtain, issue], type_ignores=[]), str(SOURCE / 'sslUtilities.py'), 'exec'), env)
        utility.obtainSSLForADomain = env['obtainSSLForADomain']
        # Keep the actual caller's local imports; only their external providers are inert.
        package = ModuleType('plogical')
        package.__path__ = []
        acl = ModuleType('plogical.acl')
        acl.ACLManager = SimpleNamespace()
        v2 = ModuleType('plogical.sslv2')
        v2.sslUtilities = SimpleNamespace()
        acme_module = ModuleType('plogical.customACME')
        acme_module.CustomACME = factory
        patches = mock.patch.dict(sys.modules, {'plogical': package, 'plogical.acl': acl,
            'plogical.sslv2': v2, 'plogical.customACME': acme_module})
        patches.start()
        self.addCleanup(patches.stop)
        hostname = mock.patch('socket.gethostname', return_value='fixture.invalid')
        hostname.start()
        self.addCleanup(hostname.stop)
        return env, utility

    def test_actual_caller_both_providers_fail_without_staging_install(self):
        env, utility = self.caller()
        self.assertEqual(0, env['obtainSSLForADomain'](DOMAIN, 'admin@fixture.invalid', '/private-webroot', forceIssue=True))
        self.assertEqual(self.before, self.snapshot())
        self.assertEqual([], self.orders)
        self.assertTrue(self.processes)
        self.assertTrue(all('--install-cert' not in command for command in self.processes))
        self.assertFalse(any(staging for staging, _, _ in self.network))

    def test_actual_caller_can_continue_to_second_production_provider(self):
        env, utility = self.caller(secondary_success=True)
        self.assertEqual(1, env['obtainSSLForADomain'](DOMAIN, 'admin@fixture.invalid', '/private-webroot', forceIssue=True))
        self.assertEqual([(False, 'zerossl', (DOMAIN,))], self.orders)
        self.assertEqual([], self.processes)

    def test_actual_main_outcome_retains_existing_certificate_after_acquisition_failure(self):
        env, utility = self.caller()
        result = env['issueSSLForDomain'](DOMAIN, 'admin@fixture.invalid', '/private-webroot', forceIssue=True)
        self.assertEqual(2, result[0])
        self.assertEqual('existing_certificate', result[2]['outcome'])
        self.assertTrue(result[2]['retained_existing'])
        self.assertEqual(self.before, self.snapshot())
        self.assertEqual([], self.orders)
        utility.installSSLForDomain.assert_called_once_with(DOMAIN)


if __name__ == '__main__':
    unittest.main(verbosity=2)
