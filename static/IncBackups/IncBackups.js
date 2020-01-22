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
            } else {
                $scope.cyberpanelLoading = true;
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

            } else {
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
            jobid: id,
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
            $scope.awsHide = true;
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


app.controller('scheduleBackupInc', function ($scope, $http) {

    var globalPageNumber;
    $scope.scheduleFreq = true;
    $scope.cyberpanelLoading = true;
    $scope.getFurtherWebsitesFromDB = function (pageNumber) {
        $scope.cyberpanelLoading = false;
        globalPageNumber = pageNumber;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {page: pageNumber};


        dataurl = "/CloudLinux/submitWebsiteListing";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.listWebSiteStatus === 1) {
                var finalData = JSON.parse(response.data.data);
                $scope.WebSitesList = finalData;
                $scope.pagination = response.data.pagination;
                $scope.default = response.data.default;
                $("#listFail").hide();
            } else {
                $("#listFail").fadeIn();
                $scope.errorMessage = response.data.error_message;
                console.log(response.data);

            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
        }


    };

    var websitesToBeBacked = [];
    var websitesToBeBackedTemp = [];

    var index = 0;
    var tempTransferDir = "";
    $scope.addRemoveWebsite = function (website, websiteStatus) {

        if (websiteStatus === true) {
            var check = 1;
            for (var j = 0; j < websitesToBeBacked.length; j++) {
                if (websitesToBeBacked[j] == website) {
                    check = 0;
                    break;
                }
            }
            if (check == 1) {
                websitesToBeBacked.push(website);
            }

        } else {

            var tempArray = [];

            for (var j = 0; j < websitesToBeBacked.length; j++) {
                if (websitesToBeBacked[j] != website) {
                    tempArray.push(websitesToBeBacked[j]);
                }
            }
            websitesToBeBacked = tempArray;
        }
    };

    $scope.allChecked = function (webSiteStatus) {
        if (webSiteStatus === true) {

            websitesToBeBacked = websitesToBeBackedTemp;
            $scope.webSiteStatus = true;
        } else {
            websitesToBeBacked = [];
            $scope.webSiteStatus = false;
        }
    };

    $scope.scheduleFreqView = function () {
        $scope.scheduleFreq = false;
        $scope.getFurtherWebsitesFromDB(1);

    };
    $scope.addSchedule = function () {
        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/submitBackupSchedule";

        var data = {
            backupDestinations: $scope.backupDest,
            backupFreq: $scope.backupFreq,
            websiteData: $scope.websiteData,
            websiteEmails: $scope.websiteEmails,
            websiteDatabases: $scope.websiteDatabases,
            websitesToBeBacked: websitesToBeBacked
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

    $scope.populateCurrentRecords = function () {

        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/getCurrentBackupSchedules";


        var data = {};

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
                var parsed = JSON.parse(response.data.data);

                for (var j = 0; j < parsed.length; j++) {
                    websitesToBeBackedTemp.push(parsed[j].website);
                }
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
    $scope.populateCurrentRecords();

    $scope.delSchedule = function (id) {

        $scope.cyberpanelLoading = false;

        url = "/IncrementalBackups/scheduleDelete";


        var data = {id: id};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;

            if (response.data.status === 1) {
                $scope.populateCurrentRecords();
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

    $scope.editInitial = function (id) {

        $scope.jobID = id;

        $scope.cyberpanelLoading = false;


        url = "/IncrementalBackups/fetchSites";


        var data = {id: id};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                $scope.websites = JSON.parse(response.data.data);

                if(response.data.websiteData === 1){
                    $scope.websiteData = true;
                }
                if(response.data.websiteDatabases === 1){
                    $scope.websiteDatabases = true;
                }
                if(response.data.websiteEmails === 1){
                    $scope.websiteEmails = true;
                }

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

    $scope.saveChanges = function () {

        $scope.cyberpanelLoading = false;

        url = "/IncrementalBackups/saveChanges";


        var data = {
            id: $scope.jobID,
            websiteData: $scope.websiteData,
            websiteDatabases: $scope.websiteDatabases,
            websiteEmails: $scope.websiteEmails

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
                $scope.editInitial($scope.jobID);
                new PNotify({
                    title: 'Success!',
                    text: 'Operation successful.',
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

    $scope.removeSite = function (website) {

        $scope.cyberpanelLoading = false;

        url = "/IncrementalBackups/removeSite";


        var data = {
            id: $scope.jobID,
            website: website
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
                $scope.editInitial($scope.jobID);
                new PNotify({
                    title: 'Success!',
                    text: 'Operation successful.',
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

    $scope.cyberpanelLoading = true;

    $scope.addWebsite = function () {

        $scope.cyberpanelLoading = false;

        url = "/IncrementalBackups/addWebsite";


        var data = {
            id: $scope.jobID,
            website: $scope.websiteToBeAdded
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
                $scope.editInitial($scope.jobID);
                new PNotify({
                    title: 'Success!',
                    text: 'Operation successful.',
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


app.controller('restoreRemoteBackupsInc', function ($scope, $http, $timeout) {

    $scope.destination = true;
    $scope.backupButton = true;
    $scope.cyberpanelLoading = true;
    $scope.runningBackup = true;
    $scope.restoreSt = true;

    $scope.showThings = function () {
        $scope.destination = false;
        $scope.runningBackup = true;
    };

    $scope.fetchDetails = function () {
        $scope.populateCurrentRecords();
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
                    if(response.data.status === 1){
                        $scope.status = 'Fetching status..'
                    }else{
                        $scope.status = response.data.status;
                    }

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

    $scope.populateCurrentRecords = function () {
        $scope.cyberpanelLoading = false;

        url = "/IncrementalBackups/fetchCurrentBackups";

        var data = {
            websiteToBeBacked: $scope.websiteToBeBacked,
            backupDestinations: $scope.backupDestinations,
            password: $scope.password
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
                    title: 'Error!',
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

    $scope.restorePoint = function (id, path) {

        $scope.status = '';

        $scope.cyberpanelLoading = false;
        $scope.restoreSt = false;


        url = "/IncrementalBackups/restorePoint";

        var data = {
            websiteToBeBacked: $scope.websiteToBeBacked,
            jobid: id,
            reconstruct: 'remote',
            path: path,
            backupDestinations: $scope.backupDestinations,
            password: $scope.password

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