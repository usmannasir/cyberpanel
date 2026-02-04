/**
 * Email Limits page controller - ensures EmailLimitsNew is registered on CyberCP
 * even if main mailServer.js loads late or fails. Load this script in the
 * EmailLimits template so the page works reliably.
 */
(function () {
    'use strict';
    var app = (typeof window.app !== 'undefined') ? window.app : angular.module('CyberCP');
    if (!app) return;

    app.controller('EmailLimitsNew', function ($scope, $http) {
        $scope.creationBox = true;
        $scope.emailDetails = true;
        $scope.forwardLoading = false;
        $scope.forwardError = true;
        $scope.forwardSuccess = true;
        $scope.couldNotConnect = true;
        $scope.notifyBox = true;

        $scope.showEmailDetails = function () {
            $scope.creationBox = true;
            $scope.emailDetails = true;
            $scope.forwardLoading = true;
            $scope.forwardError = true;
            $scope.forwardSuccess = true;
            $scope.couldNotConnect = true;
            $scope.notifyBox = true;

            var url = "/email/getEmailsForDomain";
            var data = { domain: $scope.emailDomain };
            var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };

            $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

            function ListInitialDatas(response) {
                if (response.data.fetchStatus === 1) {
                    $scope.emails = JSON.parse(response.data.data);
                    $scope.creationBox = true;
                    $scope.emailDetails = false;
                    $scope.forwardLoading = false;
                    $scope.forwardError = true;
                    $scope.forwardSuccess = true;
                    $scope.couldNotConnect = true;
                    $scope.notifyBox = false;
                } else {
                    $scope.creationBox = true;
                    $scope.emailDetails = true;
                    $scope.forwardLoading = false;
                    $scope.forwardError = false;
                    $scope.forwardSuccess = true;
                    $scope.couldNotConnect = true;
                    $scope.notifyBox = false;
                    $scope.errorMessage = response.data.error_message;
                }
            }

            function cantLoadInitialDatas() {
                $scope.creationBox = true;
                $scope.emailDetails = true;
                $scope.forwardLoading = false;
                $scope.forwardError = true;
                $scope.forwardSuccess = true;
                $scope.couldNotConnect = false;
                $scope.notifyBox = false;
            }
        };

        $scope.selectForwardingEmail = function () {
            $scope.creationBox = false;
            $scope.emailDetails = false;
            $scope.forwardLoading = true;
            $scope.forwardError = true;
            $scope.forwardSuccess = true;
            $scope.couldNotConnect = true;
            $scope.notifyBox = true;

            var givenEmail = $scope.selectedEmail;
            if ($scope.emails) {
                for (var i = 0; i < $scope.emails.length; i++) {
                    if ($scope.emails[i].email === givenEmail) {
                        $scope.numberofEmails = $scope.emails[i].numberofEmails;
                        $scope.duration = $scope.emails[i].duration;
                        break;
                    }
                }
            }
        };

        $scope.SaveChanges = function () {
            $scope.creationBox = false;
            $scope.emailDetails = false;
            $scope.forwardLoading = true;
            $scope.forwardError = true;
            $scope.forwardSuccess = true;
            $scope.couldNotConnect = true;
            $scope.notifyBox = true;

            var url = "/email/SaveEmailLimitsNew";
            var data = {
                numberofEmails: $scope.numberofEmails,
                source: $scope.selectedEmail,
                duration: $scope.duration
            };
            var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };

            $http.post(url, data, config).then(SaveListInitialDatas, SaveCantLoadInitialDatas);

            function SaveListInitialDatas(response) {
                if (response.data.status === 1) {
                    $scope.creationBox = false;
                    $scope.emailDetails = false;
                    $scope.forwardLoading = false;
                    $scope.forwardError = true;
                    $scope.forwardSuccess = true;
                    $scope.couldNotConnect = true;
                    $scope.notifyBox = true;
                    if (typeof PNotify === 'function') {
                        new PNotify({ title: 'Success!', text: 'Changes applied.', type: 'success' });
                    }
                    $scope.showEmailDetails();
                } else {
                    $scope.creationBox = false;
                    $scope.emailDetails = false;
                    $scope.forwardLoading = false;
                    $scope.forwardError = false;
                    $scope.forwardSuccess = true;
                    $scope.couldNotConnect = true;
                    $scope.notifyBox = false;
                    if (typeof PNotify === 'function') {
                        new PNotify({ title: 'Error!', text: response.data.error_message || 'Error', type: 'error' });
                    }
                }
            }

            function SaveCantLoadInitialDatas() {
                $scope.creationBox = true;
                $scope.emailDetails = true;
                $scope.forwardLoading = false;
                $scope.forwardError = true;
                $scope.forwardSuccess = true;
                $scope.couldNotConnect = false;
                $scope.notifyBox = false;
            }
        };
    });
})();
