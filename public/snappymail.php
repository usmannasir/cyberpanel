<?php
$_ENV['snappymail_INCLUDE_AS_API'] = true;
include '/usr/local/CyberCP/public/snappymail/index.php';

$oConfig = \snappymail\Api::Config();
$oConfig->SetPassword('u2wfFtdy3WLLQT');
echo $oConfig->Save() ? 'Done' : 'Error';

?>