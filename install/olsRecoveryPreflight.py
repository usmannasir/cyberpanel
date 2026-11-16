"""Fail-closed, namespace-isolated preflight for the paired parser repair."""
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import struct
import re
import glob
import hashlib
import stat

from olsParserRecovery import OLD_CORE_SHA256, digest, host_platform, require_known_failure, split_diagnostics


def checked(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Isolation command failed: %s: %s' % (args[0], result.stderr))
    return result


def readonly_namespace():
    # Linux mount_setattr(AT_RECURSIVE, MOUNT_ATTR_RDONLY), x86_64 syscall 442.
    # Older kernels fail closed; never fall back to a writable host filesystem.
    class Attr(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ('attr_set', 'attr_clr', 'propagation', 'userns_fd')]
    attr = Attr(1, 0, 0, 0)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.syscall(442, -100, ctypes.c_char_p(b'/'), 0x8000,
                    ctypes.byref(attr), ctypes.sizeof(attr)):
        error = ctypes.get_errno()
        raise RuntimeError('Recursive read-only mount isolation unavailable: ' + os.strerror(error))


def config_fingerprint(root, inspect=None):
    """Bind config inputs and opaque TLS dependencies without parsing key bytes.

    A TLS reference never grants permission to use that path as configuration.
    The entire configuration tree remains fingerprinted, including inactive files.
    """
    result, inventory, deferred, tls, config_seen = {}, {}, {}, set(), set()
    root = root.resolve()
    max_file, max_total, max_nodes = 16 * 1024 * 1024, 64 * 1024 * 1024, 10000
    total, nodes, byte_counts = 0, set(), {}

    def signature(info):
        return tuple(getattr(info, field) for field in
                     ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid',
                      'st_size', 'st_mtime_ns', 'st_ctime_ns'))

    def account(path):
        nodes.add(str(path))
        if len(nodes) > max_nodes:
            raise RuntimeError('Configuration tree exceeds recovery inspection limit')

    def lexical(path):
        if '..' in Path(path).parts:
            raise RuntimeError('Parent traversal is unsupported in recovery reference: ' + str(path))
        return Path(os.path.abspath(str(path)))

    def internal(path):
        path = lexical(path)
        resolved = path.resolve()
        if (os.path.commonpath([str(root), str(path)]) != str(root) or
                os.path.commonpath([str(root), str(resolved)]) != str(root)):
            raise RuntimeError('Recovery cannot fingerprint external configuration: ' + str(path))
        return resolved

    def snapshot(path, capture=False):
        nonlocal total
        account(path)
        try:
            link_before = signature(path.lstat())
            link_value = os.readlink(str(path)) if path.is_symlink() else None
            target = path.resolve(strict=True)
            # Resolve first, then open every physical component without following
            # links. O_NONBLOCK prevents a swapped FIFO from blocking inspection.
            parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                for part in target.parts[1:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY |
                                    os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
                    os.close(parent)
                    parent = child
                descriptor = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW |
                                     os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
            finally:
                os.close(parent)
            data, hasher, count = [], hashlib.sha256(), 0
            try:
                before = os.fstat(descriptor)
                if not stat.S_ISREG(before.st_mode):
                    raise RuntimeError('Nonregular recovery dependency: ' + str(path))
                prior_size = byte_counts.get(str(path), 0)
                if before.st_size > max_file or total - prior_size + before.st_size > max_total:
                    raise RuntimeError('Configuration input exceeds recovery inspection limit')
                while True:
                    block = os.read(descriptor, 65536)
                    if not block:
                        break
                    count += len(block)
                    if count > max_file or total - prior_size + count > max_total:
                        raise RuntimeError('Configuration input exceeds recovery inspection limit')
                    hasher.update(block)
                    if capture:
                        data.append(block)
                if signature(before) != signature(os.fstat(descriptor)) or count != before.st_size:
                    raise RuntimeError('Recovery dependency changed while reading: ' + str(path))
            finally:
                os.close(descriptor)
            if (path.resolve(strict=True) != target or
                    signature(path.lstat()) != link_before or
                    signature(target.stat()) != signature(before)):
                raise RuntimeError('Recovery dependency changed while reading: ' + str(path))
            total = total - byte_counts.get(str(path), 0) + count
            byte_counts[str(path)] = count
            record = ('dependency', str(target), link_value, link_before,
                      signature(before), hasher.hexdigest())
            return record, b''.join(data).decode('utf-8') if capture else None
        except (OSError, ValueError) as error:
            raise RuntimeError('Cannot fingerprint recovery dependency: ' + str(path)) from error

    def reference(value, allow_vhost=False):
        value = value.strip()
        if value.startswith(('\"', "'")):
            quote = value[0]
            end = value.find(quote, 1)
            if end < 0 or (value[end + 1:].strip() and not value[end + 1:].strip().startswith('#')):
                raise RuntimeError('Ambiguous quoted recovery reference')
            value = value[1:end]
            if '#' in value or '\"' in value or "'" in value:
                raise RuntimeError('Ambiguous quoted recovery reference')
        else:
            match = re.fullmatch(r'([^\s#\"\']+)(?:\s+(?:#.*)?)?', value)
            if not match:
                raise RuntimeError('Ambiguous unquoted recovery reference')
            value = match.group(1)
        value = re.sub(r'\$\{SERVER_ROOT\}|\$SERVER_ROOT\b', lambda _: str(root), value)
        if allow_vhost:
            value = re.sub(r'\$\{VH_NAME\}|\$VH_NAME\b', '*', value)
        if not value or '$' in value or '\\' in value or any(c in value for c in ('\n', '\r', '\x00')):
            raise RuntimeError('Unresolved or unsupported recovery reference: ' + value)
        return lexical(Path(value) if value.startswith('/') else root / value)

    # Inventory first: external tree links remain unapproved until the active
    # config graph proves that the exact lexical path is a TLS dependency.
    pending = [root / 'conf', root / 'admin/conf']
    while pending:
        path = lexical(pending.pop())
        account(path)
        if path in inventory or path in deferred:
            continue
        target = path.resolve()
        if path.is_symlink():
            if not target.is_file():
                raise RuntimeError('Configuration directory links or nonregular targets are unsupported: ' + str(path))
            if os.path.commonpath([str(root), str(target)]) != str(root):
                deferred[path] = None
                continue
        elif path.is_dir():
            internal(path)
            pending.extend(path.iterdir())
            continue
        internal(path)
        inventory[path], _ = snapshot(path)

    waf_entries, active_documents = [], []
    pending = [root / 'conf/httpd_config.conf']
    if (root / 'admin/conf/admin_config.conf').exists():
        pending.append(root / 'admin/conf/admin_config.conf')
    while pending:
        path = lexical(pending.pop())
        internal(path)  # Config role is strict even when this path is also TLS.
        if path in config_seen:
            continue
        config_seen.add(path)
        record, content = snapshot(path, capture=True)
        if path in inventory and inventory[path] != record:
            raise RuntimeError('Configuration changed during fingerprint: ' + str(path))
        inventory[path] = record
        if inspect:
            waf_entries.extend(inspect(content, root))
            active_documents.append(content)
        for line in content.splitlines():
            match = re.match(r'^\s*(include|configfile|templatefile|keyfile|certfile)\s+(.*)$', line, re.I)
            if not match:
                continue
            kind, value = match.groups()
            if kind.lower() in ('keyfile', 'certfile'):
                referenced = reference(value)
                if glob.has_magic(str(referenced)):
                    raise RuntimeError('Wildcard TLS dependencies are unsupported: ' + value)
                tls.add(referenced)
            else:
                referenced = reference(value, allow_vhost=True)
                internal(referenced)
                matches = glob.glob(str(referenced))
                if not matches:
                    raise RuntimeError('Configuration include cannot be fingerprinted: ' + value)
                pending.extend(Path(item) for item in matches)

    if waf_entries:
        verify_waf_graph(root, waf_entries, active_documents, inventory, snapshot)
    for path in deferred:
        if path not in tls:
            raise RuntimeError('Recovery cannot fingerprint external configuration: ' + str(path))
    for path in sorted(tls):
        record, _ = snapshot(path)
        if path in inventory and inventory[path] != record:
            raise RuntimeError('TLS dependency changed during fingerprint: ' + str(path))
        result['tls:' + str(path)] = record
        if path in deferred:
            inventory[path] = record
    result.update((str(path.relative_to(root)), record)
                  for path, record in inventory.items()
                  if os.path.commonpath([str(root), str(path)]) == str(root))
    from olsLogShadows import log_state
    result['external_log_permissions'] = log_state(root)
    return result


def namespace_probe(root, staging, selected, scratch, candidate, stock=False):
    import installBundle as driver
    root, staging, scratch = Path(root), Path(staging), Path(scratch)
    # This routine runs only in the private mount namespace created by probe().
    parent_namespaces = json.loads(os.environ.get('CP_OLS_PARENT_NAMESPACES', '{}'))
    for name in ('mnt', 'pid', 'ipc', 'net'):
        if not parent_namespaces.get(name) or os.readlink('/proc/self/ns/' + name) == parent_namespaces[name]:
            raise RuntimeError('Refusing a probe without private ' + name + ' isolation')
    checked(['mount', '--bind', str(scratch), str(scratch)])
    from olsLogShadows import log_state, private_shadows, mount_shadows
    log_inputs = log_state(root)
    log_binds = private_shadows(root, scratch, log_inputs)
    readonly_namespace()
    checked(['mount', '-o', 'remount,bind,rw', str(scratch)])
    mount_shadows(log_binds)
    # Hide service-control and NSS sockets, including /var/run -> /run, and POSIX IPC.
    for target in ('/run', '/dev/shm'):
        checked(['mount', '-t', 'tmpfs', '-o', 'mode=755,nosuid,nodev', 'tmpfs', target])
    # OLS -t writes /tmp/lshttpd/testconf and derives its exit status from it.
    # It also invokes usermod. Both writes must succeed only in private overlays.
    for number, target in enumerate((Path('/tmp'), Path('/etc'), root)):
        upper, work, view = [scratch / (str(number) + name) for name in ('upper', 'work', 'view')]
        for directory in (upper, work, view):
            directory.mkdir()
        # OverlayFS exposes the upper directory's mode at the mount root.
        # Preserve traversal permissions inside the probe under restrictive umasks.
        mode = target.stat().st_mode & 0o7777
        upper.chmod(mode)
        options = 'lowerdir=%s,upperdir=%s,workdir=%s' % (target, upper, work)
        checked(['mount', '-t', 'overlay', 'overlay', '-o', options, str(view)])
        checked(['mount', '--bind', str(view), str(target)])
    os.environ['LSWS_HOME'] = str(root) + '/'
    os.environ['TMPDIR'] = str(scratch)
    tempfile.tempdir = str(scratch)
    if stock:
        # Stock startup runs the full server: remove inherited filesystem IPC
        # sockets as well as the abstract sockets isolated by the net namespace.
        isolate_stock_sockets()
        # A stock test/start cannot reuse any host PID, IPC socket or listener.
        pid_dir = Path('/tmp/lshttpd')
        if pid_dir.is_symlink():
            raise RuntimeError('Linked stock runtime directory')
        pid_dir.mkdir(exist_ok=True)
        checked(['mount', '-t', 'tmpfs', '-o', 'mode=755,nosuid,nodev', 'tmpfs', str(pid_dir)])
        private_loopback_up()
        from olsStockClassifier import require_bytes
        require_bytes(root, selected)
        stock_layout(root)
    if candidate:
        from olsSecurityAssets import SecurityAssetsTransaction, SECURITY_ASSETS_SHA256
        assets = SecurityAssetsTransaction(str(staging / 'security-assets.tar.gz'),
                                           SECURITY_ASSETS_SHA256, str(root), webadmin_policy='preserve')
        assets.apply()
        for kind, name, relative in (
                ('binary', 'openlitespeed', 'bin/openlitespeed'),
                ('module', 'cyberpanel_ols.so', 'modules/cyberpanel_ols.so'),
                ('modsec', 'mod_security.so', 'modules/mod_security.so')):
            if digest(staging / name) != driver.RELEASES[selected][kind]:
                raise RuntimeError('Candidate checksum changed: ' + kind)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Replacing symlinks avoids following a destination outside the overlay.
            temporary = target.with_name(target.name + '.parser-probe')
            with open(str(staging / name), 'rb') as source, open(str(temporary), 'xb') as output:
                shutil.copyfileobj(source, output)
            os.chmod(str(temporary), 0o755 if kind == 'binary' else 0o644)
            os.replace(str(temporary), str(target))
            if digest(target) != driver.RELEASES[selected][kind]:
                raise RuntimeError('Staged target checksum changed: ' + kind)
    elif not stock and digest(root / 'bin/openlitespeed') != OLD_CORE_SHA256[selected]:
        raise RuntimeError('Installed core changed before baseline execution')
    challenge = None
    if stock == 'smoke':
        challenge = make_stock_waf_challenge(root)
    result = ledger_test(root, stock_child_sandbox if stock else None)
    if stock:
        from olsStockClassifier import require_stock
        output = (result.stdout or '') + (result.stderr or '')
        if candidate:
            require_clean_candidate(root, result.returncode, output)
        else:
            try:
                require_stock(root, selected, result.returncode, output)
            except RuntimeError as exc:
                raise RuntimeError('Stock -t refused (rc=%s): %s' % (result.returncode, output[:700])) from exc
        # Prove the configured server starts with the unchanged controller and
        # that the observed master really runs the tested executable. Namespace
        # PID 1 exits after this proof; the kernel destroys all remaining tasks.
        if stock != 'stopped-baseline':
            service = driver.Service(root)
            service.unit = None
            # This daemon inherits the installer's cgroup; it has independently
            # verified private namespaces and is never controlled by host systemd.
            service.isolated_probe = True
            service.child_guard = stock_child_sandbox
            try:
                service.change('start')
            except RuntimeError as exc:
                if challenge and (root/'logs/ols-waf-canary.log').is_file():
                    details = [line for line in (root/'logs/ols-waf-canary.log').read_text(errors='replace').splitlines()
                               if 'ERROR' in line or 'FATAL' in line]
                    raise RuntimeError('Private WAF canary startup failed: '+str(details[-4:])) from exc
                raise RuntimeError('Private native start failed (%s)' % (
                    'WAF canary' if challenge else 'candidate' if candidate else 'stock baseline')) from exc
            stock_listener_response(root)
            if challenge:
                stock_waf_response(*challenge)
            identity = stock_service_identity(root, service)
            if not identity:
                raise RuntimeError('Isolated OLS server did not stay running')
            stock_loaded_modules(root, identity[0], candidate, selected)
    receipt = {'returncode': result.returncode, 'output': (result.stdout or '') + (result.stderr or '')}
    if stock and candidate:
        receipt['assets'] = {e['path']: e['sha256'] for e in assets.entries}
    print(json.dumps(receipt))


def ledger_test(root, child_guard=None):
    ledger = Path('/tmp/lshttpd/testconf')
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if ledger.exists() or ledger.is_symlink():
        ledger.unlink()
    with open(str(ledger), 'xb') as output:
        output.flush()
        os.fsync(output.fileno())
    libc = ctypes.CDLL(None, use_errno=True)
    descriptor = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
    if descriptor < 0 or libc.inotify_add_watch(descriptor, str(ledger).encode(), 0x20 | 0x400) < 0:
        raise RuntimeError('Cannot verify the native configuration diagnostic ledger')
    try:
        result = subprocess.run([str(root / 'bin/openlitespeed'), '-t'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, timeout=30, preexec_fn=child_guard)
        events = os.read(descriptor, 65536)
    finally:
        os.close(descriptor)
    observed = 0
    while events:
        _, mask, _, length = struct.unpack('iIII', events[:16])
        observed |= mask
        events = events[16 + length:]
    if observed & 0x420 != 0x420 or ledger.exists():
        raise RuntimeError('Native configuration test did not consume its fresh private diagnostic ledger')
    return result


def probe(root, staging, selected, candidate, stock=False):
    root = Path(root).resolve()
    # Overlay mount option grammar must never be influenced by an unusual path.
    if any(char in str(root) for char in (',', ':', '\\', '\n')):
        raise RuntimeError('Unsupported installation path for isolated parser probe')
    before = config_fingerprint(root)
    scratch_parent = Path(tempfile.gettempdir()).resolve()
    if str(scratch_parent).startswith('/tmp') or os.path.commonpath([str(root), str(scratch_parent)]) == str(root):
        scratch_parent = Path('/var/tmp')
    with tempfile.TemporaryDirectory(prefix='ols-parser-probe-', dir=str(scratch_parent)) as scratch:
        command = ['unshare', '--mount', '--propagation', 'private', '--pid', '--fork',
                   '--mount-proc', '--ipc', '--net', sys.executable,
                   '-B', '-E', '-s', str(Path(__file__).resolve()), '--namespace-probe',
                   str(root), str(Path(staging).resolve()), selected, scratch,
                   ('stock-waf-smoke' if stock == 'smoke' else 'stock-stopped-baseline' if stock == 'stopped-baseline'
                    else ('stock-' if stock else '') + ('candidate' if candidate else 'baseline'))]
        if stock:
            command.insert(1, '--kill-child=KILL')
        environment = dict(os.environ, CP_OLS_PARENT_NAMESPACES=json.dumps({
            name: os.readlink('/proc/self/ns/' + name) for name in ('mnt', 'pid', 'ipc', 'net')}))
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, timeout=180, env=environment)
    if before != config_fingerprint(root):
        raise RuntimeError('Installed configuration changed during isolated preflight')
    if result.returncode:
        raise RuntimeError('Isolated parser probe failed: ' + result.stderr[-3000:])
    return json.loads(result.stdout)


def prepare_recovery(root, staging, selected):
    if host_platform() != selected:
        raise RuntimeError('Recovery platform does not match this OS')
    root = Path(root)
    if digest(root / 'bin/openlitespeed') != OLD_CORE_SHA256[selected]:
        raise RuntimeError('Installed core is not the affected pinned release')
    baseline = probe(root, staging, selected, False)
    require_known_failure(root, selected, baseline['returncode'], baseline['output'])
    candidate = probe(root, staging, selected, True)
    _, baseline_warnings = split_diagnostics(root, baseline['output'])
    candidate_errors, candidate_warnings = split_diagnostics(root, candidate['output'])
    # Permit only the identical bounded pre-existing warnings; never a new one.
    expected_status = 1 if candidate_warnings else 0
    if candidate['returncode'] != expected_status or candidate_errors or candidate_warnings != baseline_warnings:
        raise RuntimeError('Candidate failed clean configuration validation: ' + candidate['output'][-3000:])
    return config_fingerprint(root)


def stock_layout(root):
    from olsStockClassifier import require_bytes, require_platform
    selected = require_platform(None)[0]
    require_bytes(root, selected)
    prefix = './' if selected == 'rhel9' else ''
    for rel, link in [('bin/litespeed', 'lshttpd'), ('bin/lshttpd', prefix+'openlitespeed'),
                      ('bin/lswsctrl', prefix+'lswsctrl.open')]:
        if not (root / rel).is_symlink() or os.readlink(str(root / rel)) != link:
            raise RuntimeError('Unsupported stock service layout: ' + rel)
    for rel, expected in [
        ('bin/lswsctrl.open', '5af78d0aede6c139f030210e1c080575a742789ed0110fa112357eecd1e27f67' if
         selected == 'rhel9' else 'cacef63b88f0eb0f95b82259c311dfe9b5ff08760f50ff30342dc6615246a114'),
        ('bin/lsws_env', '1851443bf9fa883d94967751e705611d5a630bfb0f5bf05553d73b6ed89edeb8')]:
        if (root / rel).is_symlink() or not (root / rel).is_file() or digest(root / rel) != expected:
            raise RuntimeError('Unrecognized stock controller: ' + rel)
    if os.path.lexists(str(root / 'bin/get_trial_key.sh')) or os.getenv('WSWATCH'):
        raise RuntimeError('Stock controller startup side effects are unsupported')


def stock_child_sandbox():
    """Native descendants may listen and reply but cannot contact host IPC.

    Filesystem Unix sockets can live outside /run. A read-only bind does not
    prevent connecting or sending datagrams to them. Keep this filter in every
    descendant, never in the parent conducting its private HTTP client probe.
    """
    import errno
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not ctx:
        raise RuntimeError('Cannot initialize stock native sandbox')
    try:
        for name in ('connect', 'sendmsg', 'sendmmsg', 'io_uring_setup', 'mount', 'mount_setattr',
                     'setns', 'unshare', 'fsopen', 'open_tree', 'move_mount', 'umount2',
                     'pivot_root', 'bpf', 'ptrace', 'pidfd_getfd'):
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            if nr < 0 or lib.seccomp_rule_add(ctx, 0x00050000 | errno.EPERM, nr, 0):
                raise RuntimeError('Cannot restrict stock probe syscall: ' + name)
        # sendto(fd,buf,n,flags,NULL,0) is also used for ordinary replies.
        # Deny sendto with an explicit destination (including Unix datagrams).
        class Compare(ctypes.Structure):
            _fields_ = [('arg',ctypes.c_uint),('op',ctypes.c_uint),('a',ctypes.c_uint64),('b',ctypes.c_uint64)]
        lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
                                                ctypes.c_uint, ctypes.POINTER(Compare)]
        if lib.seccomp_rule_add_array(ctx, 0x00050000 | errno.EPERM,
                lib.seccomp_syscall_resolve_name(b'sendto'), 1, ctypes.byref(Compare(4, 1, 0, 0))):
            raise RuntimeError('Cannot restrict native probe datagrams')
        if lib.seccomp_load(ctx):
            raise RuntimeError('Cannot enforce stock native sandbox')
    finally:
        lib.seccomp_release(ctx)


def isolate_stock_sockets():
    # Foreign pathname sockets can be reachable even in a private net namespace.
    # System services live under /run and /dev/shm (already hidden); replace /tmp
    # completely, and hide inherited service-control sockets in the server tree.
    checked(['mount', '-t', 'tmpfs', '-o', 'mode=1777,nosuid,nodev', 'tmpfs', '/tmp'])
    for name in ('admin/tmp', 'tmp'):
        path = Path('/usr/local/lsws') / name
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError('Unsupported stock runtime path: ' + str(path))
        checked(['mount', '-t', 'tmpfs', '-o', 'mode=1777,nosuid,nodev', 'tmpfs', str(path)])


def make_stock_waf_challenge(root):
    # A separate private overlay, after verifying startup with the entire
    # original config. This canary cannot modify or enable the installed WAF.
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    site = Path(tempfile.mkdtemp(prefix='ols-waf-canary-', dir=str(root)))
    os.chmod(str(site), 0o755)
    os.chown(str(site), 65534, 65534)
    token = 'private-waf-canary'
    (site / 'check.txt').write_text(token)
    # OLS reads this generated file as the canary worker, not as root.
    (site / "check.txt").chmod(0o644)
    (site / 'vhost.conf').write_text('docRoot %s/\n' % site)
    conf = site / 'httpd_config.conf'
    conf.write_text("""user nobody
group %s
disableWebAdmin 1
serverName private-recovery
mime conf/mime.properties
httpdWorkers 1
errorLog logs/ols-waf-canary.log {
 logLevel INFO
}
accessLog logs/access.log {
 rollingSize 1M
}
tuning {
 maxConnections 64
 maxSSLConnections 16
}
module cyberpanel_ols {
 ls_enabled 1
}
module mod_security {
 modsecurity on
 modsecurity_rules `
SecRuleEngine On
SecRule ARGS:cp_recovery "@streq block" "id:1099281,phase:1,deny,status:403,nolog"
`
}
virtualhost RecoveryCanary {
 vhRoot %s/
 configFile %s/vhost.conf
 allowSymbolLink 1
 restrained 1
}
listener Canary {
 address 127.0.0.1:%s
 secure 0
 map RecoveryCanary *
}
""" % (__import__('grp').getgrgid(65534).gr_name, site, site, port))
    os.replace(str(conf), str(root / 'conf/httpd_config.conf'))
    return port, token


def stock_waf_response(port, token):
    import http.client
    for path, expected in [('/check.txt', 200), ('/check.txt?cp_recovery=block', 403)]:
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=4)
        try:
            conn.request('GET', path, headers={'Host':'ols-recovery.invalid', 'Connection':'close'})
            reply = conn.getresponse()
            if reply.status != expected or (expected == 200 and reply.read(1024) != token.encode()):
                raise RuntimeError('Isolated HTTP/WAF canary failed: expected %s, got %s' % (expected, reply.status))
        finally:
            conn.close()


def stock_process_owner(path, unit):
    """Accept manual/scope control or the positively identified systemd unit."""
    owners = set()
    for line in path.read_text().splitlines():
        fields = line.split(':', 2)
        if len(fields) != 3 or not fields[0].isdigit() or not fields[2].startswith('/'):
            raise RuntimeError('Cannot identify stock process control group')
        if not ((fields[0]=='0' and fields[1]=='') or 'name=systemd' in fields[1].split(',')):
            continue
        components = Path(fields[2]).parts
        if '..' in components:
            raise RuntimeError('Unresolved stock process control group')
        services = [part for part in components if part.endswith('.service')]
        owners.add(services[-1] if services else None)
    if not owners or len(owners) != 1:
        raise RuntimeError('Missing or conflicting stock systemd control-group evidence')
    if owners != {unit}:
        raise RuntimeError('Unknown systemd service controls the OLS master; refusing direct controller action')


def stock_controller_scope(root, service, action='inspect', proc=Path('/proc')):
    """Do not let vendor-wide pkill or an unknown service unit affect other jobs."""
    from installBundle import run
    if (os.path.lexists(str(root/'admin/tmp/.restart')) or
            os.path.lexists(str(root/'bin/get_trial_key.sh')) or os.getenv('WSWATCH')):
        raise RuntimeError('Unsupported stock controller restart/watchdog side effects')
    # lswsctrl uses "pkill wswatch.sh" and, on a failed start, "pkill -9
    # litespeed". Match the same unanchored process-name regex. Never signal
    # these jobs, and never execute that controller while its match set is unsafe.
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        try:
            name = (item/'comm').read_text().rstrip('\n')
            if re.search(r'wswatch.sh', name):
                raise RuntimeError('Vendor controller may stop an existing watchdog; refusing')
            if 'litespeed' in name and not os.path.samefile(str(item/'exe'), str(root/'bin/openlitespeed')):
                raise RuntimeError('Vendor controller may stop an unrelated LiteSpeed process; refusing')
        except (FileNotFoundError, ProcessLookupError):
            continue
    if not service.unit:
        if action == 'stop':
            pid = int(Path('/tmp/lshttpd/lshttpd.pid').read_text())
            if pid < 1 or not os.path.samefile(str(proc/str(pid)/'exe'),str(root/'bin/openlitespeed')):
                raise RuntimeError('Stock master is ambiguous immediately before direct control')
            stock_process_owner(proc/str(pid)/'cgroup', None)
        return
    fields = 'Id,LoadState,FragmentPath,DropInPaths,NeedDaemonReload,ActiveState,MainPID'
    result = run(['systemctl','show',service.unit,'--property='+fields],30)
    values = dict(line.split('=',1) for line in (result.stdout or '').splitlines() if '=' in line)
    path = Path(values.get('FragmentPath',''))
    unit_sha = 'e1a05ef5fbaba9b5eed156ac77fe4b91019cd0e433bfefd46cdfa02af78b199d'
    if (result.returncode or service.unit not in ('lsws.service','lshttpd.service','openlitespeed.service') or
            values.get('Id') != service.unit or values.get('LoadState') != 'loaded' or
            values.get('DropInPaths') != '' or values.get('NeedDaemonReload') != 'no' or
            not path.is_absolute() or not path.is_file() or digest(path) != unit_sha):
        raise RuntimeError('Unverified stock systemd controller or unit override')
    if action == 'start':
        if values.get('ActiveState') not in ('inactive','failed') or values.get('MainPID') != '0':
            raise RuntimeError('Stock systemd unit is not confirmed stopped')
    else:
        pid = values.get('MainPID','')
        if (values.get('ActiveState') != 'active' or not re.fullmatch('[1-9][0-9]*',pid) or
                not os.path.samefile(str(proc/pid/'exe'),str(root/'bin/openlitespeed')) or
                int(pid) != int(Path('/tmp/lshttpd/lshttpd.pid').read_text())):
            raise RuntimeError('Stock systemd master changed before controller action')


def stock_listener_response(root):
    """Probe an ordinary configured cleartext listener inside the private netns."""
    import http.client
    content = (root / 'conf/httpd_config.conf').read_text()
    for body in re.findall(r'(?im)^[ \t]*listener[ \t]+[^\s{}]+[ \t]*\{([^{}]*)\}', content):
        addresses = re.findall(r'(?im)^[ \t]*address[ \t]+(?:\*|127\.0\.0\.1|0\.0\.0\.0):([0-9]+)[ \t]*$', body)
        secure = re.findall(r'(?im)^[ \t]*secure[ \t]+([01])[ \t]*$', body)
        if len(addresses) != 1 or secure != ['0'] or not 0 < int(addresses[0]) <= 65535:
            continue
        conn = http.client.HTTPConnection('127.0.0.1', int(addresses[0]), timeout=4)
        try:
            conn.request('GET', '/.well-known/cyberpanel-ols-recovery-probe',
                         headers={'Host': 'ols-recovery.invalid', 'Connection':'close'})
            reply = conn.getresponse()
            if reply.status not in (200, 204, 301, 302, 307, 308, 401, 403, 404, 410):
                raise RuntimeError('Unusable private stock HTTP probe status: %s' % reply.status)
        finally:
            conn.close()
        return
    raise RuntimeError('No supported ordinary HTTP listener for isolated stock startup proof')


def stock_service_identity(root, service, proc=Path('/proc')):
    # A missing status PID is insufficient to call a service stopped. Find its
    # workers and verify all descend from the exact controller-reported master.
    running = service.running()
    master = int(Path('/tmp/lshttpd/lshttpd.pid').read_text()) if running else None
    binary = root / 'bin/openlitespeed'
    aliases = {str(root / 'bin' / name) for name in ('openlitespeed', 'lshttpd', 'litespeed')}
    seen = {}
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        try:
            executable = os.readlink(str(item / 'exe'))
            same = os.path.samefile(str(item / 'exe'), str(binary))
            if same or (executable[:-10] if executable.endswith(' (deleted)') else executable) in aliases:
                if not same or executable.endswith(' (deleted)'):
                    raise RuntimeError('Live OLS process uses a different or deleted executable')
                fields = (item / 'stat').read_text().rsplit(')', 1)[1].split()
                seen[int(item.name)] = (int(fields[1]), fields[19])
        except (FileNotFoundError, ProcessLookupError):
            continue  # no userspace executable (dead task, kernel thread or race)
    if not running:
        if seen:
            raise RuntimeError('OLS status missed a running process')
        return None
    if master not in seen:
        raise RuntimeError('Cannot establish stock master identity')
    for pid in seen:
        ancestors = set()
        while pid != master:
            if pid in ancestors or pid not in seen:
                raise RuntimeError('Unmanaged additional OLS process')
            ancestors.add(pid)
            pid = seen[pid][0]
    if not getattr(service, 'isolated_probe', False):
        stock_process_owner(proc/str(master)/'cgroup', service.unit)
    return (master, seen[master][1], service.unit)


def require_clean_candidate(root, rc, output):
    from olsParserRecovery import split_diagnostics
    errors, warnings = split_diagnostics(root, output)
    if errors or len(warnings) != len(set(warnings)) or rc != (1 if warnings else 0):
        raise RuntimeError('Unsafe candidate native configuration result: ' + output[-1500:])


def private_loopback_up():
    import socket
    import fcntl
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        request = struct.pack('16sH22x', b'lo', 0)
        flags = struct.unpack('16sH22x', fcntl.ioctl(sock.fileno(), 0x8913, request))[1]
        fcntl.ioctl(sock.fileno(), 0x8914, struct.pack('16sH22x', b'lo', flags | 1))


def vendor_waf_digests(selected, original):
    """Accept vendor bytes verified from the matching signed OLS WAF packages."""
    approved = {original}
    if selected == 'rhel9':
        # ols-modsecurity-1.9.4-3.el9.x86_64.rpm, LiteSpeed vendor signature
        # 42259994257E19EB6A91CA853F6F627083084D0E from the EL9 update repo.
        approved.add('7307fc447261d98fd4d8724c7cb1b7b64a95f9574823c8713779becd7b16504b')
    return approved


def stock_loaded_modules(root, pid, candidate, selected):
    # ModuleManager::loadModules initializes external modules in the master
    # before workers fork. Ignore distro system libraries; explicitly bind
    # the configured OLS module graph to the installed or staged artifacts.
    from installBundle import RELEASES
    from olsStockClassifier import require_platform
    _, _, paired_module, stock_waf = require_platform(selected)
    modules = root / 'modules'
    approved = {
        'cyberpanel_ols.so': {RELEASES[selected]['module'] if candidate else paired_module},
        'mod_security.so': ({RELEASES[selected]['modsec']} if candidate
                            else vendor_waf_digests(selected, stock_waf)),
    }
    loaded, checked_maps = set(), set()
    for line in Path('/proc/%s/maps' % pid).read_text().splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6 or not fields[5].startswith(str(modules) + '/'):
            continue
        path = Path(fields[5])
        if (path.parent != modules or path.name not in approved or path.is_symlink() or not path.is_file()):
            raise RuntimeError('Unexpected native OLS module in isolated server: ' + str(path))
        mapped_id = (fields[3], fields[4], path.name)
        if mapped_id not in checked_maps:
            # Overlay mounts expose different stat device/inode numbers from the
            # underlying file recorded in /proc/maps. Hash the actual mapped
            # file via the kernel, not a second lookup by pathname.
            mapping = Path('/proc/%s/map_files' % pid) / fields[0]
            mapped_digest = digest(mapping)
            if mapped_digest not in approved[path.name] or digest(path) != mapped_digest:
                raise RuntimeError('Mapped OLS module differs from pinned file: ' + str(path))
            checked_maps.add(mapped_id)
        loaded.add(path.name)
    if 'cyberpanel_ols.so' not in loaded:
        raise RuntimeError('Paired module is missing from the isolated server')


# This profile matches CyberPanel's OWASP installer and upstream CRS 3.3.2
# commit 18703f1bc47e9c4ec4096853d5fb4e2a204a07a2. Rules are never replaced.
CRS_DIRECTORY = 'owasp-modsecurity-crs-3.0-master'
CRS_SHA256 = {'crs-setup.conf': 'bb065ec8287c1b3b474ca8e517817ae786e035410bf777c74f8c1ff57495e6b8',
 'rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf': '539d75e7eb0a7e6ffdac741353e1ee23b15adf5bd4dae193c8e7dd4e3f201bd1',
 'rules/REQUEST-901-INITIALIZATION.conf': '56139099a4f0af44391d7e63fe55dedc39c7c56c4ec7601edbbfb7f9de8a2e64',
 'rules/REQUEST-903.9001-DRUPAL-EXCLUSION-RULES.conf': '85dfaedda326273ecf33ee7a34d84de525dbb057c91ef598468285a51ce17844',
 'rules/REQUEST-903.9002-WORDPRESS-EXCLUSION-RULES.conf': '026fa8260d839b7e23d25823574ed1299c6424a23d32cf53d50d36deea74c0b8',
 'rules/REQUEST-903.9003-NEXTCLOUD-EXCLUSION-RULES.conf': 'a8a8f7317de921e81b4804a19af3130c3490692c9df3f26b5345abd1043cd880',
 'rules/REQUEST-903.9004-DOKUWIKI-EXCLUSION-RULES.conf': 'a8e5af1a412697a6243672a6be73997e3ef8b9a2affb27ead6b04cf1918feabc',
 'rules/REQUEST-903.9005-CPANEL-EXCLUSION-RULES.conf': '41f38f58bdce57a2bb4f73b55258408c03a53fee222e427bb47c78cc4c4b46b1',
 'rules/REQUEST-903.9006-XENFORO-EXCLUSION-RULES.conf': 'c210aaaa442b8a228e4656efd3526fdddb511007d9d30eeee87b60929fa3a67a',
 'rules/REQUEST-905-COMMON-EXCEPTIONS.conf': 'e04493e4cad6505d0012205e56119136a17764129953d58204b13ad927ccb481',
 'rules/REQUEST-910-IP-REPUTATION.conf': 'dc69757f052ef6b81bb3ba1366a6a2039480954088d315f9712e5eb2191a82bd',
 'rules/REQUEST-911-METHOD-ENFORCEMENT.conf': '77db6f722c7b22a82afd2f8b76dc3de57564b510a4f929b15c730b8d03a4c9e6',
 'rules/REQUEST-912-DOS-PROTECTION.conf': '440ff858ecea85f7f9b36faa504c0dc60cb3802ffdfa4c08b22405faf37a1b79',
 'rules/REQUEST-913-SCANNER-DETECTION.conf': 'bfab1cb8a25a14c46ae5873fc376c059a873be1d9523b77be322c6c3656f6dce',
 'rules/REQUEST-920-PROTOCOL-ENFORCEMENT.conf': '47d99cdd3b630aa6b9b0f40903bb21cf269a23a5fa5ec5f481b6557c799a69b1',
 'rules/REQUEST-921-PROTOCOL-ATTACK.conf': 'd1d3237248cd2e674cabd59b93110e82489b0884a5a8050fb95dc75e9e6eeb5d',
 'rules/REQUEST-930-APPLICATION-ATTACK-LFI.conf': '33c75abd7eeb68b4545f195539224962395448f7b36278af13cdb65b41ebce7a',
 'rules/REQUEST-931-APPLICATION-ATTACK-RFI.conf': 'b812d6a58eb077dc64b418d8d57f3a718196327d769dce89c9045ebffd432c7a',
 'rules/REQUEST-932-APPLICATION-ATTACK-RCE.conf': '405da70852ea31eaac6f36163cf907af6a6573a9e212b40d5a543063b09abc2c',
 'rules/REQUEST-933-APPLICATION-ATTACK-PHP.conf': '1189dcdd92554537acfeb6a26d9c259d0418a3ce384530981a120c651d6dadef',
 'rules/REQUEST-934-APPLICATION-ATTACK-NODEJS.conf': 'f098d2732103b93b39ebb4c5ff9c1463cebdbc836de9b14688c21597d28f181d',
 'rules/REQUEST-941-APPLICATION-ATTACK-XSS.conf': 'a50a92e904597cf0804ecbfc890b3af1dc963ee898ac6f9a8659188ad4e77e04',
 'rules/REQUEST-942-APPLICATION-ATTACK-SQLI.conf': '7d0dfc305d86dde03b467b8b68546272d88d530bbc83eb6fb2d60ac014375b50',
 'rules/REQUEST-943-APPLICATION-ATTACK-SESSION-FIXATION.conf': '90fd4e25ed56d7310e26da8a94893460c119017fd344e7226413a177b55f7fd7',
 'rules/REQUEST-944-APPLICATION-ATTACK-JAVA.conf': '51c9c83d5a12541cf377cbb6f8fd3b9b18b1e8436339729fc6179e1737b3828e',
 'rules/REQUEST-949-BLOCKING-EVALUATION.conf': '5fbac998880935d50111edd7b3c5590fa636a22fd197ef44ea7b73c8615cbeb8',
 'rules/RESPONSE-950-DATA-LEAKAGES.conf': 'cad9d3224e84647fc6e62f3bca240a22c790e5ff2c92b9e45693dd4bdf723f1c',
 'rules/RESPONSE-951-DATA-LEAKAGES-SQL.conf': 'c306d761d4579debf2234a296c87b652a133e01d5df3dc6f5f753039d6c266f2',
 'rules/RESPONSE-952-DATA-LEAKAGES-JAVA.conf': '418c06148eea4821e3f95b5579a0e466f086c914450113fc3312e036b53bcbc9',
 'rules/RESPONSE-953-DATA-LEAKAGES-PHP.conf': '50a8ae512574c5c0e48511dc24a53a471b8191965b59e68e7c4fe6b33308bff7',
 'rules/RESPONSE-954-DATA-LEAKAGES-IIS.conf': '4d7125aa290cd98d2cdd5e4dc00b6a8bb8d939c1c444ae8bb35c58b6a1a26808',
 'rules/RESPONSE-959-BLOCKING-EVALUATION.conf': '2fc74240b7ae90350156368b6ab851720fd2e499f34da752b16852101f9b502b',
 'rules/RESPONSE-980-CORRELATION.conf': 'dffe1d4c5ddcda51a92c424d15f210bf039fd828c0d66418050e30351f7e9105',
 'rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf': 'b76d9f6128f2b7f160191a8b3b24327fa6cf6c576cd246065e8a3e9a9f0ec7ae',
 'rules/crawlers-user-agents.data': '8b921d3deafab1bf395d98ce62383afd65618c5fad0c0be06c4ac394024fa5e7',
 'rules/iis-errors.data': 'fb40a871496599882f2b1dde3b10fa16bada18082cb3538e9cd7dc0ba1773001',
 'rules/java-classes.data': '43441681b1b40889c97428597f35cf1708b1a7957290e645e46db890e2befbb4',
 'rules/java-code-leakages.data': 'cef3ac262bd5aff61eff1ed783ced149041bd44667cfd68a224d765b91a4660a',
 'rules/java-errors.data': 'ddc0c0f6f7f9ed4be844b725f73bda72c6a12712a0a7e1e15f5343f429611160',
 'rules/lfi-os-files.data': 'c7b8b98f2d18b1b23f27466ca3f26013fac183e9acfbd3f3e7ba85a056b2596c',
 'rules/php-config-directives.data': 'edb347416d697ca72ed50ae24701925082b65ee841d50036d71dc9e23e7c7f82',
 'rules/php-errors.data': 'e15890dfef62c52f6ffadeaed8ca542452c50a0b9b0383c1d3f5c018b716f47b',
 'rules/php-function-names-933150.data': '2d5b5c300839de027daca356b7755039c1c3f6b0b85a7edad94bf22217b6f544',
 'rules/php-function-names-933151.data': '4dc76522c2d79a5d6211621d90c19058c6361ce1eb1037e571d70e6148bf6879',
 'rules/php-variables.data': 'd2db4baa63b2512079c424b1982a960b45b1f112ce4010cbf3b707169b166099',
 'rules/restricted-files.data': '2053965cadfec3bc7d598d0d2292975a2327f794f6d87fe6d67f11227d8ccf4b',
 'rules/restricted-upload.data': '9d6565e2b95f2f382a102bdf5c24056354b507ea9923954480a2c14f84dec93e',
 'rules/scanners-headers.data': 'c32b2bdd5db260ddd4a94e9ad6cbb0afe2f7fe3f83ae1d3e7265b3f3794ab970',
 'rules/scanners-urls.data': '28c12103022af25a6a27139c81ed772adee41db13e776976d7527e650ba01b4c',
 'rules/scanners-user-agents.data': '5fed9b3e9f617123fb8afbb015c1923d4b8e23cd18135a2012b3ee50ece9a582',
 'rules/scripting-user-agents.data': 'cea4807edc1429b3f0784a9d773d72ca70f6e826cb95154196166ce89dbf42fb',
 'rules/sql-errors.data': 'b0bff288c118e6ea4ee4449f106e02837b3a5b996ad5240a09d72b33f2b7566b',
 'rules/unix-shell.data': '279710a6dd5d6b3ae7ce951621381407171731a770a9ad44d67e2a85bc1bafda',
 'rules/windows-powershell-commands.data': 'f43771664b8eec658d0c30b4cbdaeff17e360635eff677b47b639002152b24b1'}
DEFAULT_PANEL_RULE = 'SecRule ARGS "\\.\\./" "t:normalisePathWin,id:99999,severity:4,msg:\'Drive Access\' ,log,auditlog,deny"'
WAF_FILE = re.compile(r'^[ \t]*(?i:modsecurity_rules_file)[ \t]+(.+)$', re.M)
WAF_INCLUDE = re.compile(r'(?i:include)[ \t]+(.+)')
WAF_IP_SETTINGS = re.compile(
    r'(?i)(?:block_(?:suspicious_ip|harvester_ip|spammer_ip|search_ip)|'
    r'high_risk_country_codes|SecHttpBlKey|SecGeoLookupDb)')


def waf_path(value, base, glob_ok=False):
    """Native word expansion is safe only for this absolute path grammar."""
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    if not re.fullmatch(r'/[A-Za-z0-9._/-]+(?:\*\.conf)?', value):
        raise RuntimeError('Unrecognized local ModSecurity file reference')
    path = Path(value)
    if any(part in ('.', '..') for part in value.split('/')) or base not in path.parents:
        raise RuntimeError('ModSecurity file reference escapes conf/modsec')
    if path.suffix != '.conf' or ('*' in value and
                                  (not glob_ok or path != base / CRS_DIRECTORY / 'rules/*.conf')):
        raise RuntimeError('Unsupported ModSecurity file pattern')
    return path


def collect_waf_entries(text, root):
    base = root / 'conf/modsec'
    entries = []

    def collect(match):
        entry = waf_path(match[1], base)
        if entry not in (base/'rules.conf', base/CRS_DIRECTORY/'owasp-master.conf'):
            raise RuntimeError('Unsupported local ModSecurity entry point')
        entries.append(entry)
        return ''

    text = WAF_FILE.sub(collect, text)
    if re.search(r'(?im)^\s*modsecurity_rules_file\b', text):
        raise RuntimeError('Unrecognized local ModSecurity file directive')
    return text, entries


PANEL_INLINE_SETTINGS = re.compile(
    r'(?i:SecRuleEngine)[ \t]+(?i:On|Off|DetectionOnly)|'
    r'(?i:SecDebugLogLevel)[ \t]+[0-9]|'
    r'(?i:SecAuditEngine)[ \t]+(?i:On|Off|RelevantOnly)|'
    r'(?i:SecAuditLogParts)[ \t]+[A-Z]+|'
    r'(?i:SecAuditLogType)[ \t]+Serial')


def require_full_waf_keys(text):
    # Native module keys also accept prefixes. Recovery must never inspect a
    # shortened spelling as inert text while the native parser executes it.
    keys = ('modsecurity', 'modsecurity_rules', 'modsecurity_rules_file',
            'modsecurity_rules_remote')
    logical = text.replace('\r\n', '\n')
    if any((ord(char) < 32 and char not in '\t\n') or ord(char) == 127 for char in logical):
        raise RuntimeError('Control characters in OLS configuration are unsupported')
    parameter_block = None
    for line in logical.split('\n'):
        if parameter_block and line.strip(' \t') == parameter_block:
            parameter_block = None
            continue
        match = re.match(r'^[ \t]*([A-Za-z_]+)(?=[ \t\\<]|$)', line)
        if not match:
            continue
        key = match[1].lower()
        waf_key = any(full.startswith(key) for full in keys) or key.startswith('modsecurity')
        if parameter_block and waf_key:
            raise RuntimeError('ModSecurity parameters in an alternate parameter block are unsupported')
        if key == 'param':
            # The shipped cache module uses this form. Permit its ordinary
            # parameter block, while refusing hidden WAF keys in its body.
            opening = re.fullmatch(r'[ \t]*(?i:param)[ \t]+<<<([A-Za-z0-9_]+)[ \t]*', line)
            if parameter_block or not opening:
                raise RuntimeError('Alternate OLS module parameter form is unsupported')
            parameter_block = opening[1]
            continue
        if any(full.startswith(key) for full in keys) and ('<<<' in line or line.rstrip(' \t').endswith('\\')):
            raise RuntimeError('Assembled ModSecurity parameter syntax is unsupported')
        if (key not in keys and
                (any(full.startswith(key) for full in keys) or key.startswith('modsecurity'))):
            raise RuntimeError('Abbreviated or unknown ModSecurity parameter is unsupported')
    if parameter_block:
        raise RuntimeError('Unterminated alternate OLS parameter block')


def offline_method_action(line):
    """Recognize a static phase-one method policy, without executing actions.

    Accept only the inert actions used alongside tx.allowed_methods. In
    particular, a second assignment, macro expansion, persistent collection,
    disruptive action or transformation must not enter the offline probe.
    """
    match = re.fullmatch(r'(?i:SecAction)[ \t]+"([^"\r\n]+)"', line)
    if not match:
        return False
    actions = match[1].split(',')
    if len(actions) != 6:
        return False
    fixed = {'phase:1', 'nolog', 'pass', 't:none'}
    if not fixed.issubset(actions):
        return False
    remaining = [part for part in actions if part not in fixed]
    if len(remaining) != 2:
        return False
    ids = [part for part in remaining if re.fullmatch(r'id:[1-9][0-9]{0,9}', part)]
    assignments = [part for part in remaining if part.startswith('setvar:')]
    if len(ids) != 1 or int(ids[0][3:]) > 2147483647 or len(assignments) != 1:
        return False
    assignment = assignments[0][7:]
    if assignment.startswith("'") and assignment.endswith("'"):
        assignment = assignment[1:-1]
    return bool(re.fullmatch(
        r'tx\.allowed_methods=[A-Z][A-Z0-9_-]*(?: +[A-Z][A-Z0-9_-]*)*', assignment))


def require_offline_crs_settings(documents, root):
    # The pinned IP reputation rules are inert with default CRS setup. When
    # those rules are loaded, allow the panel's declarative inline options
    # and static method policies only. Arbitrary SecAction/SecRule can
    # otherwise set reputation flags. Never rewrite the customer's rules.
    fixed = {
        'SecDebugLog ' + str(root/'logs/modsec.log'),
        'SecAuditLog ' + str(root/'logs/auditmodsec.log'),
        'SecAuditLogRelevantStatus "^(?:5|4(?!04))"',
    }
    def option(line, marker):
        # The native parser closes a string on the matching quote. Refuse
        # concatenated/escaped quoting rather than inspect different bytes
        # from those the native module will receive.
        if marker in line or '\\' in line:
            raise RuntimeError('Ambiguous inline ModSecurity quoting')
        if line not in fixed and not PANEL_INLINE_SETTINGS.fullmatch(line) and not offline_method_action(line):
            raise RuntimeError('Custom inline options are unsupported with CRS IP reputation rules')

    for text in documents:
        require_full_waf_keys(text)
        marker = None
        for source in text.split('\n'):
            line = source.strip(' \t\r')
            if not line or line.startswith('#'):
                continue
            if WAF_IP_SETTINGS.search(line):
                raise RuntimeError('Configured CRS IP reputation dependencies are unsupported')
            if marker:
                if line == marker:
                    marker = None
                else:
                    option(line, marker)
            elif re.match(r'(?i:modsecurity_rules)\b', line):
                opening = re.fullmatch(r'''(?i:modsecurity_rules)[ \t]+([`'"])(.*)''', line)
                if not opening:
                    raise RuntimeError('Unsupported inline ModSecurity syntax')
                marker, tail = opening.groups()
                if tail:
                    if not tail.endswith(marker):
                        raise RuntimeError('Unsupported inline ModSecurity syntax')
                    option(tail[:-1].strip(' \t'), marker)
                    marker = None
        if marker:
            raise RuntimeError('Unterminated inline ModSecurity block')


def verify_waf_graph(root, entries, documents, inventory, snapshot):
    import pwd

    base = root / 'conf/modsec'
    crs = base / CRS_DIRECTORY
    trusted = {0}
    lsadm = pwd.getpwnam('lsadm')
    if (lsadm.pw_uid != pwd.getpwnam('nobody').pw_uid and
            Path(lsadm.pw_shell).name in ('nologin', 'false')):
        trusted.add(lsadm.pw_uid)

    def file_record(path):
        if path not in inventory:
            raise RuntimeError('Missing local ModSecurity dependency: ' + str(path.relative_to(base)))
        record = inventory[path]
        mode, uid = record[4][2:4]
        if record[2] is not None or uid not in trusted or mode & 0o022 or Path(record[1]) != path:
            raise RuntimeError('Untrusted local ModSecurity file: ' + str(path.relative_to(base)))
        for parent in path.parents:
            if parent == root.parent:
                break
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid not in trusted or info.st_mode & 0o022:
                raise RuntimeError('Untrusted local ModSecurity directory')
        return record

    active = set()
    verified = set()
    need_data = False
    ordered_crs = []

    def visit(path):
        nonlocal need_data
        if path in active:
            raise RuntimeError('Cycle in local ModSecurity includes')
        if path in verified:
            raise RuntimeError('Duplicate local ModSecurity include: ' + path.name)
        if len(active) >= 24:
            raise RuntimeError('Local ModSecurity includes are nested too deeply')
        record = file_record(path)
        relative = path.relative_to(crs).as_posix() if crs in path.parents else None
        if relative in CRS_SHA256:
            if record[-1] != CRS_SHA256[relative]:
                raise RuntimeError('Local OWASP CRS file differs from the approved version: ' + relative)
            need_data |= path.parent == crs/'rules'
            ordered_crs.append(relative)
            verified.add(path)
            return
        if path.parent not in (base, crs):
            raise RuntimeError('Unrecognized local OWASP CRS configuration: ' + path.name)
        captured, text = snapshot(path, capture=True)
        if captured != record:
            raise RuntimeError('ModSecurity configuration changed during inspection')
        active.add(path)
        for line in text.split('\n'):
            line = line.strip(' \t\r')
            if not line or line.startswith('#'):
                continue
            include = WAF_INCLUDE.fullmatch(line)
            if include:
                target = waf_path(include[1], base, glob_ok=True)
                if '*' in target.name:
                    matches = sorted(Path(item) for item in glob.glob(str(target)))
                    if not matches:
                        raise RuntimeError('No files matched the local CRS rule pattern')
                    for match in matches:
                        visit(match)
                else:
                    visit(target)
            elif line != DEFAULT_PANEL_RULE and not re.fullmatch(
                    r'(?i:SecRuleEngine)[ \t]+(?i:On|Off|DetectionOnly)|'
                    r'(?i:SecRuleRemoveById)(?:[ \t]+[0-9]+(?:-[0-9]+)?)+', line):
                raise RuntimeError('Unsupported local ModSecurity directive in ' + path.name)
        active.remove(path)
        verified.add(path)

    for entry in entries:
        visit(entry)
    if ordered_crs:
        require_offline_crs_settings(documents, root)
        required = ('crs-setup.conf', 'rules/REQUEST-901-INITIALIZATION.conf',
                    'rules/REQUEST-949-BLOCKING-EVALUATION.conf',
                    'rules/RESPONSE-959-BLOCKING-EVALUATION.conf')
        if (any(name not in ordered_crs for name in required) or
                tuple(name for name in ordered_crs if name in required) != required or
                ordered_crs[0] != required[0]):
            raise RuntimeError('Incomplete or incorrectly ordered local OWASP CRS configuration')
    if need_data:
        for name, digest in CRS_SHA256.items():
            if not name.endswith('.data'):
                continue
            path = crs / name
            if file_record(path)[-1] != digest:
                raise RuntimeError('Local OWASP CRS data differs from the approved version: ' + path.name)



def stock_config_policy(text, root):
    # The built-in cache is registered before dlopen (ModuleManager::loadModule);
    # our two release modules have separately verified on-disk pins. Third-party
    # modules can survive startup but fail at an untested LSI hook after upgrade.
    require_full_waf_keys(text)
    for line in text.splitlines():
        if re.match(r'^\s*module\b', line, re.I):
            match = re.fullmatch(r'\s*module\s+([A-Za-z0-9_]+)\s*\{\s*(?:#.*)?', line, re.I)
            if not match or match.group(1) not in ('cache', 'cyberpanel_ols', 'mod_security'):
                raise RuntimeError('Unsupported external or ambiguous OLS module in stock configuration')
        if re.match(r'^\s*(?:<|loadmodule\b|loadmodulefile\b)', line, re.I):
            raise RuntimeError('Unsupported alternate OLS module/configuration syntax')
    # Accept only the bounded local entry grammar. Every referenced file is
    # verified by config_fingerprint before the native probes run.
    text, waf_entries = collect_waf_entries(text, root)
    if re.search(r'(?im)^\s*(?:readapacheconf|modsecurity_rules_remote|'
                 r'scrulesfile|secremoterules|secunicodeMapFile|secRuleScript|lua_load_resty_core)\b', text):
        raise RuntimeError('Unsupported external stock configuration/WAF dependency')
    if re.search(r'(?im)@(?:pmFromFile|ipMatchFromFile|inspectFile|validateDTD|validateSchema|'
                 r'verifyCC|fuzzyHash)\b|(?:^|[,\s"\x27])exec:|(?:^|[,\s"\x27])\+?@(?:rbl|geoLookup)\b', text):
        raise RuntimeError('Unsupported external dependency in stock WAF rule')

    return waf_entries


def stock_state(root, service):
    stock_layout(root)
    stock_controller_scope(root, service)
    if os.path.lexists(str(root/'modules/cache.so')):
        raise RuntimeError('External module shadows the built-in stock cache')
    if any((root / d).is_symlink() for d in ('bin', 'modules')):
        raise RuntimeError('Linked stock installation directory')
    service_state = stock_service_identity(root, service)
    result = []
    for rel in ('modules/mod_security.so', 'cyberpanel_ols.license', 'cyberpanel_ols.lastcheck'):
        p = root / rel
        if p.is_symlink() or (os.path.lexists(str(p)) and not p.is_file()):
            raise RuntimeError('Unsupported stock dependency: ' + rel)
        if p.is_file():
            if rel != 'modules/mod_security.so' and p.stat().st_size > 65536:
                raise RuntimeError('Unrecognized license state')
            info = p.stat()
            value = digest(p)
            if rel == 'modules/mod_security.so':
                from olsStockClassifier import STOCK_CORE, require_platform
                selected, stock_core, _, stock_waf = require_platform(None)
                from installBundle import RELEASES
                vendor_waf = vendor_waf_digests(selected, stock_waf)
                approved_waf = vendor_waf | {RELEASES[selected]['modsec'],
                                {'ubuntu': '640966b5c93922809327db4df59c5955d32211a7faad0311863236d98a617536', 'ubuntu26': '057dd4a47ec7baa189f71c26a3ca4b180eea168c17d3a83c69dd47e4bc3df9ae', 'rhel9': '0e9ea48580bdb103131506ce2258ae910cfc2e49c6ca742ea8d1e0927909c9e9'}.get(selected)}
                # This published Ubuntu 24.04 WAF is accepted as a rollback
                # input only. The existing custom-WAF rule requires OLS stopped.
                if stock_core == STOCK_CORE:
                    approved_waf.add('d196438c0a113ca339706a1e7e37c51026489e4893d06436d6f76252b6e0d6ec')
                if value not in approved_waf:
                    raise RuntimeError('Unrecognized installed WAF module')
                if value not in vendor_waf and service_state:
                    raise RuntimeError('Custom WAF on running stock core is not restartable. '
                                       'Use an operator-managed maintenance window and rerun only when stopped.')
            result.append((rel, value, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_ctime_ns))
        else:
            result.append((rel, None))
    if service_state:
        from olsStockClassifier import require_platform
        stock_loaded_modules(root, service_state[0], False, require_platform(None)[0])
    for rel in ('bin/openlitespeed', 'modules/cyberpanel_ols.so', 'bin/lswsctrl.open', 'bin/lsws_env'):
        info = (root / rel).stat()
        result.append((rel, info.st_dev, info.st_ino, info.st_ctime_ns))
    return (config_fingerprint(root, inspect=stock_config_policy), tuple(result), service_state)


def prepare_stock(root, staging, selected, service):
    if str(root) != '/usr/local/lsws':
        raise RuntimeError('Stock recovery requires the native installation path')
    stock_layout(root)
    before = stock_state(root, service)
    from olsStockClassifier import require_stock
    baseline = probe(root, staging, selected, False, stock=True if before[2] else 'stopped-baseline')
    prior_warnings = require_stock(root, selected, baseline['returncode'], baseline['output'])
    candidate = probe(root, staging, selected, True, stock=True)
    require_clean_candidate(root, candidate['returncode'], candidate['output'])
    from olsParserRecovery import LICENSE_WARNING
    candidate_warnings = split_diagnostics(root, candidate['output'])[1]
    if [w for w in candidate_warnings if w != LICENSE_WARNING] != prior_warnings:
        raise RuntimeError('Example ownership diagnostics changed during stock recovery')
    probe(root, staging, selected, True, stock='smoke')
    if before != stock_state(root, service):
        raise RuntimeError('Stock recovery inputs changed during isolated validation')
    return before, candidate['assets']


if __name__ == '__main__':
    if len(sys.argv) != 7 or sys.argv[1] != '--namespace-probe':
        raise SystemExit('This helper must be invoked by the paired recovery installer')
    namespace_probe(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                    sys.argv[6] in ('candidate', 'stock-candidate', 'stock-waf-smoke'),
                    {'stock-waf-smoke':'smoke', 'stock-stopped-baseline':'stopped-baseline',
                     'stock-baseline':True, 'stock-candidate':True}.get(sys.argv[6], False))
