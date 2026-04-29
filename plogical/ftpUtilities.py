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
    def get_domain_home_directory(domain_name):
        try:
            child = ChildDomains.objects.select_related('master').get(domain=domain_name)
            master_dom = child.master.domain
            rel = (child.path or '').strip().strip('/')
            if rel:
                return os.path.abspath('/home/%s/%s' % (master_dom, rel))
        except ChildDomains.DoesNotExist:
            pass
        return os.path.abspath('/home/' + domain_name)

    @staticmethod
    def assert_ftp_raw_path_safe(raw):
        if raw is None or not str(raw).strip():
            return
        s = str(raw)
        dangerous_chars = [';', '|', '&', '$', '`', '\'', '"', '<', '>', '*', '?']
        if any(char in s for char in dangerous_chars):
            raise BaseException("Invalid path: Path contains dangerous characters")
        if '..' in s or '~' in s:
            raise BaseException("Invalid path: Path cannot contain '..' or '~'")

    @staticmethod
    def resolve_ftp_home_path(domain_name, raw_path):
        domain_home = FTPUtilities.get_domain_home_directory(domain_name)
        if raw_path is None:
            return domain_home
        raw = str(raw_path).strip()
        if raw == '' or raw == 'None':
            return domain_home
        FTPUtilities.assert_ftp_raw_path_safe(raw)
        if raw.startswith('/'):
            candidate = os.path.abspath(raw)
        else:
            candidate = os.path.abspath(os.path.join(domain_home, raw))
        dh = domain_home
        if candidate != dh and not candidate.startswith(dh + os.sep):
            raise BaseException("Security violation: Path must be within domain home directory")
        return candidate

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
            if os.path.exists(path):
                if not os.path.isdir(path):
                    return 0, "Specified path exists but is not a directory"
                command = 'chown -R %s:%s %s' % (externalApp, externalApp, path)
                ProcessUtilities.executioner(command, externalApp)
                return 1, 'None'
            command = 'mkdir -p %s' % (path)
            result = ProcessUtilities.executioner(command, externalApp)
            if result == 0:
                command = 'chown -R %s:%s %s' % (externalApp, externalApp, path)
                ProcessUtilities.executioner(command, externalApp)
                command = 'chmod 755 %s' % (path)
                ProcessUtilities.executioner(command, externalApp)
                return 1, 'None'
            return 0, "Failed to create directory: %s" % path
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [ftpFunctions]")
            return 0, str(msg)

    @staticmethod
    def submitFTPCreation(domainName, userName, password, path, owner, api = None):
        try:

            ## need to get gid and uid

            try:
                child = ChildDomains.objects.get(domain=domainName)
                website = child.master
                externalApp = child.master.externalApp
            except ChildDomains.DoesNotExist:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp

            uid = pwd.getpwnam(externalApp).pw_uid
            gid = grp.getgrnam(externalApp).gr_gid

            ## gid , uid ends

            if path and str(path).strip() and str(path).strip() != 'None':
                path = FTPUtilities.resolve_ftp_home_path(domainName, path)
                result = FTPUtilities.ftpFunctions(path, externalApp)
                if result[0] != 1:
                    raise BaseException(result[1])
            else:
                path = FTPUtilities.get_domain_home_directory(domainName)

            if os.path.islink(path):
                print("0, %s file is symlinked." % (path))
                return 0

            ProcessUtilities.decideDistro()

            if ProcessUtilities.ubuntu22Check == 1 or ProcessUtilities.alma9check:
                from crypt import crypt, METHOD_SHA512
                FTPPass = crypt(password, METHOD_SHA512)
            else:
                hash = hashlib.md5()
                hash.update(password.encode('utf-8'))
                FTPPass = hash.hexdigest()

            admin = Administrator.objects.get(userName=owner)


            if api == '0':
                userName = admin.userName + "_" + userName


            if website.package.ftpAccounts == 0:
                user = Users(domain=website, user=userName, password=FTPPass, uid=uid, gid=gid,
                             dir=path,
                             quotasize=website.package.diskSpace,
                             status="1",
                             ulbandwidth=500000,
                             dlbandwidth=500000,
                             date=datetime.now())

                user.save()
            elif website.users_set.all().count() < website.package.ftpAccounts:
                user = Users(domain=website, user=userName, password=FTPPass, uid=uid, gid=gid,
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
    def changeFTPDirectory(userName, raw_path, selected_domain):
        try:
            website = Websites.objects.get(domain=selected_domain)
            ftp = Users.objects.get(user=userName)
            if ftp.domain_id != website.id:
                raise BaseException("FTP user does not belong to the selected domain")
            externalApp = website.externalApp
            resolved = FTPUtilities.resolve_ftp_home_path(selected_domain, raw_path)
            if os.path.islink(resolved):
                logging.CyberCPLogFileWriter.writeToFile(
                    "FTP path is symlinked: %s" % resolved)
                raise BaseException("Cannot set FTP directory: Path is a symbolic link")
            result = FTPUtilities.ftpFunctions(resolved, externalApp)
            if result[0] != 1:
                raise BaseException("Path validation failed: " + result[1])
            ftp.dir = resolved
            ftp.save()
            return 1, None
        except Users.DoesNotExist:
            return 0, "FTP user not found"
        except Websites.DoesNotExist:
            return 0, "Domain not found"
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [changeFTPDirectory]")
            return 0, str(msg)

    @staticmethod
    def changeFTPPassword(userName, password):
        try:
            ProcessUtilities.decideDistro()
            if ProcessUtilities.ubuntu22Check == 1 or ProcessUtilities.alma9check:
                from crypt import crypt, METHOD_SHA512
                FTPPass = crypt(password, METHOD_SHA512)
            else:
                hash = hashlib.md5()
                hash.update(password.encode('utf-8'))
                FTPPass = hash.hexdigest()

            ftp = Users.objects.get(user=userName)
            ftp.password = FTPPass
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