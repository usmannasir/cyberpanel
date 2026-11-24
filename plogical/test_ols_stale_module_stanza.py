"""A declaration of the CyberPanel module on a server that never received it.

Until 3.0.18 the installer declared the module also when it kept the vendor
OpenLiteSpeed (no CyberPanel build for the architecture or system), and older
upgrades did the same after a failed download. The vendor core cannot load the
missing file, reports it on every configuration test and keeps serving; the
upgrade then stopped. These fixtures are that state as servers report it.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('stale_fixture_' + name, str(HERE / (name + '.py')))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


classifier = load('olsStockClassifier')
MARKER = b'cyberpanel_lsi_api_abi_v1'
# What the installer appended (configureCustomModule) to a stock configuration.
STANZA = '\nmodule cyberpanel_ols {\n  ls_enabled          1\n}\n'
STOCK_CONFIG = ('serverName                example\nuser                      nobody\ngroup                     nogroup\n'
                'adminEmails               root@localhost\nautoSSL                   1\n'
                'acmeEmail                 admin@cyberpanel.net\n'
                'module cache {\n  ls_enabled              1\n  checkPrivateCache       1\n}\n'
                'module mod_security {\n  modsecurity  on\n  modsecurity_rules `\nSecRuleEngine On\n'
                'SecRule ARGS "{x}" "id:1"\n`\n  modsecurity_rules_file /usr/local/lsws/conf/modsec/rules.conf\n}\n')


class StaleModuleStanzaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'lsws'
        for name in ('bin', 'modules', 'conf/vhosts/site'):
            (self.root / name).mkdir(parents=True)
        self.core = self.root / 'bin/openlitespeed'
        self.core.write_bytes(b'\x7fELF vendor core 1.8.4')
        self.module = self.root / 'modules/cyberpanel_ols.so'
        self.httpd = self.root / 'conf/httpd_config.conf'
        self.httpd.write_text(STOCK_CONFIG + STANZA)

    def missing(self, slashes='//', stamp='2026-11-24 07:52:07.891010 ', pid='[200193] '):
        # The configuration test runs with LSWS_HOME ending in a slash.
        return ('%s[ERROR] %sFailed to load module [cyberpanel_ols], error: %s%smodules/cyberpanel_ols.so: '
                'cannot open shared object file: No such file or directory' % (stamp, pid, self.root, slashes))

    def output(self, *extra, **kwargs):
        return '\n'.join((self.missing(**kwargs),) + extra) + '\n'

    def state(self, output=None, returncode=2):
        return classifier.stale_module_stanza(self.core, returncode, self.output() if output is None else output)

    def test_the_reported_state_is_recognised(self):
        baseline = self.state()
        self.assertEqual(baseline['state'], 'stale-module-stanza')
        self.assertEqual(baseline['returncode'], 2)
        self.assertEqual(baseline['errors'], ['[ERROR] Failed to load module [cyberpanel_ols], error: %s//modules/'
                                              'cyberpanel_ols.so: cannot open shared object file: No such file or '
                                              'directory' % self.root])

    def test_path_spelling_timestamps_and_process_ids_do_not_matter(self):
        for kwargs in ({'slashes': '/'}, {'stamp': ''}, {'pid': ''}, {'stamp': '', 'pid': ''}):
            with self.subTest(**kwargs):
                self.assertIsNotNone(self.state(self.output(**kwargs)))
        # The baseline identifies the same state in a later run.
        self.assertEqual(self.state(self.output(stamp='2026-11-24 08:00:00.000001 ', pid='[3] ')),
                         self.state())

    def test_status_zero_or_one_and_website_errors_are_still_this_state(self):
        site = ('2026-11-24 07:52:07.891011 [ERROR] [200193] [config:server:vhosts:vhost:example.com:epsr:lsphp73] '
                'invalid path - /usr/local/lsws/lsphp73/bin/lsphp, it cannot be started by Web server!')
        warn = '2026-11-24 07:52:07.891012 [WARN] [200193] [PlainConf] [httpServerConfig:] Not support [autossl 1]'
        baseline = self.state(self.output(site, warn))
        self.assertIsNotNone(baseline)
        self.assertEqual(len(baseline['errors']), 2)
        for code in (0, 1):
            self.assertIsNotNone(self.state(returncode=code))

    def test_a_module_file_of_any_kind_is_not_this_state(self):
        for shape in ('marked', 'incompatible', 'empty', 'dangling link', 'link'):
            with self.subTest(shape=shape):
                if shape == 'marked':
                    self.module.write_bytes(b'\x7fELF ' + MARKER)
                elif shape == 'incompatible':
                    self.module.write_bytes(b'\x7fELF built for GLIBC_2.34')
                elif shape == 'empty':
                    self.module.write_bytes(b'')
                elif shape == 'dangling link':
                    self.module.symlink_to(self.root / 'missing.so')
                else:
                    target = self.root / 'other.so'
                    target.write_bytes(b'\x7fELF ' + MARKER)
                    self.module.symlink_to(target)
                self.assertIsNone(self.state())
                self.module.unlink()

    def test_a_cyberpanel_core_or_the_legacy_ubuntu_core_is_not_this_state(self):
        self.core.write_bytes(b'\x7fELF ' + MARKER)
        self.assertIsNone(self.state())
        self.core.write_bytes(b'\x7fELF legacy 2.5.0')
        with patch.object(classifier, 'LEGACY_UBUNTU_CORE', hashlib.sha256(self.core.read_bytes()).hexdigest()):
            self.assertIsNone(self.state())
        self.core.unlink()
        self.core.symlink_to(self.root / 'bin/elsewhere')
        self.assertIsNone(self.state())

    def test_a_stock_recovery_policy_is_not_this_state(self):
        (self.root / '.cyberpanel-stock-recovery-policy').write_bytes(b'CYBERPANEL_STOCK_RECOVERY_V1\n')
        self.assertIsNone(self.state())

    def test_any_other_global_error_keeps_the_refusal(self):
        for extra in ('2026-11-24 07:52:07.9 [ERROR] [200193] [PlainConf] [httpServerConfig:] Not support [x 1]',
                      '[FATAL] cannot open listener',
                      '[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed core ABI',
                      '2026-11-24 07:52:07.9 [ERROR] [200193] Failed to load module [mod_security], error: '
                      '%s//modules/mod_security.so: cannot open shared object file: No such file or directory'
                      % self.root):
            with self.subTest(extra=extra):
                self.assertIsNone(self.state(self.output(extra)))
        # The same line twice, or for another installation, is not this state either.
        self.assertIsNone(self.state(self.output(self.missing())))
        other = self.missing().replace(str(self.root), '/opt/other-lsws')
        self.assertIsNone(self.state(other + '\n'))
        self.assertIsNone(self.state(self.missing().replace('No such file or directory', 'Permission denied')))

    def test_a_crashed_or_timed_out_test_is_not_this_state(self):
        for code in (-11, 3, 124):
            with self.subTest(code=code):
                self.assertIsNone(self.state(returncode=code))

    def test_only_one_plain_top_level_declaration_is_accepted(self):
        refused = {
            'two declarations': STOCK_CONFIG + STANZA + STANZA,
            'unknown setting': STOCK_CONFIG + '\nmodule cyberpanel_ols {\n  ls_enabled 1\n  param x\n}\n',
            'comment inside': STOCK_CONFIG + '\nmodule cyberpanel_ols {\n  # on\n  ls_enabled 1\n}\n',
            'one line': STOCK_CONFIG + '\nmodule cyberpanel_ols { ls_enabled 1 }\n',
            'inside a block': STOCK_CONFIG + 'virtualHost x {\nmodule cyberpanel_ols {\n  ls_enabled 1\n}\n}\n',
            'unterminated': STOCK_CONFIG + '\nmodule cyberpanel_ols {\n  ls_enabled 1\n',
            'mentioned elsewhere': '# cyberpanel_ols was here\n' + STOCK_CONFIG + STANZA,
            'only in opaque text': STOCK_CONFIG.replace('SecRuleEngine On', 'module cyberpanel_ols {\n}'),
            'unbalanced': STOCK_CONFIG + '}\n' + STANZA,
            'windows line ends': (STOCK_CONFIG + STANZA).replace('\n', '\r\n'),
        }
        for name, text in refused.items():
            with self.subTest(name):
                self.httpd.write_text(text)
                self.assertIsNone(self.state())
        for body in ('  ls_enabled 0', '\tls_enabled\t1  ', ''):
            with self.subTest(body=body):
                self.httpd.write_text(STOCK_CONFIG + '\nmodule  cyberpanel_ols  {\n' + body + '\n}\n')
                self.assertIsNotNone(self.state())

    def test_a_linked_missing_or_unreadable_configuration_is_not_this_state(self):
        real = self.root / 'conf/real.conf'
        self.httpd.rename(real)
        self.assertIsNone(self.state())
        self.httpd.symlink_to(real)
        self.assertIsNone(self.state())
        self.httpd.unlink()
        self.httpd.write_bytes(b'\xff\xfe' + (STOCK_CONFIG + STANZA).encode())
        self.assertIsNone(self.state())

    def test_removal_takes_out_exactly_the_declaration(self):
        text = STOCK_CONFIG + STANZA + 'listener Default {\n  address *:80\n}\n'
        span = classifier.module_stanza(text)
        self.assertIsNotNone(span)
        removed = classifier.without_module_stanza(text, span)
        self.assertEqual(removed, STOCK_CONFIG + '\n' + 'listener Default {\n  address *:80\n}\n')
        self.assertIsNone(classifier.module_stanza(removed))
        self.assertNotIn('cyberpanel_ols', removed)
        # The opaque ModSecurity rules, with braces inside, are left as they were.
        self.assertIn('SecRule ARGS "{x}" "id:1"\n`', removed)

    def test_the_module_is_declarable_only_beside_the_cyberpanel_build(self):
        marked = b'\x7fELF ' + MARKER
        self.assertFalse(classifier.module_declarable(self.root))  # vendor core, no module
        self.module.write_bytes(marked)
        self.assertFalse(classifier.module_declarable(self.root))  # vendor core beside our module
        self.core.write_bytes(marked)
        self.assertTrue(classifier.module_declarable(self.root))
        self.module.write_bytes(b'\x7fELF module without the marker')
        self.assertFalse(classifier.module_declarable(self.root))
        self.module.unlink()
        target = self.root / 'other.so'
        target.write_bytes(marked)
        self.module.symlink_to(target)
        self.assertFalse(classifier.module_declarable(self.root))
        self.assertFalse(classifier.module_declarable(self.root / 'missing'))

    def test_launcher_entry_point(self):
        script = str(HERE / 'olsStockClassifier.py')

        def run(*args, output=None):
            return subprocess.run([sys.executable, '-IB', script] + list(args), input=output or self.output(),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)

        self.assertEqual(run('--stale-module-stanza', str(self.core), '2').returncode, 0)
        self.assertEqual(run('--stale-module-stanza', str(self.core), '2',
                             output=self.output('[ERROR] something else')).returncode, 3)
        self.assertEqual(run('--stale-module-stanza', str(self.core), 'two').returncode, 78)
        self.assertEqual(run('--stale-module-stanza', str(self.core)).returncode, 64)
        self.assertEqual(run('--unknown', str(self.core), '2', '/etc/os-release').returncode, 64)


if __name__ == '__main__':
    unittest.main()
