"""Checked package disk/inode quotas; never enable or rebuild a filesystem quota."""
import json
import os
import pwd
import re
import shlex
import stat
import subprocess
import sys


class QuotaError(ValueError):
    pass


def limit(value):
    # Reject lossy conversions such as 1.5 -> 1 and True -> 1.
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)):
        raise QuotaError('Disk and inode limits must be nonnegative integers.')
    result = int(value)
    if result > 2147483647:
        raise QuotaError('Disk or inode limit exceeds the supported package range.')
    return result


def _transport(action, payload):
    from plogical.processUtilities import ProcessUtilities
    command = ' '.join(shlex.quote(arg) for arg in (
        '/usr/local/CyberCP/bin/python',
        '/usr/local/CyberCP/plogical/filesystemQuota.py', action,
        json.dumps(payload, separators=(',', ':'))))
    # An explicit identity avoids sendCommand's legacy substring-based sudo
    # detection when a legitimate domain contains "sudo" or "export".
    response = ProcessUtilities.outputExecutioner(command, user='root', shell=False, retRequired=True)
    try:
        status, output = response
        records = [line[len('QUOTA_RESULT='):] for line in output.splitlines()
                   if line.startswith('QUOTA_RESULT=')]
        if len(records) != 1:
            raise ValueError('missing or ambiguous result')
        result = json.loads(records[0])
        if status != 1 or result.get('ok') is not True:
            raise QuotaError(result.get('error') or 'Quota helper failed.')
        return result['plan'] if action == 'prepare' else result
    except QuotaError:
        raise
    except Exception as error:
        raise QuotaError('Quota outcome could not be verified; retry the save after checking the quota service.') from error


def prepare_package_quota(package, websites=None):
    """Preflight prospective settings, before the caller saves its model."""
    return _transport('prepare', {
        'package_id': package.pk,
        'disk_space': limit(package.diskSpace),
        'inode_limit': limit(package.inodeLimit),
        'site_ids': None if websites is None else [site.pk for site in websites],
    })


def apply_quota_plan(plan):
    return _transport('apply', plan)


def _tool(name):
    for directory in ('/usr/sbin', '/usr/bin', '/sbin', '/bin'):
        path = os.path.realpath(os.path.join(directory, name))
        try:
            info = os.stat(path)
        except FileNotFoundError:
            continue
        if (stat.S_ISREG(info.st_mode) and info.st_uid == 0
                and not info.st_mode & 0o022 and os.access(path, os.X_OK)):
            return path
    raise QuotaError('Required quota tool is missing or untrusted: ' + name)


def _run(arguments):
    environment = dict(os.environ, LC_ALL='C', LANG='C', LANGUAGE='C')
    return subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=30, env=environment, check=False)


def _block_device(path):
    if not os.path.isabs(path):
        raise QuotaError('Quota target requires an absolute block device.')
    info = os.stat(path)
    if not stat.S_ISBLK(info.st_mode):
        raise QuotaError('Quota target source is not a block device.')
    return info.st_rdev


def _scan_context(mount):
    result = _run([_tool('findmnt'), '--json', '--list',
                   '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'])
    if result.returncode != 0 or result.stderr:
        raise QuotaError('Cannot verify quota mount-scan context.')
    try:
        rows = json.loads(result.stdout)['filesystems']
        relevant, eligible = [], []
        selected = [row for row in rows if row['target'] == mount['target']]
        if len(selected) != 1:
            raise ValueError('missing or ambiguous target')
        expected = {'target': mount['target'], 'source': mount['source'],
                    'fstype': mount['fstype'], 'options': mount['options']}
        for row in rows:
            if row['target'] != mount['target'] and row['source'] != 'tmpfs':
                continue
            entry = {key: row[key] for key in ('target', 'source', 'fstype')}
            entry['options'] = sorted(set(row['options'].split(',')))
            target = entry['target']
            if (row.get('children') or not os.path.isabs(target)
                    or os.path.realpath(target) != target
                    or any(ord(c) < 32 or ord(c) == 127 for c in target)):
                raise ValueError('ambiguous mount identity')
            info = os.stat(target)
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError('mount path is not a directory')
            if target == mount['target']:
                if (entry != expected or info.st_dev != mount['device']
                        or _block_device(entry['source']) != mount['device']):
                    raise ValueError('target device changed')
            else:
                if entry['fstype'] != 'tmpfs' or info.st_dev == mount['device']:
                    raise ValueError('ambiguous tmpfs source')
                options = set(entry['options'])
                quota_options = {option for option in options if 'quota' in option}
                # Ordinary /run-like tmpfs records are known excluded entries.
                if quota_options - {'noquota'}:
                    if quota_options != {'usrquota'} or options.intersection({'bind', 'rbind'}):
                        raise ValueError('unsupported quota-bearing tmpfs entry')
                    eligible.append(target)
            entry['device'] = info.st_dev
            relevant.append(entry)
        targets = [entry['target'] for entry in relevant]
        if len(targets) != len(set(targets)):
            raise ValueError('duplicate mount identity')
        if eligible:
            try:
                os.stat('tmpfs')
            except FileNotFoundError:
                pass
            else:
                raise ValueError('relative tmpfs source is not absent')
        return {'mounts': sorted(relevant, key=lambda row: row['target']),
                'warning_mounts': sorted(eligible)}
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise QuotaError('Quota mount-scan context is unsupported or changed.') from error


def _scan_command(name, arguments, mount):
    before = _scan_context(mount)
    result = _run(arguments)
    if _scan_context(mount) != before:
        raise QuotaError('Quota mount-scan context changed during the command; verify quotas and retry.')
    diagnostics = []
    if result.stderr:
        line = name + ': Cannot stat() mounted device tmpfs: No such file or directory\n'
        if (not before['warning_mounts']
                or result.stderr != line * len(before['warning_mounts'])):
            raise QuotaError(name + ' returned an unverified diagnostic; verify quotas and retry.')
        diagnostics.append({'tool': name, 'stderr': result.stderr,
                            'mounts': before['warning_mounts']})
    return result, diagnostics


def quota_enforced(result, mount, filesystem, device=None):
    # quotaon -p returns raw 1 for one active quota. Errors may also return 1.
    # Verbose output is required: XFS plain "on" also means accounting-only.
    if (filesystem not in ('ext4', 'xfs') or result.returncode != 1
            or any(ord(c) < 32 or ord(c) == 127 for c in result.stdout.rstrip('\n'))):
        return False
    states = r'on \(enforced\)' if filesystem == 'xfs' else r'on(?: \(enforced\))?'
    pattern = r'user quota on ' + re.escape(mount) + r' \(([^()\r\n]+)\) is ' + states + r'\n?'
    match = re.fullmatch(pattern, result.stdout)
    if not match:
        return False
    if device is None:
        return not result.stderr
    try:
        return _block_device(match.group(1)) == device
    except (OSError, QuotaError):
        return False


def _mount(path):
    result = _run([_tool('findmnt'), '--json', '--target', path,
                   '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'])
    if result.returncode != 0 or result.stderr:
        raise QuotaError('Cannot determine the website filesystem.')
    try:
        mounts = json.loads(result.stdout)['filesystems']
        if len(mounts) != 1 or mounts[0].get('children'):
            raise ValueError('ambiguous mount')
        mount = mounts[0]
        target, filesystem = mount['target'], mount['fstype']
        options = set(mount['options'].split(','))
        if (not os.path.isabs(target) or os.path.realpath(target) != target
                or os.path.commonpath([path, target]) != target
                or filesystem not in ('ext4', 'xfs') or 'rw' not in options
                or options.intersection({'ro', 'noquota', 'uqnoenforce', 'usrqnoenforce'})):
            raise ValueError('unsupported or unenforced mount')
        mount_device = os.stat(target).st_dev
        if (os.stat(path).st_dev != mount_device
                or _block_device(mount['source']) != mount_device):
            raise ValueError('mount device mismatch')
    except (KeyError, TypeError, ValueError) as error:
        raise QuotaError('Website requires a writable ext4/XFS filesystem with enforced user quotas.') from error
    record = {'target': target, 'fstype': filesystem, 'source': mount['source'],
              'options': sorted(options), 'device': mount_device}
    state, diagnostics = _scan_command('quotaon', [
        _tool('quotaon'), '--print-state', '--verbose', '--user', '--', target], record)
    if not quota_enforced(state, target, filesystem, mount_device):
        raise QuotaError('User quota enforcement could not be verified on ' + target +
                         '; configure and verify it manually before retrying.')
    record['diagnostics'] = diagnostics
    return record


def _inspect(site, all_sites):
    username, domain = site.externalApp, site.domain
    if (not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.-]*\$?', username)
            or not domain or domain in ('.', '..') or '/' in domain
            or any(ord(c) < 33 for c in domain)):
        raise QuotaError('Website has an unsupported Unix identity or home path.')
    account = pwd.getpwnam(username)
    if (account.pw_uid == 0 or pwd.getpwuid(account.pw_uid).pw_name != username
            or [entry.pw_name for entry in pwd.getpwall() if entry.pw_uid == account.pw_uid] != [username]):
        raise QuotaError('Website requires a dedicated non-root Unix UID: ' + domain)
    owners = []
    for other in all_sites:
        try:
            other_uid = pwd.getpwnam(other.externalApp).pw_uid
        except KeyError:
            continue
        if other_uid == account.pw_uid:
            owners.append(other.pk)
    if owners != [site.pk]:
        raise QuotaError('Unix UID is shared by top-level websites: ' + domain)
    path = '/home/' + domain
    if os.path.realpath(path) != path:
        raise QuotaError('Website home must not be a symbolic link: ' + domain)
    info = os.stat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != account.pw_uid:
        raise QuotaError('Website home ownership does not match its dedicated UID: ' + domain)
    return {'site_id': site.pk, 'domain': domain, 'username': username,
            'uid': account.pw_uid, 'path': path, 'inode': info.st_ino,
            'mount': _mount(path)}


def _sites():
    from websiteFunctions.models import Websites
    return list(Websites.objects.all().order_by('pk'))


def _package(package_id):
    from packages.models import Package
    return Package.objects.get(pk=package_id)


def prepare(payload):
    package_id = limit(payload['package_id'])
    _package(package_id)
    sites = _sites()
    requested = payload['site_ids']
    if requested is None:
        selected = [site for site in sites if site.package_id == package_id]
    else:
        if (not isinstance(requested, list) or not requested
                or len(requested) != len(set(requested))):
            raise QuotaError('Invalid website selection.')
        selected = [site for site in sites if site.pk in requested]
        if len(selected) != len(requested):
            raise QuotaError('Website selection changed; retry the save.')
    if selected:
        _tool('setquota')
    return {'package_id': package_id, 'disk_space': limit(payload['disk_space']),
            'inode_limit': limit(payload['inode_limit']), 'all_sites': requested is None,
            'sites': [_inspect(site, sites) for site in selected]}


def apply(plan):
    package = _package(plan['package_id'])
    if (not package.enforceDiskLimits or limit(package.diskSpace) != plan['disk_space']
            or limit(package.inodeLimit) != plan['inode_limit']):
        raise QuotaError('Package policy changed; retry the save.')
    sites = _sites()
    expected_ids = [entry['site_id'] for entry in plan['sites']]
    selected = [site for site in sites if site.pk in expected_ids]
    if (len(selected) != len(expected_ids)
            or any(site.package_id != package.pk for site in selected)
            or (plan['all_sites'] and [site.pk for site in sites if site.package_id == package.pk] != expected_ids)):
        raise QuotaError('Package membership changed; retry the save.')
    # Revalidate the complete set before the first mutation, then each target
    # immediately before its command. Database and filesystem updates are not atomic.
    for site, expected in zip(selected, plan['sites']):
        if _inspect(site, sites) != expected:
            raise QuotaError('Website identity or filesystem changed: ' + site.domain)
    command = _tool('setquota') if selected else None
    applied, failed, diagnostics = [], [], []
    blocks, inodes = str(limit(plan['disk_space']) * 1024), str(limit(plan['inode_limit']))
    for site, expected in zip(selected, plan['sites']):
        try:
            current_sites = _sites()
            current = next(item for item in current_sites if item.pk == site.pk)
            current_package = _package(package.pk)
            if (current.package_id != package.pk or not current_package.enforceDiskLimits
                    or limit(current_package.diskSpace) != plan['disk_space']
                    or limit(current_package.inodeLimit) != plan['inode_limit']
                    or (plan['all_sites'] and [item.pk for item in current_sites if item.package_id == package.pk] != expected_ids)
                    or _inspect(current, current_sites) != expected):
                raise QuotaError('Identity, filesystem or package policy changed; retry.')
            result, warnings = _scan_command('setquota', [
                command, '-u', str(expected['uid']), blocks, blocks,
                inodes, inodes, expected['mount']['target']], expected['mount'])
            diagnostics.extend(warnings)
            if result.returncode != 0 or result.stdout:
                raise QuotaError('setquota failed or returned a warning; verify quotas and retry.')
            applied.append(site.domain)
        except Exception as error:
            failed.append(site.domain + ': ' + str(error))
    if failed:
        raise QuotaError('Quota command succeeded for %d of %d websites; failed or unverified: %s' %
                         (len(applied), len(selected), '; '.join(failed)))
    return {'ok': True, 'applied': applied, 'diagnostics': diagnostics}


def main():
    try:
        if os.geteuid() != 0:
            raise QuotaError('Quota helper requires the existing privileged command transport.')
        if len(sys.argv) != 3 or sys.argv[1] not in ('prepare', 'apply'):
            raise QuotaError('Expected prepare or apply and one JSON argument.')
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
        import django
        django.setup()
        payload = json.loads(sys.argv[2])
        result = ({'ok': True, 'plan': prepare(payload)} if sys.argv[1] == 'prepare'
                  else apply(payload))
        status = 0
    except Exception as error:
        result, status = {'ok': False, 'error': str(error)}, 1
    print('QUOTA_RESULT=' + json.dumps(result, separators=(',', ':')))
    return status


if __name__ == '__main__':
    sys.exit(main())
