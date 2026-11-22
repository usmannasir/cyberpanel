"""The record of a file operation is kept whatever the path of the file looks like."""
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from aiScanner import api


class FileOperationLogTests(SimpleTestCase):

    def setUp(self):
        self.rows = []
        self.refuse = lambda fields: False
        test = self

        class Operations(object):
            @staticmethod
            def create(**fields):
                # The table holds what its columns hold, and refuses the rest.
                if len(fields['file_path']) > 500 or len(fields['backup_path'] or '') > 500 \
                        or len(fields['scan_id']) > 255 or len(fields['user_agent'] or '') > 255 \
                        or test.refuse(fields):
                    raise ValueError('Data too long or incorrect string value')
                test.rows.append(fields)

        patcher = mock.patch('aiScanner.models.ScannerFileOperation', SimpleNamespace(objects=Operations))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('aiScanner.api.logging')
        self.log = patcher.start()
        self.addCleanup(patcher.stop)

    def test_an_ordinary_operation_is_recorded_as_it_is(self):
        request = RequestFactory().get('/api/scanner/get-file', HTTP_USER_AGENT='AI-Scanner-Platform/1.0')
        api.log_file_operation('cp_0123456789ab', 'backup', 'wp-content/plugins/demo.php', True,
                               backup_path='/home/e.com/.ai-scanner-backups/2026-11-22/demo.php.1.ab.bak',
                               request=request)
        self.assertEqual([{
            'scan_id': 'cp_0123456789ab', 'operation': 'backup', 'file_path': 'wp-content/plugins/demo.php',
            'backup_path': '/home/e.com/.ai-scanner-backups/2026-11-22/demo.php.1.ab.bak', 'success': True,
            'error_message': None, 'ip_address': '127.0.0.1', 'user_agent': 'AI-Scanner-Platform/1.0'}], self.rows)

    def test_a_path_longer_than_the_column_is_shortened_and_still_recorded(self):
        path = 'wp-content/' + 'deep/' * 300 + 'planted-file.php'
        backup = '/home/e.com/.ai-scanner-backups/2026-11-22/' + 'n' * 600 + '.1730000000.abcdef.bak'
        api.log_file_operation('s' * 400, 'delete', path, False, 'File not found', backup_path=backup)
        row, = self.rows
        self.assertEqual((500, 500, 255), (len(row['file_path']), len(row['backup_path']), len(row['scan_id'])))
        # Where the file is and what it is called are both still there.
        self.assertTrue(row['file_path'].startswith('wp-content/deep/deep/'))
        self.assertTrue(row['file_path'].endswith('/deep/planted-file.php'))
        self.assertIn('...', row['file_path'])
        self.assertTrue(row['backup_path'].endswith('.1730000000.abcdef.bak'))
        self.assertEqual(('delete', False, 'File not found'), (row['operation'], row['success'], row['error_message']))
        for length in (1, 499, 500):
            self.assertEqual('p' * length, api.shortened('p' * length, 500))
        self.assertEqual(500, len(api.shortened('p' * 501, 500)))
        self.assertIsNone(api.shortened(None, 500))

    def test_a_path_the_table_cannot_hold_is_recorded_with_its_characters_written_out(self):
        # A table in an older character set refuses text outside it.
        self.refuse = lambda fields: any(ord(char) > 255 for char in fields['file_path'])
        api.log_file_operation('cp_0123456789ab', 'read', 'wp-content/uploads/\u0645\u06cc\U0001f600.php', True)
        row, = self.rows
        self.assertEqual('wp-content/uploads/\\u0645\\u06cc\\U0001f600.php', row['file_path'])
        self.assertEqual(('read', True), (row['operation'], row['success']))
        api.log_file_operation('cp_0123456789ab', 'read', 'wp-content/' + '\u0645' * 400 + '/x.php', True)
        self.assertEqual(500, len(self.rows[1]['file_path']))
        self.assertTrue(self.rows[1]['file_path'].endswith('\\u0645/x.php'))

    def test_a_table_that_takes_nothing_is_reported_in_the_log_and_stops_no_request(self):
        self.refuse = lambda fields: True
        api.log_file_operation('cp_0123456789ab', 'read', 'index.php', True)
        self.assertEqual([], self.rows)
        self.assertIn('Failed to log operation', self.log.writeToFile.call_args[0][0])
