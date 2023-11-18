<?php
$_ENV['snappymail_INCLUDE_AS_API'] = true;
include '/usr/local/CyberCP/public/snappymail/index.php';

$oConfig = \snappymail\Api::Config();
$oConfig->SetPassword('HhvovdTfICGHLR');
echo $oConfig->Save() ? 'Done' : 'Error';

?>