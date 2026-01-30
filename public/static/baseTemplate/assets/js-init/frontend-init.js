new WOW().init();
$(function() {
    var windowWidth = $(window).width();
    if(windowWidth > 767) {
        skrollr.init({
            mobileCheck: function () {
                return false;
            },
            forceHeight: false,
            smoothScrolling: true
        });
    }
});
jQuery(document).ready(function($) {

    /* Sticky bars */

    $(function() { "use strict";

        $('.sticky-nav').hcSticky({
            top: 50
        });

    });

});