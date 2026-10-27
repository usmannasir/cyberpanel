"""Opt-in integration: disposable WordPress trees and MariaDB databases only.

CYBERPANEL_SYNC_INTEGRATION=1 PHP_BIN=/path/php WP_CLI=/path/wp-cli.phar
python -m unittest websiteFunctions.test_staging_sync_integration
Requires local MariaDB administrative socket access; always drops owned fixtures.
"""
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import uuid
from websiteFunctions.stagingSync import StagingSync


@unittest.skipUnless(os.environ.get('CYBERPANEL_SYNC_INTEGRATION') == '1', 'opt-in MariaDB/WordPress integration')
class WordPressSyncIntegration(unittest.TestCase):
    def setUp(self):
        self.php = os.environ.get('PHP_BIN', '/usr/bin/php')
        self.cli = os.environ.get('WP_CLI', '/usr/bin/wp')
        self.temp = tempfile.TemporaryDirectory(prefix='cyberpanel-sync-qa-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.target = self.root / 'stage', self.root / 'live'
        self.db_prefix = 'cpsync_' + uuid.uuid4().hex[:12]
        self.db_user = self.db_prefix
        password = secrets.token_hex(20)
        self.sql("CREATE USER '%s'@'localhost' IDENTIFIED BY '%s'" % (self.db_user, password))
        self.addCleanup(self.sql, "DROP USER IF EXISTS '%s'@'localhost'" % self.db_user)
        self.source.mkdir()
        self.wp(self.source, 'core', 'download', '--quiet')
        shutil.copytree(self.source, self.target)
        for path, suffix, url in ((self.source, 'stage', 'http://stage.example'),
                                  (self.target, 'live', 'https://live.example')):
            database = self.db_prefix + '_' + suffix
            self.sql('CREATE DATABASE ' + database)
            self.addCleanup(self.sql, 'DROP DATABASE IF EXISTS ' + database)
            self.sql("GRANT ALL ON `%s`.* TO '%s'@'localhost'" % (database, self.db_user))
            self.wp(path, 'config', 'create', '--dbname=' + database, '--dbuser=' + self.db_user,
                    '--dbpass=' + password, '--dbhost=localhost', '--quiet')
            self.wp(path, 'core', 'install', '--url=' + url, '--title=Disposable QA',
                    '--admin_user=fixture', '--admin_password=' + secrets.token_hex(20),
                    '--admin_email=fixture@example.invalid', '--skip-email', '--quiet')
            self.wp(path, 'option', 'update', 'sync_fixture', suffix)
            self.wp(path, 'option', 'update', 'sync_serialized', json.dumps({'link': url + '/article'}), '--format=json')
            (path / 'wp-content' / 'fixture.txt').write_text(suffix)
        (self.target / '.htaccess').write_text('production rewrite rules')
        (self.source / '.htaccess').write_text('staging rewrite rules')
        (self.target / 'wp-content' / 'live-only.txt').write_text('keep unless replacing')
        self.status = []

    def sql(self, query):
        subprocess.run(['mariadb', '-e', query], check=True, capture_output=True)

    def wp(self, path, *args):
        return subprocess.check_output([self.php, "-d", "memory_limit=512M", self.cli, '--allow-root', '--skip-plugins',
                                        '--skip-themes', '--path=' + str(path), *args],
                                       stderr=subprocess.PIPE, text=True).strip()

    def runner(self, command, **kwargs):
        from plogical.processUtilities import ProcessUtilities
        return ProcessUtilities.outputExecutioner(command, **kwargs)

    def worker(self, runner=None):
        return StagingSync(runner or self.runner, self.status.append,
                           str(self.root / 'private-backups'), self.cli)

    def test_full_sync_and_restore_preserve_urls_and_configuration(self):
        old_config = (self.target / 'wp-config.php').read_bytes()
        backup = Path(self.worker().run(str(self.source), str(self.target), self.php,
                                       database=True, copy_all=True))
        self.assertEqual('stage', self.wp(self.target, 'option', 'get', 'sync_fixture'))
        for option in ('home', 'siteurl'):
            self.assertEqual('https://live.example', self.wp(self.target, 'option', 'get', option))
        self.assertEqual({'link': 'https://live.example/article'},
                         json.loads(self.wp(self.target, 'option', 'get', 'sync_serialized', '--format=json')))
        self.assertEqual('stage', (self.target / 'wp-content' / 'fixture.txt').read_text())
        self.assertFalse((self.target / 'wp-content' / 'live-only.txt').exists())
        self.assertEqual(old_config, (self.target / 'wp-config.php').read_bytes())
        self.assertEqual('production rewrite rules', (self.target / '.htaccess').read_text())
        self.assertEqual(0o700, backup.stat().st_mode & 0o777)
        self.assertEqual(0o600, (backup / 'production.sql').stat().st_mode & 0o777)
        self.assertEqual([], list(self.target.rglob('*.sql')))
        self.wp(self.target, 'db', 'import', str(backup / 'production.sql'))
        shutil.rmtree(self.target)
        self.target.mkdir()
        with tarfile.open(backup / 'production.tar.gz') as archive:
            archive.extractall(self.target)
        self.assertEqual('live', self.wp(self.target, 'option', 'get', 'sync_fixture'))
        self.assertEqual('https://live.example', self.wp(self.target, 'option', 'get', 'home'))
        self.assertEqual('live', (self.target / 'wp-content' / 'fixture.txt').read_text())
        self.assertTrue((self.target / 'wp-content' / 'live-only.txt').exists())

    def test_database_only_does_not_copy_files(self):
        self.worker().run(str(self.source), str(self.target), self.php, database=True)
        self.assertEqual('stage', self.wp(self.target, 'option', 'get', 'sync_fixture'))
        self.assertEqual('live', (self.target / 'wp-content' / 'fixture.txt').read_text())

    def test_content_merge_preserves_database_and_production_only_files(self):
        self.worker().run(str(self.source), str(self.target), self.php, copy_changed=True)
        self.assertEqual('live', self.wp(self.target, 'option', 'get', 'sync_fixture'))
        self.assertEqual('stage', (self.target / 'wp-content' / 'fixture.txt').read_text())
        self.assertTrue((self.target / 'wp-content' / 'live-only.txt').exists())

    def test_backup_failure_leaves_production_untouched(self):
        def fail_archive(command, **kwargs):
            if shlex.split(command)[:2] == ['tar', '-czpf']:
                return 0, 'simulated full backup disk'
            return self.runner(command, **kwargs)
        with self.assertRaises(RuntimeError):
            self.worker(fail_archive).run(str(self.source), str(self.target), self.php,
                                          database=True, copy_all=True)
        self.assertEqual('live', self.wp(self.target, 'option', 'get', 'sync_fixture'))
        self.assertEqual('live', (self.target / 'wp-content' / 'fixture.txt').read_text())
        self.assertEqual('https://live.example', self.wp(self.target, 'option', 'get', 'home'))
        self.assertFalse(any('[200]' in message for message in self.status))


if __name__ == '__main__':
    unittest.main()
