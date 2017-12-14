<?php if (!$no_main_header) { ?>
<!DOCTYPE html>
<html lang="en-us">
<?php } ?>    
	<head>
		<meta charset="utf-8">
		<!--<meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">-->

		<title>LiteSpeed WebAdmin Console</title>
		<meta name="description" content="LiteSpeed WebAdmin Console">
		<meta name="author" content="LiteSpeed Technologies, Inc.">

		<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

		<!-- Basic Styles -->
		<link rel="stylesheet" type="text/css" media="screen" href="/res/css/bootstrap.min.css">
		<link rel="stylesheet" type="text/css" media="screen" href="/res/css/font-awesome.min.css">

		<link rel="stylesheet" type="text/css" media="screen" href="/res/css/smartadmin-production.min.css">

		<link rel="stylesheet" type="text/css" media="screen" href="/res/css/lst-webadmin.min.css">

		<!-- FAVICONS -->
		<link rel="shortcut icon" href="/res/img/favicon/favicon.ico" type="image/x-icon">
		<link rel="icon" href="/res/img/favicon/favicon.ico" type="image/x-icon">

		<!-- GOOGLE FONT -->
		<link rel="stylesheet" href="//fonts.googleapis.com/css?family=Open+Sans:400italic,700italic,300,400,700">

		<!-- iOS web-app metas : hides Safari UI Components and Changes Status Bar Appearance -->
		<meta name="apple-mobile-web-app-capable" content="yes">
		<meta name="apple-mobile-web-app-status-bar-style" content="black">

		<!-- Link to Google CDN's jQuery + jQueryUI; fall back to local -->
		<script src="//ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
		<script>
			if (!window.jQuery) {
				document.write('<script src="/res/js/libs/jquery-2.1.1.min.js"><\/script>');
			}
		</script>

		<script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.11.1/jquery-ui.min.js"></script>
		<script>
			if (!window.jQuery.ui) {
				document.write('<script src="/res/js/libs/jquery-ui-1.11.1.min.js"><\/script>');
			}
		</script>

	</head>
      		<?php
			if ($no_main_header)
				return;
		?>
	<body>

		<!-- POSSIBLE CLASSES: minified, fixed-ribbon, fixed-header, fixed-width
			 You can also add different skin classes such as "smart-skin-1", "smart-skin-2" etc...-->

		<!-- HEADER -->
		<header id="header">
			<div id="logo-group">
                            <span id="logo"> 
                                <object type="image/svg+xml" data="/res/img/product_logo.svg"  height="35" width="200">
Your browser doesn't support SVG
                                </object> 
                            </span>
			</div>

			<!-- projects dropdown -->
			<div class="project-context hidden-xs"><span class="label">

			<?php
			$prod = Product::GetInstance();
			$version = $prod->getVersion();
			$new_version = $prod->getNewVersion();

			$ver_notice = DMsg::UIStr('note_curver') . ':</span><span>'
				. Product::PROD_NAME . ' ' . $version; 
			if ($new_version) {
				$ver_notice .= ' &nbsp;&nbsp;<a href="http://open.litespeedtech.com/releaselog" rel="noopener noreferrer" target="_blank"><i>'
						. DMsg::UIStr('note_newver') . ' ' . $new_version . '</i></a>';
			}
			echo $ver_notice;

			?>
			</span></div>
			<!-- end projects dropdown -->

			<!-- pulled right: nav area -->
			<div class="pull-right">
<?php

	echo '<!-- collapse menu button -->
		<div id="hide-menu" class="btn-header pull-right">
			<span> <a href="javascript:void(0);" title="' . DMsg::UIStr('note_collapsemenu') . '" data-action="toggleMenu"><i class="fa fa-reorder"></i></a> </span>
		</div>
		<!-- end collapse menu -->

		<!-- logout button -->
		<div id="logout" class="btn-header transparent pull-right">
			<span> <a href="/login.php?logoff=1" title="' . DMsg::UIStr('note_signout') . '" data-action="userLogout" data-logout-msg="' . DMsg::UIStr('note_logout') . '"><i class="fa fa-sign-out"></i></a> </span>
		</div>
		<!-- end logout button -->

		<!-- fullscreen button -->
		<div id="fullscreen" class="btn-header transparent pull-right">
			<span> <a href="javascript:void(0);" title="' . DMsg::UIStr('note_fullscreen') . '" data-action="launchFullscreen"><i class="fa fa-arrows-alt"></i></a> </span>
		</div>
		<!-- end fullscreen button -->

		<!-- multiple lang dropdown : find all flags in the flags page -->

		<ul class="header-dropdown-list hidden-xs">
			<li>
	';
	echo UIBase::Get_LangDropdown();
?>
			</li>
		</ul>

		<!-- end multiple lang -->
			</div>
			<!-- end pulled right: nav area -->

		</header>
		<!-- END HEADER -->

		<!-- SHORTCUT AREA : With large tiles (activated via clicking user name tag) -->
		<div id="shortcut">
			<ul>
				<li>
					<a href="javascript:lst_restart()" class="jarvismetro-tile big-cubes bg-color-greenLight"> <span class="iconbox"> <i class="fa fa-repeat fa-4x"></i> <span><?php echo DMsg::UIStr('menu_restart')?> </span> </span> </a>
				</li>
				<li>
					<a href="#view/realtimestats.php" class="jarvismetro-tile big-cubes bg-color-blue"> <span class="iconbox"> <i class="fa fa-bar-chart-o fa-4x"></i> <span><?php echo DMsg::UIStr('menu_rtstats')?></span> </span> </a>
				</li>
				<li>
					<a href="#view/logviewer.php" class="jarvismetro-tile big-cubes bg-color-orange"> <span class="iconbox"> <i class="fa fa-list fa-4x"></i> <span><?php echo DMsg::UIStr('menu_logviewer')?></span> </span> </a>
				</li>
				<li>
					<a href="javascript:lst_toggledebug()" class="jarvismetro-tile big-cubes bg-color-purple"> <span class="iconbox"> <i class="fa fa-bug fa-4x"></i> <span><?php echo DMsg::UIStr('menu_toggledebug')?></span> </span> </a>
				</li>
			</ul>
		</div>
		<!-- END SHORTCUT AREA -->
