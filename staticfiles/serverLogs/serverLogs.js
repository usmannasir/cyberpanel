/**
 * Created by usman on 7/31/17.
 */


/* Java script code to read access log file */

app.controller('readAccessLogs', function ($scope, $http) {

    $scope.logFileLoading = false;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;


    var url = "/serverlogs/getLogsFromFile";

    var data = {
        type: "access"
    };

    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


    function ListInitialDatas(response) {


        if (response.data.logstatus == 1) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = false;
            $scope.couldNotFetchLogs = true;

            $scope.logsData = response.data.logsdata;


        } else {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;


        }


    }

    function cantLoadInitialDatas(response) {

        $scope.logFileLoading = true;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = false;

    }


    $scope.fetchLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/getLogsFromFile";

        var data = {
            type: "access"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.logstatus == 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = response.data.logsdata;


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

    $scope.clearLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/clearLogFile";

        var data = {
            fileName: "/usr/local/lsws/logs/access.log"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.cleanStatus === 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = "";


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

});

/* Java script code to read log file ends here */

/* Java script code to read error log file */

app.controller('readErrorLogs', function ($scope, $http) {

    $scope.logFileLoading = false;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;


    var url = "/serverlogs/getLogsFromFile";

    var data = {
        type: "error"
    };

    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


    function ListInitialDatas(response) {


        if (response.data.logstatus === 1) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = false;
            $scope.couldNotFetchLogs = true;

            $scope.logsData = response.data.logsdata;


        } else {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;


        }


    }

    function cantLoadInitialDatas(response) {

        $scope.logFileLoading = true;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = false;

    }


    $scope.fetchLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/getLogsFromFile";

        var data = {
            type: "error"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.logstatus == 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = response.data.logsdata;


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

    $scope.clearLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/clearLogFile";

        var data = {
            fileName: "/usr/local/lsws/logs/error.log"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.cleanStatus === 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = "";


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

});

/* Java script code to read log file ends here */

/* Java script code to read ftp log file */

app.controller('readFTPLogs', function ($scope, $http) {

    $scope.logFileLoading = false;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;


    var url = "/serverlogs/getLogsFromFile";

    var data = {
        type: "ftp"
    };

    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


    function ListInitialDatas(response) {


        if (response.data.logstatus === 1) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = false;
            $scope.couldNotFetchLogs = true;

            $scope.logsData = response.data.logsdata;


        } else {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;


        }


    }

    function cantLoadInitialDatas(response) {

        $scope.logFileLoading = true;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = false;

    }


    $scope.fetchLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/getLogsFromFile";

        var data = {
            type: "ftp"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.logstatus == 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = response.data.logsdata;


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

    $scope.clearLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/clearLogFile";

        var data = {
            fileName: "/var/log/messages"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.cleanStatus === 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = "";


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

});

/* Java script code to read log file ends here */

/* Java script code to read email log file */

app.controller('readEmailLogs', function ($scope, $http) {

    $scope.logFileLoading = false;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;


    var url = "/serverlogs/getLogsFromFile";

    var data = {
        type: "email"
    };

    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


    function ListInitialDatas(response) {


        if (response.data.logstatus === 1) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = false;
            $scope.couldNotFetchLogs = true;

            $scope.logsData = response.data.logsdata;


        } else {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;


        }


    }

    function cantLoadInitialDatas(response) {

        $scope.logFileLoading = true;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = false;

    }


    $scope.fetchLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/getLogsFromFile";

        var data = {
            type: "email"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.logstatus == 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = response.data.logsdata;


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

    $scope.clearLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/clearLogFile";

        var data = {
            fileName: "/var/log/maillog"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.cleanStatus === 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = "";


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

});

/* Java script code to read log file ends here */

/* Java script code to read modsec audit log file */

app.controller('modSecAuditLogs', function ($scope, $http) {

    $scope.logFileLoading = false;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;


    var url = "/serverlogs/getLogsFromFile";

    var data = {
        type: "modSec"
    };

    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


    function ListInitialDatas(response) {


        if (response.data.logstatus === 1) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = false;
            $scope.couldNotFetchLogs = true;

            $scope.logsData = response.data.logsdata;


        } else {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;


        }


    }

    function cantLoadInitialDatas(response) {

        $scope.logFileLoading = true;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = false;

    }


    $scope.fetchLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/getLogsFromFile";

        var data = {
            type: "modSec"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.logstatus == 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = response.data.logsdata;


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };
    $scope.clearLogs = function () {


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;


        var url = "/serverlogs/clearLogFile";

        var data = {
            fileName: "/usr/local/lsws/logs/auditmodsec.log"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.cleanStatus === 1) {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;

                $scope.logsData = "";


            } else {

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = false;

        }

    };

});

/* Java script code to read modsec audit log ends here */

app.controller('serverMail', function ($scope, $http) {

    $scope.cyberPanelLoading = true;
    $scope.installationDetailsForm = true;

    $scope.mailerSettings = function(){
        if($scope.mailer === 'SMTP'){
            $scope.installationDetailsForm = false;
        }else {
            $scope.installationDetailsForm = true;
        }
    };

    $scope.saveSMTPSettings = function () {
        $scope.cyberPanelLoading = false;

        var url = "/serverlogs/saveSMTPSettings";

        var data = {
            mailer: $scope.mailer,
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
                new PNotify({
                    title: 'Success',
                    text: 'Successfully saved.',
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
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

});

