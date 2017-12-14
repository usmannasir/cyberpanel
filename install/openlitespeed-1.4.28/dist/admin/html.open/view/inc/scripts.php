<script type="text/javascript">
    function lst_restart() {
        $.SmartMessageBox({
            title: "<i class='fa fa-lg fa-repeat txt-color-green'></i> <span class='text-warning'><strong><?php DMsg::EchoUIStr('service_restartconfirm') ?></strong></span>",
            buttons: '<?php echo '[' . DMsg::UIStr('btn_cancel') . '][' . DMsg::UIStr('btn_go') . ']' ; ?>'
        }, function (ButtonPressed) {
            if (ButtonPressed === "<?php DMsg::EchoUIStr('btn_go') ?>") {

                $.ajax({
                    type: "POST",
                    url: "view/serviceMgr.php",
                    data: {act: "restart"},
                    beforeSend: function () {
                        $.smallBox({
                            title: "<?php DMsg::EchoUIStr('service_requesting') ?>",
                            content: "<i class='fa fa-clock-o'></i> <i><?php DMsg::EchoUIStr('service_willrefresh') ?></i>",
                            color: "#659265",
                            iconSmall: "fa fa-check fa-2x fadeInRight animated",
                            timeout: 15000
                        });
                    },
                    success: function (data) {
                        location.reload(true);
                    }
                });

            }

        });
    }

    function lst_toggledebug() {
        $.SmartMessageBox({
            title: "<i class='fa fa-lg fa-bug txt-color-red'></i> <span class='text-warning'><strong><?php DMsg::EchoUIStr('service_toggledebug') ?></strong></span>",
            content: "<?php DMsg::EchoUIStr('service_toggledebugmsg') ?>",
            buttons: '<?php echo '[' . DMsg::UIStr('btn_cancel') . '][' . DMsg::UIStr('btn_go') . ']' ; ?>'
        }, function (ButtonPressed) {
            if (ButtonPressed === "<?php DMsg::EchoUIStr('btn_go') ?>") {

                $.ajax({
                    type: "POST",
                    url: "view/serviceMgr.php",
                    data: {"act": "toggledebug"},
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
                        setTimeout(refreshLog, 2000);
                    }
                });

            }

        });
    }
</script>

<!-- IMPORTANT: APP CONFIG -->
<script src="/res/js/app.config.min.js"></script>

<!-- BOOTSTRAP JS -->
<script src="/res/js/bootstrap/bootstrap.min.js"></script>

<!-- CUSTOM NOTIFICATION -->
<script src="/res/js/notification/SmartNotification.min.js"></script>

<!-- browser msie issue fix -->
<script src="/res/js/plugin/msie-fix/jquery.mb.browser.min.js"></script>

<!--[if IE 8]>
    <h1>Your browser is out of date, please update your browser by going to www.microsoft.com/download</h1>
<![endif]-->

<!-- MAIN APP JS FILE -->
<script src="/res/js/lst-app.min.js"></script>


<script type="text/javascript">
    // DO NOT REMOVE : GLOBAL FUNCTIONS!
    $(document).ready(function () {
        pageSetUp();
    });


</script>
