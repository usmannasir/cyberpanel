/**
 * Created by usman on 7/31/17.
 */



/* Java script code to start/stop litespeed */
app.controller('litespeedStatus', function ($scope, $http) {

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

            }
            else {

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

            }
            else {

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
            }
            else {
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
            }
            else {
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

/* Java script code to start/stop litespeed */

/* Java script code to read log file */

app.controller('readCyberCPLogFile', function ($scope, $http) {

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


        }
        else {

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


            }
            else {

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

/* Java script code to read log file ends here */

/* Java script code to read log file ends here */

/* Services */

app.controller('servicesManager', function ($scope, $http) {

    $scope.services = false;
    $scope.btnDisable = false;
    $scope.actionLoader = false;

    function getServiceStatus() {
        $scope.btnDisable = true;

        url = "/serverstatus/servicesStatus";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        data = {};

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status.litespeed) {
                $scope.olsStatus = "Running";
                $scope.olsStats = true;
                $scope.olsStart = false;
                $scope.olsStop = true;
                $scope.olsMem = Math.round(parseInt(response.data.memUsage.litespeed) / 1048576) + " MB";
            }
            else {
                $scope.olsStatus = "Stopped";
                $scope.olsStats = false;
                $scope.olsStart = true;
                $scope.olsStop = false;
            }

            if (response.data.status.docker) {
                $scope.dockerStatus = "Running";
                $scope.dockerStart = false;
                $scope.dockerStop = true;
            }
            else {
                $scope.dockerStatus = "Stopped";
                $scope.dockerStart = true;
                $scope.dockerStop = false;
            }

            // Update SQL stats
            if (response.data.status.mysql) {
                $scope.sqlStatus = "Running";
                $scope.sqlStats = true;
                $scope.sqlStart = false;
                $scope.sqlStop = true;
                $scope.sqlMem = Math.round(parseInt(response.data.memUsage.mysql) / 1048576) + " MB";
            }
            else {
                $scope.sqlStatus = "Stopped";
                $scope.sqlStats = false;
                $scope.sqlStart = true;
                $scope.sqlStop = false;
            }

            // Update DNS stats

            if (response.data.status.powerdns) {
                $scope.dnsStatus = "Running";
                $scope.dnsStats = true;
                $scope.dnsStart = false;
                $scope.dnsStop = true;
                $scope.dnsMem = Math.round(parseInt(response.data.memUsage.powerdns) / 1048576) + " MB";
            }
            else {
                $scope.dnsStatus = "Stopped";
                $scope.dnsStats = false;
                $scope.dnsStart = true;
                $scope.dnsStop = false;
            }

            // Update FTP stats

            if (response.data.status.pureftp) {
                $scope.ftpStatus = "Running";
                $scope.ftpStats = true;
                $scope.ftpStart = false;
                $scope.ftpStop = true;
                $scope.ftpMem = Math.round(parseInt(response.data.memUsage.pureftp) / 1048576) + " MB";
            }
            else {
                $scope.ftpStatus = "Stopped";
                $scope.ftpStats = false;
                $scope.ftpStart = true;
                $scope.ftpStop = false;
            }

            $scope.services = true;

            $scope.btnDisable = false;

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = true;

        }

    }
    getServiceStatus();

    $scope.serviceAction = function (serviceName, action) {
        $scope.ActionProgress = true;
        $scope.btnDisable = true;
        $scope.ActionSuccessfull = false;
        $scope.ActionFailed = false;
        $scope.couldNotConnect = false;
        $scope.actionLoader = true;

        url = "/serverstatus/servicesAction";

        var data = {
            service: serviceName,
            action: action
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response.data);

            if (response.data.serviceAction == 1) {
                setTimeout(function () {
                    getServiceStatus();
                    $scope.ActionSuccessfull = true;
                    $scope.ActionFailed = false;
                    $scope.couldNotConnect = false;
                    $scope.actionLoader = false;
                    $scope.btnDisable = false;
                }, 3000);
            }
            else {
                setTimeout(function () {
                    getServiceStatus();
                    $scope.ActionSuccessfull = false;
                    $scope.ActionFailed = true;
                    $scope.couldNotConnect = false;
                    $scope.actionLoader = false;
                    $scope.btnDisable = false;
                }, 5000);

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.ActionSuccessfull = false;
            $scope.ActionFailed = false;
            $scope.couldNotConnect = true;
            $scope.actionLoader = false;
            $scope.btnDisable = false;
        }

    }

});

app.controller('lswsSwitch', function ($scope, $http, $timeout, $window) {


    $scope.cyberPanelLoading = true;
    $scope.installBoxGen = true;

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

app.controller('topProcesses', function ($scope, $http, $timeout) {

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