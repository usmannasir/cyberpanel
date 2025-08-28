$(document).ready(function(){

    /* Box switch toggle */

  $('.switch-button').click(function(ev){

    ev.preventDefault();

    var switchParent = $(this).attr('switch-parent');
    var switchTarget = $(this).attr('switch-target');

    $(switchParent).slideToggle();
    $(switchTarget).slideToggle();

  });

    /* Content Box Show/Hide Buttons */

  $('.hidden-button').hover(function(){

    $(".btn-hide", this).fadeIn('fast');

  },function(){

    $(".btn-hide", this).fadeOut('normal');

  });


  /* Content Box Toggle */

  $('.toggle-button').click(function(ev) {

    ev.preventDefault();

    $(".glyph-icon", this).toggleClass("icon-rotate-180");

    $(this).parents(".content-box:first").find(".content-box-wrapper").slideToggle();

  });

  /* Content Box Remove */

  $('.remove-button').click(function(ev){

      ev.preventDefault();

      var animationEFFECT = $(this).attr('data-animation');

      var animationTARGET = $(this).parents(".content-box:first");

      $(animationTARGET).addClass('animated');
      $(animationTARGET).addClass(animationEFFECT);

      var wait = window.setTimeout( function(){
        $(animationTARGET).slideUp()},
        500
      );

      /* Demo show removed content box */

      var wait2 = window.setTimeout( function(){
        $(animationTARGET).removeClass(animationEFFECT).fadeIn()},
        2500
      );

  });

  /* Close Info Boxes */

  $(function() { "use strict";

    $(".infobox-close").click(function(ev){

      ev.preventDefault();

      $(this).parent().fadeOut();

    });


  });

});