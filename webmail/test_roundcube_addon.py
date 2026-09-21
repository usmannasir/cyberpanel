"""Behavioral checks for the paid gateway, transport and management boundary.

Run with Django installed: python -m unittest webmail.test_roundcube_addon
No database, root privilege or network access is required.
"""
import importlib
from contextlib import nullcontext
import sqlite3
import io
import json
import os
import pwd
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tarfile
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

from django.conf import settings
if not settings.configured:
    settings.configure(DEFAULT_CHARSET='utf-8', ALLOWED_HOSTS=['testserver'],
                       SECRET_KEY='roundcube-unit-tests-only', USE_TZ=True)
from django.test import RequestFactory
from django.core.cache import cache

# The boundary test uses Django's real requests/responses. Project ACL/database
# imports are replaced only while loading the isolated optional integration.
acl_module = types.ModuleType('plogical.acl')
acl_module.ACLManager = Mock()
http_module = types.ModuleType('plogical.httpProc')
http_module.httpProc = Mock()
with patch.dict(sys.modules, {'plogical.acl': acl_module, 'plogical.httpProc': http_module}):
    from webmail import roundcube
from plogical import roundcubeRuntime as runtime


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()
        roundcube.ACLManager.reset_mock()

    def request(self, path='/roundcube/', **kw):
        return self.factory.get(path, secure=True, **kw)

    def test_named_and_all_entitlements_accept_only_integer_one(self):
        for malformed in (True, '1', {'status': 1}, None, 0, -1):
            cache.clear()
            roundcube.ACLManager.CheckForPremFeature.return_value = malformed
            self.assertFalse(roundcube.entitled())
        cache.clear()
        roundcube.ACLManager.CheckForPremFeature.side_effect = [0, 1]
        self.assertTrue(roundcube.entitled())
        self.assertEqual(('roundcube',), roundcube.ACLManager.CheckForPremFeature.call_args.args)
        roundcube.ACLManager.CheckForPremFeature.side_effect = None

    def test_lookup_failure_is_denied_and_cached_for_bounded_time(self):
        roundcube.ACLManager.CheckForPremFeature.side_effect = RuntimeError('offline')
        with patch.object(roundcube.cache, 'set', wraps=cache.set) as save:
            self.assertFalse(roundcube.entitled())
            self.assertEqual(10, save.call_args.args[2])
        roundcube.ACLManager.CheckForPremFeature.side_effect = None
        cache.clear()
        roundcube.ACLManager.CheckForPremFeature.return_value = 1
        with patch.object(roundcube.cache, 'set', wraps=cache.set) as save:
            self.assertTrue(roundcube.entitled())
            self.assertEqual(60, save.call_args.args[2])

    def test_unlicensed_direct_entry_and_assets_never_reach_php(self):
        with patch.object(roundcube, 'entitled', return_value=False), patch.object(roundcube, 'fastcgi') as backend:
            for path in ('', 'index.php', 'static.php/skins/elastic/styles/styles.css'):
                self.assertEqual(403, roundcube.gateway(self.request(), path).status_code)
            backend.assert_not_called()

    def test_forbidden_scripts_and_traversals_never_reach_php(self):
        with patch.object(roundcube, 'fastcgi') as backend:
            for path in ('installer.php', 'config/config.inc.php', 'SQL/sqlite.initial.sql',
                         '../index.php', 'index.php/a', 'static.php/../config/config.inc.php',
                         'static.php/skins\\foo.css', 'static.php/\0'):
                self.assertEqual(404, roundcube.gateway(self.request(), path).status_code, path)
            backend.assert_not_called()

    def test_plain_http_is_refused_before_credentials_are_forwarded(self):
        request = self.factory.post('/roundcube/', {'_pass': 'secret'})
        with patch.object(roundcube, 'fastcgi') as backend:
            self.assertEqual(400, roundcube.gateway(request).status_code)
            backend.assert_not_called()

    def test_disabled_entitled_client_is_not_forwarded(self):
        with patch.object(roundcube, 'entitled', return_value=True), patch.object(roundcube, 'ENABLED', Path('/does-not-exist')), patch.object(roundcube, 'fastcgi') as backend:
            self.assertEqual(503, roundcube.gateway(self.request()).status_code)
            backend.assert_not_called()

    def test_only_roundcube_cookies_and_safe_headers_are_forwarded(self):
        request = self.factory.post('/roundcube/index.php?_task=login', data='_user=a%40b.c&_pass=secret',
                                    content_type='application/x-www-form-urlencoded', secure=True,
                                    HTTP_COOKIE='cyberpanel_sessionid=panel-secret; cp_roundcube_session=mail-session',
                                    HTTP_AUTHORIZATION='Bearer secret', HTTP_X_FORWARDED_HOST='attacker.test',
                                    HTTP_X_ROUNDCUBE_REQUEST='roundcube-csrf-token')
        with tempfile.NamedTemporaryFile() as enabled, patch.object(roundcube, 'ENABLED', Path(enabled.name)), patch.object(roundcube, 'entitled', return_value=True), patch.object(roundcube, 'fastcgi', return_value=b'Content-Type: text/html\r\n\r\nok') as backend:
            result = roundcube.gateway(request, 'index.php')
            self.assertEqual(200, result.status_code)
            params, body = backend.call_args.args
            self.assertEqual(b'_user=a%40b.c&_pass=secret', body)
            self.assertNotIn('panel-secret', params['HTTP_COOKIE'])
            self.assertNotIn('HTTP_AUTHORIZATION', params)
            self.assertNotIn('HTTP_X_FORWARDED_HOST', params)
            self.assertEqual('roundcube-csrf-token', params['HTTP_X_ROUNDCUBE_REQUEST'])
            self.assertTrue(params['SCRIPT_FILENAME'].endswith('/public_html/index.php'))
            self.assertEqual('private, no-store', result['Cache-Control'])

    def test_upload_limit_and_runtime_failure_return_safe_errors(self):
        with tempfile.NamedTemporaryFile() as enabled, patch.object(roundcube, 'ENABLED', Path(enabled.name)), patch.object(roundcube, 'entitled', return_value=True), patch.object(roundcube, 'fastcgi', side_effect=OSError('mail password secret')) as backend:
            self.assertEqual(502, roundcube.gateway(self.request()).status_code)
            request = self.request(CONTENT_LENGTH=str(roundcube.MAX_REQUEST + 1))
            self.assertEqual(413, roundcube.gateway(request).status_code)
            self.assertEqual(1, backend.call_count)

    def test_cookies_have_separate_names_and_path_and_security_flags(self):
        raw = (b'Status: 302 Found\r\nLocation: ./?_task=mail\r\n'
               b'Set-Cookie: cp_roundcube_session=abc; Path=/; Domain=evil.test\r\n'
               b'Set-Cookie: cp_roundcube_auth=def; Path=/\r\n'
               b'Set-Cookie: cyberpanel_sessionid=replace\r\n\r\n')
        response = roundcube.cgi_response(raw)
        self.assertEqual(302, response.status_code)
        self.assertEqual(2, len(response.cookies))
        for value in response.cookies.values():
            self.assertEqual('/roundcube/', value['path'])
            self.assertEqual('', value['domain'])
            self.assertTrue(value['secure'])
            self.assertTrue(value['httponly'])
            self.assertEqual('Lax', value['samesite'])

    def test_external_redirects_and_broken_headers_are_rejected(self):
        for raw in (b'Location: https://evil.test/\r\n\r\n', b'Location: //evil.test/\r\n\r\n',
                    b'invalid\r\n\r\n', b'no headers'):
            with self.assertRaises(OSError):
                roundcube.cgi_response(raw)

    def test_administrator_and_entitlement_required_to_install(self):
        request = self.factory.post('/webmail/roundcube/operate', data=json.dumps({'action': 'install'}), content_type='application/json')
        request.session = {}
        with patch.object(roundcube.subprocess, 'Popen') as process:
            self.assertEqual(403, roundcube.operate(request).status_code)
            process.assert_not_called()
        request.session = {'userID': 1}
        roundcube.ACLManager.loadedACL.return_value = {'admin': 1}
        with patch.object(roundcube, 'entitled', return_value=False), patch.object(roundcube.subprocess, 'Popen') as process:
            self.assertEqual(403, roundcube.operate(request).status_code)
            process.assert_not_called()

    def test_expired_entitlement_can_still_disable_but_cannot_inject_commands(self):
        roundcube.ACLManager.loadedACL.return_value = {'admin': 1}
        with patch.object(roundcube, 'entitled', return_value=False), patch.object(roundcube.subprocess, 'Popen') as process:
            process.return_value.wait.return_value = 0
            for action, expected in [('disable', 202), ('disable; touch /tmp/x', 400)]:
                request = self.factory.post('/webmail/roundcube/operate', data=json.dumps({'action': action}), content_type='application/json')
                request.session = {'userID': 1}
                self.assertEqual(expected, roundcube.operate(request).status_code)
            self.assertEqual(1, process.call_count)
            self.assertEqual('disable', process.call_args.args[0][-1])


class RuntimeTests(unittest.TestCase):
    def archive(self, directory, name, kind=tarfile.REGTYPE, linkname=''):
        path = Path(directory) / 'test.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.linkname = linkname
            member.size = 4 if kind == tarfile.REGTYPE else 0
            archive.addfile(member, io.BytesIO(b'test') if member.size else None)
        return path

    def test_archive_rejects_traversal_links_and_special_files(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = f'roundcubemail-{runtime.VERSION}/'
            for name, kind in [(prefix + '../escape', tarfile.REGTYPE), ('/etc/evil', tarfile.REGTYPE),
                               (prefix + 'link', tarfile.SYMTYPE), (prefix + 'hard', tarfile.LNKTYPE),
                               (prefix + 'fifo', tarfile.FIFOTYPE)]:
                archive = self.archive(directory, name, kind, '/etc/passwd')
                with self.assertRaises(RuntimeError):
                    runtime.checked_extract(archive, Path(directory) / 'output')

    def test_archive_extracts_only_below_version_root(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.archive(directory, f'roundcubemail-{runtime.VERSION}/public_html/index.php')
            output = Path(directory) / 'output'
            runtime.checked_extract(archive, output)
            self.assertEqual(b'test', (output / 'public_html/index.php').read_bytes())

    def test_checksum_mismatch_never_installs_payload(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runtime.urllib.request, 'urlopen', return_value=io.BytesIO(b'wrong archive')):
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                runtime.download(Path(directory) / 'archive')

    def test_key_is_private_and_stable_across_reconfiguration(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runtime, 'CONFIG', Path(directory)):
            first = runtime.php_config()
            second = runtime.php_config()
            self.assertEqual(first, second)
            self.assertEqual(0o600, (Path(directory) / 'key').stat().st_mode & 0o777)
            self.assertIn("$config['enable_installer'] = false;", first)
            self.assertIn("$config['session_path'] = '/roundcube/';", first)
            self.assertIn("$config['smtp_user'] = '%u';", first)

    def test_master_log_is_private_and_writable_through_the_service_sandbox(self):
        config = runtime.pool_config()
        service = runtime.service_config('/usr/sbin/php-fpm8.5')
        self.assertNotIn('/proc/self/fd/', config)
        self.assertIn(f'error_log = {runtime.MASTER_LOG_DIR}/fpm.log', config)
        self.assertIn('LogsDirectory=cyberpanel-roundcube', service)
        self.assertIn('LogsDirectoryMode=0700', service)
        self.assertIn(f'ReadWritePaths={runtime.DATA} /run/cyberpanel-roundcube {runtime.MASTER_LOG_DIR}', service)
        self.assertIn('ProtectSystem=strict', service)
        self.assertIn('NoNewPrivileges=true', service)
        self.assertIn('UMask=0077', service)
        self.assertNotEqual(runtime.DATA, runtime.MASTER_LOG_DIR.parent)

    def test_master_log_rejects_a_preplanted_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory) / 'logs'
            logs.mkdir()
            secret = Path(directory) / 'secret'
            secret.write_text('do not modify')
            (logs / 'fpm.log').symlink_to(secret)
            with patch.object(runtime, 'MASTER_LOG_DIR', logs), patch.object(runtime.os, 'fchown'):
                with self.assertRaises(OSError):
                    runtime.ensure_master_log()
            self.assertEqual('do not modify', secret.read_text())

    def test_fastcgi_stream_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            address = str(Path(directory) / 'php.sock')
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(address)
            server.listen(1)
            received = []
            errors = []
            def serve():
                try:
                    with server.accept()[0] as peer:
                        while True:
                            header = roundcube._read(peer, 8)
                            _, kind, _, length, padding, _ = struct.unpack('!BBHHBB', header)
                            content = roundcube._read(peer, length)
                            roundcube._read(peer, padding)
                            received.append((kind, content))
                            if kind == 5 and length == 0:
                                break
                        peer.sendall(roundcube._record(6, b'Content-Type: text/plain\r\n\r\nHello'))
                        peer.sendall(roundcube._record(7, b'private diagnostic'))
                        peer.sendall(roundcube._record(3, b'\0' * 8))
                except Exception as error:
                    errors.append(error)
            thread = threading.Thread(target=serve)
            thread.start()
            try:
                with patch.object(roundcube, 'SOCKET', address):
                    result = roundcube.fastcgi({'SCRIPT_NAME': '/roundcube/index.php'}, b'A' * 70000)
                self.assertEqual(b'Content-Type: text/plain\r\n\r\nHello', result)
                self.assertEqual(b'A' * 70000, b''.join(data for kind, data in received if kind == 5))
            finally:
                thread.join(timeout=3)
                server.close()
            self.assertFalse(errors)


class UpdateRollbackTests(unittest.TestCase):
    def setup_tree(self, directory):
        root = Path(directory) / 'app'
        data = Path(directory) / 'data'
        config = Path(directory) / 'config'
        root.mkdir(); data.mkdir(); config.mkdir()
        release = root / runtime.VERSION
        release.mkdir()
        (release / 'old-marker').write_text('original release')
        (root / 'current').symlink_to(release)
        (config / 'fpm.conf').write_text('original fpm')
        (config / 'enabled').write_text('1')
        database = data / 'roundcube.sqlite'
        with sqlite3.connect(database) as connection:
            connection.execute('CREATE TABLE contacts (name TEXT)')
            connection.execute("INSERT INTO contacts VALUES ('keep me')")
        return root, data, config, database

    def test_failed_backup_does_not_replace_the_live_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root, data, config, database = self.setup_tree(directory)
            initial = database.read_bytes()
            stale_previous = root / (runtime.VERSION + '.previous')
            stale_previous.mkdir()
            (stale_previous / 'stale-marker').write_text('must not replace current')
            identity = types.SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())
            def fake_extract(archive, candidate):
                (candidate / 'config').mkdir()
                (candidate / 'public_html').mkdir()
            failed_source = Mock()
            failed_source.backup.side_effect = sqlite3.OperationalError('disk full')
            with patch.multiple(runtime, ROOT=root, DATA=data, CONFIG=config, STATE=config/'state.json', ENABLED=config/'enabled', UNIT=config/'unit.service'), patch.object(runtime, 'find_php', return_value=('/usr/sbin/php-fpm', '/usr/bin/php')), patch.object(runtime, 'ensure_identity', return_value=identity), patch.object(runtime, 'ensure_master_log'), patch.object(runtime, 'download'), patch.object(runtime, 'checked_extract', side_effect=fake_extract), patch.object(runtime, 'runtime_identity', side_effect=lambda _: nullcontext()), patch.object(runtime.os, 'chown'), patch.object(runtime.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)), patch.object(runtime.sqlite3, 'connect', return_value=failed_source), patch.object(runtime, 'run', return_value=types.SimpleNamespace(returncode=0)):
                with self.assertRaises(sqlite3.OperationalError):
                    runtime.install()
            self.assertEqual(initial, database.read_bytes())
            self.assertTrue((root/'current'/'old-marker').is_file())
            self.assertFalse((root/'current'/'stale-marker').exists())
            self.assertEqual('original fpm', (config/'fpm.conf').read_text())

    def test_failed_migration_restores_verified_database_and_previous_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root, data, config, database = self.setup_tree(directory)
            identity = types.SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())
            def fake_extract(archive, candidate):
                (candidate / 'config').mkdir()
                (candidate / 'public_html').mkdir()
            def fake_run(argv, **kwargs):
                if argv[0] == 'runuser':
                    with sqlite3.connect(database) as connection:
                        connection.execute('DELETE FROM contacts')
                    raise subprocess.CalledProcessError(1, argv)
                return types.SimpleNamespace(returncode=0)
            with patch.multiple(runtime, ROOT=root, DATA=data, CONFIG=config, STATE=config/'state.json', ENABLED=config/'enabled', UNIT=config/'unit.service'), patch.object(runtime, 'find_php', return_value=('/usr/sbin/php-fpm', '/usr/bin/php')), patch.object(runtime, 'ensure_identity', return_value=identity), patch.object(runtime, 'ensure_master_log'), patch.object(runtime, 'download'), patch.object(runtime, 'checked_extract', side_effect=fake_extract), patch.object(runtime, 'runtime_identity', side_effect=lambda _: nullcontext()), patch.object(runtime.os, 'chown'), patch.object(runtime, 'run', side_effect=fake_run), patch.object(runtime.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)):
                with self.assertRaises(subprocess.CalledProcessError):
                    runtime.install()
            with sqlite3.connect(database) as connection:
                self.assertEqual([('keep me',)], connection.execute('SELECT name FROM contacts').fetchall())
            self.assertTrue((root/'current'/'old-marker').is_file())
            self.assertEqual('original fpm', (config/'fpm.conf').read_text())
            self.assertTrue((config/'enabled').exists())

    def test_runtime_identity_drops_supplementary_groups_and_restores_after_error(self):
        identity = types.SimpleNamespace(pw_uid=123, pw_gid=456)
        with patch.object(runtime.os, 'geteuid', return_value=0), patch.object(runtime.os, 'getegid', return_value=0), patch.object(runtime.os, 'getgroups', return_value=[0, 10]), patch.object(runtime.os, 'setgroups') as groups, patch.object(runtime.os, 'setegid') as gid, patch.object(runtime.os, 'seteuid') as uid:
            with self.assertRaises(RuntimeError):
                with runtime.runtime_identity(identity):
                    raise RuntimeError('simulated failure')
            self.assertEqual([unittest.mock.call([456]), unittest.mock.call([0, 10])], groups.call_args_list)
            self.assertEqual([unittest.mock.call(123), unittest.mock.call(0)], uid.call_args_list)
            self.assertEqual([unittest.mock.call(456), unittest.mock.call(0)], gid.call_args_list)


@unittest.skipUnless(os.geteuid() == 0 and os.environ.get('CYBERPANEL_ROUNDCUBE_ROOT_TESTS') == '1',
                     'Opt-in disposable-node test requires root to exercise real Unix permissions')
class RuntimePermissionTests(unittest.TestCase):
    def test_real_uid_backup_is_root_owned_and_restore_readable(self):
        identity = pwd.getpwnam('nobody')
        with tempfile.TemporaryDirectory(prefix='roundcube-permissions-') as directory:
            base = Path(directory)
            base.chmod(0o755)
            root, data = base/'releases', base/'data'
            root.mkdir(mode=0o755)
            data.mkdir(mode=0o700)
            os.chown(data, identity.pw_uid, identity.pw_gid)
            database = data/'database.sqlite'
            with runtime.runtime_identity(identity), sqlite3.connect(database) as connection:
                connection.execute('CREATE TABLE contacts (name TEXT)')
                connection.execute("INSERT INTO contacts VALUES ('private contact')")
            connection.close()
            with patch.object(runtime, 'ROOT', root):
                backup = runtime.backup_database(database, identity)
            self.assertEqual(0, backup.stat().st_uid)
            self.assertEqual(0o600, backup.stat().st_mode & 0o777)
            with sqlite3.connect(backup) as connection:
                self.assertEqual([('private contact',)], connection.execute('SELECT name FROM contacts').fetchall())
            connection.close()
            with runtime.runtime_identity(identity):
                with self.assertRaises(PermissionError):
                    backup.read_bytes()

    def test_runtime_database_symlink_cannot_read_root_private_database(self):
        identity = pwd.getpwnam('nobody')
        with tempfile.TemporaryDirectory(prefix='roundcube-permissions-') as directory:
            base = Path(directory)
            base.chmod(0o755)
            root, data = base/'releases', base/'data'
            root.mkdir(mode=0o755)
            data.mkdir(mode=0o700)
            os.chown(data, identity.pw_uid, identity.pw_gid)
            secret = base/'root-private.sqlite'
            with sqlite3.connect(secret) as connection:
                connection.execute('CREATE TABLE secrets (value TEXT)')
            connection.close()
            secret.chmod(0o600)
            original = secret.read_bytes()
            (data/'database.sqlite').symlink_to(secret)
            with patch.object(runtime, 'ROOT', root):
                with self.assertRaises(sqlite3.OperationalError):
                    runtime.backup_database(data/'database.sqlite', identity)
            self.assertEqual(original, secret.read_bytes())

if __name__ == '__main__':
    unittest.main()
