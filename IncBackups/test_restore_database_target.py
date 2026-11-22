"""An incremental restore loads a dump only into a database of the website it was asked for."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from IncBackups.test_database_backup_step import dump_database_name
from plogical.test_child_domain_conversion import load_method
from plogical.test_database_restore_accounts import Rows

SOURCE = 'IncBackups/IncBackupsControl.py'
REGISTERED = Rows([{'dbName': 'shop_db', 'website': 'example.com'}, {'dbName': 'orders', 'website': 'example.com'},
                   {'dbName': 'other_db', 'website': 'other.example'}])


class RestoreTargetTests(unittest.TestCase):
    def job(self, **attributes):
        self.restore = mock.Mock(return_value=1)
        self.commands = []
        namespace = dict(
            os=os, dump_database_name=dump_database_name, mysqlUtilities=SimpleNamespace(mysqlUtilities=SimpleNamespace(restoreDatabaseBackup=self.restore)),
            ProcessUtilities=SimpleNamespace(executioner=lambda command, *a: self.commands.append(command)),
            logging=SimpleNamespace(statusWriter=mock.Mock(), writeToFile=mock.Mock()))
        name_of = load_method(SOURCE, 'IncJobs', 'databaseOfDump', dict(namespace))
        run = load_method(SOURCE, 'IncJobs', 'restoreDatabase', namespace)
        job = SimpleNamespace(website='example.com', statusPath='/dev/null', backupDestinations='s3:bucket',
                              awsFunction=mock.Mock(return_value=1), sftpFunction=mock.Mock(return_value=1),
                              localFunction=mock.Mock(return_value=1), **attributes)
        job.databaseOfDump = lambda name: name_of(job, name)
        with mock.patch('databases.models.Databases', REGISTERED):
            return run(job), job

    def test_remote_restore_refuses_a_database_that_is_not_the_website_s(self):
        for path in ('/usr/local/CyberCP/tmp/other_db.sql', '/usr/local/CyberCP/tmp/mysql.sql', 'cyberpanel.sql',
                     '/x/missing.sql'):
            result, job = self.job(reconstruct='remote', path=path, jobid='abcdef')
            self.assertEqual(0, result, path)
            self.restore.assert_not_called()
            # Nothing is fetched from the remote repository either.
            job.awsFunction.assert_not_called()
            job.sftpFunction.assert_not_called()

    def test_remote_restore_loads_the_website_s_own_database(self):
        result, job = self.job(reconstruct='remote', path='/usr/local/CyberCP/tmp/shop_db.sql', jobid='abcdef')
        self.assertEqual(1, result)
        self.assertEqual('shop_db', self.restore.call_args[0][0])
        job.awsFunction.assert_called_once_with('restore', '', 'abcdef')

    def test_name_is_the_file_name_without_its_ending(self):
        result, job = self.job(reconstruct='remote', path='/usr/local/CyberCP/tmp/orders.sql', jobid='abcdef')
        self.assertEqual(1, result)
        self.assertEqual('orders', self.restore.call_args[0][0])

    def test_recorded_snapshot_is_checked_the_same_way(self):
        snapshot = SimpleNamespace(type='database:other_db', destination='local', snapshotid='abc')
        result, job = self.job(reconstruct='local', jobid=snapshot)
        self.assertEqual(0, result)
        self.restore.assert_not_called()
        job.localFunction.assert_not_called()
        snapshot = SimpleNamespace(type='database:orders', destination='local', snapshotid='abc')
        result, job = self.job(reconstruct='local', jobid=snapshot)
        self.assertEqual(1, result)
        self.assertEqual('orders', self.restore.call_args[0][0])


if __name__ == '__main__':
    unittest.main()
