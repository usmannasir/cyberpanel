"""The compact PHP version ('83') that becomes part of paths and command lines is digits or nothing."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP.test_php_selection import OFFERED

SOURCE = Path(__file__).with_name('phpManager.py')


def load_php_manager(names, **namespace):
    owner = next(node for node in ast.parse(SOURCE.read_text()).body
                 if isinstance(node, ast.ClassDef) and node.name == 'PHPManager')
    namespace.setdefault('re', re)
    for node in owner.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            node.decorator_list = []
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    manager = NS(**{name: namespace[name] for name in names})
    namespace['PHPManager'] = manager
    return manager


class PHPVersionStringTests(unittest.TestCase):
    def setUp(self):
        self.manager = load_php_manager(['getPHPString'])

    def test_offered_versions_keep_their_compact_form(self):
        for selection in OFFERED:
            self.assertEqual(selection[4:].replace('.', ''), self.manager.getPHPString(selection))

    def test_stored_selections_with_loose_spacing_still_resolve(self):
        # Rows written by earlier versions were never checked for spacing.
        for stored in ('PHP  8.3', ' PHP 8.3 ', 'php 8.3', 'PHP\t8.3'):
            self.assertEqual('83', self.manager.getPHPString(stored))

    def test_text_that_would_reach_a_path_or_command_is_refused(self):
        for stored in ('PHP $(id)', 'PHP 8.3;id', 'PHP ../../x', 'PHP 8.3/..', "PHP 8.3'", 'PHP 8.3"', 'P `id`',
                       'PHP 8', 'PHP 8.3.1.1', 'PHP \u0668.\u0663', 'PHP -8.3', 'PHP 8.3|x', 'PHP 8.3&'):
            with self.subTest(stored=stored):
                with self.assertRaisesRegex(ValueError, 'Invalid PHP version'):
                    self.manager.getPHPString(stored)


class StoredVersionOnPagesTests(unittest.TestCase):
    """ACLManager.getPHPString, which the WordPress pages use for the website's PHP command."""

    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'plogical' / 'acl.py'
        owner = next(node for node in ast.parse(source.read_text()).body
                     if isinstance(node, ast.ClassDef) and node.name == 'ACLManager')
        function = next(node for node in owner.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'getPHPString')
        function.decorator_list = []
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        self.compact = namespace['getPHPString']

    def test_offered_versions_keep_their_compact_form(self):
        for selection in OFFERED:
            self.assertEqual(selection[4:].replace('.', ''), self.compact(selection))

    def test_the_result_is_digits_whatever_is_stored(self):
        for stored in ('PHP 8.3;id', 'PHP $(id)', 'PHP ../../x', "PHP 8.3' x", 'PHP 8.3 -r', 'PHP 8.3/..',
                       'PHP \u0668.\u0663', '', 'latest'):
            with self.subTest(stored=stored):
                self.assertRegex(self.compact(stored), r'\A[0-9]*\Z')


class InstalledVersionListTests(unittest.TestCase):
    listing = '\n'.join('drwxr-xr-x 5 root root 4096 Nov 21 10:02 ' + name for name in (
        '.', '..', 'admin', 'conf', 'lsphp74', 'lsphp83', 'lsphp810', 'lsphp74.bak', 'lsphp83-old', 'lsphp8x'))

    def versions(self, installed):
        process = mock.Mock(debugPath='/nonexistent-debug-marker')
        process.outputExecutioner.return_value = self.listing
        paths = NS(exists=lambda path: path in installed)
        manager = load_php_manager(['getPHPString', 'findPHPVersions'], ProcessUtilities=process,
                                   os=NS(path=paths))
        return manager.findPHPVersions()

    def test_only_installed_lsphp_directories_are_offered(self):
        installed = {'/usr/local/lsws/lsphp%s/bin/lsphp' % version for version in ('74', '83', '810')}
        self.assertEqual(['PHP 7.4', 'PHP 8.3', 'PHP 8.10'], self.versions(installed))

    def test_a_copy_of_an_lsphp_directory_does_not_replace_the_list(self):
        # A name such as lsphp74.bak must be skipped, not turn the page's list
        # into the built-in list of every version.
        self.assertEqual(['PHP 8.3'], self.versions({'/usr/local/lsws/lsphp83/bin/lsphp'}))


if __name__ == '__main__':
    unittest.main()
