"""Opt-in combined website/mail project quotas on already configured filesystems.

Enrollment requires a maintenance window. No ownership, mount, filesystem
feature, or Dovecot identity is changed. Project quotas constrain ordinary
writes; Linux inode owners may alter project attributes, so this is not an
untrusted-tenant isolation boundary. Existing website UID quotas remain useful.
"""
import argparse
import contextlib
import ctypes
import errno
import fcntl
import hashlib
import json
import os
import platform
import pwd
import re
import secrets
import shlex
import stat
import struct
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical import filesystemQuota, storageAccounting


REGISTRY_DIRECTORY = '/var/lib/cyberpanel'
REGISTRY_NAME = 'storage-quotas.json'
LOCK_NAME = 'storage-quotas.lock'
MAX_INODES = 1000000
FSGETXATTR = 0x801c581f
FSSETXATTR = 0x401c5820
PROJINHERIT = 0x200
PROJECT_TYPE = 2


class StorageQuotaError(ValueError):
    pass


class _Dqblk(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        'bhard', 'bsoft', 'space', 'ihard', 'isoft', 'inodes', 'btime', 'itime')]
    _fields_ += [('valid', ctypes.c_uint32)]


class _NextDqblk(ctypes.Structure):
    _fields_ = _Dqblk._fields_ + [('id', ctypes.c_uint32)]


def _quota_call(command, source, project_id, value):
    if platform.system() != 'Linux' or ctypes.sizeof(_Dqblk) != 72:
        raise StorageQuotaError('Project quotas require the supported Linux quota ABI.')
    library = ctypes.CDLL(None, use_errno=True)
    function = library.quotactl
    function.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    function.restype = ctypes.c_int
    result = function(ctypes.c_int((command << 8) | PROJECT_TYPE),
                      os.fsencode(source), project_id, ctypes.byref(value))
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def _get_quota(mount, project_id):
    value = _Dqblk()
    _quota_call(0x800007, mount['source'], project_id, value)
    return {name: int(getattr(value, name)) for name, unused in _Dqblk._fields_}


def _next_project(mount, project_id):
    value = _NextDqblk()
    try:
        _quota_call(0x800009, mount['source'], project_id, value)
    except OSError as error:
        # The quota-tree backend used by ext4 returns ENOENT at exhaustion;
        # other quota implementations return ESRCH for the same condition.
        if error.errno in (errno.ENOENT, errno.ESRCH):
            return None
        raise StorageQuotaError('Cannot enumerate existing project quota IDs.') from error
    if value.id < project_id:
        raise StorageQuotaError('Project quota enumeration returned an invalid ID.')
    return int(value.id)


def _set_limits(mount, project_id, disk, inodes):
    blocks = filesystemQuota.limit(disk) * 1024
    count = filesystemQuota.limit(inodes)
    value = _Dqblk(bhard=blocks, bsoft=blocks, ihard=count, isoft=count, valid=5)
    _quota_call(0x800008, mount['source'], project_id, value)
    result = _get_quota(mount, project_id)
    if any(result[key] != expected for key, expected in (
            ('bhard', blocks), ('bsoft', blocks), ('ihard', count), ('isoft', count))):
        raise StorageQuotaError('Project quota limits changed but readback did not match.')
    return result


def project_enforced(result, mount):
    """quotaon returns one for one enabled quota; XFS accounting alone is insufficient."""
    if result.returncode != 1:
        return False
    state = r'on \(enforced\)' if mount['fstype'] == 'xfs' else r'on(?: \(enforced\))?'
    pattern = (r'project quota on ' + re.escape(mount['target'])
               + r' \(([^()\r\n]+)\) is ' + state + r'\n?')
    match = re.fullmatch(pattern, result.stdout)
    if not match:
        return False
    try:
        return filesystemQuota._block_device(match.group(1)) == mount['device']
    except (OSError, filesystemQuota.QuotaError):
        return False


def _mount(path):
    result = filesystemQuota._run([
        filesystemQuota._tool('findmnt'), '--json', '--target', path,
        '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID'])
    try:
        if result.returncode or result.stderr:
            raise ValueError('findmnt failed')
        rows = json.loads(result.stdout)['filesystems']
        if len(rows) != 1 or rows[0].get('children'):
            raise ValueError('ambiguous mount')
        row = rows[0]
        target, source, kind, uuid = (row[key] for key in ('target', 'source', 'fstype', 'uuid'))
        options = sorted(set(row['options'].split(',')))
        if (kind not in ('ext4', 'xfs') or not uuid or not re.fullmatch(r'[A-Za-z0-9-]+', uuid)
                or not os.path.isabs(target) or os.path.realpath(target) != target
                or os.path.commonpath((path, target)) != target or 'rw' not in options
                or set(options).intersection({'ro', 'noquota', 'pqnoenforce', 'prjqnoenforce', 'bind', 'rbind'})):
            raise ValueError('unsupported filesystem')
        device = os.stat(path).st_dev
        if os.stat(target).st_dev != device or filesystemQuota._block_device(source) != device:
            raise ValueError('device mismatch')
        mount = {'target': target, 'source': source, 'fstype': kind, 'options': options,
                 'device': device, 'uuid': uuid}
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise StorageQuotaError('Combined quotas require one writable ext4/XFS filesystem with a stable UUID.') from error
    state, unused = filesystemQuota._scan_command('quotaon', [
        filesystemQuota._tool('quotaon'), '--print-state', '--verbose', '--project', '--', target], mount)
    if not project_enforced(state, mount):
        raise StorageQuotaError('Project quota enforcement is not enabled and verified; configure it during filesystem maintenance.')
    return mount


def _mount_tree(roots, mount):
    """Reject nested mounts, including same-device bind mounts invisible to st_dev."""
    result = filesystemQuota._run([
        filesystemQuota._tool('findmnt'), '--json', '--list',
        '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'])
    try:
        if result.returncode or result.stderr:
            raise ValueError('mount scan failed')
        rows = json.loads(result.stdout)['filesystems']
        for row in rows:
            target = row['target']
            if not os.path.isabs(target) or row.get('children'):
                raise ValueError('ambiguous mount inventory')
            if target == mount['target']:
                continue
            if any(os.path.commonpath((root['path'], target)) == root['path'] for root in roots):
                raise ValueError('nested mount')
        for root in roots:
            if _mount(root['path']) != mount:
                raise ValueError('root mount changed')
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise StorageQuotaError('Storage scope contains a nested or changed mount.') from error


def _secure_directory(create=False):
    path = os.path.abspath(REGISTRY_DIRECTORY)
    current = '/'
    for component in path.strip('/').split('/'):
        current = os.path.join(current, component)
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            if not create or current != path:
                raise
            os.mkdir(current, 0o700)
            info = os.lstat(current)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise StorageQuotaError('Storage quota registry directory is not secure.')
    return path


def _secure_open(path, flags, mode=0o600):
    descriptor = os.open(path, flags | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077 or info.st_nlink != 1:
        os.close(descriptor)
        raise StorageQuotaError('Storage quota registry file is not secure.')
    return descriptor


@contextlib.contextmanager
def _registry(create=False):
    if os.geteuid() != 0:
        raise StorageQuotaError('Storage quota registry requires the privileged helper.')
    try:
        directory = _secure_directory(create)
    except FileNotFoundError:
        if create:
            raise
        yield None
        return
    registry_path = os.path.join(directory, REGISTRY_NAME)
    if not create and not os.path.lexists(registry_path):
        yield None
        return
    descriptor = _secure_open(os.path.join(directory, LOCK_NAME), os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            with os.fdopen(_secure_open(registry_path, os.O_RDONLY), 'r') as stream:
                registry = json.load(stream)
        except FileNotFoundError:
            registry = {'version': 1, 'next_id': 1000000000, 'sites': {}}
        if (not isinstance(registry, dict) or registry.get('version') != 1
                or not isinstance(registry.get('sites'), dict)
                or type(registry.get('next_id')) is not int
                or not 1 <= registry['next_id'] <= 2147483647):
            raise StorageQuotaError('Storage quota registry is invalid; no changes were made.')
        yield registry
    finally:
        os.close(descriptor)


def _save_registry(registry):
    directory = _secure_directory()
    path = os.path.join(directory, REGISTRY_NAME)
    temporary = path + '.tmp-%d' % os.getpid()
    created = False
    try:
        descriptor = _secure_open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        created = True
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(registry, stream, sort_keys=True, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if created and os.path.lexists(temporary):
            os.unlink(temporary)


def _site(site_id):
    from websiteFunctions.models import Websites
    return Websites.objects.select_related('package').get(pk=site_id)


def _identity(website):
    if website.pk is None:
        raise StorageQuotaError('Website has no saved identity.')
    domain = storageAccounting._component(website.domain)
    username = website.externalApp
    account = pwd.getpwnam(username)
    if (account.pw_uid == 0 or pwd.getpwuid(account.pw_uid).pw_name != username
            or [entry.pw_name for entry in pwd.getpwall() if entry.pw_uid == account.pw_uid] != [username]):
        raise StorageQuotaError('Website must have a dedicated non-root Unix identity.')
    return {'site_id': website.pk, 'domain': domain, 'username': username, 'uid': account.pw_uid}


def _roots(website):
    identity = _identity(website)
    home = os.path.join(storageAccounting.HOME_ROOT, identity['domain'])
    paths = [{'path': home, 'kind': 'web'}]
    for child in website.childdomains_set.all():
        if (child.master_id != website.pk or not isinstance(child.path, str)
                or not os.path.isabs(child.path) or os.path.commonpath((home, child.path)) != home):
            raise StorageQuotaError('Combined enrollment requires child website paths inside the website home.')
    domains = storageAccounting.owned_mail_domains(website)
    for domain in domains:
        paths.append({'path': storageAccounting.mail_domain_path(domain), 'kind': 'mail', 'domain': domain.domain})
    for root in paths:
        path = root['path']
        if not os.path.isabs(path) or os.path.realpath(path) != path:
            raise StorageQuotaError('Storage roots and their ancestors must not be symbolic links.')
        info = os.lstat(path)
        if not stat.S_ISDIR(info.st_mode):
            raise StorageQuotaError('Storage root is not a directory: ' + path)
        if root['kind'] == 'web' and info.st_uid != identity['uid']:
            raise StorageQuotaError('Website home ownership changed.')
        root.update(device=info.st_dev, inode=info.st_ino)
    return identity, paths


def _attrs(path, expected=None):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(descriptor)
        if expected is not None and (info.st_dev, info.st_ino) != expected:
            raise StorageQuotaError('Storage inode changed during inspection.')
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise StorageQuotaError('Enrollment supports regular files and directories only.')
        data = bytearray(28)
        fcntl.ioctl(descriptor, FSGETXATTR, data, True)
        return tuple(struct.unpack('=5I8x', data))
    finally:
        os.close(descriptor)


def _inode_record(path, info):
    return {'path': path, 'device': info.st_dev, 'inode': info.st_ino,
            'mode': info.st_mode, 'uid': info.st_uid, 'gid': info.st_gid,
            'links': info.st_nlink, 'size': info.st_size, 'mtime': info.st_mtime_ns,
            'attrs': _attrs(path, (info.st_dev, info.st_ino))}


def _inventory(roots, project_id=None, allow_unassigned=False):
    inventory, links = {}, {}
    device = roots[0]['device']
    for root in roots:
        if root['device'] != device:
            raise StorageQuotaError('Web and mail roots must share a single filesystem.')
        base = root['path']
        initial = os.lstat(base)
        if (initial.st_dev, initial.st_ino) != (root['device'], root['inode']):
            raise StorageQuotaError('Storage root was replaced; maintenance enrollment is required.')
        pending = [base]
        while pending:
            path = pending.pop()
            if path in inventory:
                continue
            info = os.lstat(path)
            if info.st_dev != device or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                raise StorageQuotaError('Enrollment refuses symbolic links, special files and mount boundaries: ' + path)
            record = _inode_record(path, info)
            current_id = record['attrs'][3]
            if project_id is not None:
                accepted = {project_id, 0} if allow_unassigned else {project_id}
                if current_id not in accepted:
                    raise StorageQuotaError('Storage inode has a foreign project ID: ' + path)
                if not allow_unassigned and stat.S_ISDIR(info.st_mode) and not record['attrs'][0] & PROJINHERIT:
                    raise StorageQuotaError('Storage directory lost project inheritance: ' + path)
            inventory[path] = record
            if len(inventory) > MAX_INODES:
                raise StorageQuotaError('Enrollment inventory exceeds the supported bounded scan.')
            if stat.S_ISDIR(info.st_mode):
                with os.scandir(path) as entries:
                    pending.extend(sorted((entry.path for entry in entries), reverse=True))
            else:
                key = (info.st_dev, info.st_ino)
                links[key] = links.get(key, 0) + 1
    for record in inventory.values():
        if stat.S_ISREG(record['mode']) and links[(record['device'], record['inode'])] != record['links']:
            raise StorageQuotaError('Storage contains a hard link outside its enrolled roots.')
    return inventory


def _tag(record, project_id):
    path = record['path']
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(descriptor)
        actual = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                  info.st_nlink, info.st_size, info.st_mtime_ns)
        expected = tuple(record[key] for key in ('device', 'inode', 'mode', 'uid', 'gid', 'links', 'size', 'mtime'))
        if actual != expected:
            raise StorageQuotaError('Storage changed during maintenance enrollment.')
        data = bytearray(28)
        fcntl.ioctl(descriptor, FSGETXATTR, data, True)
        current = tuple(struct.unpack('=5I8x', data))
        if current != record['attrs']:
            raise StorageQuotaError('Project attributes changed during enrollment.')
        changed = list(current)
        changed[3] = project_id
        if stat.S_ISDIR(info.st_mode):
            changed[0] |= PROJINHERIT
        fcntl.ioctl(descriptor, FSSETXATTR, struct.pack('=5I8x', *changed))
        fcntl.ioctl(descriptor, FSGETXATTR, data, True)
        if tuple(struct.unpack('=5I8x', data)) != tuple(changed):
            raise StorageQuotaError('Project assignment could not be verified.')
    finally:
        os.close(descriptor)


def _binding(website, record):
    # A caller may hold a select_related/prefetched object from before a save.
    # Reload the owner before accepting current domain membership and roots.
    website = _site(website.pk)
    identity, roots = _roots(website)
    if identity != record['identity'] or roots != record['roots']:
        raise StorageQuotaError('Storage ownership or roots changed; maintenance enrollment is required.')
    mount = _mount(roots[0]['path'])
    if mount != record['mount']:
        raise StorageQuotaError('Storage filesystem changed; maintenance enrollment is required.')
    _mount_tree(roots, mount)
    _inventory(roots, record['project_id'])
    return mount


def _policy(website):
    enabled = bool(website.package.enforceDiskLimits)
    return {'disk_space': filesystemQuota.limit(website.package.diskSpace),
            'inode_limit': filesystemQuota.limit(website.package.inodeLimit), 'enforce': enabled}


def _verify_limits(website, record, mount):
    website = _site(website.pk)
    policy = _policy(website)
    disk = policy['disk_space'] if policy['enforce'] else 0
    inodes = policy['inode_limit'] if policy['enforce'] else 0
    if policy != record['policy']:
        raise StorageQuotaError('Package policy differs from the last verified combined quota.')
    value = _get_quota(mount, record['project_id'])
    if (value['bhard'] != disk * 1024 or value['bsoft'] != disk * 1024
            or value['ihard'] != inodes or value['isoft'] != inodes):
        raise StorageQuotaError('Combined quota limits differ from the package policy.')
    return value


def _record(registry, website):
    return None if registry is None else registry['sites'].get(str(website.pk))


def _status(website):
    result = {'state': 'unconfigured', 'enforced': False, 'enrolled': False,
              'scope': 'website_and_owned_mail', 'security_boundary': False,
              'reason': 'Combined mail and website enforcement has not been enrolled.'}
    try:
        with _registry() as registry:
            record = _record(registry, website)
            if record is None:
                return result
            website = _site(website.pk)
            result.update(project_id=record['project_id'], enrolled=True)
            if record['state'] == 'disabled':
                result.update(reason='Combined limits were disabled during maintenance; enrollment identity is retained.')
                return result
            if record['state'] != 'active':
                result.update(state='pending', reason='Maintenance enrollment or a verified policy update is incomplete.')
                return result
            mount = _binding(website, record)
            policy = _policy(website)
            expected_disk = policy['disk_space'] if policy['enforce'] else 0
            expected_inodes = policy['inode_limit'] if policy['enforce'] else 0
            quota = _verify_limits(website, record, mount)
            enabled = policy['enforce'] and bool(expected_disk or expected_inodes)
            result.update(state='active' if enabled else 'unconfigured', enforced=enabled,
                          reason='Kernel project quota verified for ordinary web/mail writes.' if enabled
                          else 'Combined scope is enrolled; package limits are disabled or unlimited.',
                          usage_bytes=quota['space'], usage_inodes=quota['inodes'], policy=policy)
    except Exception as error:
        result.update(state='unsupported', enforced=False, reason=str(error))
    return result


def _prepare_policy(website, disk, inodes, enforce=None):
    with _registry() as registry:
        record = _record(registry, website)
        if record is None:
            return None
        if record['state'] != 'active':
            raise StorageQuotaError('Combined quota enrollment is pending; finish maintenance before changing its policy.')
        _binding(website, record)
        return {'site_id': website.pk, 'revision': record['revision'],
                'identity': record['identity'], 'roots': record['roots'], 'mount': record['mount'],
                'project_id': record['project_id'],
                'policy': {'disk_space': filesystemQuota.limit(disk),
                           'inode_limit': filesystemQuota.limit(inodes),
                           'enforce': bool(website.package.enforceDiskLimits) if enforce is None else bool(enforce)}}


def _apply_policy(plan):
    website = _site(plan['site_id'])
    with _registry() as registry:
        record = _record(registry, website)
        if record is None or record['state'] != 'active':
            raise StorageQuotaError('Combined quota enrollment disappeared or is pending.')
        for key in ('revision', 'identity', 'roots', 'mount', 'project_id'):
            if plan[key] != record[key]:
                raise StorageQuotaError('Combined quota plan is stale; retry the package save.')
        if _policy(website) != plan['policy']:
            raise StorageQuotaError('Package policy changed; retry the save.')
        mount = _binding(website, record)
        record['state'] = 'pending'
        record['revision'] += 1
        _save_registry(registry)
        policy = plan['policy']
        result = _set_limits(mount, record['project_id'], policy['disk_space'] if policy['enforce'] else 0,
                             policy['inode_limit'] if policy['enforce'] else 0)
        if _policy(_site(website.pk)) != policy:
            raise StorageQuotaError('Package changed during combined quota application; maintenance verification is required.')
        _binding(website, record)
        record.update(state='active', policy=policy)
        _save_registry(registry)
        return {'ok': True, 'project_id': record['project_id'], 'quota': result}


def _reserved_ids():
    values = set()
    for path, field in (('/etc/projects', 0), ('/etc/projid', 1)):
        try:
            with open(path, 'r') as stream:
                for line in stream:
                    content = line.strip()
                    if content and not content.startswith('#'):
                        parts = content.split(':')
                        if len(parts) != 2 or not parts[field].isdigit():
                            raise StorageQuotaError('Administrator project mappings cannot be safely parsed.')
                        values.add(int(parts[field]))
        except FileNotFoundError:
            pass
    return values


def _allocate(registry, mount):
    reserved = _reserved_ids() | {record['project_id'] for record in registry['sites'].values()}
    candidate = registry['next_id']
    for unused in range(10000):
        if candidate >= 2147483647:
            break
        if candidate not in reserved and _next_project(mount, candidate) != candidate:
            registry['next_id'] = candidate + 1
            return candidate
        candidate += 1
    raise StorageQuotaError('No verified unused project quota ID is available.')


def _snapshot(identity, roots, mount, policy, inventory, project_id):
    encoded = json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return {'identity': identity, 'roots': roots, 'mount': mount, 'policy': policy,
            'project_id': project_id, 'inode_count': len(inventory),
            'inventory_sha256': hashlib.sha256(encoded).hexdigest()}


def _write_enrollment_plan(website):
    website = _site(website.pk)
    identity, roots = _roots(website)
    mount = _mount(roots[0]['path'])
    _mount_tree(roots, mount)
    with _registry(create=True) as registry:
        record = _record(registry, website)
        if record is not None and (record['identity'] != identity or record['roots'] != roots
                                   or record['mount'] != mount):
            raise StorageQuotaError('Existing enrollment identity changed; manual recovery is required.')
        project_id = record['project_id'] if record is not None else None
        inventory = _inventory(roots, project_id if project_id is not None else 0, allow_unassigned=True)
        snapshot = _snapshot(identity, roots, mount, _policy(website), inventory, project_id)
        path = os.path.join(_secure_directory(), 'storage-plan-%s-%s.json' % (website.pk, secrets.token_hex(8)))
        with os.fdopen(_secure_open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL), 'w') as stream:
            json.dump({'version': 1, 'snapshot': snapshot}, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        return {'plan_file': path, 'snapshot': snapshot,
                'next_step': 'Keep affected writers quiesced, review the plan, then enroll using --plan and --quiesced.'}


def _read_enrollment_plan(path):
    directory = _secure_directory()
    if (not os.path.isabs(path) or os.path.dirname(path) != directory
            or not os.path.basename(path).startswith('storage-plan-')):
        raise StorageQuotaError('Use a plan file created in the private storage quota directory.')
    with os.fdopen(_secure_open(path, os.O_RDONLY), 'r') as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('snapshot'), dict):
        raise StorageQuotaError('Enrollment plan is invalid.')
    return value['snapshot']


def _enroll(website, quiesced=False, plan=None):
    if not quiesced:
        raise StorageQuotaError('Enrollment requires --quiesced after affected web and mail writers have been stopped for maintenance.')
    website = _site(website.pk)
    identity, roots = _roots(website)
    mount = _mount(roots[0]['path'])
    _mount_tree(roots, mount)
    with _registry(create=True) as registry:
        record = _record(registry, website)
        if record is None:
            project_id = _allocate(registry, mount)
        else:
            if record['identity'] != identity or record['mount'] != mount:
                raise StorageQuotaError('Existing enrollment identity changed; manual recovery is required.')
            if record['roots'] != roots:
                raise StorageQuotaError('Existing storage roots were replaced or membership changed; manual recovery is required.')
            project_id = record['project_id']
        inventory = _inventory(roots, project_id, allow_unassigned=True)
        policy = _policy(website)
        if plan is not None and plan != _snapshot(identity, roots, mount, policy, inventory,
                                                  record['project_id'] if record is not None else None):
            raise StorageQuotaError('Enrollment plan is stale; keep writers quiesced and prepare a fresh plan.')
        if record is None:
            record = {'identity': identity, 'roots': roots, 'mount': mount,
                      'project_id': project_id, 'revision': 0, 'policy': policy}
            registry['sites'][str(website.pk)] = record
        record['state'] = 'pending'
        record['revision'] += 1
        _save_registry(registry)
        # Parents are tagged before children; writers must remain quiesced.
        tagged = set()
        for path in sorted(inventory, key=lambda item: (item.count(os.sep), item)):
            inode = (inventory[path]['device'], inventory[path]['inode'])
            if inode not in tagged:
                _tag(inventory[path], project_id)
                tagged.add(inode)
        after = _inventory(roots, project_id)
        if set(after) != set(inventory):
            raise StorageQuotaError('Storage membership changed during enrollment; keep writers quiesced and retry.')
        for path, old in inventory.items():
            new = after[path]
            if any(old[key] != new[key] for key in ('device', 'inode', 'mode', 'uid', 'gid', 'links', 'size', 'mtime')):
                raise StorageQuotaError('Storage changed during enrollment; keep writers quiesced and retry.')
        _set_limits(mount, project_id, policy['disk_space'] if policy['enforce'] else 0,
                    policy['inode_limit'] if policy['enforce'] else 0)
        current = _site(website.pk)
        if _identity(current) != identity or _policy(current) != policy:
            raise StorageQuotaError('Website policy changed during enrollment; keep writers quiesced and retry.')
        _binding(current, record)
        record.update(state='active', policy=policy)
        _save_registry(registry)
        return {'ok': True, 'project_id': project_id, 'inode_count': len(inventory),
                'scope': 'website_and_owned_mail', 'security_boundary': False}


def _ensure_mail_domain(domain, website):
    name = storageAccounting._component(domain.domain if hasattr(domain, 'domain') else domain)
    website = _site(website.pk)
    with _registry() as registry:
        target = os.path.join(storageAccounting.MAIL_ROOT, name)
        if registry is not None:
            for key, other in registry['sites'].items():
                if key != str(website.pk) and any(root['path'] == target for root in other['roots']):
                    raise StorageQuotaError('Mail storage is reserved by another website enrollment; maintenance ownership review is required.')
        record = _record(registry, website)
        if record is None:
            return None
        if record['state'] != 'active' or _identity(website) != record['identity']:
            raise StorageQuotaError('Combined quota enrollment is pending or website identity changed.')
        # Resolve authorization after the Domains row exists but before EUsers
        # activation. Directory names alone never authorize another tenant.
        allowed = {website.domain} | {child.domain for child in website.childdomains_set.all()
                                     if child.master_id == website.pk}
        owned = {item.domain for item in storageAccounting.owned_mail_domains(website)}
        if name not in allowed or name not in owned:
            raise StorageQuotaError('Mail domain does not belong to this website.')
        registered = {root['domain'] for root in record['roots'] if root['kind'] == 'mail'}
        if owned != registered | {name}:
            raise StorageQuotaError('Mail domain membership changed; finish maintenance enrollment before activation.')
        existing = next((root for root in record['roots'] if root['path'] == target), None)
        if existing is not None:
            current = _site(website.pk)
            _binding(current, record)
            _verify_limits(current, record, record['mount'])
            return {'ok': True, 'project_id': record['project_id']}
        # Membership may now contain the new Domains record. Verify old roots
        # independently before extending the registry's authorized scope.
        if _mount(record['roots'][0]['path']) != record['mount']:
            raise StorageQuotaError('Storage filesystem changed.')
        _mount_tree(record['roots'], record['mount'])
        _inventory(record['roots'], record['project_id'])
        _verify_limits(website, record, record['mount'])
        mail_root = storageAccounting.MAIL_ROOT
        if os.path.realpath(mail_root) != mail_root or not stat.S_ISDIR(os.lstat(mail_root).st_mode):
            raise StorageQuotaError('Mail root is missing or is not a real directory.')
        if _mount(mail_root) != record['mount']:
            raise StorageQuotaError('New mail domain must be on the enrolled filesystem.')
        created = False
        vmail = pwd.getpwnam('vmail')
        try:
            info = os.lstat(target)
            if not stat.S_ISDIR(info.st_mode) or os.path.realpath(target) != target:
                raise StorageQuotaError('New mail domain root is not a real directory.')
            if (info.st_uid, info.st_gid) != (vmail.pw_uid, vmail.pw_gid):
                raise StorageQuotaError('Existing mail root ownership needs maintenance review.')
            with os.scandir(target) as entries:
                if next(entries, None) is not None:
                    raise StorageQuotaError('Existing mail data requires maintenance enrollment before activation.')
        except FileNotFoundError:
            os.mkdir(target, 0o700)
            created = True
            info = os.lstat(target)
        root = {'path': target, 'kind': 'mail', 'domain': name, 'device': info.st_dev, 'inode': info.st_ino}
        try:
            attributes = _inode_record(target, info)
            if attributes['attrs'][3] not in (0, record['project_id']):
                raise StorageQuotaError('Mail domain root has a foreign project ID.')
            record['roots'].append(root)
            record['roots'].sort(key=lambda entry: (entry['kind'] != 'web', entry['path']))
            record['state'] = 'pending'
            record['revision'] += 1
            _save_registry(registry)
            _tag(attributes, record['project_id'])
            if created:
                os.chown(target, vmail.pw_uid, vmail.pw_gid, follow_symlinks=False)
            # Only a newly created empty root changes identity to the established
            # vmail owner. Existing mail ownership is never altered.
            _inventory(record['roots'], record['project_id'])
            current = _site(website.pk)
            _binding(current, record)
            _verify_limits(current, record, record['mount'])
            record['state'] = 'active'
            _save_registry(registry)
            return {'ok': True, 'project_id': record['project_id'], 'created': created}
        except Exception:
            if created and record['state'] != 'pending':
                try:
                    os.rmdir(target)
                except OSError:
                    pass
            raise


def _assert_restore_allowed(website):
    with _registry() as registry:
        if _record(registry, website) is not None:
            raise StorageQuotaError('This website has combined storage enrollment. The legacy restore replaces storage roots; restore to an unenrolled destination and enroll during maintenance.')
    return None


def _has_enrollment(website):
    with _registry() as registry:
        return _record(registry, website) is not None


def _disable(website, quiesced=False):
    if not quiesced:
        raise StorageQuotaError('Disabling combined quotas requires --quiesced during maintenance.')
    with _registry() as registry:
        record = _record(registry, website)
        if record is None:
            return {'ok': True, 'changed': False}
        mount = _binding(website, record)
        record['state'] = 'pending'
        record['revision'] += 1
        _save_registry(registry)
        _set_limits(mount, record['project_id'], 0, 0)
        # A tombstone retains ID ownership and prevents unsafe reuse. Package
        # state is untouched, so status cannot describe this as active coverage.
        record['state'] = 'disabled'
        _save_registry(registry)
        return {'ok': True, 'changed': True, 'project_id': record['project_id']}


def _transport(action, payload):
    from plogical.processUtilities import ProcessUtilities
    command = ' '.join(shlex.quote(value) for value in (
        '/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/storageQuota.py',
        'request', action, json.dumps(payload, separators=(',', ':'))))
    response = ProcessUtilities.outputExecutioner(command, user='root', shell=False, retRequired=True)
    try:
        success, output = response
        lines = [line[len('STORAGE_QUOTA_RESULT='):] for line in output.splitlines()
                 if line.startswith('STORAGE_QUOTA_RESULT=')]
        if len(lines) != 1:
            raise ValueError('ambiguous result')
        result = json.loads(lines[0])
        if success != 1 or result.get('ok') is not True:
            raise StorageQuotaError(result.get('error') or 'Storage quota helper failed.')
        return result.get('result')
    except StorageQuotaError:
        raise
    except Exception as error:
        raise StorageQuotaError('Storage quota outcome could not be verified.') from error


def status(website):
    try:
        return _status(website) if os.geteuid() == 0 else _transport('status', {'site_id': website.pk})
    except Exception as error:
        return {'state': 'unsupported', 'enforced': False, 'enrolled': False, 'reason': str(error),
                'scope': 'website_and_owned_mail', 'security_boundary': False}


def prepare_policy(website, disk, inodes, enforce=None):
    if os.geteuid() == 0:
        return _prepare_policy(website, disk, inodes, enforce)
    return _transport('prepare', {'site_id': website.pk, 'disk': disk, 'inodes': inodes,
                                 'enforce': bool(website.package.enforceDiskLimits) if enforce is None else bool(enforce)})


def apply_policy(plan):
    if plan is None:
        return None
    return _apply_policy(plan) if os.geteuid() == 0 else _transport('apply', plan)


def ensure_mail_domain(domain, website):
    if os.geteuid() == 0:
        return _ensure_mail_domain(domain, website)
    name = domain.domain if hasattr(domain, 'domain') else domain
    return _transport('mail-domain', {'site_id': website.pk, 'domain': name})


def assert_restore_allowed(website):
    if os.geteuid() == 0:
        return _assert_restore_allowed(website)
    return _transport('restore', {'site_id': website.pk})


def has_enrollment(website):
    """Preserve a registered domain's lifecycle even when its quota is pending."""
    return (_has_enrollment(website) if os.geteuid() == 0
            else _transport('enrolled', {'site_id': website.pk}))


def _request(action, payload):
    if action == 'apply':
        return _apply_policy(payload)
    website = _site(payload['site_id'])
    if action == 'status':
        return _status(website)
    if action == 'prepare':
        return _prepare_policy(website, payload['disk'], payload['inodes'], payload.get('enforce'))
    if action == 'mail-domain':
        return _ensure_mail_domain(payload['domain'], website)
    if action == 'restore':
        return _assert_restore_allowed(website)
    if action == 'enrolled':
        return _has_enrollment(website)
    raise StorageQuotaError('Unsupported storage quota action.')


def main(arguments=None):
    try:
        if os.geteuid() != 0:
            raise StorageQuotaError('Run storage quota maintenance as root.')
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
        import django
        django.setup()
        values = list(sys.argv[1:] if arguments is None else arguments)
        if len(values) == 3 and values[0] == 'request':
            result = _request(values[1], json.loads(values[2]))
        else:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument('action', choices=('status', 'plan', 'enroll', 'disable'))
            parser.add_argument('--website', required=True)
            parser.add_argument('--quiesced', action='store_true', help='Confirm affected writers are stopped for maintenance')
            parser.add_argument('--plan', help='Private reviewed enrollment plan produced by the plan command')
            options = parser.parse_args(values)
            from websiteFunctions.models import Websites
            website = Websites.objects.select_related('package').get(domain=options.website)
            if options.action == 'status':
                result = _status(website)
            elif options.action == 'plan':
                result = _write_enrollment_plan(website)
            elif options.action == 'enroll':
                if not options.plan:
                    raise StorageQuotaError('Enrollment requires a reviewed --plan from the plan command.')
                result = _enroll(website, options.quiesced, _read_enrollment_plan(options.plan))
            else:
                result = _disable(website, options.quiesced)
        print('STORAGE_QUOTA_RESULT=' + json.dumps({'ok': True, 'result': result}, separators=(',', ':')))
        return 0
    except Exception as error:
        print('STORAGE_QUOTA_RESULT=' + json.dumps({'ok': False, 'error': str(error)}, separators=(',', ':')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
