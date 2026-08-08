# -*- coding: utf-8 -*-


from django.test import SimpleTestCase

from managePHP.phpConfig import matches_directive


class PHPDirectiveMatchingTests(SimpleTestCase):
    def test_memory_limit_matches_exact_directive(self):
        self.assertTrue(matches_directive('memory_limit = 128M', 'memory_limit'))
        self.assertTrue(matches_directive('  MEMORY_LIMIT=256M', 'memory_limit'))

    def test_memory_limit_does_not_match_php_85_maximum(self):
        self.assertFalse(matches_directive('max_memory_limit = 256M', 'memory_limit'))
        self.assertFalse(matches_directive('; memory_limit = 128M', 'memory_limit'))
