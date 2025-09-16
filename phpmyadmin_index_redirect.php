<?php
/**
 * phpMyAdmin Access Control - Direct Access Redirect
 * 
 * This file should be placed at /usr/local/CyberCP/public/phpmyadmin/index.php
 * to replace the default phpMyAdmin index.php and redirect unauthenticated users
 * to the CyberPanel login page.
 */

// Check if user is logged into CyberPanel
session_start();
if (!isset($_SESSION['userID'])) {
    // Redirect to CyberPanel login page
    header('Location: /base/');
    exit();
}

// If user is authenticated, redirect to the actual phpMyAdmin interface
// through the proper CyberPanel route
header('Location: /dataBases/phpMyAdmin');
exit();
?>
