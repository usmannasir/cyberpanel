<?php
// Private synthetic key for root-run native fixture tests; never production key.
$peerFixtureKey = tempnam(sys_get_temp_dir(), 'pma-peer-fixture-');
file_put_contents($peerFixtureKey, str_repeat('a', 64));
chmod($peerFixtureKey, 0640);
define('PMA_PEER_KEY_PATH', $peerFixtureKey);
register_shutdown_function(function () use ($peerFixtureKey) { @unlink($peerFixtureKey); });
