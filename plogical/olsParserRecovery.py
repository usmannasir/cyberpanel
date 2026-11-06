"""Identify the narrowly bounded WebAdmin parser defect; never waive validation.

Revision 5 classifier. The only behavioral change from the r2 classifier is the
stock Example virtual-host ownership allowlist, which is now derived from the
actual document-root ownership and the configured server group exactly as the
native core prints them (src/http/httpvhost.cpp, HttpVHost::updateUGid):

    if (st.st_uid < procConfig.getUidMin())
        LS_WARN("[%s] Uid of %s is %d, ...", pLogId, achBuf, st.st_uid, uidMin);
    if (st.st_gid < procConfig.getGidMin()) {
        st.st_gid = procConfig.getGid();            /* server gid, not the file's */
        LS_WARN("[%s] Gid of %s is %d, ...", pLogId, achBuf, st.st_gid, gidMin);
    }

The Uid line therefore reports the directory's real uid, while the Gid line
reports the SERVER group after reassignment. A printed Gid never equals the
directory's gid; it proves only that the directory gid was below the minimum.
"""
import grp
import hashlib
import os
import platform
import re
import stat
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

# Explicitly supported customer/generator process limits: every supported
# configuration generator writes CGIRLimit minUID 11 / minGID 10. These are
# NOT the native source defaults (which can be 100/100); a server whose
# minimum differs prints different text and fails closed. It is not recovered.
MIN_UID, MIN_GID = 11, 10
EXAMPLE_CONTEXT = '[config:server:vhosts:vhost:Example] '
LICENSE_WARNING = '[cyberpanel_ols] License validation failed - module features disabled'
_WARNING = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+ \[WARN\] \[\d+\] (.*)$')
_GROUP = re.compile(r'^[ \t]*group[ \t]+(\S+)[ \t]*(?:#.*)?$', re.I)
_APACHE = re.compile(r'^[ \t]*readApacheConf[ \t]+\S', re.I | re.M)


def example_ownership(root):
    """Return (uid, gid) of the stock Example document root, or None.

    Every path component below the validated installation root (`Example`
    and `Example/html`) is inspected with lstat and must be a real directory.
    The native core follows links, but a linked parent or document root can
    point outside the installation and is not the stock layout this recovery
    is bounded to, so it earns no allowance. The root itself is normalized
    with abspath exactly like the paired driver, which rejects a linked root.
    """
    current = Path(os.path.abspath(str(root)))
    info = None
    for part in ('Example', 'html'):
        current = current / part
        try:
            info = os.lstat(str(current))
        except OSError:
            return None
        if not stat.S_ISDIR(info.st_mode):
            return None
    return info.st_uid, info.st_gid


def top_level_group(text):
    """Return the single top-level `group` value from plain OLS config, or None.

    This is a narrow brace/backtick scanner, not an OLS parser. Lines inside
    `{ ... }` blocks or inside backtick-quoted opaque text (for example
    modsecurity_rules) are ignored. Anything the scanner cannot classify
    unambiguously (unbalanced braces, several braces per line, an
    unterminated backtick block, braces or backticks on the group line, more
    than one top-level group) yields None so the Gid allowance fails closed.
    """
    depth, opaque, found = 0, False, []
    for line in text.splitlines():
        ticks = line.count('`')
        if opaque:
            if ticks % 2:
                opaque = False
            continue
        if ticks:
            if ticks % 2:
                opaque = True
            continue
        if line.lstrip().startswith('#'):
            continue
        opens, closes = line.count('{'), line.count('}')
        if opens > 1 or closes > 1:
            return None
        if depth == 0 and not opens and not closes:
            match = _GROUP.match(line)
            if match:
                found.append(match.group(1))
        depth += opens - closes
        if depth < 0:
            return None
    if opaque or depth != 0 or len(found) != 1:
        return None
    return found[0]


def server_gid(root):
    """Resolve the configured server group id the native core prints, or None.

    Exactly one top-level `group` directive in conf/httpd_config.conf is
    accepted (see top_level_group). ReadApacheConf re-applies Apache
    User/Group into the process configuration after the plain directives
    (patch 06, httpserver.cpp), so a configuration that imports Apache
    settings cannot be resolved here and yields None; the Gid warning then
    stays an unrecognized diagnostic.
    """
    try:
        text = (Path(root) / 'conf/httpd_config.conf').read_text(encoding='utf-8')
    except (OSError, ValueError):
        return None
    if _APACHE.search(text):
        return None
    name = top_level_group(text)
    if name is None:
        return None
    if re.fullmatch(r'[0-9]{1,10}', name):
        value = int(name)
        return value if value < 2 ** 32 - 1 else None
    try:
        return grp.getgrnam(name).gr_gid
    except (KeyError, OSError, ValueError):
        return None


def example_warnings(root):
    """Allowlist only the Example warnings the actual ownership can produce."""
    root = Path(os.path.abspath(str(root)))
    allowed = set()
    ownership = example_ownership(root)
    if ownership is None:
        return allowed
    uid, gid = ownership
    path = str(root / 'Example/html') + '/'
    if uid < MIN_UID:
        allowed.add(EXAMPLE_CONTEXT + 'Uid of %s is %d, smaller than minimum requirement %d, use server uid!'
                    % (path, uid, MIN_UID))
    if gid < MIN_GID:
        printed = server_gid(root)
        if printed is not None:
            allowed.add(EXAMPLE_CONTEXT + 'Gid of %s is %d, smaller than minimum requirement %d, use server gid!'
                        % (path, printed, MIN_GID))
    return allowed


def split_diagnostics(root, output):
    """Allow only source-confirmed pre-existing paid-module/stock-Example warnings."""
    errors, warnings = [], []
    allowed = {LICENSE_WARNING} | example_warnings(root)
    for line in output.splitlines():
        if not line.strip():
            continue
        match = _WARNING.fullmatch(line)
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


def _describe(line):
    """Bounded, printable rendering of an unrecognized diagnostic for the operator."""
    text = ''.join(char if 32 <= ord(char) < 127 else '?' for char in line)
    return text[:300] + ('...' if len(text) > 300 else '')


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
            # Name the first unrecognized line so one native run yields evidence.
            # A customized minUID/minGID (for example the native 100/100 defaults)
            # lands here by design and is not recovered.
            ownership = example_ownership(root)
            raise RuntimeError('Preflight contains diagnostics outside the known parser defect: %s '
                               '(Example/html ownership %s, configured server gid %s)'
                               % (_describe(line),
                                  'uid=%d gid=%d' % ownership if ownership else 'unavailable',
                                  server_gid(root)))
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
            'install-module-2.5.7-r5.sh --repair-webadmin-parser recovery release, '
            'then rerun this upgrade. Configuration validation remains mandatory.')
