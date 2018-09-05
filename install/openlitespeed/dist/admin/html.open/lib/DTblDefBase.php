<?php

class DTblDefBase
{

    protected $_tblDef = [];
    protected $_options = [];
    protected $_attrs;
    protected $_specials = [];

    public function GetTblDef($tblId)
    {
        if (!isset($this->_tblDef[$tblId])) {
            $funcname = 'add_' . $tblId;
            if (!method_exists($this, $funcname)) {
                die("invalid tid $tblId\n");
            }
            $this->$funcname($tblId);
        }
        return $this->_tblDef[$tblId];
    }

    protected function loadSpecials()
    {
        // define special block contains raw data
        $this->addSpecial('rewrite', ['enable', 'logLevel', 'inherit', 'base'], 'rules');
    }

    protected function addSpecial($key, $attrList, $catchAllTag)
    {
        $key = strtolower($key);
        if (!isset($this->_specials[$key])) {
            $this->_specials[$key] = [];
        }
        foreach($attrList as $attr) {
            $this->_specials[$key][] = strtolower($attr);
        }
        $this->_specials[$key]['*'] = $catchAllTag;
    }

    public function MarkSpecialBlock($node)
    {
        $key = strtolower($node->Get(CNode::FLD_KEY));
        if (isset($this->_specials[$key])) {
            $tag = $this->_specials[$key]['*']; // cache all key
            $node->AddRawTag($tag);
            return true;
        }
        return false;
    }

    public function IsSpecialBlockRawContent($node, $testKey)
    {
        $key = strtolower($node->Get(CNode::FLD_KEY));
        if (isset($this->_specials[$key])) {
            if (!in_array(strtolower($testKey), $this->_specials[$key])) {
                return true;
            }
        }
        return false;
    }

    protected function DupTblDef($tblId, $newId, $newTitle = null)
    {
        $tbl = $this->GetTblDef($tblId);
        $newtbl = $tbl->Dup($newId, $newTitle);
        return $newtbl;
    }

    protected static function NewIntAttr($key, $label, $allowNull = true, $min = null, $max = null, $helpKey = null)
    {
        return new DAttr($key, 'uint', $label, 'text', $allowNull, $min, $max, null, 0, $helpKey);
    }

    protected static function NewBoolAttr($key, $label, $allowNull = true, $helpKey = null)
    {
        return new DAttr($key, 'bool', $label, 'radio', $allowNull, null, null, null, 0, $helpKey);
    }

    protected static function NewSelAttr($key, $label, $options, $allowNull = true, $helpKey = null, $inputAttr = null, $multiInd = 0)
    {
        if (is_array($options)) // fixed options
            return new DAttr($key, 'sel', $label, 'select', $allowNull, null, $options, $inputAttr, 0, $helpKey);

        // derived options
        if ($multiInd == 0)
            return new DAttr($key, 'sel1', $label, 'select', $allowNull, $options, null, $inputAttr, 0, $helpKey);
        else //sel2 is derived and multi and using text
            return new DAttr($key, 'sel2', $label, 'text', $allowNull, $options, null, $inputAttr, 1, $helpKey);
    }

    protected static function NewCheckBoxAttr($key, $label, $options, $allowNull = true, $helpKey = null, $default = null)
    {
        return new DAttr($key, 'checkboxOr', $label, 'checkboxgroup', $allowNull, $default, $options, null, 0, $helpKey);
    }

    protected static function NewTextAttr($key, $label, $type, $allowNull = true, $helpKey = null, $multiInd = 0, $inputAttr = null)
    {
        return new DAttr($key, $type, $label, 'text', $allowNull, null, null, $inputAttr, $multiInd, $helpKey);
    }

    protected static function NewParseTextAttr($key, $label, $parseformat, $parsehelp, $allowNull = true, $helpKey = null, $multiInd = 0)
    {
        return new DAttr($key, 'parse', $label, 'text', $allowNull, $parseformat, $parsehelp, null, $multiInd, $helpKey);
    }

    protected static function NewParseTextAreaAttr($key, $label, $parseformat, $parsehelp, $allowNull = true, $row, $helpKey = null, $viewtextarea = 1, $wrapoff = 0, $multiInd = 0)
    {
        $inputAttr = 'rows="' . $row . '"';
        if ($wrapoff == 1)
            $inputAttr .= ' wrap=off';

        $type = ($viewtextarea == 1) ? 'textarea1' : 'textarea';
        return new DAttr($key, 'parse', $label, $type, $allowNull, $parseformat, $parsehelp, $inputAttr, $multiInd, $helpKey);
    }

    protected static function NewTextAreaAttr($key, $label, $type, $allowNull = true, $row, $helpKey = null, $viewtextarea = 1, $wrapoff = 0, $multiInd = 0)
    {
        $inputAttr = 'rows="' . $row . '"';
        if ($wrapoff == 1)
            $inputAttr .= ' wrap="off"';

        $inputtype = ($viewtextarea == 1) ? 'textarea1' : 'textarea';
        return new DAttr($key, $type, $label, $inputtype, $allowNull, null, null, $inputAttr, $multiInd, $helpKey);
    }

    protected static function NewPathAttr($key, $label, $type, $reflevel, $rwc = '', $allowNull = true, $helpKey = null, $multiInd = 0)
    {
        return new DAttr($key, $type, $label, 'text', $allowNull, $reflevel, $rwc, null, $multiInd, $helpKey);
    }

    protected static function NewCustFlagAttr($key, $label, $flag = 0, $allowNull = true, $type = 'cust', $inputtype = 'text', $helpKey = null, $multiInd = 0)
    {
        $attr = new DAttr($key, $type, $label, $inputtype, $allowNull, null, null, null, $multiInd, $helpKey);
        if ($flag != 0)
            $attr->SetFlag($flag);
        return $attr;
    }

    protected static function NewPassAttr($key, $label, $allowNull = true, $helpKey = null)
    {
        return new DAttr($key, 'cust', $label, 'password', $allowNull, null, null, null, 0, $helpKey);
    }

    protected static function NewViewAttr($key, $label, $helpKey = null) // for view only
    {
        return new DAttr($key, 'cust', $label, null, null, null, null, null, 0, $helpKey);
    }

    protected static function NewActionAttr($linkTbl, $act, $allowNull = true)
    {
        return new DAttr('action', 'action', DMsg::ALbl('l_action'), null, $allowNull, $linkTbl, $act);
    }

    protected function loadCommonOptions()
    {
        $this->_options['tp_vname'] = array('/\$VH_NAME/', DMsg::ALbl('parse_tpname'));

        $this->_options['symbolLink'] = array('1' => DMsg::ALbl('o_yes'), '2' => DMsg::ALbl('o_ifownermatch'), '0' => DMsg::ALbl('o_no'));

        $this->_options['extType'] = array(
            'fcgi'         => DMsg::ALbl('l_fcgiapp'), 'fcgiauth'     => DMsg::ALbl('l_extfcgiauth'),
            'lsapi'        => DMsg::ALbl('l_extlsapi'),
            'servlet'      => DMsg::ALbl('l_extservlet'), 'proxy'        => DMsg::ALbl('l_extproxy'),
            'logger'       => DMsg::ALbl('l_extlogger'),
            'loadbalancer' => DMsg::ALbl('l_extlb'));

        $this->_options['extTbl'] = array(
            0              => 'type', 1              => 'A_EXT_FCGI',
            'fcgi'         => 'A_EXT_FCGI', 'fcgiauth'     => 'A_EXT_FCGIAUTH',
            'lsapi'        => 'A_EXT_LSAPI',
            'servlet'      => 'A_EXT_SERVLET', 'proxy'        => 'A_EXT_PROXY',
            'logger'       => 'A_EXT_LOGGER',
            'loadbalancer' => 'A_EXT_LOADBALANCER');

        $this->_options['tp_extTbl'] = array(
            0              => 'type', 1              => 'T_EXT_FCGI',
            'fcgi'         => 'T_EXT_FCGI', 'fcgiauth'     => 'T_EXT_FCGIAUTH',
            'lsapi'        => 'T_EXT_LSAPI',
            'servlet'      => 'T_EXT_SERVLET', 'proxy'        => 'T_EXT_PROXY',
            'logger'       => 'T_EXT_LOGGER',
            'loadbalancer' => 'T_EXT_LOADBALANCER');

        $this->_options['logLevel'] = array('ERROR'  => 'ERROR', 'WARN'   => 'WARNING',
            'NOTICE' => 'NOTICE', 'INFO'   => 'INFO', 'DEBUG'  => 'DEBUG');

        // for shared parse format
        $this->_options['parseFormat'] = array(
            'filePermission4' => '/^0?[0-7]{3,4}$/',
            'filePermission3' => '/^0?[0-7]{3}$/'
        );

        $ipv6str = isset($_SERVER['LSWS_IPV6_ADDRS']) ? $_SERVER['LSWS_IPV6_ADDRS'] : '';
        $ipv6 = [];
        if ($ipv6str != '') {
            $ipv6['[ANY]'] = '[ANY] IPv6';
            $ips = explode(',', $ipv6str);
            foreach ($ips as $ip) {
                if ($pos = strpos($ip, ':')) {
                    $aip = substr($ip, $pos + 1);
                    $ipv6[$aip] = $aip;
                }
            }
        }
        $ipo = [];
        $ipo['ANY'] = 'ANY';
        $ipstr = isset($_SERVER['LSWS_IPV4_ADDRS']) ? $_SERVER['LSWS_IPV4_ADDRS'] : '';
        if ($ipstr != '') {
            $ips = explode(',', $ipstr);
            foreach ($ips as $ip) {
                if ($pos = strpos($ip, ':')) {
                    $aip = substr($ip, $pos + 1);
                    $ipo[$aip] = $aip;
                    if ($aip != '127.0.0.1')
                        $ipv6["[::FFFF:$aip]"] = "[::FFFF:$aip]";
                }
            }
        }
        if ($ipv6str != '')
            $this->_options['ip'] = $ipo + $ipv6;
        else
            $this->_options['ip'] = $ipo;
    }

    protected function loadCommonAttrs()
    {
        $ctxOrder = self::NewViewAttr('order', DMsg::ALbl('l_order'));
        $ctxOrder->SetFlag(DAttr::BM_NOFILE | DAttr::BM_HIDE | DAttr::BM_NOEDIT);

        $attrs = array(
            'priority'    => self::NewIntAttr('priority', DMsg::ALbl('l_priority'), true, -20, 20),
            'indexFiles'  => self::NewTextAreaAttr('indexFiles', DMsg::ALbl('l_indexfiles'), 'fname', true, 2, null, 0, 0, 1),
            'autoIndex'   => self::NewBoolAttr('autoIndex', DMsg::ALbl('l_autoindex')),
            'adminEmails' => self::NewTextAreaAttr('adminEmails', DMsg::ALbl('l_adminemails'), 'email', true, 3, null, 0, 0, 1),
            'suffix'      => self::NewParseTextAttr('suffix', DMsg::ALbl('l_suffix'), "/^[A-z0-9_\-]+$/", DMsg::ALbl('parse_suffix'), false, null, 1),
            'fileName2'   => self::NewPathAttr('fileName', DMsg::ALbl('l_filename'), 'file0', 2, 'r', false),
            'fileName3'   => self::NewPathAttr('fileName', DMsg::ALbl('l_filename'), 'file0', 3, 'r', true),
            'rollingSize'     => self::NewIntAttr('rollingSize', DMsg::ALbl('l_rollingsize'), true, null, null, 'log_rollingSize'),
            'keepDays'        => self::NewIntAttr('keepDays', DMsg::ALbl('l_keepdays'), true, 0, null, 'accessLog_keepDays'),
            'logFormat'       => self::NewTextAttr('logFormat', DMsg::ALbl('l_logformat'), 'cust', true, 'accessLog_logFormat'),
            'logHeaders'      => self::NewCheckBoxAttr('logHeaders', DMsg::ALbl('l_logheaders'), array('1' => 'Referrer', '2' => 'UserAgent', '4' => 'Host', '0' => DMsg::ALbl('o_none')), true, 'accessLog_logHeader'),
            'compressArchive' => self::NewBoolAttr('compressArchive', DMsg::ALbl('l_compressarchive'), true, 'accessLog_compressArchive'),
            'extraHeaders' => self::NewTextAreaAttr('extraHeaders', DMsg::ALbl('l_extraHeaders'), 'cust', true, 2, null, 1, 1),
            'scriptHandler_type' => self::NewSelAttr('type', DMsg::ALbl('l_handlertype'), $this->_options['scriptHandler'], false, 'shType', 'onChange="lst_conf(\'c\')"'),
            'scriptHandler' => self::NewSelAttr('handler', DMsg::ALbl('l_handlername'), 'extprocessor:$$type', false, 'shHandlerName'),
            'ext_type'           => self::NewSelAttr('type', DMsg::ALbl('l_type'), $this->_options['extType'], false, 'extAppType'),
            'name'               => self::NewTextAttr('name', DMsg::ALbl('l_name'), 'name', false),
            'ext_name'           => self::NewTextAttr('name', DMsg::ALbl('l_name'), 'name', false, 'extAppName'),
            'ext_address'        => self::NewTextAttr('address', DMsg::ALbl('l_address'), 'addr', false, 'extAppAddress'),
            'ext_maxConns'       => self::NewIntAttr('maxConns', DMsg::ALbl('l_maxconns'), false, 1, 2000),
            'pcKeepAliveTimeout' => self::NewIntAttr('pcKeepAliveTimeout', DMsg::ALbl('l_pckeepalivetimeout'), true, -1, 10000),
            'ext_env'          => self::NewParseTextAreaAttr('env', DMsg::ALbl('l_env'), "/\S+=\S+/", DMsg::ALbl('parse_env'), true, 5, null, 0, 1, 2),
            'ext_initTimeout'  => self::NewIntAttr('initTimeout', DMsg::ALbl('l_inittimeout'), false, 1),
            'ext_retryTimeout' => self::NewIntAttr('retryTimeout', DMsg::ALbl('l_retrytimeout'), false, 0),
            'ext_respBuffer'   => self::NewSelAttr('respBuffer', DMsg::ALbl('l_respbuffer'), array('0' => DMsg::ALbl('o_no'), '1' => DMsg::ALbl('o_yes'), '2' => DMsg::ALbl('o_nofornph')), false),
            'ext_persistConn'  => self::NewBoolAttr('persistConn', DMsg::ALbl('l_persistconn')),
            'ext_autoStart'    => self::NewSelAttr('autoStart', DMsg::ALbl('l_autostart'), array('1' => DMsg::ALbl('o_yes'), '0' => DMsg::ALbl('o_no'), '2' => DMsg::ALbl('o_thrucgidaemon')), false),
            'ext_path'         => self::NewPathAttr('path', DMsg::ALbl('l_command'), 'file1', 3, 'x', true, 'extAppPath'),
            'ext_backlog'      => self::NewIntAttr('backlog', DMsg::ALbl('l_backlog'), true, 1, 100),
            'ext_instances'    => self::NewIntAttr('instances', DMsg::ALbl('l_instances'), true, 0, 1000),
            'ext_runOnStartUp' => self::NewSelAttr('runOnStartUp', DMsg::ALbl('l_runonstartup'), array('' => '', '1' => DMsg::ALbl('o_yes'), '0' => DMsg::ALbl('o_no'), '2' => 'suEXEC Daemon')),
            'ext_user'         => self::NewTextAttr('extUser', DMsg::ALbl('l_suexecuser'), 'cust'),
            'ext_group'        => self::NewTextAttr('extGroup', DMsg::ALbl('l_suexecgrp'), 'cust'),
            'cgiUmask'      => self::NewParseTextAttr('umask', DMsg::ALbl('l_umask'), $this->_options['parseFormat']['filePermission3'], DMsg::ALbl('parse_umask')),
            'memSoftLimit'  => self::NewIntAttr('memSoftLimit', DMsg::ALbl('l_memsoftlimit'), true, 0),
            'memHardLimit'  => self::NewIntAttr('memHardLimit', DMsg::ALbl('l_memhardlimit'), true, 0),
            'procSoftLimit' => self::NewIntAttr('procSoftLimit', DMsg::ALbl('l_procsoftlimit'), true, 0),
            'procHardLimit' => self::NewIntAttr('procHardLimit', DMsg::ALbl('l_prochardlimit'), true, 0),
            'ssl_renegProtection' => self::NewBoolAttr('renegProtection', DMsg::ALbl('l_renegprotection')),
            'sslSessionCache'     => self::NewBoolAttr('sslSessionCache', DMsg::ALbl('l_sslSessionCache')),
            'sslSessionTickets'   => self::NewBoolAttr('sslSessionTickets', DMsg::ALbl('l_sslSessionTickets')),
            'l_vhost'         => self::NewSelAttr('vhost', DMsg::ALbl('l_vhost'), 'virtualhost', false, 'virtualHostName'),
            'l_domain'        => self::NewTextAttr('domain', DMsg::ALbl('l_domains'), 'domain', false, 'domainName', 1),
            'tp_templateFile' => self::NewPathAttr('templateFile', DMsg::ALbl('l_templatefile'), 'filetp', 2, 'rwc', false),
            'tp_listeners'    => self::NewSelAttr('listeners', DMsg::ALbl('l_mappedlisteners'), 'listener', false, 'mappedListeners', null, 1),
            'tp_vhName'       => self::NewTextAttr('vhName', DMsg::ALbl('l_vhname'), 'vhname', false, 'templateVHName'),
            'tp_vhDomain'     => self::NewTextAttr('vhDomain', DMsg::ALbl('l_domain'), 'domain', true, 'templateVHDomain'),
            'tp_vhAliases'    => self::NewTextAttr('vhAliases', DMsg::ALbl('l_vhaliases'), 'domain', true, 'templateVHAliases', 1),
            'tp_vhRoot' => self::NewParseTextAttr('vhRoot', DMsg::ALbl('l_defaultvhroot'), $this->_options['tp_vname'][0], $this->_options['tp_vname'][1], false, 'templateVHRoot'),
            'tp_vrFile' => self::NewParseTextAttr('fileName', DMsg::ALbl('l_filename'), '/(\$VH_NAME)|(\$VH_ROOT)/', DMsg::ALbl('parse_tpfile'), false, 'templateFileRef'),
            'tp_name'            => self::NewParseTextAttr('name', DMsg::ALbl('l_name'), $this->_options['tp_vname'][0], $this->_options['tp_vname'][1], false, 'tpextAppName'),
            'vh_maxKeepAliveReq' => self::NewIntAttr('maxKeepAliveReq', DMsg::ALbl('l_maxkeepalivereq'), true, 0, 32767, 'vhMaxKeepAliveReq'),
            'vh_smartKeepAlive'  => self::NewBoolAttr('smartKeepAlive', DMsg::ALbl('l_smartkeepalive'), true, 'vhSmartKeepAlive'),
            'vh_enableGzip'      => self::NewBoolAttr('enableGzip', DMsg::ALbl('l_enablecompress'), true, 'vhEnableGzip'),
            'vh_spdyAdHeader'    => self::NewParseTextAttr('spdyAdHeader', DMsg::ALbl('l_spdyadheader'), "/^\d+:npn-spdy\/[23]$/", DMsg::ALbl('parse_spdyadheader')),
            'vh_allowSymbolLink' => self::NewSelAttr('allowSymbolLink', DMsg::ALbl('l_allowsymbollink'), $this->_options['symbolLink']),
            'vh_enableScript'    => self::NewBoolAttr('enableScript', DMsg::ALbl('l_enablescript'), false),
            'vh_restrained'      => self::NewBoolAttr('restrained', DMsg::ALbl('l_restrained'), false),
            'vh_setUIDMode'      => self::NewSelAttr('setUIDMode', DMsg::ALbl('l_setuidmode'), array('' => '', 0 => 'Server UID', 1 => 'CGI File UID', 2 => 'DocRoot UID'), true, 'setUidMode'),
            'staticReqPerSec'    => self::NewIntAttr('staticReqPerSec', DMsg::ALbl('l_staticreqpersec'), true, 0),
            'dynReqPerSec'       => self::NewIntAttr('dynReqPerSec', DMsg::ALbl('l_dynreqpersec'), true, 0),
            'outBandwidth'       => self::NewIntAttr('outBandwidth', DMsg::ALbl('l_outbandwidth'), true, 0),
            'inBandwidth'        => self::NewIntAttr('inBandwidth', DMsg::ALbl('l_inbandwidth'), true, 0),
            'ctx_order'    => $ctxOrder,
            'ctx_type'     => self::NewSelAttr('type', DMsg::ALbl('l_type'), $this->_options['ctxType'], false, 'ctxType'),
            'ctx_uri'      => self::NewTextAttr('uri', DMsg::ALbl('l_uri'), 'expuri', false, 'expuri'),
            'ctx_location' => self::NewTextAttr('location', DMsg::ALbl('l_location'), 'cust', false),
            'ctx_shandler' => self::NewSelAttr('handler', DMsg::ALbl('l_servletengine'), 'extprocessor:servlet', false, 'servletEngine'),
            'appserverEnv' => self::NewSelAttr('envType', DMsg::ALbl('l_runtimemode'), array('' => '', '0' => 'Development', '1' => 'Production', '2' => 'Staging')),
            'geoipDBFile' => self::NewPathAttr('geoipDBFile', DMsg::ALbl('l_geoipdbfile'), 'filep', 2, 'r', false),
            'geoipDBCache' => self::NewSelAttr('geoipDBCache', DMsg::ALbl('l_dbcache'), array(''            => '', 'Standard'    => 'Standard',
                'MemoryCache' => 'MemoryCache',
                'CheckCache'  => 'CheckCache',
                'IndexCache'  => 'IndexCache')),
            'enableIpGeo'  => self::NewBoolAttr('enableIpGeo', DMsg::ALbl('l_enableipgeo')),
            'note'         => self::NewTextAreaAttr('note', DMsg::ALbl('l_notes'), 'cust', true, 4, null, 0),
        );
        $this->_attrs = $attrs;
    }

    //	DAttr($key, $type, $label,  $inputType, $allowNull,$min, $max, $inputAttr, $multiInd)
    protected function get_expires_attrs()
    {
        return array(
            self::NewBoolAttr('enableExpires', DMsg::ALbl('l_enableexpires')),
            self::NewParseTextAttr('expiresDefault', DMsg::ALbl('l_expiresdefault'), "/^[AaMm]\d+$/", DMsg::ALbl('parse_expiresdefault')),
            self::NewParseTextAreaAttr('expiresByType', DMsg::ALbl('l_expiresByType'), "/^(\*\/\*)|([A-z0-9_\-\.\+]+\/\*)|([A-z0-9_\-\.\+]+\/[A-z0-9_\-\.\+]+)=[AaMm]\d+$/", DMsg::ALbl('parse_expiresByType'), true, 2, null, 0, 0, 1)
        );
    }

    protected function add_S_INDEX($id)
    {
        $attrs = array(
            $this->_attrs['indexFiles'],
            $this->_attrs['autoIndex'],
            self::NewTextAttr('autoIndexURI', DMsg::ALbl('l_autoindexuri'), 'uri')
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_indexfiles'), $attrs);
    }

    protected function add_S_LOG($id)
    {
        $attrs = array(
            $this->_attrs['fileName2']->dup(null, null, 'log_fileName'),
            self::NewSelAttr('logLevel', DMsg::ALbl('l_loglevel'), $this->_options['logLevel'], false, 'log_logLevel'),
            self::NewSelAttr('debugLevel', DMsg::ALbl('l_debuglevel'), array('10' => DMsg::ALbl('o_high'), '5' => DMsg::ALbl('o_medium'), '2' => DMsg::ALbl('o_low'), '0' => DMsg::ALbl('o_none')), false, 'log_debugLevel'),
            $this->_attrs['rollingSize'],
            self::NewBoolAttr('enableStderrLog', DMsg::ALbl('l_enablestderrlog'), true, 'log_enableStderrLog')
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_serverlog'), $attrs, 'fileName');
    }

    protected function add_S_ACLOG($id)
    {
        $attrs = array(
            $this->_attrs['fileName2']->dup(null, null, 'accessLog_fileName'),
            self::NewSelAttr('pipedLogger', DMsg::ALbl('l_pipedlogger'), 'extprocessor:logger', true, 'accessLog_pipedLogger'),
            $this->_attrs['logFormat'],
            $this->_attrs['logHeaders'],
            $this->_attrs['rollingSize'],
            $this->_attrs['keepDays'],
            $this->_attrs['compressArchive']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_accesslog'), $attrs, 'fileName');
    }

    protected function add_A_EXPIRES($id)
    {
        $attrs = $this->get_expires_attrs();
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_expires'), $attrs);
    }

    protected function add_S_GEOIP_TOP($id)
    {
        $align = array('center', 'center', 'center');

        $attrs = array(
            $this->_attrs['geoipDBFile'],
            $this->_attrs['geoipDBCache'],
            self::NewActionAttr('S_GEOIP', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_geoipdb'), $attrs, 'geoipDBFile', 'S_GEOIP', $align, 'geolocationDB', 'database', true);
    }

    protected function add_S_GEOIP($id)
    {
        $attrs = array(
            $this->_attrs['geoipDBFile'],
            $this->_attrs['geoipDBCache'],
            $this->_attrs['note'],
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_geoipdb'), $attrs, 'geoipDBFile', 'geolocationDB');
    }

    private function add_S_IP2LOCATION($id)
    {
        $attrs = array(
            self::NewPathAttr('ip2locDBFile', DMsg::ALbl('l_ip2locDBFile'), 'filep', 2, 'r'),
            self::NewSelAttr('ip2locDBCache', DMsg::ALbl('l_dbcache'), array(''                  => '', 'FileIo'            => 'File System',
                'MemoryCache'       => 'Memory',
                'SharedMemoryCache' => 'Shared Memory')),
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_ip2locDB'), $attrs);
    }

    protected function add_S_TUNING_CONN($id)
    {
        $attrs = array(
            self::NewIntAttr('maxConnections', DMsg::ALbl('l_maxconns'), false, 1),
            self::NewIntAttr('maxSSLConnections', DMsg::ALbl('l_maxsslconns'), false, 0),
            self::NewIntAttr('connTimeout', DMsg::ALbl('l_conntimeout'), false, 10, 1000000),
            self::NewIntAttr('maxKeepAliveReq', DMsg::ALbl('l_maxkeepalivereq'), false, 0, 32767),
            self::NewBoolAttr('smartKeepAlive', DMsg::ALbl('l_smartkeepalive'), false),
            self::NewIntAttr('keepAliveTimeout', DMsg::ALbl('l_keepalivetimeout'), false, 0, 60),
            self::NewIntAttr('sndBufSize', DMsg::ALbl('l_sndbufsize'), true, 0, '512K'),
            self::NewIntAttr('rcvBufSize', DMsg::ALbl('l_rcvbufsize'), true, 0, '512K'),
        );

        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_connection'), $attrs);
    }

    protected function add_S_TUNING_REQ($id)
    {
        $attrs = array(
            self::NewIntAttr('maxReqURLLen', DMsg::ALbl('l_maxrequrllen'), false, 200, 8192),
            self::NewIntAttr('maxReqHeaderSize', DMsg::ALbl('l_maxreqheadersize'), false, 1024, 16380),
            self::NewIntAttr('maxReqBodySize', DMsg::ALbl('l_maxreqbodysize'), false, '1M', null),
            self::NewIntAttr('maxDynRespHeaderSize', DMsg::ALbl('l_maxdynrespheadersize'), false, 200, 8192),
            self::NewIntAttr('maxDynRespSize', DMsg::ALbl('l_maxdynrespsize'), false, '1M', null)
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_reqresp'), $attrs);
    }

    protected function add_S_TUNING_GZIP($id)
    {
        $parseFormat = "/^(\!)?(\*\/\*)|([A-z0-9_\-\.\+]+\/\*)|([A-z0-9_\-\.\+]+\/[A-z0-9_\-\.\+]+)$/";

        $attrs = array(
            self::NewBoolAttr('enableGzipCompress', DMsg::ALbl('l_enablecompress'), false),
            self::NewBoolAttr('enableDynGzipCompress', DMsg::ALbl('l_enabledyngzipcompress'), false),
            self::NewIntAttr('gzipCompressLevel', DMsg::ALbl('l_gzipcompresslevel'), true, 1, 9),
            self::NewParseTextAreaAttr('compressibleTypes', DMsg::ALbl('l_compressibletypes'), $parseFormat, DMsg::ALbl('parse_compressibletypes'), true, 5, null, 0, 0, 1),
            self::NewBoolAttr('gzipAutoUpdateStatic', DMsg::ALbl('l_gzipautoupdatestatic')),
            self::NewTextAttr('gzipCacheDir', DMsg::ALbl('l_gzipcachedir'), 'cust'),
            self::NewIntAttr('gzipStaticCompressLevel', DMsg::ALbl('l_staticcompresslevel'), true, 1, 9),
            self::NewIntAttr('gzipMaxFileSize', DMsg::ALbl('l_gzipmaxfilesize'), true, '1K'),
            self::NewIntAttr('gzipMinFileSize', DMsg::ALbl('l_gzipminfilesize'), true, 200)
        );

        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_gzip'), $attrs);
    }

    protected function add_S_TUNING_BROTLI($id)
    {
        $attrs = array(
            self::NewBoolAttr('enableBrCompress', DMsg::ALbl('l_enablebrcompress')),
            self::NewIntAttr('brStaticCompressLevel', DMsg::ALbl('l_staticcompresslevel'), true, 1, 11),
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_brcompress'), $attrs, 'brotliTuning');
    }

    protected function add_S_SEC_FILE($id)
    {
        $parseFormat = $this->_options['parseFormat']['filePermission4'];
        $parseHelp = DMsg::ALbl('parse_secpermissionmask');

        $attrs = array(
            self::NewSelAttr('followSymbolLink', DMsg::ALbl('l_followsymbollink'), $this->_options['symbolLink'], false),
            self::NewBoolAttr('checkSymbolLink', DMsg::ALbl('l_checksymbollink'), false),
            self::NewBoolAttr('forceStrictOwnership', DMsg::ALbl('l_forcestrictownership'), false),
            self::NewParseTextAttr('requiredPermissionMask', DMsg::ALbl('l_requiredpermissionmask'), $parseFormat, $parseHelp),
            self::NewParseTextAttr('restrictedPermissionMask', DMsg::ALbl('l_restrictedpermissionmask'), $parseFormat, $parseHelp),
            self::NewParseTextAttr('restrictedScriptPermissionMask', DMsg::ALbl('l_restrictedscriptpermissionmask'), $parseFormat, $parseHelp),
            self::NewParseTextAttr('restrictedDirPermissionMask', DMsg::ALbl('l_restricteddirpermissionmask'), $parseFormat, $parseHelp)
        );

        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_fileaccess'), $attrs);
    }

    protected function add_S_SEC_CONN($id)
    {
        $attrs = array(
            $this->_attrs['staticReqPerSec'],
            $this->_attrs['dynReqPerSec'],
            $this->_attrs['outBandwidth'],
            $this->_attrs['inBandwidth'],
            self::NewIntAttr('softLimit', DMsg::ALbl('l_softlimit'), true, 0),
            self::NewIntAttr('hardLimit', DMsg::ALbl('l_hardlimit'), true, 0),
            self::NewBoolAttr('blockBadReq', DMsg::ALbl('l_blockbadreq')),
            self::NewIntAttr('gracePeriod', DMsg::ALbl('l_graceperiod'), true, 1, 3600),
            self::NewIntAttr('banPeriod', DMsg::ALbl('l_banperiod'), true, 0)
        );

        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_perclientthrottle'), $attrs, 'perClientConnLimit');
    }

    protected function add_S_SEC_CGI($id)
    {
        $attrs = array(
            self::NewTextAttr('cgidSock', DMsg::ALbl('l_cgidsock'), 'addr'),
            self::NewIntAttr('maxCGIInstances', DMsg::ALbl('l_maxCGIInstances'), true, 1, 2000),
            self::NewIntAttr('minUID', DMsg::ALbl('l_minuid'), true, 10),
            self::NewIntAttr('minGID', DMsg::ALbl('l_mingid'), true, 5),
            self::NewIntAttr('forceGID', DMsg::ALbl('l_forcegid'), true, 0),
            $this->_attrs['cgiUmask'],
            $this->_attrs['priority']->dup(null, DMsg::ALbl('l_cgipriority'), 'CGIPriority'),
            self::NewIntAttr('CPUSoftLimit', DMsg::ALbl('l_cpusoftlimit'), true, 0),
            self::NewIntAttr('CPUHardLimit', DMsg::ALbl('l_cpuhardlimit'), true, 0),
            $this->_attrs['memSoftLimit'],
            $this->_attrs['memHardLimit'],
            $this->_attrs['procSoftLimit'],
            $this->_attrs['procHardLimit']
        );

        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_cgisettings'), $attrs, 'cgiResource');
    }

    protected function add_S_SEC_DENY($id)
    {
        $attrs = array(
            self::NewTextAreaAttr('dir', null, 'dir', true, 15, null, 0, 1, 2)
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_accessdenydir'), $attrs, 'accessDenyDir', 1);
    }

    protected function add_A_SEC_AC($id)
    {
        $attrs = array(
            self::NewTextAreaAttr('allow', DMsg::ALbl('l_accessallow'), 'subnet', true, 5, 'accessControl_allow', 0, 0, 1),
            self::NewTextAreaAttr('deny', DMsg::ALbl('l_accessdeny'), 'subnet', true, 5, 'accessControl_deny', 0, 0, 1)
        );

        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_accesscontrol'), $attrs, 'accessControl', 1);
    }

    protected function add_A_EXT_SEL($id)
    {
        $attrs = array($this->_attrs['ext_type']);
        $this->_tblDef[$id] = DTbl::NewSel($id, DMsg::ALbl('l_newextapp'), $attrs, $this->_options['extTbl']);
    }

    protected function add_T_EXT_SEL($id)
    {
        $attrs = array($this->_attrs['ext_type']);
        $this->_tblDef[$id] = DTbl::NewSel($id, DMsg::ALbl('l_newextapp'), $attrs, $this->_options['tp_extTbl']);
    }

    protected function add_A_EXT_TOP($id)
    {
        $align = array('left', 'left', 'left', 'center');

        $attrs = array(
            $this->_attrs['ext_type'],
            self::NewViewAttr('name', DMsg::ALbl('l_name')),
            self::NewViewAttr('address', DMsg::ALbl('l_address')),
            self::NewActionAttr($this->_options['extTbl'], 'vEd')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_extapps'), $attrs, 'name', 'A_EXT_SEL', $align, null, 'application', true);
    }

    protected function add_A_EXT_FCGI($id)
    {
        $attrs = array(
            $this->_attrs['ext_name'],
            $this->_attrs['ext_address'],
            $this->_attrs['note'],
            $this->_attrs['ext_maxConns'],
            $this->_attrs['ext_env'],
            $this->_attrs['ext_initTimeout'],
            $this->_attrs['ext_retryTimeout'],
            $this->_attrs['ext_persistConn'],
            $this->_attrs['pcKeepAliveTimeout'],
            $this->_attrs['ext_respBuffer'],
            $this->_attrs['ext_autoStart'],
            $this->_attrs['ext_path'],
            $this->_attrs['ext_backlog'],
            $this->_attrs['ext_instances'],
            $this->_attrs['ext_user'],
            $this->_attrs['ext_group'],
            $this->_attrs['cgiUmask'],
            $this->_attrs['ext_runOnStartUp'],
            self::NewIntAttr('extMaxIdleTime', DMsg::ALbl('l_maxidletime'), true, -1),
            $this->_attrs['priority']->dup(null, null, 'extAppPriority'),
            $this->_attrs['memSoftLimit'],
            $this->_attrs['memHardLimit'],
            $this->_attrs['procSoftLimit'],
            $this->_attrs['procHardLimit']
        );
        $defaultExtract = array('type' => 'fcgi');
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_fcgiapp'), $attrs, 'name', null, $defaultExtract);
    }

    protected function add_A_EXT_FCGIAUTH($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_FCGI', $id, DMsg::ALbl('l_extfcgiauth'));
        $this->_tblDef[$id]->Set(DTbl::FLD_DEFAULTEXTRACT, array('type' => 'fcgiauth'));
    }

    protected function add_A_EXT_LSAPI($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_FCGI', $id, DMsg::ALbl('l_extlsapi'));
        $this->_tblDef[$id]->Set(DTbl::FLD_DEFAULTEXTRACT, array('type' => 'lsapi'));
    }

    protected function add_A_EXT_LOADBALANCER($id)
    {
        $parseFormat = "/^(fcgi|fcgiauth|lsapi|servlet|proxy)::.+$/";
        $parseHelp = 'ExtAppType::ExtAppName, allowed types are fcgi, fcgiauth, lsapi, servlet and proxy. e.g. fcgi::myphp, servlet::tomcat';

        $attrs = array($this->_attrs['ext_name'],
            self::NewParseTextAreaAttr('workers', DMsg::ALbl('l_workers'), $parseFormat, $parseHelp, true, 3, 'extWorkers', 0, 0, 1),
            $this->_attrs['note'],
        );
        $defaultExtract = array('type' => 'loadbalancer');
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_extlb'), $attrs, 'name', null, $defaultExtract);
    }

    protected function add_A_EXT_LOGGER($id)
    {
        $attrs = array($this->_attrs['ext_name'],
            self::NewTextAttr('address', DMsg::ALbl('l_loggeraddress'), 'addr', true), //optional
            $this->_attrs['note'],
            $this->_attrs['ext_maxConns'],
            $this->_attrs['ext_env'],
            $this->_attrs['ext_path'],
            $this->_attrs['ext_instances'],
            $this->_attrs['ext_user'],
            $this->_attrs['ext_group'],
            $this->_attrs['cgiUmask'],
            $this->_attrs['priority']->dup(null, null, 'extAppPriority')
        );
        $defaultExtract = array('type' => 'logger');
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_extlogger'), $attrs, 'name', null, $defaultExtract);
    }

    protected function add_A_EXT_SERVLET($id)
    {
        $attrs = array($this->_attrs['ext_name'],
            $this->_attrs['ext_address'],
            $this->_attrs['note'],
            $this->_attrs['ext_maxConns'],
            $this->_attrs['pcKeepAliveTimeout'],
            $this->_attrs['ext_env'],
            $this->_attrs['ext_initTimeout'],
            $this->_attrs['ext_retryTimeout'],
            $this->_attrs['ext_respBuffer']
        );
        $defaultExtract = array('type' => 'servlet');
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_extservlet'), $attrs, 'name', null, $defaultExtract);
    }

    protected function add_A_EXT_PROXY($id)
    {
        $attrs = array($this->_attrs['ext_name'],
            self::NewTextAttr('address', DMsg::ALbl('l_address'), 'wsaddr', false, 'expWSAddress'),
            $this->_attrs['note'],
            $this->_attrs['ext_maxConns'],
            $this->_attrs['pcKeepAliveTimeout'],
            $this->_attrs['ext_env'],
            $this->_attrs['ext_initTimeout'],
            $this->_attrs['ext_retryTimeout'],
            $this->_attrs['ext_respBuffer']
        );
        $defaultExtract = array('type' => 'proxy');
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_extproxy'), $attrs, 'name', null, $defaultExtract);
    }

    protected function add_T_EXT_TOP($id)
    {
        $align = array('center', 'center', 'left', 'center');

        $attrs = array(
            $this->_attrs['ext_type'],
            self::NewViewAttr('name', DMsg::ALbl('l_name')),
            self::NewViewAttr('address', DMsg::ALbl('l_address')),
            self::NewActionAttr($this->_options['tp_extTbl'], 'vEd')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_extapps'), $attrs, 'name', 'T_EXT_SEL', $align, null, 'application', true);
    }

    protected function add_T_EXT_FCGI($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_FCGI', $id);
        $this->_tblDef[$id]->ResetAttrEntry(0, $this->_attrs['tp_name']);
    }

    protected function add_T_EXT_FCGIAUTH($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_FCGIAUTH', $id);
        $this->_tblDef[$id]->ResetAttrEntry(0, $this->_attrs['tp_name']);
    }

    protected function add_T_EXT_LSAPI($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_LSAPI', $id);
        $this->_tblDef[$id]->ResetAttrEntry(0, $this->_attrs['tp_name']);
    }

    protected function add_T_EXT_LOADBALANCER($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_LOADBALANCER', $id);
        $this->_tblDef[$id]->ResetAttrEntry(0, $this->_attrs['tp_name']);
    }

    protected function add_T_EXT_LOGGER($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_LOGGER', $id);
        $this->_tblDef[$id]->ResetAttrEntry(0, $this->_attrs['tp_name']);
    }

    protected function add_T_EXT_SERVLET($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_SERVLET', $id);
        $this->_tblDef[$id]->ResetAttrEntry(0, $this->_attrs['tp_name']);
    }

    protected function add_T_EXT_PROXY($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('A_EXT_PROXY', $id);
        $this->_tblDef[$id]->ResetAttrEntry(0, $this->_attrs['tp_name']);
    }

    protected function add_A_SCRIPT($id)
    {
        $attrs = array(
            $this->_attrs['suffix'],
            $this->_attrs['scriptHandler_type'],
            $this->_attrs['scriptHandler'],
            $this->_attrs['note'],
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_shdef'), $attrs, 'suffix');
    }

    protected function add_A_SCRIPT_TOP($id)
    {
        $align = array('center', 'center', 'center', 'center');

        $attrs = array(
            $this->_attrs['suffix'],
            $this->_attrs['scriptHandler_type'],
            $this->_attrs['scriptHandler'],
            self::NewActionAttr('A_SCRIPT', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_shdef'), $attrs, 'suffix', 'A_SCRIPT', $align, null, 'script');
    }

    protected function add_S_RAILS($id)
    {
        $attrs = array(
            self::NewPathAttr('rubyBin', DMsg::ALbl('l_rubybin'), 'file', 1, 'x'),
            self::NewPathAttr('wsgiBin', DMsg::ALbl('l_wsgibin'), 'file', 1, 'x'),
            self::NewPathAttr('nodeBin', DMsg::ALbl('l_nodebin'), 'file', 1, 'x'),
            $this->_attrs['appserverEnv'],
            $this->_attrs['ext_maxConns'],
            $this->_attrs['ext_env'],
            $this->_attrs['ext_initTimeout'],
            $this->_attrs['ext_retryTimeout'],
            $this->_attrs['pcKeepAliveTimeout'],
            $this->_attrs['ext_respBuffer'],
            $this->_attrs['ext_backlog'],
            $this->_attrs['ext_runOnStartUp'],
            self::NewIntAttr('extMaxIdleTime', DMsg::ALbl('l_maxidletime'), true, -1),
            $this->_attrs['priority']->dup(null, null, 'extAppPriority'),
            $this->_attrs['memSoftLimit'],
            $this->_attrs['memHardLimit'],
            $this->_attrs['procSoftLimit'],
            $this->_attrs['procHardLimit']
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_railssettings'), $attrs, 'railsDefault');
    }

    protected function add_V_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_name')),
            self::NewViewAttr('vhRoot', DMsg::ALbl('l_vhroot')),
            self::NewActionAttr('V_TOPD', 'Xd')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_vhostlist'), $attrs, 'name', 'V_TOPD', $align, null, 'web', true);
    }

    protected function add_V_BASE($id)
    {
        $attrs = array(
            self::NewTextAttr('name', DMsg::ALbl('l_vhname'), 'vhname', false, 'vhName'),
            self::NewTextAttr('vhRoot', DMsg::ALbl('l_vhroot'), 'cust', false), // do not check path for vhroot, it may be different owner
            self::NewPathAttr('configFile', DMsg::ALbl('l_configfile'), 'filevh', 3, 'rwc', false),
            $this->_attrs['note']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_base'), $attrs, 'name');
    }

    protected function add_V_BASE_CONN($id)
    {
        $attrs = array(
            $this->_attrs['vh_maxKeepAliveReq'],
            $this->_attrs['vh_smartKeepAlive']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_connection'), $attrs, 'name');
    }

    protected function add_V_BASE_THROTTLE($id)
    {
        $attrs = array(
            $this->_attrs['staticReqPerSec'],
            $this->_attrs['dynReqPerSec'],
            $this->_attrs['outBandwidth'],
            $this->_attrs['inBandwidth']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_perclientthrottle'), $attrs, 'name');
    }

    protected function add_L_TOP($id)
    {
        $align = array('center', 'center', 'center', 'center', 'center');

        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_listenername')),
            self::NewViewAttr('ip', DMsg::ALbl('l_ip')),
            self::NewViewAttr('port', DMsg::ALbl('l_port')),
            self::NewBoolAttr('secure', DMsg::ALbl('l_secure')),
            self::NewActionAttr('L_GENERAL', 'Xd')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_listenerlist'), $attrs, 'name', 'L_GENERAL', $align, null, 'link', true);
    }

    protected function add_ADM_L_TOP($id)
    {
        $align = array('center', 'center', 'center', 'center', 'center');

        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_listenername')),
            self::NewViewAttr('ip', DMsg::ALbl('l_ip')),
            self::NewViewAttr('port', DMsg::ALbl('l_port')),
            self::NewBoolAttr('secure', DMsg::ALbl('l_secure')),
            self::NewActionAttr('ADM_L_GENERAL', 'Xd', false)//cannot delete all
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_listenerlist'), $attrs, 'name', 'ADM_L_GENERAL', $align, null, 'link', true);
    }

    protected function add_ADM_L_GENERAL($id)
    {
        $name = self::NewTextAttr('name', DMsg::ALbl('l_listenername'), 'name', false, 'listenerName');
        $addr = self::NewCustFlagAttr('address', DMsg::ALbl('l_address'), (DAttr::BM_HIDE | DAttr::BM_NOEDIT), false);
        $ip = self::NewSelAttr('ip', DMsg::ALbl('l_ip'), $this->_options['ip'], false, 'listenerIP');
        $ip->SetFlag(DAttr::BM_NOFILE);
        $port = self::NewIntAttr('port', DMsg::ALbl('l_port'), false, 0, 65535, 'listenerPort');
        $port->SetFlag(DAttr::BM_NOFILE);

        $attrs = array(
            $name,
            $addr, $ip, $port,
            self::NewBoolAttr('secure', DMsg::ALbl('l_secure'), false, 'listenerSecure'),
            $this->_attrs['note'],
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_adminlistenersettings'), $attrs, 'name');
    }

    protected function add_L_VHMAP($id)
    {
        $attrs = array(
            $this->_attrs['l_vhost'],
            $this->_attrs['l_domain']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_vhmappings'), $attrs, 'vhost', 'virtualHostMapping');
    }

    protected function add_L_VHMAP_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            $this->_attrs['l_vhost'],
            $this->_attrs['l_domain'],
            self::NewActionAttr('L_VHMAP', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_vhmappings'), $attrs, 'vhost', 'L_VHMAP', $align, 'virtualHostMapping', 'web_link', false);
    }

    protected function add_LVT_SSL_CERT($id)
    {
        $attrs = array(
            self::NewTextAttr('keyFile', DMsg::ALbl('l_keyfile'), 'cust'),
            self::NewTextAttr('certFile', DMsg::ALbl('l_certfile'), 'cust'),
            self::NewBoolAttr('certChain', DMsg::ALbl('l_certchain')),
            self::NewTextAttr('CACertPath', DMsg::ALbl('l_cacertpath'), 'cust'),
            self::NewTextAttr('CACertFile', DMsg::ALbl('l_cacertfile'), 'cust'),
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_ssl'), $attrs, 'sslCert');
    }

    protected function add_LVT_SSL($id)
    {
        $attrs = array(
            self::NewCheckBoxAttr('sslProtocol', DMsg::ALbl('l_protocolver'), array('1' => 'SSL v3.0', '2' => 'TLS v1.0', '4' => 'TLS v1.1', '8' => 'TLS v1.2', '16' => 'TLS v1.3')),
            self::NewTextAttr('ciphers', DMsg::ALbl('l_ciphers'), 'cust'),
            self::NewBoolAttr('enableECDHE', DMsg::ALbl('l_enableecdhe')),
            self::NewBoolAttr('enableDHE', DMsg::ALbl('l_enabledhe')),
            self::NewTextAttr('DHParam', DMsg::ALbl('l_dhparam'), 'cust'),
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_sslprotocol'), $attrs);
    }

    protected function add_L_SSL_FEATURE($id)
    {
        $attrs = array(
            $this->_attrs['ssl_renegProtection'],
            $this->_attrs['sslSessionCache'],
            $this->_attrs['sslSessionTickets'],
            self::NewCheckBoxAttr('enableSpdy', DMsg::ALbl('l_enablespdy'), array('1' => 'SPDY/2', '2' => 'SPDY/3', '4' => 'HTTP/2', '0' => DMsg::ALbl('o_none')))
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_securityandfeatures'), $attrs);
    }

    protected function add_VT_SSL_FEATURE($id)
    {
        $attrs = array(
            $this->_attrs['ssl_renegProtection'],
            $this->_attrs['sslSessionCache'],
            $this->_attrs['sslSessionTickets'],
                );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::UIStr('tab_sec'), $attrs);
    }

    protected function add_LVT_SSL_OCSP($id)
    {
        $attrs = array(
            self::NewBoolAttr('enableStapling', DMsg::ALbl('l_enablestapling')),
            self::NewIntAttr('ocspRespMaxAge', DMsg::ALbl('l_ocsprespmaxage'), true, -1),
            self::NewTextAttr('ocspResponder', DMsg::ALbl('l_ocspresponder'), 'httpurl'),
            self::NewTextAttr('ocspCACerts', DMsg::ALbl('l_ocspcacerts'), 'cust'),
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_ocspstapling'), $attrs);
    }

    protected function add_T_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_name')),
            self::NewViewAttr('listeners', DMsg::ALbl('l_mappedlisteners')),
            self::NewActionAttr('T_TOPD', 'Xd')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_tplist'), $attrs, 'name', 'T_TOPD', $align, null, 'form', true);
    }

    protected function add_T_TOPD($id)
    {
        $attrs = array(
            self::NewTextAttr('name', DMsg::ALbl('l_tpname'), 'vhname', false, 'templateName'),
            $this->_attrs['tp_templateFile'],
            $this->_attrs['tp_listeners'],
            $this->_attrs['note']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_vhtemplate'), $attrs, 'name');
    }

    protected function add_T_MEMBER_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            $this->_attrs['tp_vhName'],
            $this->_attrs['tp_vhDomain'],
            self::NewActionAttr('T_MEMBER', 'vEdi')
        );

        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_membervhosts'), $attrs, 'vhName', 'T_MEMBER', $align, null, 'web', false);
    }

    protected function add_T_MEMBER($id)
    {
        $vhroot = self::NewTextAttr('vhRoot', DMsg::ALbl('l_membervhroot'), 'cust', true, 'memberVHRoot');
        $vhroot->_note = DMsg::ALbl('l_membervhroot_note');

        $attrs = array(
            $this->_attrs['tp_vhName'],
            $this->_attrs['tp_vhDomain'],
            $this->_attrs['tp_vhAliases'],
            $vhroot
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_membervhosts'), $attrs, 'vhName');
    }

    protected function add_V_GENERAL($id)
    {
        $attrs = array(
            self::NewTextAttr('docRoot', DMsg::ALbl('l_docroot'), 'cust', false), //no validation, maybe suexec owner
            $this->_attrs['tp_vhDomain'], // this setting is a new way, will merge with listener map settings for backward compatible
            $this->_attrs['tp_vhAliases'],
            $this->_attrs['adminEmails']->dup(null, null, 'vhadminEmails'),
            $this->_attrs['vh_enableGzip'],
            $this->_attrs['enableIpGeo'],
            $this->_attrs['vh_spdyAdHeader']
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::UIStr('tab_g'), $attrs);
    }

    protected function add_V_LOG($id)
    {
        $attrs = array(
            self::NewBoolAttr('useServer', DMsg::ALbl('l_useServer'), false, 'logUseServer'),
            $this->_attrs['fileName3']->dup(null, null, 'vhlog_fileName'),
            self::NewSelAttr('logLevel', DMsg::ALbl('l_loglevel'), $this->_options['logLevel'], true, 'vhlog_logLevel'),
            $this->_attrs['rollingSize']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_vhlog'), $attrs, 'fileName');
    }

    protected function add_V_ACLOG($id)
    {
        $attrs = array(
            self::NewSelAttr('useServer', DMsg::ALbl('l_logcontrol'), array(0 => DMsg::ALbl('o_ownlogfile'), 1 => DMsg::ALbl('o_serverslogfile'), 2 => DMsg::ALbl('o_disabled')), false, 'aclogUseServer'),
            $this->_attrs['fileName3']->dup(null, null, 'vhaccessLog_fileName'),
            self::NewSelAttr('pipedLogger', DMsg::ALbl('l_pipedlogger'), 'extprocessor:logger', true, 'accessLog_pipedLogger'),
            $this->_attrs['logFormat'],
            $this->_attrs['logHeaders'],
            $this->_attrs['rollingSize'],
            $this->_attrs['keepDays'],
            self::NewPathAttr('bytesLog', DMsg::ALbl('l_byteslog'), 'file0', 3, 'r', true, 'accessLog_bytesLog'),
            $this->_attrs['compressArchive']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_accesslog'), $attrs, 'fileName');
    }

    protected function add_VT_INDXF($id)
    {
        $attrs = array(
            self::NewSelAttr('useServer', DMsg::ALbl('l_useserverindexfiles'), array(0 => DMsg::ALbl('o_no'), 1 => DMsg::ALbl('o_yes'), 2 => 'Addition'), false, 'indexUseServer'),
            $this->_attrs['indexFiles'],
            $this->_attrs['autoIndex'],
            self::NewTextAttr('autoIndexURI', DMsg::ALbl('l_autoindexuri'), 'uri')
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_indexfiles'), $attrs);
    }

    protected function get_cust_status_code()
    {
        $status = array(
            300 => 'Multiple Choices',
            301 => 'Moved Permanently',
            302 => 'Found',
            303 => 'See Other',
            305 => 'Use Proxy',
            307 => 'Temporary Redirect',
            400 => 'Bad Request',
            401 => 'Unauthorized',
            402 => 'Payment Required',
            403 => 'Forbidden',
            404 => 'Not Found',
            405 => 'Method Not Allowed',
            406 => 'Not Acceptable',
            407 => 'Proxy Authentication Required',
            408 => 'Request Time-out',
            409 => 'Conflict',
            410 => 'Gone',
            411 => 'Length Required',
            412 => 'Precondition Failed',
            413 => 'Request Entity Too Large',
            414 => 'Request-URI Too Large',
            415 => 'Unsupported Media Type',
            416 => 'Requested range not satisfiable',
            417 => 'Expectation Failed',
            500 => 'Internal Server Error',
            501 => 'Not Implemented',
            502 => 'Bad Gateway',
            503 => 'Service Unavailable',
            504 => 'Gateway Time-out',
            505 => 'HTTP Version not supported'
        );
        $options = [];
        foreach ($status as $key => $value) {
            $options[$key] = "$key  $value";
        }

        return $options;
    }

    protected function add_VT_ERRPG_TOP($id)
    {
        $align = array('left', 'left', 'center');
        $errCodeOptions = $this->get_cust_status_code();
        $attrs = array(
            self::NewSelAttr('errCode', DMsg::ALbl('l_errcode'), $errCodeOptions, false),
            self::NewViewAttr('url', DMsg::ALbl('l_url')),
            self::NewActionAttr('VT_ERRPG', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_custerrpages'), $attrs, 'errCode', 'VT_ERRPG', $align, 'errPage', 'file', true);
    }

    protected function add_VT_ERRPG($id)
    {
        $attrs = array(
            self::NewSelAttr('errCode', DMsg::ALbl('l_errcode'), $this->get_cust_status_code(), false),
            self::NewTextAttr('url', DMsg::ALbl('l_url'), 'cust', false, 'errURL'),
            $this->_attrs['note'],
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_custerrpages'), $attrs, 'errCode', 'errPage');
    }

    protected function get_realm_attrs()
    {
        return array(
            'realm_type'             => self::NewSelAttr('type', DMsg::ALbl('l_realmtype'), $this->_options['realmType'], false, 'realmType'),
            'realm_name'             => self::NewTextAttr('name', DMsg::ALbl('l_realmname'), 'name', false, 'realmName'),
            'realm_udb_maxCacheSize' => self::NewIntAttr('userDB:maxCacheSize', DMsg::ALbl('l_userdbmaxcachesize'), true, 0, '100K', 'userDBMaxCacheSize'),
            'realm_udb_cacheTimeout' => self::NewIntAttr('userDB:cacheTimeout', DMsg::ALbl('l_userdbcachetimeout'), true, 0, 3600, 'userDBCacheTimeout'),
            'realm_gdb_maxCacheSize' => self::NewIntAttr('groupDB:maxCacheSize', DMsg::ALbl('l_groupdbmaxcachesize'), true, 0, '100K', 'groupDBMaxCacheSize'),
            'realm_gdb_cacheTimeout' => self::NewIntAttr('groupDB:cacheTimeout', DMsg::ALbl('l_groupdbcachetimeout'), true, 0, 3600, 'groupDBCacheTimeout'));
    }

    protected function add_V_REALM_FILE($id)
    {
        $udbLoc = self::NewPathAttr('userDB:location', DMsg::ALbl('l_userdblocation'), 'file', 3, 'rc', false, 'userDBLocation');
        $udbLoc->_href = '&t1=V_UDB_TOP&r1=$R';
        $gdbLoc = self::NewPathAttr('groupDB:location', DMsg::ALbl('l_groupdblocation'), 'file', 3, 'rc', true, 'GroupDBLocation');
        $gdbLoc->_href = '&t1=V_GDB_TOP&r1=$R';

        $realm_attr = $this->get_realm_attrs();
        $attrs = array(
            $realm_attr['realm_name'],
            $this->_attrs['note'],
            $udbLoc,
            $realm_attr['realm_udb_maxCacheSize'],
            $realm_attr['realm_udb_cacheTimeout'],
            $gdbLoc,
            $realm_attr['realm_gdb_maxCacheSize'],
            $realm_attr['realm_gdb_cacheTimeout']
        );
        $defaultExtract = array('type' => 'file');
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_passfilerealmdef'), $attrs, 'name', null, $defaultExtract);
    }

    protected function add_T_REALM_FILE($id)
    {
        $realm_attr = $this->get_realm_attrs();
        $attrs = array(
            $realm_attr['realm_name'],
            $this->_attrs['note'],
            self::NewTextAttr('userDB:location', DMsg::ALbl('l_userdblocation'), 'cust', false, 'userDBLocation'),
            $realm_attr['realm_udb_maxCacheSize'],
            $realm_attr['realm_udb_cacheTimeout'],
            self::NewTextAttr('groupDB:location', DMsg::ALbl('l_groupdblocation'), 'cust', true, 'GroupDBLocation'),
            $realm_attr['realm_gdb_maxCacheSize'],
            $realm_attr['realm_gdb_cacheTimeout']
        );
        $defaultExtract = array('type' => 'file');
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_passfilerealmdef'), $attrs, 'name', null, $defaultExtract);
    }

    protected function add_V_UDB_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_username')),
            self::NewViewAttr('group', DMsg::ALbl('l_groups')),
            self::NewActionAttr('V_UDB', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_userdbentries'), $attrs, 'name', 'V_UDB', $align, null, 'administrator', false);
        $this->_tblDef[$id]->Set(DTbl::FLD_SHOWPARENTREF, true);
    }

    protected function add_V_UDB($id)
    {
        $attrs = array(
            self::NewTextAttr('name', DMsg::ALbl('l_username'), 'name', false),
            self::NewTextAttr('group', DMsg::ALbl('l_groups'), 'name', true, 'UDBgroup', 1),
            self::NewPassAttr('pass', DMsg::ALbl('l_newpass')),
            self::NewPassAttr('pass1', DMsg::ALbl('l_retypepass'))
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_userdbentry'), $attrs, 'name');
        $this->_tblDef[$id]->Set(DTbl::FLD_SHOWPARENTREF, true);
    }

    protected function add_V_GDB_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_groupname')),
            self::NewViewAttr('users', DMsg::ALbl('l_users')),
            self::NewActionAttr('V_GDB', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_groupdbentries'), $attrs, 'name', 'V_GDB', $align);
        $this->_tblDef[$id]->Set(DTbl::FLD_SHOWPARENTREF, true);
    }

    protected function add_V_GDB($id)
    {
        $users = self::NewTextAreaAttr('users', DMsg::ALbl('l_users'), 'name', true, 15, null, 0, 0, 1);
        $users->SetGlue(' ');

        $attrs = array(
            self::NewTextAttr('name', DMsg::ALbl('l_groupname'), 'name', false),
            $users,
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_groupdbentry'), $attrs, 'name');
        $this->_tblDef[$id]->Set(DTbl::FLD_SHOWPARENTREF, true);
    }

    protected function add_VT_REWRITE_CTRL($id)
    {
        $attrs = array(
            self::NewBoolAttr('enable', DMsg::ALbl('l_enablerewrite'), true, 'enableRewrite'),
            self::NewIntAttr('logLevel', DMsg::ALbl('l_loglevel'), true, 0, 9, 'rewriteLogLevel')
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_rewritecontrol'), $attrs);
    }

    protected function add_VT_REWRITE_MAP_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_name')),
            self::NewViewAttr('location', DMsg::ALbl('l_location')),
            self::NewActionAttr('VT_REWRITE_MAP', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_rewritemap'), $attrs, 'name', 'VT_REWRITE_MAP', $align, null, 'redirect', true);
    }

    protected function add_VT_REWRITE_MAP($id)
    {
        $parseFormat = "/^((txt|rnd):\/*)|(int:(toupper|tolower|escape|unescape))$/";

        $attrs = array(
            self::NewTextAttr('name', DMsg::ALbl('l_name'), 'name', false, 'rewriteMapName'),
            self::NewParseTextAttr('location', DMsg::ALbl('l_location'), $parseFormat, DMsg::ALbl('parse_rewritemaplocation'), true, 'rewriteMapLocation'),
            $this->_attrs['note'],
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_rewritemap'), $attrs, 'name');
    }

    protected function add_VT_REWRITE_RULE($id)
    {
        $attrs = array(
            self::NewTextAreaAttr('rules', null, 'cust', true, 15, null, 1, 1)
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_rewriterules'), $attrs, 'rewriteRules', 1);
    }

    protected function add_VT_CTX_SEL($id)
    {
        $attrs = array($this->_attrs['ctx_type']);
        $this->_tblDef[$id] = DTbl::NewSel($id, DMsg::ALbl('l_newcontext'), $attrs, $this->_options['ctxTbl']);
    }

    protected function get_ctx_attrs($type)
    {
        if ($type == 'auth') {
            return array(
                self::NewSelAttr('realm', DMsg::ALbl('l_realm'), 'realm'),
                self::NewTextAttr('authName', DMsg::ALbl('l_authname'), 'name'),
                self::NewTextAttr('required', DMsg::ALbl('l_requiredauthuser'), 'cust'),
                self::NewTextAreaAttr('accessControl:allow', DMsg::ALbl('l_accessallowed'), 'subnet', true, 3, 'accessAllowed', 0, 0, 1),
                self::NewTextAreaAttr('accessControl:deny', DMsg::ALbl('l_accessdenied'), 'subnet', true, 3, 'accessDenied', 0, 0, 1),
                self::NewSelAttr('authorizer', DMsg::ALbl('l_authorizer'), 'extprocessor:fcgiauth', true, 'extAuthorizer')
            );
        }
        if ($type == 'rewrite') {
            $rules = self::NewTextAreaAttr('rewrite:rules', DMsg::ALbl('l_rewriterules'), 'cust', true, 6, 'rewriteRules', 1, 1);
            $rules->SetFlag(DAttr::BM_RAWDATA);
            return array(
                self::NewBoolAttr('rewrite:enable', DMsg::ALbl('l_enablerewrite'), true, 'enableRewrite'),
                self::NewBoolAttr('rewrite:inherit', DMsg::ALbl('l_rewriteinherit'), true, 'rewriteInherit'),
                self::NewTextAttr('rewrite:base', DMsg::ALbl('l_rewritebase'), 'uri', true, 'rewriteBase'),
                $rules,
            );
        }
        if ($type == 'charset') {
            return array(// todo: merge below
                self::NewSelAttr('addDefaultCharset', DMsg::ALbl('l_adddefaultcharset'), array('off' => 'Off', 'on' => 'On')),
                self::NewTextAttr('defaultCharsetCustomized', DMsg::ALbl('l_defaultcharsetcustomized'), 'cust'),
                $this->_attrs['enableIpGeo']
            );
        }
        if ($type == 'uri') {
            return array(
                $this->_attrs['ctx_uri'],
                $this->_attrs['ctx_order']);
        }
    }

    protected function add_VT_WBSOCK_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            self::NewViewAttr('uri', DMsg::ALbl('l_uri')),
            self::NewViewAttr('address', DMsg::ALbl('l_address')),
            self::NewActionAttr('VT_WBSOCK', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_websocketsetup'), $attrs, 'uri', 'VT_WBSOCK', $align, null, 'web_link', true);
    }

    protected function add_VT_WBSOCK($id)
    {
        $attrs = array(
            $this->_attrs['ctx_uri']->dup(null, null, 'wsuri'),
            $this->_attrs['ext_address']->dup(null, null, 'wsaddr'),
            $this->_attrs['note'],
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_websocketdef'), $attrs, 'uri');
    }

    protected function add_T_GENERAL1($id)
    {
        $attrs = array(
            $this->_attrs['tp_vhRoot'],
            self::NewParseTextAttr('configFile', DMsg::ALbl('l_configfile'), '/\$VH_NAME.+\.conf$/', DMsg::ALbl('parse_tpvhconffile'), false, 'templateVHConfigFile'),
            $this->_attrs['vh_maxKeepAliveReq'],
            $this->_attrs['vh_smartKeepAlive']
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, 'Base', $attrs); // todo: title change
    }

    protected function add_T_GENERAL2($id)
    {
        $attrs = array(
            $this->_attrs['tp_vrFile']->dup('docRoot', DMsg::ALbl('l_docroot'), 'templateVHDocRoot'),
            $this->_attrs['adminEmails']->dup(null, null, 'vhadminEmails'),
            $this->_attrs['vh_enableGzip'],
            $this->_attrs['enableIpGeo'],
            $this->_attrs['vh_spdyAdHeader']
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_base2'), $attrs);
    }

    protected function add_T_SEC_FILE($id)
    {
        $attrs = array(
            $this->_attrs['vh_allowSymbolLink'],
            $this->_attrs['vh_enableScript'],
            $this->_attrs['vh_restrained']
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_fileaccesscontrol'), $attrs);
    }

    protected function add_T_SEC_CONN($id)
    {
        $attrs = array(
            $this->_attrs['staticReqPerSec'],
            $this->_attrs['dynReqPerSec'],
            $this->_attrs['outBandwidth'],
            $this->_attrs['inBandwidth']
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_perclientthrottle'), $attrs);
    }

    protected function add_T_LOG($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('V_LOG', $id);
        $this->_tblDef[$id]->ResetAttrEntry(1, $this->_attrs['tp_vrFile']);
    }

    protected function add_T_ACLOG($id)
    {
        $this->_tblDef[$id] = $this->DupTblDef('V_ACLOG', $id);
        $this->_tblDef[$id]->ResetAttrEntry(1, $this->_attrs['tp_vrFile']);
    }

    protected function add_ADM_PHP($id)
    {
        $attrs = array(
            self::NewBoolAttr('enableCoreDump', DMsg::ALbl('l_enablecoredump'), false),
            self::NewIntAttr('sessionTimeout', DMsg::ALbl('l_sessiontimeout'), true, 60, null, 'consoleSessionTimeout')
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::UIStr('tab_g'), $attrs);
    }

    protected function add_ADM_USR_TOP($id)
    {
        $align = array('left', 'center');
        $attrs = array(
            self::NewViewAttr('name', DMsg::ALbl('l_username')),
            self::NewActionAttr('ADM_USR', 'Ed', false) //not allow null - cannot delete all
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_adminusers'), $attrs, 'name', 'ADM_USR_NEW', $align, null, 'administrator');
    }

    protected function add_ADM_USR($id)
    {
        $attrs = array(
            self::NewTextAttr('name', DMsg::ALbl('l_username'), 'name', false),
            self::NewPassAttr('oldpass', DMsg::ALbl('l_oldpass'), false, 'adminOldPass'),
            self::NewPassAttr('pass', DMsg::ALbl('l_newpass'), false),
            self::NewPassAttr('pass1', DMsg::ALbl('l_retypepass'), false)
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_adminuser'), $attrs, 'name');
    }

    protected function add_ADM_USR_NEW($id)
    {
        $attrs = array(
            self::NewTextAttr('name', DMsg::ALbl('l_username'), 'name', false),
            self::NewPassAttr('pass', DMsg::ALbl('l_newpass'), false),
            self::NewPassAttr('pass1', DMsg::ALbl('l_retypepass'), false)
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_newadminuser'), $attrs, 'name');
    }

    protected function add_ADM_ACLOG($id)
    {
        $attrs = array(
            self::NewSelAttr('useServer', DMsg::ALbl('l_logcontrol'), array(0 => DMsg::ALbl('o_ownlogfile'), 1 => DMsg::ALbl('o_serverslogfile'), 2 => DMsg::ALbl('o_disabled')), false, 'aclogUseServer'),
            $this->_attrs['fileName3']->dup(null, null, 'accessLog_fileName'),
            $this->_attrs['logFormat'],
            $this->_attrs['logHeaders'],
            $this->_attrs['rollingSize'],
            $this->_attrs['keepDays'],
            self::NewPathAttr('bytesLog', DMsg::ALbl('l_byteslog'), 'file0', 3, 'r', true, 'accessLog_bytesLog'),
            $this->_attrs['compressArchive']
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_accesslog'), $attrs, 'fileName');
    }

    protected function add_S_MIME_TOP($id)
    {
        $align = array('left', 'left', 'center');

        $attrs = array(
            self::NewViewAttr('suffix', DMsg::ALbl('l_suffix')),
            self::NewViewAttr('type', DMsg::ALbl('l_mimetype')),
            self::NewActionAttr('S_MIME', 'Ed')
        );
        $this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_mimetypedef'), $attrs, 'suffix', 'S_MIME', $align, null, 'file');
    }

    protected function add_S_MIME($id)
    {
        $attrs = array(
            $this->_attrs['suffix']->dup('suffix', DMsg::ALbl('l_suffix'), 'mimesuffix'),
            self::NewParseTextAttr('type', DMsg::ALbl('l_mimetype'), "/^[A-z0-9_\-\.\+]+\/[A-z0-9_\-\.\+]+(\s*;?.*)$/", DMsg::ALbl('parse_mimetype'), false, 'mimetype')
        );
        $this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_mimetypeentry'), $attrs, 'suffix');
    }

    protected function add_SERVICE_SUSPENDVH($id)
    {
        $attrs = array(self::NewCustFlagAttr('suspendedVhosts', null, (DAttr::BM_HIDE | DAttr::BM_NOEDIT), true, 'vhname', null, null, 1)
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_suspendvh'), $attrs);
    }

}
