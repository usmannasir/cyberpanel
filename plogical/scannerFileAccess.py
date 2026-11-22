"""Work on one website's files for the AI Scanner API, as the website's own user.

The panel's web process cannot enter a website's home, and nothing the scanner
does needs more than the website's own account may do. Every listing, read,
backup, replacement, rename and deletion is therefore a command run as that
account, and never a command run as root.

Each of them is one command that does its own checking. The shell enters the
website's home, the site directory and the folder the request names, each
time following every link to the real place, and says where it then is. Only
when that folder lies inside the site directory does it go on, and it works
on the one name in the folder it stands in, never through a link in that
name. Check and use cannot come apart, because the shell does not leave the
folder it checked. The panel reads the three places from the output and
takes nothing from a command whose folder is not inside the site.

The text of a command is fixed. What a request names goes in front of it as
quoted words, and the text only ever uses them inside double quotes.

What a command did is read from what it printed, not only from how it says
it ended: a file that is not there prints no description of itself, a backup
prints its folder and its size only once it is complete.
"""
import getpass
import hashlib
import io
import os
import re
import secrets
import shlex
import stat
import subprocess
import time
import unicodedata

from plogical import commandStatus
from plogical.securityUtils import is_safe_system_user


READ_LIMIT = 10 * 1024 * 1024
# The helper takes a command of 1023 bytes, and the shortest command with the
# shortest home leaves fewer than this for the path. Each command is measured
# exactly before it is sent.
MAX_PATH_LENGTH = 640
MAX_NAME_BYTES = 255
READABLE_EXTENSIONS = ('.php', '.js', '.html', '.htm', '.css', '.txt', '.md', '.json', '.xml',
                       '.sql', '.log', '.conf', '.ini', '.yml', '.yaml')
SKIPPED_NAMES = ('__pycache__', 'node_modules')
# Files that decide how the whole site runs: the scanner never changes them.
PROTECTED_NAMES = frozenset(('wp-config.php', '.htaccess', '.user.ini', 'php.ini'))
BACKUP_DIRECTORY = '.ai-scanner-backups'

# How every command begins: error output is dropped, and g enters a folder
# for real and keeps its true path in p (the "/" added and taken away again
# keeps a name that ends in a line break whole).
START = (
    'exec 2>/dev/null\n'
    'g(){ cd -P -- "$1"&&p=$(pwd -P&&echo /)&&p=${p%??};}\n')

# H is the website's home, R the site directory and D the folder of the
# request inside it. The three real paths are printed. Status 8: one of them
# cannot be entered. Status 9: the folder is not inside the site directory,
# or the site directory not inside the home.
ENTER = START + (
    'i(){ case "$1/" in "$2"/*);;*)exit 9;;esac;}\n'
    'g "$H"&&h=$p&&g "$R"&&r=$p&&g "$D"&&d=$p||exit 8\n'
    'printf "%s\\0" "$h" "$r" "$d"\n'
    'i "$r" "$h";i "$d" "$r"\n')

LIST = ENTER + 'find . -mindepth 1 -maxdepth 1 -printf "%y %s %m %f/"\n'

# N is the one name worked on, as ./NAME. Its mode, size and modification
# time are printed; anything but a plain file ends the command (status 5),
# and so does a name that is not there (status 4).
FILE = ENTER + (
    's=$(stat -c "%f %s %Y" -- "$N")||exit 4\n'
    'echo "$s"\n'
    'set -- $s\n'
    'case $1 in 8???);;*)exit 5;;esac\n')

# L is the largest size read.
READ = FILE + (
    '[ "$2" -le "$L" ]||exit 7\n'
    'exec dd iflag=nofollow,nonblock,count_bytes bs=64k count=$((L+1)) if="$N"\n')

# Backups go to HOME/.ai-scanner-backups/T/. The two folders are made one by
# one and entered for real, so neither can be a link to another place, and
# are kept private. The folder is printed when it is ready.
BACKUP_FOLDER = START + (
    'g "$H"||exit 8\n'
    'b=$p/' + BACKUP_DIRECTORY + '\n'
    'mkdir -m 700 "$b"\n'
    'g "$b"&&[ "$p" = "$b" ]&&{ mkdir -m 700 "$T";g "./$T";}&&[ "$p" = "$b/$T" ]&&chmod 700 . ..&&echo "$p"\n')

# The copy is NAME.X.bak in that folder, which must be where it is asked for
# and no link (status 3 otherwise). The copy is complete when it has the size
# of the file; the folder is printed first, and the size once the copy is
# complete. A copy that is not complete is removed (status 5).
BACKUP = FILE + (
    'dd iflag=nofollow,nonblock bs=64k if="$N"|(b=$h/' + BACKUP_DIRECTORY + '/$T\n'
    'g "$b"&&[ "$p" = "$b" ]&&echo "$p"||exit 3\n'
    'k=$N.$X.bak\n'
    'dd conv=excl bs=64k of="$k"\n'
    '[ "$(stat -c %s -- "$k")" = "$2" ]||{ rm -f -- "$k";exit 5;}\n'
    'echo "$2")\n')

# Z is the size of the backup just made, or empty when none was asked for: a
# file that no longer has that size is left alone (status 2).
UNCHANGED = '[ -z "$Z" ]||[ "$2" = "$Z" ]||exit 2\n'

# S is the file with the new content. What the file then holds is printed.
REPLACE = FILE + '[ "$2" -le "$L" ]||exit 7\n' + UNCHANGED + (
    'dd oflag=nofollow conv=nocreat bs=64k if="$S" of="$N"||exit 6\n'
    'exec dd iflag=nofollow,nonblock,count_bytes bs=64k count=$((L+1)) if="$N"\n')

# M is the new name, in the same folder. "E" is printed when it is taken; the
# mode of the file under its new name is printed once the old name is gone.
RENAME = FILE + UNCHANGED + (
    '[ -e "$M" ]||[ -L "$M" ]&&{ echo E;exit 6;}\n'
    'mv -n -T -- "$N" "$M"\n'
    '[ -e "$N" ]||[ -L "$N" ]&&exit 6\n'
    'stat -c %f -- "$M"\n')

# The digest of what is removed is printed, and "gone" once the name is free.
DELETE = FILE + UNCHANGED + (
    'dd iflag=nofollow,nonblock bs=64k if="$N"|sha256sum\n'
    'rm -f -- "$N"\n'
    '[ -e "$N" ]||[ -L "$N" ]&&exit 6\n'
    'echo gone\n')


# What a deletion prints after the file's description.
DELETED = re.compile(br'([0-9a-f]{64})  -\ngone\n\Z')


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

    def _command(self, script, **words):
        """The words an operation works on, each quoted, in front of the operation's fixed text."""
        words['H'] = self.home
        return ' '.join('%s=%s' % (name, shlex.quote(words[name])) for name in sorted(words)) + '\n' + script

    def _output(self, script, **words):
        """Run one command as the website's user; return (it ended with status 0, what it printed)."""
        command = self._command(script, **words)
        # The helper drops a longer request; it is refused here, the same for every caller.
        if not commandStatus.request_fits(self.user, command):
            raise Refused('path_too_long')
        try:
            succeeded, output = self.runner(command, self.user)
        except Exception:
            return False, b''
        return bool(succeeded), output if isinstance(output, bytes) else b''

    def _run(self, script, directory, **words):
        """Run one operation in one folder of the site.

        Returns whether the command ended with status 0, the real home, and
        what the operation printed after it had entered the folder. Refused
        when the folder cannot be entered or does not lie inside the site.
        """
        if self.root == self.home:
            root = '.'
        elif self.root.startswith(self.home + '/'):
            root = './' + self.root[len(self.home) + 1:]
        else:
            root = self.root
        succeeded, output = self._output(script, R=root, D='./' + directory if directory else '.', **words)
        fields = output.split(b'\0', 3)
        if len(fields) != 4:
            raise Refused('not_found')
        try:
            real_home, real_root, real_directory = [field.decode('utf-8') for field in fields[:3]]
        except UnicodeDecodeError:
            raise Refused('path_not_allowed')
        if not all(path.startswith('/') for path in (real_home, real_root, real_directory)):
            raise Refused('path_not_allowed')
        if real_home == '/' or not _inside(real_home, real_root) or not _inside(real_root, real_directory):
            raise Refused('path_not_allowed')
        return succeeded, real_home, fields[3]

    @staticmethod
    def _described(printed):
        """Mode, size and modification time of the file an operation found, and what it printed after them."""
        line, found, rest = printed.partition(b'\n')
        if not found:
            raise Refused('not_found')
        try:
            mode, size, modified = line.decode('ascii').split(' ')
            status = int(mode, 16), int(size), int(modified)
        except ValueError:
            raise Refused('failed')
        if stat.S_ISLNK(status[0]):
            raise Refused('path_not_allowed')
        if not stat.S_ISREG(status[0]):
            raise Refused('not_a_file')
        return status, rest

    @staticmethod
    def _target(requested):
        """The folder and the name a request means, both relative to the site directory."""
        relative = clean_relative_path(requested)
        if not relative:
            raise Refused('path_not_allowed')
        return os.path.split(relative)

    def _changeable(self, requested, protected=PROTECTED_NAMES):
        """The file a request wants changed: one of a kind the scanner reads, and not a protected one."""
        directory, name = self._target(requested)
        if name.lower() in protected:
            raise Refused('protected_file')
        if not has_readable_extension(name):
            raise Refused('type_not_allowed')
        return directory, name

    def _read(self, directory, name):
        succeeded, real_home, printed = self._run(READ, directory, N='./' + name, L=str(READ_LIMIT))
        status, content = self._described(printed)
        if status[1] > READ_LIMIT or len(content) > READ_LIMIT:
            raise Refused('too_large')
        # A read that was cut short is no content.
        if not succeeded or len(content) < status[1]:
            raise Refused('failed')
        return status, content

    def _backup(self, directory, name):
        """Copy one file into the website's private backup folder, outside every served directory.

        Returns the path of the copy and its size, which is the size of the file.
        """
        date = time.strftime('%Y-%m-%d')
        stamp = '%d.%s' % (int(time.time()), secrets.token_hex(6))
        for attempt in (1, 2):
            succeeded, real_home, printed = self._run(BACKUP, directory, N='./' + name, T=date, X=stamp)
            status, printed = self._described(printed)
            folder = '%s/%s/%s' % (real_home, BACKUP_DIRECTORY, date)
            ready = (folder + '\n').encode('utf-8')
            if printed.startswith(ready):
                break
            # The day's folder is not there yet, or not what it has to be: make it once, then copy again.
            if attempt == 2 or self._output(BACKUP_FOLDER, T=date)[1] != ready:
                raise Refused('backup_dir_failed')
        if not succeeded or printed[len(ready):] != b'%d\n' % status[1]:
            raise Refused('backup_failed')
        return '%s/%s.%s.bak' % (folder, name, stamp), status[1]

    def _change(self, script, directory, backup_path, backup_size, **words):
        """Run a command that changes a file; a refusal carries the path of the backup made before."""
        try:
            succeeded, real_home, printed = self._run(
                script, directory, Z='' if backup_size is None else str(backup_size), **words)
            status, printed = self._described(printed)
            if backup_size is not None and status[1] != backup_size:
                raise Refused('changed')
        except Refused as refusal:
            refusal.details.setdefault('backup_path', backup_path)
            raise
        return succeeded, status, printed

    # -- what the API offers ------------------------------------------------

    def list_directory(self, requested):
        """Folders and scannable files of one directory. Links are not listed.

        self.left_out says afterwards how many entries could not be listed for their names.
        """
        succeeded, real_home, output = self._run(LIST, clean_relative_path(requested))
        if not succeeded:
            raise Refused('failed')
        # A name cannot hold a slash, so one ends each entry.
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
        """Content of one file of a kind the scanner reads. A link is not followed."""
        directory, name = self._target(requested)
        if not has_readable_extension(name):
            raise Refused('type_not_allowed')
        status, data = self._read(directory, name)
        md5, sha256 = text_digests(data)
        return {'data': data, 'size': status[1], 'modified': status[2], 'md5': md5, 'sha256': sha256}

    def backup_file(self, requested):
        directory, name = self._changeable(requested, protected=frozenset())
        backup_path, size = self._backup(directory, name)
        return {'backup_path': backup_path, 'size': size}

    def replace_file(self, requested, content, backup=True, verify_sha256=None):
        """Give an existing file new content; its owner and mode stay what they were."""
        if not isinstance(content, bytes) or len(content) > READ_LIMIT:
            raise Refused('too_large')
        directory, name = self._changeable(requested)
        if verify_sha256:
            actual = text_digests(self._read(directory, name)[1])[1]
            if actual != verify_sha256:
                raise Refused('hash_mismatch', actual=actual)
        backup_path, backup_size = self._backup(directory, name) if backup else (None, None)
        try:
            source = self.temp_writer(content)
        except Exception:
            raise Refused('write_failed', backup_path=backup_path)
        try:
            succeeded, status, stored = self._change(
                REPLACE, directory, backup_path, backup_size, N='./' + name, S=source, L=str(READ_LIMIT))
        finally:
            try:
                os.remove(source)
            except OSError:
                pass
        if status[1] > READ_LIMIT:
            raise Refused('too_large', backup_path=backup_path)
        if not succeeded or stored != content:
            raise Refused('replace_failed', backup_path=backup_path)
        md5, sha256 = text_digests(stored)
        return {'backup_path': backup_path, 'bytes_written': len(content), 'md5': md5, 'sha256': sha256}

    def rename_file(self, old_requested, new_requested, backup=True):
        """Give a file a new name in its own folder, one that nothing else has yet."""
        new_directory, new_name = self._target(new_requested)
        directory, name = self._changeable(old_requested)
        if new_name.lower() in PROTECTED_NAMES:
            raise Refused('protected_file')
        if new_directory != directory:
            raise Refused('other_directory')
        backup_path, backup_size = self._backup(directory, name) if backup else (None, None)
        succeeded, status, printed = self._change(
            RENAME, directory, backup_path, backup_size, N='./' + name, M='./' + new_name)
        if printed == b'E\n':
            raise Refused('exists', backup_path=backup_path)
        try:
            moved = stat.S_ISREG(int(printed.decode('ascii').strip() or 'x', 16))
        except ValueError:
            moved = False
        if not succeeded or not moved:
            raise Refused('rename_failed', backup_path=backup_path)
        return {'backup_path': backup_path}

    def delete_file(self, requested):
        """Remove one file after a copy of it has been kept."""
        directory, name = self._changeable(requested, protected=PROTECTED_NAMES | frozenset(('index.php',)))
        backup_path, backup_size = self._backup(directory, name)
        succeeded, status, printed = self._change(DELETE, directory, backup_path, backup_size, N='./' + name)
        removed = DELETED.match(printed)
        if not succeeded or removed is None:
            raise Refused('delete_failed', backup_path=backup_path)
        return {'backup_path': backup_path, 'size': status[1], 'modified': status[2],
                'sha256': removed.group(1).decode('ascii')}
