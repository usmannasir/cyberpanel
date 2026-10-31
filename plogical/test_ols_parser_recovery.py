import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from plogical import olsParserRecovery as recovery


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'bin').mkdir()
        (self.root / 'admin/conf').mkdir(parents=True)
        (self.root / 'bin/openlitespeed').write_bytes(b'known old fixture')
        pin = hashlib.sha256(b'known old fixture').hexdigest()
        patcher = patch.dict(recovery.OLD_CORE_SHA256, ubuntu=pin)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = {'throttleenabled': 1, 'throttlemaxfailures': 3,
                         'throttleblockwindow': 300, 'throttlemaxbackoff': 86400,
                         'loginhistoryretention': 30, 'opsauditretainfiles': 30,
                         'configautobackupretention': 90}

    def diagnostics(self):
        lines, errors = [], []
        path = self.root / 'admin/conf/admin_config.conf'
        for number, (key, value) in enumerate(self.settings.items(), 1):
            lines.append('%s %s' % (key, value))
            errors.append('2026-10-31 12:00:00.123456 [ERROR] [123] [PlainConf] '
                          '[adminConfig:] Not support [%s %s] in file %s:%s' %
                          (key, value, path, number))
        path.write_text('\n'.join(lines) + '\n')
        return '\n'.join(errors) + '\n'

    def check(self, code=2, output=None):
        return recovery.require_known_failure(self.root, 'ubuntu', code,
                                              self.diagnostics() if output is None else output)

    def test_exact_six_and_seven_settings(self):
        self.assertEqual(self.settings, self.check())
        del self.settings['configautobackupretention']
        self.assertEqual(self.settings, self.check())

    def test_unrelated_error_warning_fatal_or_unknown_line_rejected(self):
        valid = self.diagnostics()
        for extra in ('[ERROR] broken vhost', '[WARN] bad listener', '[FATAL] broken', 'unexpected output'):
            with self.subTest(extra=extra), self.assertRaises(RuntimeError):
                self.check(output=valid + extra)

    def test_unknown_hash_and_non_error_status_rejected(self):
        for code in (0, 1, 3, -11):
            with self.subTest(code=code), self.assertRaises(RuntimeError):
                self.check(code=code)
        (self.root / 'bin/openlitespeed').write_bytes(b'foreign build')
        with self.assertRaisesRegex(RuntimeError, 'pinned release'):
            self.check()

    def test_wrong_context_path_line_and_duplicate_rejected(self):
        valid = self.diagnostics()
        for output in (valid.replace('adminConfig:', 'httpServerConfig:'),
                       valid.replace('/admin/conf/', '/conf/'),
                       valid.replace(':1\n', ':99\n'), valid + valid.splitlines()[0]):
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                self.check(output=output)

    def test_invalid_value_typo_and_relationship_rejected(self):
        for key, value in (('throttlemaxfailures', 0), ('throttleenabled', 2),
                           ('throttlemaxfailurez', 3), ('throttlemaxbackoff', 60)):
            with self.subTest(key=key), patch.dict(self.settings, {key: value}), self.assertRaises(RuntimeError):
                self.check()

    def test_changed_config_cannot_reuse_valid_diagnostic(self):
        output = self.diagnostics()
        (self.root / 'admin/conf/admin_config.conf').write_text('throttleEnabled 0\n')
        with self.assertRaises(RuntimeError):
            self.check(output=output)

    def test_host_os_mapping(self):
        os_release = self.root / 'os-release'
        with patch.object(recovery.platform, 'machine', return_value='x86_64'):
            for name, version, expected in (('ubuntu', '22.04', 'ubuntu'),
                                             ('ubuntu', '26.04', 'ubuntu26'),
                                             ('almalinux', '10', 'rhel10')):
                os_release.write_text('ID="%s"\nVERSION_ID="%s"\n' % (name, version))
                self.assertEqual(expected, recovery.host_platform(str(os_release)))
            os_release.write_text('ID=debian\nVERSION_ID=13\n')
            with self.assertRaises(RuntimeError):
                recovery.host_platform(str(os_release))

    def test_customer_warning_patterns_only(self):
        example = self.root / 'Example/html'
        example.mkdir(parents=True)
        warning = '2026-10-31 18:05:14.339358 [WARN] [8824] '
        warnings = [warning + '[cyberpanel_ols] License validation failed - module features disabled',
                    warning + '[config:server:vhosts:vhost:Example] Uid of %s/ is 0, smaller than minimum requirement 11, use server uid!' % example,
                    warning + '[config:server:vhosts:vhost:Example] Gid of %s/ is 65534, smaller than minimum requirement 10, use server gid!' % example]
        with patch.object(Path, 'stat', return_value=type('Info', (), {'st_uid': 0, 'st_gid': 0})()), \
                patch.object(Path, 'is_dir', return_value=True):
            self.assertEqual(self.settings, self.check(output=self.diagnostics() + '\n'.join(warnings)))
            with self.assertRaises(RuntimeError):
                self.check(output=self.diagnostics() + warning + '[cyberpanel_ols] ABI mismatch')


if __name__ == '__main__':
    unittest.main()
