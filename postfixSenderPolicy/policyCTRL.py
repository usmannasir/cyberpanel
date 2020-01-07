#!/usr/local/CyberCP/bin/python
import subprocess, signal
import shlex
import argparse
import os
import sys
sys.path.append('/usr/local/CyberCP')
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


class policyCTRL:
    applicationPath = '/usr/local/CyberCP/postfixSenderPolicy/pid'
    cleaningPID = '/usr/local/CyberCP/postfixSenderPolicy/cpid'

    def prepareArguments(self):

        parser = argparse.ArgumentParser(description='CyberPanel Policy Control Parser!')
        parser.add_argument('function', help='Specific a operation to perform!')

        return parser.parse_args()

    def start(self):

        if os.path.exists(policyCTRL.applicationPath):
            self.stop()

        command = '/usr/local/CyberCP/postfixSenderPolicy/startServer.py'
        subprocess.Popen(shlex.split(command))

    def stop(self):

        path = policyCTRL.applicationPath
        if os.path.exists(path):
            pid = open(path, "r").readlines()[0]
            try:
                os.kill(int(pid), signal.SIGTERM)
            except BaseException as msg:
                logging.writeToFile(str(msg))



def main():

    policy = policyCTRL()
    args = policy.prepareArguments()

    ## Website functions

    if args.function == "start":
        policy.start()
    elif args.function == "stop":
        policy.stop()
    elif args.function == "restart":
        policy.stop()
        policy.start()

if __name__ == "__main__":
    main()