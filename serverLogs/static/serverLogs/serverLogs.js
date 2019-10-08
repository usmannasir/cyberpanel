/**
 * Created by usman on 7/31/17.
 */



/* Java script code to read access log file */


app.controller('readAccessLogs', function($scope,$http) {

                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"access"
                };

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


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"access"
                };

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

    $scope.clearLogs = function(){


                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/clearLogFile";

                var data = {
                    fileName:"/usr/local/lsws/logs/access.log"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.cleanStatus === 1){

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;

                        $scope.logsData = "";



                    }
                    else{

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;


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




/* Java script code to read error log file */


app.controller('readErrorLogs', function($scope,$http) {

                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"error"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.logstatus === 1){

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


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"error"
                };

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

    $scope.clearLogs = function(){


                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/clearLogFile";

                var data = {
                    fileName:"/usr/local/lsws/logs/error.log"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.cleanStatus === 1){

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;

                        $scope.logsData = "";



                    }
                    else{

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;


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


/* Java script code to read ftp log file */


app.controller('readFTPLogs', function($scope,$http) {

                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"ftp"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.logstatus === 1){

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


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"ftp"
                };

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

    $scope.clearLogs = function(){


                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/clearLogFile";

                var data = {
                    fileName:"/var/log/messages"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.cleanStatus === 1){

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;

                        $scope.logsData = "";



                    }
                    else{

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;


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


/* Java script code to read email log file */


app.controller('readEmailLogs', function($scope,$http) {

                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"email"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.logstatus === 1){

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


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"email"
                };

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

    $scope.clearLogs = function(){


                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/clearLogFile";

                var data = {
                    fileName:"/var/log/maillog"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.cleanStatus === 1){

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;

                        $scope.logsData = "";



                    }
                    else{

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;


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


/* Java script code to read modsec audit log file */


app.controller('modSecAuditLogs', function($scope,$http) {

                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"modSec"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.logstatus === 1){

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


                var url = "/serverlogs/getLogsFromFile";

                var data = {
                    type:"modSec"
                };

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
    $scope.clearLogs = function(){


                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


                var url = "/serverlogs/clearLogFile";

                var data = {
                    fileName:"/usr/local/lsws/logs/auditmodsec.log"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {



                    if(response.data.cleanStatus === 1){

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;

                        $scope.logsData = "";



                    }
                    else{

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = true;


                    }


                }
                function cantLoadInitialDatas(response) {

                    $scope.logFileLoading = true;
                    $scope.logsFeteched = true;
                    $scope.couldNotFetchLogs = false;

                }

    };

});



/* Java script code to read modsec audit log ends here */