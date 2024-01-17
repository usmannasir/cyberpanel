newapp.controller('createEmailAccountV2', function ($scope, $http) {

    $scope.emailDetails = true;
    $scope.emailLoading = true;
    $scope.canNotCreate = true;
    $scope.successfullyCreated = true;
    $scope.couldNotConnect = true;

    $scope.showEmailDetails = function () {

        $scope.emailDetails = false;
        $scope.emailLoading = true;
        $scope.canNotCreate = true;
        $scope.successfullyCreated = true;
        $scope.couldNotConnect = true;


        $scope.selectedDomain = $scope.emailDomain;


    };

    $scope.createEmailAccount = function () {

        $scope.emailDetails = false;
        $scope.emailLoading = false;
        $scope.canNotCreate = true;
        $scope.successfullyCreated = true;
        $scope.couldNotConnect = true;


        var url = "/email/submitEmailCreation";

        var domain = $scope.emailDomain;
        var username = $scope.emailUsername;
        var password = $scope.emailPassword;


        var data = {
            domain: domain,
            username: username,
            passwordByPass: password,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.createEmailStatus === 1) {

                $scope.emailDetails = false;
                $scope.emailLoading = true;
                $scope.canNotCreate = true;
                $scope.successfullyCreated = false;
                $scope.couldNotConnect = true;

                $scope.createdID = username + "@" + domain;


            } else {
                $scope.emailDetails = false;
                $scope.emailLoading = true;
                $scope.canNotCreate = false;
                $scope.successfullyCreated = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.emailDetails = false;
            $scope.emailLoading = true;
            $scope.canNotCreate = true;
            $scope.successfullyCreated = true;
            $scope.couldNotConnect = false;


        }


    };

    $scope.hideFewDetails = function () {

        $scope.successfullyCreated = true;

    };

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
        $scope.generatedPasswordView = false;
        $scope.emailPassword = randomPassword(16);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
    };

});