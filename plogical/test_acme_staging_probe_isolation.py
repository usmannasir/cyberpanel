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


if __name__ == '__main__':
    unittest.main(verbosity=2)
