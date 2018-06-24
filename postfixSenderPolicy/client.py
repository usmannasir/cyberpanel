#!/usr/bin/env python2.7
import socket
import sys
sys.path.append('/usr/local/CyberCP')
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import argparse

class cacheClient:
    def __init__(self, serverAddr):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverAddr = serverAddr
        self.sock.connect(self.serverAddr)

    def sendData(self, data):
        self.sock.sendall(data)

    def __del__(self):
        self.sock.close()


    @staticmethod
    def handleCachePurgeRequest(command):
        try:
            serverAddr = ('localhost', 1089)
            cachePurger = cacheClient(serverAddr)
            cachePurger.sendData(command)
        except BaseException, msg:
            logging.writeToFile(str(msg))


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Email Policy Cache Cleaner')
    parser.add_argument('function', help='Specific a function to call!')


    args = parser.parse_args()

    if args.function == "hourlyCleanup":
        command = 'cyberpanelCleaner hourlyCleanup'
        cacheClient.handleCachePurgeRequest(command)
    elif args.function == 'monthlyCleanup':
        command = 'cyberpanelCleaner monthlyCleanup'
        cacheClient.handleCachePurgeRequest(command)


if __name__ == "__main__":
    main()