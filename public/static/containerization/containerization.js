app.controller('installContainer', function ($scope, $http, $timeout, $window) {
    $scope.installDockerStatus = true;
    $scope.installBoxGen = true;
    $scope.dockerInstallBTN = false;

    $scope.submitContainerInstall = function () {

        $scope.installDockerStatus = false;
        $scope.installBoxGen = true;
        $scope.dockerInstallBTN = true;

        url = "/container/submitContainerInstall";

        var data = {};
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.installBoxGen = false;
                getRequestStatus();
            }
            else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };
    function getRequestStatus() {
        $scope.cyberPanelLoading = false;

        url = "/serverstatus/switchTOLSWSStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.abort === 0) {
                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            }
            else {
                // Notifications
                $scope.cyberPanelLoading = true;
                $timeout.cancel();
                $scope.requestData = response.data.requestStatus;
                if (response.data.installed === 1) {
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });


        }

    }
});


app.controller('websiteContainerLimit', function ($scope, $http, $timeout, $window) {


    // Get CPU Usage of User

    var cpu = [];
    var dataset;
    var totalPoints = 100;
    var updateInterval = 1000;
    var now = new Date().getTime();

    var options = {
        series: {
            lines: {
                lineWidth: 1.2
            },
            bars: {
                align: "center",
                fillColor: {colors: [{opacity: 1}, {opacity: 1}]},
                barWidth: 500,
                lineWidth: 1
            }
        },
        xaxis: {
            mode: "time",
            tickSize: [5, "second"],
            tickFormatter: function (v, axis) {
                var date = new Date(v);

                if (date.getSeconds() % 20 == 0) {
                    var hours = date.getHours() < 10 ? "0" + date.getHours() : date.getHours();
                    var minutes = date.getMinutes() < 10 ? "0" + date.getMinutes() : date.getMinutes();
                    var seconds = date.getSeconds() < 10 ? "0" + date.getSeconds() : date.getSeconds();

                    return hours + ":" + minutes + ":" + seconds;
                } else {
                    return "";
                }
            },
            axisLabel: "Time",
            axisLabelUseCanvas: true,
            axisLabelFontSizePixels: 12,
            axisLabelFontFamily: 'Verdana, Arial',
            axisLabelPadding: 10
        },
        yaxes: [
            {
                min: 0,
                max: 100,
                tickSize: 5,
                tickFormatter: function (v, axis) {
                    if (v % 10 == 0) {
                        return v + "%";
                    } else {
                        return "";
                    }
                },
                axisLabel: "CPU loading",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 6
            }, {
                max: 5120,
                position: "right",
                axisLabel: "Disk",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 6
            }
        ],
        legend: {
            noColumns: 0,
            position: "nw"
        },
        grid: {
            backgroundColor: {colors: ["#ffffff", "#EDF5FF"]}
        }
    };

    function initData() {
        for (var i = 0; i < totalPoints; i++) {
            var temp = [now += updateInterval, 0];

            cpu.push(temp);
        }
    }

    function GetData() {

        var data = {
            domain: $("#domain").text()
        };
        $.ajaxSetup({cache: false});

        $.ajax({
            url: "/container/getUsageData",
            dataType: 'json',
            success: update,
            type: "POST",
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            contentType: "application/json",
            data: JSON.stringify(data), // Our valid JSON string
            error: function () {
                setTimeout(GetData, updateInterval);
            }
        });
    }

    var temp;

    function update(_data) {
        cpu.shift();

        now += updateInterval;

        temp = [now, _data.cpu];
        cpu.push(temp);


        dataset = [
            {label: "CPU:" + _data.cpu + "%", data: cpu, lines: {fill: true, lineWidth: 1.2}, color: "#00FF00"}
        ];

        $.plot($("#flot-placeholder1"), dataset, options);
        setTimeout(GetData, updateInterval);
    }

    // Memory Usage of User

    var memory = [];
    var datasetMemory;
    var totalPointsMemory = 100;
    var updateIntervalMemory = 1000;
    var nowMemory = new Date().getTime();

    var optionsMemory = {
        series: {
            lines: {
                lineWidth: 1.2
            },
            bars: {
                align: "center",
                fillColor: {colors: [{opacity: 1}, {opacity: 1}]},
                barWidth: 500,
                lineWidth: 1
            }
        },
        xaxis: {
            mode: "time",
            tickSize: [5, "second"],
            tickFormatter: function (v, axis) {
                var date = new Date(v);

                if (date.getSeconds() % 20 == 0) {
                    var hours = date.getHours() < 10 ? "0" + date.getHours() : date.getHours();
                    var minutes = date.getMinutes() < 10 ? "0" + date.getMinutes() : date.getMinutes();
                    var seconds = date.getSeconds() < 10 ? "0" + date.getSeconds() : date.getSeconds();

                    return hours + ":" + minutes + ":" + seconds;
                } else {
                    return "";
                }
            },
            axisLabel: "Time",
            axisLabelUseCanvas: true,
            axisLabelFontSizePixels: 12,
            axisLabelFontFamily: 'Verdana, Arial',
            axisLabelPadding: 10
        },
        yaxes: [
            {
                min: 0,
                max: $scope.memory,
                tickSize: 5,
                tickFormatter: function (v, axis) {
                    if (v % 10 == 0) {
                        return v + "MB";
                    } else {
                        return "";
                    }
                },
                axisLabel: "CPU loading",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 6
            }, {
                max: 5120,
                position: "right",
                axisLabel: "Disk",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 6
            }
        ],
        legend: {
            noColumns: 0,
            position: "nw"
        },
        grid: {
            backgroundColor: {colors: ["#ffffff", "#EDF5FF"]}
        }
    };

    function initDataMemory() {
        for (var i = 0; i < totalPointsMemory; i++) {
            var temp = [nowMemory += updateIntervalMemory, 0];

            memory.push(temp);
        }
    }

    function GetDataMemory() {

        var data = {
            domain: $("#domain").text(),
            type: 'memory'
        };
        $.ajaxSetup({cache: false});

        $.ajax({
            url: "/container/getUsageData",
            dataType: 'json',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            success: updateMemory,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(data), // Our valid JSON string
            error: function () {
                setTimeout(GetDataMemory, updateIntervalMemory);
            }
        });
    }

    var tempMemory;

    function updateMemory(_data) {
        memory.shift();

        nowMemory += updateIntervalMemory;

        tempMemory = [nowMemory, _data.memory];
        memory.push(tempMemory);


        datasetMemory = [
            {
                label: "Memory:" + _data.memory + "MB",
                data: memory,
                lines: {fill: true, lineWidth: 1.2},
                color: "#00FF00"
            }
        ];

        $.plot($("#memoryUsage"), datasetMemory, optionsMemory);
        setTimeout(GetDataMemory, updateIntervalMemory);
    }

    // Disk Usage

    var readRate = [], writeRate = [];
    var datasetDisk;
    var totalPointsDisk = 100;
    var updateIntervalDisk = 5000;
    var now = new Date().getTime();

    var optionsDisk = {
        series: {
            lines: {
                lineWidth: 1.2
            },
            bars: {
                align: "center",
                fillColor: {colors: [{opacity: 1}, {opacity: 1}]},
                barWidth: 500,
                lineWidth: 1
            }
        },
        xaxis: {
            mode: "time",
            tickSize: [30, "second"],
            tickFormatter: function (v, axis) {
                var date = new Date(v);

                if (date.getSeconds() % 20 == 0) {
                    var hours = date.getHours() < 10 ? "0" + date.getHours() : date.getHours();
                    var minutes = date.getMinutes() < 10 ? "0" + date.getMinutes() : date.getMinutes();
                    var seconds = date.getSeconds() < 10 ? "0" + date.getSeconds() : date.getSeconds();

                    return hours + ":" + minutes + ":" + seconds;
                } else {
                    return "";
                }
            },
            axisLabel: "Time",
            axisLabelUseCanvas: true,
            axisLabelFontSizePixels: 12,
            axisLabelFontFamily: 'Verdana, Arial',
            axisLabelPadding: 10
        },
        yaxes: [
            {
                min: 0,
                max: $scope.networkSpeed,
                tickSize: 5,
                tickFormatter: function (v, axis) {
                    if (v % 10 == 0) {
                        return v + "mb/sec";
                    } else {
                        return "";
                    }
                },
                axisLabel: "CPU loading",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 6
            }, {
                max: 5120,
                position: "right",
                axisLabel: "Disk",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 6
            }
        ],
        legend: {
            noColumns: 0,
            position: "nw"
        },
        grid: {
            backgroundColor: {colors: ["#ffffff", "#EDF5FF"]}
        }
    };

    function initDataDisk() {
        for (var i = 0; i < totalPointsDisk; i++) {
            var temp = [now += updateIntervalDisk, 0];

            readRate.push(temp);
            writeRate.push(temp);
        }
    }

    function GetDataDisk() {

        var data = {
            domain: $("#domain").text(),
            type: 'io'
        };

        $.ajaxSetup({cache: false});

        $.ajax({
            url: "/container/getUsageData",
            dataType: 'json',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            success: updateDisk,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(data), // Our valid JSON string
            error: function () {
                setTimeout(GetDataMemory, updateIntervalMemory);
            }
        });
    }

    var tempDisk;

    function updateDisk(_data) {
        readRate.shift();
        writeRate.shift();

        now += updateIntervalDisk;

        tempDisk = [now, _data.readRate];
        readRate.push(tempDisk);

        tempDisk = [now, _data.readRate];
        writeRate.push(tempDisk);

        datasetDisk = [
            {label: "Read IO/s " + _data.readRate + " mb/s ", data: readRate, lines: {fill: true, lineWidth: 1.2}, color: "#00FF00"},
            {label: "Write IO/s " + _data.writeRate + " mb/s ", data: writeRate, lines: {lineWidth: 1.2}, color: "#FF0000"}
        ];

        $.plot($("#diskUsage"), datasetDisk, optionsDisk);
        setTimeout(GetDataDisk, updateIntervalDisk);
    }


    $(document).ready(function () {
        initDataDisk();

        datasetDisk = [
            {label: "Read IO/s: ", data: readRate, lines: {fill: true, lineWidth: 1.2}, color: "#00FF00"},
            {label: "Write IO/s: ", data: writeRate, color: "#0044FF", bars: {show: true}, yaxis: 2}
        ];

        $.plot($("#diskUsage"), datasetDisk, optionsDisk);
        setTimeout(GetDataDisk, updateIntervalDisk);
    });

    ////

    $scope.cyberPanelLoading = true;
    $scope.limitsInfoBox = true;

    $scope.fetchWebsiteLimits = function () {

        $scope.cyberPanelLoading = false;

        url = "/container/fetchWebsiteLimits";

        var data = {
            'domain': $("#domain").text()
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.cpuPers = response.data.cpuPers;
                $scope.IO = response.data.IO;
                $scope.IOPS = response.data.IOPS;
                $scope.memory = response.data.memory;
                $scope.networkSpeed = response.data.networkSpeed;

                if (response.data.enforce === 0) {
                    $scope.limitsInfoBox = false;
                } else {
                    $scope.limitsInfoBox = true;
                }


                // Report Memory Usage

                initDataMemory();

                datasetMemory = [
                    {label: "Memory", data: memory, lines: {fill: true, lineWidth: 1.2}, color: "#00FF00"}
                ];

                $.plot($("#memoryUsage"), datasetMemory, optionsMemory);
                setTimeout(GetDataMemory, updateIntervalMemory);

                // Report CPU Usage

                initData();

                dataset = [
                    {label: "CPU", data: cpu, lines: {fill: true, lineWidth: 1.2}, color: "#00FF00"}
                ];

                $.plot($("#flot-placeholder1"), dataset, options);
                setTimeout(GetData, updateInterval);
            }
            else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };
    $scope.fetchWebsiteLimits();

    $scope.saveWebsiteLimits = function () {

        $scope.cyberPanelLoading = false;

        url = "/container/saveWebsiteLimits";

        var data = {
            'domain': $("#domain").text(),
            'cpuPers': $scope.cpuPers,
            'IO': $scope.IO,
            'IOPS': $scope.IOPS,
            'memory': $scope.memory,
            'networkSpeed': $scope.networkSpeedBox,
            'networkHandle': $scope.networkHandle,
            'enforce': $scope.enforce
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes successfully applied.',
                    type: 'success'
                });
                $scope.fetchWebsiteLimits();
            }
            else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };


});