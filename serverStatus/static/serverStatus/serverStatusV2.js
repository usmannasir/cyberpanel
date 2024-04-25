newapp.controller('readCyberCPLogFileV2', function ($scope, $http) {

    $scope.logFileLoading = false;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;


    var url = "/serverstatus/getFurtherDataFromLogFile";

    var data = {};

    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


    function ListInitialDatas(response) {


        if (response.data.logstatus == 1) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = false;
            $scope.couldNotFetchLogs = true;

            $scope.logsData = response.data.logsdata;


        } else {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;


        }


    }

    function cantLoadInitialDatas(response) {

        $scope.logFileLoading = true;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = false;

    }


    $scope.fetchLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverstatus/getFurtherDataFromLogFile";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.logstatus == 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = response.data.logsdata;


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }


    };

});
newapp.controller('litespeedStatusV2', function ($scope, $http) {

    $scope.restartorStopLoading = true;
    $scope.actionResult = true;
    $scope.actionResultBad = true;
    $scope.serverStatusCouldNotConnect = true;


    $scope.restartLitespeed = function () {


        $scope.disableReboot = true;
        $scope.disableStop = true;
        $scope.restartorStopLoading = false;


        var url = "/serverstatus/startorstopLitespeed";

        var data = {
            reboot: 1,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.restartorStopLoading = true;
            $scope.disableReboot = false;
            $scope.disableStop = false;

            if (response.data.reboot == 1) {

                $scope.restartorStopLoading = true;
                $scope.actionResult = false;
                $scope.actionResultBad = true;
                $scope.serverStatusCouldNotConnect = true;

            } else {

                $scope.restartorStopLoading = true;
                $scope.actionResult = true;
                $scope.actionResultBad = false;
                $scope.serverStatusCouldNotConnect = true;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.restartorStopLoading = true;
            $scope.actionResult = true;
            $scope.actionResultBad = true;
            $scope.serverStatusCouldNotConnect = false;
            $scope.disableReboot = false;
            $scope.disableStop = false;
        }


    };

    $scope.stopLitespeed = function () {


        $scope.disableReboot = true;
        $scope.disableStop = true;
        $scope.restartorStopLoading = false;


        var url = "/serverstatus/startorstopLitespeed";

        var data = {
            reboot: 0,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.restartorStopLoading = true;
            $scope.disableReboot = false;
            $scope.disableStop = false;

            if (response.data.shutdown == 1) {

                $scope.restartorStopLoading = true;
                $scope.actionResult = false;
                $scope.actionResultBad = true;
                $scope.serverStatusCouldNotConnect = true;

            } else {

                $scope.restartorStopLoading = true;
                $scope.actionResult = true;
                $scope.actionResultBad = false;
                $scope.serverStatusCouldNotConnect = true;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.restartorStopLoading = true;
            $scope.actionResult = true;
            $scope.actionResultBad = true;
            $scope.serverStatusCouldNotConnect = false;
            $scope.disableReboot = false;
            $scope.disableStop = false;
        }


    };

    /// License Manager

    $scope.cpLoading = true;
    $scope.fetchedData = true;
    $scope.changeSerialBox = true;

    $scope.hideLicenseStatus = function () {
        $scope.fetchedData = true;
    };

    $scope.licenseStatus = function () {

        $scope.cpLoading = false;
        $scope.changeSerialBox = true;

        var url = "/serverstatus/licenseStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.cpLoading = true;
                $scope.fetchedData = false;
                new PNotify({
                    title: 'Success!',
                    text: 'Status successfully fetched',
                    type: 'success'
                });
                $scope.lsSerial = response.data.lsSerial;
                $scope.lsexpiration = response.data.lsexpiration;
            } else {
                $scope.cpLoading = true;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.erroMessage,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cpLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    };
    $scope.showSerialBox = function () {
        $scope.fetchedData = true;
        $scope.changeSerialBox = false;
    };
    $scope.changeLicense = function () {

        $scope.cpLoading = false;

        var url = "/serverstatus/changeLicense";

        var data = {newKey: $scope.newKey};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.cpLoading = true;
                new PNotify({
                    title: 'Success!',
                    text: 'License successfully Updated',
                    type: 'success'
                });
            } else {
                $scope.cpLoading = true;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.erroMessage,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cpLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    };

    $scope.refreshLicense = function () {

        $scope.cpLoading = false;

        var url = "/serverstatus/refreshLicense";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        data = {};


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.cpLoading = true;
                new PNotify({
                    title: 'Success!',
                    text: 'License successfully refreshed',
                    type: 'success'
                });
            } else {
                $scope.cpLoading = true;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.erroMessage,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cpLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    };

});

newapp.controller('lswsSwitchV2', function ($scope, $http, $timeout, $window) {


    $scope.cyberPanelLoading = true;
    $scope.installBoxGen = true;

    $scope.confrimtril = function () {
        $('#confrimtril').show();
    }

    $scope.switchTOLSWS = function () {

        $scope.cyberPanelLoading = false;
        $scope.installBoxGen = true;

        url = "/serverstatus/switchTOLSWS";

        var data = {
            licenseKey: $scope.licenseKey
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
            } else {
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
newapp.controller('topProcessesV2', function ($scope, $http, $timeout) {

    $scope.cyberPanelLoading = true;

    $scope.topProcessesStatus = function () {

        $scope.cyberPanelLoading = false;

        url = "/serverstatus/topProcessesStatus";

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
                $scope.processes = JSON.parse(response.data.data);

                //CPU Details
                $scope.cores = response.data.cores;
                $scope.modelName = response.data.modelName;
                $scope.cpuMHZ = response.data.cpuMHZ;
                $scope.cacheSize = response.data.cacheSize;

                //CPU Load
                $scope.cpuNow = response.data.cpuNow;
                $scope.cpuOne = response.data.cpuOne;
                $scope.cpuFive = response.data.cpuFive;
                $scope.cpuFifteen = response.data.cpuFifteen;

                //CPU Time spent
                $scope.ioWait = response.data.ioWait;
                $scope.idleTime = response.data.idleTime;
                $scope.hwInterrupts = response.data.hwInterrupts;
                $scope.Softirqs = response.data.Softirqs;

                //Memory
                $scope.totalMemory = response.data.totalMemory;
                $scope.freeMemory = response.data.freeMemory;
                $scope.usedMemory = response.data.usedMemory;
                $scope.buffCache = response.data.buffCache;

                //Swap
                $scope.swapTotalMemory = response.data.swapTotalMemory;
                $scope.swapFreeMemory = response.data.swapFreeMemory;
                $scope.swapUsedMemory = response.data.swapUsedMemory;
                $scope.swapBuffCache = response.data.swapBuffCache;

                //Processes
                $scope.totalProcesses = response.data.totalProcesses;
                $scope.runningProcesses = response.data.runningProcesses;
                $scope.sleepingProcesses = response.data.sleepingProcesses;
                $scope.stoppedProcesses = response.data.stoppedProcesses;
                $scope.zombieProcesses = response.data.zombieProcesses;

                $timeout($scope.topProcessesStatus, 3000);
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
    $scope.topProcessesStatus();

    $scope.killProcess = function (pid) {

        $scope.cyberPanelLoading = false;

        url = "/serverstatus/killProcess";

        var data = {
            pid: pid
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
                    text: 'Process successfully killed.',
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