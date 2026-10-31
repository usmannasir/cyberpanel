"""Identify the narrowly bounded WebAdmin parser defect; never waive validation."""
import hashlib
import os
import platform
import re
from pathlib import Path

OLD_CORE_SHA256 = {
    'ubuntu': '404c148b3dbdc7341d9a8166b034ddb93f4aac9eee1168ba331f9b0e9fb79b6c',
    'ubuntu26': '404c148b3dbdc7341d9a8166b034ddb93f4aac9eee1168ba331f9b0e9fb79b6c',
    'rhel8': 'daf71e8f3e0f284ddc2abb038eb858e0df5f154f9df6d8ad1e60a23d75dd096d',
    'rhel9': 'ebc4411647d29aaf900b7610adafd6734b57776f4f7c59fa62b6a9347a5a65b3',
    'rhel10': '00ddb4ba37c69bc9a2030ece5494ab990c7a65b3e79fd8e2ef432c3725a4767f',
}
LIMITS = {'throttleenabled': (0, 1), 'throttlemaxfailures': (1, 10),
          'throttleblockwindow': (60, 86400), 'throttlemaxbackoff': (60, 86400),
          'loginhistoryretention': (1, 365), 'opsauditretainfiles': (1, 100),
          'configautobackupretention': (3, 3650)}


def split_diagnostics(root, output):
    """Allow only source-confirmed pre-existing paid-module/stock-Example warnings."""
    errors, warnings = [], []
    prefix = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ \[WARN\] \[\d+\] (.*)$')
    example = Path(root) / 'Example/html'
    allowed = {'[cyberpanel_ols] License validation failed - module features disabled'}
    if example.is_dir() and example.stat().st_uid == 0 and example.stat().st_gid < 10:
        context = '[config:server:vhosts:vhost:Example] '
        allowed.update((context + 'Uid of %s/ is 0, smaller than minimum requirement 11, use server uid!' % example,
                        context + 'Gid of %s/ is 65534, smaller than minimum requirement 10, use server gid!' % example))
    for line in output.splitlines():
        if not line.strip():
            continue
        match = prefix.fullmatch(line)
        if match and match.group(1) in allowed:
            warnings.append(match.group(1))
        else:
            errors.append(line)
    return errors, sorted(warnings)


def digest(path):
    result = hashlib.sha256()
    with open(str(path), 'rb') as source:
        for data in iter(lambda: source.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def host_platform(os_release='/etc/os-release'):
    if platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('Parser recovery requires x86_64')
    values = {}
    for line in Path(os_release).read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value.strip().strip('\"\'')
    name, major = values.get('ID'), values.get('VERSION_ID', '').split('.')[0]
    if name == 'ubuntu' and major in ('22', '24', '26'):
        return 'ubuntu26' if major == '26' else 'ubuntu'
    if name in ('almalinux', 'rocky', 'rhel', 'centos', 'cloudlinux', 'ol') and major in ('8', '9', '10'):
        return 'rhel' + major
    raise RuntimeError('Unsupported parser recovery OS')


def require_known_failure(root, selected, returncode, output):
    """Return recognized settings only for the exact released defect signature."""
    root = Path(root)
    if selected not in OLD_CORE_SHA256 or digest(root / 'bin/openlitespeed') != OLD_CORE_SHA256[selected]:
        raise RuntimeError('Installed core is not the affected pinned release')
    if returncode != 2:
        raise RuntimeError('Installed core did not report the affected error status')
    path = str(root / 'admin/conf/admin_config.conf')
    # Only the exact native diagnostic is admissible, including root context/path.
    pattern = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ \[ERROR\] \[\d+\] '
                         r'\[PlainConf\] \[adminConfig:\] Not support \[([a-z]+) ([0-9]+)\] in file '
                         + re.escape(path) + r':([1-9][0-9]*)$')
    lines = (root / 'admin/conf/admin_config.conf').read_text().splitlines()
    found = {}
    diagnostic_lines, _ = split_diagnostics(root, output)
    for line in diagnostic_lines:
        if not line.strip():
            continue
        match = pattern.fullmatch(line)
        if not match:
            # Warnings may conceal additional incompatible state: intentionally strict.
            raise RuntimeError('Preflight contains diagnostics outside the known parser defect')
        key, value, number = match.groups()
        if key not in LIMITS or key in found or not LIMITS[key][0] <= int(value) <= LIMITS[key][1]:
            raise RuntimeError('Unknown, duplicate or invalid WebAdmin setting')
        index = int(number) - 1
        if index >= len(lines) or not re.fullmatch(r'\s*' + key + r'\s+' + re.escape(value) + r'\s*(?:#.*)?', lines[index], re.I):
            raise RuntimeError('Diagnostic does not match unchanged admin configuration')
        found[key] = int(value)
    if not found:
        raise RuntimeError('No affected WebAdmin settings found')
    if found.get('throttleblockwindow', 900) > found.get('throttlemaxbackoff', 14400):
        raise RuntimeError('Invalid throttle block/backoff relationship')
    return found


def recovery_hint(binary, returncode, output):
    try:
        require_known_failure(Path(binary).parent.parent, host_platform(), returncode, output)
    except (OSError, RuntimeError, ValueError):
        return ''
    return (' Known WebAdmin parser defect detected. Use the checksum-verified '
            'install-module-2.5.7-r2.sh --repair-webadmin-parser recovery release, '
            'then rerun this upgrade. Configuration validation remains mandatory.')
