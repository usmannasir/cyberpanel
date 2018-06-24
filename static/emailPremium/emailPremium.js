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

            $timeout(function() {  $window.location.reload(); }, 3000);
        }
        else
        {
            $timeout(function() {  $window.location.reload(); }, 3000);
        }
    }
        function cantLoadInitialData(response) {
            $timeout(function() {  $window.location.reload(); }, 3000);
    }
    }
});

/* Java script code for email domain page */