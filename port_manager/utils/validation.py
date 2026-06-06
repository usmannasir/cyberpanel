import re

PROTECTED_PORTS = {22, 80, 443, 53, 8090, 7080, 3306, 2087}
PROTECTED_PROCS = {
    'systemd', 'sshd', 'lscpd', 'lshttpd', 'openlitespeed', 'lsws',
    'dockerd', 'containerd', 'mysqld', 'mariadbd', 'pdns_server', 'named',
}
PROTO_ALLOW = frozenset(['tcp', 'udp'])
SEARCH_RE = re.compile(r'^[a-zA-Z0-9._\- ]{0,64}$')

def parse_port(value):
    try:
        p = int(value)
    except (TypeError, ValueError):
        return None
    if p < 1 or p > 65535:
        return None
    return p

def parse_proto(value):
    if not value:
        return 'tcp'
    p = str(value).lower().strip()
    return p if p in PROTO_ALLOW else None

def parse_pid(value):
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    if pid < 2:
        return None
    return pid

def is_protected_port(port):
    return int(port) in PROTECTED_PORTS

def is_protected_process(name):
    if not name:
        return False
    base = name.lower().split('/')[-1]
    return base in PROTECTED_PROCS

def sanitize_search(value):
    if value is None:
        return ''
    s = str(value).strip()
    if not s or not SEARCH_RE.match(s):
        return ''
    return s
