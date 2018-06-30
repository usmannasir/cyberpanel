#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import mysqlUtilities as sql
import subprocess
import CyberCPLogFileWriter as logging
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


class FTPUtilities:


    # This function will only install FTP
    @staticmethod
    def installProFTPD():
        try:
            cmd = []


            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("proftpd-mysql")
            res = subprocess.call(cmd)
            if res == 1:
                print("###############################################")
                print("         Could not install ProFTPD              ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          ProFTPD Installed                     ")
                print("###############################################")
        except OSError,msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installProFTPD]")
            return 0
        except ValueError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installProFTPD]")
            return 0

        return 1

    @staticmethod
    def createFTPDataBaseinMariaDB(username,password):
        try:

            #Create DB
            #sql.mysqlUtilities.createDatabase("1qaz@9xvps", "ftp", username, password)

            #Add group
            cmd = []

            cmd.append("groupadd")
            cmd.append("-g")
            cmd.append("2001")
            cmd.append("ftpgroup")

            res = subprocess.call(cmd)
            if res == 1:
                print "Group adding failed"
            else:
                print "Group added"

            #Add user to group

            cmd = []

            cmd.append("useradd")
            cmd.append("-u")
            cmd.append("2001")
            cmd.append("-s")
            cmd.append("/bin/false")
            cmd.append("-d")
            cmd.append("/bin/null")
            cmd.append("-c")
            cmd.append("\"proftpd user\"")
            cmd.append("-g")
            cmd.append("ftpgroup")
            cmd.append("ftpuser")

            res = subprocess.call(cmd)
            if res == 1:
                print "User adding failed"
            else:
                print "User added"

            #query = "CREATE TABLE ftp_ftpuser (id int(10) unsigned NOT NULL auto_increment,userid varchar(32) NOT NULL default '',passwd varchar(32) NOT NULL default '',uid smallint(6) NOT NULL default '2001',gid smallint(6) NOT NULL default '2001',homedir varchar(255) NOT NULL default '',shell varchar(16) NOT NULL default '/sbin/nologin',count int(11) NOT NULL default '0',accessed datetime NOT NULL default '0000-00-00 00:00:00',modified datetime NOT NULL default '0000-00-00 00:00:00',PRIMARY KEY (id),UNIQUE KEY userid (userid)) ENGINE=MyISAM COMMENT='ProFTP user table';"
            #sql.mysqlUtilities.SendQuery(username,password,"ftp", query)

            #query = "CREATE TABLE ftpgroup (groupname varchar(16) NOT NULL default '',gid smallint(6) NOT NULL default '2001',members varchar(16) NOT NULL default '',KEY groupname (groupname)) ENGINE=MyISAM COMMENT='ProFTP group table';"
            #sql.mysqlUtilities.SendQuery(username, password, "ftp", query)

            #query = "INSERT INTO ftpgroup (groupname, gid, members) VALUES ('ftpgroup', '2001', 'ftp_ftpuser');"
            #sql.mysqlUtilities.SendQuery(username, password, "ftp", query)

            # File Write
            lines = open("/etc/proftpd.conf").readlines()
            data = open("/etc/proftpd.conf", "w")

            line1 = "\nLoadModule mod_sql.c\n"
            line2 = "LoadModule mod_sql_mysql.c\n\n"

            line3 = "SQLAuthTypes            Plaintext Crypt\n"
            line4 = "SQLAuthenticate         users groups\n\n"

            line5 = "SQLConnectInfo  cybercp@localhost "+username+" "+password+"\n"
            line6 = "SQLUserInfo     ftp_ftp_ftpuser userid passwd uid gid homedir shell\n"
            line7 = "SQLGroupInfo    ftp_ftpgroup groupname gid members\n\n"

            line8 = "SQLLog PASS updatecount\n"
            line9 = "SQLNamedQuery updatecount UPDATE \"count=count+1, accessed=now() WHERE userid='%u'\" ftp_ftpuser\n\n"

            line10 = "SQLLog  STOR,DELE modified\n"
            line11 = "SQLNamedQuery modified UPDATE \"modified=now() WHERE userid='%u'\" ftp_ftpuser"

            Auth0 = "\n#AuthPAMConfig\n"
            Auth1 = "#AuthOrder\n"
            for items in lines:
                if ((items.find("AuthPAMConfig") > -1)):
                    data.writelines(Auth0)
                    continue

                if ((items.find("AuthOrder") > -1)):
                    data.writelines(Auth1)
                    continue

                data.writelines(items)


            data.writelines(line1)
            data.writelines(line2)
            data.writelines(line3)
            data.writelines(line4)
            data.writelines(line5)
            data.writelines(line6)
            data.writelines(line7)
            data.writelines(line8)
            data.writelines(line9)
            data.writelines(line10)
            data.writelines(line11)

            data.close()

            #File Write End

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with proftpd config file [createFTPDataBaseinMariaDB]]")
            return 0
        return 1

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
                print "Permissions not changed."
            else:
                print "User permissions setted."

            query = "INSERT INTO ftp_ftpuser (userid,passwd,homedir) VALUES ('" + username + "'" +","+"'"+password+"'"+","+"'"+path+"'"+");"
            print query
            sql.mysqlUtilities.SendQuery(udb,upass, "ftp", query)

        except BaseException, msg:
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
                print "Permissions not changed."
                return 0
            else:
                print "User permissions setted."



            command = "sudo chown -R nobody:cyberpanel " + directory

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                return 0
            else:
                return 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [createNewFTPAccount]")
            return 0

        return 1

    @staticmethod
    def ftpFunctions(path,externalApp):
        try:
            FNULL = open(os.devnull, 'w')

            if not os.path.exists(path):
                os.makedirs(path)

            command = "chown " + externalApp + ":" + externalApp + " " + path
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            return 1,'None'

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [ftpFunctions]")
            return 0, str(msg)

    @staticmethod
    def submitFTPCreation(domainName, userName, password, path, owner):
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

            hash = hashlib.md5()
            hash.update(password)

            admin = Administrator.objects.get(userName=owner)

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

            print "1,None"
            return 1,'None'

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [submitFTPCreation]")
            print "0,"+str(msg)
            return 0, str(msg)

    @staticmethod
    def submitFTPDeletion(ftpUsername):
        try:
            ftp = Users.objects.get(user=ftpUsername)
            ftp.delete()
            return 1,'None'
        except BaseException, msg:
            return 0, str(msg)

    @staticmethod
    def changeFTPPassword(userName, password):
        try:
            hash = hashlib.md5()
            hash.update(password)

            ftp = Users.objects.get(user=userName)
            ftp.password = hash.hexdigest()
            ftp.save()

            return 1, None
        except BaseException, msg:
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


    args = parser.parse_args()

    if args.function == "submitFTPCreation":
        FTPUtilities.submitFTPCreation(args.domainName,args.userName, args.password, args.path, args.owner)




if __name__ == "__main__":
    main()

