"""The Applications page shows a one-click service as installed only when it is.

The installer used to write its marker file and report success after trying
the package and service commands, whatever they returned, and the page read
nothing but the marker. These tests use stand-ins for the commands and for
the files on the server; nothing is installed, started or asked of systemd.
"""
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from manageServices import applicationState as state

ROOT = Path(__file__).resolve().parents[1]

APT_LOCK = (
    'E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 41270 (apt-get)\n'
    'E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), is another process using it?\n')
APT_INSTALL = 'DEBIAN_FRONTEND=noninteractive apt-get install redis-server -y'


class Server(object):
    """A stand-in for the server: which programs exist and what each command does."""

    def __init__(self, package=(0, ''), installs=True, unit='active', program=False):
        self.package = package
        self.installs = installs
        self.unit = unit
        self.program = program
        self.commands = []

    def exists(self, path):
        return self.program

    def run(self, command, log):
        self.commands.append(command)
        if command.startswith('systemctl is-active'):
            return (0 if self.unit == 'active' else 3), self.unit + '\n'
        if command.startswith('systemctl'):
            return 0, ''
        if 'remove' in command or 'erase' in command:
            if self.package[0] == 0:
                self.program = False
            return self.package
        if self.package[0] == 0 and self.installs:
            self.program = True
        return self.package


class Markers(unittest.TestCase):
    """Each test gets marker paths of its own in a temporary folder."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        for name in ('Redis', 'Elasticsearch'):
            patch = mock.patch.dict(state.APPLICATIONS[name], {'marker': os.path.join(self.folder, name)})
            patch.start()
            self.addCleanup(patch.stop)

    def marker(self, name='Redis'):
        return os.path.exists(state.APPLICATIONS[name]['marker'])

    def install(self, server, name='Redis', debian=True, configure=None):
        return state.install(name, APT_INSTALL, debian, None, configure=configure,
                             run=server.run, exists=server.exists)

    def remove(self, server, name='Redis', debian=True):
        return state.remove(name, 'apt-get remove redis-server -y', debian, None,
                            run=server.run, exists=server.exists)


class PageState(Markers):

    def test_a_marker_alone_does_not_make_an_application_installed(self):
        state.remember('Redis')
        asked = []
        shown = state.state('Redis', True, asked.append, exists=lambda path: False)
        self.assertEqual(shown, state.NOT_INSTALLED)
        self.assertEqual(asked, [], 'systemd is not asked about a program that is not there')

    def test_installed_means_the_program_is_present_and_the_unit_is_active(self):
        self.assertFalse(self.marker())
        shown = state.state('Redis', True, lambda unit: 'active\n', exists=lambda path: True)
        self.assertEqual(shown, state.INSTALLED)

    def test_a_program_whose_unit_is_not_active_is_shown_as_stopped(self):
        for reply in ('inactive\n', 'failed\n', 'activating\n', 'unknown\n', '', None,
                      'Failed to connect to bus', 'inactive\nactive'):
            shown = state.state('Redis', True, lambda unit: reply, exists=lambda path: True)
            self.assertEqual(shown, state.STOPPED, repr(reply))

    def test_the_unit_asked_about_is_the_one_of_the_system(self):
        asked = []

        def reply(unit):
            asked.append(unit)
            return 'active'

        state.state('Redis', True, reply, exists=lambda path: True)
        state.state('Redis', False, reply, exists=lambda path: True)
        state.state('Elasticsearch', True, reply, exists=lambda path: True)
        self.assertEqual(asked, ['redis-server', 'redis', 'elasticsearch'])

    def test_the_program_looked_for_is_the_service_itself(self):
        looked = []
        state.state('Redis', True, lambda unit: 'active', exists=lambda path: looked.append(path))
        state.state('Elasticsearch', True, lambda unit: 'active', exists=lambda path: looked.append(path))
        self.assertEqual(looked, ['/usr/bin/redis-server', '/usr/share/elasticsearch/bin/elasticsearch'])


class Install(Markers):

    def test_a_held_package_lock_is_a_failure_that_says_so_and_leaves_no_marker(self):
        state.remember('Redis')  # left behind by an earlier false success
        server = Server(package=(100, APT_LOCK))
        done, message = self.install(server)
        self.assertFalse(done)
        self.assertIn('Redis was not installed.', message)
        self.assertIn('busy with another installation or update', message)
        self.assertIn('try again', message)
        self.assertFalse(self.marker())
        self.assertEqual(server.commands, [APT_INSTALL], 'no service is started for a package that is not there')

    def test_a_package_manager_that_returns_success_without_the_program_is_a_failure(self):
        server = Server(package=(0, 'Reading package lists...\n'), installs=False)
        done, message = self.install(server)
        self.assertFalse(done)
        self.assertIn('Redis was not installed.', message)
        self.assertFalse(self.marker())

    def test_another_failure_gives_the_package_managers_own_words(self):
        output = ('Reading package lists...\n'
                  'E: Unable to locate package redis-server\n')
        done, message = self.install(Server(package=(100, output)))
        self.assertFalse(done)
        self.assertIn('E: Unable to locate package redis-server', message)
        self.assertNotIn('busy', message)

    def test_a_service_that_does_not_run_is_a_failure_and_leaves_no_marker(self):
        state.remember('Redis')
        server = Server(unit='failed')
        done, message = self.install(server)
        self.assertFalse(done)
        self.assertIn('is installed, but its service (redis-server) is not running', message)
        self.assertIn('journalctl -u redis-server', message)
        self.assertFalse(self.marker())

    def test_the_marker_is_written_after_the_program_and_the_running_unit_were_seen(self):
        server = Server()
        done, message = self.install(server)
        self.assertTrue(done)
        self.assertEqual(message, 'Redis successfully installed.')
        self.assertTrue(self.marker())
        self.assertEqual(server.commands, [APT_INSTALL, 'systemctl enable redis-server',
                                           'systemctl start redis-server', 'systemctl is-active redis-server'])

    def test_the_unit_of_the_other_systems_is_redis(self):
        server = Server()
        self.install(server, debian=False)
        self.assertEqual(server.commands[1:], ['systemctl enable redis', 'systemctl start redis',
                                               'systemctl is-active redis'])

    def test_a_stopped_service_is_started_even_when_the_package_manager_is_busy(self):
        server = Server(package=(100, APT_LOCK), program=True)
        done, message = self.install(server)
        self.assertTrue(done)
        self.assertIn('installed and running', message)
        self.assertIn('busy with another installation or update', message)
        self.assertTrue(self.marker())

    def test_the_package_is_configured_only_when_it_is_there(self):
        configured = []
        self.install(Server(package=(100, APT_LOCK)), name='Elasticsearch',
                     configure=lambda: configured.append(1))
        self.assertEqual(configured, [])
        server = Server()
        self.install(server, name='Elasticsearch', configure=lambda: configured.append(list(server.commands)))
        self.assertEqual(configured, [[APT_INSTALL]], 'configured after the package, before the service starts')
        self.assertTrue(self.marker('Elasticsearch'))

    def test_no_result_message_ends_the_log_by_accident(self):
        for server in (Server(), Server(package=(100, APT_LOCK)), Server(unit='failed'),
                       Server(package=(1, 'Error: Unable to find a match: redis\n'))):
            message = self.install(server)[1]
            self.assertNotIn('[200]', message)
            self.assertNotIn('[404]', message)


class Remove(Markers):

    def test_a_removal_the_package_manager_refused_is_a_failure_and_the_marker_stays_true(self):
        state.remember('Redis')
        server = Server(package=(100, APT_LOCK), program=True)
        done, message = self.remove(server)
        self.assertFalse(done)
        self.assertIn('Redis was not removed.', message)
        self.assertIn('try again', message)
        self.assertTrue(self.marker(), 'the service is still installed and running')

    def test_a_failed_removal_that_left_the_service_stopped_takes_the_marker_away(self):
        state.remember('Redis')
        server = Server(package=(100, 'dpkg: error processing package redis-server (--remove)\n'),
                        program=True, unit='inactive')
        done, message = self.remove(server)
        self.assertFalse(done)
        self.assertFalse(self.marker())

    def test_a_removal_takes_the_marker_away(self):
        state.remember('Redis')
        server = Server(program=True)
        done, message = self.remove(server)
        self.assertTrue(done)
        self.assertEqual(message, 'Redis successfully removed.')
        self.assertFalse(self.marker())


class Reasons(unittest.TestCase):

    def test_every_form_of_a_held_lock_is_recognised(self):
        for line in (
                'E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 9 (unattended-upgr)',
                'E: Could not get lock /var/lib/dpkg/lock - open (11: Resource temporarily unavailable)',
                'E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), is another process using it?',
                'E: Unable to lock the administration directory (/var/lib/dpkg/), is another process using it?',
                'E: Unable to lock directory /var/lib/apt/lists/',
                'dpkg: error: dpkg frontend lock was locked by another process with pid 812',
                'dpkg: error: dpkg status database is locked by another process'):
            self.assertEqual(state.failure_reason('Reading package lists...\n' + line + '\n'),
                             state.LOCK_REASON, line)

    def test_other_errors_are_quoted(self):
        self.assertEqual(
            state.failure_reason("E: dpkg was interrupted, you must manually run 'dpkg --configure -a' "
                                 "to correct the problem. \n"),
            "The package manager reported: E: dpkg was interrupted, you must manually run "
            "'dpkg --configure -a' to correct the problem.")
        self.assertEqual(state.failure_reason('Last metadata expiration check\nError: Unable to find a match: redis\n'),
                         'The package manager reported: Error: Unable to find a match: redis')

    def test_without_an_error_line_the_last_line_is_quoted(self):
        self.assertEqual(state.failure_reason('one\ntwo\n\n'), 'The package manager reported: two')
        self.assertEqual(state.failure_reason(''), 'The package manager gave no reason.')
        self.assertEqual(state.failure_reason(None), 'The package manager gave no reason.')


class RunLogged(unittest.TestCase):
    """The runner the installer uses reports the status a command really ended with."""

    def run_logged(self, command):
        with tempfile.TemporaryFile() as log:
            result = state.run_logged(command, log)
            log.seek(0)
            return result, log.read()

    def test_the_exit_status_and_the_output_are_returned_and_the_log_gets_the_output(self):
        result, logged = self.run_logged('echo out; echo err >&2; exit 100')
        self.assertEqual(result, (100, 'out\nerr\n'))
        self.assertEqual(logged, b'out\nerr\n')
        self.assertEqual(self.run_logged('true')[0], (0, ''))

    def test_output_that_is_not_text_does_not_stop_the_run(self):
        result, logged = self.run_logged("printf 'caf\\351\\n'; exit 3")
        self.assertEqual(result[0], 3)
        self.assertEqual(logged, b'caf\xe9\n')

    def test_a_command_cannot_wait_for_an_answer(self):
        self.assertEqual(self.run_logged('read answer; echo "got:$answer"')[0], (0, 'got:\n'))


class Sources(unittest.TestCase):
    """The installer and the page use the rule above and nothing else."""

    def read(self, path):
        return (ROOT / path).read_text()

    def test_the_installer_no_longer_writes_or_removes_a_marker_by_itself(self):
        source = self.read('manageServices/serviceManager.py')
        self.assertNotIn('touch /home/cyberpanel/', source)
        self.assertNotIn('rm -f /home/cyberpanel/', source)
        self.assertNotIn('successfully installed.[200]', source)
        for function in ('InstallRedis', 'InstallElasticSearch'):
            body = source.split('def %s():' % function)[1].split('@staticmethod')[0]
            self.assertIn('applicationState.install(', body, function)
        for function in ('RemoveRedis', 'RemoveElasticSearch'):
            body = source.split('def %s():' % function)[1].split('@staticmethod')[0]
            self.assertIn('applicationState.remove(', body, function)

    def test_the_page_does_not_read_a_marker(self):
        view = self.read('manageServices/views.py').split('def manageApplications(request):')[1]
        view = view.split('\ndef ')[0]
        self.assertNotIn('/home/cyberpanel/', view)
        self.assertNotIn('os.path.exists', view)
        self.assertIn('applicationState.state(', view)
        self.assertIn("'systemctl is-active %s' % unit", view)

    def test_the_page_shows_the_three_states_and_offers_removal_for_a_stopped_service(self):
        page = self.read('manageServices/templates/manageServices/applications.html')
        self.assertIn("{% elif service.installed == 'Stopped' %}", page)
        self.assertIn('{% trans "Installed, service not running" %}', page)
        self.assertIn('{% trans "Start service" %}', page)
        self.assertIn("{% if service.installed == 'Installed' or service.installed == 'Stopped' %}", page)

    def test_both_copies_of_the_script_end_a_failed_run_and_are_loaded_fresh(self):
        script = self.read('manageServices/static/manageServices/manageServices.js')
        self.assertEqual(script, self.read('static/manageServices/manageServices.js'))
        ended = script.split("app.controller('manageApplications'")[1].split('// The work has ended')[1]
        ended = ended.split('function cantLoadInitialDatas')[0]
        self.assertIn('$scope.cyberpanelLoading = true;', ended)
        self.assertIn("title: 'Operation Failed!'", ended)
        loads = re.compile(r"manageServices/manageServices\.js' %}\?v={{ CP_VERSION }}-app-state\"")
        self.assertTrue(loads.search(self.read('manageServices/templates/manageServices/applications.html')))
        self.assertTrue(loads.search(self.read('baseTemplate/templates/baseTemplate/index.html')))


if __name__ == '__main__':
    unittest.main()
