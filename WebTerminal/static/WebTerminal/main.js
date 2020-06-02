var charWidth = 6.2;
var charHeight = 15.2;

/**
 * for full screen
 * @returns {{w: number, h: number}}
 */
function getTerminalSize() {
    var width = window.innerWidth;
    var height = window.innerHeight;
    return {
        w: Math.floor(width / charWidth),
        h: Math.floor(height / charHeight)
    };
}



function openTerminal(options) {
    if (!$.isEmptyObject($('.terminal')[0])) {
        alert("Please refresh this page.");
        return
    }

    var client = new WSSHClient();
    var term = new Terminal({cols: 120, rows: 30, screenKeys: true, useStyle: true});
    term.on('data', function (data) {
        client.sendClientData(data);
    });
    term.open();
    $('.terminal').detach().appendTo('#term');
    $("#term").show();
    term.write('Connecting...' + '\r\n');

    client.connect({
        onError: function (error) {
            term.write('Error connecting to backend.\r\n');
            //term.destroy();
        },
        onConnect: function () {
            client.sendInitData(options);
            term.write('connection established..\r\n');
        },
        onClose: function (e) {
            term.write("\r\nconnection closed.")
            //term.destroy();
        },
        onData: function (data) {
            term.write(data);
        }
    })

}

function store(options) {
    window.localStorage.host = options.host;
    window.localStorage.port = options.port;
    window.localStorage.username = options.username;
    window.localStorage.ispwd = options.ispwd;
    window.localStorage.secret = options.secret
}

function check() {
    return validResult["host"] && validResult["port"] && validResult["username"];
}

function connect() {
    var remember = $("#remember").is(":checked");
    var options = {
        verifyPath: $("#verifyPath").text(),
        password: $("#password").text()
    };
    if (remember) {
        store(options)
    }
    openTerminal(options)
}

app.controller('webTerminal', function ($scope, $http, $window) {

    $scope.cyberpanelLoading = true;

    connect();
    $scope.restartSSH = function (name) {
        $scope.cyberpanelLoading = false;

        url = "/Terminal/restart";

        var data = {
            name: name
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully restarted SSH server, refreshing the page now..',
                    type: 'success'
                });
                $window.location.href = '/Terminal/';
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

});