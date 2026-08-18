<?php
/**
 * Regression test for issue #1680, phpMyAdmin logout leaving a blank page.
 *
 * phpMyAdmin is configured with LogoutURL = 'phpmyadminsignin.php?logout', so the
 * logout arrives as a GET. The signon file used to look at $_POST only, fell through
 * every branch, and returned an empty page with the session still alive.
 *
 * Run: php tests/test_phpmyadmin_signin_logout.php
 */

$signin = __DIR__ . '/../plogical/phpmyadminsignin.php';

$_GET['logout'] = '';
session_name('SignonSession');
@session_start();
$_SESSION['PMA_single_signon_user'] = 'someuser';

if (session_status() !== PHP_SESSION_ACTIVE) {
    fwrite(STDERR, "FAIL: could not start a session to test with\n");
    exit(1);
}

ob_start();
include $signin;
ob_end_clean();

$destroyed = (session_status() !== PHP_SESSION_ACTIVE) || empty($_SESSION);

if (!$destroyed) {
    fwrite(STDERR, "FAIL: GET ?logout did not destroy the signon session\n");
    exit(1);
}

fwrite(STDOUT, "OK: GET ?logout destroys the signon session\n");
exit(0);
