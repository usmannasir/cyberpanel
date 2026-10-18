"""Validate the installed lscgctl reset-user command contract and error handling."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import subprocess
import unittest
from unittest import mock


class ResourceLimitRemovalTests(unittest.TestCase):
    def call(self, result=None, error=None):
        tree = ast.parse(Path(__file__).with_name('resourceLimits.py').read_text())
        method = next(n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name == 'remove_user_limits')
        run = mock.Mock(return_value=result, side_effect=error)
        scope = {'os': NS(path=NS(exists=lambda path: True)),
                 'subprocess': NS(run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired),
                 'logging': NS(writeToFile=mock.Mock())}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'resource-limits', 'exec'), scope)
        value = scope['remove_user_limits'](NS(LSCGCTL_PATH='/fixture/lscgctl'), 'fixtureuser')
        self.assertEqual(['/fixture/lscgctl', 'reset-user', 'fixtureuser'], run.call_args[0][0])
        return value

    def test_success(self):
        self.assertTrue(self.call(NS(returncode=0)))

    def test_failure_is_reported(self):
        self.assertFalse(self.call(NS(returncode=1, stderr='failed', stdout='')))

    def test_timeout_is_reported(self):
        self.assertFalse(self.call(error=subprocess.TimeoutExpired('lscgctl', 10)))
