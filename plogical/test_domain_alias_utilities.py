import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from plogical import sslUtilities as ssl_utilities_module
from plogical.domainAliasUtilities import merge_alias_names, remove_alias_from_map_line
from plogical.sslUtilities import sslUtilities


class DomainAliasUtilitiesTests(unittest.TestCase):

    @patch.object(sslUtilities, 'removeSSLForDomain', return_value=1)
    def test_module_level_certificate_cleanup_delegates_to_utility(self, remove_ssl):
        self.assertEqual(
            ssl_utilities_module.removeSSLForDomain('child.example.com'),
            1,
        )
        remove_ssl.assert_called_once_with('child.example.com')

    def test_current_and_legacy_aliases_are_merged_without_duplicates(self):
        aliases = merge_alias_names(
            ['current.example', 'shared.example'],
            ['legacy.example', 'shared.example'],
        )
        self.assertEqual(
            ['current.example', 'shared.example', 'legacy.example'],
            aliases,
        )

    def test_alias_is_removed_without_dropping_other_mapped_domains(self):
        line = '  map                     main.example main.example, first.example, remove.example, last.example\n'
        updated = remove_alias_from_map_line(line, 'main.example', 'remove.example')
        self.assertEqual(
            '  map                     main.example main.example, first.example, last.example\n',
            updated,
        )

    def test_other_maps_are_unchanged(self):
        line = '  map                     other.example other.example, remove.example\n'
        self.assertEqual(
            line,
            remove_alias_from_map_line(line, 'main.example', 'remove.example'),
        )

    def test_alias_certificate_files_are_removed_without_touching_siblings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            certificate_root = pathlib.Path(temp_dir) / 'live'
            alias_path = certificate_root / 'alias.example.com'
            sibling_path = certificate_root / 'keep.example.com'
            alias_path.mkdir(parents=True)
            sibling_path.mkdir()
            (alias_path / 'fullchain.pem').write_text('alias', encoding='utf-8')
            (sibling_path / 'fullchain.pem').write_text('sibling', encoding='utf-8')

            result = sslUtilities.removeSSLForDomain(
                'alias.example.com',
                certificateRoot=str(certificate_root),
                acmePath=os.path.join(temp_dir, 'missing-acme'),
            )

            self.assertEqual(result, 1)
            self.assertFalse(alias_path.exists())
            self.assertTrue(sibling_path.exists())

    def test_alias_certificate_cleanup_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(
                sslUtilities.removeSSLForDomain(
                    '../outside',
                    certificateRoot=temp_dir,
                    acmePath=os.path.join(temp_dir, 'missing-acme'),
                ),
                0,
            )

    def test_alias_certificate_cleanup_unlinks_symlink_without_deleting_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            certificate_root = pathlib.Path(temp_dir) / 'live'
            target_path = certificate_root / 'keep.example.com'
            alias_path = certificate_root / 'alias.example.com'
            target_path.mkdir(parents=True)
            (target_path / 'fullchain.pem').write_text('target', encoding='utf-8')
            alias_path.symlink_to(target_path.name)

            result = sslUtilities.removeSSLForDomain(
                'alias.example.com',
                certificateRoot=str(certificate_root),
                acmePath=os.path.join(temp_dir, 'missing-acme'),
            )

            self.assertEqual(result, 1)
            self.assertFalse(alias_path.exists())
            self.assertFalse(alias_path.is_symlink())
            self.assertTrue(target_path.is_dir())
            self.assertEqual(
                (target_path / 'fullchain.pem').read_text(encoding='utf-8'),
                'target',
            )


if __name__ == '__main__':
    unittest.main()
