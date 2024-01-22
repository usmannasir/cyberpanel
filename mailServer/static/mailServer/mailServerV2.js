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

newapp.controller('listEmailsV2', function ($scope, $http) {

    $scope.cyberpanelLoading = true;
    $scope.emailsAccounts = true;
    $scope.mailConfigured = 1;

    $scope.populateCurrentRecords = function () {
        $scope.cyberpanelLoading = false;
        $scope.emailsAccounts = true;

        url = "/email/fetchEmails";

        var data = {
            selectedDomain: $scope.selectedDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;

            if (response.data.status === 1) {
                $scope.emailsAccounts = false;
                $scope.records = JSON.parse(response.data.data);
                $scope.mailConfigured = response.data.mailConfigured;
                $scope.serverHostname = response.data.serverHostname;

                new PNotify({
                    title: 'Success!',
                    text: 'Emails Successfully Fetched.',
                    type: 'success'
                });


            } else {
                $scope.emailsAccounts = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            $scope.emailsAccounts = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }

    };

    $scope.deleteEmailAccountFinal = function (email) {

        $scope.cyberpanelLoading = false;

        var url = "/email/submitEmailDeletion";

        var data = {
            email: email,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (response.data.deleteEmailStatus === 1) {
                $scope.populateCurrentRecords();
                new PNotify({
                    title: 'Success!',
                    text: 'Email Successfully deleted.',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

    $scope.fixMailSSL = function (email) {

        $scope.cyberpanelLoading = false;

        var url = "/email/fixMailSSL";

        var data = {
            selectedDomain: $scope.selectedDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (response.data.status === 1) {
                $scope.populateCurrentRecords();
                new PNotify({
                    title: 'Success!',
                    text: 'Configurations applied successfully.',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

    $scope.changePasswordInitial = function (email) {
        $scope.email = email;
    };

    $scope.changePassword = function () {

        $scope.cyberpanelLoading = false;


        var url = "/email/submitPasswordChange";

        var data = {
            domain: $scope.selectedDomain,
            email: $scope.email,
            passwordByPass: $scope.password,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Password Successfully changed.',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };
});