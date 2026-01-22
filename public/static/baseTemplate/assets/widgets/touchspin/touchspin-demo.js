$(function() { "use strict";
    $("input[name='touchspin-demo-1']").TouchSpin({
        min: 0,
        max: 100,
        step: 0.1,
        decimals: 2,
        boostat: 5,
        maxboostedstep: 10,
        postfix: '%'
    });
});

$(function() { "use strict";
    $("input[name='touchspin-demo-2']").TouchSpin({
        min: -1000000000,
        max: 1000000000,
        stepinterval: 50,
        maxboostedstep: 10000000,
        prefix: '$'
    });
});

$(function() { "use strict";
    $("input[name='touchspin-demo-3']").TouchSpin({
        verticalbuttons: true
    });
});

$(function() { "use strict";
    $("input[name='touchspin-demo-4']").TouchSpin({
        verticalbuttons: true,
        verticalupclass: 'glyph-icon icon-plus',
        verticaldownclass: 'glyph-icon icon-minus'
    });
});

