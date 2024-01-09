newapp.controller('createUserCtrV2', function ($scope, $http) {

    $scope.acctsLimit = true;
    $scope.webLimits = true;
    $scope.userCreated = true;
    $scope.userCreationFailed = true;
    $scope.couldNotConnect = true;
    $scope.userCreationLoading = true;
    $scope.combinedLength = true;

    $scope.createUserFunc = function () {

        $scope.webLimits = false;
        $scope.userCreated = true;
        $scope.userCreationFailed = true;
        $scope.couldNotConnect = true;
        $scope.userCreationLoading = false;
        $scope.combinedLength = true;


        var firstName = $scope.firstName;
        var lastName = $scope.lastName;
        var email = $scope.email;
        var selectedACL = $scope.selectedACL;
        var websitesLimits = $scope.websitesLimits;
        var userName = $scope.userName;
        var password = $scope.password;


        var url = "/users/submitUserCreation";

        var data = {
            firstName: firstName,
            lastName: lastName,
            email: email,
            selectedACL: selectedACL,
            websitesLimit: websitesLimits,
            userName: userName,
            password: password,
            securityLevel: $scope.securityLevel
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.createStatus == 1) {

                $scope.userCreated = false;
                $scope.userCreationFailed = true;
                $scope.couldNotConnect = true;
                $scope.userCreationLoading = true;

                $scope.userName = userName;


            } else {

                $scope.acctsLimit = false;
                $scope.webLimits = false;
                $scope.userCreated = true;
                $scope.userCreationFailed = false;
                $scope.couldNotConnect = true;
                $scope.userCreationLoading = true;

                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.acctsLimit = false;
            $scope.webLimits = false;
            $scope.userCreated = true;
            $scope.userCreationFailed = true;
            $scope.couldNotConnect = false;
            $scope.userCreationLoading = true;


        }


    };

    $scope.hideSomeThings = function () {

        $scope.userCreated = true;


    };

    ///

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
        $scope.generatedPasswordView = false;
        $scope.password = randomPassword(16);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
    };

});

newapp.controller('listTableUsersV2', function ($scope, $http) {

    $scope.cyberpanelLoading = true;

    var UserToDelete;

    $scope.populateCurrentRecords = function () {
        $scope.cyberpanelLoading = false;

        url = "/users/fetchTableUsers";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;

            if (response.data.status === 1) {

                $scope.records = JSON.parse(response.data.data);

                new PNotify({
                    title: 'Success!',
                    text: 'Users successfully fetched!',
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
    $scope.populateCurrentRecords();


    $scope.deleteUserInitial = function (name){
        UserToDelete = name;
        $scope.UserToDelete = name;
    };

    $scope.deleteUserFinal = function () {
        $scope.cyberpanelLoading = false;

        var url = "/users/submitUserDeletion";

        var data = {
            accountUsername: UserToDelete,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.deleteStatus === 1) {
                $scope.populateCurrentRecords();
                new PNotify({
                    title: 'Success!',
                    text: 'Users successfully deleted!',
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

            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };

    $scope.editInitial = function (name) {

        $scope.name = name;

    };

    $scope.saveResellerChanges = function () {

        $scope.cyberpanelLoading = false;

        url = "/users/saveResellerChanges";

        var data = {
            userToBeModified: $scope.name,
            newOwner: $scope.newOwner
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
                    text: 'Changes successfully applied!',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
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

    $scope.changeACLFunc = function () {

        $scope.cyberpanelLoading = false;

        url = "/users/changeACLFunc";

        var data = {
            selectedUser: $scope.name,
            selectedACL: $scope.selectedACL
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
                $scope.populateCurrentRecords();
                new PNotify({
                    title: 'Success!',
                    text: 'ACL Successfully changed.',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

    $scope.controlUserState = function (userName, state) {

        $scope.cyberpanelLoading = false;

        var url = "/users/controlUserState";

        var data = {
            accountUsername: userName,
            state: state
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
                $scope.populateCurrentRecords();
                new PNotify({
                    title: 'Success!',
                    text: 'Action successfully started.',
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

            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    }

});