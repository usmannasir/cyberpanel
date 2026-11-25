"""PostgreSQL for n8n: what counts as installed, which steps decide, and
when the service is running."""
from types import SimpleNamespace
import unittest
from unittest import mock

from plogical.processUtilities import ProcessUtilities
from plogical.test_child_domain_conversion import load_method

UBUNTU_WHICH = {'which psql': '', 'which apt-get': '/usr/bin/apt-get\n'}
ALMA_WHICH = {'which psql': 'which: no psql in (/usr/local/sbin:/usr/bin)\n',
              'which apt-get': 'which: no apt-get in (/usr/local/sbin:/usr/bin)\n'}


class PostgresSetupTests(unittest.TestCase):
    def setup(self, distro, which, statuses=None, initialised=False, active='active'):
        """statuses: command -> exit status 0 or not, for the commands run with retRequired."""
        statuses = statuses or {}
        ran, installed = [], []

        def output(command, user=None, shell=None, dir=None, retRequired=None, okStatuses=(0,)):
            ran.append(command)
            if retRequired:
                ok = statuses.get(command, 0) == 0
                if ok and 'install -y postgresql' in command:
                    installed.append(command)
                return (1 if ok else 0), ('' if ok else 'E: failure')
            if command in ('which psql', 'which apt-get'):
                return '/usr/bin/psql\n' if command == 'which psql' and installed else which[command]
            if command.startswith('systemctl list-unit-files'):
                return 'postgresql.service enabled enabled\n'
            if command.startswith('systemctl is-active'):
                return active + '\n'
            return ''

        patches = [mock.patch.object(ProcessUtilities, 'outputExecutioner', side_effect=output),
                   mock.patch.object(ProcessUtilities, 'executioner', return_value=1),
                   mock.patch.object(ProcessUtilities, 'checkedExecutioner',
                                     side_effect=lambda command: 1 if initialised else 0),
                   mock.patch.object(ProcessUtilities, 'decideDistro', return_value=distro),
                   mock.patch('time.sleep'),
                   mock.patch('os.path.exists', return_value=True),
                   mock.patch('builtins.open', mock.mock_open(read_data='{"postgrespassword": "pw"}'))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        setup = load_method('cloudAPI/cloudManager.py', 'CloudManager', '_setupPostgreSQLForN8N',
                            dict(logging=mock.Mock()))
        return (lambda: setup(SimpleNamespace())), ran

    def test_a_broken_package_source_does_not_stop_the_install_on_ubuntu(self):
        update = 'DEBIAN_FRONTEND=noninteractive apt-get update'
        run, ran = self.setup(ProcessUtilities.ubuntu, UBUNTU_WHICH, {update: 100})
        self.assertEqual((True, 'pw', None), run())
        self.assertIn('DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib', ran)

    def test_a_failed_package_install_still_stops_it(self):
        install = 'DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib'
        run, _ = self.setup(ProcessUtilities.ubuntu, UBUNTU_WHICH, {install: 100})
        status, _, message = run()
        self.assertFalse(status)
        self.assertIn('Failed to install PostgreSQL', message)

    def test_almalinux_without_postgresql_installs_it_with_its_own_tools(self):
        # "which: no psql in (...)" is not a path: PostgreSQL is missing, and
        # "which: no apt-get in (...)" does not make it an apt system.
        run, ran = self.setup(ProcessUtilities.cent9, ALMA_WHICH, {'yum install -y epel-release': 1})
        self.assertEqual((True, 'pw', None), run())
        self.assertIn('yum install -y postgresql postgresql-server postgresql-contrib', ran)
        self.assertIn('postgresql-setup initdb', ran)
        self.assertFalse(any('apt-get' in command and 'which' not in command for command in ran))

    def test_an_initialised_data_directory_is_not_initialised_again(self):
        run, ran = self.setup(ProcessUtilities.cent9, ALMA_WHICH, initialised=True)
        self.assertEqual((True, 'pw', None), run())
        self.assertNotIn('postgresql-setup initdb', ran)

    def test_an_inactive_service_is_not_running(self):
        for state in ('inactive', 'failed', ''):
            run, _ = self.setup(ProcessUtilities.ubuntu, {'which psql': '/usr/bin/psql\n'}, active=state)
            self.assertEqual((False, None, 'PostgreSQL service failed to start'), run(), state)


if __name__ == '__main__':
    unittest.main()
