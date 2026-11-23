"""install.py enables the panel's service only for a caller that does not do it itself.

A panel without an administrator creates "admin" with a well-known password on
the first request it gets. cyberpanel.sh therefore enables and starts the
panel's service only once the administrator's password is confirmed, and tells
install.py so with CP_PANEL_ENABLED_BY_SCRIPT=1. Every other caller (older
scripts that only restart the service) still gets it enabled by install.py.
"""
import ast
import os
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'install' / 'install.py'


def load_helper():
    tree = ast.parse(INSTALLER.read_text(encoding='utf-8'))
    selected = [node for node in tree.body
                if (isinstance(node, ast.FunctionDef) and node.name == 'panel_enabled_by_script')
                or (isinstance(node, ast.Assign)
                    and any(getattr(target, 'id', '') == 'PANEL_ENABLED_BY_SCRIPT' for target in node.targets))]
    namespace = {'os': os}
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module, str(INSTALLER), 'exec'), namespace)
    return namespace


def lscpd_enables(tree):
    """Every call that enables the panel's service, with the If nodes around it."""
    found = []

    def walk(node, conditions):
        for child in ast.iter_child_nodes(node):
            inner = conditions
            if isinstance(node, ast.If) and child in node.body:
                inner = conditions + [('if', node.test)]
            elif isinstance(node, ast.If) and child in node.orelse:
                inner = conditions + [('else', node.test)]
            if (isinstance(child, ast.Call) and getattr(child.func, 'attr', '') == 'manage_service'
                    and [getattr(argument, 's', getattr(argument, 'value', None)) for argument in child.args]
                    == ['lscpd', 'enable']):
                found.append((child, inner))
            walk(child, inner)

    walk(tree, [])
    return found


class PanelServiceTests(unittest.TestCase):
    def test_only_the_value_1_means_that_the_script_enables_the_panel(self):
        helper = load_helper()
        self.assertEqual('CP_PANEL_ENABLED_BY_SCRIPT', helper['PANEL_ENABLED_BY_SCRIPT'])
        decide = helper['panel_enabled_by_script']
        self.assertTrue(decide({'CP_PANEL_ENABLED_BY_SCRIPT': '1'}))
        for environment in ({}, {'CP_PANEL_ENABLED_BY_SCRIPT': ''}, {'CP_PANEL_ENABLED_BY_SCRIPT': '0'},
                            {'CP_PANEL_ENABLED_BY_SCRIPT': 'yes'}, {'CP_PANEL_ENABLED_BY_SCRIPT': ' 1'}):
            with self.subTest(environment=environment):
                self.assertFalse(decide(environment))

    def test_the_process_environment_is_read_when_none_is_given(self):
        decide = load_helper()['panel_enabled_by_script']
        saved = os.environ.get('CP_PANEL_ENABLED_BY_SCRIPT')
        try:
            os.environ['CP_PANEL_ENABLED_BY_SCRIPT'] = '1'
            self.assertTrue(decide())
            del os.environ['CP_PANEL_ENABLED_BY_SCRIPT']
            self.assertFalse(decide())
        finally:
            if saved is None:
                os.environ.pop('CP_PANEL_ENABLED_BY_SCRIPT', None)
            else:
                os.environ['CP_PANEL_ENABLED_BY_SCRIPT'] = saved

    def test_the_only_enable_of_the_panel_is_for_a_caller_that_does_not_do_it_itself(self):
        source = INSTALLER.read_text(encoding='utf-8')
        enables = lscpd_enables(ast.parse(source))
        self.assertEqual(1, len(enables))
        call, conditions = enables[0]
        self.assertEqual(1, len(conditions))
        kind, test = conditions[0]
        self.assertEqual('if', kind)
        self.assertIsInstance(test, ast.UnaryOp)
        self.assertIsInstance(test.op, ast.Not)
        self.assertEqual('panel_enabled_by_script', getattr(test.operand.func, 'id', ''))
        self.assertEqual([], test.operand.args)
        # No other way of enabling or starting the service by a command line.
        # The one such command line in the file is never run: the call that
        # would run it is a comment.
        lines = source.splitlines()
        found = [number for number, line in enumerate(lines)
                 if re.search(r"systemctl (?:enable|start|restart|reenable)\s+lscpd['\"]", line)]
        self.assertEqual(1, len(found))
        self.assertEqual("command = 'systemctl start lscpd'", lines[found[0]].strip())
        self.assertTrue(lines[found[0] + 1].strip().startswith('# preFlightsChecks.call(command'))

    def test_the_script_tells_install_py_in_both_ways_of_calling_it(self):
        script = (ROOT / 'cyberpanel.sh').read_text(encoding='utf-8')
        calls = [line.strip() for line in script.splitlines()
                 if re.search(r'/usr/local/CyberPanel/bin/python install\.py', line)]
        self.assertEqual(2, len(calls))
        self.assertIn('CP_INSTALL_MYSQL_PASSWORD="$MySQL_Password" CP_PANEL_ENABLED_BY_SCRIPT=1 \\', script)
        self.assertIn('  CP_PANEL_ENABLED_BY_SCRIPT=1 /usr/local/CyberPanel/bin/python install.py "${Final_Flags[@]}"\n',
                      script)


if __name__ == '__main__':
    unittest.main()
