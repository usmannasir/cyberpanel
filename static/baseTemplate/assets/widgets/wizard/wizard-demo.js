/* Form wizard */

$(function() {
    "use strict";
    $('#form-wizard-1').bootstrapWizard({
        'tabClass': 'nav nav-pills'
    });
});

$(function() {
    "use strict";
    $('#form-wizard-2').bootstrapWizard({
        'tabClass': 'list-group list-group-separator row list-group-icons list-group-centered',
        'nextSelector': '.button-next',
        'previousSelector': '.button-previous',
        'firstSelector': '.button-first',
        'lastSelector': '.button-last'
    });
});

$(function() {
    "use strict";
    $('#form-wizard-3').bootstrapWizard({
        'tabClass': ''
    });
});
