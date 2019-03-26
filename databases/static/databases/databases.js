/**
 * Created by usman on 8/6/17.
 */


/* Java script code to create database */
app.controller('createDatabase', function ($scope, $http) {

    $scope.createDatabaseLoading = true;
    $scope.dbDetails = true;
    $scope.databaseCreationFailed = true;
    $scope.databaseCreated = true;
    $scope.couldNotConnect = true;
    $scope.generatedPasswordView = true;


    $scope.showDetailsBoxes = function () {
        $scope.dbDetails = false;
    };

    $scope.createDatabase = function () {

        $scope.createDatabaseLoading = false;
        $scope.dbDetails = false;
        $scope.databaseCreationFailed = true;
        $scope.databaseCreated = true;
        $scope.couldNotConnect = true;


        var databaseWebsite = $scope.databaseWebsite;
        var dbName = $scope.dbName;
        var dbUsername = $scope.dbUsername;
        var dbPassword = $scope.dbPassword;
        var webUserName = "";

        // getting website username

        webUserName = databaseWebsite.replace(/-/g, '');
        webUserName = webUserName.split(".")[0];

        if (webUserName.length > 5) {
            webUserName = webUserName.substring(0, 4);
        }

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


            if (response.data.createDBStatus == 1) {

                $scope.createDatabaseLoading = true;
                $scope.dbDetails = false;
                $scope.databaseCreationFailed = true;
                $scope.databaseCreated = false;
                $scope.couldNotConnect = true;


            }

            else {


                $scope.createDatabaseLoading = true;
                $scope.dbDetails = false;
                $scope.databaseCreationFailed = false;
                $scope.databaseCreated = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.createDatabaseLoading = true;
            $scope.dbDetails = true;
            $scope.databaseCreationFailed = true;
            $scope.databaseCreated = true;
            $scope.couldNotConnect = false;
        }


    };

    $scope.generatePassword = function () {
        $scope.generatedPasswordView = false;
        $scope.dbPassword = randomPassword(12);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
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


            }

            else {
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


            }

            else {
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

            }
            else {
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

            }
            else {
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
        $scope.dbPassword = randomPassword(12);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
    };

});


/* Java script code to list database ends here */


app.controller('phpMyAdmin', function ($scope, $http, $window) {

    function setupPHPMYAdminSession() {

        url = "/dataBases/setupPHPMYAdminSession";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status === 1) {
                $window.location.href = '/phpmyadmin';
            }
            else {}

        }

        function cantLoadInitialDatas(response) {}

    }
    setupPHPMYAdminSession();

});