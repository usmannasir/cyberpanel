<?php
require_once('inc/auth.php') ;

echo UI::content_header('fa-home', DMsg::UIStr('menu_dashboard')) ;

$servstatbottom = array(
    array(
        array( RealTimeStats::FLD_UPTIME, DMsg::UIStr('service_uptime'), 'success', '' ),
        array( RealTimeStats::FLD_S_TOT_REQS, DMsg::UIStr('service_totalreq'), 'muted', '' ),
        array( RealTimeStats::FLD_BLOCKEDIP_COUNT, DMsg::UIStr('service_blockedipcnt'), '', 'pinkDark' )
    ),
    array(
        array( RealTimeStats::FLD_AVAILCONN, DMsg::UIStr('service_availconn'), 'success', '' ),
        array( RealTimeStats::FLD_PLAINCONN, DMsg::UIStr('service_plainconn'), 'orange', 'pinkDark' ),
        array( RealTimeStats::FLD_MAXCONN, DMsg::UIStr('service_maxconn'), 'muted', '' )
    ),
    array(
        array( RealTimeStats::FLD_AVAILSSL, DMsg::UIStr('service_availssl'), 'success', '' ),
        array( RealTimeStats::FLD_SSLCONN, DMsg::UIStr('service_sslconn'), 'orange', 'pinkDark' ),
        array( RealTimeStats::FLD_MAXSSL_CONN, DMsg::UIStr('service_maxsslconn'), 'muted', '' )
    ),
    array(
        array( RealTimeStats::FLD_S_REQ_PROCESSING, DMsg::UIStr('service_reqprocessing'), 'success', 'pinkDark' ),
        array( RealTimeStats::FLD_S_REQ_PER_SEC, DMsg::UIStr('service_reqpersec'), 'success', 'green' )
    )
        ) ;

$servstatplot = array(
    array( RealTimeStats::FLD_BPS_IN, DMsg::UIStr('service_bpsin'), true ),
    array( RealTimeStats::FLD_BPS_OUT, DMsg::UIStr('service_bpsout'), true ),
    array( RealTimeStats::FLD_SSL_BPS_IN, DMsg::UIStr('service_sslbpsin'), false ),
    array( RealTimeStats::FLD_SSL_BPS_OUT, DMsg::UIStr('service_sslbpsout'), false ),
    array( RealTimeStats::FLD_PLAINCONN, DMsg::UIStr('service_plainconn'), true ),
    array( RealTimeStats::FLD_IDLECONN, DMsg::UIStr('service_idleconn'), false ),
    array( RealTimeStats::FLD_SSLCONN, DMsg::UIStr('service_sslconn'), true ),
    array( RealTimeStats::FLD_S_REQ_PROCESSING, DMsg::UIStr('service_reqprocessing'), false ),
    array( RealTimeStats::FLD_S_REQ_PER_SEC, DMsg::UIStr('service_reqpersec'), true )
        ) ;
?>

<!-- row -->
<div class="row">

    <!-- NEW WIDGET START -->
    <article class="col-xs-12 col-sm-12 col-md-12 col-lg-12">
        <div class="jarviswidget">
            <header>
                <span class="widget-icon"><i class="fa fa-bar-chart-o fa-lg"></i></span>
                <h2><?php DMsg::EchoUIStr('service_livefeeds') ?></h2>
                <div class="widget-toolbar" role="menu">
                    <span class="onoffswitch-title"><?php DMsg::EchoUIStr('service_realtime') ?></span>
                    <span class="onoffswitch">
                        <input type="checkbox" name="live_feed" class="onoffswitch-checkbox" id="live_feed">
                        <label class="onoffswitch-label" for="live_feed"> <span class="onoffswitch-inner" data-swchon-text="YES" data-swchoff-text="NO"></span> <span class="onoffswitch-switch"></span> </label> </span>
                </div>
            </header>

            <!-- widget div-->
            <?php echo UIBase::GenPlotTab('serv', $servstatbottom, $servstatplot, -1) ; ?>

            <!-- end widget div -->
        </div>
    </article>
    <!-- WIDGET END -->
</div>
<!-- end row -->

<hr class="simple">
<article>
    <div class="jarviswidget" id="lvh_widget">
        <ul class="nav nav-tabs bordered">
            <li class="active">
                <a href="#listeners" data-toggle="tab"><i class="fa fa-fw fa-lg fa-chain"></i> <?php DMsg::EchoUIStr('menu_sl') ?>
                    <span id="listener_running" class="badge bg-color-greenLight txt-color-white" title="<?php DMsg::EchoUIStr('service_running') ?>"></span>
                    <span id="listener_broken" class="badge bg-color-red txt-color-white" title="<?php DMsg::EchoUIStr('service_notrunning') ?>"></span></a>
            </li>
            <li>
                <a href="#vhosts" data-toggle="tab"><i class="fa fa-fw fa-lg fa-cubes"></i> <?php DMsg::EchoUIStr('menu_vh') ?>
                    <span id="vh_running" class="badge bg-color-greenLight txt-color-white" title="<?php DMsg::EchoUIStr('service_active') ?>"></span>
                    <span id="vh_disabled" class="badge bg-color-orange txt-color-white" title="<?php DMsg::EchoUIStr('service_disabled') ?>"></span>
                    <span id="vh_error" class="badge bg-color-red txt-color-white" title="<?php DMsg::EchoUIStr('service_error') ?>"></span></a>
            </li>
            <li class="pull-right lst-spin-icon"></li>
        </ul>

        <div class="tab-content padding-10">
            <div class="tab-pane fade in active" id="listeners">
                <table id="dt_lstatus" class="table table-condensed table-hover"  width="100%">
                    <thead><tr>
                            <th class="lst-iconcol"></th>
                            <th><?php DMsg::EchoUIStr('l_name') ?></th>
                            <th><?php DMsg::EchoUIStr('l_address') ?></th>
                        </tr></thead>
                    <tbody id="listener_body">
                    </tbody>
                </table>
            </div>
            <div class="tab-pane fade" id="vhosts">
                <table id="dt_vhstatus" class="table table-condensed table-hover" width="100%">
                    <thead>
                        <tr>
                            <th></th>
                            <th data-class="expand"><?php DMsg::EchoUIStr('l_name') ?></th>
                            <th data-hide="phone"><?php DMsg::EchoUIStr('service_intemplate') ?></th>
                            <th data-hide="phone,tablet"><i class="fa fa-fw fa-map-marker txt-color-blue hidden-md hidden-sm hidden-xs"></i><?php DMsg::EchoUIStr('l_domains') ?></th>
                            <th data-hide="phone,tablet"><?php DMsg::EchoUIStr('l_action') ?></th>
                        </tr>
                    </thead>
                    <tbody id="vh_body">
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</article>

<hr class="simple">
<article>
    <div class="jarviswidget" id="log_widget">

        <header role="heading">
            <div class="widget-toolbar lst-spin-icon" role="menu"></div>
            <div class="widget-toolbar" role="menu">
                <a class="btn btn-info" href="#view/logviewer.php"><?php DMsg::EchoUIStr('service_gotologviewer') ?></a>
            </div>
            <div class="widget-toolbar" role="menu">
                <span id="debuglogstatus"></span> <?php DMsg::EchoUIStr('service_debuglogstatus') ?>
                <span id="toggledebug" class="btn btn-danger" title="<?php DMsg::EchoUIStr('service_toggledebuglog') ?>"><i class="fa fa-bug"></i></span>
            </div>
            <span class="widget-icon"> <i class="fa fa-file-text-o"></i> </span>
            <h2>
                <?php DMsg::EchoUIStr('service_servererrlog') ?> <small>(
                    <?php DMsg::EchoUIStr('service_loglastsize', array( '%%size%%' => '20KB' )) ?>)</small>
                &nbsp;&nbsp;
                <span id="dash_logfound" class="badge bg-color-blueLight txt-color-white"></span></h2>
        </header>

        <!-- widget div-->
        <div role="content">
            <div class="widget-body no-padding font-sm">
                <!-- content goes here -->

                <table id="dash_logtbl" class="table table-condensed table-hover" width="100%">
                    <thead><tr>
                            <th width="150"><?php DMsg::EchoUIStr('service_time') ?></th>
                            <th width="60"><?php DMsg::EchoUIStr('service_level') ?></th>
                            <th><?php DMsg::EchoUIStr('service_mesg') ?></th>
                        </tr></thead>
                    <tbody id="dash_logbody">
                        <tr><td></td><td></td><td></td></tr>
                    </tbody>
                </table>
                <!-- end content -->
            </div>
        </div>
        <!-- end widget div -->
    </div>
</article>

<script type="text/javascript">

    pageSetUp();

    // PAGE RELATED SCRIPTS

    function refreshListenerVh() {

        var lvh = $("#lvh_widget");
        $.ajax({
            url: "view/ajax_data.php?id=dashstatus",
            type: "GET",
            dataType: "json",
            beforeSend: function () {
                // destroy all datatable instances
                lvh.find("#dt_vhstatus").dataTable().fnDestroy();
                lvh.find("#dt_lstatus").dataTable().fnDestroy();
                lvh.find(".lst-spin-icon").html('<i class="fa fa-refresh fa-spin"></i>');
            }
        })
                .success(function (status) {
                    lvh.find("#listener_running").text(status.l_running);
                    lvh.find("#listener_broken").text(status.l_broken);
                    lvh.find("#vh_running").text(status.v_running);
                    lvh.find("#vh_disabled").text(status.v_disabled);
                    lvh.find("#vh_error").text(status.v_err);
                    lvh.find("#listener_body").html(status.l_body);
                    lvh.find("#vh_body").html(status.v_body);
                    lvh.find('#dt_vhstatus').dataTable();
                    lvh.find('#dt_lstatus').dataTable();
                    lst_refreshFooterTime();
                    lvh.find(".lst-spin-icon").html('<a href="javascript:refreshListenerVh();" title="<?php DMsg::EchoUIStr('btn_refresh') ?>"><i class="fa fa-refresh"></i></a>');
                })
                .error(function (mesg) {
                    console.log("dash status");
                    console.log(arguments);
                })
                ;
    }

    function refreshLog() {
        var logdiv = $("#log_widget");
        $.ajax({
            url: "view/ajax_data.php?id=dashlog",
            type: "GET",
            dataType: "json",
            beforeSend: function () {
                // destroy all datatable instances
                logdiv.find("#dash_logtbl").dataTable().fnDestroy();
                logdiv.find(".lst-spin-icon").html('<i class="fa fa-refresh fa-spin"></i>');
            }
        })
                .success(function (log) {
                    if (log.debuglog == -1) {
                        logdiv.find("#debuglogstatus").html('<i class="fa fa-square text-warning');
                    }
                    else if (log.debuglog == 0) {
                        logdiv.find("#debuglogstatus").html('<i class="fa fa-minus-square text-muted"></i>');
                    }
                    else if (log.debuglog == 1) {
                        logdiv.find("#debuglogstatus").html('<i class="fa fa-check-square text-danger"></i>');
                    }
                    logdiv.find("#dash_logfound").text(log.logfound).attr('title', log.logfoundmesg);
                    logdiv.find("#dash_logbody").html(log.log_body);
                    logdiv.find("#dash_logtbl").dataTable(
                            {"ordering": false}
                    );
                    lst_refreshFooterTime();
                    logdiv.find(".lst-spin-icon").html('<a href="javascript:refreshLog();" title="<?php DMsg::EchoUIStr('btn_refresh') ?>"><i class="fa fa-refresh"></i></a>');
                })
                .error(function (mesg) {
                    console.log("dash log");
                    console.log(arguments);
                })
                ;

    }
    // pagefunction


    var pagefunction = function () {

        /* updating chart */

        var dataset = [], totalPoints = 200;

        // setup control widget
        var updateInterval = 15000;
		if ($("#live_feed").is(':checked')) {
	        $.intervalArr.push(setInterval(update, updateInterval));
        }
        var timezoneoffset = (new Date()).getTimezoneOffset() * 60000;

        // setup plot
        var options = {
            series: {
                lines: {show: true},
                points: {show: true}
            },
            legend: {
                show: true,
                noColumns: 1, // number of colums in legend table
                labelFormatter: null, // fn: string -> string
                labelBoxBorderColor: "#000", // border color for the little label boxes
                container: null, // container (as jQuery object) to put legend in, null means default on top of graph
                position: "ne", // position of default legend container within plot
                margin: [5, 10], // distance from grid edge to default legend container within plot
                backgroundColor: "#efefef", // null means auto-detect
                backgroundOpacity: 1 // set to 0 to avoid background
            },
            grid: {
                hoverable: true,
                clickable: true
            },
            xaxis: {
                mode: "time",
            },
            tooltip: true,
            tooltipOpts: {
                content: "%s <?php DMsg::EchoUIStr('service_at') ?> <b>%x</b> <?php DMsg::EchoUIStr('service_was') ?> <span>%y</span>",
                dateFormat: "%m-%0d %H:%M:%S",
                defaultTheme: false
            },
        };

        var choicecontainer = $("#choices");

        function initDataSet(tab)
        {
            tab.find('input[type="checkbox"]').each(function () {
                var idx = $(this).data("lstStatIdx");
                var label = $(this).parent().text();
                dataset[idx] = {"label": label, "data": []};
            });
            tab.find('input[type="checkbox"]').click(function () {
                plotAccordingToChoices(tab);
            });
        }

        $("#live_feed").on('click', function () {

            if ($(this).is(':checked')) {
                $.intervalArr.push(setInterval(update, updateInterval));
            }
            else {
                clearInterval($.intervalArr.pop());
            }
        });

        $("#toggledebug").on('click', function () {
            lst_toggledebug();
        });

        function plotAccordingToChoices(tab)
        {
            var plotdata = [];
            tab.find("input:checked").each(function () {
                var key = $(this).data("lstStatIdx");
                plotdata.push(dataset[key]);

            });
            if (plotdata.length)
                $.plot(tab.find(".chart-large"), plotdata, options);
        }

        var up = '<i class="fa fa-caret-up"></i> ';
        var highest = '<?php DMsg::EchoUIStr('service_higheston') ?> ';
        var tab = $("#serv");
        initDataSet(tab);

        function update() {

            function onDataReceived(data) {

                var curtime = new Date();
                var curlocaltime = curtime.getTime() - timezoneoffset;
                var curlocaltimestr = curtime.toLocaleString();
                var fieldcount = 9;

                tab.find("span.lst-stat-val").each(function () {
                    var idx = $(this).data("lstStatIdx");
                    $(this).text(data[idx]);
                });
                tab.find("span.lst-stat-max").each(function () {
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

                for (i = 0; i < fieldcount; i++) {
                    dataset[i].data.push([curlocaltime, data[i]]);
                }

                if (dataset[0].data.length > totalPoints) {
                    for (i = 0; i < fieldcount; i++) {
                        dataset[i].data.shift();
                    }
                }
                plotAccordingToChoices(tab);
                lst_refreshFooterTime();
            }

            $.ajax({
                url: "view/ajax_data.php?id=dashstat",
                type: "GET",
                dataType: "json",
                success: onDataReceived
            });

        }

        update();


        refreshListenerVh();

        $('#dt_vhstatus').on('click', '[data-action="lstvhcontrol"]', function (e) {
            var vn = $(this).closest("tr").data("vn"),
                    act = $(this).data("lstact"),
                    atitle;
            if (act == 'disable') {
                atitle = "<?php DMsg::EchoUIStr('service_suspendvhconfirm') ?>";
            }
            else if (act == 'enable') {
                atitle = "<?php DMsg::EchoUIStr('service_resumevhconfirm') ?>";
            }
            vhcontrol(act, atitle, vn);
            e.preventDefault();
        });

        function vhcontrol(act, acttitle, vn) {
            $.SmartMessageBox({
                title: "<i class='fa fa-lg fa-cube txt-color-green'></i> <span class='txt-color-orangeDark'><strong>" + acttitle + "</strong></span>",
                content: vn,
                buttons: '[No][Yes]'
            }, function (ButtonPressed) {
                if (ButtonPressed === "Yes") {

                    $.ajax({
                        type: "POST",
                        url: "view/serviceMgr.php",
                        data: {"act": act, "actId": vn},
                        beforeSend: function () {
                            $.smallBox({
                                title: "<?php DMsg::EchoUIStr('service_requesting') ?>",
                                content: "<i class='fa fa-clock-o'></i> <i><?php DMsg::EchoUIStr('service_willrefresh') ?></i>",
                                color: "#659265",
                                iconSmall: "fa fa-check fa-2x fadeInRight animated",
                                timeout: 2200
                            });
                        },
                        success: function (data) {
                            setTimeout(refreshListenerVh, 2000);
                        }
                    });

                }

            });
        }

        refreshLog();

    };

    // end pagefunction

    // load related plugins

    loadScript("/res/js/plugin/datatables/jquery.dataTables.min.js", function () {
        loadScript("/res/js/plugin/datatables/dataTables.colVis.min.js", function () {
            loadScript("/res/js/plugin/datatables/dataTables.tableTools.min.js", function () {
                loadScript("/res/js/plugin/datatables/dataTables.bootstrap.min.js", function () {
                    loadScript("/res/js/plugin/datatable-responsive/datatables.responsive.min.js", function () {
                        loadScript("/res/js/plugin/flot/jquery.flot.cust.min.js", function () {
                            loadScript("/res/js/plugin/flot/jquery.flot.resize.min.js", function () {
                                loadScript("/res/js/plugin/flot/jquery.flot.tooltip.min.js", pagefunction);
                            });
                        });
                    });
                });
            });
        });
    });



</script>
