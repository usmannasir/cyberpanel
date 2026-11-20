"""A Backup V2 schedule holds only values the scheduled job can use safely as root."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical.backupV2Repository import forget_selection, retention_days, schedule_entry
from plogical.test_child_domain_conversion import load_method

ROOT = Path(__file__).resolve().parents[1]


class ScheduleValueTests(unittest.TestCase):
    def test_form_values_are_kept(self):
        self.assertEqual(
            {'repo': 'local', 'retention': '30', 'frequency': '1 Day', 'websiteData': True,
             'websiteEmails': False, 'websiteDatabases': True, 'lastRun': ''},
            schedule_entry('local', '1 Day', '30', True, True, False))
        self.assertEqual('7', schedule_entry('my-s3 bucket', '1 Week', 7, False, False, True)['retention'])

    def test_retention_is_a_whole_number_of_days(self):
        for value in ('1', '30', 3, '3650'):
            self.assertEqual(int(value), retention_days(value))
        for value in ('7; id', '7 --prune', ["x' $(id)"], {'a': '$(id)'}, '', None, True, 1.5, '0', 0, '-1',
                      '36500', ' 7', '7\n'):
            with self.assertRaises(ValueError, msg=repr(value)):
                retention_days(value)

    def test_other_values_are_checked(self):
        for arguments in (
                ('local; id', '1 Day', '7', True, True, True),
                (['local'], '1 Day', '7', True, True, True),
                ('local', 'Every minute', '7', True, True, True),
                ('local', ['1 Day'], '7', True, True, True),
        ):
            with self.assertRaises(ValueError, msg=repr(arguments)):
                schedule_entry(*arguments)
        entry = schedule_entry('local', '1 Day', '7', 'yes', ['x'], 1)
        self.assertEqual([False, False, False],
                         [entry['websiteData'], entry['websiteDatabases'], entry['websiteEmails']])

    def test_what_may_be_forgotten(self):
        for value in ('--keep-daily 7', '--keep-daily 3650', 'abcdef0123456789', '1a2b3c4d'):
            self.assertEqual(value, forget_selection(value))
        for value in ('--keep-daily 7; id', "--keep-daily ['x']", '--keep-daily $(id)', 'abcdef01 --prune',
                      'abcdef01; id', '', None, ['abcdef01'], '--keep-daily 7\n'):
            with self.assertRaises(ValueError, msg=repr(value)):
                forget_selection(value)


class ScheduleStorageTests(unittest.TestCase):
    def create(self, *arguments):
        written = {}

        class Handle:
            def write(self, content):
                written['content'] = content

            def close(self):
                pass

        commands = Mock()
        create = load_method('plogical/Backupsv2.py', 'CPBackupsV2', 'CreateScheduleV2', dict(
            os=SimpleNamespace(path=SimpleNamespace(exists=lambda path: path.endswith('/'))),
            ProcessUtilities=commands, json=json, open=lambda *a, **k: Handle(),
            schedule_entry=schedule_entry, print=lambda *a, **k: None))
        return create(*arguments), written, commands

    def test_hostile_retention_is_never_written(self):
        (status, message), written, commands = self.create(
            'example.com', 'local', '1 Week', True, True, True, ["x' $(id)"])
        self.assertEqual(0, status)
        self.assertEqual({}, written)

    def test_ordinary_schedule_is_written(self):
        (status, config), written, commands = self.create('example.com', 'local', '1 Week', True, True, False, '30')
        self.assertEqual(1, status)
        self.assertEqual([{'repo': 'local', 'retention': '30', 'frequency': '1 Week', 'websiteData': True,
                           'websiteEmails': False, 'websiteDatabases': True, 'lastRun': ''}],
                         json.loads(written['content'])['schedules'])


class ScheduledJobTests(unittest.TestCase):
    def test_job_and_delete_button_pass_only_checked_values(self):
        scheduler = (ROOT / 'plogical' / 'IncScheduler.py').read_text()
        self.assertNotIn('''f"--keep-daily {value['retention']}"''', scheduler)
        self.assertIn("""'--keep-daily %d' % retention_days(value['retention']))""", scheduler)
        engine = (ROOT / 'plogical' / 'Backupsv2.py').read_text()
        self.assertIn('forget {forget_selection(deleteString)} --prune', engine)


if __name__ == '__main__':
    unittest.main()
