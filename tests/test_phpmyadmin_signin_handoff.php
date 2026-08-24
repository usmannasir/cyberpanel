<?php
/**
 * Regression test for the CyberPanel-to-phpMyAdmin one-time signon handoff.
 *
 * Run: php tests/test_phpmyadmin_signin_handoff.php
 */

$signin = __DIR__ . '/../plogical/phpmyadminsignin.php';
$source = file_get_contents($signin);

foreach (array('handoff_token', 'cyberpanel_sessionid', 'curl_exec') as $required) {
    if (strpos($source, $required) === false) {
        fwrite(STDERR, "FAIL: missing authenticated handoff operation: {$required}\n");
        exit(1);
    }
}

if (strpos($source, "\$_SESSION['userID']") !== false) {
    fwrite(STDERR, "FAIL: signon still relies on the obsolete PHP userID session\n");
    exit(1);
}

$testRoot = sys_get_temp_dir() . '/pma-session-test-' . bin2hex(random_bytes(6));
$sessionDir = $testRoot . '/sessions';
$router = $testRoot . '/validator.php';
mkdir($testRoot, 0700);
mkdir($sessionDir, 0700);
session_save_path($sessionDir);

file_put_contents($router, <<<'PHP'
<?php
$valid = isset($_COOKIE['cyberpanel_sessionid'])
    && $_COOKIE['cyberpanel_sessionid'] === 'authenticatedsession'
    && isset($_POST['username'], $_POST['token'])
    && $_POST['username'] === 'admin'
    && $_POST['token'] === 'one-time-token';
http_response_code($valid ? 200 : 403);
header('Content-Type: application/json');
echo json_encode(array('status' => $valid ? 1 : 0));
PHP
);

$socket = stream_socket_server('tcp://127.0.0.1:0', $errno, $error);
if ($socket === false) {
    fwrite(STDERR, "FAIL: could not reserve a local validation port\n");
    exit(1);
}
$address = stream_socket_get_name($socket, false);
$port = (int) substr(strrchr($address, ':'), 1);
fclose($socket);

$descriptors = array(
    0 => array('pipe', 'r'),
    1 => array('file', '/dev/null', 'a'),
    2 => array('file', '/dev/null', 'a'),
);
$server = proc_open(
    array(PHP_BINARY, '-S', '127.0.0.1:' . $port, $router),
    $descriptors,
    $pipes
);
if (!is_resource($server)) {
    fwrite(STDERR, "FAIL: could not start the local handoff validator\n");
    exit(1);
}
fclose($pipes[0]);

$ready = false;
for ($attempt = 0; $attempt < 50; $attempt++) {
    $connection = @fsockopen('127.0.0.1', $port, $errno, $error, 0.1);
    if ($connection !== false) {
        fclose($connection);
        $ready = true;
        break;
    }
    usleep(20_000);
}
if (!$ready) {
    proc_terminate($server);
    fwrite(STDERR, "FAIL: local handoff validator did not start\n");
    exit(1);
}

define(
    'PMA_HANDOFF_VALIDATION_URL',
    'http://127.0.0.1:' . $port . '/validate'
);
$_COOKIE['cyberpanel_sessionid'] = 'authenticatedsession';
$_POST['username'] = 'admin';
$_POST['password'] = 'database-password';
$_POST['handoff_token'] = 'one-time-token';

$GLOBALS['assertions_ran'] = false;
register_shutdown_function(function () use ($server, $sessionDir, $router, $testRoot) {
    if (is_resource($server)) {
        proc_terminate($server);
        proc_close($server);
    }
    foreach (glob($sessionDir . '/*') ?: array() as $sessionFile) {
        @unlink($sessionFile);
    }
    @unlink($router);
    @rmdir($sessionDir);
    @rmdir($testRoot);

    if (!$GLOBALS['assertions_ran']) {
        fwrite(STDERR, "FAIL: signon ended before the handoff assertions ran\n");
        exit(1);
    }
});

ob_start();
include $signin;
ob_end_clean();

session_name('SignonSession');
@session_start();
$valid = isset($_SESSION['PMA_single_signon_user'])
    && $_SESSION['PMA_single_signon_user'] === 'admin'
    && isset($_SESSION['PMA_single_signon_password'])
    && $_SESSION['PMA_single_signon_password'] === 'database-password';
@session_destroy();

$GLOBALS['assertions_ran'] = true;

if (!$valid) {
    fwrite(STDERR, "FAIL: signon session did not receive the validated credentials\n");
    exit(1);
}

fwrite(STDOUT, "OK: authenticated handoff creates the phpMyAdmin signon session\n");
exit(0);
