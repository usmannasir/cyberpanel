<?php

if ($argc != 3)
  die ("require parameter SERVER_ROOT and [recover script file path | 2xml ]");
  
$SERVROOT = $argv[1];

ini_set('include_path', "../html.open/lib/:../html.open/lib/ows/:../html.open/view/:../html.open/view/inc/:.");

date_default_timezone_set('America/New_York');

spl_autoload_register( function ($class) {
 include $class . '.php';
});


if ($argv[2] == "2xml" )
	CData::Util_Migrate_AllConf2Xml($SERVROOT);
else
	CData::Util_Migrate_AllXml2Conf($SERVROOT, $argv[2], 1);

?>
