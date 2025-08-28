/**
 * Created by usman on 7/24/17.
 */

/* Utilities */


function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function randomPassword(length) {
    var chars = "abcdefghijklmnopqrstuvwxyz!@#%^*-+ABCDEFGHIJKLMNOP1234567890";
    var pass = "";
    for (var x = 0; x < length; x++) {
        var i = Math.floor(Math.random() * chars.length);
        pass += chars.charAt(i);
    }
    return pass;
}

/* Utilities ends here */

/* Java script code to monitor system status */

var app = angular.module('CyberCP', []);

var globalScope;

function GlobalRespSuccess(response) {
    globalScope.cyberPanelLoading = true;
    if (response.data.status === 1) {
        new PNotify({
            title: 'Success',
            text: 'Successfully executed.',
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

function GlobalRespFailed(response) {
    globalScope.cyberPanelLoading = true;
    new PNotify({
        title: 'Operation Failed!',
        text: 'Could not connect to server, please refresh this page',
        type: 'error'
    });
}

function GLobalAjaxCall(http, url, data, successCallBack, failureCallBack) {
    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };
    http.post(url, data, config).then(successCallBack, failureCallBack);
}

app.config(['$interpolateProvider', function ($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
}]);

app.filter('getwebsitename', function () {
    return function (domain, uppercase) {

        if (domain !== undefined) {

            domain = domain.replace(/-/g, '');

            var domainName = domain.split(".");

            var finalDomainName = domainName[0];

            if (finalDomainName.length > 5) {
                finalDomainName = finalDomainName.substring(0, 4);
            }

            return finalDomainName;
        }
    };
});

function getWebsiteName(domain) {
    if (domain !== undefined) {

        domain = domain.replace(/-/g, '');

        var domainName = domain.split(".");

        var finalDomainName = domainName[0];

        if (finalDomainName.length > 5) {
            finalDomainName = finalDomainName.substring(0, 4);
        }

        return finalDomainName;
    }
}

app.controller('systemStatusInfo', function ($scope, $http, $timeout) {

    $scope.uptimeLoaded = false;
    $scope.uptime = 'Loading...';
    
    getStuff();
    
    $scope.getSystemStatus = function() {
        getStuff();
    };

    function getStuff() {

        url = "/base/getSystemStatus";

        $http.get(url).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.cpuUsage = response.data.cpuUsage;
            $scope.ramUsage = response.data.ramUsage;
            $scope.diskUsage = response.data.diskUsage;
            
            // Total system information
            $scope.cpuCores = response.data.cpuCores;
            $scope.ramTotalMB = response.data.ramTotalMB;
            $scope.diskTotalGB = response.data.diskTotalGB;
            $scope.diskFreeGB = response.data.diskFreeGB;
            
            // Get uptime if available
            if (response.data.uptime) {
                $scope.uptime = response.data.uptime;
                $scope.uptimeLoaded = true;
            } else {
                // Fallback: try to get uptime separately
                $http.get("/base/getUptime").then(function(uptimeResponse) {
                    if (uptimeResponse.data.uptime) {
                        $scope.uptime = uptimeResponse.data.uptime;
                        $scope.uptimeLoaded = true;
                    }
                });
            }

        }

        function cantLoadInitialData(response) {
            $scope.uptime = 'Unavailable';
            $scope.uptimeLoaded = true;
        }

        $timeout(getStuff, 60000); // Update every minute

    }
});

/*  Admin status */

app.controller('adminController', function ($scope, $http, $timeout) {

    url = "/base/getAdminStatus";

    $http.get(url).then(ListInitialData, cantLoadInitialData);


    function ListInitialData(response) {


        $scope.currentAdmin = response.data.adminName;
        $scope.admin_type = response.data.admin_type;

        $("#serverIPAddress").text(response.data.serverIPAddress);

        if (response.data.admin === 0) {
            $('.serverACL').hide();


            if (!Boolean(response.data.versionManagement)) {
                $('.versionManagement').hide();
            }
            // User Management
            if (!Boolean(response.data.createNewUser)) {
                $('.createNewUser').hide();
            }
            if (!Boolean(response.data.listUsers)) {
                $('.listUsers').hide();
            }
            if (!Boolean(response.data.resellerCenter)) {
                $('.resellerCenter').hide();
            }
            if (!Boolean(response.data.deleteUser)) {
                $('.deleteUser').hide();
            }
            if (!Boolean(response.data.changeUserACL)) {
                $('.changeUserACL').hide();
            }
            // Website Management
            if (!Boolean(response.data.createWebsite)) {
                $('.createWebsite').hide();
            }

            if (!Boolean(response.data.modifyWebsite)) {
                $('.modifyWebsite').hide();
            }

            if (!Boolean(response.data.suspendWebsite)) {
                $('.suspendWebsite').hide();
            }

            if (!Boolean(response.data.deleteWebsite)) {
                $('.deleteWebsite').hide();
            }

            // Package Management

            if (!Boolean(response.data.createPackage)) {
                $('.createPackage').hide();
            }

            if (!Boolean(response.data.listPackages)) {
                $('.listPackages').hide();
            }

            if (!Boolean(response.data.deletePackage)) {
                $('.deletePackage').hide();
            }

            if (!Boolean(response.data.modifyPackage)) {
                $('.modifyPackage').hide();
            }

            // Database Management

            if (!Boolean(response.data.createDatabase)) {
                $('.createDatabase').hide();
            }

            if (!Boolean(response.data.deleteDatabase)) {
                $('.deleteDatabase').hide();
            }

            if (!Boolean(response.data.listDatabases)) {
                $('.listDatabases').hide();
            }

            // DNS Management

            if (!Boolean(response.data.dnsAsWhole)) {
                $('.dnsAsWhole').hide();
            }

            if (!Boolean(response.data.createNameServer)) {
                $('.createNameServer').hide();
            }

            if (!Boolean(response.data.createDNSZone)) {
                $('.createDNSZone').hide();
            }

            if (!Boolean(response.data.deleteZone)) {
                $('.addDeleteRecords').hide();
            }

            if (!Boolean(response.data.addDeleteRecords)) {
                $('.deleteDatabase').hide();
            }

            // Email Management

            if (!Boolean(response.data.emailAsWhole)) {
                $('.emailAsWhole').hide();
            }

            if (!Boolean(response.data.listEmails)) {
                $('.listEmails').hide();
            }

            if (!Boolean(response.data.createEmail)) {
                $('.createEmail').hide();
            }

            if (!Boolean(response.data.deleteEmail)) {
                $('.deleteEmail').hide();
            }

            if (!Boolean(response.data.emailForwarding)) {
                $('.emailForwarding').hide();
            }

            if (!Boolean(response.data.changeEmailPassword)) {
                $('.changeEmailPassword').hide();
            }

            if (!Boolean(response.data.dkimManager)) {
                $('.dkimManager').hide();
            }


            // FTP Management

            if (!Boolean(response.data.ftpAsWhole)) {
                $('.ftpAsWhole').hide();
            }

            if (!Boolean(response.data.createFTPAccount)) {
                $('.createFTPAccount').hide();
            }

            if (!Boolean(response.data.deleteFTPAccount)) {
                $('.deleteFTPAccount').hide();
            }

            if (!Boolean(response.data.listFTPAccounts)) {
                $('.listFTPAccounts').hide();
            }

            // Backup Management

            if (!Boolean(response.data.createBackup)) {
                $('.createBackup').hide();
            }

            if (!Boolean(response.data.restoreBackup)) {
                $('.restoreBackup').hide();
            }

            if (!Boolean(response.data.addDeleteDestinations)) {
                $('.addDeleteDestinations').hide();
            }

            if (!Boolean(response.data.scheduleBackups)) {
                $('.scheduleBackups').hide();
            }

            if (!Boolean(response.data.remoteBackups)) {
                $('.remoteBackups').hide();
            }


            // SSL Management

            if (!Boolean(response.data.manageSSL)) {
                $('.manageSSL').hide();
            }

            if (!Boolean(response.data.hostnameSSL)) {
                $('.hostnameSSL').hide();
            }

            if (!Boolean(response.data.mailServerSSL)) {
                $('.mailServerSSL').hide();
            }


        } else {

            if (!Boolean(response.data.emailAsWhole)) {
                $('.emailAsWhole').hide();
            }

            if (!Boolean(response.data.ftpAsWhole)) {
                $('.ftpAsWhole').hide();
            }

            if (!Boolean(response.data.dnsAsWhole)) {
                $('.dnsAsWhole').hide();
            }
        }
    }

    function cantLoadInitialData(response) {
    }
});

/* Load average */

app.controller('loadAvg', function ($scope, $http, $timeout) {

    getLoadAvg();

    function getLoadAvg() {


        url = "/base/getLoadAverage";

        $http.get(url).then(ListLoadAvgData, cantGetLoadAvgData);


        function ListLoadAvgData(response) {

            $scope.one = response.data.one;
            $scope.two = response.data.two;
            $scope.three = response.data.three;

        }

        function cantGetLoadAvgData(response) {
            console.log("Can't get load average data");
        }

        //$timeout(getStuff, 2000);

    }
});

/// home page system status

app.controller('homePageStatus', function ($scope, $http, $timeout) {

    getStuff();
    getLoadAvg();

    function getStuff() {


        url = "/base/getSystemStatus";

        $http.get(url).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            console.log(response.data);

            $("#redcircle").removeClass();
            $("#greencircle").removeClass();
            $("#pinkcircle").removeClass();


            $scope.cpuUsage = response.data.cpuUsage;
            $scope.ramUsage = response.data.ramUsage;
            $scope.diskUsage = response.data.diskUsage;

            $scope.RequestProcessing = response.data.RequestProcessing;
            $scope.TotalRequests = response.data.TotalRequests;

            $scope.MAXCONN = response.data.MAXCONN;
            $scope.MAXSSL = response.data.MAXSSL;
            $scope.Avail = response.data.Avail;
            $scope.AvailSSL = response.data.AvailSSL;


            $("#redcircle").addClass("c100");
            $("#redcircle").addClass("p" + $scope.cpuUsage);
            $("#redcircle").addClass("red");

            $("#greencircle").addClass("c100");
            $("#greencircle").addClass("p" + $scope.ramUsage);
            $("#greencircle").addClass("green");


            $("#pinkcircle").addClass("c100");
            $("#pinkcircle").addClass("p" + $scope.diskUsage);
            $("#pinkcircle").addClass("red");


            // home page cpu,ram and disk update.
            var rotationMultiplier = 3.6;
            // For each div that its id ends with "circle", do the following.
            $("div[id$='circle']").each(function () {
                // Save all of its classes in an array.
                var classList = $(this).attr('class').split(/\s+/);
                // Iterate over the array
                for (var i = 0; i < classList.length; i++) {
                    /* If there's about a percentage class, take the actual percentage and apply the
                         css transformations in all occurences of the specified percentage class,
                         even for the divs without an id ending with "circle" */
                    if (classList[i].match("^p" + $scope.cpuUsage)) {
                        var rotationPercentage = $scope.cpuUsage;
                        var rotationDegrees = rotationMultiplier * rotationPercentage;
                        $('.c100.p' + rotationPercentage + ' .bar').css({
                            '-webkit-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-moz-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-ms-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-o-transform': 'rotate(' + rotationDegrees + 'deg)',
                            'transform': 'rotate(' + rotationDegrees + 'deg)'
                        });
                    } else if (classList[i].match("^p" + $scope.ramUsage)) {
                        var rotationPercentage = response.data.ramUsage;
                        ;
                        var rotationDegrees = rotationMultiplier * rotationPercentage;
                        $('.c100.p' + rotationPercentage + ' .bar').css({
                            '-webkit-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-moz-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-ms-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-o-transform': 'rotate(' + rotationDegrees + 'deg)',
                            'transform': 'rotate(' + rotationDegrees + 'deg)'
                        });
                    } else if (classList[i].match("^p" + $scope.diskUsage)) {
                        var rotationPercentage = response.data.diskUsage;
                        ;
                        var rotationDegrees = rotationMultiplier * rotationPercentage;
                        $('.c100.p' + rotationPercentage + ' .bar').css({
                            '-webkit-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-moz-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-ms-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-o-transform': 'rotate(' + rotationDegrees + 'deg)',
                            'transform': 'rotate(' + rotationDegrees + 'deg)'
                        });
                    }
                }
            });


        }

        function cantLoadInitialData(response) {
            console.log("not good");
        }

        $timeout(getStuff, 2000);

    }

    function getLoadAvg() {

        url = "/base/getLoadAverage";

        $http.get(url).then(ListLoadAvgData, cantGetLoadAvgData);


        function ListLoadAvgData(response) {

            $scope.one = response.data.one;
            $scope.two = response.data.two;
            $scope.three = response.data.three;

            //document.getElementById("load1").innerHTML = $scope.one;
            //document.getElementById("load2").innerHTML = $scope.two;
            //document.getElementById("load3").innerHTML = $scope.three;
        }

        function cantGetLoadAvgData(response) {
            console.log("Can't get load average data");
        }

        $timeout(getLoadAvg, 2000);

    }
});

////////////

function increment() {
    $('.box').hide();
    setTimeout(function () {
        $('.box').show();
    }, 100);


}

increment();

////////////

app.controller('versionManagment', function ($scope, $http, $timeout) {

    $scope.upgradeLoading = true;
    $scope.upgradelogBox = true;

    $scope.updateError = true;
    $scope.updateStarted = true;
    $scope.updateFinish = true;
    $scope.couldNotConnect = true;


    $scope.upgrade = function () {

        $scope.upgradeLoading = false;
        $scope.updateError = true;
        $scope.updateStarted = true;
        $scope.updateFinish = true;
        $scope.couldNotConnect = true;

        var data = {
            branchSelect: document.getElementById("branchSelect").value,

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        url = "/base/upgrade";
        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            if (response.data.upgrade == 1) {
                $scope.upgradeLoading = true;
                $scope.updateError = true;
                $scope.updateStarted = false;
                $scope.updateFinish = true;
                $scope.couldNotConnect = true;
                getUpgradeStatus();
            } else {
                $scope.updateError = false;
                $scope.updateStarted = true;
                $scope.updateFinish = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;
            }
        }

        function cantLoadInitialData(response) {

            $scope.updateError = true;
            $scope.updateStarted = true;
            $scope.updateFinish = true;
            $scope.couldNotConnect = false;

        }


    }


    function getUpgradeStatus() {

        $scope.upgradeLoading = false;

        url = "/base/UpgradeStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            console.log(response.data.upgradeLog);


            if (response.data.upgradeStatus === 1) {

                if (response.data.finished === 1) {
                    $timeout.cancel();
                    $scope.upgradelogBox = false;
                    $scope.upgradeLog = response.data.upgradeLog;
                    $scope.upgradeLoading = true;
                    $scope.updateError = true;
                    $scope.updateStarted = true;
                    $scope.updateFinish = false;
                    $scope.couldNotConnect = true;

                } else {
                    $scope.upgradelogBox = false;
                    $scope.upgradeLog = response.data.upgradeLog;
                    timeout(getUpgradeStatus, 2000);
                }
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.updateError = true;
            $scope.updateStarted = true;
            $scope.updateFinish = true;
            $scope.couldNotConnect = false;

        }


    };

});


app.controller('designtheme', function ($scope, $http, $timeout) {

    $scope.themeloading = true;


    $scope.getthemedata = function () {
        $scope.themeloading = false;

        url = "/base/getthemedata";

        var data = {
            package: "helo world",
            Themename: $('#stheme').val(),
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(Listgetthemedata, cantgetthemedata);


        function Listgetthemedata(response) {
            $scope.themeloading = true;

            if (response.data.status === 1) {
                document.getElementById('appendthemedata').innerHTML = "";
                $("#appendthemedata").val(response.data.csscontent)
            } else {
                alert(response.data.error_message)
            }
        }

        function cantgetthemedata(response) {
            $scope.themeloading = true;
            console.log(response);
        }

        //$timeout(getStuff, 2000);

    };
});


app.controller('OnboardingCP', function ($scope, $http, $timeout, $window) {

    $scope.cyberpanelLoading = true;
    $scope.ExecutionStatus = true;
    $scope.ReportStatus = true;
    $scope.OnboardineDone = true;
    
    var statusTimer = null;

    function statusFunc() {
        $scope.cyberpanelLoading = false;
        $scope.ExecutionStatus = false;
        var url = "/emailPremium/statusFunc";

        var data = {
            statusFile: statusFile
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            if (response.data.status === 1) {
                if (response.data.abort === 1) {
                    $scope.functionProgress = {"width": "100%"};
                    $scope.functionStatus = response.data.currentStatus;
                    $scope.cyberpanelLoading = true;
                    $scope.OnboardineDone = false;
                    if (statusTimer) {
                        $timeout.cancel(statusTimer);
                        statusTimer = null;
                    }
                } else {
                    $scope.functionProgress = {"width": response.data.installationProgress + "%"};
                    $scope.functionStatus = response.data.currentStatus;
                    statusTimer = $timeout(statusFunc, 3000);
                }

            } else {
                $scope.cyberpanelLoading = true;
                $scope.functionStatus = response.data.error_message;
                $scope.functionProgress = {"width": response.data.installationProgress + "%"};
                if (statusTimer) {
                    $timeout.cancel(statusTimer);
                    statusTimer = null;
                }
            }

        }

        function cantLoadInitialData(response) {
            $scope.functionProgress = {"width": response.data.installationProgress + "%"};
            $scope.functionStatus = 'Could not connect to server, please refresh this page.';
            $timeout.cancel();
        }
    }

    $scope.RunOnboarding = function () {
        $scope.cyberpanelLoading = false;
        $scope.OnboardineDone = true;

        var url = "/base/runonboarding";

        var data = {
            hostname: $scope.hostname,
            rDNSCheck: $scope.rDNSCheck
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                statusFunc();


            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;

            new PNotify({
                title: 'Error',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    };

    $scope.RestartCyberPanel = function () {
        $scope.cyberpanelLoading = false;

        var url = "/base/RestartCyberPanel";

        var data = {

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);
        $scope.cyberpanelLoading = true;
        new PNotify({
                    title: 'Success',
                    text: 'Refresh your browser after 3 seconds to fetch new SSL.',
                    type: 'success'
                });

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {

            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;

            new PNotify({
                title: 'Error',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    };

});

app.controller('dashboardStatsController', function ($scope, $http, $timeout) {
    // Card values
    $scope.totalUsers = 0;
    $scope.totalSites = 0;
    $scope.totalWPSites = 0;
    $scope.totalDBs = 0;
    $scope.totalEmails = 0;
    $scope.totalFTPUsers = 0;
    
    // Hide system charts for non-admin users
    $scope.hideSystemCharts = false;

    // Top Processes
    $scope.topProcesses = [];
    $scope.loadingTopProcesses = true;
    $scope.errorTopProcesses = '';
    $scope.refreshTopProcesses = function() {
        $scope.loadingTopProcesses = true;
        $http.get('/base/getTopProcesses').then(function (response) {
            $scope.loadingTopProcesses = false;
            if (response.data && response.data.status === 1 && response.data.processes) {
                $scope.topProcesses = response.data.processes;
            } else {
                $scope.topProcesses = [];
            }
        }, function (err) {
            $scope.loadingTopProcesses = false;
            $scope.errorTopProcesses = 'Failed to load top processes.';
        });
    };

    // SSH Logins
    $scope.sshLogins = [];
    $scope.loadingSSHLogins = true;
    $scope.errorSSHLogins = '';
    $scope.refreshSSHLogins = function() {
        $scope.loadingSSHLogins = true;
        $http.get('/base/getRecentSSHLogins').then(function (response) {
            $scope.loadingSSHLogins = false;
            if (response.data && response.data.logins) {
                $scope.sshLogins = response.data.logins;
            } else {
                $scope.sshLogins = [];
            }
        }, function (err) {
            $scope.loadingSSHLogins = false;
            $scope.errorSSHLogins = 'Failed to load SSH logins.';
        });
    };

    // SSH Logs
    $scope.sshLogs = [];
    $scope.loadingSSHLogs = true;
    $scope.errorSSHLogs = '';
    $scope.securityAlerts = [];
    $scope.loadingSecurityAnalysis = false;
    $scope.refreshSSHLogs = function() {
        $scope.loadingSSHLogs = true;
        $http.get('/base/getRecentSSHLogs').then(function (response) {
            $scope.loadingSSHLogs = false;
            if (response.data && response.data.logs) {
                $scope.sshLogs = response.data.logs;
                // Analyze logs for security issues
                $scope.analyzeSSHSecurity();
            } else {
                $scope.sshLogs = [];
            }
        }, function (err) {
            $scope.loadingSSHLogs = false;
            $scope.errorSSHLogs = 'Failed to load SSH logs.';
        });
    };
    
    // Security Analysis
    $scope.showAddonRequired = false;
    $scope.addonInfo = {};
    
    $scope.analyzeSSHSecurity = function() {
        $scope.loadingSecurityAnalysis = true;
        $scope.showAddonRequired = false;
        $http.post('/base/analyzeSSHSecurity', {}).then(function (response) {
            $scope.loadingSecurityAnalysis = false;
            if (response.data) {
                if (response.data.addon_required) {
                    $scope.showAddonRequired = true;
                    $scope.addonInfo = response.data;
                    $scope.securityAlerts = [];
                } else if (response.data.status === 1) {
                    $scope.securityAlerts = response.data.alerts;
                    $scope.showAddonRequired = false;
                }
            }
        }, function (err) {
            $scope.loadingSecurityAnalysis = false;
        });
    };

    // Initial fetch
    $scope.refreshTopProcesses();
    $scope.refreshSSHLogins();
    $scope.refreshSSHLogs();

    // Chart.js chart objects
    var trafficChart, diskIOChart, cpuChart;
    // Data arrays for live graphs
    var trafficLabels = [], rxData = [], txData = [];
    var diskLabels = [], readData = [], writeData = [];
    var cpuLabels = [], cpuUsageData = [];
    // For rate calculation
    var lastRx = null, lastTx = null, lastDiskRead = null, lastDiskWrite = null, lastCPU = null;
    var lastCPUTimes = null;
    var pollInterval = 2000; // ms
    var maxPoints = 30;

    function pollDashboardStats() {
        $http.get('/base/getDashboardStats').then(function(response) {
            if (response.data.status === 1) {
                $scope.totalUsers = response.data.total_users;
                $scope.totalSites = response.data.total_sites;
                $scope.totalWPSites = response.data.total_wp_sites;
                $scope.totalDBs = response.data.total_dbs;
                $scope.totalEmails = response.data.total_emails;
                $scope.totalFTPUsers = response.data.total_ftp_users;
            }
        });
    }

    function pollTraffic() {
        console.log('pollTraffic called');
        $http.get('/base/getTrafficStats').then(function(response) {
            if (response.data.admin_only) {
                // Hide chart for non-admin users
                $scope.hideSystemCharts = true;
                return;
            }
            if (response.data.status === 1) {
                var now = new Date();
                var rx = response.data.rx_bytes;
                var tx = response.data.tx_bytes;
                if (lastRx !== null && lastTx !== null) {
                    var rxRate = (rx - lastRx) / (pollInterval / 1000); // bytes/sec
                    var txRate = (tx - lastTx) / (pollInterval / 1000);
                    trafficLabels.push(now.toLocaleTimeString());
                    rxData.push(rxRate);
                    txData.push(txRate);
                    if (trafficLabels.length > maxPoints) {
                        trafficLabels.shift(); rxData.shift(); txData.shift();
                    }
                    if (trafficChart) {
                        trafficChart.data.labels = trafficLabels.slice();
                        trafficChart.data.datasets[0].data = rxData.slice();
                        trafficChart.data.datasets[1].data = txData.slice();
                        trafficChart.update();
                        console.log('trafficChart updated:', trafficChart.data.labels, trafficChart.data.datasets[0].data, trafficChart.data.datasets[1].data);
                    }
                } else {
                    // First poll, push zero data point
                    trafficLabels.push(now.toLocaleTimeString());
                    rxData.push(0);
                    txData.push(0);
                    if (trafficChart) {
                        trafficChart.data.labels = trafficLabels.slice();
                        trafficChart.data.datasets[0].data = rxData.slice();
                        trafficChart.data.datasets[1].data = txData.slice();
                        trafficChart.update();
                        console.log('trafficChart first update:', trafficChart.data.labels, trafficChart.data.datasets[0].data, trafficChart.data.datasets[1].data);
                        setTimeout(function() {
                            if (window.trafficChart) {
                                window.trafficChart.resize();
                                window.trafficChart.update();
                                console.log('trafficChart forced resize/update after first poll.');
                            }
                        }, 1000);
                    }
                }
                lastRx = rx; lastTx = tx;
            } else {
                console.log('pollTraffic error or no data:', response);
            }
        });
    }

    function pollDiskIO() {
        $http.get('/base/getDiskIOStats').then(function(response) {
            if (response.data.admin_only) {
                // Hide chart for non-admin users
                $scope.hideSystemCharts = true;
                return;
            }
            if (response.data.status === 1) {
                var now = new Date();
                var read = response.data.read_bytes;
                var write = response.data.write_bytes;
                if (lastDiskRead !== null && lastDiskWrite !== null) {
                    var readRate = (read - lastDiskRead) / (pollInterval / 1000); // bytes/sec
                    var writeRate = (write - lastDiskWrite) / (pollInterval / 1000);
                    diskLabels.push(now.toLocaleTimeString());
                    readData.push(readRate);
                    writeData.push(writeRate);
                    if (diskLabels.length > maxPoints) {
                        diskLabels.shift(); readData.shift(); writeData.shift();
                    }
                    if (diskIOChart) {
                        diskIOChart.data.labels = diskLabels.slice();
                        diskIOChart.data.datasets[0].data = readData.slice();
                        diskIOChart.data.datasets[1].data = writeData.slice();
                        diskIOChart.update();
                    }
                } else {
                    // First poll, push zero data point
                    diskLabels.push(now.toLocaleTimeString());
                    readData.push(0);
                    writeData.push(0);
                    if (diskIOChart) {
                        diskIOChart.data.labels = diskLabels.slice();
                        diskIOChart.data.datasets[0].data = readData.slice();
                        diskIOChart.data.datasets[1].data = writeData.slice();
                        diskIOChart.update();
                    }
                }
                lastDiskRead = read; lastDiskWrite = write;
            }
        });
    }

    function pollCPU() {
        $http.get('/base/getCPULoadGraph').then(function(response) {
            if (response.data.admin_only) {
                // Hide chart for non-admin users
                $scope.hideSystemCharts = true;
                return;
            }
            if (response.data.status === 1 && response.data.cpu_times && response.data.cpu_times.length >= 4) {
                var now = new Date();
                var cpuTimes = response.data.cpu_times;
                if (lastCPUTimes) {
                    var idle = cpuTimes[3];
                    var total = cpuTimes.reduce(function(a, b) { return a + b; }, 0);
                    var lastIdle = lastCPUTimes[3];
                    var lastTotal = lastCPUTimes.reduce(function(a, b) { return a + b; }, 0);
                    var idleDiff = idle - lastIdle;
                    var totalDiff = total - lastTotal;
                    var usage = totalDiff > 0 ? (100 * (1 - idleDiff / totalDiff)) : 0;
                    cpuLabels.push(now.toLocaleTimeString());
                    cpuUsageData.push(usage);
                    if (cpuLabels.length > maxPoints) {
                        cpuLabels.shift(); cpuUsageData.shift();
                    }
                    if (cpuChart) {
                        cpuChart.data.labels = cpuLabels.slice();
                        cpuChart.data.datasets[0].data = cpuUsageData.slice();
                        cpuChart.update();
                    }
                } else {
                    // First poll, push zero data point
                    cpuLabels.push(now.toLocaleTimeString());
                    cpuUsageData.push(0);
                    if (cpuChart) {
                        cpuChart.data.labels = cpuLabels.slice();
                        cpuChart.data.datasets[0].data = cpuUsageData.slice();
                        cpuChart.update();
                    }
                }
                lastCPUTimes = cpuTimes;
            }
        });
    }

    function setupCharts() {
        console.log('setupCharts called, initializing charts...');
        var trafficCtx = document.getElementById('trafficChart').getContext('2d');
        trafficChart = new Chart(trafficCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { 
                        label: 'Download', 
                        data: [], 
                        borderColor: '#5b5fcf', 
                        backgroundColor: 'rgba(91,95,207,0.1)', 
                        pointBackgroundColor: '#5b5fcf',
                        pointBorderColor: '#5b5fcf',
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        tension: 0.4, 
                        fill: true 
                    },
                    { 
                        label: 'Upload', 
                        data: [], 
                        borderColor: '#4a90e2', 
                        backgroundColor: 'rgba(74,144,226,0.1)', 
                        pointBackgroundColor: '#4a90e2',
                        pointBorderColor: '#4a90e2',
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        tension: 0.4, 
                        fill: true 
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                plugins: {
                    legend: { 
                        display: true, 
                        position: 'top',
                        labels: { 
                            font: { size: 12, weight: '600' },
                            color: '#64748b',
                            usePointStyle: true,
                            padding: 20
                        } 
                    },
                    title: { display: false },
                    tooltip: { 
                        enabled: true, 
                        mode: 'index', 
                        intersect: false,
                        backgroundColor: 'rgba(255,255,255,0.95)',
                        titleColor: '#2f3640',
                        bodyColor: '#64748b',
                        borderColor: '#e8e9ff',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false },
                scales: {
                    x: { 
                        grid: { color: '#f0f0ff', drawBorder: false }, 
                        ticks: { 
                            font: { size: 11 },
                            color: '#94a3b8',
                            maxTicksLimit: 8
                        }
                    },
                    y: { 
                        beginAtZero: true, 
                        grid: { color: '#f0f0ff', drawBorder: false }, 
                        ticks: { 
                            font: { size: 11 },
                            color: '#94a3b8'
                        }
                    }
                },
                layout: { padding: { top: 10, bottom: 10, left: 10, right: 10 } }
            }
        });
        window.trafficChart = trafficChart;
        setTimeout(function() {
            if (window.trafficChart) {
                window.trafficChart.resize();
                window.trafficChart.update();
                console.log('trafficChart resized and updated after setup.');
            }
        }, 500);
        var diskCtx = document.getElementById('diskIOChart').getContext('2d');
        diskIOChart = new Chart(diskCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { 
                        label: 'Read', 
                        data: [], 
                        borderColor: '#5b5fcf', 
                        backgroundColor: 'rgba(91,95,207,0.1)', 
                        pointBackgroundColor: '#5b5fcf',
                        pointBorderColor: '#5b5fcf',
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        tension: 0.4, 
                        fill: true 
                    },
                    { 
                        label: 'Write', 
                        data: [], 
                        borderColor: '#e74c3c', 
                        backgroundColor: 'rgba(231,76,60,0.1)', 
                        pointBackgroundColor: '#e74c3c',
                        pointBorderColor: '#e74c3c',
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        tension: 0.4, 
                        fill: true 
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                plugins: {
                    legend: { 
                        display: true, 
                        position: 'top',
                        labels: { 
                            font: { size: 12, weight: '600' },
                            color: '#64748b',
                            usePointStyle: true,
                            padding: 20
                        } 
                    },
                    title: { display: false },
                    tooltip: { 
                        enabled: true, 
                        mode: 'index', 
                        intersect: false,
                        backgroundColor: 'rgba(255,255,255,0.95)',
                        titleColor: '#2f3640',
                        bodyColor: '#64748b',
                        borderColor: '#e8e9ff',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false },
                scales: {
                    x: { 
                        grid: { color: '#f0f0ff', drawBorder: false }, 
                        ticks: { 
                            font: { size: 11 },
                            color: '#94a3b8',
                            maxTicksLimit: 8
                        }
                    },
                    y: { 
                        beginAtZero: true, 
                        grid: { color: '#f0f0ff', drawBorder: false }, 
                        ticks: { 
                            font: { size: 11 },
                            color: '#94a3b8'
                        }
                    }
                },
                layout: { padding: { top: 10, bottom: 10, left: 10, right: 10 } }
            }
        });
        var cpuCtx = document.getElementById('cpuChart').getContext('2d');
        cpuChart = new Chart(cpuCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { 
                        label: 'CPU Usage (%)', 
                        data: [], 
                        borderColor: '#5b5fcf', 
                        backgroundColor: 'rgba(91,95,207,0.1)', 
                        pointBackgroundColor: '#5b5fcf',
                        pointBorderColor: '#5b5fcf',
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        tension: 0.4, 
                        fill: true 
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                plugins: {
                    legend: { 
                        display: true, 
                        position: 'top',
                        labels: { 
                            font: { size: 12, weight: '600' },
                            color: '#64748b',
                            usePointStyle: true,
                            padding: 20
                        } 
                    },
                    title: { display: false },
                    tooltip: { 
                        enabled: true, 
                        mode: 'index', 
                        intersect: false,
                        backgroundColor: 'rgba(255,255,255,0.95)',
                        titleColor: '#2f3640',
                        bodyColor: '#64748b',
                        borderColor: '#e8e9ff',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false },
                scales: {
                    x: { 
                        grid: { color: '#f0f0ff', drawBorder: false }, 
                        ticks: { 
                            font: { size: 11 },
                            color: '#94a3b8',
                            maxTicksLimit: 8
                        }
                    },
                    y: { 
                        beginAtZero: true, 
                        max: 100, 
                        grid: { color: '#f0f0ff', drawBorder: false }, 
                        ticks: { 
                            font: { size: 11 },
                            color: '#94a3b8'
                        }
                    }
                },
                layout: { padding: { top: 10, bottom: 10, left: 10, right: 10 } }
            }
        });

        // Redraw charts on tab shown
        $("a[data-toggle='tab']").on('shown.bs.tab', function (e) {
            setTimeout(function() {
                if (trafficChart) trafficChart.resize();
                if (diskIOChart) diskIOChart.resize();
                if (cpuChart) cpuChart.resize();
            }, 100);
        });
        
        // Also handle custom tab switching
        document.addEventListener('DOMContentLoaded', function() {
            var tabs = document.querySelectorAll('a[data-toggle="tab"]');
            tabs.forEach(function(tab) {
                tab.addEventListener('click', function(e) {
                    setTimeout(function() {
                        if (trafficChart) trafficChart.resize();
                        if (diskIOChart) diskIOChart.resize();
                        if (cpuChart) cpuChart.resize();
                    }, 200);
                });
            });
        });
    }

    // Initial setup
    $timeout(function() {
        // Check if user is admin before setting up charts
        $http.get('/base/getAdminStatus').then(function(response) {
            if (response.data && response.data.admin === 1) {
                setupCharts();
            } else {
                $scope.hideSystemCharts = true;
            }
        }).catch(function() {
            // If error, assume non-admin and hide charts
            $scope.hideSystemCharts = true;
        });
        
        // Immediately poll once so stats are updated on first load
        pollDashboardStats();
        pollTraffic();
        pollDiskIO();
        pollCPU();
        // Start polling
        function pollAll() {
            pollDashboardStats();
            pollTraffic();
            pollDiskIO();
            pollCPU();
            $scope.refreshTopProcesses();
            $timeout(pollAll, pollInterval);
        }
        pollAll();
    }, 500);

    // SSH User Activity Modal
    $scope.showSSHActivityModal = false;
    $scope.sshActivity = { processes: [], w: [] };
    $scope.sshActivityUser = '';
    $scope.loadingSSHActivity = false;
    $scope.errorSSHActivity = '';
    
    $scope.viewSSHActivity = function(login) {
        $scope.showSSHActivityModal = true;
        $scope.sshActivity = { processes: [], w: [] };
        $scope.sshActivityUser = login.user;
        $scope.loadingSSHActivity = true;
        $scope.errorSSHActivity = '';
        var tty = '';
        // Try to extract tty from login.raw or login.session if available
        if (login.raw) {
            var match = login.raw.match(/(pts\/[0-9]+)/);
            if (match) tty = match[1];
        }
        $http.post('/base/getSSHUserActivity', { user: login.user, tty: tty }).then(function(response) {
            $scope.loadingSSHActivity = false;
            if (response.data) {
                $scope.sshActivity = response.data;
            } else {
                $scope.sshActivity = { processes: [], w: [] };
            }
        }, function(err) {
            $scope.loadingSSHActivity = false;
            $scope.errorSSHActivity = (err.data && err.data.error) ? err.data.error : 'Failed to fetch activity.';
        });
    };
    
    $scope.closeSSHActivityModal = function() {
        $scope.showSSHActivityModal = false;
        $scope.sshActivity = { processes: [], w: [] };
        $scope.sshActivityUser = '';
        $scope.loadingSSHActivity = false;
        $scope.errorSSHActivity = '';
    };

    // Close modal when clicking backdrop
    $scope.closeModalOnBackdrop = function(event) {
        if (event.target === event.currentTarget) {
            $scope.closeSSHActivityModal();
        }
    };
});