"""Suspension must work on a server whose configuration test is not clean.

OpenLiteSpeed ends `-t` with 1 after warnings and with 2 after any error. A
fresh installation warns about its stock Example virtual host, so a test that
had to end with 0 refused every suspension there, and then refused to put the
original files back. These tests run the real update against a stand-in for
the server's two commands in a temporary directory.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from plogical.websiteSuspension import START, config_check, config_errors_added, server_update

VHOST = '''docRoot /home/example/public_html
rewrite {
  enable 1
  rules <<<END_rules
RewriteRule ^ /index.php [L]
END_rules
}
'''
# The kinds of warning a fresh installation prints; olsParserRecovery.example_warnings
# derives the exact Example lines of a given server.
STOCK = [
    '[WARN] [config:server:vhosts:vhost:Example] Uid of /usr/local/lsws/Example/html/ is 0, '
    'smaller than minimum requirement 11, use server uid!',
    '[WARN] [config:server:vhosts:vhost:Example] Gid of /usr/local/lsws/Example/html/ is 65534, '
    'smaller than minimum requirement 10, use server gid!',
    '[WARN] [cyberpanel_ols] License validation failed - module features disabled',
]
LISTENER = '[ERROR] [config:server:listener:SSL] failed to load the certificate'
REWRITE = '[ERROR] [config:server:vhosts:vhost:parent.test] rewrite: suspension rule was rejected'

# Stands in for `openlitespeed -t`. It reads `plan.json` beside `bin`, stamps
# each line with the present time and its own process ID as the server does,
# reports a `nosuch` directive in a website file with its real line number, and
# reports the `suspended` part of the plan while any website is suspended.
SERVER = '''#!%(python)s
import datetime, json, os, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
with (root / 'calls').open('a') as calls:
    calls.write('test\\n')
plan = json.loads((root / 'plan.json').read_text())
lines = list(plan.get('lines', []))
suspended = False
for path in sorted(root.glob('conf/vhosts/*/vhost.conf')):
    text = path.read_text()
    suspended = suspended or %(start)r in text
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith('nosuch'):
            lines.append('[ERROR] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] in file %%s:%%d'
                         %% (path, number))
if suspended:
    lines += plan.get('suspended', [])
status = 2 if any('[ERROR]' in line or '[FATAL]' in line for line in lines) else 1 if lines else 0
status = plan.get('suspended_status' if suspended else 'status', status)
for line in lines:
    level, rest = line.split(' ', 1)
    text = '%%s %%s [%%d] %%s\\n' %% (datetime.datetime.now().strftime('%%Y-%%m-%%d %%H:%%M:%%S.%%f'), level,
                                  os.getpid(), rest)
    sys.stdout.buffer.write(text.encode() + plan.get('noise', '').encode('latin-1'))
sys.exit(status)
'''
# Stands in for `lswsctrl restart`; it fails once while `restart-fails` exists.
CONTROL = '''#!%(python)s
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
with (root / 'calls').open('a') as calls:
    calls.write('restart\\n')
if (root / 'restart-fails').exists():
    (root / 'restart-fails').unlink()
    print('restart refused')
    sys.exit(1)
'''


class ServerFixture(unittest.TestCase):
    binary = 'openlitespeed'

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.paths = {}
        for domain in ('parent.test', 'other.test'):
            path = self.root / 'conf' / 'vhosts' / domain / 'vhost.conf'
            path.parent.mkdir(parents=True)
            path.write_text(VHOST)
            self.paths[domain] = path
        (self.root / 'bin').mkdir()
        for name, source in ((self.binary, SERVER), ('lswsctrl', CONTROL)):
            script = self.root / 'bin' / name
            script.write_text(source % {'python': sys.executable, 'start': START})
            script.chmod(0o700)
        self.plan()

    def plan(self, **plan):
        (self.root / 'plan.json').write_text(json.dumps(plan))

    def calls(self):
        path = self.root / 'calls'
        return path.read_text().split() if path.exists() else []

    def change(self, suspended=True, domain='parent.test', activate=True):
        with server_update(self.root, activate=activate) as update:
            update.apply([(domain, suspended)])

    def assert_suspended(self, domain='parent.test'):
        self.assertIn(START, self.paths[domain].read_text())

    def refused(self, **arguments):
        with self.assertRaises(RuntimeError) as refusal:
            self.change(**arguments)
        return str(refusal.exception)


class NotCleanBeforeTheChangeTests(ServerFixture):
    def test_clean_before_and_after(self):
        self.change()
        self.assert_suspended()
        self.assertEqual(self.calls(), ['test', 'test', 'restart'])
        self.change(suspended=False)
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.assertEqual(self.calls(), ['test', 'test', 'restart'] * 2)

    def test_a_fresh_installation_that_only_warns_suspends_and_restores(self):
        self.plan(lines=STOCK)
        self.assertEqual(config_check([str(self.root / 'bin' / self.binary), '-t'])[0], 1)
        self.change()
        self.assert_suspended()
        self.change(suspended=False)
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.assertEqual(self.calls().count('restart'), 2)

    def test_an_error_in_another_website_does_not_stop_a_suspension(self):
        self.paths['other.test'].write_text(VHOST + 'nosuch 1\n')
        self.assertEqual(config_check([str(self.root / 'bin' / self.binary), '-t'])[0], 2)
        self.change()
        self.assert_suspended()
        self.change(suspended=False)
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)

    def test_the_websites_own_error_moves_to_another_line_and_is_still_the_same_error(self):
        broken = VHOST + 'nosuch 1\n'
        self.paths['parent.test'].write_text(broken)
        self.change()
        self.assert_suspended()
        self.change(suspended=False)
        self.assertEqual(self.paths['parent.test'].read_text(), broken)

    def test_a_server_wide_error_from_before_does_not_stop_a_suspension(self):
        self.plan(lines=STOCK + [LISTENER])
        self.change()
        self.assert_suspended()

    def test_output_that_is_not_text_is_still_judged(self):
        self.plan(lines=STOCK, noise='\xff\xfe')
        self.change()
        self.assert_suspended()

    def test_creation_tests_the_configuration_and_leaves_the_restart_to_its_caller(self):
        self.plan(lines=STOCK)
        self.change(activate=False)
        self.assert_suspended()
        self.assertEqual(self.calls(), ['test', 'test'])


class MadeWorseByTheChangeTests(ServerFixture):
    def assert_put_back(self, message, shown, calls):
        self.assertIn('Web server configuration activation failed', message)
        self.assertIn(shown, message)
        self.assertNotIn('automatic recovery failed', message)
        for path in self.paths.values():
            self.assertNotIn(START, path.read_text())
        self.assertEqual(self.calls(), calls)

    def test_clean_before_and_an_error_after_is_put_back_and_reported(self):
        self.plan(suspended=[REWRITE])
        message = self.refused()
        self.assert_put_back(message, 'suspension rule was rejected', ['test', 'test', 'test', 'restart'])
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)

    def test_an_error_before_and_one_more_after_is_put_back_and_only_the_new_one_is_reported(self):
        self.paths['other.test'].write_text(VHOST + 'nosuch 1\n')
        self.plan(lines=STOCK + [LISTENER], suspended=[REWRITE])
        message = self.refused()
        self.assert_put_back(message, 'suspension rule was rejected', ['test', 'test', 'test', 'restart'])
        self.assertNotIn('nosuch', message)
        self.assertNotIn('failed to load the certificate', message)
        self.assertNotIn('Example', message)

    def test_a_second_copy_of_an_error_from_before_is_a_new_error(self):
        self.plan(lines=[LISTENER], suspended=[LISTENER])
        self.assert_put_back(self.refused(), 'failed to load the certificate', ['test', 'test', 'test', 'restart'])

    def test_an_error_status_without_an_error_line_is_put_back(self):
        for before, after in ((None, 2), (1, 2), (2, 3), (0, 139)):
            with self.subTest(before=before, after=after):
                (self.root / 'calls').write_text('')
                self.plan(lines=STOCK, suspended_status=after, **({} if before is None else {'status': before}))
                self.assert_put_back(self.refused(), 'ended with status', ['test', 'test', 'test', 'restart'])

    def test_a_failed_restart_is_put_back_on_a_server_that_was_not_clean(self):
        self.paths['other.test'].write_text(VHOST + 'nosuch 1\n')
        self.plan(lines=STOCK)
        (self.root / 'restart-fails').write_text('')
        message = self.refused()
        self.assert_put_back(message, 'restart refused', ['test', 'test', 'restart', 'test', 'restart'])

    def test_a_failure_after_activation_is_put_back_on_a_server_that_was_not_clean(self):
        self.paths['other.test'].write_text(VHOST + 'nosuch 1\n')
        self.plan(lines=STOCK + [LISTENER])
        with self.assertRaisesRegex(RuntimeError, '^database commit failed$'):
            with server_update(self.root) as update:
                update.apply([('parent.test', True)])
                self.assert_suspended()
                raise RuntimeError('database commit failed')
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.assertEqual(self.calls(), ['test', 'test', 'restart', 'test', 'restart'])

    def test_originals_that_now_have_another_error_are_restored_but_not_activated(self):
        self.plan(lines=STOCK)
        with self.assertRaises(RuntimeError) as failure:
            with server_update(self.root) as update:
                update.apply([('parent.test', True)])
                # Somebody else's change, made while this one was in progress.
                self.plan(lines=STOCK + [LISTENER])
                raise RuntimeError('database commit failed')
        message = str(failure.exception)
        self.assertIn('automatic recovery failed', message)
        self.assertIn('failed to load the certificate', message)
        self.assertIn('original error: database commit failed', message)
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.assertEqual(self.calls(), ['test', 'test', 'restart', 'test'])


class NoResultBeforeTheChangeTests(ServerFixture):
    def assert_untouched(self, message, shown):
        self.assertIn(shown, message)
        self.assertNotIn('automatic recovery failed', message)
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.assertNotIn('restart', self.calls())

    def test_a_test_that_gives_no_result_changes_nothing(self):
        for status in (3, 78, 127, 139):
            with self.subTest(status=status):
                self.plan(lines=STOCK, status=status)
                self.assert_untouched(self.refused(), 'gave no result (exit status %d)' % status)

    def test_a_test_that_cannot_be_run_changes_nothing(self):
        (self.root / 'bin' / self.binary).chmod(0o600)
        self.assert_untouched(self.refused(), 'could not be run')


class EnterpriseBinaryTests(NotCleanBeforeTheChangeTests):
    """Without `openlitespeed` the same test is asked of `lshttpd`."""
    binary = 'lshttpd'


class AddedErrorsTests(unittest.TestCase):
    OLD = ('2026-11-22 09:10:11.000001 [ERROR] [4100] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] '
           'in file /usr/local/lsws/conf/vhosts/a.test/vhost.conf:9')
    MOVED = ('2026-11-22 09:10:12.500000 [ERROR] [4177] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] '
             'in file /usr/local/lsws/conf/vhosts/a.test/vhost.conf:25')
    WARN = '2026-11-22 09:10:11.000001 [WARN] [4100] [cyberpanel_ols] License validation failed - module features disabled'

    def test_time_process_and_line_number_do_not_make_an_error_new(self):
        self.assertEqual(config_errors_added((2, self.OLD + '\n' + self.WARN), (2, self.WARN + '\n' + self.MOVED)), [])

    def test_only_what_was_not_there_is_returned(self):
        other_file = self.MOVED.replace('a.test', 'b.test')
        fatal = '2026-11-22 09:10:12.500000 [FATAL] [4177] cannot continue'
        disabled = '[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed core ABI (expected CyberPanel OLS 2.5.2)'
        after = '\n'.join((self.MOVED, other_file, self.WARN, fatal, disabled))
        self.assertEqual(config_errors_added((2, self.OLD), (2, after)), [other_file, fatal, disabled])
        self.assertEqual(config_errors_added((2, after), (2, after)), [])

    def test_new_warnings_and_a_better_status_are_not_errors(self):
        self.assertEqual(config_errors_added((0, ''), (1, self.WARN)), [])
        self.assertEqual(config_errors_added((2, self.OLD), (1, self.WARN)), [])
        self.assertEqual(config_errors_added((2, self.OLD), (0, '')), [])

    def test_a_worse_status_alone_is_reported_with_the_output(self):
        for before, after in ((0, 2), (1, 2), (2, 3), (1, -11), (2, 139)):
            with self.subTest(before=before, after=after):
                added = config_errors_added((before, self.WARN), (after, self.WARN))
                self.assertEqual(len(added), 1)
                self.assertIn('ended with status %d' % after, added[0])
                self.assertIn('License validation failed', added[0])


if __name__ == '__main__':
    unittest.main()
