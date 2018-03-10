<?php

//ribbon breadcrumbs config
//array("Display Name" => "URL");
$breadcrumbs = array(
	//"Home" => '/'
);

/*navigation array config

ex:
"dashboard" => array(
	"title" => "Display Title",
	"url" => "http://yoururl.com",
	"url_target" => "_self",
	"icon" => "fa-home",
	"label_htm" => "<span>Add your custom label/badge html here</span>",
	"sub" => array() //contains array of sub items with the same format as the parent
)

*/

$page_nav = array(
		'dashboard' => array(
				'title' => DMsg::UIStr('menu_dashboard'),
				'url' => 'view/dashboard.php',
				'icon' => 'fa-home'),
		'serv' => array(
				'title' => DMsg::UIStr('menu_serv'),
				'icon' => 'fa-globe',
				'url' => 'view/confMgr.php?m=serv'),
		'sl' => array(
				'title' => DMsg::UIStr('menu_sl'),
				'icon' => 'fa-chain',
				'url' => 'view/confMgr.php?m=sl'),
		'vh' => array(
				'title' => DMsg::UIStr('menu_vh'),
				'icon' => 'fa-cubes',
				'url' => 'view/confMgr.php?m=vh'),
		'tp' => array(
				'title' => DMsg::UIStr('menu_tp'),
				'url' => 'view/confMgr.php?m=tp',
				'icon' => 'fa-files-o'),
		'tools' => array(
				'title' => DMsg::UIStr('menu_tools'),
				'icon' => 'fa-th',
				'sub' => array(
						'buildphp' => array(
								'title' => DMsg::UIStr('menu_compilephp'),
								'url' => 'view/compilePHP.php'),
						'logviewer' => array(
								'title' => DMsg::UIStr('menu_logviewer'),
								'url' => 'view/logviewer.php'),
						'stats' => array(
								'title' => DMsg::UIStr('menu_rtstats'),
								'url' => 'view/realtimestats.php'),
				)
		),
		'webadmin' => array(
				'title' => DMsg::UIStr('menu_webadmin'),
				'icon' => 'fa-gear',
				'sub' => array(
						'lg' => array(
								'title' => DMsg::UIStr('menu_general'),
								'url' => 'view/confMgr.php?m=admin'),
						'al' => array(
								'title' => DMsg::UIStr('menu_sl'),
								'url' => 'view/confMgr.php?m=al')
				)
		),
		'help' => array(
				'title' => DMsg::UIStr('menu_help'),
				'icon' => 'fa-book',
				'sub' => array(
						'docs' => array(
								'title' => DMsg::UIStr('menu_docs'),
								'url_target' => '_blank',
								'url' => DMsg::DocsUrl()),
						'guides' => array(
								'title' => DMsg::UIStr('menu_guides'),
								'url' => 'http://open.litespeedtech.com/mediawiki/?utm_source=Open&utm_medium=WebAdmin',
								'url_target' => '_blank'),
						'community' => array(
								'title' => DMsg::UIStr('menu_community'),
								'url' => 'https://groups.google.com/forum/#!forum/openlitespeed-development',
								'url_target' => '_blank')
				)
		)


);

//configuration variables
$page_title = "";
$no_main_header = false; //set true for lock.php and login.php

$footer_lic_info = '
		Open LiteSpeed is an open source HTTP server.
				Copyright (C) 2013-2015  Lite Speed Technologies, Inc.

				This program is free software: you can redistribute it and/or modify
				it under the terms of the GNU General Public License as published by
				the Free Software Foundation, either version 3 of the License, or
				(at your option) any later version.

				This program is distributed in the hope that it will be useful,
				but WITHOUT ANY WARRANTY; without even the implied warranty of
				MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
				GNU General Public License for more details.

				You should have received a copy of the GNU General Public License
				along with this program.  If not, see http://www.gnu.org/licenses/ .

		';
