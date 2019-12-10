#!/usr/local/CyberCP/bin/python
import sys
sys.path.append('/usr/local/CyberCP')
import plogical.CyberCPLogFileWriter as logging
import argparse
from plogical.mailUtilities import mailUtilities
from serverStatus.serverStatusUtil import ServerStatusUtil


class Container:
    packages = ['talksho']
    users = ['5001']

    @staticmethod
    def listAll():
        try:
            counter = 0
            length = len(Container.users)
            for items in Container.users:
                if (counter + 1) == length:
                    print(items + ' ' + Container.packages[counter])
                else:
                    print(items + ' ' + Container.packages[counter] + ' ')
                counter = counter + 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def listPackages():
        try:
            counter = 0
            length = len(Container.users)
            for items in Container.packages:
                if (counter + 1) == length:
                    print(items)
                else:
                    print(items + '\n')
                counter = counter + 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def userIDPackage(user):
        try:
            counter = 0
            for items in Container.users:
                if items == user:
                    print(Container.packages[counter])
                    return
                counter = counter + 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def packageForUser(package):
        try:
            counter = 0
            for items in Container.packages:
                if items == package:
                    print(Container.users[counter])
                    return
                counter = counter + 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def submitContainerInstall():
        try:

            mailUtilities.checkHome()

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Starting Packages Installation..\n", 1)

            command = 'sudo yum install -y libcgroup-tools'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'sudo systemctl enable cgconfig'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'sudo systemctl enable cgred'
            ServerStatusUtil.executioner(command, statusFile)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Container Manager')
    parser.add_argument('--userid', help='User ID')
    parser.add_argument('--package', help='Package')
    parser.add_argument('--function', help='Function')
    parser.add_argument('--list-all', help='List all users/packages.', action='store_true')
    parser.add_argument('--list-packages', help='List all packages.', action='store_true')


    args = vars(parser.parse_args())

    if args['userid']:
        Container.userIDPackage(args['userid'])
    elif args['package']:
        Container.packageForUser(args['package'])
    elif args['list_all']:
        Container.listAll()
    elif args['list_packages']:
        Container.listPackages()
    elif args['list_packages']:
        Container.listPackages()
    elif args["function"] == "submitContainerInstall":
        Container.submitContainerInstall()





if __name__ == "__main__":
    main()

