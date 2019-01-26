#!/usr/local/CyberCP/bin/python2
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
#django.setup()
import plogical.CyberCPLogFileWriter as logging
import argparse
import subprocess
import shlex
from plogical.processUtilities import ProcessUtilities
from xml.etree import ElementTree

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
                    print items + ' ' + Container.packages[counter]
                else:
                    print items + ' ' + Container.packages[counter] + ' '
                counter = counter + 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def listPackages():
        try:
            counter = 0
            length = len(Container.users)
            for items in Container.packages:
                if (counter + 1) == length:
                    print items
                else:
                    print items + '\n'
                counter = counter + 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def userIDPackage(user):
        try:
            counter = 0
            for items in Container.users:
                if items == user:
                    print Container.packages[counter]
                    return
                counter = counter + 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def packageForUser(package):
        try:
            counter = 0
            for items in Container.packages:
                if items == package:
                    print Container.users[counter]
                    return
                counter = counter + 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Container Manager')
    parser.add_argument('--userid', help='User ID')
    parser.add_argument('--package', help='Package')
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




if __name__ == "__main__":
    main()

