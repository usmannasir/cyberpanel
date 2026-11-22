"""The AI Scanner works on a website's files as that website's user and only inside the site."""
import hashlib
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from plogical import fileSystemSecurity
from plogical import scannerFileAccess as files
from plogical.scannerFileAccess import Refused, SiteFiles, clean_relative_path


# Names a file can have and a shell would act on if they ever reached it unquoted.
ODD_NAMES = (
    '\' " $ ` \\ ; & | < > * ? ( ) { } [ ] ! # ~.php',
    '$(touch secaimark1).php', '`touch secaimark2`.php', 'a.php"; touch secaimark3; ".php',
    "a.php'; touch secaimark4; '.php", 'a.php & touch secaimark5 &.php', 'a;touch secaimark6;.php',
    '-rf.php', '--help.php', '$HOME.php', '*.php', 'a:b,c=d+e@f%g^h.php', 'caf\u00e9 \u0645\u06cc\u200c\u062e.php',
)


class LocalRunner(object):
    """Runs each command with a shell, as the root helper does, and keeps what was asked.

    `before` runs ahead of every command and `amend` may change its text:
    that is how a test moves things around between a request and its command,
    or in the middle of one.
    """

    def __init__(self, honest=True, before=None, amend=None, prefix=''):
        self.commands = []
        self.honest = honest
        self.before = before
        self.amend = amend
        self.prefix = prefix

    def __call__(self, command, user):
        self.commands.append((command, user))
        if self.before:
            self.before()
        if self.amend:
            command = self.amend(command)
        process = subprocess.Popen(['sh', '-c', self.prefix + command], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = process.communicate()[0]
        # A runner that is not honest says every command succeeded, whatever it did.
        return (process.returncode == 0) if self.honest else True, output


def write(path, content=b'', mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as handle:
        handle.write(content)
    os.chmod(path, mode)


class SiteTree(unittest.TestCase):

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix='secai'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = os.path.join(self.base, 'home', 'secai.test')
        self.root = os.path.join(self.home, 'public_html')
        self.outside = os.path.join(self.base, 'outside')
        self.temp = os.path.join(self.base, 'tmp')
        os.makedirs(self.temp)
        write(os.path.join(self.root, 'index.php'), b'<?php // index\n')
        write(os.path.join(self.root, 'wp-config.php'), b'<?php // secrets\n')
        write(os.path.join(self.root, 'readme.txt'), b'read me\n')
        write(os.path.join(self.root, 'image.png'), b'\x89PNG')
        write(os.path.join(self.root, '.hidden.php'), b'<?php\n')
        write(os.path.join(self.root, 'node_modules', 'x.js'), b'x\n')
        write(os.path.join(self.root, 'wp-content', 'plugins', 'demo', 'demo.php'), b'<?php // demo\n', 0o640)
        write(os.path.join(self.root, 'wp-content', 'my file (1).php'), b'<?php // spaced\n')
        write(os.path.join(self.home, 'public_html-old', 'secret.php'), b'<?php // old\n')
        write(os.path.join(self.outside, 'secret.txt'), b'outside\n')
        write(os.path.join(self.outside, 'target.php'), b'<?php // outside\n')
        os.symlink(os.path.join(self.outside, 'secret.txt'), os.path.join(self.root, 'link.txt'))
        os.symlink(os.path.join(self.root, 'readme.txt'), os.path.join(self.root, 'inner.txt'))
        os.symlink(self.outside, os.path.join(self.root, 'linkdir'))
        os.symlink(os.path.join(self.home, 'public_html-old'), os.path.join(self.root, 'sibling'))
        os.symlink(os.path.join(self.outside, 'target.php'), os.path.join(self.root, 'evil.php'))
        self.runner = LocalRunner()
        self.site = SiteFiles('secaiuser', self.home, self.root, runner=self.runner,
                              temp_writer=self.temp_writer)

    def temp_writer(self, content):
        path = os.path.join(self.temp, secrets.token_hex(8))
        with open(path, 'wb') as handle:
            handle.write(content)
        return path

    def refused(self, code, call, *arguments, **options):
        with self.assertRaises(Refused) as caught:
            call(*arguments, **options)
        self.assertEqual(code, caught.exception.code)
        return caught.exception

    def read(self, *parts):
        with open(os.path.join(*parts), 'rb') as handle:
            return handle.read()

    def backups(self):
        found = []
        for directory, unused, names in os.walk(os.path.join(self.home, files.BACKUP_DIRECTORY)):
            found.extend(os.path.join(directory, name) for name in names)
        return found


class TempFileTests(unittest.TestCase):
    """New content waits in the panel's shared temporary folder under a name only the panel knows."""

    def setUp(self):
        self.folder = os.path.realpath(tempfile.mkdtemp(prefix='secai'))
        self.addCleanup(shutil.rmtree, self.folder, True)
        os.chmod(self.folder, 0o711)
        patcher = mock.patch.object(fileSystemSecurity, 'SHARED_TEMP_DIRECTORY', self.folder)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_content_is_written_to_a_new_file_the_website_user_can_read(self):
        path = files.write_private_temp_file(b'<?php // new\n\xff')
        self.assertEqual([os.path.basename(path)], os.listdir(self.folder))
        self.assertRegex(os.path.basename(path), r'\A[0-9a-f]{32}\Z')
        self.assertEqual(0o644, stat.S_IMODE(os.stat(path).st_mode))
        with open(path, 'rb') as handle:
            self.assertEqual(b'<?php // new\n\xff', handle.read())

    def test_a_file_that_could_not_be_written_is_not_left_behind(self):
        real_fdopen = os.fdopen

        class Full(object):
            """A file on a disk that takes no more data."""

            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *unused):
                self.handle.close()

            def write(self, content):
                self.handle.write(content[:3])
                raise OSError(28, 'No space left on device')

        with mock.patch.object(fileSystemSecurity.os, 'fdopen', lambda *a, **k: Full(real_fdopen(*a, **k))):
            with self.assertRaises(OSError):
                files.write_private_temp_file(b'<?php // new\n')
            self.assertEqual([], os.listdir(self.folder))
            with mock.patch.object(fileSystemSecurity.os, 'chmod', side_effect=OSError(1, 'Operation not permitted')):
                with self.assertRaises(OSError):
                    fileSystemSecurity.write_shared_temp_file(b'x', discard_on_failure=True)
            self.assertEqual([], os.listdir(self.folder))

    def test_replacing_reports_a_failed_write_and_leaves_no_file(self):
        home = os.path.join(self.folder, 'home')
        write(os.path.join(home, 'public_html', 'readme.txt'), b'read me\n')
        site = SiteFiles('secaiuser', home, os.path.join(home, 'public_html'), runner=LocalRunner())
        with mock.patch.object(fileSystemSecurity.os, 'fdopen', side_effect=OSError(28, 'No space left on device')):
            with self.assertRaises(Refused) as caught:
                site.replace_file('readme.txt', b'new\n', backup=False)
        self.assertEqual('write_failed', caught.exception.code)
        self.assertEqual(['home'], os.listdir(self.folder))
        with open(os.path.join(home, 'public_html', 'readme.txt'), 'rb') as handle:
            self.assertEqual(b'read me\n', handle.read())


class PathTests(unittest.TestCase):

    def test_plain_names_are_accepted(self):
        self.assertEqual('', clean_relative_path(''))
        self.assertEqual('', clean_relative_path('.'))
        self.assertEqual('', clean_relative_path('/'))
        self.assertEqual('wp-content/plugins/a_b.php', clean_relative_path('/wp-content/plugins/a_b.php/'))
        self.assertEqual('wp-content/my file (1).php', clean_relative_path('wp-content/my file (1).php'))
        self.assertEqual('wp-content/uploads/café.txt', clean_relative_path('wp-content/uploads/café.txt'))

    def test_any_character_of_a_file_name_is_accepted_except_control_characters(self):
        for name in ODD_NAMES + ('a b', ' ', '-rf', '--help', 'ünï', '\u200c', '\U0001f600', 'x' * 255, 'é' * 127):
            self.assertEqual(name, clean_relative_path(name), name)
            self.assertEqual('wp-content/' + name, clean_relative_path('/wp-content/' + name + '/'), name)

    def test_names_that_are_no_usable_text_are_refused(self):
        for path in ('a/../b', '..', 'a//b', './a', 'a/./b', 'a/..', '../a',
                     'a\nb.php', 'a\x00b.php', 'a\tb.php', 'a\rb.php', 'a\x1b[0mb.php', 'a\x7fb.php', 'a\x85b.php',
                     '\udcff.php', 'x' * 256, 'é' * 128, 'a/' * 600 + 'b.php', None, 7, b'a.php'):
            with self.assertRaises(Refused):
                clean_relative_path(path)


class AccountTests(unittest.TestCase):

    def test_a_website_without_an_account_of_its_own_gets_no_file_access(self):
        for user in ('', None, 'root', '-u', 'a b', 'a;b', 'a/b'):
            with self.assertRaises(Refused) as caught:
                SiteFiles(user, '/home/example.com', '/home/example.com/public_html')
            self.assertEqual('no_site_user', caught.exception.code)

    def test_the_site_directory_must_be_a_plain_absolute_path(self):
        for root in ('public_html', '/home/example.com/../other', '/home/example.com/a\nb',
                     '/home/example.com/public_html/', '/home/example.com//public_html', None):
            with self.assertRaises(Refused):
                SiteFiles('example', '/home/example.com', root)


class ReadTests(SiteTree):

    def test_a_name_is_only_ever_a_name(self):
        # Each of these is the name of a real file; none of them is run, expanded or taken for an option.
        folder = os.path.join(self.root, 'odd')
        for number, name in enumerate(ODD_NAMES):
            write(os.path.join(folder, name), b'<?php // %d\n' % number)
            write(os.path.join(folder, name + ' dir', 'in.php'), b'<?php // in %d\n' % number)
        listed = dict((item['name'], item['type']) for item in self.site.list_directory('odd'))
        self.assertEqual(sorted(ODD_NAMES + tuple(name + ' dir' for name in ODD_NAMES)), sorted(listed))
        self.assertEqual(0, self.site.left_out)
        for number, name in enumerate(ODD_NAMES):
            self.assertEqual('file', listed[name])
            self.assertEqual(b'<?php // %d\n' % number, self.site.read_file('odd/' + name)['data'], name)
            self.assertEqual(b'<?php // in %d\n' % number, self.site.read_file('odd/%s dir/in.php' % name)['data'])
            self.assertEqual(['in.php'], [item['name'] for item in self.site.list_directory('odd/%s dir' % name)])
            backup = self.site.backup_file('odd/' + name)
            self.assertEqual(b'<?php // %d\n' % number, self.read(backup['backup_path']), name)
            self.assertEqual(os.path.join(self.home, '.ai-scanner-backups'),
                             os.path.dirname(os.path.dirname(backup['backup_path'])))
            self.assertTrue(os.path.basename(backup['backup_path']).startswith(name + '.'), name)
            self.site.replace_file('odd/' + name, b'<?php // clean\n')
            self.assertEqual(b'<?php // clean\n', self.read(folder, name), name)
            self.site.rename_file('odd/' + name, 'odd/%s.quarantined.1730000000' % name)
            self.assertEqual(b'<?php // clean\n', self.read(folder, name + '.quarantined.1730000000'), name)
            self.site.rename_file('odd/%s dir/in.php' % name, 'odd/%s dir/%s' % (name, name))
            self.site.delete_file('odd/%s dir/%s' % (name, name))
            self.assertEqual([], os.listdir(os.path.join(folder, name + ' dir')), name)
        for place in (os.getcwd(), self.root, folder, self.home):
            self.assertEqual([], [name for name in os.listdir(place) if name.startswith('secaimark')])

    def test_a_name_with_a_control_character_is_refused_before_any_command(self):
        for path in ('a.php\ntouch secaimark', 'a\tb.php', 'a\x00b.php', 'a\rb.php', 'a/../b.php', '../a.php'):
            self.refused('path_not_allowed', self.site.read_file, path)
            self.refused('path_not_allowed', self.site.list_directory, path)
            self.refused('path_not_allowed', self.site.replace_file, path, b'x')
            self.refused('path_not_allowed', self.site.rename_file, 'index.php', path)
            self.refused('path_not_allowed', self.site.delete_file, path)
            self.refused('path_not_allowed', self.site.backup_file, path)
        for call in (self.site.read_file, self.site.delete_file, self.site.backup_file):
            self.refused('path_not_allowed', call, '')
            self.refused('path_not_allowed', call, '.')
        self.assertEqual([], self.runner.commands)

    def test_listing_shows_folders_and_scannable_files_but_no_links(self):
        items = dict((item['name'], item) for item in self.site.list_directory('.'))
        self.assertEqual(['index.php', 'readme.txt', 'wp-config.php', 'wp-content'], sorted(items))
        self.assertEqual({'name': 'wp-content', 'type': 'directory', 'size': 0, 'permissions': 'rwx'},
                         items['wp-content'])
        self.assertEqual({'name': 'readme.txt', 'type': 'file', 'size': 8, 'permissions': 'rw-'},
                         items['readme.txt'])
        nested = [item['name'] for item in self.site.list_directory('wp-content')]
        self.assertEqual(['my file (1).php', 'plugins'], sorted(nested))
        self.assertEqual(0, self.site.left_out)
        self.assertEqual(sorted(items), sorted(item['name'] for item in self.site.list_directory('')))

    def test_listing_counts_the_entries_it_cannot_name(self):
        # A name may hold anything but a slash: one that looks like more entries adds none.
        write(os.path.join(self.root, 'wp-content', 'odd\nd 0 755 forged.php'), b'')
        write(os.path.join(self.root, 'wp-content', 'tab\there.php'), b'')
        os.mkdir(os.path.join(self.root.encode(), b'wp-content', b'not-text-\xff'))
        write(os.path.join(self.root, 'wp-content', "it's $(odd).php"), b'')
        nested = [item['name'] for item in self.site.list_directory('wp-content')]
        self.assertEqual(["it's $(odd).php", 'my file (1).php', 'plugins'], sorted(nested))
        self.assertEqual(3, self.site.left_out)
        self.site.list_directory('wp-content/plugins')
        self.assertEqual(0, self.site.left_out)

    def test_listing_something_that_is_no_folder_is_refused(self):
        self.refused('not_found', self.site.list_directory, 'index.php')
        self.refused('not_found', self.site.list_directory, 'missing')

    def test_reading_gives_the_bytes_and_their_digests(self):
        found = self.site.read_file('wp-content/plugins/demo/demo.php')
        self.assertEqual(b'<?php // demo\n', found['data'])
        self.assertEqual(14, found['size'])
        self.assertEqual(int(os.stat(os.path.join(self.root, 'wp-content/plugins/demo/demo.php')).st_mtime),
                         found['modified'])
        self.assertEqual(files.text_digests(b'<?php // demo\n'), (found['md5'], found['sha256']))
        self.assertEqual(b'<?php // spaced\n', self.site.read_file('wp-content/my file (1).php')['data'])
        binary = bytes(bytearray(range(256))) * 300
        write(os.path.join(self.root, 'binary.txt'), binary)
        self.assertEqual(binary, self.site.read_file('binary.txt')['data'])
        write(os.path.join(self.root, 'empty.txt'), b'')
        self.assertEqual(b'', self.site.read_file('empty.txt')['data'])

    def test_a_link_that_leaves_the_site_is_refused(self):
        self.refused('path_not_allowed', self.site.read_file, 'link.txt')
        self.refused('path_not_allowed', self.site.read_file, 'linkdir/secret.txt')
        self.refused('path_not_allowed', self.site.list_directory, 'linkdir')

    def test_a_folder_beside_the_site_with_the_same_prefix_is_refused(self):
        self.refused('path_not_allowed', self.site.read_file, '../public_html-old/secret.php')
        self.refused('path_not_allowed', self.site.read_file, 'sibling/secret.php')
        self.refused('path_not_allowed', self.site.list_directory, 'sibling')

    def test_a_folder_that_is_a_link_to_another_folder_of_the_site_is_entered(self):
        os.symlink(os.path.join(self.root, 'wp-content', 'plugins'), os.path.join(self.root, 'addons'))
        self.assertEqual(b'<?php // demo\n', self.site.read_file('addons/demo/demo.php')['data'])
        self.assertEqual(['demo'], [item['name'] for item in self.site.list_directory('addons')])

    def test_a_file_that_is_a_link_is_not_read_even_inside_the_site(self):
        # What it points to is listed and read under its own name.
        self.refused('path_not_allowed', self.site.read_file, 'inner.txt')
        self.assertEqual(b'read me\n', self.site.read_file('readme.txt')['data'])

    def test_only_scannable_kinds_of_file_are_read(self):
        self.refused('type_not_allowed', self.site.read_file, 'image.png')
        self.refused('type_not_allowed', self.site.read_file, 'wp-content')
        self.assertEqual([], self.runner.commands)

    def test_missing_and_special_files_are_refused(self):
        self.refused('not_found', self.site.read_file, 'missing.php')
        self.refused('not_found', self.site.read_file, 'missing/index.php')
        os.mkdir(os.path.join(self.root, 'folder.php'))
        self.refused('not_a_file', self.site.read_file, 'folder.php')
        os.mkfifo(os.path.join(self.root, 'pipe.php'))
        self.refused('not_a_file', self.site.read_file, 'pipe.php')

    def test_a_file_over_the_limit_is_refused_for_reading_and_replacing(self):
        with mock.patch.object(files, 'READ_LIMIT', 8):
            self.assertEqual(b'read me\n', self.site.read_file('readme.txt')['data'])
            self.refused('too_large', self.site.read_file, 'index.php')
            self.refused('too_large', self.site.replace_file, 'index.php', b'<?php\n')
            self.refused('too_large', self.site.replace_file, 'index.php', b'<?php\n', backup=False)
            self.refused('too_large', self.site.replace_file, 'readme.txt', b'123456789')
        self.assertEqual(b'<?php // index\n', self.read(self.root, 'index.php'))

    def test_a_helper_that_fails_is_a_refusal_not_content(self):
        def failing(command, user):
            return False, b'sh: error text\n'

        def broken(command, user):
            raise OSError('no helper')

        def silent(command, user):
            return True, b''

        for runner in (failing, broken, silent, lambda command, user: (True, None)):
            site = SiteFiles('secaiuser', self.home, self.root, runner=runner)
            self.refused('not_found', site.read_file, 'index.php')
            self.refused('not_found', site.list_directory, '')
            self.refused('not_found', site.backup_file, 'index.php')
            self.refused('not_found', site.replace_file, 'index.php', b'x')
            self.refused('not_found', site.rename_file, 'index.php', 'index.php.quarantined.1')
            self.refused('not_found', site.delete_file, 'readme.txt')

    def test_a_read_or_listing_that_ends_badly_gives_nothing(self):
        # The same commands, cut off after they said where they are and what the file is.
        cut = LocalRunner(amend=lambda command: command.replace('\nexec dd ', '\nexit 1\nexec dd ').replace(
            '\nfind . ', '\nfind . -quit\nexit 1\nfind . '))
        site = SiteFiles('secaiuser', self.home, self.root, runner=cut)
        self.refused('failed', site.read_file, 'index.php')
        self.refused('failed', site.list_directory, '')
        # And a read that was cut short while the command claims success.
        short = LocalRunner(honest=False, amend=lambda command: command.replace('count=$((L+1))', 'count=3'))
        self.refused('failed', SiteFiles('secaiuser', self.home, self.root, runner=short).read_file, 'index.php')


class PlaceTests(SiteTree):
    """A command checks where it is and works there; what it printed decides what the panel takes."""

    def scripted(self, output, succeeded=True):
        return SiteFiles('secaiuser', self.home, self.root, runner=lambda command, user: (succeeded, output))

    def test_output_from_a_folder_outside_the_site_is_not_taken(self):
        described = b'81a4 8 1730000000\n'
        for home, root, folder in (
                (self.home, self.root, self.outside),
                (self.home, self.root, self.home),
                (self.home, self.root, self.root + '-old'),
                (self.home, self.outside, self.outside),
                (self.home, self.home + '-other/public_html', self.home + '-other/public_html'),
                ('/', '/etc', '/etc'),
                (self.home, self.root, 'relative'),
                (self.home, 'relative', 'relative'),
        ):
            header = b''.join(part.encode() + b'\0' for part in (home, root, folder))
            site = self.scripted(header + described + b'secret content')
            self.refused('path_not_allowed', site.read_file, 'index.php')
            self.refused('path_not_allowed', self.scripted(header + b'f 8 644 secret.php/').list_directory, '')
            self.refused('path_not_allowed', site.backup_file, 'index.php')
            self.refused('path_not_allowed', site.replace_file, 'index.php', b'x', backup=False)
            self.refused('path_not_allowed', site.rename_file, 'index.php', 'index.php.q', backup=False)
        self.refused('path_not_allowed', self.scripted(b'\xff\0\xff\0\xff\0' + described).read_file, 'index.php')
        for incomplete in (b'', b'/a', b'/a\0/a', b'/a\0/a\0/a'):
            self.refused('not_found', self.scripted(incomplete).read_file, 'index.php')
        # The same output from inside the site is taken.
        header = b''.join(part.encode() + b'\0' for part in (self.home, self.root, self.root + '/wp-content'))
        self.assertEqual(b'12345678', self.scripted(header + described + b'12345678').read_file('a.php')['data'])

    def test_a_folder_that_is_a_link_out_of_the_site_gives_no_content_and_takes_no_write(self):
        write(os.path.join(self.outside, 'access.log'), b'outside log\n')
        write(os.path.join(self.outside, 'other.php'), b'<?php // outside\n')
        os.symlink(self.outside, os.path.join(self.root, 'wp-content', 'logs'))
        for path in ('wp-content/logs/access.log', 'wp-content/logs/other.php'):
            self.refused('path_not_allowed', self.site.read_file, path)
            self.refused('path_not_allowed', self.site.backup_file, path)
            self.refused('path_not_allowed', self.site.replace_file, path, b'changed\n')
            self.refused('path_not_allowed', self.site.replace_file, path, b'changed\n', backup=False)
            self.refused('path_not_allowed', self.site.rename_file, path, path + '.quarantined.1')
            self.refused('path_not_allowed', self.site.rename_file, path, path + '.quarantined.1', backup=False)
            self.refused('path_not_allowed', self.site.delete_file, path)
        self.refused('path_not_allowed', self.site.list_directory, 'wp-content/logs')
        self.assertEqual(['access.log', 'other.php', 'secret.txt', 'target.php'], sorted(os.listdir(self.outside)))
        self.assertEqual(b'outside log\n', self.read(self.outside, 'access.log'))
        self.assertEqual(b'<?php // outside\n', self.read(self.outside, 'other.php'))
        self.assertEqual([], self.backups())
        # A command that claims success changes nothing about that.
        lying = SiteFiles('secaiuser', self.home, self.root, runner=LocalRunner(honest=False),
                          temp_writer=self.temp_writer)
        self.refused('path_not_allowed', lying.read_file, 'wp-content/logs/access.log')
        self.refused('path_not_allowed', lying.replace_file, 'wp-content/logs/other.php', b'changed\n', backup=False)
        self.refused('path_not_allowed', lying.rename_file, 'wp-content/logs/other.php',
                     'wp-content/logs/other.php.quarantined.1', backup=False)
        self.refused('path_not_allowed', lying.delete_file, 'wp-content/logs/other.php')
        self.assertEqual(b'<?php // outside\n', self.read(self.outside, 'other.php'))
        self.assertEqual(['access.log', 'other.php', 'secret.txt', 'target.php'], sorted(os.listdir(self.outside)))

    def test_a_site_directory_that_is_a_link_out_of_the_home_is_refused(self):
        os.rename(self.root, self.root + '-real')
        os.symlink(self.outside, self.root)
        self.refused('path_not_allowed', self.site.read_file, 'secret.txt')
        self.refused('path_not_allowed', self.site.list_directory, '')
        self.refused('path_not_allowed', self.site.replace_file, 'target.php', b'changed\n', backup=False)
        self.refused('path_not_allowed', self.site.delete_file, 'target.php')
        self.assertEqual(b'<?php // outside\n', self.read(self.outside, 'target.php'))

    def swap(self, folder):
        """Replace a folder of the site by a link to the place outside it."""
        os.rename(folder, folder + '.moved')
        os.symlink(self.outside, folder)

    def test_a_folder_swapped_for_a_link_before_the_command_runs_is_refused(self):
        folder = os.path.join(self.root, 'wp-content')
        write(os.path.join(self.outside, 'my file (1).php'), b'<?php // outside\n')
        swapping = LocalRunner(before=lambda: os.path.islink(folder) or self.swap(folder))
        site = SiteFiles('secaiuser', self.home, self.root, runner=swapping, temp_writer=self.temp_writer)
        self.refused('path_not_allowed', site.read_file, 'wp-content/my file (1).php')
        self.refused('path_not_allowed', site.replace_file, 'wp-content/my file (1).php', b'changed\n', backup=False)
        self.refused('path_not_allowed', site.delete_file, 'wp-content/my file (1).php')
        self.assertEqual(b'<?php // outside\n', self.read(self.outside, 'my file (1).php'))

    def test_a_folder_swapped_for_a_link_in_the_middle_of_a_command_changes_nothing(self):
        # The swap happens right after the command has checked where it is. It keeps
        # working in the folder it entered, which is the site's own, never in the link's.
        folder = os.path.join(self.root, 'wp-content')
        write(os.path.join(self.outside, 'my file (1).php'), b'<?php // outside\n')
        checked = 'i "$r" "$h";i "$d" "$r"\n'
        swap = 'mv %s %s && ln -s %s %s\n' % tuple(shlex.quote(word) for word in (
            folder, folder + '.moved', self.outside, folder))

        def amend(command):
            if checked not in command:
                return command
            if os.path.islink(folder):
                os.remove(folder)
                os.rename(folder + '.moved', folder)
            return command.replace(checked, checked + swap)

        site = SiteFiles('secaiuser', self.home, self.root, runner=LocalRunner(amend=amend),
                         temp_writer=self.temp_writer)
        self.assertEqual(b'<?php // spaced\n', site.read_file('wp-content/my file (1).php')['data'])
        self.assertTrue(os.path.islink(folder))
        site.replace_file('wp-content/my file (1).php', b'<?php // clean\n')
        self.assertEqual(b'<?php // clean\n', self.read(folder + '.moved', 'my file (1).php'))
        self.assertEqual(['my file (1).php', 'plugins'],
                         sorted(item['name'] for item in site.list_directory('wp-content')))
        site.rename_file('wp-content/my file (1).php', 'wp-content/my file (1).php.quarantined.1')
        self.assertEqual(['my file (1).php.quarantined.1', 'plugins'], sorted(os.listdir(folder + '.moved')))
        self.assertEqual(7, len([command for command, user in site.runner.commands if checked in command]))
        self.assertEqual(['my file (1).php', 'secret.txt', 'target.php'], sorted(os.listdir(self.outside)))
        self.assertEqual(b'<?php // outside\n', self.read(self.outside, 'my file (1).php'))

    def test_every_command_is_fixed_text_after_quoted_words_and_runs_as_the_website_user(self):
        self.site.list_directory('wp-content')
        self.site.read_file('wp-content/my file (1).php')
        self.site.replace_file('wp-content/my file (1).php', b'<?php // new\n',
                               verify_sha256=files.text_digests(b'<?php // spaced\n')[1])
        self.site.rename_file('wp-content/my file (1).php', "wp-content/it's (1).php.quarantined.1")
        self.site.delete_file('readme.txt')
        fixed = {files.LIST: 0, files.READ: 0, files.BACKUP: 0, files.BACKUP_FOLDER: 0, files.REPLACE: 0,
                 files.RENAME: 0, files.DELETE: 0}
        for command, user in self.runner.commands:
            self.assertEqual('secaiuser', user)
            words, script = command.split('\n', 1)
            fixed[script] += 1
            assigned = shlex.split(words)
            self.assertEqual(words, ' '.join(
                '%s=%s' % (word[0], shlex.quote(word[2:])) for word in assigned))
            for word in assigned:
                self.assertRegex(word[:2], '^[A-Z]=$')
            given = dict((word[0], word[2:]) for word in assigned)
            self.assertEqual(self.home, given['H'])
            if script != files.BACKUP_FOLDER:
                self.assertEqual('./public_html', given['R'])
                self.assertIn(given['D'], ('.', './wp-content'))
            for name in ('N', 'M'):
                if name in given:
                    self.assertRegex(given[name], r'^\./[^/]+$')
        self.assertEqual({files.LIST: 1, files.READ: 2, files.BACKUP: 4, files.BACKUP_FOLDER: 1, files.REPLACE: 1,
                          files.RENAME: 1, files.DELETE: 1}, fixed)
        for script in fixed:
            # Nothing in the fixed text is quoted with single quotes, run a second time or
            # filled in later, and a word of the request is only used inside double quotes,
            # in an assignment or as a number.
            self.assertNotIn("'", script)
            self.assertNotIn('`', script)
            self.assertNotIn('eval', script)
            self.assertNotIn('%(', script)
            bare = re.sub(r'"[^"]*"', '""', script)
            for use in re.findall(r'[^\s(|;&]*\$[HRDNMSTXZL]\b[^\s;&|)]*', bare):
                self.assertRegex(use, r'^([bk]=[$\w./-]+|count=\$)$', script)

    def test_a_command_too_long_for_the_helper_is_refused_and_not_run(self):
        deep = '/'.join(['d' * 60] * 5)
        write(os.path.join(self.root, deep, 'a.php'), b'<?php\n')
        self.assertEqual(b'<?php\n', self.site.read_file(deep + '/a.php')['data'])
        self.refused('path_too_long', self.site.backup_file, deep + '/a.php')
        self.refused('path_too_long', self.site.replace_file, deep + '/a.php', b'x')
        self.refused('path_too_long', self.site.delete_file, deep + '/a.php')
        self.assertEqual(1, len(self.runner.commands))
        self.assertEqual(b'<?php\n', self.read(self.root, deep, 'a.php'))
        self.refused('path_not_allowed', self.site.read_file, 'a/' * 400 + 'b.php')
        # What is refused is what the helper would not take, for this account and this home.
        for command, user in self.runner.commands:
            self.assertTrue(files.commandStatus.request_fits(user, command))
        sent = []
        longest = SiteFiles('secaiuser', '/home/example.com', '/home/example.com/public_html',
                            runner=lambda command, user: sent.append(command) or (True, b''))
        room = 0
        while True:
            try:
                longest._output(files.REPLACE, R='./public_html', D='./' + 'p' * room, N='./a.php',
                                S='/usr/local/CyberCP/tmp/' + 'a' * 32, Z=str(files.READ_LIMIT),
                                L=str(files.READ_LIMIT))
            except Refused as refusal:
                self.assertEqual('path_too_long', refusal.code)
                break
            room += 1
        self.assertEqual(room, len(sent))
        # The longest command still leaves this much for the folder of a file in an ordinary site.
        self.assertGreater(room, 250)
        self.assertLess(room, files.MAX_PATH_LENGTH)


class ChangeTests(SiteTree):

    def test_replacing_keeps_the_file_and_its_mode_and_backs_it_up_outside_the_site(self):
        target = os.path.join(self.root, 'wp-content', 'plugins', 'demo', 'demo.php')
        before = os.stat(target)
        replaced = self.site.replace_file('wp-content/plugins/demo/demo.php', b'<?php // clean\n')
        after = os.stat(target)
        self.assertEqual(b'<?php // clean\n', self.read(target))
        self.assertEqual((before.st_ino, stat.S_IMODE(before.st_mode)), (after.st_ino, stat.S_IMODE(after.st_mode)))
        self.assertEqual(15, replaced['bytes_written'])
        self.assertEqual(files.text_digests(b'<?php // clean\n'), (replaced['md5'], replaced['sha256']))
        self.assertEqual([replaced['backup_path']], self.backups())
        self.assertEqual(b'<?php // demo\n', self.read(replaced['backup_path']))
        self.assertTrue(replaced['backup_path'].startswith(os.path.join(self.home, '.ai-scanner-backups') + os.sep))
        self.assertFalse(replaced['backup_path'].startswith(self.root + os.sep))
        for folder in (os.path.join(self.home, '.ai-scanner-backups'), os.path.dirname(replaced['backup_path'])):
            self.assertEqual(0o700, stat.S_IMODE(os.stat(folder).st_mode))
        self.assertEqual([], os.listdir(self.temp))

    def test_backup_folders_that_exist_are_used_and_made_private_again(self):
        today = os.path.join(self.home, '.ai-scanner-backups', time.strftime('%Y-%m-%d'))
        os.makedirs(today)
        self.site.backup_file('readme.txt')
        os.chmod(os.path.join(self.home, '.ai-scanner-backups'), 0o755)
        os.rmdir(today) if not os.listdir(today) else None
        shutil.rmtree(today)
        backup = self.site.backup_file('readme.txt')
        self.assertEqual(b'read me\n', self.read(backup['backup_path']))
        for folder in (os.path.join(self.home, '.ai-scanner-backups'), today):
            self.assertEqual(0o700, stat.S_IMODE(os.stat(folder).st_mode))
        # Two backups of one file in one second get two names.
        self.assertNotEqual(self.site.backup_file('readme.txt')['backup_path'],
                            self.site.backup_file('readme.txt')['backup_path'])

    def test_replacing_checks_the_expected_content_first(self):
        refusal = self.refused('hash_mismatch', self.site.replace_file, 'readme.txt', b'new\n',
                               verify_sha256='0' * 64)
        self.assertEqual(files.text_digests(b'read me\n')[1], refusal.details['actual'])
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.site.replace_file('readme.txt', b'new\n', backup=False,
                               verify_sha256=files.text_digests(b'read me\n')[1])
        self.assertEqual(b'new\n', self.read(self.root, 'readme.txt'))
        self.assertEqual([], self.backups())

    def test_a_link_is_never_written_through_renamed_or_deleted(self):
        self.refused('path_not_allowed', self.site.replace_file, 'evil.php', b'<?php // changed\n')
        self.refused('path_not_allowed', self.site.replace_file, 'evil.php', b'<?php // changed\n', backup=False)
        self.refused('path_not_allowed', self.site.rename_file, 'evil.php', 'evil.php.quarantined.1')
        self.refused('path_not_allowed', self.site.rename_file, 'evil.php', 'evil.php.quarantined.1', backup=False)
        self.refused('path_not_allowed', self.site.delete_file, 'evil.php')
        self.refused('path_not_allowed', self.site.backup_file, 'evil.php')
        self.refused('path_not_allowed', self.site.replace_file, 'linkdir/target.php', b'<?php // changed\n')
        self.assertEqual(b'<?php // outside\n', self.read(self.outside, 'target.php'))
        self.assertTrue(os.path.islink(os.path.join(self.root, 'evil.php')))
        self.assertEqual([], self.backups())

    def test_replacing_never_creates_a_file(self):
        self.refused('not_found', self.site.replace_file, 'wp-content/new.php', b'<?php\n')
        self.refused('not_found', self.site.replace_file, 'wp-content/new.php', b'<?php\n', backup=False)
        self.assertFalse(os.path.exists(os.path.join(self.root, 'wp-content', 'new.php')))
        self.assertEqual([], os.listdir(self.temp))

    def test_files_that_configure_the_site_are_never_changed(self):
        write(os.path.join(self.root, '.htaccess'), b'deny\n')
        write(os.path.join(self.root, 'wp-content', '.user.ini'), b'a=b\n')
        write(os.path.join(self.root, 'php.ini'), b'a=b\n')
        for name in ('wp-config.php', '.htaccess', 'wp-content/.user.ini', 'php.ini', 'WP-Config.PHP'):
            self.refused('protected_file', self.site.replace_file, name, b'changed\n')
            self.refused('protected_file', self.site.rename_file, name, name + '.quarantined.1')
            self.refused('protected_file', self.site.delete_file, name)
        for name in ('.htaccess', 'wp-content/.user.ini', 'wp-content/php.ini', 'wp-content/WP-Config.php'):
            self.refused('protected_file', self.site.rename_file, 'readme.txt', name)
        self.refused('protected_file', self.site.delete_file, 'index.php')
        self.assertEqual([], self.runner.commands)

    def test_only_scannable_kinds_of_file_are_changed(self):
        self.refused('type_not_allowed', self.site.replace_file, 'image.png', b'x')
        self.refused('type_not_allowed', self.site.rename_file, 'image.png', 'image.php')
        self.refused('type_not_allowed', self.site.delete_file, 'image.png')
        self.refused('type_not_allowed', self.site.backup_file, 'image.png')
        self.assertEqual([], self.runner.commands)

    def test_the_configuration_file_can_be_backed_up_because_the_copy_is_private(self):
        backup = self.site.backup_file('wp-config.php')
        self.assertEqual(b'<?php // secrets\n', self.read(backup['backup_path']))
        self.assertEqual(17, backup['size'])
        self.assertFalse(backup['backup_path'].startswith(self.root + os.sep))

    def test_renaming_moves_the_file_to_a_free_name_in_its_folder(self):
        renamed = self.site.rename_file('wp-content/plugins/demo/demo.php',
                                        'wp-content/plugins/demo/demo.php.quarantined.1730000000')
        self.assertEqual(['demo.php.quarantined.1730000000'],
                         os.listdir(os.path.join(self.root, 'wp-content', 'plugins', 'demo')))
        self.assertEqual(b'<?php // demo\n', self.read(
            self.root, 'wp-content', 'plugins', 'demo', 'demo.php.quarantined.1730000000'))
        self.assertEqual(b'<?php // demo\n', self.read(renamed['backup_path']))
        self.assertEqual({'backup_path': None}, self.site.rename_file('readme.txt', '/readme.txt.old/', backup=False))
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt.old'))

    def test_renaming_into_another_folder_is_refused(self):
        os.mkdir(os.path.join(self.root, 'wp-content', 'uploads'))
        for new in ('wp-content/readme.txt', 'wp-content/uploads/readme.txt', 'linkdir/readme.txt',
                    'missing/readme.txt', 'sibling/readme.txt'):
            self.refused('other_directory', self.site.rename_file, 'readme.txt', new)
        self.refused('other_directory', self.site.rename_file, 'wp-content/my file (1).php', 'my file (1).php')
        self.refused('other_directory', self.site.rename_file, 'wp-content/my file (1).php',
                     'wp-content/plugins/my file (1).php')
        self.refused('path_not_allowed', self.site.rename_file, 'readme.txt', '../readme.txt')
        self.refused('path_not_allowed', self.site.rename_file, 'readme.txt', '')
        self.assertEqual([], self.runner.commands)
        self.assertEqual([], self.backups())

    def test_renaming_onto_a_name_that_is_taken_is_refused(self):
        os.mkdir(os.path.join(self.root, 'folder'))
        os.symlink('/nonexistent', os.path.join(self.root, 'dangling'))
        for taken in ('index.php', 'link.txt', 'folder', 'dangling', 'readme.txt'):
            refusal = self.refused('exists', self.site.rename_file, 'readme.txt', taken, backup=False)
            self.assertEqual(None, refusal.details['backup_path'])
        refusal = self.refused('exists', self.site.rename_file, 'readme.txt', 'index.php')
        self.assertEqual(b'read me\n', self.read(refusal.details['backup_path']))
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertEqual(b'<?php // index\n', self.read(self.root, 'index.php'))
        self.assertEqual(['secret.txt', 'target.php'], sorted(os.listdir(self.outside)))

    def test_deleting_keeps_a_copy_first(self):
        deleted = self.site.delete_file('wp-content/my file (1).php')
        self.assertFalse(os.path.exists(os.path.join(self.root, 'wp-content', 'my file (1).php')))
        self.assertEqual(b'<?php // spaced\n', self.read(deleted['backup_path']))
        self.assertEqual(16, deleted['size'])
        self.assertEqual(hashlib.sha256(b'<?php // spaced\n').hexdigest(), deleted['sha256'])

    def test_a_backup_folder_that_is_a_link_is_refused(self):
        exposed = os.path.join(self.root, 'exposed')
        os.makedirs(exposed)
        os.symlink(exposed, os.path.join(self.home, '.ai-scanner-backups'))
        self.refused('backup_dir_failed', self.site.backup_file, 'readme.txt')
        self.refused('backup_dir_failed', self.site.replace_file, 'readme.txt', b'new\n')
        self.refused('backup_dir_failed', self.site.rename_file, 'readme.txt', 'readme.txt.quarantined.1')
        self.refused('backup_dir_failed', self.site.delete_file, 'readme.txt')
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertEqual([], os.listdir(exposed))
        # The same when only the folder of the day is a link, or a file is in the way.
        os.remove(os.path.join(self.home, '.ai-scanner-backups'))
        os.mkdir(os.path.join(self.home, '.ai-scanner-backups'))
        today = os.path.join(self.home, '.ai-scanner-backups', time.strftime('%Y-%m-%d'))
        os.symlink(exposed, today)
        self.refused('backup_dir_failed', self.site.delete_file, 'readme.txt')
        os.remove(today)
        write(today, b'')
        self.refused('backup_dir_failed', self.site.delete_file, 'readme.txt')
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertEqual([], os.listdir(exposed))

    def test_a_file_of_any_size_is_backed_up_renamed_and_deleted_on_the_server(self):
        big = b'0123456789abcdef' * 4096
        write(os.path.join(self.root, 'big.sql'), big)
        write(os.path.join(self.root, 'large.log'), big)
        with mock.patch.object(files, 'READ_LIMIT', 1024):
            self.refused('too_large', self.site.read_file, 'big.sql')
            self.refused('too_large', self.site.replace_file, 'big.sql', b'small\n')
            backup = self.site.backup_file('big.sql')
            self.assertEqual((len(big), big), (backup['size'], self.read(backup['backup_path'])))
            renamed = self.site.rename_file('big.sql', 'big.sql.quarantined.1')
            self.assertEqual(big, self.read(self.root, 'big.sql.quarantined.1'))
            self.assertEqual(big, self.read(renamed['backup_path']))
            deleted = self.site.delete_file('large.log')
            self.assertEqual((len(big), hashlib.sha256(big).hexdigest()), (deleted['size'], deleted['sha256']))
            self.assertEqual(big, self.read(deleted['backup_path']))
        self.assertEqual(['big.sql.quarantined.1'],
                         [name for name in os.listdir(self.root) if name.startswith(('big', 'large'))])


class OddHomeTests(unittest.TestCase):

    def test_a_home_with_a_backslash_and_a_space_in_its_name_is_worked_in(self):
        base = os.path.realpath(tempfile.mkdtemp(prefix='secai'))
        self.addCleanup(shutil.rmtree, base, True)
        home = os.path.join(base, 'home', 'secai\\n \\c.test')
        root = os.path.join(home, 'public html')
        temp = os.path.join(base, 'tmp')
        os.makedirs(temp)
        write(os.path.join(root, 'sub dir', 'a.php'), b'<?php // a\n')

        def temp_writer(content):
            path = os.path.join(temp, secrets.token_hex(8))
            with open(path, 'wb') as handle:
                handle.write(content)
            return path

        site = SiteFiles('secaiuser', home, root, runner=LocalRunner(), temp_writer=temp_writer)
        self.assertEqual(['sub dir'], [item['name'] for item in site.list_directory('')])
        self.assertEqual(b'<?php // a\n', site.read_file('sub dir/a.php')['data'])
        replaced = site.replace_file('sub dir/a.php', b'<?php // b\n')
        self.assertEqual(os.path.join(home, '.ai-scanner-backups'),
                         os.path.dirname(os.path.dirname(replaced['backup_path'])))
        with open(replaced['backup_path'], 'rb') as handle:
            self.assertEqual(b'<?php // a\n', handle.read())
        site.rename_file('sub dir/a.php', 'sub dir/a.php.quarantined.1')
        self.assertEqual(['a.php.quarantined.1'], os.listdir(os.path.join(root, 'sub dir')))
        # A site directory that is the home itself is worked in too; one outside it is not.
        whole = SiteFiles('secaiuser', home, home, runner=LocalRunner(), temp_writer=temp_writer)
        self.assertEqual(['public html'], [item['name'] for item in whole.list_directory('')])
        other = SiteFiles('secaiuser', home, base, runner=LocalRunner(), temp_writer=temp_writer)
        with self.assertRaises(Refused) as caught:
            other.list_directory('')
        self.assertEqual('path_not_allowed', caught.exception.code)


class UntrustedStatusTests(SiteTree):
    """Every operation against a runner that says each command succeeded, as the helper's last byte did."""

    def setUp(self):
        SiteTree.setUp(self)
        self.runner = LocalRunner(honest=False)
        self.site = SiteFiles('secaiuser', self.home, self.root, runner=self.runner,
                              temp_writer=self.temp_writer)

    def test_a_missing_file_is_missing_for_every_operation(self):
        for path in ('missing.php', 'wp-content/missing.php', 'missing/other.php'):
            self.refused('not_found', self.site.read_file, path)
            self.refused('not_found', self.site.backup_file, path)
            self.refused('not_found', self.site.replace_file, path, b'x')
            self.refused('not_found', self.site.replace_file, path, b'x', backup=False)
            self.refused('not_found', self.site.rename_file, path, path + '.quarantined.1')
            self.refused('not_found', self.site.rename_file, path, path + '.quarantined.1', backup=False)
            self.refused('not_found', self.site.delete_file, path)
        self.refused('not_found', self.site.list_directory, 'missing')
        self.assertEqual([], self.backups())
        self.assertFalse(os.path.exists(os.path.join(self.home, '.ai-scanner-backups')))
        self.assertEqual([], os.listdir(self.temp))

    def test_a_missing_backup_folder_is_made_and_every_operation_works(self):
        self.assertFalse(os.path.exists(os.path.join(self.home, '.ai-scanner-backups')))
        backup = self.site.backup_file('readme.txt')
        self.assertEqual(b'read me\n', self.read(backup['backup_path']))
        replaced = self.site.replace_file('readme.txt', b'new\n')
        self.assertEqual((b'new\n', b'read me\n'),
                         (self.read(self.root, 'readme.txt'), self.read(replaced['backup_path'])))
        renamed = self.site.rename_file('readme.txt', 'readme.txt.quarantined.1')
        self.assertEqual((b'new\n', b'new\n'), (self.read(self.root, 'readme.txt.quarantined.1'),
                                                 self.read(renamed['backup_path'])))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'readme.txt')))
        deleted = self.site.delete_file('wp-content/my file (1).php')
        self.assertEqual(b'<?php // spaced\n', self.read(deleted['backup_path']))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'wp-content', 'my file (1).php')))
        self.assertEqual(['index.php', 'wp-config.php', 'wp-content'],
                         sorted(item['name'] for item in self.site.list_directory('')))
        self.assertEqual(b'<?php // index\n', self.site.read_file('index.php')['data'])

    def test_a_backup_folder_that_cannot_be_made_stops_every_change(self):
        write(os.path.join(self.home, '.ai-scanner-backups'), b'a file in the way\n')
        self.refused('backup_dir_failed', self.site.backup_file, 'readme.txt')
        self.refused('backup_dir_failed', self.site.replace_file, 'readme.txt', b'new\n')
        self.refused('backup_dir_failed', self.site.rename_file, 'readme.txt', 'readme.txt.quarantined.1')
        self.refused('backup_dir_failed', self.site.delete_file, 'readme.txt')
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertEqual([], os.listdir(self.temp))

    def test_a_copy_that_was_cut_short_is_no_backup_and_the_file_stays(self):
        # No file may grow past 512 bytes while these commands run: the copy stops there.
        content = b'<?php // long\n' + b'x' * 3000
        write(os.path.join(self.root, 'long.php'), content)
        self.runner.prefix = 'ulimit -f 1\n'
        self.refused('backup_failed', self.site.backup_file, 'long.php')
        self.refused('backup_failed', self.site.replace_file, 'long.php', b'new\n')
        self.refused('backup_failed', self.site.rename_file, 'long.php', 'long.php.quarantined.1')
        self.refused('backup_failed', self.site.delete_file, 'long.php')
        self.assertEqual(content, self.read(self.root, 'long.php'))
        self.assertEqual(['long.php'], [name for name in os.listdir(self.root) if name.startswith('long')])
        # The piece that was copied is not left behind as if it were a backup.
        self.assertEqual([], self.backups())
        self.assertEqual([], os.listdir(self.temp))
        self.runner.prefix = ''
        self.assertEqual(content, self.read(self.site.backup_file('long.php')['backup_path']))

    def test_a_backup_is_taken_only_when_the_command_itself_reports_the_size_of_the_file(self):
        header = b''.join(part.encode() + b'\0' for part in (self.home, self.root, self.root))
        folder = '%s/.ai-scanner-backups/%s\n' % (self.home, time.strftime('%Y-%m-%d'))
        for printed, code in (
                (b'81a4 3000 1730000000\n' + folder.encode() + b'3000\n', None),
                (b'81a4 3000 1730000000\n' + folder.encode() + b'512\n', 'backup_failed'),
                (b'81a4 3000 1730000000\n' + folder.encode() + b'30000\n', 'backup_failed'),
                (b'81a4 3000 1730000000\n' + folder.encode(), 'backup_failed'),
                (b'81a4 3000 1730000000\n' + folder.encode() + b'3000', 'backup_failed'),
                (b'81a4 3000 1730000000\n' + folder.encode() + b'3000\n3000\n', 'backup_failed'),
                (b'81a4 3000 1730000000\n', 'backup_dir_failed'),
                (b'81a4 3000 1730000000\n' + self.outside.encode() + b'\n3000\n', 'backup_dir_failed'),
                (b'81a4 3000 1730000000\n3000\n', 'backup_dir_failed'),
                (b'41ed 3000 1730000000\n' + folder.encode() + b'3000\n', 'not_a_file'),
                (b'a1ff 3000 1730000000\n' + folder.encode() + b'3000\n', 'path_not_allowed'),
                (b'', 'not_found'),
                (b'what is this\n', 'failed'),
        ):
            site = SiteFiles('secaiuser', self.home, self.root, runner=lambda command, user: (True, header + printed))
            if code is None:
                self.assertEqual(3000, site.backup_file('long.php')['size'])
            else:
                self.refused(code, site.backup_file, 'long.php')

    def test_a_file_that_changed_size_after_its_backup_is_left_alone(self):
        target = os.path.join(self.root, 'readme.txt')

        def grow():
            if self.runner.commands[-1][0].endswith((files.REPLACE, files.RENAME, files.DELETE)):
                with open(target, 'ab') as handle:
                    handle.write(b'more\n')

        self.runner.before = grow
        for call, arguments in ((self.site.replace_file, ('readme.txt', b'new\n')),
                                (self.site.rename_file, ('readme.txt', 'readme.txt.quarantined.1')),
                                (self.site.delete_file, ('readme.txt',))):
            before = self.read(target)
            refusal = self.refused('changed', call, *arguments)
            self.assertEqual(before, self.read(refusal.details['backup_path']))
            self.assertEqual(before + b'more\n', self.read(target))
        self.assertEqual([], os.listdir(self.temp))

    def test_replacing_does_not_wait_for_a_pipe_put_in_the_place_of_the_file(self):
        # The file becomes a pipe that nobody reads, right after the command looked at it.
        looked = 'case $1 in 8???);;*)exit 5;;esac\n'
        waited = []

        def runner(command, user):
            command = command.replace(looked, looked + 'rm -f -- "$N";mkfifo -- "$N"\n')
            process = subprocess.Popen(['sh', '-c', command], stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                return True, process.communicate(timeout=8)[0]
            except subprocess.TimeoutExpired:
                waited.append(command)
                process.kill()
                subprocess.call(['pkill', '-f', 'of=./readme.txt'])
                return True, process.communicate()[0]

        site = SiteFiles('secaiuser', self.home, self.root, runner=runner, temp_writer=self.temp_writer)
        self.refused('replace_failed', site.replace_file, 'readme.txt', b'new\n', backup=False)
        self.assertEqual([], waited)
        self.assertTrue(stat.S_ISFIFO(os.lstat(os.path.join(self.root, 'readme.txt')).st_mode))
        self.assertEqual([], os.listdir(self.temp))

    def test_a_change_that_did_not_happen_is_not_reported_as_done(self):
        target = os.path.join(self.root, 'readme.txt')
        os.chmod(self.root, 0o555)
        self.addCleanup(os.chmod, self.root, 0o755)
        skip = lambda command: command.replace('\nmv -n -T ', '\n: ').replace('\nrm -f ', '\n: ').replace(
            '\ndd oflag=nofollow', '\n: ')
        self.runner.amend = skip
        refusal = self.refused('replace_failed', self.site.replace_file, 'readme.txt', b'new\n')
        self.assertEqual(b'read me\n', self.read(refusal.details['backup_path']))
        self.refused('rename_failed', self.site.rename_file, 'readme.txt', 'readme.txt.quarantined.1')
        self.refused('delete_failed', self.site.delete_file, 'readme.txt')
        self.assertEqual(b'read me\n', self.read(target))
        self.assertEqual([], os.listdir(self.temp))


if __name__ == '__main__':
    unittest.main()
