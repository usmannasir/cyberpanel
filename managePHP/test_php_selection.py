"""The one check of a PHP selection, and the names that are built from its digits."""
import unittest

from managePHP.phpConfig import fpm_service_for_selection, php_selection_digits

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


if __name__ == '__main__':
    unittest.main()
