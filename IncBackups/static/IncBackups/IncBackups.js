//*** Backup site ****//

app.controller('createIncrementalBackups', function ($scope, $http, $timeout) {

    $scope.destination = true;
    $scope.backupButton = true;
    $scope.cyberpanelLoading = true;
    $scope.runningBackup = true;
    $scope.restoreSt = true;


    $scope.fetchDetails = function () {
        getBackupStatus();
        $scope.populateCurrentRecords();
        $scope.destination = false;
        $scope.runningBackup = true;
    };

    function getBackupStatus() {

        $scope.cyberpanelLoadingBottom = false;

        url = "/IncrementalBackups/getBackupStatus";

        var data = {
            websiteToBeBacked: $scope.websiteToBeBacked,
            tempPath: $scope.tempPath
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
                    $scope.backupButton = false;
                    $scope.cyberpanelLoading = true;
                    $scope.fileName = response.data.fileName;
                    $scope.status = response.data.status;
                    $scope.populateCurrentRecords();
                    return;
                } else {
                    $scope.destination = true;
                    $scope.backupButton = true;
                    $scope.runningBackup = false;

                    $scope.fileName = response.data.fileName;
                    $scope.status = response.data.status;
                    $timeout(getBackupStatus, 2000);

                }
            } else {
                $timeout.cancel();
                $scope.cyberpanelLoadingBottom = true;
                $scope.cyberpanelLoading = true;
                $scope.backupButton = false;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    }

    $scope.destinationSelection = function () {
        $scope.backupButton = false;
    };

    $scope.populateCurrentRecords = function () {

        url = "/IncrementalBackups/fetchCurrentBackups";

        var data = {
            websiteToBeBacked: $scope.websiteToBeBacked,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.status === 1) {
                $scope.records = JSON.parse(response.data.data);
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
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    $scope.createBackup = function () {

        $scope.status = '';

        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/submitBackupCreation";

        var data = {
            websiteToBeBacked: $scope.websiteToBeBacked,
            backupDestinations: $scope.backupDestinations,
            websiteData: $scope.websiteData,
            websiteEmails: $scope.websiteEmails,
            websiteSSLs: $scope.websiteSSLs,
            websiteDatabases: $scope.websiteDatabases

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.tempPath = response.data.tempPath;
                getBackupStatus();
            }else{
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    $scope.deleteBackup = function (id) {


        url = "/IncrementalBackups/deleteBackup";

        var data = {
            backupID: id,
            websiteToBeBacked: $scope.websiteToBeBacked
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status === 1) {

                $scope.populateCurrentRecords();

            }else{
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }


    };

    $scope.restore = function (id) {

        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/fetchRestorePoints";

        var data = {
            id: id,
            websiteToBeBacked: $scope.websiteToBeBacked
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
                $scope.jobs = JSON.parse(response.data.data);
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

    $scope.restorePoint = function (id, reconstruct) {

        $scope.status = '';

        $scope.cyberpanelLoading = false;
        $scope.restoreSt = false;


        url = "/IncrementalBackups/restorePoint";

        var data = {
            websiteToBeBacked: $scope.websiteToBeBacked,
            jobid : id,
            reconstruct: reconstruct

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.tempPath = response.data.tempPath;
                getBackupStatus();
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
        if ($scope.destinationType === 'SFTP') {
            type = 'SFTP';
        } else {
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

        if (type === 'SFTP') {
            var data = {
                type: type,
                IPAddress: $scope.IPAddress,
                password: $scope.password,
                backupSSHPort: $scope.backupSSHPort
            };
        } else {
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