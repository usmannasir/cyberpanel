"""Preservation policy tests; all filesystem paths and commands are isolated."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'cyberpanel_firewall_migration.py'
spec = importlib.util.spec_from_file_location('csf_preservation', MODULE)
csf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csf)


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.config = self.root / 'csf.conf'
        self.config.write_text('TCP_IN = "22,8090"\n')
        self.files = {str(self.config): csf._tree((str(self.config),))[str(self.config)]}
        self.services = {'csf.service': 'ActiveState=active', 'lfd.service': 'ActiveState=active'}
        self.rules = {'ipv4': '*filter\n:INPUT DROP [1:80]\n-A INPUT -p tcp --dport 22 -j ACCEPT\nCOMMIT\n'}
        self.manifest = {'version': 1, 'roots': [str(self.config)], 'files': self.files,
                         'services': self.services, 'plugin': None,
                         'rules': {'ipv4': csf.hashlib.sha256(csf._normalized_rules(self.rules['ipv4']).encode()).hexdigest()}}
        self.path = self.root / 'manifest.json'
        self.path.write_text(json.dumps(self.manifest))
        self.path.chmod(0o600)
        for name, value in (('_service_state', self.services), ('_plugin_state', None), ('_rules', self.rules)):
            mock = patch.object(csf, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def test_unchanged_snapshot_verifies(self):
        self.assertTrue(csf.verify(str(self.root)))

    def test_config_change_is_detected(self):
        self.config.write_text('TCP_IN = "1"')
        with self.assertRaisesRegex(RuntimeError, 'configuration'):
            csf.verify(str(self.root))

    def test_mode_change_is_detected(self):
        self.config.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError, 'configuration'):
            csf.verify(str(self.root))

    def test_deleted_config_is_detected(self):
        self.config.unlink()
        with self.assertRaisesRegex(RuntimeError, 'configuration'):
            csf.verify(str(self.root))

    def test_policy_change_is_detected(self):
        self.rules['ipv4'] += '-A INPUT -j ACCEPT\n'
        with self.assertRaisesRegex(RuntimeError, 'policy'):
            csf.verify(str(self.root))

    def test_counters_do_not_fail_verification(self):
        self.rules['ipv4'] = self.rules['ipv4'].replace('[1:80]', '[900:99000]')
        self.assertTrue(csf.verify(str(self.root)))

    def test_configured_timeouts_are_not_ignored(self):
        self.assertNotEqual(csf._normalized_rules('create qa hash:ip timeout 60'),
                            csf._normalized_rules('create qa hash:ip timeout 90'))
        self.assertNotEqual(csf._normalized_rules('timeout 60s'),
                            csf._normalized_rules('timeout 90s'))

    def test_member_countdowns_are_normalized(self):
        self.assertEqual(csf._normalized_rules('add qa 198.51.100.1 timeout 59'),
                         csf._normalized_rules('add qa 198.51.100.1 timeout 57'))
        self.assertEqual(csf._normalized_rules('expires 59s12ms'),
                         csf._normalized_rules('expires 57s98ms'))

    def test_service_change_is_detected(self):
        self.services['lfd.service'] = 'ActiveState=inactive'
        with self.assertRaisesRegex(RuntimeError, 'service state'):
            csf.verify(str(self.root))

    def test_plugin_change_is_detected(self):
        with patch.object(csf, '_plugin_state', return_value={'files': {}, 'activation': {}}):
            with self.assertRaisesRegex(RuntimeError, 'integration'):
                csf.verify(str(self.root))

    def test_public_state_directory_rejected(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'private root-owned'):
            csf.verify(str(self.root))

    def test_public_manifest_rejected(self):
        self.path.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, 'private root-owned'):
            csf.verify(str(self.root))

    def test_symlink_manifest_rejected(self):
        target = self.root / 'saved'
        self.path.rename(target)
        self.path.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'regular file'):
            csf.verify(str(self.root))

    def test_unexpected_manifest_version_rejected(self):
        self.manifest['version'] = 999
        self.path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(RuntimeError, 'version'):
            csf.verify(str(self.root))

    def test_deleted_csf_marker_does_not_bypass_state_verification(self):
        with patch.dict(os.environ, {csf.STATE_ENV: str(self.root)}), patch.object(csf, 'verify', side_effect=RuntimeError('removed')):
            with self.assertRaises(SystemExit):
                csf.requireCSFMigration()

    def test_missing_manifest_never_bypasses_guard(self):
        self.path.unlink()
        with patch.dict(os.environ, {csf.STATE_ENV: str(self.root)}):
            with self.assertRaises(SystemExit):
                csf.requireCSFMigration()

    def test_symlinks_are_recorded_without_following(self):
        link = self.root / 'link'
        link.symlink_to('/unavailable')
        self.assertEqual('/unavailable', csf._tree((str(link),))[str(link)]['link'])


if __name__ == '__main__':
    unittest.main()
