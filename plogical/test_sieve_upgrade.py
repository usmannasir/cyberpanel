import ast
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from plogical.sieveUpgrade import (prepare_sieve_upgrade,
                                  SieveConfigCheckpoint, activate_sieve_config)


def result(code=0, output=''):
    return subprocess.CompletedProcess([], code, stdout=output, stderr='')


class SieveUpgradeTests(unittest.TestCase):
    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_invalid_existing_config_never_installs_or_restarts(self, run):
        run.return_value = result(1)
        self.assertFalse(prepare_sieve_upgrade(Mock()))
        self.assertEqual(1, run.call_count)

    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_dovecot24_is_not_rewritten_with_legacy_syntax(self, run):
        run.side_effect = [result(), result(output='2.4.2')]
        self.assertFalse(prepare_sieve_upgrade(Mock()))
        self.assertEqual(2, run.call_count)

    @patch('plogical.sieveUpgrade.os.path.exists', return_value=False)
    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_third_party_or_unknown_provider_is_not_migrated(self, run, exists):
        for code, provider in ((0, 'dovecot23\n1.gf.el8\nGhettoforge\n'),
                               (0, 'dovecot\n1.gf.el8\nGhettoforge\n'),
                               (0, 'dovecot\n1.el8\nUnknown\n'), (1, '')):
            run.reset_mock()
            run.side_effect = [result(), result(output='2.3.21'), result(code, provider)]
            self.assertFalse(prepare_sieve_upgrade(Mock()))
            self.assertEqual(3, run.call_count)

    @patch('plogical.sieveUpgrade.os.path.exists', return_value=False)
    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_stock_package_failure_is_attempted_only_once(self, run, exists):
        run.side_effect = [result(), result(output='2.3.16'),
                           result(output='dovecot\n16.el8_10\nAlmaLinux\n'), result(1)]
        self.assertFalse(prepare_sieve_upgrade(Mock()))
        installs = [c.args[0] for c in run.call_args_list if c.args[0][0] == 'dnf']
        self.assertEqual([['dnf', 'install', '-y', 'dovecot-pigeonhole']], installs)

    @patch('plogical.sieveUpgrade.os.path.exists', return_value=True)
    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_debian_packages_succeed_before_configuration(self, run, exists):
        run.side_effect = [result(), result(output='2.3.21'), result()]
        self.assertTrue(prepare_sieve_upgrade(Mock()))
        self.assertEqual(['apt-get','install','-y','dovecot-sieve','dovecot-managesieved'],
                         run.call_args.args[0])

    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_invalid_candidate_restores_config_without_restart(self, run):
        with tempfile.TemporaryDirectory() as directory:
            existing, new = Path(directory)/'existing', Path(directory)/'new'
            existing.write_bytes(b'original\n')
            existing.chmod(0o640)
            checkpoint = SieveConfigCheckpoint([existing, new])
            existing.write_bytes(b'invalid\n')
            new.write_bytes(b'new config\n')
            run.return_value = result(1)
            self.assertFalse(activate_sieve_config(checkpoint, Mock()))
            self.assertEqual(b'original\n', existing.read_bytes())
            self.assertEqual(0o640, existing.stat().st_mode & 0o777)
            self.assertFalse(new.exists())
            self.assertEqual(1, run.call_count)

    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_restart_failure_restores_and_recovers_previously_active_service(self, run):
        checkpoint = Mock()
        run.side_effect = [result(), result(), result(1), result()]
        self.assertFalse(activate_sieve_config(checkpoint, Mock()))
        checkpoint.restore.assert_called_once()
        self.assertEqual(2, sum(c.args[0] == ['systemctl','restart','dovecot']
                                for c in run.call_args_list))

    @patch('plogical.sieveUpgrade.subprocess.run')
    def test_valid_candidate_activates(self, run):
        checkpoint = Mock()
        run.side_effect = [result(), result(), result()]
        self.assertTrue(activate_sieve_config(checkpoint, Mock()))
        checkpoint.restore.assert_not_called()

    def test_real_setup_stops_before_config_access_when_preflight_fails(self):
        source = Path(__file__).with_name('upgrade.py').read_text()
        tree = ast.parse(source)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Upgrade')
        function = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'setupSieve')
        function.decorator_list = []
        module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
        fake_os, fake_upgrade = Mock(), Mock()
        fake_os.path.exists.return_value = True
        namespace = {'os': fake_os, 'Upgrade': fake_upgrade}
        exec(compile(module, '<real setupSieve>', 'exec'), namespace)
        with patch('plogical.sieveUpgrade.prepare_sieve_upgrade', return_value=False), \
                patch('builtins.open', side_effect=AssertionError('config must not be opened')), \
                patch('plogical.sieveUpgrade.SieveConfigCheckpoint') as checkpoint:
            namespace['setupSieve']()
        checkpoint.assert_not_called()
        fake_upgrade.executioner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
