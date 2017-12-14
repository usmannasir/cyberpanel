/**
 * Created by usman on 7/31/17.
 */



/* Java script code to start/stop litespeed */
app.controller('litespeedStatus', function($scope,$http) {

    $scope.restartorStopLoading = true;
    $scope.actionResult = true;
    $scope.actionResultBad = true;
    $scope.serverStatusCouldNotConnect = true;


    $scope.restartLitespeed = function(){


                $scope.disableReboot = true;
                $scope.disableStop = true;
                $scope.restartorStopLoading = false;




                var url = "/serverstatus/startorstopLitespeed";

                var data = {
                    reboot:1,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    $scope.restartorStopLoading = true;
                    $scope.disableReboot = false;
                    $scope.disableStop = false;

                    if(response.data.reboot == 1){

                        $scope.restartorStopLoading = true;
                        $scope.actionResult = false;
                        $scope.actionResultBad = true;
                        $scope.serverStatusCouldNotConnect = true;

                    }
                    else{

                        $scope.restartorStopLoading = true;
                        $scope.actionResult = true;
                        $scope.actionResultBad = false;
                        $scope.serverStatusCouldNotConnect = true;
                    }


                }
                function cantLoadInitialDatas(response) {
                    $scope.restartorStopLoading = true;
                    $scope.actionResult = true;
                    $scope.actionResultBad = true;
                    $scope.serverStatusCouldNotConnect = false;
                    $scope.disableReboot = false;
                    $scope.disableStop = false;
                }





    };


    $scope.stopLitespeed = function(){


                $scope.disableReboot = true;
                $scope.disableStop = true;
                $scope.restartorStopLoading = false;




                var url = "/serverstatus/startorstopLitespeed";

                var data = {
                    reboot:0,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    $scope.restartorStopLoading = true;
                    $scope.disableReboot = false;
                    $scope.disableStop = false;

                    if(response.data.shutdown == 1){

                        $scope.restartorStopLoading = true;
                        $scope.actionResult = false;
                        $scope.actionResultBad = true;
                        $scope.serverStatusCouldNotConnect = true;

                    }
                    else{

                        $scope.restartorStopLoading = true;
                        $scope.actionResult = true;
                        $scope.actionResultBad = false;
                        $scope.serverStatusCouldNotConnect = true;
                    }


                }
                function cantLoadInitialDatas(response) {
                    $scope.restartorStopLoading = true;
                    $scope.actionResult = true;
                    $scope.actionResultBad = true;
                    $scope.serverStatusCouldNotConnect = false;
                    $scope.disableReboot = false;
                    $scope.disableStop = false;
                }





    };

});



/* Java script code to start/stop litespeed */




/* Java script code to read log file */


app.controller('readCyberCPLogFile', function($scope,$http) {

                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverstatus/getFurtherDataFromLogFile";

                var data = {};

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.logstatus == 1){

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = false;
                        $scope.couldNotFetchLogs = true;

                        $scope.logsData = response.data.logsdata;



                    }
                    else{

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = false;


                    }


                }
                function cantLoadInitialDatas(response) {

                    $scope.logFileLoading = true;
                    $scope.logsFeteched = true;
                    $scope.couldNotFetchLogs = false;

                }




    $scope.fetchLogs = function(){


                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverstatus/getFurtherDataFromLogFile";

                var data = {};

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.logstatus == 1){

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = false;
                        $scope.couldNotFetchLogs = true;

                        $scope.logsData = response.data.logsdata;



                    }
                    else{

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = false;


                    }


                }
                function cantLoadInitialDatas(response) {

                    $scope.logFileLoading = true;
                    $scope.logsFeteched = true;
                    $scope.couldNotFetchLogs = false;

                }





    };

});



/* Java script code to read log file ends here */