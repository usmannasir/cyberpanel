"""Run native OLS -t and verify that the CyberPanel core actually read its diagnostics."""
import ctypes
import json
import mmap
import os
from pathlib import Path
import secrets
import stat
import struct
import subprocess
import sys
import tempfile


RUNTIME = Path('/tmp/lshttpd')
MARKER = b'cyberpanel_lsi_api_abi_v1'


def custom_core(binary):
    with open(binary, 'rb') as source:
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
            return data.find(MARKER) >= 0


def checked_mount(*args):
    result = subprocess.run(['mount', *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
    if result.returncode:
        raise RuntimeError('Could not isolate OLS diagnostic files: ' + result.stderr.strip())


def check_runtime():
    try:
        info = RUNTIME.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError('Refusing a linked or non-directory /tmp/lshttpd.')
    if os.path.lexists(str(RUNTIME / 'testconf')):
        raise RuntimeError('An existing OLS diagnostic file is present. Check for an active configuration test.')
    return True


def overlay(target, scratch):
    tag = target.name
    upper, work, view = [scratch / (tag + '-' + name) for name in ('upper', 'work', 'view')]
    for path in (upper, work, view):
        path.mkdir()
    checked_mount('-t', 'overlay', 'overlay', '-o',
                  'lowerdir=%s,upperdir=%s,workdir=%s' % (target, upper, work), str(view))
    checked_mount('--bind', str(view), str(target))


def private_test(binary, scratch, parent_namespace):
    if os.readlink('/proc/self/ns/mnt') == parent_namespace:
        raise RuntimeError('No private mount namespace for OpenLiteSpeed validation.')
    # Preserve every other /tmp path. The overlay is needed only to supply a
    # missing mount point without creating or changing the live runtime dir.
    if not check_runtime():
        overlay(Path('/tmp'), scratch)
        RUNTIME.mkdir()
    checked_mount('-t', 'tmpfs', '-o', 'mode=0755,nosuid,nodev,noexec', 'tmpfs', str(RUNTIME))
    # The native config test invokes usermod. Isolate its passwd/group writes.
    overlay(Path('/etc'), scratch)
    ledger = RUNTIME / 'testconf'
    nonce = ('CYBERPANEL_OLS_TEST_' + secrets.token_hex(16) + '\n').encode()
    with ledger.open('xb') as seed:
        seed.write(nonce)
        seed.flush()
        os.fsync(seed.fileno())
    libc = ctypes.CDLL(None, use_errno=True)
    descriptor = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
    if descriptor < 0:
        raise OSError(ctypes.get_errno(), 'Cannot initialize diagnostic ledger observation')
    try:
        if libc.inotify_add_watch(descriptor, os.fsencode(ledger), 0x20 | 0x400) < 0:
            raise OSError(ctypes.get_errno(), 'Cannot observe diagnostic ledger')
        result = subprocess.run([str(binary), '-t'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=30, env=dict(os.environ, LSWS_HOME=str(binary.parent.parent) + '/'))
        try:
            events = os.read(descriptor, 65536)
        except BlockingIOError:
            events = b''
    finally:
        os.close(descriptor)
    observed = 0
    while events:
        _, mask, _, size = struct.unpack('iIII', events[:16])
        observed |= mask
        events = events[16 + size:]
    combined = result.stdout + result.stderr
    if observed & 0x420 != 0x420 or os.path.lexists(str(ledger)) or combined.count(nonce) != 1:
        raise RuntimeError('OpenLiteSpeed did not read and delete its fresh diagnostic ledger.')
    remaining = combined.replace(nonce, b'', 1)
    # Only the injected nonce turned a genuinely silent native check into rc1.
    code = 0 if result.returncode == 1 and not remaining.strip() else result.returncode
    return code, remaining.decode('utf-8', errors='replace')


def validate(binary):
    binary = Path(binary).absolute()
    if not custom_core(binary):
        return subprocess.run([str(binary), '-t'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                              timeout=30, env=dict(os.environ, LSWS_HOME=str(binary.parent.parent) + '/'))
    check_runtime()
    with tempfile.TemporaryDirectory(prefix='ols-config-proof-', dir='/var/tmp') as scratch:
        probe = subprocess.run([
            'unshare', '--mount', '--propagation', 'private', sys.executable, '-IB',
            str(Path(__file__).resolve()), '--private', str(binary), scratch, os.readlink('/proc/self/ns/mnt'),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=75)
    if probe.returncode:
        raise RuntimeError('Cannot verify native OLS diagnostics: ' + (probe.stderr or probe.stdout).strip()[-1000:])
    code, output = json.loads(probe.stdout)
    return subprocess.CompletedProcess([str(binary), '-t'], code, output, '')


if __name__ == '__main__':
    try:
        if len(sys.argv) == 5 and sys.argv[1] == '--private':
            print(json.dumps(private_test(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])))
        elif len(sys.argv) == 2:
            result = validate(sys.argv[1])
            sys.stdout.write((result.stdout or '') + (result.stderr or ''))
            sys.exit(result.returncode)
        else:
            sys.exit(78)
    except Exception as error:
        print('OpenLiteSpeed validation could not establish a native result: ' + str(error), file=sys.stderr)
        sys.exit(78)
