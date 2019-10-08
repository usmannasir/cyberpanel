/**
 * Created by usman on 6/22/18.
 */


/* Java script code */

app.controller('powerDNS', function ($scope, $http, $timeout, $window) {

    $scope.pdnsLoading = true;
    $scope.failedToFetch = true;
    $scope.couldNotConnect = true;
    $scope.changesApplied = true;
    $scope.slaveIPs = true;
    $scope.masterServerHD  = true;

    var pdnsStatus = false;


    $('#pdnsStatus').change(function () {
        pdnsStatus = $(this).prop('checked');
    });

    fetchPDNSStatus('powerdns');
    function fetchPDNSStatus(service) {

        $scope.pdnsLoading = false;

        $('#pdnsStatus').bootstrapToggle('off');

        url = "/manageservices/fetchStatus";

        var data = {
            'service': service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.pdnsLoading = true;

            if (response.data.status === 1) {

                if (response.data.installCheck === 1) {
                    $('#pdnsStatus').bootstrapToggle('on');
                }

                $scope.slaveIPData = response.data.slaveIPData;

            } else {
                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.pdnsLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }

    }

    $scope.saveStatus = function (service) {

        $scope.pdnsLoading = false;
        $scope.failedToFetch = true;
        $scope.couldNotConnect = true;
        $scope.changesApplied = true;


        url = "/manageservices/saveStatus";

        if (service === 'powerdns') {
            var data = {
                status: pdnsStatus,
                service: service,
                dnsMode: $scope.dnsMode,
                slaveServerNS: $scope.slaveServerNS,
                masterServerIP: $scope.masterServerIP,
                slaveServer: $scope.slaveServer,
                slaveServerIP: $scope.slaveServerIP,
                slaveServer2: $scope.slaveServer2,
                slaveServerIP2: $scope.slaveServerIP2,
                slaveServer3: $scope.slaveServer3,
                slaveServerIP3: $scope.slaveServerIP3,
            };
        }else {
            var data = {
                status: pdnsStatus,
                service: service
            };
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.pdnsLoading = true;

            if (response.data.status === 1) {

                $scope.failedToFetch = true;
                $scope.couldNotConnect = true;
                $scope.changesApplied = false;

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.policyServerLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }


    };

    $scope.modeChange = function () {
        if ($scope.dnsMode === 'MASTER') {
            $scope.slaveIPs = false;
            $scope.masterServerHD  = true;

        } else if($scope.dnsMode == 'SLAVE') {
            $scope.slaveIPs = true;
            $scope.masterServerHD  = false;
        }else{
            $scope.slaveIPs = true;
            $scope.masterServerHD  = true;
        }
    }

});


/* Java script code */



/* Java script code */

app.controller('postfix', function ($scope, $http, $timeout, $window) {

    $scope.serviceLoading = true;
    $scope.failedToFetch = true;
    $scope.couldNotConnect = true;
    $scope.changesApplied = true;


    var serviceStatus = false;


    $('#serviceStatus').change(function () {
        serviceStatus = $(this).prop('checked');
    });

    fetchPDNSStatus('postfix');
    function fetchPDNSStatus(service) {

        $scope.serviceLoading = false;

        $('#serviceStatus').bootstrapToggle('off');

        url = "/manageservices/fetchStatus";

        var data = {
            'service': service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                if (response.data.installCheck === 1) {
                    $('#serviceStatus').bootstrapToggle('on');
                }

            } else {
                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }

    }


    $scope.saveStatus = function (service) {

        $scope.serviceLoading = false;
        $scope.failedToFetch = true;
        $scope.couldNotConnect = true;
        $scope.changesApplied = true;


        url = "/manageservices/saveStatus";

        var data = {
            status: serviceStatus,
            service: service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                $scope.failedToFetch = true;
                $scope.couldNotConnect = true;
                $scope.changesApplied = false;

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }


    };

});

/* Java script code */


/* Java script code */

app.controller('pureFTPD', function ($scope, $http, $timeout, $window) {

    $scope.serviceLoading = true;
    $scope.failedToFetch = true;
    $scope.couldNotConnect = true;
    $scope.changesApplied = true;


    var serviceStatus = false;


    $('#serviceStatus').change(function () {
        serviceStatus = $(this).prop('checked');
    });

    fetchPDNSStatus('pureftpd');
    function fetchPDNSStatus(service) {

        $scope.serviceLoading = false;

        $('#serviceStatus').bootstrapToggle('off');

        url = "/manageservices/fetchStatus";

        var data = {
            'service': service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                if (response.data.installCheck === 1) {
                    $('#serviceStatus').bootstrapToggle('on');
                }

            } else {
                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }

    }


    $scope.saveStatus = function (service) {

        $scope.serviceLoading = false;
        $scope.failedToFetch = true;
        $scope.couldNotConnect = true;
        $scope.changesApplied = true;


        url = "/manageservices/saveStatus";

        var data = {
            status: serviceStatus,
            service: service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                $scope.failedToFetch = true;
                $scope.couldNotConnect = true;
                $scope.changesApplied = false;

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }


    };

});

/* Java script code */