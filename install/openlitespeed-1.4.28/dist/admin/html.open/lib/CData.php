<?php

class CData
{
	private $_type; //{'serv','admin','vh','tp','special'}
	private $_id;

	private $_root;

	private $_path;
	private $_xmlpath;

	private $_conferr;

	public function __construct($type, $path, $id=NULL)
	{
		$this->_type = $type;
		$this->_id = $id;
		$isnew = ($id != NULL && $id[0] == '`');

		if ($type == DInfo::CT_EX) {
			$this->_path = $path;
			$this->init_special();
		}
		else {
			$pos = strpos($path, '.xml');
			if ($pos > 0) {
				$this->_xmlpath = $path;
				$this->_path = substr($path, 0, $pos) . '.conf';
			}
			else {
				$pos = strpos($path, '.conf');
				if ($pos > 0) {
					$this->_path = $path;
					$this->_xmlpath = substr($path, 0, $pos) . '.xml';
				}
				else {
					// assume xml format
					$this->_xmlpath = $path . '.xml'; // forced
					$this->_path = $path . '.conf';
				}
			}
			$this->init($isnew);
		}
	}

	public static function Util_Migrate_AllConf2Xml($SERVER_ROOT)
	{
		// will migrate all included vh and tp xml files
		if ($SERVER_ROOT == '' || trim($SERVER_ROOT) == '')
			die("Require SERVER_ROOT as input param!");

		error_log("Migrate plain conf to xml from $SERVER_ROOT\n");

		if ( $SERVER_ROOT{-1} != '/' )
			$SERVER_ROOT .= '/';

		define('SERVER_ROOT', $SERVER_ROOT);

		$servconf = SERVER_ROOT . 'conf/httpd_config.conf';

		$cdata = new CData(DInfo::CT_SERV, $servconf);
		$cdata->migrate_allconf2xml();

		$adminconf = SERVER_ROOT . 'admin/conf/admin_config.conf';
		$admindata = new CData(DInfo::CT_ADMIN, $adminconf);
		$filemap = DPageDef::GetInstance()->GetFileMap(DInfo::CT_ADMIN);
		$admindata->save_xml_file($admindata->_root, $filemap, $admindata->_xmlpath);
		$admindata->copy_permission($admindata->_path, $admindata->_xmlpath);
		error_log("Migration done.\n");
	}

	public static function Util_Migrate_AllXml2Conf($SERVER_ROOT, $recover_script, $removexml)
	{
		// will migrate all included vh and tp xml files
		if ($SERVER_ROOT == '' || trim($SERVER_ROOT) == '')
			die("Require SERVER_ROOT as input param!");

		if ($recover_script == '' || trim($recover_script) == '')
			die("Require recover script as input param!");

		if ($removexml != 1 && $removexml != 0)
			die("Require removexml as input param with value 1 or 0.");

		error_log("Migrate xml to plain conf under server root $SERVER_ROOT\n");
		if ( $SERVER_ROOT{-1} != '/' )
			$SERVER_ROOT .= '/';

		define('SERVER_ROOT', $SERVER_ROOT);

		$servconf = SERVER_ROOT . 'conf/httpd_config.xml';
		if (!file_exists($servconf)) {
			die("cannot find xml config file $servconf under server root $SERVER_ROOT\n");
		}

		$timestamp = date(DATE_RFC2822);
		$script = "#!/bin/sh

########################################################################################
#  xml configuration files (.xml) were migrated to plain configuration (.conf) on $timestamp
#  If you need to revert back to older versions that based on xml configuration, please manually
#  run this script to restore the original files.
######################################################################################## \n\n";

		if (file_put_contents($recover_script, $script) === FALSE) {
			die("Failed to write to recover script $recover_script, abort!");
		}

		define('RECOVER_SCRIPT', $recover_script);

		if ($removexml == 0)
			define ('SAVE_XML', 1);

		$cdata = new CData(DInfo::CT_SERV, $servconf);

		// migrate admin conf
		$adminconf = SERVER_ROOT . 'admin/conf/admin_config.xml';
		$admindata = new CData(DInfo::CT_ADMIN, $adminconf);

		if (defined('RECOVER_SCRIPT')) {
			chmod(RECOVER_SCRIPT, 0700);
			error_log("You can recover the migrated xml configuration files from this script " . RECOVER_SCRIPT . "\n");
		}

		error_log("Migration done.\n");
	}

	public function GetRootNode()
	{
		return $this->_root;
	}

	public function GetId()
	{
		return $this->_id;
	}

	public function GetType()
	{
		return $this->_type;
	}

	public function GetConfErr()
	{
		return $this->_conferr;
	}

	public function GetChildrenValues($location, $ref='')
	{
		$vals = array();
		$layer = $this->_root->GetChildrenByLoc($location, $ref);
		if ($layer != NULL) {
			if (is_array($layer))
				$vals = array_map('strval', array_keys($layer));
			else
				$vals[] = $layer->Get(CNode::FLD_VAL);
		}
		return $vals;
	}

	public function GetChildVal($location, $ref='')
	{
		$layer = $this->_root->GetChildrenByLoc($location, $ref);
		if ($layer != NULL && is_a($layer, 'CNode'))
			return $layer->Get(CNode::FLD_VAL);
		else
			return NULL;
	}

	public function GetChildNodeById($key, $id)
	{
		return $this->_root->GetChildNodeById($key, $id);
	}

	public function SetRootNode($nd)
	{
		$this->_root = $nd;
		$this->_root->SetVal($this->_path);
		$this->_root->Set(CNode::FLD_TYPE, CNode::T_ROOT);
	}

	public function SavePost($extractData, $disp)
	{
		$tid = $disp->GetLast(DInfo::FLD_TID);
		if ($this->_type == DInfo::CT_EX)
			$ref = $disp->GetLast(DInfo::FLD_REF);
		else
			$ref = $disp->Get(DInfo::FLD_REF);
		$tblmap = DPageDef::GetPage($disp)->GetTblMap();
		$location = $tblmap->FindTblLoc($tid);
		$this->_root->UpdateChildren($location, $ref, $extractData);

		if (($newref = $extractData->Get(CNode::FLD_VAL)) != NULL)
			$this->check_integrity($tid, $newref, $disp);

		$this->SaveFile();
	}

	public function ChangeContextSeq($seq)
	{
		$loc = ($this->_type == DInfo::CT_VH) ? 'context' : 'virtualHostConfig:context';
		if ( ($ctxs = $this->_root->GetChildren($loc)) == NULL)
			return FALSE;

		if ( !is_array($ctxs) || $seq == -1 || $seq == count($ctxs) )
			return FALSE;

		if ( $seq > 0 ) {
			$index = $seq - 1;
			$switched = $seq;
		}
		else {
			$index = - $seq - 1;
			$switched = $index - 1;
		}

		$parent = NULL;
		$uris = array_keys($ctxs);
		$temp = $uris[$switched];
		$uris[$switched] = $uris[$index];
		$uris[$index] = $temp;

		foreach( $uris as $uri ) {
			$ctx = $ctxs[$uri];
			if ($parent == NULL) {
				$parent = $ctx->Get(CNode::FLD_PARENT);
				$parent->RemoveChild('context');
			}
			$parent->AddChild($ctx);
		}
		$this->SaveFile();
		return TRUE;
	}


	public function DeleteEntry($disp)
	{
		$tid = $disp->GetLast(DInfo::FLD_TID);
		if ($this->_type == DInfo::CT_EX)
			$ref = $disp->GetLast(DInfo::FLD_REF);
		else
			$ref = $disp->Get(DInfo::FLD_REF);
		$tblmap = DPageDef::GetPage($disp)->GetTblMap();
		$location = $tblmap->FindTblLoc($tid);

		$layer = $this->_root->GetChildrenByLoc($location, $ref);
		if ($layer != NULL) {
			$layer->RemoveFromParent();
			$this->check_integrity($tid, NULL, $disp);
			$this->SaveFile();
		}
		else {
			error_log("cannot find delete entry\n");
		}
	}

	public function SaveFile()
	{
		if ($this->_type == DInfo::CT_EX)
			return $this->save_special();

		$filemap = DPageDef::GetInstance()->GetFileMap($this->_type);   // serv, vh, tp, admin
		$root = $this->save_conf_file($this->_root, $filemap, $this->_path);

		if (defined('SAVE_XML'))
			$this->save_xml_file($root, $filemap, $this->_xmlpath);

	}

	private function check_integrity($tid, $newref, $disp)
	{
		if ( ($ref = $disp->GetLast(DInfo::FLD_REF)) == NULL || $newref == $ref) {
			return;
		}

		if ( in_array($tid, array('ADM_L_GENERAL', 'T_TOPD', 'V_TOPD', 'V_BASE', 'L_GENERAL')) ) {
			$disp->Set(DInfo::FLD_ViewName, $newref);
		}

		$root = $disp->Get(DInfo::FLD_ConfData)->GetRootNode();

		if (($tid == 'V_BASE' || $tid == 'V_TOPD')
		&& ($dlayer = $root->GetChildren('listener')) != NULL ) {
			if (!is_array($dlayer))
				$dlayer = array($dlayer);

			foreach ($dlayer as $listener) {
				if ( ($maplayer = $listener->GetChildren('vhmap')) != NULL) {
					if (!is_array($maplayer))
						$maplayer = array($maplayer);
					foreach ($maplayer as $map) {
						if ($map->Get(CNode::FLD_VAL) == $ref) {
							if ($newref == NULL) {
								$map->RemoveFromParent();  // handle delete
							}
							else {
								$map->SetVal($newref);
								if ($map->GetChildren('vhost') != NULL)
									$map->SetChildVal('vhost', $newref);
							}
							break;
						}
					}
				}
			}
		}

		if ($newref == NULL)  // for delete condition, do not auto delete, let user handle
			return;

		if ($tid == 'L_GENERAL'
				&& ($dlayer = $root->GetChildren('vhTemplate')) != NULL ) {
			if (!is_array($dlayer))
				$dlayer = array($dlayer);

			foreach($dlayer as $templ) {
				if (($listeners = $templ->GetChildVal('listeners')) != NULL) {
					$changed = FALSE;
					$lns = preg_split("/, /", $listeners, -1, PREG_SPLIT_NO_EMPTY);
					foreach ($lns as $i => $ln) {
						if ($ln == $ref) {
							$lns[$i] = $newref;
							$changed = TRUE;
							break;
						}
					}
					if ($changed) {
						$listeners = implode(', ', $lns);
						$templ->SetChildVal('listeners', $listeners);
					}
				}
			}
		}
		elseif (strncmp($tid, 'A_EXT_', 6) == 0 ) {
			$disp_view = $disp->Get(DInfo::FLD_View);
			$loc = ($disp_view == DInfo::CT_TP) ? 'virtualHostConfig:scripthandler:addsuffix' : 'scripthandler:addsuffix';
			if (($dlayer = $root->GetChildren($loc)) != NULL) {
				if (!is_array($dlayer))
					$dlayer = array($dlayer);

				foreach ($dlayer as $sh) {
					if ($sh->GetChildVal('handler') == $ref)
						$sh->SetChildVal('handler', $newref);
				}
			}

			if ( $disp_view != DInfo::CT_SERV )	{
				$loc = ($disp_view == DInfo::CT_TP) ? 'virtualHostConfig:context' : 'context';
				if (($dlayer = $root->GetChildren($loc)) != NULL) {
					if (!is_array($dlayer))
						$dlayer = array($dlayer);

					foreach ($dlayer as $ctx) {
						if ($ctx->GetChildVal('authorizer') == $ref)
							$ctx->SetChildVal('authorizer', $newref);
						if ($ctx->GetChildVal('handler') == $ref)
							$ctx->SetChildVal('handler', $newref);
					}
				}

			}
		}
		elseif (strpos($tid, '_REALM_')) { //'T_REALM_FILE','V_REALM_FILE','VT_REALM_LDAP'
			$loc = ($disp->Get(DInfo::FLD_View) == DInfo::CT_TP) ? 'virtualHostConfig:context' : 'context';
			if (($dlayer = $root->GetChildren($loc)) != NULL) {
				if (!is_array($dlayer))
					$dlayer = array($dlayer);

				foreach ($dlayer as $ctx) {
					if ($ctx->GetChildVal('realm') == $ref)
						$ctx->SetChildVal('realm', $newref);
				}
			}
		}
	}



	private function save_conf_file($root, $filemap, $filepath)
	{
		$convertedroot = $root->DupHolder();
		$filemap->Convert(1, $root, 1, $convertedroot);

		$confbuf = '';
		$this->before_write_conf($convertedroot);
		$convertedroot->PrintBuf($confbuf);
		$this->write_file($filepath, $confbuf);
		return $convertedroot;
	}

	private function save_xml_file($root, $filemap, $filepath)
	{
		$this->before_write_xml($root);
		$xmlroot = $root->DupHolder();
		$filemap->Convert(1, $root, 0, $xmlroot);

		$xmlbuf = '';
		$xmlroot->PrintXmlBuf($xmlbuf);
		$this->write_file($filepath, $xmlbuf);
		return $xmlroot;
	}

	private function before_write_conf($root)
	{
		if ($this->_type == DInfo::CT_SERV && ($listeners = $root->GetChildren('listener')) != NULL) {
			if (!is_array($listeners))
				$listeners = array($listeners);
			foreach ($listeners as $l) {
				if (($maps = $l->GetChildren('vhmap')) != NULL) {
					if (!is_array($maps))
						$maps = array($maps);
					foreach ($maps as $map) {
						$vn = $map->Get(CNode::FLD_VAL);
						$domain = $map->GetChildVal('domain');
						$l->AddChild(new CNode('map', "$vn $domain"));
					}
					$l->RemoveChild('vhmap');
				}
			}
		}

		$loc = ($this->_type == DInfo::CT_TP) ? 'virtualHostConfig:scripthandler' : 'scripthandler';
		if ( ($sh = $root->GetChildren($loc)) != NULL) {
			if (($shc = $sh->GetChildren('addsuffix')) != NULL) {
				if (!is_array($shc))
					$shc = array($shc);
				foreach ($shc as $shcv) {
					$suffix = $shcv->Get(CNode::FLD_VAL);
					$type = $shcv->GetChildVal('type');
					$handler = $shcv->GetChildVal('handler');
					$sh->AddChild(new CNode('add', "$type:$handler $suffix"));
				}
				$sh->RemoveChild('addsuffix');
			}
		}

		if ($this->_type == DInfo::CT_TP) {
			$vhconf = $root->GetChildVal('configFile');
			if (($pos = strpos($vhconf, '.xml')) > 0) {
				$vhconf = substr($vhconf, 0, $pos) . '.conf';
				$root->SetChildVal('configFile', $vhconf);
			}
		}
	}

	private function before_write_xml($root)
	{
		if ( $this->_type == DInfo::CT_SERV ) {
			if (($listeners = $root->GetChildren('listener')) != NULL) {
				if (!is_array($listeners))
					$listeners = array($listeners);
				foreach ($listeners as $l) {
					if (($maps = $l->GetChildren('map')) != NULL) {
						if (!is_array($maps))
							$maps = array($maps);
						foreach ($maps as $map) {
							$mapval = $map->Get(CNode::FLD_VAL);
							if (($pos = strpos($mapval, ' ')) > 0) {
								$vn = substr($mapval, 0, $pos);
								$domain = trim(substr($mapval, $pos + 1));
								$anode = new CNode('vhmap', $vn);
								$anode->AddChild(new CNode('vhost', $vn));
								$anode->AddChild(new CNode('domain', $domain));
								$l->AddChild($anode);
							}
						}
						$l->RemoveChild('map');
					}
				}
			}
			if ($root->GetChildren('adminRoot') == NULL) {
				// backward compatible
				$root->AddChild(new CNode('adminRoot', '$SERVER_ROOT/admin/'));
			}
			elseif ($root->GetChildVal('adminRoot') == NULL) {
				$root->SetChildVal('adminRoot', '$SERVER_ROOT/admin/');
			}

			if (($vhosts = $root->GetChildren('virtualhost')) != NULL) {
				if (!is_array($vhosts))
					$vhosts = array($vhosts);
				foreach ($vhosts as $vh) {
					$vhconf = $vh->GetChildVal('configFile');
					if (($pos = strpos($vhconf, '.conf')) > 0) {
						$vhconf = substr($vhconf, 0, $pos) . '.xml';
						$vh->SetChildVal('configFile', $vhconf);
					}
				}
			}

			// migrate all tp.xml
			if (($tps = $root->GetChildren('vhTemplate')) != NULL) {
				if (!is_array($tps))
					$tps = array($tps);
				foreach ($tps as $tp) {
					$tpconf = $tp->GetChildVal('templateFile');
					if (($pos = strpos($tpconf, '.conf')) > 0) {
						$tpconf = substr($tpconf, 0, $pos) . '.xml';
						$tp->SetChildVal('templateFile', $tpconf);
					}
				}
			}

		}

		$loc = ($this->_type == DInfo::CT_TP) ? 'virtualHostConfig:scripthandler' : 'scripthandler';
		if ( ($sh = $root->GetChildren($loc)) != NULL) {
			if (($shc = $sh->GetChildren('add')) != NULL) {
				if (!is_array($shc))
					$shc = array($shc);
				foreach ($shc as $shcv) {
					$typeval = $shcv->Get(CNode::FLD_VAL);
					if (preg_match("/^(\w+):(\S+)\s+(.+)$/", $typeval, $m)) {
						$anode = new CNode('addsuffix', $m[3]);
						$anode->AddChild(new CNode('suffix', $m[3]));
						$anode->AddChild(new CNode('type', $m[1]));
						$anode->AddChild(new CNode('handler', $m[2]));
						$sh->AddChild($anode);
					}
				}
				$sh->RemoveChild('add');
			}

		}

		if ($this->_type == DInfo::CT_TP) {
			$vhconf = $root->GetChildVal('configFile');
			if (($pos = strpos($vhconf, '.conf')) > 0) {
				$vhconf = substr($vhconf, 0, $pos) . '.xml';
				$root->SetChildVal('configFile', $vhconf);
			}
		}
	}

	private function after_read()
	{
		if ($this->_type == DInfo::CT_SERV) {
			$serverName = $this->_root->GetChildVal('serverName');
		 	if ($serverName == '$HOSTNAME' || $serverName == '') {
				$serverName = php_uname('n');
		 	}
		 	$this->_id = $serverName;

		 	$runningAs = 'user('. $this->_root->GetChildVal('user') .
		 		') : group(' . $this->_root->GetChildVal('group') .')' ;
		 	$this->_root->AddChild(new CNode('runningAs', $runningAs));
        }

        if ($this->_type == DInfo::CT_SERV || $this->_type == DInfo::CT_ADMIN) {
		 	if ( ($listeners = $this->_root->GetChildren('listener')) != NULL) {
		 		if (!is_array($listeners))
		 			$listeners = array($listeners);
		 		foreach ($listeners as $l) {
		 			$addr = $l->GetChildVal('address');
		 			if ( $pos = strrpos($addr,':') ) {
		 				$ip = substr($addr, 0, $pos);
		 				if ( $ip == '*' )
		 					$ip = 'ANY';
		 				$l->AddChild(new CNode('ip', $ip));
		 				$l->AddChild(new CNode('port', substr($addr, $pos+1)));
		 			}
		 			if (($maps = $l->GetChildren('map')) != NULL) {
		 				if (!is_array($maps))
		 					$maps = array($maps);
		 				foreach ($maps as $map) {
		 					$mapval = $map->Get(CNode::FLD_VAL);
		 					if (($pos = strpos($mapval, ' ')) > 0) {
		 						$vn = substr($mapval, 0, $pos);
		 						$domain = trim(substr($mapval, $pos + 1));
		 						$anode = new CNode('vhmap', $vn);
		 						$anode->AddChild(new CNode('vhost', $vn));
		 						$anode->AddChild(new CNode('domain', $domain));
		 						$l->AddChild($anode);
		 					}
		 				}
		 				$l->RemoveChild('map');
		 			}
		 		}
		 	}

		}

        if ($this->_type == DInfo::CT_VH || $this->_type == DInfo::CT_TP) {
			$loc = ($this->_type == DInfo::CT_VH) ? 'context' : 'virtualHostConfig:context';
			if ( ($ctxs = $this->_root->GetChildren($loc)) != NULL) {
				if (!is_array($ctxs))
					$ctxs = array($ctxs);
				$order = 1;
				foreach ($ctxs as $ctx) {
					$ctx->AddChild(new CNode('order', $order++));
				}
			}
		}

		$loc = ($this->_type == DInfo::CT_TP) ? 'virtualHostConfig:scripthandler' : 'scripthandler';
		if ( ($sh = $this->_root->GetChildren($loc)) != NULL) {
			if (($shc = $sh->GetChildren('add')) != NULL) {
				if (!is_array($shc))
					$shc = array($shc);
				foreach ($shc as $shcv) {
					$typeval = $shcv->Get(CNode::FLD_VAL);
					if (preg_match("/^(\w+):(\S+)\s+(.+)$/", $typeval, $m)) {
						$anode = new CNode('addsuffix', $m[3]);
						$anode->AddChild(new CNode('suffix', $m[3]));
						$anode->AddChild(new CNode('type', $m[1]));
						$anode->AddChild(new CNode('handler', $m[2]));
						$sh->AddChild($anode);
					}

				}
				$sh->RemoveChild('add');
			}

		}


	}

	private function init($isnew)
	{
		if ($isnew) {
			if ( !file_exists($this->_path) && ! PathTool::createFile($this->_path, $err) ) {
				$this->_conferr = 'Failed to create config file at ' . $this->_path;
				return FALSE;
			}
			else {
				$this->_root = new CNode(CNode::K_ROOT, $this->_path, CNode::T_ROOT);
				return TRUE;
			}
		}

		if (!file_exists($this->_path) || filesize($this->_path) < 10) {

			if ($this->_type == DInfo::CT_SERV) {
				if (file_exists($this->_xmlpath) && !$this->migrate_allxml2conf())
					return FALSE;
				else {
					$this->_conferr = 'Failed to find config file at ' . $this->_path;
					return FALSE;
				}
			}
			else {
				if (file_exists($this->_xmlpath)) {
					if (!$this->migrate_xml2conf())
						return FALSE;
				}
				else {// treat as new vh or tp
					$this->_root = new CNode(CNode::K_ROOT, $this->_path, CNode::T_ROOT);
					return TRUE;
				}
			}
		}

		$parser = new PlainConfParser();
		$this->_root = $parser->Parse($this->_path);
		if ($this->_root->HasFatalErr()) {
			$this->_conferr = $this->_root->GetErr();
			error_log("fatel err " . $this->_root->GetErr());
			return FALSE;
		}

		$this->after_read();
		return TRUE;
	}

	private function init_special()
	{
		$lines = file($this->_path);
		if ( $lines === FALSE ) {
			return FALSE;
		}

		$this->_root = new CNode(CNode::K_ROOT, $this->_id, CNode::T_ROOT);
		$items = array();

		if ($this->_id == 'MIME') {
			foreach( $lines as $line ) {
				if ( ($c = strpos($line, '=')) > 0 ) {
					$suffix = trim(substr($line, 0, $c));
					$type = trim(substr($line, $c+1 ));
					$m = new CNode('index', $suffix);
					$m->AddChild(new CNode('suffix', $suffix));
					$m->AddChild(new CNode('type', $type));
					$items[$suffix] = $m;
				}
			}

		}
		elseif ( $this->_id == 'ADMUSR' || $this->_id == 'V_UDB') {
			foreach( $lines as $line ) {
				$parsed = explode(':',trim($line));
				$size = count($parsed);
				if($size == 2 || $size ==3) {
					$name = trim($parsed[0]);
					$pass = trim($parsed[1]);
					if ($name != '' && $pass != '') {
						$u = new CNode('index', $name);
						$u->AddChild(new CNode('name', $name));
						$u->AddChild(new CNode('passwd', $pass));
						if ($size == 3 && (($group = trim($parsed[2])) != '')) {
							$u->AddChild(new CNode('group', $group));
						}
						$items[$name] = $u;
					}
				}
			}
		}
		elseif ($this->_id == 'V_GDB') {
			foreach( $lines as $line ) {
				$parsed = explode(':',trim($line));
				if (count($parsed) == 2) {
					$group = trim($parsed[0]);
					$users = trim($parsed[1]);
					if ($group != '') {
						$g = new CNode('index', $group);
						$g->AddChild(new CNode('name', $group));
						$g->AddChild(new CNode('users', $users));
						$items[$group] = $g;
					}
				}
			}
		}

		ksort($items, SORT_STRING);
		reset($items);
		foreach( $items as $item ) {
			$this->_root->AddChild($item);
		}
		return TRUE;
	}

	private function save_special()
	{
		$fd = fopen($this->_path, 'w');
		if ( !$fd ) {
			return FALSE;
		}

		$items = $this->_root->GetChildren('index');

		if ($items != NULL) {
			if (is_array($items)) {
				ksort($items, SORT_STRING);
				reset($items);
			}
			else
				$items = array($items);

			foreach ($items as $key => $item) {
				$line = '';
				if ($this->_id == 'MIME') {
					$line = str_pad($key, 8) . ' = ' . $item->GetChildVal('type') . "\n";
				}
				elseif ($this->_id == 'ADMUSR' || $this->_id == 'V_UDB') {
					$line = $item->GetChildVal('name') . ':' . $item->GetChildVal('passwd');
					$group = $item->GetChildVal('group');
					if ($group != NULL)
						$line .= ':' . $group;
					$line .= "\n";
				}
				else if ($this->_id == 'V_GDB') {
					$line = $key . ':' . $item->GetChildVal('users') . "\n";
				}
				fputs( $fd, $line );
			}
		}
		fclose($fd);
		return TRUE;
	}

	private function migrate_xml2conf()
	{
		error_log("Migrating $this->_xmlpath \n");
		$xmlparser = new XmlParser();
		$xmlroot = $xmlparser->Parse($this->_xmlpath);
		if ($xmlroot->HasFatalErr()) {
			$this->_conferr = $xmlroot->Get(CNode::FLD_ERR);
			return FALSE;
		}

		$root = $xmlroot->DupHolder();
		$filemap = DPageDef::GetInstance()->GetFileMap($this->_type);   // serv, vh, tp, admin
		$filemap->Convert(0, $xmlroot, 1, $root);

		$buf = '';
		$this->before_write_conf($root);
		$root->PrintBuf($buf);
		touch($this->_path);

		$this->write_file($this->_path, $buf);
		$this->copy_permission($this->_xmlpath, $this->_path);

		$migrated = $this->_xmlpath . '.migrated.' . time();
		if (defined('SAVE_XML')) {
			copy($this->_xmlpath, $migrated);
		}
		else {
			rename($this->_xmlpath, $migrated);
		}

		if (defined('RECOVER_SCRIPT')) {
			file_put_contents(RECOVER_SCRIPT, "mv $migrated $this->_xmlpath\n", FILE_APPEND);
		}
		error_log("  converted $this->_xmlpath to $this->_path\n\n");
		return TRUE;
	}

	private function copy_permission($fromfile, $tofile)
	{
		$owner = fileowner($fromfile);
		if (fileowner($tofile) != $owner)
			chown($tofile, $owner);
		$perm = fileperms($fromfile);
		if (fileperms($tofile) != $perm)
			chmod($tofile, $perm);
	}

	private function migrate_allxml2conf()
	{
		error_log("Migrating all config from server xml config $this->_xmlpath \n");
		$xmlparser = new XmlParser();
		$xmlroot = $xmlparser->Parse($this->_xmlpath);
		if ($xmlroot->HasFatalErr()) {
			$this->_conferr = $xmlroot->Get(CNode::FLD_ERR);
			return FALSE;
		}

		$root = $xmlroot->DupHolder();
		$filemap = DPageDef::GetInstance()->GetFileMap(DInfo::CT_SERV);   // serv, vh, tp, admin
		$filemap->Convert(0, $xmlroot, 1, $root);

		// migrate all vh.xml
		if (($vhosts = $root->GetChildren('virtualhost')) != NULL) {
			if (!is_array($vhosts))
				$vhosts = array($vhosts);
			foreach ($vhosts as $vh) {
				$vhname = $vh->Get(CNode::FLD_VAL);
				$vhroot = $vh->GetChildVal('vhRoot');
				$vhconf = $vh->GetChildVal('configFile');
				$conffile = PathTool::GetAbsFile($vhconf, 'VR', $vhname, $vhroot);
				$vhdata = new CData(DInfo::CT_VH, $conffile);
				if (($pos = strpos($vhconf, '.xml')) > 0) {
					$vhconf = substr($vhconf, 0, $pos) . '.conf';
					$vh->SetChildVal('configFile', $vhconf);
				}
			}
		}

		// migrate all tp.xml
		if (($tps = $root->GetChildren('vhTemplate')) != NULL) {
			if (!is_array($tps))
				$tps = array($tps);
			foreach ($tps as $tp) {
				$tpconf = $tp->GetChildVal('templateFile');
				$conffile = PathTool::GetAbsFile($tpconf, 'SR');
				$tpdata = new CData(DInfo::CT_TP, $conffile);
				if (($pos = strpos($tpconf, '.xml')) > 0) {
					$tpconf = substr($tpconf, 0, $pos) . '.conf';
					$tp->SetChildVal('templateFile', $tpconf);
				}
			}
		}

		$buf = '';
		$this->before_write_conf($root);
		$root->PrintBuf($buf);
		touch($this->_path);

		$this->write_file($this->_path, $buf);
		$this->copy_permission($this->_xmlpath, $this->_path);

		$migrated = $this->_xmlpath . '.migrated.' . time();

		if (defined('SAVE_XML')) {
			copy($this->_xmlpath, $migrated);
		}
		else {
			rename($this->_xmlpath, $migrated);
		}
		if (defined('RECOVER_SCRIPT')) {
			file_put_contents(RECOVER_SCRIPT, "mv $migrated $this->_xmlpath\n", FILE_APPEND);
		}

		error_log("  converted $this->_xmlpath to $this->_path\n\n");
	}

	private function migrate_allconf2xml()
	{
		if (($vhosts = $this->_root->GetChildren('virtualhost')) != NULL) {
			if (!is_array($vhosts))
				$vhosts = array($vhosts);
			$filemap = DPageDef::GetInstance()->GetFileMap(DInfo::CT_VH);
			foreach ($vhosts as $vh) {
				$vhname = $vh->Get(CNode::FLD_VAL);
				$vhroot = $vh->GetChildVal('vhRoot');
				$vhconf = $vh->GetChildVal('configFile');
				$conffile = PathTool::GetAbsFile($vhconf, 'VR', $vhname, $vhroot);
				$vhdata = new CData(DInfo::CT_VH, $conffile);
				$this->save_xml_file($vhdata->_root, $filemap, $vhdata->_xmlpath);
				$this->copy_permission($vhdata->_path, $vhdata->_xmlpath);
				error_log("  converted $vhdata->_path to $vhdata->_xmlpath\n");
			}
		}

		if (($tps = $this->_root->GetChildren('vhTemplate')) != NULL) {
			if (!is_array($tps))
				$tps = array($tps);
			$filemap = DPageDef::GetInstance()->GetFileMap(DInfo::CT_TP);
			foreach ($tps as $tp) {
				$tpconf = $tp->GetChildVal('templateFile');
				$conffile = PathTool::GetAbsFile($tpconf, 'SR');
				$tpdata = new CData(DInfo::CT_TP, $conffile);
				$this->save_xml_file($tpdata->_root, $filemap, $tpdata->_xmlpath);
				$this->copy_permission($tpdata->_path, $tpdata->_xmlpath);
				error_log("  converted $tpdata->_path to $tpdata->_xmlpath\n");
			}
		}

		$filemap = DPageDef::GetInstance()->GetFileMap(DInfo::CT_SERV);
		$this->save_xml_file($this->_root, $filemap, $this->_xmlpath);
		$this->copy_permission($this->_path, $this->_xmlpath);
		error_log("  converted $this->_path to $this->_xmlpath\n");
	}


	private function write_file($filepath, $buf)
	{
		if (!file_exists($filepath)) {
			// new file, check path exists
			if (!PathTool::createFile("{$filepath}.new", $err)) {
				error_log("failed to create file $filepath : $err \n");
				return FALSE;
			}
		}

		$fd = fopen("{$filepath}.new", 'w');
		if ( !$fd )	{
			error_log("failed to open in write mode for {$filepath}.new");
			return FALSE;
		}

		if(fwrite($fd, $buf) === FALSE) {
			error_log("failed to write temp config for {$filepath}.new");
			return FALSE;
		}
		fclose($fd);

		@unlink("{$filepath}.bak");
		if(file_exists($filepath) && !rename($filepath, "{$filepath}.bak")) {
			error_log("failed to rename {$filepath} to {$filepath}.bak");
			return FALSE;
		}

		if(!rename("{$filepath}.new", $filepath)) {
			error_log("failed to rename {$filepath}.new to {$filepath}");
			return FALSE;
		}

		return TRUE;
	}
}
