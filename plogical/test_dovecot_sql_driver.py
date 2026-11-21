"""An RPM server whose Dovecot lacks the MySQL driver gets it, and nothing else is touched."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import dovecotSqlDriver  # noqa: E402


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = Path(self.directory.name, 'dovecot-sql.conf.ext')
        self.settings.write_text('driver = mysql\n')
        self.installed = {'dovecot'}
        self.commands, self.log = [], []
        self.install_works = True
        patcher = mock.patch.object(dovecotSqlDriver.os.path, 'exists',
                                    lambda path: path == '/usr/bin/rpm' or Path(path).exists())
        patcher.start()
        self.addCleanup(patcher.stop)

    def succeeds(self, *command):
        self.commands.append(command)
        if command[:2] == ('rpm', '-q'):
            return command[2] in self.installed
        if command[:3] == ('dnf', 'install', '-y'):
            if self.install_works:
                self.installed.add(command[3])
            return self.install_works
        return True

    def repair(self):
        return dovecotSqlDriver.repair(self.log.append, self.succeeds, str(self.settings))

    def changes(self):
        return [command for command in self.commands if command[0] != 'rpm']

    def test_missing_driver_is_installed_and_mail_services_restarted(self):
        self.assertEqual('installed', self.repair())
        self.assertEqual([('dnf', 'install', '-y', 'dovecot-mysql'), ('systemctl', 'restart', 'dovecot'),
                          ('systemctl', 'restart', 'postfix')], self.changes())
        self.assertIn('mail sign-in works again', self.log[0])
        self.commands.clear()
        self.assertEqual('not needed', self.repair())
        self.assertEqual([], self.changes())

    def test_server_with_the_driver_is_left_alone(self):
        self.installed.add('dovecot-mysql')
        self.assertEqual('not needed', self.repair())
        self.assertEqual([], self.changes())

    def test_other_dovecot_packages_are_left_alone(self):
        self.installed = {'dovecot23', 'dovecot23-mysql'}
        self.assertEqual('not needed', self.repair())
        self.assertEqual([], self.changes())

    def test_server_without_mail_set_up_is_left_alone(self):
        self.settings.unlink()
        self.assertEqual('not needed', self.repair())
        self.assertEqual([], self.changes())

    def test_systems_without_rpm_are_left_alone(self):
        with mock.patch.object(dovecotSqlDriver.os.path, 'exists', lambda path: Path(path).exists() and path != '/usr/bin/rpm'):
            self.assertEqual('not needed', self.repair())
        self.assertEqual([], self.commands)

    def test_failed_install_is_reported_and_services_are_not_restarted(self):
        self.install_works = False
        self.assertEqual('failed', self.repair())
        self.assertEqual([('dnf', 'install', '-y', 'dovecot-mysql')], self.changes())
        self.assertIn('could not be installed', self.log[0])


class CallSiteTests(unittest.TestCase):
    def test_upgrader_repairs_before_it_touches_the_mail_filter_settings(self):
        upgrader = (ROOT / 'plogical' / 'upgrade.py').read_text()
        call = 'repair_dovecot_sql_driver(log=Upgrade.stdOut)'
        self.assertEqual(1, upgrader.count(call))
        block = upgrader[upgrader.rindex('\n        try:\n', 0, upgrader.index(call)):upgrader.index('Upgrade.setupSieve()')]
        self.assertIn('from plogical.dovecotSqlDriver import repair as repair_dovecot_sql_driver', block)
        self.assertIn('except Exception as error:', block)
        self.assertLess(upgrader.index('Upgrade.downloadAndUpgrade('), upgrader.index(call))

    def test_installer_completes_the_distribution_dovecot_on_el8(self):
        installer = (ROOT / 'install' / 'install.py').read_text()
        start = installer.index("elif self.distro == cent8:\n                clAPVersion = FetchCloudLinuxAlmaVersionVersion()")
        block = installer[start:installer.index('elif self.distro == openeuler:', start)]
        self.assertEqual(2, block.count("command = 'dnf install -y dovecot dovecot-mysql'"))
        self.assertIn("subprocess.call(['rpm', '-q', 'dovecot']", block)
        self.assertLess(block.index("subprocess.call(['rpm', '-q', 'dovecot']"),
                        block.index("command = 'dnf install --enablerepo=gf-plus dovecot23 dovecot23-mysql -y'"))


if __name__ == '__main__':
    unittest.main()
