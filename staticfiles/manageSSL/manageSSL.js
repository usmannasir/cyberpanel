/**
 * Created by usman on 9/26/17.
 */


/* Java script code to issue SSL */
app.controller('sslIssueCtrl', function ($scope, $http) {

    $scope.sslIssueCtrl = true;
    $scope.manageSSLLoading = true;
    $scope.issueSSLBtn = true;
    $scope.canNotIssue = true;
    $scope.sslIssued = true;
    $scope.couldNotConnect = true;
    $scope.sslDetails = null;

    $scope.showbtn = function () {
        $scope.issueSSLBtn = false;
        $scope.fetchSSLDetails();
    };

    $scope.fetchSSLDetails = function() {
        if (!$scope.virtualHost) return;
        
        var url = "/manageSSL/getSSLDetails";
        var data = {
            virtualHost: $scope.virtualHost
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(function(response) {
            if (response.data.status === 1) {
                $scope.sslDetails = response.data;
            } else {
                $scope.sslDetails = null;
                new PNotify({
                    title: 'Error',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }, function(response) {
            $scope.sslDetails = null;
            new PNotify({
                title: 'Error',
                text: 'Could not fetch SSL details',
                type: 'error'
            });
        });
    };

    $scope.issueSSL = function () {
        $scope.manageSSLLoading = false;

        var url = "/manageSSL/issueSSL";
        var data = {
            virtualHost: $scope.virtualHost,
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (response.data.SSL == 1) {
                $scope.sslIssueCtrl = true;
                $scope.manageSSLLoading = true;
                $scope.issueSSLBtn = false;
                $scope.canNotIssue = true;
                $scope.sslIssued = false;
                $scope.couldNotConnect = true;
                $scope.sslDomain = $scope.virtualHost;
                $scope.fetchSSLDetails(); // Refresh SSL details after issuing
                
                // Show success notification
                new PNotify({
                    title: 'Success',
                    text: 'SSL certificate successfully issued/renewed for ' + $scope.virtualHost,
                    type: 'success'
                });
            } else {
                $scope.sslIssueCtrl = true;
                $scope.manageSSLLoading = true;
                $scope.issueSSLBtn = false;
                $scope.canNotIssue = false;
                $scope.sslIssued = true;
                $scope.couldNotConnect = true;
                
                // Enhanced error handling
                $scope.errorMessage = response.data.error_message || 'SSL issuance failed';
                $scope.technicalDetails = response.data.technicalDetails || '';
                $scope.sslLogs = response.data.sslLogs || '';
                
                // Show detailed error notification
                var errorText = response.data.error_message || 'Unknown error occurred';
                if (response.data.technicalDetails) {
                    console.error('SSL Technical Details:', response.data.technicalDetails);
                }
                if (response.data.sslLogs) {
                    console.error('SSL Logs:', response.data.sslLogs);
                }
                
                new PNotify({
                    title: 'SSL Issuance Failed',
                    text: errorText,
                    type: 'error',
                    delay: 10000,  // Show for 10 seconds
                    buttons: {
                        closer: true,
                        sticker: true
                    }
                });
                
                // Check for specific error types and provide helpful suggestions
                if (errorText.toLowerCase().includes('rate limit')) {
                    $scope.errorSuggestion = 'You have hit the Let\'s Encrypt rate limit. Please wait before retrying or use a different domain.';
                } else if (errorText.toLowerCase().includes('dns')) {
                    $scope.errorSuggestion = 'Please ensure your domain DNS is properly configured and pointing to this server.';
                } else if (errorText.toLowerCase().includes('connection') || errorText.toLowerCase().includes('timeout')) {
                    $scope.errorSuggestion = 'Check your firewall settings and ensure port 80 is accessible from the internet.';
                } else if (errorText.toLowerCase().includes('authorization') || errorText.toLowerCase().includes('unauthorized')) {
                    $scope.errorSuggestion = 'Domain validation failed. Verify that this server is accessible via the domain name.';
                } else if (errorText.toLowerCase().includes('caa')) {
                    $scope.errorSuggestion = 'CAA DNS records are preventing SSL issuance. Update your DNS CAA records to allow Let\'s Encrypt.';
                } else if (errorText.toLowerCase().includes('challenge')) {
                    $scope.errorSuggestion = 'The ACME challenge failed. Ensure the .well-known/acme-challenge path is accessible.';
                }
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.sslIssueCtrl = true;
            $scope.manageSSLLoading = true;
            $scope.issueSSLBtn = false;
            $scope.canNotIssue = true;
            $scope.sslIssued = true;
            $scope.couldNotConnect = false;
            
            // Show connection error
            new PNotify({
                title: 'Connection Error',
                text: 'Could not connect to the server. Please check your connection and try again.',
                type: 'error'
            });
        }
    };

});
/* Java script code to issue SSL ends here */

/* Java script code to issue SSL V2 */
app.controller('sslIssueCtrlV2', function ($scope, $http) {

    $scope.manageSSLLoading = true;
    $scope.sslDetails = null;

    $scope.showbtn = function () {
        $scope.issueSSLBtn = false;
        $scope.fetchSSLDetails();
    };

    $scope.fetchSSLDetails = function() {
        if (!$scope.virtualHost) return;
        
        var url = "/manageSSL/getSSLDetails";
        var data = {
            virtualHost: $scope.virtualHost
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(function(response) {
            if (response.data.status === 1) {
                $scope.sslDetails = response.data;
            } else {
                $scope.sslDetails = null;
                new PNotify({
                    title: 'Error',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }, function(response) {
            $scope.sslDetails = null;
            new PNotify({
                title: 'Error',
                text: 'Could not fetch SSL details',
                type: 'error'
            });
        });
    };

    $scope.issueSSL = function () {
        $scope.manageSSLLoading = false;

        var url = "/manageSSL/v2IssueSSL";
        var data = {
            virtualHost: $scope.virtualHost,
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.manageSSLLoading = true;
            if (response.data.SSL === 1) {
                $scope.sslStatus = 'Issued.';
                $scope.sslLogs = response.data.sslLogs;
                $scope.fetchSSLDetails(); // Refresh SSL details after issuing
            } else {
                $scope.sslStatus = 'Failed.';
                $scope.sslLogs = response.data.sslLogs;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.sslIssueCtrl = true;
            $scope.manageSSLLoading = true;
            $scope.issueSSLBtn = false;
            $scope.canNotIssue = true;
            $scope.sslIssued = true;
            $scope.couldNotConnect = false;
        }
    };
});
/* Java script code to issue SSL V2 ends here */


/* Java script code to issue SSL for hostname */
app.controller('sslIssueForHostNameCtrl', function ($scope, $http) {

    $scope.sslIssueCtrl = true;
    $scope.manageSSLLoading = true;
    $scope.issueSSLBtn = true;
    $scope.canNotIssue = true;
    $scope.sslIssued = true;
    $scope.couldNotConnect = true;

    $scope.showbtn = function () {
        $scope.issueSSLBtn = false;
    };


    $scope.issueSSL = function () {
        $scope.manageSSLLoading = false;

        var url = "/manageSSL/obtainHostNameSSL";


        var data = {
            virtualHost: $scope.virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.SSL == 1) {

                $scope.sslIssueCtrl = true;
                $scope.manageSSLLoading = true;
                $scope.issueSSLBtn = false;
                $scope.canNotIssue = true;
                $scope.sslIssued = false;
                $scope.couldNotConnect = true;

                $scope.sslDomain = $scope.virtualHost;


            } else {
                $scope.sslIssueCtrl = true;
                $scope.manageSSLLoading = true;
                $scope.issueSSLBtn = false;
                $scope.canNotIssue = false;
                $scope.sslIssued = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
            $scope.sslIssueCtrl = true;
            $scope.manageSSLLoading = true;
            $scope.issueSSLBtn = false;
            $scope.canNotIssue = true;
            $scope.sslIssued = true;
            $scope.couldNotConnect = false;

        }


    };

});
/* Java script code to issue SSL for hostname */


/* Java script code to issue SSL for MailServer */
app.controller('sslIssueForMailServer', function ($scope, $http) {

    $scope.sslIssueCtrl = true;
    $scope.manageSSLLoading = true;
    $scope.issueSSLBtn = true;
    $scope.canNotIssue = true;
    $scope.sslIssued = true;
    $scope.couldNotConnect = true;

    $scope.showbtn = function () {
        $scope.issueSSLBtn = false;
    };


    $scope.issueSSL = function () {

        $scope.manageSSLLoading = false;

        var url = "/manageSSL/obtainMailServerSSL";


        var data = {
            virtualHost: $scope.virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.SSL === 1) {

                $scope.sslIssueCtrl = true;
                $scope.manageSSLLoading = true;
                $scope.issueSSLBtn = false;
                $scope.canNotIssue = true;
                $scope.sslIssued = false;
                $scope.couldNotConnect = true;

                $scope.sslDomain = $scope.virtualHost;


            } else {
                $scope.sslIssueCtrl = true;
                $scope.manageSSLLoading = true;
                $scope.issueSSLBtn = false;
                $scope.canNotIssue = false;
                $scope.sslIssued = true;
                $scope.couldNotConnect = true;
                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
            $scope.sslIssueCtrl = true;
            $scope.manageSSLLoading = true;
            $scope.issueSSLBtn = false;
            $scope.canNotIssue = true;
            $scope.sslIssued = true;
            $scope.couldNotConnect = false;

        }


    };

});
/* Java script code to issue SSL for MailServer */