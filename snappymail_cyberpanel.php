#!/usr/bin/php
<?php
/**
 * CyberPanel SnappyMail post-install configuration (bundled; do not wget upstream).
 */
define('SNAPPYMAIL_PUBLIC_DIR', '/usr/local/CyberCP/public/snappymail');
define('SNAPPYMAIL_DATA_PATH', '/usr/local/lscp/cyberpanel/snappymail/data/');

if (PHP_SAPI !== 'cli' && false === stripos(php_sapi_name(), 'cli')) {
	exit('not cli');
}

chdir(SNAPPYMAIL_PUBLIC_DIR);

spl_autoload_register(function ($sClassName) {
	$file = SNAPPYMAIL_LIBRARIES_PATH . strtolower(strtr($sClassName, '\\', DIRECTORY_SEPARATOR)) . '.php';
	if (is_file($file)) {
		include_once $file;
	}
});

file_put_contents(
	SNAPPYMAIL_PUBLIC_DIR . '/include.php',
	str_replace(
		"//define('APP_DATA_FOLDER_PATH', dirname(__DIR__) . '/snappymail-data/');",
		"define('APP_DATA_FOLDER_PATH', '" . SNAPPYMAIL_DATA_PATH . "');",
		file_get_contents(SNAPPYMAIL_PUBLIC_DIR . '/_include.php')
	)
);

$_ENV['SNAPPYMAIL_INCLUDE_AS_API'] = true;
require_once SNAPPYMAIL_PUBLIC_DIR . '/index.php';

$oConfig = RainLoop\Api::Config();

$oConfig->Set('ssl', 'verify_certificate', false);
$oConfig->Set('plugins', 'enable', true);

SnappyMail\Repository::installPackage('plugin', 'mailbox-detect');

$oPlugin = RainLoop\Api::Actions()->Plugins()->CreatePluginByName('mailbox-detect');
if ($oPlugin) {
	$oPluginConfig = $oPlugin->Config();
	$oPluginConfig->Set('plugin', 'autocreate_system_folders', true);
	$oPluginConfig->Save();
}

$aList = SnappyMail\Repository::getEnabledPackagesNames();
$aList[] = 'mailbox-detect';
$oConfig->Set('plugins', 'enabled_list', implode(',', array_unique($aList)));

$oConfig->Save();
