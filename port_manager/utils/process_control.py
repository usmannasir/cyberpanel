import os
import signal
import subprocess
from .validation import parse_pid, is_protected_port, is_protected_process

def pid_owns_port(pid, port, proto='tcp'):
    port = int(port)
    cmd = ['ss', '-H', '-tulnp']
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    needle = f':{port}'
    for line in (out.stdout or '').splitlines():
        if needle not in line:
            continue
        if f'pid={pid},' in line or f'pid={pid})' in line:
            return True
    return False

def stop_process(pid, port=None, proto='tcp'):
    pid_i = parse_pid(pid)
    if pid_i is None:
        return False, 'invalid pid'
    if port is not None and is_protected_port(port):
        return False, 'protected port'
    name = ''
    try:
        with open(f'/proc/{pid_i}/comm', 'r') as f:
            name = f.read().strip()
    except OSError:
        return False, 'process not found'
    if is_protected_process(name):
        return False, 'protected process'
    if port is not None and not pid_owns_port(pid_i, port, proto):
        return False, 'pid does not own port'
    try:
        os.kill(pid_i, signal.SIGTERM)
        return True, 'sigterm sent'
    except OSError as msg:
        return False, str(msg)
