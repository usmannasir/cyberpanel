#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from plogical import mysqlUtilities as sql
import subprocess
from plogical import CyberCPLogFileWriter as logging
import os
import shlex
import argparse
from websiteFunctions.models import Websites, ChildDomains
from loginSystem.models import Administrator
import pwd
import grp
import hashlib
from ftp.models import Users
from datetime import datetime
from plogical.processUtilities import ProcessUtilities


class FTPUtilities:

    @staticmethod
    def createNewFTPAccount(udb,upass,username,password,path):
        try:

            cmd = []
            cmd.append("chown")
            cmd.append("-R")
            cmd.append("ftpuser:2001")
            cmd.append(path)

            res = subprocess.call(cmd)
            if res == 1:
                print("Permissions not changed.")
            else:
                print("User permissions setted.")

            query = "INSERT INTO ftp_ftpuser (userid,passwd,homedir) VALUES ('" + username + "'" +","+"'"+password+"'"+","+"'"+path+"'"+");"
            print(query)
            sql.mysqlUtilities.SendQuery(udb,upass, "ftp", query)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [createNewFTPAccount]")
            return 0

        return 1

    @staticmethod
    def changePermissions(directory):

        try:

            command = "sudo chmod -R 775 " + directory

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                print("Permissions not changed.")
                return 0
            else:
                print("User permissions setted.")



            command = "sudo chown -R lscpd:cyberpanel " + directory

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                return 0
            else:
                return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [createNewFTPAccount]")
            return 0

        return 1

    @staticmethod
    def ftpFunctions(path,externalApp):
        try:

            command = 'mkdir %s' % (path)
            ProcessUtilities.executioner(command, externalApp)

            return 1,'None'

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [ftpFunctions]")
            return 0, str(msg)

    @staticmethod
    def submitFTPCreation(domainName, userName, password, path, owner, api = None):
        try:

            ## need to get gid and uid

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp
            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp

            uid = pwd.getpwnam(externalApp).pw_uid
            gid = grp.getgrnam(externalApp).gr_gid

            ## gid , uid ends

            path = path.lstrip("/")

            if path != 'None':
                path = "/home/" + domainName + "/public_html/" + path

                ## Security Check

                if path.find("..") > -1:
                    raise BaseException("Specified path must be inside virtual host home!")


                result = FTPUtilities.ftpFunctions(path, externalApp)

                if result[0] == 1:
                    pass
                else:
                    raise BaseException(result[1])

            else:
                path = "/home/" + domainName

            if os.path.islink(path):
                print("0, %s file is symlinked." % (path))
                return 0

            hash = hashlib.md5()
            hash.update(password.encode('utf-8'))

            admin = Administrator.objects.get(userName=owner)

            if api == '0':
                userName = admin.userName + "_" + userName


            if website.package.ftpAccounts == 0:
                user = Users(domain=website, user=userName, password=hash.hexdigest(), uid=uid, gid=gid,
                             dir=path,
                             quotasize=website.package.diskSpace,
                             status="1",
                             ulbandwidth=500000,
                             dlbandwidth=500000,
                             date=datetime.now())

                user.save()
            elif website.users_set.all().count() < website.package.ftpAccounts:
                user = Users(domain=website, user=userName, password=hash.hexdigest(), uid=uid, gid=gid,
                             dir=path, quotasize=website.package.diskSpace,
                             status="1",
                             ulbandwidth=500000,
                             dlbandwidth=500000,
                             date=datetime.now())

                user.save()

            else:
                raise BaseException("Exceeded maximum amount of FTP accounts allowed for the package.")

            print("1,None")
            return 1,'None'

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [submitFTPCreation]")
            print("0,"+str(msg))
            return 0, str(msg)

    @staticmethod
    def submitFTPDeletion(ftpUsername):
        try:
            ftp = Users.objects.get(user=ftpUsername)
            ftp.delete()
            return 1,'None'
        except BaseException as msg:
            return 0, str(msg)

    @staticmethod
    def changeFTPPassword(userName, password):
        try:
            hash = hashlib.md5()
            hash.update(password.encode('utf-8'))

            ftp = Users.objects.get(user=userName)
            ftp.password = hash.hexdigest()
            ftp.save()

            return 1, None
        except BaseException as msg:
            return 0,str(msg)

    @staticmethod
    def getFTPRecords(virtualHostName):
        try:
            website = Websites.objects.get(domain=virtualHostName)
            return website.users_set.all()
        except:
            ## There does not exist a zone for this domain.
            pass


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--domainName', help='Domain to create FTP for!')
    parser.add_argument('--userName', help='Username for FTP Account')
    parser.add_argument('--password', help='Password for FTP Account')
    parser.add_argument('--owner', help='FTP Account owner.')
    parser.add_argument('--path', help='Path to ftp directory!')
    parser.add_argument('--api', help='API Check!')


    args = parser.parse_args()

    if args.function == "submitFTPCreation":
        FTPUtilities.submitFTPCreation(args.domainName,args.userName, args.password, args.path, args.owner, args.api)




if __name__ == "__main__":
    main()