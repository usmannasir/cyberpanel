<?php

class ControllerBase
{
	protected $_serv;
	protected $_admin;
	protected $_curOne; //vh or tp
	protected $_special;

	protected $_disp;
	protected $_service;

	protected static $_instance = NULL;

	protected function __construct()
	{
		$this->_disp = new DInfo();
	}

	public static function singleton()
	{
		if (!isset(self::$_instance)) {
			$c = __CLASS__;
			self::$_instance = new $c;
		}

		return self::$_instance;
	}

	public static function ConfigDispData()
	{
		$cc = self::singleton();

		$data = $cc->process_config();
		// temp
		if (is_a($data, 'CData'))
			$data = $data->GetRootNode();

		$cc->_disp->Set(DInfo::FLD_PgData, $data);

		return $cc->_disp;
	}

	public static function ServiceData($type)
	{
		$cc = self::singleton();
		$data = $cc->process_service_data($type);

		return $data;
	}

	public static function ServiceRequest($type, $actId = '')
	{
		$cc = self::singleton();
		$result = $cc->process_service_request($type, $actId);

		return $result;
	}

	public static function HasChanged()
	{
		return (isset($_SESSION['changed']) ? $_SESSION['changed'] : false);
	}

	protected function setChanged($changed)
	{
		$_SESSION['changed'] = $changed;
	}

	protected function getConfFilePath($type, $name='')
	{
		$path = NULL;

		if ( $type == DInfo::CT_SERV) {
			$path = SERVER_ROOT . "conf/httpd_config.conf" ; //fixed location
		}
		elseif ( $type ==  DInfo::CT_ADMIN) {
			$adminRoot = PathTool::GetAbsFile('$SERVER_ROOT/admin/','SR'); //fixed loc

			if ($name == '') {
				$path = $adminRoot . 'conf/admin_config.conf' ;
			} elseif ($name == 'key') {
				$path = $adminRoot . 'conf/jcryption_keypair' ;
			}
		}
		elseif ( $type ==  DInfo::CT_VH ) {
			$vh = $this->_serv->GetChildNodeById('virtualhost', $name);
			if ($vh != NULL) {
				$vhrootpath = $vh->GetChildVal('vhRoot');
				$path = PathTool::GetAbsFile($vh->GetChildVal('configFile'), 'VR', $name, $vhrootpath);
			}
			else {
				die ("cannot find config file for vh $name\n");
				// should set as conf err
			}
		}
		elseif ($type == DInfo::CT_TP) {
			$tp = $this->_serv->GetChildNodeById('vhTemplate', $name);
			if ($tp != NULL)
				$path = PathTool::GetAbsFile($tp->GetChildVal('templateFile'), 'SR');
			else {
				die ("cannot find config file for tp $name\n");
				// should set as conf err
			}
		}

		return $path;
	}

	protected function getConfData()
	{
		$view = $this->_disp->Get(DInfo::FLD_View);
		$pid = $this->_disp->Get(DInfo::FLD_PID);
		$tid = $this->_disp->Get(DInfo::FLD_TID);

		if ( ($view == DInfo::CT_SERV && strpos($tid, 'S_MIME') !== false)
			|| ($view == DInfo::CT_ADMIN && $pid == 'usr')
			|| ($view == DInfo::CT_VH && (strpos($tid, 'V_UDB') !== false || strpos($tid, 'V_GDB') !== false))) {
			$confdata = $this->_special;
		}
		elseif (($view == DInfo::CT_VH && $pid != 'base') || ($view == DInfo::CT_TP && $pid != 'mbr')) {
			$confdata = $this->_curOne;
		}
		elseif ($this->_disp->Get(DInfo::FLD_ConfType) == DInfo::CT_ADMIN) {
			$confdata = $this->_admin;
		}
		else  {
			$confdata = $this->_serv;
		}

		$this->_disp->Set(DInfo::FLD_ConfData, $confdata);
		return $confdata;
	}

	protected function load_server_config($load_admin=false)
	{
		$this->_serv = new CData(DInfo::CT_SERV, $this->getConfFilePath(DInfo::CT_SERV));
		$this->_disp->Set(DInfo::FLD_ServData, $this->_serv);
		if (($conferr = $this->_serv->GetConfErr()) != NULL) {
			$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);
		}

		$has_set_timout = CAuthorizer::HasSetTimeout();
		if (!$has_set_timout || $load_admin) {
			$this->_admin = new CData(DInfo::CT_ADMIN, $this->getConfFilePath(DInfo::CT_ADMIN));
			if (($conferr = $this->_admin->GetConfErr()) != NULL)
				$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);

			if (!$has_set_timout) {
				$timeout = $this->_admin->GetChildVal('sessionTimeout');
				if ($timeout == NULL)
					$timeout = 60; // default
				CAuthorizer::SetTimeout($timeout);
			}
		}
	}

	protected function loadConfig()
	{
		// always load serv
		$this->load_server_config(($this->_disp->Get(DInfo::FLD_ConfType) == DInfo::CT_ADMIN));

		$view = $this->_disp->Get(DInfo::FLD_View);
		$pid = $this->_disp->Get(DInfo::FLD_PID);
		$tid = $this->_disp->Get(DInfo::FLD_TID);

		if (($view == DInfo::CT_VH && $pid != 'base') || ($view == DInfo::CT_TP && $pid != 'mbr')) {
			$confpath = $this->getConfFilePath($view, $this->_disp->Get(DInfo::FLD_ViewName));
			$this->_curOne = new CData($view, $confpath);
			if (($conferr = $this->_curOne->GetConfErr()) != NULL)
				$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);
		}

		// special
		if ($view == DInfo::CT_SERV && strpos($tid, 'S_MIME') !== false) {
			$mime = $this->_serv->GetChildrenValues('mime');
			$file = PathTool::GetAbsFile($mime[0], 'SR');
			$this->_special = new CData(DInfo::CT_EX, $file, 'MIME');
			if (($conferr = $this->_special->GetConfErr()) != NULL)
				$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);

		}
		elseif ($view == DInfo::CT_ADMIN && $pid == 'usr') {
			$file = SERVER_ROOT . 'admin/conf/htpasswd';
			$this->_special = new CData(DInfo::CT_EX, $file, 'ADMUSR');
			if (($conferr = $this->_special->GetConfErr()) != NULL)
				$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);
		}
		elseif ($view == DInfo::CT_VH &&
				(($isudb = strpos($tid, 'V_UDB')) !== false || strpos($tid, 'V_GDB') !== false )) {
			$realm = $this->_curOne->GetChildNodeById('realm', $this->_disp->GetFirst(DInfo::FLD_REF));
			if ($realm != NULL) {
				$isudb = ($isudb !== false);
				$file = $realm->GetChildVal($isudb ? 'userDB:location' : 'groupDB:location');
				$vhroot = $this->_disp->GetVHRoot();
				$file = PathTool::GetAbsFile($file, 'VR', $this->_disp->Get(DInfo::FLD_ViewName), $vhroot);
				$this->_special = new CData(DInfo::CT_EX, $file, $isudb ? 'V_UDB' : 'V_GDB');
				if (($conferr = $this->_special->GetConfErr()) != NULL)
					$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);
			}
		}

	}

	protected function process_config()
	{
		//init here
		$this->_disp->InitConf();
		$this->loadConfig();

		$confdata = $this->getConfData($this->_disp);

		$needTrim = 0;
		$tblDef = DTblDef::GetInstance();
		$disp_act = $this->_disp->Get(DInfo::FLD_ACT);
		if ( $disp_act == 's' )
		{
			$validator = new ConfValidation();
			$extracted = $validator->ExtractPost($this->_disp);
			if ($extracted->HasErr()) {
				$this->_disp->Set(DInfo::FLD_ACT, 'S');
				$this->_disp->Set(DInfo::FLD_TopMsg, $extracted->Get(CNode::FLD_ERR));
				return $extracted;
			}
			else {
				$confdata->SavePost( $extracted, $this->_disp);
				$this->setChanged(true);
				$needTrim = 2;
			}
		}
		elseif ($disp_act == 'a') {
			$added = new CNode(CNode::K_EXTRACTED, '');
			return $added;
		}
		elseif ( $disp_act == 'c' || $disp_act == 'n')
		{ // 'c': change, 'n': next
			$validator = new ConfValidation();
			$extracted = $validator->ExtractPost($this->_disp );
			if ($disp_act == 'n')
				$this->_disp->SwitchToSubTid($extracted);
			return $extracted;
		}
		elseif ($disp_act == 'D' )
		{
			$confdata->DeleteEntry($this->_disp);
			$needTrim = 1;
		}
		elseif ( $disp_act == 'I' )
		{
			if ( $this->instantiateTemplate() ) {
				$needTrim = 1;
			}
		}
		elseif ($disp_act == 'd' || $disp_act == 'i') {
			if ( $disp_act == 'd' ) {
				$actions = 'DC';
				$mesg = DMsg::UIStr('note_confirm_delete');
			}
			else {
				$actions = 'IC';
				$mesg = DMsg::UIStr('note_confirm_instantiate');
			}

			$adata = $this->_disp->GetActionData($actions);
			$mesg = '<p>' . $mesg . '</p>' . UI::GetActionButtons($adata, 'text');

			$this->_disp->Set(DInfo::FLD_TopMsg, $mesg);
		}

		$ctxseq = UIBase::GrabGoodInputWithReset('ANY', 'ctxseq', 'int');
		if ($ctxseq != 0) {
			if ($this->_curOne->ChangeContextSeq($ctxseq))
				$needTrim = 1;
		}

		if ( $needTrim ) {
			$this->_disp->TrimLastId();
			// need reload
			$this->loadConfig();
			$confdata = $this->getConfData($this->_disp);
		}

		return $confdata;
	}


	protected function instantiateTemplate()
	{
		$tpname = $this->_disp->Get(DInfo::FLD_ViewName);

		$vhname = $this->_disp->GetLast(DInfo::FLD_REF);
		$s_tpnode = $this->_serv->GetChildNodeById('vhTemplate', $tpname);
		if ($s_tpnode == NULL)
			return false;
		$s_vhnode = $s_tpnode->GetChildNodeById('member', $vhname);
		if ($s_vhnode == NULL)
			return false;

		$confpath = $this->getConfFilePath(DInfo::CT_TP, $tpname);
		$tp = new CData(DInfo::CT_TP, $confpath);
		if (($conferr = $tp->GetConfErr()) != NULL) {
			$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);
			return false;
		}
		$tproot = $tp->GetRootNode();

		$configfile = $tproot->GetChildVal('configFile');
		if ($configfile == NULL)
			return false;

		$vhRoot_path = '';
		if ( strncasecmp('$VH_ROOT', $configfile, 8) == 0 ) {
			$vhRoot_path = $s_vhnode->GetChildVal('vhRoot'); // customized
			if ($vhRoot_path == NULL) {
				//default
				$vhRoot_path = $tproot->GetChildVal('vhRoot');
				if ($vhRoot_path == NULL)
					return false;
			}
		}
		$configfile = PathTool::GetAbsFile($configfile, 'VR', $vhname, $vhRoot_path);
		$vh = new CData(DInfo::CT_VH, $configfile, "`$vhname");
		if (($conferr = $vh->GetConfErr()) != NULL) {
			$this->_disp->Set(DInfo::FLD_TopMsg, $conferr);
			return false;
		}

		$domains = $s_vhnode->GetChildVal('vhDomain');
		if ($domains == NULL) {
			$domains = $vhname; // default
		}
		$domain = $domains;
		$alias = '';
		if ( ($domainalias = $s_vhnode->GetChildVal('vhAliases')) != NULL ) {
			$domains .= ", $domainalias";
			$alias = $domainalias;
		}
		
		$vhroot = $tproot->GetChildren('virtualHostConfig');
		if ($vhroot == false)
			return false;
		$vhroot->AddChild(new CNode('vhDomain', $domain));
		$vhroot->AddChild(new CNode('vhAliases', $alias));
		
		$vh->SetRootNode($vhroot);
		$vh->SaveFile();

		// save serv file
		$basemap = new DTblMap(array('','*virtualhost$name'), 'V_TOPD');
		$tproot->AddChild(new CNode('name', $vhname));
		$tproot->AddChild(new CNode('note', "Instantiated from template $tpname"));
		$basemap->Convert(0, $tproot, 1, $this->_serv->GetRootNode());
		$s_vhnode->RemoveFromParent();

		$listeners = $s_tpnode->GetChildVal('listeners');
		$lns = preg_split("/, /", $listeners, -1, PREG_SPLIT_NO_EMPTY);

		foreach( $lns as $ln) {
			$listener = $this->_serv->GetChildNodeById('listener', $ln);
			if ($listener != NULL) {
				$vhmap = new CNode('vhmap', $vhname);
				$vhmap->AddChild(new CNode('domain', $domains));
				$listener->AddChild($vhmap);
			}
			else {
				error_log("cannot find listener $ln \n");
			}
		}
		$this->_serv->SaveFile();
		return true;
	}

	protected function enableDisableVh($act, $actId)
	{
		$haschanged = false;
		$cur_disabled = array();
		$key = 'suspendedVhosts';

		if ($this->_serv == NULL) {
			$this->load_server_config();
		}
		$curnode = $this->_serv->GetRootNode()->GetChildren($key);
		if ($curnode != NULL && $curnode->Get(CNode::FLD_VAL) != NULL)
			$cur_disabled = preg_split("/[,;]+/", $curnode->Get(CNode::FLD_VAL), -1, PREG_SPLIT_NO_EMPTY);

		$found = in_array($actId, $cur_disabled);
		if ($act == SInfo::SREQ_VH_DISABLE) {
			if (!$found) {
				$cur_disabled[] = $actId;
				$haschanged = true;
			}
		}
		elseif ($act == SInfo::SREQ_VH_ENABLE) {
			if ($found) {
				$key = array_search($actId, $cur_disabled);
				unset($cur_disabled[$key]);
				$haschanged = true;
			}
		}
		if ($haschanged) {
			$vals = implode(',', $cur_disabled);
			if ($curnode == NULL)
				$this->_serv->GetRootNode()->AddChild(new CNode($key, $vals));
			else
				$curnode->SetVal($vals);
			$this->_serv->SaveFile();
		}
	}

	protected function process_service_request($type, $actId)
	{
		// has pending command processs
		if (file_exists(SInfo::FNAME)) {
			return false;
		}

		$cmd = '';
		$this->_service = new SInfo();

		switch ($type) {
			case SInfo::SREQ_RESTART_SERVER:
				$cmd = 'restart';
				$this->setChanged(false);
				break;

			case SInfo::SREQ_TOGGLE_DEBUG:
				$cmd = 'toggledbg';
				break;

			case SInfo::SREQ_VH_RELOAD:
				$cmd = 'restart:vhost:' . $actId;
				break;

			case SInfo::SREQ_VH_DISABLE:
				$cmd = 'disable:vhost:' . $actId;
				$this->enableDisableVh($type, $actId);
				break;

			case SInfo::SREQ_VH_ENABLE:
				$cmd = 'enable:vhost:' . $actId;
				$this->enableDisableVh($type, $actId);
				break;

			default:
				error_log("illegal type in process_service_request $type ");
				return false;
		}

		$this->issueCmd($cmd);
		$this->_service->WaitForChange();
	}


	protected function process_service_data($type)
	{
		// process static type
		switch ($type) {
			case SInfo::DATA_PID:
				return file_get_contents(SInfo::FPID);

			case SInfo::DATA_ADMIN_KEYFILE:
				return $this->getConfFilePath('admin', 'key');

			case SInfo::DATA_DEBUGLOG_STATE:
				return SInfo::GetDebugLogState();
		}

		// require config data
		$this->_service = new SInfo();
		$this->load_server_config();
		$this->_service->Init($this->_serv);

		switch($type) {
			case SInfo::DATA_ADMIN_EMAIL:
				return $this->_serv->GetChildVal('adminEmails');

			case SInfo::DATA_DASH_LOG:
			case SInfo::DATA_VIEW_LOG:
				return $this->_service->LoadLog($type);

			case SInfo::DATA_Status_LV:
				$this->_service->LoadStatus();
				return $this->_service;

			default: "Illegal type in process_service_data : $type ";
		}

		return false;
	}

	public static function getCommandSocket($cmd)
	{
		$ADMSOCK =  $_SERVER['LSWS_ADMIN_SOCK'];
		if ( strncmp( $ADMSOCK, 'uds://', 6 ) == 0 ) {
			$sock = socket_create( AF_UNIX, SOCK_STREAM, 0 );
			$chrootOffset = isset($_SERVER['LS_CHROOT']) ? strlen( $_SERVER['LS_CHROOT']) : 0;
			$addr = substr( $ADMSOCK, 5 + $chrootOffset );
			if ( !socket_connect( $sock, $addr ) ) {
				error_log( 'cmd ' . $cmd . ' failed to connect to server! socket_connect() failed: ' . socket_strerror(socket_last_error()) . " $ADMSOCK\n" );
				return false;
			}
		}
		else {
			$sock = socket_create( AF_INET, SOCK_STREAM, SOL_TCP );
			$addr = explode( ":", $ADMSOCK );
			if ( !socket_connect( $sock, $addr[0], intval( $addr[1] ) ) ) {
				error_log( 'cmd ' . $cmd . ' failed to connect to server! socket_connect() failed: ' . socket_strerror(socket_last_error()) . " $ADMSOCK\n" );
				return false;
			}
		}
		$cauth = CAuthorizer::singleton();
		$outBuf = $cauth->GetCmdHeader() . $cmd . "\nend of actions";
		socket_write( $sock, $outBuf );
		socket_shutdown( $sock, 1 );
		return $sock;
	}

	protected function issueCmd($cmd)
	{
		$commandline = '';
		if (is_array($cmd)) {
			foreach( $cmd as $line ) {
				$commandline .= $line . "\n";
			}
		}
		else {
			$commandline = $cmd . "\n";
		}

		$sock = $this->getCommandSocket($commandline);
		if ($sock) {
			$res = socket_recv( $sock, $buffer, 1024, 0 );
			socket_close( $sock );
			return (( $res > 0 )&&(strncasecmp( $buffer, 'OK', 2 ) == 0 ));
		}
		else
			return false;
	}

	public function retrieveCommandData($cmd)
	{
		$sock = $this->getCommandSocket($cmd);
		$buffer = '';
		if ($sock) {
			$read   = array($sock);
			$write  = NULL;
			$except = NULL;
			$num_changed_sockets = socket_select($read, $write, $except, 3); //wait for max 3 seconds
			if ($num_changed_sockets === false) {
				error_log("socket_select failed: " . socket_strerror(socket_last_error()));
			}
			else if ($num_changed_sockets > 0) {
				while (socket_recv($sock, $data, 8192, 0)) {
					$buffer .= $data;
				}
			}
			socket_close( $sock );
		}
		return $buffer;

	}

}

