#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import socket

import os
import accept_traffic as handle
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from signal import *
from cacheManager import cacheManager


class SetupConn:
    cleaningPath = '/home/cyberpanel/purgeCache'
    server_address = ('localhost', 1089)
    cleaning_server = ('localhost', 1090)
    applicationPath = '/usr/local/CyberCP/postfixSenderPolicy/pid'
    cleaningServerPID = '/usr/local/CyberCP/postfixSenderPolicy/cpid'


    def __init__(self, serv_addr):
        self.server_addr = serv_addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def setup_conn(self):
        logging.writeToFile('Starting CyberPanel Email Policy Server!')
        self.sock.bind(self.server_addr)
        logging.writeToFile('CyberPanel Email Policy Server Successfully started!')

    def start_listening(self):
        self.sock.listen(5)
        while True:
            # Wait for a connection
            if os.path.exists(SetupConn.cleaningPath):
                readFromFile = open(SetupConn.cleaningPath, 'r')
                command = readFromFile.read()
                cacheManager.handlePurgeRequest(command)
                readFromFile.close()
                os.remove(SetupConn.cleaningPath)

            connection, client_address = self.sock.accept()
            background = handle.HandleRequest(connection)
            background.start()


    def __del__(self):
        self.sock.close()
        logging.writeToFile('Closing open connections!')


def Main():

    for sig in (SIGABRT, SIGINT, SIGTERM):
        signal(sig, cacheManager.cleanUP)
    ###

    writeToFile = open(SetupConn.applicationPath, 'w')
    writeToFile.write(str(os.getpid()))
    writeToFile.close()

    listenConn = SetupConn(SetupConn.server_address)
    listenConn.setup_conn()
    listenConn.start_listening()


if __name__ == "__main__":
    Main()

