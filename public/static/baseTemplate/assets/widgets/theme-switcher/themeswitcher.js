/* Admin layout options */

$(document).on('ready', function() {

    $('#theme-switcher-wrapper .switch-toggle').on('click', this, function() {
        var dataToggle = $(this).prev().attr('data-toggletarget');
        $('body').toggleClass(dataToggle);

        if ( dataToggle = 'closed-sidebar' ) {
            $('#close-sidebar .glyph-icon').toggleClass('icon-angle-right').toggleClass('icon-angle-left');
        }
    });

    $('.switch-toggle[id="#boxed-layout"]').click(function(){

        if ( $('#boxed-layout').attr("checked") ) {
            $('.boxed-bg-wrapper').slideDown();
        } else {
            $('.boxed-bg-wrapper').slideUp();
        }

    });
});

/* Open theme switcher */

$(function() {

    $(".theme-switcher").click(function() {
        $("#theme-options").toggleClass('active');
    });

});

/* Admin header style */

$(function() {

    $('.set-adminheader-style').click(function() {
        $('.set-adminheader-style').removeClass('active');
        $(this).addClass('active');
        var newBg = $(this).attr('data-header-bg');
        $("#page-header").removeClass(function(index, css) {
            return (css.match(/(^|\s)bg-\S+/g) || []).join(' ');
        });
        $("#page-header").removeClass(function(index, css) {
            return (css.match(/(^|\s)font-\S+/g) || []).join(' ');
        });
        $('#page-header').addClass(newBg);
    });

});

/* Admin sidebar style */

$(function() {

    $('.set-sidebar-style').click(function() {
        $('.set-sidebar-style').removeClass('active');
        $(this).addClass('active');
        var newBg = $(this).attr('data-header-bg');
        $("#page-sidebar").removeClass(function(index, css) {
            return (css.match(/(^|\s)bg-\S+/g) || []).join(' ');
        });
        $("#page-sidebar").removeClass(function(index, css) {
            return (css.match(/(^|\s)font-\S+/g) || []).join(' ');
        });
        $('#page-sidebar').addClass(newBg);
    });

});

/* Boxed layout background style */

$(function() {

    $('.set-background-style').click(function() {
        $('.set-background-style').removeClass('active');
        $(this).addClass('active');
        var newBg = $(this).attr('data-header-bg');
        $("body").removeClass(function(index, css) {
            return (css.match(/(^|\s)pattern-\S+/g) || []).join(' ');
        });
        $("body").removeClass(function(index, css) {
            return (css.match(/(^|\s)full-\S+/g) || []).join(' ');
        });
        $("body").removeClass(function(index, css) {
            return (css.match(/(^|\s)bg-\S+/g) || []).join(' ');
        });
        $("body").removeClass(function(index, css) {
            return (css.match(/(^|\s)fixed-\S+/g) || []).join(' ');
        });
        $('body').addClass(newBg);
    });

});

/* Frontend header style */

$(function() {

    $('.set-header-style').click(function() {
        $('.set-header-style').removeClass('active');
        $(this).addClass('active');
        var newBg = $(this).attr('data-header-bg');
        $(".main-header").removeClass(function(index, css) {
            return (css.match(/(^|\s)bg-\S+/g) || []).join(' ');
        });
        $(".main-header").removeClass(function(index, css) {
            return (css.match(/(^|\s)font-\S+/g) || []).join(' ');
        });
        $('.main-header').addClass(newBg);
    });

});

/* Frontend footer style */

$(function() {

    $('.set-footer-style').click(function() {
        $('.set-footer-style').removeClass('active');
        $(this).addClass('active');
        var newBg = $(this).attr('data-header-bg');
        $(".main-footer").removeClass(function(index, css) {
            return (css.match(/(^|\s)bg-\S+/g) || []).join(' ');
        });
        $(".main-footer").removeClass(function(index, css) {
            return (css.match(/(^|\s)font-\S+/g) || []).join(' ');
        });
        $('.main-footer').addClass(newBg);
    });

});


/* Frontend top menu style */

$(function() {

    $('.set-topmenu-style').click(function() {
        $('.set-topmenu-style').removeClass('active');
        $(this).addClass('active');
        var newBg = $(this).attr('data-header-bg');
        $(".top-bar").removeClass(function(index, css) {
            return (css.match(/(^|\s)bg-\S+/g) || []).join(' ');
        });
        $(".top-bar").removeClass(function(index, css) {
            return (css.match(/(^|\s)font-\S+/g) || []).join(' ');
        });
        $('.top-bar').addClass(newBg);
    });

});

/* Theme styler scroll */

$(function() {

    $('.scroll-switcher').slimscroll({
        height: '100%',
        color: 'rgba(0,0,0,0.3)',
        size: '10px',
        alwaysVisible: true
    });
    //
    //$(".scroll-switcher").slimScroll({
    //    destroy: true
    //});

});

function swither_resizer() {
    var windowHeight = $(window).height();
    $('#theme-switcher-wrapper').height(windowHeight / 1.4);
}

$(document).on('ready', function() {
    swither_resizer();
});

$(window).on('resize', function() {
    swither_resizer();
});