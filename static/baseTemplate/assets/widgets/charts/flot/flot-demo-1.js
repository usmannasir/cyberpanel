
$(function() {

    //Interacting with Data Points example

    var sin = [], cos = [];

    for (var i = 0; i < 354; i += 31) {
        sin.push([i, Math.random(i)]);
        cos.push([i, Math.random(i)]);
    }

    var plot = $.plot($("#data-example-1"),
        [{ data: sin, label: "Today" }, { data: cos, label: "Yesterday" }], {
            series: {

                shadowSize: 0,
                lines: {
                    show: true,
                    lineWidth: 2
                },
                points: { show: true }
            },
            grid: {
                labelMargin: 10,
                hoverable: true,
                clickable: true,
                borderWidth: 1,
                borderColor: 'rgba(82, 167, 224, 0.06)'
            },
            legend: {
                backgroundColor: '#fff'
            },
            yaxis: { tickColor: 'rgba(0, 0, 0, 0.06)', font: {color: 'rgba(0, 0, 0, 0.4)'}},
            xaxis: { tickColor: 'rgba(0, 0, 0, 0.06)', font: {color: 'rgba(0, 0, 0, 0.4)'}},
            colors: [getUIColor('success'), getUIColor('gray')],
            tooltip: true,
            tooltipOpts: {
                content: "x: %x, y: %y"
            }
        });

    var previousPoint = null;
    $("#data-example-1").bind("plothover", function (event, pos, item) {
        $("#x").text(pos.x.toFixed(2));
        $("#y").text(pos.y.toFixed(2));
    });

    $("#data-example-1").bind("plotclick", function (event, pos, item) {
        if (item) {
            $("#clickdata").text("You clicked point " + item.dataIndex + " in " + item.series.label + ".");
            plot.highlight(item.series, item.datapoint);
        }
    });


});


$(function() {

    // We use an inline data source in the example, usually data would
    // be fetched from a server

    var data = [],
        totalPoints = 300;

    function getRandomData() {

        if (data.length > 0)
            data = data.slice(1);

        // Do a random walk

        while (data.length < totalPoints) {

            var prev = data.length > 0 ? data[data.length - 1] : 50,
                y = prev + Math.random() * 10 - 5;

            if (y < 0) {
                y = 0;
            } else if (y > 100) {
                y = 100;
            }

            data.push(y);
        }

        // Zip the generated y values with the x values

        var res = [];
        for (var i = 0; i < data.length; ++i) {
            res.push([i, data[i]])
        }

        return res;
    }

    // Set up the control widget

    var updateInterval = 30;

    var plot = $.plot("#data-example-3", [ getRandomData() ], {

        series: {
            lines: {
                show: true,
                lineWidth: 2,
                fill: 0.5,
                fillColor: { colors: [ { opacity: 0.01 }, { opacity: 0.08 } ] }
            },
            shadowSize: 0   // Drawing is faster without shadows
        },
        grid: {
            labelMargin: 10,
            hoverable: true,
            clickable: true,
            borderWidth: 1,
            borderColor: 'rgba(82, 167, 224, 0.06)'
        },
        yaxis: {
            min: 0,
            max: 120,
            tickColor: 'rgba(0, 0, 0, 0.06)', font: {color: 'rgba(0, 0, 0, 0.4)'}},
        xaxis: { show: false },
        colors: [getUIColor('default'),getUIColor('gray')]
    });

    function update() {

        plot.setData([getRandomData()]);

        // Since the axes don't change, we don't need to call plot.setupGrid()

        plot.draw();
        setTimeout(update, updateInterval);
    }

    update();

});