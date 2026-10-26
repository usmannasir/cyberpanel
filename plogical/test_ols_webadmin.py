import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from plogical import olsWebAdmin as target


class WebAdminNoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('bin/openlitespeed', 'ELF fixture cyberpanel_lsi_api_abi_v1')
        self.write(target._BASE, '''<?php
class ProductBase {
    protected function isNewRelease($release) {
        $version = $this->extractReleaseVersion($release);
        return ($release !== '' && $version !== '' && $this->version != $version);
    }
    public static function extractBuildDisplay($versionOutput) {}
}
''')
        self.write(target._OWS, '''<?php
class Product extends ProductBase {
    protected function detectAvailableVersion() {
        $newVersion = '';
        if ($this->version != $currentBranchVersion) {}
        if ($this->version != $latestVersion && $currentBranchVersion != $latestVersion) {}
    }
}
''')
        self.write(target._DASHBOARD,
                   "<?php if ($dashboardNewVersion !== '' && $dashboardNewVersionUrl !== '') { ?>new version<?php } ?>")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_patch(self):
        return target.patch_webadmin_release_notice(str(self.root))

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def test_custom_channel_is_explicit_and_bound_to_binary(self):
        result = self.run_patch()
        self.assertEqual('cyberpanel-custom', result['channel'])
        marker = json.loads((self.root / target._MARKER).read_text())
        binary = (self.root / 'bin/openlitespeed').stat()
        self.assertEqual(binary.st_ino, marker['ino'])
        self.assertEqual(binary.st_size, marker['size'])
        self.assertIn('separate release channel', (self.root / target._DASHBOARD).read_text())
        self.assertIn("version_compare($version, $this->version, '>')", (self.root / target._BASE).read_text())

    def test_reapply_is_noop_without_extra_backup(self):
        self.run_patch()
        before = self.snapshot()
        self.assertEqual('current', self.run_patch()['status'])
        self.assertEqual(before, self.snapshot())

    def test_stock_binary_does_not_gain_custom_channel(self):
        self.write('bin/openlitespeed', 'stock executable fixture')
        self.assertEqual('upstream', self.run_patch()['channel'])

    def test_replacement_stock_binary_clears_custom_channel(self):
        self.run_patch()
        replacement = self.root / 'stock'
        replacement.write_text('stock executable')
        os.replace(str(replacement), str(self.root / 'bin/openlitespeed'))
        self.assertEqual('upstream', self.run_patch()['channel'])

    def test_unknown_dashboard_leaves_all_installed_files_unchanged(self):
        self.write(target._DASHBOARD, '<?php echo "another layout"; ?>')
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Unrecognized WebAdmin'):
            self.run_patch()
        self.assertEqual(before, self.snapshot())

    def test_unknown_comparison_leaves_all_installed_files_unchanged(self):
        self.write(target._BASE, '<?php class ProductBase {}')
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Unrecognized WebAdmin'):
            self.run_patch()
        self.assertEqual(before, self.snapshot())

    def test_partial_replacement_failure_restores_original_bytes(self):
        before = {name: (self.root / name).read_bytes() for name in (target._BASE, target._OWS, target._DASHBOARD)}
        original = os.replace
        count = [0]
        def fail_second(source, destination):
            count[0] += 1
            if count[0] == 2:
                raise OSError('simulated write failure')
            return original(source, destination)
        with patch.object(target.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated write failure'):
                self.run_patch()
        for name, data in before.items():
            self.assertEqual(data, (self.root / name).read_bytes())
        self.assertFalse((self.root / target._MARKER).exists())

    def test_linked_source_is_never_overwritten(self):
        path = self.root / target._BASE
        path.unlink()
        outside = self.root / 'external.php'
        outside.write_text('outside content')
        path.symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, 'Missing or linked'):
            self.run_patch()
        self.assertEqual('outside content', outside.read_text())

    def test_missing_all_webadmin_assets_is_reported_without_writes(self):
        import shutil
        shutil.rmtree(self.root / 'admin')
        before = self.snapshot()
        self.assertEqual('unsupported-webadmin-layout', self.run_patch()['status'])
        self.assertEqual(before, self.snapshot())

    def test_custom_abi_marker_across_read_boundary_is_detected(self):
        (self.root / 'bin/openlitespeed').write_bytes(b'x' * (1024 * 1024 - 10) + target._CUSTOM_ABI)
        self.assertTrue(target._has_custom_abi(str(self.root / 'bin/openlitespeed')))


if __name__ == '__main__':
    unittest.main()
