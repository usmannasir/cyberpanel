#!/usr/bin/env python2.7
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
    server_address = ('localhost', 1089)
    applicationPath = '/usr/local/CyberCP/postfixSenderPolicy/pid'


    def __init__(self, serv_addr):
        self.server_addr = serv_addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def setup_conn(self):

        logging.writeToFile('Starting CyberPanel Email Policy Server!')
        self.sock.bind(SetupConn.server_address)
        logging.writeToFile('CyberPanel Email Policy Server Successfully started!')

    def start_listening(self):
        self.sock.listen(1)
        while True:
            # Wait for a connection
            logging.writeToFile('Waiting For Connection!')
            connection, client_address = self.sock.accept()
            background = handle.HandleRequest(connection)
            background.start()
    def __del__(self):
        self.sock.close()
        logging.writeToFile('Closing open connections!')



def Main():
    writeToFile = open(SetupConn.applicationPath, 'w')
    writeToFile.write(str(os.getpid()))
    writeToFile.close()

    for sig in (SIGABRT, SIGINT, SIGTERM):
        signal(sig, cacheManager.cleanUP)

    listenConn = SetupConn(SetupConn.server_address)
    listenConn.setup_conn()
    listenConn.start_listening()


if __name__ == "__main__":
    Main()

