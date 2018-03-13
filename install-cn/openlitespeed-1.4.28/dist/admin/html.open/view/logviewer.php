<?php

require_once('inc/auth.php');

echo UI::content_header('fa-list', DMsg::UIStr('menu_tools'), DMsg::UIStr('menu_logviewer'));

?>

<div>

<article>
	<div class="well well-sm">
	<form class="form-horizontal" name="logform" id="logform">
		<fieldset>
			<legend>
			<!-- div class="btn-group">
							<button class="btn btn-default dropdown-toggle" data-toggle="dropdown">
								<i class="fa fa-file-text-o"></i> <span class="caret"> </span>
							</button>
							<ul class="dropdown-menu">
								<li>
									<a href="javascript:void(0);">Choose a different file</a>
								</li>
							</ul>
						</div-->
			<code id="cur_log_file"></code>
			<a href="javascript:download_log()" class="btn btn-xs btn-default"><i class="fa fa-download"></i></a>
			<span class="pull-right"><?php DMsg::EchoUIStr('service_size')?>: <code id="cur_log_size"></code>KB</span>
			</legend>

			<div class="form-group">
				<label class="col-md-2 control-label"><?php DMsg::EchoUIStr('service_displevel')?></label>
				<div class="col-md-2">
							<select class="form-control" id="sellevel" name="sellevel">
								<option value="1">ERROR</option>
								<option value="2">WARNING</option>
								<option value="3">NOTICE</option>
								<option value="4">INFO</option>
								<option value="5">DEBUG</option>
							</select>
				</div>
				<label class="control-label col-md-2"><i class="fa fa-search"></i> <?php DMsg::EchoUIStr('service_searchfrom')?> (KB)</label>
				<div class="col-md-2">
					<input name="startpos" id="startpos" class="form-control" type="text">
				</div>
				<label class="control-label col-md-2"><?php DMsg::EchoUIStr('service_length')?> (KB)</label>
				<div class="col-md-2">
					<input name="blksize" id="blksize" class="form-control" type="text">
				</div>
			</div>
				<div class="col-md-4 col-md-offset-4"><div class="btn-group btn-group-justified">
				<a class="btn btn-default btn-sm" href="javascript:refreshLog('begin');" ><i class="fa fa-fast-backward"></i></a>
				<a class="btn btn-default btn-sm" href="javascript:refreshLog('prev');"><i class="fa fa-backward"></i></a>
				<a id="refreshlog_icon" class="btn btn-default btn-sm" href="javascript:refreshLog('');"><i class="fa fa-refresh"></i></a>
				<a class="btn btn-default btn-sm" href="javascript:refreshLog('next');"><i class="fa fa-forward"></i></a>
				<a class="btn btn-default btn-sm" href="javascript:refreshLog('end');"><i class="fa fa-fast-forward"></i></a>
			</div></div>

		</fieldset>

		<input id="filename" name="filename" type="hidden">
		<input id="act" name="act" type="hidden">
	</form>
	</div>
	<p id="dash_logfoundmesg" class="alert alert-info no-margin"></p>
						</p>
	<!-- widget div-->
			<!-- content goes here -->

	<table id="dash_logtbl" class="table table-condensed table-hover" width="100%">
		<thead><tr><th width="150"><?php DMsg::EchoUIStr('service_time')?></th><th width="60"><?php DMsg::EchoUIStr('service_level')?></th><th><?php DMsg::EchoUIStr('service_mesg')?></th></tr></thead>
		<tbody id="dash_logbody" class="font-lstlog">
			<tr><td></td><td></td><td></td></tr>
		</tbody>
	</table>
			<!-- end content -->
</article>
</div>

<script type="text/javascript">
	/* DO NOT REMOVE : GLOBAL FUNCTIONS!
	 *
	 * pageSetUp() is needed whenever you load a page.
	 * It initializes and checks for all basic elements of the page
	 * and makes rendering easier.
	 */

	pageSetUp();

	// PAGE RELATED SCRIPTS

		function refreshLog(act) {
			var spinicon = $("#refreshlog_icon");
			var logform = $("#logform");
			logform.find("#act").val(act);
			logform.find("#filename").val($("#cur_log_file").text());

			$.ajax({
				url: "view/ajax_data.php?id=viewlog",
				data : logform.serialize(),
				dataType: "json",
				async : false,
				beforeSend : function() {
					// destroy all datatable instances
					$("#dash_logtbl").dataTable().fnDestroy();
					spinicon.html('<i class="fa fa-refresh fa-spin"></i>');
				}
			})
			.success (function(log) {
				$("#cur_log_file").text(log.cur_log_file);
				$("#cur_log_size").text(log.cur_log_size);
				$("#dash_logfoundmesg").text(log.logfoundmesg);
				$("#dash_logbody").html(log.log_body);
				logform.find("#sellevel").val(log.sellevel);
				logform.find("#startpos").val(log.startpos);
				logform.find("#blksize").val(log.blksize);
				$("#dash_logtbl").dataTable(
						{"ordering": false,
						"lengthMenu":[[30,50,100,200],[30,50,100,200]]}
				);
				lst_refreshFooterTime();
				spinicon.html('<i class="fa fa-refresh"></i>');
			})
			.error (function(mesg) {
				alert("error " + mesg);
			})
			;
		}

		function download_log() {
			document.logform.id.value = 'downloadlog';
			document.logform.filename.value = $("#cur_log_file").text();
			document.logform.submit();
		}
	// pagefunction


	var pagefunction = function() {


		refreshLog('');
	};

	// end pagefunction

	// load related plugins

	loadScript("/res/js/plugin/datatables/jquery.dataTables.min.js", function(){
		loadScript("/res/js/plugin/datatables/dataTables.colVis.min.js", function(){
			loadScript("/res/js/plugin/datatables/dataTables.tableTools.min.js", function(){
				loadScript("/res/js/plugin/datatables/dataTables.bootstrap.min.js", function(){
					loadScript("/res/js/plugin/datatable-responsive/datatables.responsive.min.js", pagefunction);
				});
			});
		});
	});


</script>
