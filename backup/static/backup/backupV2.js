newapp.controller('backupWebsiteControlV2', function ($scope, $http, $timeout) {

    $(document).ready(function () {
        $(".destinationHide").hide();
        $('#create-backup-select').select2();
    });

    $('#create-backup-select').on('select2:select', function (e) {
        var data = e.params.data;
        $scope.websiteToBeBacked = data.text;
        $(".destinationHide").show();
        getBackupStatus();
        populateCurrentRecords();
        $scope.destination = false;
        $scope.runningBackup = true;
    });

    $scope.destination = true;
    $scope.backupButton = true;
    $scope.backupLoading = true;
    $scope.runningBackup = true;
    $scope.cancelButton = true;

    populateCurrentRecords();

    $scope.cancelBackup = function () {

        var backupCancellationDomain = $scope.websiteToBeBacked;

        url = "/backup/cancelBackupCreation";

        var data = {
            backupCancellationDomain: backupCancellationDomain, fileName: $scope.fileName,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

    };

    $scope.fetchDetails = function () {
        getBackupStatus();
        populateCurrentRecords();
        $scope.destination = false;
        $scope.runningBackup = true;

    };

    function getBackupStatus() {

        $scope.backupLoadingBottom = false;

        var websiteToBeBacked = $scope.websiteToBeBacked;

        url = "/backup/backupStatus";

        var data = {
            websiteToBeBacked: websiteToBeBacked,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.backupStatus === 1) {

                if (response.data.abort === 1) {
                    $timeout.cancel();
                    $scope.backupLoadingBottom = true;
                    $scope.destination = false;
                    $scope.runningBackup = false;
                    $scope.cancelButton = true;
                    $scope.backupButton = false;
                    $scope.backupLoading = true;
                    $scope.fileName = response.data.fileName;
                    $scope.status = response.data.status;
                    populateCurrentRecords();
                    return;
                } else {
                    $scope.destination = true;
                    $scope.backupButton = true;
                    $scope.runningBackup = false;
                    $scope.cancelButton = false;

                    $scope.fileName = response.data.fileName;
                    $scope.status = response.data.status;
                    $timeout(getBackupStatus, 2000);

                }
            } else {
                $timeout.cancel();
                $scope.backupLoadingBottom = true;
                $scope.backupLoading = true;
                $scope.cancelButton = true;
                $scope.backupButton = false;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    $scope.destinationSelection = function () {
        $scope.backupButton = false;
    };

    function populateCurrentRecords() {

        var websiteToBeBacked = $scope.websiteToBeBacked;

        url = "/backup/getCurrentBackups";

        var data = {
            websiteToBeBacked: websiteToBeBacked,
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
            }


        }

        function cantLoadInitialDatas(response) {
        }

    };

    $scope.createBackup = function () {

        var createBackupButton = document.getElementById("createBackup");
        createBackupButton.disabled = true;
        var websiteToBeBacked = $scope.websiteToBeBacked;
        $scope.backupLoading = false;


        url = "/backup/submitBackupCreation";

        var data = {
            websiteToBeBacked: websiteToBeBacked,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        // console.log("-------------------")
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.metaStatus === 1) {
                getBackupStatus();
                createBackupButton.disabled = false;
            }

        }

        function cantLoadInitialDatas(response) {
            createBackupButton.disabled = false;
        }

    };

    $scope.deleteBackup = function (id) {

        url = "/backup/deleteBackup";

        var data = {
            backupID: id,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.deleteStatus == 1) {

                populateCurrentRecords();


            } else {

            }

        }

        function cantLoadInitialDatas(response) {


        }


    };


});
$("#websiteDeleteFailure").hide();
$("#websiteDeleteSuccess").hide();

newapp.controller('restoreWebsiteControlV2', function ($scope, $http, $timeout) {

    $scope.restoreLoading = true;
    $scope.runningRestore = true;
    $scope.restoreButton = true;
    $scope.restoreFinished = false;
    $scope.couldNotConnect = true;
    $scope.backupError = true;
    $scope.siteExists = true;

    // check to start time of status function

    var check = 1;


    $scope.fetchDetails = function () {
        $scope.restoreLoading = false;
        getRestoreStatus();
    };


    function getRestoreStatus() {

        var backupFile = $scope.backupFile;

        url = "/backup/restoreStatus";

        var data = {
            backupFile: backupFile,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.restoreStatus === 1) {

                if (response.data.abort === 1) {
                    $scope.running = response.data.running;
                    $scope.fileName = $scope.backupFile;
                    $scope.restoreLoading = true;
                    $scope.status = response.data.status;
                    $scope.runningRestore = false;
                    $scope.restoreButton = false;
                    $scope.restoreFinished = true;
                    $timeout.cancel();
                    return;
                } else {
                    $scope.running = response.data.running;
                    $scope.fileName = $scope.backupFile;
                    $scope.restoreLoading = false;
                    $scope.status = response.data.status;
                    $scope.runningRestore = false;
                    $scope.restoreButton = true;
                    $timeout(getRestoreStatus, 2000);
                }
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;


        }

    };


    $scope.restoreBackup = function () {
        var restoreBackupButton = document.getElementById("restoreBackup");
        restoreBackupButton.disabled = true;
        var backupFile = $scope.backupFile;
        $scope.running = "Lets start.."

        url = "/backup/submitRestore";

        var data = {
            backupFile: backupFile,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.restoreLoading = true;
            if (response.data.restoreStatus == 1) {
                $scope.runningRestore = false;
                $scope.running = "Running";
                $scope.fileName = $scope.backupFile;
                $scope.status = "Just Started..";

                getRestoreStatus();
                restoreBackupButton.disabled = false;
            } else {
                $scope.backupError = false;
                $scope.errorMessage = response.data.error_message;
                restoreBackupButton.disabled = false;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
            restoreBackupButton.disabled = false;
        }

    };


    function createWebsite() {

        var backupFile = $scope.backupFile;

        url = "/websites/CreateWebsiteFromBackup";

        var data = {
            backupFile: backupFile,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createWebSiteStatus == 1) {
                getRestoreStatus();
            } else if (response.data.existsStatus == 1) {
                $scope.backupError = false;
                $scope.errorMessage = response.data.error_message;
                $scope.restoreButton = true;
                $scope.runningRestore = true;
            } else {
                $scope.websiteDomain = domainName;
                $scope.backupError = false;
                $scope.errorMessage = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
        }


    };


});