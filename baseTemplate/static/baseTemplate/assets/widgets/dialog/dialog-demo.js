/* jQueryUI Dialogs */

$(function() {

    $(".basic-dialog").click(function() {

        $("#basic-dialog").dialog({
            resizable: true,
            minWidth: 400,
            minHeight: 350,
            modal: false,
            closeOnEscape: true,
            position: 'center',
            buttons: {
                "OK": function() {
                    $(this).dialog("close");
                }
            },
            position: "center"
        });

    });

    $(".white-dialog").click(function() {
        $("#basic-dialog").dialog({
            modal: true,
            minWidth: 500,
            minHeight: 200,
            dialogClass: "",
            show: "fadeIn"
        });
        $('.ui-widget-overlay').addClass('bg-white opacity-60');
    });

    $(".black-dialog").click(function() {
        $("#basic-dialog").dialog({
            modal: true,
            minWidth: 500,
            minHeight: 200,
            dialogClass: "",
            show: "fadeIn"
        });
        $('.ui-widget-overlay').addClass('bg-black opacity-60');
    });

    $(".green-dialog").click(function() {
        $("#basic-dialog").dialog({
            modal: true,
            minWidth: 500,
            minHeight: 200,
            dialogClass: "",
            show: "fadeIn"
        });
        $('.ui-widget-overlay').addClass('bg-green opacity-60');
    });

    $(".opacity-dialog-30").click(function() {
        $("#basic-dialog").dialog({
            modal: true,
            minWidth: 500,
            minHeight: 200,
            dialogClass: "",
            show: "fadeIn"
        });
        $('.ui-widget-overlay').addClass('bg-black opacity-30');
    });

    $(".opacity-dialog-60").click(function() {
        $("#basic-dialog").dialog({
            modal: true,
            minWidth: 500,
            minHeight: 200,
            dialogClass: "",
            show: "fadeIn"
        });
        $('.ui-widget-overlay').addClass('bg-black opacity-60');
    });

    $(".opacity-dialog-80").click(function() {
        $("#basic-dialog").dialog({
            modal: true,
            minWidth: 500,
            minHeight: 200,
            dialogClass: "",
            show: "fadeIn"
        });
        $('.ui-widget-overlay').addClass('bg-black opacity-80');
    });

});
