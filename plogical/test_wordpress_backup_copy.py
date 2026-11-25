"""A WordPress backup copies the site's folder as its own user: contents and
hidden files, whether or not the site has hidden files and whether or not its
stored path ends with a slash."""
import getpass
import os
from pathlib import Path
import shlex
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from plogical.test_child_domain_conversion import load_method


def copier(process):
    return load_method('plogical/applicationInstaller.py', 'ApplicationInstaller', 'copyWordPressFiles',
                       dict(ProcessUtilities=process, shlex=shlex))


class CommandTests(unittest.TestCase):
    def test_one_rsync_as_the_site_user_with_vanished_files_allowed(self):
        process = mock.Mock()
        process.outputExecutioner.return_value = (1, '')
        self.assertEqual((1, ''), copier(process)('examp1234', "/home/example.com/public_html",
                                                  '/usr/local/CyberCP/tmp/abc/public_html'))
        args, kwargs = process.outputExecutioner.call_args
        self.assertEqual(['sudo', '-u', 'examp1234', 'rsync', '-a', '/home/example.com/public_html/',
                          '/usr/local/CyberCP/tmp/abc/public_html/'], shlex.split(args[0]))
        self.assertEqual((0, 24), kwargs['okStatuses'])
        self.assertTrue(args[4])  # retRequired

    def test_a_trailing_slash_is_not_doubled_and_odd_names_are_quoted(self):
        process = mock.Mock()
        process.outputExecutioner.return_value = (1, '')
        copier(process)('examp1234', "/home/it's here/", '/tmp/x/public_html/')
        words = shlex.split(process.outputExecutioner.call_args[0][0])
        self.assertEqual(["/home/it's here/", '/tmp/x/public_html/'], words[-2:])


@unittest.skipUnless(os.geteuid() == 0 and shutil.which('rsync') and shutil.which('sudo'),
                     'needs root, sudo and rsync')
class RealCopyTests(unittest.TestCase):
    def setUp(self):
        from plogical.processUtilities import ProcessUtilities
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        self.copy = copier(ProcessUtilities)
        self.user = getpass.getuser()

    def site(self, hidden):
        site = self.root / 'site' / 'public_html'
        (site / 'wp-content' / 'uploads').mkdir(parents=True)
        (site / 'index.php').write_text('<?php')
        (site / 'wp-content' / 'uploads' / 'a.jpg').write_text('jpg')
        if hidden:
            (site / '.htaccess').write_text('rules')
            (site / '.well-known').mkdir()
        destination = self.root / 'backup' / 'public_html'
        destination.mkdir(parents=True)
        return site, destination

    def listing(self, folder):
        return sorted(str(path.relative_to(folder)) for path in folder.rglob('*'))

    def test_site_without_hidden_files(self):
        site, destination = self.site(hidden=False)
        self.assertEqual(1, self.copy(self.user, str(site) + '/', str(destination))[0])
        self.assertEqual(self.listing(site), self.listing(destination))

    def test_hidden_files_are_copied_and_a_path_without_slash_is_not_nested(self):
        site, destination = self.site(hidden=True)
        self.assertEqual(1, self.copy(self.user, str(site), str(destination))[0])
        self.assertEqual(self.listing(site), self.listing(destination))
        self.assertIn('.htaccess', self.listing(destination))
        self.assertFalse((destination / 'public_html').exists())

    def test_a_missing_site_folder_is_a_failure(self):
        _, destination = self.site(hidden=False)
        status, output = self.copy(self.user, str(self.root / 'nothing-here'), str(destination))
        self.assertEqual(0, status)
        self.assertIn('nothing-here', output)


if __name__ == '__main__':
    unittest.main()
