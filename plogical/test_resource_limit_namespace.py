"""Keep cgroup bootstrap from implicitly enabling server-wide namespaces."""
import ast
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS
import unittest
from unittest import mock


class ResourceLimitNamespaceTests(unittest.TestCase):
    def bootstrap(self, retry=False, fail=False, configured=False):
        tree = ast.parse(Path(__file__).with_name('resourceLimits.py').read_text())
        method = next(n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name == '_ensure_cgroups_enabled')
        missing = 'You must configure LiteSpeed for LiteSpeed Containers'
        success = NS(returncode=0, stdout='', stderr='')
        unconfigured = NS(returncode=1, stdout='', stderr=missing)
        results = [success] if configured else [unconfigured, success,
                    unconfigured if retry else success]
        if retry:
            results.extend([success, unconfigured if fail else success])
        run = mock.Mock(side_effect=results)
        logger = mock.Mock()
        scope = {'os': NS(path=NS(exists=lambda path: True)),
                 'subprocess': NS(run=run, PIPE=subprocess.PIPE),
                 'time': NS(sleep=mock.Mock()),
                 'logging': NS(writeToFile=logger)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'resource-limits', 'exec'), scope)
        manager = NS(_initialized=False, LSCGCTL_PATH='/fixture/lscgctl',
                     LSSETUP_PATH='/fixture/lssetup',
                     _check_rhel8_cgroups_v2=lambda: True,
                     _check_ols_cgroups_enabled=lambda: True)
        result = scope['_ensure_cgroups_enabled'](manager)
        return result, [call.args[0] for call in run.call_args_list
                        if call.args[0][0] == manager.LSSETUP_PATH], logger

    def test_first_setup_initializes_namespace_off(self):
        result, commands, _ = self.bootstrap()
        self.assertTrue(result)
        self.assertEqual(commands, [['/fixture/lssetup', '-c', '2', '-n', '0',
                                     '-m', '0', '-s', '/usr/local/lsws']])

    def test_retry_also_initializes_namespace_off(self):
        result, commands, _ = self.bootstrap(retry=True)
        self.assertTrue(result)
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[1], ['/fixture/lssetup', '-c', '10', '-n', '0',
                                       '-m', '0', '-s', '/usr/local/lsws'])

    def test_manual_recovery_preserves_namespace_choice(self):
        result, _, logger = self.bootstrap(retry=True, fail=True)
        self.assertFalse(result)
        logger.assert_any_call('Please manually run: /usr/local/lsws/lsns/bin/lssetup '
                               '-c 10 -n 0 -m 0 -s /usr/local/lsws')

    def test_configured_containers_do_not_run_setup(self):
        result, commands, _ = self.bootstrap(configured=True)
        self.assertTrue(result)
        self.assertEqual(commands, [])
