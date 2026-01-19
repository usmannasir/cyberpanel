/**
 * Created by usman on 8/6/17.
 */


/* Java script code to create database */
app.controller('createDatabase', function ($scope, $http) {

    $(document).ready(function () {
        $(".dbDetails").hide();
        $(".generatedPasswordDetails").hide();
        $('#create-database-select').select2();
        
        // Initialize preview if website is already selected
        setTimeout(function() {
            if ($scope.databaseWebsite) {
                var truncatedName = $scope.getTruncatedWebName($scope.databaseWebsite);
                $("#domainDatabase").text(truncatedName);
                $("#domainUsername").text(truncatedName);
                $(".dbDetails").show();
            }
        }, 100);
    });

    // Helper function to get truncated website name
    $scope.getTruncatedWebName = function(domain) {
        if (!domain) return '';
        
        // Remove hyphens and get first part before dot
        var webName = domain.replace(/-/g, '').split('.')[0];
        
        // Truncate to 4 characters if longer than 5
        if (webName.length > 5) {
            webName = webName.substring(0, 4);
        }
        
        return webName;
    };

    $('#create-database-select').on('select2:select', function (e) {
        var data = e.params.data;
        $scope.databaseWebsite = data.text;
        $(".dbDetails").show();
        
        // Use local truncation function to ensure consistency
        var truncatedName = $scope.getTruncatedWebName(data.text);
        $("#domainDatabase").text(truncatedName);
        $("#domainUsername").text(truncatedName);
        
        // Apply scope to update Angular bindings
        $scope.$apply();
    });


    $scope.showDetailsBoxes = function () {
        $scope.dbDetails = false;
    }
    
    // Function called when website selection changes
    $scope.websiteChanged = function() {
        if ($scope.databaseWebsite) {
            $(".dbDetails").show();
            var truncatedName = $scope.getTruncatedWebName($scope.databaseWebsite);
            $("#domainDatabase").text(truncatedName);
            $("#domainUsername").text(truncatedName);
        }
    }

    $scope.createDatabaseLoading = true;
    
    // Watch for changes to databaseWebsite to update preview
    $scope.$watch('databaseWebsite', function(newValue, oldValue) {
        if (newValue && newValue !== oldValue) {
            var truncatedName = $scope.getTruncatedWebName(newValue);
            $("#domainDatabase").text(truncatedName);
            $("#domainUsername").text(truncatedName);
        }
    });

    $scope.createDatabase = function () {

        $scope.createDatabaseLoading = false;
        $scope.dbDetails = false;


        var databaseWebsite = $scope.databaseWebsite;
        var dbName = $scope.dbName;
        var dbUsername = $scope.dbUsername;
        var dbPassword = $scope.dbPassword;
        var webUserName = "";

        // getting website username - use the same truncation function for consistency
        webUserName = $scope.getTruncatedWebName(databaseWebsite);

        var url = "/dataBases/submitDBCreation";


        var data = {
            webUserName: webUserName,
            databaseWebsite: databaseWebsite,
            dbName: dbName,
            dbUsername: dbUsername,
            dbPassword: dbPassword
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.createDBStatus === 1) {

                $scope.createDatabaseLoading = true;
                $scope.dbDetails = false;
                var successMessage = 'Database successfully created.';
                if (response.data.dbName && response.data.dbUsername) {
                    successMessage = 'Database successfully created.\n' +
                                   'Database Name: ' + response.data.dbName + '\n' +
                                   'Database User: ' + response.data.dbUsername;
                }
                new PNotify({
                    title: 'Success!',
                    text: successMessage,
                    type: 'success'
                });
            } else {

                $scope.createDatabaseLoading = true;
                $scope.dbDetails = false;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.createDatabaseLoading = true;
            $scope.dbDetails = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.generatePassword = function () {
        $(".generatedPasswordDetails").show();
        $scope.dbPassword = randomPassword(16);
    };

    $scope.usePassword = function () {
        $(".generatedPasswordDetails").hide();
    };

});
/* Java script code to create database ends here */

/* Java script code to delete database */

app.controller('deleteDatabase', function ($scope, $http) {

    $scope.deleteDatabaseLoading = true;
    $scope.fetchedDatabases = true;
    $scope.databaseDeletionFailed = true;
    $scope.databaseDeleted = true;
    $scope.couldNotConnect = true;


    $scope.fetchDatabases = function () {

        $scope.deleteDatabaseLoading = false;
        $scope.fetchedDatabases = true;
        $scope.databaseDeletionFailed = true;
        $scope.databaseDeleted = true;
        $scope.couldNotConnect = true;


        var databaseWebsite = $scope.databaseWebsite;

        var url = "/dataBases/fetchDatabases";


        var data = {
            databaseWebsite: databaseWebsite,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus == 1) {


                $scope.dbnames = JSON.parse(response.data.data);


                $scope.deleteDatabaseLoading = true;
                $scope.fetchedDatabases = false;
                $scope.databaseDeletionFailed = true;
                $scope.databaseDeleted = true;
                $scope.couldNotConnect = true;


            } else {
                $scope.deleteDatabaseLoading = true;
                $scope.fetchedDatabases = true;
                $scope.databaseDeletionFailed = false;
                $scope.databaseDeleted = true;
                $scope.couldNotConnect = true;


                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.deleteDatabaseLoading = true;
            $scope.fetchedDatabases = true;
            $scope.databaseDeletionFailed = true;
            $scope.databaseDeleted = true;
            $scope.couldNotConnect = false;


        }
    };

    $scope.deleteDatabase = function () {

        $scope.deleteDatabaseLoading = false;
        $scope.fetchedDatabases = true;
        $scope.databaseDeletionFailed = true;
        $scope.databaseDeleted = true;
        $scope.couldNotConnect = true;


        var databaseWebsite = $scope.databaseWebsite;

        var url = "/dataBases/submitDatabaseDeletion";


        var data = {
            dbName: $scope.selectedDB,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.deleteStatus == 1) {


                $scope.deleteDatabaseLoading = true;
                $scope.fetchedDatabases = false;
                $scope.databaseDeletionFailed = true;
                $scope.databaseDeleted = false;
                $scope.couldNotConnect = true;


            } else {
                $scope.deleteDatabaseLoading = true;
                $scope.fetchedDatabases = true;
                $scope.databaseDeletionFailed = false;
                $scope.databaseDeleted = true;
                $scope.couldNotConnect = true;


                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.deleteDatabaseLoading = true;
            $scope.fetchedDatabases = true;
            $scope.databaseDeletionFailed = true;
            $scope.databaseDeleted = true;
            $scope.couldNotConnect = false;


        }
    };


});

/* Java script code to delete database ends here */


/* Java script code to list  databases */


app.controller('listDBs', function ($scope, $http) {

    $scope.recordsFetched = true;
    $scope.passwordChanged = true;
    $scope.canNotChangePassword = true;
    $scope.couldNotConnect = true;
    $scope.dbLoading = true;
    $scope.dbAccounts = true;
    $scope.changePasswordBox = true;
    $scope.notificationsBox = true;

    var globalDBUsername = "";

    $scope.fetchDBs = function () {
        populateCurrentRecords();
    };

    $scope.changePassword = function (dbUsername) {
        $scope.recordsFetched = true;
        $scope.passwordChanged = true;
        $scope.canNotChangePassword = true;
        $scope.couldNotConnect = true;
        $scope.dbLoading = true;
        $scope.dbAccounts = false;
        $scope.changePasswordBox = false;
        $scope.notificationsBox = true;
        $scope.dbUsername = dbUsername;


        globalDBUsername = dbUsername;

    };

    $scope.changePasswordBtn = function () {

        $scope.dbLoading = false;
        $scope.passwordChanged = true;


        url = "/dataBases/changePassword";

        var data = {
            dbUserName: globalDBUsername,
            dbPassword: $scope.dbPassword,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePasswordStatus == 1) {
                $scope.notificationsBox = false;
                $scope.passwordChanged = false;
                $scope.dbLoading = true;
                $scope.domainFeteched = $scope.selectedDomain;

            } else {
                $scope.notificationsBox = false;
                $scope.canNotChangePassword = false;
                $scope.dbLoading = true;
                $scope.canNotChangePassword = false;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.notificationsBox = false;
            $scope.couldNotConnect = false;
            $scope.dbLoading = true;

        }

    };

    function populateCurrentRecords() {
        $scope.recordsFetched = true;
        $scope.passwordChanged = true;
        $scope.canNotChangePassword = true;
        $scope.couldNotConnect = true;
        $scope.dbLoading = false;
        $scope.dbAccounts = true;
        $scope.changePasswordBox = true;
        $scope.notificationsBox = true;

        var selectedDomain = $scope.selectedDomain;

        url = "/dataBases/fetchDatabases";

        var data = {
            databaseWebsite: selectedDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus == 1) {

                $scope.records = JSON.parse(response.data.data);


                $scope.recordsFetched = false;
                $scope.passwordChanged = true;
                $scope.canNotChangePassword = true;
                $scope.couldNotConnect = true;
                $scope.dbLoading = true;
                $scope.dbAccounts = false;
                $scope.changePasswordBox = true;
                $scope.notificationsBox = false;

                $scope.domainFeteched = $scope.selectedDomain;

            } else {
                $scope.recordsFetched = true;
                $scope.passwordChanged = true;
                $scope.canNotChangePassword = true;
                $scope.couldNotConnect = true;
                $scope.dbLoading = true;
                $scope.dbAccounts = true;
                $scope.changePasswordBox = true;
                $scope.notificationsBox = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.recordsFetched = true;
            $scope.passwordChanged = true;
            $scope.canNotChangePassword = true;
            $scope.couldNotConnect = false;
            $scope.dbLoading = true;
            $scope.dbAccounts = true;
            $scope.changePasswordBox = true;
            $scope.notificationsBox = true;

        }

    }

    ////

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
        $scope.generatedPasswordView = false;
        $scope.dbPassword = randomPassword(16);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
    };

    $scope.remoteAccess = function (userName) {

        $scope.dbUsername = userName;
        $scope.dbLoading = false;


        url = "/dataBases/remoteAccess";

        var data = {
            dbUserName: $scope.dbUsername
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.dbLoading = true;

            if (response.data.status === 1) {

                $scope.dbHost = response.data.dbHost;

            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
            $scope.dbLoading = true;

        }

    };

    $scope.allowRemoteIP = function () {

        $scope.dbLoading = false;

        url = "/dataBases/allowRemoteIP";

        var data = {
            dbUserName: $scope.dbUsername,
            remoteIP: $scope.remoteIP
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.dbLoading = true;

            if (response.data.status === 1) {

                $scope.remoteAccess($scope.dbUsername);

                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
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
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
            $scope.dbLoading = true;

        }

    };

});


/* Java script code to list database ends here */


app.controller('phpMyAdmin', function ($scope, $http, $window) {
    $scope.cyberPanelLoading = true;

    $scope.generateAccess = function () {

        $scope.cyberPanelLoading = false;

        url = "/dataBases/generateAccess";

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
                //var rUrl = '/phpmyadmin/phpmyadminsignin.php?username=' + response.data.username + '&token=' + response.data.token;
                //$window.location.href = rUrl;

                var form = document.createElement('form');
                form.method = 'post';
                form.action = '/phpmyadmin/phpmyadminsignin.php';

// Create input elements for username and token
                var usernameInput = document.createElement('input');
                usernameInput.type = 'hidden';
                usernameInput.name = 'username';
                usernameInput.value = response.data.username;

                var tokenInput = document.createElement('input');
                tokenInput.type = 'hidden';
                tokenInput.name = 'token';
                tokenInput.value = response.data.token;

// Append input elements to the form
                form.appendChild(usernameInput);
                form.appendChild(tokenInput);

// Append the form to the body
                document.body.appendChild(form);

// Submit the form
                form.submit();

            } else {
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
        }

    }

});


app.controller('Mysqlmanager', function ($scope, $http, $compile, $window, $timeout) {
    $scope.cyberPanelLoading = false;
    $scope.mysql_status = 'test'


    $scope.getstatus = function () {

        $scope.cyberPanelLoading = true;

        url = "/dataBases/getMysqlstatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = false;
            if (response.data.status === 1) {
                $scope.uptime = response.data.uptime;
                $scope.connections = response.data.connections;
                $scope.Slow_queries = response.data.Slow_queries;
                $scope.processes = JSON.parse(response.data.processes);
                $timeout($scope.showStatus, 3000);

                new PNotify({
                    title: 'Success',
                    text: 'Successfully Fetched',
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
            $scope.cyberPanelLoading = false;
            new PNotify({
                title: 'Error!',
                text: "cannot load",
                type: 'error'
            });
        }

    }

    $scope.getstatus();
});


app.controller('OptimizeMysql', function ($scope, $http) {
    $scope.cyberPanelLoading = true;

    $scope.generateRecommendations = function () {
        $scope.cyberhosting = false;
        url = "/dataBases/generateRecommendations";

        var data = {
            detectedRam: $("#detectedRam").text()
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberhosting = true;
            if (response.data.status === 1) {
                $scope.suggestedContent = response.data.generatedConf;

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberhosting = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }

    };


    $scope.applyMySQLChanges = function () {
        $scope.cyberhosting = false;
        url = "/dataBases/applyMySQLChanges";

        var encodedContent = encodeURIComponent($scope.suggestedContent);

        var data = {
            suggestedContent: encodedContent
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberhosting = true;
            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success',
                    text: 'Changes successfully applied.',
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
            $scope.cyberhosting = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }

    };


    $scope.restartMySQL = function () {
        $scope.cyberPanelLoading = false;

        url = "/dataBases/restartMySQL";

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
                new PNotify({
                    title: 'Success',
                    text: 'Successfully Done',
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
            $scope.cyberhosting = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    }
})


app.controller('mysqlupdate', function ($scope, $http, $timeout) {
    $scope.cyberPanelLoading = true;
    $scope.dbLoading = true;
    $scope.modeSecInstallBox = true;
    $scope.modsecLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.modSecSuccessfullyInstalled = true;
    $scope.installationFailed = true;

    $scope.Upgardemysql = function () {
        $scope.dbLoading = false;
        $scope.installform = true;
        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;


        url = "/dataBases/upgrademysqlnow";

        var data = {
            mysqlversion: $scope.version
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberhosting = true;
            if (response.data.status === 1) {
                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.statusfile = response.data.tempStatusPath

                $timeout(getRequestStatus, 1000);

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = true;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberhosting = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    }


    function getRequestStatus() {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/dataBases/upgrademysqlstatus";

        var data = {
            statusfile: $scope.statusfile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            } else {
                // Notifications
                $timeout.cancel();
                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.modSecSuccessfullyInstalled = false;
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }
});