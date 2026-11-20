"""File manager: page markup, the delete probe, temporary files and privileged reads."""
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from filemanager.test_permission_feedback import load, response
from plogical import fileSystemSecurity

ROOT = Path(__file__).resolve().parents[1]


class EditorThemeTests(unittest.TestCase):
    def setUp(self):
        namespace = {'re': re}
        theme = load('filemanager/filemanager.py', 'editorTheme', namespace, 'FileManager')
        namespace['FileManager'] = SimpleNamespace(editorTheme=theme)
        self.theme = theme
        self.link = load('filemanager/filemanager.py', 'findThemeFile', namespace, 'FileManager')

    def test_known_theme_names_are_kept(self):
        for name in ('cobalt', 'monokai', '3024-day', 'base16-dark', 'solarized'):
            self.assertEqual(name, self.theme(name))
            self.assertIn('/theme/%s.min.css"' % name, self.link(name))

    def test_anything_that_is_not_a_plain_name_becomes_the_default(self):
        for value in ('x"><script>alert(1)</script>', 'a b', 'A', '../x', 'x.css', '', None, ['cobalt'],
                      'a' * 41, 'x"onload="y', 'cobalt\n'):
            self.assertEqual('cobalt', self.theme(value), repr(value))
            link = self.link(value)
            self.assertEqual(1, link.count('<'), repr(value))
            self.assertIn('/theme/cobalt.min.css"', link)

    def test_editor_page_uses_the_checked_name(self):
        source = (ROOT / 'filemanager/views.py').read_text()
        self.assertIn("theme = FM.editorTheme(request.GET.get('theme'))", source)


class Recorder:
    """Stands in for the command helper and remembers which account ran what."""

    def __init__(self, output=''):
        self.calls = []
        self.output = output

    def outputExecutioner(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        return self.output

    def executioner(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        return 1


class DeleteProbeTests(unittest.TestCase):
    def test_probe_in_the_customers_home_never_runs_with_privilege(self):
        commands = Recorder()
        website = SimpleNamespace(externalApp='examp1234')
        delete = load('filemanager/filemanager.py', 'deleteFolderOrFile', dict(
            Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda **kwargs: website)),
            ProcessUtilities=commands, json=json, HttpResponse=response, Trash=Mock(),
            require_root_entitlement=Mock(side_effect=AssertionError('site request fell into root mode'))),
            'FileManager')
        manager = SimpleNamespace(
            data={'domainName': 'example.com', 'path': '/home/example.com/public_html',
                  'fileAndFolders': ['old.txt'], 'skipTrash': True},
            returnPathEnclosed=shlex.quote, notInside=lambda path, home: False,
            ajaxPre=lambda status, message: response(json.dumps({'status': status, 'error_message': message})))
        self.assertEqual(1, json.loads(delete(manager).content)['status'])
        probe = [(command, user) for command, user in commands.calls if 'hello.txt' in command]
        self.assertEqual([('touch -h /home/example.com/hello.txt', 'examp1234'),
                          ('rm -f /home/example.com/hello.txt', 'examp1234')], probe)
        for command, user in commands.calls:
            self.assertEqual('examp1234', user, command)


class UploadTests(unittest.TestCase):
    def run_upload(self, listing=''):
        removed = []
        commands = Recorder(output=listing)
        stored = {}

        class Storage:
            def save(self, name, content):
                stored['asked'] = name
                stored['saved'] = name + '_Ab3dE9x'      # the name was taken: stored under another
                return stored['saved']

            def url(self, name):
                return '/media/' + name

        website = SimpleNamespace(externalApp='examp1234')
        upload = load('filemanager/filemanager.py', 'upload', dict(
            ACLManager=SimpleNamespace(CreateSecureDir=lambda: None), secrets=secrets,
            FileSystemStorage=Storage, logging=Mock(), json=json, HttpResponse=response,
            Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda **kwargs: website)),
            ProcessUtilities=commands,
            os=SimpleNamespace(remove=removed.append, path=os.path),
            require_root_entitlement=Mock(side_effect=AssertionError('site request fell into root mode'))),
            'FileManager')
        manager = SimpleNamespace(
            request=SimpleNamespace(FILES={'file': SimpleNamespace(name='photo.jpg')}),
            data={'domainName': 'example.com', 'completePath': '/home/example.com/public_html'},
            returnPathEnclosed=shlex.quote, safeUploadPath=lambda path: True,
            notInside=lambda path, home: False, changeOwner=lambda path: None,
            ajaxPre=lambda status, message: response(json.dumps({'uploadStatus': status,
                                                                 'error_message': message})))
        result = json.loads(upload(manager).content)
        return result, stored, commands.calls, removed

    def test_temporary_name_cannot_be_guessed(self):
        _, stored, _, _ = self.run_upload()
        self.assertRegex(stored['asked'], r'\A[0-9a-f]{32}\Z')
        self.assertNotEqual(stored['asked'], self.run_upload()[1]['asked'])

    def test_the_file_that_was_stored_is_the_one_copied_and_removed(self):
        result, stored, calls, removed = self.run_upload()
        self.assertEqual(1, result['uploadStatus'])
        temporary = '/usr/local/CyberCP/tmp/' + stored['saved']
        copies = [command for command, user in calls if command.startswith('cp ')]
        self.assertEqual(['cp %s /home/example.com/public_html/photo.jpg' % temporary], copies)
        self.assertIn(temporary, removed)
        self.assertNotIn('/usr/local/CyberCP/tmp/' + stored['asked'], removed)

    def test_refused_upload_does_not_leave_its_temporary_file(self):
        result, stored, calls, removed = self.run_upload(listing='lrwxrwxrwx x -> /etc')
        self.assertEqual(0, result['uploadStatus'])
        self.assertEqual([], [command for command, user in calls if command.startswith('cp ')])
        self.assertEqual(['/usr/local/CyberCP/tmp/' + stored['saved']], removed)

    def test_no_guessable_temporary_name_remains(self):
        source = (ROOT / 'filemanager/filemanager.py').read_text()
        self.assertNotIn('randint(', source)
        self.assertEqual(3, source.count('secrets.token_hex(16)'))
        self.assertEqual(2, source.count('os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600'))


class PrivilegedReadTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.home = Path(holder.name, 'home')
        self.home.mkdir()
        self.outside = Path(holder.name, 'shadow')
        self.outside.write_text('root:$6$secret\n')

    def read(self, name, **options):
        with fileSystemSecurity._open_regular_file_under(str(self.home), str(self.home / name), **options) as handle:
            return handle.read()

    def test_named_pipe_is_refused_without_waiting(self):
        os.mkfifo(str(self.home / 'pipe'))
        with self.assertRaises(OSError):
            self.read('pipe')

    def test_second_name_for_another_file_is_refused_only_for_the_privileged_reader(self):
        os.link(str(self.outside), str(self.home / 'copy'))
        self.assertEqual(b'root:$6$secret\n', self.read('copy'))
        with self.assertRaises(OSError):
            self.read('copy', single_link=True)
        (self.home / 'own.txt').write_text('own')
        self.assertEqual(b'own', self.read('own.txt', single_link=True))

    def test_download_staging_uses_the_single_name_rule(self):
        source = (ROOT / 'plogical/fileSystemSecurity.py').read_text()
        self.assertIn('_open_regular_file_under(allowed_root, source_path, single_link=True)', source)


if __name__ == '__main__':
    unittest.main()
