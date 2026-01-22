/* jQuery UI Datepicker */

$(function() {
    "use strict";
    $("#fromDate").datepicker({
        defaultDate: "+1w",
        changeMonth: true,
        numberOfMonths: 3,
        onClose: function(selectedDate) {
            $("#toDate").datepicker("option", "minDate", selectedDate);
        }
    });
    $("#toDate").datepicker({
        defaultDate: "+1w",
        changeMonth: true,
        numberOfMonths: 3,
        onClose: function(selectedDate) {
            $("#fromDate").datepicker("option", "maxDate", selectedDate);
        }
    });
});

$(function() {
    "use strict";

    $("#datepicker_multiple_months").datepicker({
        numberOfMonths: 3,
        showButtonPanel: true
    });

});

$(function() {
    "use strict";
    $(".datepicker").datepicker();
});
