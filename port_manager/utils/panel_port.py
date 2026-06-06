"""Detect CyberPanel admin port from bind.conf (8090, 2087, etc.)."""
import os
import re

BIND_CANDIDATES = (
    '/usr/local/lscp/conf/bind.conf',
    '/usr/local/lscp/conf/bind.conf0',
)

def get_panel_port(default=8090):
    for path in BIND_CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r') as f:
                text = f.read()
        except OSError:
            continue
        m = re.search(r'address\s+\*:(\d+)', text)
        if m:
            return int(m.group(1))
        m = re.search(r':(\d+)\s*$', text.strip().splitlines()[-1] if text.strip() else '')
        if m:
            return int(m.group(1))
    return default

def get_panel_base_url(request):
    try:
        host = request.get_host()
        return f'https://{host}/plugins/port_manager/'
    except Exception:
        port = get_panel_port()
        return f'https://127.0.0.1:{port}/plugins/port_manager/'
