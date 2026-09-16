import os
import shlex
import unittest

from plogical.wordpressInstallerUtilities import (
    build_directory_probe,
    build_wordpress_core_install_command,
    change_php_succeeded,
    directory_allows_install,
    php_binary_for_selection,
    select_wordpress_version,
    wordpress_php_change_required,
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

    def test_wordpress_api_version_skips_invalid_offers(self):
        offers = [
            {'current': '7.0.2;id'},
            {'current': '7.0.2'},
            {'current': '6.9.1'},
        ]

        self.assertEqual('7.0.2', select_wordpress_version(offers))

    def test_wordpress_api_version_requires_a_valid_release(self):
        with self.assertRaisesRegex(ValueError, 'valid release'):
            select_wordpress_version([{}, {'current': 'latest'}])

    def test_matching_wordpress_php_does_not_require_a_web_server_restart(self):
        php = '/usr/local/lsws/lsphp83/bin/php'

        self.assertFalse(wordpress_php_change_required(php, php))
        self.assertTrue(
            wordpress_php_change_required(
                '/usr/local/lsws/lsphp82/bin/php', php,
            )
        )

    def test_php_selection_maps_to_the_exact_requested_runtime(self):
        self.assertEqual(
            '/usr/local/lsws/lsphp85/bin/php',
            php_binary_for_selection('PHP 8.5'),
        )
        with self.assertRaisesRegex(ValueError, 'Invalid PHP version'):
            php_binary_for_selection('PHP latest')

    def test_change_php_requires_the_explicit_success_record(self):
        self.assertTrue(change_php_succeeded('example.com\n1,None\n'))
        self.assertFalse(change_php_succeeded('example.com\n0,missing runtime\n'))
        self.assertFalse(change_php_succeeded(''))

    def test_installer_does_not_force_existing_sites_to_php_83(self):
        source_path = os.path.join(os.path.dirname(__file__), 'applicationInstaller.py')
        with open(source_path, encoding='utf-8') as source_file:
            source = source_file.read()
        installer = source.split('    def installWordPress(self):', 1)[1].split(
            '    def wordpressInstallNew(self):', 1
        )[0]
        self.assertNotIn("changePHP --phpVersion 'PHP 8.3'", installer)
        self.assertNotIn("FinalPHPPath = '/usr/local/lsws/lsphp83/bin/php'", installer)


if __name__ == '__main__':
    unittest.main()
