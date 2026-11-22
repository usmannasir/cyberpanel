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
from unittest import mock

from plogical import websiteSuspension
from plogical.websiteSuspension import START, VhostUpdate, config_check, config_errors_added, server_update

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

OTHER = '[ERROR] [config:server:vhosts:vhost:other.test] missing docRoot'
FATAL = '[FATAL] [config:server:vhosts:vhost:child.test] cannot continue'

# Stands in for `openlitespeed -t`. It reads `plan.json` beside `bin`, stamps
# each line with the present time and its own process ID as the server does,
# and reports the `suspended` part of the plan while any website is suspended
# and the `restored` part while none is. A line of a website file that begins
# with one of these words is an error with its real line number, worded in
# the forms a message can name its website and its line by:
#   nosuch     parser message that ends with the file and line
#   badparen   the file and line in brackets, followed by a full stop
#   badrule    the virtual host in the context, and "line N"
#   badglobal  names neither the website nor its file
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
        elif line.startswith('badparen'):
            lines.append('[ERROR] [PlainConf] [virtualHostConfig:] unknown keyword (%%s:%%d).' %% (path, number))
        elif line.startswith('badrule'):
            lines.append('[ERROR] [config:server:vhosts:vhost:%%s:rewrite] invalid rewrite rule at line %%d'
                         %% (path.parent.name, number))
        elif line.startswith('badglobal'):
            lines.append('[ERROR] [rewrite] invalid rule badglobal')
lines += plan.get('suspended' if suspended else 'restored', [])
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
        for domain in ('parent.test', 'child.test', 'sibling.test', 'other.test'):
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

    def family(self, suspended):
        # A parent is suspended and restored together with its children.
        with server_update(self.root) as update:
            update.apply([(domain, suspended) for domain in ('parent.test', 'child.test', 'sibling.test')])

    def status(self):
        return config_check([str(self.root / 'bin' / self.binary), '-t'])[0]

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


def with_rule(word):
    """A website file with a faulty line among its own rewrite rules."""
    return VHOST.replace('RewriteRule ^ /index.php [L]\n', 'RewriteRule ^ /index.php [L]\n' + word + '\n')


class RestoredWithItsOwnErrorTests(ServerFixture):
    """Suspension comments a website's rewrite rules out, and an error in them with it."""

    def test_a_website_is_restored_with_the_error_its_own_rules_had(self):
        for word in ('badrule', 'badparen', 'nosuch'):
            with self.subTest(word=word):
                self.paths['parent.test'].write_text(with_rule(word))
                self.assertEqual(self.status(), 2)
                self.change()
                self.assert_suspended()
                self.assertEqual(self.status(), 0)  # the error is not reported while suspended
                self.change(suspended=False)
                self.assertEqual(self.paths['parent.test'].read_text(), with_rule(word))
                self.assertEqual(self.status(), 2)

    def test_a_parent_is_restored_with_a_child_whose_rules_have_an_error(self):
        self.paths['child.test'].write_text(with_rule('badrule'))
        self.plan(lines=STOCK)
        self.family(True)
        for domain in ('parent.test', 'child.test', 'sibling.test'):
            self.assert_suspended(domain)
        (self.root / 'calls').write_text('')
        self.family(False)
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.assertEqual(self.paths['sibling.test'].read_text(), VHOST)
        self.assertEqual(self.paths['child.test'].read_text(), with_rule('badrule'))
        self.assertEqual(self.calls(), ['test', 'test', 'restart'])

    def test_a_restore_is_still_refused_for_a_new_error_anywhere_else(self):
        self.paths['child.test'].write_text(with_rule('badrule'))
        self.family(True)
        for foreign in (LISTENER, OTHER, FATAL):
            with self.subTest(foreign=foreign):
                self.plan(restored=[foreign])
                with self.assertRaises(RuntimeError) as refusal:
                    self.family(False)
                message = str(refusal.exception)
                self.assertIn(foreign.split('] ', 1)[1], message)
                self.assertNotIn('invalid rewrite rule', message)
                self.assertNotIn('automatic recovery failed', message)
                for domain in ('parent.test', 'child.test', 'sibling.test'):
                    self.assert_suspended(domain)

    def test_an_error_that_names_no_website_cannot_be_told_apart_and_refuses_the_restore(self):
        self.paths['parent.test'].write_text(with_rule('badglobal'))
        self.change()
        message = self.refused(suspended=False)
        self.assertIn('invalid rule badglobal', message)
        self.assert_suspended()

    def test_an_error_in_the_website_being_suspended_is_not_excused(self):
        self.plan(suspended=[REWRITE])
        self.assertIn('suspension rule was rejected', self.refused())
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)


class CallTests(ServerFixture):
    """What the update passes to its check, as the callers and their tests rely on it."""

    def test_the_check_is_given_the_earlier_result_and_the_websites_that_changed(self):
        check = mock.Mock()
        with VhostUpdate(self.root, check, mock.Mock()) as update:
            update.apply([('parent.test', True), ('child.test', True)])
        self.assertEqual(check.call_args_list, [
            mock.call(), mock.call(check.return_value, {'parent.test': True, 'child.test': True})])
        check.reset_mock()
        with self.assertRaisesRegex(RuntimeError, 'database'):
            with VhostUpdate(self.root, check, mock.Mock()) as update:
                update.apply([('parent.test', False), ('child.test', True), ('sibling.test', True)])
                raise RuntimeError('database commit failed')
        # The unchanged child is not named, and the files put back are compared as they are.
        self.assertEqual(check.call_args_list, [
            mock.call(), mock.call(check.return_value, {'parent.test': False, 'sibling.test': True}),
            mock.call(check.return_value)])

    def test_the_installed_server_is_asked_through_config_check(self):
        command = [str(self.root / 'bin' / self.binary), '-t']
        with mock.patch.object(websiteSuspension, 'config_check') as check, \
                mock.patch.object(websiteSuspension, '_checked') as restart:
            self.change()
        self.assertEqual(check.call_args_list, [
            mock.call(command), mock.call(command, check.return_value, {'parent.test': True})])
        restart.assert_called_once_with([str(self.root / 'bin' / 'lswsctrl'), 'restart'])


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
    FILE = '/usr/local/lsws/conf/vhosts/a.test/vhost.conf'
    OLD = ('2026-11-22 09:10:11.000001 [ERROR] [4100] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] '
           'in file ' + FILE + ':9')
    MOVED = ('2026-11-22 09:10:12.500000 [ERROR] [4177] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] '
             'in file ' + FILE + ':25')
    WARN = '2026-11-22 09:10:11.000001 [WARN] [4100] [cyberpanel_ols] License validation failed - module features disabled'
    SUSPENDED = {'a.test': True}
    RESTORED = {'a.test': False}

    def test_time_process_and_line_number_do_not_make_an_error_new(self):
        self.assertEqual(config_errors_added((2, self.OLD + '\n' + self.WARN), (2, self.WARN + '\n' + self.MOVED),
                                             self.SUSPENDED), [])

    def test_a_line_number_is_dropped_in_every_form_but_only_for_the_edited_website(self):
        forms = (
            '[ERROR] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] in file ' + self.FILE + ':%d',
            '[ERROR] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] in file ' + self.FILE + ':%d.',
            '[ERROR] [PlainConf] [virtualHostConfig:] unknown keyword (' + self.FILE + ':%d)',
            '[ERROR] [PlainConf] [virtualHostConfig:] unknown keyword at ' + self.FILE + ':%d, column 3',
            '[ERROR] unknown keyword in "' + self.FILE + '":%d',
            '[ERROR] unknown keyword in ' + self.FILE + '(%d): nosuch',
            '[ERROR] [config:server:vhosts:vhost:a.test:rewrite] invalid rewrite rule at line %d',
            '[ERROR] [config:server:vhosts:vhost:a.test:rewrite] invalid rewrite rule, Line: %d.',
            '[ERROR] ' + self.FILE + ' line %d: invalid rewrite rule',
        )
        for form in forms:
            with self.subTest(form=form):
                before, after = (2, form % 9), (2, form % 25)
                self.assertEqual(config_errors_added(before, after, self.SUSPENDED), [])
                self.assertEqual(config_errors_added(before, after, self.RESTORED), [])
                # Lines do not move in a file that was not edited: there it is another error.
                self.assertEqual(config_errors_added(before, after), [form % 25])
                self.assertEqual(config_errors_added(before, after, {'b.test': True}), [form % 25])
                self.assertEqual(config_errors_added(before, after, {'a.tes': True, 'a.test2': True}), [form % 25])

    def test_a_port_or_another_number_is_not_a_line_number(self):
        pairs = (
            ('[ERROR] [config:server:vhosts:vhost:a.test:extprocessor] cannot reach http://127.0.0.1:8080/app',
             '[ERROR] [config:server:vhosts:vhost:a.test:extprocessor] cannot reach http://127.0.0.1:8081/app'),
            ('[ERROR] [config:server:vhosts:vhost:a.test] address *:443 is in use',
             '[ERROR] [config:server:vhosts:vhost:a.test] address *:8443 is in use'),
            ('[ERROR] [config:server:vhosts:vhost:a.test] uds://tmp/lshttpd/a.test.sock:1 refused',
             '[ERROR] [config:server:vhosts:vhost:a.test] uds://tmp/lshttpd/a.test.sock:2 refused'),
            ('[ERROR] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] in file ' + self.FILE + ':9',
             '[ERROR] [PlainConf] [virtualHostConfig:] Not support [nosuch 2] in file ' + self.FILE + ':9'),
            ('[ERROR] [config:server:listener:Default] cannot bind http://127.0.0.1:8080/ for ' + self.FILE + ':9',
             '[ERROR] [config:server:listener:Default] cannot bind http://127.0.0.1:8081/ for ' + self.FILE + ':9'),
        )
        for before, after in pairs:
            with self.subTest(after=after):
                self.assertEqual(config_errors_added((2, before), (2, after), self.SUSPENDED), [after])

    def test_only_what_was_not_there_is_returned(self):
        other_file = self.MOVED.replace('a.test', 'b.test')
        fatal = '2026-11-22 09:10:12.500000 [FATAL] [4177] cannot continue'
        disabled = '[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed core ABI (expected CyberPanel OLS 2.5.2)'
        after = '\n'.join((self.MOVED, other_file, self.WARN, fatal, disabled))
        self.assertEqual(config_errors_added((2, self.OLD), (2, after), self.SUSPENDED), [other_file, fatal, disabled])
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

    def test_an_error_about_a_restored_website_is_its_own(self):
        own = (
            self.MOVED,
            '[ERROR] [config:server:vhosts:vhost:a.test:rewrite] invalid rewrite rule at line 25',
            '[ERROR] [config:server:vhosts:vhost:a.test] missing docRoot',
            '[ERROR] [PlainConf] [virtualHostConfig:] unknown keyword (' + self.FILE + ':25).',
            '[ERROR] invalid rewrite rule in ' + self.FILE,
        )
        for line in own:
            with self.subTest(line=line):
                self.assertEqual(config_errors_added((1, self.WARN), (2, line), self.RESTORED), [])
                # Not while it is being suspended, and not for another website's restore.
                self.assertEqual(config_errors_added((1, self.WARN), (2, line), self.SUSPENDED), [line])
                self.assertEqual(config_errors_added((1, self.WARN), (2, line), {'b.test': False}), [line])
                self.assertEqual(config_errors_added((1, self.WARN), (2, line), {'a.tes': False}), [line])
                self.assertEqual(config_errors_added((1, self.WARN), (2, line)), [line])
        self.assertEqual(config_errors_added((0, ''), (2, '\n'.join(own)), self.RESTORED), [])

    def test_an_error_about_anything_else_refuses_a_restore(self):
        foreign = (
            '[ERROR] [config:server:vhosts:vhost:b.test] missing docRoot',
            '[ERROR] [config:server:vhosts:vhost:a.test2] missing docRoot',
            '[ERROR] [config:server:listener:SSL] failed to load the certificate',
            '[ERROR] [rewrite] invalid rule',
            '[ERROR] [config:server:vhosts:vhost:b.test] cannot include ' + self.FILE,
            '[ERROR] ' + self.FILE + ' and /usr/local/lsws/conf/vhosts/b.test/vhost.conf share a document root',
            '[FATAL] [config:server:vhosts:vhost:a.test] cannot continue',
            '[FATAL] cannot read ' + self.FILE,
            '[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed core ABI in ' + self.FILE,
        )
        for line in foreign:
            with self.subTest(line=line):
                self.assertEqual(config_errors_added((1, self.WARN), (2, line + '\n' + self.MOVED), self.RESTORED),
                                 [line])

    def test_a_restored_websites_error_accounts_for_status_two_and_for_no_other(self):
        self.assertEqual(config_errors_added((0, ''), (2, self.MOVED), self.RESTORED), [])
        for after in ((3, self.MOVED), (139, self.MOVED), (2, ''), (2, self.WARN)):
            with self.subTest(after=after):
                added = config_errors_added((1, self.WARN), after, self.RESTORED)
                self.assertEqual(len(added), 1)
                self.assertIn('ended with status %d' % after[0], added[0])


if __name__ == '__main__':
    unittest.main()
