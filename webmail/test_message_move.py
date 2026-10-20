"""Checked multi-message IMAP Move outcomes, without network or real mail."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from webmail.services.imap_client import IMAPClient, IMAPOperationError
from webmail.test_message_deletion import MemoryIMAP


class MessageMoveTests(unittest.TestCase):
    def client(self, capabilities=b'IMAP4rev1 MOVE UIDPLUS'):
        client = object.__new__(IMAPClient)
        client.conn = MemoryIMAP(capabilities)
        client.conn.trash.add('INBOX.Archive')
        return client

    def test_multiple_uids_move_once_to_explicit_destination(self):
        client = self.client()
        with client:
            self.assertIs(True, client.move_messages('INBOX', [1, 2], 'INBOX.Archive'))
        self.assertEqual({99}, client.conn.messages)
        self.assertEqual({1, 2}, client.conn.copied)
        self.assertIn(('move', '1,2', '"INBOX.Archive"'), client.conn.calls)
        self.assertIn(('capability',), client.conn.calls)
        self.assertIn(('search', None, 'UID', '1,2'), client.conn.calls)

    def test_move_rejection_is_not_retried_as_copy(self):
        client = self.client(); client.conn.codes['move'] = 'NO'
        with self.assertRaises(IMAPOperationError):
            with client:
                client.move_messages('INBOX', [1, 2], 'INBOX.Archive')
        self.assertEqual({1, 2, 99}, client.conn.messages)
        self.assertFalse(any(call[0] in ('copy', 'store', 'expunge', 'expunge_all') for call in client.conn.calls))

    def test_uidplus_fallback_never_globally_expunges(self):
        client = self.client(b'IMAP4rev1 UIDPLUS')
        with client:
            self.assertIs(True, client.move_messages('INBOX', [1, 2], 'INBOX.Archive'))
        self.assertEqual({99}, client.conn.messages)
        self.assertIn(('expunge', '1,2'), client.conn.calls)
        self.assertFalse(any(call[0] in ('move', 'expunge_all', 'close_expunges_all') for call in client.conn.calls))

    def test_rejected_fallback_stage_is_truthful_and_preserves_source(self):
        for stage in ('copy', 'store', 'expunge'):
            with self.subTest(stage=stage):
                client = self.client(b'IMAP4rev1 UIDPLUS'); client.conn.codes[stage] = 'NO'
                with self.assertRaises(IMAPOperationError):
                    with client:
                        client.move_messages('INBOX', [1, 2], 'INBOX.Archive')
                self.assertEqual({1, 2, 99}, client.conn.messages)
                self.assertFalse(any(call[0] in ('expunge_all', 'close_expunges_all') for call in client.conn.calls))
                if stage != 'expunge':
                    self.assertFalse(any(call[0] == 'expunge' for call in client.conn.calls))

    def test_missing_source_uid_or_destination_refuses_before_write(self):
        for ids, target in (([1, 20], 'INBOX.Archive'), ([1, 2], 'INBOX.Missing')):
            with self.subTest(ids=ids, target=target):
                client = self.client()
                with self.assertRaises(IMAPOperationError):
                    with client:
                        client.move_messages('INBOX', ids, target)
                self.assertEqual({1, 2, 99}, client.conn.messages)
                self.assertFalse(any(call[0] in ('move', 'copy', 'create', 'store') for call in client.conn.calls))

    def test_invalid_or_same_folder_request_cannot_write(self):
        for folder, ids, target in (('INBOX', [1], 'INBOX'), (None, [1], 'INBOX.Archive'),
                                    ('INBOX', ['1:*'], 'INBOX.Archive'), ('INBOX', [1], 'Trash\r\nInjected')):
            with self.subTest(folder=folder, ids=ids, target=target):
                client = self.client()
                with self.assertRaises((ValueError, IMAPOperationError)):
                    client.move_messages(folder, ids, target)
                self.assertFalse(any(call[0] in ('move', 'copy', 'create', 'store') for call in client.conn.calls))

    def test_connection_loss_does_not_trigger_second_operation(self):
        client = self.client(); client.conn.codes['move'] = OSError('private backend details')
        with self.assertRaises(IMAPOperationError) as error:
            with client:
                client.move_messages('INBOX', [1, 2], 'INBOX.Archive')
        self.assertNotIn('private backend details', str(error.exception))
        self.assertEqual(1, sum(call[0] == 'move' for call in client.conn.calls))
        self.assertFalse(any(call[0] == 'copy' for call in client.conn.calls))


class MoveAPIOutcomeTests(unittest.TestCase):
    def method(self):
        path = Path(__file__).with_name('webmailManager.py')
        cls = next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef) and node.name == 'WebmailManager')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'apiMoveMessages')
        namespace = {'IMAPOperationError': IMAPOperationError,
                     'logging': SimpleNamespace(CyberCPLogFileWriter=mock.Mock())}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        return namespace['apiMoveMessages']

    def manager(self, result=True, error=None):
        client = mock.MagicMock(); client.__enter__.return_value = client
        client.move_messages.return_value = result; client.move_messages.side_effect = error
        return SimpleNamespace(_get_post_data=lambda: {'folder': 'INBOX', 'uids': [1, 2], 'targetFolder': 'INBOX.Archive'},
                               _get_imap=lambda: client, _success=lambda: {'status': 1},
                               _error=lambda msg: {'status': 0, 'error_message': str(msg)})

    def test_only_explicit_verified_success_is_success_json(self):
        method = self.method()
        for result in (False, None, 1, 'OK'):
            with self.subTest(result=result):
                self.assertEqual(0, method(self.manager(result))['status'])
        self.assertEqual({'status': 1}, method(self.manager(True)))

    def test_backend_error_is_not_exposed(self):
        response = self.method()(self.manager(error=OSError('private backend details')))
        self.assertEqual(0, response['status'])
        self.assertNotIn('private backend details', response['error_message'])
