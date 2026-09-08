# -*- coding: utf-8 -*-


from django.test import SimpleTestCase

from managePHP.phpConfig import fpm_service_for_ini, matches_directive


class PHPDirectiveMatchingTests(SimpleTestCase):
    def test_memory_limit_matches_exact_directive(self):
        self.assertTrue(matches_directive('memory_limit = 128M', 'memory_limit'))
        self.assertTrue(matches_directive('  MEMORY_LIMIT=256M', 'memory_limit'))

    def test_memory_limit_does_not_match_php_85_maximum(self):
        self.assertFalse(matches_directive('max_memory_limit = 256M', 'memory_limit'))
        self.assertFalse(matches_directive('; memory_limit = 128M', 'memory_limit'))


class FPMServiceSelectionTests(SimpleTestCase):
    def test_managed_fpm_paths_select_their_version(self):
        for version in ('7.4', '8.3', '8.5'):
            with self.subTest(version=version, layout='debian'):
                self.assertEqual('php%s-fpm' % version,
                                 fpm_service_for_ini('/etc/php/%s/fpm/php.ini' % version))
            compact = version.replace('.', '')
            with self.subTest(version=version, layout='remi'):
                self.assertEqual('php%s-php-fpm' % compact,
                                 fpm_service_for_ini('/etc/opt/remi/php%s/php.ini' % compact))

    def test_non_fpm_paths_do_not_select_a_service(self):
        for path in (
                '/usr/local/lsws/lsphp83/etc/php.ini',
                '/usr/local/lsws/lsphp83/etc/php/8.3/litespeed/php.ini',
                '/etc/php/8.3/cli/php.ini',
                '/etc/php/8.3/fpm/php.ini.backup',
                '/etc/opt/remi/php83/php.ini.backup',
                '/etc/php/8.3/fpm/php.ini\n',
                '/etc/opt/remi/php83;other/php.ini'):
            with self.subTest(path=path):
                self.assertIsNone(fpm_service_for_ini(path))
