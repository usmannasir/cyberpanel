newapp.controller('createFTPAccountV2', function ($scope, $http) {



    $(document).ready(function () {
        $( ".ftpDetails" ).hide();
        $( ".ftpPasswordView" ).hide();
        $('.create-ftp-acct-select').select2();
    });

    $('.create-ftp-acct-select').on('select2:select', function (e) {
        var data = e.params.data;
        $scope.ftpDomain = data.text;
        $( ".ftpDetails" ).show();

    });

    $scope.ftpLoading = true;

    $scope.createFTPAccount = function () {

        $scope.ftpLoading = false;
        $scope.ftpDetails = false;
        $scope.canNotCreate = true;
        $scope.successfullyCreated = true;
        $scope.couldNotConnect = true;

        var ftpDomain = $scope.ftpDomain;
        var ftpUserName = $scope.ftpUserName;
        var ftpPassword = $scope.ftpPassword;
        var path = $scope.ftpPath;

        if (typeof path === 'undefined') {
            path = "";
        }

        var url = "/ftp/submitFTPCreation";


        var data = {
            ftpDomain: ftpDomain,
            ftpUserName: ftpUserName,
            passwordByPass: ftpPassword,
            path: path,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.creatFTPStatus === 1) {
                $scope.ftpLoading = true;
                new PNotify({
                title: 'Success!',
                text: 'FTP account successfully created.',
                type: 'success'
            });


            } else {
                $scope.ftpLoading = true;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });


            }

        }
        function cantLoadInitialDatas(response) {

            $scope.ftpLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });


        }


    };

    $scope.hideFewDetails = function () {

        $scope.successfullyCreated = true;


    };

    ///

    $scope.generatePassword = function () {
        $( ".ftpPasswordView" ).show();
        $scope.ftpPassword = randomPassword(16);
    };

    $scope.usePassword = function () {
        $(".ftpPasswordView" ).hide();
    };

});

newapp.controller('deleteFTPAccountV2', function ($scope, $http) {

    $scope.ftpAccountsOfDomain = true;
    $scope.deleteFTPButton = true;
    $scope.deleteFailure = true;
    $scope.deleteSuccess = true;
    $scope.couldNotConnect = true;
    $scope.deleteFTPButtonInit = true;

    $scope.getFTPAccounts = function () {

        $scope.ftpAccountsOfDomain = true;
        $scope.deleteFTPButton = true;
        $scope.deleteFailure = true;
        $scope.deleteSuccess = true;
        $scope.couldNotConnect = true;
        $scope.deleteFTPButtonInit = true;


        var url = "/ftp/fetchFTPAccounts";


        var data = {
            ftpDomain: $scope.selectedDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus == 1) {


                $scope.ftpAccountsFeteched = JSON.parse(response.data.data);

                $scope.ftpAccountsOfDomain = false;
                $scope.deleteFTPButton = true;
                $scope.deleteFailure = true;
                $scope.deleteSuccess = true;
                $scope.couldNotConnect = true;
                $scope.deleteFTPButtonInit = false;


            } else {

                $scope.ftpAccountsOfDomain = true;
                $scope.deleteFTPButton = true;
                $scope.deleteFailure = true;
                $scope.deleteSuccess = true;
                $scope.couldNotConnect = false;
                $scope.deleteFTPButtonInit = true;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.ftpAccountsOfDomain = true;
            $scope.deleteFTPButton = true;
            $scope.deleteFailure = true;
            $scope.deleteSuccess = true;
            $scope.couldNotConnect = false;
            $scope.deleteFTPButtonInit = true;


        }


    };

    $scope.deleteFTPAccount = function () {

        $scope.ftpAccountsOfDomain = false;
        $scope.deleteFTPButton = false;
        $scope.deleteFailure = true;
        $scope.deleteSuccess = true;
        $scope.couldNotConnect = true;
        $scope.deleteFTPButtonInit = false;

    };


    $scope.deleteFTPFinal = function () {


        var url = "/ftp/submitFTPDelete";


        var data = {
            ftpUsername: $scope.selectedFTPAccount,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.deleteStatus == 1) {


                $scope.ftpAccountsOfDomain = true;
                $scope.deleteFTPButton = true;
                $scope.deleteFailure = true;
                $scope.deleteSuccess = false;
                $scope.couldNotConnect = true;
                $scope.deleteFTPButtonInit = true;

                $scope.ftpUserNameDeleted = $scope.selectedFTPAccount;


            } else {

                $scope.ftpAccountsOfDomain = true;
                $scope.deleteFTPButton = true;
                $scope.deleteFailure = false;
                $scope.deleteSuccess = true;
                $scope.couldNotConnect = true;
                $scope.deleteFTPButtonInit = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.ftpAccountsOfDomain = true;
            $scope.deleteFTPButton = true;
            $scope.deleteFailure = false;
            $scope.deleteSuccess = true;
            $scope.couldNotConnect = false;
            $scope.deleteFTPButtonInit = true;


        }


    };

});
newapp.controller('listFTPAccountsV2', function ($scope, $http) {

    $scope.recordsFetched = true;
    $scope.passwordChanged = true;
    $scope.canNotChangePassword = true;
    $scope.couldNotConnect = true;
    $scope.ftpLoading = true;
    $scope.ftpAccounts = true;
    $scope.changePasswordBox = true;
    $scope.notificationsBox = true;

    var globalFTPUsername = "";

    $scope.fetchFTPAccounts = function () {
        populateCurrentRecords();
    };

    $scope.changePassword = function (ftpUsername) {
        $scope.recordsFetched = true;
        $scope.passwordChanged = true;
        $scope.canNotChangePassword = true;
        $scope.couldNotConnect = true;
        $scope.ftpLoading = true;
        $scope.changePasswordBox = false;
        $scope.notificationsBox = true;
        $scope.ftpUsername = ftpUsername;
        globalFTPUsername = ftpUsername;

    };

    $scope.changePasswordBtn = function () {

        $scope.ftpLoading = false;


        url = "/ftp/changePassword";

        var data = {
            ftpUserName: globalFTPUsername,
            passwordByPass: $scope.ftpPassword,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePasswordStatus == 1) {
                $scope.notificationsBox = false;
                $scope.passwordChanged = false;
                $scope.ftpLoading = true;
                $scope.domainFeteched = $scope.selectedDomain;

            } else {
                $scope.notificationsBox = false;
                $scope.canNotChangePassword = false;
                $scope.ftpLoading = true;
                $scope.canNotChangePassword = false;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.notificationsBox = false;
            $scope.couldNotConnect = false;
            $scope.ftpLoading = true;

        }

    };

    function populateCurrentRecords() {
        $scope.recordsFetched = true;
        $scope.passwordChanged = true;
        $scope.canNotChangePassword = true;
        $scope.couldNotConnect = true;
        $scope.ftpLoading = false;
        $scope.ftpAccounts = true;
        $scope.changePasswordBox = true;

        var selectedDomain = $scope.selectedDomain;

        url = "/ftp/getAllFTPAccounts";

        var data = {
            selectedDomain: selectedDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus == 1) {

                $scope.records = JSON.parse(response.data.data);


                $scope.notificationsBox = false;
                $scope.recordsFetched = false;
                $scope.passwordChanged = true;
                $scope.canNotChangePassword = true;
                $scope.couldNotConnect = true;
                $scope.ftpLoading = true;
                $scope.ftpAccounts = false;
                $scope.changePasswordBox = true;

                $scope.domainFeteched = $scope.selectedDomain;

            } else {
                $scope.notificationsBox = false;
                $scope.recordsFetched = true;
                $scope.passwordChanged = true;
                $scope.canNotChangePassword = true;
                $scope.couldNotConnect = true;
                $scope.ftpLoading = true;
                $scope.ftpAccounts = true;
                $scope.changePasswordBox = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.notificationsBox = false;
            $scope.recordsFetched = true;
            $scope.passwordChanged = true;
            $scope.canNotChangePassword = true;
            $scope.couldNotConnect = false;
            $scope.ftpLoading = true;
            $scope.ftpAccounts = true;
            $scope.changePasswordBox = true;


        }

    }

    ////

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
        $scope.generatedPasswordView = false;
        $scope.ftpPassword = randomPassword(16);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
    };

});