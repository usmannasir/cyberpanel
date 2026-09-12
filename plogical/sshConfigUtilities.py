"""Edit only global SSH settings and verify them before activating a change."""
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile
import uuid


class SSHConfigError(RuntimeError):
    pass


def render_ssh_config(original, port, root_login):
    port = str(port)
    if not re.fullmatch(r'[0-9]{1,5}', port) or not 1 <= int(port) <= 65535:
        raise SSHConfigError('Invalid SSH port.')
    if root_login not in ('yes', 'no'):
        raise SSHConfigError('Invalid root login setting.')
    values = {b'port': str(int(port)).encode('ascii'), b'permitrootlogin': root_login.encode('ascii')}
    newline = b'\r\n' if b'\r\n' in original else b'\n'
    seen, output, conditional = set(), [], False
    for line in original.splitlines(keepends=True):
        if line.lstrip().startswith(b'#'):
            output.append(line)
            continue
        match = re.match(rb'^([ \t]*)([^ \t=\r\n]+)([ \t]+|[ \t]*=[ \t]*)([^\r\n]*)(\r?\n)?$', line)
        if not match:
            output.append(line)
            continue
        indent, keyword, separator, argument, ending = match.groups()
        keyword_lower = keyword.lower()
        if keyword_lower == b'match':
            conditional = True
        if conditional or keyword_lower not in values:
            output.append(line)
            continue
        if keyword_lower in seen:
            # Retain the old directive and any inline comment as a comment.
            output.append(indent + b'# ' + line[len(indent):])
            continue
        seen.add(keyword_lower)
        comment_at = argument.find(b'#')
        before_comment = argument if comment_at < 0 else argument[:comment_at]
        trailing = before_comment[len(before_comment.rstrip(b' \t')):]
        if comment_at >= 0:
            trailing += argument[comment_at:]
        output.append(indent + keyword + separator + values[keyword_lower] + trailing + (ending or b''))
    # Missing settings must be global even when the file starts with Include or
    # ends inside a Match block. All existing Include/Match lines stay in place.
    missing = [(b'Port', b'port'), (b'PermitRootLogin', b'permitrootlogin')]
    prefix = b''.join(name + b' ' + values[key] + newline for name, key in missing if key not in seen)
    return prefix + b''.join(output)


def validate_ssh_config(path, port, root_login, runner=subprocess.run):
    for flag in ('-t', '-T'):
        result = runner(['/usr/sbin/sshd', flag, '-f', str(path)], stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, timeout=30)
        if result.returncode != 0:
            raise SSHConfigError('SSH configuration validation failed. Existing settings were kept.')
        if flag == '-T':
            settings = {}
            for line in result.stdout.decode('utf-8', errors='replace').splitlines():
                fields = line.split(None, 1)
                if len(fields) == 2:
                    settings.setdefault(fields[0], []).append(fields[1])
            requested = str(int(port))
            if settings.get('port') != [requested]:
                raise SSHConfigError('Included SSH settings select additional ports. Existing settings were kept.')
            if settings.get('permitrootlogin') != [root_login]:
                raise SSHConfigError('Included SSH settings override root login. Existing settings were kept.')
            addresses = settings.get('listenaddress', [])
            if not addresses or any(value.rsplit(':', 1)[-1] != requested for value in addresses):
                raise SSHConfigError('ListenAddress selects a different SSH port. Existing settings were kept.')


def validate_ssh_service(runner=subprocess.run):
    """Refuse launch arguments that can bypass the file being validated.

    Only one explicitly empty options assignment in its standard distribution
    file is supported. No shell or general environment-file parser is used.
    """
    names = ('ExecStart', 'EnvironmentFiles', 'Environment', 'PassEnvironment', 'UnsetEnvironment')
    result = runner(['systemctl', 'show', 'sshd'] + ['--property=' + name for name in names],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    properties = {}
    for line in result.stdout.decode('utf-8', errors='replace').splitlines():
        name, separator, value = line.partition('=')
        if not separator or name not in names or name in properties:
            raise SSHConfigError('Could not verify the SSH service launch command. Existing settings were kept.')
        properties[name] = value
    match = re.fullmatch(r'\{\s*path=/usr/sbin/sshd\s*;\s*argv\[\]=(.*?)\s*;\s*ignore_errors=no\s*;[^{}]*\}', properties.get('ExecStart', ''))
    if result.returncode != 0 or set(properties) != set(names) or match is None:
        raise SSHConfigError('Could not verify the SSH service launch command. Existing settings were kept.')
    try:
        arguments = shlex.split(match.group(1))
    except ValueError:
        arguments = []
    options = {'$SSHD_OPTS': ('SSHD_OPTS', '/etc/default/ssh'),
               '${SSHD_OPTS}': ('SSHD_OPTS', '/etc/default/ssh'),
               '$OPTIONS': ('OPTIONS', '/etc/sysconfig/sshd'),
               '${OPTIONS}': ('OPTIONS', '/etc/sysconfig/sshd')}
    expansions = [argument for argument in arguments[1:] if argument in options]
    if not arguments or arguments[0] != '/usr/sbin/sshd' or len(expansions) > 1 or any(
            argument not in ('-D', '-e', '-4', '-6') and argument not in options for argument in arguments[1:]):
        raise SSHConfigError('The SSH service has custom launch arguments or environment options. Manage those service settings before using this form.')
    environment_binding = None
    if expansions:
        name, filename = options[expansions[0]]
        if any(properties[key] for key in ('Environment', 'PassEnvironment', 'UnsetEnvironment')) or not re.fullmatch(
                re.escape(filename) + r' \(ignore_errors=(?:yes|no)\)', properties['EnvironmentFiles']):
            raise SSHConfigError('SSH options must come only from the standard explicitly empty options file. Existing settings were kept.')
        data, metadata = _empty_options_file(Path(filename), name)
        environment_binding = (filename, hashlib.sha256(data).hexdigest(),
                               {key: metadata[key] for key in ('uid', 'gid', 'mode', 'mtime_ns', 'xattrs')})
    # Runtime status fields in ExecStart change during restart. Bind the parsed
    # command and static environment properties, not PID/start/exit timestamps.
    properties.pop('ExecStart')
    return tuple(arguments), tuple(sorted(properties.items())), environment_binding


def _empty_options_file(path, name):
    try:
        for parent in path.parents:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise SSHConfigError('SSH options file has an unsafe parent directory.')
        data, metadata = _read(path)
        if len(data) > 65536 or metadata['uid'] != 0 or metadata['mode'] & 0o022:
            raise SSHConfigError('SSH options file is not a protected regular file.')
        assignments = [line.strip() for line in data.decode('ascii').splitlines()
                       if line.strip() and not line.lstrip().startswith(('#', ';'))]
        if len(assignments) != 1 or re.fullmatch(name + r"[ \t]*=[ \t]*(?:''|\"\")?[ \t]*", assignments[0]) is None:
            raise SSHConfigError('SSH options are not explicitly empty. Existing settings were kept.')
        return data, metadata
    except (OSError, UnicodeError) as error:
        raise SSHConfigError('Could not verify the standard empty SSH options file. Existing settings were kept.') from error


def ssh_service_is_listening(port, runner=subprocess.run):
    """Verify the active service owns the requested listener."""
    try:
        active = runner(['systemctl', 'is-active', '--quiet', 'sshd'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if active.returncode != 0:
            return False
        process = runner(['systemctl', 'show', 'sshd', '--property=MainPID', '--value'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        pid = process.stdout.decode('ascii').strip()
        if process.returncode != 0 or not pid.isdigit() or int(pid) < 2:
            return False
        listeners = runner(['ss', '-H', '-ltnp', 'sport = :' + str(int(port))],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return listeners.returncode == 0 and re.search(
            rb'\bpid=' + pid.encode('ascii') + rb'(?=[,)])', listeners.stdout) is not None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def _sync_directory(path):
    descriptor = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read(path):
    for parent in reversed(path.parents):
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise SSHConfigError('SSH configuration has a non-directory parent.')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SSHConfigError('SSH configuration must be a regular file.')
    descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise SSHConfigError('SSH configuration changed while opening.')
        data = stream.read()
        after = os.fstat(stream.fileno())
        if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns):
            raise SSHConfigError('SSH configuration changed while reading.')
    metadata = {'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode),
                'atime_ns': info.st_atime_ns, 'mtime_ns': info.st_mtime_ns,
                'xattrs': {name: os.getxattr(path, name, follow_symlinks=False)
                          for name in os.listxattr(path, follow_symlinks=False)}}
    return data, metadata


def _temporary(path, data, metadata):
    descriptor, name = tempfile.mkstemp(prefix='.cyberpanel-sshd-', dir=str(path.parent))
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, metadata['uid'], metadata['gid'])
        os.chmod(temporary, metadata['mode'])
        for key in os.listxattr(temporary, follow_symlinks=False):
            if key not in metadata['xattrs']:
                os.removexattr(temporary, key, follow_symlinks=False)
        for key, value in metadata['xattrs'].items():
            os.setxattr(temporary, key, value, follow_symlinks=False)
        os.utime(temporary, ns=(metadata['atime_ns'], metadata['mtime_ns']))
        actual_data, actual_metadata = _read(temporary)
        if actual_data != data or actual_metadata != metadata:
            raise SSHConfigError('Could not preserve SSH configuration metadata.')
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        return temporary
    except BaseException:
        temporary.unlink()
        raise


def _same(path, data, metadata):
    current_data, current_metadata = _read(path)
    # Reading can update atime; modification, ownership and all ACL/xattrs must
    # still match before replace or rollback.
    return current_data == data and all(current_metadata[key] == metadata[key]
                for key in ('uid', 'gid', 'mode', 'mtime_ns', 'xattrs'))


def update_ssh_config(path, port, root_login, prepare, restart, is_active,
                      runner=subprocess.run, validator=validate_ssh_config, is_listening=None, backup_directory=None):
    path = Path(path)
    original, metadata = _read(path)
    candidate = render_ssh_config(original, port, root_login)
    lock_path = path.parent / '.cyberpanel-sshd.lock'
    descriptor = os.open(str(lock_path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    temporary = None
    try:
        lock_info = os.fstat(descriptor)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1 or lock_info.st_uid != os.geteuid() or stat.S_IMODE(lock_info.st_mode) != 0o600:
            raise SSHConfigError('SSH configuration lock is not private.')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SSHConfigError('Another SSH configuration change is running.')
        if not _same(path, original, metadata):
            raise SSHConfigError('SSH configuration changed before validation.')
        for service in ('ssh.socket', 'sshd.socket'):
            result = runner(['systemctl', 'is-active', '--quiet', service],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if result.returncode == 0:
                raise SSHConfigError('SSH socket activation manages the listening port. Existing settings were kept.')
            if result.returncode not in (3, 4):
                raise SSHConfigError('Could not determine SSH socket activation state. Existing settings were kept.')
        service_arguments = validate_ssh_service(runner)
        temporary = _temporary(path, candidate, metadata)
        validator(temporary, port, root_login, runner)
        if candidate == original:
            if not is_active() or (is_listening is not None and not is_listening()):
                raise SSHConfigError('SSH service is not active.')
            if validate_ssh_service(runner) != service_arguments:
                raise SSHConfigError('SSH service launch settings changed during validation.')
            return
        prepare()
        validator(temporary, port, root_login, runner)
        if validate_ssh_service(runner) != service_arguments:
            raise SSHConfigError('SSH service launch settings changed during validation.')
        if not _same(path, original, metadata):
            raise SSHConfigError('SSH configuration changed during validation.')
        # Keep previous bytes outside /etc/ssh so Include globs cannot load a
        # newly created backup as another live configuration file.
        backup_root = Path(backup_directory or '/var/lib/cyberpanel/ssh-config-backups')
        for parent in reversed((backup_root,) + tuple(backup_root.parents)):
            if os.path.lexists(parent) and not stat.S_ISDIR(parent.lstat().st_mode):
                raise SSHConfigError('SSH backup path has a non-directory parent.')
        missing_parents = [parent for parent in (backup_root,) + tuple(backup_root.parents)
                           if not parent.exists()]
        backup_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = backup_root.lstat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise SSHConfigError('SSH backup directory is not private.')
        for parent in reversed(missing_parents):
            _sync_directory(parent.parent)
        _sync_directory(backup_root.parent)
        backup = backup_root / ('previous-' + uuid.uuid4().hex + '.conf')
        with backup.open('xb') as stream:
            os.chmod(backup, 0o600)
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        _sync_directory(backup_root)
        os.replace(temporary, path)
        temporary = None
        _sync_directory(path.parent)
        try:
            if not restart() or not is_active() or (is_listening is not None and not is_listening()):
                raise SSHConfigError('SSH did not restart successfully.')
            if validate_ssh_service(runner) != service_arguments:
                raise SSHConfigError('SSH service launch settings changed during activation.')
            if not _same(path, candidate, metadata):
                raise SSHConfigError('SSH configuration changed during activation.')
        except BaseException as error:
            if not _same(path, candidate, metadata):
                raise SSHConfigError('SSH activation failed and configuration changed concurrently. The private previous copy was retained.') from error
            temporary = _temporary(path, original, metadata)
            os.replace(temporary, path)
            temporary = None
            _sync_directory(path.parent)
            try:
                restored = restart() and is_active()
            except Exception:
                restored = False
            if not restored:
                raise SSHConfigError('Previous SSH configuration restored, but the service needs attention through the server console.') from error
            raise SSHConfigError('SSH change failed. Previous configuration and service restored.') from error
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
            _sync_directory(path.parent)
        os.close(descriptor)
