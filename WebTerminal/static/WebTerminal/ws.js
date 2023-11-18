function WSSHClient() {
};

WSSHClient.prototype._generateEndpoint = function () {
    var protocol = 'wss://';

    var host = window.location.host.split(':')[0];
    var endpoint = protocol + host + ':5678';
    return endpoint;
};

WSSHClient.prototype.connect = function (options) {
    var endpoint = this._generateEndpoint();

    if (window.WebSocket) {
        this._connection = new WebSocket(endpoint);
    }
    else if (window.MozWebSocket) {
        this._connection = MozWebSocket(endpoint);
    }
    else {
        options.onError('WebSocket Not Supported');
        return;
    }

    this._connection.onerror = function (evt) {
        options.onError(evt);
    };

    this._connection.onopen = function () {
        options.onConnect();
    };

    this._connection.onmessage = function (evt) {
        var data = evt.data.toString()
        options.onData(data);
    };


    this._connection.onclose = function (evt) {
        options.onClose(evt);
    };
};

WSSHClient.prototype.send = function (data) {
    this._connection.send(JSON.stringify(data));
};

WSSHClient.prototype.sendInitData = function (options) {
    var data = {
        hostname: options.host,
        port: options.port,
        username: options.username,
        ispwd: options.ispwd,
        secret: options.secret
    };
    this._connection.send(JSON.stringify({"tp": "init", "data": options}))
}

WSSHClient.prototype.sendClientData = function (data) {
    this._connection.send(JSON.stringify({"tp": "client", "data": data, 'verifyPath': $("#verifyPath").text(), 'password': $("#password").text()}))
}

var client = new WSSHClient();
