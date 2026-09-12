"""Real Django request/JSON response tests with in-memory IMAP; no database use."""
import json
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from webmail.services.imap_client import IMAPClient
from webmail.test_message_deletion import MemoryIMAP
from webmail.webmailManager import WebmailManager


class NativeDeletionResponseTests(SimpleTestCase):
    def setUp(self):
        self.client = object.__new__(IMAPClient)
        self.client.conn = MemoryIMAP()
        self.log = mock.patch('webmail.webmailManager.logging.CyberCPLogFileWriter.writeToFile').start()
        self.addCleanup(mock.patch.stopall)

    def response(self, data, client=None):
        request = RequestFactory().post('/webmail/api/deleteMessages',
                                        json.dumps(data), content_type='application/json')
        manager = WebmailManager(request)
        with mock.patch.object(manager, '_get_imap', return_value=client or self.client):
            response = manager.apiDeleteMessages()
        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        return json.loads(response.content)

    def test_real_manager_returns_success_only_after_verified_move(self):
        self.assertEqual({'status': 1}, self.response({'folder': 'INBOX', 'uids': [1]}))
        self.assertEqual({2, 99}, self.client.conn.messages)
        self.assertIn(('logout',), self.client.conn.calls)

    def test_backend_rejection_remains_error_json_and_preserves_mail(self):
        self.client.conn.codes['move'] = 'NO'
        response = self.response({'folder': 'INBOX', 'uids': [1]})
        self.assertEqual(0, response['status'])
        self.assertIn('Refresh', response['error_message'])
        self.assertNotIn('private backend details', response['error_message'])
        self.assertEqual({1, 2, 99}, self.client.conn.messages)
        self.assertIn(('logout',), self.client.conn.calls)

    def test_missing_folder_and_nonexplicit_uids_do_not_default_to_inbox(self):
        for data in ({'uids': [1]}, {'folder': 'INBOX', 'uids': ['1:*']},
                     {'folder': 'INBOX', 'uids': []}):
            with self.subTest(data=data):
                self.client.conn.calls.clear()
                response = self.response(data)
                self.assertEqual(0, response['status'])
                self.assertFalse(any(call[0] in ('select', 'copy', 'move', 'store', 'expunge')
                                     for call in self.client.conn.calls))

    def test_ambiguous_helper_result_cannot_become_success_json(self):
        client = mock.MagicMock()
        client.__enter__.return_value = client
        for result in (None, False, 1, 'OK'):
            with self.subTest(result=result):
                client.delete_messages.return_value = result
                self.assertEqual(0, self.response({'folder': 'INBOX', 'uids': [1]}, client)['status'])

    def test_unexpected_connection_value_error_is_not_exposed_to_browser(self):
        request = RequestFactory().post('/webmail/api/deleteMessages',
                                        json.dumps({'folder': 'INBOX', 'uids': [1]}),
                                        content_type='application/json')
        manager = WebmailManager(request)
        with mock.patch.object(manager, '_get_imap', side_effect=ValueError('private backend details')):
            response = json.loads(manager.apiDeleteMessages().content)
        self.assertEqual(0, response['status'])
        self.assertNotIn('private backend details', response['error_message'])
        self.log.assert_called_once()


class NativeMoveResponseTests(SimpleTestCase):
    def setUp(self):
        self.client = object.__new__(IMAPClient)
        self.client.conn = MemoryIMAP()
        self.client.conn.trash.add('INBOX.Archive')
        self.log = mock.patch('webmail.webmailManager.logging.CyberCPLogFileWriter.writeToFile').start()
        self.addCleanup(mock.patch.stopall)

    def response(self, data):
        request = RequestFactory().post('/webmail/api/moveMessages', json.dumps(data), content_type='application/json')
        manager = WebmailManager(request)
        with mock.patch.object(manager, '_get_imap', return_value=self.client):
            response = manager.apiMoveMessages()
        self.assertEqual(200, response.status_code)
        return json.loads(response.content)

    def test_native_multiple_message_move_response_matches_backend(self):
        response = self.response({'folder': 'INBOX', 'uids': [1, 2], 'targetFolder': 'INBOX.Archive'})
        self.assertEqual({'status': 1}, response)
        self.assertEqual({99}, self.client.conn.messages)

    def test_native_move_rejection_is_error_and_never_retried(self):
        self.client.conn.codes['move'] = 'NO'
        response = self.response({'folder': 'INBOX', 'uids': [1, 2], 'targetFolder': 'INBOX.Archive'})
        self.assertEqual(0, response['status'])
        self.assertEqual({1, 2, 99}, self.client.conn.messages)
        self.assertFalse(any(call[0] in ('copy', 'store', 'expunge') for call in self.client.conn.calls))

    def test_native_move_rejects_missing_folder_and_destination(self):
        for data in ({'uids': [1], 'targetFolder': 'INBOX.Archive'}, {'folder': 'INBOX', 'uids': [1]}):
            with self.subTest(data=data):
                self.client.conn.calls.clear()
                self.assertEqual(0, self.response(data)['status'])
                self.assertFalse(any(call[0] in ('move', 'copy', 'store', 'expunge') for call in self.client.conn.calls))
