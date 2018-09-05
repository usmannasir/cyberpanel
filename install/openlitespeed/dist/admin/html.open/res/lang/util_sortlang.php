<?php

if ($argc == 1) {
	echo "Usage: $argv[0] lang [mixed]
		lang is the language file you want to sort.
		If supply 2nd param mixed, the translated file will mix all the tags. \n\n";
	return;
}

include('../../lib/DMsg.php');

DMsg::Util_SortMsg($argv[1], $argv[2]);

