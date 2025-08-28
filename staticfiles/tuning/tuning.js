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

                // Initialize with default values to prevent type errors
                $scope.maxConnections = 0;
                $scope.maxSSLConnections = 0;
                $scope.connectionTimeOut = 0;
                $scope.keepAliveTimeOut = 0;
                $scope.cacheSizeInMemory = 0;
                $scope.gzipStatus = "Loading...";
                $scope.gzipCompression = "Enable";

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

                        $scope.maxConnections = parseInt(currentTuningData.maxConnections) || 0;
                        $scope.maxSSLConnections = parseInt(currentTuningData.maxSSLConnections) || 0;
                        $scope.connectionTimeOut = parseInt(currentTuningData.connTimeout) || 0;
                        $scope.keepAliveTimeOut = parseInt(currentTuningData.keepAliveTimeout) || 0;
                        $scope.cacheSizeInMemory = parseInt(currentTuningData.totalInMemCacheSize) || 0;

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

                    var maxConn = parseInt($scope.maxConnections) || 0;
                    var maxSSLConn = parseInt($scope.maxSSLConnections) || 0;
                    var connTime = parseInt($scope.connectionTimeOut) || 0;
                    var keepAlive = parseInt($scope.keepAliveTimeOut) || 0;
                    var inMemCache = parseInt($scope.cacheSizeInMemory) || 0;
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
                
                // Initialize persistConn with a default value
                $scope.persistConn = 'Disable';



                $scope.fetchPHPDetails = function(){
                    
                    // Check if domainSelection is valid before making the API call
                    if (!$scope.domainSelection || $scope.domainSelection === '') {
                        // Don't make the API call if no domain is selected
                        return;
                    }

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


                            if (phpData.persistConn == "1") {
                                $scope.persistConn = "Enable";
                                $scope.persistStatus = "Enabled";
                            }
                            else {
                                $scope.persistConn = "Disable";
                                $scope.persistStatus = "Disabled";
                            }

                            $scope.hideDetails = false;


                        }


                    }

                    function cantLoadInitialDatas(response) {
                        $scope.errorMessage = response.data.error_message;
                        $("#tunePHPLoading").hide();
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