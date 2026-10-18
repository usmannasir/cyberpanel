"""Cloud upgrade failures must not invoke the obsolete destructive rollback."""
import ast
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

class CloudUpgradePreservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.current = self.root / 'CyberCP'
        self.stale_backup = self.root / 'CyberCPBak'
        for directory, data in ((self.current, 'current installation'),
                                (self.stale_backup, 'stale installation')):
            directory.mkdir()
            (directory/'identity').write_text(data)
        tree = ast.parse(Path(__file__).with_name('CyberPanelUpgrade.py').read_text())
        tree.body = [n for n in tree.body if isinstance(n, ast.ClassDef)]
        namespace = {'os': types.SimpleNamespace(path=types.SimpleNamespace(lexists=lambda _: False))}
        exec(compile(tree, 'CyberPanelUpgrade.py', 'exec'), namespace)
        cls = namespace['UpgradeCyberPanel']
        self.cloud = cls.__new__(cls)
        self.cloud.branch = 'v3.0.7'
        self.cloud.PostStatus = Mock()
        self.upgrade = Mock()
        self.upgrade.downloadAndUpgrade.return_value = (0, 'download failed')
        self.commands = []
        def execute(command, *args):
            self.commands.append(command)
            argv = shlex.split(command.replace('/usr/local', str(self.root)))
            if argv[0] in ('cp', 'rm', 'mv'):
                return int(subprocess.run(argv, capture_output=True).returncode == 0)
            return 1
        self.upgrade.executioner.side_effect = execute
        module = types.ModuleType('plogical.upgrade')
        module.Upgrade = self.upgrade
        self.modules = patch.dict(sys.modules, {'plogical.upgrade': module})
        self.modules.start()
        self.addCleanup(self.modules.stop)
    def test_download_failure_preserves_current_installation_despite_stale_backup(self):
        self.assertEqual(0, self.cloud.UpgardeNow())
        self.assertEqual('current installation', (self.current/'identity').read_text())
        self.assertEqual('stale installation', (self.stale_backup/'identity').read_text())
        self.assertEqual([], self.commands)
        self.upgrade.mailServerMigrations.assert_not_called()
        messages = [call.args[0] for call in self.cloud.PostStatus.call_args_list]
        self.assertTrue(messages[-1].endswith('[404]'))
        self.assertFalse(any('[200]' in message for message in messages))
    def test_restart_failure_reports_failure_without_following_success(self):
        self.upgrade.downloadAndUpgrade.return_value = (1, None)
        self.upgrade.executioner.side_effect = lambda *args: 0
        self.assertEqual(0, self.cloud.UpgardeNow())
        messages = [call.args[0] for call in self.cloud.PostStatus.call_args_list]
        self.assertIn('systemctl restart lscpd', messages[-1])
        self.assertIn('[404]', messages[-1])
        self.assertFalse(any('[200]' in message for message in messages))
    def test_success_reports_completion_only_after_restart(self):
        self.upgrade.downloadAndUpgrade.return_value = (1, None)
        self.assertIsNone(self.cloud.UpgardeNow())
        self.assertEqual(['systemctl restart lscpd'], self.commands)
        self.assertIn('[200]', self.cloud.PostStatus.call_args.args[0])

if __name__ == '__main__':
    unittest.main()
