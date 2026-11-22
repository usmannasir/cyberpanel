"""The stored name of a panel user is one argument on a command line and never a path of its own."""
import os
import re
import shlex
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from plogical.panelUserNames import existing_file_for_user, file_for_user

ROOT = Path(__file__).resolve().parents[1]

# Names earlier releases stored as typed.
EARLIER_NAMES = ('John Smith', 'a b; c', "o'brien", 'x & y', 'a|b', '$(x)', '`x`', 'tab\there', 'new\nline')


class CommandLineTests(unittest.TestCase):
    def source(self, name):
        return (ROOT / name).read_text()

    def test_every_command_site_quotes_the_name(self):
        sites = (
            ('websiteFunctions/website.py', "' --websiteOwner ' + shlex.quote(websiteOwner)"),
            ('websiteFunctions/website.py', "' --websiteOwner ' \\\n"
             "                       + shlex.quote(admin.userName) + ' --tempStatusPath '"),
            ('websiteFunctions/website.py', "' --websiteOwner ' + shlex.quote(admin.userName)\n"),
            ('websiteFunctions/StagingSetup.py', "+ shlex.quote(admin.userName) + ' --tempStatusPath"),
            ('mailServer/mailserverManager.py', '(execPath, selectedDomain, shlex.quote(website.admin.userName))'),
            ('plogical/virtualHostUtilities.py', 'virtualHostUser, shlex.quote(admin.userName))'),
        )
        for name, text in sites:
            self.assertIn(text, self.source(name), (name, text))

    def test_no_owner_argument_is_left_without_quotes(self):
        # A line that puts a user's name behind an owner option does it through shlex.quote.
        option = re.compile(r"--(?:websiteOwner|owner) ?(?:%s)?['\"]")
        for path in sorted(ROOT.rglob('*.py')):
            relative = str(path.relative_to(ROOT))
            if relative.startswith(('cli/', 'install/')) or path.name.startswith('test_'):
                continue
            lines = path.read_text(errors='replace').splitlines()
            for number, line in enumerate(lines):
                if option.search(line) is None or 'add_argument' in line:
                    continue
                statement = ' '.join(lines[number:number + 3])
                self.assertIn('shlex.quote(', statement, '%s:%d' % (relative, number + 1))

    def test_a_quoted_name_stays_one_argument(self):
        for name in EARLIER_NAMES:
            command = 'worker createDomain --websiteOwner ' + shlex.quote(name) + ' --tempStatusPath /tmp/x'
            self.assertEqual(['worker', 'createDomain', '--websiteOwner', name, '--tempStatusPath', '/tmp/x'],
                             shlex.split(command), repr(name))


class SettingsFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.prefix = os.path.join(self.directory.name, 'CloudFlare')

    def user(self, name, number=7):
        return SimpleNamespace(userName=name, pk=number)

    def write(self, path):
        with open(path, 'w') as stream:
            stream.write('mail@example.com\nkey\n1')

    def test_plain_name_keeps_the_file_it_always_had(self):
        for name in ('admin', 'john', 'John.Doe', 'john-doe', 'john_doe', 'john@example.com', '-x', '..'):
            self.assertEqual(self.prefix + name, file_for_user(self.prefix, self.user(name)), name)
        self.write(self.prefix + 'john')
        self.assertEqual(self.prefix + 'john', existing_file_for_user(self.prefix, self.user('john')))
        self.assertIsNone(existing_file_for_user(self.prefix, self.user('jane')))

    def test_any_other_name_gets_a_file_named_after_the_users_number(self):
        for name in EARLIER_NAMES + ('a/b', '../../etc/passwd', '/etc/passwd', 'jürgen', '', 'x\x00y', None):
            path = file_for_user(self.prefix, self.user(name))
            self.assertEqual(self.prefix + ',7', path, repr(name))
            self.assertEqual(self.directory.name, os.path.dirname(path))

    def test_numbered_file_cannot_be_the_file_of_a_plain_name(self):
        self.assertNotEqual(file_for_user(self.prefix, self.user('John Smith', 7)),
                            file_for_user(self.prefix, self.user(',7', 8)))
        self.assertIsNone(re.fullmatch(r'[A-Za-z0-9._@-]+', ',7'))

    def test_settings_saved_under_an_earlier_name_are_still_read(self):
        user = self.user('John Smith')
        self.write(self.prefix + 'John Smith')
        self.assertEqual(self.prefix + 'John Smith', existing_file_for_user(self.prefix, user))
        # Once saved again they live in the numbered file.
        self.write(file_for_user(self.prefix, user))
        self.assertEqual(self.prefix + ',7', existing_file_for_user(self.prefix, user))

    def test_name_with_a_separator_reads_nothing_outside_the_directory(self):
        outside = os.path.join(self.directory.name, 'elsewhere')
        self.write(outside)
        os.mkdir(self.prefix + 'x')
        for name in ('x/../elsewhere', 'x/../../' + os.path.basename(self.directory.name) + '/elsewhere'):
            self.assertTrue(os.path.isfile(self.prefix + name), name)
            self.assertIsNone(existing_file_for_user(self.prefix, self.user(name)), name)

    def test_link_under_an_earlier_name_is_not_followed(self):
        target = os.path.join(self.directory.name, 'target')
        self.write(target)
        os.symlink(target, self.prefix + 'John Smith')
        self.assertIsNone(existing_file_for_user(self.prefix, self.user('John Smith')))

    def test_dns_pages_find_the_file_through_these_functions(self):
        manager = (ROOT / 'dns' / 'dnsManager.py').read_text()
        utilities = (ROOT / 'plogical' / 'dnsUtilities.py').read_text()
        for source in (manager, utilities):
            self.assertNotIn('DNS.CFPath, self.admin.userName', source)
            self.assertNotIn('DNS.CFPath, admin.userName', source)
        self.assertEqual(2, manager.count('existing_file_for_user(DNS.CFPath, '))
        self.assertEqual(1, manager.count('file_for_user(DNS.CFPath, admin)\n'))
        self.assertEqual(1, utilities.count('existing_file_for_user(DNS.CFPath, self.admin)'))


if __name__ == '__main__':
    unittest.main()
