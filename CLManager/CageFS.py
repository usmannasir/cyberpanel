#!/usr/local/CyberCP/bin/python2
import sys
sys.path.append('/usr/local/CyberCP')
import plogical.CyberCPLogFileWriter as logging
import argparse
from plogical.mailUtilities import mailUtilities
from serverStatus.serverStatusUtil import ServerStatusUtil


class CageFS:
    packages = ['talksho']
    users = ['5001']

    @staticmethod
    def submitCageFSInstall():
        try:

            mailUtilities.checkHome()

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Starting Packages Installation..\n", 1)

            command = 'sudo yum install cagefs -y'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'sudo /usr/sbin/cagefsctl --init'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'sudo /usr/sbin/cagefsctl --update-etc'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'sudo /usr/sbin/cagefsctl --force-update'
            ServerStatusUtil.executioner(command, statusFile)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel CageFS Manager')
    parser.add_argument('--function', help='Function')


    args = vars(parser.parse_args())

    if args["function"] == "submitCageFSInstall":
        CageFS.submitCageFSInstall()





if __name__ == "__main__":
    main()

