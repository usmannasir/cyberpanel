<?php
/**
 * Exercise the real handoff function with isolated file and cURL transports.
 * No request reaches a live server and no LSCPD configuration is changed.
 *
 * Run: php tests/test_phpmyadmin_signin_port_transport.php
 */

if (($argv[1] ?? '') !== '--capture') {
    $cases = array('custom_success', 'custom_connection_failure', 'custom_http_failure',
        'redirect_response', 'invalid_json', 'rejected_token',
        'malformed', 'unreadable', 'missing', 'empty', 'runtime_change');
    foreach ($cases as $case) {
        // A fresh PHP process without configured extensions lets this harness
        // capture cURL calls instead of replacing or contacting a real backend.
        $process = proc_open(array(PHP_BINARY, '-n', __FILE__, '--capture', $case),
            array(0 => array('pipe', 'r'), 1 => array('pipe', 'w'), 2 => array('pipe', 'w')), $pipes);
        if (!is_resource($process)) {
            fwrite(STDERR, "FAIL: could not start isolated transport case {$case}\n");
            exit(1);
        }
        fclose($pipes[0]);
        $stdout = stream_get_contents($pipes[1]); fclose($pipes[1]);
        $stderr = stream_get_contents($pipes[2]); fclose($pipes[2]);
        $status = proc_close($process);
        if ($status !== 0 || trim($stdout) !== 'OK: ' . $case) {
            fwrite(STDERR, "FAIL: isolated transport case {$case}\n" . $stdout . $stderr);
            exit(1);
        }
    }
    fwrite(STDOUT, 'OK: ' . count($cases) . " phpMyAdmin port transport cases passed\n");
    exit(0);
}

if (extension_loaded('curl')) {
    fwrite(STDERR, "FAIL: isolated transport process unexpectedly loaded cURL\n");
    exit(1);
}

function assertTransport($condition, $label) {
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$label}\n");
        exit(1);
    }
}

$options = array('CURLOPT_POST', 'CURLOPT_POSTFIELDS', 'CURLOPT_COOKIE', 'CURLOPT_HTTPHEADER',
    'CURLOPT_RETURNTRANSFER', 'CURLOPT_FOLLOWLOCATION', 'CURLOPT_CONNECTTIMEOUT', 'CURLOPT_TIMEOUT',
    'CURLOPT_SSL_VERIFYPEER', 'CURLOPT_SSL_VERIFYHOST', 'CURLINFO_RESPONSE_CODE');
foreach ($options as $number => $name) { define($name, 1000 + $number); }
$GLOBALS['requests'] = array();
$GLOBALS['response'] = '{"status":1}';
$GLOBALS['response_status'] = 200;

if (!extension_loaded('curl')) {
    function curl_init($url) {
        $GLOBALS['requests'][] = array('url' => $url, 'options' => array(), 'execs' => 0);
        return (object) array('index' => count($GLOBALS['requests']) - 1);
    }
    function curl_setopt_array($request, $options) {
        $GLOBALS['requests'][$request->index]['options'] = $options;
        return true;
    }
    function curl_exec($request) {
        $GLOBALS['requests'][$request->index]['execs']++;
        return $GLOBALS['response'];
    }
    function curl_getinfo($request, $option) {
        assertTransport($option === CURLINFO_RESPONSE_CODE, 'unexpected cURL status query');
        return $GLOBALS['response_status'];
    }
}

$_POST = array('token' => 'test-form-token', 'username' => 'test-user');
assertTransport(!defined('PMA_HANDOFF_VALIDATION_URL'), 'fixture must not override endpoint resolution');
ob_start();
include __DIR__ . '/../plogical/phpmyadminsignin.php';
ob_end_clean();
$_POST = array();

class PMABindFileTransport {
    public $context;
    public static $content = '*:5687';
    public static $exists = true;
    public static $readable = true;
    public static $paths = array();
    private $offset = 0;
    private function record($path) {
        self::$paths[] = $path;
        assertTransport($path === '/usr/local/lscp/conf/bind.conf', 'only the fixed local bind file may be read');
    }
    public function url_stat($path, $flags) {
        $this->record($path);
        return self::$exists ? array('mode' => 0100600, 'size' => strlen(self::$content)) : false;
    }
    public function stream_open($path, $mode, $options, &$openedPath) {
        $this->record($path);
        return self::$exists && self::$readable;
    }
    public function stream_read($count) {
        $result = substr(self::$content, $this->offset, $count);
        $this->offset += strlen($result);
        return $result;
    }
    public function stream_eof() { return $this->offset >= strlen(self::$content); }
    public function stream_stat() { return array('mode' => 0100600, 'size' => strlen(self::$content)); }
    public function stream_set_option($option, $arg1, $arg2) { return false; }
}

$case = $argv[2] ?? '';
if ($case === 'custom_connection_failure') $GLOBALS['response'] = false;
if ($case === 'custom_http_failure') $GLOBALS['response_status'] = 503;
if ($case === 'redirect_response') $GLOBALS['response_status'] = 302;
if ($case === 'invalid_json') $GLOBALS['response'] = 'not-json';
if ($case === 'rejected_token') $GLOBALS['response'] = '{"status":0}';
if ($case === 'malformed') PMABindFileTransport::$content = '*:5687@attacker.invalid';
if ($case === 'unreadable') PMABindFileTransport::$readable = false;
if ($case === 'missing') PMABindFileTransport::$exists = false;
if ($case === 'empty') PMABindFileTransport::$content = '';

$_COOKIE['cyberpanel_sessionid'] = 'authenticatedsession';
$_SERVER['REMOTE_ADDR'] = '203.0.113.10';
$_SERVER['HTTP_HOST'] = 'attacker.invalid:1234';
$_SERVER['SERVER_NAME'] = 'attacker.invalid';
$_SERVER['SERVER_PORT'] = '1234';
$_SERVER['HTTP_X_FORWARDED_HOST'] = 'attacker.invalid:1234';
$_SERVER['HTTP_X_FORWARDED_PORT'] = '1234';
$_SERVER['HTTP_X_FORWARDED_PROTO'] = 'http';
$_SERVER['HTTP_FORWARDED'] = 'host=attacker.invalid:1234;proto=http';

assertTransport(stream_wrapper_unregister('file'), 'could not isolate file transport');
assertTransport(stream_wrapper_register('file', 'PMABindFileTransport'), 'could not install isolated file transport');
try {
    $result = consumeHandoff('admin', 'one-time-token');
    if ($case === 'runtime_change') {
        PMABindFileTransport::$content = '*:7080';
        $secondResult = consumeHandoff('admin', 'another-one-time-token');
    }
} finally {
    stream_wrapper_restore('file');
}

$requests = $GLOBALS['requests'];
if ($case === 'malformed' || $case === 'unreadable') {
    assertTransport($result === false, 'invalid local configuration must reject the handoff');
    assertTransport(count($requests) === 0, 'invalid local configuration must not start a request');
} else {
    $expectedCount = $case === 'runtime_change' ? 2 : 1;
    assertTransport(count($requests) === $expectedCount, 'unexpected request count or fallback retry');
    $expectedPort = ($case === 'missing' || $case === 'empty') ? 8090 : 5687;
    assertTransport($requests[0]['url'] === 'https://127.0.0.1:' . $expectedPort . '/dataBases/consumePHPMYAdminHandoff',
        'handoff must use port ' . $expectedPort . ' at the fixed HTTPS loopback endpoint; got ' . $requests[0]['url']);
    $requestOptions = $requests[0]['options'];
    assertTransport($requestOptions[CURLOPT_POST] === true, 'handoff must remain a POST');
    assertTransport($requestOptions[CURLOPT_FOLLOWLOCATION] === false, 'handoff must not follow a redirect');
    assertTransport($requestOptions[CURLOPT_COOKIE] === 'cyberpanel_sessionid=authenticatedsession', 'session cookie changed');
    assertTransport($requestOptions[CURLOPT_HTTPHEADER] === array('CF-Connecting-IP: 203.0.113.10'), 'client IP propagation changed');
    assertTransport($requestOptions[CURLOPT_POSTFIELDS] === 'username=admin&token=one-time-token', 'handoff payload changed');
    assertTransport($requestOptions[CURLOPT_CONNECTTIMEOUT] === 2 && $requestOptions[CURLOPT_TIMEOUT] === 5, 'timeouts changed');
    assertTransport($requests[0]['execs'] === 1, 'handoff repeated its request');
    $failure = in_array($case, array('custom_connection_failure', 'custom_http_failure',
        'redirect_response', 'invalid_json', 'rejected_token'), true);
    assertTransport($result === !$failure, 'handoff result does not match the backend response');
    if ($case === 'runtime_change') {
        assertTransport($secondResult === true, 'handoff failed after configured port change');
        assertTransport($requests[1]['url'] === 'https://127.0.0.1:7080/dataBases/consumePHPMYAdminHandoff',
            'subsequent handoff did not read the changed port');
        assertTransport($requests[1]['execs'] === 1, 'changed-port handoff repeated its request');
    }
}

assertTransport(count(PMABindFileTransport::$paths) > 0, 'handoff did not read its configured port');
fwrite(STDOUT, "OK: {$case}\n");
