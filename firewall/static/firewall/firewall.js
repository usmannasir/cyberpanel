/**
 * Created by usman on 9/5/17.
 */






/* Java script code to ADD Firewall Rules */

app.controller('firewallController', function($scope,$http) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = true;
            $scope.rulesDetails = false;



           firewallStatus();


           populateCurrentRecords();




           $scope.addRule = function(){

                        $scope.rulesLoading = false;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;


                        url = "/firewall/addRule";


                        var ruleName = $scope.ruleName;
                        var ruleProtocol = $scope.ruleProtocol;
                        var rulePort = $scope.rulePort;



                        var data = {
                            ruleName:ruleName,
                            ruleProtocol:ruleProtocol,
                            rulePort:rulePort,
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

                        $scope.rulesLoading = true;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = false;
                        $scope.couldNotConnect = true;



                    }
                    else{

                        $scope.rulesLoading = true;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = false;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;


                        $scope.errorMessage = response.data.error_message;
                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.rulesLoading = true;
                    $scope.actionFailed = true;
                    $scope.actionSuccess = true;

                    $scope.canNotAddRule = true;
                    $scope.ruleAdded = true;
                    $scope.couldNotConnect = false;


                }

           };



           function populateCurrentRecords(){

                        $scope.rulesLoading = false;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;


                        url = "/firewall/getCurrentRules";

                        var data = {

                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

                        $scope.rules = JSON.parse(response.data.data);
                        $scope.rulesLoading = true;

                    }
                    else{
                        $scope.rulesLoading = true;
                        $scope.errorMessage = response.data.error_message;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = false;

                }

           };



           $scope.deleteRule = function(id,proto,port){




                        $scope.rulesLoading = false;

                        url = "/firewall/deleteRule";

                        var data = {
                            id:id,
                            proto:proto,
                            port:port,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.delete_status == 1){


                        populateCurrentRecords();
                        $scope.rulesLoading = true;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;



                    }
                    else{

                        $scope.rulesLoading = true;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = false;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.rulesLoading = true;
                        $scope.errorMessage = response.data.error_message;


                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.rulesLoading = true;
                    $scope.actionFailed = true;
                    $scope.actionSuccess = true;

                    $scope.canNotAddRule = true;
                    $scope.ruleAdded = true;
                    $scope.couldNotConnect = false;



                }


           };


           $scope.reloadFireWall = function(){


                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.rulesLoading = false;

                        url = "/firewall/reloadFirewall";

                        var data = {
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.reload_status == 1){


                        $scope.rulesLoading = true;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = false;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;



                    }
                    else{

                        $scope.rulesLoading = true;
                        $scope.actionFailed = false;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.errorMessage = response.data.error_message;


                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.rulesLoading = true;
                    $scope.actionFailed = true;
                    $scope.actionSuccess = true;

                    $scope.canNotAddRule = true;
                    $scope.ruleAdded = true;
                    $scope.couldNotConnect = false;


                }


           };

           $scope.startFirewall = function(){


                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.rulesLoading = false;

                        url = "/firewall/startFirewall";

                        var data = {
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.start_status == 1){


                        $scope.rulesLoading = true;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = false;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.rulesDetails = false;

                         firewallStatus();



                    }
                    else{

                        $scope.rulesLoading = true;
                        $scope.actionFailed = false;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.errorMessage = response.data.error_message;


                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.rulesLoading = true;
                    $scope.actionFailed = true;
                    $scope.actionSuccess = true;

                    $scope.canNotAddRule = true;
                    $scope.ruleAdded = true;
                    $scope.couldNotConnect = false;


                }


           };


           $scope.stopFirewall = function(){


                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.rulesLoading = false;

                        url = "/firewall/stopFirewall";

                        var data = {
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.stop_status == 1){


                        $scope.rulesLoading = true;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = false;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.rulesDetails = true;

                        firewallStatus();



                    }
                    else{

                        $scope.rulesLoading = true;
                        $scope.actionFailed = false;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.errorMessage = response.data.error_message;


                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.rulesLoading = true;
                    $scope.actionFailed = true;
                    $scope.actionSuccess = true;

                    $scope.canNotAddRule = true;
                    $scope.ruleAdded = true;
                    $scope.couldNotConnect = false;


                }


           };


           function firewallStatus(){



                        url = "/firewall/firewallStatus";

                        var data = {

                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.status == 1){

                        if(response.data.firewallStatus == 1){
                            $scope.rulesDetails = false;
                            $scope.status = "ON";
                        }
                        else{
                            $scope.rulesDetails = true;
                            $scope.status = "OFF";
                        }
                    }
                    else{

                        $scope.rulesDetails = true;
                        $scope.status = "OFF";
                    }


                }
                function cantLoadInitialDatas(response) {

                    $scope.couldNotConnect = false;


                }

           };






});

/* Java script code to ADD Firewall Rules */



/* Java script code to Secure SSH */

app.controller('secureSSHCTRL', function($scope,$http) {

           $scope.couldNotSave = true;
           $scope.detailsSaved = true;
           $scope.couldNotConnect = true;
           $scope.secureSSHLoading = true;
           $scope.keyDeleted = true;
           $scope.keyBox = true;
           $scope.showKeyBox = false;
           $scope.saveKeyBtn = true;

           $scope.addKey = function(){
                $scope.saveKeyBtn = false;
                $scope.showKeyBox = true;
                $scope.keyBox = false;
           };


           getSSHConfigs();
           populateCurrentKeys();

           // Checking root login

            var rootLogin = false;

            $('#rootLogin').change(function() {
                rootLogin = $(this).prop('checked');
            });


           function getSSHConfigs(){

                        $scope.couldNotSave = true;
                        $scope.detailsSaved = true;
                        $scope.couldNotConnect = true;
                        $scope.secureSSHLoading = false;

                        url = "/firewall/getSSHConfigs";

                        var data = {
                            type:"1",
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    $scope.sshPort = response.data.sshPort;

                    if(response.data.permitRootLogin == 1){
                        $('#rootLogin').bootstrapToggle('on');
                        $scope.couldNotSave = true;
                       $scope.detailsSaved = true;
                       $scope.couldNotConnect = true;
                       $scope.secureSSHLoading = true;
                    }
                    else{
                        $scope.errorMessage = response.data.error_message;
                        $scope.couldNotSave = true;
                        $scope.detailsSaved = true;
                        $scope.couldNotConnect = true;
                        $scope.secureSSHLoading = true;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = false;

                }

           };

           $scope.saveChanges = function () {

               $scope.couldNotSave = true;
               $scope.detailsSaved = true;
               $scope.couldNotConnect = true;
               $scope.secureSSHLoading = false;

               url = "/firewall/saveSSHConfigs";

                        var data = {
                            type:"1",
                            sshPort:$scope.sshPort,
                            rootLogin:rootLogin,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.saveStatus == 1){
                        $scope.couldNotSave = true;
                        $scope.detailsSaved = false;
                        $scope.couldNotConnect = true;
                        $scope.secureSSHLoading = true;
                    }
                    else{

                        $scope.couldNotSave = false;
                       $scope.detailsSaved = true;
                       $scope.couldNotConnect = true;
                       $scope.secureSSHLoading = true;

                        $scope.errorMessage = response.data.error_message;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotSave = true;
                    $scope.detailsSaved = true;
                    $scope.couldNotConnect = false;
                    $scope.secureSSHLoading = true;

                }
           };


           function populateCurrentKeys(){

                        url = "/firewall/getSSHConfigs";

                        var data = {
                            type:"2",
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.status == 1){
                        $scope.records = JSON.parse(response.data.data);
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = false;

                }


           }

           $scope.deleteKey =  function(key){

                        $scope.secureSSHLoading = false;

                        url = "/firewall/deleteSSHKey";

                        var data = {
                            key:key,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.delete_status == 1){
                        $scope.secureSSHLoading = true;
                        $scope.keyDeleted = false;
                        populateCurrentKeys();
                    }
                    else{
                        $scope.couldNotConnect = false;
                        $scope.secureSSHLoading = true;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = false;
                    $scope.secureSSHLoading = true;

                }


           }


           $scope.saveKey =  function(key){

                        $scope.secureSSHLoading = false;

                        url = "/firewall/addSSHKey";

                        var data = {
                            key:$scope.keyData,
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.add_status == 1){
                        $scope.secureSSHLoading = true;
                        $scope.saveKeyBtn = true;
                        $scope.showKeyBox = false;
                        $scope.keyBox = true;


                        populateCurrentKeys();
                    }
                    else{
                        $scope.secureSSHLoading = true;
                        $scope.saveKeyBtn = false;
                        $scope.showKeyBox = true;
                        $scope.keyBox = true;
                        $scope.couldNotConnect = false;
                        $scope.secureSSHLoading = true;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.secureSSHLoading = true;
                    $scope.saveKeyBtn = false;
                    $scope.showKeyBox = true;
                    $scope.keyBox = true;
                    $scope.couldNotConnect = false;
                    $scope.secureSSHLoading = true;

                }


           }

});

/* Java script code to Secure SSH */