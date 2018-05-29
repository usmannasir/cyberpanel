<?php

require_once("view/inc/auth.php");

//require UI configuration (nav, ribbon, etc.)
require_once("view/inc/configui.php");

include("view/inc/header.php");
include("view/inc/nav.php");

?>
<!-- ==========================CONTENT STARTS HERE ========================== -->
<!-- MAIN PANEL -->
<div id="main" role="main">

	<!-- RIBBON -->
	<div id="ribbon">

		<!-- breadcrumb auto generated-->
		<ol class="breadcrumb">
			<!-- This is auto generated -->
		</ol>
		<!-- end breadcrumb -->
		<span class="hide pull-right well well-sm text-warning"><i class="fa fa-bell"></i> <?php DMsg::EchoUIStr('note_configmodified')?></span>
	</div>
	<!-- END RIBBON -->

	<!-- MAIN CONTENT -->
	<div id="content">

	</div>
	<!-- END MAIN CONTENT -->

</div>
<!-- END MAIN PANEL -->


<!--
<?php echo $footer_lic_info; ?>
-->

<!-- PAGE FOOTER -->
<div class="page-footer">
	<div class="row">
		<div class="col-xs-12 col-sm-6">
			<span class="txt-color-white">LiteSpeed WebAdmin Console © 2014-2017 <?php DMsg::EchoUIStr('note_copyrightreserved')?></span>
		</div>
		<div class="col-xs-6 col-sm-6 text-right hidden-xs">
			<i class="txt-color-blueLight hidden-mobile"> <i class="fa fa-clock-o"></i>
			<i><?php DMsg::EchoUIStr('note_dataretrievedat')?> <span id="lst_UpdateStamp"></span> </i>
		</div>
	</div>
</div>


<!-- END PAGE FOOTER -->

<!-- ==========================CONTENT ENDS HERE ========================== -->

<?php
	include("view/inc/scripts.php");
?>

	</body>

</html>
