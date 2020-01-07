app.controller('installCageFS', function ($scope, $http, $timeout, $window) {

    $scope.installDockerStatus = true;
    $scope.installBoxGen = true;
    $scope.dockerInstallBTN = false;

    $scope.submitCageFSInstall = function () {

        $scope.installDockerStatus = false;
        $scope.installBoxGen = true;
        $scope.dockerInstallBTN = true;

        url = "/CloudLinux/submitCageFSInstall";

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
            } else {
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
        $scope.installDockerStatus = false;

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
            } else {
                // Notifications
                $scope.installDockerStatus = true;
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
            $scope.installDockerStatus = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });


        }

    }
});

app.controller('listWebsitesCage', function ($scope, $http) {

    var globalPageNumber;
    $scope.getFurtherWebsitesFromDB = function (pageNumber) {
        $scope.cyberPanelLoading = false;
        globalPageNumber = pageNumber;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {page: pageNumber};


        dataurl = "/CloudLinux/submitWebsiteListing";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.listWebSiteStatus === 1) {
                var finalData = JSON.parse(response.data.data);
                $scope.WebSitesList = finalData;
                $scope.pagination = response.data.pagination;
                $scope.default = response.data.default;
                $("#listFail").hide();
            } else {
                $("#listFail").fadeIn();
                $scope.errorMessage = response.data.error_message;
                console.log(response.data);

            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberPanelLoading = true;
            console.log("not good");
        }


    };
    $scope.getFurtherWebsitesFromDB(1);

    $scope.cyberPanelLoading = true;

    $scope.searchWebsites = function () {

        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            patternAdded: $scope.patternAdded
        };

        dataurl = "/websites/searchWebsites";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.listWebSiteStatus === 1) {

                var finalData = JSON.parse(response.data.data);
                $scope.WebSitesList = finalData;
                $("#listFail").hide();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Connect disrupted, refresh the page.',
                type: 'error'
            });
        }


    };

    $scope.enableOrDisable = function (domain, all, mode, toggle = 0) {
        $scope.cyberPanelLoading = false;

        url = "/CloudLinux/enableOrDisable";

        var data = {
            domain: domain,
            all: all,
            mode: mode,
            toggle: toggle
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
                    text: response.data.success,
                    type: 'success'
                });

                if (all === 0) {
                    $scope.getFurtherWebsitesFromDB(globalPageNumber);
                }
            } else {
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

    $scope.refreshStatus = function () {
        $scope.getFurtherWebsitesFromDB(globalPageNumber);
    }


});

app.controller('createCLPackage', function ($scope, $http) {

    $scope.cyberPanelLoading = true;
    $scope.modifyPackageForm = true;
    $scope.toggleView = function () {
        $scope.modifyPackageForm = false;
    };

    $scope.createPackage = function () {
        $scope.cyberPanelLoading = false;

        url = "/CloudLinux/submitCreatePackage";

        var data = {
            selectedPackage: $scope.selectedPackage,
            name: $scope.name,
            SPEED: $scope.SPEED,
            VMEM: $scope.VMEM,
            PMEM: $scope.PMEM,
            IO: $scope.IO,
            IOPS: $scope.IOPS,
            EP: $scope.EP,
            NPROC: $scope.NPROC,
            INODESsoft: $scope.INODESsoft,
            INODEShard: $scope.INODEShard,
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
                    text: 'Successfully created.',
                    type: 'success'
                });
            } else {
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

app.controller('listCloudLinuxPackages', function ($scope, $http) {

    $scope.cyberPanelLoading = true;

    $scope.fetchPackageas = function () {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {};


        dataurl = "/CloudLinux/fetchPackages";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.packages = JSON.parse(response.data.data);
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };
    $scope.fetchPackageas();

    $scope.deleteCLPackage = function (name) {
        $scope.cyberPanelLoading = false;

        url = "/CloudLinux/deleteCLPackage";

        var data = {
            name: name
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
                    text: 'Successfully deleted.',
                    type: 'success'
                });
                $scope.fetchPackageas();
            } else {
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
    $scope.populatePackage = function (name, speed, vmem, pmem, io, iops, ep, nproc, inodessoft, inodeshard) {
        $scope.name = name;
        $scope.SPEED = speed;
        $scope.VMEM = vmem;
        $scope.PMEM = pmem;
        $scope.IO = io;
        $scope.IOPS = iops;
        $scope.EP = ep;
        $scope.NPROC = nproc;
        $scope.inodessoft = inodessoft;
        $scope.inodeshard = inodeshard;

    };

    $scope.saveSettings = function () {
        $scope.cyberPanelLoading = false;

        url = "/CloudLinux/saveSettings";

        var data = {
            name: $scope.name,
            SPEED: $scope.SPEED,
            VMEM: $scope.VMEM,
            PMEM: $scope.PMEM,
            IO: $scope.IO,
            IOPS: $scope.IOPS,
            EP: $scope.EP,
            NPROC: $scope.NPROC,
            INODESsoft: $scope.inodessoft,
            INODEShard: $scope.inodeshard,
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
                $scope.fetchPackageas();
            } else {
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


app.controller('websiteContainerLimitCL', function ($scope, $http, $timeout, $window) {


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
            url: "/CloudLinux/getUsageData",
            dataType: 'json',
            success: update,
            type: "POST",
            headers: {'X-CSRFToken': getCookie('csrftoken')},
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
            url: "/CloudLinux/getUsageData",
            dataType: 'json',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
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
            url: "/CloudLinux/getUsageData",
            dataType: 'json',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
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
            {
                label: "Read IO/s " + _data.readRate + " mb/s ",
                data: readRate,
                lines: {fill: true, lineWidth: 1.2},
                color: "#00FF00"
            },
            {
                label: "Write IO/s " + _data.writeRate + " mb/s ",
                data: writeRate,
                lines: {lineWidth: 1.2},
                color: "#FF0000"
            }
        ];

        $.plot($("#diskUsage"), datasetDisk, optionsDisk);
        setTimeout(GetDataDisk, updateIntervalDisk);
    }


    $(document).ready(function () {

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

        // Report Disk Usage

        initDataDisk();

        datasetDisk = [
            {label: "Read IO/s: ", data: readRate, lines: {fill: true, lineWidth: 1.2}, color: "#00FF00"},
            {label: "Write IO/s: ", data: writeRate, color: "#0044FF", bars: {show: true}, yaxis: 2}
        ];

        $.plot($("#diskUsage"), datasetDisk, optionsDisk);
        setTimeout(GetDataDisk, updateIntervalDisk);
    });
});