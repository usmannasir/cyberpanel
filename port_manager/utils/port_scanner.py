import os
import re
import subprocess
from plogical.processUtilities import ProcessUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from .validation import sanitize_search

IPV4_ANY = frozenset(['0.0.0.0', '*'])
IPV6_ANY = frozenset(['::', '[::]'])

def _classify_bind(addr):
    addr = (addr or '').strip()
    if addr in ('127.0.0.1', '::1', 'localhost'):
        return 'local'
    if addr in IPV4_ANY or addr in IPV6_ANY:
        return 'public'
    if addr.startswith(('172.', '10.', '192.168.')):
        return 'private'
    return 'other'

def _is_dual_stack_public(bind):
    return (bind or '').strip() in (IPV4_ANY | IPV6_ANY)

def _proc_info(pid):
    info = {'pid': pid, 'name': '', 'user': '', 'exe': '', 'cmdline': ''}
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return info
    proc = '/proc/{0}'.format(pid)
    if not os.path.isdir(proc):
        return info
    try:
        info['exe'] = os.readlink(proc + '/exe')
    except OSError:
        pass
    try:
        with open(proc + '/comm', 'r') as f:
            info['name'] = f.read().strip()
    except OSError:
        pass
    try:
        import pwd
        info['user'] = pwd.getpwuid(os.stat(proc).st_uid).pw_name
    except Exception:
        pass
    return info

def _run_ss():
    for cmd in ('ss -H -tulnp', 'ss -H -tuln'):
        try:
            out = ProcessUtilities.outputExecutioner(cmd)
            if out and out.strip():
                return out
        except Exception as e:
            logging.writeToFile('Port Manager ss: {0}'.format(e))
    return ''

def _parse_local(local):
    local = (local or '').strip()
    m = re.match(r'^\[(.+)\]:(\d+)$', local)
    if m:
        try:
            return m.group(1), int(m.group(2))
        except ValueError:
            return None, None
    if ':' in local:
        h, ps = local.rsplit(':', 1)
        try:
            return h.strip('[]'), int(ps)
        except ValueError:
            return None, None
    return None, None

def _parse_line(line):
    line = (line or '').strip()
    if not line:
        return None
    m = re.search(r'(\[[^\]]+\]:\d+|\S+:\d+)', line)
    if not m:
        return None
    host, port = _parse_local(m.group(1))
    if port is None:
        return None
    row = {
        'proto': line.split()[0].lower(),
        'port': port,
        'bind': host or '*',
        'bind_type': _classify_bind(host),
        'state': 'LISTEN',
        'process': {},
    }
    pm = re.search(r'pid=(\d+)', line)
    if pm:
        row['process'] = _proc_info(pm.group(1))
    return row

def _merge_key(row):
    p = row.get('process') or {}
    pid = p.get('pid') or ''
    return (row['proto'], row['port'], str(pid))

def _merge_dual_stack(rows):
    groups = {}
    order = []
    for row in rows:
        k = _merge_key(row)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(row)
    merged = []
    for k in order:
        items = groups[k]
        if len(items) == 1:
            merged.append(items[0])
            continue
        binds = [i['bind'] for i in items]
        has_v4 = any(b in IPV4_ANY for b in binds)
        has_v6 = any(b in IPV6_ANY or b == '::' for b in binds)
        if has_v4 and has_v6 and all(_is_dual_stack_public(i['bind']) for i in items):
            base = dict(items[0])
            base['bind'] = '0.0.0.0 + ::'
            base['bind_type'] = 'public'
            base['dual_stack'] = True
            merged.append(base)
        else:
            merged.extend(items)
    return merged

def list_listeners(search=''):
    search = sanitize_search(search)
    rows, seen = [], set()
    for line in _run_ss().splitlines():
        try:
            r = _parse_line(line)
        except Exception as e:
            logging.writeToFile('Port Manager skip: {0}'.format(e))
            continue
        if not r:
            continue
        key = (r['proto'], r['port'], r['bind'])
        if key in seen:
            continue
        seen.add(key)
        p = r.get('process') or {}
        blob = '{0} {1} {2} {3}'.format(r['port'], r['proto'], r['bind'], p.get('name', ''))
        if search and search.lower() not in blob.lower():
            continue
        rows.append(r)
    rows = _merge_dual_stack(rows)
    return sorted(rows, key=lambda x: (x['port'], x['proto']))
