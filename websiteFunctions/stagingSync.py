"""Checked WordPress staging deployment with a private recovery point."""
import fcntl
import hashlib
import os
import shlex
import uuid
from urllib.parse import urlsplit


class StagingSync:
    def __init__(self, runner, status, backup_root='/var/lib/cyberpanel/sync-backups', wp_cli='/usr/bin/wp',
                 lock_root='/home/cyberpanel'):
        self.wp_cli = wp_cli
        self.runner = runner
        self.status = status
        self.backup_root = backup_root
        self.lock_root = lock_root
        self.backup = None

    def run_command(self, args, ok):
        # sendCommand otherwise omits sudo for commands containing 'export'.
        if os.geteuid() != 0:
            args = ('sudo',) + tuple(args)
        return self.runner(' '.join(shlex.quote(str(arg)) for arg in args),
                           shell=False, retRequired=True, okStatuses=ok)

    def command(self, *args, ok=(0,)):
        """Run one command; ok lists the exit statuses that are its normal end."""
        result = self.run_command(args, ok)
        if not result or result[0] != 1:
            # Command output can contain SQL or credentials; keep it out of status files.
            raise RuntimeError('Sync command failed (%s). Recovery backup: %s' %
                               (os.path.basename(str(args[0])), self.backup or 'not created'))
        return result[1].strip()

    def probe(self, *args):
        result = self.run_command(args, (0,))
        return bool(result) and result[0] == 1

    def lock(self, target):
        """Hold one deployment per production site. The lock belongs to this
        process: it ends with the process, so a worker that died cannot leave
        a lock behind that blocks every later deployment."""
        path = os.path.join(self.lock_root, 'staging-sync-%s.lock' % hashlib.sha256(target.encode()).hexdigest())
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            raise RuntimeError('Another deployment to this website is still running. Try again when it has finished.')
        return descriptor

    def run(self, source, target, php, copy_all=False, database=False, copy_changed=False):
        if not any((copy_all, database, copy_changed)) or (copy_all and copy_changed):
            raise ValueError('Choose a database or content sync mode; select only one content mode.')
        source, target = (self.command('readlink', '-f', path) for path in (source, target))
        if not all(os.path.isabs(path) for path in (source, target)):
            raise ValueError('WordPress paths could not be resolved.')
        if source == target:
            raise ValueError('Staging and production paths must differ.')
        for path in (source, target):
            # WordPress also reads wp-config.php from the folder above its root.
            if not any(self.probe('test', '-f', os.path.join(folder, 'wp-config.php'))
                       for folder in (path, os.path.dirname(path))):
                raise ValueError('wp-config.php was not found in %s or the folder above it.' % path)

        if copy_all or copy_changed:
            source_content = os.path.join(source, 'wp-content')
            target_content = os.path.join(target, 'wp-content')
            if os.path.commonpath([source_content, target_content]) in (source_content, target_content):
                raise ValueError('Staging and production content paths must not overlap.')
            for path in (source, target):
                content = os.path.join(path, 'wp-content')
                if self.command('readlink', '-f', content) != content:
                    raise ValueError('Symlinked WordPress content needs a manual deployment.')
                if not self.probe('test', '-d', content):
                    raise ValueError('wp-content was not found in %s.' % path)

        def wp(path, *args):
            return self.command(php, '-d', 'error_reporting=0', self.wp_cli,
                                '--allow-root', '--skip-plugins', '--skip-themes',
                                '--path=' + path, *args)

        self.command('install', '-d', '-m', '700', self.backup_root)
        lock = self.lock(target)
        try:
            self.backup = os.path.join(self.backup_root, uuid.uuid4().hex)
            self.command('mkdir', '-m', '700', self.backup)
            self.status('Backing up production files and database..,5')
            archive = os.path.join(self.backup, 'production.tar.gz')
            sql = os.path.join(self.backup, 'production.sql')
            # A live site changes while it is archived: GNU tar then ends with 1
            # ("file changed as we read it"). The listing below checks the archive.
            self.command('tar', '-czpf', archive, '-C', target, '.', ok=(0, 1))
            self.command('tar', '-tzf', archive)
            wp(target, 'db', 'export', sql, '--single-transaction')
            self.command('test', '-s', sql)
            self.command('chmod', '600', archive, sql)
            self.status('Recovery backup: %s,15' % self.backup)

            if database:
                urls = {}
                for option in ('home', 'siteurl'):
                    urls[option] = wp(target, 'option', 'get', option)
                    parsed = urlsplit(urls[option])
                    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                        raise ValueError('Production WordPress URL is invalid; sync stopped.')
                stage_urls = [wp(source, 'option', 'get', option) for option in ('siteurl', 'home')]
                for value in stage_urls:
                    parsed = urlsplit(value)
                    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                        raise ValueError('Staging WordPress URL is invalid; sync stopped.')
                if stage_urls[0] == stage_urls[1] and urls['siteurl'] != urls['home']:
                    raise ValueError('Staging and production URL layouts differ; use a manual deployment.')
                if wp(source, 'config', 'get', 'table_prefix') != wp(target, 'config', 'get', 'table_prefix'):
                    raise ValueError('WordPress table prefixes differ; use a manual deployment.')
                stage_sql = os.path.join(self.backup, 'staging.sql')
                wp(source, 'db', 'export', stage_sql, '--single-transaction')
                self.command('test', '-s', stage_sql)
                self.command('chmod', '600', stage_sql)
                self.status('Syncing database..,35')
                wp(target, 'db', 'import', stage_sql)
                # Replace full URLs, longest first, so a subdirectory is not replaced twice.
                replacements = dict(zip(stage_urls, (urls['siteurl'], urls['home'])))
                for before, after in sorted(replacements.items(), key=lambda item: -len(item[0])):
                    parsed = urlsplit(before)
                    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                        raise ValueError('Staging WordPress URL is invalid.')
                    suffix = before.split('://', 1)[1]
                    for scheme in ('https://', 'http://'):
                        wp(target, 'search-replace', scheme + suffix, after, '--all-tables-with-prefix', '--precise')
                for option, value in urls.items():
                    wp(target, 'option', 'update', option, value)

            if copy_all or copy_changed:
                self.status('Syncing WordPress content..,65')
                owner = self.command('stat', '-c', '%u:%g', target + '/wp-content')
                if len(owner.split(':')) != 2 or not all(value.isdigit() for value in owner.split(':')):
                    raise ValueError('Could not determine production file ownership.')
                args = ['rsync', '-a', '--chown=' + owner]
                if copy_all:
                    args.append('--delete')
                # Keep production wp-config.php, rewrite rules and server configuration.
                args.extend([source + '/wp-content/', target + '/wp-content/'])
                # 24: a source file vanished during the transfer (a cache file).
                self.command(*args, ok=(0, 24))
        finally:
            os.close(lock)
        self.status('Completed. Recovery backup: %s,[200]' % self.backup)
        return self.backup
