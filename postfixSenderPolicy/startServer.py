#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import socket
import os
from . import accept_traffic as handle
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from signal import *
from .cacheManager import cacheManager
import pwd
import grp


class SetupConn:
    cleaningPath = '/home/cyberpanel/purgeCache'
    applicationPath = '/usr/local/CyberCP/postfixSenderPolicy/pid'
    serverAddress = '/var/log/policyServerSocket'


    def __init__(self, serv_addr):
        self.server_addr = serv_addr
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def setup_conn(self):
        try:
            logging.writeToFile('Starting CyberPanel Email Policy Server!')

            try:
                os.unlink(self.server_addr)
            except OSError:
                if os.path.exists(self.server_addr):
                    raise

            self.sock.bind(self.server_addr)

            uid = pwd.getpwnam("postfix").pw_uid
            gid = grp.getgrnam("postfix").gr_gid
            os.chown(self.server_addr, uid, gid)
            os.chmod(self.server_addr, 0o755)

            logging.writeToFile('CyberPanel Email Policy Server Successfully started!')
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [SetupConn.setup_conn]')

    def start_listening(self):
        try:
            self.sock.listen(5)
            while True:
                try:
                    # Wait for a connection
                    if os.path.exists(SetupConn.cleaningPath):
                        readFromFile = open(SetupConn.cleaningPath, 'r')
                        command = readFromFile.read()
                        cacheManager.handlePurgeRequest(command)
                        readFromFile.close()
                        os.remove(SetupConn.cleaningPath)
                except:
                    pass

                connection, client_address = self.sock.accept()
                background = handle.HandleRequest(connection)
                background.start()
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [SetupConn.start_listening]')

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

    listenConn = SetupConn(SetupConn.serverAddress)
    listenConn.setup_conn()
    listenConn.start_listening()


if __name__ == "__main__":
    Main()

