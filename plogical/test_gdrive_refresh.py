"""Synthetic-only refresh and repository-preservation regressions (no Google access)."""
import ast
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from plogical.gdriveRefresh import custom_client, drive_credentials, legacy_access_token, update_legacy_remote, update_legacy_remote_as_user


class FakeCredentials:
    fail = False
    refreshes = 0

    def __init__(self, token, refresh_token=None, token_uri=None, client_id=None, client_secret=None, scopes=None, expiry=None):
        self.token, self.refresh_token, self.expiry = token, refresh_token, expiry
        self.client_id, self.client_secret, self.token_uri = client_id, client_secret, token_uri

    @property
    def expired(self):
        return self.expiry is not None and self.expiry < datetime.utcnow() + timedelta(minutes=4)

    def refresh(self, request):
        type(self).refreshes += 1
        if self.fail:
            raise RuntimeError('secret-that-must-not-appear')
        self.token = 'synthetic-new-token'
        self.expiry = datetime.utcnow() + timedelta(hours=1)


class RefreshTests(unittest.TestCase):
    def setUp(self):
        FakeCredentials.fail, FakeCredentials.refreshes = False, 0
        modules = {
            'google': types.ModuleType('google'), 'google.oauth2': types.ModuleType('google.oauth2'),
            'google.oauth2.credentials': types.SimpleNamespace(Credentials=FakeCredentials),
            'google.auth': types.ModuleType('google.auth'), 'google.auth.transport': types.ModuleType('google.auth.transport'),
            'google.auth.transport.requests': types.SimpleNamespace(Request=Mock(return_value=object())),
        }
        self.google = patch.dict('sys.modules', modules)
        self.google.start()
        self.addCleanup(self.google.stop)
        self.auth = dict(token='synthetic-token', refresh_token='synthetic-refresh',
                         token_uri='https://oauth2.googleapis.com/token', scopes=['https://www.googleapis.com/auth/drive.file'],
                         client_id='qa.apps.googleusercontent.com', client_secret='synthetic-secret', handoff_version=2,
                         expiry=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(), folderIDIP='keep-folder', FileRetentiontime=7)

    def test_custom_valid_does_not_refresh(self):
        with patch('plogical.gdriveRefresh.legacy_access_token') as legacy:
            credentials, result = drive_credentials(self.auth)
        self.assertEqual(result, self.auth)
        self.assertIsNot(result, self.auth)
        self.assertEqual(credentials.client_id, self.auth['client_id'])
        self.assertEqual(FakeCredentials.refreshes, 0)
        legacy.assert_not_called()

    def test_expired_own_client_refresh_preserves_metadata(self):
        self.auth['expiry'] = '2020-01-01T00:00:00Z'
        before = copy.deepcopy(self.auth)
        with patch('plogical.gdriveRefresh.legacy_access_token') as legacy:
            credentials, result = drive_credentials(self.auth)
        self.assertEqual(result['token'], 'synthetic-new-token')
        self.assertEqual(result['folderIDIP'], 'keep-folder')
        self.assertEqual(result['FileRetentiontime'], 7)
        self.assertEqual(self.auth, before)
        legacy.assert_not_called()

    def test_failure_never_mutates_or_falls_back(self):
        FakeCredentials.fail = True
        before = copy.deepcopy(self.auth)
        with patch('plogical.gdriveRefresh.legacy_access_token') as legacy:
            with self.assertRaisesRegex(ValueError, '^Google Drive authorization failed$'):
                drive_credentials(self.auth, force_refresh=True)
        self.assertEqual(self.auth, before)
        legacy.assert_not_called()

    def test_malformed_custom_cannot_be_legacy(self):
        for key, value in [('handoff_version', True), ('token_uri', 'https://evil.invalid/token'),
                           ('client_secret', ''), ('expiry', 'bad'), ('token', 'None')]:
            candidate = dict(self.auth, **{key: value})
            with self.subTest(key=key), patch('plogical.gdriveRefresh.legacy_access_token') as legacy:
                with self.assertRaises(ValueError):
                    drive_credentials(candidate, True)
                legacy.assert_not_called()

    def test_legacy_results_compatible(self):
        legacy = {key: self.auth[key] for key in ('token', 'refresh_token', 'token_uri', 'scopes')}
        credentials, result = drive_credentials(legacy)
        self.assertEqual(result, legacy)
        self.assertIsNone(credentials.client_id)
        with patch('plogical.gdriveRefresh.legacy_access_token', return_value='legacy-new') as refresh:
            credentials, result = drive_credentials(legacy, True)
        refresh.assert_called_once_with('synthetic-refresh')
        self.assertEqual(result['token'], 'legacy-new')
        self.assertEqual(legacy['token'], 'synthetic-token')

    def test_legacy_blank_clients_still_use_shared_refresh(self):
        legacy = {key: self.auth[key] for key in ('token', 'refresh_token', 'token_uri', 'scopes')}
        legacy.update(client_id='', client_secret='')
        with patch('plogical.gdriveRefresh.legacy_access_token', return_value='legacy-new') as refresh:
            credentials, result = drive_credentials(legacy, True)
        refresh.assert_called_once_with('synthetic-refresh')
        self.assertEqual(result['token'], 'legacy-new')
        self.assertIsNone(credentials.client_id)
        legacy['handoff_version'] = 2
        with patch('plogical.gdriveRefresh.legacy_access_token') as refresh:
            with self.assertRaises(ValueError):
                drive_credentials(legacy, True)
            refresh.assert_not_called()

    def test_legacy_request_endpoint_and_error_redaction(self):
        response = Mock()
        response.json.return_value = {'access_token': 'legacy-access'}
        requests = types.SimpleNamespace(post=Mock(return_value=response))
        with patch.dict('sys.modules', {'requests': requests}):
            self.assertEqual(legacy_access_token('synthetic-refresh'), 'legacy-access')
            self.assertEqual(requests.post.call_args.args[0], 'https://platform.cyberpersons.com/refreshToken')
            self.assertEqual(json.loads(requests.post.call_args.kwargs['data']), {'refresh_token': 'synthetic-refresh'})
            response.json.return_value = {'access_token': None}
            with self.assertRaisesRegex(ValueError, '^Google Drive authorization failed$'):
                legacy_access_token('synthetic-refresh')

    def test_file_backed_fake_drive_refresh_upload_restore(self):
        """Execute the actual scheduler upload retry against a file-backed fake."""
        before = copy.deepcopy(self.auth)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentinel = root / 'existing-backup.bin'
            sentinel.write_bytes(b'existing backup must remain untouched')
            archive = b'synthetic archive fixture\x00restore proof'
            source = root / 'local-fixture.tar.gz'
            source.write_bytes(archive)

            class FakeDrive:
                def __init__(self, valid):
                    self.valid = valid

                def files(self):
                    return self

                def create(self, body, media_body, fields):
                    self.source = media_body
                    return self

                def execute(self):
                    if not self.valid:
                        raise RuntimeError('Synthetic expired access token')
                    (root / 'uploaded-fixture.tar.gz').write_bytes(Path(self.source).read_bytes())
                    return {'id': 'synthetic-new-file'}

            scheduler = ast.parse(Path(__file__).with_name('IncScheduler.py').read_text())
            method = next(x for x in ast.walk(scheduler) if isinstance(x, ast.FunctionDef) and x.name == 'runGoogleDriveBackups')
            upload_try = next(x for x in ast.walk(method) if isinstance(x, ast.Try)
                              and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                                      and call.func.attr == 'create' and any(k.arg == 'media_body' for k in call.keywords)
                                      for call in ast.walk(ast.Module(body=x.body, type_ignores=[]))))
            # Choose the smallest enclosing try: exactly the scheduler's upload
            # and retry, not its outer backup/retention/filesystem workflow.
            candidates = [x for x in ast.walk(upload_try) if isinstance(x, ast.Try)
                          and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                                  and call.func.attr == 'create' and any(k.arg == 'media_body' for k in call.keywords)
                                  for call in ast.walk(ast.Module(body=x.body, type_ignores=[])))]
            upload_try = min(candidates, key=lambda x: len(list(ast.walk(x))))
            items = types.SimpleNamespace(auth=json.dumps(self.auth), save=Mock())
            namespace = dict(drive=FakeDrive(False), file_metadata={'name': 'fixture'}, media=str(source),
                             gDriveData=copy.deepcopy(self.auth), drive_credentials=drive_credentials,
                             build=lambda *a, **kw: FakeDrive(kw['credentials'].token == 'synthetic-new-token'),
                             items=items, json=json)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[upload_try], type_ignores=[])), '<scheduler upload retry>', 'exec'), namespace)
            self.assertEqual((root / 'uploaded-fixture.tar.gz').read_bytes(), archive)
            self.assertEqual(sentinel.read_bytes(), b'existing backup must remain untouched')
            self.assertEqual(self.auth, before)
            self.assertEqual(json.loads(items.auth)['folderIDIP'], before['folderIDIP'])
            items.save.assert_called_once()
            self.assertEqual(FakeCredentials.refreshes, 1)


@unittest.skipIf(os.geteuid() == 0, 'Run configuration mutation tests as an unprivileged fixture user')
class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'rclone.conf'
        self.old = (b'# preserve comment\n[sentinel]\ntype = local\ncustom = original\n\n[legacy]\n'
                    b'type = drive\n# keep this\ntoken = {"access_token":"old","refresh_token":"refresh"}\n'
                    b'root_folder_id = keep-me\n[after]\ntype = sftp\npassword = unchanged\n')
        self.path.write_bytes(self.old)
        self.path.chmod(0o600)

    def update(self, **kwargs):
        update_legacy_remote(str(self.path), 'legacy', 'new', 'refresh', os.geteuid(), **kwargs)

    def test_exact_unrelated_bytes_and_permissions_preserved(self):
        self.update()
        old_lines, new_lines = self.old.splitlines(), self.path.read_bytes().splitlines()
        self.assertEqual([x for x in old_lines if not x.startswith(b'token =')],
                         [x for x in new_lines if not x.startswith(b'token =')])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.stat().st_uid, os.geteuid())
        token = json.loads(next(x.split(b'=', 1)[1] for x in new_lines if x.startswith(b'token =')))
        self.assertEqual(token['access_token'], 'new')
        self.assertNotIn('2024', token['expiry'])

    def test_none_or_failure_never_overwrites(self):
        with self.assertRaises(ValueError):
            update_legacy_remote(str(self.path), 'legacy', None, 'refresh', os.geteuid())
        with patch('os.replace', side_effect=OSError('fixture failure')):
            with self.assertRaises(OSError):
                self.update()
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_concurrent_native_atomic_replacement_is_not_overwritten(self):
        original_fsync = os.fsync
        replacement = self.path.with_name('native.conf')
        changed = self.old + b'# native writer replacement\n'
        replacement.write_bytes(changed)
        replacement.chmod(0o600)
        fired = []

        def native_writer(descriptor):
            original_fsync(descriptor)
            if not fired:
                fired.append(True)
                os.replace(str(replacement), str(self.path))

        with patch('os.fsync', side_effect=native_writer):
            with self.assertRaisesRegex(ValueError, 'changed concurrently'):
                self.update()
        self.assertEqual(self.path.read_bytes(), changed)
        self.assertFalse(list(self.path.parent.glob('.gdrive-refresh-*')))

    def test_concurrent_native_inplace_write_is_not_overwritten(self):
        original_fsync = os.fsync
        changed = self.old + b'# native writer in-place edit\n'
        fired = []

        def native_writer(descriptor):
            original_fsync(descriptor)
            if not fired:
                fired.append(True)
                self.path.write_bytes(changed)

        with patch('os.fsync', side_effect=native_writer):
            with self.assertRaisesRegex(ValueError, 'changed concurrently'):
                self.update()
        self.assertEqual(self.path.read_bytes(), changed)
        self.assertFalse(list(self.path.parent.glob('.gdrive-refresh-*')))

    def test_custom_config_never_overwritten(self):
        self.path.write_bytes(self.old.replace(b'# keep this', b'client_id = own.apps.googleusercontent.com'))
        old = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.update()
        self.assertEqual(self.path.read_bytes(), old)

    def test_blank_legacy_client_fields_and_old_remote_names(self):
        self.path.write_bytes(self.old.replace(b'[legacy]', b'[drive.backup legacy]').replace(
            b'# keep this', b'client_id =\nclient_secret =\n# keep this'))
        update_legacy_remote(str(self.path), 'drive.backup legacy', 'new', 'refresh', os.geteuid())
        data = self.path.read_bytes()
        self.assertIn(b'client_id =\nclient_secret =\n# keep this', data)
        self.assertIn(b'[drive.backup legacy]', data)
        self.assertIn(b'"access_token":"new"', data)

    def test_actual_unprivileged_cli_updates_only_fixture(self):
        import subprocess
        import sys
        home = self.path.parent
        target = home / '.config/rclone/rclone.conf'
        target.parent.mkdir(parents=True, mode=0o700)
        target.write_bytes(self.old)
        target.chmod(0o600)
        command = [sys.executable, str(Path(__file__).with_name('gdriveRefresh.py').resolve()), '--home', str(home)]
        result = subprocess.run(command, input=json.dumps({'remote': 'legacy', 'access_token': 'synthetic-cli-access',
                                                          'refresh_token': 'refresh'}).encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.stat().st_uid, os.geteuid())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertIn(b'"access_token":"synthetic-cli-access"', target.read_bytes())
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_symlink_and_concurrent_change_rejected(self):
        with self.assertRaises(ValueError):
            update_legacy_remote(str(self.path), 'legacy', 'new', 'wrong-refresh', os.geteuid())
        alias = self.path.parent / 'alias.conf'
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            update_legacy_remote(str(alias), 'legacy', 'new', 'refresh', os.geteuid())
        self.assertEqual(self.path.read_bytes(), self.old)


class InstalledGoogleAuthTests(unittest.TestCase):
    def test_real_google_auth_uses_only_own_client_with_mock_transport(self):
        """Runs on QA's installed google-auth; no real OAuth network or account."""
        try:
            from google.auth.transport.requests import Request
        except ImportError:
            self.skipTest('Installed google-auth is checked on the owned QA runtime')
        from urllib.parse import parse_qs
        calls = []

        def transport(**kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(status=200, headers={}, data=json.dumps({
                'access_token': 'synthetic-real-lib-new', 'expires_in': 3600,
                'token_type': 'Bearer',
            }).encode('utf-8'))

        auth = dict(token='old-synthetic-token', refresh_token='synthetic-refresh', handoff_version=2,
                    client_id='qa.apps.googleusercontent.com', client_secret='synthetic-secret',
                    token_uri='https://oauth2.googleapis.com/token', expiry='2020-01-01T00:00:00Z',
                    scopes=['https://www.googleapis.com/auth/drive.file'], folderIDIP='preserve-existing-folder')
        before = copy.deepcopy(auth)
        with patch('google.auth.transport.requests.Request', return_value=transport), patch('plogical.gdriveRefresh.legacy_access_token') as legacy:
            credentials, result = drive_credentials(auth)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['url'], 'https://oauth2.googleapis.com/token')
        body = calls[0]['body']
        body = body.decode() if isinstance(body, bytes) else body
        self.assertEqual(parse_qs(body)['client_id'], [auth['client_id']])
        self.assertEqual(parse_qs(body)['client_secret'], [auth['client_secret']])
        self.assertEqual(result['token'], 'synthetic-real-lib-new')
        self.assertEqual(auth, before)
        legacy.assert_not_called()


class SourceBoundaryTests(unittest.TestCase):
    def test_writer_caller_passes_secrets_only_on_stdin(self):
        owner = types.SimpleNamespace(pw_uid=12345, pw_dir='/home/owned.example')
        with patch('pwd.getpwnam', return_value=owner), patch('subprocess.run', return_value=types.SimpleNamespace(returncode=0)) as run:
            update_legacy_remote_as_user('owned.example', 'fixtureuser', 'legacy', 'synthetic-secret-access', 'synthetic-secret-refresh')
        args = run.call_args.args[0]
        self.assertEqual(args[:4], ['sudo', '-n', '-u', 'fixtureuser'])
        self.assertNotIn('synthetic-secret', ' '.join(args))
        self.assertEqual(json.loads(run.call_args.kwargs['input'])['access_token'], 'synthetic-secret-access')
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_root_owner_or_mismatched_home_rejected_before_process(self):
        for owner in (types.SimpleNamespace(pw_uid=0, pw_dir='/home/owned.example'),
                      types.SimpleNamespace(pw_uid=12345, pw_dir='/home/another.example')):
            with patch('pwd.getpwnam', return_value=owner), patch('subprocess.run') as run:
                with self.assertRaises(ValueError):
                    update_legacy_remote_as_user('owned.example', 'fixtureuser', 'legacy', 'access', 'refresh')
                run.assert_not_called()

    def test_v2_constructor_custom_skips_shared_refresh(self):
        source = Path(__file__).with_name('Backupsv2.py').read_text()
        module = ast.parse(source)
        cls = next(x for x in module.body if isinstance(x, ast.ClassDef) and x.name == 'CPBackupsV2')
        init = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == '__init__')
        # Execute only the credential-handling try block, not the constructor's
        # installer, status-file deletion, or other unrelated side effects.
        block = next(x for x in ast.walk(init) if isinstance(x, ast.If) and isinstance(x.test, ast.Compare)
                     and isinstance(x.test.left, ast.Name) and x.test.left.id == 'reponame')
        output = Mock(return_value=json.dumps({'custom': {'type': 'drive', 'client_id': 'own',
                                                         'client_secret': 'own-secret', 'token': '{"refresh_token":"refresh"}'}}))
        owner = types.SimpleNamespace(website=types.SimpleNamespace(externalApp='fixture'), refresh_V2Gdive_token=Mock())
        namespace = dict(self=owner, reponame='custom', ProcessUtilities=types.SimpleNamespace(outputExecutioner=output),
                         json=json, custom_client=custom_client)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[block], type_ignores=[])), '<v2 credential block>', 'exec'), namespace)
        owner.refresh_V2Gdive_token.assert_not_called()
        self.assertEqual(output.call_count, 1)

    def test_v2_blank_legacy_client_uses_broker_and_user_boundary(self):
        module = ast.parse(Path(__file__).with_name('Backupsv2.py').read_text())
        cls = next(x for x in module.body if isinstance(x, ast.ClassDef) and x.name == 'CPBackupsV2')
        init = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == '__init__')
        block = next(x for x in ast.walk(init) if isinstance(x, ast.If) and isinstance(x.test, ast.Compare)
                     and isinstance(x.test.left, ast.Name) and x.test.left.id == 'reponame')
        output = Mock(return_value=json.dumps({'drive.backup legacy': {'type': 'drive', 'client_id': '',
                              'client_secret': '', 'token': '{"refresh_token":"refresh"}'}}))
        owner = types.SimpleNamespace(website=types.SimpleNamespace(externalApp='fixture', domain='owned.example'),
                                      refresh_V2Gdive_token=Mock(return_value='legacy-access'))
        update = Mock()
        namespace = dict(self=owner, reponame='drive.backup legacy', ProcessUtilities=types.SimpleNamespace(outputExecutioner=output),
                         json=json, custom_client=custom_client, update_legacy_remote_as_user=update)
        compiled = compile(ast.fix_missing_locations(ast.Module(body=[block], type_ignores=[])), '<v2 credential block>', 'exec')
        exec(compiled, namespace)
        owner.refresh_V2Gdive_token.assert_called_once_with('refresh')
        update.assert_called_once_with('owned.example', 'fixture', 'drive.backup legacy', 'legacy-access', 'refresh')
        owner.refresh_V2Gdive_token.return_value = None
        update.reset_mock()
        exec(compiled, namespace)
        update.assert_not_called()

    def test_scheduler_uses_helper_initial_and_both_retry_paths(self):
        module = ast.parse(Path(__file__).with_name('IncScheduler.py').read_text())
        method = next(x for x in ast.walk(module) if isinstance(x, ast.FunctionDef) and x.name == 'runGoogleDriveBackups')
        calls = [x for x in ast.walk(method) if isinstance(x, ast.Call)]
        helpers = [x for x in calls if isinstance(x.func, ast.Name) and x.func.id == 'drive_credentials']
        self.assertEqual(len(helpers), 3)
        self.assertEqual(sum(bool(x.keywords) for x in helpers), 2)
        self.assertFalse(any(isinstance(x, ast.Constant) and x.value == 'https://platform.cyberpersons.com/refreshToken'
                             for x in ast.walk(method)))


if __name__ == '__main__':
    unittest.main()
