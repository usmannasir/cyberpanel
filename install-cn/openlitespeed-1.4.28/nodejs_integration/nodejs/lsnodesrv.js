//
//  Open LiteSpeed is an open source HTTP server.                           *
//  Copyright (C) 2014  LiteSpeed Technologies, Inc.                        *
//
//  Simple LiteSpeed Handler for Node.js http server
//  (1) accepting remote connection via domain socket
//  (2) dup2x accepted fd for Node.js - allow future communication
//  (3) open specified "JavaScript" from url.
//  (4) create a protected sandbox to execute the corresponding script.
//
//
//  NOTE:
//      Require LightSpeed Node.js C++ addon 
//          lsnodeapi.cc
//
//  Variable:
//      server_path       -  unix domain named file
//      LiteSpeedVerbose  -  turn on debug messages
//      LiteSpeedClientFd -  fd captured from read_fd
//

//
// var litespeed = require("./build/Release/lsnodeapi");
var litespeed = require("./build/Debug/lsnodeapi");

// var server_path = "LS_NODE";
var server_path = "/home/user/lsws/socket/LS_NODE";
var counter = 0;
var errorCounter = 0;
var serverTimeOut = 10000; // allow to run 10 sec timeout
var LiteSpeedClientFd = -1;
var LiteSpeedVerbose = 0;   // print out more debug message

var util = require("util");
var http = require("http"),
    net = require("net"),
    url = require("url"),
    path = require("path"),
    fs = require("fs"),
    vm = require("vm");

function dumpObj(x) {
    console.log(util.inspect(x, true, null));
}

//
//  Use the first parameter as server domain socket  path
//
if (process.argv.length > 2)
    server_path = process.argv[2];


function getFileExtension(filename) {
    var i = filename.lastIndexOf('.');
    return (i < 0) ? '' : filename.substr(i+1);
}

function try2dup(sockfd) {
    var code = litespeed.dup2x(LiteSpeedClientFd, sockfd);
    // console.log("dup2x " + LiteSpeedClientFd + ", " + sockfd);
    // console.log("ret = " + code);
    switch (code) {
        case sockfd:
            // good!
            LiteSpeedClientFd = -1;
            return;
        case -1:
            // I should abort here
            console.log("dup2x: Failed... return code " + code);
            process.abort();
            break;
        default:
            break;
    }
}

//
//  Setup HTTP server to process remote command
//
myhttp = http.createServer(function(request, response) {
    var uri = url.parse(request.url).pathname
                , filename = path.join(process.cwd(), uri);

    if (LiteSpeedClientFd != -1) {
        try2dup(response.socket._handle.fd) ;
    }

    fs.exists(filename, function(exists) {
        if(!exists) {
            console.log("Script file not found: " + filename);
            response.writeHead(404, {"Content-Type": "text/plain"});
            response.write("404 Not Found\n");
            response.end();
            return;
        }

        //
        //  If this path to directory -> default to lookup index.js
        //
        if (fs.statSync(filename).isDirectory()) filename += '/index.js';
        if (LiteSpeedVerbose)
            console.log("Script file: " + filename);

        //
        //  Execute the Server Side JavaScript
        //
        try {
            var sandbox = { "module": module, "response": response, "console": console  };
            var script_code = fs.readFileSync( filename ),
                script = vm.createScript( script_code );

            response.writeHead(200);
            script.runInNewContext( sandbox );
            counter++;
            if (LiteSpeedVerbose)
                console.log(counter + " " + errorCounter + " After Execute Script " + filename );
            response.end();
            return ;
        }
        catch (error) {
            response.writeHead(404, {"Content-Type": "text/plain"});
            response.write("SCRIPT FILE: [" + filename + "]\r\n");
            response.write(" ERROR CODE: [" + error.code + "]\r\n");
            response.write(" ERROR MSG : [" + error.message + ']\r\n');
            response.end();
            return ;
        }

    }); // End of the check path

});

//
//  Server connection - read fd from remote 
//
myhttp.on('connection', function (socket) {
    // socket.on('end', function() { console.log("CLIENT END"); });
    // socket.on('close', function() { console.log("CLIENT CLOSED"); });

    //
    //  read the new fd from domain socket
    //
    LiteSpeedClientFd = litespeed.readfd(socket._handle.fd);
    if (LiteSpeedVerbose)
        console.log("CLIENT FD " + LiteSpeedClientFd + " MY " + socket._handle.fd);
    if (LiteSpeedClientFd == -1) {
        console.log("PROBLEM TO READ CLIENT FD " + socket._handle.fd);
        console.log("Client closed too early or too slow... ");
        errorCounter++;
    } else {
        try2dup(socket._handle.fd);
    }
});

//
//  remove domain socket path
//
fs.unlink(server_path, function(err) {
    if (err) {
        // console.log("ERROR: in removing " + server_path + " err " + err);
        ;
    } else {
        if (LiteSpeedVerbose)
            console.log("Removed: " + server_path );
    }
});

myhttp.setTimeout (serverTimeOut);

if (LiteSpeedVerbose) {
    console.log("create HTTP server with timeout " + serverTimeOut + " sec.");
    console.log("Server path " + server_path);
}

//
//  Listen on the domain socket
//
myhttp.listen( server_path );

