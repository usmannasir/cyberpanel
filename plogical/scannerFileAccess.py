"""Work on one website's files for the AI Scanner API, as the website's own user.

The panel's web process cannot enter a website's home, and nothing the scanner
does needs more than the website's own account may do. Every listing, read,
backup, replacement, rename and deletion is therefore one fixed command run as
that account, with each word quoted, and never a command run as root.

A path from a request is accepted in one place only, SiteFiles._resolve():
it must be made of plain names, and after every link on the way has been
resolved (as the website's user) it must still lie inside the site directory.
The commands that then open a file refuse to follow a link in its last name.
"""
import getpass
import hashlib
import io
import os
import secrets
import shlex
import stat
import subprocess
import time
import unicodedata

from plogical.securityUtils import is_safe_system_user


READ_LIMIT = 10 * 1024 * 1024
MAX_PATH_LENGTH = 1024
MAX_NAME_BYTES = 255
READABLE_EXTENSIONS = ('.php', '.js', '.html', '.htm', '.css', '.txt', '.md', '.json', '.xml',
                       '.sql', '.log', '.conf', '.ini', '.yml', '.yaml')
SKIPPED_NAMES = ('__pycache__', 'node_modules')
# Files that decide how the whole site runs: the scanner never changes them.
PROTECTED_NAMES = frozenset(('wp-config.php', '.htaccess', '.user.ini', 'php.ini'))
BACKUP_DIRECTORY = '.ai-scanner-backups'


class Refused(Exception):
    """The request is not allowed or cannot be met; the code goes back to the API."""

    def __init__(self, code, **details):
        Exception.__init__(self, code)
        self.code = code
        self.details = details


def clean_relative_path(requested):
    """Return a request's path as clean relative components; '' is the site directory itself.

    A name may hold any character a file name can, except control characters:
    whoever plants a file chooses its name, and the scanner has to reach it.
    Refused: anything that is not text, a parent or empty component, a name
    longer than a file system allows, and control characters (a line break
    and a tab among them). Every name reaches a command as one quoted word.
    """
    if not isinstance(requested, str):
        raise Refused('path_not_allowed')
    path = requested.strip('/')
    if path in ('', '.'):
        return ''
    if len(path) > MAX_PATH_LENGTH:
        raise Refused('path_not_allowed')
    parts = path.split('/')
    for part in parts:
        if part in ('', '.', '..'):
            raise Refused('path_not_allowed')
        # Cc: control characters, NUL included. Cs: half a character, which is no text.
        if any(unicodedata.category(char) in ('Cc', 'Cs') for char in part):
            raise Refused('path_not_allowed')
        if len(part.encode('utf-8')) > MAX_NAME_BYTES:
            raise Refused('path_not_allowed')
    return '/'.join(parts)


def is_protected_name(path):
    return os.path.basename(path).lower() in PROTECTED_NAMES


def has_readable_extension(path):
    return os.path.splitext(path)[1].lower() in READABLE_EXTENSIONS


def text_digests(data):
    """MD5 and SHA-256 of file content as the API hands it out: as UTF-8 text."""
    text = data.decode('utf-8', errors='replace').encode('utf-8')
    try:
        md5 = hashlib.md5(text).hexdigest()
    except ValueError:
        # A system that only allows approved digests has no MD5.
        md5 = ''
    return md5, hashlib.sha256(text).hexdigest()


def run_as_site_user(command, user):
    """Run one command as a website's user; return (it exited with 0, its output as bytes)."""
    if getpass.getuser() == 'root':
        process = subprocess.Popen(['sudo', '-u', user, '--', 'sh', '-c', command], cwd='/',
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
        output = process.communicate()[0]
        return process.returncode == 0, output
    from plogical.processUtilities import ProcessUtilities
    sink = io.BytesIO()
    succeeded = ProcessUtilities.streamCommand(command, user, sink)
    return succeeded == 1, sink.getvalue()


def write_private_temp_file(content):
    """Keep new file content under a name nobody can guess, where only the panel creates files.

    The website's user reads it from there. The folder is set up with the
    panel's fixed commands only when it is missing or not in that state.
    """
    from plogical.fileSystemSecurity import SHARED_TEMP_DIRECTORY, write_shared_temp_file
    try:
        status = os.stat(SHARED_TEMP_DIRECTORY)
        ready = status.st_uid == os.geteuid() and stat.S_IMODE(status.st_mode) == 0o711
    except OSError:
        ready = False
    if not ready:
        from plogical.acl import ACLManager
        ACLManager.CreateSecureDir()
    return write_shared_temp_file(content)


def _inside(base, path):
    return os.path.commonpath([base, path]) == base


class SiteFiles(object):
    """The files of one website, reached as its own user.

    `home` is the website's home, `root` the directory the scanner may work
    in; `user` must be a plain account name other than root, so a website
    without an account of its own gets no file access at all.
    """

    def __init__(self, user, home, root, runner=None, temp_writer=None):
        if not is_safe_system_user(user) or user == 'root' or user.startswith('-'):
            raise Refused('no_site_user')
        for path in (home, root):
            if not isinstance(path, str) or not path.startswith('/') or path != os.path.normpath(path) \
                    or '/' + clean_relative_path(path) != path:
                raise Refused('path_not_allowed')
        self.user = user
        self.home = home
        self.root = root
        self.runner = runner or run_as_site_user
        self.left_out = 0
        self.temp_writer = temp_writer or write_private_temp_file

    # -- commands ---------------------------------------------------------

    def _run(self, *words):
        """One command for the website's user: fixed words, each quoted, nothing else."""
        command = ' '.join(shlex.quote(word) for word in words) + ' 2>/dev/null'
        try:
            succeeded, output = self.runner(command, self.user)
        except Exception:
            return False, b''
        return bool(succeeded), output if isinstance(output, bytes) else b''

    def _resolve(self, requested, keep_last=False, directory=False):
        """Accept one path from a request, or refuse it.

        Returns the resolved home, the resolved site directory and the
        resolved path. With keep_last the last name is taken as it is: it
        names the entry to change or create, not what a link there points to.
        With directory the path must be a folder.
        """
        relative = clean_relative_path(requested)
        if keep_last:
            if not relative:
                raise Refused('path_not_allowed')
            parent, name = os.path.split(relative)
        else:
            parent, name = relative, ''
        target = os.path.join(self.root, parent) if parent else self.root
        if keep_last or directory:
            target += '/.'
        succeeded, output = self._run('realpath', '-e', '--', self.home, self.root, target)
        if not succeeded:
            raise Refused('not_found')
        try:
            lines = output.decode('utf-8').split('\n')
        except UnicodeDecodeError:
            raise Refused('path_not_allowed')
        if len(lines) != 4 or lines[3] != '' or not all(line.startswith('/') for line in lines[:3]):
            raise Refused('path_not_allowed')
        real_home, real_root, resolved = lines[:3]
        if real_home == '/' or not _inside(real_home, real_root) or not _inside(real_root, resolved):
            raise Refused('path_not_allowed')
        if name:
            resolved = os.path.join(resolved, name)
        return real_home, real_root, resolved

    def _status(self, path):
        """Mode, size and modification time of the entry itself; None when there is none."""
        succeeded, output = self._run('stat', '-c', '%f %s %Y', '--', path)
        if not succeeded:
            return None
        try:
            mode, size, modified = output.decode('ascii').split()
            return int(mode, 16), int(size), int(modified)
        except (UnicodeDecodeError, ValueError):
            raise Refused('failed')

    def _regular_file(self, path, limit=READ_LIMIT):
        status = self._status(path)
        if status is None:
            raise Refused('not_found')
        if stat.S_ISLNK(status[0]):
            raise Refused('path_not_allowed')
        if not stat.S_ISREG(status[0]):
            raise Refused('not_a_file')
        if limit is not None and status[1] > limit:
            raise Refused('too_large')
        return status

    def _content(self, path, limit=READ_LIMIT):
        succeeded, output = self._run(
            'dd', 'iflag=nofollow,nonblock,count_bytes', 'status=none', 'bs=65536',
            'count=%d' % (limit + 1), 'if=' + path)
        if not succeeded:
            raise Refused('failed')
        if len(output) > limit:
            raise Refused('too_large')
        return output

    def _changeable(self, requested, protected=PROTECTED_NAMES):
        """The file a request wants changed: a plain file of a kind the scanner reads."""
        real_home, real_root, path = self._resolve(requested, keep_last=True)
        if os.path.basename(path).lower() in protected:
            raise Refused('protected_file')
        if not has_readable_extension(path):
            raise Refused('type_not_allowed')
        status = self._regular_file(path)
        return real_home, path, status

    def _backup(self, real_home, path):
        """Copy one file into the website's private backup folder, outside every served directory."""
        base = os.path.join(real_home, BACKUP_DIRECTORY)
        directory = os.path.join(base, time.strftime('%Y-%m-%d'))
        # The folder must be exactly where it is asked for, not behind a link:
        # checked before anything is created in it, and again once it exists.
        succeeded, output = self._run('realpath', '-e', '--', base)
        if succeeded and output != (base + '\n').encode('utf-8'):
            raise Refused('backup_dir_failed')
        if not self._run('mkdir', '-p', '--', directory)[0]:
            raise Refused('backup_dir_failed')
        succeeded, output = self._run('realpath', '-e', '--', directory)
        if not succeeded or output != (directory + '\n').encode('utf-8'):
            raise Refused('backup_dir_failed')
        if not self._run('chmod', '700', '--', base, directory)[0]:
            raise Refused('backup_dir_failed')
        backup_path = os.path.join(directory, '%s.%d.%s.bak' % (
            os.path.basename(path), int(time.time()), secrets.token_hex(6)))
        copied = self._run('dd', 'iflag=nofollow,nonblock', 'oflag=nofollow', 'conv=excl',
                           'status=none', 'bs=65536', 'if=' + path, 'of=' + backup_path)[0]
        status = self._status(backup_path) if copied else None
        if status is None or not stat.S_ISREG(status[0]):
            raise Refused('backup_failed')
        return backup_path, status[1]

    # -- what the API offers ------------------------------------------------

    def list_directory(self, requested):
        """Folders and scannable files of one directory. Links are not listed.

        self.left_out says afterwards how many entries could not be listed for their names.
        """
        path = self._resolve(requested, directory=True)[2]
        # find's exit status says nothing here: it is also non-zero when the
        # folder the command was started in cannot be returned to.
        # A name cannot hold a slash, so one ends each entry.
        output = self._run(
            'find', path + '/.', '-mindepth', '1', '-maxdepth', '1', '-printf', '%y %s %m %f/')[1]
        items = []
        self.left_out = 0
        for entry in output.split(b'/'):
            fields = entry.split(b' ', 3)
            if len(fields) != 4 or fields[0] not in (b'd', b'f'):
                continue
            try:
                name = fields[3].decode('utf-8')
                if clean_relative_path(name) != name:
                    raise Refused('path_not_allowed')
                size, mode = int(fields[1]), int(fields[2], 8)
            except (Refused, ValueError):
                # A name that is no text or holds a control character cannot be asked for.
                self.left_out += 1
                continue
            if name.startswith('.') or name in SKIPPED_NAMES:
                continue
            kind = fields[0].decode('ascii')
            item = {'name': name, 'permissions': stat.filemode(mode)[1:4]}
            if kind == 'd':
                item['type'] = 'directory'
                item['size'] = 0
            elif name.lower().endswith(READABLE_EXTENSIONS):
                item['type'] = 'file'
                item['size'] = size
            else:
                continue
            items.append(item)
        return items

    def read_file(self, requested):
        """Content of one file of a kind the scanner reads, wherever inside the site it really lies."""
        if not has_readable_extension(clean_relative_path(requested)):
            raise Refused('type_not_allowed')
        path = self._resolve(requested)[2]
        if not has_readable_extension(path):
            raise Refused('type_not_allowed')
        status = self._regular_file(path)
        data = self._content(path)
        md5, sha256 = text_digests(data)
        return {'data': data, 'size': status[1], 'modified': status[2], 'md5': md5, 'sha256': sha256}

    def backup_file(self, requested):
        real_home, path, status = self._changeable(requested, protected=frozenset())
        backup_path, size = self._backup(real_home, path)
        return {'backup_path': backup_path, 'size': size}

    def replace_file(self, requested, content, backup=True, verify_sha256=None):
        """Give an existing file new content; its owner and mode stay what they were."""
        if not isinstance(content, bytes) or len(content) > READ_LIMIT:
            raise Refused('too_large')
        real_home, path, status = self._changeable(requested)
        if verify_sha256:
            actual = text_digests(self._content(path))[1]
            if actual != verify_sha256:
                raise Refused('hash_mismatch', actual=actual)
        backup_path = self._backup(real_home, path)[0] if backup else None
        try:
            source = self.temp_writer(content)
        except Exception:
            raise Refused('write_failed', backup_path=backup_path)
        try:
            written = self._run('dd', 'oflag=nofollow', 'conv=nocreat', 'status=none', 'bs=65536',
                                'if=' + source, 'of=' + path)[0]
        finally:
            try:
                os.remove(source)
            except OSError:
                pass
        try:
            stored = self._content(path) if written else None
        except Refused:
            stored = None
        if stored != content:
            raise Refused('replace_failed', backup_path=backup_path)
        md5, sha256 = text_digests(stored)
        return {'backup_path': backup_path, 'bytes_written': len(content), 'md5': md5, 'sha256': sha256}

    def rename_file(self, old_requested, new_requested, backup=True):
        """Give a file a new name that nothing else has yet."""
        clean_relative_path(new_requested)
        real_home, old_path, status = self._changeable(old_requested)
        new_path = self._resolve(new_requested, keep_last=True)[2]
        if is_protected_name(new_path):
            raise Refused('protected_file')
        if self._status(new_path) is not None:
            raise Refused('exists')
        backup_path = self._backup(real_home, old_path)[0] if backup else None
        self._run('mv', '-n', '-T', '--', old_path, new_path)
        moved = self._status(new_path)
        if moved is None or not stat.S_ISREG(moved[0]) or self._status(old_path) is not None:
            raise Refused('rename_failed', backup_path=backup_path)
        return {'backup_path': backup_path}

    def delete_file(self, requested):
        """Remove one file after a copy of it has been kept."""
        real_home, path, status = self._changeable(
            requested, protected=PROTECTED_NAMES | frozenset(('index.php',)))
        sha256 = text_digests(self._content(path))[1]
        backup_path = self._backup(real_home, path)[0]
        self._run('rm', '-f', '--', path)
        if self._status(path) is not None:
            raise Refused('delete_failed', backup_path=backup_path)
        return {'backup_path': backup_path, 'size': status[1], 'modified': status[2], 'sha256': sha256}
