/* Pie gauges */

var initPieChart = function() {

    $('.chart').easyPieChart({
        barColor: function(percent) {
            percent /= 100;
            return "rgb(" + Math.round(254 * (1 - percent)) + ", " + Math.round(255 * percent) + ", 0)";
        },
        animate: 1000,
        scaleColor: '#ccc',
        lineWidth: 3,
        size: 100,
        lineCap: 'cap',
        onStep: function(value) {
            this.$el.find('span').text(~~value);
        }
    });


    $('.chart-home').easyPieChart({
        barColor: 'rgba(255,255,255,0.5)',
        trackColor: 'rgba(255,255,255,0.1)',
        animate: 1000,
        scaleColor: 'rgba(255,255,255,0.3)',
        lineWidth: 3,
        size: 100,
        lineCap: 'cap',
        onStep: function(value) {
            this.$el.find('span').text(~~value);
        }
    });

    $('.chart-alt').easyPieChart({
        barColor: function(percent) {
            percent /= 100;
            return "rgb(" + Math.round(255 * (1 - percent)) + ", " + Math.round(255 * percent) + ", 0)";
        },
        trackColor: '#333',
        scaleColor: false,
        lineCap: 'butt',
        rotate: -90,
        lineWidth: 20,
        animate: 1500,
        onStep: function(value) {
            this.$el.find('span').text(~~value);
        }
    });

    $('.chart-alt-1').easyPieChart({
        barColor: function(percent) {
            percent /= 100;
            return "rgb(" + Math.round(255 * (1 - percent)) + ", " + Math.round(255 * percent) + ", 0)";
        },
        trackColor: '#e1ecf1',
        scaleColor: '#c4d7e0',
        lineCap: 'cap',
        rotate: -90,
        lineWidth: 10,
        size: 80,
        animate: 2500,
        onStep: function(value) {
            this.$el.find('span').text(~~value);
        }
    });

    $('.chart-alt-2').easyPieChart({
        barColor: function(percent) {
            percent /= 100;
            return "rgb(" + Math.round(255 * (1 - percent)) + ", " + Math.round(255 * percent) + ", 0)";
        },
        trackColor: '#fff',
        scaleColor: false,
        lineCap: 'butt',
        rotate: -90,
        lineWidth: 4,
        size: 50,
        animate: 1500,
        onStep: function(value) {
            this.$el.find('span').text(~~value);
        }
    });

    $('.chart-alt-3').easyPieChart({
        barColor: function(percent) {
            percent /= 100;
            return "rgb(" + Math.round(255 * (1 - percent)) + ", " + Math.round(255 * percent) + ", 0)";
        },
        trackColor: '#333',
        scaleColor: true,
        lineCap: 'butt',
        rotate: -90,
        lineWidth: 4,
        size: 50,
        animate: 1500,
        onStep: function(value) {
            this.$el.find('span').text(~~value);
        }
    });

    $('.chart-alt-10').easyPieChart({
        barColor: 'rgba(255,255,255,255.4)',
        trackColor: 'rgba(255,255,255,0.1)',
        scaleColor: 'transparent',
        lineCap: 'round',
        rotate: -90,
        lineWidth: 4,
        size: 100,
        animate: 2500,
        onStep: function(value) {
            this.$el.find('span').text(~~value);
        }
    });

    $('.updateEasyPieChart').on('click', function(e) {
        e.preventDefault();
        $('.chart-home, .chart, .chart-alt, .chart-alt-1, .chart-alt-2, .chart-alt-3, .chart-alt-10').each(function() {
            $(this).data('easyPieChart').update(Math.round(100 * Math.random()));
        });
    });
};

$(document).ready(function() {

    initPieChart();

});
