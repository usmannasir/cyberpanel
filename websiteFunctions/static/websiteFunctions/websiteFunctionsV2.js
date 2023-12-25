newapp.controller('createWebsiteV2', function ($scope, $http, $timeout, $window) {

    alert('Create Website V2 loading')
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

        var ssl, dkimCheck, openBasedir, mailDomain, apacheBackend;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        if ($scope.apacheBackend === true) {
            apacheBackend = 1;
        } else {
            apacheBackend = 0
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

        if ($scope.mailDomain === true) {
            mailDomain = 1;
        } else {
            mailDomain = 0
        }


        url = "/websites/submitWebsiteCreation";

        var package = $scope.packageForWebsite;

        // if (website_create_domain_check == 0) {
        //     var Part2_domainNameCreate = document.getElementById('Part2_domainNameCreate').value;
        //     var domainName = document.getElementById('TestDomainNameCreate').value + Part2_domainNameCreate;
        // }
        // if (website_create_domain_check == 1) {
        //
        //     var domainName = $scope.domainNameCreate;
        // }
        var domainName = $scope.domainNameCreate;

        // var domainName = $scope.domainNameCreate;

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
            openBasedir: openBasedir,
            mailDomain: mailDomain,
            apacheBackend: apacheBackend
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

newapp.controller('listWebsitesV2', function ($scope, $http) {


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

    $scope.ScanWordpressSite = function () {

        $('#cyberPanelLoading').show();


        var url = "/websites/ScanWordpressSite";

        var data = {}


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $('#cyberPanelLoading').hide();

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully Saved!.',
                    type: 'success'
                });
                location.reload();

            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#cyberPanelLoading').hide();
            new PNotify({
                title: 'Operation Failed!',
                text: response.data.error_message,
                type: 'error'
            });


        }


    };


});

newapp.controller('websitePagesV2', function ($scope, $http, $timeout, $window) {

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
    $scope.installMauticURL = $("#domainNamePage").text() + "/installMautic";
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
        var username = 'admin';
        var password = $scope.password;
        var prefix = $scope.prefix;


        url = "/websites/installJoomla";

        var home = "1";

        if (typeof path != 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            siteName: $scope.siteName,
            home: home,
            path: path,
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
    $scope.DomainCreateForm = true;

    var statusFile;

    $scope.WebsiteSelection = function () {
        $scope.DomainCreateForm = false;
    };

    $scope.createDomain = function () {

        $scope.domainLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting creation..";
        $scope.DomainCreateForm = true;

        var ssl, dkimCheck, openBasedir, apacheBackend;

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


        if ($scope.apacheBackend === true) {
            apacheBackend = 1;
        } else {
            apacheBackend = 0
        }


        url = "/websites/submitDomainCreation";
        var domainName = $scope.domainNameCreate;
        var phpSelection = $scope.phpSelection;

        var path = $scope.docRootPath;

        if (typeof path === 'undefined') {
            path = "";
        }
        var package = $scope.packageForWebsite;

        // if (website_child_domain_check == 0) {
        //     var Part2_domainNameCreate = document.getElementById('Part2_domainNameCreate').value;
        //     var domainName = document.getElementById('TestDomainNameCreate').value + Part2_domainNameCreate;
        // }
        // if (website_child_domain_check == 1) {
        //
        //     var domainName = $scope.own_domainNameCreate;
        // }
        var domainName = $scope.domainNameCreate;

        var data = {
            domainName: domainName,
            phpSelection: phpSelection,
            ssl: ssl,
            path: path,
            masterDomain: $scope.masterDomain,
            dkimCheck: dkimCheck,
            openBasedir: openBasedir,
            apacheBackend: apacheBackend
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
                $scope.DomainCreateForm = true;
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
            $scope.DomainCreateForm = true;
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
        $scope.DomainCreateForm = true;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $scope.DomainCreateForm = true;
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
                    $scope.DomainCreateForm = true;
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
            $scope.DomainCreateForm = true;
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

    const WWWToNonWWW = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteCond %{HTTP_HOST} ^www\.(.*)$
RewriteRule ^(.*)$ http://%1/$1 [L,R=301]

### End CyberPanel Generated Rules.

`;

    const nonWWWToWWW = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteCond %{HTTP_HOST} !^www\. [NC]
RewriteRule ^(.*)$ http://www.%{HTTP_HOST}%{REQUEST_URI} [R=301,L]

### End CyberPanel Generated Rules.

`;

    const WordpressProtect = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteRule ^/(xmlrpc|wp-trackback)\.php - [F,L,NC]

### End CyberPanel Generated Rules.

`;

    $scope.applyRewriteTemplate = function () {

        if ($scope.rewriteTemplate === "Force HTTP -> HTTPS") {
            $scope.rewriteRules = httpToHTTPS + $scope.rewriteRules;
        } else if ($scope.rewriteTemplate === "Force NON-WWW -> WWW") {
            $scope.rewriteRules = nonWWWToWWW + $scope.rewriteRules;
        } else if ($scope.rewriteTemplate === "Force WWW -> NON-WWW") {
            $scope.rewriteRules = WWWToNonWWW + $scope.rewriteRules;
        } else if ($scope.rewriteTemplate === "Disable Wordpress XMLRPC & Trackback") {
            $scope.rewriteRules = WordpressProtect + $scope.rewriteRules;
        }
    };


});

newapp.controller('listChildDomainsMainV2', function ($scope, $http, $timeout) {

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

        dataurl = "/websites/searchChilds";

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

    $scope.initConvert = function (virtualHost) {
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

    var DeleteDomain;
    $scope.deleteDomainInit = function (childDomainForDeletion) {
        DeleteDomain = childDomainForDeletion;
    };

    $scope.deleteChildDomain = function () {
        $scope.cyberPanelLoading = false;
        url = "/websites/submitDomainDeletion";

        var data = {
            websiteName: DeleteDomain,
            DeleteDocRoot: $scope.DeleteDocRoot
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.websiteDeleteStatus === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Child Domain successfully deleted.',
                    type: 'success'
                });
                $scope.getFurtherWebsitesFromDB();
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