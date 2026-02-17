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

        var globalID = null;
        var nameNow = null;
        var ttlNow = null;
        var contentNow = null;
        var priorityNow = null;


        $scope.setupContent = function (id, type, content) {
            if (globalID === null) {
                globalID = id;
            } else {
                if (globalID !== id) {
                    globalID = id;
                    nameNow = null;
                    ttlNow = null;
                    contentNow = null;
                    priorityNow = null;
                }
            }

            if (type === 'name') {
                nameNow = content;
            } else if (type === 'ttl') {
                ttlNow = content;
            } else if (type === 'content') {
                contentNow = content;
            } else if (type === 'priority') {
                priorityNow = content;
            }
        };

        $scope.saveNow = function (id) {

            if (id !== globalID) {
                alert('This record is not changed');
                return;
            }
            $scope.recordsLoading = false;

            url = "/dns/updateRecord";

            var data = {
                selectedZone: $scope.selectedZone,
                id: globalID,
                nameNow: nameNow,
                ttlNow: ttlNow,
                contentNow: contentNow,
                priorityNow: priorityNow,
            };

            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


            function ListInitialDatas(response) {
                $scope.recordsLoading = true;

                if (response.data.status === 1) {

                    new PNotify({
                        title: 'Success!',
                        text: 'Record updated.',
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
                $scope.recordsLoading = true;
                new PNotify({
                    title: 'Operation Failed!',
                    text: 'Could not connect to server, please refresh this page',
                    type: 'error'
                });
            }
        };

    $scope.confirmDeleteRecord = function (record) {
        var msg = 'Delete DNS record?\n\nName: ' + (record.name || '') + '\nType: ' + (record.type || '') + '\nValue: ' + (record.content || '');
        if (!$window.confirm(msg)) {
            return;
        }
        var zone = $scope.selectedZone;
        if (!zone) {
            return;
        }
        if (!$scope.cfDeletedBackup[zone]) {
            $scope.cfDeletedBackup[zone] = [];
        }
        $scope.cfDeletedBackup[zone].push({
            type: record.type,
            name: record.name,
            content: record.content,
            priority: parseInt(record.priority, 10) || 0,
            ttl: record.ttlNum || record.ttl || 3600,
            proxy: record.proxy,
            proxiable: record.proxiable !== false
        });
        $scope.deleteRecord(record.id);
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


    }
);

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

/* Java script code for CloudFlare */

app.directive('cfImportFile', function () {
    return {
        link: function (scope, element) {
            element.on('change', function (ev) {
                var files = ev.target && ev.target.files;
                if (files && files.length && scope.onImportFile) {
                    scope.$apply(function () {
                        scope.onImportFile(files);
                    });
                }
                ev.target.value = '';
            });
        }
    };
});

app.controller('addModifyDNSRecordsCloudFlare', function ($scope, $http, $window) {

    $scope.saveCFConfigs = function () {

        $scope.recordsLoading = false;

        url = "/dns/saveCFConfigs";

        var data = {
            cfEmail: $scope.cfEmail,
            cfToken: $scope.cfToken,
            cfSync: $scope.cfSync,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.recordsLoading = true;

            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success',
                    text: 'Changes successfully saved.',
                    type: 'success'
                });
                $window.location.reload();
            } else {


                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {
            $scope.recordsLoading = true;

            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });


        }


    };


    ////

    $scope.addRecordsBox = true;
    $scope.currentRecords = true;
    $scope.canNotFetchRecords = true;
    $scope.recordsFetched = true;
    $scope.recordDeleted = true;
    $scope.recordAdded = true;
    $scope.couldNotConnect = true;
    $scope.recordsLoading = true;
    $scope.loadingRecords = true;
    $scope.recordDeleted = true;
    $scope.couldNotDeleteRecords = true;
    $scope.couldNotAddRecord = true;
    $scope.recordValueDefault = false;
    $scope.records = [];
    $scope.cfDeletedBackup = {};
    $scope.exportLoading = false;
    $scope.clearAllLoading = false;
    $scope.restoreLoading = false;
    $scope.staleRecords = [];
    $scope.staleModalVisible = false;
    $scope.staleLoading = false;

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


        url = "/dns/addDNSRecordCloudFlare";


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
        $scope.loadingRecords = true;
        var selectedZone = $scope.selectedZone;

        url = "/dns/getCurrentRecordsForDomainCloudFlare";

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
            $scope.loadingRecords = false;
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
                $scope.records = [];

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.loadingRecords = false;
            $scope.addRecordsBox = true;
            $scope.currentRecords = true;
            $scope.canNotFetchRecords = true;
            $scope.recordsFetched = true;
            $scope.recordDeleted = true;
            $scope.recordAdded = true;
            $scope.couldNotConnect = false;
            $scope.couldNotAddRecord = true;
            $scope.records = [];


        }

    }

    $scope.deleteRecord = function (id) {


        var selectedZone = $scope.selectedZone;

        url = "/dns/deleteDNSRecordCloudFlare";

        var data = {
            selectedZone: selectedZone,
            id: id
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

    $scope.hasBackupForZone = function () {
        var zone = $scope.selectedZone;
        if (!zone) return false;
        var list = $scope.cfDeletedBackup[zone];
        return list && list.length > 0;
    };

    $scope.confirmClearAll = function () {
        var zone = $scope.selectedZone;
        if (!zone) return;
        var msg1 = 'This will remove ALL DNS records for this zone in CloudFlare. This action cannot be undone on CloudFlare.\n\nA local copy will be kept so you can use Restore.\n\nContinue?';
        if (!$window.confirm(msg1)) return;
        var msg2 = 'Type the zone name below to confirm:\n\n' + zone;
        var typed = $window.prompt(msg2);
        if (typed === null) return;
        if (typed.trim() !== zone) {
            new PNotify({ title: 'Cancelled', text: 'Zone name did not match. No records were deleted.', type: 'warning' });
            return;
        }
        $scope.clearAllLoading = true;
        url = '/dns/clearAllDNSRecordsCloudFlare';
        var data = { selectedZone: zone };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function (response) {
            $scope.clearAllLoading = false;
            if (response.data.delete_status === 1 && response.data.deleted_records) {
                $scope.cfDeletedBackup[zone] = response.data.deleted_records;
                $scope.canNotFetchRecords = true;
                $scope.recordsFetched = false;
                $scope.recordDeleted = false;
                populateCurrentRecords();
                new PNotify({ title: 'Done', text: 'All DNS records were deleted. Use Restore to undo.', type: 'success' });
            } else {
                $scope.errorMessage = response.data.error_message || 'Clear all failed';
                new PNotify({ title: 'Error', text: $scope.errorMessage, type: 'error' });
            }
        }, function () {
            $scope.clearAllLoading = false;
            new PNotify({ title: 'Error', text: 'Could not connect to server.', type: 'error' });
        });
    };

    $scope.restoreFromBackup = function () {
        var zone = $scope.selectedZone;
        var list = $scope.cfDeletedBackup[zone];
        if (!zone || !list || list.length === 0) return;
        $scope.restoreLoading = true;
        url = '/dns/importDNSRecordsCloudFlare';
        var data = { selectedZone: zone, records: list };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function (response) {
            $scope.restoreLoading = false;
            if (response.data.import_status === 1) {
                $scope.cfDeletedBackup[zone] = [];
                populateCurrentRecords();
                var failed = response.data.failed || [];
                var msg = response.data.imported + ' record(s) restored.';
                if (failed.length) msg += ' ' + failed.length + ' failed.';
                new PNotify({ title: 'Restore done', text: msg, type: failed.length ? 'warning' : 'success' });
            } else {
                new PNotify({ title: 'Error', text: response.data.error_message || 'Restore failed', type: 'error' });
            }
        }, function () {
            $scope.restoreLoading = false;
            new PNotify({ title: 'Error', text: 'Could not connect to server.', type: 'error' });
        });
    };

    $scope.exportRecords = function () {
        var zone = $scope.selectedZone;
        if (!zone) return;
        $scope.exportLoading = true;
        url = '/dns/getExportRecordsCloudFlare';
        var data = { selectedZone: zone };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function (response) {
            $scope.exportLoading = false;
            if (response.data.fetchStatus === 1 && response.data.data) {
                var arr = typeof response.data.data === 'string' ? JSON.parse(response.data.data) : response.data.data;
                var blob = new Blob([JSON.stringify(arr, null, 2)], { type: 'application/json' });
                var a = document.createElement('a');
                a.href = (window.URL || window.webkitURL).createObjectURL(blob);
                a.download = 'dns-records-' + zone.replace(/\./g, '-') + '.json';
                a.click();
                if (a.href) (window.URL || window.webkitURL).revokeObjectURL(a.href);
                new PNotify({ title: 'Export done', text: 'DNS records downloaded.', type: 'success' });
            } else {
                new PNotify({ title: 'Error', text: response.data.error_message || 'Export failed', type: 'error' });
            }
        }, function () {
            $scope.exportLoading = false;
            new PNotify({ title: 'Error', text: 'Could not connect to server.', type: 'error' });
        });
    };

    $scope.onImportFile = function (files) {
        if (!files || !files.length) return;
        var zone = $scope.selectedZone;
        if (!zone) {
            new PNotify({ title: 'Error', text: 'Select a zone first.', type: 'error' });
            return;
        }
        var file = files[0];
        var reader = new FileReader();
        reader.onload = function (e) {
            var text = e.target && e.target.result;
            if (!text) {
                new PNotify({ title: 'Error', text: 'Could not read file.', type: 'error' });
                return;
            }
            var arr;
            try {
                arr = JSON.parse(text);
            } catch (err) {
                new PNotify({ title: 'Error', text: 'Invalid JSON: ' + (err.message || ''), type: 'error' });
                return;
            }
            if (!Array.isArray(arr)) {
                if (arr && Array.isArray(arr.records)) arr = arr.records;
                else if (arr && arr.data) arr = Array.isArray(arr.data) ? arr.data : [arr.data];
                else arr = [arr];
            }
            url = '/dns/importDNSRecordsCloudFlare';
            var data = { selectedZone: zone, records: arr };
            var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
            $http.post(url, data, config).then(function (response) {
                if (response.data.import_status === 1) {
                    populateCurrentRecords();
                    var failed = response.data.failed || [];
                    var msg = response.data.imported + ' record(s) imported.';
                    if (failed.length) msg += ' ' + failed.length + ' failed.';
                    new PNotify({ title: 'Import done', text: msg, type: failed.length ? 'warning' : 'success' });
                } else {
                    new PNotify({ title: 'Error', text: response.data.error_message || 'Import failed', type: 'error' });
                }
            }, function () {
                new PNotify({ title: 'Error', text: 'Could not connect to server.', type: 'error' });
            });
        };
        reader.readAsText(file, 'UTF-8');
    };

    $scope.checkStaleRecords = function () {
        var zone = $scope.selectedZone;
        if (!zone) return;
        $scope.staleLoading = true;
        url = '/dns/getStaleDNSRecordsCloudFlare';
        var data = { selectedZone: zone };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function (response) {
            $scope.staleLoading = false;
            if (response.data.fetchStatus === 1) {
                $scope.staleRecords = response.data.stale_records || [];
                $scope.staleModalVisible = true;
            } else {
                new PNotify({ title: 'Error', text: response.data.error_message || 'Could not fetch stale records', type: 'error' });
            }
        }, function () {
            $scope.staleLoading = false;
            new PNotify({ title: 'Error', text: 'Could not connect to server.', type: 'error' });
        });
    };

    $scope.closeStaleModal = function () {
        $scope.staleModalVisible = false;
        $scope.staleRecords = [];
    };

    $scope.removeStaleRecords = function () {
        if (!$scope.staleRecords || $scope.staleRecords.length === 0) return;
        var zone = $scope.selectedZone;
        var msg = 'Remove ' + $scope.staleRecords.length + ' orphan DNS record(s)? A local copy will be kept for Restore.';
        if (!$window.confirm(msg)) return;
        var ids = $scope.staleRecords.map(function (r) { return r.id; });
        url = '/dns/removeStaleDNSRecordsCloudFlare';
        var data = { selectedZone: zone, ids: ids };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function (response) {
            if (response.data.delete_status === 1 && response.data.deleted_records) {
                if (!$scope.cfDeletedBackup[zone]) $scope.cfDeletedBackup[zone] = [];
                $scope.cfDeletedBackup[zone] = $scope.cfDeletedBackup[zone].concat(response.data.deleted_records);
                $scope.closeStaleModal();
                populateCurrentRecords();
                new PNotify({ title: 'Done', text: response.data.deleted_records.length + ' orphan record(s) removed. Use Restore to undo.', type: 'success' });
            } else {
                new PNotify({ title: 'Error', text: response.data.error_message || 'Remove failed', type: 'error' });
            }
        }, function () {
            new PNotify({ title: 'Error', text: 'Could not connect to server.', type: 'error' });
        });
    };

    $scope.syncCF = function () {

        $scope.recordsLoading = false;
        var selectedZone = $scope.selectedZone;

        url = "/dns/syncCF";

        var data = {
            selectedZone: selectedZone
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status === 1) {


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

    $scope.enableProxy = function (name, value) {
        $scope.recordsLoading = false;

        var selectedZone = $scope.selectedZone;

        url = "/dns/enableProxy";

        var data = {
            selectedZone: selectedZone,
            name: name,
            value: value
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            populateCurrentRecords();

            if (response.data.status === 1) {


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

/* Java script code for CloudFlare */


app.controller('ResetDNSconf', function ($scope, $http, $timeout){
    $scope.Loading = true;
    $scope.NotifyBox = true;
    $scope.InstallBox = true;


    $scope.resetDNS = function () {
        $scope.Loading = false;
        $scope.installationDetailsForm = true;
        $scope.InstallBox = false;



         url = "/dns/resetDNSnow";

        var data = {
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


         function ListInitialData(response) {

            if (response.data.status === 1) {
                $scope.NotifyBox = true;
                $scope.InstallBox = false;
                $scope.Loading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.statusfile = response.data.tempStatusPath

                $timeout(getRequestStatus, 1000);

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.NotifyBox = false;
                $scope.InstallBox = true;
                $scope.Loading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberhosting = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    }



    function getRequestStatus() {

        $scope.NotifyBox = true;
        $scope.InstallBox = false;
        $scope.Loading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/dns/getresetstatus";

        var data = {
            statusfile: $scope.statusfile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.NotifyBox = true;
                $scope.InstallBox = false;
                $scope.Loading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            } else {
                // Notifications
                $timeout.cancel();
                $scope.NotifyBox = false;
                $scope.InstallBox = false;
                $scope.Loading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.modSecSuccessfullyInstalled = false;
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.NotifyBox = false;
            $scope.InstallBox = false;
            $scope.Loading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }
});