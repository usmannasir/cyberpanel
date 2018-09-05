<?php

class DTblDef extends DTblDefBase
{
	public static function getInstance()
	{
        if ( !isset($GLOBALS['_DTblDef_']) )
			$GLOBALS['_DTblDef_'] = new DTblDef();
		return $GLOBALS['_DTblDef_'];
	}

	private function __construct()
	{
		$this->loadCommonOptions();
		$this->loadCommonAttrs();
        $this->loadSpecials();
	}

    protected function loadSpecials()
    {
        // define special block contains raw data
        parent::loadSpecials();

        $this->addSpecial('phpIniOverride', [], 'data');

        $tags = array_merge(['ls_enabled', 'note', 'internal', 'urlFilter'], $this->getModuleTags());
        $this->addSpecial('module', $tags, 'param');

        $this->addSpecial('urlFilter', ['ls_enabled'], 'param');
    }

	protected function loadCommonOptions()
	{
		parent::loadCommonOptions();
		$this->_options['scriptHandler'] = array(
				'fcgi'=>'Fast CGI', 'servlet'=>'Servlet Engine',
				'lsapi'=>'LiteSpeed SAPI',
				'proxy'=>'Web Server', 'cgi'=>'CGI',
				'loadbalancer'=>'Load Balancer', 'module'=>'Module Handler' );

		$this->_options['ctxType'] = array(
				'null'=>'Static', 'webapp'=>'Java Web App',
				'servlet'=>'Servlet', 'fcgi'=>'Fast CGI',
				'lsapi'=>'LiteSpeed SAPI',
				'proxy'=>'Proxy', 'cgi'=>'CGI',
				'loadbalancer'=> 'Load Balancer',
				'redirect'=>'Redirect',
				'appserver'=>'App Server', 'module'=>'Module Handler');

		$this->_options['ctxTbl'] = array(
				0=>'type', 1=>'VT_CTXG',
				'null'=>'VT_CTXG', 'webapp'=>'VT_CTXJ',
				'servlet'=>'VT_CTXS', 'fcgi'=>'VT_CTXF',
				'lsapi'=>'VT_CTXL',
				'proxy'=>'VT_CTXP', 'cgi'=>'VT_CTXC',
				'loadbalancer'=>'VT_CTXB',
				'redirect'=>'VT_CTXR',
				'appserver'=>'VT_CTXAS',
				'module'=>'VT_CTXMD');

		$this->_options['realmType'] = array('file' => 'Password File');
	}

	protected function loadCommonAttrs()
	{
		parent::loadCommonAttrs();
        $param = self::NewTextAreaAttr('param', DMsg::ALbl('l_moduleparams'), 'cust', true, 4, 'modParams', 1, 1);
        $param->SetFlag(DAttr::BM_RAWDATA);
		$this->_attrs['mod_params'] = $param;
		$this->_attrs['mod_enabled'] = self::NewBoolAttr('ls_enabled', DMsg::ALbl('l_enablehooks'), true, 'moduleEnabled');
	}

	protected function add_S_PROCESS($id) //keep
	{
		$attrs = array(
				self::NewTextAttr('serverName', DMsg::ALbl('l_servername'), 'name', false),
				self::NewIntAttr('httpdWorkers', DMsg::ALbl('l_numworkers'), true, 1, 16),
				self::NewCustFlagAttr('runningAs', DMsg::ALbl('l_runningas'), (DAttr::BM_NOFILE | DAttr::BM_NOEDIT)),
				self::NewCustFlagAttr('user', null, (DAttr::BM_HIDE | DAttr::BM_NOEDIT), false),
				self::NewCustFlagAttr('group', null, (DAttr::BM_HIDE | DAttr::BM_NOEDIT), false),
				$this->_attrs['priority']->dup(null, null, 'serverPriority'),
				self::NewIntAttr('inMemBufSize', DMsg::ALbl('l_inmembufsize'), false, 0),
				self::NewTextAttr('swappingDir', DMsg::ALbl('l_swappingdir'), 'cust', false),
				self::NewBoolAttr('autoFix503', DMsg::ALbl('l_autofix503')),
                self::NewBoolAttr('enableh2c', DMsg::ALbl('l_enableh2c')),
				self::NewIntAttr('gracefulRestartTimeout', DMsg::ALbl('l_gracefulrestarttimeout'), true, -1, 2592000),
				self::NewTextAttr('statDir', DMsg::ALbl('l_statDir'), 'cust')
		);
		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_serverprocess'), $attrs);
	}

	protected function add_S_GENERAL($id) // keep
	{
		$attr_mime = self::NewPathAttr('mime', DMsg::ALbl('l_mimesettings'), 'file', 2, 'rw', false);
		$attr_mime->_href = '&t=S_MIME_TOP';

		$attrs = array(
				$attr_mime,
				self::NewBoolAttr('disableInitLogRotation', DMsg::ALbl('l_disableinitlogrotation')),
				self::NewSelAttr('showVersionNumber', DMsg::ALbl('l_serversig'),
						array('0'=>DMsg::ALbl('o_hidever'), '1'=>DMsg::ALbl('o_showver'), '2'=>DMsg::ALbl('o_hidefullheader')), false),
				$this->_attrs['enableIpGeo'],
				self::NewSelAttr('useIpInProxyHeader', DMsg::ALbl('l_useipinproxyheader'),
						array('0'=>DMsg::ALbl('o_no'), '1'=>DMsg::ALbl('o_yes'), '2'=>DMsg::ALbl('o_trustediponly')) ),
				$this->_attrs['adminEmails'],
				self::NewCustFlagAttr('adminRoot', null, (DAttr::BM_HIDE | DAttr::BM_NOEDIT), false)
		);
		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_generalsettings'), $attrs);
	}

    protected function add_S_FILEUPLOAD($id)
    {
		$attrs = array(
            self::NewPathAttr('uploadTmpDir', DMsg::ALbl('l_uploadtmpdir'), 'path', 2),
            self::NewParseTextAttr('uploadTmpFilePermission', DMsg::ALbl('l_uploadtmpfilepermission'), $this->_options['parseFormat']['filePermission3'], DMsg::ALbl('parse_uploadtmpfilepermission')),
            self::NewBoolAttr('uploadPassByPath', DMsg::ALbl('l_uploadpassbypath'))
		);
		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_uploadfile'), $attrs, 'fileUpload');
    }

    protected function add_VT_FILEUPLOAD($id)
    {
		$attrs = array(
            self::NewPathAttr('uploadTmpDir', DMsg::ALbl('l_uploadtmpdir'), 'path', 3),
            self::NewParseTextAttr('uploadTmpFilePermission', DMsg::ALbl('l_uploadtmpfilepermission'), $this->_options['parseFormat']['filePermission3'], DMsg::ALbl('parse_uploadtmpfilepermission')),
            self::NewBoolAttr('uploadPassByPath', DMsg::ALbl('l_uploadpassbypath'))
		);
		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_uploadfile'), $attrs, 'fileUpload');
    }

    protected function add_VT_PHPINIOVERRIDE($id)
    {
        $override =  self::NewTextAreaAttr('data', null, 'cust', true, 6, null, 1, 1);
        $override->SetFlag(DAttr::BM_RAWDATA);
        $attrs = array(
           $override,
        );
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_phpinioverride'), $attrs, 'phpIniOverride', 1);
    }

	protected function add_S_TUNING_OS($id) //keep
	{
		$edoptions = array( 'best'    => 'best (All platforms)',
				    'poll'    => 'poll (All platforms)',
				    'epoll'   => 'epoll (Linux 2.6 kernel)',
				    'kqueue'  => 'kqueue (FreeBSD/Mac OS X)',
				    'devpoll' => 'devpoll (Solaris)');

		$attrs = array(
			self::NewSelAttr('eventDispatcher', DMsg::ALbl('l_ioeventdispatcher'), $edoptions),
            self::NewTextAttr('shmDefaultDir', DMsg::ALbl('l_shmDefaultDir'), 'cust'),
			);

		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_tuningos'), $attrs);
	}

	protected function add_S_TUNING_STATIC($id)
	{
		$attrs = array(
				self::NewIntAttr('maxCachedFileSize', DMsg::ALbl('l_maxcachedfilesize'), false, 0, 1048576),
				self::NewIntAttr('totalInMemCacheSize', DMsg::ALbl('l_totalinmemcachesize'), false, 0),
				self::NewIntAttr('maxMMapFileSize', DMsg::ALbl('l_maxmmapfilesize'), false, 0),
				self::NewIntAttr('totalMMapCacheSize', DMsg::ALbl('l_totalmmapcachesize'), false, 0),
				self::NewBoolAttr('useSendfile', DMsg::ALbl('l_usesendfile')),
				self::NewCheckBoxAttr('fileETag', DMsg::ALbl('l_fileetag'),
						array( '4'=>'iNode', '8'=>DMsg::ALbl('o_modifiedtime'), '16'=>DMsg::ALbl('o_size'), '0'=>DMsg::ALbl('o_none')), true, null, 28),
			);

		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_tuningstatic'), $attrs);
	}

	protected function add_S_TUNING_SSL($id)
	{
		$ssloptions = array( 'null' => DMsg::ALbl('l_ssloptnull'),
			 'auto' => DMsg::ALbl('l_ssloptauto'),
			 'dynamic'=> DMsg::ALbl('l_ssloptdynamic'),
			 'cswift' => DMsg::ALbl('l_ssloptcswift'),
			 'chil' => DMsg::ALbl('l_ssloptchil'),
			 'atalla' => DMsg::ALbl('l_ssloptatalla'),
			 'nuron' => DMsg::ALbl('l_ssloptnuron'),
			 'ubsec' => DMsg::ALbl('l_ssloptubsec'),
			 'aep' => DMsg::ALbl('l_ssloptaep'),
			 'sureware' => DMsg::ALbl('l_ssloptsureware'),
			 '4758cca' => DMsg::ALbl('l_sslopt4758cca') );

		$attrs = array(
			self::NewBoolAttr('SSLStrongDhKey', DMsg::ALbl('l_SSLStrongDhKey')),
			self::NewBoolAttr('sslEnableMultiCerts', DMsg::ALbl('l_sslEnableMultiCerts')),
			self::NewSelAttr('SSLCryptoDevice', DMsg::ALbl('l_sslcryptodevice'), $ssloptions),
            $this->_attrs['sslSessionCache'],
            self::NewIntAttr('sslSessionCacheSize', DMsg::ALbl('l_sslSessionCacheSize'), true, 512),
            self::NewIntAttr('sslSessionCacheTimeout', DMsg::ALbl('l_sslSessionCacheTimeout'), true, 10, 1000000),
            $this->_attrs['sslSessionTickets'],
            self::NewIntAttr('sslSessionTicketLifetime', DMsg::ALbl('l_sslSessionTicketLifetime'), true, 10, 1000000),
            self::NewTextAttr('sslSessionTicketKeyFile', DMsg::ALbl('l_sslSessionTicketKeyFile'), 'cust')
			);
        $this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_tuningsslsettings'), $attrs, 'sslGlobal');
	}

	protected function add_S_MOD_TOP($id)
	{
		$align = array('center', 'center', 'center', 'center');

		$attrs = array(self::NewViewAttr('name', DMsg::ALbl('l_module')),
				//self::NewBoolAttr('internal', DMsg::ALbl('l_internal'), true, 'internalmodule'),
				$this->_attrs['mod_params'],
				$this->_attrs['mod_enabled'],
				self::NewActionAttr('S_MOD', 'vEd')
		);
		$this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_servermodulesdef'), $attrs, 'name', 'S_MOD', $align, null, 'module', TRUE);
	}

    protected function getModuleTags()
    {
		$tags = ['L4_BEGINSESSION','L4_ENDSESSION','L4_RECVING','L4_SENDING',
				'HTTP_BEGIN','RECV_REQ_HEADER','URI_MAP','HTTP_AUTH',
				'RECV_REQ_BODY','RCVD_REQ_BODY','RECV_RESP_HEADER','RECV_RESP_BODY','RCVD_RESP_BODY',
				'HANDLER_RESTART','SEND_RESP_HEADER','SEND_RESP_BODY','HTTP_END',
				'MAIN_INITED','MAIN_PREFORK','MAIN_POSTFORK','WORKER_POSTFORK','WORKER_ATEXIT','MAIN_ATEXIT'];
        return $tags;
    }

	protected function add_S_MOD($id)
	{
		$attrs = array(self::NewTextAttr('name', DMsg::ALbl('l_module'), 'modulename', false, 'modulename'),
						$this->_attrs['note'],
						//self::NewBoolAttr('internal', DMsg::ALbl('l_internal'), true, 'internalmodule'),
						$this->_attrs['mod_params'],
						$this->_attrs['mod_enabled']);

        $tags = $this->getModuleTags();

		$hook = DMsg::ALbl('l_hook');
		$priority = DMsg::ALbl('l_priority');
		foreach($tags as $tag) {
			$attrs[] = self::NewIntAttr($tag, "$hook $tag $priority", true, -6000, 6000);
		}
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_servermoduledef'), $attrs, 'name', 'servModules');
	}

	protected function add_VT_MOD_TOP($id)
	{
		$align = array('center', 'center', 'center', 'center');

		$attrs = array(self::NewViewAttr('name', DMsg::ALbl('l_module')),
					$this->_attrs['mod_params'],
					$this->_attrs['mod_enabled']->dup(null, null, 'moduleEnabled_vh'),
					self::NewActionAttr('VT_MOD', 'vEd')
		);
		$this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_moduleconf'), $attrs, 'name', 'VT_MOD', $align, 'vhModules', 'module', TRUE);
	}

	protected function add_VT_MOD($id)
	{
		$attrs = array(self::NewSelAttr('name', DMsg::ALbl('l_module'), 'module', false, 'moduleNameSel'),
						$this->_attrs['note'],
						$this->_attrs['mod_params'],
						$this->_attrs['mod_enabled']->dup(null, null, 'moduleEnabled_vh')
		);

		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_moduleconf'), $attrs, 'name', 'vhModules');
		$this->_tblDef[$id]->Set(DTbl::FLD_LINKEDTBL, array('VT_MOD_FILTERTOP'));
	}

	protected function add_VT_MOD_FILTERTOP($id)
	{
		$align = array('center', 'center', 'center', 'center');

		$attrs = array( self::NewViewAttr('uri', DMsg::ALbl('l_uri')),
						$this->_attrs['mod_params'],
						$this->_attrs['mod_enabled']->dup(null, null, 'moduleEnabled_vh'),
				self::NewActionAttr('VT_MOD_FILTER', 'vEd')
		);

		$this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_urlfilter'), $attrs, 'uri', 'VT_MOD_FILTER', $align, 'vhModuleUrlFilters', 'filter', FALSE);
		$this->_tblDef[$id]->Set(Dtbl::FLD_SHOWPARENTREF, true);
	}

	protected function add_VT_MOD_FILTER($id)
	{
		$attrs = array($this->_attrs['ctx_uri'],
					$this->_attrs['mod_params'],
					$this->_attrs['mod_enabled']->dup(null, null, 'moduleEnabled_vh')
		);

		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_urlfilter'), $attrs, 'uri', 'vhModuleUrlFilters');
		$this->_tblDef[$id]->Set(Dtbl::FLD_SHOWPARENTREF, true);
	}

	protected function add_L_MOD_TOP($id)
	{
		$align = array('center', 'center', 'center', 'center');

		$attrs = array( self::NewViewAttr('name', DMsg::ALbl('l_module')),
						$this->_attrs['mod_params'],
						$this->_attrs['mod_enabled']->dup(null, null, 'moduleEnabled_lst'),
						self::NewActionAttr('L_MOD', 'vEd')
		);
		$this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_moduleconf'), $attrs, 'name', 'L_MOD', $align, 'listenerModules', 'module', TRUE);
	}

	protected function add_L_MOD($id)
	{
		$attrs = array(self::NewSelAttr('name', DMsg::ALbl('l_module'), 'module', false, 'moduleNameSel'),
						$this->_attrs['note'],
						$this->_attrs['mod_params'],
						$this->_attrs['mod_enabled']->dup(null, null, 'moduleEnabled_lst')
		);
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_moduleconf'), $attrs, 'name', 'listenerModules');
	}

	protected function add_V_TOPD($id)
	{
		$attrs = array(
			self::NewTextAttr('name', DMsg::ALbl('l_vhname'), 'vhname', false, 'vhName'),
			self::NewTextAttr('vhRoot', DMsg::ALbl('l_vhroot'), 'cust', false),//no validation, maybe suexec owner
			self::NewPathAttr('configFile', DMsg::ALbl('l_configfile'), 'filevh', 3, 'rwc', false),
			$this->_attrs['note'],
			$this->_attrs['vh_allowSymbolLink'],
			$this->_attrs['vh_enableScript'],
			$this->_attrs['vh_restrained'],
			$this->_attrs['vh_maxKeepAliveReq'],
			$this->_attrs['vh_smartKeepAlive'],
			$this->_attrs['vh_setUIDMode'],
			$this->_attrs['staticReqPerSec'],
			$this->_attrs['dynReqPerSec'],
			$this->_attrs['outBandwidth'],
			$this->_attrs['inBandwidth'],
			);
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_vhost'), $attrs, 'name');
	}

	protected function add_V_BASE_SEC($id)
	{
		$attrs = array(
			$this->_attrs['vh_allowSymbolLink'],
			$this->_attrs['vh_enableScript'],
			$this->_attrs['vh_restrained'],
			$this->_attrs['vh_setUIDMode']
			);
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::UIStr('tab_sec'), $attrs, 'name');
	}

	protected function add_V_REALM_TOP($id)
	{
		$align = array('center', 'center', 'center');
		$realm_attr = $this->get_realm_attrs();

		$attrs = array(
			$realm_attr['realm_name'],
			self::NewViewAttr('userDB:location', DMsg::ALbl('l_userdblocation'), 'userDBLocation'),
			self::NewActionAttr('V_REALM_FILE', 'vEd')
		);
		$this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_realmlist'), $attrs, 'name', 'V_REALM_FILE', $align, 'realms', 'shield', TRUE);
	}

	protected function add_T_REALM_TOP($id)
	{
		$align = array('center', 'center', 'center');
		$realm_attr = $this->get_realm_attrs();

		$attrs = array(
				$realm_attr['realm_name'],
				self::NewViewAttr('userDB:location', DMsg::ALbl('l_userdblocation'), 'userDBLocation'),
				self::NewActionAttr('T_REALM_FILE', 'vEd')
		);
		$this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_realmlist'), $attrs, 'name', 'T_REALM_FILE', $align, 'realms', 'shield', TRUE);
	}

	protected function add_VT_CTX_TOP($id)
	{
		$align = array('center', 'left', 'center', 'center');

		$attrs = array(
				$this->_attrs['ctx_type'],
				self::NewViewAttr('uri', DMsg::ALbl('l_uri')),
				self::NewCustFlagAttr('order', DMsg::ALbl('l_order'), (DAttr::BM_NOFILE | DAttr::BM_NOEDIT), true, 'ctxseq'),
				self::NewActionAttr($this->_options['ctxTbl'], 'vEd')
		);
		$this->_tblDef[$id] = DTbl::NewTop($id, DMsg::ALbl('l_contextlist'), $attrs, 'uri', 'VT_CTX_SEL', $align, null,
				array('null' => 'file', 'proxy' => 'network', 'redirect' => 'redirect', 'module'=>'module'), TRUE);
	}

	protected function add_VT_CTXG($id)
	{
        $override =  self::NewTextAreaAttr('phpIniOverride:data', DMsg::ALbl('l_phpinioverride'), 'cust', true, 6, 'phpIniOverride', 1, 1);
        $override->SetFlag(DAttr::BM_RAWDATA);

		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						$this->_attrs['ctx_location'],
						self::NewBoolAttr('allowBrowse', DMsg::ALbl('l_allowbrowse'), false),
						$this->_attrs['note']),
				$this->get_expires_attrs(),
				array(
						$this->_attrs['extraHeaders'],
						self::NewParseTextAreaAttr('addMIMEType', DMsg::ALbl('l_mimetype'),
						  "/[A-z0-9_\-\.\+]+\/[A-z0-9_\-\.\+]+(\s+[A-z0-9_\-\+]+)+/", DMsg::ALbl('parse_mimetype'),
						  true, 2, null, 0, 0, 1),
						self::NewParseTextAttr('forceType', DMsg::ALbl('l_forcemimetype'),
						  "/^([A-z0-9_\-\.\+]+\/[A-z0-9_\-\.\+]+)|(NONE)$/i", DMsg::ALbl('parse_forcemimetype')),
						self::NewParseTextAttr('defaultType', DMsg::ALbl('l_defaultmimetype'),
						  "/^[A-z0-9_\-\.\+]+\/[A-z0-9_\-\.\+]+$/", DMsg::ALbl('parse_defaultmimetype')),
						$this->_attrs['indexFiles'],
						$this->_attrs['autoIndex']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('rewrite'),
				$this->get_ctx_attrs('charset'),
                array(
                    $override,
                )
        );
		$defaultExtract = array('type'=>'null');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxg'), $attrs, 'uri', 'generalContext', $defaultExtract);
	}

	protected function add_VT_CTXJ($id)
	{
		$attrs = array_merge(
				array(
						self::NewTextAttr('uri', DMsg::ALbl('l_uri'), 'uri', false),
						$this->_attrs['ctx_order'],
						$this->_attrs['ctx_location']->dup(null, null, 'javaWebApp_location'),
						$this->_attrs['ctx_shandler'],
						$this->_attrs['note']),
				$this->get_expires_attrs(),
				array(
						$this->_attrs['extraHeaders'],
						$this->_attrs['indexFiles'],
						$this->_attrs['autoIndex']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'webapp');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxj'), $attrs, 'uri', 'javaWebAppContext', $defaultExtract);
	}

	protected function add_VT_CTXAS($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
                        self::NewTextAttr('location', DMsg::ALbl('l_location'), 'cust', false, 'as_location'),
			self::NewPathAttr('binPath', DMsg::ALbl('l_binpath'), 'file', 1, 'x'),
                                    self::NewSelAttr('appType', DMsg::ALbl('l_apptype'),
							array(''=>'', 'rails'=>'Rails', 'wsgi'=>'WSGI', 'node'=>'Node' )),
                        self::NewTextAttr('startupFile', DMsg::ALbl('l_startupfile'), 'cust', true, 'as_startupfile'),
						$this->_attrs['note'],
						$this->_attrs['appserverEnv'],
						self::NewIntAttr('maxConns', DMsg::ALbl('l_maxconns'), true, 1, 2000),
						$this->_attrs['ext_env']),
				$this->get_expires_attrs(),
				array(
						$this->_attrs['extraHeaders'],
						$this->_attrs['indexFiles'],
						$this->_attrs['autoIndex']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('rewrite'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'appserver');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxas'), $attrs, 'uri', 'appserverContext', $defaultExtract);
	}

	protected function add_VT_CTXS($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						$this->_attrs['ctx_shandler'],
						$this->_attrs['note'],
						$this->_attrs['extraHeaders']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'servlet');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxs'), $attrs, 'uri', 'servletContext', $defaultExtract);
	}

	protected function add_VT_CTXF($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						self::NewSelAttr('handler', DMsg::ALbl('l_fcgiapp'),	'extprocessor:fcgi', false, 'fcgiapp'),
						$this->_attrs['note'],
						$this->_attrs['extraHeaders']),
						$this->get_ctx_attrs('auth'),
						$this->get_ctx_attrs('charset')
				);
		$defaultExtract = array('type'=>'fcgi');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxf'), $attrs, 'uri', 'fcgiContext', $defaultExtract);
	}


	protected function add_VT_CTXL($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						self::NewSelAttr('handler', DMsg::ALbl('l_lsapiapp'), 'extprocessor:lsapi', false, 'lsapiapp'),
						$this->_attrs['note'],
						$this->_attrs['extraHeaders']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'lsapi');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxl'), $attrs, 'uri', 'lsapiContext', $defaultExtract);
	}

	protected function add_VT_CTXMD($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						self::NewSelAttr('handler', DMsg::ALbl('l_modulehandler'), 'module', false, 'moduleNameSel'),
						$this->_attrs['note'],
						$this->_attrs['mod_params'],
						$this->_attrs['extraHeaders']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'module');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxmd'), $attrs, 'uri', 'lmodContext', $defaultExtract);
	}

	protected function add_VT_CTXB($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						self::NewSelAttr('handler', DMsg::ALbl('l_loadbalancer'), 'extprocessor:loadbalancer', false, 'lbapp'),
						$this->_attrs['note'],
                        $this->_attrs['extraHeaders']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'loadbalancer');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxb'), $attrs, 'uri', 'lbContext', $defaultExtract);
	}

	protected function add_VT_CTXP($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						self::NewSelAttr('handler', DMsg::ALbl('l_webserver'), 'extprocessor:proxy', false, 'proxyWebServer'),
						$this->_attrs['note'],
						$this->_attrs['extraHeaders']),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'proxy');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxp'), $attrs, 'uri', 'proxyContext', $defaultExtract);
	}

	protected function add_VT_CTXC($id)
	{
		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						$this->_attrs['ctx_location']->dup(null, DMsg::ALbl('l_path'), 'cgi_path'),
						$this->_attrs['note'],
						$this->_attrs['extraHeaders'],
						self::NewBoolAttr('allowSetUID', DMsg::ALbl('l_allowsetuid'))),
				$this->get_ctx_attrs('auth'),
				$this->get_ctx_attrs('rewrite'),
				$this->get_ctx_attrs('charset')
		);
		$defaultExtract = array('type'=>'cgi');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxc'), $attrs, 'uri', 'cgiContext', $defaultExtract);
	}

	protected function add_VT_CTXR($id)
	{
		$options = $this->get_cust_status_code();

		$attrs = array_merge(
				$this->get_ctx_attrs('uri'),
				array(
						self::NewBoolAttr('externalRedirect',  DMsg::ALbl('l_externalredirect'), false, 'externalredirect'),
						self::NewSelAttr('statusCode', DMsg::ALbl('l_statuscode'), $options, true, 'statuscode'),
						self::NewTextAttr('location', DMsg::ALbl('l_desturi'), 'url', true, 'destinationuri'),
						$this->_attrs['note'],
                        $this->_attrs['extraHeaders']),
				$this->get_ctx_attrs('auth')
		);
		$defaultExtract = array('type'=>'redirect');
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_ctxr'), $attrs, 'uri', 'redirectContext', $defaultExtract);
	}

	protected function add_T_SEC_CGI($id)
	{
		$attrs = array(
			$this->_attrs['vh_setUIDMode'],
			);
		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_extappresctl'), $attrs);
	}

	protected function add_L_GENERAL($id)
	{
		$ip = self::NewSelAttr('ip', DMsg::ALbl('l_ip'), $this->_options['ip'], false, 'listenerIP');
		$ip->SetFlag(DAttr::BM_NOFILE);
		$port = self::NewIntAttr('port', DMsg::ALbl('l_port'), false, 0, 65535, 'listenerPort');
		$port->SetFlag(DAttr::BM_NOFILE);

		$processes = isset($_SERVER['LSWS_CHILDREN']) ? $_SERVER['LSWS_CHILDREN'] : 1;
		for( $i = 1; $i <= $processes; ++$i )
			$bindoptions[1<<($i-1)] = "Process $i";

		$attrs = array(
				self::NewTextAttr('name', DMsg::ALbl('l_listenername'), 'name', false, 'listenerName'),
				self::NewCustFlagAttr('address', DMsg::ALbl('l_address'), (DAttr::BM_HIDE | DAttr::BM_NOEDIT), false),
				$ip, $port,
				self::NewCheckBoxAttr('binding', DMsg::ALbl('l_binding'), $bindoptions, true, 'listenerBinding'),
				self::NewBoolAttr('secure', DMsg::ALbl('l_secure'), false, 'listenerSecure'),
				$this->_attrs['note'],
		);
		$this->_tblDef[$id] = DTbl::NewIndexed($id, DMsg::ALbl('l_addresssettings'), $attrs, 'name');
	}

	protected function add_LVT_SSL_CLVERIFY($id)
	{
		$attrs = array(
			self::NewSelAttr('clientVerify', DMsg::ALbl('l_clientverify'),
						array('0'=>'none','1'=>'optional','2'=>'require','3'=>'optional_no_ca' )),
		    self::NewIntAttr('verifyDepth', DMsg::ALbl('l_verifydepth'), true, 0, 100),
		    self::NewTextAttr('crlPath', DMsg::ALbl('l_crlpath'), 'cust'),
		    self::NewTextAttr('crlFile', DMsg::ALbl('l_crlfile'), 'cust'),
		    );
		$this->_tblDef[$id] = DTbl::NewRegular($id, DMsg::ALbl('l_clientverify'), $attrs);
	}

}
