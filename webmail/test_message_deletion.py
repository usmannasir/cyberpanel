"""Deletion outcomes with an in-memory IMAP server; no connections or messages."""
import ast
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest import mock

from webmail.services.imap_client import IMAPClient


class MemoryIMAP:
    def __init__(self, capabilities=b'IMAP4rev1 MOVE UIDPLUS'):
        self.capabilities_response = capabilities
        self.codes = {}
        self.calls = []
        self.trash = {'INBOX.Deleted Items'}
        self.deleted = {99}
        self.messages = {1, 2, 99}
        self.copied = set()

    def result(self, command):
        value = self.codes.get(command, 'OK')
        if isinstance(value, Exception):
            raise value
        return value, [b'private backend details must not appear in public errors']

    def select(self, folder):
        self.calls.append(('select', folder))
        return self.result('select')

    def capability(self):
        self.calls.append(('capability',))
        return self.result('capability')[0], [self.capabilities_response]

    def status(self, folder, fields):
        self.calls.append(('status', folder, fields))
        if folder.strip('"') not in self.trash:
            return 'NO', [b'missing']
        return self.result('status')

    def create(self, folder):
        self.calls.append(('create', folder))
        result = self.result('create')
        if result[0] == 'OK':
            self.trash.add(folder.strip('"'))
        return result

    def uid(self, command, ids, *args):
        self.calls.append((command, ids, *args))
        result = self.result(command)
        if result[0] != 'OK':
            return result
        if command == 'search':
            selected = set(int(uid) for uid in args[-1].split(','))
            return result[0], [' '.join(str(uid) for uid in sorted(selected & self.messages)).encode()]
        chosen = set(int(uid) for uid in ids.split(','))
        if command == 'copy':
            self.copied.update(chosen & self.messages)
        elif command == 'move':
            self.copied.update(chosen & self.messages)
            self.messages.difference_update(chosen)
        elif command == 'store':
            if args != ('+FLAGS', '(\\Deleted)'):
                raise AssertionError('Incorrect deletion flags')
            self.deleted.update(chosen & self.messages)
        elif command == 'expunge':
            self.messages.difference_update(chosen & self.deleted)
        return result

    def expunge(self):
        self.calls.append(('expunge_all',))
        result = self.result('expunge')
        if result[0] == 'OK':
            self.messages.difference_update(self.deleted)
        return result

    def close(self):
        self.calls.append(('close_expunges_all',))
        self.messages.difference_update(self.deleted)

    def logout(self):
        self.calls.append(('logout',))
        return 'BYE', [b'done']


class MessageDeletionTests(unittest.TestCase):
    def client(self, capabilities=b'IMAP4rev1 MOVE UIDPLUS'):
        client = object.__new__(IMAPClient)
        client.conn = MemoryIMAP(capabilities)
        return client

    def assert_rejected(self, client, folder='INBOX'):
        with self.assertRaises(Exception) as failure:
            with client:
                client.delete_messages(folder, [1])
        self.assertNotIn('private backend details', str(failure.exception))
        self.assertIn(99, client.conn.messages)
        self.assertNotIn(('expunge_all',), client.conn.calls)
        self.assertNotIn(('close_expunges_all',), client.conn.calls)

    def test_native_move_deletes_only_selected_uid_and_logs_out_without_expunge(self):
        client = self.client()
        with client:
            self.assertTrue(client.delete_messages('INBOX', [1]))
        self.assertEqual({2, 99}, client.conn.messages)
        self.assertIn(('move', '1', '"INBOX.Deleted Items"'), client.conn.calls)
        self.assertIn(('capability',), client.conn.calls)
        self.assertNotIn(('close_expunges_all',), client.conn.calls)

    def test_copy_fallback_uses_uid_expunge_and_preserves_other_deleted_message(self):
        client = self.client(b'IMAP4rev1 UIDPLUS')
        with client:
            self.assertTrue(client.delete_messages('INBOX', [1]))
        self.assertEqual({2, 99}, client.conn.messages)
        self.assertIn(('expunge', '1'), client.conn.calls)

    def test_copy_failure_never_falls_through_to_permanent_delete(self):
        client = self.client(b'IMAP4rev1 UIDPLUS')
        client.conn.codes['copy'] = 'NO'
        self.assert_rejected(client)
        self.assertFalse(any(call[0] in ('store', 'expunge') for call in client.conn.calls))
        self.assertEqual({1, 2, 99}, client.conn.messages)

    def test_move_rejection_is_not_retried_as_copy_or_against_another_trash(self):
        client = self.client()
        client.conn.codes['move'] = 'NO'
        self.assert_rejected(client)
        self.assertFalse(any(call[0] == 'copy' for call in client.conn.calls))

    def test_store_failure_after_copy_is_not_reported_success(self):
        client = self.client(b'IMAP4rev1 UIDPLUS')
        client.conn.codes['store'] = 'NO'
        self.assert_rejected(client)
        self.assertIn(1, client.conn.messages)
        self.assertFalse(any(call[0] == 'expunge' for call in client.conn.calls))

    def test_uid_expunge_failure_is_not_reported_success(self):
        client = self.client(b'IMAP4rev1 UIDPLUS')
        client.conn.codes['expunge'] = 'NO'
        self.assert_rejected(client)
        self.assertIn(1, client.conn.messages)

    def test_trash_deletion_is_uid_scoped(self):
        for folder in ('INBOX.Deleted Items', 'INBOX.Trash', 'Trash'):
            with self.subTest(folder=folder):
                client = self.client()
                with client:
                    self.assertTrue(client.delete_messages(folder, [1]))
                self.assertEqual({2, 99}, client.conn.messages)
                self.assertNotIn(1, client.conn.copied)
                self.assertIn(('expunge', '1'), client.conn.calls)

    def test_trash_without_uidplus_refuses_before_marking_anything(self):
        client = self.client(b'IMAP4rev1 MOVE')
        self.assert_rejected(client, 'Trash')
        self.assertFalse(any(call[0] == 'store' for call in client.conn.calls))

    def test_copy_fallback_without_uidplus_refuses_before_copy(self):
        client = self.client(b'IMAP4rev1')
        self.assert_rejected(client)
        self.assertFalse(any(call[0] in ('copy', 'store') for call in client.conn.calls))

    def test_native_move_does_not_require_uidplus(self):
        client = self.client(b'IMAP4rev1 MOVE')
        with client:
            self.assertTrue(client.delete_messages('INBOX', [1]))
        self.assertEqual({2, 99}, client.conn.messages)

    def test_missing_trash_is_created_with_quoted_standard_name(self):
        client = self.client();client.conn.trash.clear()
        self.assertTrue(client.delete_messages('INBOX', [1]))
        self.assertIn(('create', '"INBOX.Deleted Items"'), client.conn.calls)
        self.assertIn(('move', '1', '"INBOX.Deleted Items"'), client.conn.calls)

    def test_failed_trash_creation_leaves_source_messages(self):
        client = self.client();client.conn.trash.clear();client.conn.codes['create']='NO'
        self.assert_rejected(client)
        self.assertEqual({1, 2, 99}, client.conn.messages)
        self.assertFalse(any(call[0] in ('move','copy','store') for call in client.conn.calls))

    def test_existing_alternative_trash_is_used(self):
        client = self.client();client.conn.trash={'Trash'}
        self.assertTrue(client.delete_messages('INBOX', [1]))
        self.assertIn(('move','1','"Trash"'),client.conn.calls)
        self.assertFalse(any(call[0]=='create' for call in client.conn.calls))

    def test_select_and_capability_failures_do_not_mutate_messages(self):
        for stage in ('select', 'capability'):
            with self.subTest(stage=stage):
                client = self.client();client.conn.codes[stage]='NO'
                self.assert_rejected(client)
                self.assertFalse(any(call[0] in ('move','copy','store') for call in client.conn.calls))

    def test_connection_failure_stops_deletion_instead_of_trying_other_targets(self):
        client = self.client();client.conn.codes['move']=OSError('private backend details')
        self.assert_rejected(client)
        self.assertEqual({1,2,99},client.conn.messages)

    def test_uids_must_be_explicit_positive_integer_list_and_are_deduplicated(self):
        for ids in ([], '*', [0], [-1], [True], ['1:9'], ['1,2'], [1.5], [4294967296]):
            with self.subTest(ids=ids):
                client=self.client()
                with self.assertRaises(ValueError):client.delete_messages('INBOX',ids)
                self.assertEqual([],client.conn.calls)
        client=self.client()
        self.assertTrue(client.delete_messages('INBOX',[1,'2',1]))
        self.assertIn(('move','1,2','"INBOX.Deleted Items"'),client.conn.calls)

    def test_folder_is_quoted_and_invalid_control_characters_rejected(self):
        client=self.client()
        self.assertTrue(client.delete_messages('INBOX.A "quoted" folder',[1]))
        self.assertIn(('select','"INBOX.A \\"quoted\\" folder"'),client.conn.calls)
        for folder in ('', None, 'INBOX\r\nTrash'):
            client=self.client()
            with self.assertRaises(ValueError):client.delete_messages(folder,[1])
            self.assertEqual([],client.conn.calls)


    def test_explicit_uids_are_rechecked_in_selected_folder_before_any_write(self):
        for ids in ([1, 10], [10]):
            with self.subTest(ids=ids):
                client = self.client()
                with self.assertRaises(Exception):
                    with client:
                        client.delete_messages('INBOX', ids)
                self.assertEqual({1, 2, 99}, client.conn.messages)
                self.assertFalse(any(call[0] in ('create', 'move', 'copy', 'store', 'expunge') for call in client.conn.calls))

    def test_uid_search_rejection_cannot_create_trash_or_change_messages(self):
        client = self.client()
        client.conn.codes['search'] = 'NO'
        self.assert_rejected(client)
        self.assertFalse(any(call[0] in ('status', 'create', 'move', 'copy', 'store') for call in client.conn.calls))

    def test_invalid_capability_data_fails_before_message_mutation(self):
        for capabilities in (None, b'\xff', 123):
            with self.subTest(capabilities=capabilities):
                client = self.client(capabilities)
                self.assert_rejected(client)
                self.assertEqual({1, 2, 99}, client.conn.messages)

    def test_trash_status_error_does_not_try_alternative_or_permanent_delete(self):
        client = self.client()
        client.conn.codes['status'] = 'BAD'
        self.assert_rejected(client)
        self.assertEqual(1, sum(call[0] == 'status' for call in client.conn.calls))
        self.assertFalse(any(call[0] in ('create', 'move', 'copy', 'store') for call in client.conn.calls))

    def test_mailbox_backslash_is_escaped_in_quoted_select(self):
        client = self.client()
        self.assertTrue(client.delete_messages('INBOX.Back\\slash', [1]))
        self.assertEqual(('select', '"INBOX.Back\\\\slash"'), client.conn.calls[0])

    def test_partially_completed_move_does_not_retry_or_expunge_other_messages(self):
        client = self.client()
        original_uid = client.conn.uid
        def partial_move(command, ids, *args):
            if command == 'move':
                original_uid(command, '1', *args)
                return 'NO', [b'private backend details']
            return original_uid(command, ids, *args)
        client.conn.uid = partial_move
        with self.assertRaises(Exception):
            with client:
                client.delete_messages('INBOX', [1, 2])
        self.assertEqual({2, 99}, client.conn.messages)
        self.assertEqual({1}, client.conn.copied)
        self.assertEqual(1, sum(call[0] == 'move' for call in client.conn.calls))
        self.assertFalse(any(call[0] in ('copy', 'store', 'expunge', 'expunge_all', 'close_expunges_all') for call in client.conn.calls))


class MessageDeletionAPIOutcomeTests(unittest.TestCase):
    @staticmethod
    def method():
        path=Path(__file__).with_name('webmailManager.py')
        tree=ast.parse(path.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WebmailManager')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='apiDeleteMessages')
        import webmail.services.imap_client as imap_module
        namespace={'logging':SimpleNamespace(CyberCPLogFileWriter=mock.Mock()),
                   'IMAPOperationError':getattr(imap_module,'IMAPOperationError',type('IMAPOperationError',(Exception,),{}))}
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
        return namespace['apiDeleteMessages'],namespace

    def manager(self,result=True,error=None):
        imap=mock.MagicMock();imap.__enter__.return_value=imap
        imap.delete_messages.return_value=result
        imap.delete_messages.side_effect=error
        manager=SimpleNamespace(_get_post_data=lambda:{'folder':'INBOX','uids':[1]},
                                _get_imap=lambda:imap,_success=lambda:{'status':1},
                                _error=lambda msg:{'status':0,'error_message':str(msg)})
        return manager

    def test_false_or_ambiguous_helper_result_is_not_success(self):
        method,_=self.method()
        for result in (False,None,'yes',1):
            with self.subTest(result=result):
                self.assertEqual(0,method(self.manager(result))['status'])
        self.assertEqual({'status':1},method(self.manager(True)))

    def test_unexpected_connection_error_is_sanitized_and_logged(self):
        method,namespace=self.method()
        for error in (OSError('private backend details'), ValueError('private backend details')):
            with self.subTest(error=type(error).__name__):
                response=method(self.manager(error=error))
                self.assertEqual(0,response['status'])
                self.assertNotIn('private backend details',response['error_message'])
        self.assertEqual(2, namespace['logging'].CyberCPLogFileWriter.writeToFile.call_count)
