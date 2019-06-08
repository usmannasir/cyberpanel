/**
 * Created by usman on 6/22/18.
 */

/* Java script code to list accounts */

app.controller('listDomains', function($scope,$http) {

    $scope.listFail = true;
    $scope.emailLimitsLoading = true;

    // Global page number, to be used in later function to refresh the domains
    var globalPageNumber;


    $scope.getFurtherWebsitesFromDB = function(pageNumber) {

        globalPageNumber = pageNumber;
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/getFurtherDomains";

        var data = {page: pageNumber};

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

        if (response.data.listWebSiteStatus === 1) {

            $scope.WebSitesList = JSON.parse(response.data.data);
            $scope.listFail = true;
        }
        else
        {
            $scope.listFail = false;
            $scope.errorMessage = response.data.error_message;

        }
    }
        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
    }


        };
    $scope.getFurtherWebsitesFromDB(1);

    $scope.enableDisableEmailLimits = function (operationVal, domainName) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableEmailLimits";

        var data = {
            operationVal: operationVal,
            domainName: domainName
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {

            $scope.getFurtherWebsitesFromDB(globalPageNumber);
            $scope.listFail = true;
        }
        else
        {
            $scope.listFail = false;
            $scope.errorMessage = response.data.error_message;

        }
    }
        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
    }
    }
});

/* Java script code to list accounts ends here */



/* Java script code for email domain page */

app.controller('emailDomainPage', function($scope,$http, $timeout, $window) {

    $scope.listFail = true;
    $scope.emailLimitsLoading = true;

    var globalDomainName = window.location.pathname.split("/")[2];

    // Global page number, to be used in later function to refresh the domains
    var globalPageNumber;


    $scope.getFurtherEmailsFromDB = function(pageNumber) {

        globalPageNumber = pageNumber;
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/getFurtherEmail";

        var data = {
            page: pageNumber,
            domainName: globalDomainName
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {

            $scope.emailList = JSON.parse(response.data.data);
            $scope.listFail = true;
        }
        else
        {
            $scope.listFail = false;
            $scope.errorMessage = response.data.error_message;

        }
    }
        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
    }


        };
    $scope.getFurtherEmailsFromDB(1);

    $scope.enableDisableEmailLimits = function (operationVal, domainName) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableEmailLimits";

        var data = {
            operationVal: operationVal,
            domainName: domainName
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {

            $timeout(function() {  $window.location.reload(); }, 0);
        }
        else
        {
            $timeout(function() {  $window.location.reload(); }, 0);
        }
    }
        function cantLoadInitialData(response) {
            $timeout(function() {  $window.location.reload(); }, 0);
    }
    };


    /// Email limits

    $scope.changeLimitsForm = true;
    $scope.changeLimitsFail = true;
    $scope.changeLimitsSuccess = true;
    $scope.couldNotConnect = true;

    $scope.showLimitsForm = function () {
        $scope.changeLimitsForm = false;
    };

    $scope.hideLimitsForm = function () {
        $scope.changeLimitsForm = true;
        $scope.changeLimitsFail = true;
        $scope.changeLimitsSuccess = true;
        $scope.couldNotConnect = true;
    };

    $scope.changeDomainEmailLimits = function (domainName) {
            $scope.emailLimitsLoading = false;

            url = "/emailPremium/changeDomainLimit";

            var data = {
                domainName: domainName,
                newLimit: $scope.monthlyLimit
            };

            var config = {
                headers : {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


            function ListInitialData(response) {

                $scope.emailLimitsLoading = true;


            if (response.data.status === 1) {

                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = true;
                $scope.changeLimitsSuccess = false;
                $scope.couldNotConnect = true;
                $timeout(function() {  $window.location.reload(); }, 3000);
            }
            else
            {
                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = false;
                $scope.changeLimitsSuccess = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;

            }
        }
            function cantLoadInitialData(response) {
                $scope.emailLimitsLoading = true;
                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = true;
                $scope.changeLimitsSuccess = true;
                $scope.couldNotConnect = false;
        }
    }


    $scope.enableDisableIndividualEmailLimits = function (operationVal, emailAddress) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableIndividualEmailLimits";

        var data = {
            operationVal: operationVal,
            emailAddress: emailAddress
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {
            $scope.getFurtherEmailsFromDB(1);
        }
        else
        {
            $scope.getFurtherEmailsFromDB(1);
        }
    }
        function cantLoadInitialData(response) {
            $scope.getFurtherEmailsFromDB(1);
    }
    };

});

/* Java script code for email domain page */


/* Java script code for Email Page */

app.controller('emailPage', function($scope,$http, $timeout, $window) {

    $scope.emailLimitsLoading = true;

    var globalEamilAddress = $("#emailAddress").text();

    // Global page number, to be used in later function to refresh the domains
    var globalPageNumber;

    $scope.getEmailStats = function() {

        $scope.emailLimitsLoading = false;

        ////

        $scope.limitsOn = true;
        $scope.limitsOff = true;

        url = "/emailPremium/getEmailStats";

        var data = {
            emailAddress: globalEamilAddress
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {

            $scope.monthlyLimit = response.data.monthlyLimit;
            $scope.monthlyUsed = response.data.monthlyUsed;
            $scope.hourlyLimit = response.data.hourlyLimit;
            $scope.hourlyUsed = response.data.hourlyUsed;

            if(response.data.limitStatus === 1){
                $scope.limitsOn = false;
                $scope.limitsOff = true;
            }else{
                $scope.limitsOn = true;
                $scope.limitsOff = false;
            }

            if(response.data.logsStatus === 1){
                $scope.loggingOn = false;
                $scope.loggingOff = true;
            }else{
                $scope.loggingOn = true;
                $scope.loggingOff = false;
            }

        }
        else
        {

            $scope.errorMessage = response.data.error_message;

        }
    }
        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
    }


        };
    $scope.getEmailStats();

    $scope.enableDisableIndividualEmailLimits = function (operationVal, emailAddress) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableIndividualEmailLimits";

        var data = {
            operationVal: operationVal,
            emailAddress: emailAddress
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {
                $scope.getEmailStats();
            }
            else
            {
                $scope.getEmailStats();
            }
    }
        function cantLoadInitialData(response) {
            $scope.getEmailStats();
    }
    };
    $scope.enableDisableIndividualEmailLogs = function (operationVal, emailAddress) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableIndividualEmailLogs";

        var data = {
            operationVal: operationVal,
            emailAddress: emailAddress
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

            if (response.data.status === 1) {
                $scope.getEmailStats();
            }
            else
            {
                $scope.getEmailStats();
            }
    }
        function cantLoadInitialData(response) {
            $scope.getEmailStats();
    }
    };


    $scope.enableDisableEmailLimits = function (operationVal, domainName) {

        $scope.emailLimitsLoading = false;


        url = "/emailPremium/enableDisableEmailLimits";

        var data = {
            operationVal: operationVal,
            domainName: domainName
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {

            $timeout(function() {  $window.location.reload(); }, 0);
        }
        else
        {
            $timeout(function() {  $window.location.reload(); }, 0);
        }
    }
        function cantLoadInitialData(response) {
            $timeout(function() {  $window.location.reload(); }, 0);
    }
    };


    /// Email limits
    $scope.changeLimitsForm = true;
    $scope.changeLimitsFail = true;
    $scope.changeLimitsSuccess = true;
    $scope.couldNotConnect = true;

    $scope.showLimitsForm = function () {
        $scope.changeLimitsForm = false;
    };

    $scope.hideLimitsForm = function () {
        $scope.changeLimitsForm = true;
        $scope.changeLimitsFail = true;
        $scope.changeLimitsSuccess = true;
        $scope.couldNotConnect = true;
    };

    $scope.changeDomainEmailLimitsIndividual = function () {
            $scope.emailLimitsLoading = false;

            url = "/emailPremium/changeDomainEmailLimitsIndividual";

            var data = {
                emailAddress: globalEamilAddress,
                monthlyLimit: $scope.monthlyLimitForm,
                hourlyLimit: $scope.hourlyLimitForm
            };

            var config = {
                headers : {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


            function ListInitialData(response) {

                $scope.emailLimitsLoading = true;


            if (response.data.status === 1) {

                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = true;
                $scope.changeLimitsSuccess = false;
                $scope.couldNotConnect = true;
                $scope.getEmailStats();

            }
            else
            {
                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = false;
                $scope.changeLimitsSuccess = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;

            }
        }
            function cantLoadInitialData(response) {
                $scope.emailLimitsLoading = true;
                $scope.changeLimitsForm = false;
                $scope.changeLimitsFail = true;
                $scope.changeLimitsSuccess = true;
                $scope.couldNotConnect = false;
        }
    };

    /// Get email logs

    $scope.getLogEntries = function(pageNumber) {

        globalPageNumber = pageNumber;
        $scope.emailLimitsLoading = false;

        url = "/emailPremium/getEmailLogs";

        var data = {
            page: pageNumber,
            emailAddress: globalEamilAddress
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {

            $scope.logs = JSON.parse(response.data.data);
            $scope.listFail = true;
        }
        else
        {
            $scope.listFail = false;
            $scope.errorMessage = response.data.error_message;

        }
    }
        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
    }


        };
    $scope.getLogEntries(1);


    $scope.flushLogs = function(emailAddress) {

        $scope.emailLimitsLoading = false;

        url = "/emailPremium/flushEmailLogs";

        var data = {
            emailAddress: emailAddress
        };

        var config = {
            headers : {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            $scope.emailLimitsLoading = true;

        if (response.data.status === 1) {
            $scope.getLogEntries(1);

        }
        else
            {
            $scope.listFail = false;
            $scope.errorMessage = response.data.error_message;

            }
        }
        function cantLoadInitialData(response) {
            $scope.emailLimitsLoading = true;
            $scope.listFail = false;
        }


        };

});

/* Java script code for Email Page */


/* Java script code for SpamAssassin */

app.controller('SpamAssassin', function($scope, $http, $timeout, $window) {

           $scope.SpamAssassinNotifyBox  = true;
           $scope.SpamAssassinInstallBox = true;
           $scope.SpamAssassinLoading = true;
           $scope.failedToStartInallation = true;
           $scope.couldNotConnect = true;
           $scope.SpamAssassinSuccessfullyInstalled = true;
           $scope.installationFailed = true;



           $scope.installSpamAssassin = function(){

               $scope.SpamAssassinNotifyBox  = true;
               $scope.SpamAssassinInstallBox = true;
               $scope.SpamAssassinLoading = false;
               $scope.failedToStartInallation = true;
               $scope.couldNotConnect = true;
               $scope.SpamAssassinSuccessfullyInstalled = true;
               $scope.installationFailed = true;

               url = "/emailPremium/installSpamAssassin";

                        var data = {};

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.status === 1){

                        $scope.SpamAssassinNotifyBox  = true;
                        $scope.SpamAssassinInstallBox = false;
                        $scope.SpamAssassinLoading = false;
                        $scope.failedToStartInallation = true;
                        $scope.couldNotConnect = true;
                        $scope.SpamAssassinSuccessfullyInstalled = true;
                        $scope.installationFailed = true;

                        getRequestStatus();

                    }
                    else{
                        $scope.errorMessage = response.data.error_message;

                        $scope.SpamAssassinNotifyBox  = false;
                        $scope.SpamAssassinInstallBox = true;
                        $scope.SpamAssassinLoading = true;
                        $scope.failedToStartInallation = false;
                        $scope.couldNotConnect = true;
                        $scope.SpamAssassinSuccessfullyInstalled = true;
                    }

                }
                function cantLoadInitialDatas(response) {

                        $scope.SpamAssassinNotifyBox  = false;
                        $scope.SpamAssassinInstallBox = false;
                        $scope.SpamAssassinLoading = true;
                        $scope.failedToStartInallation = true;
                        $scope.couldNotConnect = false;
                        $scope.SpamAssassinSuccessfullyInstalled = true;
                        $scope.installationFailed = true;
                }

           };

           function getRequestStatus(){

                        $scope.SpamAssassinNotifyBox  = true;
                        $scope.SpamAssassinInstallBox = false;
                        $scope.SpamAssassinLoading = false;
                        $scope.failedToStartInallation = true;
                        $scope.couldNotConnect = true;
                        $scope.SpamAssassinSuccessfullyInstalled = true;
                        $scope.installationFailed = true;

                        url = "/emailPremium/installStatusSpamAssassin";

                        var data = {};

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.abort === 0){

                        $scope.SpamAssassinNotifyBox  = true;
                        $scope.SpamAssassinInstallBox = false;
                        $scope.SpamAssassinLoading = false;
                        $scope.failedToStartInallation = true;
                        $scope.couldNotConnect = true;
                        $scope.SpamAssassinSuccessfullyInstalled = true;
                        $scope.installationFailed = true;

                        $scope.requestData = response.data.requestStatus;
                        $timeout(getRequestStatus,1000);
                    }
                    else{
                        // Notifications
                        $timeout.cancel();
                        $scope.SpamAssassinNotifyBox  = false;
                        $scope.SpamAssassinInstallBox = false;
                        $scope.SpamAssassinLoading = true;
                        $scope.failedToStartInallation = true;
                        $scope.couldNotConnect = true;

                        $scope.requestData = response.data.requestStatus;

                        if(response.data.installed === 0) {
                            $scope.installationFailed = false;
                            $scope.errorMessage = response.data.error_message;
                        }else{
                            $scope.SpamAssassinSuccessfullyInstalled = false;
                            $timeout(function() {  $window.location.reload(); }, 3000);
                        }

                    }

                }
                function cantLoadInitialDatas(response) {

                        $scope.SpamAssassinNotifyBox  = false;
                        $scope.SpamAssassinInstallBox = false;
                        $scope.SpamAssassinLoading = true;
                        $scope.failedToStartInallation = true;
                        $scope.couldNotConnect = false;
                        $scope.SpamAssassinSuccessfullyInstalled = true;
                        $scope.installationFailed = true;


                }

           }

           ///// SpamAssassin configs

           var report_safe = false;


           $('#report_safe').change(function() {
                report_safe = $(this).prop('checked');
           });

           fetchSpamAssassinSettings();
           function fetchSpamAssassinSettings(){

               $scope.SpamAssassinLoading = false;

               $('#report_safe').bootstrapToggle('off');

               url = "/emailPremium/fetchSpamAssassinSettings";

               var data = {};

               var config = {
                   headers : {
                       'X-CSRFToken': getCookie('csrftoken')
                   }
               };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    $scope.SpamAssassinLoading = true;

                    if(response.data.fetchStatus === 1){

                        if(response.data.installed === 1) {

                            if (response.data.report_safe === 1) {
                                $('#report_safe').bootstrapToggle('on');
                            }

                            $scope.required_hits = response.data.required_hits;
                            $scope.rewrite_header = response.data.rewrite_header;
                            $scope.required_score = response.data.required_score;

                        }

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.SpamAssassinLoading = true;
                }

           }


           /////

           /// Save SpamAssassin Changes

          $scope.failedToSave = true;
          $scope.successfullySaved = true;

          $scope.saveSpamAssassinConfigurations = function () {

               $scope.failedToSave = true;
               $scope.successfullySaved = true;
               $scope.SpamAssassinLoading = false;
               $scope.couldNotConnect = true;


                        url = "/emailPremium/saveSpamAssassinConfigurations";

                        var data = {
                            report_safe:report_safe,
                            required_hits:$scope.required_hits,
                            rewrite_header:$scope.rewrite_header,
                            required_score:$scope.required_score
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.saveStatus === 1){

                        $scope.failedToSave = true;
                        $scope.successfullySaved = false;
                        $scope.SpamAssassinLoading = true;
                        $scope.couldNotConnect = true;

                    }
                    else{
                        $scope.errorMessage = response.data.error_message;

                        $scope.failedToSave = false;
                        $scope.successfullySaved = true;
                        $scope.SpamAssassinLoading = true;
                        $scope.couldNotConnect = true;
                    }

                }
                function cantLoadInitialDatas(response) {
                        $scope.failedToSave = true;
                        $scope.successfullySaved = false;
                        $scope.SpamAssassinLoading = true;
                        $scope.couldNotConnect = true;
                }


           };

});


/* Java script code for SpamAssassin */


/* Java script code for Email Policy Server */

app.controller('policyServer', function($scope, $http, $timeout, $window) {

           $scope.policyServerLoading = true;
           $scope.failedToFetch = true;
           $scope.couldNotConnect = true;
           $scope.changesApplied = true;


           ///// SpamAssassin configs

           var report_safe = false;


           $('#policServerStatus').change(function() {
                policServerStatus = $(this).prop('checked');
           });

           fetchPolicServerStatus();
           function fetchPolicServerStatus(){

               $scope.policyServerLoading = false;

               $('#policServerStatus').bootstrapToggle('off');

               url = "/emailPremium/fetchPolicyServerStatus";

               var data = {};

               var config = {
                   headers : {
                       'X-CSRFToken': getCookie('csrftoken')
                   }
               };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    $scope.policyServerLoading = true;

                    if(response.data.status === 1){

                        if (response.data.installCheck === 1) {
                                $('#policServerStatus').bootstrapToggle('on');
                            }

                    }else{
                       $scope.failedToFetch = false;
                       $scope.couldNotConnect = true;
                       $scope.changesApplied = true;

                       $scope.errorMessage = response.data.error_message;

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.policyServerLoading = true;
                    $scope.failedToFetch = true;
                    $scope.couldNotConnect = false;
                    $scope.changesApplied = true;
                }

           }


           $scope.savePolicServerStatus = function () {

               $scope.policyServerLoading = false;
               $scope.failedToFetch = true;
               $scope.couldNotConnect = true;
               $scope.changesApplied = true;



                        url = "/emailPremium/savePolicyServerStatus";

                        var data = {
                            policServerStatus:policServerStatus
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.policyServerLoading = true;

                    if(response.data.status === 1){

                        $scope.failedToFetch = true;
                        $scope.couldNotConnect = true;
                        $scope.changesApplied = false;

                    }
                    else{
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

});


/* Java script code for Email Policy Server */