<?php
/**
 * Regression test for the CyberPanel-to-phpMyAdmin one-time signon handoff.
 *
 * Run: php tests/test_phpmyadmin_signin_handoff.php
 */

$signin = __DIR__ . '/../plogical/phpmyadminsignin.php';
$source = file_get_contents($signin);

foreach (array('handoff_token', 'hash_equals', 'lstat', 'unlink') as $required) {
    if (strpos($source, $required) === false) {
        fwrite(STDERR, "FAIL: missing secure handoff operation: {$required}\n");
        exit(1);
    }
}

if (strpos($source, "\$_SESSION['userID']") !== false) {
    fwrite(STDERR, "FAIL: signon still relies on the obsolete PHP userID session\n");
    exit(1);
}

$sessionDir = sys_get_temp_dir() . '/pma-session-test-' . bin2hex(random_bytes(6));
$handoffDir = $sessionDir . '/handoff';
mkdir($sessionDir, 0700);
mkdir($handoffDir, 0700);
chmod($handoffDir, 0700);
session_save_path($sessionDir);
define('PMA_HANDOFF_DIRECTORY', $handoffDir);

$token = bin2hex(random_bytes(24));
$handoffPath = $handoffDir . '/' . hash('sha256', $token);
file_put_contents($handoffPath, json_encode(array(
    'username' => 'admin',
    'expires' => time() + 120,
)));
chmod($handoffPath, 0600);

$_POST['username'] = 'admin';
$_POST['password'] = 'database-password';
$_POST['handoff_token'] = $token;

$GLOBALS['assertions_ran'] = false;
register_shutdown_function(function () use ($sessionDir, $handoffPath) {
    if (!$GLOBALS['assertions_ran']) {
        @unlink($handoffPath);
        @rmdir($sessionDir);
        fwrite(STDERR, "FAIL: signon ended before the handoff assertions ran\n");
        exit(1);
    }
});

ob_start();
include $signin;
ob_end_clean();

if (file_exists($handoffPath)) {
    fwrite(STDERR, "FAIL: one-time handoff record was not consumed\n");
    exit(1);
}

session_name('SignonSession');
@session_start();
$valid = isset($_SESSION['PMA_single_signon_user'])
    && $_SESSION['PMA_single_signon_user'] === 'admin'
    && isset($_SESSION['PMA_single_signon_password'])
    && $_SESSION['PMA_single_signon_password'] === 'database-password';
@session_destroy();

foreach (glob($sessionDir . '/*') ?: array() as $sessionFile) {
    if (is_file($sessionFile)) {
        @unlink($sessionFile);
    }
}
@rmdir($handoffDir);
@rmdir($sessionDir);

$GLOBALS['assertions_ran'] = true;

if (!$valid) {
    fwrite(STDERR, "FAIL: signon session did not receive the validated credentials\n");
    exit(1);
}

fwrite(STDOUT, "OK: one-time handoff creates the phpMyAdmin signon session\n");
exit(0);
