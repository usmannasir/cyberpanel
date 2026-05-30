<?php


define("PMA_SIGNON_INDEX", 1);

// Policy helper lives in plogical/; public/phpmyadmin/ copy may not include it
$_lpma_policy = dirname(__DIR__) . '/plogical/lpma_policy_read.inc.php';
if (is_readable($_lpma_policy)) {
    require_once $_lpma_policy;
} elseif (is_readable(__DIR__ . '/lpma_policy_read.inc.php')) {
    require_once __DIR__ . '/lpma_policy_read.inc.php';
} else {
    http_response_code(500);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'phpMyAdmin sign-on is misconfigured: lpma_policy_read.inc.php is missing.';
    exit;
}

try {
    define('PMA_SIGNON_SESSIONNAME', 'SignonSession');
    define('PMA_DISABLE_SSL_PEER_VALIDATION', TRUE);

    function lpma_set_strict_cookie($enabled) {
        $opts = array(
            'expires' => $enabled ? (time() + 86400) : (time() - 86400),
            'path' => '/phpmyadmin/',
            'secure' => isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
            'httponly' => true,
            'samesite' => 'Lax',
        );
        setcookie('PMA_LPMA_STRICT', $enabled ? '1' : '', $opts);
    }

    function lpma_global_strict_mode_enabled() {
        $p = lpma_read_limited_policy();
        return ! empty($p['strict_mode']);
    }

    // Handle both GET and POST parameters for token and username
    $token = isset($_POST['token']) ? $_POST['token'] : (isset($_GET['token']) ? $_GET['token'] : null);
    $username = isset($_POST['username']) ? $_POST['username'] : (isset($_GET['username']) ? $_GET['username'] : null);

    if ($token && $username) {

        ### Get credentials using the token

        $token = htmlspecialchars($token, ENT_QUOTES, 'UTF-8');
        $username = htmlspecialchars($username, ENT_QUOTES, 'UTF-8');

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
        lpma_set_strict_cookie(false);
        session_name(PMA_SIGNON_SESSIONNAME);
        @session_start();
        $_SESSION = array();
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 86400, $params["path"], $params["domain"], $params["secure"], $params["httponly"]);
        session_destroy();
        header('Location: /base/');
        exit;
    } else if (isset($_POST['password'])) {

        session_name(PMA_SIGNON_SESSIONNAME);
        @session_start();

        $username = htmlspecialchars($_POST['username'], ENT_QUOTES, 'UTF-8');
        $password = $_POST['password'];
        $strictMode = (isset($_POST['lpma_strict']) && $_POST['lpma_strict'] === '1');
        $isLimitedUser = (strpos($username, 'cpma_') === 0);
        $host = isset($_POST['host']) ? trim($_POST['host']) : '127.0.0.1';
        if ($host === 'localhost') { $host = '127.0.0.1'; }

        $effectiveStrictMode = ($strictMode || lpma_global_strict_mode_enabled()) && $isLimitedUser;
        lpma_set_strict_cookie($effectiveStrictMode);

        $_SESSION['PMA_single_signon_user'] = $username;
        $_SESSION['PMA_single_signon_password'] = $password;
        $_SESSION['PMA_single_signon_host'] = $host;

        @session_write_close();

        header('Location: /phpmyadmin/index.php?server=' . PMA_SIGNON_INDEX);
    }
} catch (Exception $e) {
    echo 'Caught exception: ', $e->getMessage(), "\n";
    $params = session_get_cookie_params();
    setcookie(session_name(), '', time() - 86400, $params["path"], $params["domain"], $params["secure"], $params["httponly"]);
    session_destroy();
    header('Location: /dataBases/phpMyAdmin');
    return;
}
