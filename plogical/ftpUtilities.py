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
    def submitFTPCreation(domainName, userName, password, path, owner, api = None, customQuotaSize = None, enableCustomQuota = False):
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
                path = "/home/" + domainName + "/" + path

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

            # Determine quota size
            if enableCustomQuota and customQuotaSize and customQuotaSize > 0:
                # Use custom quota
                quotaSize = customQuotaSize
                customQuotaEnabled = True
            else:
                # Use package default
                quotaSize = website.package.diskSpace
                customQuotaEnabled = False

            if website.package.ftpAccounts == 0:
                user = Users(domain=website, user=userName, password=FTPPass, uid=uid, gid=gid,
                             dir=path,
                             quotasize=quotaSize,
                             status="1",
                             ulbandwidth=500000,
                             dlbandwidth=500000,
                             date=datetime.now(),
                             custom_quota_enabled=customQuotaEnabled,
                             custom_quota_size=customQuotaSize if customQuotaEnabled else 0)

                user.save()
            elif website.users_set.all().count() < website.package.ftpAccounts:
                user = Users(domain=website, user=userName, password=FTPPass, uid=uid, gid=gid,
                             dir=path, quotasize=quotaSize,
                             status="1",
                             ulbandwidth=500000,
                             dlbandwidth=500000,
                             date=datetime.now(),
                             custom_quota_enabled=customQuotaEnabled,
                             custom_quota_size=customQuotaSize if customQuotaEnabled else 0)

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

    @staticmethod
    def updateFTPQuota(ftpUsername, customQuotaSize, enableCustomQuota):
        """
        Update FTP user quota settings
        """
        try:
            ftp = Users.objects.get(user=ftpUsername)
            
            # Validate quota size
            if enableCustomQuota and customQuotaSize <= 0:
                return 0, "Custom quota size must be greater than 0"
            
            # Update quota settings
            ftp.custom_quota_enabled = enableCustomQuota
            if enableCustomQuota:
                ftp.custom_quota_size = customQuotaSize
                ftp.quotasize = customQuotaSize
            else:
                # Reset to package default
                ftp.custom_quota_size = 0
                ftp.quotasize = ftp.domain.package.diskSpace
            
            ftp.save()
            
            # Apply quota to filesystem if needed
            FTPUtilities.applyQuotaToFilesystem(ftp)
            
            return 1, "FTP quota updated successfully"
            
        except Users.DoesNotExist:
            return 0, "FTP user not found"
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [updateFTPQuota]")
            return 0, str(msg)

    @staticmethod
    def applyQuotaToFilesystem(ftp_user):
        """
        Apply quota settings to the filesystem level
        """
        try:
            import subprocess
            
            # Get the user's directory
            user_dir = ftp_user.dir
            if not user_dir or not os.path.exists(user_dir):
                return False, "User directory not found"
            
            # Convert quota from MB to KB for setquota command
            quota_kb = ftp_user.quotasize * 1024
            
            # Apply quota using setquota command
            # Note: This requires quota tools to be installed
            try:
                # Set both soft and hard limits to the same value
                subprocess.run([
                    'setquota', '-u', str(ftp_user.uid), 
                    f'{quota_kb}K', f'{quota_kb}K', 
                    '0', '0',  # inode limits (unlimited)
                    user_dir
                ], check=True, capture_output=True)
                
                logging.CyberCPLogFileWriter.writeToFile(f"Applied quota {quota_kb}KB to user {ftp_user.user} in {user_dir}")
                return True, "Quota applied successfully"
                
            except subprocess.CalledProcessError as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Failed to apply quota: {e}")
                return False, f"Failed to apply quota: {e}"
            except FileNotFoundError:
                # setquota command not found, quota tools not installed
                logging.CyberCPLogFileWriter.writeToFile("setquota command not found - quota tools may not be installed")
                return False, "Quota tools not installed"
                
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error applying quota to filesystem: {str(e)}")
            return False, str(e)

    @staticmethod
    def getFTPQuotaUsage(ftpUsername):
        """
        Get current quota usage for an FTP user
        """
        try:
            ftp = Users.objects.get(user=ftpUsername)
            user_dir = ftp.dir
            
            if not user_dir or not os.path.exists(user_dir):
                return 0, "User directory not found"
            
            # Get directory size in MB
            import subprocess
            result = subprocess.run(['du', '-sm', user_dir], capture_output=True, text=True)
            
            if result.returncode == 0:
                usage_mb = int(result.stdout.split()[0])
                quota_mb = ftp.quotasize
                usage_percent = (usage_mb / quota_mb * 100) if quota_mb > 0 else 0
                
                return {
                    'usage_mb': usage_mb,
                    'quota_mb': quota_mb,
                    'usage_percent': round(usage_percent, 2),
                    'remaining_mb': max(0, quota_mb - usage_mb)
                }
            else:
                return 0, "Failed to get directory size"
                
        except Users.DoesNotExist:
            return 0, "FTP user not found"
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error getting quota usage: {str(e)}")
            return 0, str(e)

    @staticmethod
    def migrateExistingFTPUsers():
        """
        Migrate existing FTP users to use the new quota system
        """
        try:
            migrated_count = 0
            
            for ftp_user in Users.objects.all():
                # If custom_quota_enabled is not set, set it to False and use package default
                if not hasattr(ftp_user, 'custom_quota_enabled') or ftp_user.custom_quota_enabled is None:
                    ftp_user.custom_quota_enabled = False
                    ftp_user.custom_quota_size = 0
                    ftp_user.quotasize = ftp_user.domain.package.diskSpace
                    ftp_user.save()
                    migrated_count += 1
            
            return 1, f"Migrated {migrated_count} FTP users to new quota system"
            
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error migrating FTP users: {str(e)}")
            return 0, str(e)


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