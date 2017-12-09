<?php

require_once("inc/auth.php");

$disp = Service::ConfigDispData();

$page = DPageDef::GetPage($disp);
UI::PrintConfPage($disp, $page);

?>

<script type="text/javascript">

pageSetUp();

var pagefunction = function() {
	// clears memory even if nothing is in the function

<?php
if (Service::HasChanged()) { ?>
	var span = $("#ribbon span");
	if (span.hasClass("hide"))
		span.removeClass("hide");
 <?php } ?>
};

// end pagefunction

// run pagefunction on load
pagefunction();

</script>
