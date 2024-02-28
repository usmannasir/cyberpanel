newapp.controller('EmailDebuugerV2', function ($scope, $http, $timeout, $window) {

    $scope.cyberpanelLoading = true;
    $scope.ExecutionStatus = true;
    $scope.ReportStatus = true;


    $scope.RunServerLevelEmailChecks = function () {
        $scope.cyberpanelLoading = false;

        var url = "/emailPremium/RunServerLevelEmailChecks";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                reportFile = response.data.reportFile;
                statusFunc();


            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;

            new PNotify({
                title: 'Error',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    };

    function statusFunc() {
        $scope.cyberpanelLoading = false;
        $scope.ExecutionStatus = false;
        var url = "/emailPremium/statusFunc";

        var data = {
            statusFile: statusFile
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            if (response.data.status === 1) {
                if (response.data.abort === 1) {
                    $scope.functionProgress = {"width": "100%"};
                    $scope.functionStatus = response.data.currentStatus;
                    $scope.cyberpanelLoading = true;
                    $scope.ReadReport();
                    $timeout.cancel();
                } else {
                    $scope.functionProgress = {"width": response.data.installationProgress + "%"};
                    $scope.functionStatus = response.data.currentStatus;
                    $timeout(statusFunc, 3000);
                }

            } else {
                $scope.cyberpanelLoading = true;
                $scope.functionStatus = response.data.error_message;
                $scope.functionProgress = {"width": response.data.installationProgress + "%"};
                $timeout.cancel();
            }

        }

        function cantLoadInitialData(response) {
            $scope.functionProgress = {"width": response.data.installationProgress + "%"};
            $scope.functionStatus = 'Could not connect to server, please refresh this page.';
            $timeout.cancel();
        }
    }

    $scope.ReadReport = function () {

        if (reportFile === 'none') {
            return;
        }

        $scope.cyberpanelLoading = false;

        var url = "/emailPremium/ReadReport";

        var data = {
            reportFile: reportFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                var reportResult = JSON.parse(response.data.reportContent);

                if (reportResult.MailSSL === 1) {
                    $scope.MailSSL = 'Issued and Valid';
                } else {
                    $scope.MailSSL = 'Not issued or expired.'
                }
                var report = response.data.report;

                console.log(report);
                $scope.Port25 = report.Port25;
                $scope.Port587 = report.Port587;
                $scope.Port465 = report.Port465;
                $scope.Port110 = report.Port110;
                $scope.Port143 = report.Port143;
                $scope.Port993 = report.Port993;
                $scope.Port995 = report.Port995;
                //document.getElementById('MailSSLURL').href = 'https://' + report.serverHostName + ":" + report.port + '/cloudAPI/access?token=' + report.token + "&serverUserName=" + report.userName + '&redirect=/manageSSL/sslForMailServer';
                document.getElementById('MailSSLURLV2').href = '/manageSSL/V2/sslForMailServerV2';


                $scope.ReportStatus = false;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Error',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

    $scope.ResetEmailConfigurations = function () {
        $scope.cyberpanelLoading = false;

        var url = "/emailPremium/ResetEmailConfigurations";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                reportFile = response.data.reportFile;
                reportFile = 'none';
                statusFunc();


            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;

            new PNotify({
                title: 'Error',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    };

});

newapp.controller('emailDebuggerDomainLevelV2', function ($scope, $http, $timeout, $window) {
    $scope.cyberpanelLoading = true;
    $scope.ReportStatus = true;

    $scope.debugEmailForSite = function () {
        $scope.cyberpanelLoading = false;

        url = "/emailPremium/debugEmailForSite";

        var data = {
            websiteName: $scope.websiteName
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            $scope.status = response.data.status;
            $scope.message = response.data.error_message;
            $scope.ReportStatus = false;

        }

        function cantLoadInitialData(response) {
            $scope.cyberhosting = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }

    };

    $scope.fixMailSSL = function () {
        $scope.cyberpanelLoading = false;
        url = "/emailPremium/fixMailSSL";

        var data = {
            websiteName: $scope.websiteName
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success',
                    text: 'Successfully fixed.',
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

        function cantLoadInitialData(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }
    };

});