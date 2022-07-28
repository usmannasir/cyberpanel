/**
 * Created by usman on 6/22/18.
 */

/* Java script code to list accounts */

app.controller('listDomains', function ($scope, $http) {

    $scope.listFail = true;
    $scope.emailLimitsLoading = true;

    // Global page number, to be used in later function to refresh the domains
    var globalPageNumber;


    $scope.getFurtherWebsitesFromDB = function (pageNumber) {

        globalPageNumber = pageNumber;
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/getFurtherDomains";

        var data = {page: pageNumber};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

            if (response.data.listWebSiteStatus === 1) {

                $scope.WebSitesList = JSON.parse(response.data.data);
                $scope.listFail = true;
            } else {
                $scope.listFail = false;
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
        }


    };
    $scope.getFurtherWebsitesFromDB(1);

    $scope.enableDisableEmailLimits = function (operationVal, domainName) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableEmailLimits";

        var data = {
            operationVal: operationVal,
            domainName: domainName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {

                $scope.getFurtherWebsitesFromDB(globalPageNumber);
                $scope.listFail = true;
            } else {
                $scope.listFail = false;
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
        }
    }
});

/* Java script code to list accounts ends here */


/* Java script code for email domain page */

app.controller('emailDomainPage', function ($scope, $http, $timeout, $window) {

    $scope.listFail = true;
    $scope.emailLimitsLoading = true;

    var globalDomainName = window.location.pathname.split("/")[2];

    // Global page number, to be used in later function to refresh the domains
    var globalPageNumber;


    $scope.getFurtherEmailsFromDB = function (pageNumber) {

        globalPageNumber = pageNumber;
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/getFurtherEmail";

        var data = {
            page: pageNumber,
            domainName: globalDomainName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {

                $scope.emailList = JSON.parse(response.data.data);
                $scope.listFail = true;
            } else {
                $scope.listFail = false;
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
        }


    };
    $scope.getFurtherEmailsFromDB(1);

    $scope.enableDisableEmailLimits = function (operationVal, domainName) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableEmailLimits";

        var data = {
            operationVal: operationVal,
            domainName: domainName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {

                $timeout(function () {
                    $window.location.reload();
                }, 0);
            } else {
                $timeout(function () {
                    $window.location.reload();
                }, 0);
            }
        }

        function cantLoadInitialData(response) {
            $timeout(function () {
                $window.location.reload();
            }, 0);
        }
    };


    /// Email limits

    $scope.changeLimitsForm = true;
    $scope.changeLimitsFail = true;
    $scope.changeLimitsSuccess = true;
    $scope.couldNotConnect = true;

    $scope.showLimitsForm = function () {
        $scope.changeLimitsForm = false;
    };

    $scope.hideLimitsForm = function () {
        $scope.changeLimitsForm = true;
        $scope.changeLimitsFail = true;
        $scope.changeLimitsSuccess = true;
        $scope.couldNotConnect = true;
    };

    $scope.changeDomainEmailLimits = function (domainName) {
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/changeDomainLimit";

        var data = {
            domainName: domainName,
            newLimit: $scope.monthlyLimit
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;


            if (response.data.status === 1) {

                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = true;
                $scope.changeLimitsSuccess = false;
                $scope.couldNotConnect = true;
                $timeout(function () {
                    $window.location.reload();
                }, 3000);
            } else {
                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = false;
                $scope.changeLimitsSuccess = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.changeLimitsForm = false;
            $scope.changeLimitsFail = true;
            $scope.changeLimitsSuccess = true;
            $scope.couldNotConnect = false;
        }
    }


    $scope.enableDisableIndividualEmailLimits = function (operationVal, emailAddress) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableIndividualEmailLimits";

        var data = {
            operationVal: operationVal,
            emailAddress: emailAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {
                $scope.getFurtherEmailsFromDB(1);
            } else {
                $scope.getFurtherEmailsFromDB(1);
            }
        }

        function cantLoadInitialData(response) {
            $scope.getFurtherEmailsFromDB(1);
        }
    };

});

/* Java script code for email domain page */

/* Java script code for Email Page */

app.controller('emailPage', function ($scope, $http, $timeout, $window) {

    $scope.emailLimitsLoading = true;

    var globalEamilAddress = $("#emailAddress").text();

    // Global page number, to be used in later function to refresh the domains
    var globalPageNumber;

    $scope.getEmailStats = function () {

        $scope.emailLimitsLoading = false;

        ////

        $scope.limitsOn = true;
        $scope.limitsOff = true;

        url = "/emailPremium/getEmailStats";

        var data = {
            emailAddress: globalEamilAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {

                $scope.monthlyLimit = response.data.monthlyLimit;
                $scope.monthlyUsed = response.data.monthlyUsed;
                $scope.hourlyLimit = response.data.hourlyLimit;
                $scope.hourlyUsed = response.data.hourlyUsed;

                if (response.data.limitStatus === 1) {
                    $scope.limitsOn = false;
                    $scope.limitsOff = true;
                } else {
                    $scope.limitsOn = true;
                    $scope.limitsOff = false;
                }

                if (response.data.logsStatus === 1) {
                    $scope.loggingOn = false;
                    $scope.loggingOff = true;
                } else {
                    $scope.loggingOn = true;
                    $scope.loggingOff = false;
                }

            } else {

                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
        }


    };
    $scope.getEmailStats();

    $scope.enableDisableIndividualEmailLimits = function (operationVal, emailAddress) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableIndividualEmailLimits";

        var data = {
            operationVal: operationVal,
            emailAddress: emailAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {
                $scope.getEmailStats();
            } else {
                $scope.getEmailStats();
            }
        }

        function cantLoadInitialData(response) {
            $scope.getEmailStats();
        }
    };
    $scope.enableDisableIndividualEmailLogs = function (operationVal, emailAddress) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableIndividualEmailLogs";

        var data = {
            operationVal: operationVal,
            emailAddress: emailAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {
                $scope.getEmailStats();
            } else {
                $scope.getEmailStats();
            }
        }

        function cantLoadInitialData(response) {
            $scope.getEmailStats();
        }
    };


    $scope.enableDisableEmailLimits = function (operationVal, domainName) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableEmailLimits";

        var data = {
            operationVal: operationVal,
            domainName: domainName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {

                $timeout(function () {
                    $window.location.reload();
                }, 0);
            } else {
                $timeout(function () {
                    $window.location.reload();
                }, 0);
            }
        }

        function cantLoadInitialData(response) {
            $timeout(function () {
                $window.location.reload();
            }, 0);
        }
    };


    /// Email limits
    $scope.changeLimitsForm = true;
    $scope.changeLimitsFail = true;
    $scope.changeLimitsSuccess = true;
    $scope.couldNotConnect = true;

    $scope.showLimitsForm = function () {
        $scope.changeLimitsForm = false;
    };

    $scope.hideLimitsForm = function () {
        $scope.changeLimitsForm = true;
        $scope.changeLimitsFail = true;
        $scope.changeLimitsSuccess = true;
        $scope.couldNotConnect = true;
    };

    $scope.changeDomainEmailLimitsIndividual = function () {
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/changeDomainEmailLimitsIndividual";

        var data = {
            emailAddress: globalEamilAddress,
            monthlyLimit: $scope.monthlyLimitForm,
            hourlyLimit: $scope.hourlyLimitForm
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;


            if (response.data.status === 1) {

                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = true;
                $scope.changeLimitsSuccess = false;
                $scope.couldNotConnect = true;
                $scope.getEmailStats();

            } else {
                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = false;
                $scope.changeLimitsSuccess = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.changeLimitsForm = false;
            $scope.changeLimitsFail = true;
            $scope.changeLimitsSuccess = true;
            $scope.couldNotConnect = false;
        }
    };

    /// Get email logs

    $scope.getLogEntries = function (pageNumber) {

        globalPageNumber = pageNumber;
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/getEmailLogs";

        var data = {
            page: pageNumber,
            emailAddress: globalEamilAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {

                $scope.logs = JSON.parse(response.data.data);
                $scope.listFail = true;
            } else {
                $scope.listFail = false;
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
        }


    };
    $scope.getLogEntries(1);


    $scope.flushLogs = function (emailAddress) {

        $scope.emailLimitsLoading = false;

        url = "/emailPremium/flushEmailLogs";

        var data = {
            emailAddress: emailAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {
                $scope.getLogEntries(1);

            } else {
                $scope.listFail = false;
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
        }


    };

});

/* Java script code for Email Page */

/* Java script code for SpamAssassin */

app.controller('SpamAssassin', function ($scope, $http, $timeout, $window) {

    $scope.SpamAssassinNotifyBox = true;
    $scope.SpamAssassinInstallBox = true;
    $scope.SpamAssassinLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.RspamdSuccessfullyInstalled = true;
    $scope.installationFailed = true;


    $scope.installSpamAssassin = function () {

        $scope.SpamAssassinNotifyBox = true;
        $scope.SpamAssassinInstallBox = true;
        $scope.SpamAssassinLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.SpamAssassinSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/emailPremium/installSpamAssassin";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status === 1) {

                $scope.SpamAssassinNotifyBox = true;
                $scope.SpamAssassinInstallBox = false;
                $scope.SpamAssassinLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.SpamAssassinSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getRequestStatus();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.SpamAssassinNotifyBox = false;
                $scope.SpamAssassinInstallBox = true;
                $scope.SpamAssassinLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.SpamAssassinSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.SpamAssassinNotifyBox = false;
            $scope.SpamAssassinInstallBox = false;
            $scope.SpamAssassinLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.SpamAssassinSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }

    };

    function getRequestStatus() {

        $scope.SpamAssassinNotifyBox = true;
        $scope.SpamAssassinInstallBox = false;
        $scope.SpamAssassinLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.SpamAssassinSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/emailPremium/installStatusSpamAssassin";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.SpamAssassinNotifyBox = true;
                $scope.SpamAssassinInstallBox = false;
                $scope.SpamAssassinLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.SpamAssassinSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            } else {
                // Notifications
                $timeout.cancel();
                $scope.SpamAssassinNotifyBox = false;
                $scope.SpamAssassinInstallBox = false;
                $scope.SpamAssassinLoading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.SpamAssassinSuccessfullyInstalled = false;
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.SpamAssassinNotifyBox = false;
            $scope.SpamAssassinInstallBox = false;
            $scope.SpamAssassinLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.SpamAssassinSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }

    ///// SpamAssassin configs

    var report_safe = false;


    $('#report_safe').change(function () {
        report_safe = $(this).prop('checked');
    });

    fetchSpamAssassinSettings();

    function fetchSpamAssassinSettings() {

        $scope.SpamAssassinLoading = false;

        $('#report_safe').bootstrapToggle('off');

        url = "/emailPremium/fetchSpamAssassinSettings";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.SpamAssassinLoading = true;

            if (response.data.fetchStatus === 1) {

                if (response.data.installed === 1) {

                    if (response.data.report_safe === 1) {
                        $('#report_safe').bootstrapToggle('on');
                    }

                    $scope.required_hits = response.data.required_hits;
                    $scope.rewrite_header = response.data.rewrite_header;
                    $scope.required_score = response.data.required_score;

                }

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.SpamAssassinLoading = true;
        }

    }


    /////

    /// Save SpamAssassin Changes

    $scope.failedToSave = true;
    $scope.successfullySaved = true;

    $scope.saveSpamAssassinConfigurations = function () {

        $scope.failedToSave = true;
        $scope.successfullySaved = true;
        $scope.SpamAssassinLoading = false;
        $scope.couldNotConnect = true;


        url = "/emailPremium/saveSpamAssassinConfigurations";

        var data = {
            report_safe: report_safe,
            required_hits: $scope.required_hits,
            rewrite_header: $scope.rewrite_header,
            required_score: $scope.required_score
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.failedToSave = true;
                $scope.successfullySaved = false;
                $scope.SpamAssassinLoading = true;
                $scope.couldNotConnect = true;

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToSave = false;
                $scope.successfullySaved = true;
                $scope.SpamAssassinLoading = true;
                $scope.couldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.failedToSave = true;
            $scope.successfullySaved = false;
            $scope.SpamAssassinLoading = true;
            $scope.couldNotConnect = true;
        }


    };

});

/* Java script code for SpamAssassin */


/* Rspamd start  */
app.controller('Rspamd', function ($scope, $http, $timeout, $window) {
    $scope.RspamdNotifyBox = true;
    $scope.RspamdInstallBox = true;
    $scope.RspamdLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.RspamdSuccessfullyInstalled = true;
    $scope.installationFailed = true;
    $scope.failedToSave = true;
    $scope.successfullySaved = true;
    $scope.ActionValue = true;
    $scope.installedrspamd = false;
    $scope.uninstalldiv = true;
    $scope.uninstallRspamdNotifyBox = true;
    $scope.uninstallRspamdInstallBox = true;
    $scope.uninstallbutton = true;


    $scope.installRspamd = function () {

        $scope.RspamdNotifyBox = true;
        $scope.RspamdInstallBox = true;
        $scope.RspamdLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.RspamdSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        var url = "/emailPremium/installRspamd";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status === 1) {

                $scope.RspamdNotifyBox = true;
                $scope.RspamdInstallBox = false;
                $scope.RspamdLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.RspamdSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getRequestStatus();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.RspamdNotifyBox = false;
                $scope.RspamdInstallBox = true;
                $scope.RspamdLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.RspamdSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.RspamdNotifyBox = false;
            $scope.RspamdInstallBox = false;
            $scope.RspamdLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.RspamdSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }

    };

    function getRequestStatus() {

        $scope.RspamdNotifyBox = true;
        $scope.RspamdInstallBox = false;
        $scope.RspamdLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.RspamdSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        var url = "/emailPremium/installStatusRspamd";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.RspamdNotifyBox = true;
                $scope.RspamdInstallBox = false;
                $scope.RspamdLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.RspamdSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            } else {
                // Notifications
                $timeout.cancel();
                $scope.RspamdNotifyBox = false;
                $scope.RspamdInstallBox = false;
                $scope.RspamdLoading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.RspamdSuccessfullyInstalled = false;
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.RspamdNotifyBox = false;
            $scope.RspamdInstallBox = false;
            $scope.RspamdLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.RspamdSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }

    var antivirus_status = false;
    var scan_mime_parts = false;
    var log_clean = false;


    $('#antivirus_status').change(function () {
        antivirus_status = $(this).prop('checked');
    });
    $('#scan_mime_parts').change(function () {
        scan_mime_parts = $(this).prop('checked');
    });
    $('#log_clean').change(function () {
        log_clean = $(this).prop('checked');
    });
    $('#clamav_Debug').change(function () {
        clamav_Debug = $(this).prop('checked');
    });

    fetchRspamdSettings();

    function fetchRspamdSettings() {

        $scope.RspamdLoading = false;

        var url = "/emailPremium/fetchRspamdSettings";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.RspamdLoading = true;
            $scope.ActionValue = false;

            if (response.data.fetchStatus === 1) {


                if (response.data.installed === 1) {
                    $scope.uninstallbutton = false;

                    if (response.data.enabled === true) {
                        $('#antivirus_status').bootstrapToggle('on');
                    } else if (response.data.enabled === false) {
                        $('#antivirus_status').bootstrapToggle('off');
                    }
                    if (response.data.scan_mime_parts === true) {
                        $('#scan_mime_parts').bootstrapToggle('on');
                    } else if (response.data.scan_mime_parts === false) {
                        $('#scan_mime_parts').bootstrapToggle('off');
                    }
                    if (response.data.log_clean === true) {
                        $('#log_clean').bootstrapToggle('on');
                    } else if (response.data.log_clean === false) {
                        $('#log_clean').bootstrapToggle('off');
                    }
                    if (response.data.clamav_Debug === true) {
                        $('#clamav_Debug').bootstrapToggle('on');
                    } else if (response.data.clamav_Debug === false) {
                        $('#clamav_Debug').bootstrapToggle('off');
                    }

                    $scope.max_size = response.data.max_Size;
                    $scope.server = response.data.Server;
                    $scope.CLAMAV_VIRUS = response.data.CLAMAV_VIRUS;
                    $('#selctedaction').text(response.data.action);
                    $scope.smtpd_milters = response.data.smtpd_milters;
                    $scope.non_smtpd_milters = response.data.non_smtpd_milters;
                    $scope.read_servers = response.data.read_servers;
                    $scope.write_servers = response.data.write_servers;
                    $scope.LogFile = response.data.LogFile;
                    $scope.TCPAddr = response.data.TCPAddr;
                    $scope.TCPSocket = response.data.TCPSocket;
                    //     $scope.required_score = response.data.required_score;
                    //
                }

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.RspamdLoading = true;
        }

    }


    $scope.saveRspamdConfigurations = function () {
        $scope.failedToSave = true;
        $scope.successfullySaved = true;
        $scope.RspamdLoading = false;
        $scope.couldNotConnect = true;
        url = "/emailPremium/saveRspamdConfigurations";


        var data = {
            status: antivirus_status,
            scan_mime_parts: scan_mime_parts,
            log_clean: log_clean,
            action_rspamd: $scope.action_rspamd,
            max_size: $scope.max_size,
            Rspamdserver: $scope.server,
            CLAMAV_VIRUS: $scope.CLAMAV_VIRUS,

        };
        // console.log(data)

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        if ($scope.action_rspamd == undefined) {
            alert('Please Select Action')
            $scope.RspamdLoading = true;
        } else {
            $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);
        }


        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.failedToSave = true;
                $scope.successfullySaved = false;
                $scope.RspamdLoading = true;
                $scope.couldNotConnect = true;

                location.reload();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToSave = false;
                $scope.successfullySaved = true;
                $scope.RspamdLoading = true;
                $scope.couldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.failedToSave = true;
            $scope.successfullySaved = true;
            $scope.RspamdLoading = true;
            $scope.couldNotConnect = false;
        }
    };


    ///postfix;
    $scope.postfixfailedToSave = true;
    $scope.postfixsuccessfullySaved = true;
    $scope.postfixcouldNotConnect = true;
    $scope.postfixLoading = true;


    $scope.savepostfixConfigurations = function () {
        $scope.postfixLoading = false;
        url = "/emailPremium/savepostfixConfigurations";
        var data = {
            smtpd_milters: $scope.smtpd_milters,
            non_smtpd_milters: $scope.non_smtpd_milters,
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.postfixfailedToSave = true;
                $scope.postfixsuccessfullySaved = false;
                $scope.postfixLoading = true;
                $scope.postfixcouldNotConnect = true;

                location.reload();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.postfixfailedToSave = false;
                $scope.postfixsuccessfullySaved = true;
                $scope.postfixLoading = true;
                $scope.postfixcouldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.postfixfailedToSave = true;
            $scope.postfixsuccessfullySaved = true;
            $scope.postfixLoading = true;
            $scope.postfixcouldNotConnect = false;
        }
    };


    ////Redis
    $scope.RedisfailedToSave = true;
    $scope.RedissuccessfullySaved = true;
    $scope.RediscouldNotConnect = true;
    $scope.RedisLoading = true;

    $scope.saveRedisConfigurations = function () {
        $scope.RedisLoading = false;
        url = "/emailPremium/saveRedisConfigurations";
        var data = {
            write_servers: $scope.write_servers,
            read_servers: $scope.read_servers,
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.RedisfailedToSave = true;
                $scope.RedissuccessfullySaved = false;
                $scope.RedisLoading = true;
                $scope.RediscouldNotConnect = true;

                location.reload();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.RedisfailedToSave = false;
                $scope.RedissuccessfullySaved = true;
                $scope.RedisLoading = true;
                $scope.RediscouldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.RedisfailedToSave = true;
            $scope.RedissuccessfullySaved = true;
            $scope.RedisLoading = true;
            $scope.RediscouldNotConnect = false;
        }
    };


    ////uninstall

    $scope.RspamduninstallLoading = true;
    $scope.uninstallationProgress = true;
    $scope.errorMessageBox = true;
    $scope.uninstallsuccess = true;
    $scope.couldNotConnect = true;


    $scope.unistallRspamd = function () {
        $('#UninstallRspamdmodal').modal('hide');
        $scope.RspamdLoading = false;
        $scope.uninstalldiv = false;
        $scope.uninstallbutton = true;
        $scope.installedrspamd = true;

        var url = "/emailPremium/unistallRspamd";
        var data = {};
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response.data)

            if (response.data.status === 1) {
                console.log(response.data)

                $scope.uninstallRspamdNotifyBox = true;
                $scope.uninstallRspamdInstallBox = false;
                $scope.RspamdLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.RspamdSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getuninstallRequestStatus();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.uninstallRspamdNotifyBox = false;
                $scope.uninstallRspamdInstallBox = true;
                $scope.RspamdLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.RspamdSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.uninstallRspamdNotifyBox = false;
            $scope.uninstallRspamdInstallBox = false;
            $scope.RspamdLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.RspamdSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }
    };

    function getuninstallRequestStatus() {

        $scope.uninstallRspamdNotifyBox = true;
        $scope.uninstallRspamdInstallBox = false;
        $scope.RspamdLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.RspamdSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        var url = "/emailPremium/uninstallStatusRspamd";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.uninstallRspamdNotifyBox = true;
                $scope.uninstallRspamdInstallBox = false;
                $scope.RspamdLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.RspamdSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getuninstallRequestStatus, 1000);
            } else {
                // Notifications
                $timeout.cancel();
                $scope.uninstallRspamdNotifyBox = false;
                $scope.uninstallRspamdInstallBox = false;
                $scope.RspamdLoading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.RspamdSuccessfullyInstalled = false;
                    $timeout(function () {
                        location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.uninstallRspamdNotifyBox = false;
            $scope.uninstallRspamdInstallBox = false;
            $scope.RspamdLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.RspamdSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }


    ///ClamAV config

    $scope.CLamAVLoading = true;
    $scope.ClamAVfailedToSave = true;
    $scope.ClamAVsuccessfullySaved = true;
    $scope.ClamAVcouldNotConnect = true;

    $scope.saveclamavConfigurations = function () {
        $scope.CLamAVLoading = false;
        url = "/emailPremium/saveclamavConfigurations";
        var data = {
            LogFile: $scope.LogFile,
            TCPAddr: $scope.TCPAddr,
            TCPSocket: $scope.TCPSocket,
            clamav_Debug: clamav_Debug
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.CLamAVfailedToSave = true;
                $scope.CLamAVsuccessfullySaved = false;
                $scope.CLamAVLoading = true;
                $scope.CLamAVcouldNotConnect = true;

                location.reload();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.CLamAVfailedToSave = false;
                $scope.CLamAVsuccessfullySaved = true;
                $scope.CLamAVLoading = true;
                $scope.CLamAVcouldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.CLamAVfailedToSave = true;
            $scope.CLamAVsuccessfullySaved = true;
            $scope.CLamAVLoading = true;
            $scope.CLamAVcouldNotConnect = false;
        }
    };

    $scope.FetchRspamdLog = function () {
         url = "/emailPremium/FetchRspamdLog";
        var data = {

        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);
        function ListInitialDatas(response) {


            if (response.data.status === 1) {

                console.log(response.data)
                $scope.RspamdlogsData = response.data.logsdata;

            } else {

               console.log( response.data.error_message)
            }

        }

        function cantLoadInitialDatas(response) {
            console.log(response)
        }
    };


    $scope.RestartRspamd = function () {

        $scope.RspamdLoading = false;
        url = "/emailPremium/RestartRspamd";
        var data = {

        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);
        function ListInitialDatas(response) {
            $scope.RspamdLoading = true;
            if (response.data.status === 1) {

                console.log(response.data)
                new PNotify({
                    title: 'Success',
                    text: 'SUccessfully Restarted.',
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
            $scope.RspamdLoading = true;
             new PNotify({
                    title: 'Error',
                    text: 'Could not connect to server, please refresh this page.',
                    type: 'error'
                });
        }
    };


});

//// Email Debugger

app.controller('EmailDebuuger', function ($scope, $http, $timeout, $window) {

    $scope.cyberpanelLoading = true;
    $scope.ExecutionStatus = true;
    $scope.ReportStatus = true;


    $scope.RunServerLevelEmailChecks = function () {
         $scope.cyberpanelLoading = false;

         var url = "/emailPremium/RunServerLevelEmailChecks";

        var data = {};

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
                reportFile = response.data.reportFile;
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

    function statusFunc(){
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
                    $scope.ReadReport();
                    $timeout.cancel();
                } else {
                    $scope.functionProgress = {"width": response.data.installationProgress + "%"};
                    $scope.functionStatus = response.data.currentStatus;
                    $timeout(statusFunc, 3000);
                }

            } else {
                $scope.cyberpanelLoading = true;
                $scope.functionStatus = response.data.error_message;
                $scope.functionProgress = {"width": response.data.installationProgress + "%"};
                $timeout.cancel();
            }

        }

        function cantLoadInitialData(response) {
            $scope.functionProgress = {"width": response.data.installationProgress + "%"};
            $scope.functionStatus = 'Could not connect to server, please refresh this page.';
            $timeout.cancel();
        }
    }

     $scope.ReadReport = function () {

        if (reportFile === 'none') {
            return;
        }

        $scope.cyberpanelLoading = false;

       var url = "/emailPremium/ReadReport";

        var data = {
            reportFile: reportFile
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
                var reportResult = JSON.parse(response.data.reportContent);

                if (reportResult.MailSSL === 1) {
                    $scope.MailSSL = 'Issued and Valid';
                } else {
                    $scope.MailSSL = 'Not issued or expired.'
                }
                var report = response.data.report;

                console.log(report);
                $scope.Port25 = report.Port25;
                $scope.Port587 = report.Port587;
                $scope.Port465 = report.Port465;
                $scope.Port110 = report.Port110;
                $scope.Port143 = report.Port143;
                $scope.Port993 = report.Port993;
                $scope.Port995 = report.Port995;
                //document.getElementById('MailSSLURL').href = 'https://' + report.serverHostName + ":" + report.port + '/cloudAPI/access?token=' + report.token + "&serverUserName=" + report.userName + '&redirect=/manageSSL/sslForMailServer';
                document.getElementById('MailSSLURL').href = '/manageSSL/sslForMailServer';


                $scope.ReportStatus = false;
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

    $scope.ResetEmailConfigurations = function () {
         $scope.cyberpanelLoading = false;

         var url = "/emailPremium/ResetEmailConfigurations";

        var data = {};

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
                reportFile = response.data.reportFile;
                reportFile = 'none';
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

});

app.controller('emailDebuggerDomainLevel', function ($scope, $http, $timeout, $window) {
    $scope.cyberpanelLoading = true;
    $scope.ReportStatus = true;

    $scope.debugEmailForSite = function () {
        $scope.cyberpanelLoading = false;

          url = "/emailPremium/debugEmailForSite";

        var data = {
            websiteName: $scope.websiteName
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            $scope.status = response.data.status;
            $scope.message = response.data.error_message;
            $scope.ReportStatus = false;

        }

         function cantLoadInitialData(response) {
            $scope.cyberhosting = true;
             new PNotify({
                    title: 'Operation Failed!',
                    text: 'Could not connect to server, please refresh this page.',
                    type: 'error'
                });
        }

    };

    $scope.fixMailSSL = function () {
        $scope.cyberpanelLoading = false;
         url = "/emailPremium/fixMailSSL";

        var data = {
            websiteName: $scope.websiteName
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

                   new PNotify({
                    title: 'Success',
                    text: 'Successfully fixed.',
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

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
             new PNotify({
                    title: 'Operation Failed!',
                    text: 'Could not connect to server, please refresh this page.',
                    type: 'error'
                });
        }
    };

});

/* Java script code for Email Policy Server */

app.controller('policyServer', function ($scope, $http, $timeout, $window) {

    $scope.policyServerLoading = true;
    $scope.failedToFetch = true;
    $scope.couldNotConnect = true;
    $scope.changesApplied = true;


    ///// SpamAssassin configs

    var report_safe = false;


    $('#policServerStatus').change(function () {
        policServerStatus = $(this).prop('checked');
    });

    fetchPolicServerStatus();

    function fetchPolicServerStatus() {

        $scope.policyServerLoading = false;

        $('#policServerStatus').bootstrapToggle('off');

        url = "/emailPremium/fetchPolicyServerStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.policyServerLoading = true;

            if (response.data.status === 1) {

                if (response.data.installCheck === 1) {
                    $('#policServerStatus').bootstrapToggle('on');
                }

            } else {
                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.policyServerLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }

    }


    $scope.savePolicServerStatus = function () {

        $scope.policyServerLoading = false;
        $scope.failedToFetch = true;
        $scope.couldNotConnect = true;
        $scope.changesApplied = true;


        url = "/emailPremium/savePolicyServerStatus";

        var data = {
            policServerStatus: policServerStatus
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.policyServerLoading = true;

            if (response.data.status === 1) {

                $scope.failedToFetch = true;
                $scope.couldNotConnect = true;
                $scope.changesApplied = false;

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.policyServerLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }


    };

});

/* Java script code for Email Policy Server */

/* Java script code to manage mail queue */

app.controller('mailQueue', function ($scope, $http) {

    $scope.currentPage = 1;
    $scope.recordsToShow = 10;
    $scope.cyberpanelLoading = true;

    $scope.fetchMailQueue = function () {
        $scope.cyberpanelLoading = false;
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            folder: $scope.folder,
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };

        dataurl = "/emailPremium/fetchMailQueue";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.queues = JSON.parse(response.data.data);
                $scope.pagination = response.data.pagination;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };
    $scope.fetchMailQueue();

    $scope.fetchMessage = function (id) {
        $scope.cyberpanelLoading = false;
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            id: id
        };

        dataurl = "/emailPremium/fetchMessage";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.emailMessageContent = response.data.emailMessageContent;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };

    $scope.delete = function (type) {
        $scope.cyberpanelLoading = false;
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            type: type
        };

        dataurl = "/emailPremium/delete";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully deleted.',
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
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };

    $scope.flushQueue = function () {
        $scope.cyberpanelLoading = false;
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {};

        dataurl = "/emailPremium/flushQueue";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Delivery scheduled.',
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
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };
});

/* Java script code to manage mail queue ends here */

app.controller('MailScanner', function ($scope, $http, $timeout, $window) {

    $scope.SpamAssassinNotifyBox = true;
    $scope.SpamAssassinInstallBox = true;
    $scope.SpamAssassinLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.SpamAssassinSuccessfullyInstalled = true;
    $scope.installationFailed = true;

    $scope.installSpamAssassin = function () {

        $scope.SpamAssassinNotifyBox = true;
        $scope.SpamAssassinInstallBox = true;
        $scope.SpamAssassinLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.SpamAssassinSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/emailPremium/installMailScanner";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status === 1) {

                $scope.SpamAssassinNotifyBox = true;
                $scope.SpamAssassinInstallBox = false;
                $scope.SpamAssassinLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.SpamAssassinSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getRequestStatus();

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.SpamAssassinNotifyBox = false;
                $scope.SpamAssassinInstallBox = true;
                $scope.SpamAssassinLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.SpamAssassinSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.SpamAssassinNotifyBox = false;
            $scope.SpamAssassinInstallBox = false;
            $scope.SpamAssassinLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.SpamAssassinSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }

    };

    function getRequestStatus() {

        $scope.SpamAssassinNotifyBox = true;
        $scope.SpamAssassinInstallBox = false;
        $scope.SpamAssassinLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.SpamAssassinSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/emailPremium/installStatusMailScanner";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.SpamAssassinNotifyBox = true;
                $scope.SpamAssassinInstallBox = false;
                $scope.SpamAssassinLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.SpamAssassinSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            } else {
                // Notifications
                $timeout.cancel();
                $scope.SpamAssassinNotifyBox = false;
                $scope.SpamAssassinInstallBox = false;
                $scope.SpamAssassinLoading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.SpamAssassinSuccessfullyInstalled = false;
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.SpamAssassinNotifyBox = false;
            $scope.SpamAssassinInstallBox = false;
            $scope.SpamAssassinLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.SpamAssassinSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }
});