"""The AI Scanner's backups of earlier releases leave the served folders during an upgrade."""
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from plogical import scannerBackupRelocation as relocation

ROOT = Path(__file__).resolve().parents[1]


class Cursor(object):
    """The panel's tables: websites, child domains and WordPress sites."""

    def __init__(self, websites, children=(), wordpress=(), missing=()):
        self.tables = {'websiteFunctions_websites': list(websites), 'websiteFunctions_childdomains': list(children),
                       'websiteFunctions_wpsites': list(wordpress)}
        self.missing = missing
        self.statements = []
        self.rows = []

    def execute(self, statement, args=None):
        self.statements.append(statement)
        table = [name for name in self.tables if ('.%s p ' % name) in statement] or ['websiteFunctions_websites']
        if table[0] in self.missing:
            raise RuntimeError("Table 'cyberpanel.%s' doesn't exist" % table[0])
        self.rows = self.tables[table[0]]

    def fetchall(self):
        return self.rows


def local_runner(user, home, root, name):
    """The fixed command, run by a shell here instead of through sudo."""
    process = subprocess.Popen(['sh', '-c', relocation.MOVE, 'sh', home, root, name], cwd='/',
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    output = process.communicate()[0]
    return process.returncode, output


def write(path, content=b''):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as handle:
        handle.write(content)


class PlacesTests(unittest.TestCase):

    def test_document_roots_child_domains_and_wordpress_sites_are_looked_at(self):
        cursor = Cursor(
            websites=[('example.com', 'examp1234'), (b'shop.example.org', b'shope5678')],
            children=[('example.com', 'examp1234', '/home/example.com/blog.example.com'),
                      ('example.com', 'examp1234', '/home/example.com/public_html/sub/')],
            wordpress=[('example.com', 'examp1234', '/home/example.com/public_html'),
                       ('example.com', 'examp1234', '/home/example.com/public_html/staging'),
                       ('shop.example.org', 'shope5678', '/home/shop.example.org/public_html/')])
        self.assertEqual([
            ('examp1234', '/home/example.com', '/home/example.com/public_html'),
            ('shope5678', '/home/shop.example.org', '/home/shop.example.org/public_html'),
            ('examp1234', '/home/example.com', '/home/example.com/blog.example.com'),
            ('examp1234', '/home/example.com', '/home/example.com/public_html/sub'),
            ('examp1234', '/home/example.com', '/home/example.com/public_html/staging'),
        ], relocation.places(cursor, 'cyberpanel'))
        self.assertEqual([
            'SELECT domain, externalApp FROM `cyberpanel`.websiteFunctions_websites',
            'SELECT w.domain, w.externalApp, p.path FROM `cyberpanel`.websiteFunctions_childdomains p '
            'JOIN `cyberpanel`.websiteFunctions_websites w ON w.id = p.master_id',
            'SELECT w.domain, w.externalApp, p.path FROM `cyberpanel`.websiteFunctions_wpsites p '
            'JOIN `cyberpanel`.websiteFunctions_websites w ON w.id = p.owner_id',
        ], cursor.statements)

    def test_a_table_an_older_installation_lacks_is_passed_over(self):
        cursor = Cursor(websites=[('example.com', 'examp1234')],
                        children=[('example.com', 'examp1234', '/home/example.com/child')],
                        missing=('websiteFunctions_wpsites',))
        self.assertEqual(2, len(relocation.places(cursor, 'cyberpanel')))

    def test_a_name_that_is_no_domain_names_no_home(self):
        cursor = Cursor(websites=[('../etc', 'x'), ('a/b', 'x'), ('', 'x'), ('.hidden', 'x'), ('a..b', 'x'),
                                  ('-x.com', 'x'), ('good.example', 'goode1234')])
        self.assertEqual([('goode1234', '/home/good.example', '/home/good.example/public_html')],
                         relocation.places(cursor, 'cyberpanel'))


class RelocateTests(unittest.TestCase):
    """What is done with each place, with the command itself replaced."""

    def relocate(self, found, status=0, present=True):
        self.calls = []

        def runner(user, home, root, name):
            self.calls.append((user, home, root, name))
            if isinstance(status, Exception):
                raise status
            return status, ('%s/.ai-scanner-backups/from-%s-1\n' % (home, name)).encode() if status == 0 else b''

        return relocation.relocate(found, runner, lambda path: present)

    def test_a_folder_that_is_there_is_moved_by_the_website_user(self):
        result = self.relocate([('examp1234', '/home/example.com', '/home/example.com/public_html'),
                                ('examp1234', '/home/example.com', '/home/example.com/public_html/my blog')])
        self.assertEqual([('examp1234', '/home/example.com', '/home/example.com/public_html', 'public_html'),
                          ('examp1234', '/home/example.com', '/home/example.com/public_html/my blog',
                           'public_html_my_blog')], self.calls)
        self.assertEqual({'moved': [
            ['/home/example.com/public_html/.ai-scanner-backups',
             '/home/example.com/.ai-scanner-backups/from-public_html-1'],
            ['/home/example.com/public_html/my blog/.ai-scanner-backups',
             '/home/example.com/.ai-scanner-backups/from-public_html_my_blog-1']], 'skipped': []}, result)

    def test_no_command_is_run_where_there_is_no_such_folder(self):
        result = self.relocate([('examp1234', '/home/example.com', '/home/example.com/public_html')], present=False)
        self.assertEqual(({'moved': [], 'skipped': []}, []), (result, self.calls))

    def test_a_place_outside_the_home_of_its_website_is_not_touched(self):
        for root in ('/home/other.com/public_html', '/home/example.com/../other.com/public_html', '/etc',
                     '/home/example.com', '/home/example.com-old/public_html', 'public_html',
                     '/home/example.com/a\nb', '/home/example.com//public_html'):
            result = self.relocate([('examp1234', '/home/example.com', root)])
            self.assertEqual(({'moved': [], 'skipped': []}, []), (result, self.calls), root)

    def test_a_website_without_a_user_of_its_own_is_reported_and_nothing_runs(self):
        for user in ('root', '', '-u', 'a b', 'a;b', None):
            result = self.relocate([(user, '/home/example.com', '/home/example.com/public_html')])
            self.assertEqual([], self.calls)
            self.assertEqual([['/home/example.com/public_html/.ai-scanner-backups',
                               'its website has no user of its own']], result['skipped'])

    def test_what_the_command_found_is_reported(self):
        place = [('examp1234', '/home/example.com', '/home/example.com/public_html')]
        old = '/home/example.com/public_html/.ai-scanner-backups'
        self.assertEqual({'moved': [], 'skipped': []}, self.relocate(place, status=4))
        for status, reason in ((5, 'it is a link'),
                               (6, 'the private folder in the home is a link or cannot be used'),
                               (7, 'it could not be moved'), (8, 'the folder cannot be entered'),
                               (9, 'the folder is not inside the home of its website'),
                               (1, 'the command ended with status 1'), (-9, 'the command ended with status -9')):
            self.assertEqual({'moved': [], 'skipped': [[old, reason]]}, self.relocate(place, status=status))
        result = self.relocate(place * 1 + [('other5678', '/home/other.org', '/home/other.org/public_html')],
                               status=OSError('sudo is missing'))
        self.assertEqual([[old, 'OSError: sudo is missing'],
                          ['/home/other.org/public_html/.ai-scanner-backups', 'OSError: sudo is missing']],
                         result['skipped'])
        self.assertEqual(2, len(self.calls))

    def test_the_command_runs_through_sudo_as_the_user_with_the_paths_as_arguments(self):
        with mock.patch.object(relocation.subprocess, 'Popen') as popen:
            popen.return_value.communicate.return_value = (b'/home/e.com/.ai-scanner-backups/from-public_html-1\n', b'')
            popen.return_value.returncode = 0
            self.assertEqual((0, b'/home/e.com/.ai-scanner-backups/from-public_html-1\n'), relocation.run_as_site_user(
                'examp1234', '/home/e.com', "/home/e.com/it's $(x)", 'it_s___x_'))
        (command,), options = popen.call_args
        self.assertEqual(['sudo', '-u', 'examp1234', '--', 'sh', '-c', relocation.MOVE, 'sh', '/home/e.com',
                          "/home/e.com/it's $(x)", 'it_s___x_'], command)
        self.assertEqual('/', options['cwd'])
        self.assertNotIn('shell', options)
        # The text of the command is fixed: nothing of a path is ever part of it.
        self.assertNotIn('%', relocation.MOVE.replace('${p%??}', '').replace('printf "%s\\n"', ''))
        self.assertNotIn("'", relocation.MOVE)


class MoveTests(unittest.TestCase):
    """The fixed command itself, on real folders."""

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix='secai'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = os.path.join(self.base, 'home', 'secai.test')
        self.root = os.path.join(self.home, 'public_html')
        self.old = os.path.join(self.root, '.ai-scanner-backups')
        self.private = os.path.join(self.home, '.ai-scanner-backups')
        write(os.path.join(self.old, '2025-10-25', 'wp-config.php.1730000000.bak'), b'<?php // secrets\n')
        write(os.path.join(self.old, '2025-10-26', "it's.php.1730086400.bak"), b'<?php // other\n')
        write(os.path.join(self.root, 'index.php'), b'<?php // index\n')

    def move(self, root=None, name='public_html'):
        return relocation.relocate([('secaiuser', self.home, root or self.root)], local_runner)

    def tree(self, top):
        found = {}
        for directory, unused, names in os.walk(top):
            for name in names:
                path = os.path.join(directory, name)
                if os.path.islink(path):
                    continue
                with open(path, 'rb') as handle:
                    found[os.path.relpath(path, top)] = handle.read()
        return found

    def test_the_folder_goes_whole_into_the_private_folder_of_the_home(self):
        before = self.tree(self.old)
        result = self.move()
        target = os.path.join(self.private, 'from-public_html-1')
        self.assertEqual({'moved': [[self.old, target]], 'skipped': []}, result)
        self.assertFalse(os.path.lexists(self.old))
        self.assertEqual(before, self.tree(target))
        self.assertEqual(2, len(before))
        self.assertEqual(0o700, stat.S_IMODE(os.stat(self.private).st_mode))
        self.assertEqual(['index.php'], os.listdir(self.root))
        # A second upgrade finds nothing to do.
        self.assertEqual({'moved': [], 'skipped': []}, self.move())
        self.assertEqual(before, self.tree(target))

    def test_what_the_private_folder_already_holds_is_kept_and_nothing_is_overwritten(self):
        write(os.path.join(self.private, '2026-11-22', 'a.php.1.ab.bak'), b'new backup\n')
        write(os.path.join(self.private, 'from-public_html-1', 'earlier.bak'), b'earlier move\n')
        os.symlink('/nonexistent', os.path.join(self.private, 'from-public_html-2'))
        os.chmod(self.private, 0o755)
        result = self.move()
        self.assertEqual([[self.old, os.path.join(self.private, 'from-public_html-3')]], result['moved'])
        self.assertEqual(b'new backup\n', self.tree(self.private)['2026-11-22/a.php.1.ab.bak'])
        self.assertEqual(b'earlier move\n', self.tree(self.private)['from-public_html-1/earlier.bak'])
        self.assertEqual(b'<?php // secrets\n',
                         self.tree(self.private)['from-public_html-3/2025-10-25/wp-config.php.1730000000.bak'])
        self.assertEqual(0o700, stat.S_IMODE(os.stat(self.private).st_mode))

    def test_the_folders_of_several_places_of_one_website_get_names_of_their_own(self):
        blog = os.path.join(self.home, 'public_html', 'my blog')
        child = os.path.join(self.home, 'child.secai.test')
        write(os.path.join(blog, '.ai-scanner-backups', '2025-10-25', 'b.bak'), b'blog\n')
        write(os.path.join(child, '.ai-scanner-backups', '2025-10-25', 'c.bak'), b'child\n')
        result = relocation.relocate([('secaiuser', self.home, place) for place in (self.root, blog, child)],
                                     local_runner)
        self.assertEqual(['from-child.secai.test-1', 'from-public_html-1', 'from-public_html_my_blog-1'],
                         sorted(os.listdir(self.private)))
        self.assertEqual(3, len(result['moved']))
        self.assertEqual(b'child\n', self.tree(self.private)['from-child.secai.test-1/2025-10-25/c.bak'])

    def test_a_folder_that_is_a_link_is_left_alone_and_reported(self):
        elsewhere = os.path.join(self.base, 'elsewhere')
        os.rename(self.old, elsewhere)
        os.symlink(elsewhere, self.old)
        result = self.move()
        self.assertEqual({'moved': [], 'skipped': [[self.old, 'it is a link']]}, result)
        self.assertTrue(os.path.islink(self.old))
        self.assertEqual(2, len(self.tree(elsewhere)))
        self.assertFalse(os.path.lexists(self.private))

    def test_a_private_folder_that_is_a_link_is_not_moved_into(self):
        elsewhere = os.path.join(self.base, 'elsewhere')
        os.mkdir(elsewhere)
        os.symlink(elsewhere, self.private)
        before = self.tree(self.old)
        result = self.move()
        self.assertEqual({'moved': [], 'skipped': [
            [self.old, 'the private folder in the home is a link or cannot be used']]}, result)
        self.assertEqual(before, self.tree(self.old))
        self.assertEqual([], os.listdir(elsewhere))
        os.remove(self.private)
        write(self.private, b'a file in the way\n')
        self.assertEqual('the private folder in the home is a link or cannot be used', self.move()['skipped'][0][1])
        self.assertEqual(before, self.tree(self.old))

    def test_a_site_directory_that_is_a_link_out_of_the_home_is_left_alone(self):
        outside = os.path.join(self.base, 'outside')
        write(os.path.join(outside, '.ai-scanner-backups', 'x.bak'), b'not ours\n')
        linked = os.path.join(self.home, 'linked')
        os.symlink(outside, linked)
        result = self.move(root=linked)
        self.assertEqual([[os.path.join(linked, '.ai-scanner-backups'),
                           'the folder is not inside the home of its website']], result['skipped'])
        self.assertEqual({'.ai-scanner-backups/x.bak': b'not ours\n'}, self.tree(outside))
        self.assertFalse(os.path.lexists(self.private))

    def test_a_home_with_a_backslash_and_a_space_in_its_name_is_reported_as_it_is(self):
        home = os.path.join(self.base, 'home', 'secai\\n \\c.test')
        root = os.path.join(home, 'public html')
        write(os.path.join(root, '.ai-scanner-backups', '2025-10-25', 'a.bak'), b'a\n')
        result = relocation.relocate([('secaiuser', home, root)], local_runner)
        target = os.path.join(home, '.ai-scanner-backups', 'from-public_html-1')
        self.assertEqual({'moved': [[os.path.join(root, '.ai-scanner-backups'), target]], 'skipped': []}, result)
        self.assertEqual({'2025-10-25/a.bak': b'a\n'}, self.tree(target))

    def test_a_file_of_that_name_is_no_folder_to_move(self):
        shutil.rmtree(self.old)
        write(self.old, b'a file\n')
        self.assertEqual({'moved': [], 'skipped': []}, self.move())
        self.assertTrue(os.path.isfile(self.old))


class RunTests(unittest.TestCase):

    def setUp(self):
        self.log = []
        self.connection = mock.Mock()
        self.cursor = Cursor(websites=[('example.com', 'examp1234'), ('shop.example.org', 'shope5678')],
                             children=[('example.com', 'examp1234', '/home/example.com/blog.example.com')])

    def run_with(self, runner, exists=lambda path: True):
        with mock.patch.object(relocation, 'panel_database', return_value='cyberpanel'):
            return relocation.run(lambda: (self.connection, self.cursor), self.log.append, runner, exists)

    def test_one_line_says_what_was_done(self):
        summary = self.run_with(lambda user, home, root, name: (
            (0, ('%s/.ai-scanner-backups/from-%s-1\n' % (home, name)).encode()) if 'shop' not in home else (5, b'')))
        self.assertEqual('2 folder(s) of earlier releases moved out of served folders, 1 left where they are, '
                         '3 place(s) looked at', summary)
        self.assertEqual([
            'AI Scanner backups: moved /home/example.com/public_html/.ai-scanner-backups to '
            '/home/example.com/.ai-scanner-backups/from-public_html-1',
            'AI Scanner backups: moved /home/example.com/blog.example.com/.ai-scanner-backups to '
            '/home/example.com/.ai-scanner-backups/from-blog.example.com-1',
            'WARNING: The AI Scanner backups in /home/shop.example.org/public_html/.ai-scanner-backups were left '
            'where they are: it is a link. The web server may serve the files in them.'], self.log)
        self.connection.close.assert_called_once_with()

    def test_a_server_without_such_folders_runs_no_command(self):
        runner = mock.Mock()
        self.assertEqual('0 folder(s) of earlier releases moved out of served folders, 0 left where they are, '
                         '3 place(s) looked at', self.run_with(runner, exists=lambda path: False))
        runner.assert_not_called()
        self.assertEqual([], self.log)

    def test_a_long_list_of_moves_is_shortened(self):
        moved = [['/home/s%d.test/public_html/.ai-scanner-backups' % number, '/x'] for number in range(15)]
        relocation.describe({'moved': moved, 'skipped': []}, self.log.append)
        self.assertEqual(13, len(self.log))
        self.assertEqual('AI Scanner backups: and 3 more folder(s) moved.', self.log[-1])

    def test_no_connection_changes_nothing(self):
        runner = mock.Mock()
        self.assertEqual('no connection', relocation.run(lambda: (0, 0), self.log.append, runner))
        self.assertEqual(1, len(self.log))
        runner.assert_not_called()

    def test_unreadable_websites_close_the_connection_and_run_nothing(self):
        self.cursor.missing = ('websiteFunctions_websites',)
        runner = mock.Mock()
        with self.assertRaises(RuntimeError):
            self.run_with(runner)
        runner.assert_not_called()
        self.connection.close.assert_called_once_with()


class CallSiteTests(unittest.TestCase):
    def test_upgrader_moves_the_backups_and_can_not_fail_on_it(self):
        upgrader = (ROOT / 'plogical' / 'upgrade.py').read_text()
        start = upgrader.index('    def relocateScannerBackups():')
        method = upgrader[start:upgrader.index('    @staticmethod', start)]
        self.assertIn('from plogical.scannerBackupRelocation import run as relocate_scanner_backups', method)
        self.assertIn('connect=Upgrade.setupConnection, log=Upgrade.stdOut', method)
        self.assertIn("except Exception as error:\n            Upgrade.warn('AI Scanner backups of "
                      "earlier releases were not looked for: ' + str(error))", method)
        self.assertLess(method.index('        try:'), method.index('from plogical.scannerBackupRelocation'))
        # Called once in the upgrade itself, after the repair of the database grants.
        self.assertEqual(1, upgrader.count('Upgrade.relocateScannerBackups()'))
        self.assertLess(upgrader.index('\n        Upgrade.repairDatabaseGrants()\n'),
                        upgrader.index('\n        Upgrade.relocateScannerBackups()\n'))

    def test_upgrade_started_from_the_cloud_platform_runs_it_too(self):
        cloud = (ROOT / 'plogical' / 'CyberPanelUpgrade.py').read_text()
        self.assertEqual(1, cloud.count('Upgrade.relocateScannerBackups()'))
        self.assertLess(cloud.index('\n        Upgrade.repairDatabaseGrants()\n'),
                        cloud.index('\n        Upgrade.relocateScannerBackups()\n'))

    def test_helper_does_not_need_the_panel_models(self):
        source = (ROOT / 'plogical' / 'scannerBackupRelocation.py').read_text()
        self.assertNotIn('django', source)
        self.assertEqual('`odd``name`', relocation.quote('odd`name'))
        self.assertEqual('public_html', relocation.folder_name('/home/e.com', '/home/e.com/public_html'))
        self.assertEqual('site', relocation.folder_name('/home/e.com', '/home/e.com/...'))


if __name__ == '__main__':
    unittest.main()
