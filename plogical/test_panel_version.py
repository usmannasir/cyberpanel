import json
import pathlib
import unittest
from unittest import mock

from cyberpanel_version import (
    BUILD,
    FULL_VERSION,
    VERSION,
    backup_uses_database_users_schema,
    backup_uses_full_directory_layout,
    version_at_least,
)


class PanelVersionTests(unittest.TestCase):

    def test_release_version_is_3_0_0(self):
        self.assertEqual('3.0', VERSION)
        self.assertEqual(0, BUILD)
        self.assertEqual('3.0.0', FULL_VERSION)

    def test_public_version_file_matches_runtime_version(self):
        version_path = pathlib.Path(__file__).parents[1] / 'version.txt'
        version_data = json.loads(version_path.read_text(encoding='utf-8'))
        self.assertEqual(VERSION, version_data['version'])
        self.assertEqual(BUILD, version_data['build'])

    def test_upgrade_writes_numeric_build_to_runtime_version_file(self):
        from plogical.upgrade import Upgrade

        version_file = mock.mock_open()
        with mock.patch('builtins.open', version_file):
            archive_name = Upgrade.downloadLink()

        written_data = ''.join(
            call.args[0] for call in version_file().write.call_args_list
        )
        self.assertEqual(BUILD, json.loads(written_data)['build'])
        self.assertEqual('%s.%s.tar.gz' % (VERSION, BUILD), archive_name)

    def test_modern_backup_database_schema_accepts_3_x(self):
        self.assertTrue(backup_uses_database_users_schema('3.0', 0))
        self.assertTrue(backup_uses_database_users_schema('3.1', 12))

    def test_modern_backup_database_schema_keeps_existing_boundaries(self):
        self.assertTrue(backup_uses_database_users_schema('2.1', 1))
        self.assertFalse(backup_uses_database_users_schema('2.1', 0))
        self.assertFalse(backup_uses_database_users_schema('2.2', 9))
        self.assertTrue(backup_uses_database_users_schema('2.3', 1))
        self.assertFalse(backup_uses_database_users_schema('2.3', 0))
        self.assertTrue(backup_uses_database_users_schema('2.4', 0))

    def test_invalid_backup_versions_use_legacy_path(self):
        self.assertFalse(backup_uses_database_users_schema(None, 0))
        self.assertFalse(backup_uses_database_users_schema('invalid', 0))
        self.assertFalse(backup_uses_database_users_schema('3.0', 'invalid'))

    def test_full_directory_layout_comparison_is_forward_compatible(self):
        self.assertTrue(backup_uses_full_directory_layout('3.0', 0))
        self.assertTrue(backup_uses_full_directory_layout('2.10', 0))
        self.assertTrue(backup_uses_full_directory_layout('2.0', 1))
        self.assertFalse(backup_uses_full_directory_layout('2.0', 0))

    def test_semantic_version_comparison_does_not_use_decimal_floats(self):
        self.assertTrue(version_at_least('3.0', 0, '1.6'))
        self.assertTrue(version_at_least('1.10', 0, '1.6'))
        self.assertFalse(version_at_least('1.5', 9, '1.6'))
        self.assertFalse(version_at_least('invalid', 0, '1.6'))


if __name__ == '__main__':
    unittest.main()
