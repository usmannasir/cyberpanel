import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
from plogical.terminalService import configure_terminal_service


class TerminalServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = pathlib.Path(self.directory.name) / 'source.service'
        self.target = pathlib.Path(self.directory.name) / 'target.service'
        self.source.write_text('[Service]\nExecStart=/usr/bin/true\n')

    def configure(self, load='loaded', active=False, fresh=False):
        def run(command, **kwargs):
            if command[1] == 'show':return SimpleNamespace(stdout=load, returncode=0)
            if command[1] == 'is-active':return SimpleNamespace(stdout='', returncode=0 if active else 3)
            return SimpleNamespace(stdout='', returncode=0)
        with mock.patch('plogical.terminalService.subprocess.run', side_effect=run) as execute:
            result = configure_terminal_service(fresh_install=fresh, source=str(self.source), target=str(self.target))
        return result, [call.args[0] for call in execute.call_args_list]

    def test_fresh_install_installs_and_enables_unit(self):
        result, commands = self.configure(load='not-found', fresh=True)
        self.assertEqual(result, 'enabled')
        self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
        self.assertIn(['systemctl','enable','--now','fastapi_ssh_server.service'], commands)

    def test_upgrade_preserves_explicitly_removed_unit(self):
        result, commands = self.configure(load='not-found')
        self.assertEqual(result, 'absent')
        self.assertFalse(self.target.exists())
        self.assertEqual(len(commands), 1)

    def test_upgrade_and_repeat_install_preserve_stopped_unit(self):
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                self.target.write_text('previous unit')
                result, commands = self.configure(fresh=fresh)
                self.assertEqual(result, 'inactive')
                self.assertFalse(any(command[1] in ('start','restart','enable') for command in commands))

    def test_masked_unit_is_never_replaced(self):
        self.target.symlink_to('/dev/null')
        result, commands = self.configure(load='masked', fresh=True)
        self.assertEqual(result, 'masked')
        self.assertEqual(self.target.readlink(), pathlib.Path('/dev/null'))
        self.assertEqual(len(commands), 1)

    def test_enabled_active_unit_is_refreshed_without_changing_enable_policy(self):
        self.target.write_text('previous unit')
        result, commands = self.configure(active=True)
        self.assertEqual(result, 'restarted')
        self.assertIn(['systemctl','restart','fastapi_ssh_server.service'], commands)
        self.assertFalse(any(command[1] == 'enable' for command in commands))

    def test_install_and_upgrade_use_distinct_lifecycle_policies(self):
        root = pathlib.Path(__file__).parents[1]
        self.assertIn('configure_terminal_service(fresh_install=True)',
                      (root / 'install/install.py').read_text())
        upgrade = (root / 'plogical/upgrade.py').read_text()
        self.assertIn('configure_terminal_service()', upgrade)
        self.assertNotIn('systemctl enable --now fastapi_ssh_server', upgrade)
        self.assertIn('systemctl is-active --quiet fastapi_ssh_server; then',
                      (root / 'cyberpanel_upgrade.sh').read_text())

    def test_unknown_service_state_fails_closed(self):
        with self.assertRaises(RuntimeError):self.configure(load='error')
        self.assertFalse(self.target.exists())


if __name__ == '__main__':unittest.main()
