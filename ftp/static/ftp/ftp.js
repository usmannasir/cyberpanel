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
        
        // Only use select2 if it's actually a function (avoids errors when Rocket Loader defers scripts)
        if (typeof $ !== 'undefined' && $ && typeof $.fn !== 'undefined' && typeof $.fn.select2 === 'function') {
            try {
                var $sel = $('.create-ftp-acct-select');
                if ($sel.length) {
                    $sel.select2();
                    $sel.on('select2:select', function (e) {
                        var data = e.params.data;
                        $scope.ftpDomain = data.text;
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
                $scope.$apply();
                $(".ftpDetails").show();
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

        // Enhanced path validation
        if (typeof path === 'undefined' || path === null) {
            path = "";
        } else {
            path = path.trim();
        }
        
        // Client-side path validation
        if (path && path !== "") {
            // Check for dangerous characters
            var dangerousChars = /[;&|$`'"<>*?~]/;
            if (dangerousChars.test(path)) {
                $scope.ftpLoading = false;
                $scope.canNotCreateFTP = false;
                $scope.successfullyCreatedFTP = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = "Invalid path: Path contains dangerous characters";
                return;
            }
            
            // Check for path traversal attempts
            if (path.indexOf("..") !== -1 || path.indexOf("~") !== -1) {
                $scope.ftpLoading = false;
                $scope.canNotCreateFTP = false;
                $scope.successfullyCreatedFTP = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = "Invalid path: Path cannot contain '..' or '~'";
                return;
            }
            
            // Check if path starts with slash (should be relative)
            if (path.startsWith("/")) {
                $scope.ftpLoading = false;
                $scope.canNotCreateFTP = false;
                $scope.successfullyCreatedFTP = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = "Invalid path: Path must be relative (not starting with '/')";
                return;
            }
        }

        var url = "/ftp/submitFTPCreation";


        var data = {
            ftpDomain: ftpDomain,
            ftpUserName: ftpUserName,
            passwordByPass: ftpPassword,
            path: path || '',
            api: '0',
            enableCustomQuota: $scope.enableCustomQuota || false,
            customQuotaSize: $scope.customQuotaSize || 0,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data && response.data.creatFTPStatus === 1) {
                $scope.ftpLoading = false;  // Hide loading on success
                $scope.successfullyCreatedFTP = false;
                $scope.canNotCreateFTP = true;
                $scope.couldNotConnect = true;
                $scope.createdFTPUsername = (response.data.createdFTPUsername != null && response.data.createdFTPUsername !== '') ? response.data.createdFTPUsername : (ftpDomain + '_' + ftpUserName);
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Success!', text: 'FTP account successfully created.', type: 'success' });
                }
            } else {
                $scope.ftpLoading = false;
                $scope.canNotCreateFTP = false;
                $scope.successfullyCreatedFTP = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = (response.data && response.data.error_message) ? response.data.error_message : 'Unknown error';
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Operation Failed!', text: $scope.errorMessage, type: 'error' });
                }
            }
        }
        
        function cantLoadInitialDatas(response) {
            $scope.ftpLoading = false;
            if ($scope.successfullyCreatedFTP !== false) {
                $scope.couldNotConnect = false;
                $scope.canNotCreateFTP = true;
                $scope.successfullyCreatedFTP = true;
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Operation Failed!', text: 'Could not connect to server, please refresh this page', type: 'error' });
                }
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

    // Quota management functions
    $scope.toggleCustomQuota = function() {
        if (!$scope.enableCustomQuota) {
            $scope.customQuotaSize = 0;
        }
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
                $scope.deleteFailure = false;
                $scope.deleteSuccess = true;
                $scope.couldNotConnect = true;
                $scope.deleteFTPButtonInit = true;
                $scope.errorMessage = (response.data && (response.data.error_message || response.data.errorMessage)) || 'Unknown error';
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
    $scope.ftpLoading = false;
    $scope.ftpAccounts = true;
    $scope.changePasswordBox = true;
    $scope.quotaManagementBox = true;
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

    // Quota management functions
    $scope.manageQuota = function (record) {
        $scope.recordsFetched = true;
        $scope.passwordChanged = true;
        $scope.canNotChangePassword = true;
        $scope.couldNotConnect = true;
        $scope.ftpLoading = false;
        $scope.quotaManagementBox = false;
        $scope.notificationsBox = true;
        $scope.ftpUsername = record.user;
        globalFTPUsername = record.user;
        
        // Set current quota info
        $scope.currentQuotaInfo = record.quotasize;
        $scope.packageQuota = record.package_quota;
        $scope.enableCustomQuotaEdit = record.custom_quota_enabled;
        $scope.customQuotaSizeEdit = record.custom_quota_size || 0;
    };

    $scope.toggleCustomQuotaEdit = function() {
        if (!$scope.enableCustomQuotaEdit) {
            $scope.customQuotaSizeEdit = 0;
        }
    };

    $scope.updateQuotaBtn = function () {
        $scope.ftpLoading = true;

        url = "/ftp/updateFTPQuota";

        var data = {
            ftpUserName: globalFTPUsername,
            customQuotaSize: parseInt($scope.customQuotaSizeEdit) || 0,
            enableCustomQuota: $scope.enableCustomQuotaEdit || false,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (response.data.updateQuotaStatus == 1) {
                $scope.notificationsBox = false;
                $scope.quotaUpdated = false;
                $scope.ftpLoading = false;
                $scope.domainFeteched = $scope.selectedDomain;
                
                // Refresh the records to show updated quota
                populateCurrentRecords();
                
                // Show success notification
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Success!',
                        text: 'FTP quota updated successfully.',
                        type: 'success'
                    });
                }
            } else {
                $scope.notificationsBox = false;
                $scope.quotaUpdateFailed = false;
                $scope.ftpLoading = false;
                $scope.errorMessage = response.data.error_message;
                
                // Show error notification
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Error!',
                        text: response.data.error_message,
                        type: 'error'
                    });
                }
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.notificationsBox = false;
            $scope.couldNotConnect = false;
            $scope.ftpLoading = false;
            
            // Show error notification
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Error!',
                    text: 'Could not connect to server.',
                    type: 'error'
                });
            }
        }
    };

});



app.controller('Resetftpconf', function ($scope, $http, $timeout, $window){
    $scope.Loading = true;
    $scope.NotifyBox = true;
    $scope.InstallBox = true;
    $scope.installationDetailsForm = false;
    $scope.alertType = '';
    $scope.errorMessage = '';

    $scope.resetftp = function () {
        $scope.Loading = false;
        $scope.installationDetailsForm = true;
        $scope.InstallBox = false;
        $scope.alertType = '';
        $scope.NotifyBox = true;

        var url = "/ftp/resetftpnow";
        var data = {};
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            if (response.data && response.data.status === 1) {
                $scope.NotifyBox = true;
                $scope.InstallBox = false;
                $scope.Loading = false;
                $scope.alertType = '';
                $scope.statusfile = response.data.tempStatusPath;
                $timeout(getRequestStatus, 1000);
            } else {
                $scope.errorMessage = (response.data && (response.data.error_message || response.data.errorMessage)) || 'Unknown error';
                $scope.alertType = 'failedToStart';
                $scope.NotifyBox = false;
                $scope.InstallBox = true;
                $scope.Loading = false;
            }
        }

        function cantLoadInitialData(response) {
            $scope.errorMessage = (response && response.data && (response.data.error_message || response.data.errorMessage)) || 'Could not connect to server. Please refresh this page.';
            $scope.alertType = 'couldNotConnect';
            $scope.NotifyBox = false;
            $scope.InstallBox = true;
            $scope.Loading = false;
            try {
                new PNotify({ title: 'Error!', text: $scope.errorMessage, type: 'error' });
            } catch (e) {}
        }
    }



    var statusPollPromise = null;
    function getRequestStatus() {
        $scope.NotifyBox = true;
        $scope.InstallBox = false;
        $scope.Loading = false;
        $scope.alertType = '';

        var url = "/ftp/getresetstatus";
        var data = { statusfile: $scope.statusfile };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (!response.data) return;
            if (response.data.abort === 0) {
                $scope.alertType = '';
                $scope.requestData = response.data.requestStatus || '';
                statusPollPromise = $timeout(getRequestStatus, 1000);
            } else {
                if (statusPollPromise) {
                    $timeout.cancel(statusPollPromise);
                    statusPollPromise = null;
                }
                $scope.NotifyBox = false;
                $scope.InstallBox = false;
                $scope.Loading = false;
                $scope.requestData = response.data.requestStatus || '';

                if (response.data.installed === 0) {
                    $scope.alertType = 'resetFailed';
                    $scope.errorMessage = response.data.error_message || 'Reset failed';
                } else {
                    $scope.alertType = 'success';
                    $timeout(function () { $window.location.reload(); }, 3000);
                }
            }
        }

        function cantLoadInitialDatas(response) {
            if (statusPollPromise) {
                $timeout.cancel(statusPollPromise);
                statusPollPromise = null;
            }
            $scope.alertType = 'couldNotConnect';
            $scope.errorMessage = (response && response.data && (response.data.error_message || response.data.errorMessage)) || 'Could not connect to server. Please refresh this page.';
            $scope.NotifyBox = false;
            $scope.InstallBox = true;
            $scope.Loading = false;
        }
    }
});