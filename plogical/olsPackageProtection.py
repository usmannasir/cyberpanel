"""Keep OS package updates away from the CyberPanel OpenLiteSpeed build.

CyberPanel installs the vendor ``openlitespeed`` package and overlays its own
core and modules. The package database still says the vendor package owns
those files, so an ordinary OS update puts the stock core back. This helper
makes the protection persistent: an APT hold on Ubuntu, an entry in the
``exclude`` key of the dnf/yum ``[main]`` section on the RPM family. It
records what it added and can take exactly that back.

Standard library only, runs on Python 3.6 and is loadable by file path.

    python3 -IB olsPackageProtection.py --apply | --status | --release

One JSON object is printed. The exit status is 0 for the states
not_applicable, already, applied, protected and released, otherwise 1.

Every result carries ``state``, ``family`` (apt, rpm or None), ``packages``
(what the rules select) and ``reason`` (a sentence, empty when fine), plus
``added`` (newly protected by this call), ``missing`` (still unprotected),
``detail`` (why nothing applies) and ``path`` (the RPM configuration used).
"""
import argparse
import errno
import fnmatch
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile

MARKER = b'cyberpanel_lsi_api_abi_v1'
# The panel's package lock rewrites every line holding the key's name, so the
# tag must never contain it.
TAG_LINE = '# cyberpanel-ols-package-protection'
RECORD_VERSION = 1
CORE_PACKAGE = 'openlitespeed'
WAF_PACKAGE = 'ols-modsecurity'
APT_IDS = ('ubuntu',)
RPM_IDS = ('almalinux', 'rhel', 'centos', 'rocky', 'cloudlinux', 'ol', 'openeuler')
FINE_STATES = ('not_applicable', 'already', 'applied', 'protected', 'released')
INSTALLED = ('install ok installed', 'hold ok installed')
WAF_ABSENT = ('1:', '0:unknown ok not-installed', '0:deinstall ok config-files',
              '0:purge ok not-installed')

_SECTION = re.compile(r'^\[([^\]]*)\]')
_KEY = re.compile(r'^(exclude|excludepkgs)[ \t]*[=:]')
_TOKEN = re.compile(r'[^\s,]+')
# yum reads " ;" on a key line as a comment; dnf reads it as more names.
_INLINE_COMMENT = re.compile(r'[ \t]+;')


class _Stop(Exception):
    def __init__(self, state, reason):
        Exception.__init__(self, reason)
        self.state = state
        self.reason = reason


def _result(state, family, packages, reason='', added=(), missing=(), detail='', path=None):
    return {'state': state, 'family': family, 'packages': list(packages), 'reason': reason,
            'added': list(added), 'missing': list(missing), 'detail': detail, 'path': path}


def _has_marker(path):
    """True only for a regular file, not a symlink, that contains the marker."""
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return False
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return False
        carry = b''
        while True:
            block = os.read(descriptor, 1 << 20)
            if not block:
                return False
            if MARKER in carry + block:
                return True
            carry = block[-(len(MARKER) - 1):]
    except OSError:
        return False
    finally:
        os.close(descriptor)


def _distro_id(path):
    """The ID of os-release in lower case, as the upgrade guard reads it."""
    try:
        with open(path, 'rb') as handle:
            text = handle.read(1 << 16).decode('utf-8', 'replace')
    except OSError:
        return ''
    value = ''
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('ID='):
            value = line[3:].strip().strip('"\'')
    return value.lower()


def _terminate(process):
    # rpm closes its database on SIGTERM; SIGKILL is the last resort.
    for signum in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, signum)
        except OSError:
            pass
        try:
            process.communicate(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()


def _last_line(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:200] if lines else ''


# -- the [main] section of dnf.conf / yum.conf -------------------------------

def _split_lines(text):
    return re.findall(r'[^\n]*\n|[^\n]+', text)


def _split_eol(line):
    for eol in ('\r\n', '\n'):
        if line.endswith(eol):
            return line[:-len(eol)], eol
    return line, ''


def _file_eol(lines):
    return _split_eol(lines[0])[1] or '\n' if lines else '\n'


def _scan(lines):
    """Return (has_main, anchor, keys) for the lines of a configuration.

    ``keys`` lists [first, last] line indexes of every exclude/excludepkgs
    key inside [main], continuation lines included. ``anchor`` is the last
    line of [main] that is its header, a key or a continuation.
    """
    in_main = has_main = continuing = False
    anchor = current = None
    keys = []
    for index, line in enumerate(lines):
        body = _split_eol(line)[0]
        if not body.strip() or body[0] in '#;':
            continuing, current = False, None
        elif body[0] in ' \t':
            # An indented comment between or below value lines carries no names.
            if in_main and continuing and body.strip()[0] not in '#;':
                anchor = index
                if current is not None:
                    current[1] = index
        elif _SECTION.match(body):
            in_main = _SECTION.match(body).group(1) == 'main'
            continuing, current = False, None
            if in_main:
                has_main, anchor = True, index
        else:
            continuing, current = in_main, None
            if in_main:
                anchor = index
                if _KEY.match(body):
                    current = [index, index]
                    keys.append(current)
    return has_main, anchor, keys


def _value_span(body, first):
    """Where the names are on one physical line of a key."""
    if not first:
        return (0, 0) if body.strip()[:1] in ('#', ';') else (0, len(body))
    start = _KEY.match(body).end()
    comment = _INLINE_COMMENT.search(body, start)
    return start, comment.start() if comment else len(body)


def _key_tokens(lines, key):
    tokens = []
    for index in range(key[0], key[1] + 1):
        body = _split_eol(lines[index])[0]
        start, stop = _value_span(body, index == key[0])
        tokens.extend(_TOKEN.findall(body[start:stop]))
    return tokens


def _uncovered(packages, tokens):
    return [package for package in packages
            if not any(fnmatch.fnmatchcase(package, token) for token in tokens)]


def _is_tagged(lines, key):
    return key[0] > 0 and lines[key[0] - 1].strip() == TAG_LINE


def _append(lines, key, names):
    """Add names to the last physical line of an existing key."""
    index = key[1]
    body, eol = _split_eol(lines[index])
    start, stop = _value_span(body, index == key[0])
    head = body[:stop].rstrip(' \t')
    if index == key[0] and len(head) <= start:  # the key has no value yet
        body = body[:stop] + ' '.join(names) + body[stop:]
    else:
        body = head + ' ' + ' '.join(names) + body[len(head):]
    # A later ">>" append must not be glued to the names.
    lines[index] = body + (eol or _file_eol(lines))


def _create(lines, anchor, names):
    """Add the tag line and a new key at the end of [main]."""
    body, eol = _split_eol(lines[anchor])
    eol = eol or _file_eol(lines)
    lines[anchor] = body + eol
    lines[anchor + 1:anchor + 1] = [TAG_LINE + eol, 'exclude=' + ' '.join(names) + eol]


def _drop_token(value, name):
    while True:
        spans = [match.span() for match in _TOKEN.finditer(value)]
        hits = [position for position, (begin, end) in enumerate(spans) if value[begin:end] == name]
        if not hits:
            return value
        position = hits[-1]
        begin, end = spans[position]
        before = value[:begin].rstrip(' \t')
        if position + 1 < len(spans):  # with the separator that follows it
            value = value[:begin] + value[spans[position + 1][0]:]
        elif before:  # the inverse of _append: the space it wrote and the name
            value = before + value[end:]
        else:  # the inverse of filling an empty value
            value = value[:begin] + value[end:]


def _withdraw(lines, keys, names, created_key):
    """Remove recorded names, and the key and tag line this helper created."""
    doomed = set()
    for name in names:
        for key in reversed(keys):
            found = False
            for index in range(key[0], key[1] + 1):
                body, eol = _split_eol(lines[index])
                start, stop = _value_span(body, index == key[0])
                value = _drop_token(body[start:stop], name)
                if value != body[start:stop]:
                    found = True
                    lines[index] = body[:start] + value + body[stop:] + eol
                    if index != key[0] and not lines[index].strip():
                        doomed.add(index)
            if found:
                break
    if created_key:
        for key in keys:
            if _is_tagged(lines, key):
                doomed.add(key[0] - 1)
                if not _key_tokens(lines, key):
                    doomed.update(range(key[0], key[1] + 1))
    return [line for index, line in enumerate(lines) if index not in doomed]


def _sync_directory(directory):
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _atomic_write(path, data, mode, owner=None):
    """Replace path with data through a synced temp file beside it."""
    directory = os.path.dirname(path) or '.'
    descriptor, temporary = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.',
                                             suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            current = os.fstat(handle.fileno())
            if owner is not None and (current.st_uid, current.st_gid) != owner:
                os.fchown(handle.fileno(), owner[0], owner[1])
            os.fchmod(handle.fileno(), mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    _sync_directory(directory)


class Protection(object):
    def __init__(self, root='/usr/local/lsws', os_release='/etc/os-release',
                 record='/etc/cyberpanel/ols-package-protection.json',
                 dnf_conf='/etc/dnf/dnf.conf', yum_conf='/etc/yum.conf', timeout=120):
        self.root = str(root)
        self.core = os.path.join(self.root, 'bin', 'openlitespeed')
        self.module = os.path.join(self.root, 'modules', 'cyberpanel_ols.so')
        self.waf = os.path.join(self.root, 'modules', 'mod_security.so')
        self.os_release = str(os_release)
        self.record = str(record)
        self.dnf_conf = str(dnf_conf)
        self.yum_conf = str(yum_conf)
        self.timeout = timeout

    # -- public surface ----------------------------------------------------
    def protect(self):
        """Apply the protection; never raises. See the module docstring."""
        return self._guarded(self._protect)

    def status(self):
        """Report not_applicable, protected, unprotected or refused; changes nothing."""
        result = self._guarded(self._status, unconfirmed='unprotected')
        if result['state'] == 'unprotected' and not result['missing']:
            result['missing'] = list(result['packages'])
        return result

    def release(self):
        """Undo what the record lists, whatever the core is now."""
        return self._guarded(self._release)

    # -- plumbing ----------------------------------------------------------
    def _guarded(self, action, unconfirmed='failed'):
        context = {'family': None, 'packages': [], 'missing': [], 'path': None}
        try:
            return action(context)
        except _Stop as stop:
            state, reason = stop.state, stop.reason
        except Exception as error:  # an expected problem never reaches a caller as a traceback
            state, reason = 'failed', 'Unexpected error (%s): %s.' % (type(error).__name__, error)
        if state == 'failed':
            state = unconfirmed
        return _result(state, context['family'], context['packages'], reason,
                       missing=context['missing'], path=context['path'])

    def _run(self, argv, merge=False):
        """Run a command found on PATH; return (exit status, stdout, stderr)."""
        environment = dict(os.environ)
        environment['LC_ALL'] = 'C'
        try:
            process = subprocess.Popen(
                argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT if merge else subprocess.PIPE,
                env=environment, start_new_session=True)
        except OSError as error:
            raise _Stop('failed', 'Cannot run %s: %s.' % (argv[0], error.strerror or error))
        try:
            output, errors = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            _terminate(process)
            raise _Stop('failed', '%s did not finish within %s seconds.' % (' '.join(argv[:2]), self.timeout))
        return (process.returncode, output.decode('utf-8', 'replace'),
                (errors or b'').decode('utf-8', 'replace'))

    def _applicable(self):
        """Return (family, detail); family is None when nothing here is ours."""
        if not _has_marker(self.core):
            return None, ('The OpenLiteSpeed core %s is absent, not a regular file or not '
                          'the CyberPanel build.' % self.core)
        if not _has_marker(self.module):
            return None, ('The CyberPanel module %s is absent, not a regular file or not '
                          'the CyberPanel build.' % self.module)
        distro = _distro_id(self.os_release)
        if distro in APT_IDS:
            return 'apt', ''
        if distro in RPM_IDS:
            return 'rpm', ''
        return None, 'The distribution "%s" has no package protection rule.' % distro

    # -- record ------------------------------------------------------------
    def _read_record(self):
        """Return (record or None, problem)."""
        try:
            with open(self.record, 'rb') as handle:
                data = handle.read(1 << 20)
        except OSError as error:
            if error.errno in (errno.ENOENT, errno.ENOTDIR):
                return None, ''
            return None, 'Cannot read the record %s: %s.' % (self.record, error.strerror or error)
        try:
            record = json.loads(data.decode('utf-8'))
            valid = (isinstance(record, dict) and record.get('family') in ('apt', 'rpm') and
                     isinstance(record.get('added'), list) and
                     all(name in (CORE_PACKAGE, WAF_PACKAGE) for name in record['added']))
        except ValueError:
            valid = False
        if not valid:
            return None, 'The record %s is not one this helper wrote.' % self.record
        return record, ''

    def _remember(self, family, path, added, created, tagged):
        """Merge what this call added into the record; return a problem or ''."""
        old = self._read_record()[0]
        names = []
        if old and old.get('path') == path and old['family'] == family:
            names = list(old['added'])
            created = created or (bool(old.get('created_key')) and tagged)
        names.extend(name for name in added if name not in names)
        record = {'version': RECORD_VERSION, 'family': family, 'path': path,
                  'added': names, 'created_key': bool(created)}
        try:
            parent = os.path.dirname(self.record) or '.'
            if not os.path.isdir(parent):
                os.makedirs(parent, 0o755)
                os.chmod(parent, 0o755)
            _atomic_write(self.record, (json.dumps(record, indent=2, sort_keys=True) + '\n').encode('utf-8'), 0o644)
        except OSError as error:
            return ('The protection is in place, but the record %s could not be written (%s), '
                    'so --release will not undo it.' % (self.record, error.strerror or error))
        return ''

    # -- apt ---------------------------------------------------------------
    def _apt_packages(self):
        output = self._run(['dpkg-query', '-W', '-f=${Status}', CORE_PACKAGE])[1].rstrip('\n')
        if output not in INSTALLED:
            raise _Stop('refused', 'dpkg does not report the %s package as installed (state "%s"), so the '
                        'custom OpenLiteSpeed build has no verified package owner; nothing was changed.'
                        % (CORE_PACKAGE, output))
        packages = [CORE_PACKAGE]
        # ols-modsecurity owns modules/mod_security.so on its own.
        status, output = self._run(['dpkg-query', '-W', '-f=${Status}', WAF_PACKAGE])[:2]
        state = '%d:%s' % (status, output.rstrip('\n'))
        if state in tuple('0:' + installed for installed in INSTALLED):
            packages.append(WAF_PACKAGE)
        elif state not in WAF_ABSENT:
            raise _Stop('refused', 'The %s package is in an uncertain dpkg state (%s); nothing was changed.'
                        % (WAF_PACKAGE, state))
        return packages

    def _held(self):
        status, output, errors = self._run(['apt-mark', 'showhold'])
        if status != 0:
            raise _Stop('failed', ('apt-mark showhold exited %d. %s' % (status, _last_line(errors))).strip())
        return set(line.strip() for line in output.splitlines() if line.strip())

    def _protect_apt(self, context):
        packages = context['packages'] = self._apt_packages()
        held = self._held()
        missing = [package for package in packages if package not in held]
        if not missing:
            return _result('already', 'apt', packages)
        status, _, errors = self._run(['apt-mark', 'hold'] + missing)
        held = self._held()
        added = [package for package in missing if package in held]
        problem = self._remember('apt', None, added, False, False) if added else ''
        context['missing'] = [package for package in missing if package not in held]
        if context['missing']:
            raise _Stop('failed', ('apt-mark hold (exit %d) left %s without a hold. %s'
                        % (status, ', '.join(context['missing']), _last_line(errors))).strip())
        if problem:
            raise _Stop('failed', problem)
        return _result('applied', 'apt', packages, added=added)

    def _release_apt(self, names):
        held = self._held()
        targets = [name for name in names if name in held]
        if not targets:
            return
        status, _, errors = self._run(['apt-mark', 'unhold'] + targets)
        held = self._held()
        left = [name for name in targets if name in held]
        if left:
            raise _Stop('failed', ('apt-mark unhold (exit %d) left %s on hold; the record is kept. %s'
                        % (status, ', '.join(left), _last_line(errors))).strip())

    # -- rpm ---------------------------------------------------------------
    def _rpm_packages(self):
        names = []
        for target in (self.core, self.module, self.waf):
            if target != self.core and not os.path.lexists(target):
                continue
            status, output = self._run(['rpm', '-q', '--queryformat', '%{NAME}\\n', '--file', target],
                                       merge=True)[:2]
            output = output.rstrip('\n')
            if (status == 1 and target != self.core and
                    output == 'file %s is not owned by any package' % target):
                continue  # the overlay normally installs the CyberPanel module
            if status != 0 or not output:
                raise _Stop('refused', 'Cannot determine the RPM owner of %s (rpm exit %d: %s); '
                            'nothing was changed.' % (target, status, _last_line(output)))
            for owner in output.split('\n'):
                if owner != CORE_PACKAGE and not (owner == WAF_PACKAGE and target == self.waf):
                    raise _Stop('refused', 'Unexpected RPM owner "%s" of %s; nothing was changed.'
                                % (owner[:80], target))
                if owner not in names:
                    names.append(owner)
        return names

    def _config_path(self):
        for candidate in (self.dnf_conf, self.yum_conf):
            if os.path.exists(candidate):
                return os.path.realpath(candidate)  # yum.conf is a symlink on EL8 and later
        raise _Stop('failed', 'Neither %s nor %s exists; nothing was changed.' % (self.dnf_conf, self.yum_conf))

    def _read_config(self, path):
        try:
            info = os.stat(path)
            if not stat.S_ISREG(info.st_mode):
                raise _Stop('failed', '%s is not a regular file; nothing was changed.' % path)
            with open(path, 'rb') as handle:
                return info, _split_lines(handle.read().decode('latin-1'))
        except OSError as error:
            raise _Stop('failed', 'Cannot read %s: %s.' % (path, error.strerror or error))

    def _layout(self, path, packages):
        """Return (stat, lines, anchor, keys, uncovered packages)."""
        info, lines = self._read_config(path)
        has_main, anchor, keys = _scan(lines)
        if not has_main:
            raise _Stop('failed', '%s has no [main] section; add "exclude=%s" to its main section by hand.'
                        % (path, ' '.join(packages)))
        return info, lines, anchor, keys, _uncovered(packages, _key_tokens(lines, keys[-1]) if keys else [])

    def _write_config(self, path, info, lines):
        try:
            _atomic_write(path, ''.join(lines).encode('latin-1'), stat.S_IMODE(info.st_mode),
                          (info.st_uid, info.st_gid))
        except OSError as error:
            raise _Stop('failed', 'Cannot update %s (%s); the file is unchanged.' % (path, error.strerror or error))

    def _protect_rpm(self, context):
        packages = context['packages'] = self._rpm_packages()
        path = context['path'] = self._config_path()
        info, lines, anchor, keys, missing = self._layout(path, packages)
        if not missing:
            return _result('already', 'rpm', packages, path=path)
        if keys:
            _append(lines, keys[-1], missing)
        else:
            _create(lines, anchor, missing)
        self._write_config(path, info, lines)
        _, lines, _, written, context['missing'] = self._layout(path, packages)
        if context['missing']:
            raise _Stop('failed', '%s was written but still does not exclude %s.'
                        % (path, ', '.join(context['missing'])))
        problem = self._remember('rpm', path, missing, not keys,
                                 any(_is_tagged(lines, key) for key in written))
        if problem:
            raise _Stop('failed', problem)
        return _result('applied', 'rpm', packages, added=missing, path=path)

    def _release_rpm(self, record, names):
        path = record.get('path')
        if not path or not os.path.exists(path):
            return
        info, lines = self._read_config(path)
        cleaned = _withdraw(list(lines), _scan(lines)[2], names, bool(record.get('created_key')))
        if cleaned == lines:
            return
        self._write_config(path, info, cleaned)
        if self._read_config(path)[1] != cleaned:
            raise _Stop('failed', '%s was written but does not hold the expected content; '
                        'the record is kept.' % path)

    # -- the three actions -------------------------------------------------
    def _protect(self, context):
        family, detail = self._applicable()
        if family is None:
            return _result('not_applicable', None, [], detail=detail)
        context['family'] = family
        return self._protect_apt(context) if family == 'apt' else self._protect_rpm(context)

    def _status(self, context):
        family, detail = self._applicable()
        if family is None:
            return _result('not_applicable', None, [], detail=detail)
        context['family'] = family
        if family == 'apt':
            packages = context['packages'] = self._apt_packages()
            held = self._held()
            missing = [package for package in packages if package not in held]
        else:
            packages = context['packages'] = self._rpm_packages()
            context['path'] = self._config_path()
            missing = self._layout(context['path'], packages)[4]
        if missing:
            return _result('unprotected', family, packages, missing=missing, path=context['path'],
                           reason='A package update can replace the custom OpenLiteSpeed build: '
                                  '%s is not protected.' % ', '.join(missing))
        return _result('protected', family, packages, path=context['path'])

    def _release(self, context):
        record, problem = self._read_record()
        if problem:
            raise _Stop('failed', problem + ' Nothing was released.')
        if record is None:
            return _result('not_applicable', None, [], detail='There is no record at %s, so there is '
                           'nothing of this helper to undo.' % self.record)
        family = context['family'] = record['family']
        names = context['packages'] = list(record['added'])
        if family == 'apt':
            self._release_apt(names)
        else:
            context['path'] = record.get('path')
            self._release_rpm(record, names)
        try:
            os.unlink(self.record)
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise _Stop('failed', 'The protection was released but the record %s could not be '
                            'removed: %s.' % (self.record, error.strerror or error))
        return _result('released', family, names, path=context['path'])


def protect(**paths):
    return Protection(**paths).protect()


def status(**paths):
    return Protection(**paths).status()


def release(**paths):
    return Protection(**paths).release()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Protect the CyberPanel OpenLiteSpeed build from OS package updates.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--apply', action='store_true', help='hold or exclude the owning packages')
    mode.add_argument('--status', action='store_true', help='report without changing anything')
    mode.add_argument('--release', action='store_true', help='undo what --apply recorded')
    defaults = Protection()
    parser.add_argument('--root', default=defaults.root)
    parser.add_argument('--os-release', default=defaults.os_release)
    parser.add_argument('--record', default=defaults.record)
    parser.add_argument('--dnf-conf', default=defaults.dnf_conf)
    parser.add_argument('--yum-conf', default=defaults.yum_conf)
    options = parser.parse_args(argv)
    protection = Protection(root=options.root, os_release=options.os_release, record=options.record,
                            dnf_conf=options.dnf_conf, yum_conf=options.yum_conf)
    if options.apply:
        result = protection.protect()
    elif options.status:
        result = protection.status()
    else:
        result = protection.release()
    sys.stdout.write(json.dumps(result, sort_keys=True) + '\n')
    return 0 if result['state'] in FINE_STATES else 1


if __name__ == '__main__':
    sys.exit(main())
