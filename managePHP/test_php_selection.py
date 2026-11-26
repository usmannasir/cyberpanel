"""The one check of a PHP selection, and the names that are built from its digits."""
import os
from pathlib import Path
import tempfile
import unittest

from managePHP.phpConfig import (fpm_service_for_selection, normalized_php_selection, php_selection_digits,
                                  require_installed_php, stored_php_selection)

# Every version a page or an installer of the panel offers, and a two-digit
# minor number as findPHPVersions would report it for /usr/local/lsws/lsphp810.
OFFERED = ['PHP %s' % version for version in (
    '5.3', '5.4', '5.5', '5.6', '7.0', '7.1', '7.2', '7.3', '7.4',
    '8.0', '8.1', '8.2', '8.3', '8.4', '8.5', '8.10')]

# Texts that are not a selection. Several of them were turned into a service
# name or a path by the code that only removed spaces or dots.
NOT_A_SELECTION = (
    'PHP 8.3\tmulti-user.target', 'PHP 8.3\rmulti-user.target', 'PHP 8.3\n', '\nPHP 8.3',
    'PHP 8.3 --no-block', 'PHP 8.3 sshd', 'PHP  8.3', ' PHP 8.3', 'PHP 8.3 ', 'PHP\t8.3',
    'php 8.3', 'PHP8.3', 'PHP 8.3.1', 'PHP 8.', 'PHP .3', 'PHP 8', 'PHP 08.3', 'PHP 8.03',
    'PHP 8.300', 'PHP 8.3-fpm', 'PHP 8.3;id', 'PHP ../../etc', 'PHP 8.3/../..', 'PHP $(id)',
    'PHP \u0668.\u0663', 'PHP 8\u200b.3', 'latest', '8.3', '', None, 83, 8.3, True,
    ['PHP 8.3'], {'PHP 8.3': 1}, b'PHP 8.3')

# How earlier releases also wrote a version in storage, in backups and on the
# command line, and the selection each one stands for.
OLDER_SPELLINGS = {
    'PHP 74': 'PHP 7.4', 'php 7.4': 'PHP 7.4', 'PHP  7.4': 'PHP 7.4', '7.4': 'PHP 7.4', '74': 'PHP 7.4',
    'Php 8.3': 'PHP 8.3', 'PHP8.3': 'PHP 8.3', 'php83': 'PHP 8.3', 'PHP 80': 'PHP 8.0', '56': 'PHP 5.6',
    'PHP 810': 'PHP 8.10', '810': 'PHP 8.10', '8.10': 'PHP 8.10', 'PHP  8.3': 'PHP 8.3', 'php 8.3': 'PHP 8.3',
    '8.3': 'PHP 8.3',
}
# Still no version in any spelling.
NOT_A_SPELLING = ('7', 'PHP 7', 'PHP', '7.4.1', '7405', '704', 'PHP 7.04', '07.4', 'PHP 7.4 ', ' 7.4', '7.4\n',
                  'PHP\t7.4', 'PHP 7 4', 'PHP 7,4', 'v7.4', 'PHP-7.4', 'lsphp74', 'PHP 7.x', 74, 7.4)


class PHPSelectionTests(unittest.TestCase):
    def test_every_offered_version_is_a_selection(self):
        for selection in OFFERED:
            with self.subTest(selection=selection):
                major, minor = php_selection_digits(selection)
                self.assertEqual(selection, 'PHP %s.%s' % (major, minor))
                self.assertTrue((major + minor).isdigit())

    def test_anything_else_is_refused(self):
        for value in NOT_A_SELECTION:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid PHP version'):
                    php_selection_digits(value)

    def test_an_older_spelling_becomes_the_selection_it_stands_for(self):
        for spelling, selection in OLDER_SPELLINGS.items():
            with self.subTest(spelling=spelling):
                self.assertEqual(selection, normalized_php_selection(spelling))

    def test_a_selection_is_its_own_normal_form(self):
        for selection in OFFERED:
            self.assertEqual(selection, normalized_php_selection(selection))

    def test_the_normal_form_always_passes_the_one_check(self):
        for spelling in OLDER_SPELLINGS:
            php_selection_digits(normalized_php_selection(spelling))

    def test_text_that_is_no_version_in_any_spelling_is_refused(self):
        for value in NOT_A_SPELLING + tuple(value for value in NOT_A_SELECTION
                                            if not (isinstance(value, str) and value in OLDER_SPELLINGS)):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid PHP version'):
                    normalized_php_selection(value)

    def test_the_strict_check_still_refuses_the_older_spellings(self):
        for spelling, selection in OLDER_SPELLINGS.items():
            with self.subTest(spelling=spelling):
                with self.assertRaisesRegex(ValueError, 'Invalid PHP version'):
                    php_selection_digits(spelling)

    def test_fpm_service_is_built_from_the_digits(self):
        for selection in OFFERED:
            major, minor = php_selection_digits(selection)
            with self.subTest(selection=selection):
                self.assertEqual('php%s%s-php-fpm' % (major, minor), fpm_service_for_selection(selection, True))
                self.assertEqual('php%s.%s-fpm' % (major, minor), fpm_service_for_selection(selection, False))

    def test_fpm_service_keeps_the_names_used_before(self):
        self.assertEqual('php74-php-fpm', fpm_service_for_selection('PHP 7.4', True))
        self.assertEqual('php8.3-fpm', fpm_service_for_selection('PHP 8.3', False))

    def test_no_service_name_for_anything_else(self):
        for value in NOT_A_SELECTION:
            for rpm_family in (True, False):
                with self.subTest(value=value, rpm_family=rpm_family):
                    with self.assertRaises(ValueError):
                        fpm_service_for_selection(value, rpm_family)


class StoredSelectionTests(unittest.TestCase):
    def test_a_stored_older_spelling_gets_the_panels_form(self):
        self.assertEqual('PHP 7.4', stored_php_selection('PHP 74'))
        self.assertEqual('PHP 8.1', stored_php_selection('php 8.1'))

    def test_a_stored_value_without_such_a_form_goes_on_as_it_is(self):
        # The worker refuses it for that one website; the caller's loop goes on.
        for value in ('PHP seven', '', None, 'PHP 8.3; x'):
            self.assertIs(value, stored_php_selection(value))


def lsphp_root(testcase, installed=(), extensions_only=()):
    """A LiteSpeed root in a temporary folder: complete versions and versions with only extension packages.

    A version with only extension packages is what the installer left on
    AlmaLinux 10 for PHP 8.6: lsphp86 with php-config and the extension
    folders, without lsphp and php.
    """
    folder = tempfile.TemporaryDirectory()
    testcase.addCleanup(folder.cleanup)
    root = Path(folder.name)
    for digits in installed:
        for name in ('lsphp', 'php', 'php-config'):
            program = root / ('lsphp' + digits) / 'bin' / name
            program.parent.mkdir(parents=True, exist_ok=True)
            program.write_text('#!/bin/sh\n')
            program.chmod(0o755)
    for digits in extensions_only:
        (root / ('lsphp' + digits) / 'etc' / 'php.d').mkdir(parents=True)
        program = root / ('lsphp' + digits) / 'bin' / 'php-config'
        program.parent.mkdir(parents=True, exist_ok=True)
        program.write_text('#!/bin/sh\n')
        program.chmod(0o755)
    return str(root)


class InstalledPHPTests(unittest.TestCase):
    def test_an_installed_version_passes(self):
        root = lsphp_root(self, installed=('83', '85', '810'))
        for selection in ('PHP 8.3', 'PHP 8.5', 'PHP 8.10'):
            with self.subTest(selection=selection):
                self.assertIsNone(require_installed_php(selection, server_root=root))

    def test_a_version_with_only_extension_packages_is_refused(self):
        root = lsphp_root(self, installed=('85',), extensions_only=('86',))
        with self.assertRaisesRegex(ValueError, r'^PHP 8\.6 is not installed on this server\.$'):
            require_installed_php('PHP 8.6', server_root=root)

    def test_a_version_without_its_folder_is_refused(self):
        root = lsphp_root(self, installed=('85',))
        for selection in ('PHP 7.4', 'PHP 8.4', 'PHP 8.1'):
            with self.subTest(selection=selection):
                with self.assertRaisesRegex(ValueError, 'is not installed on this server'):
                    require_installed_php(selection, server_root=root)

    def test_php_without_lsphp_is_not_enough(self):
        # The web server starts lsphp; a command-line php alone runs no website.
        root = lsphp_root(self, installed=('84',))
        os.remove(os.path.join(root, 'lsphp84', 'bin', 'lsphp'))
        with self.assertRaisesRegex(ValueError, 'PHP 8.4 is not installed'):
            require_installed_php('PHP 8.4', server_root=root)

    def test_an_lsphp_that_cannot_run_is_refused(self):
        root = lsphp_root(self, installed=('84', '83'))
        os.chmod(os.path.join(root, 'lsphp84', 'bin', 'lsphp'), 0o644)
        program = os.path.join(root, 'lsphp83', 'bin', 'lsphp')
        os.remove(program)
        os.mkdir(program)
        for selection in ('PHP 8.4', 'PHP 8.3'):
            with self.subTest(selection=selection):
                with self.assertRaisesRegex(ValueError, 'is not installed on this server'):
                    require_installed_php(selection, server_root=root)

    def test_text_that_is_no_selection_is_refused_as_before(self):
        root = lsphp_root(self, installed=('83',))
        for value in NOT_A_SELECTION:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid PHP version'):
                    require_installed_php(value, server_root=root)

    def test_the_default_root_is_the_web_servers(self):
        self.assertEqual('/usr/local/lsws', require_installed_php.__defaults__[0])


if __name__ == '__main__':
    unittest.main()
