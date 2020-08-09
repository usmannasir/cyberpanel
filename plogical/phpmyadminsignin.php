<?php


define("PMA_SIGNON_INDEX", 1);


define('PMA_SIGNON_SESSIONNAME', 'SignonSession');
define('PMA_DISABLE_SSL_PEER_VALIDATION', TRUE);

if(isset($_GET['token'])){

    ### Get credentials using the token

    $token = $_GET['token'];
    $username = $_GET['username'];

    $url = "/dataBases/fetchDetailsPHPMYAdmin?token=" . $token . '&username=' . $username;

    header('Location: ' . $url);

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

echo 'Failed login';