import shlex
import unittest

from plogical.wordpressInstallerUtilities import (
    build_directory_probe,
    build_wordpress_core_install_command,
    directory_allows_install,
)


class WordPressInstallerUtilitiesTests(unittest.TestCase):
    def test_directory_probe_quotes_the_website_path(self):
        path = "/home/example site/public_html/it's-here"

        command = build_directory_probe(path)

        self.assertIn(shlex.quote(path), command)
        self.assertIn('-mindepth 1 -maxdepth 1 -printf x', command)
        self.assertIn('| head -c 4', command)

    def test_directory_check_accepts_at_most_three_entries(self):
        self.assertTrue(directory_allows_install(1, 'xxx'))
        self.assertFalse(directory_allows_install(1, 'xxxx'))

    def test_directory_check_fails_closed_on_probe_errors(self):
        self.assertFalse(directory_allows_install(0, ''))
        self.assertFalse(directory_allows_install(1, None))

    def test_wordpress_command_uses_system_tar_and_checksum_verification(self):
        command = build_wordpress_core_install_command(
            '7.0.2', '/home/example.com/public_html/', '/usr/bin/php',
        )

        self.assertIn('https://wordpress.org/wordpress-7.0.2.tar.gz', command)
        self.assertIn('mktemp /tmp/cyberpanel-wordpress.', command)
        self.assertIn('tar -xzf', command)
        self.assertIn('--strip-components=1', command)
        self.assertIn('wp core verify-checksums --version=7.0.2', command)
        self.assertIn("trap 'rm -f \"$archive\"' EXIT", command)
        self.assertNotIn('wp core download', command)

    def test_wordpress_command_rejects_untrusted_versions(self):
        invalid_versions = ('latest', '7.0.2;id', '../../tmp', '')

        for version in invalid_versions:
            with self.subTest(version=version):
                with self.assertRaisesRegex(ValueError, 'Invalid WordPress version'):
                    build_wordpress_core_install_command(
                        version, '/home/example.com/public_html/', '/usr/bin/php',
                    )


if __name__ == '__main__':
    unittest.main()
