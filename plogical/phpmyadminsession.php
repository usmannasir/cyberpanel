<?php
/** phpMyAdmin SignonScript: validate the originating panel session per request. */
if (!defined('PMA_SIGNON_LIBRARY_ONLY')) {
    define('PMA_SIGNON_LIBRARY_ONLY', true);
}
require_once __DIR__ . '/phpmyadminsignin.php';

if (!function_exists('get_login_credentials')) {
function get_login_credentials($unusedUser) {
    $empty = array('', '');
    $cookie = isset($_COOKIE[PMA_SIGNON_SESSIONNAME]) ? $_COOKIE[PMA_SIGNON_SESSIONNAME] : null;
    if (!is_string($cookie) || !preg_match('/^[A-Za-z0-9,-]{16,128}$/D', $cookie)) {
        return $empty;
    }
    $oldName = session_name();
    $oldID = session_id();
    $oldParams = session_get_cookie_params();
    // Match the vendor's SignonSession cookie settings. Inheriting phpMyAdmin's
    // narrower path creates a second cookie that shadows the next handoff.
    $signonParams = (array)($GLOBALS['cfg']['Server']['SignonCookieParams'] ?? array());
    foreach (array('lifetime' => 0, 'path' => '/', 'domain' => '',
        'secure' => false, 'httponly' => false) as $key => $default) {
        if (!isset($signonParams[$key])) {
            $signonParams[$key] = $default;
        }
    }
    if (isset($signonParams['samesite']) && !in_array($signonParams['samesite'], array('Lax', 'Strict'))) {
        unset($signonParams['samesite']);
    }
    $wasActive = session_status() === PHP_SESSION_ACTIVE;
    if ($wasActive) {
        session_write_close();
    }
    $saved = array();
    $valid = false;
    try {
        session_set_cookie_params($signonParams);
        session_name(PMA_SIGNON_SESSIONNAME);
        session_id($cookie);
        if (!@session_start()) {
            return $empty;
        }
        $saved = $_SESSION;
        session_write_close();

        $panelCookie = isset($_COOKIE['cyberpanel_sessionid']) ? $_COOKIE['cyberpanel_sessionid'] : null;
        $bound = isset($saved['PMA_panel_session'], $saved['PMA_panel_grant'],
            $saved['PMA_single_signon_user'], $saved['PMA_single_signon_password'],
            $saved['PMA_single_signon_host'], $saved['PMA_single_signon_port'])
            && is_string($panelCookie) && is_string($saved['PMA_panel_session'])
            && hash_equals($saved['PMA_panel_session'], $panelCookie)
            && is_string($saved['PMA_panel_grant'])
            && preg_match('/^[a-f0-9]{64}$/D', $saved['PMA_panel_grant'])
            && is_string($saved['PMA_single_signon_user']) && $saved['PMA_single_signon_user'] !== ''
            && is_string($saved['PMA_single_signon_password'])
            && is_string($saved['PMA_single_signon_host']) && $saved['PMA_single_signon_host'] !== ''
            && is_int($saved['PMA_single_signon_port'])
            && $saved['PMA_single_signon_port'] > 0 && $saved['PMA_single_signon_port'] <= 65535;
        if ($bound) {
            $url = defined('PMA_SESSION_VALIDATION_URL')
                ? PMA_SESSION_VALIDATION_URL : getPMASessionValidationURL();
            $valid = requestPMAPanel($url, array(
                'username' => $saved['PMA_single_signon_user'], 'grant' => $saved['PMA_panel_grant'])) !== false;
        }
    } catch (Throwable $error) {
        $valid = false;
    } finally {
        if (session_status() === PHP_SESSION_ACTIVE) {
            session_write_close();
        }
        if (!$valid) {
            // Another request may have completed a new handoff while validation
            // ran. Remove only the same rejected grant, never a newer one.
            session_set_cookie_params($signonParams);
            session_name(PMA_SIGNON_SESSIONNAME);
            session_id($cookie);
            if (@session_start()) {
                if (($_SESSION['PMA_panel_grant'] ?? null) === ($saved['PMA_panel_grant'] ?? null)) {
                    $_SESSION = array();
                }
                session_write_close();
            }
        }
        session_name($oldName);
        session_id($oldID);
        session_set_cookie_params($oldParams);
        if ($wasActive) {
            if (!@session_start()) {
                $valid = false;
            }
        } else {
            $_SESSION = array();
        }
    }
    if (!$valid) {
        return $empty;
    }
    // Script signon bypasses the vendor's SignonSession branch. Preserve its
    // trusted connection and CSRF/HMAC transfers after panel authorization.
    $GLOBALS['cfg']['Server']['host'] = $saved['PMA_single_signon_host'];
    $GLOBALS['cfg']['Server']['port'] = $saved['PMA_single_signon_port'];
    if (!empty($saved['PMA_single_signon_token'])) {
        $_SESSION[' PMA_token '] = $saved['PMA_single_signon_token'];
        $_SESSION[' HMAC_secret '] = $saved['PMA_single_signon_HMAC_secret'] ?? random_bytes(16);
    }
    return array($saved['PMA_single_signon_user'], $saved['PMA_single_signon_password']);
}
}
