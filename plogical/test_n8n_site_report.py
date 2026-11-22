"""The upgrade names the n8n sites that earlier releases deployed, changes nothing on them and cannot fail on it."""
import ast
import subprocess
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
COMMAND = ['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/DockerSites.py', 'CheckN8NSites']
OPEN = 'n8n site flows.example (flows): HAS NO OWNER ACCOUNT: open the site and finish its set-up, or delete the site'
PORT = 'n8n site flows.example (flows): port 11000 is published on every address of the server'


def upgrader_source():
    return (ROOT / 'plogical' / 'upgrade.py').read_text()


def method_source():
    source = upgrader_source()
    start = source.index('    def reportN8NSites():')
    return source[start:source.index('    @staticmethod', start)]


def report(output='', error=None, timeout=False, log_fails=False):
    """Run the upgrader's own method with the command and the log replaced."""
    printed = []

    def log(message, do_exit=0):
        if log_fails:
            raise OSError('the log cannot be written')
        printed.append((message, do_exit))

    process = mock.Mock()
    if timeout:
        process.communicate.side_effect = [subprocess.TimeoutExpired(COMMAND, 120), ('', None)]
    else:
        process.communicate.return_value = (output, None)
    runner = SimpleNamespace(Popen=mock.Mock(return_value=process, side_effect=error), PIPE=subprocess.PIPE,
                             DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired)
    namespace = {'subprocess': runner, 'Upgrade': SimpleNamespace(stdOut=log)}
    exec(compile(ast.parse(textwrap.dedent(method_source())), 'upgrade.py', 'exec'), namespace)
    result = namespace['reportN8NSites']()
    return SimpleNamespace(result=result, printed=printed, runner=runner, process=process)


class ReportTests(unittest.TestCase):
    def test_every_line_of_the_check_becomes_a_notice_and_one_line_says_how_to_see_them_again(self):
        run = report(OPEN + '\n' + PORT + '\n')
        self.assertEqual([('NOTICE: ' + OPEN, 0), ('NOTICE: ' + PORT, 0)], run.printed[:2])
        self.assertEqual(3, len(run.printed))
        closing, do_exit = run.printed[2]
        self.assertTrue(closing.startswith('NOTICE: The upgrade changed nothing on these n8n sites.'))
        self.assertTrue(closing.endswith('run: ' + ' '.join(COMMAND)))
        self.assertEqual(0, do_exit)

    def test_a_server_without_such_a_site_or_without_docker_gets_no_line(self):
        for output in ('', '\n', 'No n8n site needs attention.\n', None):
            with self.subTest(output=output):
                self.assertEqual([], report(output).printed)

    def test_only_the_lines_of_the_report_are_shown(self):
        noise = ('/usr/local/CyberCP/x.py:7: DeprecationWarning: something\n  pagination.append(1)\n'
                 "No module named 'docker'\nTraceback (most recent call last):\n")
        self.assertEqual([], report(noise).printed)
        run = report(noise + '  ' + OPEN + '  \n' + noise)
        self.assertEqual('NOTICE: ' + OPEN, run.printed[0][0])
        self.assertEqual(2, len(run.printed))

    def test_the_check_of_the_new_source_runs_as_a_command_of_its_own_with_a_time_limit(self):
        run = report(OPEN)
        run.runner.Popen.assert_called_once_with(
            COMMAND, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            universal_newlines=True, cwd='/usr/local/CyberCP')
        run.process.communicate.assert_called_once_with(timeout=120)

    def test_a_check_that_does_not_end_is_stopped_and_named_in_one_warning(self):
        run = report(timeout=True)
        run.process.kill.assert_called_once_with()
        self.assertEqual(2, run.process.communicate.call_count)
        self.assertEqual(1, len(run.printed))
        self.assertTrue(run.printed[0][0].startswith('WARNING: The n8n sites were not checked: the check did not '
                                                     'end within two minutes.'))
        self.assertEqual(0, run.printed[0][1])

    def test_no_error_stops_the_upgrade(self):
        for error in (OSError('No such file or directory'), ValueError('bad'), RuntimeError('x'),
                      subprocess.SubprocessError('y')):
            with self.subTest(error=error):
                run = report(error=error)
                self.assertIsNone(run.result)
                self.assertEqual([('WARNING: The n8n sites were not checked: ' + str(error), 0)], run.printed)

    def test_not_even_a_log_that_cannot_be_written_stops_the_upgrade(self):
        self.assertIsNone(report(OPEN, log_fails=True).result)
        self.assertIsNone(report(error=OSError('no interpreter'), log_fails=True).result)
        self.assertIsNone(report(timeout=True, log_fails=True).result)

    def test_the_method_uses_nothing_python_3_6_lacks_and_never_ends_the_upgrade(self):
        method = method_source()
        for word in ('capture_output', 'text=', 'do_exit=1', 'sys.exit', 'os._exit', 'raise '):
            self.assertNotIn(word, method)
        self.assertNotIn(', 1)', method)


class CallTests(unittest.TestCase):
    CALL = '\n        Upgrade.reportN8NSites()\n'

    def test_the_upgrade_runs_it_once_right_after_the_database_grants(self):
        upgrader = upgrader_source()
        self.assertEqual(1, upgrader.count(self.CALL))
        self.assertEqual(1, upgrader.count('\n        Upgrade.repairDatabaseGrants()' + self.CALL))
        # The new source is in place and the database answers by then.
        self.assertLess(upgrader.index('if Upgrade.waitForDatabaseReady() != 1:'), upgrader.index(self.CALL))
        self.assertLess(upgrader.index('Upgrade.downloadAndUpgrade('), upgrader.index(self.CALL))

    def test_an_upgrade_started_from_the_cloud_platform_runs_it_too(self):
        cloud = (ROOT / 'plogical' / 'CyberPanelUpgrade.py').read_text()
        self.assertEqual(1, cloud.count(self.CALL))
        self.assertEqual(1, cloud.count('\n        Upgrade.repairDatabaseGrants()' + self.CALL))
        self.assertLess(cloud.index('Upgrade.downloadAndUpgrade('), cloud.index(self.CALL))

    def test_the_command_the_upgrade_runs_is_one_the_new_source_has(self):
        source = (ROOT / 'plogical' / 'DockerSites.py').read_text()
        self.assertIn("elif args.function == 'CheckN8NSites':", source)
        self.assertIn("'n8n site %s (%s): %s'", source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
