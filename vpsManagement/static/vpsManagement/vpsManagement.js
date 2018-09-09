/**
 * Created by usman on 5/18/18.
 */


/* Java script code to create IP Pool */
app.controller('createVPSCTRL', function($scope, $http, $timeout) {

    $scope.tronLoading = true;
    $scope.goBackDisable = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    var statusFile;

    $scope.findIPs = function(){

        $scope.tronLoading = false;


        var url = "/vps/findIPs";

        var data = {
                    hvName: $scope.hvName
                };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
                    $scope.tronLoading = true;
                    if(response.data.status === 1){
                        $scope.ips = JSON.parse(response.data.allIps);
                    }

                }
        function cantLoadInitialDatas(response) {$scope.tronLoading = true;}


    };

    $scope.createVPS = function(){

        $scope.tronLoading = false;
        $scope.goBackDisable = true;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.currentStatus = "Starting creation..";



        var url = "/vps/submitVPSCreation";

        var data = {
                    vpsPackage: $scope.vpsPackage,
                    hvName: $scope.hvName,
                    vpsOwner: $scope.vpsOwner,
                    vpsIP: $scope.vpsIP,
                    hostname: $scope.hostname,
                    rootPassword: $scope.rootPassword,
                    networkSpeed: $scope.networkSpeed,
                    osName: $scope.osName,
                    sshKey: $scope.sshKey
                };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
                    $scope.tronLoading = true;
                    if(response.data.success === 1){
                        statusFile = response.data.tempStatusPath;
                        getCreationStatus();
                    }
                    else
                    {
                        $scope.installationDetailsForm = true;
                        $scope.installationProgress = false;
                        $scope.goBackDisable = false;

                    }
                }
        function cantLoadInitialDatas(response) {
                        $scope.installationDetailsForm = true;
                        $scope.installationProgress = false;
                        $scope.goBackDisable = false;
        }

    };

    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;

    function getCreationStatus(){

                        url = "/websites/installWordpressStatus";

                        var data = {
                            statusFile: statusFile
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.abort === 1){

                        if(response.data.installStatus === 1){

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

                        }
                        else{
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

                    }
                    else{
                        $("#installProgress").css("width", response.data.installationProgress + "%");
                        $scope.installPercentage = response.data.installationProgress;
                        $scope.currentStatus = response.data.currentStatus;
                        $timeout(getCreationStatus,1000);
                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.tronLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = true;
                    $scope.couldNotConnect = false;
                    $scope.goBackDisable = false;

                }


           }

});
/* Java script code to create IP Pool ends here */


/* Java script code to List IP Pools */
app.controller('listVPSCTRL', function($scope,$http) {

    $scope.tronLoading = true;
    $scope.poolCreationFailed = true;
    $scope.poolCreated = true;
    $scope.couldNotConnect = true;

    var currentPageNumber = 1;
    $scope.getFurtherVPS = function(pageNumber){

        currentPageNumber = pageNumber;

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/vps/fetchVPS";

        var data = {page: 1};

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = true;
                        $scope.poolCreated = false;
                        $scope.couldNotConnect = true;
                        $scope.vpsList = JSON.parse(response.data.data);
                        $scope.successMessage = response.data.successMessage;
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = false;
                        $scope.poolCreated = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.poolCreationFailed = true;
                    $scope.poolCreated = true;
                    $scope.couldNotConnect = false;

                }

    };
    $scope.getFurtherVPS(1);

    var vpsIDGlobal;

    $scope.setVPSID = function (vpsID) {
        vpsIDGlobal = vpsID;
    };

    $scope.deleteVPS = function(){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/vps/deleteVPS";

        var data = {vpsID: vpsIDGlobal};

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = true;
                        $scope.poolCreated = false;
                        $scope.couldNotConnect = true;
                        $scope.successMessage = response.data.successMessage;
                        $scope.getFurtherVPS(currentPageNumber);
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = false;
                        $scope.poolCreated = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.poolCreationFailed = true;
                    $scope.poolCreated = true;
                    $scope.couldNotConnect = false;

                }

    };
    $scope.restartVPS = function(){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/vps/restartVPS";

        var data = {vpsID: vpsIDGlobal};

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = true;
                        $scope.poolCreated = false;
                        $scope.couldNotConnect = true;
                        $scope.successMessage = response.data.successMessage;
                        $scope.getFurtherVPS(currentPageNumber);
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = false;
                        $scope.poolCreated = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.poolCreationFailed = true;
                    $scope.poolCreated = true;
                    $scope.couldNotConnect = false;

                }

    };
    $scope.shutdownVPS = function(){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/vps/shutdownVPS";

        var data = {vpsID: vpsIDGlobal};

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = true;
                        $scope.poolCreated = false;
                        $scope.couldNotConnect = true;
                        $scope.successMessage = response.data.successMessage;
                        $scope.getFurtherVPS(currentPageNumber);
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = false;
                        $scope.poolCreated = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.poolCreationFailed = true;
                    $scope.poolCreated = true;
                    $scope.couldNotConnect = false;

                }

    };

});
/* Java script code to List IP Pools ends here */


/* Java script code to Manage VPS */
app.controller('manageVPSCTRL', function($scope, $http, $timeout) {

    $scope.getVPSDetails = function(){


        $scope.tronLoading = false;


        var url = "/vps/getVPSDetails";

        var data = {
            hostName: $("#vpsHostname").text()
        };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    $scope.tronLoading = true;

                    if(response.data.success === 1){

                        $scope.diskUsage = response.data.diskUsage;
                        $scope.sizeInMB = response.data.sizeInMB;
                    }
                    else
                    {
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                          });

                    }
                }
        function cantLoadInitialDatas(response) {
                    new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page',
                            type:'error'
                          });

                }

    };
    $scope.getVPSDetails();

    /// Administrative Tasks

    $scope.tronLoading = true;
    $scope.hostNameBox = true;
    $scope.rootPasswordBox = true;
    $scope.reinstallBox = true;

    $scope.hideAdminTasks = function () {
        $scope.hostNameBox = true;
        $scope.rootPasswordBox = true;
        $scope.reinstallBox = true;
    };

    $scope.showHostnameBox = function () {
        $scope.hostNameBox = false;
        $scope.rootPasswordBox = true;
        $scope.reinstallBox = true;
    };

    $scope.showChangePasswordBox = function () {
        $scope.hostNameBox = true;
        $scope.rootPasswordBox = false;
        $scope.reinstallBox = true;
    };

    $scope.showReinstallBox = function () {
        $scope.hostNameBox = true;
        $scope.rootPasswordBox = true;
        $scope.reinstallBox = false;
    };

    $scope.changeHostname = function(vpsID){

        $scope.tronLoading = false;


        var url = "/vps/changeHostname";

        var data = {
            hostName: $("#vpsHostname").text(),
            newHostname: $scope.newHostname
        };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    $scope.tronLoading = true;

                    if(response.data.success === 1){

                        $scope.successMessage = response.data.successMessage;

                        new PNotify({
                            title: 'Operation Successfull!',
                            text: response.data.successMessage,
                            type:'success'
                          });

                    }
                    else
                    {

                        new PNotify({
                            title: 'Operation failed!',
                            text: response.data.error_message,
                            type:'error'
                          });
                    }
                }
        function cantLoadInitialDatas(response) {

                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Operation failed!',
                            text: "Could not connect to server. Please refresh this page.",
                            type:'error'
                          });


                }

    };
    $scope.changeRootPassword = function(vpsID){

        $scope.tronLoading = false;


        var url = "/vps/changeRootPassword";

        var data = {
            hostName: $("#vpsHostname").text(),
            newPassword: $scope.newPassword
        };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    $scope.tronLoading = true;

                    if(response.data.success === 1){

                        $scope.successMessage = response.data.successMessage;

                        new PNotify({
                            title: 'Operation Successfull!',
                            text: response.data.successMessage,
                            type:'success'
                          });

                    }
                    else
                    {
                        new PNotify({
                            title: 'Operation failed!',
                            text: response.data.error_message,
                            type:'error'
                          });
                    }
                }
        function cantLoadInitialDatas(response) {

                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Operation failed!',
                            text: "Could not connect to server. Please refresh this page.",
                            type:'error'
                          });


                }

    };

    // Re-install

    $scope.goBackDisable = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    var statusFile;

    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus(){

                        url = "/websites/installWordpressStatus";

                        var data = {
                            statusFile: statusFile
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.abort === 1){
                        $scope.tronLoading = true;
                        if(response.data.installStatus === 1){
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

                        }
                        else{
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

                    }
                    else{
                        $("#installProgress").css("width", response.data.installationProgress + "%");
                        $scope.installPercentage = response.data.installationProgress;
                        $scope.currentStatus = response.data.currentStatus;
                        $timeout(getCreationStatus,1000);
                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.tronLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = true;
                    $scope.couldNotConnect = false;
                    $scope.goBackDisable = false;

                }


           }

    $scope.reinstallOS = function(){

        $scope.tronLoading = false;
        $scope.goBackDisable = true;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.currentStatus = "Starting re-install..";


        var url = "/vps/reInstallOS";

        var data = {
            hostname: $("#vpsHostname").text(),
            osName : $scope.osName,
            sshKey : $scope.sshKey,
            rootPassword: $scope.reinstallPassword
        };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
                    $scope.tronLoading = true;
                    if(response.data.success === 1){
                        statusFile = response.data.tempStatusPath;
                        getCreationStatus();
                    }
                    else
                    {
                        $scope.installationDetailsForm = true;
                        $scope.installationProgress = false;
                        $scope.goBackDisable = false;
                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;
                }

    };

    $scope.restartVPS = function(vpsID){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/vps/restartVPS";

        var data = {vpsID: vpsID};

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = true;
                        $scope.poolCreated = false;
                        $scope.couldNotConnect = true;
                        $scope.successMessage = response.data.successMessage;
                        $scope.getFurtherVPS(currentPageNumber);
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = false;
                        $scope.poolCreated = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.poolCreationFailed = true;
                    $scope.poolCreated = true;
                    $scope.couldNotConnect = false;

                }

    };
    $scope.shutdownVPS = function(vpsID){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/vps/shutdownVPS";

        var data = {vpsID: vpsID};

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = true;
                        $scope.poolCreated = false;
                        $scope.couldNotConnect = true;
                        $scope.successMessage = response.data.successMessage;
                        $scope.getFurtherVPS(currentPageNumber);
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = false;
                        $scope.poolCreated = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.poolCreationFailed = true;
                    $scope.poolCreated = true;
                    $scope.couldNotConnect = false;

                }

    };

    $scope.setupVNC = function(){

        $scope.tronLoading = false;

        var url = "/vps/startWebsocketServer";

        var data = {hostname: $("#vpsHostname").text()};

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
                    $scope.tronLoading = true;
                    if(response.data.success === 1){
                        window.open(response.data.finalURL);
                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                }

    };

});
/* Java script code to Manage VPS ends here */

app.controller('sshKeys', function($scope,$http) {

           $scope.tronLoading = true;
           $scope.keyBox = true;

           $scope.addKey = function(){
                $scope.showKeyBox = true;
                $scope.keyBox = false;
           };

           populateCurrentKeys();
           function populateCurrentKeys(){

                        url = "/vps/fetchKeys";

                        var data = {};

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.status === 1){
                        $scope.records = JSON.parse(response.data.sshKeys);
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = false;

                }


           }
           $scope.deleteKey =  function(keyName){

                        $scope.tronLoading = false;

                        url = "/vps/deleteKey";

                        var data = {
                            keyName:keyName
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.status === 1){
                        $scope.tronLoading = true;
                        populateCurrentKeys();
                        new PNotify({
                            title: 'Success!',
                            text: 'Key successfully deleted.',
                            type:'success'
                          });
                        $scope.showKeyBox = false;
                        $scope.keyBox = true;
                    }
                    else{
                        $scope.tronLoading = true;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.erroMessage,
                            type:'error'
                          });
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });

                }


           };
           $scope.saveKey =  function(){

                        $scope.tronLoading = false;

                        url = "/vps/addKey";

                        var data = {
                            keyName : $scope.keyName,
                            keyData: $scope.keyData
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };


                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.status === 1){
                        $scope.tronLoading = true;
                        populateCurrentKeys();
                        new PNotify({
                            title: 'Success!',
                            text: 'Key successfully added.',
                            type:'success'
                          });
                        $scope.showKeyBox = false;
                        $scope.keyBox = true;
                    }
                    else{
                        $scope.tronLoading = true;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.erroMessage,
                            type:'error'
                          });
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });

                }

           }

});