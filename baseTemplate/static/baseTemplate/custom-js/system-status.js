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

// Create global app reference for CyberCP module so other scripts can access it
window.app = angular.module('CyberCP', []);
var app = window.app; // Local reference for this file

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
                $scope.uptime = 'N/A';
                $scope.uptimeLoaded = true;
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
    console.log('dashboardStatsController initialized');
    
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
                // Debug: Log first login to see structure
                if ($scope.sshLogins.length > 0) {
                    console.log('First SSH login object:', $scope.sshLogins[0]);
                    console.log('IP field:', $scope.sshLogins[0].ip);
                    console.log('All keys:', Object.keys($scope.sshLogins[0]));
                }
            } else {
                $scope.sshLogins = [];
            }
        }, function (err) {
            $scope.loadingSSHLogins = false;
            $scope.errorSSHLogins = 'Failed to load SSH logins.';
            console.error('Failed to load SSH logins:', err);
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
    
    // IP Blocking functionality
    $scope.blockingIP = null;
    $scope.blockedIPs = {};
    
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
    
    $scope.blockIPAddress = function(ipAddress) {
        try {
            console.log('========================================');
            console.log('=== blockIPAddress CALLED ===');
            console.log('========================================');
            console.log('blockIPAddress called with:', ipAddress);
            console.log('ipAddress type:', typeof ipAddress);
            console.log('ipAddress value:', ipAddress);
            console.log('$scope:', $scope);
            console.log('$scope.blockIPAddress:', typeof $scope.blockIPAddress);
            
            // Validate IP address parameter
        if (!ipAddress) {
            console.error('No IP address provided:', ipAddress);
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Error',
                    text: 'No IP address provided',
                    type: 'error',
                    delay: 5000
                });
            }
            return;
        }
        
        // Ensure it's a string and trim it
        ipAddress = String(ipAddress).trim();
        
        // Validate after trimming
        if (!ipAddress || ipAddress === '' || ipAddress === 'undefined' || ipAddress === 'null') {
            console.error('IP address is empty or invalid after trim:', ipAddress);
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Error',
                    text: 'Invalid IP address provided: ' + ipAddress,
                    type: 'error',
                    delay: 5000
                });
            }
            return;
        }
        
        // Basic IP format validation
        var ipPattern = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
        if (!ipPattern.test(ipAddress)) {
            console.error('IP address format is invalid:', ipAddress);
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Error',
                    text: 'Invalid IP address format: ' + ipAddress,
                    type: 'error',
                    delay: 5000
                });
            }
            return;
        }
        
        // Prevent duplicate requests
        if ($scope.blockingIP === ipAddress) {
            console.log('Already processing IP:', ipAddress);
            return; // Already processing this IP
        }
        
        // Check if already blocked
        if ($scope.blockedIPs && $scope.blockedIPs[ipAddress]) {
            console.log('IP already blocked:', ipAddress);
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Info',
                    text: `IP address ${ipAddress} is already banned`,
                    type: 'info',
                    delay: 3000
                });
            }
            return;
        }
        
        // Set blocking flag to prevent duplicate requests
        $scope.blockingIP = ipAddress;
            
            // Use the new Banned IPs system instead of the old blockIPAddress
            var data = {
                ip: ipAddress,
                reason: 'Brute force attack detected from SSH Security Analysis',
                duration: 'permanent'
            };
            
            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };
            
            console.log('Sending ban IP request:', data);
            console.log('CSRF Token:', getCookie('csrftoken'));
            console.log('Config:', config);
            
            $http.post('/firewall/addBannedIP', data, config).then(function (response) {
                console.log('=== addBannedIP SUCCESS ===');
                console.log('Full response:', response);
                console.log('response.data:', response.data);
                console.log('response.data type:', typeof response.data);
                console.log('response.status:', response.status);
                
                // Reset blocking flag
                $scope.blockingIP = null;
                
                // Apply scope changes
                if (!$scope.$$phase && !$scope.$root.$$phase) {
                    $scope.$apply();
                }
                
                // Handle both JSON string and object responses
                var responseData = response.data;
                if (typeof responseData === 'string') {
                    try {
                        responseData = JSON.parse(responseData);
                        console.log('Parsed responseData from string:', responseData);
                    } catch (e) {
                        console.error('Failed to parse response as JSON:', e);
                        console.error('Raw response string:', responseData);
                        // Try to extract error from string
                        if (responseData.includes('error')) {
                            if (typeof PNotify !== 'undefined') {
                                new PNotify({
                                    title: 'Error',
                                    text: 'Failed to block IP address: ' + responseData,
                                    type: 'error',
                                    delay: 5000
                                });
                            }
                            return;
                        }
                    }
                }
                
                console.log('Final responseData:', responseData);
                console.log('responseData.status:', responseData ? responseData.status : 'undefined');
                console.log('responseData.message:', responseData ? responseData.message : 'undefined');
                console.log('responseData.error_message:', responseData ? responseData.error_message : 'undefined');
                
                // Check for success (status === 1 or status === '1')
                if (responseData && (responseData.status === 1 || responseData.status === '1')) {
                    // Mark IP as blocked
                    if (!$scope.blockedIPs) {
                        $scope.blockedIPs = {};
                    }
                    $scope.blockedIPs[ipAddress] = true;
                    
                    // Show success notification
                    if (typeof PNotify !== 'undefined') {
                        new PNotify({
                            title: 'IP Address Banned',
                            text: `IP address ${ipAddress} has been permanently banned and added to the firewall. You can manage it in the Firewall > Banned IPs section.`,
                            type: 'success',
                            delay: 5000
                        });
                    }
                    
                    // Refresh security analysis to update alerts
                    if ($scope.analyzeSSHSecurity) {
                        $scope.analyzeSSHSecurity();
                    }
                    
                    // Apply scope changes
                    if (!$scope.$$phase && !$scope.$root.$$phase) {
                        $scope.$apply();
                    }
                } else {
                    // Show error notification
                    var errorMsg = 'Failed to block IP address';
                    if (responseData && responseData.error_message) {
                        errorMsg = responseData.error_message;
                    } else if (responseData && responseData.error) {
                        errorMsg = responseData.error;
                    } else if (responseData && responseData.message) {
                        errorMsg = responseData.message;
                    } else if (responseData) {
                        errorMsg = JSON.stringify(responseData);
                    }
                    console.error('Ban IP failed:', errorMsg);
                    if (typeof PNotify !== 'undefined') {
                        new PNotify({
                            title: 'Error',
                            text: errorMsg,
                            type: 'error',
                            delay: 5000
                        });
                    }
                }
            }, function (err) {
                $scope.blockingIP = null;
                console.error('addBannedIP error:', err);
                console.error('Error status:', err.status);
                console.error('Error statusText:', err.statusText);
                console.error('Error data:', err.data);
                
                // Prevent showing duplicate error notifications
                if ($scope.lastErrorIP === ipAddress && $scope.lastErrorTime && (Date.now() - $scope.lastErrorTime) < 2000) {
                    console.log('Skipping duplicate error notification for IP:', ipAddress);
                    return;
                }
                
                $scope.lastErrorIP = ipAddress;
                $scope.lastErrorTime = Date.now();
                
                var errorMessage = 'Failed to block IP address';
                if (err.data) {
                    var errData = err.data;
                    if (typeof errData === 'string') {
                        try {
                            errData = JSON.parse(errData);
                        } catch (e) {
                            errorMessage = errData || errorMessage;
                        }
                    }
                    if (errData && typeof errData === 'object') {
                        if (errData.error_message) {
                            errorMessage = errData.error_message;
                        } else if (errData.error) {
                            errorMessage = errData.error;
                        } else if (errData.message) {
                            errorMessage = errData.message;
                        }
                    }
                } else if (err.statusText) {
                    errorMessage = err.statusText;
                } else if (err.status) {
                    errorMessage = `HTTP ${err.status}: ${err.statusText || 'Unknown error'}`;
                }
                
                console.error('Final error message:', errorMessage);
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Error',
                        text: errorMessage,
                        type: 'error',
                        delay: 5000
                    });
                }
            });
        } catch (e) {
            console.error('========================================');
            console.error('=== ERROR in blockIPAddress ===');
            console.error('========================================');
            console.error('Error:', e);
            console.error('Error message:', e.message);
            console.error('Error stack:', e.stack);
            $scope.blockingIP = null;
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Error',
                    text: 'An error occurred while trying to ban the IP address: ' + (e.message || String(e)),
                    type: 'error',
                    delay: 5000
                });
            }
        }
    };
    
    // Ban IP from SSH Logs
    $scope.banIPFromSSHLog = function(ipAddress) {
        if (!ipAddress) {
            new PNotify({
                title: 'Error',
                text: 'No IP address provided',
                type: 'error',
                delay: 5000
            });
            return;
        }
        
        if ($scope.blockingIP === ipAddress) {
            return; // Already processing
        }
        
        if ($scope.blockedIPs[ipAddress]) {
            new PNotify({
                title: 'Info',
                text: `IP address ${ipAddress} is already banned`,
                type: 'info',
                delay: 3000
            });
            return;
        }
        
        $scope.blockingIP = ipAddress;
        
        // Use the Banned IPs system
        var data = {
            ip: ipAddress,
            reason: 'Suspicious activity detected from SSH logs',
            duration: 'permanent'
        };
        
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        
        $http.post('/firewall/addBannedIP', data, config).then(function (response) {
            $scope.blockingIP = null;
            if (response.data && response.data.status === 1) {
                // Mark IP as blocked
                $scope.blockedIPs[ipAddress] = true;
                
                // Show success notification
                new PNotify({
                    title: 'IP Address Banned',
                    text: `IP address ${ipAddress} has been permanently banned and added to the firewall. You can manage it in the Firewall > Banned IPs section.`,
                    type: 'success',
                    delay: 5000
                });
                
                // Refresh SSH logs to update the UI
                $scope.refreshSSHLogs();
            } else {
                // Show error notification
                var errorMsg = 'Failed to ban IP address';
                if (response.data && response.data.error_message) {
                    errorMsg = response.data.error_message;
                } else if (response.data && response.data.error) {
                    errorMsg = response.data.error;
                }
                
                new PNotify({
                    title: 'Error',
                    text: errorMsg,
                    type: 'error',
                    delay: 5000
                });
            }
        }, function (err) {
            $scope.blockingIP = null;
            var errorMessage = 'Failed to ban IP address';
            if (err.data && err.data.error_message) {
                errorMessage = err.data.error_message;
            } else if (err.data && err.data.error) {
                errorMessage = err.data.error;
            } else if (err.data && err.data.message) {
                errorMessage = err.data.message;
            }
            
            new PNotify({
                title: 'Error',
                text: errorMessage,
                type: 'error',
                delay: 5000
            });
        });
    };
    
    // Ban IP from SSH Logs
    $scope.banIPFromSSHLog = function(ipAddress) {
        if (!ipAddress) {
            new PNotify({
                title: 'Error',
                text: 'No IP address provided',
                type: 'error',
                delay: 5000
            });
            return;
        }
        
        if ($scope.blockingIP === ipAddress) {
            return; // Already processing
        }
        
        if ($scope.blockedIPs[ipAddress]) {
            new PNotify({
                title: 'Info',
                text: `IP address ${ipAddress} is already banned`,
                type: 'info',
                delay: 3000
            });
            return;
        }
        
        $scope.blockingIP = ipAddress;
        
        // Use the Banned IPs system
        var data = {
            ip: ipAddress,
            reason: 'Suspicious activity detected from SSH logs',
            duration: 'permanent'
        };
        
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        
        $http.post('/firewall/addBannedIP', data, config).then(function (response) {
            $scope.blockingIP = null;
            if (response.data && response.data.status === 1) {
                // Mark IP as blocked
                $scope.blockedIPs[ipAddress] = true;
                
                // Show success notification
                new PNotify({
                    title: 'IP Address Banned',
                    text: `IP address ${ipAddress} has been permanently banned and added to the firewall. You can manage it in the Firewall > Banned IPs section.`,
                    type: 'success',
                    delay: 5000
                });
                
                // Refresh SSH logs to update the UI
                $scope.refreshSSHLogs();
            } else {
                // Show error notification
                var errorMsg = 'Failed to ban IP address';
                if (response.data && response.data.error_message) {
                    errorMsg = response.data.error_message;
                } else if (response.data && response.data.error) {
                    errorMsg = response.data.error;
                }
                
                new PNotify({
                    title: 'Error',
                    text: errorMsg,
                    type: 'error',
                    delay: 5000
                });
            }
        }, function (err) {
            $scope.blockingIP = null;
            var errorMessage = 'Failed to ban IP address';
            if (err.data && err.data.error_message) {
                errorMessage = err.data.error_message;
            } else if (err.data && err.data.error) {
                errorMessage = err.data.error;
            } else if (err.data && err.data.message) {
                errorMessage = err.data.message;
            }
            
            new PNotify({
                title: 'Error',
                text: errorMessage,
                type: 'error',
                delay: 5000
            });
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
        console.log('[dashboardStatsController] pollDashboardStats() called');
        console.log('[dashboardStatsController] Fetching dashboard stats from /base/getDashboardStats');
        $http({
            method: 'GET',
            url: '/base/getDashboardStats',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        }).then(function(response) {
            console.log('[dashboardStatsController] pollDashboardStats SUCCESS callback called');
            console.log('[dashboardStatsController] Dashboard stats response received:', response);
            console.log('[dashboardStatsController] Response status:', response.status);
            console.log('[dashboardStatsController] Response data:', response.data);
            if (response.data && response.data.status === 1) {
                $scope.totalUsers = response.data.total_users || 0;
                $scope.totalSites = response.data.total_sites || 0;
                $scope.totalWPSites = response.data.total_wp_sites || 0;
                $scope.totalDBs = response.data.total_dbs || 0;
                $scope.totalEmails = response.data.total_emails || 0;
                $scope.totalFTPUsers = response.data.total_ftp_users || 0;
                console.log('[dashboardStatsController] Dashboard stats updated:', {
                    users: $scope.totalUsers,
                    sites: $scope.totalSites,
                    wp: $scope.totalWPSites,
                    dbs: $scope.totalDBs,
                    emails: $scope.totalEmails,
                    ftp: $scope.totalFTPUsers
                });
                // No $apply needed - $http already triggers digest cycle
            } else {
                // Set default values if request fails
                console.error('[dashboardStatsController] Failed to load dashboard stats - invalid response:', response.data);
                $scope.$apply(function() {
                    $scope.totalUsers = 0;
                    $scope.totalSites = 0;
                    $scope.totalWPSites = 0;
                    $scope.totalDBs = 0;
                    $scope.totalEmails = 0;
                    $scope.totalFTPUsers = 0;
                });
            }
        }, function(error) {
            console.error('[dashboardStatsController] Error loading dashboard stats:', error);
            console.error('[dashboardStatsController] Error status:', error.status);
            console.error('[dashboardStatsController] Error data:', error.data);
            // Set default values on error (no $apply needed - error callback also triggers digest)
            $scope.totalUsers = 0;
            $scope.totalSites = 0;
            $scope.totalWPSites = 0;
            $scope.totalDBs = 0;
            $scope.totalEmails = 0;
            $scope.totalFTPUsers = 0;
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

    // Initial setup - fetch stats immediately
    pollDashboardStats();
    $scope.refreshTopProcesses();
    $scope.refreshSSHLogins();
    $scope.refreshSSHLogs();
    
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
        
        // Start polling for all stats
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
    
    $scope.viewSSHActivity = function(login, event) {
        $scope.showSSHActivityModal = true;
        $scope.sshActivity = { processes: [], w: [] };
        $scope.sshActivityUser = login.user;
        
        // Extract IP from multiple sources - comprehensive extraction for IPv4 and IPv6
        var extractedIP = '';
        
        // Method 1: Direct property access (highest priority - from backend)
        if (login && login.ip) {
            extractedIP = login.ip.toString().trim();
        } else if (login && login['ip']) {
            extractedIP = login['ip'].toString().trim();
        }
        
        // Method 2: Alternative field names
        if (!extractedIP && login) {
            if (login.ipAddress) extractedIP = login.ipAddress.toString().trim();
            else if (login['IP Address']) extractedIP = login['IP Address'].toString().trim();
            else if (login['IP']) extractedIP = login['IP'].toString().trim();
        }
        
        // Method 3: Extract from raw line using regex (IPv4 and IPv6)
        if (!extractedIP && login && login.raw) {
            // Try IPv4 first (most common)
            var ipv4Match = login.raw.match(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/);
            if (ipv4Match && ipv4Match[1]) {
                var ipv4 = ipv4Match[1].trim();
                if (ipv4 !== '127.0.0.1' && ipv4 !== '0.0.0.0') {
                    extractedIP = ipv4;
                }
            }
            
            // If no valid IPv4, try IPv6
            if (!extractedIP) {
                // IPv6 pattern: matches full IPv6 addresses and compressed forms
                var ipv6Pattern = /([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}/;
                var ipv6Match = login.raw.match(ipv6Pattern);
                if (ipv6Match && ipv6Match[0]) {
                    var ipv6 = ipv6Match[0].trim();
                    if (ipv6 !== '::1' && ipv6.length > 0) {
                        extractedIP = ipv6;
                    }
                }
            }
        }
        
        // Method 4: Try to get from event target data attribute as fallback
        if (!extractedIP && event && event.currentTarget) {
            var dataIP = event.currentTarget.getAttribute('data-ip');
            if (dataIP) extractedIP = dataIP.toString().trim();
        }
        
        // Final fallback: search entire raw line for any IP
        if (!extractedIP && login && login.raw) {
            // Try all IPv4 addresses
            var allIPv4s = login.raw.match(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/g);
            if (allIPv4s && allIPv4s.length > 0) {
                for (var i = 0; i < allIPv4s.length; i++) {
                    var ip = allIPv4s[i].trim();
                    if (ip !== '127.0.0.1' && ip !== '0.0.0.0' && ip.length > 0) {
                        extractedIP = ip;
                        break;
                    }
                }
            }
            // If no IPv4, try all IPv6 addresses
            if (!extractedIP) {
                var allIPv6s = login.raw.match(/([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}/g);
                if (allIPv6s && allIPv6s.length > 0) {
                    for (var j = 0; j < allIPv6s.length; j++) {
                        var ip6 = allIPv6s[j].trim();
                        if (ip6 !== '::1' && ip6.length > 0) {
                            extractedIP = ip6;
                            break;
                        }
                    }
                }
            }
        }
        
        // Final cleanup
        $scope.sshActivityIP = (extractedIP || '').toString().trim();
        $scope.sshActivityTTY = ''; // Store TTY for kill session
        // Check both 'session' and 'activity' fields for status
        $scope.sshActivityStatus = login.session || login.activity || '';
        
        // Use backend is_active field if available (most reliable)
        // Fallback to checking session text if is_active is not set
        // IMPORTANT: Check for both boolean true and string 'true' (JSON might serialize differently)
        if (login.is_active !== undefined && login.is_active !== null) {
            // Backend explicitly set is_active
            $scope.isActiveSession = (login.is_active === true || login.is_active === 'true' || login.is_active === 1 || login.is_active === '1');
            console.log('Using backend is_active field:', login.is_active, '-> isActiveSession:', $scope.isActiveSession);
        } else {
            // Fallback: check session text
            var sessionStatus = ($scope.sshActivityStatus || '').toLowerCase();
            $scope.isActiveSession = (sessionStatus.indexOf('still logged in') !== -1);
            console.log('Using fallback session text check:', sessionStatus, '-> isActiveSession:', $scope.isActiveSession);
        }
        
        // If IP is still empty, try one more time with more aggressive extraction
        if (!$scope.sshActivityIP && login) {
            console.log('IP still empty, trying aggressive extraction...');
            // Try every possible field name variation
            var possibleIPFields = ['ip', 'IP', 'ipAddress', 'IP Address', 'ip_address', 'IP_ADDRESS', 'client_ip', 'clientIP', 'source_ip', 'sourceIP'];
            for (var k = 0; k < possibleIPFields.length; k++) {
                if (login[possibleIPFields[k]]) {
                    var testIP = login[possibleIPFields[k]].toString().trim();
                    // Validate it looks like an IP (IPv4 or IPv6)
                    if (testIP.match(/^(\d{1,3}\.){3}\d{1,3}$/) || testIP.match(/^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/)) {
                        if (testIP !== '127.0.0.1' && testIP !== '0.0.0.0' && testIP !== '::1') {
                            $scope.sshActivityIP = testIP;
                            console.log('Found IP in field', possibleIPFields[k], ':', $scope.sshActivityIP);
                            break;
                        }
                    }
                }
            }
            // Last resort: check if IP is in the table cell itself (from DOM)
            if (!$scope.sshActivityIP && event && event.currentTarget) {
                try {
                    var row = event.currentTarget.closest('tr');
                    if (row) {
                        // Try different column positions (IP could be in different positions)
                        var cells = row.querySelectorAll('td');
                        for (var cellIdx = 0; cellIdx < cells.length; cellIdx++) {
                            var cellText = cells[cellIdx].textContent.trim();
                            // Check if this cell contains an IP address
                            var ipMatch = cellText.match(/^(\d{1,3}\.){3}\d{1,3}$/) || cellText.match(/^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/);
                            if (ipMatch && cellText !== '127.0.0.1' && cellText !== '0.0.0.0' && cellText !== '::1') {
                                $scope.sshActivityIP = cellText;
                                console.log('Found IP from table cell (column ' + cellIdx + '):', $scope.sshActivityIP);
                                break;
                            }
                        }
                    }
                } catch (e) {
                    console.log('Error extracting IP from DOM:', e);
                }
            }
        }
        
        // Debug logging - detailed inspection
        console.log('View SSH Activity - Login object:', login);
        console.log('Login keys:', Object.keys(login));
        console.log('login.ip:', login.ip);
        console.log('login.is_active:', login.is_active);
        console.log('Extracted IP:', $scope.sshActivityIP);
        console.log('Session status:', $scope.sshActivityStatus);
        console.log('Is active session:', $scope.isActiveSession);
        $scope.showFullJSON = false; // Collapsible JSON view
        $scope.loadingSSHActivity = true;
        $scope.errorSSHActivity = '';
        $scope.killingProcess = null;
        $scope.killingSession = false;
        var tty = '';
        // Try to extract tty from login.raw or login.session if available
        if (login.raw) {
            var match = login.raw.match(/(pts\/[0-9]+)/);
            if (match) {
                tty = match[1];
                $scope.sshActivityTTY = tty;
            }
        }
        // Also try to extract from session field or raw line
        if (!tty && login.session) {
            var sessionMatch = login.session.match(/(pts\/[0-9]+)/);
            if (sessionMatch) {
                tty = sessionMatch[1];
                $scope.sshActivityTTY = tty;
            }
        }
        // Also check raw line for TTY
        if (!tty && login.raw) {
            var rawMatch = login.raw.match(/(pts\/[0-9]+)/);
            if (rawMatch) {
                tty = rawMatch[1];
                $scope.sshActivityTTY = tty;
            }
        }
        // Make API call with IP included - reduced timeout for faster response
        var requestData = { 
            user: login.user, 
            tty: tty,
            ip: $scope.sshActivityIP
        };
        
        // Set shorter timeout for faster feedback
        var timeoutPromise = $timeout(function() {
            $scope.loadingSSHActivity = false;
            $scope.errorSSHActivity = 'Request timed out. The user may not have any active processes.';
            $scope.sshActivity = { processes: [], w: [] };
        }, 5000); // 5 second timeout (reduced from 10)
        
        $http.post('/base/getSSHUserActivity', requestData, { timeout: 3000 }).then(function(response) {
            $timeout.cancel(timeoutPromise); // Cancel timeout on success
            $scope.loadingSSHActivity = false;
            if (response.data) {
                // Check if response has error field
                if (response.data.error) {
                    $scope.errorSSHActivity = response.data.error;
                    $scope.sshActivity = { processes: [], w: [] };
                } else {
                    $scope.sshActivity = response.data;
                    // Ensure all expected fields exist
                    if (!$scope.sshActivity.processes) $scope.sshActivity.processes = [];
                    if (!$scope.sshActivity.w) $scope.sshActivity.w = [];
                    if (!$scope.sshActivity.process_tree) $scope.sshActivity.process_tree = [];
                    if (!$scope.sshActivity.shell_history) $scope.sshActivity.shell_history = [];
                    
                    // Try to extract TTY from processes if not already set
                    if (!$scope.sshActivityTTY && response.data.processes && response.data.processes.length > 0) {
                        var firstProcess = response.data.processes[0];
                        if (firstProcess.tty) {
                            $scope.sshActivityTTY = firstProcess.tty;
                        }
                    }
                    // Update active session status - prioritize backend is_active field
                    // The backend already determined if session is active, so trust that first
                    // Only update if we have additional evidence (processes/w output)
                    var hasProcesses = response.data.processes && response.data.processes.length > 0;
                    var hasActiveW = response.data.w && response.data.w.length > 0;
                    
                    // If backend says it's active, keep it active (don't override)
                    // If backend says inactive but we find processes/w, mark as active
                    if ($scope.isActiveSession === true) {
                        // Backend already marked as active, keep it that way
                        // (processes might not have loaded yet, but session is still active)
                    } else if (hasProcesses || hasActiveW) {
                        // Backend said inactive, but we found evidence it's active
                        $scope.isActiveSession = true;
                    }
                    // If backend said inactive and no processes found, keep as inactive
                    
                    // Debug logging
                    console.log('SSH Activity loaded:', {
                        processes: response.data.processes ? response.data.processes.length : 0,
                        w: response.data.w ? response.data.w.length : 0,
                        hasProcesses: hasProcesses,
                        hasActiveW: hasActiveW,
                        originalStatus: $scope.sshActivityStatus,
                        isActiveSession: $scope.isActiveSession,
                        ip: $scope.sshActivityIP
                    });
                }
            } else {
                $scope.sshActivity = { processes: [], w: [] };
                $scope.errorSSHActivity = 'No data returned from server.';
            }
        }, function(err) {
            $timeout.cancel(timeoutPromise); // Cancel timeout on error
            $scope.loadingSSHActivity = false;
            var errorMsg = 'Failed to fetch activity.';
            
            // Handle different error scenarios
            if (err.data) {
                // Server returned error data
                if (err.data.error) {
                    errorMsg = err.data.error;
                } else if (typeof err.data === 'string') {
                    errorMsg = err.data;
                } else if (err.data.message) {
                    errorMsg = err.data.message;
                }
            } else if (err.status === 0 || err.status === -1) {
                errorMsg = 'Network error. Please check your connection and try again.';
            } else if (err.status >= 500) {
                errorMsg = 'Server error (HTTP ' + err.status + '). Please try again later.';
            } else if (err.status === 404) {
                errorMsg = 'Endpoint not found. Please refresh the page.';
            } else if (err.status === 403) {
                errorMsg = 'Access denied. Admin privileges required.';
            } else if (err.status === 400) {
                errorMsg = 'Invalid request. Please check the user information.';
            } else if (err.status) {
                errorMsg = 'Request failed with status ' + err.status + '.';
            } else if (err.message) {
                errorMsg = err.message;
            }
            
            $scope.errorSSHActivity = errorMsg;
            // Set empty activity data so modal can still display
            $scope.sshActivity = { 
                processes: [], 
                w: [],
                process_tree: [],
                shell_history: [],
                disk_usage: '',
                geoip: {}
            };
            
            // Log error for debugging
            console.error('SSH Activity fetch error:', err);
        });
    };
    
    // Kill individual process
    $scope.killProcess = function(pid, user) {
        if (!confirm('Are you sure you want to force kill process ' + pid + '? This action cannot be undone.')) {
            return;
        }
        
        $scope.killingProcess = pid;
        
        var data = {
            pid: pid,
            user: user
        };
        
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        
        $http.post('/base/killSSHProcess', data, config).then(function(response) {
            $scope.killingProcess = null;
            if (response.data && response.data.success) {
                new PNotify({
                    title: 'Process Killed',
                    text: response.data.message || 'Process ' + pid + ' has been terminated.',
                    type: 'success',
                    delay: 3000
                });
                // Refresh activity to update process list
                $scope.viewSSHActivity({ user: user, ip: $scope.sshActivityIP, raw: '', session: '' });
            } else {
                new PNotify({
                    title: 'Error',
                    text: (response.data && response.data.error) || 'Failed to kill process.',
                    type: 'error',
                    delay: 5000
                });
            }
        }, function(err) {
            $scope.killingProcess = null;
            var errorMsg = 'Failed to kill process.';
            if (err.data && err.data.error) {
                errorMsg = err.data.error;
            } else if (err.data && err.data.message) {
                errorMsg = err.data.message;
            }
            new PNotify({
                title: 'Error',
                text: errorMsg,
                type: 'error',
                delay: 5000
            });
        });
    };
    
    // Kill entire SSH session
    $scope.killSSHSession = function(user, tty) {
        var confirmMsg = 'Are you sure you want to kill all processes for user ' + user;
        if (tty) {
            confirmMsg += ' on terminal ' + tty;
        }
        confirmMsg += '? This will terminate their SSH session.';
        
        if (!confirm(confirmMsg)) {
            return;
        }
        
        $scope.killingSession = true;
        
        var data = {
            user: user,
            tty: tty || ''
        };
        
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        
        $http.post('/base/killSSHSession', data, config).then(function(response) {
            $scope.killingSession = false;
            if (response.data && response.data.success) {
                new PNotify({
                    title: 'Session Terminated',
                    text: response.data.message || 'SSH session has been terminated successfully.',
                    type: 'success',
                    delay: 3000
                });
                // Close modal and refresh page after a delay
                setTimeout(function() {
                    $scope.closeSSHActivityModal();
                    location.reload();
                }, 1500);
            } else {
                new PNotify({
                    title: 'Error',
                    text: (response.data && response.data.error) || 'Failed to kill session.',
                    type: 'error',
                    delay: 5000
                });
            }
        }, function(err) {
            $scope.killingSession = false;
            var errorMsg = 'Failed to kill session.';
            if (err.data && err.data.error) {
                errorMsg = err.data.error;
            } else if (err.data && err.data.message) {
                errorMsg = err.data.message;
            }
            new PNotify({
                title: 'Error',
                text: errorMsg,
                type: 'error',
                delay: 5000
            });
        });
    };
    
    $scope.closeSSHActivityModal = function() {
        $scope.showSSHActivityModal = false;
        $scope.sshActivity = { processes: [], w: [] };
        $scope.sshActivityUser = '';
        $scope.sshActivityIP = ''; // Clear IP when closing modal
        $scope.sshActivityTTY = ''; // Clear TTY when closing modal
        $scope.sshActivityStatus = ''; // Clear activity status
        $scope.isActiveSession = false; // Reset active session flag
        $scope.showFullJSON = false; // Reset JSON view
        $scope.loadingSSHActivity = false;
        $scope.errorSSHActivity = '';
        $scope.killingProcess = null;
        $scope.killingSession = false;
    };

    // Close modal when clicking backdrop
    $scope.closeModalOnBackdrop = function(event) {
        if (event.target === event.currentTarget) {
            $scope.closeSSHActivityModal();
        }
    };
});