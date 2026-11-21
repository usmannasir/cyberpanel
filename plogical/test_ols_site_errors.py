"""An error in one website's configuration must not refuse an upgrade.

Reported on 21 Nov 2026: mail websites still pointed at PHP 7.3, which was no
longer installed, and one website file had a stray closing brace. OpenLiteSpeed
ran with both; the upgrade to 3.0.10 stopped at its configuration check.
"""
import ast
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

STAMP = '2026-11-21 19:54:31.349049 [ERROR] [191712] '
REPORTED = [
    STAMP + '[config:server:vhosts:vhost:mail.eaglestccs.com:scripthandler:add] use static file handler for suffix [php]',
    STAMP + '[config:server:vhosts:vhost:mail.captainlabaguis.com:epsr:capta74768842.655340] invalid path - '
            '/usr/local/lsws/lsphp73/bin/lsphp, it cannot be started by Web server!',
    STAMP + '[config:server:vhosts:vhost:mail.captainlabaguis.com:scripthandler:add] HttpMime::addMimeHandler '
            'getHandler with name capta74768842 ret (nil)',
    STAMP + "[PlainConf] [virtualHostConfig:] parseline found more '}' in "
            "/usr/local/lsws/conf/vhosts/caritasgumaca.com/vhost.conf:110",
]
# (line, the one website it is confined to)
VECTORS = [
    (REPORTED[0], 'website mail.eaglestccs.com'),
    (REPORTED[1], 'website mail.captainlabaguis.com'),
    (REPORTED[2], 'website mail.captainlabaguis.com'),
    (REPORTED[3], 'website caritasgumaca.com'),
    ('[ERROR] [config:server:vhosts:vhost:shop.example.com] missing docRoot', 'website shop.example.com'),
    ('2026-11-21 20:02:19.431919 [ERROR] [101268] Path for vhost config is invalid: '
     '/usr/local/lsws/conf/vhosts/gone.example.com/vhost.conf', 'website gone.example.com'),
    ('[ERROR] [PlainConf] [virtualHostConfig:] Not support [nosuch 1] in file /usr/local/lsws/conf/vhosts/a.com/vhost.conf:9',
     'website a.com'),
    ("[ERROR] [PlainConf] [virtualHostConfig:] parseline found more '}' in /home/a.com/custom/vhost.conf:3",
     'file /home/a.com/custom/vhost.conf'),
    # Not confined to one website: these still stop an upgrade.
    (STAMP + '[config:server:listener:SSL] failed to load the certificate', None),
    (STAMP + '[PlainConf] [adminConfig:] Not support [throttleenabled 1] in file /usr/local/lsws/admin/conf/admin_config.conf:3', None),
    (STAMP + "[PlainConf] [httpServerConfig:] parseline found more '}' in /usr/local/lsws/conf/httpd_config.conf:40", None),
    ('[ERROR] [PlainConf] [virtualHostConfig:] a failure that names no file', None),
    ('[ERROR] invalid PHP path', None),
    ('[ERROR] Path for vhost config is invalid: relative/vhost.conf', None),
    ('2026-11-21 19:54:31.3 [FATAL] [1] [config:server:vhosts:vhost:shop.example.com] cannot continue', None),
    ('[ERROR] [config:server:vhosts:vhost:shop.example.com] [cyberpanel_ols] Module v2.7.7 DISABLED: '
     'incompatible OpenLiteSpeed core ABI (expected CyberPanel OLS 2.5.2)', None),
    ('[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed core ABI (expected CyberPanel OLS 2.5.2)', None),
]
HARMLESS = [
    '2026-11-21 19:44:40.824386 [WARN] [264970] [config:server:vhosts:vhost:Example] Uid of /usr/local/lsws/Example/html/ is 0',
    '[StockRecovery] Native AutoSSL remains inactive to preserve stock behavior',
    '',
]


def helper(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location('site_fixture_' + name, str(HERE / (name + '.py')))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


classifier = helper('olsStockClassifier')


class ClassifierTests(unittest.TestCase):
    def test_each_line_is_confined_to_the_expected_website_or_to_none(self):
        for line, scope in VECTORS:
            with self.subTest(line=line):
                self.assertEqual(classifier.site_scope(line), scope)
        for line in HARMLESS:
            self.assertIsNone(classifier.site_scope(line))

    def test_the_reported_output_stops_nothing_and_names_three_websites(self):
        output = '\n'.join(HARMLESS + REPORTED) + '\n'
        self.assertEqual(classifier.blocking_errors(output), [])
        found = classifier.site_errors(output)
        self.assertEqual(sorted(found), ['website caritasgumaca.com', 'website mail.captainlabaguis.com',
                                         'website mail.eaglestccs.com'])
        self.assertEqual(found['website mail.captainlabaguis.com'], REPORTED[1:3])

    def test_everything_else_still_stops(self):
        output = '\n'.join(line for line, _ in VECTORS) + '\n'
        self.assertEqual(classifier.blocking_errors(output), [line for line, scope in VECTORS if scope is None])

    def test_an_error_in_a_website_that_was_clean_before_stops(self):
        known = classifier.site_errors('\n'.join(REPORTED))
        self.assertEqual(classifier.blocking_errors('\n'.join(REPORTED), known), [])
        # The same website may word its error differently under another core.
        reworded = '[ERROR] [config:server:vhosts:vhost:mail.eaglestccs.com:epsr] cannot start lsphp73'
        self.assertEqual(classifier.blocking_errors(reworded, known), [])
        new = '[ERROR] [config:server:vhosts:vhost:shop.example.com] missing docRoot'
        self.assertEqual(classifier.blocking_errors('\n'.join(REPORTED + [new]), known), [new])
        self.assertEqual(classifier.blocking_errors(new, {}), [new])

    def test_status_two_needs_a_website_error_to_account_for_it(self):
        # Measured on OpenLiteSpeed 2.5.7: 1 after warnings, 2 after any error line.
        reported, harmless = '\n'.join(REPORTED), '\n'.join(HARMLESS)
        for status, output, refused in ((0, '', False), (1, harmless, False), (2, reported, False),
                                        (2, harmless, True), (2, '', True), (3, reported, True),
                                        (78, reported, True), (124, '', True), (-11, reported, True)):
            with self.subTest(status=status, output=output[:40]):
                self.assertEqual(classifier.status_refused(status, output), refused)

    def test_the_launcher_applies_the_same_rule(self):
        source = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        function = source[source.index('OLS_Blocking_Errors() {'):source.index('\nOLS_Custom_Config_Test() (')]
        lines = [line for line, _ in VECTORS] + HARMLESS
        script = function + '\nOLS_Blocking_Errors "$2"\nOLS_Validation_Refused "$1" "$2"'
        for output in ('\n'.join(lines), '\n'.join(REPORTED), '\n'.join(HARMLESS), '') + tuple(line for line, _ in VECTORS):
            for status in (0, 1, 2, 3, 78, 124, 139):
                with self.subTest(status=status, output=output[:60]):
                    result = subprocess.run(['bash', '-c', script, 'bash', str(status), output],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=20)
                    self.assertEqual(result.stderr, '')
                    blocking = classifier.blocking_errors(output)
                    self.assertEqual(result.stdout.splitlines(), blocking)
                    self.assertEqual(result.returncode == 0, bool(blocking) or classifier.status_refused(status, output))


class UpgraderTests(unittest.TestCase):
    """The upgrader's own check, with the real helpers and a real subprocess."""

    def setUp(self):
        path = HERE / 'upgrade.py'
        wanted = {'OLSUpgradeFailure', 'load_ols_diagnostic_helper', 'validate_ols_configuration',
                  'ols_site_error_notice'}
        nodes = [node for node in ast.parse(path.read_text()).body if getattr(node, 'name', '') in wanted]
        self.assertEqual(len(nodes), len(wanted))
        self.namespace = {'__file__': str(path), 'os': os}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), self.namespace)
        self.validate = self.namespace['validate_ols_configuration']
        self.failure = self.namespace['OLSUpgradeFailure']
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.binary = Path(self.temporary.name) / 'bin/openlitespeed'
        self.binary.parent.mkdir()
        self.output = Path(self.temporary.name) / 'output'

    def native(self, lines, status=2):
        self.output.write_text('\n'.join(lines) + '\n')
        self.binary.write_text('#!/bin/sh\ncat %s >&2\nexit %d\n' % (self.output, status))
        self.binary.chmod(0o700)

    def test_reported_server_is_upgraded_and_told_what_to_correct(self):
        self.native(HARMLESS + REPORTED)  # the status the real core gives for this output
        self.assertIsNone(self.validate(str(self.binary)))
        notice = self.namespace['ols_site_error_notice']()
        self.assertIn('3 website(s)', notice)
        self.assertIn('the upgrade continues', notice)
        for line in REPORTED:
            self.assertIn(line, notice)
        self.assertIn('PHP version chosen for that website is not installed', notice)
        # Later checks of the same run accept the same websites again.
        self.assertIsNone(self.validate(str(self.binary)))

    def test_a_clean_server_gets_no_notice(self):
        self.native(HARMLESS, 1)
        self.assertIsNone(self.validate(str(self.binary)))
        self.assertEqual(self.namespace['ols_site_error_notice'](), '')

    def test_an_error_that_appears_during_the_upgrade_is_refused(self):
        self.native(REPORTED)
        self.validate(str(self.binary))
        new = '[ERROR] [config:server:vhosts:vhost:shop.example.com] missing docRoot'
        self.native(REPORTED + [new])
        with self.assertRaises(self.failure) as refusal:
            self.validate(str(self.binary))
        self.assertIn(new, str(refusal.exception))
        self.assertNotIn('mail.eaglestccs.com', str(refusal.exception))
        # A website that had no error when the run began is not excused later either.
        self.native(HARMLESS, 1)
        fresh = dict(self.namespace)
        exec(compile(ast.Module(body=[node for node in ast.parse((HERE / 'upgrade.py').read_text()).body
                                      if getattr(node, 'name', '') == 'validate_ols_configuration'],
                                type_ignores=[]), 'upgrade.py', 'exec'), fresh)
        fresh['validate_ols_configuration'](str(self.binary))
        self.native(REPORTED[:1])
        with self.assertRaises(self.failure):
            fresh['validate_ols_configuration'](str(self.binary))

    def test_server_wide_errors_and_failed_tests_are_still_refused(self):
        listener = STAMP + '[config:server:listener:SSL] failed to load the certificate'
        for lines, status in ((REPORTED + [listener], 2), (REPORTED + ['[FATAL] cannot continue'], 2),
                              (HARMLESS, 2), (REPORTED, 3), (REPORTED, 139)):
            with self.subTest(lines=lines[-1], status=status):
                self.native(lines, status)
                with self.assertRaises(self.failure) as refusal:
                    self.validate(str(self.binary))
                self.assertIn('validation failed', str(refusal.exception))
                self.assertFalse(hasattr(self.validate, 'site_errors'))
        self.native(REPORTED + [listener])
        with self.assertRaises(self.failure) as refusal:
            self.validate(str(self.binary))
        self.assertIn(listener, str(refusal.exception))
        self.assertNotIn('lsphp73', str(refusal.exception))

    def test_without_the_classifier_every_error_stops_the_upgrade(self):
        real = self.namespace['load_ols_diagnostic_helper']

        def broken(name):
            if name == 'olsStockClassifier.py':
                raise SyntaxError('broken helper')
            return real(name)
        self.namespace['load_ols_diagnostic_helper'] = broken
        self.native(REPORTED)
        with self.assertRaises(self.failure) as refusal:
            self.validate(str(self.binary))
        self.assertIn('lsphp73', str(refusal.exception))
        self.native(HARMLESS, 1)
        self.assertIsNone(self.validate(str(self.binary)))


if __name__ == '__main__':
    unittest.main()
