"""Native UI/CLI responses; shared cleanup/rollback policy has real ORM tests."""
import contextlib
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory

from cli import cyberPanel as cli
from mailServer import mailserverManager as manager
from mailServer import views
from plogical import mailDomainDeletion


class EmailDeletionStatusTests(unittest.TestCase):
    def setUp(self):
        self.address = 'owned@example.test'
        self.request = RequestFactory().post(
            '/email/submitEmailDeletion', json.dumps({'email': self.address}),
            content_type='application/json')
        self.request.session = {'userID': 7}
        self.website = SimpleNamespace(pk=31, domain='example.test')
        self.admin = SimpleNamespace(pk=7)
        self.denied = HttpResponse(json.dumps({'status': 0, 'deleteEmailStatus': 0,
                                               'error_message': 'Permission denied'}))
        self.actual_delete = manager.mailUtilities.deleteEmailAccount
        patches = {
            'pre_hook': patch.object(views.pluginManager, 'preSubmitEmailDeletion', return_value=200),
            'post_hook': patch.object(views.pluginManager, 'postSubmitEmailDeletion', return_value=200),
            'acl': patch.object(manager.ACLManager, 'loadedACL', return_value={'admin': 1}),
            'permission': patch.object(manager.ACLManager, 'currentContextPermission', return_value=1),
            'ownership': patch.object(manager.ACLManager, 'checkOwnership', return_value=1),
            'denied': patch.object(manager.ACLManager, 'loadErrorJson', return_value=self.denied),
            'admin': patch.object(manager.Administrator.objects, 'get', return_value=self.admin),
            'delete': patch.object(manager.mailUtilities, 'deleteEmailAccount', return_value=(1, 'None')),
            'cli_logger': patch.object(cli.logger, 'writeforCLI'),
        }
        self.mocks = {}
        for name, item in patches.items():
            self.mocks[name] = item.start()
            self.addCleanup(item.stop)

    def response(self):
        return json.loads(views.submitEmailDeletion(self.request).content)

    def cli_response(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cli.cyberPanel().deleteEmail(self.address)
        return json.loads(output.getvalue())

    def assert_ui_delegate(self):
        self.mocks['delete'].assert_called_once()
        self.assertEqual((self.address,), self.mocks['delete'].call_args.args)
        authorize = self.mocks['delete'].call_args.kwargs['authorize']
        self.assertTrue(callable(authorize))
        return authorize

    def test_ui_helper_failure_returns_error(self):
        self.mocks['delete'].return_value = (0, 'Mailbox deletion failed')
        self.assertEqual({'status': 0, 'deleteEmailStatus': 0,
                          'error_message': 'Mailbox deletion failed'}, self.response())
        self.assert_ui_delegate()

    def test_cli_helper_failure_reports_success_zero(self):
        self.mocks['delete'].return_value = (0, 'Mailbox deletion failed')
        self.assertEqual({'success': 0, 'errorMessage': 'Mailbox deletion failed'}, self.cli_response())
        self.mocks['delete'].assert_called_once_with(self.address)

    def test_actual_wrapper_delete_error_reaches_ui(self):
        self.mocks['delete'].side_effect = self.actual_delete
        with patch.object(mailDomainDeletion, 'delete_mailbox', side_effect=RuntimeError('Delete refused')), \
                patch('plogical.CyberCPLogFileWriter.CyberCPLogFileWriter.writeToFile'):
            self.assertEqual({'status': 0, 'deleteEmailStatus': 0,
                              'error_message': 'Delete refused'}, self.response())

    def test_ui_success_preserves_response_schema(self):
        self.assertEqual({'status': 1, 'deleteEmailStatus': 1,
                          'error_message': 'None'}, self.response())
        self.assert_ui_delegate()

    def test_ui_authorization_uses_shared_helpers_fresh_resolved_owner(self):
        self.response()
        authorize = self.assert_ui_delegate()
        self.assertTrue(authorize(self.website))
        self.mocks['ownership'].assert_called_once_with('example.test', self.admin, {'admin': 1})

    def test_ui_authorization_denial_is_returned_to_shared_helper(self):
        self.mocks['ownership'].return_value = 0
        self.response()
        self.assertFalse(self.assert_ui_delegate()(self.website))

    def test_registry_failure_returned_by_shared_helper_is_failure(self):
        self.mocks['delete'].return_value = (0, 'Quota registry unavailable')
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.assert_ui_delegate()

    def test_child_owner_is_authorized_using_resolved_master(self):
        self.response()
        authorize = self.assert_ui_delegate()
        self.assertTrue(authorize(SimpleNamespace(pk=44, domain='master.example.test')))
        self.assertEqual('master.example.test', self.mocks['ownership'].call_args.args[0])

    def test_conflicting_child_owner_failure_is_reported(self):
        self.mocks['delete'].return_value = (0, 'Mail domain has inconsistent website ownership.')
        self.assertEqual(0, self.response()['deleteEmailStatus'])

    def test_cli_success_keeps_existing_response(self):
        self.assertEqual({'success': 1, 'errorMessage': 'None'}, self.cli_response())
        self.mocks['delete'].assert_called_once_with(self.address)

    def test_helper_exception_is_failure_in_both_callers(self):
        self.mocks['delete'].side_effect = RuntimeError('Deletion unavailable')
        self.assertEqual({'status': 0, 'deleteEmailStatus': 0,
                          'error_message': 'Deletion unavailable'}, self.response())
        self.assertEqual({'success': 0, 'errorMessage': 'Deletion unavailable'}, self.cli_response())

    def test_permission_denial_precedes_deletion(self):
        self.mocks['permission'].return_value = 0
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['delete'].assert_not_called()
        self.mocks['admin'].assert_not_called()

    def test_missing_email_does_not_invoke_deletion(self):
        self.request = RequestFactory().post('/email/submitEmailDeletion', '{}', content_type='application/json')
        self.request.session = {'userID': 7}
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['delete'].assert_not_called()

    def test_missing_session_preserves_authentication_failure(self):
        self.request.session = {}
        self.assertEqual(0, json.loads(views.submitEmailDeletion(self.request).content)['deleteEmailStatus'])
        self.mocks['acl'].assert_not_called()
        self.mocks['delete'].assert_not_called()

    def test_pre_hook_rejection_still_stops_before_auth_and_deletion(self):
        self.mocks['pre_hook'].return_value = self.denied
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['acl'].assert_not_called()
        self.mocks['delete'].assert_not_called()
        self.mocks['post_hook'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
