/**
 * Created by usman on 7/26/17.
 */


function getCookie(name) {
    var cookieValue = null;
    var t = document.cookie;
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

/* Java script code to create account */
app.controller('createWebsite', function ($scope, $http, $timeout, $window) {

    $scope.webSiteCreationLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    var statusFile;

    $scope.createWebsite = function () {

        $scope.webSiteCreationLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Starting creation..";

        var ssl, dkimCheck, openBasedir;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        if ($scope.dkimCheck === true) {
            dkimCheck = 1;
        } else {
            dkimCheck = 0
        }

        if ($scope.openBasedir === true) {
            openBasedir = 1;
        } else {
            openBasedir = 0
        }

        url = "/websites/submitWebsiteCreation";

        var package = $scope.packageForWebsite;
        var domainName = $scope.domainNameCreate;
        var adminEmail = $scope.adminEmail;
        var phpSelection = $scope.phpSelection;
        var websiteOwner = $scope.websiteOwner;


        var data = {
            package: package,
            domainName: domainName,
            adminEmail: adminEmail,
            phpSelection: phpSelection,
            ssl: ssl,
            websiteOwner: websiteOwner,
            dkimCheck: dkimCheck,
            openBasedir: openBasedir
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createWebSiteStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.webSiteCreationLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    };
    $scope.goBack = function () {
        $scope.webSiteCreationLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.webSiteCreationLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = false;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.webSiteCreationLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = false;
                    $scope.success = true;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    }

});
/* Java script code to create account ends here */

/* Java script code to list accounts */

$("#listFail").hide();


app.controller('listWebsites', function ($scope, $http) {


    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.getFurtherWebsitesFromDB = function () {

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };


        dataurl = "/websites/fetchWebsitesList";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            if (response.data.listWebSiteStatus === 1) {

                $scope.WebSitesList = JSON.parse(response.data.data);
                $scope.pagination = response.data.pagination;
                $scope.clients = JSON.parse(response.data.data);
                $("#listFail").hide();
            } else {
                $("#listFail").fadeIn();
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
        }


    };
    $scope.getFurtherWebsitesFromDB();

    $scope.cyberPanelLoading = true;

    $scope.issueSSL = function (virtualHost) {
        $scope.cyberPanelLoading = false;

        var url = "/manageSSL/issueSSL";


        var data = {
            virtualHost: virtualHost
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.SSL === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'SSL successfully issued.',
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


});

app.controller('listChildDomainsMain', function ($scope, $http, $timeout) {


    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.getFurtherWebsitesFromDB = function () {

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };


        dataurl = "/websites/fetchChildDomainsMain";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            if (response.data.listWebSiteStatus === 1) {

                $scope.WebSitesList = JSON.parse(response.data.data);
                $scope.pagination = response.data.pagination;
                $scope.clients = JSON.parse(response.data.data);
                $("#listFail").hide();
            } else {
                $("#listFail").fadeIn();
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
        }


    };
    $scope.getFurtherWebsitesFromDB();

    $scope.cyberPanelLoading = true;

    $scope.issueSSL = function (virtualHost) {
        $scope.cyberPanelLoading = false;

        var url = "/manageSSL/issueSSL";


        var data = {
            virtualHost: virtualHost
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.SSL === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'SSL successfully issued.',
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

    $scope.initConvert = function(virtualHost){
        $scope.domainName = virtualHost;
    };

    var statusFile;

    $scope.installationProgress = true;

    $scope.convert = function () {

        $scope.cyberPanelLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Starting creation..";

        var ssl, dkimCheck, openBasedir;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        if ($scope.dkimCheck === true) {
            dkimCheck = 1;
        } else {
            dkimCheck = 0
        }

        if ($scope.openBasedir === true) {
            openBasedir = 1;
        } else {
            openBasedir = 0
        }

        url = "/websites/convertDomainToSite";


        var data = {
            package: $scope.packageForWebsite,
            domainName: $scope.domainName,
            adminEmail: $scope.adminEmail,
            phpSelection: $scope.phpSelection,
            websiteOwner: $scope.websiteOwner,
            ssl: ssl,
            dkimCheck: dkimCheck,
            openBasedir: openBasedir
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createWebSiteStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.cyberPanelLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.goBackDisable = false;

                $scope.currentStatus = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.cyberPanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    };
    $scope.goBack = function () {
        $scope.cyberPanelLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.cyberPanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.cyberPanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $scope.currentStatus = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberPanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    }


});

/* Java script code to list accounts ends here */


/* Java script code to delete Website */


$("#websiteDeleteFailure").hide();
$("#websiteDeleteSuccess").hide();

$("#deleteWebsiteButton").hide();
$("#deleteLoading").hide();

app.controller('deleteWebsiteControl', function ($scope, $http) {


    $scope.deleteWebsite = function () {

        $("#deleteWebsiteButton").fadeIn();


    };

    $scope.deleteWebsiteFinal = function () {

        $("#deleteLoading").show();

        var websiteName = $scope.websiteToBeDeleted;


        url = "/websites/submitWebsiteDeletion";

        var data = {
            websiteName: websiteName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.websiteDeleteStatus === 0) {
                $scope.errorMessage = response.data.error_message;
                $("#websiteDeleteFailure").fadeIn();
                $("#websiteDeleteSuccess").hide();
                $("#deleteWebsiteButton").hide();


                $("#deleteLoading").hide();

            } else {
                $("#websiteDeleteFailure").hide();
                $("#websiteDeleteSuccess").fadeIn();
                $("#deleteWebsiteButton").hide();
                $scope.deletedWebsite = websiteName;
                $("#deleteLoading").hide();

            }


        }

        function cantLoadInitialDatas(response) {
        }


    };

});


/* Java script code to delete website ends here */


/* Java script code to modify package ends here */

$("#canNotModify").hide();
$("#webSiteDetailsToBeModified").hide();
$("#websiteModifyFailure").hide();
$("#websiteModifySuccess").hide();
$("#websiteSuccessfullyModified").hide();
$("#modifyWebsiteLoading").hide();
$("#modifyWebsiteButton").hide();

app.controller('modifyWebsitesController', function ($scope, $http) {

    $scope.fetchWebsites = function () {

        $("#modifyWebsiteLoading").show();


        var websiteToBeModified = $scope.websiteToBeModified;

        url = "/websites/getWebsiteDetails";

        var data = {
            websiteToBeModified: websiteToBeModified,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.modifyStatus === 0) {
                console.log(response.data);
                $scope.errorMessage = response.data.error_message;
                $("#websiteModifyFailure").fadeIn();
                $("#websiteModifySuccess").hide();
                $("#modifyWebsiteButton").hide();
                $("#modifyWebsiteLoading").hide();
                $("#canNotModify").hide();


            } else {
                console.log(response.data);
                $("#modifyWebsiteButton").fadeIn();

                $scope.adminEmail = response.data.adminEmail;
                $scope.currentPack = response.data.current_pack;
                $scope.webpacks = JSON.parse(response.data.packages);
                $scope.adminNames = JSON.parse(response.data.adminNames);
                $scope.currentAdmin = response.data.currentAdmin;

                $("#webSiteDetailsToBeModified").fadeIn();
                $("#websiteModifySuccess").fadeIn();
                $("#modifyWebsiteButton").fadeIn();
                $("#modifyWebsiteLoading").hide();
                $("#canNotModify").hide();


            }


        }

        function cantLoadInitialDatas(response) {
            $("#websiteModifyFailure").fadeIn();
        }

    };


    $scope.modifyWebsiteFunc = function () {

        var domain = $scope.websiteToBeModified;
        var packForWeb = $scope.selectedPack;
        var email = $scope.adminEmail;
        var phpVersion = $scope.phpSelection;
        var admin = $scope.selectedAdmin;


        $("#websiteModifyFailure").hide();
        $("#websiteModifySuccess").hide();
        $("#websiteSuccessfullyModified").hide();
        $("#canNotModify").hide();
        $("#modifyWebsiteLoading").fadeIn();


        url = "/websites/saveWebsiteChanges";

        var data = {
            domain: domain,
            packForWeb: packForWeb,
            email: email,
            phpVersion: phpVersion,
            admin: admin
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.saveStatus === 0) {
                $scope.errMessage = response.data.error_message;

                $("#canNotModify").fadeIn();
                $("#websiteModifyFailure").hide();
                $("#websiteModifySuccess").hide();
                $("#websiteSuccessfullyModified").hide();
                $("#modifyWebsiteLoading").hide();


            } else {
                $("#modifyWebsiteButton").hide();
                $("#canNotModify").hide();
                $("#websiteModifyFailure").hide();
                $("#websiteModifySuccess").hide();

                $("#websiteSuccessfullyModified").fadeIn();
                $("#modifyWebsiteLoading").hide();

                $scope.websiteModified = domain;


            }


        }

        function cantLoadInitialDatas(response) {
            $scope.errMessage = response.data.error_message;
            $("#canNotModify").fadeIn();
        }


    };

});

/* Java script code to Modify Pacakge ends here */


/* Java script code to create account */

app.controller('websitePages', function ($scope, $http, $timeout, $window) {

    $scope.logFileLoading = true;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedData = true;
    $scope.hideLogs = true;
    $scope.hideErrorLogs = true;

    $scope.hidelogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.hideErrorLogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.fileManagerURL = "/filemanager/" + $("#domainNamePage").text();
    $scope.wordPressInstallURL = $("#domainNamePage").text() + "/wordpressInstall";
    $scope.joomlaInstallURL = $("#domainNamePage").text() + "/joomlaInstall";
    $scope.setupGit = $("#domainNamePage").text() + "/setupGit";
    $scope.installPrestaURL = $("#domainNamePage").text() + "/installPrestaShop";
    $scope.installMagentoURL = $("#domainNamePage").text() + "/installMagento";
    $scope.domainAliasURL = "/websites/" + $("#domainNamePage").text() + "/domainAlias";
    $scope.previewUrl = "/preview/" + $("#domainNamePage").text() + "/";

    var logType = 0;
    $scope.pageNumber = 1;

    $scope.fetchLogs = function (type) {

        var pageNumber = $scope.pageNumber;


        if (type == 3) {
            pageNumber = $scope.pageNumber + 1;
            $scope.pageNumber = pageNumber;
        } else if (type == 4) {
            pageNumber = $scope.pageNumber - 1;
            $scope.pageNumber = pageNumber;
        } else {
            logType = type;
        }


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = false;
        $scope.hideErrorLogs = true;


        url = "/websites/getDataFromLogFile";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            logType: logType,
            virtualHost: domainNamePage,
            page: pageNumber,
        };

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
                $scope.couldNotConnect = true;
                $scope.fetchedData = false;
                $scope.hideLogs = false;


                $scope.records = JSON.parse(response.data.data);

            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = false;


                $scope.errorMessage = response.data.error_message;
                console.log(domainNamePage)

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedData = true;
            $scope.hideLogs = false;

        }


    };

    $scope.errorPageNumber = 1;


    $scope.fetchErrorLogs = function (type) {

        var errorPageNumber = $scope.errorPageNumber;


        if (type == 3) {
            errorPageNumber = $scope.errorPageNumber + 1;
            $scope.errorPageNumber = errorPageNumber;
        } else if (type == 4) {
            errorPageNumber = $scope.errorPageNumber - 1;
            $scope.errorPageNumber = errorPageNumber;
        } else {
            logType = type;
        }

        // notifications

        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = true;
        $scope.hideErrorLogs = true;
        $scope.hideLogs = false;


        url = "/websites/fetchErrorLogs";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            virtualHost: domainNamePage,
            page: errorPageNumber,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.logstatus === 1) {


                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = false;
                $scope.hideErrorLogs = false;


                $scope.errorLogsData = response.data.data;

            } else {

                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = true;
                $scope.hideErrorLogs = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            // notifications

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedData = true;
            $scope.hideLogs = true;
            $scope.hideErrorLogs = true;

        }


    };

    ///////// Configurations Part

    $scope.configurationsBox = true;
    $scope.configsFetched = true;
    $scope.couldNotFetchConfigs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedConfigsData = true;
    $scope.configFileLoading = true;
    $scope.configSaved = true;
    $scope.couldNotSaveConfigurations = true;

    $scope.hideconfigbtn = function () {

        $scope.configurationsBox = true;
    };

    $scope.fetchConfigurations = function () {


        $scope.hidsslconfigs = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;


        //Rewrite rules
        $scope.configurationsBoxRewrite = true;
        $scope.rewriteRulesFetched = true;
        $scope.couldNotFetchRewriteRules = true;
        $scope.rewriteRulesSaved = true;
        $scope.couldNotSaveRewriteRules = true;
        $scope.fetchedRewriteRules = true;
        $scope.saveRewriteRulesBTN = true;

        ///

        $scope.configFileLoading = false;


        url = "/websites/getDataFromConfigFile";

        var virtualHost = $("#domainNamePage").text();


        var data = {
            virtualHost: virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus === 1) {

                //Rewrite rules

                $scope.configurationsBoxRewrite = true;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;

                ///

                $scope.configurationsBox = false;
                $scope.configsFetched = false;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = false;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = false;


                $scope.configData = response.data.configData;

            } else {

                //Rewrite rules
                $scope.configurationsBoxRewrite = true;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;

                ///
                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            //Rewrite rules
            $scope.configurationsBoxRewrite = true;
            $scope.rewriteRulesFetched = true;
            $scope.couldNotFetchRewriteRules = true;
            $scope.rewriteRulesSaved = true;
            $scope.couldNotSaveRewriteRules = true;
            $scope.fetchedRewriteRules = true;
            $scope.saveRewriteRulesBTN = true;
            ///

            $scope.configurationsBox = false;
            $scope.configsFetched = true;
            $scope.couldNotFetchConfigs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedConfigsData = true;
            $scope.configFileLoading = true;
            $scope.configSaved = true;
            $scope.couldNotSaveConfigurations = true;


        }


    };

    $scope.saveCongiruations = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveConfigsToFile";

        var virtualHost = $("#domainNamePage").text();
        var configData = $scope.configData;


        var data = {
            virtualHost: virtualHost,
            configData: configData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus === 1) {

                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = false;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;


            } else {
                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = false;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = false;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configurationsBox = false;
            $scope.configsFetched = true;
            $scope.couldNotFetchConfigs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedConfigsData = true;
            $scope.configFileLoading = true;
            $scope.configSaved = true;
            $scope.couldNotSaveConfigurations = true;


        }


    };


    ///////// Rewrite Rules

    $scope.configurationsBoxRewrite = true;
    $scope.rewriteRulesFetched = true;
    $scope.couldNotFetchRewriteRules = true;
    $scope.rewriteRulesSaved = true;
    $scope.couldNotSaveRewriteRules = true;
    $scope.fetchedRewriteRules = true;
    $scope.saveRewriteRulesBTN = true;

    $scope.hideRewriteRulesbtn = function () {
        $scope.configurationsBoxRewrite = true;
    };

    $scope.fetchRewriteFules = function () {

        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.changePHPView = true;


        $scope.configurationsBox = true;
        $scope.configsFetched = true;
        $scope.couldNotFetchConfigs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedConfigsData = true;
        $scope.configFileLoading = true;
        $scope.configSaved = true;
        $scope.couldNotSaveConfigurations = true;
        $scope.saveConfigBtn = true;

        $scope.configFileLoading = false;


        url = "/websites/getRewriteRules";

        var virtualHost = $("#domainNamePage").text();


        var data = {
            virtualHost: virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {


                // from main

                $scope.configurationsBox = true;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.fetchedConfigsData = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;

                // main ends

                $scope.configFileLoading = true;

                //


                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = false;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = false;
                $scope.saveRewriteRulesBTN = false;
                $scope.couldNotConnect = true;


                $scope.rewriteRules = response.data.rewriteRules;

            } else {
                // from main
                $scope.configurationsBox = true;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;
                // from main

                $scope.configFileLoading = true;

                ///

                $scope.configurationsBoxRewrite = true;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = false;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;
                $scope.couldNotConnect = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
            // from main

            $scope.configurationsBox = true;
            $scope.configsFetched = true;
            $scope.couldNotFetchConfigs = true;
            $scope.fetchedConfigsData = true;
            $scope.configFileLoading = true;
            $scope.configSaved = true;
            $scope.couldNotSaveConfigurations = true;
            $scope.saveConfigBtn = true;

            // from main

            $scope.configFileLoading = true;

            ///

            $scope.configurationsBoxRewrite = true;
            $scope.rewriteRulesFetched = true;
            $scope.couldNotFetchRewriteRules = true;
            $scope.rewriteRulesSaved = true;
            $scope.couldNotSaveRewriteRules = true;
            $scope.fetchedRewriteRules = true;
            $scope.saveRewriteRulesBTN = true;

            $scope.couldNotConnect = false;


        }


    };

    $scope.saveRewriteRules = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveRewriteRules";

        var virtualHost = $("#domainNamePage").text();
        var rewriteRules = $scope.rewriteRules;


        var data = {
            virtualHost: virtualHost,
            rewriteRules: rewriteRules,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {

                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = false;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;
                $scope.configFileLoading = true;


            } else {
                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = false;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = false;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = false;

                $scope.configFileLoading = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configurationsBoxRewrite = false;
            $scope.rewriteRulesFetched = false;
            $scope.couldNotFetchRewriteRules = true;
            $scope.rewriteRulesSaved = true;
            $scope.couldNotSaveRewriteRules = true;
            $scope.fetchedRewriteRules = true;
            $scope.saveRewriteRulesBTN = false;

            $scope.configFileLoading = true;

            $scope.couldNotConnect = false;


        }


    };

    //////// Application Installation part

    $scope.installationDetailsForm = true;
    $scope.installationDetailsFormJoomla = true;
    $scope.applicationInstallerLoading = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;


    $scope.installationDetails = function () {

        $scope.installationDetailsForm = !$scope.installationDetailsForm;
        $scope.installationDetailsFormJoomla = true;

    };

    $scope.installationDetailsJoomla = function () {

        $scope.installationDetailsFormJoomla = !$scope.installationDetailsFormJoomla;
        $scope.installationDetailsForm = true;

    };

    $scope.installWordpress = function () {


        $scope.installationDetailsForm = false;
        $scope.applicationInstallerLoading = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;

        var domain = $("#domainNamePage").text();
        var path = $scope.installPath;

        url = "/websites/installWordpress";

        var home = "1";

        if (typeof path != 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                if (typeof path != 'undefined') {
                    $scope.installationURL = "http://" + domain + "/" + path;
                } else {
                    $scope.installationURL = domain;
                }

                $scope.installationDetailsForm = false;
                $scope.applicationInstallerLoading = true;
                $scope.installationFailed = true;
                $scope.installationSuccessfull = false;
                $scope.couldNotConnect = true;

            } else {

                $scope.installationDetailsForm = false;
                $scope.applicationInstallerLoading = true;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.installationDetailsForm = false;
            $scope.applicationInstallerLoading = true;
            $scope.installationFailed = true;
            $scope.installationSuccessfull = true;
            $scope.couldNotConnect = false;

        }

    };

    $scope.installJoomla = function () {


        $scope.installationDetailsFormJoomla = false;
        $scope.applicationInstallerLoading = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;

        var domain = $("#domainNamePage").text();
        var path = $scope.installPath;
        var sitename = $scope.sitename;
        var username = $scope.username;
        var password = $scope.password;
        var prefix = $scope.prefix;


        url = "/websites/installJoomla";

        var home = "1";

        if (typeof path != 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            sitename: sitename,
            username: username,
            password: password,
            prefix: prefix,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                if (typeof path != 'undefined') {
                    $scope.installationURL = "http://" + domain + "/" + path;
                } else {
                    $scope.installationURL = domain;
                }

                $scope.installationDetailsFormJoomla = false;
                $scope.applicationInstallerLoading = true;
                $scope.installationFailed = true;
                $scope.installationSuccessfull = false;
                $scope.couldNotConnect = true;

            } else {

                $scope.installationDetailsFormJoomla = false;
                $scope.applicationInstallerLoading = true;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.installationDetailsFormJoomla = false;
            $scope.applicationInstallerLoading = true;
            $scope.installationFailed = true;
            $scope.installationSuccessfull = true;
            $scope.couldNotConnect = false;

        }

    };


    //////// SSL Part

    $scope.sslSaved = true;
    $scope.couldNotSaveSSL = true;
    $scope.hidsslconfigs = true;
    $scope.couldNotConnect = true;


    $scope.hidesslbtn = function () {
        $scope.hidsslconfigs = true;
    };

    $scope.addSSL = function () {
        $scope.hidsslconfigs = false;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;
    };

    $scope.saveSSL = function () {


        $scope.configFileLoading = false;

        url = "/websites/saveSSL";

        var virtualHost = $("#domainNamePage").text();
        var cert = $scope.cert;
        var key = $scope.key;


        var data = {
            virtualHost: virtualHost,
            cert: cert,
            key: key
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.sslStatus == 1) {

                $scope.sslSaved = false;
                $scope.couldNotSaveSSL = true;
                $scope.couldNotConnect = true;
                $scope.configFileLoading = true;


            } else {

                $scope.sslSaved = true;
                $scope.couldNotSaveSSL = false;
                $scope.couldNotConnect = true;
                $scope.configFileLoading = true;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.sslSaved = true;
            $scope.couldNotSaveSSL = true;
            $scope.couldNotConnect = false;
            $scope.configFileLoading = true;


        }

    };

    //// Change PHP Master

    $scope.failedToChangePHPMaster = true;
    $scope.phpChangedMaster = true;
    $scope.couldNotConnect = true;

    $scope.changePHPView = true;


    $scope.hideChangePHPMaster = function () {
        $scope.changePHPView = true;
    };

    $scope.changePHPMaster = function () {
        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = false;
    };

    $scope.changePHPVersionMaster = function (childDomain, phpSelection) {

        // notifcations

        $scope.configFileLoading = false;

        var url = "/websites/changePHP";

        var data = {
            childDomain: $("#domainNamePage").text(),
            phpSelection: $scope.phpSelectionMaster,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePHP === 1) {

                $scope.configFileLoading = true;
                $scope.websiteDomain = $("#domainNamePage").text();


                // notifcations

                $scope.failedToChangePHPMaster = true;
                $scope.phpChangedMaster = false;
                $scope.couldNotConnect = true;


            } else {

                $scope.configFileLoading = true;
                $scope.errorMessage = response.data.error_message;

                // notifcations

                $scope.failedToChangePHPMaster = false;
                $scope.phpChangedMaster = true;
                $scope.couldNotConnect = true;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configFileLoading = true;

            // notifcations

            $scope.failedToChangePHPMaster = true;
            $scope.phpChangedMaster = true;
            $scope.couldNotConnect = false;

        }

    };

    ////// create domain part

    $("#domainCreationForm").hide();

    $scope.showCreateDomainForm = function () {
        $("#domainCreationForm").fadeIn();
    };

    $scope.hideDomainCreationForm = function () {
        $("#domainCreationForm").fadeOut();
    };

    $scope.masterDomain = $("#domainNamePage").text();

    // notifcations settings
    $scope.domainLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    var statusFile;

    $scope.createDomain = function () {

        $scope.domainLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting creation..";

        var ssl, dkimCheck, openBasedir;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        if ($scope.dkimCheck === true) {
            dkimCheck = 1;
        } else {
            dkimCheck = 0
        }

        if ($scope.openBasedir === true) {
            openBasedir = 1;
        } else {
            openBasedir = 0
        }


        url = "/websites/submitDomainCreation";
        var domainName = $scope.domainNameCreate;
        var phpSelection = $scope.phpSelection;

        var path = $scope.docRootPath;

        if (typeof path === 'undefined') {
            path = "";
        }


        var data = {
            domainName: domainName,
            phpSelection: phpSelection,
            ssl: ssl,
            path: path,
            masterDomain: $("#domainNamePage").text(),
            dkimCheck: dkimCheck,
            openBasedir: openBasedir
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createWebSiteStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.domainLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.domainLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    };

    $scope.goBack = function () {
        $scope.domainLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.domainLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = false;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.domainLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = false;
                    $scope.success = true;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.domainLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    }


    ////// List Domains Part

    ////////////////////////

    // notifcations

    $scope.phpChanged = true;
    $scope.domainError = true;
    $scope.couldNotConnect = true;
    $scope.domainDeleted = true;
    $scope.sslIssued = true;
    $scope.childBaseDirChanged = true;

    $("#listDomains").hide();


    $scope.showListDomains = function () {
        fetchDomains();
        $("#listDomains").fadeIn();
    };

    $scope.hideListDomains = function () {
        $("#listDomains").fadeOut();
    };

    function fetchDomains() {
        $scope.domainLoading = false;

        var url = "/websites/fetchDomains";

        var data = {
            masterDomain: $("#domainNamePage").text(),
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus === 1) {

                $scope.childDomains = JSON.parse(response.data.data);
                $scope.domainLoading = true;


            } else {
                $scope.domainError = false;
                $scope.errorMessage = response.data.error_message;
                $scope.domainLoading = true;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.couldNotConnect = false;

        }

    }


    $scope.changePHP = function (childDomain, phpSelection) {

        // notifcations

        $scope.phpChanged = true;
        $scope.domainError = true;
        $scope.couldNotConnect = true;
        $scope.domainDeleted = true;
        $scope.sslIssued = true;
        $scope.domainLoading = false;
        $scope.childBaseDirChanged = true;

        var url = "/websites/changePHP";

        var data = {
            childDomain: childDomain,
            phpSelection: phpSelection,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePHP === 1) {

                $scope.domainLoading = true;

                $scope.changedPHPVersion = phpSelection;


                // notifcations

                $scope.phpChanged = false;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.childBaseDirChanged = true;


            } else {
                $scope.errorMessage = response.data.error_message;
                $scope.domainLoading = true;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = false;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.childBaseDirChanged = true;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.domainLoading = true;

            // notifcations

            $scope.phpChanged = true;
            $scope.domainError = false;
            $scope.couldNotConnect = true;
            $scope.domainDeleted = true;
            $scope.sslIssued = true;
            $scope.childBaseDirChanged = true;

        }

    };

    $scope.changeChildBaseDir = function (childDomain, openBasedirValue) {

        // notifcations

        $scope.phpChanged = true;
        $scope.domainError = true;
        $scope.couldNotConnect = true;
        $scope.domainDeleted = true;
        $scope.sslIssued = true;
        $scope.domainLoading = false;
        $scope.childBaseDirChanged = true;


        var url = "/websites/changeOpenBasedir";

        var data = {
            domainName: childDomain,
            openBasedirValue: openBasedirValue
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changeOpenBasedir === 1) {

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.domainLoading = true;
                $scope.childBaseDirChanged = false;

            } else {

                $scope.phpChanged = true;
                $scope.domainError = false;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.domainLoading = true;
                $scope.childBaseDirChanged = true;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.phpChanged = true;
            $scope.domainError = true;
            $scope.couldNotConnect = false;
            $scope.domainDeleted = true;
            $scope.sslIssued = true;
            $scope.domainLoading = true;
            $scope.childBaseDirChanged = true;


        }

    }

    $scope.deleteChildDomain = function (childDomain) {
        $scope.domainLoading = false;

        // notifcations

        $scope.phpChanged = true;
        $scope.domainError = true;
        $scope.couldNotConnect = true;
        $scope.domainDeleted = true;
        $scope.sslIssued = true;

        url = "/websites/submitDomainDeletion";

        var data = {
            websiteName: childDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.websiteDeleteStatus === 1) {

                $scope.domainLoading = true;
                $scope.deletedDomain = childDomain;

                fetchDomains();


                // notifications

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = false;
                $scope.sslIssued = true;


            } else {
                $scope.errorMessage = response.data.error_message;
                $scope.domainLoading = true;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = false;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.domainLoading = true;

            // notifcations

            $scope.phpChanged = true;
            $scope.domainError = true;
            $scope.couldNotConnect = false;
            $scope.domainDeleted = true;
            $scope.sslIssued = true;

        }

    };

    $scope.issueSSL = function (childDomain, path) {
        $scope.domainLoading = false;

        // notifcations

        $scope.phpChanged = true;
        $scope.domainError = true;
        $scope.couldNotConnect = true;
        $scope.domainDeleted = true;
        $scope.sslIssued = true;
        $scope.childBaseDirChanged = true;

        var url = "/manageSSL/issueSSL";


        var data = {
            virtualHost: childDomain,
            path: path,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.SSL === 1) {

                $scope.domainLoading = true;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = false;
                $scope.childBaseDirChanged = true;


                $scope.sslDomainIssued = childDomain;


            } else {
                $scope.domainLoading = true;

                $scope.errorMessage = response.data.error_message;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = false;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.childBaseDirChanged = true;

            }


        }

        function cantLoadInitialDatas(response) {

            // notifcations

            $scope.phpChanged = true;
            $scope.domainError = true;
            $scope.couldNotConnect = false;
            $scope.domainDeleted = true;
            $scope.sslIssued = true;
            $scope.childBaseDirChanged = true;


        }


    };


    /// Open_basedir protection

    $scope.baseDirLoading = true;
    $scope.operationFailed = true;
    $scope.operationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.openBaseDirBox = true;


    $scope.openBaseDirView = function () {
        $scope.openBaseDirBox = false;
    };

    $scope.hideOpenBasedir = function () {
        $scope.openBaseDirBox = true;
    };

    $scope.applyOpenBasedirChanges = function (childDomain, phpSelection) {

        // notifcations

        $scope.baseDirLoading = false;
        $scope.operationFailed = true;
        $scope.operationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.openBaseDirBox = false;


        var url = "/websites/changeOpenBasedir";

        var data = {
            domainName: $("#domainNamePage").text(),
            openBasedirValue: $scope.openBasedirValue
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changeOpenBasedir === 1) {

                $scope.baseDirLoading = true;
                $scope.operationFailed = true;
                $scope.operationSuccessfull = false;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

            } else {

                $scope.baseDirLoading = true;
                $scope.operationFailed = false;
                $scope.operationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.baseDirLoading = true;
            $scope.operationFailed = true;
            $scope.operationSuccessfull = true;
            $scope.couldNotConnect = false;
            $scope.openBaseDirBox = false;


        }

    }


    // REWRITE Template

    const httpToHTTPS = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteCond %{HTTPS}  !=on
RewriteRule ^/?(.*) https://%{SERVER_NAME}/$1 [R,L]

### End CyberPanel Generated Rules.

`;

    const nonWWWToWWW = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteCond %{HTTP_HOST} !^www\. [NC]
RewriteRule ^(.*)$ http://www.%{HTTP_HOST}%{REQUEST_URI} [R=301,L]

### End CyberPanel Generated Rules.

`;

    $scope.applyRewriteTemplate = function () {

        if ($scope.rewriteTemplate === "Force HTTP -> HTTPS") {
            $scope.rewriteRules = httpToHTTPS + $scope.rewriteRules;
        } else if ($scope.rewriteTemplate === "Force NON-WWW -> WWW") {
            $scope.rewriteRules = nonWWWToWWW + $scope.rewriteRules;
        }
    };


});

/* Java script code to create account ends here */

/* Java script code to suspend/un-suspend Website */

app.controller('suspendWebsiteControl', function ($scope, $http) {

    $scope.suspendLoading = true;
    $scope.stateView = true;

    $scope.websiteSuspendFailure = true;
    $scope.websiteUnsuspendFailure = true;
    $scope.websiteSuccess = true;
    $scope.couldNotConnect = true;

    $scope.showSuspendUnsuspend = function () {

        $scope.stateView = false;


    };

    $scope.save = function () {

        $scope.suspendLoading = false;

        var websiteName = $scope.websiteToBeSuspended
        var state = $scope.state;


        url = "/websites/submitWebsiteStatus";

        var data = {
            websiteName: websiteName,
            state: state,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.websiteStatus === 1) {
                if (state == "Suspend") {

                    $scope.suspendLoading = true;
                    $scope.stateView = false;

                    $scope.websiteSuspendFailure = true;
                    $scope.websiteUnsuspendFailure = true;
                    $scope.websiteSuccess = false;
                    $scope.couldNotConnect = true;

                    $scope.websiteStatus = websiteName;
                    $scope.finalStatus = "Suspended";

                } else {
                    $scope.suspendLoading = true;
                    $scope.stateView = false;

                    $scope.websiteSuspendFailure = true;
                    $scope.websiteUnsuspendFailure = true;
                    $scope.websiteSuccess = false;
                    $scope.couldNotConnect = true;

                    $scope.websiteStatus = websiteName;
                    $scope.finalStatus = "Un-suspended";

                }

            } else {

                if (state == "Suspend") {

                    $scope.suspendLoading = true;
                    $scope.stateView = false;

                    $scope.websiteSuspendFailure = false;
                    $scope.websiteUnsuspendFailure = true;
                    $scope.websiteSuccess = true;
                    $scope.couldNotConnect = true;


                } else {
                    $scope.suspendLoading = true;
                    $scope.stateView = false;

                    $scope.websiteSuspendFailure = true;
                    $scope.websiteUnsuspendFailure = false;
                    $scope.websiteSuccess = true;
                    $scope.couldNotConnect = true;


                }


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
            $scope.suspendLoading = true;
            $scope.stateView = true;

            $scope.websiteSuspendFailure = true;
            $scope.websiteUnsuspendFailure = true;
            $scope.websiteSuccess = true;

        }


    };

});

/* Java script code to suspend/un-suspend ends here */

/* Java script code to manage cron */

app.controller('manageCronController', function ($scope, $http) {
    $("#manageCronLoading").hide();
    $("#modifyCronForm").hide();
    $("#cronTable").hide();
    $("#saveCronButton").hide();
    $("#addCronButton").hide();

    $("#addCronFailure").hide();
    $("#cronEditSuccess").hide();
    $("#fetchCronFailure").hide();

    $scope.fetchWebsites = function () {

        $("#manageCronLoading").show();
        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();
        var websiteToBeModified = $scope.websiteToBeModified;
        url = "/websites/getWebsiteCron";

        var data = {
            domain: websiteToBeModified,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (response.data.getWebsiteCron === 0) {
                console.log(response.data);
                $scope.errorMessage = response.data.error_message;
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").hide();
                $("#saveCronButton").hide();
                $("#addCronButton").hide();
            } else {
                console.log(response.data);
                var finalData = response.data.crons;
                $scope.cronList = finalData;
                $("#cronTable").show();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").hide();
                $("#saveCronButton").hide();
                $("#addCronButton").hide();
            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#cronTable").hide();
            $("#fetchCronFailure").show();
            $("#addCronFailure").hide();
            $("#cronEditSuccess").hide();
        }
    };

    $scope.fetchCron = function (cronLine) {

        $("#cronTable").show();
        $("#manageCronLoading").show();
        $("#modifyCronForm").show();
        $("#saveCronButton").show();
        $("#addCronButton").hide();

        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        $scope.line = cronLine;
        console.log($scope.line);

        var websiteToBeModified = $scope.websiteToBeModified;
        url = "/websites/getCronbyLine";
        var data = {
            domain: websiteToBeModified,
            line: cronLine
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response);

            if (response.data.getWebsiteCron === 0) {
                console.log(response.data);
                $scope.errorMessage = response.data.error_message;
                $("#cronTable").show();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").hide();
                $("#saveCronButton").hide();
                $("#addCronButton").hide();
            } else {
                console.log(response.data);

                $scope.minute = response.data.cron.minute
                $scope.hour = response.data.cron.hour
                $scope.monthday = response.data.cron.monthday
                $scope.month = response.data.cron.month
                $scope.weekday = response.data.cron.weekday
                $scope.command = response.data.cron.command
                $scope.line = response.data.line

                $("#cronTable").show();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").fadeIn();
                $("#addCronButton").hide();
                $("#saveCronButton").show();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#fetchCronFailure").show();
            $("#addCronFailure").hide();
            $("#cronEditSuccess").hide();
        }
    };

    $scope.populate = function () {
        splitTime = $scope.defined.split(" ");
        $scope.minute = splitTime[0];
        $scope.hour = splitTime[1];
        $scope.monthday = splitTime[2];
        $scope.month = splitTime[3];
        $scope.weekday = splitTime[4];
    }

    $scope.addCronForm = function () {

        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();
        $("#manageCronLoading").hide();
        if (!$scope.websiteToBeModified) {
            alert("Please select a domain first");
        } else {
            $scope.minute = $scope.hour = $scope.monthday = $scope.month = $scope.weekday = $scope.command = $scope.line = "";

            $("#cronTable").hide();
            $("#manageCronLoading").hide();
            $("#modifyCronForm").show();
            $("#saveCronButton").hide()
            $("#addCronButton").show();
        }
    };

    $scope.addCronFunc = function () {

        $("#manageCronLoading").show();
        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        var websiteToBeModified = $scope.websiteToBeModified;

        url = "/websites/addNewCron";
        var data = {
            domain: websiteToBeModified,
            minute: $scope.minute,
            hour: $scope.hour,
            monthday: $scope.monthday,
            month: $scope.month,
            weekday: $scope.weekday,
            cronCommand: $scope.command
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response);

            if (response.data.addNewCron === 0) {
                $scope.errorMessage = response.data.error_message
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").hide();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").show();
            } else {
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").show();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").hide();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#addCronFailure").show();
            $("#cronEditSuccess").hide();
            $("#fetchCronFailure").hide();
        }
    };


    $scope.removeCron = function (line) {

        $("#manageCronLoading").show();

        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        url = "/websites/remCronbyLine";
        var data = {
            domain: $scope.websiteToBeModified,
            line: line
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response);

            if (response.data.remCronbyLine === 0) {
                $scope.errorMessage = response.data.error_message;
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").hide();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").show();
            } else {
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").show();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").hide();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#addCronFailure").show();
            $("#cronEditSuccess").hide();
            $("#fetchCronFailure").hide();
        }
    };

    $scope.modifyCronFunc = function () {

        $("#manageCronLoading").show();
        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        var websiteToBeModified = $scope.websiteToBeModified;

        url = "/websites/saveCronChanges";
        var data = {
            domain: websiteToBeModified,
            line: $scope.line,
            minute: $scope.minute,
            hour: $scope.hour,
            monthday: $scope.monthday,
            month: $scope.month,
            weekday: $scope.weekday,
            cronCommand: $scope.command
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.addNewCron === 0) {

                $scope.errorMessage = response.data.error_message;
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").hide();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").show();
            } else {
                console.log(response.data);
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").show();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").hide();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#addCronFailure").show();
            $("#cronEditSuccess").hide();
            $("#fetchCronFailure").hide();
        }
    };

});

/* Java script code to manage cron ends here */

/* Java script code to manage cron */

app.controller('manageAliasController', function ($scope, $http, $timeout, $window) {

    $('form').submit(function (e) {
        e.preventDefault();
    });

    var masterDomain = "";

    $scope.aliasTable = false;
    $scope.addAliasButton = false;
    $scope.domainAliasForm = true;
    $scope.aliasError = true;
    $scope.couldNotConnect = true;
    $scope.aliasCreated = true;
    $scope.manageAliasLoading = true;
    $scope.operationSuccess = true;

    $scope.createAliasEnter = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.manageAliasLoading = false;
            $scope.addAliasFunc();
        }
    };

    $scope.showAliasForm = function (domainName) {

        $scope.domainAliasForm = false;
        $scope.aliasTable = true;
        $scope.addAliasButton = true;

        masterDomain = domainName;

    };

    $scope.addAliasFunc = function () {

        $scope.manageAliasLoading = false;

        var ssl;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        url = "/websites/submitAliasCreation";

        var data = {
            masterDomain: masterDomain,
            aliasDomain: $scope.aliasDomain,
            ssl: ssl

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createAliasStatus === 1) {

                $scope.aliasTable = true;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = false;
                $scope.aliasError = true;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = false;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $timeout(function () {
                    $window.location.reload();
                }, 3000);


            } else {

                $scope.aliasTable = true;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = false;
                $scope.aliasError = false;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aliasTable = true;
            $scope.addAliasButton = true;
            $scope.domainAliasForm = false;
            $scope.aliasError = true;
            $scope.couldNotConnect = false;
            $scope.aliasCreated = true;
            $scope.manageAliasLoading = true;
            $scope.operationSuccess = true;


        }


    };

    $scope.issueSSL = function (masterDomain, aliasDomain) {

        $scope.manageAliasLoading = false;


        url = "/websites/issueAliasSSL";

        var data = {
            masterDomain: masterDomain,
            aliasDomain: aliasDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.sslStatus === 1) {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = true;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = false;


            } else {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = false;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aliasTable = false;
            $scope.addAliasButton = true;
            $scope.domainAliasForm = true;
            $scope.aliasError = true;
            $scope.couldNotConnect = false;
            $scope.aliasCreated = true;
            $scope.manageAliasLoading = true;
            $scope.operationSuccess = true;


        }


    };

    $scope.removeAlias = function (masterDomain, aliasDomain) {

        $scope.manageAliasLoading = false;

        url = "/websites/delateAlias";

        var data = {
            masterDomain: masterDomain,
            aliasDomain: aliasDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.deleteAlias === 1) {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = true;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = false;

                $timeout(function () {
                    $window.location.reload();
                }, 3000);


            } else {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = false;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aliasTable = false;
            $scope.addAliasButton = true;
            $scope.domainAliasForm = true;
            $scope.aliasError = true;
            $scope.couldNotConnect = false;
            $scope.aliasCreated = true;
            $scope.manageAliasLoading = true;
            $scope.operationSuccess = true;


        }


    };


});

/* Java script code to manage cron ends here */

app.controller('launchChild', function ($scope, $http) {

    $scope.logFileLoading = true;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedData = true;
    $scope.hideLogs = true;
    $scope.hideErrorLogs = true;

    $scope.hidelogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.hideErrorLogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.fileManagerURL = "/filemanager/" + $("#domainNamePage").text();
    $scope.previewUrl = "/preview/" + $("#childDomain").text() + "/";
    $scope.wordPressInstallURL = "/websites/" + $("#childDomain").text() + "/wordpressInstall";
    $scope.joomlaInstallURL = "/websites/" + $("#childDomain").text() + "/joomlaInstall";
    $scope.setupGit = "/websites/" + $("#childDomain").text() + "/setupGit";
    $scope.installPrestaURL = "/websites/" + $("#childDomain").text() + "/installPrestaShop";
    $scope.installMagentoURL = "/websites/" + $("#childDomain").text() + "/installMagento";

    var logType = 0;
    $scope.pageNumber = 1;

    $scope.fetchLogs = function (type) {

        var pageNumber = $scope.pageNumber;


        if (type == 3) {
            pageNumber = $scope.pageNumber + 1;
            $scope.pageNumber = pageNumber;
        } else if (type == 4) {
            pageNumber = $scope.pageNumber - 1;
            $scope.pageNumber = pageNumber;
        } else {
            logType = type;
        }


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = false;
        $scope.hideErrorLogs = true;


        url = "/websites/getDataFromLogFile";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            logType: logType,
            virtualHost: domainNamePage,
            page: pageNumber,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.logstatus === 1) {


                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = false;
                $scope.hideLogs = false;


                $scope.records = JSON.parse(response.data.data);

            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = false;


                $scope.errorMessage = response.data.error_message;
                console.log(domainNamePage)

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedData = true;
            $scope.hideLogs = false;

        }


    };

    $scope.errorPageNumber = 1;


    $scope.fetchErrorLogs = function (type) {

        var errorPageNumber = $scope.errorPageNumber;


        if (type === 3) {
            errorPageNumber = $scope.errorPageNumber + 1;
            $scope.errorPageNumber = errorPageNumber;
        } else if (type === 4) {
            errorPageNumber = $scope.errorPageNumber - 1;
            $scope.errorPageNumber = errorPageNumber;
        } else {
            logType = type;
        }

        // notifications

        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = true;
        $scope.hideErrorLogs = true;
        $scope.hideLogs = false;


        url = "/websites/fetchErrorLogs";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            virtualHost: domainNamePage,
            page: errorPageNumber,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.logstatus === 1) {


                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = false;
                $scope.hideErrorLogs = false;


                $scope.errorLogsData = response.data.data;

            } else {

                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = true;
                $scope.hideErrorLogs = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            // notifications

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedData = true;
            $scope.hideLogs = true;
            $scope.hideErrorLogs = true;

        }


    };

    ///////// Configurations Part

    $scope.configurationsBox = true;
    $scope.configsFetched = true;
    $scope.couldNotFetchConfigs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedConfigsData = true;
    $scope.configFileLoading = true;
    $scope.configSaved = true;
    $scope.couldNotSaveConfigurations = true;

    $scope.hideconfigbtn = function () {

        $scope.configurationsBox = true;
    };

    $scope.fetchConfigurations = function () {


        $scope.hidsslconfigs = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;


        //Rewrite rules
        $scope.configurationsBoxRewrite = true;
        $scope.rewriteRulesFetched = true;
        $scope.couldNotFetchRewriteRules = true;
        $scope.rewriteRulesSaved = true;
        $scope.couldNotSaveRewriteRules = true;
        $scope.fetchedRewriteRules = true;
        $scope.saveRewriteRulesBTN = true;

        ///

        $scope.configFileLoading = false;


        url = "/websites/getDataFromConfigFile";

        var virtualHost = $("#childDomain").text();


        var data = {
            virtualHost: virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus === 1) {

                //Rewrite rules

                $scope.configurationsBoxRewrite = true;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;

                ///

                $scope.configurationsBox = false;
                $scope.configsFetched = false;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = false;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = false;


                $scope.configData = response.data.configData;

            } else {

                //Rewrite rules
                $scope.configurationsBoxRewrite = true;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;

                ///
                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            //Rewrite rules
            $scope.configurationsBoxRewrite = true;
            $scope.rewriteRulesFetched = true;
            $scope.couldNotFetchRewriteRules = true;
            $scope.rewriteRulesSaved = true;
            $scope.couldNotSaveRewriteRules = true;
            $scope.fetchedRewriteRules = true;
            $scope.saveRewriteRulesBTN = true;
            ///

            $scope.configurationsBox = false;
            $scope.configsFetched = true;
            $scope.couldNotFetchConfigs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedConfigsData = true;
            $scope.configFileLoading = true;
            $scope.configSaved = true;
            $scope.couldNotSaveConfigurations = true;


        }


    };

    $scope.saveCongiruations = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveConfigsToFile";

        var virtualHost = $("#childDomain").text();
        var configData = $scope.configData;


        var data = {
            virtualHost: virtualHost,
            configData: configData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus == 1) {

                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = false;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;


            } else {
                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = false;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = false;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configurationsBox = false;
            $scope.configsFetched = true;
            $scope.couldNotFetchConfigs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedConfigsData = true;
            $scope.configFileLoading = true;
            $scope.configSaved = true;
            $scope.couldNotSaveConfigurations = true;


        }


    };


    ///////// Rewrite Rules

    $scope.configurationsBoxRewrite = true;
    $scope.rewriteRulesFetched = true;
    $scope.couldNotFetchRewriteRules = true;
    $scope.rewriteRulesSaved = true;
    $scope.couldNotSaveRewriteRules = true;
    $scope.fetchedRewriteRules = true;
    $scope.saveRewriteRulesBTN = true;

    $scope.hideRewriteRulesbtn = function () {
        $scope.configurationsBoxRewrite = true;
    };


    $scope.fetchRewriteFules = function () {

        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.changePHPView = true;


        $scope.configurationsBox = true;
        $scope.configsFetched = true;
        $scope.couldNotFetchConfigs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedConfigsData = true;
        $scope.configFileLoading = true;
        $scope.configSaved = true;
        $scope.couldNotSaveConfigurations = true;
        $scope.saveConfigBtn = true;

        $scope.configFileLoading = false;


        url = "/websites/getRewriteRules";

        var virtualHost = $("#childDomain").text();


        var data = {
            virtualHost: virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {


                // from main

                $scope.configurationsBox = true;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.fetchedConfigsData = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;

                // main ends

                $scope.configFileLoading = true;

                //


                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = false;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = false;
                $scope.saveRewriteRulesBTN = false;
                $scope.couldNotConnect = true;


                $scope.rewriteRules = response.data.rewriteRules;

            } else {
                // from main
                $scope.configurationsBox = true;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;
                // from main

                $scope.configFileLoading = true;

                ///

                $scope.configurationsBoxRewrite = true;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = false;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;
                $scope.couldNotConnect = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
            // from main

            $scope.configurationsBox = true;
            $scope.configsFetched = true;
            $scope.couldNotFetchConfigs = true;
            $scope.fetchedConfigsData = true;
            $scope.configFileLoading = true;
            $scope.configSaved = true;
            $scope.couldNotSaveConfigurations = true;
            $scope.saveConfigBtn = true;

            // from main

            $scope.configFileLoading = true;

            ///

            $scope.configurationsBoxRewrite = true;
            $scope.rewriteRulesFetched = true;
            $scope.couldNotFetchRewriteRules = true;
            $scope.rewriteRulesSaved = true;
            $scope.couldNotSaveRewriteRules = true;
            $scope.fetchedRewriteRules = true;
            $scope.saveRewriteRulesBTN = true;

            $scope.couldNotConnect = false;


        }


    };

    $scope.saveRewriteRules = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveRewriteRules";

        var virtualHost = $("#childDomain").text();
        var rewriteRules = $scope.rewriteRules;


        var data = {
            virtualHost: virtualHost,
            rewriteRules: rewriteRules,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {

                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = false;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;
                $scope.configFileLoading = true;


            } else {
                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = false;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = false;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = false;

                $scope.configFileLoading = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configurationsBoxRewrite = false;
            $scope.rewriteRulesFetched = false;
            $scope.couldNotFetchRewriteRules = true;
            $scope.rewriteRulesSaved = true;
            $scope.couldNotSaveRewriteRules = true;
            $scope.fetchedRewriteRules = true;
            $scope.saveRewriteRulesBTN = false;

            $scope.configFileLoading = true;

            $scope.couldNotConnect = false;


        }


    };


    //////// SSL Part

    $scope.sslSaved = true;
    $scope.couldNotSaveSSL = true;
    $scope.hidsslconfigs = true;
    $scope.couldNotConnect = true;


    $scope.hidesslbtn = function () {
        $scope.hidsslconfigs = true;
    };

    $scope.addSSL = function () {
        $scope.hidsslconfigs = false;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;
    };


    $scope.saveSSL = function () {


        $scope.configFileLoading = false;

        url = "/websites/saveSSL";

        var virtualHost = $("#childDomain").text();
        var cert = $scope.cert;
        var key = $scope.key;


        var data = {
            virtualHost: virtualHost,
            cert: cert,
            key: key,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.sslStatus === 1) {

                $scope.sslSaved = false;
                $scope.couldNotSaveSSL = true;
                $scope.couldNotConnect = true;
                $scope.configFileLoading = true;


            } else {

                $scope.sslSaved = true;
                $scope.couldNotSaveSSL = false;
                $scope.couldNotConnect = true;
                $scope.configFileLoading = true;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.sslSaved = true;
            $scope.couldNotSaveSSL = true;
            $scope.couldNotConnect = false;
            $scope.configFileLoading = true;


        }

    };


    //// Change PHP Master

    $scope.failedToChangePHPMaster = true;
    $scope.phpChangedMaster = true;
    $scope.couldNotConnect = true;

    $scope.changePHPView = true;


    $scope.hideChangePHPMaster = function () {
        $scope.changePHPView = true;
    };

    $scope.changePHPMaster = function () {
        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = false;
    };


    $scope.changePHPVersionMaster = function (childDomain, phpSelection) {

        // notifcations

        $scope.configFileLoading = false;

        var url = "/websites/changePHP";

        var data = {
            childDomain: $("#childDomain").text(),
            phpSelection: $scope.phpSelectionMaster,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePHP === 1) {

                $scope.configFileLoading = true;
                $scope.websiteDomain = $("#childDomain").text();


                // notifcations

                $scope.failedToChangePHPMaster = true;
                $scope.phpChangedMaster = false;
                $scope.couldNotConnect = true;


            } else {

                $scope.configFileLoading = true;
                $scope.errorMessage = response.data.error_message;

                // notifcations

                $scope.failedToChangePHPMaster = false;
                $scope.phpChangedMaster = true;
                $scope.couldNotConnect = true;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configFileLoading = true;

            // notifcations

            $scope.failedToChangePHPMaster = true;
            $scope.phpChangedMaster = true;
            $scope.couldNotConnect = false;

        }

    };


    /// Open_basedir protection

    $scope.baseDirLoading = true;
    $scope.operationFailed = true;
    $scope.operationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.openBaseDirBox = true;


    $scope.openBaseDirView = function () {
        $scope.openBaseDirBox = false;
    };

    $scope.hideOpenBasedir = function () {
        $scope.openBaseDirBox = true;
    };

    $scope.applyOpenBasedirChanges = function (childDomain, phpSelection) {

        // notifcations

        $scope.baseDirLoading = false;
        $scope.operationFailed = true;
        $scope.operationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.openBaseDirBox = false;


        var url = "/websites/changeOpenBasedir";

        var data = {
            domainName: $("#childDomain").text(),
            openBasedirValue: $scope.openBasedirValue
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changeOpenBasedir === 1) {

                $scope.baseDirLoading = true;
                $scope.operationFailed = true;
                $scope.operationSuccessfull = false;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

            } else {

                $scope.baseDirLoading = true;
                $scope.operationFailed = false;
                $scope.operationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.baseDirLoading = true;
            $scope.operationFailed = true;
            $scope.operationSuccessfull = true;
            $scope.couldNotConnect = false;
            $scope.openBaseDirBox = false;


        }

    }

});

/* Application Installer */

app.controller('installWordPressCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    $scope.installWordPress = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/installWordpress";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            blogTitle: $scope.blogTitle,
            adminUser: $scope.adminUser,
            passwordByPass: $scope.adminPassword,
            adminEmail: $scope.adminEmail
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {


        }

    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }


});

app.controller('installJoomlaCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    $scope.databasePrefix = 'jm_';

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }

    $scope.installJoomla = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/installJoomla";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            sitename: $scope.blogTitle,
            username: $scope.adminUser,
            passwordByPass: $scope.adminPassword,
            prefix: $scope.databasePrefix
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {


        }

    };


});

app.controller('setupGit', function ($scope, $http, $timeout, $window) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.gitLoading = true;
    $scope.githubBranch = 'master';
    $scope.installProg = true;
    $scope.goBackDisable = true;

    var defaultProvider = 'github';

    $scope.setProvider = function (provider) {
        defaultProvider = provider;
    };


    var statusFile;
    var domain = $("#domainNamePage").text();

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.gitLoading = true;
                    $scope.goBackDisable = true;

                    $scope.installationURL = domain;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.gitLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;


        }


    }

    $scope.attachRepo = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = false;
        $scope.installProg = false;

        $scope.currentStatus = "Attaching GIT..";

        url = "/websites/setupGitRepo";

        var data = {
            domain: domain,
            username: $scope.githubUserName,
            reponame: $scope.githubRepo,
            branch: $scope.githubBranch,
            defaultProvider: defaultProvider
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.gitLoading = true;

                $scope.errorMessage = response.data.error_message;
                $scope.goBackDisable = false;

            }


        }

        function cantLoadInitialDatas(response) {


        }

    };

    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installProg = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    /// Detach Repo

    $scope.failedMesg = true;
    $scope.successMessage = true;
    $scope.couldNotConnect = true;
    $scope.gitLoading = true;
    $scope.successMessageBranch = true;

    $scope.detachRepo = function () {

        $scope.failedMesg = true;
        $scope.successMessage = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = false;
        $scope.successMessageBranch = true;

        url = "/websites/detachRepo";

        var data = {
            domain: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.gitLoading = true;

            if (response.data.status === 1) {
                $scope.failedMesg = true;
                $scope.successMessage = false;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = true;

                $timeout(function () {
                    $window.location.reload();
                }, 3000);

            } else {

                $scope.failedMesg = false;
                $scope.successMessage = true;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = true;

                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {
            $scope.failedMesg = true;
            $scope.successMessage = true;
            $scope.couldNotConnect = false;
            $scope.gitLoading = true;
            $scope.successMessageBranch = true;
        }

    };
    $scope.changeBranch = function () {

        $scope.failedMesg = true;
        $scope.successMessage = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = false;
        $scope.successMessageBranch = true;

        url = "/websites/changeBranch";

        var data = {
            domain: domain,
            githubBranch: $scope.githubBranch
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.gitLoading = true;

            if (response.data.status === 1) {
                $scope.failedMesg = true;
                $scope.successMessage = true;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = false;

            } else {

                $scope.failedMesg = false;
                $scope.successMessage = true;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = true;

                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {
            $scope.failedMesg = true;
            $scope.successMessage = true;
            $scope.couldNotConnect = false;
            $scope.gitLoading = true;
            $scope.successMessageBranch = true;
        }

    };


});

app.controller('installPrestaShopCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    $scope.databasePrefix = 'ps_';

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }

    $scope.installPrestShop = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/prestaShopInstall";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            shopName: $scope.shopName,
            firstName: $scope.firstName,
            lastName: $scope.lastName,
            databasePrefix: $scope.databasePrefix,
            email: $scope.email,
            passwordByPass: $scope.password
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
        }

    };


});

app.controller('sshAccess', function ($scope, $http, $timeout) {

    $scope.wpInstallLoading = true;

    $scope.setupSSHAccess = function () {
        $scope.wpInstallLoading = false;

        url = "/websites/saveSSHAccessChanges";

        var data = {
            domain: $("#domainName").text(),
            externalApp: $("#externalApp").text(),
            password: $scope.password
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.wpInstallLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes Successfully Applied.',
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

        function cantLoadInitialDatas(response) {

            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };


});


/* Java script code to cloneWebsite */
app.controller('cloneWebsite', function ($scope, $http, $timeout, $window) {

    $('form').submit(function (e) {
        e.preventDefault();
    });

    $scope.cyberpanelLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.goBackDisable = true;

    $scope.cloneEnter = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.cyberpanelLoading = false;
            $scope.startCloning();
        }
    };

    var statusFile;

    $scope.startCloning = function () {

        $scope.cyberpanelLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Cloning started..";

        url = "/websites/startCloning";


        var data = {
            masterDomain: $("#domainName").text(),
            domainName: $scope.domain

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.cyberpanelLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.goBackDisable = false;

                $scope.currentStatus = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }

    };
    $scope.goBack = function () {
        $scope.cyberpanelLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $scope.currentStatus = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    }

});
/* Java script code to cloneWebsite ends here */


/* Java script code to syncWebsite */
app.controller('syncWebsite', function ($scope, $http, $timeout, $window) {

    $scope.cyberpanelLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.goBackDisable = true;

    var statusFile;

    $scope.startSyncing = function () {

        $scope.cyberpanelLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Cloning started..";

        url = "/websites/startSync";


        var data = {
            childDomain: $("#childDomain").text(),
            eraseCheck: $scope.eraseCheck,
            dbCheck: $scope.dbCheck,
            copyChanged: $scope.copyChanged

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.cyberpanelLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.goBackDisable = false;

                $scope.currentStatus = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }

    };
    $scope.goBack = function () {
        $scope.cyberpanelLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $scope.currentStatus = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    }

});
/* Java script code to syncWebsite ends here */


app.controller('installMagentoCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    $scope.databasePrefix = 'ps_';

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }

    $scope.installMagento = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/magentoInstall";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }
        var sampleData;
        if ($scope.sampleData === true) {
            sampleData = 1;
        } else {
            sampleData = 0
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            firstName: $scope.firstName,
            lastName: $scope.lastName,
            username: $scope.username,
            email: $scope.email,
            passwordByPass: $scope.password,
            sampleData: sampleData
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
        }

    };


});