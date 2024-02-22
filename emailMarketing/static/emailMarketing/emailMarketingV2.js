var emailListURL = "/emailMarketing/" + $("#domainNamePageV2").text() + "/emailListsV2";
$("#emailListsV2").attr("href", emailListURL);
$("#emailListsChildV2").attr("href", emailListURL);

newapp.controller('createEmailListV2', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.cyberPanelLoading = true;
    $scope.goBackDisable = true;

    var statusFile;
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.cyberPanelLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    $scope.createEmailList = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.cyberPanelLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting to load email addresses..";


        url = "/emailMarketing/submitEmailList";

        var data = {
            domain: $("#domainNamePage").text(),
            path: $scope.path,
            listName: $scope.listName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.cyberPanelLoading = true;
                $scope.goBackDisable = false;

                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });

        }

    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: $("#domainNamePage").text()
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.cyberPanelLoading = true;
                    $scope.goBackDisable = false;
                    $scope.currentStatus = 'Emails successfully loaded.';
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.cyberPanelLoading = true;
                    $scope.goBackDisable = false;
                    $scope.currentStatus = response.data.error_message;


                }

            } else {
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });


        }


    }

    $scope.fetchEmails = function () {
        $scope.cyberPanelLoading = false;

        url = "/emailMarketing/fetchEmails";

        var data = {'listName': $scope.listName};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;

            if (response.data.status === 1) {
                $scope.records = JSON.parse(response.data.data);
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });

        }

    };


});
newapp.controller('composeMessageCTRLV2', function ($scope, $http) {

    $scope.cyberPanelLoading = true;
    $scope.saveTemplate = function (status, userName) {
        $scope.cyberPanelLoading = false;

        url = "/emailMarketing/saveEmailTemplate";

        var data = {
            name: $scope.name,
            subject: $scope.subject,
            fromName: $scope.fromName,
            fromEmail: $scope.fromEmail,
            replyTo: $scope.replyTo,
            emailMessage: $scope.emailMessage
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Template successfully saved.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });

        }

    };
});
newapp.controller('manageSMTPHostsCTRLV2', function ($scope, $http) {

    $scope.cyberPanelLoading = true;
    $scope.fetchSMTPHosts = function () {
        $scope.cyberPanelLoading = false;

        url = "/emailMarketing/fetchSMTPHosts";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;

            if (response.data.status === 1) {
                $scope.records = JSON.parse(response.data.data);
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });

        }

    };
    $scope.fetchSMTPHosts();
    $scope.saveSMTPHost = function (status, userName) {
        $scope.cyberPanelLoading = false;

        url = "/emailMarketing/saveSMTPHost";

        var data = {
            smtpHost: $scope.smtpHost,
            smtpPort: $scope.smtpPort,
            smtpUserName: $scope.smtpUserName,
            smtpPassword: $scope.smtpPassword
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;

            if (response.data.status === 1) {
                $scope.fetchSMTPHosts();
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully saved new SMTP host.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });

        }

    };
    $scope.smtpHostOperations = function (operation, id) {
        $scope.cyberPanelLoading = false;

        url = "/emailMarketing/smtpHostOperations";

        var data = {
            id: id,
            operation: operation
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            $scope.fetchSMTPHosts();

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: response.data.message,
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });

        }

    };
});