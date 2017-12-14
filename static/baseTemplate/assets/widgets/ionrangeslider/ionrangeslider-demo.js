/* Ion RangeSlider */

$(function() {
    "use strict";
    $("#ion-slider-basic").ionRangeSlider({
        min: 0,
        max: 5000,
        type: 'double',
        prefix: "$",
        maxPostfix: "+",
        prettify: false,
        hasGrid: true,
        gridMargin: 7
    });
});

$(function() {
    "use strict";
    $("#ion-slider-money").ionRangeSlider({
        min: 1000,
        max: 100000,
        from: 30000,
        to: 90000,
        type: 'double',
        step: 500,
        postfix: " €",
        hasGrid: true,
        gridMargin: 15
    });
});

$(function() {
    "use strict";
    $("#ion-slider-carat").ionRangeSlider({
        min: 0,
        max: 10,
        type: 'single',
        step: 0.1,
        postfix: " carats",
        prettify: false,
        hasGrid: true
    });
});

$(function() {
    "use strict";
    $("#ion-slider-date").ionRangeSlider({
        values: [
            "January", "February",
            "March", "April",
            "May", "June",
            "July", "August",
            "September", "October",
            "November", "December"
        ],
        type: 'single',
        hasGrid: true
    });
});

$(function() {
    "use strict";

    $("#ion-slider-console").ionRangeSlider({
        min: 1000000,
        max: 100000000,
        type: "double",
        postfix: " pounds",
        step: 10000,
        from: 25000000,
        to: 35000000,
        onChange: function(obj) {
            delete obj.input;
            delete obj.slider;
            var t = "Range Slider value: " + JSON.stringify(obj, "", 2);

            $("#result").html(t);
        },
        onLoad: function(obj) {
            delete obj.input;
            delete obj.slider;
            var t = "Range Slider value: " + JSON.stringify(obj, "", 2);

            $("#result").html(t);
        }
    });

    $("#updateLast").on("click", function() {

        $("#example_8").ionRangeSlider("update", {
            min: Math.round(10000 + Math.random() * 40000),
            max: Math.round(200000 + Math.random() * 100000),
            step: 1,
            from: Math.round(40000 + Math.random() * 40000),
            to: Math.round(150000 + Math.random() * 80000)
        });

    });

});
