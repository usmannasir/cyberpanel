# -*- coding: utf-8 -*-
"""
Full config + data backups for managed applications (pre version change).
"""
import json
import os
import shutil
import subprocess
import tarfile
import time

CONFIG_PATHS = {
    'Elasticsearch': ['/etc/elasticsearch'],
    'Redis': ['/etc/redis', '/etc/redis.conf'],
    'RabbitMQ': ['/etc/rabbitmq'],
}

DATA_PATHS = {
    'Elasticsearch': ['/var/lib/elasticsearch'],
    'Redis': ['/var/lib/redis'],
    'RabbitMQ': ['/var/lib/rabbitmq'],
}

SERVICE_UNITS = {
    'Elasticsearch': 'elasticsearch',
    'Redis': 'redis',
    'RabbitMQ': 'rabbitmq-server',
}

CHOWN_CMDS = {
    'Elasticsearch': 'chown -R elasticsearch:elasticsearch /var/lib/elasticsearch /etc/elasticsearch',
    'Redis': 'chown -R redis:redis /var/lib/redis /etc/redis /etc/redis.conf 2>/dev/null; true',
    'RabbitMQ': 'chown -R rabbitmq:rabbitmq /var/lib/rabbitmq /etc/rabbitmq',
}

BACKUP_ROOT = '/home/cyberpanel/backups/manageApplications'


def _existing_paths(app_name):
    out = []
    for p in CONFIG_PATHS.get(app_name, []) + DATA_PATHS.get(app_name, []):
        if os.path.exists(p):
            out.append(p)
    return out


def create_managed_app_backup(app_name, status_file):
    """
    Tar config + data paths into BACKUP_ROOT/<app>/<epoch>/bundle.tar.gz.
    Returns backup directory path, or '' on failure / nothing to back up.
    """
    def log(msg):
        try:
            status_file.write(msg + '\n')
            status_file.flush()
        except Exception:
            pass

    paths = _existing_paths(app_name)
    if not paths:
        log('No paths on disk to back up for {0}; skipping archive.'.format(app_name))
        return ''

    ts = int(time.time())
    safe = app_name.lower().replace(' ', '_')
    backup_dir = os.path.join(BACKUP_ROOT, safe, str(ts))
    os.makedirs(backup_dir, mode=0o750, exist_ok=True)
    archive = os.path.join(backup_dir, 'bundle.tar.gz')

    try:
        with tarfile.open(archive, 'w:gz', compresslevel=6) as tf:
            for abs_path in paths:
                arc = abs_path.lstrip('/')
                tf.add(abs_path, arcname=arc, recursive=True)
        manifest = {
            'app': app_name,
            'created': ts,
            'paths': [p.lstrip('/') for p in paths],
        }
        with open(os.path.join(backup_dir, 'manifest.json'), 'w') as mh:
            json.dump(manifest, mh, indent=2)
        log('Backup created at {0}'.format(backup_dir))
        return backup_dir
    except Exception as err:
        log('Backup failed: {0}'.format(err))
        try:
            shutil.rmtree(backup_dir, ignore_errors=True)
        except Exception:
            pass
        return ''


def _archive_path(backup_dir):
    return os.path.join(backup_dir, 'bundle.tar.gz')


def merge_data_from_backup(app_name, backup_dir, status_file):
    """Overlay saved data directories from backup onto live system (preserves package layout)."""
    def log(msg):
        try:
            status_file.write(msg + '\n')
            status_file.flush()
        except Exception:
            pass

    arc = _archive_path(backup_dir)
    if not os.path.isfile(arc):
        log('No bundle at {0}; skip data merge.'.format(arc))
        return False
    data_prefixes = [p.lstrip('/') for p in DATA_PATHS.get(app_name, [])]
    if not data_prefixes:
        return True
    try:
        with tarfile.open(arc, 'r:gz') as tf:
            for m in tf.getmembers():
                name = m.name
                if m.isfile() or m.isdir():
                    for pref in data_prefixes:
                        if name == pref or name.startswith(pref + '/'):
                            tf.extract(m, path='/', set_attrs=False)
                            break
        log('Merged data trees from backup for {0}.'.format(app_name))
        return True
    except Exception as err:
        log('Data merge failed: {0}'.format(err))
        return False


def restore_full_backup(backup_dir, status_file):
    """Extract full bundle to / (recovery)."""
    def log(msg):
        try:
            status_file.write(msg + '\n')
            status_file.flush()
        except Exception:
            pass

    arc = _archive_path(backup_dir)
    if not os.path.isfile(arc):
        log('Cannot restore: missing {0}'.format(arc))
        return False
    try:
        with tarfile.open(arc, 'r:gz') as tf:
            for m in tf.getmembers():
                tf.extract(m, path='/', set_attrs=False)
        log('Full restore from backup completed.')
        return True
    except Exception as err:
        log('Full restore failed: {0}'.format(err))
        return False


def cleanup_managed_backup(backup_dir, status_file):
    def log(msg):
        try:
            status_file.write(msg + '\n')
            status_file.flush()
        except Exception:
            pass

    if not backup_dir or not os.path.isdir(backup_dir):
        return
    try:
        shutil.rmtree(backup_dir, ignore_errors=True)
        log('Removed backup directory after successful change: {0}'.format(backup_dir))
    except Exception as err:
        log('Could not remove backup dir: {0}'.format(err))


def chown_app_paths(app_name, status_writer):
    cmd = CHOWN_CMDS.get(app_name)
    if not cmd:
        return
    try:
        subprocess.call(cmd, shell=True, stdout=status_writer, stderr=status_writer)
    except Exception:
        pass


def service_is_active(app_name):
    unit = SERVICE_UNITS.get(app_name)
    if not unit:
        return False
    try:
        r = subprocess.run(
            ['systemctl', 'is-active', unit],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.stdout.strip() == 'active'
    except Exception:
        return False
