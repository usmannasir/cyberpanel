/* Progress bars */

function progress(percent, element) {
    var progressBarWidth = percent * element.width() / 100;

    element.find('.progressbar-value').animate({ width: progressBarWidth }, 1200);
}

$(document).on('ready', function() {

    $('.progressbar').each(function() {
        var bar = $(this);
        var max = $(this).attr('data-value');

        progress(max, bar);
    });

});

$(function(){

    $('#header-right, .updateEasyPieChart, .complete-user-profile, #progress-dropdown, .progress-box').hover(function () {

        $('.progressbar').each(function() {
            var bar = $(this);
            var max = $(this).attr('data-value');

            progress(max, bar);
        });

    });

});