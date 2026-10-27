import shlex
import unittest
from unittest import mock
from websiteFunctions.stagingSync import StagingSync


class SyncTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("websiteFunctions.stagingSync.os.geteuid", return_value=0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def setup_worker(self, fail=None, source_url='http://stage.example'):
        commands, status = [], []
        def runner(command, **kwargs):
            args = shlex.split(command)
            commands.append(args)
            if fail and fail(args):
                return 0, 'sensitive failure detail'
            if args[0] == 'readlink':
                return 1, args[-1]
            if args[0] == 'stat':
                return 1, '1001:1001'
            if 'option' in args and 'get' in args:
                return 1, source_url if '--path=/stage' in args else 'https://live.example'
            return 1, 'OK'
        return StagingSync(runner, status.append, '/private-backup'), commands, status

    def test_backup_precedes_import_and_preserves_https(self):
        worker, commands, status = self.setup_worker()
        worker.run('/stage', '/live', '/php', database=True, copy_all=True)
        imported = next(i for i, args in enumerate(commands) if 'import' in args)
        backup_checked = next(i for i, args in enumerate(commands) if args[:2] == ['test', '-s'])
        self.assertLess(backup_checked, imported)
        updates = [args for args in commands if 'update' in args]
        self.assertEqual(['https://live.example'] * 2, [args[-1] for args in updates])
        self.assertTrue(any('--delete' in args for args in commands))
        self.assertTrue(status[-1].endswith('[200]'))
        self.assertTrue(all('/live/' not in arg for args in commands if 'export' in args for arg in args[-1:]))

    def test_backup_failure_never_mutates_production(self):
        for failure in (lambda a: a[:2] == ['tar', '-czpf'],
                        lambda a: a[:2] == ['tar', '-tzf'],
                        lambda a: 'export' in a,
                        lambda a: a[:2] == ['test', '-s']):
            worker, commands, status = self.setup_worker(failure)
            with self.assertRaises(RuntimeError):
                worker.run('/stage', '/live', '/php', database=True, copy_all=True)
            self.assertFalse(any('import' in a or a[0] == 'rsync' for a in commands))
            self.assertFalse(any('[200]' in line for line in status))
            self.assertEqual('rmdir', commands[-1][0])

    def test_content_only_never_imports_or_rewrites_database(self):
        worker, commands, _ = self.setup_worker()
        worker.run('/stage', '/live', '/php', copy_changed=True)
        self.assertFalse(any('import' in a or 'search-replace' in a for a in commands))
        rsync = next(a for a in commands if a[0] == 'rsync')
        self.assertNotIn('--delete', rsync)
        self.assertEqual(['/stage/wp-content/', '/live/wp-content/'], rsync[-2:])

    def test_database_only_never_copies_files(self):
        worker, commands, _ = self.setup_worker()
        worker.run('/stage', '/live', '/php', database=True)
        self.assertFalse(any(a[0] == 'rsync' for a in commands))

    def test_invalid_options_or_same_path_fail_before_commands(self):
        for options in ({}, {'copy_all': True, 'copy_changed': True}):
            worker, commands, _ = self.setup_worker()
            with self.assertRaises(ValueError):
                worker.run('/stage', '/live', '/php', **options)
            self.assertEqual([], commands)
        worker, commands, _ = self.setup_worker()
        with self.assertRaises(ValueError):
            worker.run('/live', '/live', '/php', database=True)
        self.assertTrue(all(args[0] == 'readlink' for args in commands))

    def test_invalid_staging_url_fails_before_import(self):
        worker, commands, _ = self.setup_worker(source_url='invalid')
        with self.assertRaises(ValueError):
            worker.run('/stage', '/live', '/php', database=True)
        self.assertFalse(any('import' in a for a in commands))

    def test_failed_import_never_reports_success_or_copies_files(self):
        worker, commands, status = self.setup_worker(lambda a: 'import' in a)
        with self.assertRaisesRegex(RuntimeError, 'Recovery backup'):
            worker.run('/stage', '/live', '/php', database=True, copy_all=True)
        self.assertFalse(any(a[0] == 'rsync' for a in commands))
        self.assertFalse(any('[200]' in line for line in status))

    def test_busy_lock_never_mutates_site_or_removes_other_lock(self):
        worker, commands, _ = self.setup_worker(lambda a: a[0] == 'mkdir' and '/lock-' in a[-1])
        with self.assertRaises(RuntimeError):
            worker.run('/stage', '/live', '/php', database=True)
        self.assertFalse(any(a[0] in ('tar', 'rmdir', 'rsync') for a in commands))

    def test_nonroot_transport_quotes_arguments_and_keeps_sudo_for_export(self):
        from plogical.processUtilities import ProcessUtilities
        with mock.patch('websiteFunctions.stagingSync.os.geteuid', return_value=1000), \
             mock.patch('plogical.processUtilities.getpass.getuser', return_value='cyberpanel'), \
             mock.patch.object(ProcessUtilities, 'sendCommand', return_value='done\x00') as transport:
            worker = StagingSync(ProcessUtilities.outputExecutioner, lambda message: None)
            self.assertEqual('done', worker.command('/php', 'db', 'export', '/private/a b.sql'))
            self.assertEqual(['sudo', '/php', 'db', 'export', '/private/a b.sql'],
                             shlex.split(transport.call_args.args[0]))
            transport.return_value = 'failure\x01'
            with self.assertRaises(RuntimeError):
                worker.command('tar', '-czpf', '/private/a b.tar.gz')

    def test_overlapping_content_or_different_database_prefixes_fail_closed(self):
        worker, commands, _ = self.setup_worker()
        with self.assertRaises(ValueError):
            worker.run('/live/wp-content/stage', '/live', '/php', copy_all=True)
        self.assertFalse(any(a[0] == 'rsync' for a in commands))
        worker, commands, _ = self.setup_worker()
        original = worker.runner
        def different_prefix(command, **kwargs):
            args = shlex.split(command)
            if args[-3:] == ['config', 'get', 'table_prefix']:
                commands.append(args)
                return 1, 'stage_' if '--path=/stage' in args else 'live_'
            return original(command, **kwargs)
        worker.runner = different_prefix
        with self.assertRaisesRegex(ValueError, 'table prefixes'):
            worker.run('/stage', '/live', '/php', database=True)
        self.assertFalse(any('import' in a for a in commands))

    def test_ambiguous_url_topology_fails_before_import(self):
        worker, commands, _ = self.setup_worker()
        original = worker.runner
        def different_layout(command, **kwargs):
            args = shlex.split(command)
            if '--path=/live' in args and args[-3:] == ['option', 'get', 'siteurl']:
                commands.append(args)
                return 1, 'https://live.example/wordpress'
            return original(command, **kwargs)
        worker.runner = different_layout
        with self.assertRaisesRegex(ValueError, 'URL layouts'):
            worker.run('/stage', '/live', '/php', database=True)
        self.assertFalse(any('import' in a for a in commands))


if __name__ == '__main__':
    unittest.main()
