"""The counters that limit container commands are kept where only the panel can write."""
import ast
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parent / 'container.py'


def load(directory):
    """The real method and the real constant, without the rest of the module."""
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    constant = next(node for node in tree.body if isinstance(node, ast.Assign)
                    and getattr(node.targets[0], 'id', None) == 'RATE_LIMIT_DIRECTORY')
    manager = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ContainerManager')
    method = next(node for node in manager.body if isinstance(node, ast.FunctionDef)
                  and node.name == '_check_rate_limit')
    scope = {'logging': mock.Mock()}
    exec(compile(ast.Module(body=[constant, method], type_ignores=[]), 'container.py', 'exec'), scope)
    configured = scope['RATE_LIMIT_DIRECTORY']
    scope['RATE_LIMIT_DIRECTORY'] = directory
    return scope['_check_rate_limit'], configured


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.parent = tempfile.mkdtemp(prefix='docker-rate-limit-')
        self.addCleanup(shutil.rmtree, self.parent)
        self.directory = os.path.join(self.parent, 'counters')
        self.check, self.configured = load(self.directory)

    def test_the_counters_are_in_the_panels_own_directory(self):
        self.assertEqual('/home/cyberpanel/docker_rate_limit', self.configured)
        self.assertNotIn('/tmp', SOURCE.read_text(encoding='utf-8').split('def _check_rate_limit')[1]
                         .split('def _log_command_execution')[0].replace('such as /tmp', ''))

    def test_the_directory_is_made_for_the_panel_alone(self):
        previous = os.umask(0)
        self.addCleanup(os.umask, previous)
        self.assertTrue(self.check(None, 7, 'web'))
        self.assertEqual(0o700, stat.S_IMODE(os.stat(self.directory).st_mode))
        self.assertEqual(['user_7_container_web'], os.listdir(self.directory))

    def test_ten_commands_a_minute_as_before(self):
        self.assertEqual([True] * 10 + [False, False], [self.check(None, 7, 'web') for _ in range(12)])
        self.assertTrue(self.check(None, 8, 'web'))
        self.assertTrue(self.check(None, 7, 'db'))

    def test_a_name_cannot_lead_out_of_the_directory(self):
        for name in ('../../outside', '/etc/cron.d/x', 'a/b', '..', 'web\x00x'):
            with self.subTest(name=name):
                self.assertTrue(self.check(None, 7, name))
        self.assertEqual(['counters'], os.listdir(self.parent))
        for entry in os.listdir(self.directory):
            self.assertTrue(os.path.isfile(os.path.join(self.directory, entry)), entry)
        self.assertEqual(5, len(os.listdir(self.directory)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
