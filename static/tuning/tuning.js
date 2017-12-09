/**
 * Created by usman on 7/29/17.
 */


/* Java script code for litespeed tuning */


$("#tuningLoading").hide();
$("#canNotFetchTuning").hide();
$("#notTuned").hide();
$("#tuned").hide();
$("#phpDetails").hide();
$("#tunePHPLoading").hide();


app.controller('litespeedTuning', function($scope,$http) {


                url = "/tuning/tuneLitespeed";

                var data = {
                    status:"fetch"
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetch_status == 1){

                        $("#canNotFetchTuning").hide();

                        var currentTuningData = JSON.parse(response.data.tuning_data);

                        $scope.maxConnections = currentTuningData.maxConnections;
                        $scope.maxSSLConnections = currentTuningData.maxSSLConnections;
                        $scope.connectionTimeOut = currentTuningData.connTimeout;
                        $scope.keepAliveTimeOut = currentTuningData.keepAliveTimeout;
                        $scope.cacheSizeInMemory = currentTuningData.totalInMemCacheSize;

                        if(currentTuningData.enableGzipCompress == 1)
                            $scope.gzipStatus = "Enable"
                        else
                            $scope.gzipStatus = "Disabled"


                    }


                }

                function cantLoadInitialDatas(response) {
                    $errMessage = response.data.error_message;
                    $("#canNotFetchTuning").fadeIn();
                }



                $scope.saveTuningSettings = function(){

                    $("#tuningLoading").fadeIn();
                    $('#tuned').hide();

                    var maxConn = $scope.maxConnections;
                    var maxSSLConn = $scope.maxSSLConnections;
                    var connTime = $scope.connectionTimeOut;
                    var keepAlive = $scope.keepAliveTimeOut;
                    var inMemCache = $scope.cacheSizeInMemory;
                    var gzipCompression = $scope.gzipCompression;

                    url = "/tuning/tuneLitespeed";


                    var data = {
                        maxConn:maxConn,
                        maxSSLConn:maxSSLConn,
                        keepAlive:keepAlive,
                        connTime:connTime,
                        inMemCache:inMemCache,
                        gzipCompression:gzipCompression,
                        status:"save"
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };


                    $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.tuneStatus == 1){

                        $("#canNotFetchTuning").hide();
                        $("#tuned").fadeIn();
                        $("#notTuned").hide();
                        $("#tuningLoading").hide();
                    }
                    else{
                        $scope.errMessage = response.data.error_message;
                        $("#notTuned").fadeIn();
                        $("#tuned").hide();
                        $("#tuningLoading").hide();
                    }

                }


                function cantLoadInitialDatas(response) {
                    $scope.errMessage = response.data.error_message;
                    $("#notTuned").fadeIn();
                    $("#tuned").hide();
                    $("#tuningLoading").hide();
                }








                };




});
/* Java script code for litespeed tuning ends here */




/* Java script code for php tuning */

$('#canNotFetch').hide();
$('#successfullyFetched').hide();
$('#successfullyTuned').hide();
$('#canNotTune').hide();

app.controller('tunePHP', function($scope,$http) {

                $scope.hideDetails = true;


                $scope.fetchPHPDetails = function() {

                    $("#tunePHPLoading").fadeIn();


                    url = "/tuning/tunePHP";


                    var data = {
                        status: "fetch",
                        domainSelection: $scope.domainSelection,
                    };

                    var config = {
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    };

                    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


                    function ListInitialDatas(response) {


                        if (response.data.fetch_status == 1) {

                            $("#tunePHPLoading").hide();
                            $('#canNotFetch').hide();
                            $('#successfullyTuned').hide();
                            $('#canNotTune').hide();


                            $('#successfullyFetched').fadeIn();

                            var phpData = JSON.parse(response.data.tuning_data);

                            $scope.initTimeout = Number(phpData.initTimeout);
                            $scope.maxConns = Number(phpData.maxConns);
                            $scope.memSoftLimit = phpData.memSoftLimit;
                            $scope.memHardLimit = phpData.memHardLimit;
                            $scope.procSoftLimit = Number(phpData.procSoftLimit);
                            $scope.procHardLimit = Number(phpData.procHardLimit);


                            if (phpData.persistConn == "1")
                                $scope.persistStatus = "Enabled";
                            else
                                $scope.persistStatus = "Disabled";

                            $scope.hideDetails = false;


                        }


                    }

                    function cantLoadInitialDatas(response) {
                        $errMessage = response.data.error_message;
                        $('#canNotFetch').fadeIn();
                        $('#successfullyFetched').hide();
                        $('#successfullyTuned').hide();
                        $('#canNotTune').hide();
                    }
                };



                $scope.fetchPHPDetails = function(){



                    $("#tunePHPLoading").fadeIn();


                    url = "/tuning/tunePHP";


                    var data = {
                        status: "fetch",
                        domainSelection: $scope.domainSelection,
                    };

                    var config = {
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    };

                    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


                    function ListInitialDatas(response) {


                        if (response.data.fetch_status == 1) {

                            $("#tunePHPLoading").hide();

                            $('#canNotFetch').hide();
                            $('#successfullyTuned').hide();
                            $('#canNotTune').hide();


                            $('#successfullyFetched').fadeIn();

                            var phpData = JSON.parse(response.data.tuning_data);

                            $scope.initTimeout = Number(phpData.initTimeout);
                            $scope.maxConns = Number(phpData.maxConns);
                            $scope.memSoftLimit = phpData.memSoftLimit;
                            $scope.memHardLimit = phpData.memHardLimit;
                            $scope.procSoftLimit = Number(phpData.procSoftLimit);
                            $scope.procHardLimit = Number(phpData.procHardLimit);


                            if (phpData.persistConn == "1")
                                $scope.persistStatus = "Enabled";
                            else
                                $scope.persistStatus = "Disabled";

                            $scope.hideDetails = false;


                        }


                    }

                    function cantLoadInitialDatas(response) {
                        $errMessage = response.data.error_message;
                        $('#canNotFetch').fadeIn();
                        $('#successfullyFetched').hide();
                        $('#successfullyTuned').hide();
                        $('#canNotTune').hide();
                    }
                };




                $scope.tunePHPFunc = function(){



                    $("#tunePHPLoading").fadeIn();


                    var initTimeout = $scope.initTimeout;
                    var maxConns = $scope.maxConns;
                    var memSoftLimit = $scope.memSoftLimit;
                    var memHardLimit = $scope.memHardLimit;
                    var procSoftLimit = $scope.procSoftLimit;
                    var procHardLimit = $scope.procHardLimit;
                    var persistConn = $scope.persistConn;


                    url = "/tuning/tunePHP";


                    var data = {
                        status: "save",
                        domainSelection: $scope.domainSelection,
                        initTimeout: initTimeout,
                        maxConns: maxConns,
                        memSoftLimit: memSoftLimit,
                        memHardLimit: memHardLimit,
                        procSoftLimit: procSoftLimit,
                        procHardLimit: procHardLimit,
                        persistConn: persistConn
                    };

                    var config = {
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    };

                    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


                    function ListInitialDatas(response) {


                        if (response.data.tuneStatus == 1) {

                            $scope.phpVersionTuned = $scope.domainSelection;

                            $("#tunePHPLoading").hide();
                            $('#canNotFetch').hide();
                            $('#successfullyFetched').hide();
                            $('#canNotTune').hide();
                            $('#successfullyTuned').fadeIn();
                            $scope.hideDetails = false;
                        }
                        else{
                            $("#tunePHPLoading").hide();
                            $('#canNotFetch').hide();
                            $('#successfullyFetched').hide();
                            $('#canNotTune').fadeIn();
                            $('#successfullyTuned').hide();
                            $scope.errorMessage = response.data.error_message;
                            $scope.hideDetails = false;
                        }


                    }
                    function cantLoadInitialDatas(response) {
                        $errMessage = response.data.error_message;
                        $("#tunePHPLoading").hide();
                        $('#canNotFetch').hide();
                        $('#successfullyFetched').hide();
                        $('#canNotTune').fadeIn();
                        $('#successfullyTuned').hide();
                    }
                };



});



/* Java script code for php tuning ends here */