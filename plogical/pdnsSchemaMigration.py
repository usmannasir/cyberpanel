#!/usr/local/CyberCP/bin/python
"""
PowerDNS schema migration helper.

Detects and applies missing PowerDNS gmysql-backend schema changes that
PowerDNS 4.7+ (including 4.8/4.9/5.0.x) require but older CyberPanel installs
never received.

Background
----------
PowerDNS 4.7 introduced catalog zones, which added two columns to the
`domains` table (`catalog`, `options`) and widened the `type` column. PDNS
gets auto-upgraded on customer servers via `dnf update` (often as a
transitive dependency of unrelated package upgrades) but CyberPanel has
never migrated the schema, so the new binary crash-loops with:

    Unknown column 'domains.catalog' in 'SELECT'

resulting in total DNS outage on the affected server. This module is the
fix.

Cumulative schema changes implemented (all idempotent):

    PDNS 4.1 -> 4.2:
        ALTER TABLE domains MODIFY notified_serial INT UNSIGNED DEFAULT NULL
        (records.change_date is dropped upstream but harmless if left)
    PDNS 4.2 -> 4.3:
        ALTER TABLE cryptokeys ADD published BOOL NULL DEFAULT 1 AFTER active
    PDNS 4.3 -> 4.7+ (mandatory for catalog zones):
        ALTER TABLE domains ADD options  VARCHAR(64000) DEFAULT NULL
        ALTER TABLE domains ADD catalog  VARCHAR(255)   DEFAULT NULL
        ALTER TABLE domains MODIFY type  VARCHAR(8) NOT NULL
        CREATE INDEX catalog_idx ON domains(catalog)

Character-set handling
----------------------
Upstream PDNS uses CHARACTER SET 'latin1' on these tables, which is what
allows VARCHAR(64000). CyberPanel's Django ORM, however, may have created
the tables with utf8mb3/utf8mb4 -- in which case a bare VARCHAR(64000) is
rejected with "Column length too big". We therefore add the new columns
with an explicit `CHARACTER SET 'latin1'` so the migration succeeds
regardless of the existing table charset. The data stored in these columns
(catalog hash strings, opaque metadata blob) is always ASCII in practice,
so a per-column charset is safe.

Invocation
----------
    From CyberPanel upgrade  : Upgrade.pdnsSchemaMigrations() in upgrade.py
    From fresh install       : right before startPowerDNS()
    Directly (customer SOS)  :
        /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/pdnsSchemaMigration.py
"""

import json
import os
import subprocess
import sys
import time

try:
    import MySQLdb as _mysql
except ImportError:
    import pymysql as _mysql  # type: ignore


PDNS_DB_NAME_DEFAULT = 'cyberpanel'
MYSQL_PASSWORD_FILE = '/etc/cyberpanel/mysqlPassword'
HEALTH_FILE = '/etc/cyberpanel/health.json'
ERROR_LOG_FILE = '/home/cyberpanel/error-logs.txt'


def _log(message):
    line = '[%s] [PDNS_SCHEMA] %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), message)
    print(line)
    try:
        os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
        with open(ERROR_LOG_FILE, 'a') as fh:
            fh.write(line + '\n')
    except Exception:
        pass


def _read_root_password():
    try:
        with open(MYSQL_PASSWORD_FILE) as fh:
            return fh.read().split('\n', 1)[0].strip()
    except Exception as exc:
        _log('Cannot read %s: %s' % (MYSQL_PASSWORD_FILE, exc))
        return None


def _connect(db_name):
    """
    Connect to MySQL/MariaDB. Mirrors plogical.upgrade.setupConnection so we
    work in the same environments (local socket, port 3307, remote MySQL).
    """
    password = _read_root_password()
    if not password:
        return None

    last_err = None
    attempts = (
        {'user': 'root', 'passwd': password, 'db': db_name},
        {'user': 'root', 'passwd': password, 'db': db_name,
         'host': '127.0.0.1', 'port': 3307},
    )
    for kwargs in attempts:
        try:
            return _mysql.connect(**kwargs)
        except Exception as exc:
            last_err = exc

    try:
        sys.path.append('/usr/local/CyberCP')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
        from CyberCP import settings as django_settings
        cfg = django_settings.DATABASES['default']
        port = int(cfg['PORT']) if cfg.get('PORT') else 3306
        return _mysql.connect(host=cfg.get('HOST') or 'localhost',
                              port=port,
                              db=cfg['NAME'],
                              user=cfg['USER'],
                              passwd=cfg['PASSWORD'])
    except Exception as exc:
        last_err = exc

    _log('Could not connect to MySQL/MariaDB: %s' % last_err)
    return None


def _resolve_db_name():
    try:
        sys.path.append('/usr/local/CyberCP')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
        from CyberCP import settings as django_settings
        return django_settings.DATABASES['default']['NAME'] or PDNS_DB_NAME_DEFAULT
    except Exception:
        return PDNS_DB_NAME_DEFAULT


def _table_exists(cursor, db_name, table):
    cursor.execute(
        "SELECT 1 FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
        (db_name, table),
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, db_name, table, column):
    cursor.execute(
        "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (db_name, table, column),
    )
    return cursor.fetchone() is not None


def _column_type(cursor, db_name, table, column):
    cursor.execute(
        "SELECT COLUMN_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (db_name, table, column),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {'column_type': row[0], 'is_nullable': row[1], 'max_len': row[2]}


def _index_exists(cursor, db_name, table, index_name):
    cursor.execute(
        "SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND INDEX_NAME=%s",
        (db_name, table, index_name),
    )
    return cursor.fetchone() is not None


def _try_exec(cursor, sql, label, results):
    try:
        cursor.execute(sql)
        _log('APPLIED  %s' % label)
        results['applied'].append(label)
        return True
    except Exception as exc:
        _log('FAILED   %s :: %s' % (label, exc))
        results['errors'].append({'step': label, 'error': str(exc)})
        return False


def migrate_pdns_schema(restart_service=True):
    """
    Idempotently bring the PowerDNS schema up to PDNS 5.x expectations.
    Returns a results dict: {applied, skipped, errors}.
    """
    results = {'applied': [], 'skipped': [], 'errors': []}

    db_name = _resolve_db_name()
    conn = _connect(db_name)
    if conn is None:
        results['errors'].append({'step': 'connect', 'error': 'no MySQL connection'})
        _write_health(results, ok=False)
        return results

    cursor = conn.cursor()

    if not _table_exists(cursor, db_name, 'domains'):
        _log('Table `domains` does not exist in `%s`; PDNS schema not yet '
             'created. Nothing to migrate.' % db_name)
        results['skipped'].append('domains-table-missing')
        try:
            cursor.close(); conn.close()
        except Exception:
            pass
        _write_health(results, ok=True)
        return results

    # --- domains.catalog (PDNS 4.7) -----------------------------------------
    if _column_exists(cursor, db_name, 'domains', 'catalog'):
        results['skipped'].append('domains.catalog already present')
    else:
        _try_exec(
            cursor,
            "ALTER TABLE `domains` ADD COLUMN `catalog` "
            "VARCHAR(255) CHARACTER SET 'latin1' DEFAULT NULL",
            'add domains.catalog',
            results,
        )

    # --- domains.options (PDNS 4.7) -----------------------------------------
    if _column_exists(cursor, db_name, 'domains', 'options'):
        results['skipped'].append('domains.options already present')
    else:
        # Always pin to latin1 so VARCHAR(64000) fits regardless of table charset.
        ok = _try_exec(
            cursor,
            "ALTER TABLE `domains` ADD COLUMN `options` "
            "VARCHAR(64000) CHARACTER SET 'latin1' DEFAULT NULL",
            'add domains.options',
            results,
        )
        if not ok:
            # Some MariaDB builds reject 64000 even on latin1; fall back to TEXT
            # which PDNS also accepts (bytes-equivalent).
            _try_exec(
                cursor,
                "ALTER TABLE `domains` ADD COLUMN `options` "
                "TEXT CHARACTER SET 'latin1' DEFAULT NULL",
                'add domains.options (TEXT fallback)',
                results,
            )

    # --- domains.type widened to VARCHAR(8) NOT NULL (PDNS 4.7) -------------
    type_meta = _column_type(cursor, db_name, 'domains', 'type')
    if type_meta and (type_meta['max_len'] or 0) < 8:
        _try_exec(
            cursor,
            "ALTER TABLE `domains` MODIFY `type` VARCHAR(8) NOT NULL",
            'widen domains.type to VARCHAR(8) NOT NULL',
            results,
        )
    else:
        results['skipped'].append('domains.type already wide enough')

    # --- domains.notified_serial INT UNSIGNED (PDNS 4.1.1) ------------------
    notified = _column_type(cursor, db_name, 'domains', 'notified_serial')
    if notified and 'unsigned' not in (notified['column_type'] or '').lower():
        _try_exec(
            cursor,
            "ALTER TABLE `domains` MODIFY `notified_serial` "
            "INT UNSIGNED DEFAULT NULL",
            'make domains.notified_serial UNSIGNED',
            results,
        )
    else:
        results['skipped'].append('domains.notified_serial already UNSIGNED')

    # --- cryptokeys.published (PDNS 4.3) ------------------------------------
    if _table_exists(cursor, db_name, 'cryptokeys'):
        if _column_exists(cursor, db_name, 'cryptokeys', 'published'):
            results['skipped'].append('cryptokeys.published already present')
        else:
            _try_exec(
                cursor,
                "ALTER TABLE `cryptokeys` ADD COLUMN `published` "
                "BOOL NULL DEFAULT 1 AFTER `active`",
                'add cryptokeys.published',
                results,
            )

    # --- catalog_idx (PDNS 4.7) ---------------------------------------------
    if _index_exists(cursor, db_name, 'domains', 'catalog_idx'):
        results['skipped'].append('catalog_idx already present')
    else:
        # Only create the index once the column is in place.
        if _column_exists(cursor, db_name, 'domains', 'catalog'):
            _try_exec(
                cursor,
                "CREATE INDEX `catalog_idx` ON `domains` (`catalog`)",
                'create domains.catalog_idx',
                results,
            )

    try:
        conn.commit()
    except Exception:
        pass
    try:
        cursor.close(); conn.close()
    except Exception:
        pass

    if results['applied']:
        _log('Schema changes applied: %s' % ', '.join(results['applied']))
    if results['errors']:
        _log('Schema migration finished with errors: %s' %
             json.dumps(results['errors']))
    else:
        _log('Schema migration finished cleanly. '
             '(%d applied, %d skipped)' %
             (len(results['applied']), len(results['skipped'])))

    if restart_service and results['applied']:
        _restart_pdns()

    _write_health(results, ok=not results['errors'])
    return results


def _restart_pdns():
    """
    Restart PowerDNS so the new schema takes effect. We try both unit names
    (CentOS/RHEL ships `pdns`, Debian/Ubuntu ships `pdns` as well but some
    images expose `powerdns`). Failures are logged, not raised.
    """
    for unit in ('pdns', 'powerdns'):
        try:
            r = subprocess.run(['systemctl', 'is-enabled', unit],
                               capture_output=True, text=True)
            if r.returncode != 0 and 'masked' not in (r.stdout + r.stderr):
                # Not installed under this name.
                continue
            r = subprocess.run(['systemctl', 'restart', unit],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                _log('Restarted %s' % unit)
                # Reset systemd's failed/restart counter so a subsequent
                # health check doesn't see stale 26830-restart noise.
                subprocess.run(['systemctl', 'reset-failed', unit],
                               capture_output=True, text=True)
                return
            _log('systemctl restart %s failed: %s' %
                 (unit, (r.stderr or r.stdout).strip()))
        except Exception as exc:
            _log('systemctl restart %s raised: %s' % (unit, exc))


def _write_health(results, ok=True):
    try:
        os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)
        payload = {
            'pdns_schema_migration': {
                'last_run': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'ok': ok,
                'applied': results.get('applied', []),
                'skipped': results.get('skipped', []),
                'errors': results.get('errors', []),
            }
        }
        existing = {}
        if os.path.exists(HEALTH_FILE):
            try:
                with open(HEALTH_FILE) as fh:
                    existing = json.load(fh) or {}
            except Exception:
                existing = {}
        existing.update(payload)
        with open(HEALTH_FILE, 'w') as fh:
            json.dump(existing, fh, indent=2)
    except Exception as exc:
        _log('Could not write health file: %s' % exc)


if __name__ == '__main__':
    res = migrate_pdns_schema(restart_service=True)
    sys.exit(0 if not res['errors'] else 1)
