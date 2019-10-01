//*** Backup site ****//

app.controller('createIncrementalBackups', function ($scope, $http, $timeout) {

    $scope.destination = true;
    $scope.backupButton = true;
    $scope.cyberpanelLoading = true;
    $scope.runningBackup = true;
    $scope.cancelButton = true;

    populateCurrentRecords();

    $scope.cancelBackup = function () {

        var backupCancellationDomain = $scope.websiteToBeBacked;

        url = "/backup/cancelBackupCreation";

        var data = {
            backupCancellationDomain: backupCancellationDomain,
            fileName: $scope.fileName,
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

        $scope.cyberpanelLoadingBottom = false;

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
                    $scope.cyberpanelLoadingBottom = true;
                    $scope.destination = false;
                    $scope.runningBackup = false;
                    $scope.cancelButton = true;
                    $scope.backupButton = false;
                    $scope.cyberpanelLoading = true;
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
                $scope.cyberpanelLoadingBottom = true;
                $scope.cyberpanelLoading = true;
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

        var websiteToBeBacked = $scope.websiteToBeBacked;
        $scope.cyberpanelLoading = false;


        url = "/backup/submitBackupCreation";

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


            if (response.data.metaStatus === 1) {
                getBackupStatus();
            }

        }

        function cantLoadInitialDatas(response) {
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

///** Backup site ends **///


app.controller('incrementalDestinations', function ($scope, $http) {
    $scope.cyberpanelLoading = true;
    $scope.sftpHide = true;
    $scope.awsHide = true;

    $scope.fetchDetails = function () {

        if ($scope.destinationType === 'SFTP') {
            $scope.sftpHide = false;
            $scope.populateCurrentRecords();
        } else {
            $scope.sftpHide = true;
            $scope.awsHide = false;
            $scope.populateCurrentRecords();
        }
    };

    $scope.populateCurrentRecords = function () {

        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/populateCurrentRecords";

        var type = 'SFTP';
        if ($scope.destinationType === 'SFTP'){
            type = 'SFTP';
        }else{
            type = 'AWS';
        }

        var data = {
            type: type
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                $scope.records = JSON.parse(response.data.data);
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    $scope.addDestination = function (type) {
        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/addDestination";

        if(type === 'SFTP'){
            var data = {
                type: type,
                IPAddress: $scope.IPAddress,
                password: $scope.password,
                backupSSHPort: $scope.backupSSHPort
            };
        }else {
            var data = {
                type: type,
                AWS_ACCESS_KEY_ID: $scope.AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY: $scope.AWS_SECRET_ACCESS_KEY,
            };
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            $scope.populateCurrentRecords();
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Destination successfully added.',
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    $scope.removeDestination = function (type, ipAddress) {
        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/removeDestination";

        var data = {
            type: type,
            IPAddress: ipAddress,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            $scope.populateCurrentRecords();
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Destination successfully removed.',
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };


});