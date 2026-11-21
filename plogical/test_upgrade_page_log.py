"""The log the upgrade page shows belongs to the current run and is kept to its end."""
import ast
import os
import stat
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'plogical' / 'upgrade.py').read_text()


def upgrader_class():
    return next(node for node in ast.parse(SOURCE).body
                if isinstance(node, ast.ClassDef) and node.name == 'Upgrade')


def upgrader_method(name):
    method = next(node for node in upgrader_class().body if isinstance(node, ast.FunctionDef) and node.name == name)
    method.decorator_list = []
    return method


def method_text(name):
    """The source lines of one method, up to the next member of the class."""
    members = upgrader_class().body
    index = next(i for i, node in enumerate(members) if isinstance(node, ast.FunctionDef) and node.name == name)
    lines = SOURCE.splitlines()
    end = members[index + 1].lineno - 1 if index + 1 < len(members) else len(lines)
    return '\n'.join(lines[members[index].lineno - 1:end])


class PanelUpgradeLogTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.log = Path(self.directory.name, 'upgrade_logs')
        owner = types.SimpleNamespace(pw_uid=os.geteuid(), pw_gid=os.getegid())
        self.namespace = {'os': os, 'pwd': types.SimpleNamespace(getpwnam=lambda name: owner),
                          'Upgrade': types.SimpleNamespace(LogPathNew=str(self.log))}
        module = ast.Module(body=[upgrader_method('startPanelUpgradeLog')], type_ignores=[])
        exec(compile(module, 'upgrade.py', 'exec'), self.namespace)
        self.start = self.namespace['startPanelUpgradeLog']

    def test_lines_of_an_earlier_run_are_gone_and_only_the_panel_account_can_read_the_log(self):
        self.log.write_text('[06.27.2026_10-00-00] Upgrade Completed.\n')
        self.log.chmod(0o644)
        self.start()
        self.assertEqual('', self.log.read_text())
        self.assertEqual(0o600, stat.S_IMODE(self.log.stat().st_mode))
        self.log.unlink()
        self.start()
        self.assertEqual(0o600, stat.S_IMODE(self.log.stat().st_mode))

    def test_a_link_placed_at_the_log_path_is_not_followed(self):
        target = Path(self.directory.name, 'elsewhere')
        target.write_text('not a log\n')
        os.symlink(str(target), str(self.log))
        self.start()
        self.assertEqual('not a log\n', target.read_text())

    def test_a_missing_panel_account_does_not_stop_the_upgrade(self):
        def missing(name):
            raise KeyError(name)
        self.namespace['pwd'].getpwnam = missing
        self.start()


class UpgraderLogHandlingTests(unittest.TestCase):
    def test_a_run_started_from_the_panel_begins_its_log_before_any_work(self):
        body = method_text('upgrade')
        start = body.index("if branch.find('SoftUpgrade') > -1:\n            Upgrade.startPanelUpgradeLog()")
        self.assertLess(body.index('requireCSFMigration()'), start)
        self.assertLess(start, body.index('has_ols = '))

    def test_the_log_is_never_removed_by_the_upgrader(self):
        self.assertNotIn('os.remove(Upgrade.LogPathNew)', SOURCE)
        end = SOURCE.index('Upgrade.stdOut("Upgrade Completed.")')
        self.assertNotIn('time.sleep', SOURCE[end:SOURCE.index('def installQuota', end)])
        fatal = method_text('stdOut')
        self.assertNotIn('time.sleep', fatal)
        self.assertIn('os._exit(1)', fatal)


if __name__ == '__main__':
    unittest.main()
