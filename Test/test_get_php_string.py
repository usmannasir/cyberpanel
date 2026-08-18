#!/usr/bin/env python3
"""Focused tests for ACLManager.getPHPString (PR review: PHP 8.6, 9.0, 8.10, malformed)."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def load_get_php_string():
    """Load getPHPString from plogical/acl.py without requiring Django/MySQL."""
    path = os.path.join(ROOT, 'plogical', 'acl.py')
    with open(path, 'r', encoding='utf-8') as fh:
        src = fh.read()
    start = src.index('    def getPHPString')
    end = src.index('\n    @staticmethod', start + 1)
    body = src[start:end]
    lines = []
    for line in body.splitlines():
        if line.startswith('    '):
            lines.append(line[4:])
        else:
            lines.append(line)
    code = 'from re import search\n' + '\n'.join(lines) + '\n'
    namespace = {}
    exec(code, namespace)
    return namespace['getPHPString']


GET_PHP_STRING = load_get_php_string()


class GetPHPStringTests(unittest.TestCase):

    def test_explicit_php_85(self):
        self.assertEqual(GET_PHP_STRING('PHP 8.5'), '85')

    def test_php_86_fallback(self):
        self.assertEqual(GET_PHP_STRING('PHP 8.6'), '86')

    def test_php_90_fallback(self):
        self.assertEqual(GET_PHP_STRING('PHP 9.0'), '90')

    def test_php_810_is_810_not_last_two_digits(self):
        self.assertEqual(GET_PHP_STRING('PHP 8.10'), '810')
        self.assertNotEqual(GET_PHP_STRING('PHP 8.10'), '10')

    def test_malformed_falls_back_to_85(self):
        self.assertEqual(GET_PHP_STRING('not-a-version'), '85')
        self.assertEqual(GET_PHP_STRING(''), '85')
        self.assertEqual(GET_PHP_STRING(None), '85')

    def test_source_uses_1834_major_minor_regex(self):
        path = os.path.join(ROOT, 'plogical', 'acl.py')
        with open(path, 'r', encoding='utf-8') as fh:
            src = fh.read()
        self.assertIn(r'\d+\.\d+', src)
        self.assertNotIn("digits[-2:]", src)


if __name__ == '__main__':
    unittest.main()
