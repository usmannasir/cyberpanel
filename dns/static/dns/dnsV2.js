newapp.controller('createNameserverV2', function ($scope, $http) {

    $scope.createNameserverLoading = true;
    $scope.nameserverCreationFailed = true;
    $scope.nameserverCreated = true;
    $scope.couldNotConnect = true;

    $scope.createNameserverFunc = function () {

        var domainForNS = $scope.domainForNS;

        var ns1 = $scope.firstNS;
        var ns2 = $scope.secondNS;

        var firstNSIP = $scope.firstNSIP;
        var secondNSIP = $scope.secondNSIP;


        url = "/dns/NSCreation";

        var data = {
            domainForNS: domainForNS,
            ns1: ns1,
            ns2: ns2,
            firstNSIP: firstNSIP,
            secondNSIP: secondNSIP,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.NSCreation === 1) {
                $scope.createNameserverLoading = true;
                $scope.nameserverCreationFailed = true;
                $scope.nameserverCreated = false;
                $scope.couldNotConnect = true;


                $scope.nameServerTwo = $scope.firstNS;
                $scope.nameServerOne = $scope.secondNS;

            } else {
                $scope.createNameserverLoading = true;
                $scope.nameserverCreationFailed = false;
                $scope.nameserverCreated = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.createNameserverLoading = true;
            $scope.nameserverCreationFailed = true;
            $scope.nameserverCreated = true;
            $scope.couldNotConnect = false;

        }

    };


});
newapp.controller('createDNSZoneV2', function ($scope, $http) {

    $scope.createDNSZoneLoading = true;
    $scope.dnsZoneCreationFailed = true;
    $scope.dnsZoneCreated = true;
    $scope.couldNotConnect = true;

    $scope.createDNSZone = function () {

        var zoneDomain = $scope.zoneDomain;


        url = "/dns/zoneCreation";

        var data = {
            zoneDomain: zoneDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.zoneCreation === 1) {
                $scope.createDNSZoneLoading = true;
                $scope.dnsZoneCreationFailed = true;
                $scope.dnsZoneCreated = false;
                $scope.couldNotConnect = true;

                $scope.zoneDomain = $scope.zoneDomain;

            } else {
                $scope.createDNSZoneLoading = true;
                $scope.dnsZoneCreationFailed = false;
                $scope.dnsZoneCreated = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.createDNSZoneLoading = true;
            $scope.dnsZoneCreationFailed = true;
            $scope.dnsZoneCreated = true;
            $scope.couldNotConnect = false;

        }

    };


});