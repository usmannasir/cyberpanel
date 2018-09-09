/**
 * Created by usman on 5/18/18.
 */


/* Java script code to create IP Pool */
app.controller('createIPPoolCTRL', function($scope,$http) {

    $scope.tronLoading = true;
    $scope.poolCreationFailed = true;
    $scope.poolCreated = true;
    $scope.couldNotConnect = true;


    $scope.createIPPool = function(){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/ip/submitIPPoolCreation";

        var data = {
                    poolName: $scope.poolName,
                    poolGateway: $scope.poolGateway,
                    poolNetmask: $scope.poolNetmask,
                    poolStartingIP: $scope.poolStartingIP,
                    poolEndingIP: $scope.poolEndingIP,
                    hvName: $scope.hvName
                };

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
/* Java script code to create IP Pool ends here */


/* Java script code to List IP Pools */
app.controller('listIPPoolsCTRL', function($scope,$http) {

    $scope.tronLoading = true;
    $scope.poolCreationFailed = true;
    $scope.poolCreated = true;
    $scope.couldNotConnect = true;

    // Special

    $scope.currentRecords = true;
    $scope.macBox = true;


    $scope.fetchRecords = function(){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/ip/fetchIPsInPool";

        var data = {
                    poolName: $scope.poolName
                };

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

                        //

                        $scope.currentRecords = false;

                        $scope.successMessage = response.data.successMessage;
                        $scope.records = JSON.parse(response.data.data);
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

    $scope.changeMac = function(ipAddr){

        // Special

        $scope.macIP = ipAddr;
        $scope.macBox = false;
    };

    $scope.changeMacFinal = function(){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/ip/submitNewMac";

        var data = {
                    macIP: $scope.macIP,
                    newMac: $scope.newMac
                };

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

                        //

                        $scope.currentRecords = false;

                        $scope.successMessage = response.data.successMessage;
                        $scope.fetchRecords();
                        $scope.macBox = true;
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

    $scope.deleteIP = function(id){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/ip/deleteIP";

        var data = {
                    id: id
                };

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

                        //

                        $scope.currentRecords = false;
                        $scope.successMessage = response.data.successMessage;
                        $scope.fetchRecords();

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

    $scope.deletePool = function(){

        $scope.tronLoading = false;

        var url = "/ip/deletePool";

        var data = {
                    poolName: $scope.poolName
                };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;

                        //

                        new PNotify({
                            title: 'Success!',
                            text: 'Pool successfully deleted.',
                            type:'success'
                          });
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
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

    $scope.addSingleIP = function(){

        $scope.tronLoading = false;

        var url = "/ip/addSingleIP";

        var data = {
                    poolName: $scope.poolName,
                    newIP: $scope.newIP
                };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;

                        //

                        new PNotify({
                            title: 'Success!',
                            text: 'IP successfully added.',
                            type:'success'
                          });
                        $scope.fetchRecords();
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
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

    $scope.addMultipleIP = function(){

        $scope.tronLoading = false;

        var url = "/ip/addMultipleIP";

        var data = {
                    poolName: $scope.poolName,
                    startingIP: $scope.startingIP,
                    endingIP: $scope.endingIP
                };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;

                        //

                        new PNotify({
                            title: 'Success!',
                            text: 'IP successfully added.',
                            type:'success'
                          });
                        $scope.fetchRecords();
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
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


});
/* Java script code to List IP Pools ends here */