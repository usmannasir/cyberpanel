//*** Backup site ****//

app.controller('createIncrementalBackups', function ($scope, $http, $timeout) {

    $scope.destination = true;
    $scope.backupButton = true;
    $scope.cyberpanelLoading = false;
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
                    $scope.cyberpanelLoading = false;
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
                $scope.cyberpanelLoading = false;
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
                $scope.records = response.data.data;
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
                $scope.cyberpanelLoading = false;
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

    // $scope.RestoreV2Backup = function () {
    //
    //     // $scope.status = '';
    //     //
    //     // $scope.cyberpanelLoading = false;
    //     //
    //     //
    //     // url = "/IncrementalBackups/submitBackupCreation";
    //
    //
    //     console.log($scope.websiteToBeBacked)
    //     console.log($scope.websiteData)
    //     var websites = document.getElementById('create-backup-select');
    //     var selected_website = websites.options[websites.selectedIndex].innerHTML;
    //     console.log(selected_website);
    //
    //     var data = {
    //         websiteToBeBacked: $scope.websiteToBeBacked,
    //         backupDestinations: $scope.backupDestinations,
    //         websiteData: $scope.websiteData,
    //         websiteEmails: $scope.websiteEmails,
    //         websiteSSLs: $scope.websiteSSLs,
    //         websiteDatabases: $scope.websiteDatabases
    //
    //     };
    //
    //     // var config = {
    //     //     headers: {
    //     //         'X-CSRFToken': getCookie('csrftoken')
    //     //     }
    //     // };
    //     //
    //     //
    //     // $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);
    //     //
    //     //
    //     // function ListInitialDatas(response) {
    //     //
    //     //     if (response.data.status === 1) {
    //     //         $scope.tempPath = response.data.tempPath;
    //     //         getBackupStatus();
    //     //     } else {
    //     //         $scope.cyberpanelLoading = true;
    //     //         new PNotify({
    //     //             title: 'Operation Failed!',
    //     //             text: response.data.error_message,
    //     //             type: 'error'
    //     //         });
    //     //     }
    //     //
    //     // }
    //     //
    //     // function cantLoadInitialDatas(response) {
    //     // }
    //
    // };

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
            $scope.cyberpanelLoading = false;
            if (response.data.status === 1) {
                $scope.jobs = response.data.data;
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
    $scope.cyberpanelLoading = false;
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

        $scope.cyberpanelLoading = true;


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
            $scope.cyberpanelLoading = false;
            if (response.data.status === 1) {
                $scope.records = response.data.data;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    $scope.addDestination = function (type) {
        $scope.cyberpanelLoading = true;


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
            $scope.cyberpanelLoading = false;
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
            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    $scope.removeDestination = function (type, ipAddress) {
        $scope.cyberpanelLoading = true;


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
            $scope.cyberpanelLoading = false;
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
            $scope.cyberpanelLoading = false;
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
            backupRetention: $scope.backupRetention,
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
                let data = response.data.data;
                $scope.records = data;
                data.forEach(item => {
                    websitesToBeBackedTemp.push(item.website)
                })
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
                $scope.websites = response.data.data;

                if (response.data.websiteData === 1) {
                    $scope.websiteData = true;
                }
                if (response.data.websiteDatabases === 1) {
                    $scope.websiteDatabases = true;
                }
                if (response.data.websiteEmails === 1) {
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
                    $scope.cyberpanelLoading = false;
                    $scope.fileName = response.data.fileName;
                    $scope.status = response.data.status;
                    $scope.populateCurrentRecords();
                    return;
                } else {
                    $scope.destination = true;
                    $scope.backupButton = true;
                    $scope.runningBackup = false;

                    $scope.fileName = response.data.fileName;
                    if (response.data.status === 1) {
                        $scope.status = 'Fetching status..'
                    } else {
                        $scope.status = response.data.status;
                    }

                    $timeout(getBackupStatus, 2000);

                }
            } else {
                $timeout.cancel();
                $scope.cyberpanelLoadingBottom = true;
                $scope.cyberpanelLoading = false;
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
                $scope.records = response.data.data;
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


app.controller('restorev2backupoage', function ($scope, $http, $timeout, $compile) {


    $scope.backupLoading = true;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    $scope.selectwebsite = function () {
        //document.getElementById('reposelectbox').innerHTML = "";
        $scope.backupLoading = false;

        var url = "/IncrementalBackups/selectwebsiteRetorev2";

        var data = {
            Selectedwebsite: $scope.selwebsite,

        };
        //alert( $scope.selwebsite);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {

                $scope.repos = response.data.data;

                console.log($scope.repos);


                // const selectBox = document.getElementById('reposelectbox');
                //
                //
                // const options = response.data.data;
                // const option = document.createElement('option');
                //
                //
                // option.value = 1;
                // option.text = 'Choose Repo';
                //
                // selectBox.appendChild(option);
                //
                // if (options.length >= 1) {
                //     for (let i = 0; i < options.length; i++) {
                //
                //         const option = document.createElement('option');
                //
                //
                //         option.value = options[i];
                //         option.text = options[i];
                //
                //         selectBox.appendChild(option);
                //     }
                //
                // } else {
                //     new PNotify({
                //         title: 'Error!',
                //         text: 'file empty',
                //         type: 'error'
                //     });
                // }


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }

    $scope.RestorePathV2Model = function (SnapshotId, Path) {

        $('#RestoreSnapshotPath').modal('show');

        document.getElementById('Snapshot_id').innerText = SnapshotId
        document.getElementById('Snapshot_Path_id').innerText = Path


    }

    $scope.DeleteSnapshotBackupsv2 = function (SnapshotId, Path) {
        $('#DeleteSnapshotmodelv2').modal('show');

        document.getElementById('Snapshot_id_delete').innerText = SnapshotId;
        //alert(document.getElementById('Snapshot_id_delete').innerText);

    }

    function getCreationStatus() {

        url = "/IncrementalBackups/CreateV2BackupStatus";

        var data = {
            domain: Domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.abort === 1) {
                $scope.backupLoading = true;
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
                    $scope.backupLoading = true;
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
                $scope.webSiteCreationLoading = false;
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

    $scope.RestorePathV2 = function (SnapshotId, Path) {

        $scope.backupLoading = false;

        SnapshotId = document.getElementById('Snapshot_id').innerText
        Path = document.getElementById('Snapshot_Path_id').innerText
        console.log("SnapshotId: " + SnapshotId)
        console.log("Path: " + Path)
        var url = "/IncrementalBackups/RestorePathV2";
        var data = {
            snapshotid: SnapshotId,
            path: Path,
            selwebsite: $scope.selwebsite,
            selectedrepo: $scope.testhabbi
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.status === 1) {
                $scope.SnapShotId = response.data.SnapShotId;
                $scope.tempPath = response.data.Path;


                console.log("Returned ID on ListInitialDatas: " + $scope.SnapShotId)
                console.log("Returned PATH on ListInitialDatas: " + $scope.tempPath)


                Domain = $scope.selwebsite;
                getCreationStatus();

            } else {
                $scope.backupLoading = true;
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
        }


    }

    $scope.DeleteSnapshotV2Final = function (SnapshotId, Path) {

        $scope.backupLoading = false;

        SnapshotId = document.getElementById('Snapshot_id_delete').innerText
        console.log("SnapshotId: " + SnapshotId)
        var url = "/IncrementalBackups/DeleteSnapshotV2Final";
        var data = {
            snapshotid: SnapshotId,
            selwebsite: $scope.selwebsite,
            selectedrepo: $scope.testhabbi
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                        title: 'Success!',
                        text: 'Snapshot Deleted.',
                        type: 'success'
                    });

            } else {
                $scope.backupLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                new PNotify({
                        title: 'Error!',
                        text: response.data.error_message,
                        type: 'error'
                    });
            }

        }

        function cantLoadInitialDatas(response) {
        }


    }

    $scope.selectrepo = function () {
        $scope.backupLoading = false;

        var url = "/IncrementalBackups/selectreporestorev2";

        var data = {
            Selectedrepo: $scope.testhabbi,
            Selectedwebsite: $scope.selwebsite,
        }
        //alert( $scope.selwebsite);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {

                var data = response.data.data


                var snapshots = response.data.data

                for (var i = 0; i < snapshots.length; i++) {
                    for (var j = 0; j < snapshots[i][1].length; j++) {
                        var tml = '<tr style="">\n' +
                            '  <td>' + snapshots[i][1][j].id + '</td>' +
                            '  <td>' + snapshots[i][1][j].time + '</td>' +
                            '  <td><button ng-click=\'DeleteSnapshotBackupsv2("' + snapshots[i][1][j].id + '","' + snapshots[i][1][j].paths[k] + '")\'  type="button" class="btn btn-danger">Delete</button></td>\n' +
                            '</tr>' +
                            '<tr style="border: none!important;"> <td colspan="2" style="display: inherit;max-height: 10px;background-color: transparent; border: none">\n' +
                            '  <button id="' + snapshots[i][1][j].id + 'button" class="my-4 mx-4 btn " style="margin-bottom: 15px;margin-top: -8px;background-color: #161a69; color: white;border-radius: 6px" onclick=listpaths("' + snapshots[i][1][j].id + '","' + snapshots[i][1][j].id + 'button")>+</button>\n' +
                            '</td></tr>' +
                            '<tr style="border: none!important;">' +
                            '  <td colspan="2" style="display: none;border: none"  id="' + snapshots[i][1][j].id + '">' +
                            '    <table id="inside" style="margin: 0 auto; margin-bottom: 30px;border: 1px #ccc solid;">\n';

                        for (var k = 0; k < snapshots[i][1][j].paths.length; k++) {
                            tml += '<tr style="border-top: 1px #cccccc solid;display: flex;padding: 15px; justify-content: space-between;">\n' +
                                '<td style="">' + snapshots[i][1][j].paths[k] + '</td>\n' +
                                '<td style="">' +
                                '<button id="' + snapshots[i][1][j].paths[k] + '" style="margin-inline: 30px; color: white!important; background-color: #3051be; border-radius: 6px;" class="btn" ng-click=\'RestorePathV2Model("' + snapshots[i][1][j].id + '","' + snapshots[i][1][j].paths[k] + '")\'>Restore</button></td>\n' +
                                '</tr>\n';
                        }

                        tml += '</table>\n' +
                            '</td>\n' +
                            '</tr>\n' +
                            '</tr>\n';
                        var mp = $compile(tml)($scope);

                        $('#listsnapshots').append(mp);
                    }
                }


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }


});

app.controller('CreateV2Backup', function ($scope, $http, $timeout, $compile) {


    $scope.backupLoading = true;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    $scope.selectwebsite = function () {
        document.getElementById('reposelectbox').innerHTML = "";
        $scope.backupLoading = false;
        // document.getElementById('CreateV2BackupButton').style.display = "block";
        var url = "/IncrementalBackups/selectwebsiteCreatev2";

        var data = {
            Selectedwebsite: $scope.selwebsite,
            Selectedrepo: $('#reposelectbox').val(),
        };
        //alert( $scope.selwebsite);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {

                const selectBox = document.getElementById('reposelectbox');


                const options = response.data.data;
                const option = document.createElement('option');


                option.value = 1;
                option.text = 'Choose Repo';

                selectBox.appendChild(option);

                if (options.length >= 1) {
                    for (let i = 0; i < options.length; i++) {

                        const option = document.createElement('option');


                        option.value = options[i];
                        option.text = options[i];

                        selectBox.appendChild(option);
                    }

                } else {
                    new PNotify({
                        title: 'Error!',
                        text: 'file empty',
                        type: 'error'
                    });
                }


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }

    var Domain;

    $scope.CreateV2BackupButton = function () {
        $scope.backupLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;

        var url = "/IncrementalBackups/CreateV2BackupButton";
        var websiteData = $scope.websiteData;
        var websiteEmails = $scope.websiteEmails;
        var websiteDatabases = $scope.websiteDatabases;
        var chk = 0;
        if (websiteData === true || websiteDatabases === true || websiteEmails === true) {
            chk = 1;
        }
        var data = {};


        data = {
            Selectedwebsite: $scope.selwebsite,
            Selectedrepo: $('#reposelectbox').val(),
            websiteDatabases: websiteDatabases,
            websiteEmails: websiteEmails,
            websiteData: websiteData,

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        //alert('Done..........')
        if (chk === 1) {
            $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);
        } else {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Choose Backup Content!',
                text: 'Please Choose Backup content Data, Database, Email',
                type: 'error'
            });
        }


        function ListInitialDatas(response) {
            if (response.data.status === 1) {

                Domain = $scope.selwebsite;
                getCreationStatus();

            } else {
                $scope.backupLoading = true;
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
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }


    function getCreationStatus() {

        url = "/IncrementalBackups/CreateV2BackupStatus";

        var data = {
            domain: Domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.abort === 1) {
                $scope.backupLoading = true;
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
                $scope.webSiteCreationLoading = false;
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

app.controller('ConfigureV2Backup', function ($scope, $http, $timeout) {
    $scope.cyberpanelLoading = true;
    $scope.selectbackuptype = function () {

        $scope.cyberpanelLoading = false;

        var backuptype = $scope.v2backuptype
        if (backuptype === 'GDrive') {
            $scope.cyberpanelLoading = true;
            $('#GdriveModal').modal('show');
        } else if (backuptype === 'SFTP') {
            $scope.cyberpanelLoading = true;
            $('#SFTPModal').modal('show');
        }
    }


    $scope.setupAccount = function () {
        window.open("https://platform.cyberpersons.com/gDrive?name=" + $scope.accountName + '&client_id=' + $scope.client_id + '&client_secret=' + $scope.client_secret + '&server=' + window.location.href + 'Setup&domain=' + $scope.selwebsite);
    };

    $scope.ConfigerSFTP = function () {
        $scope.cyberpanelLoading = false;
        var url = "/IncrementalBackups/ConfigureSftpV2Backup";

        var data = {
            Selectedwebsite: $scope.selwebsite,
            sfptpasswd: $scope.sfptpasswd,
            hostName: $scope.hostName,
            UserName: $scope.UserName,
            Repo_Name: $scope.reponame,
            sshPort: $scope.sshPort
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {
                location.reload()

            } else {
                $scope.goBackDisable = false;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }
});

function listpaths(pathid, button) {

    var pathlist = document.getElementById(pathid)
    if (pathlist.style.display === "none") {
        pathlist.style.display = "revert";

        document.getElementById(button).innerText = "-"

    } else {
        pathlist.style.display = "none";

        document.getElementById(button).innerText = "+"

    }
}

app.controller('ScheduleV2Backup', function ($scope, $http, $timeout, $compile) {


    $scope.backupLoading = true;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    var repoG, frequencyG, websiteDataG, websiteDatabasesG, websiteEmailsG;

    $scope.deleteBackupInitialv2 = function (repo, frequency, websiteData, websiteDatabases, websiteEmails) {
        repoG = repo;
        frequencyG = frequency;
        websiteDataG = websiteData;
        websiteDatabasesG = websiteDatabases;
        websiteEmailsG = websiteEmails;
    }

    $scope.DeleteScheduleV2 = function () {
        $scope.backupLoading = false;
        // document.getElementById('CreateV2BackupButton').style.display = "block";
        var url = "/IncrementalBackups/DeleteScheduleV2";

        var data = {
            Selectedwebsite: $scope.selwebsite,
            repo: repoG,
            frequency: frequencyG,
            websiteData: websiteDataG,
            websiteDatabases: websiteDatabasesG,
            websiteEmails: websiteEmailsG
        };
        //alert( $scope.selwebsite);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {
                $scope.selectwebsite();
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully deleted.',
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
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }

    $scope.selectwebsite = function () {
        document.getElementById('reposelectbox').innerHTML = "";
        $scope.backupLoading = false;
        // document.getElementById('CreateV2BackupButton').style.display = "block";
        var url = "/IncrementalBackups/selectwebsiteCreatev2";

        var data = {
            Selectedwebsite: $scope.selwebsite,
            Selectedrepo: $('#reposelectbox').val(),
        };
        //alert( $scope.selwebsite);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {

                const selectBox = document.getElementById('reposelectbox');


                const options = response.data.data;
                const option = document.createElement('option');
                $scope.records = response.data.currentSchedules;


                option.value = 1;
                option.text = 'Choose Repo';

                selectBox.appendChild(option);

                if (options.length >= 1) {
                    for (let i = 0; i < options.length; i++) {

                        const option = document.createElement('option');


                        option.value = options[i];
                        option.text = options[i];

                        selectBox.appendChild(option);
                    }

                } else {
                    new PNotify({
                        title: 'Error!',
                        text: 'file empty',
                        type: 'error'
                    });
                }


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }

    $scope.CreateScheduleV2 = function () {
        $scope.backupLoading = false;
        // document.getElementById('CreateV2BackupButton').style.display = "block";
        var url = "/IncrementalBackups/CreateScheduleV2";

        var data = {
            Selectedwebsite: $scope.selwebsite,
            repo: $('#reposelectbox').val(),
            frequency: $scope.frequency,
            websiteData: $scope.websiteData,
            websiteDatabases: $scope.websiteDatabases,
            websiteEmails: $scope.websiteEmails,
            retention: $scope.retention
        };
        //alert( $scope.selwebsite);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {
                $scope.selectwebsite();
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully created.',
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
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }

    var Domain;

    $scope.CreateV2BackupButton = function () {
        $scope.backupLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;

        var url = "/IncrementalBackups/CreateV2BackupButton";
        var websiteData = $scope.websiteData;
        var websiteEmails = $scope.websiteEmails;
        var websiteDatabases = $scope.websiteDatabases;
        var chk = 0;
        if (websiteData === true || websiteDatabases === true || websiteEmails === true) {
            chk = 1;
        }
        var data = {};


        data = {
            Selectedwebsite: $scope.selwebsite,
            Selectedrepo: $('#reposelectbox').val(),
            websiteDatabases: websiteDatabases,
            websiteEmails: websiteEmails,
            websiteData: websiteData,

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        //alert('Done..........')
        if (chk === 1) {
            $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);
        } else {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Choose Backup Content!',
                text: 'Please Choose Backup content Data, Database, Email',
                type: 'error'
            });
        }


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {

                Domain = $scope.selwebsite;
                getCreationStatus();

            } else {
                $scope.backupLoading = true;
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
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }

    function getCreationStatus() {

        url = "/IncrementalBackups/CreateV2BackupStatus";

        var data = {
            domain: Domain
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
                $scope.webSiteCreationLoading = false;
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


app.controller('DeleteBackuprepo', function ($scope, $http, $timeout, $compile) {

    $scope.backupLoading = true;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    $scope.selectwebsite = function () {
        document.getElementById('reposelectbox').innerHTML = "";
        $scope.backupLoading = false;
        // document.getElementById('CreateV2BackupButton').style.display = "block";
        var url = "/IncrementalBackups/selectwebsiteCreatev2";

        var data = {
            Selectedwebsite: $scope.selwebsite,
            Selectedrepo: $('#reposelectbox').val(),
        };
        //alert( $scope.selwebsite);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.backupLoading = true;
            if (response.data.status === 1) {

                const selectBox = document.getElementById('reposelectbox');


                const options = response.data.data;
                const option = document.createElement('option');


                option.value = 1;
                option.text = 'Choose Repo';

                selectBox.appendChild(option);

                if (options.length >= 1) {
                    for (let i = 0; i < options.length; i++) {

                        const option = document.createElement('option');


                        option.value = options[i];
                        option.text = options[i];

                        selectBox.appendChild(option);
                    }

                } else {
                    new PNotify({
                        title: 'Error!',
                        text: 'file empty',
                        type: 'error'
                    });
                }


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }

    $scope.DeleteV2BackupButton = function () {
        $scope.backupLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;

        var url = "/IncrementalBackups/DeleteV2BackupButton";


        data = {
            Selectedwebsite: $scope.selwebsite,
            Selectedrepo: $('#reposelectbox').val(),
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        //alert('Done..........')
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (response.data.status === 1) {
                $scope.backupLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = true;
                $scope.errorMessageBox = true;
                $scope.success = false;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = true;
                new PNotify({
                    title: 'Operation Done!',
                    text: 'Delete Successfully',
                    type: 'sucess'
                });
            } else {
                $scope.backupLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.backupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }
    }
});

