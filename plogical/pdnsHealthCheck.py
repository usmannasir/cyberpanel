#!/usr/local/CyberCP/bin/python
"""
PowerDNS service health watchdog.

Goals:

1. Detect when `pdns.service` is in a tight restart loop (the failure mode
   that left customer #6OGPBWCLP at `restart counter is at 26830` before they
   noticed). systemd's `NRestarts` counter and `SubState=auto-restart` make
   this trivially observable.

2. When a crash loop is detected, attempt a self-heal by running
   `plogical.pdnsSchemaMigration.migrate_pdns_schema()`. The migration is
   idempotent, so calling it on a healthy server is a no-op. If the schema
   was the cause of the crash (PDNS 4.7+/5.x against a pre-catalog-zones
   schema -- the May 2026 incident pattern), this brings the customer back
   online without manual intervention.

3. Whether or not we self-heal, write a structured entry to
   `/etc/cyberpanel/health.json` so the dashboard or fleet monitoring can
   surface the failure.

Designed to run from cron every few minutes. Stays silent on stdout when
everything is healthy so the cron mail spool doesn't fill up.
"""

import json
import os
import subprocess
import sys
import time

HEALTH_FILE = '/etc/cyberpanel/health.json'
ERROR_LOG_FILE = '/home/cyberpanel/error-logs.txt'
SELF_HEAL_COOLDOWN_SECONDS = 60 * 30  # don't self-heal more than every 30min
RESTART_LOOP_THRESHOLD = 5  # NRestarts above this is "looping"
KNOWN_SCHEMA_MARKERS = (
    "Unknown column 'domains.catalog'",
    "Unknown column 'domains.options'",
    "Could not prepare statement",
)


def _now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _write_log(message):
    line = '[%s] [PDNS_HEALTH] %s\n' % (
        time.strftime('%Y-%m-%d %H:%M:%S'), message)
    try:
        os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
        with open(ERROR_LOG_FILE, 'a') as fh:
            fh.write(line)
    except Exception:
        pass


def _read_health():
    try:
        with open(HEALTH_FILE) as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _write_health(payload):
    existing = _read_health()
    existing.update(payload)
    try:
        os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)
        with open(HEALTH_FILE, 'w') as fh:
            json.dump(existing, fh, indent=2)
    except Exception:
        pass


def _systemctl_show(unit):
    """
    Return a dict of `systemctl show <unit>` properties, or None if the unit
    is unknown.
    """
    try:
        r = subprocess.run(
            ['systemctl', 'show', unit,
             '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState',
             '-p', 'NRestarts', '-p', 'Result', '-p', 'ExecMainStatus'],
            capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = {}
    for line in r.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    if out.get('LoadState') in ('not-found', 'masked', ''):
        return None
    return out


def _journal_indicates_schema_bug(unit):
    """
    Look at the last few minutes of pdns journal for the catalog/options
    schema error. If absent, we still self-heal (migration is idempotent),
    but presence makes the alert message actionable.
    """
    try:
        r = subprocess.run(
            ['journalctl', '-u', unit, '--since', '-10 minutes',
             '--no-pager', '-q'],
            capture_output=True, text=True, timeout=10)
    except Exception:
        return False
    log = (r.stdout or '') + (r.stderr or '')
    return any(m in log for m in KNOWN_SCHEMA_MARKERS)


def _detect_unit():
    """RHEL/AlmaLinux ships `pdns`; some Debian images expose `pdns-server`
    or `powerdns`. Return the first unit that systemd recognises."""
    for unit in ('pdns', 'pdns.service', 'powerdns', 'pdns-server'):
        if _systemctl_show(unit):
            return unit
    return None


def _self_heal():
    """Call the idempotent schema migrator. Suppress all errors -- a
    cron-driven watchdog must not propagate failures."""
    try:
        sys.path.append('/usr/local/CyberCP')
        from plogical.pdnsSchemaMigration import migrate_pdns_schema
        return migrate_pdns_schema(restart_service=True)
    except Exception as exc:
        _write_log('self-heal failed: %s' % exc)
        return {'applied': [], 'skipped': [], 'errors': [str(exc)]}


def check():
    """Single watchdog tick. Returns a status dict."""
    status = {
        'last_check': _now_iso(),
        'unit': None,
        'healthy': True,
        'restart_loop': False,
        'self_heal_attempted': False,
        'self_heal_result': None,
    }

    unit = _detect_unit()
    if unit is None:
        # PDNS isn't installed on this server; nothing to watch.
        status['unit'] = 'not-installed'
        _write_health({'pdns_service': status})
        return status

    status['unit'] = unit
    info = _systemctl_show(unit) or {}
    try:
        n_restarts = int(info.get('NRestarts', '0') or '0')
    except ValueError:
        n_restarts = 0

    active_state = info.get('ActiveState', '')
    sub_state = info.get('SubState', '')

    looping = (
        n_restarts >= RESTART_LOOP_THRESHOLD
        or sub_state == 'auto-restart'
        or (active_state == 'failed' and info.get('Result') == 'exit-code')
    )
    status['restart_loop'] = looping
    status['n_restarts'] = n_restarts
    status['active_state'] = active_state
    status['sub_state'] = sub_state

    if not looping and active_state == 'active':
        status['healthy'] = True
        _write_health({'pdns_service': status})
        return status

    # Crash loop / failed state: try to self-heal, but rate-limit so we don't
    # thrash on a genuinely broken server.
    status['healthy'] = False
    schema_marker = _journal_indicates_schema_bug(unit)
    status['schema_marker_in_journal'] = schema_marker

    last_heal = (_read_health().get('pdns_service') or {}).get(
        'last_self_heal_at') or 0
    try:
        last_heal_ts = time.mktime(time.strptime(last_heal,
                                                 '%Y-%m-%dT%H:%M:%SZ'))
    except Exception:
        last_heal_ts = 0
    cooldown_active = (time.time() - last_heal_ts) < SELF_HEAL_COOLDOWN_SECONDS

    if cooldown_active:
        status['self_heal_attempted'] = False
        status['self_heal_result'] = 'cooldown'
        _write_log('PDNS unhealthy (NRestarts=%d sub=%s) but in self-heal '
                   'cooldown.' % (n_restarts, sub_state))
    else:
        _write_log('PDNS unhealthy (NRestarts=%d sub=%s schema_marker=%s); '
                   'attempting schema self-heal.' %
                   (n_restarts, sub_state, schema_marker))
        result = _self_heal()
        status['self_heal_attempted'] = True
        status['self_heal_result'] = result
        status['last_self_heal_at'] = _now_iso()

    _write_health({'pdns_service': status})
    return status


if __name__ == '__main__':
    check()
