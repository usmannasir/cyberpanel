import fcntl
import os
import shlex
import tempfile
import unittest
from unittest import mock
from websiteFunctions.stagingSync import StagingSync


class SyncTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("websiteFunctions.stagingSync.os.geteuid", return_value=0)
        patcher.start()
        self.addCleanup(patcher.stop)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.locks = holder.name

    def setup_worker(self, fail=None, source_url='http://stage.example', status_of=None):
        """fail(args): the command fails. status_of(args): its exit status, judged
        against the statuses the worker accepts, as outputExecutioner does."""
        commands, status = [], []
        def runner(command, **kwargs):
            args = shlex.split(command)
            commands.append(args)
            if fail and fail(args):
                return 0, 'sensitive failure detail'
            if status_of and status_of(args) not in kwargs.get('okStatuses', (0,)):
                return 0, 'sensitive failure detail'
            if args[0] == 'readlink':
                return 1, args[-1]
            if args[0] == 'stat':
                return 1, '1001:1001'
            if 'option' in args and 'get' in args:
                return 1, source_url if '--path=/stage' in args else 'https://live.example'
            return 1, 'OK'
        return StagingSync(runner, status.append, '/private-backup', lock_root=self.locks), commands, status

    def lock_is_free(self):
        for name in os.listdir(self.locks):
            descriptor = os.open(os.path.join(self.locks, name), os.O_RDWR)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            finally:
                os.close(descriptor)
        return True

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
            self.assertTrue(self.lock_is_free())

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
        first, _, _ = self.setup_worker()
        held = first.lock('/live')
        self.addCleanup(os.close, held)
        worker, commands, _ = self.setup_worker()
        with self.assertRaisesRegex(RuntimeError, 'still running'):
            worker.run('/stage', '/live', '/php', database=True)
        self.assertFalse(any(a[0] in ('tar', 'rsync') or 'import' in a for a in commands))
        self.assertFalse(self.lock_is_free())
        # Another website is not blocked.
        self.setup_worker()[0].run('/stage', '/other', '/php', database=True)

    def test_lock_of_a_worker_that_died_does_not_block_the_next_deployment(self):
        worker, _, _ = self.setup_worker()
        os.close(worker.lock('/live'))  # the descriptor ends with its process
        worker, commands, status = self.setup_worker()
        worker.run('/stage', '/live', '/php', database=True)
        self.assertTrue(status[-1].endswith('[200]'))
        self.assertTrue(self.lock_is_free())

    def test_live_site_archive_and_vanished_cache_files_are_normal(self):
        # tar 1: a file changed while it was read; rsync 24: a source file vanished.
        normal = lambda a: {'tar': 1 if '-czpf' in a else 0, 'rsync': 24}.get(a[0], 0)
        worker, commands, status = self.setup_worker(status_of=normal)
        worker.run('/stage', '/live', '/php', database=True, copy_all=True)
        self.assertTrue(status[-1].endswith('[200]'))
        for failing in ({'tar': 2}, {'rsync': 23}, {'rsync': 11}):
            worker, commands, status = self.setup_worker(
                status_of=lambda a, codes=failing: codes.get(a[0], 0) if '-tzf' not in a else 0)
            with self.assertRaises(RuntimeError):
                worker.run('/stage', '/live', '/php', database=True, copy_all=True)
            self.assertFalse(any('[200]' in line for line in status))
        # Every other command still needs exit status 0.
        worker, commands, _ = self.setup_worker(status_of=lambda a: 1 if 'import' in a else 0)
        with self.assertRaises(RuntimeError):
            worker.run('/stage', '/live', '/php', database=True)

    def test_wp_config_in_the_folder_above_the_wordpress_root_is_accepted(self):
        above = lambda a: a[:2] == ['test', '-f'] and a[2] in ('/live/wp-config.php', '/stage/wp-config.php')
        worker, commands, status = self.setup_worker(fail=above)
        worker.run('/stage', '/live', '/php', database=True)
        self.assertTrue(status[-1].endswith('[200]'))
        self.assertIn(['test', '-f', '/wp-config.php'], commands)
        worker, commands, _ = self.setup_worker(fail=lambda a: a[:2] == ['test', '-f'])
        with self.assertRaisesRegex(ValueError, 'wp-config.php was not found in /stage'):
            worker.run('/stage', '/live', '/php', database=True)
        self.assertFalse(any(a[0] == 'tar' for a in commands))

    def test_missing_wp_content_is_named(self):
        worker, commands, _ = self.setup_worker(fail=lambda a: a[:2] == ['test', '-d'])
        with self.assertRaisesRegex(ValueError, 'wp-content was not found in /stage'):
            worker.run('/stage', '/live', '/php', copy_all=True)
        self.assertFalse(any(a[0] in ('tar', 'rsync') for a in commands))

    def test_a_failure_names_the_program_not_sudo(self):
        worker, _, _ = self.setup_worker(fail=lambda a: 'tar' in a)
        with mock.patch('websiteFunctions.stagingSync.os.geteuid', return_value=1000):
            with self.assertRaisesRegex(RuntimeError, r'\(tar\)'):
                worker.command('tar', '-czpf', '/private/a.tar.gz')

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
