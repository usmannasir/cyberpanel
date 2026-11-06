"""Run with the legacy /usr/libexec/platform-python as well as current Python.

Execute the owning upgrader's validator and native helper without importing
Django or changing a server. Real subprocess calls reproduce the 3.6 failure.
"""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class LegacyValidatorTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('upgrade.py')
        tree = ast.parse(path.read_text())
        wanted = {'OLSUpgradeFailure', 'load_ols_diagnostic_helper', 'validate_ols_configuration'}
        nodes = [node for node in tree.body if getattr(node, 'name', '') in wanted]
        self.assertEqual(len(nodes), 3)
        namespace = {'__file__': str(path), 'os': os}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
        self.validate = namespace['validate_ols_configuration']
        self.failure = namespace['OLSUpgradeFailure']
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.binary = Path(self.temporary.name) / 'bin/openlitespeed'
        self.binary.parent.mkdir()

    def program(self, content):
        self.binary.write_text('#!/bin/sh\n' + content + '\n')
        self.binary.chmod(0o700)

    def test_real_subprocess_success_on_legacy_runtime(self):
        self.program('printf "Syntax OK\\n"; exit 0')
        self.assertIn('Syntax OK', self.validate(str(self.binary)))

    def test_native_error_with_zero_exit_still_fails_closed(self):
        self.program('printf "[ERROR] invalid configuration\\n" >&2; exit 0')
        with self.assertRaises(self.failure):
            self.validate(str(self.binary))

    def test_nonzero_native_failure_is_preserved(self):
        self.program('printf "invalid configuration\\n" >&2; exit 2')
        with self.assertRaises(self.failure):
            self.validate(str(self.binary))

    def test_reported_legacy_keyword_failure_is_reproduced(self):
        if sys.version_info < (3, 7):
            with self.assertRaises(TypeError):
                subprocess.run(['/bin/true'], capture_output=True, text=True)
        else:
            self.assertEqual(0, subprocess.run(['/bin/true'], capture_output=True, text=True).returncode)


if __name__ == '__main__':
    unittest.main()
