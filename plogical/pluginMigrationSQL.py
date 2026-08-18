# -*- coding: utf-8 -*-
"""
Plugin install/remove: robust DB migration and teardown for CyberPanel.

- Prefer Django ``migrate`` / ``migrate zero``.
- If the global loader fails or migrate errors, apply ``sqlmigrate`` output and
  ``--fake``, or drop plugin tables and clean ``django_migrations`` on removal.

Assumes ``manage.py`` / ``CyberCP.settings`` are available under /usr/local/CyberCP.
"""

from __future__ import annotations

import os
import subprocess


def _manage_py() -> str:
    return '/usr/local/CyberCP/manage.py'


def _python_executable() -> str:
    for candidate in ('/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/bin/python3'):
        try:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        except OSError:
            continue
    return 'python3'


def _django_setup():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
    import django

    django.setup()


def _db_name() -> str:
    _django_setup()
    from django.conf import settings

    return settings.DATABASES['default']['NAME']


def run_manage(args: list, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run manage.py with args (e.g. ['migrate', 'contaboAutoSnapshot', '--noinput'])."""
    cmd = [_python_executable(), _manage_py()] + args
    return subprocess.run(
        cmd,
        cwd=cwd or '/usr/local/CyberCP',
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=600,
    )


def list_plugin_migration_names(plugin_name: str) -> list[str]:
    """Sorted migration names from disk (e.g. 0001_initial), excluding __init__."""
    mig_dir = '/usr/local/CyberCP/' + plugin_name + '/migrations'
    if not os.path.isdir(mig_dir):
        return []
    names = []
    try:
        for fn in os.listdir(mig_dir):
            if not fn.endswith('.py') or fn == '__init__.py':
                continue
            names.append(fn[:-3])
    except OSError:
        return []
    return sorted(names)


def applied_plugin_migrations(plugin_name: str) -> set[str]:
    _django_setup()
    from django.db import connection
    from django.db.migrations.recorder import MigrationRecorder

    recorder = MigrationRecorder(connection)
    return {name for app, name in recorder.applied_migrations() if app == plugin_name}


def sqlmigrate_text(plugin_name: str, migration_name: str) -> tuple[int, str]:
    """Return (returncode, combined stdout+stderr) for sqlmigrate."""
    proc = run_manage(['sqlmigrate', plugin_name, migration_name])
    out = (proc.stdout or '') + (proc.stderr or '')
    return proc.returncode, out


def _strip_sql_comments(sql: str) -> str:
    lines = []
    for line in sql.splitlines():
        s = line.strip()
        if s.startswith('--'):
            continue
        lines.append(line)
    return '\n'.join(lines)


def _execute_multi_sql_mysql(sql: str) -> tuple[bool, str]:
    """Execute multi-statement ``sqlmigrate`` output via ``mariadb`` CLI (socket auth as root)."""
    sql = _strip_sql_comments(sql).strip()
    if not sql:
        return True, ''
    db = _db_name()
    try:
        proc = subprocess.run(
            ['mariadb', db],
            input=sql.encode('utf-8', errors='replace'),
            capture_output=True,
            timeout=300,
        )
        err = (proc.stderr or b'').decode('utf-8', errors='replace')[:2000]
        if proc.returncode != 0:
            return False, err or 'mariadb exited %s' % proc.returncode
        return True, ''
    except FileNotFoundError:
        return False, 'mariadb client not found; install MariaDB client or fix PATH'
    except Exception as e:
        return False, str(e)[:2000]


def apply_pending_migrations_via_sql_and_fake(plugin_name: str, log) -> bool:
    """
    For each on-disk migration not in django_migrations: sqlmigrate + execute, then
    ``migrate <app> <name> --fake`` so each is recorded.
    """
    pending = [m for m in list_plugin_migration_names(plugin_name) if m not in applied_plugin_migrations(plugin_name)]
    if not pending:
        log(
            'SQL fallback: no pending migrations recorded for %s — schema/DB mismatch may remain; '
            'check migrate errors above.'
            % plugin_name
        )
        return False
    for mig in pending:
        rc, out = sqlmigrate_text(plugin_name, mig)
        if rc != 0:
            log('sqlmigrate %s %s failed (rc=%s): %s' % (plugin_name, mig, rc, out[:800]))
            return False
        ok, err = _execute_multi_sql_mysql(out)
        if not ok:
            log('SQL exec failed for %s %s: %s' % (plugin_name, mig, err))
            return False
        log('Applied raw SQL for %s %s' % (plugin_name, mig))
        proc = run_manage(['migrate', plugin_name, mig, '--fake', '--noinput'])
        if proc.returncode != 0:
            log(
                'migrate --fake %s %s failed: %s'
                % (plugin_name, mig, (proc.stderr or proc.stdout or '')[:800])
            )
            return False
    return True


def drop_plugin_tables_and_migration_rows(plugin_name: str, log) -> bool:
    """
    DROP all tables for this app label (prefix ``pluginName_``) and remove
    django_migrations rows. Uses FOREIGN_KEY_CHECKS=0.
    """
    _django_setup()
    from django.db import connection

    db = _db_name()
    prefix_a = plugin_name + '_'
    prefix_b = plugin_name.lower() + '_'
    tables = []
    try:
        with connection.cursor() as c:
            c.execute(
                'SELECT table_name FROM information_schema.tables WHERE table_schema = %s '
                'AND (table_name LIKE %s OR table_name LIKE %s)',
                [db, prefix_a + '%', prefix_b + '%'],
            )
            tables = [row[0] for row in c.fetchall()]
    except Exception as e:
        log('list tables for drop failed: %s' % str(e)[:800])
        return False
    if not tables:
        log('No tables matched prefix for %s; cleaning django_migrations only.' % plugin_name)
    try:
        with connection.cursor() as c:
            c.execute('SET FOREIGN_KEY_CHECKS=0')
            for t in tables:
                safe = t.replace('`', '``')
                c.execute('DROP TABLE IF EXISTS `%s`' % safe)
            c.execute('SET FOREIGN_KEY_CHECKS=1')
            c.execute('DELETE FROM django_migrations WHERE app = %s', [plugin_name])
        log('Dropped %s table(s) for %s and removed django_migrations rows.' % (len(tables), plugin_name))
        return True
    except Exception as e:
        log('drop_plugin_tables failed: %s' % str(e)[:800])
        return False


def ensure_login_system_migrations_applied(log) -> None:
    """
    Apply loginSystem 0001 if present (graph fix). Safe no-op if already applied.
    """
    mig_path = '/usr/local/CyberCP/loginSystem/migrations/0001_initial.py'
    if not os.path.isfile(mig_path):
        return
    proc = run_manage(['migrate', 'loginSystem', '--noinput'])
    if proc.returncode != 0:
        log(
            'migrate loginSystem exited %s (panels may need manual fix): %s'
            % (proc.returncode, (proc.stderr or proc.stdout or '')[:600])
        )
