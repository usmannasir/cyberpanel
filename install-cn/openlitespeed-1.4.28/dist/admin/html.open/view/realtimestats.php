<?php

require_once('inc/auth.php');

echo UI::content_header('fa-bar-chart-o', DMsg::UIStr('menu_rtstats'));

$label_reqprocessing = DMsg::UIStr('service_reqprocessing');
$label_reqpersec = DMsg::UIStr('service_reqpersec');
$label_maxconn = DMsg::UIStr('service_maxconn');
$label_sslconn = DMsg::UIStr('service_sslconn');
$label_plainconn = DMsg::UIStr('service_plainconn');
$label_totalreq = DMsg::UIStr('service_totalreq');
$label_eapcount = DMsg::UIStr('service_eapcount');
$label_eapinuse = DMsg::UIStr('service_eapinuse');
$label_eapidle = DMsg::UIStr('service_eapidle');
$label_eapwaitq = DMsg::UIStr('service_eapwaitq');
$label_eapreqpersec = DMsg::UIStr('service_eapreqpersec');
$label_name = DMsg::UIStr('l_name');
$th = '</th><th>';

$servstatbottom = array(
		array(
				array(RealTimeStats::FLD_UPTIME, DMsg::UIStr('service_uptime'), 'success', ''),
				array(RealTimeStats::FLD_S_TOT_REQS, $label_totalreq, 'muted', ''),
				array(RealTimeStats::FLD_BLOCKEDIP_COUNT, DMsg::UIStr('service_blockedipcnt'), '', 'pinkDark')
		),
		array(
				array(RealTimeStats::FLD_AVAILCONN, DMsg::UIStr('service_availconn'), 'success', ''),
				array(RealTimeStats::FLD_PLAINCONN, $label_plainconn, 'orange', 'pinkDark'),
				array(RealTimeStats::FLD_MAXCONN, $label_maxconn, 'muted', '')
		),
		array(
				array(RealTimeStats::FLD_AVAILSSL, DMsg::UIStr('service_availssl'), 'success', ''),
				array(RealTimeStats::FLD_SSLCONN, $label_sslconn, 'orange', 'pinkDark'),
				array(RealTimeStats::FLD_MAXSSL_CONN, DMsg::UIStr('service_maxsslconn'), 'muted', '')
		),
		array(
				array(RealTimeStats::FLD_S_REQ_PROCESSING, $label_reqprocessing, 'success', 'pinkDark'),
				array(RealTimeStats::FLD_S_REQ_PER_SEC, $label_reqpersec, 'success', 'green')
		)
);

$servstatplot = array(
		array(RealTimeStats::FLD_BPS_IN, DMsg::UIStr('service_bpsin'), true),
		array(RealTimeStats::FLD_BPS_OUT, DMsg::UIStr('service_bpsout'), true),
		array(RealTimeStats::FLD_SSL_BPS_IN, DMsg::UIStr('service_sslbpsin'), false),
		array(RealTimeStats::FLD_SSL_BPS_OUT, DMsg::UIStr('service_sslbpsout'), false),
		array(RealTimeStats::FLD_PLAINCONN, $label_plainconn, true),
		array(RealTimeStats::FLD_IDLECONN, DMsg::UIStr('service_idleconn'), false),
		array(RealTimeStats::FLD_SSLCONN, $label_sslconn, true),
		array(RealTimeStats::FLD_S_REQ_PROCESSING, $label_reqprocessing, false),
		array(RealTimeStats::FLD_S_REQ_PER_SEC, $label_reqpersec, true)
);

$vhstatbottom = array(
		array(
				array(RealTimeStats::FLD_VH_TOT_REQS, $label_totalreq, 'muted', ''),
				array(RealTimeStats::FLD_VH_EAP_COUNT, $label_eapcount, '', 'pinkDark')
		),
		array(
				array(RealTimeStats::FLD_VH_EAP_IDLE, $label_eapidle, 'success', ''),
				array(RealTimeStats::FLD_VH_EAP_INUSE, $label_eapinuse, 'orange', 'pinkDark'),
		),
		array(
				array(RealTimeStats::FLD_VH_EAP_WAITQUE, $label_eapwaitq, 'orange', 'red'),
				array(RealTimeStats::FLD_VH_EAP_REQ_PER_SEC, $label_eapreqpersec, 'success', 'green'),
		),
		array(
				array(RealTimeStats::FLD_VH_REQ_PROCESSING, $label_reqprocessing, 'success', 'pinkDark'),
				array(RealTimeStats::FLD_VH_REQ_PER_SEC, $label_reqpersec, 'success', 'green')
		)
);

$vhstatplot = array(
		array(RealTimeStats::FLD_VH_EAP_INUSE, $label_eapinuse, true),
		array(RealTimeStats::FLD_VH_EAP_WAITQUE, $label_eapwaitq, true),
		array(RealTimeStats::FLD_VH_EAP_IDLE, $label_eapidle, true),
		array(RealTimeStats::FLD_VH_EAP_REQ_PER_SEC, $label_eapreqpersec, true),
		array(RealTimeStats::FLD_VH_REQ_PROCESSING, $label_reqprocessing, true),
		array(RealTimeStats::FLD_VH_REQ_PER_SEC, $label_reqpersec, true)
);

$label_sec = DMsg::UIStr('service_seconds');
$label_min = DMsg::UIStr('service_minutes');

$refreshOptions = array(
		0 => DMsg::UIStr('service_stop'),
		10 => "10 $label_sec",
		15 => "15 $label_sec",
		30 => "30 $label_sec",
		60 => "60 $label_sec",
		120 => "2 $label_min",
		300 => "5 $label_min"
);

$topOptions = array(
		10 => 'Top 10', 20 => 'Top 20', 50 => 'Top 50', 100 => 'Top 100', 200 => 'Top 200'
);

$vhSortOptions = array(
		RealTimeStats::FLD_VH_REQ_PER_SEC => $label_reqpersec,
		RealTimeStats::FLD_VH_REQ_PROCESSING => $label_reqprocessing,
		RealTimeStats::FLD_VH_TOT_REQS => $label_totalreq,
		RealTimeStats::FLD_VH_EAP_COUNT => $label_eapcount,
		RealTimeStats::FLD_VH_EAP_INUSE => $label_eapinuse,
		RealTimeStats::FLD_VH_EAP_WAITQUE => $label_eapwaitq,
		RealTimeStats::FLD_VH_EAP_IDLE => $label_eapidle,
		RealTimeStats::FLD_VH_EAP_REQ_PER_SEC => $label_eapreqpersec
);

?>

<!-- row -->
		<div class="row">

		<!-- NEW WIDGET START -->
		<article class="col-xs-12 col-sm-12 col-md-12 col-lg-12">

				<!-- Widget ID (each widget will need unique ID)-->
				<div class="jarviswidget">
				<header>
				<span class="widget-icon"><i class="fa fa-bar-chart-o fa-lg"></i></span>
				<h2><?php DMsg::EchoUIStr('service_livefeeds')?></h2>
				<div class="widget-toolbar" role="menu">
					<?php DMsg::EchoUIStr('service_refreshinterval')?>: <select id="refresh-interval" class="font-sm">
<?php echo UIBase::genOptions($refreshOptions, 15); ?>
					</select>

				</div>
				</header>
				<!-- widget div-->
				<div class="no-padding">


					<div class="widget-body">
					<div>
						<ul class="nav nav-tabs in" id="liveTab">
							<li class="active" data-vn="serv"><a data-toggle="tab" href="#serv"><i
									class="fa fa-globe"></i> <span
									class="hidden-mobile hidden-tablet"><?php DMsg::EchoUIStr('service_server')?></span> </a>
							</li>
						</ul>
					</div>
					<!-- content -->
						<div class="tab-content">

<?php
	echo '<div id="vhhide" class="hide">' . UIBase::GenPlotTab('vh', $vhstatbottom, $vhstatplot, 0) . "</div>\n";
	echo UIBase::GenPlotTab('serv', $servstatbottom, $servstatplot, 1);
?>


</div>
<!-- end content -->

</div>
<!-- end widget body-->
</div></div>

</article>
<!-- WIDGET END -->

</div>

<!-- end row -->

<hr class="simple">
<article>
		<div class="jarviswidget">
		<header>
			<span class="widget-icon"><i class="fa fa-clock-o fa-lg"></i>
			</span>
			<h2>
				Snapshot <small class="text-muted" id="refresh_stamp"></small> <span
					id="refresh_icon"></span>
			</h2>
			<ul class="nav nav-tabs pull-right in">
				<li class="active"><a href="#vhoststab" data-toggle="tab"><i
						class="fa fa-fw fa-lg fa-cubes"></i> <?php DMsg::EchoUIStr('menu_vh')?> </a>
				</li>
				<li><a href="#expstab" data-toggle="tab"><i
						class="fa fa-fw fa-lg fa-tasks"></i> <?php DMsg::EchoUIStr('tab_ext')?></a>
				</li>
			</ul>
			<div class="widget-toolbar" role="menu">
				<span><?php DMsg::EchoUIStr('service_retrieve')?> </span>
				<select id="vh_topn" name="vh_topn" class="font-sm">
<?php echo UIBase::genOptions($topOptions, 10); ?>
				</select>
				<select name="vh_sort" id="vh_sort" class="font-sm">
<?php echo UIBase::genOptions($vhSortOptions, RealTimeStats::FLD_VH_REQ_PER_SEC); ?>
				</select>
			</div>
			<div class="widget-toolbar" role="menu">
				<span><?php DMsg::EchoUIStr('service_filterbyvn')?>: </span><input class="input-xs" type="text"
					name="vh_filter" id="vh_filter" placeholder="<?php DMsg::EchoUIStr('service_nameallowexp')?>" value="">
			</div>
		</header>

		<div class="tab-content padding-10">
			<div class="tab-pane fade in active" id="vhoststab">
				<table id="dt_vhstatus" class="table table-condensed table-hover" width="100%">
					<thead><tr><th class="lst-iconcol"></th><th class="lst-vhnames">
					<?php
					echo $label_name . $th . $label_reqprocessing . $th . $label_reqpersec . $th . $label_totalreq
					. $th . $label_eapcount . $th . $label_eapinuse . $th . $label_eapidle . $th . $label_eapwaitq
					. $th . $label_eapreqpersec;
					?>
					</th>
					</tr></thead>
					<tbody id="vh_body">
					</tbody>
				</table>
			</div>
			<div class="tab-pane fade" id="expstab">
		        <table id="dt_expstatus" class="table table-condensed table-hover" width="100%">
					<thead><tr>
							<th data-class="expand">
							<?php
							echo DMsg::UIStr('service_scope') . $th . DMsg::UIStr('l_type') . $th . $label_name
							. $th . $label_maxconn . $th . DMsg::UIStr('service_effmax') . $th
							. DMsg::UIStr('service_pool') . $th . DMsg::UIStr('service_inuse') . $th
							. DMsg::UIStr('service_idle') . $th . DMsg::UIStr('service_waitq') . $th
							. $label_reqpersec . $th . $label_totalreq;
							?>
							</th>
					</tr></thead>
					<tbody id="exp_body">
					</tbody>
				</table>
			</div>
		</div>
		</div>
</article>


<script type="text/javascript">
	/* DO NOT REMOVE : GLOBAL FUNCTIONS!
	 *
	 * pageSetUp(); WILL CALL THE FOLLOWING FUNCTIONS
	 *
	 * // activate tooltips
	 * $("[rel=tooltip]").tooltip();
	 *
	 * // activate popovers
	 * $("[rel=popover]").popover();
	 *
	 * // activate popovers with hover states
	 * $("[rel=popover-hover]").popover({ trigger: "hover" });
	 *
	 * // activate inline charts
	 * runAllCharts();
	 *
	 * // setup widgets
	 * setup_widgets_desktop();
	 *
	 * // run form elements
	 * runAllForms();
	 *
	 ********************************
	 *
	 * pageSetUp() is needed whenever you load a page.
	 * It initializes and checks for all basic elements of the page
	 * and makes rendering easier.
	 *
	 */

	pageSetUp();

	// PAGE RELATED SCRIPTS

	// vh variables
	var spinicon = $("#refresh_icon"),
	refreshstamp = $("#refresh_stamp"),
	dt_vhstatus = $("#dt_vhstatus"),
	dt_expstatus = $("#dt_expstatus"),
	vh_body = $("#vh_body"),
	exp_body = $("#exp_body"),
	vh_filter = $("#vh_filter"),
	vh_topn = $("#vh_topn"),
	vh_sort = $("#vh_sort"),
	livetabs = $("#liveTab"),
	allow_monitor_max = 3,
	dataset = [[]];

	function addMonitorTab(vhname) {
		var vhid = vhname.replace(/\./g, '_');
		var tabname = (vhname.length < 30) ? vhname : '<abbr title="' + vhname + '">' + vhname.substring(0,30) + '</abbr>';

		livetabs.append('<li data-vn="' + vhname + '"><a data-toggle="tab" href="#' + vhid
				+ '"><i class="fa fa-cube" title="' + vhname + '"></i>	<span class="hidden-mobile hidden-tablet">'
				+ tabname + ' </span>&nbsp; <span class="close">Ã—</span></a></li>');

		var tabcontent = livetabs.closest(".widget-body").find(".tab-content");
		var newcontent = tabcontent.find("#vhhide").html().replace(/id=\"vh\"/, 'id="' + vhid + '"');
		tabcontent.append(newcontent);

		var newtab = tabcontent.find("#" + vhid);
		initDataSet(newtab);
		livetabs.children().last().on("click", "span.close", function(e) {
			newtab.remove();
			var li = $(this).closest("li");
			if (li.hasClass("active")) {
				livetabs.children().first().addClass("active");
				tabcontent.find("#serv").addClass("active in");
			}
			li.remove();
			e.preventDefault();
		});
	}

	var options = {
			series: {
				lines: {show: true},
				points: {show: true	}
			},
			legend : {
				show : true,
				noColumns : 1, // number of colums in legend table
				labelFormatter : null, // fn: string -> string
				labelBoxBorderColor : "#000", // border color for the little label boxes
				container : null, // container (as jQuery object) to put legend in, null means default on top of graph
				position : "ne", // position of default legend container within plot
				margin : [5, 10], // distance from grid edge to default legend container within plot
				backgroundColor : "#efefef", // null means auto-detect
				backgroundOpacity : 1 // set to 0 to avoid background
			},
			grid : {
				hoverable : true,
				clickable : true
			},
			xaxis : {
				mode : "time",
			},

			tooltip : true,
			tooltipOpts : {
				content : "%s <?php DMsg::EchoUIStr('service_at')?> <b>%x</b> <?php DMsg::EchoUIStr('service_was')?> <span>%y</span>",
				dateFormat : "%m-%0d %H:%M:%S",
				defaultTheme : false
			},
	};

	function plotAccordingToChoices(tab)
	{
		var tabid = tab.attr("id");
		var plotdata = [];
		tab.find("input:checked").each(function () {
			var key = $(this).data("lstStatIdx");
			plotdata.push(dataset[tabid][key]);

		});
		if (plotdata.length)
			$.plot(tab.find(".chart-large"), plotdata, options);
	}

	var up = '<i class="fa fa-caret-up"></i> ';
	var highest = '<?php DMsg::EchoUIStr('service_higheston')?> ';
	var totalPoints = 150;
	var serv_tab = $("#serv");
	initDataSet(serv_tab);

	var updateInterval = 15000;
	var timezoneoffset = (new Date()).getTimezoneOffset() * 60000;

	function onPlotDataReceived(series)
	{
		var curtime = new Date();
		var curlocaltime = curtime.getTime() - timezoneoffset;
		var curlocaltimestr = curtime.toLocaleString();

		livetabs.find("li").each(function() {

			var vn = $(this).data("vn");
			var data = series[vn];
			if (data == undefined)
				return;

			var fieldcount = (vn == "serv") ? 9 : 6;
			var tabid = vn.replace(/\./g, '_');
			var tab = $("#" + tabid);

			tab.find("span.lst-stat-val").each(function(){
				var idx = $(this).data("lstStatIdx");
				$(this).text(data[idx]);
			});
			tab.find("span.lst-stat-max").each(function(){
				var newval = data[$(this).data("lstStatIdx")];
				var curval = 0;
				if (newval > 0) {
					if ($(this).data("curval") === undefined) {
						$(this).removeClass("hide");
					}
					else
						curval = $(this).data("curval");
					if (newval > curval) {
						$(this).html(up + newval)
							.attr("title", highest + curlocaltimestr)
							.data("curval", newval);
					}
				}
			});

			for (i = 0; i < fieldcount ; i++) {
				dataset[tabid][i].data.push([curlocaltime, data[i]]);
			}

			if (dataset[tabid][0].data.length > totalPoints) {
				for (i = 0; i < fieldcount ; i++) {
					dataset[tabid][i].data.shift();
				}
			}
			plotAccordingToChoices(tab);
		});


		lst_refreshFooterTime();
	}

	function initDataSet(tab)
	{
		var tabid = tab.attr("id");
		dataset[tabid] = [];
		tab.find('input[type="checkbox"]').each(function () {
			var idx = $(this).data("lstStatIdx");
			var label = $(this).parent().text();
			dataset[tabid][idx] = {"label":label, "data":[]};
		});
		tab.find('input[type="checkbox"]').click(function() {
			plotAccordingToChoices(tab);
		});
	}

	function refreshVh()
	{
		$.ajax({
			url: "view/ajax_data.php?id=vhstat",
			type: "GET",
			dataType: "json",
			data: {vh_filter: vh_filter.val(),
					vh_topn: vh_topn.val(),
					vh_sort: vh_sort.val()},
			beforeSend : function() {
				spinicon.html('<i class="fa fa-refresh fa-spin"></i>');
			}
		})
		.success (function(status) {
			// destroy all datatable instances
			dt_vhstatus.dataTable().fnDestroy();
			dt_expstatus.dataTable().fnDestroy();

			vh_body.html(status.vbody);
			exp_body.html(status.ebody);
			dt_vhstatus.dataTable();
			dt_expstatus.dataTable();

			refreshstamp.text(new Date().toLocaleString());
			spinicon.html('<a href="javascript:refreshVh();" class="btn btn-info btn-xs" title="<?php DMsg::EchoUIStr('btn_refresh')?>"><i class="fa fa-refresh"></i></a>');
			})
		.error(function(data) {
			console.log(data);
			alert(data);
		})
		;

	}

	// pagefunction

	var pagefunction = function()
	{
		$.intervalArr.push(setInterval(updateChart, updateInterval));

		$('#vh_body').on('click', '[data-lstmonitor="vh"]', function(e){
			var vhname = $(this).parent().siblings(".lst-vhname").text();
			var found  = false;
			livetabs.find("li[data-vn]").each(function() {
				if ($(this).data("vn") == vhname) {
					found = true;
					return false;
				}
			});
			if (found) {
				$.smallBox({
					title : vhname + " <?php DMsg::EchoUIStr('service_ismonitored')?>",
					content : "",
					color : "#A65858",
					iconSmall : "fa fa-eye",
					timeout : 5000
				});
			}
			else if (livetabs.find("li").length > allow_monitor_max)  {
				$.smallBox({
					title : "<?php DMsg::EchoUIStr('service_monitormaxallowed')?> " + allow_monitor_max + " <?php DMsg::EchoUIStr('menu_vh')?>",
					content : "",
					color : "#A65858",
					iconSmall : "fa fa-eye",
					timeout : 5000
				});
			}
			else {
				$.smallBox({
					title : "<?php DMsg::EchoUIStr('service_addtomonitor')?>",
					content : "<?php DMsg::EchoUIStr('service_confirmmonitor')?> " + vhname
						+ "? <p class='text-align-right'><a href='javascript:void(0);' onclick='javascript:addMonitorTab(\""
						+ vhname
						+ "\");' class='btn btn-primary btn-sm'><?php DMsg::EchoUIStr('btn_go')?></a> <a href='javascript:void(0);' class='btn btn-default btn-sm'><?php DMsg::EchoUIStr('btn_cancel')?></a></p>",
					color : "#296191",
					icon : "fa fa-stethoscope swing animated"
				});
			}
		});

		$("#refresh-interval").change(function() {
			updateInterval = $(this).val() * 1000;
			clearInterval($.intervalArr.pop());
			if (updateInterval > 0) {
				$.intervalArr.push(setInterval(updateChart, updateInterval));
			}
		});

		function updateChart()
		{
			var vnmonitor = [];
			livetabs.find("li[data-vn]").each(function() {
				vnmonitor.push($(this).data("vn"));
			});
			$.ajax({
				url: "view/ajax_data.php?id=plotstat",
				type: "POST",
				dataType: "json",
				data: {"vhnames": vnmonitor},
				success: onPlotDataReceived
			});

		}

		updateChart();

		refreshVh();
	}


	// end pagefunction

	// load related plugins

	loadScript("/res/js/plugin/datatables/jquery.dataTables.min.js", function(){
		loadScript("/res/js/plugin/datatables/dataTables.colVis.min.js", function(){
			loadScript("/res/js/plugin/datatables/dataTables.tableTools.min.js", function(){
				loadScript("/res/js/plugin/datatables/dataTables.bootstrap.min.js", function(){
					loadScript("/res/js/plugin/datatable-responsive/datatables.responsive.min.js", function() {
						loadScript("/res/js/plugin/flot/jquery.flot.cust.min.js", function(){
							loadScript("/res/js/plugin/flot/jquery.flot.resize.min.js", function(){
								loadScript("/res/js/plugin/flot/jquery.flot.tooltip.min.js", pagefunction);
							});
						});
					});
				});
			});
		});
	});


</script>
