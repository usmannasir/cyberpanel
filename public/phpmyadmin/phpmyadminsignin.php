<?php


define("PMA_SIGNON_INDEX", 1);

try{

define('PMA_SIGNON_SESSIONNAME', 'SignonSession');
define('PMA_DISABLE_SSL_PEER_VALIDATION', TRUE);

if(isset($_GET['token'])){

    ### Get credentials using the token

    $token = $_GET['token'];
    $username = $_GET['username'];

    $url = "/dataBases/fetchDetailsPHPMYAdmin?token=" . $token . '&username=' . $username;

    header('Location: ' . $url);

}
else if(isset($_GET['logout'])){
   $params = session_get_cookie_params();
   setcookie(session_name(), '', time() - 86400, $params["path"], $params["domain"], $params["secure"], $params["httponly"] );
   session_destroy();
   header('Location: /dataBases/phpMyAdmin');
   return;
}
else if(isset($_GET['password'])){

    session_name(PMA_SIGNON_SESSIONNAME);
    @session_start();

    $username = $_GET['username'];
    $password = $_GET['password'];

    $_SESSION['PMA_single_signon_user'] = $username;
    $_SESSION['PMA_single_signon_password'] = $password;
    $_SESSION['PMA_single_signon_host'] = 'localhost';


    @session_write_close();

    header('Location: /phpmyadmin/index.php?server=' . PMA_SIGNON_INDEX);
}
}catch (Exception $e) {
    echo 'Caught exception: ',  $e->getMessage(), "\n";
    $params = session_get_cookie_params();
    setcookie(session_name(), '', time() - 86400, $params["path"], $params["domain"], $params["secure"], $params["httponly"] );
    session_destroy();
    header('Location: /dataBases/phpMyAdmin');
    return;
}