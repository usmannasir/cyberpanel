import os
import shlex
import unittest

from unittest import mock

from plogical.wordpressInstallerUtilities import (
    build_directory_listing_command,
    build_directory_probe,
    build_entry_removal_command,
    build_wordpress_core_install_command,
    change_php_succeeded,
    current_wordpress_version,
    directory_allows_install,
    directory_entry_names,
    entries_added_since,
    php_binary_for_selection,
    select_wordpress_version,
    single_line_value,
    wordpress_cli_command,
    wordpress_php_change_required,
    wordpress_table_prefix_command,
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

    def test_php_binary_is_built_from_the_digits_of_an_exact_selection(self):
        from managePHP.test_php_selection import NOT_A_SELECTION, OFFERED
        for selection in OFFERED:
            digits = selection[4:].replace('.', '')
            self.assertEqual('/usr/local/lsws/lsphp%s/bin/php' % digits, php_binary_for_selection(selection))
        # Surrounding or repeated white space used to be accepted here while
        # the unchanged text went on to the worker and into the database.
        for value in NOT_A_SELECTION:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid PHP version'):
                    php_binary_for_selection(value)

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


class CurrentReleaseTests(unittest.TestCase):
    def fetch(self, payload):
        fetch = mock.Mock()
        fetch.return_value.json.return_value = payload
        return fetch

    def test_the_current_release_is_the_first_valid_one_wordpress_org_offers(self):
        fetch = self.fetch({'offers': [{'current': '7.1.5'}, {'current': '7.0.9'}]})
        self.assertEqual('7.1.5', current_wordpress_version(fetch))
        fetch.assert_called_once_with('https://api.wordpress.org/core/version-check/1.7/', timeout=15)
        fetch.return_value.raise_for_status.assert_called_once_with()

    def test_an_answer_without_a_release_is_an_error_and_never_a_default_version(self):
        for payload in ({'offers': []}, {'offers': [{'current': '6.0;id'}]}, {}, [], None, 'error'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    current_wordpress_version(self.fetch(payload))

    def test_a_failed_request_is_passed_on(self):
        fetch = self.fetch({'offers': [{'current': '7.1.5'}]})
        fetch.return_value.raise_for_status.side_effect = OSError('503')
        with self.assertRaises(OSError):
            current_wordpress_version(fetch)


class InstallDirectoryBookkeepingTests(unittest.TestCase):
    def test_the_listing_names_every_entry_of_the_directory_itself(self):
        command = build_directory_listing_command("/home/example site/public_html/it's-here")
        self.assertEqual(['find', "/home/example site/public_html/it's-here", '-mindepth', '1', '-maxdepth', '1',
                          '-printf', '%f\\n'], shlex.split(command))

    def test_a_listing_that_failed_is_no_reading(self):
        self.assertEqual({'a', '.b', 'c d'}, directory_entry_names(1, 'a\n.b\nc d\n'))
        self.assertEqual(set(), directory_entry_names(1, ''))
        self.assertIsNone(directory_entry_names(0, 'a\n'))
        self.assertIsNone(directory_entry_names(1, None))

    def test_only_what_was_not_there_before_counts_as_added(self):
        self.assertEqual(['index.php', 'wp-admin'], entries_added_since({'.well-known'}, {'.well-known', 'wp-admin',
                                                                                           'index.php'}))
        self.assertEqual([], entries_added_since({'a', 'b'}, {'a'}))

    def test_without_both_readings_nothing_counts_as_added(self):
        self.assertEqual([], entries_added_since(None, {'wp-admin'}))
        self.assertEqual([], entries_added_since({'a'}, None))

    def test_a_name_that_is_not_a_plain_entry_is_never_removed(self):
        self.assertEqual(['ok'], entries_added_since(set(), {'.', '..', "find: '/x/y': No such file", 'ok'}))
        for name in ('', '.', '..', 'a/b', '/etc', 'a\x00b', None):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    build_entry_removal_command('/home/example.com/public_html', name)

    def test_a_removal_names_one_entry_inside_the_directory_and_no_option(self):
        for name in ('wp-admin', '-rf', "it's", 'a b', '$(id)', '*'):
            command = build_entry_removal_command('/home/example.com/public html/', name)
            self.assertEqual(['rm', '-rf', '--', '/home/example.com/public html/' + name], shlex.split(command))


class WordPressCliCommandTests(unittest.TestCase):
    PHP = '/usr/local/lsws/lsphp83/bin/php'

    def test_every_value_is_one_argument_and_no_plugin_or_theme_is_loaded(self):
        for value in ('source.example', 'a b', "it's", '$(id)', '`id`', 'x; rm -rf /', '"quoted"'):
            command = wordpress_cli_command(self.PHP, '/home/new.example/public_html/', 'search-replace', value,
                                            'new.example')
            self.assertEqual([self.PHP, '-d', 'error_reporting=0', '-d', 'memory_limit=350M', '-d',
                              'max_execution_time=400', '/usr/bin/wp', 'search-replace', value, 'new.example',
                              '--skip-plugins', '--skip-themes', '--path=/home/new.example/public_html/'],
                             shlex.split(command), repr(value))

    def test_the_table_prefix_is_a_plain_name(self):
        command = wordpress_table_prefix_command(self.PHP, '/home/x/public_html/', 'wp_7a_')
        self.assertIn(' config set table_prefix wp_7a_ --type=variable ', command)
        for prefix in ('', 'wp-', 'wp_; id', "wp_'", 'a' * 65, None, 7):
            with self.subTest(prefix=prefix):
                with self.assertRaises(ValueError):
                    wordpress_table_prefix_command(self.PHP, '/home/x/public_html/', prefix)

    def test_a_value_is_exactly_one_line_of_output(self):
        self.assertEqual('newdb', single_line_value('newdb\n'))
        self.assertEqual(' p a$$ ', single_line_value(' p a$$ \n'))
        for output in ('', '\n', None, 'Warning: x\nnewdb\n', 'a\rb'):
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    single_line_value(output)


if __name__ == '__main__':
    unittest.main()
