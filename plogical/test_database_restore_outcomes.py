import json
import unittest
from types import SimpleNamespace
from unittest import mock
from plogical import mysqlUtilities as module
from plogical.mysqlUtilities import mysqlUtilities


class DatabaseRestoreOutcomeTests(unittest.TestCase):
    def test_foreign_registration_stops_before_sql_access(self):
        website = SimpleNamespace(pk=1)
        foreign = SimpleNamespace(website_id=2, dbUser='fixture_user')
        with mock.patch.object(module.Databases.objects, 'filter') as rows, mock.patch.object(mysqlUtilities, 'setupConnection') as connect:
            rows.return_value.first.return_value = foreign
            self.assertEqual(0, mysqlUtilities.prepareDatabaseForRestore('fixture_db', 'fixture_user', website)[0])
        connect.assert_not_called()

    def test_registration_with_missing_sql_is_not_recreated_or_adopted(self):
        website = SimpleNamespace(pk=1)
        connection, cursor = mock.Mock(), mock.Mock()
        cursor.fetchall.return_value = []
        with mock.patch.object(module.Databases.objects, 'filter') as rows, mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)), mock.patch.object(mysqlUtilities, 'createDatabaseAndRegister') as create:
            rows.return_value.first.return_value = SimpleNamespace(website_id=1, dbUser='fixture_user')
            self.assertEqual(0, mysqlUtilities.prepareDatabaseForRestore('fixture_db', 'fixture_user', website)[0])
        create.assert_not_called()
        connection.close.assert_called_once()

    def test_new_restore_uses_durable_creation(self):
        website = SimpleNamespace(pk=1)
        with mock.patch.object(module.Databases.objects, 'filter') as rows, mock.patch.object(mysqlUtilities, 'createDatabaseAndRegister', return_value=(0, 'failed')) as create:
            rows.return_value.first.return_value = None
            self.assertEqual((0, 'failed'), mysqlUtilities.prepareDatabaseForRestore('fixture_db', 'fixture_user', website))
        create.assert_called_once_with('fixture_db', 'fixture_user', 'cyberpanel', website)

    def test_existing_account_without_database_grant_is_preserved(self):
        connection, cursor = mock.Mock(), mock.Mock()
        cursor.fetchall.side_effect = [[('fixture_user',)], [('different_db',)]]
        with mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)), mock.patch.object(mysqlUtilities, 'changePassword') as password:
            self.assertEqual(0, mysqlUtilities.restoreDatabaseUser('fixture_db', 'fixture_user', 'hash', 'localhost'))
        password.assert_not_called()
        connection.close.assert_called_once()

    def restore(self, compressed=False, mysql_rc=0, gzip_rc=0):
        config = json.dumps({'mysqluser': 'root', 'mysqlpassword': 'fixture', 'mysqlport': 3306, 'mysqlhost': 'localhost'})
        importer = mock.Mock(returncode=mysql_rc)
        decompressor = mock.Mock(returncode=gzip_rc)
        with mock.patch('builtins.open', mock.mock_open(read_data=config)), mock.patch.object(module.os.path, 'exists', return_value=True), mock.patch.object(mysqlUtilities, 'detectBackupFormat', return_value={'compressed': compressed}), mock.patch.object(module.subprocess, 'Popen', side_effect=[decompressor, importer]), mock.patch.object(module.subprocess, 'call', return_value=mysql_rc), mock.patch.object(mysqlUtilities, 'setupConnection') as connection:
            result = mysqlUtilities.restoreDatabaseBackup('fixture_db', '/fixture', 'hash', passwordCheck=1)
        connection.assert_not_called()
        return result

    def test_plain_import_failure_is_not_success(self):
        self.assertEqual(0, self.restore(mysql_rc=1))
        self.assertEqual(1, self.restore())

    def test_compressed_import_requires_both_processes_to_succeed(self):
        for mysql_rc, gzip_rc, expected in [(0, 0, 1), (1, 0, 0), (0, 1, 0), (1, 1, 0)]:
            self.assertEqual(expected, self.restore(True, mysql_rc, gzip_rc))
