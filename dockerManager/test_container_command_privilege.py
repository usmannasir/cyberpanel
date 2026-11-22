"""A command run from the container page gets the container's own privileges, never the server's."""
import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / 'container.py'


class CommandPrivilegeTests(unittest.TestCase):
    def exec_calls(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        return [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr in ('exec_run', 'exec_create')]

    def test_commands_are_run_inside_containers(self):
        self.assertTrue(self.exec_calls())

    def test_no_command_is_run_with_the_privileged_flag(self):
        for call in self.exec_calls():
            for keyword in call.keywords:
                if keyword.arg == 'privileged':
                    # ast.Constant on current Python, ast.NameConstant on Python 3.6.
                    value = getattr(keyword.value, 'value', None)
                    self.assertIs(False, value, 'line %s' % call.lineno)


if __name__ == '__main__':
    unittest.main(verbosity=2)
