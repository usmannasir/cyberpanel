<?php

define("PMA_SIGNON_INDEX", 1);
define('PMA_SIGNON_SESSIONNAME', 'SignonSession');
define('PMA_DISABLE_SSL_PEER_VALIDATION', TRUE);
if (!defined('PMA_HANDOFF_DIRECTORY')) {
    define('PMA_HANDOFF_DIRECTORY', sys_get_temp_dir() . '/cyberpanel-phpmyadmin-handoff');
}

function rejectSignon() {
    header('Location: /base/');
    exit();
}

function handoffDirectoryIsSecure($directory) {
    $directoryStat = @lstat($directory);
    if ($directoryStat === false || ($directoryStat['mode'] & 0170000) !== 0040000) {
        return false;
    }
    if (($directoryStat['mode'] & 0777) !== 0700) {
        return false;
    }
    if (function_exists('posix_geteuid') && $directoryStat['uid'] !== posix_geteuid()) {
        return false;
    }
    return true;
}

function consumeHandoff($username, $token) {
    if (!is_string($username) || $username === '' || strlen($username) > 255) {
        return false;
    }
    if (!is_string($token) || $token === '' || strlen($token) > 512) {
        return false;
    }
    if (!handoffDirectoryIsSecure(PMA_HANDOFF_DIRECTORY)) {
        return false;
    }

    $recordPath = PMA_HANDOFF_DIRECTORY . '/' . hash('sha256', $token);
    $recordStat = @lstat($recordPath);
    if ($recordStat === false || ($recordStat['mode'] & 0170000) !== 0100000) {
        return false;
    }
    if (($recordStat['mode'] & 0777) !== 0600 || $recordStat['nlink'] !== 1) {
        return false;
    }
    if (function_exists('posix_geteuid') && $recordStat['uid'] !== posix_geteuid()) {
        return false;
    }

    $directoryPath = @realpath(PMA_HANDOFF_DIRECTORY);
    $resolvedPath = @realpath($recordPath);
    if ($directoryPath === false || $resolvedPath === false
        || dirname($resolvedPath) !== $directoryPath) {
        return false;
    }

    $payload = @json_decode(@file_get_contents($recordPath), true);
    if (!is_array($payload) || !isset($payload['username'], $payload['expires'])) {
        return false;
    }
    if (!is_int($payload['expires']) || $payload['expires'] < time()) {
        @unlink($recordPath);
        return false;
    }
    if (!is_string($payload['username']) || !hash_equals($payload['username'], $username)) {
        return false;
    }
    if (!@unlink($recordPath)) {
        return false;
    }
    return true;
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
