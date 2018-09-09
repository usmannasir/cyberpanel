/**
 * Created by usman on 9/5/17.
 */



/* Java script code for HV */

app.controller('addHyperVisorCTRL', function($scope,$http) {

           $scope.tronLoading = true;

           $scope.submitCreateHyperVisor = function(){

                        $scope.rulesLoading = false;

                        url = "/hv/submitCreateHyperVisor";

                        var data = {
                            name : $scope.name,
                            serverOwner : $scope.serverOwner,
                            serverIP : $scope.serverIP,
                            userName : $scope.userName,
                            password : $scope.password,
                            storagePath : $scope.storagePath
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

                        new PNotify({
                            title: 'Success!',
                            text: 'Server successfully added.',
                            type:'success'
                          });

                    }
                    else{

                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });
                }

           };





});

/* Java script code for HV */

/* Java script code for List HVs */

app.controller('listHVCTRL', function($scope,$http) {

           $scope.tronLoading = true;
           $scope.hvTable = false;
           $scope.hvForm = true;

           $scope.submitCreateHyperVisor = function(){

                        $scope.tronLoading = false;

                        url = "/hv/submitCreateHyperVisor";

                        var data = {
                            name : $scope.name,
                            serverOwner : $scope.serverOwner,
                            serverIP : $scope.serverIP,
                            userName : $scope.userName,
                            password : $scope.password,
                            storagePath : $scope.storagePath
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

                        new PNotify({
                            title: 'Success!',
                            text: 'Server successfully added.',
                            type:'success'
                          });

                    }
                    else{

                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });
                }

           };
           $scope.manageServer = function (hypervisorName) {
               $scope.hvTable = true;
               $scope.hvForm = false;
               $scope.name = hypervisorName;
           };
           $scope.submitHyperVisorChanges = function(){

                        $scope.tronLoading = false;

                        url = "/hv/submitHyperVisorChanges";

                        var data = {
                            name : $scope.name,
                            serverOwner : $scope.serverOwner,
                            userName : $scope.userName,
                            password : $scope.password,
                            storagePath : $scope.storagePath
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

                        new PNotify({
                            title: 'Success!',
                            text: 'Changes successfully saved.',
                            type:'success'
                          });

                    }
                    else{

                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });
                }

           };
           $scope.hidehvForm = function (hypervisorIP) {
               $scope.hvTable = false;
               $scope.hvForm = true;
           };
           $scope.setValues = function (hypervisorIP, action) {
               $scope.hypervisorIP = hypervisorIP;
               $scope.action = action;
           };

           $scope.controlCommands = function(){

                        $scope.tronLoading = false;

                        url = "/hv/controlCommands";

                        var data = {
                            hypervisorIP : $scope.hypervisorIP,
                            action : $scope.action
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

                        new PNotify({
                            title: 'Success!',
                            text: 'Changes successfully saved.',
                            type:'success'
                          });

                    }
                    else{

                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });
                }

           };





});

/* Java script code for List HVs */

