<?php

define("PMA_SIGNON_INDEX", 1);
define('PMA_SIGNON_SESSIONNAME', 'SignonSession');
define('PMA_DISABLE_SSL_PEER_VALIDATION', TRUE);
if (!defined('PMA_HANDOFF_VALIDATION_URL')) {
    define(
        'PMA_HANDOFF_VALIDATION_URL',
        'https://127.0.0.1:8090/dataBases/consumePHPMYAdminHandoff'
    );
}

function rejectSignon() {
    header('Location: /base/');
    exit();
}

function consumeHandoff($username, $token) {
    if (!is_string($username) || $username === '' || strlen($username) > 255) {
        return false;
    }
    if (!is_string($token) || $token === '' || strlen($token) > 512) {
        return false;
    }
    if (!isset($_COOKIE['cyberpanel_sessionid'])) {
        return false;
    }
    $sessionID = (string) $_COOKIE['cyberpanel_sessionid'];
    if (!preg_match('/^[A-Za-z0-9]{16,128}$/D', $sessionID)) {
        return false;
    }

    $request = @curl_init(PMA_HANDOFF_VALIDATION_URL);
    if ($request === false) {
        return false;
    }

    @curl_setopt_array($request, array(
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query(
            array('username' => $username, 'token' => $token),
            '',
            '&',
            PHP_QUERY_RFC3986
        ),
        CURLOPT_COOKIE => 'cyberpanel_sessionid=' . $sessionID,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_CONNECTTIMEOUT => 2,
        CURLOPT_TIMEOUT => 5,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => 0,
    ));
    $response = @curl_exec($request);
    $statusCode = (int) @curl_getinfo($request, CURLINFO_RESPONSE_CODE);
    @curl_close($request);

    if (!is_string($response) || $statusCode !== 200) {
        return false;
    }
    $payload = @json_decode($response, true);
    return is_array($payload)
        && isset($payload['status'])
        && $payload['status'] === 1;
}

try {
    if (isset($_POST['token'])) {

        ### Get credentials using the token

        $token = htmlspecialchars($_POST['token'], ENT_QUOTES, 'UTF-8');
        $username = htmlspecialchars($_POST['username'], ENT_QUOTES, 'UTF-8');

        //$url = "/dataBases/fetchDetailsPHPMYAdmin?token=" . $token . '&username=' . $username;
        $url = "/dataBases/fetchDetailsPHPMYAdmin";

        //         header('Location: ' . $url);

        // Redirect with POST data

        echo '<form id="redirectForm" action="' . $url . '" method="post">';
        echo '<input type="hidden"  value="' . $token . '" name="token">';
        echo '<input type="hidden"  value="' . $username . '" name="username">';
        echo '</form>';
        echo '<script>document.getElementById("redirectForm").submit();</script>';

    } else if (isset($_POST['logout']) || isset($_GET['logout'])) {
        // phpMyAdmin is configured with LogoutURL = 'phpmyadminsignin.php?logout',
        // which arrives as a GET. Checking only $_POST left the session alive and
        // rendered a blank page.
        if (session_status() !== PHP_SESSION_ACTIVE) {
            session_name(PMA_SIGNON_SESSIONNAME);
            @session_start();
        }
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 86400, $params["path"], $params["domain"], $params["secure"], $params["httponly"]);
        @session_destroy();
        header('Location: /base/');
        return;
    } else if (isset($_POST['password'])) {
        $username = isset($_POST['username']) ? (string) $_POST['username'] : '';
        $password = $_POST['password'];
        $handoffToken = isset($_POST['handoff_token']) ? (string) $_POST['handoff_token'] : '';

        if (!consumeHandoff($username, $handoffToken)) {
            rejectSignon();
        }

        session_name(PMA_SIGNON_SESSIONNAME);
        if (!@session_start()) {
            rejectSignon();
        }

        $_SESSION['PMA_single_signon_user'] = $username;
        $_SESSION['PMA_single_signon_password'] = $password;
        $_SESSION['PMA_single_signon_host'] = 'localhost';
        $_SESSION['PMA_single_signon_port'] = 3306;

        @session_write_close();

        header('Location: /phpmyadmin/index.php?server=' . PMA_SIGNON_INDEX);
    } else {
        rejectSignon();
    }
} catch (Exception $e) {
    rejectSignon();
}
