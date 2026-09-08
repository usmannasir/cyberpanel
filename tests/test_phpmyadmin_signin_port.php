<?php
/**
 * Regression coverage for the local LSCPD port used by phpMyAdmin signon.
 *
 * Run: php tests/test_phpmyadmin_signin_port.php
 */

$signin = __DIR__ . '/../plogical/phpmyadminsignin.php';
$testRoot = sys_get_temp_dir() . '/pma-bind-test-' . bin2hex(random_bytes(6));
mkdir($testRoot, 0700);
$bindingPath = $testRoot . '/bind.conf';
$assertions = 0;
$GLOBALS['port_helpers_loaded'] = false;

register_shutdown_function(function () use ($testRoot, $bindingPath) {
    @unlink($bindingPath);
    @rmdir($testRoot . '/directory');
    @rmdir($testRoot);
    if (!$GLOBALS['port_helpers_loaded']) {
        fwrite(STDERR, "FAIL: signon ended before the port assertions could run\n");
        exit(1);
    }
});

function assertPortResult($actual, $expected, $label) {
    global $assertions;
    if ($actual !== $expected) {
        fwrite(STDERR, 'FAIL: ' . $label . ': expected ' . var_export($expected, true)
            . ', got ' . var_export($actual, true) . "\n");
        exit(1);
    }
    $assertions++;
}

// Load the real helpers through the harmless form-rendering branch.
$_POST = array('token' => 'test-form-token', 'username' => 'test-user');
ob_start();
include $signin;
ob_end_clean();
$GLOBALS['port_helpers_loaded'] = true;
$_POST = array();

if (!function_exists('getPMAHandoffValidationURL')) {
    fwrite(STDERR, "FAIL: signon cannot resolve its validation endpoint from LSCPD configuration\n");
    exit(1);
}

$endpoint = '/dataBases/consumePHPMYAdminHandoff';
$defaultURL = 'https://127.0.0.1:8090' . $endpoint;
assertPortResult(getPMAHandoffValidationURL($bindingPath), $defaultURL, 'missing bind file keeps the default port');

$validBindings = array(
    array('', 8090, 'empty bind file'),
    array(" \t\r\n", 8090, 'ASCII whitespace only'),
    array('*:8090', 8090, 'explicit default port'),
    array('*:5687', 5687, 'configured custom port'),
    array(" \t*:5687\r\n", 5687, 'normal surrounding whitespace'),
    array('*:1', 1, 'lowest valid port'),
    array('*:65535', 65535, 'highest valid port'),
    array('*:00080', 80, 'decimal port with leading zeroes'),
    array('127.0.0.1:5687', 5687, 'localhost-only LSCPD bind'),
    array('0.0.0.0:5687', 5687, 'all-interfaces numeric bind'),
);
foreach ($validBindings as $case) {
    file_put_contents($bindingPath, $case[0]);
    assertPortResult(getPMAHandoffValidationURL($bindingPath),
        'https://127.0.0.1:' . $case[1] . $endpoint, $case[2]);
}

$invalidBindings = array(
    array('*:0', 'zero port'),
    array('*:65536', 'port above the TCP range'),
    array('*:999999', 'oversized port'),
    array('*:-1', 'negative port'),
    array('*:+5687', 'signed port'),
    array('*:5687.0', 'fractional port'),
    array('*:5e3', 'exponent notation'),
    array('*:', 'missing port'),
    array('5687', 'missing bind address'),
    array('* :5687', 'space inside address'),
    array('*: 5687', 'space inside port'),
    array('[::1]:5687', 'unsupported IPv6 address syntax'),
    array('https://attacker.invalid:5687', 'URL instead of bind configuration'),
    array('*:5687@attacker.invalid', 'userinfo-style destination'),
    array('*:5687/path', 'path after port'),
    array('*:5687?port=8090', 'query after port'),
    array('*:5687 # comment', 'unrecognized trailing directive'),
    array("*:5687\n*:8090", 'multiple bind declarations'),
    array("*:56\r87", 'embedded line break'),
    array("\0*:5687", 'leading NUL is not whitespace'),
    array("*:5687\0", 'trailing NUL is not whitespace'),
    array("\v*:5687", 'vertical tab is not supported padding'),
    array("*:5687\f", 'form feed is not supported padding'),
    array("\xc2\xa0*:5687", 'non-ASCII space is not supported padding'),
    array("*:\xef\xbc\x95\xef\xbc\x96\xef\xbc\x98\xef\xbc\x97", 'non-ASCII digits'),
);
foreach ($invalidBindings as $case) {
    file_put_contents($bindingPath, $case[0]);
    assertPortResult(getPMAHandoffValidationURL($bindingPath), false, $case[1]);
}

// A failed read is deterministic even when the suite runs as root. This wrapper
// reports an existing regular file but denies opening it, without host changes.
class PMAUnreadableBinding {
    public $context;
    public function url_stat($path, $flags) {
        return array('mode' => 0100000, 'size' => 7);
    }
    public function stream_open($path, $mode, $options, &$openedPath) {
        return false;
    }
}
stream_wrapper_register('pmaunreadable', 'PMAUnreadableBinding');
assertPortResult(getPMAHandoffValidationURL('pmaunreadable://bind.conf'), false,
    'existing unreadable bind file fails closed');
stream_wrapper_unregister('pmaunreadable');

file_put_contents($bindingPath, '*:5687');
$_SERVER['HTTP_HOST'] = 'attacker.invalid:1234';
$_SERVER['SERVER_NAME'] = 'attacker.invalid';
$_SERVER['SERVER_PORT'] = '4321';
$_SERVER['HTTP_X_FORWARDED_HOST'] = 'attacker.invalid:9999';
$_SERVER['HTTP_X_FORWARDED_PORT'] = '9999';
$_SERVER['HTTP_X_FORWARDED_PROTO'] = 'http';
$_SERVER['HTTP_FORWARDED'] = 'host=attacker.invalid:9999;proto=http';
assertPortResult(getPMAHandoffValidationURL($bindingPath),
    'https://127.0.0.1:5687' . $endpoint, 'request headers cannot choose the validation origin');

// Read again after an ordinary settings change, without restarting this process.
file_put_contents($bindingPath, '*:7080');
assertPortResult(getPMAHandoffValidationURL($bindingPath),
    'https://127.0.0.1:7080' . $endpoint, 'port change is read from the current file');

fwrite(STDOUT, "OK: {$assertions} phpMyAdmin bind-port assertions passed\n");
