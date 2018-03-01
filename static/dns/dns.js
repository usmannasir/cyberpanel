/**
 * Created by usman on 8/1/17.
 */


/* Java script code to create NS */

app.controller('createNameserver', function($scope,$http) {

                $scope.createNameserverLoading = true;
                $scope.nameserverCreationFailed = true;
                $scope.nameserverCreated = true;
                $scope.couldNotConnect = true;

                $scope.createNameserverFunc = function(){

                    var domainForNS = $scope.domainForNS;

                    var ns1 = $scope.firstNS;
                    var ns2 = $scope.secondNS;

                    var firstNSIP = $scope.firstNSIP;
                    var secondNSIP = $scope.secondNSIP;


                url = "/dns/NSCreation";

                    var data = {
                        domainForNS:domainForNS,
                        ns1:ns1,
                        ns2:ns2,
                        firstNSIP:firstNSIP,
                        secondNSIP:secondNSIP,
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.NSCreation == 1){
                        $scope.createNameserverLoading = true;
                        $scope.nameserverCreationFailed = true;
                        $scope.nameserverCreated = false;
                        $scope.couldNotConnect = true;


                        $scope.nameServerTwo = $scope.firstNS;
                        $scope.nameServerOne = $scope.secondNS;

                    }
                    else{
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

app.controller('createDNSZone', function($scope,$http) {

                $scope.createDNSZoneLoading = true;
                $scope.dnsZoneCreationFailed = true;
                $scope.dnsZoneCreated = true;
                $scope.couldNotConnect = true;

                $scope.createDNSZone = function(){

                var zoneDomain = $scope.zoneDomain;


                url = "/dns/zoneCreation";

                    var data = {
                        zoneDomain:zoneDomain,
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.zoneCreation == 1){
                        $scope.createDNSZoneLoading = true;
                        $scope.dnsZoneCreationFailed = true;
                        $scope.dnsZoneCreated = false;
                        $scope.couldNotConnect = true;

                        $scope.zoneDomain = $scope.zoneDomain;

                    }
                    else{
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

app.controller('addModifyDNSRecords', function($scope,$http) {

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
                $scope.recordValueMX = true;
                $scope.recordValueAAAA = true;
                $scope.recordValueCNAME = true;
                $scope.recordValueSPF = true;
                $scope.recordValueTXT = true;


           $scope.fetchRecords = function(){
               $scope.recordsLoading = false;
               $scope.addRecordsBox = false;
               populateCurrentRecords();
           };


           $scope.addDNSRecord = function(){

                        $scope.recordsLoading = false;


                        url = "/dns/addDNSRecord";


                        var selectedZone = $scope.selectedZone;
                        var recordName = $scope.recordName;
                        var recordType = $scope.recordType;

                        //specific values

                        var recordContentMX = "";
                        var recordContentA = "";
                        var recordContentAAAA = "";
                        var recordContentCNAME = "";
                        var recordContentSPF = "";
                        var recordContentTXT = "";



                        // Record specific values

                        if($scope.recordType=="MX"){
                            recordContentMX = $scope.recordContentMX;
                        }
                        else if($scope.recordType=="A"){
                            recordContentA = $scope.recordContentA;
                        }
                        else if($scope.recordType=="AAAA"){
                            recordContentAAAA = $scope.recordContentAAAA;
                        }
                        else if($scope.recordType=="CNAME"){
                            recordContentCNAME = $scope.recordContentCNAME;
                        }
                        else if($scope.recordType=="SPF"){
                            recordContentSPF = $scope.recordContentSPF;
                        }
                        else if($scope.recordType=="TXT"){
                            recordContentTXT = $scope.recordContentTXT;
                        }




                        var data = {
                            selectedZone:selectedZone,
                            recordName:recordName,
                            recordType:recordType,
                            recordContentA:recordContentA,
                            recordContentMX:recordContentMX,
                            recordContentAAAA:recordContentAAAA,
                            recordContentCNAME:recordContentCNAME,
                            recordContentSPF:recordContentSPF,
                            recordContentTXT:recordContentTXT,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };


                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.add_status == 1){


                        populateCurrentRecords();

                        $scope.canNotFetchRecords = true;
                        $scope.recordsFetched = false;
                        $scope.recordDeleted = true;
                        $scope.recordAdded = false;
                        $scope.couldNotConnect = true;
                        $scope.couldNotAddRecord = true;
                        $scope.recordsLoading = true;


                    }
                    else{

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



           function populateCurrentRecords(){

                        var selectedZone = $scope.selectedZone;

                        url = "/dns/getCurrentRecordsForDomain";

                        var data = {
                            selectedZone:selectedZone,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

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

                    }
                    else{

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



           $scope.deleteRecord = function(id){


                        var selectedZone = $scope.selectedZone;

                        url = "/dns/deleteDNSRecord";

                        var data = {
                            id:id,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.delete_status == 1){


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



                    }
                    else{

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



           // MX Record Settings

            $scope.detectType = function(){


                if($scope.recordType=="MX")
                {
                    $scope.recordValueDefault = true;
                    $scope.recordValueMX = false;
                    $scope.recordValueAAAA = true;
                    $scope.recordValueCNAME = true;
                    $scope.recordValueSPF = true;
                    $scope.recordValueTXT = true;
                }
                else if($scope.recordType=="A"){
                    $scope.recordValueDefault = false;
                    $scope.recordValueMX = true;
                    $scope.recordValueAAAA = true;
                    $scope.recordValueCNAME = true;
                    $scope.recordValueSPF = true;
                    $scope.recordValueTXT = true;
                }
                else if($scope.recordType=="AAAA"){
                    $scope.recordValueDefault = true;
                    $scope.recordValueMX = true;
                    $scope.recordValueAAAA = false;
                    $scope.recordValueCNAME = true;
                    $scope.recordValueSPF = true;
                    $scope.recordValueTXT = true;
                }
                else if($scope.recordType=="CNAME"){
                    $scope.recordValueDefault = true;
                    $scope.recordValueMX = true;
                    $scope.recordValueAAAA = true;
                    $scope.recordValueCNAME = false;
                    $scope.recordValueSPF = true;
                    $scope.recordValueTXT = true;
                }
                else if($scope.recordType=="SPF"){
                    $scope.recordValueDefault = true;
                    $scope.recordValueMX = true;
                    $scope.recordValueAAAA = true;
                    $scope.recordValueCNAME = true;
                    $scope.recordValueSPF = false;
                    $scope.recordValueTXT = true;
                }
                else if($scope.recordType=="TXT"){
                    $scope.recordValueDefault = true;
                    $scope.recordValueMX = true;
                    $scope.recordValueAAAA = true;
                    $scope.recordValueCNAME = true;
                    $scope.recordValueSPF = true;
                    $scope.recordValueTXT = false;
                }


            };



});

/* Java script code to delete DNS Zone */



/* Java script code to delete DNS Zone */

app.controller('deleteDNSZone', function($scope,$http) {

                $scope.deleteZoneButton = true;
                $scope.deleteFailure = true;
                $scope.deleteSuccess = true;
                $scope.couldNotConnect = true;


                $scope.deleteZone = function(){
                    $scope.deleteZoneButton = false;
                    $scope.deleteFailure = true;
                    $scope.deleteSuccess = true;
                }

                $scope.deleteZoneFinal = function(){

                var zoneDomain = $scope.selectedZone;


                url = "/dns/submitZoneDeletion";

                    var data = {
                        zoneDomain:zoneDomain,
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.delete_status == 1){

                        $scope.deleteZoneButton = true;
                        $scope.deleteFailure = true;
                        $scope.deleteSuccess = false;
                        $scope.couldNotConnect = true;

                        $scope.deletedZone = $scope.selectedZone;


                    }
                    else{

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