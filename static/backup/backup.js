/**
 * Created by usman on 9/17/17.
 */

//*** Backup site ****//

app.controller('backupWebsiteControl', function ($scope, $http, $timeout) {

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


//*** Resotre site ends here ***///


///** Backup Destination ***//


app.controller('backupDestinations', function ($scope, $http, $timeout) {

    $scope.destinationLoading = true;
    $scope.connectionFailed = true;
    $scope.connectionSuccess = true;
    $scope.canNotAddDestination = true;
    $scope.destinationAdded = true;
    $scope.couldNotConnect = true;

    populateCurrentRecords();

    $scope.addDestination = function () {

        $scope.destinationLoading = false;
        $scope.connectionFailed = true;
        $scope.connectionSuccess = true;
        $scope.canNotAddDestination = true;
        $scope.destinationAdded = true;
        $scope.couldNotConnect = true;

        url = "/backup/submitDestinationCreation";


        var data = {
            IPAddress: $scope.IPAddress,
            password: $scope.password,
            backupSSHPort: $scope.backupSSHPort,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.destStatus == 1) {

                $scope.destinationLoading = true;
                $scope.connectionFailed = true;
                $scope.connectionSuccess = true;
                $scope.canNotAddDestination = true;
                $scope.destinationAdded = false;
                $scope.couldNotConnect = true;

                populateCurrentRecords();

            }
            else {
                $scope.destinationLoading = true;
                $scope.connectionFailed = true;
                $scope.connectionSuccess = true;
                $scope.canNotAddDestination = false;
                $scope.destinationAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.destinationLoading = true;
            $scope.connectionFailed = true;
            $scope.connectionSuccess = true;
            $scope.canNotAddDestination = true;
            $scope.destinationAdded = true;
            $scope.couldNotConnect = false;
        }

    };

    $scope.checkConn = function (ip) {

        $scope.destinationLoading = false;
        $scope.connectionFailed = true;
        $scope.connectionSuccess = true;
        $scope.canNotAddDestination = true;
        $scope.destinationAdded = true;
        $scope.couldNotConnect = true;

        url = "/backup/getConnectionStatus";


        var data = {
            IPAddress: ip,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.connStatus == 1) {

                $scope.destinationLoading = true;
                $scope.connectionFailed = true;
                $scope.connectionSuccess = false;
                $scope.canNotAddDestination = true;
                $scope.destinationAdded = true;
                $scope.couldNotConnect = true;

                $scope.IPAddress = ip;

            }
            else {
                $scope.destinationLoading = true;
                $scope.connectionFailed = false;
                $scope.connectionSuccess = true;
                $scope.canNotAddDestination = true;
                $scope.destinationAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;
                $scope.IPAddress = ip;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.destinationLoading = true;
            $scope.connectionFailed = true;
            $scope.connectionSuccess = true;
            $scope.canNotAddDestination = true;
            $scope.destinationAdded = true;
            $scope.couldNotConnect = false;
        }

    };

    $scope.delDest = function (ip) {

        $scope.destinationLoading = false;
        $scope.connectionFailed = true;
        $scope.connectionSuccess = true;
        $scope.canNotAddDestination = true;
        $scope.destinationAdded = true;
        $scope.couldNotConnect = true;

        url = "/backup/deleteDestination";


        var data = {
            IPAddress: ip,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.delStatus == 1) {

                $scope.destinationLoading = true;
                $scope.connectionFailed = true;
                $scope.connectionSuccess = true;
                $scope.canNotAddDestination = true;
                $scope.destinationAdded = true;
                $scope.couldNotConnect = true;
                populateCurrentRecords();

                $scope.IPAddress = ip;

            }
            else {
                $scope.destinationLoading = true;
                $scope.connectionFailed = true;
                $scope.connectionSuccess = true;
                $scope.canNotAddDestination = true;
                $scope.destinationAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;
                $scope.IPAddress = ip;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.destinationLoading = true;
            $scope.connectionFailed = true;
            $scope.connectionSuccess = true;
            $scope.canNotAddDestination = true;
            $scope.destinationAdded = true;
            $scope.couldNotConnect = false;
        }

    };


    function populateCurrentRecords() {

        url = "/backup/getCurrentBackupDestinations";

        var data = {};

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
            $scope.couldNotConnect = false;
        }

    };

});


//*** Backup destination ***///


///** Schedule Backup ***//


app.controller('scheduleBackup', function ($scope, $http, $timeout) {

    $scope.scheduleBackupLoading = true;
    $scope.canNotAddSchedule = true;
    $scope.scheduleAdded = true;
    $scope.couldNotConnect = true;
    $scope.scheduleFreq = true;
    $scope.scheduleBtn = true;
    $scope.localPath = true;

    populateCurrentRecords();

    $scope.scheduleFreqView = function () {
        $scope.scheduleBackupLoading = true;
        $scope.canNotAddSchedule = true;
        $scope.scheduleAdded = true;
        $scope.couldNotConnect = true;
        $scope.scheduleFreq = false;
        $scope.scheduleBtn = true;

        if($scope.backupDest === 'Home'){
            $scope.localPath = false;
        }else{
            $scope.localPath = true;
        }

    };

    $scope.scheduleBtnView = function () {
        $scope.scheduleBackupLoading = true;
        $scope.canNotAddSchedule = true;
        $scope.scheduleAdded = true;
        $scope.couldNotConnect = true;
        $scope.scheduleFreq = false;
        $scope.scheduleBtn = false;

    };

    $scope.addSchedule = function () {

        $scope.scheduleBackupLoading = false;
        $scope.canNotAddSchedule = true;
        $scope.scheduleAdded = true;
        $scope.couldNotConnect = true;
        $scope.scheduleFreq = false;
        $scope.scheduleBtn = false;


        url = "/backup/submitBackupSchedule";


        var data = {
            backupDest: $scope.backupDest,
            backupFreq: $scope.backupFreq,
            localPath: $scope.localPathValue
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.scheduleStatus == 1) {

                $scope.scheduleBackupLoading = true;
                $scope.canNotAddSchedule = true;
                $scope.scheduleAdded = false;
                $scope.couldNotConnect = true;
                $scope.scheduleFreq = true;
                $scope.scheduleBtn = true;


                populateCurrentRecords();

            }
            else {

                $scope.scheduleBackupLoading = true;
                $scope.canNotAddSchedule = false;
                $scope.scheduleAdded = true;
                $scope.couldNotConnect = true;
                $scope.scheduleFreq = false;
                $scope.scheduleBtn = false;

                $scope.errorMessage = response.data.error_message;
            }
        }

        function cantLoadInitialDatas(response) {

            $scope.scheduleBackupLoading = true;
            $scope.canNotAddSchedule = true;
            $scope.scheduleAdded = true;
            $scope.couldNotConnect = false;
            $scope.scheduleFreq = false;
            $scope.scheduleBtn = false;

        }

    };

    $scope.checkConn = function (ip) {

        $scope.destinationLoading = false;
        $scope.connectionFailed = true;
        $scope.connectionSuccess = true;
        $scope.canNotAddDestination = true;
        $scope.destinationAdded = true;
        $scope.couldNotConnect = true;

        url = "/backup/getConnectionStatus";


        var data = {
            IPAddress: ip,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.connStatus == 1) {

                $scope.destinationLoading = true;
                $scope.connectionFailed = true;
                $scope.connectionSuccess = false;
                $scope.canNotAddDestination = true;
                $scope.destinationAdded = true;
                $scope.couldNotConnect = true;

                $scope.IPAddress = ip;

            }
            else {
                $scope.destinationLoading = true;
                $scope.connectionFailed = false;
                $scope.connectionSuccess = true;
                $scope.canNotAddDestination = true;
                $scope.destinationAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;
                $scope.IPAddress = ip;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.destinationLoading = true;
            $scope.connectionFailed = true;
            $scope.connectionSuccess = true;
            $scope.canNotAddDestination = true;
            $scope.destinationAdded = true;
            $scope.couldNotConnect = false;
        }

    };

    $scope.delSchedule = function (destLoc, frequency) {

        $scope.scheduleBackupLoading = false;
        $scope.canNotAddSchedule = true;
        $scope.scheduleAdded = true;
        $scope.couldNotConnect = true;
        $scope.scheduleFreq = true;
        $scope.scheduleBtn = true;


        url = "/backup/scheduleDelete";


        var data = {
            destLoc: destLoc,
            frequency: frequency,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.delStatus == 1) {

                $scope.scheduleBackupLoading = true;
                $scope.canNotAddSchedule = true;
                $scope.scheduleAdded = true;
                $scope.couldNotConnect = true;
                $scope.scheduleFreq = true;
                $scope.scheduleBtn = true;


                populateCurrentRecords();


            }
            else {

                $scope.scheduleBackupLoading = true;
                $scope.canNotAddSchedule = true;
                $scope.scheduleAdded = true;
                $scope.couldNotConnect = true;
                $scope.scheduleFreq = true;
                $scope.scheduleBtn = true;
                $scope.errorMessage = response.data.error_message;
            }
        }

        function cantLoadInitialDatas(response) {

            $scope.scheduleBackupLoading = true;
            $scope.canNotAddSchedule = true;
            $scope.scheduleAdded = true;
            $scope.couldNotConnect = false;
            $scope.scheduleFreq = true;
            $scope.scheduleBtn = true;
        }

    };


    function populateCurrentRecords() {

        url = "/backup/getCurrentBackupSchedules";

        var data = {};

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
            $scope.couldNotConnect = false;
        }

    };

});


//*** Schedule Backup ***///


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