"""Exercise destination API methods without a running CyberPanel installation.

The production methods are compiled from their AST, with SQLite-backed destination
fixtures replacing Django's ORM and SSH execution mocked at the process boundary.
"""
import ast
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical.normalBackupUtilities import normalize_local_backup_path


class DestinationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE destinations (id INTEGER PRIMARY KEY, name TEXT, config TEXT)')
        db = self.db

        class Rows(list):
            def exists(self):
                return bool(self)

        class Destinations:
            def all(self):
                return self.filter()

            def filter(self, **kwargs):
                columns = {'pk': 'id', 'name': 'name'}
                where = ' AND '.join(columns[key] + ' = ?' for key in kwargs)
                query = 'SELECT id, name, config FROM destinations'
                if where:
                    query += ' WHERE ' + where
                return Rows(Destination(name, config, pk) for pk, name, config in db.execute(query, list(kwargs.values())))

            def get(self, **kwargs):
                rows = self.filter(**kwargs)
                if not rows:
                    raise Destination.DoesNotExist()
                if len(rows) != 1:
                    raise ValueError('MultipleObjectsReturned')
                return rows[0]

        class Destination:
            objects = Destinations()
            DoesNotExist = type('DoesNotExist', (Exception,), {})

            def __init__(self, name, config, pk=None):
                self.name, self.config, self.pk = name, config, pk

            def save(self):
                self.pk = db.execute('INSERT INTO destinations (name, config) VALUES (?, ?)',
                                     (self.name, self.config)).lastrowid

            def delete(self):
                db.execute('DELETE FROM destinations WHERE id = ?', (self.pk,))

        self.model = Destination
        self.acl = SimpleNamespace(loadedACL=Mock(return_value={}),
                                   currentContextPermission=Mock(return_value=1),
                                   commandInjectionCheck=Mock(return_value=0),
                                   loadErrorJson=lambda key, value: json.dumps({'status': 0, key: value}))
        self.process = SimpleNamespace(debugPath='/nonexistent/backup-destination-test',
                                       outputExecutioner=Mock(return_value='1,None'))
        methods = {'submitDestinationCreation', 'getCurrentBackupDestinations', 'deleteDestination'}
        path = Path(__file__).with_name('backupManager.py')
        tree = ast.parse(path.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BackupManager')
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in methods]
        namespace = {'json': json, 'os': os, 're': re, 'shlex': shlex, 'HttpResponse': lambda value: value,
                     'ACLManager': self.acl, 'NormalBackupDests': Destination,
                     'ProcessUtilities': self.process,
                     'virtualHostUtilities': SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
                     'normalize_local_backup_path': normalize_local_backup_path}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), namespace)
        self.manager = namespace['BackupManager']()

    def add(self, name='shared', kind='SFTP'):
        row = self.model(name, json.dumps({'type': kind, 'ip': '192.0.2.1', 'username': 'root',
                                          'port': '22', 'path': '/backups'}))
        row.save()
        return row.pk

    def delete(self, **data):
        return json.loads(self.manager.deleteDestination(1, data))

    def ids(self):
        return [row.pk for row in self.model.objects.all()]

    def create(self, name='daily', kind='local'):
        return json.loads(self.manager.submitDestinationCreation(1, {
            'name': name, 'type': kind, 'path': '/backups', 'IPAddress': '192.0.2.1',
            'password': 'password', 'userName': 'root', 'backupSSHPort': '22',
        }))

    def test_selected_duplicate_is_deleted_by_id_for_both_types(self):
        for kind in ('SFTP', 'local'):
            with self.subTest(kind=kind):
                first, second = self.add(kind=kind), self.add(kind=kind)
                response = self.delete(type=kind, nameOrPath='shared', destinationID=second)
                self.assertEqual((1, 1), (response['status'], response['delStatus']))
                self.assertIn(first, self.ids())
                self.assertNotIn(second, self.ids())

    def test_numeric_string_id_is_supported_without_name(self):
        pk = self.add()
        self.assertEqual(1, self.delete(type='SFTP', destinationID=str(pk))['status'])
        self.assertEqual([], self.ids())

    def test_ambiguous_legacy_request_deletes_nothing(self):
        before = [self.add(), self.add()]
        response = self.delete(type='SFTP', nameOrPath='shared')
        self.assertEqual((0, 0), (response['status'], response['delStatus']))
        self.assertIn('Multiple backup destinations', response['error_message'])
        self.assertEqual(before, self.ids())

    def test_legacy_name_is_scoped_to_requested_type(self):
        sftp, local = self.add(), self.add(kind='local')
        self.assertEqual(1, self.delete(type='local', nameOrPath='shared')['status'])
        self.assertEqual([sftp], self.ids())
        self.assertEqual(1, self.delete(type='SFTP', nameOrPath='shared')['status'])
        self.assertEqual([], self.ids())

    def test_invalid_or_stale_id_never_falls_back_to_name(self):
        pk = self.add()
        for destination_id in (None, '', 'bad', True, False, -1, 0, 1.0, '1.0', [], {}, pk + 1):
            with self.subTest(destination_id=destination_id):
                response = self.delete(type='SFTP', nameOrPath='shared', destinationID=destination_id)
                self.assertEqual((0, 0), (response['status'], response['delStatus']))
                self.assertEqual([pk], self.ids())

    def test_wrong_or_missing_type_cannot_delete_selected_row(self):
        pk = self.add()
        for kind in ('local', 'invalid', None):
            with self.subTest(kind=kind):
                self.assertEqual(0, self.delete(type=kind, destinationID=pk)['status'])
                self.assertEqual([pk], self.ids())

    def test_missing_legacy_destination_is_failure(self):
        for data in ({'type': 'SFTP'}, {'type': 'SFTP', 'nameOrPath': 'missing'}):
            response = self.delete(**data)
            self.assertEqual((0, 0), (response['status'], response['delStatus']))

    def test_failed_database_delete_reports_failure_in_both_flags(self):
        pk = self.add()
        self.model.delete = Mock(side_effect=RuntimeError('database unavailable'))
        response = self.delete(type='SFTP', destinationID=pk)
        self.assertEqual((0, 0), (response['status'], response['delStatus']))
        self.assertEqual([pk], self.ids())

    def test_listing_returns_distinct_ids_for_same_name(self):
        sftp_ids = [self.add(), self.add()]
        local_id = self.add(kind='local')
        for kind, expected in (('SFTP', sftp_ids), ('local', [local_id])):
            with self.subTest(kind=kind):
                response = json.loads(self.manager.getCurrentBackupDestinations(1, {'type': kind}))
                records = json.loads(response['data'])
                self.assertEqual(expected, [record['id'] for record in records])
                self.assertTrue(all(record['name'] == 'shared' for record in records))

    def test_existing_names_are_rejected_across_destination_types_before_ssh(self):
        pk = self.add('daily')
        for kind in ('SFTP', 'local'):
            with self.subTest(kind=kind):
                response = self.create(kind=kind)
                self.assertEqual((0, 0), (response['status'], response['destStatus']))
                self.assertIn('already exists', response['error_message'])
                self.assertEqual([pk], self.ids())
        self.process.outputExecutioner.assert_not_called()

    def test_creation_saves_unique_names_for_both_types(self):
        for kind in ('SFTP', 'local'):
            with self.subTest(kind=kind):
                response = self.create(name=kind, kind=kind)
                self.assertEqual((1, 1), (response['status'], response['destStatus']))
                row = self.model.objects.get(name=kind)
                self.assertEqual(kind, json.loads(row.config)['type'])

    def test_blank_names_are_rejected_and_outer_whitespace_is_normalized(self):
        for name in (None, '', '   ', 12):
            with self.subTest(name=name):
                self.assertEqual(0, self.create(name=name)['status'])
        self.assertEqual(1, self.create(name=' daily ')['status'])
        self.assertEqual('daily', self.model.objects.all()[0].name)
        self.assertEqual(0, self.create(name='daily')['status'])

    def test_acl_denial_blocks_creation_listing_and_deletion(self):
        pk = self.add()
        self.acl.currentContextPermission.return_value = 0
        self.assertEqual(0, self.delete(type='SFTP', destinationID=pk)['status'])
        self.assertEqual(0, self.create()['status'])
        self.assertEqual(0, json.loads(self.manager.getCurrentBackupDestinations(1, {'type': 'SFTP'}))['status'])
        self.assertEqual([pk], self.ids())
        self.process.outputExecutioner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
