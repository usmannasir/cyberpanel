#!/usr/bin/env python3
"""
Weekly integrity monitor for public_html index.html and index.php files.

Creates or compares SHA-256 baseline at /home/cyberpanel/index_integrity_baseline.json.
Sends Discord alerts via the discordWebhooks plugin when unexpected changes are detected.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime

CYBERCP_ROOT = '/usr/local/CyberCP'
BASELINE_PATH = '/home/cyberpanel/index_integrity_baseline.json'
HOME_ROOT = '/home'
LOG_PREFIX = '[index_integrity]'


def _log(message: str) -> None:
    line = '%s %s %s' % (datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), LOG_PREFIX, message)
    print(line, flush=True)
    try:
        sys.path.insert(0, CYBERCP_ROOT)
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as cp_log
        cp_log.writeToFile(line)
    except Exception:
        pass


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def discover_index_files():
    """Yield absolute paths to index.html / index.php under */public_html/."""
    if not os.path.isdir(HOME_ROOT):
        return
    for account in os.scandir(HOME_ROOT):
        if not account.is_dir():
            continue
        if account.name in ('cyberpanel', 'backup', 'almalinux'):
            continue
        for dirpath, _dirnames, filenames in os.walk(account.path):
            if os.path.basename(dirpath) != 'public_html':
                continue
            for name in ('index.html', 'index.php'):
                full = os.path.join(dirpath, name)
                if os.path.isfile(full):
                    yield full


def build_current_hashes():
    current = {}
    for path in sorted(set(discover_index_files())):
        try:
            current[path] = _sha256_file(path)
        except OSError as exc:
            _log('skip unreadable %s: %s' % (path, exc))
    return current


def load_baseline():
    if not os.path.isfile(BASELINE_PATH):
        return {}
    try:
        with open(BASELINE_PATH, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get('files'), dict):
            return data['files']
    except Exception as exc:
        _log('baseline read error: %s' % exc)
    return {}


def save_baseline(files: dict) -> None:
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    payload = {
        'updated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'file_count': len(files),
        'files': files,
    }
    tmp = BASELINE_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    os.replace(tmp, BASELINE_PATH)
    try:
        os.chmod(BASELINE_PATH, 0o600)
    except OSError:
        pass


def send_discord_alert(changed, added, removed):
    try:
        sys.path.insert(0, CYBERCP_ROOT)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
        import django
        django.setup()
        from discordWebhooks.utils import send_to_all_webhooks
    except Exception as exc:
        _log('Discord alert skipped (plugin unavailable): %s' % exc)
        return

    lines = []
    for path in changed[:20]:
        lines.append('- changed: `%s`' % path)
    for path in added[:20]:
        lines.append('- new: `%s`' % path)
    for path in removed[:20]:
        lines.append('- removed: `%s`' % path)
    extra = len(changed) + len(added) + len(removed) - len(lines)
    if extra > 0:
        lines.append('- ... and %d more' % extra)

    embed = {
        'title': 'CyberPanel: public_html index integrity alert',
        'description': 'Unexpected index file changes detected (possible defacement).',
        'color': 0xE74C3C,
        'fields': [
            {
                'name': 'Summary',
                'value': 'changed=%d added=%d removed=%d' % (len(changed), len(added), len(removed)),
                'inline': False,
            },
            {
                'name': 'Details',
                'value': '\n'.join(lines)[:4000] or 'No paths listed',
                'inline': False,
            },
        ],
        'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
    }
    result = send_to_all_webhooks({'embeds': [embed]})
    _log('Discord alert sent success=%s fail=%s' % (result.get('success_count'), result.get('fail_count')))


def main():
    current = build_current_hashes()
    if not current:
        _log('no index files found under %s' % HOME_ROOT)
        return 0

    baseline = load_baseline()
    if not baseline:
        save_baseline(current)
        _log('initial baseline saved (%d files) -> %s' % (len(current), BASELINE_PATH))
        return 0

    changed = sorted(path for path in current if path in baseline and current[path] != baseline[path])
    added = sorted(path for path in current if path not in baseline)
    removed = sorted(path for path in baseline if path not in current)

    if not changed and not added and not removed:
        _log('OK: %d files match baseline' % len(current))
        return 0

    _log('ALERT changed=%d added=%d removed=%d' % (len(changed), len(added), len(removed)))
    send_discord_alert(changed, added, removed)
    save_baseline(current)
    _log('baseline updated after alert')
    return 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        _log('fatal: %s' % exc)
        raise
