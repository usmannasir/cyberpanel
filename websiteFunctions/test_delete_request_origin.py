"""A delete requested through a link is honoured only when this panel's own page sent it."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical.requestOrigin import confirmed_parameter, sent_by_this_panel

ROOT = Path(__file__).resolve().parents[1]
HOST = '203.0.113.10:8090'

# What a browser sends when another site, an image tag, a bookmark or a typed
# address makes the request, and what it sends from the panel's own pages.
FOREIGN = (
    {'HTTP_SEC_FETCH_SITE': 'cross-site'},
    {'HTTP_SEC_FETCH_SITE': 'same-site'},
    {'HTTP_SEC_FETCH_SITE': 'none'},
    {'HTTP_SEC_FETCH_SITE': ''},
    {'HTTP_SEC_FETCH_SITE': 'cross-site', 'HTTP_REFERER': 'https://%s/websites/ListWPSites' % HOST},
    {},
    {'HTTP_REFERER': ''},
    {'HTTP_REFERER': 'https://customer-site.example/page.html'},
    {'HTTP_REFERER': 'https://203.0.113.10/hosted-site/'},
    {'HTTP_REFERER': 'https://203.0.113.10:8090.attacker.example/'},
    {'HTTP_REFERER': 'not a url'},
)
OWN = (
    {'HTTP_SEC_FETCH_SITE': 'same-origin'},
    {'HTTP_SEC_FETCH_SITE': 'same-origin', 'HTTP_REFERER': 'https://elsewhere.example/'},
    {'HTTP_REFERER': 'https://%s/websites/ListWPSites' % HOST},
    {'HTTP_REFERER': 'http://%s/' % HOST},
)


def request(meta, **query):
    return SimpleNamespace(META=dict(meta), GET=dict(query), session={'userID': 7},
                           get_host=lambda: HOST)


class RequestOriginTests(unittest.TestCase):
    def test_only_the_panels_own_pages_count_as_this_panel(self):
        for meta in FOREIGN:
            self.assertFalse(sent_by_this_panel(request(meta)), meta)
        for meta in OWN:
            self.assertTrue(sent_by_this_panel(request(meta)), meta)

    def test_parameter_is_returned_only_for_the_panels_own_request(self):
        for meta in FOREIGN:
            self.assertIsNone(confirmed_parameter(request(meta, DeleteID='5'), 'DeleteID'), meta)
        for meta in OWN:
            self.assertEqual('5', confirmed_parameter(request(meta, DeleteID='5'), 'DeleteID'), meta)
            self.assertIsNone(confirmed_parameter(request(meta), 'DeleteID'), meta)

    def test_host_that_cannot_be_determined_confirms_nothing(self):
        def no_host():
            raise ValueError('Invalid HTTP_HOST header')
        asked = SimpleNamespace(META={'HTTP_REFERER': 'https://%s/' % HOST}, GET={'DeleteID': '5'},
                                get_host=no_host)
        self.assertIsNone(confirmed_parameter(asked, 'DeleteID'))


class DeleteViewTests(unittest.TestCase):
    # view -> (manager method, position of the delete argument in its call)
    VIEWS = {'ListWPSites': ('ListWPSites', 2), 'WPHome': ('WPHome', 3),
             'RemoteBackupConfig': ('RemoteBackupConfig', 2), 'BackupfileConfig': ('BackupfileConfig', 3),
             'AddRemoteBackupsite': ('AddRemoteBackupsite', 3), 'RestoreBackups': ('RestoreBackups', 2),
             'CreateDockerPackage': ('CreateDockerPackage', 3), 'AssignPackage': ('AssignPackage', 3),
             'ListDockerSites': ('ListDockerSites', 3)}

    def setUp(self):
        tree = ast.parse((ROOT / 'websiteFunctions/views.py').read_text())
        self.functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.manager = Mock()
        self.plugins = Mock()
        self.namespace = dict(
            WebsiteManager=lambda: self.manager, confirmed_parameter=confirmed_parameter,
            Administrator=Mock(), wpplugins=self.plugins, redirect=Mock(), loadLoginPage=Mock(),
            logging=Mock(), HttpResponse=Mock())

    def view(self, name):
        code = ast.Module(body=[self.functions[name]], type_ignores=[])
        exec(compile(code, 'websiteFunctions/views.py', 'exec'), self.namespace)
        return self.namespace[name]

    def test_foreign_request_never_reaches_a_delete(self):
        for name, (method, position) in self.VIEWS.items():
            for meta in FOREIGN:
                self.manager.reset_mock()
                self.view(name)(request(meta, DeleteID='5', ID='3'))
                arguments = getattr(self.manager, method).call_args[0]
                self.assertIsNone(arguments[position], (name, meta))

    def test_the_panels_own_request_still_deletes(self):
        for name, (method, position) in self.VIEWS.items():
            for meta in OWN:
                self.manager.reset_mock()
                self.view(name)(request(meta, DeleteID='5', ID='3'))
                arguments = getattr(self.manager, method).call_args[0]
                self.assertEqual('5', arguments[position], (name, meta))

    def test_plugin_bucket_is_deleted_only_for_the_panels_own_request(self):
        configure = self.view('ConfigurePlugins')
        for meta in FOREIGN:
            configure(request(meta, delete='9'))
        self.plugins.objects.get.assert_not_called()
        configure(request(OWN[0], delete='9'))
        self.plugins.objects.get.assert_called_once()
        self.assertEqual('9', self.plugins.objects.get.call_args[1]['pk'])

    def test_no_handler_reads_a_delete_parameter_straight_from_the_query(self):
        for relative in ('websiteFunctions/views.py', 'websiteFunctions/website.py'):
            source = (ROOT / relative).read_text()
            for unsafe in ("GET.get('DeleteID'", 'GET.get("DeleteID"', "GET.get('delete'",
                           "GET['DeleteID']"):
                self.assertNotIn(unsafe, source, relative)


if __name__ == '__main__':
    unittest.main()
