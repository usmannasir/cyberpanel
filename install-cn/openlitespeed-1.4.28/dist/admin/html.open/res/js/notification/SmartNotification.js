/*
 Copyright 2013 - SmartAdmin Template

 * This script is part of an item on wrapbootstrap.com
 * https://wrapbootstrap.com/user/myorange
 *
 * ************************************************************* *
 * For more information please contact info@myorange.ca
 * ************************************************************* */


jQuery(document).ready(function () {

    // Plugins placing
    $("body").append("<div id='divSmallBoxes'></div>");

});

//Closing Rutine for Loadings
function SmartUnLoading() {

    $(".divMessageBox").fadeOut(300, function () {
        $(this).remove();
    });

    $(".LoadingBoxContainer").fadeOut(300, function () {
        $(this).remove();
    });
}

// Messagebox
var ExistMsg = 0,
    SmartMSGboxCount = 0,
    PrevTop = 0;

    $.SmartMessageBox = function (settings, callback) {
        var SmartMSG, Content;
        settings = $.extend({
            title: "",
            content: "",
            NormalButton: undefined,
            ActiveButton: undefined,
            buttons: undefined,
            input: undefined,
            inputValue: undefined,
            placeholder: "",
            options: undefined
        }, settings);

        SmartMSGboxCount = SmartMSGboxCount + 1;

        if (ExistMsg == 0) {
            ExistMsg = 1;
            SmartMSG = "<div class='divMessageBox animated fadeIn fast' id='MsgBoxBack'></div>";
            $("body").append(SmartMSG);

            if (isIE8orlower() == 1) {
                $("#MsgBoxBack").addClass("MessageIE");
            }
        }

        var InputType = "";
        var HasInput = 0;
        if (settings.input != undefined) {
            HasInput = 1;
            settings.input = settings.input.toLowerCase();

            switch (settings.input) {
            case "text":
                settings.inputValue = $.type(settings.inputValue) === 'string' ? settings.inputValue.replace(/'/g, "&#x27;") : settings.inputValue;
                InputType = "<input class='form-control' type='" + settings.input + "' id='txt" +
                    SmartMSGboxCount + "' placeholder='" + settings.placeholder + "' value='" + settings.inputValue + "'/><br/><br/>";
                break;
            case "password":
                InputType = "<input class='form-control' type='" + settings.input + "' id='txt" +
                    SmartMSGboxCount + "' placeholder='" + settings.placeholder + "'/><br/><br/>";
                break;

            case "select":
                if (settings.options == undefined) {
                    alert("For this type of input, the options parameter is required.");
                } else {
                    InputType = "<select class='form-control' id='txt" + SmartMSGboxCount + "'>";
                    for (var i = 0; i <= settings.options.length - 1; i++) {
                        if (settings.options[i] == "[") {
                            Name = "";
                        } else {
                            if (settings.options[i] == "]") {
                                NumBottons = NumBottons + 1;
                                Name = "<option>" + Name + "</option>";
                                InputType += Name;
                            } else {
                                Name += settings.options[i];
                            }
                        }
                    };
                    InputType += "</select>"
                }

                break;
            default:
                alert("That type of input is not handled yet");
            }

        }

        Content = "<div class='MessageBoxContainer animated fadeIn fast' id='Msg" + SmartMSGboxCount +
            "'>";
        Content += "<div class='MessageBoxMiddle'>";
        Content += "<span class='MsgTitle'>" + settings.title + "</span class='MsgTitle'>";
        Content += "<p class='pText'>" + settings.content + "</p>";
        Content += InputType;
        Content += "<div class='MessageBoxButtonSection'>";

        if (settings.buttons == undefined) {
            settings.buttons = "[Accept]";
        }

        settings.buttons = $.trim(settings.buttons);
        settings.buttons = settings.buttons.split('');

        var Name = "";
        var NumBottons = 0;
        if (settings.NormalButton == undefined) {
            settings.NormalButton = "#232323";
        }

        if (settings.ActiveButton == undefined) {
            settings.ActiveButton = "#ed145b";
        }

        for (var i = 0; i <= settings.buttons.length - 1; i++) {

            if (settings.buttons[i] == "[") {
                Name = "";
            } else {
                if (settings.buttons[i] == "]") {
                    NumBottons = NumBottons + 1;
                    Name = "<button id='bot" + NumBottons + "-Msg" + SmartMSGboxCount +
                        "' class='btn btn-default btn-sm botTempo'> " + Name + "</button>";
                    Content += Name;
                } else {
                    Name += settings.buttons[i];
                }
            }
        };

        Content += "</div></div></div>";
        //MessageBoxButtonSection / MessageBoxMiddle / MessageBoxContainer

        // alert(SmartMSGboxCount);
        if (SmartMSGboxCount > 1) {
            $(".MessageBoxContainer").hide().css("z-index", 99999);
        }

        $(".divMessageBox").append(Content);

        // Focus
        if (HasInput == 1) {
            $("#txt" + SmartMSGboxCount).focus();
        }

        $('.botTempo').hover(function () {
            var ThisID = $(this).attr('id');
            // alert(ThisID);
            // $("#"+ThisID).css("background-color", settings.ActiveButton);
        }, function () {
            var ThisID = $(this).attr('id');
            //$("#"+ThisID).css("background-color", settings.NormalButton);
        });

        // Callback and button Pressed
        $(".botTempo").click(function () {
            // Closing Method
            var ThisID = $(this).attr('id');
            var MsgBoxID = ThisID.substr(ThisID.indexOf("-") + 1);
            var Press = $.trim($(this).text());

            if (HasInput == 1) {
                if (typeof callback == "function") {
                    var IDNumber = MsgBoxID.replace("Msg", "");
                    var Value = $("#txt" + IDNumber).val();
                    if (callback)
                        callback(Press, Value);
                }
            } else {
                if (typeof callback == "function") {
                    if (callback)
                        callback(Press);
                }
            }

            $("#" + MsgBoxID).addClass("animated fadeOut fast");
            SmartMSGboxCount = SmartMSGboxCount - 1;

            if (SmartMSGboxCount == 0) {
                $("#MsgBoxBack").removeClass("fadeIn").addClass("fadeOut").delay(300).queue(function () {
                    ExistMsg = 0;
                    $(this).remove();
                });
            }
        });

    }



// Small Notification
var SmallBoxes = 0,
    SmallCount = 0,
    SmallBoxesAnchos = 0;


    $.smallBox = function (settings, callback) {
        var BoxSmall, content;
        settings = $.extend({
            title: "",
            content: "",
            icon: undefined,
            iconSmall: undefined,
            color: undefined,
            timeout: undefined,
            colortime: 1500,
            colors: undefined
        }, settings);

        SmallBoxes = SmallBoxes + 1;

        BoxSmall = ""

        var IconSection = "",
            CurrentIDSmallbox = "smallbox" + SmallBoxes;

        if (settings.iconSmall == undefined) {
            IconSection = "<div class='miniIcono'></div>";
        } else {
            IconSection = "<div class='miniIcono'><i class='miniPic " + settings.iconSmall +
                "'></i></div>";
        }

        if (settings.icon == undefined) {
            BoxSmall = "<div id='smallbox" + SmallBoxes +
                "' class='SmallBox animated fadeInRight fast'><div class='textoFull'><span>" + settings.title +
                "</span><p>" + settings.content + "</p></div>" + IconSection + "</div>";
        } else {
            BoxSmall = "<div id='smallbox" + SmallBoxes +
                "' class='SmallBox animated fadeInRight fast'><div class='foto'><i class='" + settings.icon +
                "'></i></div><div class='textoFoto'><span>" + settings.title + "</span><p>" + settings.content +
                "</p></div>" + IconSection + "</div>";
        }

        if (SmallBoxes == 1) {
            $("#divSmallBoxes").append(BoxSmall);
            SmallBoxesAnchos = $("#smallbox" + SmallBoxes).height() + 40;
        } else {
            var SmartExist = $(".SmallBox").size();
            if (SmartExist == 0) {
                $("#divSmallBoxes").append(BoxSmall);
                SmallBoxesAnchos = $("#smallbox" + SmallBoxes).height() + 40;
            } else {
                $("#divSmallBoxes").append(BoxSmall);
                $("#smallbox" + SmallBoxes).css("top", SmallBoxesAnchos);
                SmallBoxesAnchos = SmallBoxesAnchos + $("#smallbox" + SmallBoxes).height() + 20;

                $(".SmallBox").each(function (index) {

                    if (index == 0) {
                        $(this).css("top", 20);
                        heightPrev = $(this).height() + 40;
                        SmallBoxesAnchos = $(this).height() + 40;
                    } else {
                        $(this).css("top", heightPrev);
                        heightPrev = heightPrev + $(this).height() + 20;
                        SmallBoxesAnchos = SmallBoxesAnchos + $(this).height() + 20;
                    }

                });

            }
        }

        var ThisSmallBox = $("#smallbox" + SmallBoxes);

        // IE fix
        // if($.browser.msie) {
        //     // alert($("#"+CurrentIDSmallbox).css("height"));
        // }

        if (settings.color == undefined) {
            ThisSmallBox.css("background-color", "#004d60");
        } else {
            ThisSmallBox.css("background-color", settings.color);
        }

        var ColorTimeInterval;

        if (settings.colors != undefined && settings.colors.length > 0) {
            ThisSmallBox.attr("colorcount", "0");

            ColorTimeInterval = setInterval(function () {

                var ColorIndex = ThisSmallBox.attr("colorcount");

                ThisSmallBox.animate({
                    backgroundColor: settings.colors[ColorIndex].color,
                });

                if (ColorIndex < settings.colors.length - 1) {
                    ThisSmallBox.attr("colorcount", ((ColorIndex * 1) + 1));
                } else {
                    ThisSmallBox.attr("colorcount", 0);
                }

            }, settings.colortime);
        }

        if (settings.timeout != undefined) {

            setTimeout(function () {
                clearInterval(ColorTimeInterval);
                var ThisHeight = $(this).height() + 20;
                var ID = CurrentIDSmallbox;
                var ThisTop = $("#" + CurrentIDSmallbox).css('top');

                // SmallBoxesAnchos = SmallBoxesAnchos - ThisHeight;
                // $("#"+CurrentIDSmallbox).remove();

                if ($("#" + CurrentIDSmallbox + ":hover").length != 0) {
                    //Mouse Over the element
                    $("#" + CurrentIDSmallbox).on("mouseleave", function () {
                        SmallBoxesAnchos = SmallBoxesAnchos - ThisHeight;
                        $("#" + CurrentIDSmallbox).remove();
                        if (typeof callback == "function") {
                            if (callback)
                                callback();
                        }

                        var Primero = 1;
                        var heightPrev = 0;
                        $(".SmallBox").each(function (index) {

                            if (index == 0) {
                                $(this).animate({
                                    top: 20
                                }, 300);

                                heightPrev = $(this).height() + 40;
                                SmallBoxesAnchos = $(this).height() + 40;
                            } else {
                                $(this).animate({
                                    top: heightPrev
                                }, 350);

                                heightPrev = heightPrev + $(this).height() + 20;
                                SmallBoxesAnchos = SmallBoxesAnchos + $(this).height() + 20;
                            }

                        });
                    });
                } else {
                    clearInterval(ColorTimeInterval);
                    SmallBoxesAnchos = SmallBoxesAnchos - ThisHeight;

                    if (typeof callback == "function") {
                        if (callback)
                            callback();
                    }

                    $("#" + CurrentIDSmallbox).removeClass().addClass("SmallBox").animate({
                        opacity: 0
                    }, 300, function () {

                        $(this).remove();

                        var Primero = 1;
                        var heightPrev = 0;
                        $(".SmallBox").each(function (index) {

                            if (index == 0) {
                                $(this).animate({
                                    top: 20
                                }, 300);

                                heightPrev = $(this).height() + 40;
                                SmallBoxesAnchos = $(this).height() + 40;
                            } else {
                                $(this).animate({
                                    top: heightPrev
                                });

                                heightPrev = heightPrev + $(this).height() + 20;
                                SmallBoxesAnchos = SmallBoxesAnchos + $(this).height() + 20;
                            }

                        });
                    })
                }

            }, settings.timeout);
        }

        // Click Closing
        $("#smallbox" + SmallBoxes).bind('click', function () {
            clearInterval(ColorTimeInterval);
            if (typeof callback == "function") {
                if (callback)
                    callback();
            }

            var ThisHeight = $(this).height() + 20;
            var ID = $(this).attr('id');
            var ThisTop = $(this).css('top');

            SmallBoxesAnchos = SmallBoxesAnchos - ThisHeight;

            $(this).removeClass().addClass("SmallBox").animate({
                opacity: 0
            }, 300, function () {
                $(this).remove();

                var Primero = 1;
                var heightPrev = 0;

                $(".SmallBox").each(function (index) {

                    if (index == 0) {
                        $(this).animate({
                            top: 20,
                        }, 300);
                        heightPrev = $(this).height() + 40;
                        SmallBoxesAnchos = $(this).height() + 40;
                    } else {
                        $(this).animate({
                            top: heightPrev
                        }, 350);
                        heightPrev = heightPrev + $(this).height() + 20;
                        SmallBoxesAnchos = SmallBoxesAnchos + $(this).height() + 20;
                    }

                });
            })
        });

    }


// .Small Notification


function getInternetExplorerVersion() {
    var rv = -1;
    // Return value assumes failure.
    if (navigator.appName == 'Microsoft Internet Explorer') {
        var ua = navigator.userAgent;
        var re = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
        if (re.exec(ua) != null)
            rv = parseFloat(RegExp.$1);
    }
    return rv;
}

function checkVersion() {

    var msg = "You're not using Windows Internet Explorer.";
    var ver = getInternetExplorerVersion();
    if (ver > -1) {
        if (ver >= 8.0)
            msg = "You're using a recent copy of Windows Internet Explorer."
        else
            msg = "You should upgrade your copy of Windows Internet Explorer.";
    }
    alert(msg);

}

function isIE8orlower() {

    var msg = "0";
    var ver = getInternetExplorerVersion();
    if (ver > -1) {
        if (ver >= 9.0)
            msg = 0
        else
            msg = 1;
    }
    return msg;
    // alert(msg);
}