<?php

/*--------------------------------
assuming  following entry in /etc/snmp/snmpd.conf

pass .1.3.6.1.4.1.22253 /usr/bin/php smaple.php

if you change the default parent oid node: .1.3.6.1.4.1.22253, you must also modify the OID entries .xml files.
--------------------------------*/


require_once("class.litespeed_snmp_bridge.php");

$processes = 1; //<-- value of > 1 only valid LiteSpeed Enterprise (num of cpus licensed)
$report_path = "/tmp/lshttpd/"; //<-- path to .rtreport folder. Default is /tmp/lshttpd/

$cache_time = 0; //<-- seconds to cache parsed data
$cache_file = "/tmp/_lsws_sampe_cache.txt"; //<-- cache file..full path.


//get params from snmpd pass mechanism
if(array_key_exists(1,$_SERVER["argv"]) && array_key_exists(2,$_SERVER["argv"])) {
	$type = trim($_SERVER["argv"][1]);
	$oid = trim($_SERVER["argv"][2]);

	$bridge = new litespeed_snmp_bridge($processes, $report_path, $cache_time, $cache_file);
	$bridge->process($type, $oid);
	
}

?>
