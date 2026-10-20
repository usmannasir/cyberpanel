"""Real PHP HTTP cookies and bundled signon authentication; fixture data only.

Run with Python and a PHP CLI with cURL enabled. The only HTTP listeners and
requests are on localhost; no panel settings, database, or external service is used.
"""
import hashlib
import http.cookiejar
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VENDOR_HASHES = {
    'AuthenticationPlugin.php': '4c9456b2df4681251dbfcfe1d95670031ccb3fc2a9a64f6420ecc6327c7881b0',
    'AuthenticationSignon.php': '4930ca9e147cca4282921cc1e0789db47495d7fccd09da1a381502031cf06599',
}
ROUTER = r'''<?php
namespace PhpMyAdmin {
    class Session { public static function secure() {} }
    class Util { public static function clearUserCache() {} }
}
namespace {
ini_set('session.save_path', __DIR__ . '/sessions');
ini_set('session.use_cookies', '1');
ini_set('session.use_only_cookies', '1');
ini_set('session.use_strict_mode', '1');
$settings = json_decode(file_get_contents(__DIR__ . '/fixture.json'), true);
define('PMA_SESSION_VALIDATION_URL', $settings['validator']);
$params = $settings['params'];
$phase = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if ($phase === '/scope/seed') {
    setcookie('cyberpanel_sessionid', 'fixturePanelSession0123456789', array('path'=>'/'));
    session_set_cookie_params($params + array('path'=>'/'));
    session_name('SignonSession'); session_start(); session_regenerate_id(true);
    $_SESSION = array('PMA_panel_session'=>'fixturePanelSession0123456789',
        'PMA_panel_grant'=>str_repeat('a',64), 'PMA_single_signon_user'=>'fixtureOnlyUser',
        'PMA_single_signon_password'=>'fixtureOnlyPassword', 'PMA_single_signon_host'=>'fixture-db.internal',
        'PMA_single_signon_port'=>3307, 'PMA_single_signon_token'=>'fixtureCSRF',
        'PMA_single_signon_HMAC_secret'=>'fixtureHMAC');
    $result = array('root_cookie_sha256'=>hash('sha256',session_id()));
    session_write_close();
} else {
    session_set_cookie_params(array('path'=>'/scope/phpmyadmin/', 'httponly'=>true,
        'secure'=>false, 'samesite'=>'Strict'));
    session_name('phpMyAdmin'); session_start();
    $_SESSION['fixture_original'] = 'preserved';
    $oldID = session_id(); $oldParams = session_get_cookie_params();
    require __DIR__ . '/AuthenticationPlugin.php';
    require __DIR__ . '/AuthenticationSignon.php';
    class FixtureDenied extends \RuntimeException {}
    class FixtureAuth extends \PhpMyAdmin\Plugins\Auth\AuthenticationSignon {
        public function __construct() {}
        public function showLoginForm(): bool { throw new FixtureDenied('reauthenticate'); }
        public function storeCredentials(): bool {
            $GLOBALS['fixture_credentials'] = array($this->user, $this->password);
            return true;
        }
        public function checkRules(): void {}
    }
    $GLOBALS['cfg'] = array('Server'=>array('SignonURL'=>'/scope/seed',
        'SignonScript'=>__DIR__.'/phpmyadminsession.php', 'SignonSession'=>'SignonSession',
        'SignonCookieParams'=>$params, 'host'=>'localhost', 'port'=>3306, 'user'=>''));
    $accepted = false;
    try { (new FixtureAuth())->authenticate(); $accepted = true; }
    catch (FixtureDenied $error) {}
    $result = array('authenticated'=>$accepted,
        'selected_signon_cookie_sha256'=>isset($_COOKIE['SignonSession'])
            ? hash('sha256', $_COOKIE['SignonSession']) : null,
        'pma_session_restored'=>session_name()==='phpMyAdmin' && session_id()===$oldID
            && session_get_cookie_params()===$oldParams && $_SESSION['fixture_original']==='preserved');
    if ($accepted) {
        $result['credentials_and_connection_preserved'] =
            $GLOBALS['fixture_credentials']===array('fixtureOnlyUser','fixtureOnlyPassword')
            && $GLOBALS['cfg']['Server']['host']==='fixture-db.internal'
            && $GLOBALS['cfg']['Server']['port']===3307
            && $_SESSION[' PMA_token ']==='fixtureCSRF' && $_SESSION[' HMAC_secret ']==='fixtureHMAC';
    }
    session_write_close();
}
header('Content-Type: application/json'); echo json_encode($result);
}
'''


class Validator(http.server.BaseHTTPRequestHandler):
    accepted = True

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': int(type(self).accepted)}).encode())

    def log_message(self, *args):
        pass


def vendor_files():
    directory = os.environ.get('PMA_TEST_VENDOR_DIR')
    if directory:
        files = {name: (Path(directory) / name).read_bytes() for name in VENDOR_HASHES}
    else:
        with zipfile.ZipFile(ROOT / 'phpmyadmin.zip') as archive:
            prefix = 'phpMyAdmin-5.2.1-all-languages/libraries/classes/Plugins/'
            files = {name: archive.read(prefix + ('Auth/' if name == 'AuthenticationSignon.php' else '') + name)
                     for name in VENDOR_HASHES}
    assert all(hashlib.sha256(files[name]).hexdigest() == digest for name, digest in VENDOR_HASHES.items())
    return files


def run(php):
    validator = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Validator)
    thread = threading.Thread(target=validator.serve_forever, daemon=True)
    thread.start()
    receipts = []
    try:
        with tempfile.TemporaryDirectory(prefix='pma-cookie-fixture-') as folder:
            for name, params in [
                ('vendor_defaults', {}),
                ('explicit_root', {'path': '/', 'lifetime': 1800, 'httponly': True, 'samesite': 'Lax'}),
                ('custom_shared_path', {'path': '/scope/', 'domain': '127.0.0.1', 'httponly': True, 'samesite': 'Strict'}),
            ]:
                root = Path(folder) / name
                root.mkdir(mode=0o700)
                (root / 'sessions').mkdir(mode=0o700)
                for product in ('phpmyadminsignin.php', 'phpmyadminsession.php'):
                    shutil.copyfile(ROOT / 'plogical' / product, root / product)
                for filename, contents in vendor_files().items():
                    (root / filename).write_bytes(contents)
                (root / 'router.php').write_text(ROUTER)
                (root / 'fixture.json').write_text(json.dumps({
                    'params': params, 'validator': 'http://127.0.0.1:%d/' % validator.server_port}))
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0))
                    port = sock.getsockname()[1]
                with (root / 'server.log').open('w') as log:
                    process = subprocess.Popen([php, '-S', '127.0.0.1:%d' % port, str(root / 'router.php')],
                                               cwd=str(root), stdout=log, stderr=log)
                    try:
                        for _ in range(100):
                            try:
                                with socket.create_connection(('127.0.0.1', port), timeout=.2):
                                    break
                            except OSError:
                                time.sleep(.05)
                        jar = http.cookiejar.CookieJar()
                        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                                             urllib.request.HTTPCookieProcessor(jar))
                        rows = []
                        phases = [('seed', True), ('read', True), ('seed', True), ('read', True),
                                  ('read', False), ('read', True), ('seed', True), ('read', True)]
                        for phase, accepted in phases:
                            Validator.accepted = accepted
                            path = '/scope/seed' if phase == 'seed' else '/scope/phpmyadmin/read'
                            with opener.open('http://127.0.0.1:%d%s' % (port, path), timeout=15) as response:
                                result = json.loads(response.read())
                            rows.append({'phase': phase, 'validator_accepted': accepted, 'result': result,
                                         'signon_cookie_paths': sorted(c.path for c in jar if c.name == 'SignonSession')})
                        receipts.append({'case': name, 'requests': rows})
                    finally:
                        process.terminate()
                        process.wait(timeout=10)
    finally:
        validator.shutdown()
        validator.server_close()
        thread.join(timeout=5)
    result = {'receipts': receipts, 'cleanup_complete': not Path(folder).exists(),
              'vendor_class_sha256': VENDOR_HASHES, 'sql_connections': 0, 'external_requests': 0}
    print(json.dumps(result, indent=2))
    for receipt in receipts:
        rows = receipt['requests']
        expected_path = '/scope/' if receipt['case'] == 'custom_shared_path' else '/'
        assert rows[0]['result']['root_cookie_sha256'] != rows[2]['result']['root_cookie_sha256']
        assert [row['result']['authenticated'] for row in rows if row['phase'] == 'read'] == [True, True, False, False, True], 'fresh signon and reauthentication must succeed; rejected grant must stay revoked'
        assert all(row['signon_cookie_paths'] == [expected_path] for row in rows), 'signon cookie must not inherit phpMyAdmin path'
        for row in rows:
            if row['phase'] == 'read':
                assert row['result']['pma_session_restored']
                if row['result']['authenticated']:
                    assert row['result']['credentials_and_connection_preserved']
        assert rows[3]['result']['selected_signon_cookie_sha256'] == rows[2]['result']['root_cookie_sha256']
    assert result['cleanup_complete']


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else 'php')
