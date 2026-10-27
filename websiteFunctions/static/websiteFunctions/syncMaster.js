/* Sync status is scoped to this deployment; lost polling never retries the write. */
app.controller('syncWebsite', function ($scope, $http, $timeout) {
    var timer, statusPath;
    $scope.cyberpanelLoading = true;
    $scope.installationProgress = true;
    $scope.goBackDisable = true;
    function csrf() {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
        return match ? decodeURIComponent(match[1]) : '';
    }
    function post(url, data) {
        return $http.post(url, data, {headers: {'X-CSRFToken': csrf()}});
    }
    function uncertain() {
        $scope.syncError = 'Status could not be confirmed. Sync may still be running. Check the server before starting another sync.';
        $scope.cyberpanelLoading = true;
    }
    function poll() {
        post('/websites/installWordpressStatus', {statusFile: statusPath}).then(function (response) {
            var data = response.data;
            if (data.error_message && data.error_message !== 'None') {
                $scope.syncError = Array.isArray(data.error_message) ? data.error_message.join('\n') : data.error_message;
                $scope.cyberpanelLoading = true;
                return;
            }
            $scope.currentStatus = data.currentStatus;
            var progress = Math.max(0, Math.min(100, Number(data.installationProgress) || 0));
            document.getElementById('installProgress').style.width = progress + '%';
            if (data.abort === 1) {
                $scope.cyberpanelLoading = true;
                if (data.installStatus === 1) {
                    $scope.currentStatus = data.currentStatus || 'Sync completed. The recovery backup is retained on the server.';
                    $scope.goBackDisable = false;
                } else {
                    $scope.syncError = 'Sync failed. Check the server and recovery backup before retrying.';
                }
                return;
            }
            timer = $timeout(poll, 2000);
        }, uncertain);
    }
    $scope.startSyncing = function () {
        if (!$scope.confirmed || $scope.syncSubmitted) return;
        if (!($scope.eraseCheck || $scope.dbCheck || $scope.copyChanged) || ($scope.eraseCheck && $scope.copyChanged)) {
            $scope.syncError = 'Select a database or content sync mode and only one content mode.';
            return;
        }
        $scope.syncSubmitted = true;
        $scope.syncError = '';
        $scope.cyberpanelLoading = false;
        $scope.currentStatus = 'Starting sync...';
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        post('/websites/startSync', {
            childDomain: document.getElementById('childDomain').textContent.trim(),
            eraseCheck: !!$scope.eraseCheck, dbCheck: !!$scope.dbCheck,
            copyChanged: !!$scope.copyChanged, confirmed: true
        }).then(function (response) {
            if (response.data.status !== 1 || !response.data.tempStatusPath) {
                $scope.syncError = response.data.error_message || 'Sync could not start.';
                $scope.cyberpanelLoading = true;
                return;
            }
            statusPath = response.data.tempStatusPath;
            poll();
        }, uncertain);
    };
    $scope.goBack = function () { if (!$scope.goBackDisable) window.location.reload(); };
    $scope.$on('$destroy', function () { if (timer) $timeout.cancel(timer); });
});
