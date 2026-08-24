<?php
/**
 * Regression test for rejecting a phpMyAdmin signon without a valid handoff.
 *
 * Run: php tests/test_phpmyadmin_signin_rejects_invalid.php
 */

$signin = __DIR__ . '/../plogical/phpmyadminsignin.php';
$testRoot = sys_get_temp_dir() . '/pma-invalid-test-' . bin2hex(random_bytes(6));
$sessionDir = $testRoot . '/sessions';
$handoffDir = $testRoot . '/handoff';
mkdir($testRoot, 0700);
mkdir($sessionDir, 0700);
mkdir($handoffDir, 0700);
chmod($handoffDir, 0700);
session_save_path($sessionDir);
define('PMA_HANDOFF_DIRECTORY', $handoffDir);

$_POST['username'] = 'admin';
$_POST['password'] = 'untrusted-password';
$_POST['handoff_token'] = 'missing-token';

register_shutdown_function(function () use ($sessionDir, $handoffDir, $testRoot) {
    $sessionFiles = glob($sessionDir . '/sess_*') ?: array();
    foreach ($sessionFiles as $sessionFile) {
        @unlink($sessionFile);
    }
    @rmdir($sessionDir);
    @rmdir($handoffDir);
    @rmdir($testRoot);

    if ($sessionFiles) {
        fwrite(STDERR, "FAIL: invalid handoff created a phpMyAdmin session\n");
        exit(1);
    }

    fwrite(STDOUT, "OK: invalid handoff is rejected before a signon session is created\n");
});

include $signin;

fwrite(STDERR, "FAIL: invalid handoff was not rejected\n");
exit(1);
