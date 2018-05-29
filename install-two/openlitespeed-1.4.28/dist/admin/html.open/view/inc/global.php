<?php

ob_start(); // just in case


header("Expires: -1"); 

header("Cache-Control: no-store, no-cache, must-revalidate, post-check=0, pre-check=0");
header("Pragma: no-cache");
header("X-Frame-Options: SAMEORIGIN");

define ('SERVER_ROOT', $_SERVER['LS_SERVER_ROOT']);

ini_set('include_path',
SERVER_ROOT . 'admin/html/lib/:' .
SERVER_ROOT . 'admin/html/lib/ows/:' .
SERVER_ROOT . 'admin/html/view/:.');

// **PREVENTING SESSION HIJACKING**
// Prevents javascript XSS attacks aimed to steal the session ID
ini_set('session.cookie_httponly', 1);

// **PREVENTING SESSION FIXATION**
// Session ID cannot be passed through URLs
ini_set('session.use_only_cookies', 1);

// Uses a secure connection (HTTPS) if possible
if (isset($_SERVER['HTTPS']) && ($_SERVER['HTTPS'] == 'on')) {
	ini_set('session.cookie_secure', 1);
}

date_default_timezone_set('America/New_York');

spl_autoload_register( function ($class) {
	include $class . '.php';
});
