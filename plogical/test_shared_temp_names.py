"""Files handed from one account to another are not written to guessable names in /tmp."""
import json
import os
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical import fileSystemSecurity
from plogical.test_child_domain_conversion import load_method

ROOT = Path(__file__).resolve().parents[1]


class SharedTempFileTests(unittest.TestCase):
    def test_bytes_are_stored_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(fileSystemSecurity, 'SHARED_TEMP_DIRECTORY', directory):
                path = fileSystemSecurity.write_shared_temp_file('RewriteRule ^café$ /x\n'.encode('utf-8'))
            self.assertEqual('RewriteRule ^café$ /x\n'.encode('utf-8'), Path(path).read_bytes())
            self.assertEqual(0o644, os.stat(path).st_mode & 0o777)
            self.assertRegex(os.path.basename(path), r'\A[0-9a-f]{32}\Z')


class RewriteRuleSaveTests(unittest.TestCase):
    def save(self, directory, child_path=None):
        self.commands = []
        self.present = []

        def executioner(command, user=None):
            self.commands.append((command, user))
            self.present.append(os.path.exists(shlex.split(command)[1]))
            return 1

        acl = Mock()
        acl.checkOwnership.return_value = 1
        acl.loadedACL.return_value = {'admin': 0}

        def child(**kwargs):
            if child_path is None:
                raise LookupError('no child domain')
            return SimpleNamespace(path=child_path, master=SimpleNamespace(externalApp='examp1234'))

        handler = load_method('websiteFunctions/website.py', 'WebsiteManager', 'saveRewriteRules', dict(
            ACLManager=acl, Administrator=Mock(), json=json, shlex=shlex, os=os,
            ProcessUtilities=SimpleNamespace(executioner=executioner),
            mailUtilities=Mock(), installUtilities=Mock(),
            ChildDomains=SimpleNamespace(objects=SimpleNamespace(get=child)),
            Websites=SimpleNamespace(objects=SimpleNamespace(
                get=lambda **k: SimpleNamespace(externalApp='examp1234'))),
            HttpResponse=lambda content: SimpleNamespace(content=content.encode())))
        with patch.object(fileSystemSecurity, 'SHARED_TEMP_DIRECTORY', directory):
            response = handler(SimpleNamespace(), userID=7, data={
                'virtualHost': 'example.com', 'rewriteRules': 'RewriteRule ^café$ /x\n'})
        return json.loads(response.content)

    def test_rules_reach_the_site_through_an_unguessable_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.save(directory)
            self.assertEqual(1, result['rewriteStatus'], result)
            (command, user), = self.commands
            words = shlex.split(command)
            self.assertEqual(['cp', '/home/example.com/public_html/.htaccess'], [words[0], words[2]])
            self.assertEqual('examp1234', user)
            self.assertEqual(directory, os.path.dirname(words[1]))
            self.assertRegex(os.path.basename(words[1]), r'\A[0-9a-f]{32}\Z')
            self.assertEqual([True], self.present)
            self.assertEqual([], os.listdir(directory))

    def test_child_domain_path_is_one_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            self.save(directory, child_path='/home/example.com/my shop; id')
            (command, user), = self.commands
            self.assertEqual('/home/example.com/my shop; id/.htaccess', shlex.split(command)[2])
            self.assertEqual(3, len(shlex.split(command)))

    def test_handler_names_nothing_in_the_world_writable_directory(self):
        source = (ROOT / 'websiteFunctions' / 'website.py').read_text()
        self.assertNotIn('"/tmp/" + str(randint', source)
        self.assertNotIn("'/tmp/' + str(randint", source)


class CronAddTests(unittest.TestCase):
    def test_new_entry_is_staged_in_a_file_only_this_account_can_reach(self):
        from plogical import cronUtil

        seen = {}

        def run(command):
            source, target = shlex.split(command)[1:]
            seen.update(source=source, target=target, mode=os.stat(source).st_mode & 0o777,
                        content=Path(source).read_text())

        with patch.object(cronUtil.ProcessUtilities, 'decideDistro', return_value='other'), \
                patch.object(cronUtil.ProcessUtilities, 'normalExecutioner', side_effect=run), \
                patch('builtins.print'):
            cronUtil.CronUtil.addNewCron('nosuchaccount0000', '5 2 * * * new')

        self.assertEqual('/var/spool/cron/crontabs/nosuchaccount0000', seen['target'])
        self.assertEqual('5 2 * * * new\n', seen['content'])
        self.assertEqual(0o600, seen['mode'])
        self.assertNotRegex(os.path.basename(seen['source']), r'\A[0-9]{4}\Z')
        self.assertFalse(os.path.exists(seen['source']))

    def test_no_four_digit_name_remains(self):
        self.assertNotIn('randint', (ROOT / 'plogical' / 'cronUtil.py').read_text())


if __name__ == '__main__':
    unittest.main()
