/**
 * Created by usman on 8/4/17.
 */


/* Java script code to create account */
app.controller('createFTPAccount', function ($scope, $http) {



    $scope.ftpLoading = false;
    $scope.ftpDetails = true;
    $scope.canNotCreateFTP = true;
    $scope.successfullyCreatedFTP = true;
    $scope.couldNotConnect = true;
    $scope.generatedPasswordView = true;

    $(document).ready(function () {
        $(".ftpDetails").hide();
        $(".ftpPasswordView").hide();
        if (typeof $ !== 'undefined' && $ && typeof $.fn !== 'undefined' && typeof $.fn.select2 === 'function') {
            try {
                var $sel = $('.create-ftp-acct-select');
                if ($sel.length) {
                    $sel.select2();
                    $sel.on('select2:select', function (e) {
                        var data = e.params.data;
                        $scope.ftpDomain = data.text;
                        $scope.ftpDetails = false;
                        $scope.$apply();
                        $(".ftpDetails").show();
                    });
                } else {
                    initNativeSelect();
                }
            } catch (err) {
                initNativeSelect();
            }
        } else {
            initNativeSelect();
        }
        function initNativeSelect() {
            $('.create-ftp-acct-select').off('select2:select').on('change', function () {
                $scope.ftpDomain = $(this).val();
                $scope.ftpDetails = !($scope.ftpDomain && $scope.ftpDomain !== "");
                $scope.$apply();
                if ($scope.ftpDomain && $scope.ftpDomain !== "") $(".ftpDetails").show();
                else $(".ftpDetails").hide();
            });
        }
    });

    $scope.showFTPDetails = function () {
        if ($scope.ftpDomain && $scope.ftpDomain !== "") {
            $(".ftpDetails").show();
            $scope.ftpDetails = false;
        } else {
            $(".ftpDetails").hide();
            $scope.ftpDetails = true;
        }
    };

    $scope.createFTPAccount = function () {

        $scope.ftpLoading = true;
        $scope.ftpDetails = false;
        $scope.canNotCreateFTP = true;
        $scope.successfullyCreatedFTP = true;
        $scope.couldNotConnect = true;

        var ftpDomain = $scope.ftpDomain;
        var ftpUserName = $scope.ftpUserName;
        var ftpPassword = $scope.ftpPassword;
        var path = $scope.ftpPath;

        if (typeof path === 'undefined' || path == null) path = "";
        else path = String(path).trim();

        var data = {
            ftpDomain: ftpDomain,
            ftpUserName: ftpUserName,
            passwordByPass: ftpPassword,
            path: path,
            enableCustomQuota: $scope.enableCustomQuota || false,
            customQuotaSize: $scope.customQuotaSize || 0,
        };
        var url = "/ftp/submitFTPCreation";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.creatFTPStatus === 1) {
                $scope.ftpLoading = false;
                $scope.successfullyCreatedFTP = false;
                $scope.canNotCreateFTP = true;
                $scope.couldNotConnect = true;
                $scope.createdFTPUsername = ftpDomain + "_" + ftpUserName;
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Success!', text: 'FTP account successfully created.', type: 'success' });
                }
            } else {
                $scope.ftpLoading = false;
                $scope.canNotCreateFTP = false;
                $scope.successfullyCreatedFTP = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Operation Failed!', text: response.data.error_message, type: 'error' });
                }
            }

        }
        function cantLoadInitialDatas(response) {
            $scope.ftpLoading = false;
            $scope.couldNotConnect = false;
            $scope.canNotCreateFTP = true;
            $scope.successfullyCreatedFTP = true;
            if (typeof PNotify !== 'undefined') {
                new PNotify({ title: 'Operation Failed!', text: 'Could not connect to server, please refresh this page', type: 'error' });
            }
        }


    };

    $scope.hideFewDetails = function () {
        $scope.successfullyCreatedFTP = true;
        $scope.canNotCreateFTP = true;
        $scope.couldNotConnect = true;
    };

    ///

    $scope.generatePassword = function () {
        $(".ftpPasswordView").show();
        $scope.generatedPasswordView = false;
        $scope.ftpPassword = randomPassword(16);
    };

    $scope.usePassword = function () {
        $(".ftpPasswordView").hide();
        $scope.generatedPasswordView = true;
    };

    $scope.toggleCustomQuota = function () {
        if (!$scope.enableCustomQuota) $scope.customQuotaSize = 0;
    };

});
/* Java script code to create account ends here */


/* Java script code to delete ftp account */


app.controller('deleteFTPAccount', function ($scope, $http) {

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
/* Java script code to delete ftp account ends here */


app.controller('listFTPAccounts', function ($scope, $http) {

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
