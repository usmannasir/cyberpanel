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


/* Java script code to read log file ends here */

/* Services */

app.controller('servicesManager', function($scope,$http) {

           $scope.services = false;
           $scope.btnDisable = false;
           $scope.actionLoader = false;

           function getServiceStatus(){
                $scope.btnDisable = true;

                url = "/serverstatus/servicesStatus";

                $http.post(url).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.status.litespeed) {
                        $scope.olsStatus = "Running";
                        $scope.olsStats = true;
                        $scope.olsStart = false;
                        $scope.olsStop = true;
                        $scope.olsMem = Math.round(parseInt(response.data.memUsage.litespeed) / 1048576) + " MB";
                    }
                    else {
                        $scope.olsStatus = "Stopped";
                        $scope.olsStats = false;
                        $scope.olsStart = true;
                        $scope.olsStop = false;
                    }

                    // Update SQL stats

                    if (response.data.status.mysql) {
                        $scope.sqlStatus = "Running";
                        $scope.sqlStats = true;
                        $scope.sqlStart = false;
                        $scope.sqlStop = true;
                        $scope.sqlMem = Math.round(parseInt(response.data.memUsage.mysql) / 1048576) + " MB";
                    }
                    else {
                        $scope.sqlStatus = "Stopped";
                        $scope.sqlStats = false;
                        $scope.sqlStart = true;
                        $scope.sqlStop = false;
                    }

                    // Update DNS stats

                    if (response.data.status.powerdns) {
                        $scope.dnsStatus = "Running";
                        $scope.dnsStats = true;
                        $scope.dnsStart = false;
                        $scope.dnsStop = true;
                        $scope.dnsMem = Math.round(parseInt(response.data.memUsage.powerdns) / 1048576) + " MB";
                    }
                    else {
                        $scope.dnsStatus = "Stopped";
                        $scope.dnsStats = false;
                        $scope.dnsStart = true;
                        $scope.dnsStop = false;
                    }

                    // Update FTP stats

                    if (response.data.status.pureftp) {
                        $scope.ftpStatus = "Running";
                        $scope.ftpStats = true;
                        $scope.ftpStart = false;
                        $scope.ftpStop = true;
                        $scope.ftpMem = Math.round(parseInt(response.data.memUsage.pureftp) / 1048576) + " MB";
                    }
                    else {
                        $scope.ftpStatus = "Stopped";
                        $scope.ftpStats = false;
                        $scope.ftpStart = true;
                        $scope.ftpStop = false;
                    }

                    $scope.services = true;

                    $scope.btnDisable = false;

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = true;

                }

           };
           getServiceStatus();

           $scope.serviceAction = function(serviceName, action){
                $scope.ActionProgress = true;
                $scope.btnDisable = true;
                $scope.ActionSuccessfull = false;
                $scope.ActionFailed = false;
                $scope.couldNotConnect = false;
                $scope.actionLoader = true;

                url = "/serverstatus/servicesAction";

                var data = {
                    service:serviceName,
                    action:action
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);

                function ListInitialDatas(response) {
                console.log(response.data);

                    if(response.data.serviceAction == 1){
                        setTimeout(function() {
                            getServiceStatus();
                            $scope.ActionSuccessfull = true;
                            $scope.ActionFailed = false;
                            $scope.couldNotConnect = false;
                            $scope.actionLoader = false;
                            $scope.btnDisable = false;
                        }, 3000);
                    }
                    else{
                        setTimeout(function() {
                            getServiceStatus();
                            $scope.ActionSuccessfull = false;
                            $scope.ActionFailed = true;
                            $scope.couldNotConnect = false;
                            $scope.actionLoader = false;
                            $scope.btnDisable = false;
                        }, 5000);

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.ActionSuccessfull = false;
                    $scope.ActionFailed = false;
                    $scope.couldNotConnect = true;
                    $scope.actionLoader = false;
                    $scope.btnDisable = false;
                }

           }

});
