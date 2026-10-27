"""Exercise actual view-manager methods with isolated model/worker boundaries."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        source = ast.parse(Path(__file__).with_name('website.py').read_text())
        manager = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'WebsiteManager')
        methods = [node for node in manager.body if isinstance(node, ast.FunctionDef)
                   and node.name in ('startSync', 'syncToMaster')]
        self.acl, self.worker, self.children, self.render = (mock.Mock() for _ in range(4))
        self.acl.checkOwnership.return_value = 1
        self.acl.loadErrorJson.return_value = {'status': 0, 'error_message': 'Permission denied'}
        self.acl.loadError.return_value = 'Permission denied'
        self.children.objects.get.return_value = SimpleNamespace(domain='stage.example',
                                                                 master=SimpleNamespace(domain='live.example', externalApp='liveuser'))
        self.environment = {'ACLManager': self.acl, 'Administrator': mock.Mock(),
                            'ChildDomains': self.children, 'StagingSetup': self.worker,
                            'validators': SimpleNamespace(domain=lambda domain: '.' in domain),
                            'httpProc': self.render, 'json': json, 'HttpResponse': json.loads}
        exec(compile(ast.Module(body=methods, type_ignores=[]), 'website.py', 'exec'), self.environment)

    def start(self, **changes):
        data = {'childDomain': 'stage.example', 'dbCheck': True, 'confirmed': True}
        data.update(changes)
        with mock.patch('plogical.statusUtilities.create_status_file', return_value='/home/cyberpanel/123'):
            return self.environment['startSync'](SimpleNamespace(), 7, data)

    def test_authorized_source_and_target_start_exactly_one_worker(self):
        response = self.start()
        self.assertEqual(1, response['status'])
        self.assertEqual(['stage.example', 'live.example'], [call.args[0] for call in self.acl.checkOwnership.call_args_list])
        self.worker.return_value.start.assert_called_once()

    def test_foreign_source_or_target_never_starts(self):
        for decisions in ([0], [1, 0]):
            self.acl.checkOwnership.side_effect = decisions
            self.assertEqual(0, self.start()['status'])
            self.worker.assert_not_called()

    def test_unconfirmed_empty_conflicting_or_malformed_options_never_start(self):
        for changes in ({'confirmed': False}, {'dbCheck': False}, {'dbCheck': 'false'},
                        {'eraseCheck': True, 'copyChanged': True}):
            self.assertEqual(0, self.start(**changes)['status'])
            self.worker.assert_not_called()

    def test_page_requires_child_of_selected_master_and_both_owners(self):
        self.environment['syncToMaster'](SimpleNamespace(domain='live.example'), None, 7, None, 'stage.example')
        self.children.objects.get.assert_called_once_with(domain='stage.example', master__domain='live.example')
        self.acl.checkOwnership.side_effect = [1, 0]
        self.render.reset_mock()
        self.assertEqual('Permission denied', self.environment['syncToMaster'](
            SimpleNamespace(domain='live.example'), None, 7, None, 'stage.example'))
        self.render.assert_not_called()


if __name__ == '__main__':
    unittest.main()
