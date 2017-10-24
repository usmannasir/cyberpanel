/**
 * Created by usman on 9/17/17.
 */

//*** Backup site ****//

app.controller('backupWebsiteControl', function($scope,$http,$timeout) {

                // variable to stop updating running status data

                var runningStatus = 1;
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
                            backupCancellationDomain:backupCancellationDomain,
                            fileName:$scope.fileName,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);

                };

                $scope.fetchDetails = function () {

                  getBackupStatus();
                  populateCurrentRecords();
                  $scope.destination = false;

                };


                function getBackupStatus(){

                        $scope.backupLoadingBottom = false;

                        var websiteToBeBacked = $scope.websiteToBeBacked;

                        url = "/backup/backupStatus";

                        var data = {
                            websiteToBeBacked:websiteToBeBacked,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.backupStatus == 1){

                        if(response.data.status != 0){

                            if (runningStatus == 1){
                                $scope.destination = true;
                                $scope.backupButton = true;
                                $scope.runningBackup = false;
                                $scope.cancelButton = false;

                                $scope.fileName = response.data.fileName;
                                $scope.status = response.data.status;
                                $timeout(getBackupStatus, 2000);
                                console.log(response.data.fileName);
                            }
                        }
                        else if(response.data.status === "Aborted, please check CyberPanel main log file." || response.data.status === "Aborted manually."){
                            runningStatus = 0;
                            $timeout.cancel();
                            populateCurrentRecords();
                            $scope.backupLoadingBottom = true;
                            $scope.destination = false;
                            $scope.runningBackup = false;
                            $scope.cancelButton = true;
                            $scope.backupButton = false;
                            $scope.backupLoading = true;
                            $scope.fileName = response.data.fileName;
                            $scope.status = response.data.status;

                        }
                        else{
                            $scope.destination = false;
                            $scope.runningBackup = true;
                            $scope.cancelButton = true;
                            $scope.backupLoading = true;
                            $timeout.cancel();
                            populateCurrentRecords();
                        }


                    }
                    else{
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


                function populateCurrentRecords(){

                        var websiteToBeBacked = $scope.websiteToBeBacked;

                        url = "/backup/getCurrentBackups";

                        var data = {
                            websiteToBeBacked:websiteToBeBacked,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

                        $scope.records = JSON.parse(response.data.data);



                    }
                    else{

                    }

                }
                function cantLoadInitialDatas(response) {



                }

           };



                $scope.createBackup = function(){

                 var websiteToBeBacked = $scope.websiteToBeBacked;
                 $scope.backupLoading = false;



                url = "/backup/submitBackupCreation";

                    var data = {
                        websiteToBeBacked:websiteToBeBacked,
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.metaStatus == 1){

                        console.log("meta generated")
                        getBackupStatus();


                    }
                    else{

                    }

                }
                function cantLoadInitialDatas(response) {


                }

           };


                $scope.deleteBackup = function (id) {


                url = "/backup/deleteBackup";

                    var data = {
                        backupID:id,
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.deleteStatus == 1){

                        populateCurrentRecords();


                    }
                    else{

                    }

                }
                function cantLoadInitialDatas(response) {


                }



            };




});

///** Backup site ends **///



///** Restore site ***//


app.controller('restoreWebsiteControl', function($scope,$http,$timeout) {

    $scope.restoreLoading = true;
    $scope.runningRestore = true;
    $scope.restoreButton=true;
    $scope.restoreFinished = false;
    $scope.couldNotConnect = true;
    $scope.backupError = true;
    $scope.siteExists = true;


    $scope.fetchDetails = function () {
                  $scope.restoreLoading = false;
                  getRestoreStatus();
                };


    function getRestoreStatus(){

                $scope.restoreButton = true;

                var backupFile = $scope.backupFile;

                url = "/backup/restoreStatus";

                var data = {
                        backupFile:backupFile,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.restoreStatus == 1){

                        $scope.restoreLoading = true;


                        if(response.data.status=="Done"){
                            $scope.restoreButton=false;
                            $scope.status = response.data.status;
                            $scope.restoreFinished = true;
                            $scope.running = "Completed";
                            $scope.restoreLoading = true;
                            $timeout.cancel();
                        }
                        else if(response.data.status=="Website already exists"){
                            $scope.siteExists = false;
                            $scope.restoreButton = true;
                            $scope.runningRestore = true;
                            $scope.restoreLoading = true;
                            $scope.running = "Running";
                            $scope.fileName = $scope.backupFile;
                            $timeout.cancel();

                        }
                        else if(response.data.status==0){
                            $scope.running = "Running";
                            $scope.fileName = $scope.backupFile;
                            $scope.restoreButton=false;
                            $scope.restoreLoading = true;
                            $timeout.cancel();
                        }
                        else if(response.data.status == "Not able to create Account and databases, aborting."){

                            $scope.running = "Aborted";
                            $scope.fileName = $scope.backupFile;
                            $scope.restoreLoading = true;
                            $scope.status = response.data.status;
                            $scope.runningRestore = false;
                            $scope.restoreButton=false;
                            $scope.restoreFinished = true;
                            $timeout.cancel();

                        }
                        else if(response.data.status != 0){

                            $scope.running = "Running";
                            $scope.fileName = $scope.backupFile;
                            $scope.restoreLoading = false;
                            $scope.status = response.data.status;
                            $scope.runningRestore = false;
                            $timeout(getRestoreStatus, 2000);

                        }

                    }
                    else{

                    }

                }
                function cantLoadInitialDatas(response) {
                        $scope.couldNotConnect = false;


                }

           };



    $scope.restoreBackup = function(){
        var backupFile = $scope.backupFile;

                url = "/backup/submitRestore";

                var data = {
                        backupFile:backupFile,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    $scope.restoreLoading = true;
                    if(response.data.restoreStatus == 1){
                        $scope.runningRestore = false;
                        $scope.running = "Running";
                        $scope.fileName = $scope.backupFile;
                        $scope.status = "Just Started..";

                        getRestoreStatus();
                    }
                    else{
                            $scope.backupError = false;
                            $scope.errorMessage = response.data.error_message;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = false;

                }

           };


    function createWebsite(){

                var backupFile = $scope.backupFile;

                url = "/websites/CreateWebsiteFromBackup";

                var data = {
                    backupFile:backupFile,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.createWebSiteStatus == 1){
                        getRestoreStatus();
                    }
                    else if(response.data.existsStatus == 1){
                        $scope.backupError = false;
                        $scope.errorMessage = response.data.error_message;
                        $scope.restoreButton = true;
                        $scope.runningRestore = true;
                    }
                    else{
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


app.controller('backupDestinations', function($scope,$http,$timeout) {

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
                            IPAddress : $scope.IPAddress,
                            password : $scope.password,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.destStatus == 1){

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
                            IPAddress : ip,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.connStatus == 1){

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
                            IPAddress : ip,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.delStatus == 1){

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



    function populateCurrentRecords(){

                        url = "/backup/getCurrentBackupDestinations";

                        var data = {
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

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


app.controller('scheduleBackup', function($scope,$http,$timeout) {

    $scope.scheduleBackupLoading = true;
    $scope.canNotAddSchedule = true;
    $scope.scheduleAdded = true;
    $scope.couldNotConnect = true;
    $scope.scheduleFreq = true;
    $scope.scheduleBtn = true;

    populateCurrentRecords();

    $scope.scheduleFreqView = function () {
        $scope.scheduleBackupLoading = true;
        $scope.canNotAddSchedule = true;
        $scope.scheduleAdded = true;
        $scope.couldNotConnect = true;
        $scope.scheduleFreq = false;
        $scope.scheduleBtn = true;

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
                            backupDest : $scope.backupDest,
                            backupFreq : $scope.backupFreq,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.scheduleStatus == 1){

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
                            IPAddress : ip,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.connStatus == 1){

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

    $scope.delSchedule = function (destLoc,frequency) {

        $scope.scheduleBackupLoading = false;
        $scope.canNotAddSchedule = true;
        $scope.scheduleAdded = true;
        $scope.couldNotConnect = true;
        $scope.scheduleFreq = true;
        $scope.scheduleBtn = true;


        url = "/backup/scheduleDelete";


                        var data = {
                            destLoc : destLoc,
                            frequency: frequency,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.delStatus == 1){

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



    function populateCurrentRecords(){

                        url = "/backup/getCurrentBackupSchedules";

                        var data = {
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

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
app.controller('remoteBackupControl', function($scope, $http, $timeout) {
    $scope.backupButton = true;

    $scope.status_success = true;
    $scope.status_danger = true;
    $scope.status_info = true;

    $scope.backupLoading = true;
    $scope.request = true;
    $scope.requestData = "";
    $scope.submitDisable = false;
    $scope.startRestore = true;
    $scope.accountsInRemoteServerTable = true;

    $scope.fetchAccountsFromRemoteServer = function () {

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

            if (response.data.status == 1) {
                $scope.records = JSON.parse(response.data.data);
                $scope.accountsInRemoteServerTable = false;
            }
            else {
                $scope.error_message = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

        }

    };

    $scope.passwordEnter = function() {
        $scope.backupButton = false;
    };

    var seek = 0;
    var backupDir;
    var username = "admin";



    function getBackupStatus(password) {

        url = "/backup/getRemoteTransferStatus";

        var data = {
            ipAddress: $scope.IPAddress,
            seek: seek,
            backupDir: backupDir,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        console.log("Initiating Status with seek: " + seek)

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response.data)

            if (response.data.remoteTransferStatus == 1) {
                seek = response.data.where;
                if (response.data.complete == 1) {
                    $scope.submitDisable = false;
                    $scope.backupLoading = true;

                    $scope.status_danger = true;
                    $scope.status_info = true;
                    $scope.status_success = false;
                    $scope.startRestore = true;
                    $scope.statusBox = "Backup Files Transferred! Require Permission to restore backups";
                    $scope.requestData = $scope.requestData + response.data.logs
                    seek = 0;

                    $scope.startRestore = false;
                } else {
                    $scope.requestData = $scope.requestData + response.data.logs
                    $timeout(getBackupStatus(password), 5000);
                }
            } else {
                if (response.data.error_message == "list index out of range") {
                    $timeout(getBackupStatus(password), 5000);
                } else {
                    $scope.submitDisable = false;
                    $scope.status_danger = false;
                    $scope.status_info = true;
                    $scope.status_success = true;
                    $scope.statusBox = "Unable to Transfer File: " + response.data.error_message;
                }

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.status_danger = false;
            $scope.status_info = true;
            $scope.status_success = true;
            $scope.statusBox = "Unable to connect"
        }
    };

    $scope.submitRemoteBackup = function() {
        $scope.requestData = "";
        $scope.status_success = true;
        $scope.status_danger = true;
        $scope.status_info = true;

        $scope.backupLoading = false;
        $scope.submitDisable = true;
        var IPAddress = $scope.IPAddress;
        var password = $scope.password;

        url = "/backup/submitRemoteBackups";

        var data = {
            ipAddress: IPAddress,
            username: username,
            password: password,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };



        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            console.log(response.data)

            if (response.data.status == 1) {
                $scope.request = false;
                console.log("Backup generated!!")
                backupDir = response.data.dir;
                getBackupStatus(password);
            } else {
                $scope.submitDisable = false;
                $scope.backupLoading = true;

                $scope.status_danger = false;
                $scope.status_info = true;
                $scope.status_success = true;
                $scope.statusBox = "Unable to Transfer File: " + response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.status_danger = false;
            $scope.status_info = true;
            $scope.status_success = true;
            $scope.statusBox = "Unable to connect"
        }

    };

    function getRestStatus() {

        url = "/backup/remoteRestoreStatus";

        var data = {
            seek: seek,
            backupDir: backupDir,
        };
        console.log(data)

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        console.log("Initiating Status with seek: " + seek)

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response.data)

            if (response.data.remoteRestoreStatus == 1) {
                seek = response.data.where;
                console.log(seek);
                if (response.data.complete == 1) {
                    $scope.submitDisable = false;
                    $scope.backupLoading = true;

                    $scope.status_danger = true;
                    $scope.status_info = true;
                    $scope.status_success = false;

                    $scope.statusBox = "Backup Files Restored!";
                    $scope.requestData = $scope.requestData + response.data.logs
                    $scope.startRestore = false;
                } else {
                    $scope.requestData = $scope.requestData + response.data.logs
                    $timeout(getRestStatus(), 5000);
                }
            } else {
                if (response.data.error_message == "list index out of range") {
                    $timeout(getRestStatus(), 5000);
                } else {
                    $scope.submitDisable = false;
                    $scope.status_danger = false;
                    $scope.status_info = true;
                    $scope.status_success = true;
                    $scope.statusBox = "Unable to Restore File: " + response.data.error_message;
                }

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.status_danger = false;
            $scope.status_info = true;
            $scope.status_success = true;
            $scope.statusBox = "Unable to connect"
        }
    };

    $scope.submitBackupRestore = function() {
        $scope.status_success = true;
        $scope.status_danger = true;
        $scope.status_info = false;
        $scope.statusBox = "Restoring Backup";

        $scope.backupLoading = false;
        $scope.submitDisable = true;

        url = "/backup/remoteBackupRestore";

        var data = {
            backupDir: backupDir
        };
        console.log(data)

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        seek = 0

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response.data)

            if (response.data.remoteRestoreStatus == 1) {
                $scope.request = false;
                $scope.backupLoading = false;

                $scope.status_danger = true;
                $scope.status_info = true;
                $scope.status_success = false;
                $scope.statusBox = "Restore in Progress, fetching details"
                getRestStatus();
            } else {
                $scope.submitDisable = false;
                $scope.backupLoading = true;
                $scope.status_danger = false;
                $scope.status_info = true;
                $scope.status_success = true;
                $scope.statusBox = "Unable to Restore Backups: " + response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.status_danger = false;
            $scope.status_info = true;
            $scope.status_success = true;
            $scope.statusBox = "Unable to connect";
        }

    };

});

///** Backup site ends **///