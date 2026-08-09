import unittest

from plogical.backupV2Repository import (
    database_name_from_snapshot_path,
    repository_names,
    rustic_repository,
    website_exclude_arguments,
)


class BackupV2RepositoryTests(unittest.TestCase):

    def test_local_repository_does_not_require_rclone(self):
        self.assertEqual(
            rustic_repository('local', 'example.com'),
            '/home/example.com/incrementalbackups',
        )

    def test_remote_repository_is_shell_quoted(self):
        self.assertEqual(
            rustic_repository('team drive', 'example.com'),
            "'rclone:team drive:example.com'",
        )

    def test_unsafe_repository_name_is_rejected(self):
        with self.assertRaises(ValueError):
            rustic_repository("repo'; touch /tmp/unsafe", 'example.com')

    def test_local_repository_is_available_without_rclone_config(self):
        self.assertEqual(repository_names(''), ['local'])

    def test_configured_repositories_are_merged_with_local(self):
        config = '[remote]\ntype = sftp\n\n[local]\ntype = local\n'
        self.assertEqual(repository_names(config), ['local', 'remote'])

    def test_website_backup_excludes_all_backup_repositories(self):
        self.assertEqual(
            website_exclude_arguments('/home/example.com'),
            (
                '--glob !/home/example.com/logs '
                '--glob !/home/example.com/backup '
                '--glob !/home/example.com/incbackup '
                '--glob !/home/example.com/incrementalbackups'
            ),
        )

    def test_database_suffix_is_removed_exactly_once(self):
        self.assertEqual(
            database_name_from_snapshot_path('wordpress.sql'),
            'wordpress',
        )


if __name__ == '__main__':
    unittest.main()
