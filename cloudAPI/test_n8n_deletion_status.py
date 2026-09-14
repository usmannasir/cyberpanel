"""n8n cleanup must wait for confirmed website deletion."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock
from django.http import HttpResponse
from websiteFunctions.models import Websites
from websiteFunctions.website import WebsiteManager


class N8NDeletionStatusTests(unittest.TestCase):
    def run_case(self, payload):
        source = Path(__file__).with_name('cloudManager.py')
        tree = ast.parse(source.read_text())
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CloudManager')
        method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == 'removeN8NInstallation')
        namespace = {'json': json, 'HttpResponse': HttpResponse}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(source), 'exec'), namespace)
        manager = SimpleNamespace(data={'domainName': 'fixture.example'}, admin=SimpleNamespace(pk=7), ajaxPre=lambda status, message: HttpResponse(json.dumps({'status': status, 'error_message': message})))
        with mock.patch.object(Websites.objects, 'get', return_value=mock.Mock()), mock.patch.object(WebsiteManager, 'submitWebsiteDeletion', return_value=HttpResponse(json.dumps(payload))), mock.patch('os.path.exists', return_value=True), mock.patch('os.remove') as remove:
            response = namespace['removeN8NInstallation'](manager)
        return json.loads(response.content), remove

    def test_pending_failed_and_unrecognized_results_do_not_clean_up_or_report_removed(self):
        for state, status in [('pending', 2), ('awaiting_primary', 2), ('failed', 0), ('unknown', 1)]:
            response, remove = self.run_case({'status': 1, 'websiteDeleteStatus': status, 'state': state, 'error_message': 'Not completed.'})
            self.assertEqual(0, response['status'])
            remove.assert_not_called()

    def test_confirmed_deletion_allows_metadata_cleanup(self):
        response, remove = self.run_case({'status': 1, 'websiteDeleteStatus': 1, 'state': 'completed'})
        self.assertEqual(1, response['status'])
        remove.assert_called_once()
