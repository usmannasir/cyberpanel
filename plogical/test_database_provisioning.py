"""Provisioning failure stages with private real journal files and fake SQL."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical.databaseProvisioning import ProvisioningJournal, ProvisioningError, create_and_register
from plogical.mysqlUtilities import mysqlUtilities


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.website = SimpleNamespace(domain='fixture.example', pk=1)
        self.model = mock.Mock()
        self.model.objects.filter.return_value.exists.return_value = False
        self.utilities = mock.Mock()
        self.utilities.databaseNamesExist.return_value = False
        self.utilities.createDatabase.side_effect = self.create_sql

    def create_sql(self, db, user, password, progress):
        for stage in ('creating_database', 'database_created', 'creating_user_localhost', 'user_created_localhost', 'granting_user_localhost', 'sql_ready'):
            progress(stage)
        return 1

    def create(self, **kwargs):
        return create_and_register('fixture_db', 'fixture_user', 'SECRET-MUST-NOT-BE-PERSISTED',
                                   self.website, self.utilities, self.model,
                                   self.directory.name, None, **kwargs)

    def record(self):
        names = [n for n in os.listdir(self.directory.name) if n.endswith('.json')]
        self.assertEqual(1, len(names))
        path = os.path.join(self.directory.name, names[0])
        self.assertEqual(0o600, os.stat(path).st_mode & 0o777)
        with open(path) as stream:
            return json.load(stream)

    def test_success_records_completion_after_panel_registration(self):
        self.assertEqual((1, 'None'), self.create())
        self.assertEqual('completed', self.record()['stage'])
        self.model.objects.create.assert_called_once_with(website=self.website, dbName='fixture_db', dbUser='fixture_user')
        self.assertNotIn('SECRET', json.dumps(self.record()))

    def test_existing_sql_namespace_is_never_adopted(self):
        self.utilities.databaseNamesExist.return_value = True
        self.assertEqual(0, self.create()[0])
        self.utilities.createDatabase.assert_not_called()
        self.model.objects.create.assert_not_called()

    def test_existing_panel_registration_stops_before_sql(self):
        self.model.objects.filter.return_value.exists.return_value = True
        self.assertEqual(0, self.create()[0])
        self.utilities.databaseNamesExist.assert_not_called()

    def test_failed_sql_stage_stops_registration(self):
        def failure(*args, progress):
            progress('granting_user_localhost')
            return 0
        self.utilities.createDatabase.side_effect = failure
        result = self.create()
        self.assertEqual(0, result[0])
        self.assertIn('granting_user_localhost', result[1])
        self.model.objects.create.assert_not_called()
        self.assertEqual('granting_user_localhost', self.record()['stage'])

    def test_panel_failure_retains_recovery_stage_without_credentials(self):
        self.model.objects.create.side_effect = RuntimeError('SECRET-MUST-NOT-BE-PERSISTED')
        result = self.create()
        self.assertEqual(0, result[0])
        self.assertNotIn('SECRET', result[1])
        self.assertEqual('registering_panel', self.record()['stage'])

    def test_journal_failure_prevents_sql(self):
        with mock.patch.object(ProvisioningJournal, 'record', side_effect=OSError('disk full')):
            self.assertEqual(0, self.create()[0])
        self.utilities.createDatabase.assert_not_called()

    def test_completed_or_crashed_record_never_proves_current_ownership(self):
        for stage in ('completed', 'creating_database', 'registering_panel'):
            with ProvisioningJournal('fixture_db', 'fixture_user', 'old.example', self.directory.name, None) as journal:
                journal.begin(); journal.record(stage)
            self.utilities.databaseNamesExist.return_value = True
            self.assertEqual(0, self.create()[0])
            self.assertEqual(stage, self.record()['stage'])
        self.utilities.createDatabase.assert_not_called()

    def test_delete_recreate_requires_independently_empty_namespaces(self):
        self.assertEqual(1, self.create()[0])
        previous = self.record()['attempt']
        self.assertEqual(1, self.create()[0])
        self.assertEqual(previous, self.record()['previous_attempt'])
        self.assertNotEqual(previous, self.record()['attempt'])
        self.assertEqual(2, self.utilities.databaseNamesExist.call_count)

    def test_database_and_user_locks_reject_concurrent_creation(self):
        with ProvisioningJournal('fixture_db', 'fixture_user', 'fixture.example', self.directory.name, None):
            for db, user in [('fixture_db', 'different_user'), ('different_db', 'fixture_user')]:
                with self.assertRaises(ProvisioningError):
                    with ProvisioningJournal(db, user, 'fixture.example', self.directory.name, None):
                        self.fail('Concurrent creator acquired the namespace')

    def test_invalid_identifier_creates_no_files(self):
        with self.assertRaises(ProvisioningError):
            ProvisioningJournal('../outside', 'fixture_user', 'fixture.example', self.directory.name, None)
        self.assertEqual([], os.listdir(self.directory.name))


class SQLCreationStageTests(unittest.TestCase):
    def test_sql_account_grant_and_loopback_failure_keep_connection_closed_and_fail(self):
        for fails in ('CREATE DATABASE', 'CREATE USER', 'GRANT ALL'):
            connection, cursor = mock.Mock(), mock.Mock()
            def execute(query, args=None):
                if query.startswith(fails):
                    raise RuntimeError('fixture failure')
            cursor.execute.side_effect = execute
            stages = []
            with mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
                self.assertEqual(0, mysqlUtilities.createDatabase('fixture_db', 'fixture_user', 'secret', progress=stages.append))
            connection.close.assert_called_once()
            self.assertNotIn('sql_ready', stages)
            self.assertFalse(any('DROP' in call.args[0] for call in cursor.execute.call_args_list))

    def test_loopback_failure_is_required_for_tracked_creation(self):
        connection, cursor = mock.Mock(), mock.Mock()
        def execute(query, args=None):
            if query.startswith('GRANT') and args[1] == '127.0.0.1':
                raise RuntimeError('fixture loopback grant failure')
        cursor.execute.side_effect = execute
        with mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)), mock.patch.object(mysqlUtilities, 'REMOTEHOST', ''), mock.patch.object(mysqlUtilities, 'LOCALHOST', 'localhost'):
            self.assertEqual(0, mysqlUtilities.createDatabase('fixture_db', 'fixture_user', 'secret', progress=lambda stage: None))
        connection.close.assert_called_once()
