/**
 * Created by usman on 8/4/17.
 */


/* Java script code to create account */
app.controller('createFTPAccount', function ($scope, $http) {

    // Initialize all ng-hide variables to hide alerts on page load
    $scope.ftpLoading = false;
    $scope.ftpDetails = true;
    $scope.canNotCreateFTP = true;
    $scope.successfullyCreatedFTP = true;
    $scope.couldNotConnect = true;
    $scope.generatedPasswordView = true;

    $(document).ready(function () {
        $( ".ftpDetails" ).hide();
        $( ".ftpPasswordView" ).hide();
        
        // Check if select2 is available
        if ($.fn.select2) {
            $('.create-ftp-acct-select').select2();
            
            $('.create-ftp-acct-select').on('select2:select', function (e) {
                var data = e.params.data;
                $scope.ftpDomain = data.text;
                $( ".ftpDetails" ).show();
            });
        } else {
            // Fallback for regular select
            $('.create-ftp-acct-select').on('change', function (e) {
                $scope.ftpDomain = $(this).val();
                $scope.$apply();
                $( ".ftpDetails" ).show();
            });
        }
    });
    
    $scope.showFTPDetails = function() {
        if ($scope.ftpDomain && $scope.ftpDomain !== "") {
            $(".ftpDetails").show();
            $scope.ftpDetails = false;
        } else {
            $(".ftpDetails").hide();
            $scope.ftpDetails = true;
        }
    };

    $scope.createFTPAccount = function () {

        $scope.ftpLoading = true;  // Show loading while creating
        $scope.ftpDetails = false;
        $scope.canNotCreateFTP = true;
        $scope.successfullyCreatedFTP = true;
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
                $scope.ftpLoading = false;  // Hide loading on success
                $scope.successfullyCreatedFTP = false;
                $scope.canNotCreateFTP = true;
                $scope.couldNotConnect = true;
                $scope.createdFTPUsername = ftpDomain + "_" + ftpUserName;
                
                // Also show PNotify if available
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Success!',
                        text: 'FTP account successfully created.',
                        type: 'success'
                    });
                }
            } else {
                $scope.ftpLoading = false;  // Hide loading on error
                $scope.canNotCreateFTP = false;
                $scope.successfullyCreatedFTP = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;
                
                // Also show PNotify if available
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Operation Failed!',
                        text: response.data.error_message,
                        type: 'error'
                    });
                }
            }
        }
        
        function cantLoadInitialDatas(response) {
            $scope.ftpLoading = false;  // Hide loading on connection error
            $scope.couldNotConnect = false;
            $scope.canNotCreateFTP = true;
            $scope.successfullyCreatedFTP = true;
            
            // Also show PNotify if available
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Operation Failed!',
                    text: 'Could not connect to server, please refresh this page',
                    type: 'error'
                });
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


app.controller('listFTPAccounts', function ($scope, $http, ) {

    $scope.recordsFetched = true;
    $scope.passwordChanged = true;
    $scope.canNotChangePassword = true;
    $scope.couldNotConnect = true;
    $scope.ftpLoading = false;
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
        $scope.ftpLoading = false;  // Don't show loading when opening password dialog
        $scope.changePasswordBox = false;
        $scope.notificationsBox = true;
        $scope.ftpUsername = ftpUsername;
        globalFTPUsername = ftpUsername;

    };

    $scope.changePasswordBtn = function () {

        $scope.ftpLoading = true;  // Show loading while changing password


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
                $scope.ftpLoading = false;  // Hide loading when done
                $scope.domainFeteched = $scope.selectedDomain;

            } else {
                $scope.notificationsBox = false;
                $scope.canNotChangePassword = false;
                $scope.ftpLoading = false;  // Hide loading on error
                $scope.canNotChangePassword = false;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.notificationsBox = false;
            $scope.couldNotConnect = false;
            $scope.ftpLoading = false;  // Hide loading on connection error

        }

    };

    function populateCurrentRecords() {
        $scope.recordsFetched = true;
        $scope.passwordChanged = true;
        $scope.canNotChangePassword = true;
        $scope.couldNotConnect = true;
        $scope.ftpLoading = true;  // Show loading while fetching
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
                $scope.ftpLoading = false;  // Hide loading when done
                $scope.ftpAccounts = false;
                $scope.changePasswordBox = true;

                $scope.domainFeteched = $scope.selectedDomain;

            } else {
                $scope.notificationsBox = false;
                $scope.recordsFetched = true;
                $scope.passwordChanged = true;
                $scope.canNotChangePassword = true;
                $scope.couldNotConnect = true;
                $scope.ftpLoading = false;  // Hide loading on error
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
            $scope.ftpLoading = false;  // Hide loading on connection error
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



app.controller('Resetftpconf', function ($scope, $http, $timeout){
    $scope.Loading = true;
    $scope.NotifyBox = true;
    $scope.InstallBox = true;


    $scope.resetftp = function () {
        $scope.Loading = false;
        $scope.installationDetailsForm = true;
        $scope.InstallBox = false;



         url = "/ftp/resetftpnow";

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

        url = "/ftp/getresetstatus";

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