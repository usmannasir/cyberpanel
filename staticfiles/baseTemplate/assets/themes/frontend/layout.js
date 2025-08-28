new WOW().init();

if (!(/Android|iPhone|iPad|iPod|BlackBerry|Windows Phone/i).test(navigator.userAgent || navigator.vendor || window.opera)) {
    skrollr.init({
        forceHeight: false,
        smoothScrolling: true
    });
}

jQuery(document).ready(function($) {

    /* Fixed header */

    $(function() {
        "use strict";

        $('.main-header-fixed .main-header').hcSticky({});

    });

    /* Sticky bars */

    $(function() {
        "use strict";

        $('.sticky-nav').hcSticky({
            top: 50
        });

    });

    /* Main nav */

    $(function() {
        "use strict";

        $('.header-nav > li').hover(function(){
            $(this).addClass('sfHover');
        },
        function(){
            $(this).removeClass('sfHover');
        });

        //$('.header-nav').superfish({
        //
        //});

    });

    /* Responsive nav */

    $(function() {
        "use strict";

        $('#responsive-menu').click(function() {
            $('.main-header ul.main-nav').toggle();
        });

    });

});
