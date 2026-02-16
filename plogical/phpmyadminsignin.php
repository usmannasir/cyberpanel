<?php


define("PMA_SIGNON_INDEX", 1);

try {
    define('PMA_SIGNON_SESSIONNAME', 'SignonSession');
    define('PMA_DISABLE_SSL_PEER_VALIDATION', TRUE);

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
        $host = isset($_POST['host']) ? trim($_POST['host']) : '127.0.0.1';
        if ($host === 'localhost') { $host = '127.0.0.1'; }

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
