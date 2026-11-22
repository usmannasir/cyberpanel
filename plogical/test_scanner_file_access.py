"""The AI Scanner works on a website's files as that website's user and only inside the site."""
import os
import secrets
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest

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
    """Runs each command with a shell, as the root helper does, and keeps what was asked."""

    def __init__(self):
        self.commands = []

    def __call__(self, command, user):
        self.commands.append((command, user))
        process = subprocess.Popen(['sh', '-c', command], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = process.communicate()[0]
        return process.returncode == 0, output


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
            self.site.replace_file('odd/' + name, b'<?php // clean\n')
            self.assertEqual(b'<?php // clean\n', self.read(folder, name), name)
            self.site.rename_file('odd/' + name, 'odd/%s.quarantined.1730000000' % name)
            self.assertEqual(b'<?php // clean\n', self.read(folder, name + '.quarantined.1730000000'), name)
            self.site.rename_file('odd/%s dir/in.php' % name, 'odd/%s dir/%s' % (name, name))
            self.site.delete_file('odd/%s dir/%s' % (name, name))
            self.assertEqual([], os.listdir(os.path.join(folder, name + ' dir')), name)
        self.assertEqual([], [name for name in os.listdir(os.getcwd()) if name.startswith('secaimark')])
        self.assertEqual([], [name for name in os.listdir(self.root) if name.startswith('secaimark')])
        self.assertEqual([], [name for name in os.listdir(folder) if name.startswith('secaimark')])

    def test_a_name_with_a_control_character_is_refused_before_any_command(self):
        for path in ('a.php\ntouch secaimark', 'a\tb.php', 'a\x00b.php', 'a\rb.php', 'a/../b.php', '../a.php'):
            self.refused('path_not_allowed', self.site.read_file, path)
            self.refused('path_not_allowed', self.site.list_directory, path)
            self.refused('path_not_allowed', self.site.replace_file, path, b'x')
            self.refused('path_not_allowed', self.site.rename_file, 'index.php', path)
            self.refused('path_not_allowed', self.site.delete_file, path)
            self.refused('path_not_allowed', self.site.backup_file, path)
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
        self.assertEqual(files.text_digests(b'<?php // demo\n'), (found['md5'], found['sha256']))
        self.assertEqual(b'<?php // spaced\n', self.site.read_file('wp-content/my file (1).php')['data'])

    def test_a_link_that_leaves_the_site_is_refused(self):
        self.refused('path_not_allowed', self.site.read_file, 'link.txt')
        self.refused('path_not_allowed', self.site.read_file, 'linkdir/secret.txt')
        self.refused('path_not_allowed', self.site.list_directory, 'linkdir')

    def test_a_folder_beside_the_site_with_the_same_prefix_is_refused(self):
        self.refused('path_not_allowed', self.site.read_file, '../public_html-old/secret.php')
        self.refused('path_not_allowed', self.site.read_file, 'sibling/secret.php')
        self.refused('path_not_allowed', self.site.list_directory, 'sibling')

    def test_a_link_that_stays_inside_the_site_is_read(self):
        self.assertEqual(b'read me\n', self.site.read_file('inner.txt')['data'])

    def test_only_scannable_kinds_of_file_are_read(self):
        self.refused('type_not_allowed', self.site.read_file, 'image.png')
        os.symlink(os.path.join(self.root, 'image.png'), os.path.join(self.root, 'picture.txt'))
        self.refused('type_not_allowed', self.site.read_file, 'picture.txt')

    def test_missing_and_special_files_are_refused(self):
        self.refused('not_found', self.site.read_file, 'missing.php')
        os.mkdir(os.path.join(self.root, 'folder.php'))
        self.refused('not_a_file', self.site.read_file, 'folder.php')
        self.refused('type_not_allowed', self.site.read_file, 'wp-content')
        os.mkfifo(os.path.join(self.root, 'pipe.php'))
        self.refused('not_a_file', self.site.read_file, 'pipe.php')

    def test_a_file_over_the_limit_is_refused(self):
        self.refused('too_large', self.site._regular_file, os.path.join(self.root, 'readme.txt'), 4)
        self.refused('too_large', self.site._content, os.path.join(self.root, 'readme.txt'), 4)
        self.assertEqual(b'read me\n', self.site._content(os.path.join(self.root, 'readme.txt'), 8))

    def test_a_helper_that_fails_is_a_refusal_not_content(self):
        def failing(command, user):
            return False, b'realpath: error text\n'

        def broken(command, user):
            raise OSError('no helper')

        for runner in (failing, broken):
            site = SiteFiles('secaiuser', self.home, self.root, runner=runner)
            self.refused('not_found', site.read_file, 'index.php')
            self.refused('not_found', site.list_directory, '')


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
        self.refused('path_not_allowed', self.site.rename_file, 'evil.php', 'evil.php.quarantined.1')
        self.refused('path_not_allowed', self.site.delete_file, 'evil.php')
        self.refused('path_not_allowed', self.site.backup_file, 'evil.php')
        self.refused('path_not_allowed', self.site.replace_file, 'linkdir/target.php', b'<?php // changed\n')
        self.assertEqual(b'<?php // outside\n', self.read(self.outside, 'target.php'))
        self.assertTrue(os.path.islink(os.path.join(self.root, 'evil.php')))
        self.assertEqual([], self.backups())

    def test_replacing_never_creates_a_file(self):
        self.refused('not_found', self.site.replace_file, 'wp-content/new.php', b'<?php\n')
        self.assertFalse(os.path.exists(os.path.join(self.root, 'wp-content', 'new.php')))

    def test_files_that_configure_the_site_are_never_changed(self):
        write(os.path.join(self.root, '.htaccess'), b'deny\n')
        write(os.path.join(self.root, 'wp-content', '.user.ini'), b'a=b\n')
        write(os.path.join(self.root, 'php.ini'), b'a=b\n')
        for name in ('wp-config.php', '.htaccess', 'wp-content/.user.ini', 'php.ini'):
            self.refused('protected_file', self.site.replace_file, name, b'changed\n')
            self.refused('protected_file', self.site.rename_file, name, name + '.quarantined.1')
            self.refused('protected_file', self.site.delete_file, name)
        for name in ('.htaccess', 'wp-content/.user.ini', 'wp-content/php.ini', 'wp-content/WP-Config.php'):
            self.refused('protected_file', self.site.rename_file, 'readme.txt', name)
        self.refused('protected_file', self.site.delete_file, 'index.php')
        self.assertEqual(b'<?php // secrets\n', self.read(self.root, 'wp-config.php'))
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertEqual([], self.backups())

    def test_only_scannable_kinds_of_file_are_changed(self):
        self.refused('type_not_allowed', self.site.replace_file, 'image.png', b'x')
        self.refused('type_not_allowed', self.site.rename_file, 'image.png', 'image.php')
        self.refused('type_not_allowed', self.site.delete_file, 'image.png')
        self.refused('type_not_allowed', self.site.backup_file, 'image.png')
        self.assertEqual(b'\x89PNG', self.read(self.root, 'image.png'))

    def test_the_configuration_file_can_be_backed_up_because_the_copy_is_private(self):
        backup = self.site.backup_file('wp-config.php')
        self.assertEqual(b'<?php // secrets\n', self.read(backup['backup_path']))
        self.assertEqual(17, backup['size'])
        self.assertFalse(backup['backup_path'].startswith(self.root + os.sep))

    def test_renaming_moves_the_file_to_a_free_name(self):
        renamed = self.site.rename_file('wp-content/plugins/demo/demo.php',
                                        'wp-content/plugins/demo/demo.php.quarantined.1730000000')
        self.assertFalse(os.path.exists(os.path.join(self.root, 'wp-content', 'plugins', 'demo', 'demo.php')))
        self.assertEqual(b'<?php // demo\n', self.read(
            self.root, 'wp-content', 'plugins', 'demo', 'demo.php.quarantined.1730000000'))
        self.assertEqual(b'<?php // demo\n', self.read(renamed['backup_path']))

    def test_renaming_onto_an_existing_name_or_out_of_the_site_is_refused(self):
        self.refused('exists', self.site.rename_file, 'readme.txt', 'index.php')
        self.refused('exists', self.site.rename_file, 'readme.txt', 'link.txt')
        self.refused('path_not_allowed', self.site.rename_file, 'readme.txt', 'linkdir/readme.txt')
        self.refused('path_not_allowed', self.site.rename_file, 'readme.txt', '../readme.txt')
        self.refused('not_found', self.site.rename_file, 'readme.txt', 'missing/readme.txt')
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertEqual(b'<?php // index\n', self.read(self.root, 'index.php'))
        self.assertEqual(['secret.txt', 'target.php'], sorted(os.listdir(self.outside)))

    def test_deleting_keeps_a_copy_first(self):
        deleted = self.site.delete_file('wp-content/my file (1).php')
        self.assertFalse(os.path.exists(os.path.join(self.root, 'wp-content', 'my file (1).php')))
        self.assertEqual(b'<?php // spaced\n', self.read(deleted['backup_path']))
        self.assertEqual(16, deleted['size'])
        self.assertEqual(files.text_digests(b'<?php // spaced\n')[1], deleted['sha256'])

    def test_a_backup_folder_that_is_a_link_is_refused(self):
        exposed = os.path.join(self.root, 'exposed')
        os.makedirs(exposed)
        os.symlink(exposed, os.path.join(self.home, '.ai-scanner-backups'))
        self.refused('backup_dir_failed', self.site.backup_file, 'readme.txt')
        self.refused('backup_dir_failed', self.site.replace_file, 'readme.txt', b'new\n')
        self.refused('backup_dir_failed', self.site.delete_file, 'readme.txt')
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertEqual([], os.listdir(exposed))

    def test_every_command_is_fixed_words_run_as_the_website_user(self):
        self.site.list_directory('wp-content')
        self.site.read_file('wp-content/my file (1).php')
        self.site.replace_file('wp-content/my file (1).php', b'<?php // new\n')
        self.site.rename_file('wp-content/my file (1).php', 'wp-content/my file (1).php.quarantined.1')
        self.site.delete_file('readme.txt')
        programs = set()
        for command, user in self.runner.commands:
            self.assertEqual('secaiuser', user)
            words = shlex.split(command)
            self.assertEqual('2>/dev/null', words[-1])
            self.assertEqual(command, ' '.join(shlex.quote(word) for word in words[:-1]) + ' 2>/dev/null')
            programs.add(words[0])
        self.assertEqual({'realpath', 'stat', 'dd', 'find', 'mkdir', 'chmod', 'mv', 'rm'}, programs)


if __name__ == '__main__':
    unittest.main()
