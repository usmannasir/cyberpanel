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

/* Java script code to start/stop litespeed */

/** Navigate between Main / Access / Error / Email / FTP / ModSec log viewers. */
window.CyberPanelLogSources = window.CyberPanelLogSources || {
    routes: {
        cyberpanel: '/serverstatus/cyberCPMainLogFile',
        access: '/serverlogs/accessLogs',
        error: '/serverlogs/errorLogs',
        email: '/serverlogs/emaillogs',
        ftp: '/serverlogs/ftplogs',
        modSec: '/serverlogs/modSecAuditLogs'
    },
    bindScope: function ($scope, currentType) {
        $scope.selectedLogSource = currentType || '';
        $scope.changeLogSource = function () {
            var key = $scope.selectedLogSource;
            var dest = window.CyberPanelLogSources.routes[key];
            if (!key || !dest) {
                return;
            }
            if (window.location.pathname.replace(/\/$/, '') === dest.replace(/\/$/, '')) {
                return;
            }
            window.location.href = dest;
        };
    }
};

/* Java script code to read log file */

app.controller('readCyberCPLogFile', function ($scope, $http) {

    $scope.logFileLoading = false;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;
    CyberPanelLogSources.bindScope($scope, 'cyberpanel');


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

/* Java script code to read log file ends here */

/* Java script code to read log file ends here */

/* Services */


app.controller('securityrule', function ($scope, $http) {

    $scope.securityruleLoading = true;


    $scope.ActivateTags = ['Agents', 'AppsInitialization', 'Backdoor', 'Bruteforce', 'CWAF', 'Domains', 'Drupal', 'FilterASP',
        'FilterGen', 'FilterInFarme', 'FilterOther', 'FilterPHP', 'FiltersEnd', 'FilterSQL', 'Generic', 'HTTP', 'HTTPDoS',
        'Incoming', 'Initialzation', 'JComponent', 'Joomla', 'Other', 'OtherApps', 'PHPGen', 'Protocol', 'Request', 'RoRGen',
        'SQLi', 'WHMCS', 'WordPress', 'WPPlugin', 'XSS']

    $scope.DeactivatedTags = []


    $scope.toggleActivation = function (tag) {
        var index = $scope.ActivateTags.indexOf(tag);
        if (index > -1) {
            $scope.ActivateTags.splice(index, 1);
            $scope.DeactivatedTags.push(tag);
        } else {
            index = $scope.DeactivatedTags.indexOf(tag);
            if (index > -1) {
                $scope.DeactivatedTags.splice(index, 1);
                $scope.ActivateTags.push(tag);
            }
        }
    };


    $scope.applychanges = function () {

        $scope.securityruleLoading = false;
        url = "/serverstatus/securityruleUpdate";

        var data = {
            ActivateTags: $scope.ActivateTags,
            DeactivatedTags: $scope.DeactivatedTags,
            RuleID: $scope.ruleID,
            Regular_expressions: $scope.Regular_expressions

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.securityruleLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Done',
                    text: "Changes Applied",
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
            $scope.securityruleLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }
});

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
            } else {
                $scope.olsStatus = "Stopped";
                $scope.olsStats = false;
                $scope.olsStart = true;
                $scope.olsStop = false;
            }

            if (response.data.status.docker) {
                $scope.dockerStatus = "Running";
                $scope.dockerStart = false;
                $scope.dockerStop = true;
            } else {
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
            } else {
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
            } else {
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
            } else {
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
            } else {
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

function cpGroupInt(n) {
    n = Math.round(Number(n) || 0);
    var sign = n < 0 ? '-' : '';
    var s = String(Math.abs(n));
    var parts = [];
    while (s.length > 3) {
        parts.unshift(s.slice(-3));
        s = s.slice(0, -3);
    }
    if (s) {
        parts.unshift(s);
    }
    return sign + parts.join(' ');
}

function cpFormatMbLabel(val) {
    if (val === null || val === undefined || val === '') {
        return '0 MB';
    }
    var mode = (window.CPSizeDisplayUnit || 'auto');
    var s = String(val).trim();
    if (/^\d+(\.\d+)?\s*(B|KB|MB|GB|TB)$/i.test(s)) {
        return s.replace(/(\d)([A-Za-z])/g, '$1 $2');
    }
    var m = s.match(/^(\d+(?:\.\d+)?)\s*MB$/i);
    var mb;
    if (m) {
        mb = parseFloat(m[1]);
    } else if (/^\d+(\.\d+)?$/.test(s)) {
        mb = parseFloat(s);
    } else {
        return s;
    }
    if (!isFinite(mb) || mb < 0) {
        return '0 MB';
    }
    if (mode === 'MB') {
        return cpGroupInt(mb) + ' MB';
    }
    if (mode === 'GB') {
        var gbFixed = mb / 1024;
        if (Math.abs(gbFixed - Math.round(gbFixed)) < 0.005 && Math.abs(gbFixed) >= 10) {
            return cpGroupInt(Math.round(gbFixed)) + ' GB';
        }
        return gbFixed.toFixed(2) + ' GB';
    }
    var bytes = mb * 1024 * 1024;
    if (bytes >= 1024 * 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024 * 1024 * 1024)).toFixed(2) + ' TB';
    }
    if (bytes >= 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    }
    if (bytes >= 1024 * 1024) {
        if (mb >= 1000) {
            return cpGroupInt(mb) + ' MB';
        }
        return (Math.abs(mb - Math.round(mb)) < 0.005 ? cpGroupInt(Math.round(mb)) : mb.toFixed(2)) + ' MB';
    }
    if (bytes >= 1024) {
        return (bytes / 1024).toFixed(1) + ' KB';
    }
    return cpGroupInt(bytes) + ' B';
}

app.controller('topProcesses', function ($scope, $http, $timeout, $interval) {

    var refreshTimeoutPromise = null;
    var countdownPromise = null;
    var REFRESH_INTERVAL_MS = 10000;

    $scope.cyberPanelLoading = true;
    $scope.initialLoad = true;
    $scope.autoRefreshEnabled = true;
    $scope.isRefreshing = false;
    $scope.refreshIntervalSeconds = REFRESH_INTERVAL_MS / 1000;
    $scope.refreshCountdown = 0;

    function stopCountdown() {
        if (countdownPromise) {
            $interval.cancel(countdownPromise);
            countdownPromise = null;
        }
    }

    function startCountdown() {
        stopCountdown();
        if (!$scope.autoRefreshEnabled) {
            $scope.refreshCountdown = 0;
            return;
        }
        $scope.refreshCountdown = REFRESH_INTERVAL_MS / 1000;
        countdownPromise = $interval(function () {
            if ($scope.refreshCountdown > 0) {
                $scope.refreshCountdown -= 1;
            }
        }, 1000);
    }

    function scheduleRefresh() {
        if (refreshTimeoutPromise) {
            $timeout.cancel(refreshTimeoutPromise);
            refreshTimeoutPromise = null;
        }
        stopCountdown();
        if ($scope.autoRefreshEnabled) {
            startCountdown();
            refreshTimeoutPromise = $timeout($scope.topProcessesStatus, REFRESH_INTERVAL_MS);
        } else {
            $scope.refreshCountdown = 0;
        }
    }

    $scope.toggleAutoRefresh = function () {
        $scope.autoRefreshEnabled = !$scope.autoRefreshEnabled;
        if ($scope.autoRefreshEnabled) {
            scheduleRefresh();
        } else {
            if (refreshTimeoutPromise) {
                $timeout.cancel(refreshTimeoutPromise);
                refreshTimeoutPromise = null;
            }
            stopCountdown();
            $scope.refreshCountdown = 0;
        }
    };

    $scope.refreshNow = function () {
        if ($scope.isRefreshing) {
            return;
        }
        if (refreshTimeoutPromise) {
            $timeout.cancel(refreshTimeoutPromise);
            refreshTimeoutPromise = null;
        }
        stopCountdown();
        $scope.refreshCountdown = 0;
        $scope.topProcessesStatus();
    };

    $scope.$on('$destroy', function () {
        if (refreshTimeoutPromise) {
            $timeout.cancel(refreshTimeoutPromise);
        }
        stopCountdown();
    });

    $scope.topProcessesStatus = function () {

        if ($scope.isRefreshing) {
            return;
        }

        $scope.isRefreshing = true;
        stopCountdown();
        $scope.refreshCountdown = 0;
        if ($scope.initialLoad) {
            $scope.cyberPanelLoading = false;
        }

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
            $scope.isRefreshing = false;
            $scope.initialLoad = false;
            if (response.data.status === 1) {
                $scope.processes = JSON.parse(response.data.data);

                if (response.data.sizeDisplayUnit) {
                    try {
                        window.CPSizeDisplayUnit = response.data.sizeDisplayUnit;
                    } catch (e) {}
                }

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
                $scope.totalMemory = cpFormatMbLabel(response.data.totalMemory);
                $scope.freeMemory = cpFormatMbLabel(response.data.freeMemory);
                $scope.usedMemory = cpFormatMbLabel(response.data.usedMemory);
                $scope.buffCache = cpFormatMbLabel(response.data.buffCache);

                //Swap
                $scope.swapTotalMemory = cpFormatMbLabel(response.data.swapTotalMemory);
                $scope.swapFreeMemory = cpFormatMbLabel(response.data.swapFreeMemory);
                $scope.swapUsedMemory = cpFormatMbLabel(response.data.swapUsedMemory);
                $scope.swapBuffCache = cpFormatMbLabel(response.data.swapBuffCache);

                //Processes
                $scope.totalProcesses = response.data.totalProcesses;
                $scope.runningProcesses = response.data.runningProcesses;
                $scope.sleepingProcesses = response.data.sleepingProcesses;
                $scope.stoppedProcesses = response.data.stoppedProcesses;
                $scope.zombieProcesses = response.data.zombieProcesses;

                scheduleRefresh();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                scheduleRefresh();
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            $scope.isRefreshing = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
            scheduleRefresh();
        }

    };
    $scope.topProcessesStatus();

    $scope.killProcess = function (pid) {

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

///


app.controller('listOSPackages', function ($scope, $http, $timeout) {

    $scope.cyberpanelLoading = true;

    $scope.currentPage = 1;
    $scope.recordsToShow = 10;
    $scope.currentTab = 'upgrade';
    var globalType;
    var packageCache = {};
    var activeFetch = null;

    $scope.fetchPackages = function (type) {
        if (typeof type === 'undefined' || type === null || type === '') {
            type = 'installed';
        }
        $scope.currentTab = type;
        globalType = type;

        // Serve cached tab data instantly (All Packages is expensive)
        var cacheKey = type + '|' + $scope.currentPage + '|' + $scope.recordsToShow;
        if (packageCache[cacheKey]) {
            var cached = packageCache[cacheKey];
            $scope.allPackages = cached.allPackages;
            $scope.pagination = cached.pagination;
            $scope.fetchedPackages = cached.fetchedPackages;
            $scope.totalPackages = cached.totalPackages;
            $scope.cyberpanelLoading = true;
            return;
        }

        $scope.cyberpanelLoading = false;
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow,
            type: type
        };

        dataurl = "/serverstatus/fetchPackages";
        var fetchToken = {};
        activeFetch = fetchToken;

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            if (activeFetch !== fetchToken) {
                return; // stale response from another tab
            }
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                $scope.allPackages = JSON.parse(response.data.packages);
                $scope.pagination = response.data.pagination;
                $scope.fetchedPackages = response.data.fetchedPackages;
                $scope.totalPackages = response.data.totalPackages;
                packageCache[cacheKey] = {
                    allPackages: $scope.allPackages,
                    pagination: $scope.pagination,
                    fetchedPackages: $scope.fetchedPackages,
                    totalPackages: $scope.totalPackages
                };
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialData(response) {
            if (activeFetch !== fetchToken) {
                return;
            }
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };
    // Available Updates first; All Packages loads only when that tab is selected
    $scope.fetchPackages('upgrade');

    $scope.fetchPackageDetails = function (packageFetch) {
        $scope.cyberpanelLoading = false;
        $scope.package = packageFetch;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            package: packageFetch
        };

        dataurl = "/serverstatus/fetchPackageDetails";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                $scope.packageDetails = response.data.packageDetails;
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.updatePackage = function (packageToUpgrade = 'all') {
        $scope.cyberpanelLoading = false;
        $scope.package = packageToUpgrade;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            package: packageToUpgrade
        };

        dataurl = "/serverstatus/updatePackage";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                getRequestStatus();
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    function getRequestStatus() {

        $scope.cyberpanelLoading = false;

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
                $timeout.cancel();
                $scope.cyberpanelLoading = true;
                $scope.requestData = response.data.requestStatus;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    }

    $scope.lockStatus = function (lockPackage, type) {
        $scope.cyberpanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            package: lockPackage,
            type: type,
        };

        dataurl = "/serverstatus/lockStatus";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Status updated.',
                    type: 'success'
                });
                $scope.fetchPackages(globalType);
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

});

app.controller('changePort', function ($scope, $http, $timeout) {

    $scope.cyberpanelLoading = false;

    $scope.changeCPPort = function () {
        $scope.cyberpanelLoading = true;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            port: $scope.port
        };

        dataurl = "/serverstatus/submitPortChange";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = false;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Port changed, open CyberPanel on new port.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please try again.',
                type: 'error'
            });
        }


    };

});