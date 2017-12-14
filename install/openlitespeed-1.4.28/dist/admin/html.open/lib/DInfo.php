<?php

class DInfo
{
	const FLD_ConfType = 1;
	const FLD_ConfErr = 2;
	const FLD_View = 3;
	const FLD_ViewName = 4;
	const FLD_TopMsg = 5;
	const FLD_ICONTITLE = 6;

	const FLD_CtrlUrl = 10;
	const FLD_MID = 11;
	const FLD_PID = 12;
	const FLD_TID = 13;
	const FLD_REF = 14;
	const FLD_ACT = 15;
	const FLD_SORT = 16;
	const FLD_TOKEN = 17;
	const FLD_PgData = 18;
	const FLD_ConfData = 19;
	const FLD_ServData = 20;

	// conftype
	const CT_SERV = 'serv';
	const CT_VH = 'vh_';
	const CT_TP = 'tp_';
	const CT_ADMIN = 'admin';
	const CT_EX = 'special';

	private $_confType;
	private $_view; //_type (serv, sl, sl_, vh, vh_, tp, tp_, lb, lb_, admin, al, al_)
	private $_viewName = NULL; // _name


	private $_ctrlUrl = 'index.php#view/confMgr.php?';

	private $_mid = 'serv'; // default
	private $_pid = NULL;
	private $_tid = NULL;
	private $_ref = NULL;
	private $_act;
	private $_token;

	private $_confErr;
	private $_pageData;
	private $_confData;
	private $_servData; // for populate vh level derived options

	private $_tabs;
	private $_sort;

	private $_topMsg;
	private $_isPrintingLinkedTbl;
	private $_allActions;

	public function ShowDebugInfo()
	{
		return "DINFO: conftype={$this->_confType} view={$this->_view} viewname={$this->_viewName} mid={$this->_mid} pid={$this->_pid} tid={$this->_tid} ref={$this->_ref} act={$this->_act}\n";
	}

	public function InitConf()
	{
		$has_pid = FALSE;
		$mid = UIBase::GrabGoodInput("request",'m');

		if ($mid != NULL) {
			$this->_mid = $mid;
			$pid = UIBase::GrabGoodInput("request",'p');
			if ($pid != NULL) {
				$this->_pid = $pid;
				$has_pid = TRUE;
			}
		}

		if ( ($pos = strpos($this->_mid, '_')) > 0 ) {
			$this->_view = substr($this->_mid, 0, $pos+1);
			$this->_viewName = substr($this->_mid, $pos+1);
			if ($this->_pid == ''
					|| $this->_view == 'sl' || $this->_view == 'sl_'
					|| $this->_view == 'al' || $this->_view == 'al_'
					|| $this->_pid == 'base' || $this->_pid == 'mbr')
				$this->_ref = $this->_viewName; // still in serv conf
		}
		else {
			$this->_view = $this->_mid ;
		}

		$this->_confType = ( $this->_mid[0] == 'a' ) ? self::CT_ADMIN: self::CT_SERV;

		$this->_tabs = DPageDef::GetInstance()->GetTabDef($this->_view);

		if ($has_pid) {
			if (!array_key_exists($this->_pid, $this->_tabs))
				die("Invalid pid - {$this->_pid} \n");
		}
		else {
			$this->_pid = key($this->_tabs); // default
		}

		if ( $has_pid && !isset($_REQUEST['t0']) && isset($_REQUEST['t']) )
		{
			$t = UIBase::GrabGoodInput('request', 't');
			if ($t != NULL) {
				$this->_tid = $t;
				$t1 = UIBase::GrabGoodInputWithReset('request', 't1');
				if ($t1 != NULL	 && ( $this->GetLast(self::FLD_TID) != $t1) )
					$this->_tid .= '`' . $t1;

				if ( ($r = UIBase::GrabGoodInputWithReset('request', 'r')) != NULL )
					$this->_ref = $r;
				if ( ($r1 = UIBase::GrabGoodInputWithReset('request', 'r1')) != NULL )
					$this->_ref .= '`' . $r1;
				}
		}

		$this->_act = UIBase::GrabGoodInput("request",'a');
		if ( $this->_act == NULL ) {
			$this->_act = 'v';
		}

		$tokenInput = UIBase::GrabGoodInput("request",'tk');
		$this->_token =  $_SESSION['token'];
		if ($this->_act != 'v' && $this->_token != $tokenInput) {
			die('Illegal entry point!');
		}

		if ($this->_act == 'B') {
			$this->TrimLastId();
			$this->_act = 'v';
		}

		$this->_sort = UIBase::GrabGoodInput("request",'sort');

		$this->_allActions = array(
				'a' => array(DMsg::UIStr('btn_add'), 'fa-indent'),
				'v'=>array(DMsg::UIStr('btn_view'), 'fa-search-plus'),
				'E'=>array(DMsg::UIStr('btn_edit'), 'fa-edit'),
				's'=>array(DMsg::UIStr('btn_save'), 'fa-save'),
				'B'=>array(DMsg::UIStr('btn_back'), 'fa-reply'), //'fa-level-up'
				'n'=>array(DMsg::UIStr('btn_next'), 'fa-step-forward'),
				'd'=>array(DMsg::UIStr('btn_delete'), 'fa-trash-o'),
				'D'=>array(DMsg::UIStr('btn_delete'), 'fa-trash-o'),
				'C'=>array(DMsg::UIStr('btn_cancel'), 'fa-angle-double-left'),
				'i'=>array(DMsg::UIStr('btn_instantiate'), 'fa-cube'),
				'I'=>array(DMsg::UIStr('btn_instantiate'), 'fa-cube'),
				'X' => array(DMsg::UIStr('btn_view'), 'fa-search-plus'));
	}

	public function Get($field)
	{
		switch ($field) {
			case self::FLD_CtrlUrl:
				return "{$this->_ctrlUrl}m={$this->_mid}&p={$this->_pid}";
			case self::FLD_View: return $this->_view;
			case self::FLD_ViewName: return $this->_viewName;
			case self::FLD_TopMsg: return $this->_topMsg;
			case self::FLD_ConfType: return $this->_confType;
			case self::FLD_ConfErr: return $this->_confErr;
			case self::FLD_MID: return $this->_mid;
			case self::FLD_PID: return $this->_pid;
			case self::FLD_TID: return $this->_tid;
			case self::FLD_REF: return $this->_ref;
			case self::FLD_ACT: return $this->_act;
			case self::FLD_PgData: return $this->_pageData;
			case self::FLD_ConfData: return $this->_confData;
			case self::FLD_TOKEN: return $this->_token;
			case self::FLD_SORT: return $this->_sort;
			case self::FLD_ICONTITLE:
				switch ($this->_view ) {
					case 'serv':
						return array('fa-globe', DMsg::UIStr('menu_serv'));
					case 'sl':
						return array('fa-chain', DMsg::UIStr('menu_sl'));
					case 'sl_':
						return array('fa-chain', DMsg::UIStr('menu_sl_') . ' ' . $this->_viewName);
					case 'vh':
						return array('fa-cubes', DMsg::UIStr('menu_vh'));
					case 'vh_':
						return array('fa-cube', DMsg::UIStr('menu_vh_') . ' ' . $this->_viewName);
					case 'tp':
						return array('fa-files-o', DMsg::UIStr('menu_tp'));
					case 'tp_':
						return array('fa-files-o', DMsg::UIStr('menu_tp_') . ' ' . $this->_viewName);
					case 'admin':
						return array('fa-gear', DMsg::UIStr('menu_webadmin'));
					case 'al':
						return array('fa-chain', DMsg::UIStr('menu_webadmin') . ' - ' . DMsg::UIStr('menu_sl'));
					case 'al_':
						return array('fa-chain', DMsg::UIStr('menu_webadmin') . ' - ' . DMsg::UIStr('menu_sl_') . ' ' . $this->_viewName);

				}
				break;
			default: error_log("invalid DInfo field : $field\n");
		}
	}

	public function Set($field, $value)
	{
		switch ($field) {
			case self::FLD_ConfErr:
				$this->_confErr = $value;
				break;
			case self::FLD_ACT:
				$this->_act = $value;
				break;
			case self::FLD_PgData:
				$this->_pageData = $value;
				break;
			case self::FLD_ConfData:
				$this->_confData = $value;
				break;
			case self::FLD_ServData:
				$this->_servData = $value;
				break;
			case self::FLD_REF:
				$this->_ref = $value;
				break;
			case self::FLD_ViewName:
				$this->_viewName = $value;
				if ($value == NULL) // by delete
					$value = '';
				else
					$value = '_' . $value;

				if ( ($pos = strpos($this->_mid, '_')) > 0 ) {
					$this->_mid = substr($this->_mid, 0, $pos) . $value;
				}
				break;
			case self::FLD_TopMsg:
				$this->_topMsg[] = $value;
				break;
			default: die("not supported - $field");
		}
	}

	public function SetPrintingLinked($printinglinked)
	{
		$this->_isPrintingLinkedTbl = $printinglinked;
	}

	public function InitUIProps($props)
	{
		$props->Set(UIProperty::FLD_FORM_HIDDENVARS,
				array(
						'a' => 'v',
						'm' => $this->_mid,
						'p' => $this->_pid,
						't' => $this->_tid,
						'r' => $this->_ref,
						'tk' => $this->_token));

		if ($this->_servData != NULL) {
			$props->Set(UIProperty::FLD_SERVER_NAME, $this->_servData->GetId());
		}

		$uri = $this->_ctrlUrl . 'm=' . $this->_mid;

		$tabs = array();
		$uri .= '&p=';

		foreach ( $this->_tabs as $pid => $tabName )
		{
			if ($pid == $this->_pid) {
				//$bread[$tabName] = $uri . $pid;
				$name = '1' . $tabName;
			}
			else {
				$name = '0' . $tabName;
			}
			//$tabs[$name] = $uri . $pid;
			$tabs[$name] = "javascript:lst_conf('v', '$pid','-','-')";
		}
		$props->Set(UIProperty::FLD_TABS, $tabs);

	}

	public function IsViewAction()
	{
		//$viewTags = 'vsDdBCiI';
		$editTags = 'EaScn';
		return ( strpos($editTags, $this->_act) === FALSE );
	}

	public function GetActionData($actions, $editTid='', $editRef='', $addTid='')
	{
		$actdata = array();

		$chars = preg_split('//', $actions, -1, PREG_SPLIT_NO_EMPTY);

		$ctrlUrl = $this->Get(DInfo::FLD_CtrlUrl);

		$cur_tid = $this->GetLast(self::FLD_TID);
		foreach ( $chars as $act )
		{
			$name = $this->_allActions[$act][0];
			$ico = $this->_allActions[$act][1];
			if ( $act == 'C' ) {
				$act = 'B';
			}

			if ($act == 'B' && $this->_isPrintingLinkedTbl)
				continue; // do not print Back for linked view

			if ( $act == 's' || $act == 'n' ) {
				$href = "javascript:lst_conf('$act','','','')";
			}
			elseif( $act == 'X') {
				//vhtop=>vh_... tptop=>tp_.... sltop=>sl_...
				$href = $this->_ctrlUrl . 'm=' . $this->_view . '_' . $editRef;
				$act = 'v';
			}
			else {

				if ($act == 'a') {
					$edittid = $addTid;
					$editref = '~';
				}
				else {
					$edittid = $editTid;
					$editref = $editRef;
				}

				if ($edittid == '' || $edittid == $cur_tid) {
					$t = $this->_tid;
				}
				elseif ($cur_tid != NULL && $cur_tid != $edittid) {
					$t = $this->_tid . '`' . $edittid;
				}
				else {
					$t = $edittid;
				}

				if ($editref == '') {
					$r = $this->_ref;
				}
				elseif ($this->_ref != NULL && $this->_ref != $editref) {
					$r = $this->_ref . '`' . $editref;
				}
				else {
					$r = $editref;
				}

				//$t = '&t=' . $t;
				//$r = '&r=' . urlencode($r);

				//$href = $ctrlUrl . $t . $r . '&a=' . $act . '&tk=' . $this->_token;
				$href = "javascript:lst_conf('$act', '', '$t', '$r')";
			}
			$actdata[$act] = array('label' => $name, 'href' => $href, 'ico' => $ico);
		}
		return $actdata;
	}

	public function TrimLastId()
	{
		if (($pos = strrpos($this->_tid, '`')) !== FALSE)
			$this->_tid = substr($this->_tid, 0, $pos);
		else
			$this->_tid = NULL;

		if (($pos = strrpos($this->_ref, '`')) !== FALSE)
			$this->_ref = substr($this->_ref, 0, $pos);
		elseif ($this->_view == 'sl_' || $this->_view == 'al_'
				|| $this->_pid == 'base' || $this->_pid == 'mbr')
			$this->_ref = $this->_viewName; // still in serv conf
		else
			$this->_ref = NULL;
	}

	public function GetLast($field)
	{
		$id = NULL;
		if ($field == self::FLD_TID)
			$id = $this->_tid;
		elseif ($field == self::FLD_REF)
			$id = $this->_ref;

		if ( $id != NULL && ($pos = strrpos($id, '`')) !== FALSE )
			if (strlen($id) > $pos + 1)
				$id = substr($id, $pos+1);
			else
				$id = '';

		return $id;
	}

	public function GetFirst($field)
	{
		$id = NULL;
		if ($field == self::FLD_TID)
			$id = $this->_tid;
		elseif ($field == self::FLD_REF)
			$id = $this->_ref;

		if ( $id != NULL && ($pos = strpos($id, '`')) !== FALSE ) {
			$id = substr($id, 0, $pos);
		}

		return $id;
	}

	public function GetParentRef()
	{
		if (($pos = strrpos($this->_ref, '`')) !== FALSE)
			return substr($this->_ref, 0, $pos);
		else
			return '';
	}

	public function SwitchToSubTid($extracted)
	{
		if (($pos = strrpos($this->_tid, '`')) !== FALSE) {
			$tid0 = substr($this->_tid, 0, $pos+1);
			$tid = substr($this->_tid, $pos+1);
		}
		else {
			$tid0 = '';
			$tid = $this->_tid;
		}
		$tbl = DTblDef::getInstance()->GetTblDef($tid);

		$subtbls = $tbl->Get(DTbl::FLD_SUBTBLS);
		$newkey = $extracted->GetChildVal($subtbls[0]);
		$subtid = '';
		if ($newkey != NULL) {
			if ($newkey == '0' || !isset($subtbls[$newkey]))
				$subtid = $subtbls[1];
			else
				$subtid = $subtbls[$newkey];
		}

		$this->_tid = $tid0 . $subtid;
	}

	public function GetDerivedSelOptions($tid, $loc, $node)
	{
		$o = array();

		if (substr($loc, 0, 13) == 'extprocessor:') {
			$type = substr($loc, 13);
			if ($type == '$$type') {
				if ($node != NULL)
					$type = $node->GetChildVal('type');
				else
					$type = 'fcgi';
			}
			if ($type == 'cgi') {
				$o['cgi'] = 'CGI Daemon';
				return $o;
			}
			if ($type == 'module') {
				$modules = $this->_servData->GetChildrenValues('module');
				if ($modules != NULL) {
					foreach ($modules as $mn)
						$o[$mn] = $mn;
				}
				return $o;
			}

			$exps = array();
			if (($servexps = $this->_servData->GetRootNode()->GetChildren('extprocessor')) != NULL) {
				if (is_array($servexps)) {
					foreach($servexps as $exname => $ex) {
						if ($ex->GetChildVal('type') == $type)
							$exps[] = $exname;
					}
				}
				elseif ($servexps->GetChildVal('type') == $type)
					$exps[] = $servexps->Get(CNode::FLD_VAL);
			}

			if ($this->_view == DInfo::CT_SERV) {
				foreach($exps as $exname) {
					$o[$exname] = $exname;
				}
				return $o;
			}
			foreach ($exps as $exname) {
				$o[$exname] = '[' . DMsg::UIStr('note_serv_level') . "]: $exname";
			}

			$loc = ($this->_view == DInfo::CT_TP) ? 'virtualHostConfig:extprocessor' : 'extprocessor';
			if (($vhexps = $this->_confData->GetRootNode()->GetChildren($loc)) != NULL) {
				if (is_array($vhexps)) {
					foreach($vhexps as $exname => $ex) {
						if ($ex->GetChildVal('type') == $type)
							$o[$exname] = "[VHost Level]: $exname";
					}
				}
				else if ($vhexps->GetChildVal('type') == $type) {
					$exname = $vhexps->Get(CNode::FLD_VAL);
					$o[$exname] = '[' . DMsg::UIStr('note_vh_level') . "]: $exname";
				}
			}
			return $o;
		}

		if (in_array($loc, array('virtualhost','listener','module'))) {
			$names = $this->_servData->GetChildrenValues($loc);
		}
		elseif ($loc == 'realm') {
			if ($this->_view == DInfo::CT_TP)
				$loc = "virtualHostConfig:$loc";
			$names = $this->_confData->GetChildrenValues($loc);
		}

		sort($names);
		foreach ($names as $name)
			$o[$name] = $name;

		return $o;
	}


	public function GetVHRoot()
	{
		// type = 'SR', 'VR'
		if ($this->_view == self::CT_VH) {
			$vn = $this->_viewName;
			if (($vh = $this->_servData->GetChildNodeById('virtualhost', $vn)) != NULL) {
				$vhroot = PathTool::GetAbsFile($vh->GetChildVal('vhRoot'),'SR', $vn);
				return $vhroot;
			}
		}
		return NULL;
	}
}

