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
        host: $("#host").val(),
        port: $("#port").val(),
        username: $("#username").val(),
        ispwd: $("input[name=ispwd]:checked").val(),
        secret: $("#secret").val(),
        verifyPath: $("#verifyPath").text()
    }
    console.debug(options);
    if (remember) {
        store(options)
    }
    // if (check()) {
    //     openTerminal(options)
    // } else {
    //     for (var key in validResult) {
    //         if (!validResult[key]) {
    //             alert(errorMsg[key]);
    //             break;
    //         }
    //     }
    // }
    openTerminal(options)
}

connect();