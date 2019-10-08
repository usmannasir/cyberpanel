/**
 * Created by usman on 9/5/17.
 */


/* Java script code to ADD Firewall Rules */

app.controller('firewallController', function ($scope, $http) {

    $scope.rulesLoading = true;
    $scope.actionFailed = true;
    $scope.actionSuccess = true;

    $scope.canNotAddRule = true;
    $scope.ruleAdded = true;
    $scope.couldNotConnect = true;
    $scope.rulesDetails = false;

    firewallStatus();

    populateCurrentRecords();

    $scope.addRule = function () {

        $scope.rulesLoading = false;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;


        url = "/firewall/addRule";


        var ruleName = $scope.ruleName;
        var ruleProtocol = $scope.ruleProtocol;
        var rulePort = $scope.rulePort;


        var data = {
            ruleName: ruleName,
            ruleProtocol: ruleProtocol,
            rulePort: rulePort,
            ruleIP: $scope.ruleIP,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.add_status == 1) {


                populateCurrentRecords();

                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = false;
                $scope.couldNotConnect = true;


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = false;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;


                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }

    };

    function populateCurrentRecords() {

        $scope.rulesLoading = false;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;


        url = "/firewall/getCurrentRules";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.fetchStatus === 1) {
                $scope.rules = JSON.parse(response.data.data);
                $scope.rulesLoading = true;
            }
            else {
                $scope.rulesLoading = true;
                $scope.errorMessage = response.data.error_message;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;

        }

    };

    $scope.deleteRule = function (id, proto, port, ruleIP) {

        $scope.rulesLoading = false;

        url = "/firewall/deleteRule";

        var data = {
            id: id,
            proto: proto,
            port: port,
            ruleIP: ruleIP
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.delete_status === 1) {


                populateCurrentRecords();
                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = false;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesLoading = true;
                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };


    $scope.reloadFireWall = function () {


        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;

        $scope.rulesLoading = false;

        url = "/firewall/reloadFirewall";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.reload_status == 1) {


                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };

    $scope.startFirewall = function () {


        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;

        $scope.rulesLoading = false;

        url = "/firewall/startFirewall";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.start_status == 1) {


                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesDetails = false;

                firewallStatus();


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };


    $scope.stopFirewall = function () {


        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;

        $scope.rulesLoading = false;

        url = "/firewall/stopFirewall";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.stop_status == 1) {


                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesDetails = true;

                firewallStatus();


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };


    function firewallStatus() {


        url = "/firewall/firewallStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status == 1) {

                if (response.data.firewallStatus == 1) {
                    $scope.rulesDetails = false;
                    $scope.status = "ON";
                }
                else {
                    $scope.rulesDetails = true;
                    $scope.status = "OFF";
                }
            }
            else {

                $scope.rulesDetails = true;
                $scope.status = "OFF";
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.couldNotConnect = false;


        }

    };


});

/* Java script code to ADD Firewall Rules */

/* Java script code to Secure SSH */

app.controller('secureSSHCTRL', function ($scope, $http) {

    $scope.couldNotSave = true;
    $scope.detailsSaved = true;
    $scope.couldNotConnect = true;
    $scope.secureSSHLoading = true;
    $scope.keyDeleted = true;
    $scope.keyBox = true;
    $scope.showKeyBox = false;
    $scope.saveKeyBtn = true;

    $scope.addKey = function () {
        $scope.saveKeyBtn = false;
        $scope.showKeyBox = true;
        $scope.keyBox = false;
    };


    getSSHConfigs();
    populateCurrentKeys();

    // Checking root login

    var rootLogin = false;

    $('#rootLogin').change(function () {
        rootLogin = $(this).prop('checked');
    });


    function getSSHConfigs() {

        $scope.couldNotSave = true;
        $scope.detailsSaved = true;
        $scope.couldNotConnect = true;
        $scope.secureSSHLoading = false;

        url = "/firewall/getSSHConfigs";

        var data = {
            type: "1",
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.sshPort = response.data.sshPort;

            if (response.data.permitRootLogin == 1) {
                $('#rootLogin').bootstrapToggle('on');
                $scope.couldNotSave = true;
                $scope.detailsSaved = true;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;
            }
            else {
                $scope.errorMessage = response.data.error_message;
                $scope.couldNotSave = true;
                $scope.detailsSaved = true;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;

        }

    }

    $scope.saveChanges = function () {

        $scope.couldNotSave = true;
        $scope.detailsSaved = true;
        $scope.couldNotConnect = true;
        $scope.secureSSHLoading = false;

        url = "/firewall/saveSSHConfigs";

        var data = {
            type: "1",
            sshPort: $scope.sshPort,
            rootLogin: rootLogin
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.saveStatus == 1) {
                $scope.couldNotSave = true;
                $scope.detailsSaved = false;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;
            }
            else {

                $scope.couldNotSave = false;
                $scope.detailsSaved = true;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotSave = true;
            $scope.detailsSaved = true;
            $scope.couldNotConnect = false;
            $scope.secureSSHLoading = true;

        }
    };


    function populateCurrentKeys() {

        url = "/firewall/getSSHConfigs";

        var data = {
            type: "2"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.records = JSON.parse(response.data.data);
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
        }


    }

    $scope.deleteKey = function (key) {

        $scope.secureSSHLoading = false;

        url = "/firewall/deleteSSHKey";

        var data = {
            key: key,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.delete_status === 1) {
                $scope.secureSSHLoading = true;
                $scope.keyDeleted = false;
                populateCurrentKeys();
            }
            else {
                $scope.couldNotConnect = false;
                $scope.secureSSHLoading = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
            $scope.secureSSHLoading = true;

        }


    }


    $scope.saveKey = function (key) {

        $scope.secureSSHLoading = false;

        url = "/firewall/addSSHKey";

        var data = {
            key: $scope.keyData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.add_status === 1) {
                $scope.secureSSHLoading = true;
                $scope.saveKeyBtn = true;
                $scope.showKeyBox = false;
                $scope.keyBox = true;


                populateCurrentKeys();
            }
            else {
                $scope.secureSSHLoading = true;
                $scope.saveKeyBtn = false;
                $scope.showKeyBox = true;
                $scope.keyBox = true;
                $scope.couldNotConnect = false;
                $scope.secureSSHLoading = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.secureSSHLoading = true;
            $scope.saveKeyBtn = false;
            $scope.showKeyBox = true;
            $scope.keyBox = true;
            $scope.couldNotConnect = false;
            $scope.secureSSHLoading = true;

        }


    }

});

/* Java script code to Secure SSH */

/* Java script code for ModSec */

app.controller('modSec', function ($scope, $http, $timeout, $window) {

    $scope.modSecNotifyBox = true;
    $scope.modeSecInstallBox = true;
    $scope.modsecLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.modSecSuccessfullyInstalled = true;
    $scope.installationFailed = true;


    $scope.installModSec = function () {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = true;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installModSec";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.installModSec === 1) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getRequestStatus();

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = true;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }

    };

    function getRequestStatus() {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installStatusModSec";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            }
            else {
                // Notifications
                $timeout.cancel();
                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = true;
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

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }

    ///// ModSec configs

    var modsecurity_status = false;
    var SecAuditEngine = false;
    var SecRuleEngine = false;


    $('#modsecurity_status').change(function () {
        modsecurity_status = $(this).prop('checked');
    });

    $('#SecAuditEngine').change(function () {
        SecAuditEngine = $(this).prop('checked');
    });


    $('#SecRuleEngine').change(function () {
        SecRuleEngine = $(this).prop('checked');
    });

    fetchModSecSettings();
    function fetchModSecSettings() {

        $scope.modsecLoading = false;

        $('#modsecurity_status').bootstrapToggle('off');
        $('#SecAuditEngine').bootstrapToggle('off');
        $('#SecRuleEngine').bootstrapToggle('off');

        url = "/firewall/fetchModSecSettings";

        var phpSelection = $scope.phpSelection;

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.fetchStatus === 1) {

                if (response.data.installed === 1) {

                    if (response.data.modsecurity === 1) {
                        $('#modsecurity_status').bootstrapToggle('on');
                    }
                    if (response.data.SecAuditEngine === 1) {
                        $('#SecAuditEngine').bootstrapToggle('on');
                    }
                    if (response.data.SecRuleEngine === 1) {
                        $('#SecRuleEngine').bootstrapToggle('on');
                    }

                    $scope.SecDebugLogLevel = response.data.SecDebugLogLevel;
                    $scope.SecAuditLogParts = response.data.SecAuditLogParts;
                    $scope.SecAuditLogRelevantStatus = response.data.SecAuditLogRelevantStatus;
                    $scope.SecAuditLogType = response.data.SecAuditLogType;

                }

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
        }

    }


    /////

    /// Save ModSec Changes

    $scope.failedToSave = true;
    $scope.successfullySaved = true;

    $scope.saveModSecConfigurations = function () {

        $scope.failedToSave = true;
        $scope.successfullySaved = true;
        $scope.modsecLoading = false;
        $scope.couldNotConnect = true;


        url = "/firewall/saveModSecConfigurations";

        var data = {
            modsecurity_status: modsecurity_status,
            SecAuditEngine: SecAuditEngine,
            SecRuleEngine: SecRuleEngine,
            SecDebugLogLevel: $scope.SecDebugLogLevel,
            SecAuditLogParts: $scope.SecAuditLogParts,
            SecAuditLogRelevantStatus: $scope.SecAuditLogRelevantStatus,
            SecAuditLogType: $scope.SecAuditLogType,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.failedToSave = true;
                $scope.successfullySaved = false;
                $scope.modsecLoading = true;
                $scope.couldNotConnect = true;

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToSave = false;
                $scope.successfullySaved = true;
                $scope.modsecLoading = true;
                $scope.couldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.failedToSave = true;
            $scope.successfullySaved = false;
            $scope.modsecLoading = true;
            $scope.couldNotConnect = true;
        }


    };

});


app.controller('modSecRules', function ($scope, $http) {

    $scope.modsecLoading = true;
    $scope.rulesSaved = true;
    $scope.couldNotConnect = true;
    $scope.couldNotSave = true;


    fetchModSecRules();
    function fetchModSecRules() {

        $scope.modsecLoading = false;
        $scope.modsecLoading = true;
        $scope.rulesSaved = true;
        $scope.couldNotConnect = true;


        url = "/firewall/fetchModSecRules";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.modSecInstalled === 1) {

                $scope.currentModSecRules = response.data.currentModSecRules;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
        }

    }

    $scope.saveModSecRules = function () {

        $scope.modsecLoading = false;
        $scope.rulesSaved = true;
        $scope.couldNotConnect = true;
        $scope.couldNotSave = true;


        url = "/firewall/saveModSecRules";

        var data = {
            modSecRules: $scope.currentModSecRules
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.saveStatus === 1) {

                $scope.rulesSaved = false;
                $scope.couldNotConnect = true;
                $scope.couldNotSave = true;

            } else {
                $scope.rulesSaved = true;
                $scope.couldNotConnect = true;
                $scope.couldNotSave = false;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
            $scope.rulesSaved = true;
            $scope.couldNotConnect = false;
            $scope.couldNotSave = true;
        }
    }

});


/* Java script code for ModSec */

app.controller('modSecRulesPack', function ($scope, $http, $timeout, $window) {

    $scope.modsecLoading = true;
    $scope.owaspDisable = true;
    $scope.comodoDisable = true;


    //

    $scope.installationQuote = true;
    $scope.couldNotConnect = true;
    $scope.installationFailed = true;
    $scope.installationSuccess = true;
    $scope.ruleFiles = true;

    /////

    var owaspInstalled = false;
    var comodoInstalled = false;
    var counterOWASP = 0;
    var counterComodo = 0;


    $('#owaspInstalled').change(function () {

        owaspInstalled = $(this).prop('checked');
        $scope.ruleFiles = true;

        if (counterOWASP !== 0) {
            if (owaspInstalled === true) {
                installModSecRulesPack('installOWASP');
            } else {
                installModSecRulesPack('disableOWASP')
            }
        }

        counterOWASP = counterOWASP + 1;
    });

    $('#comodoInstalled').change(function () {

        $scope.ruleFiles = true;
        comodoInstalled = $(this).prop('checked');

        if (counterComodo !== 0) {

            if (comodoInstalled === true) {
                installModSecRulesPack('installComodo');
            } else {
                installModSecRulesPack('disableComodo')
            }
        }

        counterComodo = counterComodo + 1;

    });


    getOWASPAndComodoStatus(true);
    function getOWASPAndComodoStatus(updateToggle) {

        $scope.modsecLoading = false;


        url = "/firewall/getOWASPAndComodoStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.modSecInstalled === 1) {

                if (updateToggle === true) {

                    if (response.data.owaspInstalled === 1) {
                        $('#owaspInstalled').bootstrapToggle('on');
                        $scope.owaspDisable = false;
                    } else {
                        $('#owaspInstalled').bootstrapToggle('off');
                        $scope.owaspDisable = true;
                    }
                    if (response.data.comodoInstalled === 1) {
                        $('#comodoInstalled').bootstrapToggle('on');
                        $scope.comodoDisable = false;
                    } else {
                        $('#comodoInstalled').bootstrapToggle('off');
                        $scope.comodoDisable = true;
                    }
                } else {

                    if (response.data.owaspInstalled === 1) {
                        $scope.owaspDisable = false;
                    } else {
                        $scope.owaspDisable = true;
                    }
                    if (response.data.comodoInstalled === 1) {
                        $scope.comodoDisable = false;
                    } else {
                        $scope.comodoDisable = true;
                    }
                }

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
        }

    }

    /////

    function installModSecRulesPack(packName) {

        $scope.modsecLoading = false;

        url = "/firewall/installModSecRulesPack";

        var data = {
            packName: packName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.installStatus === 1) {

                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = true;
                $scope.installationSuccess = false;

                getOWASPAndComodoStatus(false);

            } else {
                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = false;
                $scope.installationSuccess = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;

            //

            $scope.installationQuote = true;
            $scope.couldNotConnect = false;
            $scope.installationFailed = true;
            $scope.installationSuccess = true;
        }


    }

    /////

    $scope.fetchRulesFile = function (packName) {

        $scope.modsecLoading = false;
        $scope.ruleFiles = false;
        $scope.installationQuote = true;
        $scope.couldNotConnect = true;
        $scope.installationFailed = true;
        $scope.installationSuccess = true;

        url = "/firewall/getRulesFiles";

        var data = {
            packName: packName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.fetchStatus === 1) {
                $scope.records = JSON.parse(response.data.data);
                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = true;
                $scope.installationSuccess = false;

            }
            else {
                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = false;
                $scope.installationSuccess = true;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
            $scope.installationQuote = true;
            $scope.couldNotConnect = false;
            $scope.installationFailed = true;
            $scope.installationSuccess = true;
        }

    };


    $scope.removeRuleFile = function (fileName, packName, status) {

        $scope.modsecLoading = false;


        url = "/firewall/enableDisableRuleFile";

        var data = {
            packName: packName,
            fileName: fileName,
            status: status
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.saveStatus === 1) {

                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = true;
                $scope.installationSuccess = false;

                $scope.fetchRulesFile(packName);

            } else {
                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = false;
                $scope.installationSuccess = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;

            //

            $scope.installationQuote = true;
            $scope.couldNotConnect = false;
            $scope.installationFailed = true;
            $scope.installationSuccess = true;
        }

    }


});


/* Java script code for ModSec */


/* Java script code for CSF */

app.controller('csf', function ($scope, $http, $timeout, $window) {

    $scope.csfLoading = true;
    $scope.modeSecInstallBox = true;
    $scope.modsecLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.modSecSuccessfullyInstalled = true;
    $scope.installationFailed = true;


    $scope.installCSF = function () {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installCSF";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.installStatus === 1) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getRequestStatus();

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = true;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }

    };
    function getRequestStatus() {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installStatusCSF";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            }
            else {
                // Notifications
                $timeout.cancel();
                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = true;
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

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }


    // After installation

    var currentMain = "generalLI";
    var currentChild = "general";

    $scope.activateTab = function (newMain, newChild) {
        $("#" + currentMain).removeClass("ui-tabs-active");
        $("#" + currentMain).removeClass("ui-state-active");

        $("#" + newMain).addClass("ui-tabs-active");
        $("#" + newMain).addClass("ui-state-active");

        $('#' + currentChild).hide();
        $('#' + newChild).show();

        currentMain = newMain;
        currentChild = newChild;
    };


    $scope.removeCSF = function () {

        $scope.csfLoading = false;


        url = "/firewall/removeCSF";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;


            if (response.data.installStatus === 1) {

                new PNotify({
                    title: 'Successfully removed!',
                    text: 'CSF successfully removed from server, refreshing page in 3 seconds..',
                    type: 'success'
                });

                $timeout(function () {
                    $window.location.reload();
                }, 3000);

            }
            else {
                new PNotify({
                    title: 'Operation failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {

            new PNotify({
                title: 'Operation failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    //////// Fetch settings

    //
    var testingMode = false;
    var testingCounter = 0;


    $('#testingMode').change(function () {
        testingMode = $(this).prop('checked');

        if (testingCounter !== 0) {

            if (testingMode === true) {
                $scope.changeStatus('testingMode', 'enable');
            } else {
                $scope.changeStatus('testingMode', 'disable');
            }
        }
        testingCounter = testingCounter + 1;
    });
    //

    //
    var firewallStatus = false;
    var firewallCounter = 0;


    $('#firewallStatus').change(function () {
        firewallStatus = $(this).prop('checked');

        if (firewallCounter !== 0) {

            if (firewallStatus === true) {
                $scope.changeStatus('csf', 'enable');
            } else {
                $scope.changeStatus('csf', 'disable');
            }
        }
        firewallCounter = firewallCounter + 1;
    });
    //


    $scope.fetchSettings = function () {

        $scope.csfLoading = false;

        $('#testingMode').bootstrapToggle('off');
        $('#firewallStatus').bootstrapToggle('off');

        url = "/firewall/fetchCSFSettings";


        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.fetchStatus === 1) {

                new PNotify({
                    title: 'Successfully fetched!',
                    text: 'CSF settings successfully fetched.',
                    type: 'success'
                });

                if (response.data.testingMode === 1) {
                    $('#testingMode').bootstrapToggle('on');
                }
                if (response.data.firewallStatus === 1) {
                    $('#firewallStatus').bootstrapToggle('on');
                }

                $scope.tcpIN = response.data.tcpIN;
                $scope.tcpOUT = response.data.tcpOUT;
                $scope.udpIN = response.data.udpIN;
                $scope.udpOUT = response.data.udpOUT;
            } else {

                new PNotify({
                    title: 'Failed to load!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };
    $scope.fetchSettings();


    $scope.changeStatus = function (controller, status) {

        $scope.csfLoading = false;


        url = "/firewall/changeStatus";


        var data = {
            controller: controller,
            status: status
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied.',
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
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };

    $scope.modifyPorts = function (protocol) {

        $scope.csfLoading = false;

        var ports;

        if (protocol === 'TCP_IN') {
            ports = $scope.tcpIN;
        } else if (protocol === 'TCP_OUT') {
            ports = $scope.tcpOUT;
        } else if (protocol === 'UDP_IN') {
            ports = $scope.udpIN;
        } else if (protocol === 'UDP_OUT') {
            ports = $scope.udpOUT;
        }


        url = "/firewall/modifyPorts";


        var data = {
            protocol: protocol,
            ports: ports
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied.',
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
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };

    $scope.modifyIPs = function (mode) {

        $scope.csfLoading = false;

        var ipAddress;

        if (mode === 'allowIP') {
            ipAddress = $scope.allowIP;
        } else if (mode === 'blockIP') {
            ipAddress = $scope.blockIP;
        }


        url = "/firewall/modifyIPs";


        var data = {
            mode: mode,
            ipAddress: ipAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied.',
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
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };

});