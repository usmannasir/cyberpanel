<?php
/** Actual bundled 5.2.1 auth path, fixture sessions, no database or HTTP access.
 * Run via tests/run_phpmyadmin_session_tests.py, which extracts the two vendor
 * classes from the shipped ZIP and creates a private disposable session path.
 */
namespace PhpMyAdmin {
    class Session { public static function secure() {} }
    class Util {
        public static function generateRandom($length) { return str_repeat('r', $length); }
        public static function clearUserCache() {}
    }
}
namespace {
    $mode = $argv[1]; $case = $argv[2]; $vendor = $argv[3]; $sessionDir = $argv[4];
    function checkFixture($condition, $label) {
        if (!$condition) { throw new \RuntimeException($label); }
    }
    $GLOBALS['fixture_requests'] = array();
    if ($case !== 'missing_curl') {
        // php -n: every cURL operation is a captured in-memory fixture.
        $options = array('CURLOPT_POST', 'CURLOPT_POSTFIELDS', 'CURLOPT_COOKIE', 'CURLOPT_HTTPHEADER',
            'CURLOPT_RETURNTRANSFER', 'CURLOPT_FOLLOWLOCATION', 'CURLOPT_CONNECTTIMEOUT', 'CURLOPT_TIMEOUT',
            'CURLOPT_SSL_VERIFYPEER', 'CURLOPT_SSL_VERIFYHOST', 'CURLINFO_RESPONSE_CODE');
        foreach ($options as $number => $name) { define($name, 1000 + $number); }
        function curl_init($url) {
            $GLOBALS['fixture_requests'][] = array('url' => $url);
            return (object)array('index' => count($GLOBALS['fixture_requests']) - 1);
        }
        function curl_setopt_array($request, $options) {
            $GLOBALS['fixture_requests'][$request->index]['options'] = $options;
            return true;
        }
        function curl_exec($request) {
            $case = $GLOBALS['case'];
            if ($case === 'transport_failure') return false;
            if ($case === 'transport_exception') throw new \RuntimeException('fixture transport error');
            if ($case === 'invalid_json') return 'invalid';
            if ($case === 'non_integer_status') return '{"status":"1"}';
            return json_encode(array('status' => $case === 'revoked' ? 0 : 1));
        }
        function curl_getinfo($request, $option) {
            return $GLOBALS['case'] === 'http_failure' ? 503 : ($GLOBALS['case'] === 'redirect' ? 302 : 200);
        }
    }
    checkFixture(!extension_loaded('curl'), 'real cURL must be disabled');
    define('PMA_SESSION_VALIDATION_URL', 'http://127.0.0.1:1/isolated-validator');
    require $vendor . '/AuthenticationPlugin.php';
    require $vendor . '/AuthenticationSignon.php';
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
    session_save_path($sessionDir);
    session_name('SignonSession'); session_id('fixtureSignonSession12345'); session_start();
    $_SESSION = array(
        'PMA_single_signon_user' => 'fixture-db-user',
        'PMA_single_signon_password' => 'fixture-db-password',
        'PMA_single_signon_host' => 'fixture-db.internal',
        'PMA_single_signon_port' => 3307,
        'PMA_single_signon_token' => 'fixture-csrf-token',
        'PMA_single_signon_HMAC_secret' => 'fixture-hmac-secret',
    );
    if ($case !== 'legacy') {
        $_SESSION['PMA_panel_grant'] = str_repeat('a', 64);
        $_SESSION['PMA_panel_session'] = 'originalpanelsessionkey';
    }
    if ($case === 'malformed_grant') $_SESSION['PMA_panel_grant'] = 'invalid';
    if ($case === 'bad_db_port') $_SESSION['PMA_single_signon_port'] = 0;
    session_write_close();
    $_COOKIE['SignonSession'] = 'fixtureSignonSession12345';
    $_COOKIE['cyberpanel_sessionid'] = 'originalpanelsessionkey';
    if ($case === 'missing_panel') unset($_COOKIE['cyberpanel_sessionid']);
    if ($case === 'rotated_panel') $_COOKIE['cyberpanel_sessionid'] = 'laterpanelsessionkey';
    $_SERVER['REMOTE_ADDR'] = '203.0.113.10';
    if ($case === 'invalid_ip') $_SERVER['REMOTE_ADDR'] = 'not-an-ip';
    session_name('phpMyAdmin'); session_id('fixturePhpMyAdminSession12345'); session_start();
    $_SESSION = array('fixture_original' => 'preserved', ' PMA_token ' => 'original-token');
    $params = session_get_cookie_params();
    $GLOBALS['cfg'] = array('Server' => array(
        'SignonURL' => 'phpmyadminsignin.php', 'SignonSession' => 'SignonSession',
        'SignonScript' => $mode === 'baseline' ? '' : __DIR__ . '/../plogical/phpmyadminsession.php',
        'SignonCookieParams' => $params, 'host' => 'localhost', 'port' => 3306, 'user' => '',
    ));
    $expected = in_array($case, array('valid', 'repeat'), true);
    $accepted = false;
    try {
        $auth = new FixtureAuth(); $auth->authenticate();
        $accepted = true;
        if ($case === 'repeat') { $auth = new FixtureAuth(); $auth->authenticate(); }
    } catch (FixtureDenied $error) {}
    checkFixture($accepted === $expected, 'database access expectation: ' . $case);
    checkFixture(session_name() === 'phpMyAdmin', 'phpMyAdmin session name restored');
    checkFixture(session_id() === 'fixturePhpMyAdminSession12345', 'phpMyAdmin session ID restored');
    checkFixture(session_get_cookie_params() === $params, 'cookie parameters restored');
    checkFixture($_SESSION['fixture_original'] === 'preserved', 'original session data preserved');
    if ($accepted) {
        checkFixture($GLOBALS['fixture_credentials'] === array('fixture-db-user', 'fixture-db-password'), 'credentials preserved');
        checkFixture($GLOBALS['cfg']['Server']['host'] === 'fixture-db.internal', 'database host preserved');
        checkFixture($GLOBALS['cfg']['Server']['port'] === 3307, 'database port preserved');
        checkFixture($_SESSION[' PMA_token '] === 'fixture-csrf-token', 'CSRF transfer preserved');
        checkFixture($_SESSION[' HMAC_secret '] === 'fixture-hmac-secret', 'HMAC transfer preserved');
        if ($mode !== 'baseline') {
            checkFixture(count($GLOBALS['fixture_requests']) === ($case === 'repeat' ? 2 : 1), 'every auth request validated');
            $request = $GLOBALS['fixture_requests'][0];
            checkFixture($request['url'] === PMA_SESSION_VALIDATION_URL, 'fixed validation destination');
            checkFixture($request['options'][CURLOPT_FOLLOWLOCATION] === false, 'redirects disabled');
            checkFixture($request['options'][CURLOPT_COOKIE] === 'cyberpanel_sessionid=originalpanelsessionkey', 'originating cookie forwarded');
            checkFixture($request['options'][CURLOPT_HTTPHEADER] === array('CF-Connecting-IP: 203.0.113.10'), 'client address forwarded');
            checkFixture(strpos($request['options'][CURLOPT_POSTFIELDS], 'password') === false, 'DB password never sent to validator');
        }
    }
    session_write_close();
    if (!$accepted && $mode !== 'baseline') {
        session_name('SignonSession'); session_id('fixtureSignonSession12345'); session_start();
        checkFixture(!isset($_SESSION['PMA_single_signon_user']), 'rejected credentials removed');
        session_write_close();
    }
    echo 'OK: ' . $case . "\n";
}
