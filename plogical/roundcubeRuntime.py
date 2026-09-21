"""Root-only installer for the optional, isolated Roundcube runtime.

Only fixed operations are accepted. Mailbox credentials never enter this process.
The application is reachable through Django/FastCGI, not a public PHP directory.
"""
import fcntl
from contextlib import contextmanager, closing
import glob
import hashlib
import json
import os
from pathlib import Path
import pwd
import grp
import secrets
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

VERSION = '1.7.4'
SHA256 = '2c6c878f0093f1bf7fb6086781d2dd9269d652c016b86939c157c5f1729139a2'
URL = f'https://github.com/roundcube/roundcubemail/releases/download/{VERSION}/roundcubemail-{VERSION}-complete.tar.gz'
ROOT = Path('/usr/local/CyberPanelRoundcube')
DATA = Path('/var/lib/cyberpanel-roundcube')
CONFIG = Path('/etc/cyberpanel/roundcube')
STATE = CONFIG / 'state.json'
ENABLED = CONFIG / 'enabled'
SOCKET = '/run/cyberpanel-roundcube/php.sock'
SERVICE = 'cyberpanel-roundcube.service'
MASTER_LOG_DIR = Path('/var/log/cyberpanel-roundcube')
UNIT = Path('/etc/systemd/system') / SERVICE
USER = 'cp-roundcube'
MAX_ARCHIVE = 32 * 1024 * 1024


def write_atomic(path, content, mode=0o644):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=str(path.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def status(phase, message, **extra):
    value = {'phase': phase, 'message': message, 'version': installed_version(), **extra}
    write_atomic(STATE, json.dumps(value))


def installed_version():
    try:
        return (ROOT / 'current').resolve(strict=True).name
    except OSError:
        return None


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, timeout=kwargs.pop('timeout', 180),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)


def find_php():
    pairs = [(p, p.replace('/sbin/php-fpm', '/bin/php'))
             for p in sorted(glob.glob('/usr/sbin/php-fpm[0-9]*'), reverse=True)]
    pairs += [('/usr/sbin/php-fpm', '/usr/bin/php')]
    for fpm, cli in pairs:
        if not (os.path.isfile(fpm) and os.path.isfile(cli)):
            continue
        result = run([cli, '-r', 'echo PHP_VERSION_ID;']).stdout.decode().strip()
        if result.isdigit() and 80100 <= int(result) < 80600:
            modules = run([cli, '-m']).stdout.decode().lower().split()
            required = {'ctype', 'dom', 'fileinfo', 'filter', 'iconv', 'intl', 'mbstring',
                        'openssl', 'pdo', 'pdo_sqlite', 'session', 'xml', 'zip'}
            if required.issubset(modules):
                return fpm, cli
    raise RuntimeError('Install system PHP 8.1–8.5 FPM/CLI with mbstring, intl, XML, zip and SQLite extensions. See the Roundcube setup guide.')


def checked_extract(archive, destination):
    """Extract regular files/directories only; reject traversal and special files."""
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        total = 0
        prefix = f'roundcubemail-{VERSION}'
        for member in members:
            parts = Path(member.name).parts
            if (not parts or parts[0] != prefix or '..' in parts or
                    member.name.startswith('/') or not (member.isfile() or member.isdir())):
                raise RuntimeError('The Roundcube archive contains an unsafe entry.')
            total += member.size
            if total > 160 * 1024 * 1024 or len(members) > 15000:
                raise RuntimeError('The Roundcube archive is too large.')
        for member in members:
            target = Path(destination).joinpath(*Path(member.name).parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
            else:
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                with bundle.extractfile(member) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o644)


def download(target):
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(URL, timeout=60) as response, open(target, 'wb') as output:
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_ARCHIVE:
                raise RuntimeError('The Roundcube download is too large.')
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != SHA256:
        raise RuntimeError('Roundcube download checksum verification failed.')


def php_config():
    # The key is generated once, retained across upgrades, and never returned by APIs.
    key_path = CONFIG / 'key'
    if not key_path.exists():
        write_atomic(key_path, secrets.token_hex(12), 0o600)
    key = key_path.read_text().strip()
    if len(key) != 24 or any(c not in '0123456789abcdef' for c in key):
        raise RuntimeError('Invalid Roundcube encryption key; restore the saved configuration.')
    values = {
        'db_dsnw': f'sqlite:///{DATA}/roundcube.sqlite?mode=0640',
        'imap_host': '127.0.0.1:143',
        'smtp_host': '127.0.0.1:25',
        'smtp_user': '%u', 'smtp_pass': '%p',
        'des_key': key, 'product_name': 'Roundcube for CyberPanel',
        'temp_dir': str(DATA / 'temp'), 'log_dir': str(DATA / 'logs'),
        'session_name': 'cp_roundcube_session', 'session_auth_name': 'cp_roundcube_auth',
        'session_path': '/roundcube/', 'session_samesite': 'Lax',
        'request_path': '/roundcube/', 'login_username_filter': 'email',
        'skin': 'elastic',
    }
    lines = ['<?php']
    for name, value in values.items():
        lines.append("$config[%s] = %s;" % (repr(name), repr(value)))
    lines += ["$config['enable_installer'] = false;", "$config['force_https'] = true;",
              "$config['plugins'] = [];", "$config['login_rate_limit'] = 5;",
              "$config['session_lifetime'] = 30;", "$config['log_driver'] = 'file';",
              "$config['smtp_log'] = false;", "$config['ip_check'] = true;"]
    return '\n'.join(lines) + '\n'


def service_config(fpm):
    return f'''[Unit]
Description=CyberPanel optional Roundcube PHP runtime
After=network.target dovecot.service postfix.service
[Service]
Type=simple
ExecStart={fpm} --nodaemonize --fpm-config {CONFIG}/fpm.conf
Restart=on-failure
RuntimeDirectory=cyberpanel-roundcube
RuntimeDirectoryMode=0755
LogsDirectory=cyberpanel-roundcube
LogsDirectoryMode=0700
UMask=0077
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={DATA} /run/cyberpanel-roundcube {MASTER_LOG_DIR}
NoNewPrivileges=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
[Install]
WantedBy=multi-user.target
'''


def pool_config():
    return f'''[global]
error_log = {MASTER_LOG_DIR}/fpm.log
daemonize = no
[roundcube]
user = {USER}
group = {USER}
listen = {SOCKET}
listen.owner = cyberpanel
listen.group = cyberpanel
listen.mode = 0600
pm = ondemand
pm.max_children = 8
pm.process_idle_timeout = 20s
pm.max_requests = 500
request_terminate_timeout = 120s
catch_workers_output = yes
clear_env = yes
security.limit_extensions = .php
php_admin_flag[display_errors] = off
php_admin_flag[log_errors] = on
php_admin_value[error_log] = {DATA}/logs/php-errors.log
php_admin_value[memory_limit] = 256M
php_admin_value[upload_max_filesize] = 20M
php_admin_value[post_max_size] = 24M
php_admin_value[upload_tmp_dir] = {DATA}/temp
php_admin_value[session.save_path] = {DATA}/sessions
php_admin_flag[session.cookie_secure] = on
php_admin_flag[session.cookie_httponly] = on
php_admin_value[session.cookie_samesite] = Lax
php_admin_value[cgi.fix_pathinfo] = 0
php_admin_value[expose_php] = Off
'''


@contextmanager
def runtime_identity(identity):
    """Never open the runtime user's writable database as root."""
    original_uid, original_gid = os.geteuid(), os.getegid()
    original_groups = os.getgroups()
    try:
        os.setgroups([identity.pw_gid])
        os.setegid(identity.pw_gid)
        os.seteuid(identity.pw_uid)
        yield
    finally:
        os.seteuid(original_uid)
        os.setegid(original_gid)
        os.setgroups(original_groups)


def with_directory_owner(path, identity):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fchown(descriptor, identity.pw_uid, identity.pw_gid)
        os.fchmod(descriptor, 0o700)
    finally:
        os.close(descriptor)


def ensure_identity():
    try:
        identity = pwd.getpwnam(USER)
    except KeyError:
        run(['useradd', '--system', '--home-dir', str(DATA), '--shell', '/usr/sbin/nologin', USER])
        identity = pwd.getpwnam(USER)
    # Refuse a pre-existing privileged account or changed runtime directory owner.
    if identity.pw_uid == 0 or identity.pw_gid == 0:
        raise RuntimeError('Roundcube runtime account must be unprivileged.')
    grp.getgrnam('cyberpanel')
    if DATA.is_symlink():
        raise RuntimeError('Roundcube data directory must not be a symlink.')
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    with_directory_owner(DATA, identity)
    for name in ('temp', 'logs', 'sessions'):
        target = DATA / name
        if target.is_symlink():
            raise RuntimeError('Roundcube data directories must not be symlinks.')
        target.mkdir(mode=0o700, exist_ok=True)
        with_directory_owner(target, identity)
    return identity


def backup_database(database, identity):
    """Create a verified backup without root opening a PHP-writable path."""
    with tempfile.TemporaryDirectory(prefix='.backup-', dir=ROOT) as staging:
        stage = Path(staging)
        os.chown(stage, identity.pw_uid, identity.pw_gid)
        staged_db = stage / 'database.sqlite'
        with runtime_identity(identity), closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(staged_db)) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise RuntimeError('Roundcube database backup verification failed; update cancelled.')
        # Revoke runtime traversal before opening the generated regular file.
        os.chown(stage, 0, 0)
        stage.chmod(0o700)
        descriptor = os.open(staged_db, os.O_RDONLY | os.O_NOFOLLOW)
        backup = None
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != identity.pw_uid:
                raise RuntimeError('Unsafe Roundcube backup file; update cancelled.')
            fd, filename = tempfile.mkstemp(prefix='pre-update-', suffix='.sqlite', dir=ROOT)
            backup = Path(filename)
            with os.fdopen(fd, 'wb') as output, os.fdopen(descriptor, 'rb') as source:
                descriptor = None
                shutil.copyfileobj(source, output)
                output.flush()
                os.fsync(output.fileno())
            # Validate the root-owned snapshot, not merely the runtime staging copy.
            with closing(sqlite3.connect(backup.as_uri() + '?mode=ro&immutable=1', uri=True)) as saved:
                if saved.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                    raise RuntimeError('Roundcube backup verification failed; update cancelled.')
            return backup
        except Exception:
            if backup is not None:
                backup.unlink(missing_ok=True)
            raise
        finally:
            if descriptor is not None:
                os.close(descriptor)


def ensure_master_log():
    """Keep the root FPM master's log outside the PHP user's writable tree."""
    MASTER_LOG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = os.open(MASTER_LOG_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fchown(directory, 0, 0)
        os.fchmod(directory, 0o700)
        descriptor = os.open('fpm.log', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise RuntimeError('Roundcube master log must be a regular file.')
            os.fchown(descriptor, 0, 0)
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)


def install():
    fpm, cli = find_php()
    identity = ensure_identity()
    ensure_master_log()
    status('installing', 'Downloading and verifying Roundcube.')
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o755)
    release = ROOT / VERSION
    with tempfile.TemporaryDirectory(prefix='.stage-', dir=ROOT) as stage:
        archive = Path(stage) / 'release.tar.gz'
        download(archive)
        candidate = Path(stage) / 'app'
        candidate.mkdir()
        checked_extract(archive, candidate)
        (candidate / 'config' / 'config.inc.php').write_text(php_config())
        os.chown(candidate / 'config' / 'config.inc.php', 0, identity.pw_gid)
        (candidate / 'config' / 'config.inc.php').chmod(0o640)
        # Only the two front controllers are exposed by the gateway.
        shutil.rmtree(candidate / 'installer', ignore_errors=True)
        (candidate / 'public_html' / 'installer.php').unlink(missing_ok=True)
        db = DATA / 'roundcube.sqlite'
        old_target = (ROOT / 'current').resolve() if (ROOT / 'current').exists() else None
        replacing_same_release = old_target == release.resolve()
        was_enabled = ENABLED.exists()
        backup = None
        database_migration_started = False
        release_moved_to_previous = False
        service_enable_attempted = False
        preserved_config = {}
        for path in (CONFIG / 'fpm.conf', UNIT):
            preserved_config[path] = path.read_text() if path.exists() else None
        try:
            ENABLED.unlink(missing_ok=True)
            if old_target is not None:
                run(['systemctl', 'stop', SERVICE])
            else:
                subprocess.run(['systemctl', 'stop', SERVICE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if db.exists():
                backup = backup_database(db, identity)
            else:
                schema = (candidate / 'SQL' / 'sqlite.initial.sql').read_text()
                with runtime_identity(identity), closing(sqlite3.connect(db)) as connection:
                    connection.executescript(schema)
                with runtime_identity(identity):
                    db.chmod(0o600)
            status('installing', 'Configuring the private PHP runtime.')
            # Keep a prior same-version directory for rollback until success.
            previous = ROOT / (VERSION + '.previous')
            if previous.exists():
                shutil.rmtree(previous)
            if release.exists():
                release.rename(previous)
                release_moved_to_previous = True
            candidate.rename(release)
            database_migration_started = True
            run(['runuser', '-u', USER, '--', cli, str(release / 'bin' / 'updatedb.sh'),
                 '--dir', str(release / 'SQL'), '--package', 'roundcube'])
            link = ROOT / '.current'
            link.unlink(missing_ok=True)
            link.symlink_to(release)
            os.replace(link, ROOT / 'current')
            write_atomic(CONFIG / 'fpm.conf', pool_config())
            write_atomic(UNIT, service_config(fpm))
            run([fpm, '--test', '--fpm-config', str(CONFIG / 'fpm.conf')])
            run(['systemctl', 'daemon-reload'])
            service_enable_attempted = True
            run(['systemctl', 'enable', '--now', SERVICE])
            run(['systemctl', 'is-active', '--quiet', SERVICE])
            write_atomic(ENABLED, VERSION + '\n')
            status('ready', 'Roundcube is ready. Integrated webmail remains available.')
        except Exception:
            ENABLED.unlink(missing_ok=True)
            subprocess.run(['systemctl', 'stop', SERVICE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if service_enable_attempted and not was_enabled:
                # enable --now can register the unit even when starting fails.
                # Remove that registration before restoring/removing its unit.
                subprocess.run(['systemctl', 'disable', SERVICE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if backup is not None and database_migration_started:
                # Keep root out of paths the PHP account can replace.
                saved_database = backup.read_bytes()
                with runtime_identity(identity):
                    for suffix in ('-wal', '-shm'):
                        Path(str(db) + suffix).unlink(missing_ok=True)
                    db.write_bytes(saved_database)
            for path, content in preserved_config.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    write_atomic(path, content)
            subprocess.run(['systemctl', 'daemon-reload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if old_target is not None:
                previous = ROOT / (VERSION + '.previous')
                if replacing_same_release and release_moved_to_previous and previous.exists():
                    if release.exists():
                        shutil.rmtree(release)
                    previous.rename(release)
                link = ROOT / '.current'
                link.unlink(missing_ok=True)
                link.symlink_to(old_target)
                os.replace(link, ROOT / 'current')
                if was_enabled:
                    subprocess.run(['systemctl', 'start', SERVICE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if subprocess.run(['systemctl', 'is-active', '--quiet', SERVICE]).returncode == 0:
                        write_atomic(ENABLED, old_target.name + '\n')
            raise


def main():
    if os.geteuid() != 0:
        raise SystemExit('Roundcube management must run as root.')
    if len(sys.argv) != 2 or sys.argv[1] not in ('install', 'enable', 'disable'):
        raise SystemExit('Usage: roundcubeRuntime.py install|enable|disable')
    CONFIG.mkdir(parents=True, exist_ok=True, mode=0o755)
    with open(CONFIG / 'operation.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another Roundcube operation is running.')
        try:
            if sys.argv[1] == 'install':
                install()
            elif sys.argv[1] == 'disable':
                ENABLED.unlink(missing_ok=True)
                run(['systemctl', 'disable', '--now', SERVICE])
                status('disabled', 'Roundcube is disabled. Contacts and preferences are retained.')
            else:
                if not (ROOT / 'current' / 'public_html' / 'index.php').is_file():
                    raise RuntimeError('Install Roundcube before enabling it.')
                run(['systemctl', 'enable', '--now', SERVICE])
                run(['systemctl', 'is-active', '--quiet', SERVICE])
                write_atomic(ENABLED, installed_version() + '\n')
                status('ready', 'Roundcube is ready.')
        except RuntimeError as error:
            status('error', str(error))
            raise SystemExit(1)
        except Exception:
            # Commands may return sensitive runtime output: do not expose it in the UI.
            status('error', 'Roundcube setup failed. Check the system journal and PHP prerequisites; the previous installation was preserved when available.')
            raise SystemExit(1)


if __name__ == '__main__':
    main()
