"""Mail deletion responses and cleanup with controlled helper/ORM outcomes."""
import contextlib
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.test import RequestFactory

from cli import cyberPanel as cli
from mailServer import mailserverManager as manager
from mailServer import views
from plogical import mailUtilities as mail_module
from plogical import storageQuota


class EmailDeletionStatusTests(unittest.TestCase):
    def setUp(self):
        self.address = 'owned@example.test'
        self.request = RequestFactory().post(
            '/email/submitEmailDeletion', json.dumps({'email': self.address}),
            content_type='application/json')
        self.request.session = {'userID': 7}
        self.domain = Mock()
        self.domain.domainOwner.domain = 'example.test'
        self.domain.domainOwner.pk = 31
        self.domain.childOwner_id = None
        self.domain.childOwner = None
        self.domain.eusers_set.all.return_value.count.return_value = 0
        self.mailbox = SimpleNamespace(emailOwner=self.domain)
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
            'mailbox': patch.object(manager.EUsers.objects, 'get', return_value=self.mailbox),
            'admin': patch.object(manager.Administrator.objects, 'get', return_value=SimpleNamespace(pk=7)),
            'delete': patch.object(manager.mailUtilities, 'deleteEmailAccount', return_value=(1, 'None')),
            'enrollment': patch.object(storageQuota, 'has_enrollment', return_value=False),
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

    def test_ui_helper_failure_returns_error_before_any_domain_cleanup(self):
        self.mocks['delete'].return_value = (0, 'Mailbox deletion failed')
        self.assertEqual({'status': 0, 'deleteEmailStatus': 0,
                          'error_message': 'Mailbox deletion failed'}, self.response())
        self.mocks['delete'].assert_called_once_with(self.address)
        self.domain.eusers_set.all.assert_not_called()
        self.domain.delete.assert_not_called()

    def test_cli_helper_failure_reports_success_zero(self):
        self.mocks['delete'].return_value = (0, 'Mailbox deletion failed')
        self.assertEqual({'success': 0, 'errorMessage': 'Mailbox deletion failed'}, self.cli_response())
        self.mocks['delete'].assert_called_once_with(self.address)

    def test_actual_helper_delete_error_reaches_ui_without_cleanup(self):
        self.mocks['delete'].side_effect = self.actual_delete
        with patch.object(mail_module.EUsers, 'delete', side_effect=RuntimeError('Delete refused')), \
                patch.object(mail_module.logging.CyberCPLogFileWriter, 'writeToFile'):
            response = self.response()
        self.assertEqual({'status': 0, 'deleteEmailStatus': 0,
                          'error_message': 'Delete refused'}, response)
        self.domain.eusers_set.all.assert_not_called()
        self.domain.delete.assert_not_called()

    def test_ui_success_keeps_existing_last_mailbox_domain_cleanup(self):
        self.assertEqual({'status': 1, 'deleteEmailStatus': 1,
                          'error_message': 'None'}, self.response())
        self.mocks['delete'].assert_called_once_with(self.address)
        self.domain.delete.assert_called_once_with()

    def test_ui_success_keeps_domain_with_remaining_mailbox(self):
        self.domain.eusers_set.all.return_value.count.return_value = 1
        self.assertEqual(1, self.response()['deleteEmailStatus'])
        self.domain.delete.assert_not_called()

    def test_last_mailbox_deletion_preserves_enrolled_domain_storage_scope(self):
        self.mocks['enrollment'].return_value = True
        self.assertEqual(1, self.response()['deleteEmailStatus'])
        self.mocks['enrollment'].assert_called_once_with(self.domain.domainOwner)
        self.mocks['delete'].assert_called_once_with(self.address)
        self.domain.delete.assert_not_called()

    def test_unreadable_quota_registry_refuses_before_mailbox_deletion(self):
        self.mocks['enrollment'].side_effect = ValueError('Quota registry unavailable')
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['delete'].assert_not_called()
        self.domain.delete.assert_not_called()

    def test_child_mail_domain_checks_master_ownership_and_enrollment(self):
        website = self.domain.domainOwner
        self.domain.domainOwner = None
        self.domain.childOwner_id = 8
        self.domain.childOwner = SimpleNamespace(master_id=31, master=website)
        self.mocks['enrollment'].return_value = True
        self.assertEqual(1, self.response()['deleteEmailStatus'])
        self.assertEqual('example.test', self.mocks['ownership'].call_args[0][0])
        self.mocks['enrollment'].assert_called_once_with(website)
        self.domain.delete.assert_not_called()

    def test_conflicting_child_owner_refuses_before_deletion(self):
        self.domain.childOwner_id = 8
        self.domain.childOwner = SimpleNamespace(master_id=44, master=SimpleNamespace(pk=44))
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['enrollment'].assert_not_called()
        self.mocks['delete'].assert_not_called()
        self.domain.delete.assert_not_called()

    def test_cli_success_keeps_existing_response(self):
        self.assertEqual({'success': 1, 'errorMessage': 'None'}, self.cli_response())
        self.domain.delete.assert_not_called()

    def test_helper_exception_is_failure_without_domain_cleanup(self):
        self.mocks['delete'].side_effect = RuntimeError('Deletion unavailable')
        self.assertEqual({'status': 0, 'deleteEmailStatus': 0,
                          'error_message': 'Deletion unavailable'}, self.response())
        self.assertEqual({'success': 0, 'errorMessage': 'Deletion unavailable'}, self.cli_response())
        self.domain.eusers_set.all.assert_not_called()
        self.domain.delete.assert_not_called()

    def test_permission_denial_precedes_mailbox_lookup_and_deletion(self):
        self.mocks['permission'].return_value = 0
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['mailbox'].assert_not_called()
        self.mocks['delete'].assert_not_called()
        self.domain.delete.assert_not_called()

    def test_ownership_denial_prevents_deletion_and_cleanup(self):
        self.mocks['ownership'].return_value = 0
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['ownership'].assert_called_once()
        self.mocks['delete'].assert_not_called()
        self.domain.eusers_set.all.assert_not_called()
        self.domain.delete.assert_not_called()

    def test_missing_session_preserves_authentication_failure(self):
        self.request.session = {}
        response = views.submitEmailDeletion(self.request)
        self.assertEqual(0, json.loads(response.content)['deleteEmailStatus'])
        self.mocks['acl'].assert_not_called()
        self.mocks['delete'].assert_not_called()
        self.domain.delete.assert_not_called()

    def test_pre_hook_rejection_still_stops_before_auth_and_deletion(self):
        self.mocks['pre_hook'].return_value = self.denied
        self.assertEqual(0, self.response()['deleteEmailStatus'])
        self.mocks['acl'].assert_not_called()
        self.mocks['delete'].assert_not_called()
        self.mocks['post_hook'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
