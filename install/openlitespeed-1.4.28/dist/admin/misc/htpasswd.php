<?php
$raw = $_SERVER['argv'][1];
$valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.";
$limit = strlen($valid_chars)-1;
$isMac = (strtoupper(PHP_OS) === 'DARWIN');
if (CRYPT_MD5 == 1 && !$isMac) {
    $salt = '$1$';
    for($i = 0; $i < 8; $i++) 
    {
        $salt .= $valid_chars[rand(0,$limit)];
    }
    $salt .= '$';
}
else
{
    $salt = $valid_chars[rand(0,$limit)];
    $salt .= $valid_chars[rand(0,$limit)];
}
$encypt = crypt($raw, $salt);
echo "$encypt\n";
?>