/* Custom Inputs */

$(function() { "use strict";

    $('input[type="checkbox"].custom-checkbox').uniform();
    $('input[type="radio"].custom-radio').uniform();
    $('.custom-select').uniform();

    $(".selector").append('<i class="glyph-icon icon-caret-down"></i>');

    $('.checker span').append('<i class="glyph-icon icon-check"></i>');
    $('.radio span').append('<i class="glyph-icon icon-circle"></i>');

});
