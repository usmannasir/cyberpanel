<?php

class CValidation
{
	protected $_disp;
	protected $_go_flag;

	public function __construct() {}

	public function ExtractPost($disp)
	{
		$this->_disp = $disp;
		$this->_go_flag = 1;

		$tid = $disp->GetLast(DInfo::FLD_TID);
		$tbl = DTblDef::GetInstance()->GetTblDef($tid);

		$extracted = new CNode(CNode::K_EXTRACTED, '', CNode::T_KB);
		$attrs = $tbl->Get(DTbl::FLD_DATTRS);

		foreach ($attrs as $attr) {

			if ($attr->bypassSavePost()) {
				continue;
			}

			$needCheck = $attr->extractPost($extracted);

			if ( $needCheck ) {
				if ($attr->_type == 'sel1' || $attr->_type == 'sel2') {
                    if ($this->_disp->Get(DInfo::FLD_ACT) == 'c') {
                        $needCheck = false; // for changed top category
                    }
                    else {
                        $attr->SetDerivedSelOptions($disp->GetDerivedSelOptions($tid, $attr->_minVal, $extracted));
                    }
				}
				$dlayer = $extracted->GetChildren($attr->GetKey());
                if ($needCheck) {
                    $this->validateAttr($attr, $dlayer);
                }
				if (($tid == 'V_TOPD' || $tid == 'V_BASE') && $attr->_type == 'vhname') {
					$vhname = $dlayer->Get(CNode::FLD_VAL);
					$disp->Set(DInfo::FLD_ViewName, $vhname);
				}
			}
		}

		$res = $this->validatePostTbl($tbl, $extracted);
		$this->setValid($res);

		// if 0 , make it always point to curr page

		if ($this->_go_flag <= 0) {
			$extracted->SetErr('Input error detected. Please resolve the error(s). ');
		}

		$this->_disp = NULL;
		return $extracted;
	}


	protected function setValid($res)
	{
		if ( $this->_go_flag != -1 )	{
			if ( $res == -1 ) {
				$this->_go_flag = -1;
			} elseif ( $res == 0 && $this->_go_flag == 1 ) {
				$this->_go_flag = 0;
			}
		}
		if ( $res == 2 ) {
			$this->_go_flag = 2;
		}
	}

	protected function validatePostTbl($tbl, $extracted)
	{
		$isValid = 1;
		$tid = $tbl->Get(DTbl::FLD_ID);

		if ( ($index = $tbl->Get(DTbl::FLD_INDEX)) != NULL) {
			$keynode = $extracted->GetChildren($index);
			if ($keynode != NULL) {
				$holderval = $keynode->Get(CNode::FLD_VAL);
				$extracted->SetVal($holderval);

				if ($holderval != $this->_disp->GetLast(DInfo::FLD_REF)) {
					// check conflict
					$ref = $this->_disp->GetParentRef();
					$location = DPageDef::GetPage($this->_disp)->GetTblMap()->FindTblLoc($tid);
					if ($location[0] == '*') { // allow multiple
						$confdata = $this->_disp->Get(DInfo::FLD_ConfData);
						$existingkeys = $confdata->GetChildrenValues($location, $ref);

						if (in_array($holderval, $existingkeys)) {
							$keynode->SetErr('This value has been used! Please choose a unique one.');
							$isValid = -1;
						}
					}
				}
			}
		}

		if (($defaultExtract = $tbl->Get(DTbl::FLD_DEFAULTEXTRACT)) != NULL) {
			foreach( $defaultExtract as $k => $v ) {
				$extracted->AddChild(new CNode($k,$v));
			}
		}

		$view = $this->_disp->Get(DInfo::FLD_View);
		if ($tid == 'L_GENERAL' || $tid == 'ADM_L_GENERAL') {
			$this->chkPostTbl_L_GENERAL($extracted);
		}
		elseif ($view == 'sl' || $view == 'al' ) { // will ignore vhlevel
			if ($tid == 'LVT_SSL_CERT')
				$isValid = $this->chkPostTbl_L_SSL_CERT($extracted);
		}
		elseif ($view == 'admin') {
			if ($tid == 'ADM_USR')
				$isValid = $this->chkPostTbl_ADM_USR($extracted);
			elseif ($tid == 'ADM_USR_NEW')
				$isValid = $this->chkPostTbl_ADM_USR_NEW($extracted);
		}
		elseif ($tid == 'V_UDB') {
			$isValid = $this->chkPostTbl_ADM_USR_NEW($extracted);
		}


		return $isValid;
	}

	protected function encryptPass($val)
	{
		$valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.";
		$limit = strlen($valid_chars)-1;
		$isMac = (strtoupper(PHP_OS) === 'DARWIN');

		if (CRYPT_MD5 == 1 && !$isMac) {
			$salt = '$1$';
			for($i = 0; $i < 8; $i++) {
				$salt .= $valid_chars[rand(0,$limit)];
			}
			$salt .= '$';
		}
		else {
			$salt = $valid_chars[rand(0,$limit)];
			$salt .= $valid_chars[rand(0,$limit)];
		}
		$pass = crypt($val, $salt);
		return $pass;
	}

	protected function chkPostTbl_ADM_USR($d)
	{
		$isValid = 1;
		$oldpass = $d->GetChildVal('oldpass');
		if ( $oldpass == NULL) {
			$d->SetChildErr('oldpass', 'Missing Old password!');
			$isValid = -1;
		} else {
			$file = SERVER_ROOT . 'admin/conf/htpasswd';
			$udb = $this->_disp->Get(DInfo::FLD_ConfData);

			$oldusername = $this->_disp->GetLast(DInfo::FLD_REF);
			$passwd = $udb->GetChildVal('*index$name:passwd', $oldusername);

			$encypt = crypt($oldpass, $passwd);

			if ( $encypt != $passwd ) {
				$d->SetChildErr('oldpass', 'Invalid old password!');
				$isValid = -1;
			}
		}

		$pass = $d->GetChildVal('pass');
		if ( $pass == NULL )	{
			$d->SetChildErr('pass', 'Missing new password!');
			$isValid = -1;
		} elseif ( $pass != $d->GetChildVal('pass1') ) {
			$d->SetChildErr('pass', 'New passwords do not match!');
			$isValid = -1;
		}

		if ( $isValid == -1 )
			return -1;

		$newpass = $this->encryptPass($pass);
		$d->AddChild(new CNode('passwd', $newpass));
		return 1;
	}

	protected function chkPostTbl_ADM_USR_NEW($d)
	{
		$isValid = 1;
		$pass = $d->GetChildVal('pass');
		if ( $pass == NULL )	{
			$d->SetChildErr('pass', 'Missing new password!');
			$isValid = -1;
		} elseif ( $pass != $d->GetChildVal('pass1') ) {
			$d->SetChildErr('pass', 'New passwords do not match!');
			$isValid = -1;
		}

		if ( $isValid == -1 )
			return -1;

		$newpass = $this->encryptPass($pass);
		$d->AddChild(new CNode('passwd', $newpass));

		return 1;
	}

	protected function chkPostTbl_L_GENERAL($d)
	{
		$ip = $d->GetChildVal('ip');
		if ( $ip == 'ANY' ) {
			$ip = '*';
		}
		$port = $d->GetChildVal('port');
		$d->AddChild(new CNode('address', "$ip:$port") );
	}

	protected function isCurrentListenerSecure()
	{
		$confdata = $this->_disp->Get(DInfo::FLD_ConfData);
		$listener = $confdata->GetChildNodeById('listener', $this->_disp->Get(DInfo::FLD_ViewName));
		$secure = $listener->GetChildVal('secure');
		return ($secure == 1);
	}

	protected function chkPostTbl_L_SSL_CERT($d)
	{
		$isValid = 1;
		if ($this->isCurrentListenerSecure($disp)) {
			$err = 'Value must be set for secured listener. ';
			if ($d->GetChildVal('keyFile') == NULL) {
				$d->SetChildErr('keyFile', $err);
				$isValid = -1;
			}
			if ($d->GetChildVal('certFile') == NULL) {
				$d->SetChildErr('certFile', $err);
				$isValid = -1;
			}
		}

		return $isValid;
	}

	protected function validateAttr($attr, $dlayer)
	{
		if ( is_array($dlayer) ) {
			foreach($dlayer as $node) {
				$res = $this->isValidAttr($attr, $node);
				$this->setValid($res);
			}
		} else {
			$res = $this->isValidAttr($attr, $dlayer);
			$this->setValid($res);
		}
	}

	protected function isValidAttr($attr, $node)
	{
		if ($node == NULL || $node->HasErr())
			return -1;

		if ( !$node->HasVal()) {
			if ( !$attr->IsFlagOn(DAttr::BM_NOTNULL) )
				return 1;

			$node->SetErr('value must be set. ');
			return -1;
		}

		$notchk = array('cust', 'domain', 'subnet');
		if ( in_array($attr->_type, $notchk) ) {
			return 1;
		}

		$chktype = array('uint', 'name', 'vhname', 'sel','sel1','sel2',
		'bool','file','filep','file0','file1', 'filetp', 'filevh', 'path',
		'uri','expuri','url', 'httpurl', 'email', 'dir', 'addr', 'wsaddr', 'parse');

		if ( !in_array($attr->_type, $chktype) )	{
			return 1;
		}

		$type3 = substr($attr->_type, 0, 3);
		if ( $type3 == 'sel' ) {
			// for sel, sel1, sel2
			$funcname = 'chkAttr_sel';
		}
		elseif ( $type3 == 'fil' || $type3 == 'pat' ) {
			$funcname = 'chkAttr_file';
		}
		else {
			$funcname = 'chkAttr_' . $attr->_type;
		}

		if ( $attr->_multiInd == 1 ) {
			$vals = preg_split("/, /", $node->Get(CNode::FLD_VAL), -1, PREG_SPLIT_NO_EMPTY);
			$err = array();
			$funcname .= '_val';
			foreach( $vals as $i=>$v ) {
				$res = $this->$funcname($attr, $v, $err[$i]);
				$this->setValid($res);
			}
			$error = trim(implode(' ', $err));
			if ($error != '')
				$node->SetErr($error);
			return 1;
		}else {
			return $this->$funcname($attr, $node);
		}
	}

	protected function chkAttr_sel($attr, $node)
	{
		$err = '';
		$res = $this->chkAttr_sel_val($attr, $node->Get(CNode::FLD_VAL), $err);
		if ($err != '')
			$node->SetErr($err);
		return $res;
	}

	protected function chkAttr_sel_val($attr, $val, &$err)
	{
		if ( isset( $attr->_maxVal )
			&& !array_key_exists($val, $attr->_maxVal) ) {
				$err = "invalid value: $val";
			return -1;
		}
		return 1;
	}

	protected function chkAttr_name($attr, $node)
	{
		$node->SetVal( preg_replace("/\s+/", ' ', $node->Get(CNode::FLD_VAL)));
		$res = $this->chkAttr_name_val($attr, $node->Get(CNode::FLD_VAL), $err);
		if ($err != '')
			$node->SetErr($err);
		return $res;
	}

	protected function chkAttr_name_val($attr, $val, &$err)
	{
		if ( preg_match( "/[<>&%]/", $val) ) {
			$err = 'invalid characters in name';
			return -1;
		}
		if ( strlen($val) > 100 ) {
			$err = 'name can not be longer than 100 characters';
			return -1;
		}
		return 1;
	}

	protected function chkAttr_vhname($attr, $node)
	{
		$node->SetVal(preg_replace("/\s+/", ' ', $node->Get(CNode::FLD_VAL)));
		$val = $node->Get(CNode::FLD_VAL);
		if ( preg_match( "/[,;<>&%]/", $val ) ) {
			$node->SetErr('Invalid characters found in name');
			return -1;
		}
		if ( strpos($val, ' ') !== FALSE ) {
			$node->SetErr('No space allowed in the name');
			return -1;
		}
		if ( strlen($val) > 100 ) {
			$node->SetErr('name can not be longer than 100 characters');
			return -1;
		}
		return 1;
	}

	protected function allow_create($attr, $absname)
	{
		if ( strpos($attr->_maxVal, 'c') === FALSE )
			return FALSE;

		if ( $attr->_minVal >= 2 && ( strpos($absname, SERVER_ROOT)  === 0 )) {
			return TRUE;
		}
		//other places need to manually create
		return FALSE;
	}

	protected function test_file(&$absname, &$err, $attr)
	{
        if ($attr->_maxVal == NULL)
            return 1; // no permission test

		$absname = PathTool::clean($absname);
		if ( isset( $_SERVER['LS_CHROOT'] ) )	{
			$root = $_SERVER['LS_CHROOT'];
			$len = strlen($root);
			if ( strncmp( $absname, $root, $len ) == 0 ) {
				$absname = substr($absname, $len);
			}
		}

		if ( $attr->_type == 'file0' ) {
			if ( !file_exists($absname) ) {
				return 1; //allow non-exist
			}
		}
		if ( $attr->_type == 'path' || $attr->_type == 'filep' || $attr->_type == 'dir' ) {
			$type = 'path';
		} else {
			$type = 'file';
		}

		if ( ($type == 'path' && !is_dir($absname))
		|| ($type == 'file' && !is_file($absname)) ) {
			$err = $type .' '. htmlspecialchars($absname) . ' does not exist.';
			if ( $this->allow_create($attr, $absname) ) {
				$err .= ' <a href="javascript:lst_createFile(\''. $attr->GetKey() . '\')">CLICK TO CREATE</a>';
			} else {
				$err .= ' Please create manually.';
			}

			return -1;
		}
		if ( (strpos($attr->_maxVal, 'r') !== FALSE) && !is_readable($absname) ) {
			$err = $type . ' '. htmlspecialchars($absname) . ' is not readable';
			return -1;
		}
		if ( (strpos($attr->_maxVal, 'w') !== FALSE) && !is_writable($absname) ) {
			$err = $type . ' '. htmlspecialchars($absname) . ' is not writable';
			return -1;
		}

		return 1;
	}

	protected function chkAttr_file($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		$err = '';
		$res = $this->chkAttr_file_val($attr, $val, $err);
		$node->SetVal($val);
		if ($err != '')
			$node->SetErr($err);
		return $res;
	}

	protected function chkAttr_dir($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		$err = '';

		if ( substr($val,-1) == '*' ) {
			$res = $this->chkAttr_file_val($attr, substr($val,0,-1), $err);
		} else {
			$res = $this->chkAttr_file_val($attr, $val, $err);
		}
		$node->SetVal($val);
		if ($err != '')
			$node->SetErr($err);
		return $res;
	}

	public function chkAttr_file_val($attr, $val, &$err)
	{
		//this is public
		clearstatcache();
		$err = NULL;

		if ( $attr->_type == 'filep' ) {
			$path = substr($val, 0, strrpos($val,'/'));
		} else {
			$path = $val;
			if ( $attr->_type == 'file1' ) {
				$pos = strpos($val, ' ');
				if ( $pos > 0 ) {
					$path = substr($val, 0, $pos);
				}
			}
		}

		$res = $this->chk_file1($attr, $path, $err);

		if ($attr->_type == 'filetp') {
			$pathtp = SERVER_ROOT . 'conf/templates/';
			if (strstr($path, $pathtp) === FALSE) {
				$err = ' Template file must locate within $SERVER_ROOT/conf/templates/';
				$res = -1;
			}
			else if (substr($path, -5) != '.conf') {
				$err = ' Template file name needs to be ".conf"';
				$res = -1;
			}
		}
		elseif ($attr->_type == 'filevh') {
			$pathvh = SERVER_ROOT . 'conf/vhosts/';
			if (strstr($path, $pathvh) === FALSE) {
				$err = ' VHost config file must locate within $SERVER_ROOT/conf/vhosts/, suggested value is $SERVER_ROOT/conf/vhosts/$VH_NAME/vhconf.conf';
				$res = -1;
			}
			else if (substr($path, -5) != '.conf') {
				$err = ' VHost config file name needs to be ".conf"';
				$res = -1;
			}
		}

		if ( $res == -1 && $_POST['file_create'] == $attr->GetKey()
			&& $this->allow_create($attr, $path) )	{
			if ( PathTool::createFile($path, $err, $attr->GetKey()) ) {
				$err = "$path has been created successfully.";
			}
			$res = 0; // make it always point to curr page
		}

		return $res;
	}

	protected function chk_file1($attr, &$path, &$err)
	{
		if(!strlen($path)) {
			$err = "Invalid Path.";
			return -1;
		}

		$s = $path{0};

		if ( strpos($path, '$VH_NAME') !== FALSE )	{
			$path = str_replace('$VH_NAME', $this->_disp->Get(DInfo::FLD_ViewName), $path);
		}

		if ( $s == '/' ) {
			return $this->test_file($path, $err, $attr);
		}

		if ( $attr->_minVal == 1 ) {
			$err = 'only accept absolute path';
			return -1;
		}
		elseif ( $attr->_minVal == 2 ) {
			if ( strncasecmp('$SERVER_ROOT', $path, 12) != 0 )	{
				$err = 'only accept absolute path or path relative to $SERVER_ROOT' . $path;
				return -1;
			} else {
				$path = SERVER_ROOT . substr($path, 13);
			}
		}
		elseif ( $attr->_minVal == 3 ) {
			if ( strncasecmp('$SERVER_ROOT', $path, 12) == 0 ) {
				$path = SERVER_ROOT . substr($path, 13);
			} elseif ( strncasecmp('$VH_ROOT', $path, 8) == 0 )	{
				$vhroot = $this->_disp->GetVHRoot();
				if ($vhroot == NULL) {
					$err = 'Fail to find $VH_ROOT';
					return -1;
				}
				$path = $vhroot . substr($path, 9);
			} else {
				$err = 'only accept absolute path or path relative to $SERVER_ROOT or $VH_ROOT';
				return -1;
			}
		}

		return $this->test_file($path, $err, $attr);
	}

	protected function chkAttr_uri($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		if ( $val[0] != '/' ) {
			$node->SetErr('URI must start with "/"');
			return -1;
		}
		return 1;
	}

	protected function chkAttr_expuri($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		if ( $val{0} == '/' || strncmp( $val, 'exp:', 4 ) == 0 ) {
			return 1;
		} else {
			$node->SetErr('URI must start with "/" or "exp:"');
			return -1;
		}
	}

	protected function chkAttr_url($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		if (( $val{0} != '/' )
		&&( strncmp( $val, 'http://', 7 ) != 0 )
		&&( strncmp( $val, 'https://', 8 ) != 0 )) {
			$node->SetErr('URL must start with "/" or "http(s)://"');
			return -1;
		}
		return 1;
	}

	protected function chkAttr_httpurl($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		if (strncmp( $val, 'http://', 7 ) != 0 ) {
			$node->SetErr('Http URL must start with "http://"');
			return -1;
		}
		return 1;
	}

	protected function chkAttr_email($attr, $node)
	{
		$err = '';
		$res = $this->chkAttr_email_val($attr, $node->Get(CNode::FLD_VAL), $err);
		if ($err != '')
			$node->SetErr($err);
		return $res;
	}

	protected function chkAttr_email_val($attr, $val, &$err)
	{
		if ( preg_match("/^[[:alnum:]._-]+@.+/", $val ) ) {
			return 1;
		} else {
			$err = 'invalid email format: ' . $val;
			return -1;
		}
	}

	protected function chkAttr_addr($attr, $node)
	{
		if ( preg_match("/^[[:alnum:]._-]+:(\d)+$/", $node->Get(CNode::FLD_VAL)) ) {
			return 1;
		} elseif ( preg_match("/^UDS:\/\/.+/i", $node->Get(CNode::FLD_VAL)) ) {
			return 1;
		} else {
			$node->SetErr('invalid address: correct syntax is "IPV4|IPV6_address:port" or UDS://path');
			return -1;
		}
	}

	protected function chkAttr_wsaddr($attr, $node)
	{
		if ( preg_match("/^((http|https):\/\/)?[[:alnum:]._-]+(:\d+)?$/", $node->Get(CNode::FLD_VAL)) ) {
			return 1;
		} else {
			$node->SetErr('invalid address: correct syntax is "[http|https://]IPV4|IPV6_address[:port]". ');
			return -1;
		}
	}

	protected function chkAttr_bool($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		if ( $val === '1' || $val === '0' ) {
			return 1;
		}
		$node->SetErr('invalid value');
		return -1;
	}

	protected function chkAttr_parse($attr, $node)
	{
		$err = '';
		$res = $this->chkAttr_parse_val($attr, $node->Get(CNode::FLD_VAL), $err);
		if ($err != '')
			$node->SetErr($err);
		return $res;
	}

	protected function chkAttr_parse_val($attr, $val, &$err)
	{
		if ( preg_match($attr->_minVal, $val) ) {
			return 1;
		} else {
			$err = "invalid format - $val, syntax is {$attr->_maxVal}";
			return -1;
		}
	}

	protected function getKNum($strNum)
	{
		$tag = strtoupper(substr($strNum, -1));
		switch( $tag ) {
			case 'K': $multi = 1024; break;
			case 'M': $multi = 1048576; break;
			case 'G': $multi = 1073741824; break;
			default: return intval($strNum);
		}

		return (intval(substr($strNum, 0, -1)) * $multi);
	}

	protected function chkAttr_uint($attr, $node)
	{
		$val = $node->Get(CNode::FLD_VAL);
		if ( preg_match("/^(-?\d+)([KkMmGg]?)$/", $val, $m) ) {
			$val1 = $this->getKNum($val);
			if (isset($attr->_minVal)) {
				$min = $this->getKNum($attr->_minVal);
				if ($val1 < $min) {
					$node->SetErr('number is less than the minimum required');
					return -1;
				}

			}
			if (isset($attr->_maxVal)) {
				$max = $this->getKNum($attr->_maxVal);
				if ( $val1 > $max )	{
					$node->SetErr('number exceeds maximum allowed');
					return -1;
				}
			}
			return 1;
		} else {
			$node->SetErr('invalid number format');
			return -1;
		}
	}



}
