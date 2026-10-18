"""Literal upload punctuation stays quoted; unsafe command/path input stays blocked."""
import ast
from pathlib import Path
import shlex
import unittest


def load_function(path, name, environment):
    tree = ast.parse(Path(path).read_text())
    node = next(node for cls in tree.body if isinstance(cls, ast.ClassDef)
                for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), environment)
    return environment[name]


class UploadNamesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {}
        check = load_function('plogical/acl.py', 'commandInjectionCheck', env)
        env['ACLManager'] = type('ACL', (), {'commandInjectionCheck': staticmethod(check)})
        cls.safe = staticmethod(load_function('filemanager/filemanager.py', 'safeUploadPath', env))
        cls.quote = staticmethod(load_function('filemanager/filemanager.py', 'returnPathEnclosed', env))
        cls.inside = staticmethod(load_function('filemanager/filemanager.py', 'pathInside', {'os': __import__('os')}))
        cls.outside = staticmethod(load_function('filemanager/filemanager.py', 'notInside', {}))

    def test_human_filename_punctuation_is_one_literal_argument(self):
        for name in ["report's.txt", 'report (final).txt', 'café.txt', 'report final.txt', 'a"b.txt']:
            with self.subTest(name=name):
                path = '/home/fixture.example/public_html/' + name
                self.assertTrue(self.safe(path))
                self.assertEqual(['cp', '--', '/tmp/fixture', path],
                    shlex.split('cp -- /tmp/fixture ' + self.quote(None, path)))

    def test_command_separators_and_protocol_controls_remain_rejected(self):
        for name in ['a;b', 'a&&b', 'a|b', 'a`id`', 'a$(id)', 'a[0]', 'a{b}',
                     'a:b', 'a<b', 'a>b', 'a&b', 'a...b', 'a\nb', 'a\rb', 'a\x00b']:
            with self.subTest(name=name):
                self.assertFalse(self.safe('/home/fixture.example/' + name))

    def test_containment_gate_still_rejects_escapes(self):
        manager = type('Manager', (), {'pathInside': self.inside})()
        for path in ['/home/fixture.example/../other/file', '/home/other/file', '/home/fixture.example.evil/file']:
            self.assertTrue(self.outside(manager, path, '/home/fixture.example'))
        self.assertFalse(self.outside(manager, "/home/fixture.example/report's (final).txt", '/home/fixture.example'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
