import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

from baseTemplate.themeCatalog import fetch_theme_catalog


class ThemeCatalogTests(unittest.TestCase):
    def response(self, payload):
        return SimpleNamespace(raise_for_status=Mock(), json=lambda: payload)

    def test_valid_catalog_and_bounded_timeouts(self):
        get = Mock(side_effect=[self.response([{'sha': 'a' * 40}]), self.response({'tree': [
            {'type': 'tree', 'path': 'dark'}, {'type': 'blob', 'path': 'README'}, None, {'type': 'tree'}]})])
        self.assertEqual(fetch_theme_catalog(get), ['dark'])
        self.assertEqual([call.kwargs['timeout'] for call in get.call_args_list], [(3, 5), (3, 5)])

    def test_invalid_commit_responses(self):
        for payload in ([], {}, {'message': 'API rate limit exceeded'}, [None], [{'sha': '../bad'}]):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                fetch_theme_catalog(Mock(return_value=self.response(payload)))

    def test_invalid_tree_response(self):
        for payload in ([], {}, {'tree': None}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                fetch_theme_catalog(Mock(side_effect=[self.response([{'sha': 'a' * 40}]), self.response(payload)]))

    def test_http_errors_are_not_parsed_as_catalog(self):
        response = self.response({'message': 'rate limited'})
        response.raise_for_status.side_effect = RuntimeError('HTTP 403')
        with self.assertRaises(RuntimeError):
            fetch_theme_catalog(Mock(return_value=response))

    def test_actual_design_view_renders_and_saves_local_css_when_catalog_fails(self):
        # Execute the production view with isolated models/rendering; no customer DB writes.
        tree = ast.parse(Path(__file__).with_name('views.py').read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'design')
        function.decorator_list = []
        cosmetic = SimpleNamespace(MainDashboardCSS='old dark CSS', save=Mock())
        model = Mock()
        model.objects.get.return_value = cosmetic
        namespace = {
            'ACLManager': SimpleNamespace(loadedACL=lambda value: {'admin': 1}),
            'requests': SimpleNamespace(get=Mock(side_effect=TimeoutError('timed out'))),
            'logging': SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=Mock())),
            'httpProc': lambda request, template, data, permission: SimpleNamespace(render=lambda: data),
        }
        with patch.dict(sys.modules, {'baseTemplate.models': SimpleNamespace(CyberPanelCosmetic=model)}):
            exec(compile(ast.Module(body=[function], type_ignores=[]), 'design-view', 'exec'), namespace)
            for method in ('GET', 'POST'):
                request = SimpleNamespace(session={'userID': 1}, method=method, POST={'MainDashboardCSS': ''})
                result = namespace['design'](request)
                self.assertTrue(result['theme_catalog_unavailable'])
                self.assertEqual(result['tree'], [])
                self.assertIs(result['cosmetic'], cosmetic)
            self.assertEqual(cosmetic.MainDashboardCSS, '')
            cosmetic.save.assert_called_once()
            self.assertEqual(result['saved'], 1)
