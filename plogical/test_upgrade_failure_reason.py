"""The error an upgrade ends with says why its OpenLiteSpeed bundle step gave up.

The upgrade page's error box, an automatic update's summary and the last lines
in a terminal show that error, not the log above it. This module runs on
Python 3.6 too, the panel's interpreter on AlmaLinux 8 and CloudLinux 8.
"""
import ast
import contextlib
import io
import os
import shlex
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SOURCE = Path(__file__).with_name('upgrade.py').read_text()
WORDING = ('OLS_BUNDLE_FAILED', 'OLS_BUNDLE_FAILURE_LIMIT', 'shortened', 'ols_bundle_failure')


def module(*nodes):
    return ast.fix_missing_locations(ast.Module(body=list(nodes), type_ignores=[]))


def named(node):
    if isinstance(node, ast.FunctionDef):
        return node.name
    return getattr(node.targets[0], 'id', '') if isinstance(node, ast.Assign) else ''


def load():
    """Upgrade.upgrade() and the wording of its error, with stand-ins for everything else it names."""
    tree = ast.parse(SOURCE)
    wording = [node for node in tree.body if named(node) in WORDING]
    klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Upgrade')
    method = next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == 'upgrade')
    method.decorator_list = []

    @contextlib.contextmanager
    def no_lock():
        yield

    namespace = {'os': os, 'subprocess': subprocess, 'shlex': shlex, 'ols_upgrade_lock': no_lock,
                 'OLSUpgradeFailure': RuntimeError, 'requireCSFMigration': Mock(),
                 'validate_ols_configuration': Mock(return_value=None), 'ols_site_error_notice': lambda: '',
                 'Upgrade': Mock(CentOSPath='/not-centos', openEulerPath='/not-euler', SoftUpgrade=0, Said=None)}
    exec(compile(module(*(wording + [method])), 'upgrade.py', 'exec'), namespace)
    return namespace


def page_job_wording():
    """What the page job of an installed panel makes of the upgrader's last words (softUpgrade.py)."""
    tree = ast.parse(Path(__file__).with_name('softUpgrade.py').read_text())
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'readable_failure')
    namespace = {}
    exec(compile(module(function), 'softUpgrade.py', 'exec'), namespace)
    return namespace['readable_failure']


FAILED = 'Custom OLS bundle installation failed; upgrade stopped before further service changes.'
HOOK = ('Custom OLS overlay aborted: /usr/local/lsws/bin/get_trial_key.sh exists. The start command of '
        'OpenLiteSpeed runs that file on every start, and neither OpenLiteSpeed nor CyberPanel installs it, so '
        'this upgrade does not start OpenLiteSpeed while it is there. Move it away '
        '(mv /usr/local/lsws/bin/get_trial_key.sh /root/) and run the upgrade again')
# The line OpenLiteSpeed reported on 26 Nov 2026 for a website whose braces do not pair up.
FAULT = ("2026-11-26 09:48:53.707205 [ERROR] [312722] [PlainConf] [context:/] parseFile find '{' and '}' do not "
         "match in the end of file /usr/local/lsws/conf/vhosts/%s/vhost.conf, rootTag virtualHostConfig.")
BACK = ('The previous OpenLiteSpeed bundle is back in place, unchanged, and OpenLiteSpeed runs again. The upgrade '
        'stops because the configuration of a website gained an error while it ran; correct that website, then '
        'run the upgrade again: ')


class BundleFailureReasonTests(unittest.TestCase):
    def ended_with(self, said, branch='v3.0.21', before=None):
        ns = load()
        target = ns['Upgrade']
        target.Said = before

        def bundle_step(split, accepted=None):
            self.assertEqual(target.Said, [])  # Nothing an earlier step wrote is in it.
            target.Said.extend(said)
            return False
        target.installCustomOLSBinaries.side_effect = bundle_step
        with patch.object(os.path, 'exists', side_effect=lambda path: path == '/usr/local/lsws/bin/openlitespeed'), \
                self.assertRaises(RuntimeError) as refused:
            ns['upgrade'](branch)
        target.updateRepoURL.assert_not_called()  # Nothing after the bundle step ran.
        self.assertIsNone(target.Said)  # And nothing is kept once the step is over.
        return str(refused.exception)

    def test_a_refusal_is_repeated_in_the_error_the_upgrade_ends_with(self):
        said = ['Installing Custom OpenLiteSpeed Binaries', '=' * 50, 'Detected platform: ubuntu22',
                'ERROR: ' + HOOK]
        for branch in ('v3.0.21', 'SoftUpgrade,v3.0.21'):
            with self.subTest(branch=branch):
                self.assertEqual(self.ended_with(said, branch), FAILED + ' ' + HOOK)

    def test_only_what_the_bundle_step_wrote_is_repeated(self):
        before = ['ERROR: an earlier step of this run', 'Upgrading CyberPanel']
        self.assertEqual(self.ended_with(['Detected platform: rhel9', 'ERROR: ' + HOOK], before=before),
                         FAILED + ' ' + HOOK)

    def test_messages_are_kept_only_while_the_bundle_step_runs(self):
        ns = load()
        target = ns['Upgrade']
        target.installCustomOLSBinaries.side_effect = RuntimeError('the step itself raised')
        with patch.object(os.path, 'exists', side_effect=lambda path: path == '/usr/local/lsws/bin/openlitespeed'), \
                self.assertRaisesRegex(RuntimeError, 'the step itself raised'):
            ns['upgrade']('v3.0.21')
        self.assertIsNone(target.Said)

    def test_a_rollback_is_told_from_its_first_error_to_its_last_word(self):
        fault = "[ERROR] parseFile find '{' and '}' do not match in the end of file /usr/local/lsws/conf/vhosts/a.example/vhost.conf"
        said = ['Downloading binary...', 'SHA256 verified: binary',
                'ERROR: %s; restoring the previous OLS bundle' % fault, BACK + fault]
        self.assertEqual(self.ended_with(said),
                         '%s %s; restoring the previous OLS bundle. %s%s' % (FAILED, fault, BACK, fault))
        attention = 'ERROR: OLS rollback requires attention: Cannot prove OLS stopped; backup: /usr/local/lsws/backup-1'
        self.assertEqual(self.ended_with(said[:3] + [attention]),
                         '%s %s; restoring the previous OLS bundle. OLS rollback requires attention: Cannot prove '
                         'OLS stopped; backup: /usr/local/lsws/backup-1' % (FAILED, fault))

    def test_lines_of_one_story_become_one_paragraph(self):
        said = ['Downloading module...', 'ERROR: SHA256 mismatch for module', '  expected: aa', '  actual:   bb',
                'ERROR: Required module failed download, checksum or ABI verification; keeping the existing OLS bundle']
        self.assertEqual(self.ended_with(said),
                         FAILED + ' SHA256 mismatch for module. expected: aa. actual: bb. Required module failed '
                         'download, checksum or ABI verification; keeping the existing OLS bundle')
        self.assertEqual(self.ended_with(['ERROR: first line\n  second line\n']), FAILED + ' first line second line')

    def test_without_a_reason_the_error_points_to_the_log_as_before(self):
        for said in ([], ['Installing Custom OpenLiteSpeed Binaries', 'Detected platform: ubuntu'], ['ERROR: ', 'ERROR:  \n']):
            with self.subTest(said=said):
                self.assertEqual(self.ended_with(said),
                                 FAILED + ' Check the upgrade log and any rollback diagnostics.')

    def test_a_message_that_is_not_text_does_not_replace_the_refusal_with_a_traceback(self):
        self.assertEqual(self.ended_with(['ERROR: wget failed', OSError(28, 'No space left on device')]),
                         FAILED + ' wget failed. [Errno 28] No space left on device')


class PageBoxTests(unittest.TestCase):
    """The page of the installed (older) panel keeps 900 characters and cuts the middle out of more.

    The error must reach it whole: the cut used to fall on the sentence that says what to do.
    """

    def setUp(self):
        self.failure = load()['ols_bundle_failure']
        self.box = page_job_wording()

    def shown(self, said):
        text = self.failure(said)
        self.assertLessEqual(len(text), 860)
        self.assertTrue(text.startswith(FAILED + ' '))
        self.assertEqual(self.box(text + '\n'), text)  # Nothing is cut on the page.
        return text

    def test_the_refusals_of_27_november_fit_unshortened(self):
        self.assertEqual(self.shown(['ERROR: ' + HOOK]), FAILED + ' ' + HOOK)

    def test_a_rollback_for_a_website_keeps_the_reason_and_the_instruction(self):
        for websites in (1, 2, 5, 40):
            with self.subTest(websites=websites):
                fault = '\n'.join(FAULT % ('site%d.example' % number) for number in range(websites))
                text = self.shown(['Downloading binary...', 'ERROR: %s; restoring the previous OLS bundle' % fault,
                                   BACK + fault])
                self.assertIn('; restoring the previous OLS bundle. ' + BACK, text)
                self.assertIn('/usr/local/lsws/conf/vhosts/site0.example/vhost.conf', text)
                self.assertTrue(text.endswith('vhost.conf, rootTag virtualHostConfig.'))

    def test_a_long_reason_keeps_its_beginning_and_its_end(self):
        listing = ''.join('\tlib%03d.so => /lib64/lib%03d.so (0x00007f0000000000)\n' % (n, n) for n in range(40))
        text = self.shown(['ERROR: OLS runtime libraries did not validate: ' + listing + '\tlibudns.so.0 => not found',
                           'ERROR: Required binary failed download, checksum or ABI verification; keeping the '
                           'existing OLS bundle'])
        self.assertIn(' OLS runtime libraries did not validate: lib000.so => ', text)
        self.assertIn(' ... ', text)
        self.assertTrue(text.endswith('libudns.so.0 => not found. Required binary failed download, checksum or ABI '
                                      'verification; keeping the existing OLS bundle'))

    def test_a_long_story_keeps_its_first_and_its_last_messages(self):
        said = ['ERROR: one'] + ['two', 'three', 'four', 'five', 'six', 'seven'] + ['ERROR: eight']
        self.assertEqual(self.shown(said), FAILED + ' one. two. three. ... seven. eight')

    def test_shortening_gives_exactly_the_room_asked_for(self):
        shortened = load()['shortened']
        text = ''.join(chr(ord('a') + number % 26) for number in range(500))
        for limit in (20, 99, 100, 499):
            with self.subTest(limit=limit):
                cut = shortened(text, limit)
                self.assertEqual(len(cut), limit)
                head, tail = cut.split(' ... ')
                self.assertTrue(text.startswith(head) and text.endswith(tail) and len(head) > len(tail) > 0)
        self.assertEqual(shortened(text, 500), text)


class RememberedMessagesTests(unittest.TestCase):
    """The upgrader's own stdOut keeps a message only while the bundle step asks for it."""

    def setUp(self):
        klass = next(node for node in ast.parse(SOURCE).body
                     if isinstance(node, ast.ClassDef) and node.name == 'Upgrade')
        declared = [node for node in klass.body if named(node) == 'Said' and isinstance(node, ast.Assign)]
        self.assertEqual(len(declared), 1)
        klass.body = declared + [node for node in klass.body
                                 if isinstance(node, ast.FunctionDef) and node.name == 'stdOut']
        namespace = {'os': os, 'time': time}
        exec(compile(module(klass), 'upgrade.py', 'exec'), namespace)
        self.target = namespace['Upgrade']
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.log = Path(temp.name) / 'log'
        self.target.LogPathNew, self.target.FromCloud = str(self.log), 0

    def say(self, message):
        with contextlib.redirect_stdout(io.StringIO()):
            self.target.stdOut(message, 0)

    def test_nothing_is_kept_outside_the_bundle_step(self):
        self.assertIsNone(self.target.Said)
        self.say('ERROR: a step that is not the bundle step')
        self.assertIsNone(self.target.Said)
        self.assertIn('] ERROR: a step that is not the bundle step\n', self.log.read_text())

    def test_the_bundle_steps_messages_are_kept_in_order_and_still_logged(self):
        self.target.Said = []
        self.say('Detected platform: ubuntu')
        self.say('ERROR: ' + HOOK)
        self.assertEqual(self.target.Said, ['Detected platform: ubuntu', 'ERROR: ' + HOOK])
        self.assertIn('] ERROR: ' + HOOK + '\n', self.log.read_text())

    def test_a_message_is_kept_even_when_it_cannot_be_written_to_the_log(self):
        self.target.Said = []
        self.target.LogPathNew = str(self.log.parent / 'missing' / 'log')
        with self.assertRaises(OSError):
            self.say('ERROR: ' + HOOK)
        self.assertEqual(self.target.Said, ['ERROR: ' + HOOK])


if __name__ == '__main__':
    unittest.main()
