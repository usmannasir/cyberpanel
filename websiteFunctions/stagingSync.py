"""Checked WordPress staging deployment with a private recovery point."""
import hashlib
import os
import shlex
import uuid
from urllib.parse import urlsplit


class StagingSync:
    def __init__(self, runner, status, backup_root='/var/lib/cyberpanel/sync-backups', wp_cli='/usr/bin/wp'):
        self.wp_cli = wp_cli
        self.runner = runner
        self.status = status
        self.backup_root = backup_root
        self.backup = None

    def command(self, *args):
        # sendCommand otherwise omits sudo for commands containing 'export'.
        if os.geteuid() != 0:
            args = ('sudo',) + args
        result = self.runner(' '.join(shlex.quote(str(arg)) for arg in args),
                             shell=False, retRequired=True)
        if not result or result[0] != 1:
            # Command output can contain SQL or credentials; keep it out of status files.
            raise RuntimeError('Sync command failed (%s). Recovery backup: %s' %
                               (os.path.basename(str(args[0])), self.backup or 'not created'))
        return result[1].strip()

    def run(self, source, target, php, copy_all=False, database=False, copy_changed=False):
        if not any((copy_all, database, copy_changed)) or (copy_all and copy_changed):
            raise ValueError('Choose a database or content sync mode; select only one content mode.')
        source, target = (self.command('readlink', '-f', path) for path in (source, target))
        if not all(os.path.isabs(path) for path in (source, target)):
            raise ValueError('WordPress paths could not be resolved.')
        if source == target:
            raise ValueError('Staging and production paths must differ.')
        for path in (source, target):
            self.command('test', '-f', os.path.join(path, 'wp-config.php'))

        if copy_all or copy_changed:
            source_content = os.path.join(source, 'wp-content')
            target_content = os.path.join(target, 'wp-content')
            if os.path.commonpath([source_content, target_content]) in (source_content, target_content):
                raise ValueError('Staging and production content paths must not overlap.')
            for path in (source, target):
                content = os.path.join(path, 'wp-content')
                if self.command('readlink', '-f', content) != content:
                    raise ValueError('Symlinked WordPress content needs a manual deployment.')
                self.command('test', '-d', content)

        def wp(path, *args):
            return self.command(php, '-d', 'error_reporting=0', self.wp_cli,
                                '--allow-root', '--skip-plugins', '--skip-themes',
                                '--path=' + path, *args)

        self.command('install', '-d', '-m', '700', self.backup_root)
        lock = os.path.join(self.backup_root, 'lock-' + hashlib.sha256(target.encode()).hexdigest())
        self.command('mkdir', '-m', '700', lock)
        try:
            self.backup = os.path.join(self.backup_root, uuid.uuid4().hex)
            self.command('mkdir', '-m', '700', self.backup)
            self.status('Backing up production files and database..,5')
            archive = os.path.join(self.backup, 'production.tar.gz')
            sql = os.path.join(self.backup, 'production.sql')
            self.command('tar', '-czpf', archive, '-C', target, '.')
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
                self.command(*args)
        finally:
            self.command('rmdir', lock)
        self.status('Completed. Recovery backup: %s,[200]' % self.backup)
        return self.backup
