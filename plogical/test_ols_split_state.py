"""A vendor core beside a self-disabled CyberPanel module is classified by what
the bundle transaction needs to know, never by fingerprints of the old files."""
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('split_fixture_' + name, str(HERE / (name + '.py')))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


classifier = load('olsStockClassifier')
parser = load('olsParserRecovery')
MARKER = b'cyberpanel_lsi_api_abi_v1'
ABI = ('[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed '
       'core ABI (expected CyberPanel OLS 2.5.2)')


class SplitStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'lsws'
        for name in ('bin', 'modules', 'conf/vhosts/site', 'admin/conf'):
            (self.root / name).mkdir(parents=True)
        self.core = self.root / 'bin/openlitespeed'
        self.core.write_bytes(b'\x7fELF vendor core 1.9.4')
        self.module = self.root / 'modules/cyberpanel_ols.so'
        self.module.write_bytes(b'\x7fELF ' + MARKER)
        self.httpd = self.root / 'conf/httpd_config.conf'
        self.httpd.write_text('serverName example\nuser nobody\nautoSSL                   1\n'
                              'acmeEmail                 admin@cyberpanel.net\n')
        self.admin = self.root / 'admin/conf/admin_config.conf'
        self.admin.write_text('enableCoreDump 1\nthrottleEnabled 1\nthrottleMaxFailures 5\n'
                              'throttleBlockWindow 900\nthrottleMaxBackoff 3600\n'
                              'loginHistoryRetention 90\nopsAuditRetainFiles 30\n')
        self.release = Path(self.temp.name) / 'os-release'
        self.release.write_text('ID="almalinux"\nVERSION_ID="9.9"\n')

    def unsupported(self, level, directive, path, number, stamp='2026-11-19 14:41:43.122363 ', pid=''):
        return '%s[%s] %s[PlainConf] [%s] Not support [%s] in file %s:%s' % (
            stamp, level, pid, 'adminConfig:' if path == self.admin else 'httpServerConfig:',
            directive, path, number)

    def default_output(self, stamp='2026-11-19 14:41:43.122363 '):
        return '\n'.join([
            ABI,
            self.unsupported('WARN', 'autossl 1', self.httpd, 3, stamp),
            self.unsupported('WARN', 'acmeemail admin@cyberpanel.net', self.httpd, 4, stamp),
            stamp + '[WARN] [1579] [config:server:vhosts:vhost:Example] Uid of /usr/local/lsws/Example/html/ '
                    'is 0, smaller than minimum requirement 11, use server uid!',
        ]) + '\n'

    def admin_errors(self, pid='[2211] '):
        return [self.unsupported('ERROR', directive, self.admin, number, pid=pid) for number, directive in enumerate(
            ('throttleenabled 1', 'throttlemaxfailures 5', 'throttleblockwindow 900',
             'throttlemaxbackoff 3600', 'loginhistoryretention 90', 'opsauditretainfiles 30'), 2)]

    def state(self, returncode, output):
        return classifier.split_state(self.core, returncode, output, parser, str(self.release))

    def test_default_configuration_after_a_package_update_is_repairable(self):
        baseline = self.state(1, self.default_output())
        self.assertEqual(baseline, {'returncode': 1, 'errors': [ABI]})

    def test_vendor_rejection_of_our_webadmin_directives_is_not_a_configuration_fault(self):
        output = self.default_output() + '\n'.join(self.admin_errors()) + '\n'
        baseline = self.state(2, output)
        self.assertEqual(baseline['returncode'], 2)
        self.assertEqual(len(baseline['errors']), 7)
        self.assertTrue(all('[2211]' not in line and '14:41:43' not in line for line in baseline['errors']))

    def test_baseline_ignores_timestamps_process_ids_and_warning_noise(self):
        first = self.state(2, self.default_output() + '\n'.join(self.admin_errors()))
        second = self.state(2, self.default_output('2026-11-20 01:02:03.000001 ') + '\n'.join(
            self.admin_errors('[99] ')) + '\n2026-11-20 01:02:03.5 [WARN] [99] another harmless warning\n')
        self.assertEqual(first, second)
        self.assertNotEqual(first, self.state(1, self.default_output()))

    def test_real_configuration_errors_refuse_and_are_shown_in_full(self):
        fault = '2026-11-19 14:41:43.2 [ERROR] [77] [config:server:listener:SSL] ' + 'x' * 2500 + ' missing certificate'
        with self.assertRaises(classifier.SplitStateRefused) as refusal:
            self.state(2, self.default_output() + fault + '\n' + '\n'.join(self.admin_errors()))
        message = str(refusal.exception)
        self.assertIn(fault, message)
        self.assertIn('nothing was changed', message)
        self.assertNotIn('throttleenabled', message)
        with self.assertRaises(classifier.SplitStateRefused):
            self.state(1, self.default_output() + '[FATAL] listener conflict\n')

    def test_an_error_in_one_website_does_not_refuse_the_repair(self):
        site = ('2026-11-21 19:54:31.349049 [ERROR] [191712] [config:server:vhosts:vhost:mail.example.com:epsr:mail.655340] '
                'invalid path - /usr/local/lsws/lsphp73/bin/lsphp, it cannot be started by Web server!')
        brace = ("2026-11-21 19:54:31.351614 [ERROR] [191712] [PlainConf] [virtualHostConfig:] parseline found more '}' "
                 "in /usr/local/lsws/conf/vhosts/shop.example.com/vhost.conf:110")
        # OpenLiteSpeed ends with status 2 after any error, a website's included.
        baseline = self.state(2, self.default_output() + site + '\n' + brace + '\n')
        # The rollback target is this exact state, website errors included.
        self.assertEqual(len(baseline['errors']), 3)
        self.assertEqual(baseline, self.state(2, self.default_output('2026-11-22 00:00:00.000001 ') + brace + '\n' + site + '\n'))
        self.assertNotEqual(baseline, self.state(1, self.default_output()))
        with self.assertRaises(classifier.SplitStateRefused):
            self.state(2, self.default_output())
        with self.assertRaises(classifier.SplitStateRefused):
            self.state(3, self.default_output() + site + '\n')

    def test_a_website_file_that_leaves_a_block_open_does_not_refuse_the_repair(self):
        # Reported on 26 Nov 2026: no line number, and the bracket names the block left open.
        unpaired = ("2026-11-26 09:48:53.707205 [ERROR] [312722] [PlainConf] [context:/] parseFile find '{' and '}' "
                    "do not match in the end of file /usr/local/lsws/conf/vhosts/example.invalid/vhost.conf, "
                    "rootTag virtualHostConfig.")
        baseline = self.state(2, self.default_output() + unpaired + '\n')
        self.assertEqual(len(baseline['errors']), 2)
        self.assertEqual(baseline, self.state(2, self.default_output('2026-11-26 10:00:00.000001 ') + unpaired + '\n'))
        # The same message for the server's own configuration is not a website's error.
        server = unpaired.replace('/conf/vhosts/example.invalid/vhost.conf, rootTag virtualHostConfig.',
                                  '/conf/httpd_config.conf, rootTag httpServerConfig.')
        with self.assertRaises(classifier.SplitStateRefused) as refusal:
            self.state(2, self.default_output() + unpaired + '\n' + server + '\n')
        self.assertIn('httpd_config.conf', str(refusal.exception))
        self.assertNotIn('example.invalid', str(refusal.exception))

    def test_unsupported_line_must_match_the_cited_configuration_line(self):
        for line in (self.unsupported('ERROR', 'throttleenabled 1', self.admin, 1),      # another directive there
                     self.unsupported('ERROR', 'throttleenabled 1', self.admin, 400),    # beyond the file
                     self.unsupported('ERROR', 'vhostowner x', self.httpd, 2),           # not one of ours
                     self.unsupported('ERROR', 'throttleenabled 1', Path('/etc/passwd'), 1)):
            with self.subTest(line=line), self.assertRaises(classifier.SplitStateRefused):
                self.state(2, self.default_output() + line + '\n')
        link = self.root / 'conf/linked.conf'
        link.symlink_to(self.admin)
        with self.assertRaises(classifier.SplitStateRefused):
            self.state(2, self.default_output() + self.unsupported('ERROR', 'throttleenabled 1', link, 2) + '\n')
        # The cited line matches, but the file is not part of this installation.
        outside = Path(self.temp.name) / 'elsewhere.conf'
        outside.write_text('enableCoreDump 1\nthrottleEnabled 1\n')
        with self.assertRaises(classifier.SplitStateRefused):
            self.state(2, self.default_output() + self.unsupported('ERROR', 'throttleenabled 1', outside, 2) + '\n')

    def test_value_the_cyberpanel_core_would_reject_is_a_configuration_fault(self):
        for value in ('7', 'yes', ''):
            with self.subTest(value=value):
                self.admin.write_text('enableCoreDump 1\nthrottleEnabled %s\n' % value)
                line = self.unsupported('ERROR', ('throttleenabled ' + value).strip(), self.admin, 2)
                with self.assertRaises(classifier.SplitStateRefused) as refusal:
                    self.state(2, self.default_output() + line + '\n')
                self.assertIn(line, str(refusal.exception))
        self.admin.write_text('enableCoreDump 1\nthrottleEnabled 0\n')
        self.assertIsNotNone(self.state(2, self.default_output() + self.unsupported(
            'ERROR', 'throttleenabled 0', self.admin, 2) + '\n'))

    def test_exit_status_must_be_explained(self):
        for returncode in (2, 3, 124, -11):
            with self.subTest(returncode=returncode), self.assertRaises(classifier.SplitStateRefused):
                self.state(returncode, self.default_output())
        self.assertIsNotNone(self.state(0, ABI + '\n'))

    def test_other_states_are_left_to_the_ordinary_validation(self):
        self.assertIsNone(self.state(1, self.default_output().replace(ABI, '')))
        self.assertIsNone(self.state(1, self.default_output() + ABI + '\n'))
        self.assertIsNone(self.state(1, 'incompatible OpenLiteSpeed core ABI\n'))
        self.module.write_bytes(b'\x7fELF module without the marker')
        self.assertIsNone(self.state(1, self.default_output()))
        self.module.unlink()
        self.assertIsNone(self.state(1, self.default_output()))
        self.module.write_bytes(b'\x7fELF ' + MARKER)
        self.core.write_bytes(b'\x7fELF custom core ' + MARKER)
        self.assertIsNone(self.state(1, self.default_output()))
        self.core.unlink()
        self.assertIsNone(self.state(1, self.default_output()))

    def test_every_platform_with_a_bundle_is_accepted_without_minor_version_pins(self):
        for release in ('ID=ubuntu\nVERSION_ID="22.04"', 'ID=ubuntu\nVERSION_ID="24.04"',
                        'ID=ubuntu\nVERSION_ID="26.04"', 'ID="almalinux"\nVERSION_ID="8.10"',
                        'ID="almalinux"\nVERSION_ID="9.8"', 'ID="almalinux"\nVERSION_ID="9.9"',
                        'ID="almalinux"\nVERSION_ID="10.2"', 'ID="rocky"\nVERSION_ID="9.7"',
                        'ID="rhel"\nVERSION_ID="8.10"', 'ID="cloudlinux"\nVERSION_ID="9.6"'):
            with self.subTest(release=release):
                self.release.write_text(release + '\n')
                self.assertIsNotNone(self.state(1, self.default_output()))

    def test_platform_without_a_bundle_is_refused_with_a_plain_reason(self):
        for release in ('ID=ubuntu\nVERSION_ID="20.04"', 'ID=debian\nVERSION_ID="12"', 'ID="almalinux"\nVERSION_ID="7.9"'):
            with self.subTest(release=release):
                self.release.write_text(release + '\n')
                with self.assertRaisesRegex(classifier.SplitStateRefused, 'no CyberPanel OpenLiteSpeed bundle'):
                    self.state(1, self.default_output())

    def test_old_files_are_never_fingerprinted(self):
        for core, module in ((b'vendor 1.9.3', b'paired ' + MARKER), (b'vendor 1.9.9 not yet released', b'2.7.6 ' + MARKER)):
            self.core.write_bytes(core)
            self.module.write_bytes(module)
            output = self.default_output().replace('v2.7.7', 'v2.7.6')
            self.assertIsNotNone(self.state(1, output))

    def run_cli(self, returncode, output, *extra):
        return subprocess.run([sys.executable, '-IB', str(HERE / 'olsStockClassifier.py'), '--split-state',
                               str(self.core), str(returncode), str(self.release)] + list(extra),
                              input=output, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=30)

    def test_command_line_reports_the_three_outcomes_in_isolated_mode(self):
        result = self.run_cli(1, self.default_output())
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        result = self.run_cli(1, 'no diagnostic\n')
        self.assertEqual((result.returncode, result.stdout), (3, ''))
        result = self.run_cli(2, self.default_output() + '[ERROR] [config:server] broken include\n')
        self.assertEqual(result.returncode, 4)
        self.assertIn('[ERROR] [config:server] broken include', result.stdout)
        self.assertEqual(self.run_cli(1, self.default_output(), 'unexpected').returncode, 64)

    def test_helper_remains_python_36_compatible(self):
        source = (HERE / 'olsStockClassifier.py').read_text()
        if sys.version_info >= (3, 8):
            ast.parse(source, feature_version=(3, 6))
        self.assertNotIn('capture_output', source)
        self.assertNotIn('text=True', source)


if __name__ == '__main__':
    unittest.main()
