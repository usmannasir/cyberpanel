/* Morris color bar */

$(function() {
    "use strict";
    Morris.Bar({
        element: 'color-bar',
        data: [{
            x: '2011 Q1',
            y: 0
        }, {
            x: '2011 Q2',
            y: 1
        }, {
            x: '2011 Q3',
            y: 2
        }, {
            x: '2011 Q4',
            y: 3
        }, {
            x: '2012 Q1',
            y: 4
        }, {
            x: '2012 Q2',
            y: 5
        }, {
            x: '2012 Q3',
            y: 6
        }, {
            x: '2012 Q4',
            y: 7
        }, {
            x: '2013 Q1',
            y: 8
        }],
        xkey: 'x',
        ykeys: ['y'],
        labels: ['Y'],
        barColors: function(row, series, type) {
            if (type === 'bar') {
                var red = Math.ceil(255 * row.y / this.ymax);
                return 'rgb(' + red + ',155,22)';
            } else {
                return '#000';
            }
        }
    });
});

/* Morris labels bar */

$(function() {
    "use strict";
    var day_data = [{
        "period": "2012-10-01",
        "licensed": 3407,
        "sorned": 660
    }, {
        "period": "2012-09-30",
        "licensed": 3351,
        "sorned": 629
    }, {
        "period": "2012-09-29",
        "licensed": 3269,
        "sorned": 618
    }, {
        "period": "2012-09-20",
        "licensed": 3246,
        "sorned": 661
    }, {
        "period": "2012-09-19",
        "licensed": 3257,
        "sorned": 667
    }, {
        "period": "2012-09-18",
        "licensed": 3248,
        "sorned": 627
    }, {
        "period": "2012-09-17",
        "licensed": 3171,
        "sorned": 660
    }, {
        "period": "2012-09-16",
        "licensed": 3171,
        "sorned": 676
    }, {
        "period": "2012-09-15",
        "licensed": 3201,
        "sorned": 656
    }, {
        "period": "2012-09-10",
        "licensed": 3215,
        "sorned": 622
    }];
    Morris.Bar({
        element: 'labels-bar',
        data: day_data,
        xkey: 'period',
        ykeys: ['licensed', 'sorned'],
        labels: ['Licensed', 'SORN'],
        xLabelAngle: 60
    });
});

/* Morris stacked bars */

$(function() {
    "use strict";
    Morris.Bar({
        element: 'stacked-bars',
        data: [{
            x: '2011 Q1',
            y: 3,
            z: 2,
            a: 3
        }, {
            x: '2011 Q2',
            y: 2,
            z: null,
            a: 1
        }, {
            x: '2011 Q3',
            y: 0,
            z: 2,
            a: 4
        }, {
            x: '2011 Q4',
            y: 2,
            z: 4,
            a: 3
        }],
        xkey: 'x',
        ykeys: ['y', 'z', 'a'],
        labels: ['Y', 'Z', 'A'],
        stacked: true
    });
});

/* Morris donut */

$(function() {
    "use strict";
    Morris.Donut({
        element: 'donut',
        backgroundColor: '#fff',
        labelColor: '#ccc',
        colors: [
            '#4fb2ff',
            '#929292',
            '#67C69D',
            '#ff9393'
        ],
        data: [{
            value: 70,
            label: 'foo',
            formatted: 'at least 70%'
        }, {
            value: 15,
            label: 'bar',
            formatted: 'approx. 15%'
        }, {
            value: 10,
            label: 'baz',
            formatted: 'approx. 10%'
        }, {
            value: 5,
            label: 'A really really long label',
            formatted: 'at most 5%'
        }],
        formatter: function(x, data) {
            return data.formatted;
        }
    });
});

/* Morris decimal data */

$(function() {
    "use strict";
    var decimal_data = [];
    for (var x = 0; x <= 360; x += 10) {
        decimal_data.push({
            x: x,
            y: 1.5 + 1.5 * Math.sin(Math.PI * x / 180).toFixed(4)
        });
    }
    window.m = Morris.Line({
        element: 'decimal-data',
        data: decimal_data,
        xkey: 'x',
        ykeys: ['y'],
        labels: ['sin(x)'],
        parseTime: false,
        hoverCallback: function(index, options, default_content) {
            var row = options.data[index];
            return default_content.replace("sin(x)", "1.5 + 1.5 sin(" + row.x + ")");
        },
        xLabelMargin: 10,
        integerYLabels: true
    });
});

/* Morris daytime */

$(function() {
    "use strict";
    Morris.Area({
        element: 'daytime-bars',
        data: [{
            x: '2013-03-30 22:00:00',
            y: 3,
            z: 3
        }, {
            x: '2013-03-31 00:00:00',
            y: 2,
            z: 0
        }, {
            x: '2013-03-31 02:00:00',
            y: 0,
            z: 2
        }, {
            x: '2013-03-31 04:00:00',
            y: 4,
            z: 4
        }],
        xkey: 'x',
        ykeys: ['y', 'z'],
        labels: ['Y', 'Z']
    });
});


/* Author:

*/

$(function() {
    // data stolen from http://howmanyleft.co.uk/vehicle/jaguar_'e'_type
    var tax_data = [{
        "period": "2011 Q3",
        "licensed": 3407,
        "sorned": 660
    }, {
        "period": "2011 Q2",
        "licensed": 3351,
        "sorned": 629
    }, {
        "period": "2011 Q1",
        "licensed": 3269,
        "sorned": 618
    }, {
        "period": "2010 Q4",
        "licensed": 3246,
        "sorned": 661
    }, {
        "period": "2009 Q4",
        "licensed": 3171,
        "sorned": 676
    }, {
        "period": "2008 Q4",
        "licensed": 3155,
        "sorned": 681
    }, {
        "period": "2007 Q4",
        "licensed": 3226,
        "sorned": 620
    }, {
        "period": "2006 Q4",
        "licensed": 3245,
        "sorned": null
    }, {
        "period": "2005 Q4",
        "licensed": 3289,
        "sorned": null
    }];
    Morris.Line({
        element: 'hero-graph',
        data: tax_data,
        xkey: 'period',
        ykeys: ['licensed', 'sorned'],
        labels: ['Licensed', 'Off the road']
    });

    Morris.Donut({
        element: 'hero-donut',
        data: [{
            label: 'Jam',
            value: 25
        }, {
            label: 'Frosted',
            value: 40
        }, {
            label: 'Custard',
            value: 25
        }, {
            label: 'Sugar',
            value: 10
        }],
        formatter: function(y) {
            return y + "%"
        }
    });

    Morris.Area({
        element: 'hero-area',
        data: [{
            period: '2010 Q1',
            iphone: 2666,
            ipad: null,
            itouch: 2647
        }, {
            period: '2010 Q2',
            iphone: 2778,
            ipad: 2294,
            itouch: 2441
        }, {
            period: '2010 Q3',
            iphone: 4912,
            ipad: 1969,
            itouch: 2501
        }, {
            period: '2010 Q4',
            iphone: 3767,
            ipad: 3597,
            itouch: 5689
        }, {
            period: '2011 Q1',
            iphone: 6810,
            ipad: 1914,
            itouch: 2293
        }, {
            period: '2011 Q2',
            iphone: 5670,
            ipad: 4293,
            itouch: 1881
        }, {
            period: '2011 Q3',
            iphone: 4820,
            ipad: 3795,
            itouch: 1588
        }, {
            period: '2011 Q4',
            iphone: 15073,
            ipad: 5967,
            itouch: 5175
        }, {
            period: '2012 Q1',
            iphone: 10687,
            ipad: 4460,
            itouch: 2028
        }, {
            period: '2012 Q2',
            iphone: 8432,
            ipad: 5713,
            itouch: 1791
        }],
        xkey: 'period',
        ykeys: ['iphone', 'ipad', 'itouch'],
        labels: ['iPhone', 'iPad', 'iPod Touch'],
        pointSize: 2,
        hideHover: 'auto'
    });

    Morris.Bar({
        element: 'hero-bar',
        data: [{
            device: 'iPhone',
            geekbench: 136
        }, {
            device: 'iPhone 3G',
            geekbench: 137
        }, {
            device: 'iPhone 3GS',
            geekbench: 275
        }, {
            device: 'iPhone 4',
            geekbench: 380
        }, {
            device: 'iPhone 4S',
            geekbench: 655
        }, {
            device: 'iPhone 5',
            geekbench: 1571
        }],
        xkey: 'device',
        ykeys: ['geekbench'],
        labels: ['Geekbench'],
        barRatio: 0.4,
        xLabelAngle: 35,
        hideHover: 'auto'
    });

});
