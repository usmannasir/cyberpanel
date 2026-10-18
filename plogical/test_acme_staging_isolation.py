"""Real certificate fixtures and exact production methods; no CA/network calls."""
import ast
from datetime import datetime, timedelta
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
from types import ModuleType
import unittest
from unittest import mock

from OpenSSL import crypto

DOMAIN = 'staging.example.test'
PRODUCTION = 'https://acme-v02.api.letsencrypt.org/directory'
STAGING = 'https://acme-staging-v02.api.letsencrypt.org/directory'


def load_ssl_module():
    source = Path(__file__).with_name('sslUtilities.py')
    tree = ast.parse(source.read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
    module = ModuleType('ssl_test_subject')
    module.__dict__.update(os=os, re=re, shlex=shlex, shutil=shutil, socket=socket,
                           tempfile=tempfile, subprocess=subprocess,
                           logging=mock.Mock(), ProcessUtilities=mock.Mock(), Websites=mock.Mock())
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), module.__dict__)
    return module


def certificate(issuer='Production fixture CA', days=90, mismatch=False):
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    ca = crypto.PKey()
    ca.generate_key(crypto.TYPE_RSA, 2048)
    cert = crypto.X509()
    cert.get_subject().CN = DOMAIN
    name = crypto.X509().get_subject()
    name.CN = issuer
    cert.set_issuer(name)
    cert.set_serial_number(10)
    cert.gmtime_adj_notBefore(-86400 * 2)
    cert.gmtime_adj_notAfter(days * 86400)
    cert.set_pubkey(key)
    cert.sign(ca, 'sha256')
    return (crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
            crypto.dump_privatekey(crypto.FILETYPE_PEM, ca if mismatch else key))


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.module = load_ssl_module()
        self.ssl = self.module.sslUtilities
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.current = self.root / (DOMAIN + '_ecc')
        self.current.mkdir()
        self.live = self.root / 'live.pem'
        self.live.write_text('previous live certificate')
        self.config = self.current / (DOMAIN + '.conf')
        self.config.write_text("Le_API='%s'\nLe_RealFullChainPath='%s'\nLe_ReloadCmd='reload'\n" % (STAGING, self.live))
        self.key = self.current / (DOMAIN + '.key')
        self.key.write_text('previous key')
        self.before = {p.name: p.read_bytes() for p in self.current.iterdir()}
        self.commands = []

    def run_candidate(self, issuer='Production fixture CA', days=90, mismatch=False, rc=0, saved_ca=PRODUCTION,
                      write_material=True, staging_intermediate=False):
        pem, key = certificate(issuer, days, mismatch)
        chain = pem + (certificate('(STAGING) Intermediate CA')[0] if staging_intermediate else b'')
        def run(command, **kwargs):
            args = shlex.split(command)
            self.commands.append(args)
            self.assertEqual('letsencrypt', args[args.index('--server') + 1])
            cert_home = Path(args[args.index('--cert-home') + 1])
            self.assertNotEqual(self.root, cert_home)
            candidate = cert_home / (DOMAIN + '_ecc')
            config = candidate / (DOMAIN + '.conf')
            # Simulate acme.sh's automatic installation: these paths must be gone.
            self.assertNotIn('Le_RealFullChainPath', config.read_text())
            self.assertNotIn('Le_ReloadCmd', config.read_text())
            if rc == 0 and write_material:
                (candidate / 'fullchain.cer').write_bytes(chain)
                (candidate / (DOMAIN + '.cer')).write_bytes(pem)
                (candidate / (DOMAIN + '.key')).write_bytes(key)
                config.write_text("Le_API='%s'\n" % saved_ca)
            return subprocess.CompletedProcess(command, rc, 'HTTP-01 validation failed', 'token=do-not-log')
        with mock.patch.object(subprocess, 'run', side_effect=run):
            result = self.ssl.runProductionACME('acme.sh --renew -d ' + DOMAIN + ' --ecc --force',
                                                DOMAIN, str(self.root / 'acme.sh'), {})
        self.assertEqual('previous live certificate', self.live.read_text())
        self.assertFalse(Path(self.commands[0][self.commands[0].index('--cert-home') + 1]).exists())
        return result

    def test_contaminated_configuration_recovers_to_production_after_validation(self):
        self.assertEqual(0, self.run_candidate().returncode)
        self.assertIn(PRODUCTION, self.config.read_text())
        self.assertNotIn(STAGING, self.config.read_text())
        self.assertIn('Le_RealFullChainPath', self.config.read_text())
        self.ssl.validateACMECertificate(str(self.current / 'fullchain.cer'), str(self.key))

    def test_staging_result_cannot_replace_production_state_or_live_files(self):
        self.assertNotEqual(0, self.run_candidate(issuer='(STAGING) Artificial Apricot R3').returncode)
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.current.iterdir()})

    def test_expired_candidate_is_rejected(self):
        self.assertNotEqual(0, self.run_candidate(days=-1).returncode)
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.current.iterdir()})

    def test_staging_intermediate_is_rejected(self):
        self.assertNotEqual(0, self.run_candidate(staging_intermediate=True).returncode)
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.current.iterdir()})

    def test_exit_zero_without_new_material_cannot_reuse_the_old_certificate(self):
        self.assertNotEqual(0, self.run_candidate(write_material=False).returncode)
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.current.iterdir()})

    def test_mismatched_key_is_rejected(self):
        self.assertNotEqual(0, self.run_candidate(mismatch=True).returncode)
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.current.iterdir()})

    def test_saved_staging_ca_cannot_be_promoted_even_with_production_certificate(self):
        self.assertNotEqual(0, self.run_candidate(saved_ca=STAGING).returncode)
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.current.iterdir()})

    def test_failure_logs_diagnostics_without_credentials(self):
        self.assertEqual(1, self.run_candidate(rc=1).returncode)
        logs = str(self.module.logging.CyberCPLogFileWriter.writeToFile.call_args_list)
        self.assertIn('HTTP-01 validation failed', logs)
        self.assertNotIn('do-not-log', logs)

    def test_redaction_removes_private_keys_and_authenticated_urls(self):
        raw = ('HTTP-01 validation failed\n-----BEGIN PRIVATE KEY-----\nprivate-material\n'
               '-----END PRIVATE KEY-----\nhttps://user:password@ca.test/auth/secret\n'
               'eab_hmac_key=hidden-value\nAuthorization: Bearer bearer-value')
        safe = self.ssl.safeACMEOutput(raw)
        self.assertIn('HTTP-01 validation failed', safe)
        for secret in ('private-material', 'password', 'hidden-value', 'bearer-value'):
            self.assertNotIn(secret, safe)

    def test_failed_staging_precheck_uses_disposable_config_and_cert_home(self):
        import sys
        providers = mock.Mock()
        providers.CustomACME.return_value.issue_certificate.return_value = False
        modules = {'plogical.acl': mock.Mock(), 'plogical.sslv2': mock.Mock(),
                   'plogical.customACME': providers}
        self.ssl.CheckIfSSLNeedsToBeIssued = mock.Mock(return_value=self.ssl.ISSUE_SSL)
        self.ssl.PatchVhostConf = mock.Mock()
        self.ssl.checkDNSRecords = mock.Mock(return_value=False)
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            args = shlex.split(command)
            self.assertIn('--staging', args)
            home = Path(args[args.index('--config-home') + 1])
            self.assertEqual(str(home), args[args.index('--cert-home') + 1])
            (home / 'account.conf').write_text('staging account')
            (home / (DOMAIN + '_ecc')).mkdir()
            (home / (DOMAIN + '_ecc') / (DOMAIN + '.conf')).write_text("Le_API='%s'" % STAGING)
            return subprocess.CompletedProcess(command, 1, 'DNS validation failed', '')
        with mock.patch.dict(sys.modules, modules), mock.patch.object(subprocess, 'run', side_effect=run):
            self.assertEqual(0, self.ssl.obtainSSLForADomain(DOMAIN, 'admin@fixture.test', '/unused', forceIssue=True))
        self.assertEqual(1, len(calls))
        home = shlex.split(calls[0])[shlex.split(calls[0]).index('--config-home') + 1]
        self.assertFalse(os.path.exists(home))
        self.assertEqual(self.before, {p.name: p.read_bytes() for p in self.current.iterdir()})

    def test_installer_refuses_staging_before_writing_configuration(self):
        pem, _ = certificate(issuer='(STAGING) Fixture CA')
        with mock.patch.dict(self.module.__dict__, open=mock.mock_open(read_data=pem)):
            self.assertEqual(0, self.ssl.installSSLForDomain(DOMAIN))
        self.module.ProcessUtilities.decideServer.assert_not_called()

    def test_existing_staging_material_is_not_retained_as_public_success(self):
        pem, _ = certificate(issuer='(STAGING) Fixture CA')
        with mock.patch.object(os.path, 'exists', side_effect=lambda p: str(p).startswith('/etc/letsencrypt/live/')), \
                mock.patch.dict(self.module.__dict__, open=mock.mock_open(read_data=pem)), \
                mock.patch.object(self.ssl, 'obtainSSLForADomain', return_value=0), \
                mock.patch.object(self.ssl, 'installSSLForDomain') as install:
            result = self.module.issueSSLForDomain(DOMAIN, 'admin@fixture.test', '/unused')
        self.assertEqual(0, result[0])
        self.assertIn('staging', result[1])
        install.assert_not_called()


if __name__ == '__main__':
    unittest.main()
