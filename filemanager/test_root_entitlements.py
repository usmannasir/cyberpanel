"""Root entitlement controls using actual methods and inert IO collaborators."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ('listForTable', 'list', 'createNewFile', 'createNewFolder',
    'deleteFolderOrFile', 'restore', 'copy', 'move', 'rename', 'readFileContents',
    'writeFileContents', 'upload', 'extract', 'compress', 'changePermissions')


def forbidden(*args, **kwargs):
    raise AssertionError('Unexpected IO in an entitlement control')


def load(path, env, names):
    tree = ast.parse((ROOT / path).read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), env)


class RootEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.acl = SimpleNamespace(CheckForPremFeature=Mock(return_value=0))
        self.process = SimpleNamespace(outputExecutioner=Mock(side_effect=forbidden),
            executioner=Mock(side_effect=forbidden))
        self.sites = SimpleNamespace(objects=SimpleNamespace(get=Mock(side_effect=LookupError)))
        self.env = {'ACLManager': self.acl, 'wraps': __import__('functools').wraps,
            'HttpResponse': lambda data, **kw: json.loads(data), 'json': json,
            'ProcessUtilities': self.process, 'Websites': self.sites}
        load('filemanager/rootEntitlements.py', self.env,
            ['require_root_entitlement', 'root_entitlement_required'])
        load('filemanager/filemanager.py', self.env, ['FileManager'])
        self.cls = self.env['FileManager']

    def test_every_root_operation_denies_before_work(self):
        for value in (0, True, '1', 1.0, None):
            self.acl.CheckForPremFeature.return_value = value
            for domain in ({}, {'domainName': ''}):
                for name in OPERATIONS:
                    with self.subTest(grant=value, data=domain, method=name):
                        result = getattr(self.cls(object(), domain), name)()
                        self.assertEqual(0, result['status'])
                        self.assertEqual('An active Root File Manager entitlement is required.', result['error_message'])
        self.sites.objects.get.assert_not_called()
        self.process.executioner.assert_not_called()
        self.process.outputExecutioner.assert_not_called()

    def test_lookup_exception_denies_root(self):
        self.acl.CheckForPremFeature.side_effect = TimeoutError
        self.assertEqual(0, self.cls(object(), {}).listForTable()['status'])
        self.process.outputExecutioner.assert_not_called()

    def test_free_site_listing_does_not_check_premium_entitlement(self):
        self.sites.objects.get.return_value = SimpleNamespace(externalApp='fixture-user')
        self.sites.objects.get.side_effect = None
        self.process.outputExecutioner.side_effect = None
        self.process.outputExecutioner.return_value = ''
        manager = self.cls(object(), {'domainName': 'fixture.invalid', 'completeStartingPath': '/home/fixture.invalid'})
        manager.notInside = Mock(return_value=False)
        result = manager.listForTable()
        self.assertEqual(1, result['status'])
        self.acl.CheckForPremFeature.assert_not_called()
        self.assertEqual('fixture-user', self.process.outputExecutioner.call_args.args[1])

    def test_failed_site_lookup_cannot_become_root_operation_even_with_a_license(self):
        self.acl.CheckForPremFeature.return_value = 1
        manager = self.cls(object(), {'domainName': 'missing.invalid', 'completeStartingPath': '/'})
        result = manager.listForTable()
        self.assertEqual(0, result['status'])
        self.assertEqual('Root operations require the root file manager.', result['error_message'])
        self.acl.CheckForPremFeature.assert_not_called()
        self.process.outputExecutioner.assert_not_called()

    def test_licensed_explicit_root_listing_still_works(self):
        self.acl.CheckForPremFeature.return_value = 1
        self.process.outputExecutioner.side_effect = None
        self.process.outputExecutioner.return_value = ''
        manager = self.cls(object(), {'domainName': '', 'completeStartingPath': '/'})
        manager.notInside = Mock(return_value=False)
        result = manager.listForTable()
        self.assertEqual(1, result['status'])
        self.assertEqual(1, len(self.process.outputExecutioner.call_args.args))
        self.assertTrue(all(call.args == ('Filemanager',) for call in self.acl.CheckForPremFeature.call_args_list))


if __name__ == '__main__':
    unittest.main(verbosity=2)
