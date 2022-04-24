/**
 * Created by usman on 9/17/17.
 */

//*** Backup site ****//

app.controller('backupWebsiteControl', function ($scope, $http, $timeout) {

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
                }
                else {
                    $scope.destination = true;
                    $scope.backupButton = true;
                    $scope.runningBackup = false;
                    $scope.cancelButton = false;

                    $scope.fileName = response.data.fileName;
                    $scope.status = response.data.status;
                    $timeout(getBackupStatus, 2000);

                }
            }
            else {
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


            }
            else {

            }

        }

        function cantLoadInitialDatas(response) {


        }


    };


});

///** Backup site ends **///

///** Restore site ***//

app.controller('restoreWebsiteControl', function ($scope, $http, $timeout) {

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
                }
                else {
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
            }
            else {
                $scope.backupError = false;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;

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
            }
            else if (response.data.existsStatus == 1) {
                $scope.backupError = false;
                $scope.errorMessage = response.data.error_message;
                $scope.restoreButton = true;
                $scope.runningRestore = true;
            }
            else {
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

//*** Restore site ends here ***///

//*** Remote Backup site ****//
app.controller('remoteBackupControl', function ($scope, $http, $timeout) {

    $scope.backupButton = true;
    $scope.backupLoading = true;
    $scope.request = true;
    $scope.requestData = "";
    $scope.submitDisable = false;
    $scope.startRestore = true;

    $scope.accountsInRemoteServerTable = true;
    $scope.transferBoxBtn = true;
    $scope.stopTransferbtn = true;
    $scope.fetchAccountsBtn = false;


    // notifications boxes
    $scope.notificationsBox = true;
    $scope.errorMessage = true;
    $scope.couldNotConnect = true;
    $scope.accountsFetched = true;
    $scope.backupProcessStarted = true;
    $scope.backupCancelled = true;

    // status box

    $scope.backupStatus = true;

    var websitesToBeBacked = [];
    var websitesToBeBackedTemp = [];

    var index = 0;
    var tempTransferDir = "";

    $scope.passwordEnter = function () {
        $scope.backupButton = false;
    };

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

        }
        else {

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
        }
        else {
            websitesToBeBacked = [];
            $scope.webSiteStatus = false;
        }
    };

    $scope.fetchAccountsFromRemoteServer = function () {

        $scope.backupLoading = false;

        // notifications boxes
        $scope.notificationsBox = true;
        $scope.errorMessage = true;
        $scope.couldNotConnect = true;
        $scope.accountsFetched = true;
        $scope.backupProcessStarted = true;
        $scope.backupCancelled = true;

        var IPAddress = $scope.IPAddress;
        var password = $scope.password;

        url = "/backup/submitRemoteBackups";

        var data = {
            ipAddress: IPAddress,
            password: password,
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
                var parsed = JSON.parse(response.data.data);

                for (var j = 0; j < parsed.length; j++) {
                    websitesToBeBackedTemp.push(parsed[j].website);
                }

                $scope.accountsInRemoteServerTable = false;
                $scope.backupLoading = true;

                // enable the transfer/cancel btn

                $scope.transferBoxBtn = false;

                // notifications boxes
                $scope.notificationsBox = false;
                $scope.errorMessage = true;
                $scope.couldNotConnect = true;
                $scope.accountsFetched = false;
                $scope.backupProcessStarted = true;
                $scope.backupCancelled = true;


            }
            else {
                $scope.error_message = response.data.error_message;
                $scope.backupLoading = true;

                // notifications boxes
                $scope.notificationsBox = false;
                $scope.errorMessage = false;
                $scope.couldNotConnect = true;
                $scope.accountsFetched = true;
                $scope.backupProcessStarted = true;
                $scope.backupCancelled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            // notifications boxes

            $scope.notificationsBox = false;
            $scope.errorMessage = true;
            $scope.couldNotConnect = false;
            $scope.accountsFetched = true;
            $scope.backupProcessStarted = true;
            $scope.backupCancelled = true;

        }

    };

    $scope.startTransfer = function () {

        // notifications boxes
        $scope.notificationsBox = true;
        $scope.errorMessage = true;
        $scope.couldNotConnect = true;
        $scope.accountsFetched = true;
        $scope.backupProcessStarted = true;
        $scope.backupCancelled = true;


        if (websitesToBeBacked.length === 0) {
            alert("No websites selected for transfer.");
            return;
        }

        // disable fetch accounts button

        $scope.fetchAccountsBtn = true;
        $scope.backupLoading = false;

        var IPAddress = $scope.IPAddress;
        var password = $scope.password;

        url = "/backup/starRemoteTransfer";

        var data = {
            ipAddress: IPAddress,
            password: password,
            accountsToTransfer: websitesToBeBacked,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.remoteTransferStatus === 1) {
                tempTransferDir = response.data.dir;
                $scope.accountsInRemoteServerTable = true;

                // notifications boxes
                $scope.notificationsBox = false;
                $scope.errorMessage = true;
                $scope.couldNotConnect = true;
                $scope.accountsFetched = true;
                $scope.backupProcessStarted = false;
                $scope.backupCancelled = true;

                // disable transfer button

                $scope.startTransferbtn = true;


                // enable cancel button

                $scope.stopTransferbtn = false;


                getBackupStatus();


            }
            else {

                $scope.error_message = response.data.error_message;
                $scope.backupLoading = true;

                // Notifications box settings

                // notifications boxes
                $scope.notificationsBox = false;
                $scope.errorMessage = false;
                $scope.couldNotConnect = true;
                $scope.accountsFetched = true;
                $scope.backupProcessStarted = true;
                $scope.backupCancelled = true;

            }

        }

        function cantLoadInitialDatas(response) {

            // Notifications box settings

            // notifications boxes
            $scope.notificationsBox = false;
            $scope.errorMessage = true;
            $scope.couldNotConnect = false;
            $scope.accountsFetched = true;
            $scope.backupProcessStarted = true;
            $scope.backupCancelled = true;

        }

    };

    function getBackupStatus(password) {

        url = "/backup/getRemoteTransferStatus";

        var data = {
            password: $scope.password,
            ipAddress: $scope.IPAddress,
            dir: tempTransferDir
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.remoteTransferStatus === 1) {

                if (response.data.backupsSent === 0) {
                    $scope.backupStatus = false;
                    $scope.requestData = response.data.status;
                    $timeout(getBackupStatus, 2000);
                }
                else {
                    $scope.requestData = response.data.status;
                    $timeout.cancel();

                    // Start the restore of remote backups that are transferred to local server

                    remoteBackupRestore();
                }
            }
            else {

                $scope.error_message = response.data.error_message;
                $scope.backupLoading = true;
                $scope.couldNotConnect = true;

                // Notifications box settings

                $scope.couldNotConnect = true;
                $scope.errorMessage = false;
                $scope.accountsFetched = true;
                $scope.notificationsBox = false;
                $timeout.cancel();

            }

        }

        function cantLoadInitialDatas(response) {
            // Notifications box settings

            $scope.couldNotConnect = false;
            $scope.errorMessage = true;
            $scope.accountsFetched = true;
            $scope.notificationsBox = false;
        }
    };

    function remoteBackupRestore() {
        url = "/backup/remoteBackupRestore";

        var data = {
            backupDir: tempTransferDir,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.remoteRestoreStatus === 1) {
                localRestoreStatus();
            }
        }

        function cantLoadInitialDatas(response) {
            // Notifications box settings

            $scope.couldNotConnect = false;
            $scope.errorMessage = true;
            $scope.accountsFetched = true;
            $scope.notificationsBox = false;
            $scope.backupLoading = true;
        }

        ///////////////

    };

    function localRestoreStatus(password) {


        url = "/backup/localRestoreStatus";

        var data = {
            backupDir: tempTransferDir,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.backupProcessStarted = true;

            if (response.data.remoteTransferStatus === 1) {

                if (response.data.complete === 0) {
                    $scope.backupStatus = false;
                    $scope.restoreData = response.data.status;
                    $timeout(localRestoreStatus, 2000);
                }
                else {
                    $scope.restoreData = response.data.status;
                    $timeout.cancel();
                    $scope.backupLoading = true;
                    $scope.startTransferbtn = false;
                }
            }
            else {

                $scope.error_message = response.data.error_message;
                $scope.backupLoading = true;
                $scope.couldNotConnect = true;

                // Notifications box settings

                $scope.couldNotConnect = true;
                $scope.errorMessage = false;
                $scope.accountsFetched = true;
                $scope.notificationsBox = false;

            }

        }

        function cantLoadInitialDatas(response) {
            // Notifications box settings

            $scope.couldNotConnect = false;
            $scope.errorMessage = true;
            $scope.accountsFetched = true;
            $scope.notificationsBox = false;
        }
    };


    function restoreAccounts() {

        url = "/backup/getRemoteTransferStatus";

        var data = {
            password: $scope.password,
            ipAddress: $scope.IPAddress,
            dir: tempTransferDir,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.remoteTransferStatus == 1) {

                if (response.data.backupsSent == 0) {
                    $scope.backupStatus = false;
                    $scope.requestData = response.data.status;
                    $timeout(getBackupStatus, 2000);
                }
                else {
                    $timeout.cancel();
                }
            }

        }

        function cantLoadInitialDatas(response) {
            // Notifications box settings

            $scope.couldNotConnect = false;
            $scope.errorMessage = true;
            $scope.accountsFetched = true;
            $scope.notificationsBox = false;
        }
    };

    $scope.cancelRemoteBackup = function () {


        $scope.backupLoading = false;

        // notifications boxes
        $scope.notificationsBox = true;
        $scope.errorMessage = true;
        $scope.couldNotConnect = true;
        $scope.accountsFetched = true;
        $scope.backupProcessStarted = true;
        $scope.backupCancelled = true;

        var IPAddress = $scope.IPAddress;
        var password = $scope.password;

        url = "/backup/cancelRemoteBackup";

        var data = {
            ipAddress: IPAddress,
            password: password,
            dir: tempTransferDir,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.cancelStatus == 1) {
                $scope.backupLoading = true;

                // notifications boxes
                $scope.notificationsBox = false;
                $scope.errorMessage = true;
                $scope.couldNotConnect = true;
                $scope.accountsFetched = true;
                $scope.backupProcessStarted = true;
                $scope.backupCancelled = false;

                // enable transfer button

                $scope.startTransferbtn = false;

                //disable cancel button

                $scope.stopTransferbtn = true;

                // hide status box

                $scope.backupStatus = true;

                // bring back websites table

                $scope.accountsInRemoteServerTable = false;

                // enable fetch button

                $scope.fetchAccountsBtn = false;


            }
            else {

                $scope.error_message = response.data.error_message;
                $scope.backupLoading = true;

                // notifications boxes

                $scope.notificationsBox = false;
                $scope.errorMessage = false;
                $scope.couldNotConnect = true;
                $scope.accountsFetched = true;
                $scope.backupProcessStarted = true;
                $scope.backupCancelled = true;


            }

        }

        function cantLoadInitialDatas(response) {

            // notifications boxes

            $scope.notificationsBox = false;
            $scope.errorMessage = true;
            $scope.couldNotConnect = false;
            $scope.accountsFetched = true;
            $scope.backupProcessStarted = true;
            $scope.backupCancelled = true;

        }

    };


});

///** Backup site ends **///

//*** Remote Backup site ****//

app.controller('backupLogsScheduled', function ($scope, $http, $timeout) {

    $scope.cyberpanelLoading = true;
    $scope.logDetails = true;

    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.fetchLogs = function () {

        $scope.cyberpanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            logFile: $scope.logFile,
            recordsToShow: $scope.recordsToShow,
            page: $scope.currentPage
        };

        dataurl = "/backup/fetchLogs";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                $scope.logDetails = false;
                $scope.logs = JSON.parse(response.data.logs);
                $scope.pagination = response.data.pagination;
                $scope.jobSuccessSites = response.data.jobSuccessSites;
                $scope.jobFailedSites = response.data.jobFailedSites;
                $scope.location = response.data.location;
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }
        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };


});

///** Backup site ends **///





app.controller('googleDrive', function ($scope, $http) {

    $scope.cyberPanelLoading = true;
    $scope.driveHidden = true;

    $scope.setupAccount = function(){
        window.open("https://platform.cyberpersons.com/gDrive?name=" + $scope.accountName + '&server=' + window.location.href + 'Setup');
    };

    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.fetchWebsites = function () {

        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            selectedAccount: $scope.selectedAccount,
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };


        dataurl = "/backup/fetchgDriveSites";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.driveHidden = false;
                $('#checkret').show()
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.websites = JSON.parse(response.data.websites);
                $scope.pagination = response.data.pagination;
                $scope.currently = response.data.currently;
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
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    $scope.addSite = function () {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedWebsite: $scope.selectedWebsite,
            selectedAccount: $scope.selectedAccount
        };

        dataurl = "/backup/addSitegDrive";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Site successfully added.',
                    type: 'success'
                });
                $scope.fetchWebsites();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.deleteAccount = function () {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedAccount: $scope.selectedAccount
        };

        dataurl = "/backup/deleteAccountgDrive";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Account successfully deleted.',
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
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.changeRetention = function () {
        $scope.cyberPanelLoading = false;
           var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            Retentiontime: $scope.Retentiontime,
            selectedAccount: $scope.selectedAccount,
        };
        dataurl = "/backup/changeFileRetention";


        //console.log(data)

        $http.post(dataurl, data, config).then(fileretention, cantLoadInitialData);

            function fileretention(response) {
                $scope.cyberPanelLoading = true;
                if (response.data.status === 1) {
                    new PNotify({
                        title: 'Success',
                        text: 'Changes successfully applied',
                        type: 'success'
                    });
                    $scope.fetchWebsites();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };


    $scope.changeFrequency = function () {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedAccount: $scope.selectedAccount,
            backupFrequency: $scope.backupFrequency,
            backupRetention: $scope.backupRetention,
        };

        dataurl = "/backup/changeAccountFrequencygDrive";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes successfully applied',
                    type: 'success'
                });
                $scope.fetchWebsites();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.deleteSite = function (website) {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedAccount: $scope.selectedAccount,
            website: website
        };

        dataurl = "/backup/deleteSitegDrive";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Website Deleted.',
                    type: 'success'
                });
                $scope.fetchWebsites();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.currentPageLogs = 1;
    $scope.recordsToShowLogs = 10;

    $scope.fetchLogs = function () {

        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            selectedAccount: $scope.selectedAccount,
            page: $scope.currentPageLogs,
            recordsToShow: $scope.recordsToShowLogs
        };


        dataurl = "/backup/fetchDriveLogs";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.driveHidden = false;
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.logs = JSON.parse(response.data.logs);
                $scope.paginationLogs = response.data.pagination;
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
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }

    };

});

///

app.controller('backupDestinations', function ($scope, $http) {
    $scope.cyberpanelLoading = true;
    $scope.sftpHide = true;
    $scope.localHide = true;

    $scope.fetchDetails = function () {

        if ($scope.destinationType === 'SFTP') {
            $scope.sftpHide = false;
            $scope.localHide = true;
            $scope.populateCurrentRecords();
        } else {
            $scope.sftpHide = true;
            $scope.localHide = false;
            $scope.populateCurrentRecords();
        }
    };

    $scope.populateCurrentRecords = function () {

        $scope.cyberpanelLoading = false;

        url = "/backup/getCurrentBackupDestinations";

        var type = 'SFTP';
        if ($scope.destinationType === 'SFTP') {
            type = 'SFTP';
        } else {
            type = 'local';
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

        url = "/backup/submitDestinationCreation";

        if (type === 'SFTP') {
            var data = {
                type: type,
                name: $scope.name,
                IPAddress: $scope.IPAddress,
                userName: $scope.userName,
                password: $scope.password,
                backupSSHPort: $scope.backupSSHPort,
                path: $scope.path
            };
        } else {
            var data = {
                type: type,
                path: $scope.localPath,
                name: $scope.name
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

    $scope.removeDestination = function (type, nameOrPath) {
        $scope.cyberpanelLoading = false;


        url = "/backup/deleteDestination";

        var data = {
            type: type,
            nameOrPath: nameOrPath,
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

//

app.controller('scheduleBackup', function ($scope, $http, $window) {

    $scope.cyberPanelLoading = true;
    $scope.driveHidden = true;
    $scope.jobsHidden = true;

    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.fetchJobs = function () {

        $scope.cyberPanelLoading = false;
        $scope.jobsHidden = true;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            selectedAccount: $scope.selectedAccount,
        };


        dataurl = "/backup/fetchNormalJobs";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.jobsHidden = false;
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.jobs = response.data.jobs;
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
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    $scope.addSchedule = function () {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedAccount: $scope.selectedAccountAdd,
            name: $scope.name,
            backupFrequency: $scope.backupFrequency,
            backupRetention: $scope.backupRetention,
        };

        dataurl = "/backup/submitBackupSchedule";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Schedule successfully added.',
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
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.fetchWebsites = function () {

        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            selectedAccount: $scope.selectedJob,
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };


        dataurl = "/backup/fetchgNormalSites";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.driveHidden = false;
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.websites = JSON.parse(response.data.websites);
                $scope.pagination = response.data.pagination;
                $scope.currently = response.data.currently;
                $scope.allSites = response.data.allSites;
                $scope.lastRun = response.data.lastRun;
                $scope.currentStatus = response.data.currentStatus;

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
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    $scope.addSite = function (type) {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedWebsite: $scope.selectedWebsite,
            selectedJob: $scope.selectedJob,
            type: type
        };

        dataurl = "/backup/addSiteNormal";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Site successfully added.',
                    type: 'success'
                });
                $scope.fetchWebsites();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.deleteAccount = function () {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedJob: $scope.selectedJob
        };

        dataurl = "/backup/deleteAccountNormal";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Account successfully deleted.',
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

        function cantLoadInitialData(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.changeFrequency = function () {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedJob: $scope.selectedJob,
            backupFrequency: $scope.backupFrequency,
            backupRetention: $scope.backupRetention,
        };

        dataurl = "/backup/changeAccountFrequencyNormal";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes successfully applied',
                    type: 'success'
                });
                $scope.fetchWebsites();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.deleteSite = function (website) {
        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var data = {
            selectedJob: $scope.selectedJob,
            website: website
        };

        dataurl = "/backup/deleteSiteNormal";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Website Deleted.',
                    type: 'success'
                });
                $scope.fetchWebsites();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.currentPageLogs = 1;
    $scope.recordsToShowLogs = 10;

    $scope.fetchLogs = function () {

        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            selectedJob: $scope.selectedJob,
            page: $scope.currentPageLogs,
            recordsToShow: $scope.recordsToShowLogs
        };


        dataurl = "/backup/fetchNormalLogs";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.driveHidden = false;
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.logs = JSON.parse(response.data.logs);
                $scope.paginationLogs = response.data.pagination;
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
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }

    };

});
