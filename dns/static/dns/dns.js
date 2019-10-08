/**
 * Created by usman on 8/1/17.
 */


/* Java script code to create NS */

app.controller('createNameserver', function ($scope, $http) {

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
/* Java script code to create NS ends here */


/* Java script code to create DNS Zone */

app.controller('createDNSZone', function ($scope, $http) {

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

/* Java script code to delete DNS Zone */


/* Java script code to create DNS Zone */

app.controller('addModifyDNSRecords', function ($scope, $http) {

    $scope.addRecordsBox = true;
    $scope.currentRecords = true;
    $scope.canNotFetchRecords = true;
    $scope.recordsFetched = true;
    $scope.recordDeleted = true;
    $scope.recordAdded = true;
    $scope.couldNotConnect = true;
    $scope.recordsLoading = true;
    $scope.recordDeleted = true;
    $scope.couldNotDeleteRecords = true;
    $scope.couldNotAddRecord = true;
    $scope.recordValueDefault = false;

    // Hide records boxes
    $(".aaaaRecord").hide();
    $(".cNameRecord").hide();
    $(".mxRecord").hide();
    $(".txtRecord").hide();
    $(".spfRecord").hide();
    $(".nsRecord").hide();
    $(".soaRecord").hide();
    $(".srvRecord").hide();
    $(".caaRecord").hide();


    var currentSelection = "aRecord";
    $("#" + currentSelection).addClass("active");

    $scope.fetchRecordsTabs = function (recordType) {
        $("#" + currentSelection).removeClass("active");
        $("." + currentSelection).hide();
        $scope.recordsLoading = false;
        currentSelection = recordType;
        $("#" + currentSelection).addClass("active");
        $("." + currentSelection).show();
        populateCurrentRecords();
    };


    $scope.fetchRecords = function () {
        $scope.recordsLoading = false;
        $scope.addRecordsBox = false;
        populateCurrentRecords();
    };


    $scope.addDNSRecord = function (type) {

        $scope.recordsLoading = false;


        url = "/dns/addDNSRecord";


        // Record specific values

        var data = {};

        if (type === "MX") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentMX = $scope.recordContentMX;
            data.priority = $scope.priority;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "A") {

            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentA = $scope.recordContentA;
            data.ttl = $scope.ttl;
            data.recordType = type;

        } else if (type === "AAAA") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentAAAA = $scope.recordContentAAAA;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "CNAME") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentCNAME = $scope.recordContentCNAME;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "SPF") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentSPF = $scope.recordContentSPF;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "SOA") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.selectedZone;
            data.recordContentSOA = $scope.recordContentSOA;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "TXT") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentTXT = $scope.recordContentTXT;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "NS") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.selectedZone;
            data.recordContentNS = $scope.recordContentNS;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "SRV") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentSRV = $scope.recordContentSRV;
            data.priority = $scope.priority;
            data.ttl = $scope.ttl;
            data.recordType = type;
        } else if (type === "CAA") {
            data.selectedZone = $scope.selectedZone;
            data.recordName = $scope.recordName;
            data.recordContentCAA = $scope.recordContentCAA;
            data.ttl = $scope.ttl;
            data.recordType = type;
        }


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.add_status === 1) {


                populateCurrentRecords();

                $scope.canNotFetchRecords = true;
                $scope.recordsFetched = false;
                $scope.recordDeleted = true;
                $scope.recordAdded = false;
                $scope.couldNotConnect = true;
                $scope.couldNotAddRecord = true;
                $scope.recordsLoading = true;


            } else {

                $scope.recordsFetched = true;
                $scope.recordDeleted = true;
                $scope.recordAdded = true;
                $scope.couldNotConnect = true;
                $scope.recordsLoading = true;
                $scope.couldNotAddRecord = false;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.addRecordsBox = true;
            $scope.currentRecords = true;
            $scope.canNotFetchRecords = true;
            $scope.recordsFetched = true;
            $scope.recordDeleted = true;
            $scope.recordAdded = true;
            $scope.couldNotConnect = false;
            $scope.couldNotAddRecord = true;


        }

    };


    function populateCurrentRecords() {

        var selectedZone = $scope.selectedZone;

        url = "/dns/getCurrentRecordsForDomain";

        var data = {
            selectedZone: selectedZone,
            currentSelection: currentSelection
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.fetchStatus === 1) {

                $scope.records = JSON.parse(response.data.data);

                $scope.currentRecords = false;
                $scope.canNotFetchRecords = true;
                $scope.recordsFetched = false;
                $scope.recordDeleted = true;
                $scope.recordAdded = true;
                $scope.couldNotConnect = true;
                $scope.recordsLoading = true;
                $scope.couldNotAddRecord = true;

                $scope.domainFeteched = $scope.selectedZone;

            } else {

                $scope.addRecordsBox = true;
                $scope.currentRecords = true;
                $scope.canNotFetchRecords = false;
                $scope.recordsFetched = true;
                $scope.recordDeleted = true;
                $scope.recordAdded = true;
                $scope.couldNotConnect = true;
                $scope.recordsLoading = true;
                $scope.couldNotAddRecord = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.addRecordsBox = true;
            $scope.currentRecords = true;
            $scope.canNotFetchRecords = true;
            $scope.recordsFetched = true;
            $scope.recordDeleted = true;
            $scope.recordAdded = true;
            $scope.couldNotConnect = false;
            $scope.couldNotAddRecord = true;


        }

    };


    $scope.deleteRecord = function (id) {


        var selectedZone = $scope.selectedZone;

        url = "/dns/deleteDNSRecord";

        var data = {
            id: id,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.delete_status == 1) {


                $scope.addRecordsBox = false;
                $scope.currentRecords = false;
                $scope.canNotFetchRecords = true;
                $scope.recordsFetched = true;
                $scope.recordDeleted = false;
                $scope.recordAdded = true;
                $scope.couldNotConnect = true;
                $scope.recordsLoading = true;
                $scope.recordDeleted = true;
                $scope.couldNotDeleteRecords = true;
                $scope.couldNotAddRecord = true;

                populateCurrentRecords();


            } else {

                $scope.addRecordsBox = true;
                $scope.currentRecords = true;
                $scope.canNotFetchRecords = true;
                $scope.recordsFetched = false;
                $scope.recordDeleted = true;
                $scope.recordAdded = true;
                $scope.couldNotConnect = true;
                $scope.recordsLoading = true;
                $scope.recordDeleted = true;
                $scope.couldNotDeleteRecords = false;
                $scope.couldNotAddRecord = true;


                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.addRecordsBox = false;
            $scope.currentRecords = false;
            $scope.canNotFetchRecords = true;
            $scope.recordsFetched = true;
            $scope.recordDeleted = true;
            $scope.recordAdded = true;
            $scope.couldNotConnect = false;
            $scope.recordsLoading = true;
            $scope.recordDeleted = true;
            $scope.couldNotDeleteRecords = true;
            $scope.couldNotAddRecord = true;


        }


    };


});

/* Java script code to delete DNS Zone */


/* Java script code to delete DNS Zone */

app.controller('deleteDNSZone', function ($scope, $http) {

    $scope.deleteZoneButton = true;
    $scope.deleteFailure = true;
    $scope.deleteSuccess = true;
    $scope.couldNotConnect = true;


    $scope.deleteZone = function () {
        $scope.deleteZoneButton = false;
        $scope.deleteFailure = true;
        $scope.deleteSuccess = true;
    };

    $scope.deleteZoneFinal = function () {

        var zoneDomain = $scope.selectedZone;


        url = "/dns/submitZoneDeletion";

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


            if (response.data.delete_status == 1) {

                $scope.deleteZoneButton = true;
                $scope.deleteFailure = true;
                $scope.deleteSuccess = false;
                $scope.couldNotConnect = true;

                $scope.deletedZone = $scope.selectedZone;


            } else {

                $scope.deleteZoneButton = true;
                $scope.deleteFailure = false;
                $scope.deleteSuccess = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.deleteZoneButton = true;
            $scope.deleteFailure = true;
            $scope.deleteSuccess = true;
            $scope.couldNotConnect = false;


        }

    };


});

/* Java script code to delete DNS Zone */


/* Java script code to create NS */

app.controller('configureDefaultNameservers', function ($scope, $http) {


    $scope.cyberPanelLoading = true;

    $scope.saveNSConfigurations = function () {
        $scope.cyberPanelLoading = false;


        url = "/dns/saveNSConfigurations";

        var data = {
            firstNS: $scope.firstNS,
            secondNS: $scope.secondNS,
            thirdNS: $scope.thirdNS,
            forthNS: $scope.forthNS,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Default nameservers saved.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };


});
/* Java script code to create NS ends here */