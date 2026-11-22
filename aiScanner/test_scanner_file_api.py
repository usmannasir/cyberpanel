"""The scanner's file endpoints work as the website's user, inside the site, and run nothing a path names."""
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from aiScanner import api


SITE_USER = 'secaiuser'
SCAN_ID = 'cp_0123456789ab'


class LocalHelper(object):
    """Stands in for the root helper: runs each command with a shell and keeps what was asked."""

    def __init__(self):
        self.calls = []
        self.honest = True

    def run(self, command, user=None):
        self.calls.append((command, user))
        process = subprocess.Popen(['sh', '-c', command], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = process.communicate()[0]
        return (process.returncode == 0) if self.honest else True, output

    def outputExecutioner(self, command, user=None, shell=None, dir=None, retRequired=None):
        succeeded, output = self.run(command, user)
        text = output.decode('utf-8', errors='replace')
        return (1 if succeeded else 0, text) if retRequired else text

    def executioner(self, command, user=None, shell=False):
        return 1 if self.run(command, user)[0] else 0


def write(path, content=b'', mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as handle:
        handle.write(content)
    os.chmod(path, mode)


class ScannerFileApiTests(SimpleTestCase):

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix='secai'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = os.path.join(self.base, 'home', 'secai.test')
        self.root = os.path.join(self.home, 'public_html')
        self.outside = os.path.join(self.base, 'outside')
        self.temp = os.path.join(self.base, 'tmp')
        self.marker = os.path.join(self.base, 'marker')
        os.makedirs(self.temp)
        write(os.path.join(self.root, 'index.php'), b'<?php // index\n')
        write(os.path.join(self.root, 'readme.txt'), b'read me\n')
        write(os.path.join(self.root, 'wp-content', 'plugins', 'demo.php'), b'<?php // demo\n', 0o640)
        write(os.path.join(self.home, 'public_html-old', 'secret.php'), b'<?php // old\n')
        write(os.path.join(self.outside, 'secret.txt'), b'outside\n')
        os.symlink(os.path.join(self.outside, 'secret.txt'), os.path.join(self.root, 'link.txt'))

        self.helper = LocalHelper()
        self.auth = api.AuthWrapper('secai.test', self.root, 'api_key', external_app=SITE_USER,
                                    source_obj=SimpleNamespace())
        websites = mock.Mock()
        websites.get.side_effect = lambda **unused: SimpleNamespace(externalApp=self.auth.external_app)
        for patcher in (
                mock.patch('aiScanner.api.validate_access_token', side_effect=lambda *unused: (self.auth, None)),
                mock.patch('aiScanner.api.log_file_operation'),
                mock.patch('aiScanner.api.check_rate_limit', return_value=(True, 1)),
                mock.patch('aiScanner.api.site_home', return_value=self.home, create=True),
                mock.patch('websiteFunctions.models.Websites.objects', websites),
                mock.patch('plogical.scannerFileAccess.run_as_site_user', side_effect=self.helper.run),
                mock.patch('plogical.scannerFileAccess.write_private_temp_file', side_effect=self.temp_writer),
                mock.patch('plogical.processUtilities.ProcessUtilities.outputExecutioner',
                           side_effect=self.helper.outputExecutioner),
                mock.patch('plogical.processUtilities.ProcessUtilities.executioner',
                           side_effect=self.helper.executioner),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def temp_writer(self, content):
        path = os.path.join(self.temp, secrets.token_hex(8))
        with open(path, 'wb') as handle:
            handle.write(content)
        return path

    def get(self, view, **query):
        request = RequestFactory().get('/api/scanner', query, HTTP_X_API_KEY='cp_key', HTTP_X_SCAN_ID=SCAN_ID)
        response = view(request)
        return response.status_code, json.loads(response.content.decode('utf-8'))

    def post(self, view, payload):
        request = RequestFactory().post('/api/scanner', data=json.dumps(payload), content_type='application/json',
                                        HTTP_X_API_KEY='cp_key', HTTP_X_SCAN_ID=SCAN_ID)
        response = view(request)
        return response.status_code, json.loads(response.content.decode('utf-8'))

    def read(self, *parts):
        with open(os.path.join(*parts), 'rb') as handle:
            return handle.read()

    def test_listing_and_content_reach_the_scan_worker_in_the_known_shape(self):
        status, listing = self.get(api.list_files, path='.')
        self.assertEqual(200, status)
        self.assertEqual('.', listing['path'])
        self.assertEqual([('wp-content', 'directory'), ('index.php', 'file'), ('readme.txt', 'file')],
                         [(item['name'], item['type']) for item in listing['items']])
        status, content = self.get(api.get_file_content, path='wp-content/plugins/demo.php')
        self.assertEqual(200, status)
        self.assertEqual(b'<?php // demo\n', base64.b64decode(content['content']))
        self.assertEqual(('wp-content/plugins/demo.php', 14, 'utf-8'),
                         (content['path'], content['size'], content['encoding']))

    def test_names_with_quotes_and_shell_characters_are_listed_and_read(self):
        names = ["it's.php", 'say "x".php', '$(touch %s).php' % os.path.basename(self.marker), 'a&b;c|d.php']
        for name in names:
            write(os.path.join(self.root, 'odd', name), b'<?php // odd\n')
        with mock.patch('aiScanner.api.logging') as log:
            status, listing = self.get(api.list_files, path='odd')
        self.assertEqual((200, sorted(names)), (status, sorted(item['name'] for item in listing['items'])))
        self.assertEqual([], [call for call in log.writeToFile.call_args_list if 'left out' in call[0][0]])
        for name in names:
            status, content = self.get(api.get_file_content, path='odd/' + name)
            self.assertEqual((200, b'<?php // odd\n'), (status, base64.b64decode(content['content'])), name)
            status, found = self.get(api.scanner_get_file, file_path='odd/' + name)
            self.assertEqual((200, '<?php // odd\n'), (status, found['content']), name)
        self.assertFalse(os.path.exists(os.path.basename(self.marker)))
        self.assertFalse(os.path.exists(self.marker))

    def test_a_listing_says_in_the_log_how_many_entries_it_left_out_for_their_names(self):
        write(os.path.join(self.root, 'odd', 'tab\there.php'), b'')
        write(os.path.join(self.root, 'odd', 'line\nbreak.php'), b'')
        write(os.path.join(self.root, 'odd', 'plain.php'), b'')
        with mock.patch('aiScanner.api.logging') as log:
            status, listing = self.get(api.list_files, path='odd')
        self.assertEqual((200, ['plain.php']), (status, [item['name'] for item in listing['items']]))
        lines = [call[0][0] for call in log.writeToFile.call_args_list if 'left out' in call[0][0]]
        self.assertEqual(1, len(lines))
        self.assertIn('left out 2 entries', lines[0])
        self.assertNotIn('tab', lines[0])

    def test_the_fixer_reads_text_with_its_digest(self):
        status, found = self.get(api.scanner_get_file, file_path='readme.txt')
        self.assertEqual(200, status)
        self.assertTrue(found['success'])
        self.assertEqual('read me\n', found['content'])
        self.assertEqual(hashlib.sha256(b'read me\n').hexdigest(), found['hash']['sha256'])
        self.assertEqual(8, found['size'])

    def test_a_path_with_shell_characters_runs_nothing(self):
        for name in ('$(touch %s).php' % self.marker, '`touch %s`.php' % self.marker,
                     'x.php"; touch %s; echo ".php' % self.marker):
            for view, query in ((api.list_files, {'path': name}), (api.get_file_content, {'path': name}),
                                (api.scanner_get_file, {'file_path': name})):
                self.assertIn(self.get(view, **query)[0], (403, 404))
            self.assertIn(self.post(api.scanner_replace_file, {'file_path': name, 'content': 'x'})[0], (403, 404))
            self.assertIn(self.post(api.scanner_backup_file, {'file_path': name, 'scan_id': SCAN_ID})[0], (403, 404))
            self.assertIn(self.post(api.scanner_rename_file, {'old_path': 'readme.txt', 'new_path': name})[0],
                          (403, 404))
            self.assertIn(self.post(api.scanner_delete_file, {'file_path': name, 'confirm_deletion': True})[0],
                          (403, 404))
        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))

    def test_a_link_that_leaves_the_site_is_not_read(self):
        self.assertEqual((403, {'error': 'Path not allowed'}), self.get(api.get_file_content, path='link.txt'))
        status, found = self.get(api.scanner_get_file, file_path='link.txt')
        self.assertEqual(403, status)
        self.assertNotIn('content', found)

    def test_a_folder_beside_the_site_with_the_same_prefix_is_not_read(self):
        for path in ('../public_html-old/secret.php', '..//public_html-old/secret.php'):
            self.assertEqual(403, self.get(api.get_file_content, path=path)[0])
            self.assertEqual(403, self.get(api.scanner_get_file, file_path=path)[0])
            self.assertEqual(403, self.get(api.list_files, path='../public_html-old')[0])

    def test_replacing_runs_only_as_the_website_user(self):
        status, replaced = self.post(api.scanner_replace_file, {
            'file_path': 'wp-content/plugins/demo.php', 'content': '<?php // clean\n'})
        self.assertEqual(200, status)
        self.assertTrue(replaced['success'])
        self.assertEqual(15, replaced['bytes_written'])
        self.assertEqual(hashlib.sha256(b'<?php // clean\n').hexdigest(), replaced['new_hash']['sha256'])
        target = os.path.join(self.root, 'wp-content', 'plugins', 'demo.php')
        self.assertEqual(b'<?php // clean\n', self.read(target))
        self.assertEqual(0o640, os.stat(target).st_mode & 0o777)
        self.assertTrue(self.helper.calls)
        for command, user in self.helper.calls:
            self.assertEqual(SITE_USER, user, command)
            self.assertNotIn('/tmp/scanner_temp_', command)
        self.assertEqual([], os.listdir(self.temp))

    def test_backups_are_kept_in_the_home_outside_the_served_folder(self):
        status, backup = self.post(api.scanner_backup_file, {'file_path': 'readme.txt', 'scan_id': SCAN_ID})
        self.assertEqual(200, status)
        self.assertTrue(backup['success'])
        self.assertEqual(8, backup['backup_size'])
        self.assertTrue(backup['backup_path'].startswith(os.path.join(self.home, '.ai-scanner-backups') + os.sep))
        self.assertEqual(b'read me\n', self.read(backup['backup_path']))
        self.assertFalse(os.path.exists(os.path.join(self.root, '.ai-scanner-backups')))
        status, replaced = self.post(api.scanner_replace_file, {'file_path': 'readme.txt', 'content': 'new\n'})
        self.assertEqual(200, status)
        self.assertTrue(replaced['backup_path'].startswith(os.path.join(self.home, '.ai-scanner-backups') + os.sep))
        self.assertFalse(os.path.exists(os.path.join(self.root, '.ai-scanner-backups')))

    def test_renaming_quarantines_a_file_for_the_fixer(self):
        status, renamed = self.post(api.scanner_rename_file, {
            'old_path': 'wp-content/plugins/demo.php', 'new_path': 'wp-content/plugins/demo.php.quarantined.1730000000'})
        self.assertEqual((200, True), (status, renamed['success']))
        self.assertEqual(['demo.php.quarantined.1730000000'], os.listdir(os.path.join(self.root, 'wp-content', 'plugins')))

    def test_renaming_into_another_folder_is_refused(self):
        for new_path in ('wp-content/readme.txt', 'wp-content/plugins/readme.txt.quarantined.1', 'missing/readme.txt'):
            status, reply = self.post(api.scanner_rename_file, {'old_path': 'readme.txt', 'new_path': new_path})
            self.assertEqual((403, False, 'RENAME_OTHER_FOLDER'), (status, reply['success'], reply['error_code']))
        self.assertEqual([], self.helper.calls)
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))

    def test_a_helper_that_calls_every_command_a_success_does_not_decide_the_answer(self):
        self.helper.honest = False
        for view, payload in (
                (api.scanner_backup_file, {'file_path': 'missing.php', 'scan_id': SCAN_ID}),
                (api.scanner_replace_file, {'file_path': 'missing.php', 'content': 'x'}),
                (api.scanner_rename_file, {'old_path': 'missing.php', 'new_path': 'missing.php.quarantined.1'}),
                (api.scanner_delete_file, {'file_path': 'missing.php', 'confirm_deletion': True}),
        ):
            status, reply = self.post(view, payload)
            self.assertEqual((404, False, 'FILE_NOT_FOUND'), (status, reply['success'], reply['error_code']))
        self.assertEqual(404, self.get(api.scanner_get_file, file_path='missing.php')[0])
        self.assertEqual(404, self.get(api.get_file_content, path='missing.php')[0])
        self.assertFalse(os.path.exists(os.path.join(self.root, 'missing.php')))
        status, backup = self.post(api.scanner_backup_file, {'file_path': 'readme.txt', 'scan_id': SCAN_ID})
        self.assertEqual((200, b'read me\n'), (status, self.read(backup['backup_path'])))
        status, renamed = self.post(api.scanner_rename_file, {
            'old_path': 'readme.txt', 'new_path': 'readme.txt.quarantined.1730000000'})
        self.assertEqual((200, True), (status, renamed['success']))
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt.quarantined.1730000000'))
        status, deleted = self.post(api.scanner_delete_file, {
            'file_path': 'wp-content/plugins/demo.php', 'confirm_deletion': True})
        self.assertEqual((200, hashlib.sha256(b'<?php // demo\n').hexdigest()),
                         (status, deleted['file_info']['hash']))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'wp-content', 'plugins', 'demo.php')))

    def test_a_website_without_a_system_user_gets_no_file_access(self):
        self.auth = api.AuthWrapper('secai.test', self.root, 'api_key', external_app='', source_obj=SimpleNamespace())
        self.assertEqual(404, self.get(api.list_files, path='.')[0])
        self.assertEqual(404, self.get(api.get_file_content, path='readme.txt')[0])
        self.assertEqual(500, self.get(api.scanner_get_file, file_path='readme.txt')[0])
        status, replaced = self.post(api.scanner_replace_file, {'file_path': 'readme.txt', 'content': 'x'})
        self.assertEqual((500, 'NO_USER'), (status, replaced['error_code']))
        self.assertEqual([], self.helper.calls)

    def test_the_file_token_of_a_scan_only_reads(self):
        self.auth = api.AuthWrapper('secai.test', self.root, 'file_token', external_app=SITE_USER,
                                    source_obj=SimpleNamespace())
        self.assertEqual(200, self.get(api.list_files, path='.')[0])
        self.assertEqual(200, self.get(api.get_file_content, path='readme.txt')[0])
        self.assertEqual(200, self.get(api.scanner_get_file, file_path='readme.txt')[0])
        del self.helper.calls[:]
        for view, payload in (
                (api.scanner_replace_file, {'file_path': 'readme.txt', 'content': 'changed\n'}),
                (api.scanner_rename_file, {'old_path': 'readme.txt', 'new_path': 'readme.txt.quarantined.1'}),
                (api.scanner_delete_file, {'file_path': 'readme.txt', 'confirm_deletion': True}),
                (api.scanner_backup_file, {'file_path': 'readme.txt', 'scan_id': SCAN_ID}),
        ):
            status, reply = self.post(view, payload)
            self.assertEqual((403, False, 'READ_ONLY_TOKEN'), (status, reply['success'], reply['error_code']))
        self.assertEqual([], self.helper.calls)
        self.assertEqual(b'read me\n', self.read(self.root, 'readme.txt'))
        self.assertFalse(os.path.exists(os.path.join(self.home, '.ai-scanner-backups')))
