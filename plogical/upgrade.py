import json
import os
import os.path
import sys
import argparse
import pwd
import grp
import re

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
import shlex
import subprocess
import shutil
import time
import MySQLdb as mysql
import random
import string

def update_all_config_files_with_password(new_password):
    """
    Update all configuration files that use the cyberpanel database password.
    This includes FTP, PowerDNS, Postfix, Dovecot configurations.
    """
    config_updates = [
        # Django settings
        {
            'path': '/usr/local/CyberCP/CyberCP/settings.py',
            'updates': [
                (r"('cyberpanel'[^}]+?'PASSWORD':\s*')[^']+'", r"\1%s'" % new_password)
            ]
        },
        # FTP configurations
        {
            'path': '/etc/pure-ftpd/pureftpd-mysql.conf',
            'updates': [
                (r'^MYSQLPassword\s+.*$', 'MYSQLPassword %s' % new_password)
            ]
        },
        {
            'path': '/etc/pure-ftpd/db/mysql.conf',  # Ubuntu specific
            'updates': [
                (r'^MYSQLPassword\s+.*$', 'MYSQLPassword %s' % new_password)
            ]
        },
        # PowerDNS configurations
        {
            'path': '/etc/pdns/pdns.conf',  # CentOS/RHEL
            'updates': [
                (r'^gmysql-password=.*$', 'gmysql-password=%s' % new_password)
            ]
        },
        {
            'path': '/etc/powerdns/pdns.conf',  # Ubuntu/Debian
            'updates': [
                (r'^gmysql-password=.*$', 'gmysql-password=%s' % new_password)
            ]
        },
        # Postfix MySQL configurations
        {
            'path': '/etc/postfix/mysql-virtual_domains.cf',
            'updates': [
                (r'^password\s*=.*$', 'password = %s' % new_password)
            ]
        },
        {
            'path': '/etc/postfix/mysql-virtual_forwardings.cf',
            'updates': [
                (r'^password\s*=.*$', 'password = %s' % new_password)
            ]
        },
        {
            'path': '/etc/postfix/mysql-virtual_mailboxes.cf',
            'updates': [
                (r'^password\s*=.*$', 'password = %s' % new_password)
            ]
        },
        {
            'path': '/etc/postfix/mysql-virtual_email2email.cf',
            'updates': [
                (r'^password\s*=.*$', 'password = %s' % new_password)
            ]
        },
        # Dovecot MySQL configuration
        {
            'path': '/etc/dovecot/dovecot-sql.conf.ext',
            'updates': [
                (r'^connect\s*=.*$', lambda m: update_dovecot_connect_string(m.group(0), new_password))
            ]
        }
    ]
    
    for config in config_updates:
        if not os.path.exists(config['path']):
            continue
            
        try:
            with open(config['path'], 'r') as f:
                content = f.read()
            
            original_content = content
            for pattern, replacement in config['updates']:
                if callable(replacement):
                    # For complex replacements like dovecot connect string
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                else:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            if content != original_content:
                with open(config['path'], 'w') as f:
                    f.write(content)
                print("[RECOVERY] Updated password in: %s" % config['path'])
        except Exception as e:
            print("[RECOVERY] Warning: Could not update %s: %s" % (config['path'], str(e)))

def update_dovecot_connect_string(connect_line, new_password):
    """
    Update the password in dovecot's connect string.
    Format: connect = host=localhost dbname=cyberpanel user=cyberpanel password=oldpass
    """
    # Replace the password part in the connect string
    updated = re.sub(r'password=\S+', 'password=%s' % new_password, connect_line)
    return updated

def restart_affected_services():
    """
    Restart services that use the cyberpanel database password.
    """
    services_to_restart = [
        'pure-ftpd',      # FTP service
        'postfix',        # Mail transfer agent
        'dovecot',        # IMAP/POP3 server
        'pdns',           # PowerDNS (CentOS/RHEL)
        'powerdns',       # PowerDNS (Ubuntu/Debian)
    ]
    
    for service in services_to_restart:
        try:
            # Try systemctl first (systemd)
            result = subprocess.run(['systemctl', 'restart', service], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("[RECOVERY] Restarted service: %s" % service)
            elif 'Unit' in result.stderr and 'not found' in result.stderr:
                # Service doesn't exist, skip
                pass
            else:
                # Try service command (older systems)
                result = subprocess.run(['service', service, 'restart'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("[RECOVERY] Restarted service: %s" % service)
        except Exception as e:
            print("[RECOVERY] Warning: Could not restart %s: %s" % (service, str(e)))

# Try to import settings, but handle case where CyberCP directory is damaged
try:
    from CyberCP import settings
except ImportError:
    print("WARNING: Cannot import CyberCP settings. Attempting recovery...")
    
    def recover_database_credentials():
        """Attempt to recover or reset database credentials"""
        
        # First, ensure we have root MySQL password
        if not os.path.exists('/etc/cyberpanel/mysqlPassword'):
            print("FATAL: Cannot find MySQL root password file at /etc/cyberpanel/mysqlPassword")
            print("Manual intervention required.")
            sys.exit(1)
        
        root_password = open('/etc/cyberpanel/mysqlPassword', 'r').read().strip()
        cyberpanel_password = None
        
        # Try to read existing settings.py to get cyberpanel password
        settings_path = '/usr/local/CyberCP/CyberCP/settings.py'
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings_content = f.read()
                
                import re
                # Extract cyberpanel database password
                db_pattern = r"'default':[^}]*'USER':\s*'cyberpanel'[^}]*'PASSWORD':\s*'([^']+)'"
                match = re.search(db_pattern, settings_content, re.DOTALL)
                
                if match:
                    cyberpanel_password = match.group(1)
                    print("Found existing cyberpanel password in settings.py")
                    
                    # Test if this password actually works
                    try:
                        test_conn = mysql.connect(host='localhost', user='cyberpanel', 
                                                passwd=cyberpanel_password, db='cyberpanel')
                        test_conn.close()
                        print("Verified cyberpanel database credentials are valid")
                    except:
                        print("Found password in settings.py but it doesn't work, will reset")
                        cyberpanel_password = None
            except Exception as e:
                print("Could not extract password from settings.py: %s" % str(e))
        
        # If we couldn't get a working password, we need to reset it
        if cyberpanel_password is None:
            print("Resetting cyberpanel database user password...")
            
            # Check if we're on Ubuntu or CentOS
            # On Ubuntu, cyberpanel uses root password; on CentOS, it uses a separate password
            if os.path.exists('/etc/lsb-release'):
                # Ubuntu - use root password
                cyberpanel_password = root_password
                reset_to_root = True
            else:
                # CentOS/others - generate new password
                chars = string.ascii_letters + string.digits
                cyberpanel_password = ''.join(random.choice(chars) for _ in range(14))
                reset_to_root = False
            
            try:
                # Connect as root and reset cyberpanel user
                conn = mysql.connect(host='localhost', user='root', passwd=root_password)
                cursor = conn.cursor()
                
                # Check if cyberpanel database exists
                cursor.execute("SHOW DATABASES LIKE 'cyberpanel'")
                if not cursor.fetchone():
                    print("Creating cyberpanel database...")
                    cursor.execute("CREATE DATABASE IF NOT EXISTS cyberpanel")
                
                # Reset cyberpanel user - drop and recreate to ensure clean state
                cursor.execute("DROP USER IF EXISTS 'cyberpanel'@'localhost'")
                cursor.execute("CREATE USER 'cyberpanel'@'localhost' IDENTIFIED BY '%s'" % cyberpanel_password)
                cursor.execute("GRANT ALL PRIVILEGES ON cyberpanel.* TO 'cyberpanel'@'localhost'")
                cursor.execute("FLUSH PRIVILEGES")
                
                conn.close()
                
                if reset_to_root:
                    print("Reset cyberpanel user password to match root password (Ubuntu style)")
                else:
                    print("Reset cyberpanel user with new generated password (CentOS style)")
                
                # Update all configuration files with the new password
                print("Updating all service configuration files with new password...")
                update_all_config_files_with_password(cyberpanel_password)
                
                # Restart affected services to pick up new configuration
                print("Restarting affected services...")
                restart_affected_services()
                
                # Save the password to a temporary file for the upgrade process
                temp_pass_file = '/tmp/cyberpanel_recovered_password'
                with open(temp_pass_file, 'w') as f:
                    f.write(cyberpanel_password)
                os.chmod(temp_pass_file, 0o600)
                print("Saved recovered password to temporary file")
                
            except Exception as e:
                print("Failed to reset cyberpanel database user: %s" % str(e))
                print("Manual intervention required. Please run:")
                print("  mysql -u root -p")
                print("  CREATE DATABASE IF NOT EXISTS cyberpanel;")
                print("  GRANT ALL PRIVILEGES ON cyberpanel.* TO 'cyberpanel'@'localhost' IDENTIFIED BY 'your_password';")
                print("  FLUSH PRIVILEGES;")
                sys.exit(1)
        
        return cyberpanel_password, root_password
    
    # Perform recovery
    cyberpanel_password, root_password = recover_database_credentials()
    
    # Create a minimal settings object for recovery
    class MinimalSettings:
        DATABASES = {
            'default': {
                'NAME': 'cyberpanel',
                'USER': 'cyberpanel',
                'PASSWORD': cyberpanel_password,
                'HOST': 'localhost',
                'PORT': '3306'
            },
            'rootdb': {
                'NAME': 'mysql',
                'USER': 'root',
                'PASSWORD': root_password,
                'HOST': 'localhost',
                'PORT': '3306'
            }
        }
    
    settings = MinimalSettings()
    print("Recovery complete. Continuing with upgrade...")

VERSION = '2.4'
BUILD = 4

CENTOS7 = 0
CENTOS8 = 1
Ubuntu18 = 2
Ubuntu20 = 3
CloudLinux7 = 4
CloudLinux8 = 5
openEuler20 = 6
openEuler22 = 7
Ubuntu22 = 8
Ubuntu24 = 9


class Upgrade:
    logPath = "/usr/local/lscp/logs/upgradeLog"
    cdn = 'cdn.cyberpanel.sh'
    installedOutput = ''
    CentOSPath = '/etc/redhat-release'
    UbuntuPath = '/etc/lsb-release'
    openEulerPath = '/etc/openEuler-release'
    FromCloud = 0
    SnappyVersion = '2.38.2'
    LogPathNew = '/home/cyberpanel/upgrade_logs'
    SoftUpgrade = 0

    AdminACL = '{"adminStatus":1, "versionManagement": 1, "createNewUser": 1, "listUsers": 1, "deleteUser":1 , "resellerCenter": 1, ' \
               '"changeUserACL": 1, "createWebsite": 1, "modifyWebsite": 1, "suspendWebsite": 1, "deleteWebsite": 1, ' \
               '"createPackage": 1, "listPackages": 1, "deletePackage": 1, "modifyPackage": 1, "createDatabase": 1, "deleteDatabase": 1, ' \
               '"listDatabases": 1, "createNameServer": 1, "createDNSZone": 1, "deleteZone": 1, "addDeleteRecords": 1, ' \
               '"createEmail": 1, "listEmails": 1, "deleteEmail": 1, "emailForwarding": 1, "changeEmailPassword": 1, ' \
               '"dkimManager": 1, "createFTPAccount": 1, "deleteFTPAccount": 1, "listFTPAccounts": 1, "createBackup": 1,' \
               ' "restoreBackup": 1, "addDeleteDestinations": 1, "scheduleBackups": 1, "remoteBackups": 1, "googleDriveBackups": 1, "manageSSL": 1, ' \
               '"hostnameSSL": 1, "mailServerSSL": 1 }'

    ResellerACL = '{"adminStatus":0, "versionManagement": 1, "createNewUser": 1, "listUsers": 1, "deleteUser": 1 , "resellerCenter": 1, ' \
                  '"changeUserACL": 0, "createWebsite": 1, "modifyWebsite": 1, "suspendWebsite": 1, "deleteWebsite": 1, ' \
                  '"createPackage": 1, "listPackages": 1, "deletePackage": 1, "modifyPackage": 1, "createDatabase": 1, "deleteDatabase": 1, ' \
                  '"listDatabases": 1, "createNameServer": 1, "createDNSZone": 1, "deleteZone": 1, "addDeleteRecords": 1, ' \
                  '"createEmail": 1, "listEmails": 1, "deleteEmail": 1, "emailForwarding": 1, "changeEmailPassword": 1, ' \
                  '"dkimManager": 1, "createFTPAccount": 1, "deleteFTPAccount": 1, "listFTPAccounts": 1, "createBackup": 1,' \
                  ' "restoreBackup": 1, "addDeleteDestinations": 0, "scheduleBackups": 0, "remoteBackups": 0, "googleDriveBackups": 1, "manageSSL": 1, ' \
                  '"hostnameSSL": 0, "mailServerSSL": 0 }'

    UserACL = '{"adminStatus":0, "versionManagement": 1, "createNewUser": 0, "listUsers": 0, "deleteUser": 0 , "resellerCenter": 0, ' \
              '"changeUserACL": 0, "createWebsite": 0, "modifyWebsite": 0, "suspendWebsite": 0, "deleteWebsite": 0, ' \
              '"createPackage": 0, "listPackages": 0, "deletePackage": 0, "modifyPackage": 0, "createDatabase": 1, "deleteDatabase": 1, ' \
              '"listDatabases": 1, "createNameServer": 0, "createDNSZone": 1, "deleteZone": 1, "addDeleteRecords": 1, ' \
              '"createEmail": 1, "listEmails": 1, "deleteEmail": 1, "emailForwarding": 1, "changeEmailPassword": 1, ' \
              '"dkimManager": 1, "createFTPAccount": 1, "deleteFTPAccount": 1, "listFTPAccounts": 1, "createBackup": 1,' \
              ' "restoreBackup": 0, "addDeleteDestinations": 0, "scheduleBackups": 0, "remoteBackups": 0, "googleDriveBackups": 1, "manageSSL": 1, ' \
              '"hostnameSSL": 0, "mailServerSSL": 0 }'

    @staticmethod
    def FetchCloudLinuxAlmaVersionVersion():
        if os.path.exists('/etc/os-release'):
            data = open('/etc/os-release', 'r').read()
            if (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (
                    data.find('8.9') > -1 or data.find('Anatoly Levchenko') > -1 or data.find('VERSION="8.') > -1):
                return 'cl-89'
            elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (
                    data.find('8.8') > -1 or data.find('Anatoly Filipchenko') > -1):
                return 'cl-88'
            elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (
                    data.find('9.4') > -1 or data.find('VERSION="9.') > -1):
                return 'cl-88'
            elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (
                    data.find('8.9') > -1 or data.find('Midnight Oncilla') > -1 or data.find('VERSION="8.') > -1):
                return 'al-88'
            elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (
                    data.find('8.7') > -1 or data.find('Stone Smilodon') > -1):
                return 'al-87'
            elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (
                    data.find('9.4') > -1 or data.find('9.3') > -1 or data.find('Shamrock Pampas') > -1 or data.find(
                    'Seafoam Ocelot') > -1 or data.find('VERSION="9.') > -1):
                return 'al-93'
        return None

    @staticmethod
    def decideCentosVersion():

        if open(Upgrade.CentOSPath, 'r').read().find('CentOS Linux release 8') > -1:
            return CENTOS8
        else:
            return CENTOS7

    @staticmethod
    def FindOperatingSytem():

        if os.path.exists(Upgrade.CentOSPath):
            result = open(Upgrade.CentOSPath, 'r').read()

            if result.find('CentOS Linux release 8') > -1 or result.find('CloudLinux release 8') > -1:
                return CENTOS8
            else:
                return CENTOS7

        elif os.path.exists(Upgrade.openEulerPath):
            result = open(Upgrade.openEulerPath, 'r').read()

            if result.find('20.03') > -1:
                return openEuler20
            elif result.find('22.03') > -1:
                return openEuler22

        else:
            result = open(Upgrade.UbuntuPath, 'r').read()

            if result.find('20.04') > -1:
                return Ubuntu20
            elif result.find('22.04') > -1:
                return Ubuntu22
            elif result.find('24.04') > -1:
                return Ubuntu24
            else:
                return Ubuntu18

    @staticmethod
    def stdOut(message, do_exit=0):
        print("\n\n")
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))
        print(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] " + message + "\n"))
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))

        WriteToFile = open(Upgrade.LogPathNew, 'a')
        WriteToFile.write(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))
        WriteToFile.write(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] " + message + "\n"))
        WriteToFile.write(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))
        WriteToFile.close()

        if do_exit:

            ### remove log file path incase its there

            if Upgrade.SoftUpgrade:
                time.sleep(10)
                if os.path.exists(Upgrade.LogPathNew):
                    os.remove(Upgrade.LogPathNew)

            if Upgrade.FromCloud == 0:
                os._exit(0)

    @staticmethod
    def executioner(command, component, do_exit=0, shell=False):
        try:
            FNULL = open(os.devnull, 'w')
            count = 0
            while True:
                if shell == False:
                    res = subprocess.call(shlex.split(command), stderr=subprocess.STDOUT)
                else:
                    res = subprocess.call(command, stderr=subprocess.STDOUT, shell=True)
                if res != 0:
                    count = count + 1
                    Upgrade.stdOut(component + ' failed, trying again, try number: ' + str(count), 0)
                    if count == 3:
                        Upgrade.stdOut(component + ' failed.', do_exit)
                        return False
                else:
                    Upgrade.stdOut(component + ' successful.', 0)
                    break
            return True
        except:
            return False
    
    @staticmethod
    def executioner_silent(command, component, do_exit=0, shell=False):
        """Silent version of executioner that suppresses all output"""
        try:
            FNULL = open(os.devnull, 'w')
            count = 0
            while True:
                if shell == False:
                    res = subprocess.call(shlex.split(command), stdout=FNULL, stderr=FNULL)
                else:
                    res = subprocess.call(command, stdout=FNULL, stderr=FNULL, shell=True)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        FNULL.close()
                        return False
                else:
                    FNULL.close()
                    return True
        except:
            return False

    @staticmethod
    def updateRepoURL():
        command = "sed -i 's|sgp.cyberpanel.sh|cdn.cyberpanel.sh|g' /etc/yum.repos.d/MariaDB.repo"
        Upgrade.executioner(command, command, 0)

        command = "sed -i 's|lax.cyberpanel.sh|cdn.cyberpanel.sh|g' /etc/yum.repos.d/MariaDB.repo"
        Upgrade.executioner(command, command, 0)

        command = "sed -i 's|fra.cyberpanel.sh|cdn.cyberpanel.sh|g' /etc/yum.repos.d/MariaDB.repo"
        Upgrade.executioner(command, command, 0)

        command = "sed -i 's|mirror.cyberpanel.net|cdn.cyberpanel.sh|g' /etc/yum.repos.d/MariaDB.repo"
        Upgrade.executioner(command, command, 0)

        command = "sed -i 's|sgp.cyberpanel.sh|cdn.cyberpanel.sh|g' /etc/yum.repos.d/litespeed.repo"
        Upgrade.executioner(command, command, 0)

        command = "sed -i 's|lax.cyberpanel.sh|cdn.cyberpanel.sh|g' /etc/yum.repos.d/litespeed.repo"
        Upgrade.executioner(command, command, 0)

        command = "sed -i 's|fra.cyberpanel.sh|cdn.cyberpanel.sh|g' /etc/yum.repos.d/litespeed.repo"
        Upgrade.executioner(command, command, 0)

        command = "sed -i 's|mirror.cyberpanel.net|cdn.cyberpanel.sh|g' /etc/yum.repos.d/litespeed.repo"
        Upgrade.executioner(command, command, 0)

    @staticmethod
    def mountTemp():
        try:

            if os.path.exists("/usr/.tempdisk"):
                return 0

            command = "dd if=/dev/zero of=/usr/.tempdisk bs=100M count=15"
            Upgrade.executioner(command, 'mountTemp', 0)

            command = "mkfs.ext4 -F /usr/.tempdisk"
            Upgrade.executioner(command, 'mountTemp', 0)

            command = "mkdir -p /usr/.tmpbak/"
            Upgrade.executioner(command, 'mountTemp', 0)

            command = "cp -pr /tmp/* /usr/.tmpbak/"
            subprocess.call(command, shell=True)

            command = "mount -o loop,rw,nodev,nosuid,noexec,nofail /usr/.tempdisk /tmp"
            Upgrade.executioner(command, 'mountTemp', 0)

            command = "chmod 1777 /tmp"
            Upgrade.executioner(command, 'mountTemp', 0)

            command = "cp -pr /usr/.tmpbak/* /tmp/"
            subprocess.call(command, shell=True)

            command = "rm -rf /usr/.tmpbak"
            Upgrade.executioner(command, 'mountTemp', 0)

            command = "mount --bind /tmp /var/tmp"
            Upgrade.executioner(command, 'mountTemp', 0)

            tmp = "/usr/.tempdisk /tmp ext4 loop,rw,noexec,nosuid,nodev,nofail 0 0\n"
            varTmp = "/tmp /var/tmp none bind 0 0\n"

            fstab = "/etc/fstab"
            writeToFile = open(fstab, "a")
            writeToFile.writelines(tmp)
            writeToFile.writelines(varTmp)
            writeToFile.close()

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [mountTemp]", 0)

    @staticmethod
    def dockerUsers():
        ### Docker User/group
        try:
            pwd.getpwnam('docker')
        except KeyError:
            command = "adduser docker"
            Upgrade.executioner(command, 'adduser docker', 0)

        try:
            grp.getgrnam('docker')
        except KeyError:
            command = 'groupadd docker'
            Upgrade.executioner(command, 'adduser docker', 0)

        command = 'usermod -aG docker docker'
        Upgrade.executioner(command, 'adduser docker', 0)

        command = 'usermod -aG docker cyberpanel'
        Upgrade.executioner(command, 'adduser docker', 0)

        ###

    @staticmethod
    def fixSudoers():
        try:
            distroPath = '/etc/lsb-release'

            if os.path.exists(distroPath):
                fileName = '/etc/sudoers'
                data = open(fileName, 'r').readlines()

                writeDataToFile = open(fileName, 'w')
                for line in data:
                    if line.find("%sudo ALL=(ALL:ALL)") > -1:
                        continue
                    else:
                        writeDataToFile.write(line)
                writeDataToFile.close()

            else:
                try:
                    path = "/etc/sudoers"

                    data = open(path, 'r').readlines()

                    writeToFile = open(path, 'w')

                    for items in data:
                        if items.find("wheel") > -1 and items.find("ALL=(ALL)"):
                            continue
                        elif items.find("root") > -1 and items.find("ALL=(ALL)") > -1 and items[0] != '#':
                            writeToFile.writelines('root	ALL=(ALL:ALL) 	ALL\n')
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()
                except:
                    pass

            command = "chsh -s /bin/false cyberpanel"
            Upgrade.executioner(command, 0)
        except IOError as err:
            pass

    @staticmethod
    def download_install_phpmyadmin():
        try:
            cwd = os.getcwd()

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            try:
                shutil.rmtree("/usr/local/CyberCP/public/phpmyadmin")
            except:
                pass

            Upgrade.stdOut("Installing phpMyAdmin...", 0)
            
            command = 'wget -q -O /usr/local/CyberCP/public/phpmyadmin.zip https://github.com/usmannasir/cyberpanel/raw/stable/phpmyadmin.zip'
            Upgrade.executioner_silent(command, 'Download phpMyAdmin')

            command = 'unzip -q /usr/local/CyberCP/public/phpmyadmin.zip -d /usr/local/CyberCP/public/'
            Upgrade.executioner_silent(command, 'Extract phpMyAdmin')

            command = 'mv /usr/local/CyberCP/public/phpMyAdmin-*-all-languages /usr/local/CyberCP/public/phpmyadmin'
            subprocess.call(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            command = 'rm -f /usr/local/CyberCP/public/phpmyadmin.zip'
            Upgrade.executioner_silent(command, 'Cleanup phpMyAdmin zip')
            
            Upgrade.stdOut("phpMyAdmin installation completed.", 0)

            ## Write secret phrase

            rString = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

            data = open('/usr/local/CyberCP/public/phpmyadmin/config.sample.inc.php', 'r').readlines()

            writeToFile = open('/usr/local/CyberCP/public/phpmyadmin/config.inc.php', 'w')

            writeE = 1

            phpMyAdminContent = """
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonSession'] = 'SignonSession';
$cfg['Servers'][$i]['SignonURL'] = 'phpmyadminsignin.php';
$cfg['Servers'][$i]['LogoutURL'] = 'phpmyadminsignin.php?logout';
"""

            for items in data:
                if items.find('blowfish_secret') > -1:
                    writeToFile.writelines(
                        "$cfg['blowfish_secret'] = '" + rString + "'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */\n")
                elif items.find('/* Authentication type */') > -1:
                    writeToFile.writelines(items)
                    writeToFile.write(phpMyAdminContent)
                    writeE = 0
                elif items.find("$cfg['Servers'][$i]['AllowNoPassword']") > -1:
                    writeE = 1
                else:
                    if writeE:
                        writeToFile.writelines(items)

            writeToFile.writelines("$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';\n")

            writeToFile.close()

            os.mkdir('/usr/local/CyberCP/public/phpmyadmin/tmp')

            command = 'cp /usr/local/CyberCP/plogical/phpmyadminsignin.php /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php'
            Upgrade.executioner(command, 0)

            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                import json
                jsonData = json.loads(open(passFile, 'r').read())

                mysqluser = jsonData['mysqluser']
                mysqlpassword = jsonData['mysqlpassword']
                mysqlport = jsonData['mysqlport']
                mysqlhost = jsonData['mysqlhost']

                command = "sed -i 's|localhost|%s|g' /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php" % (
                    mysqlhost)
                Upgrade.executioner(command, 0)

            except:
                pass

            os.chdir(cwd)

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [download_install_phpmyadmin]", 0)

    @staticmethod
    def setupComposer():

        if os.path.exists('composer.sh'):
            os.remove('composer.sh')

        command = "wget https://cyberpanel.sh/composer.sh"
        Upgrade.executioner(command, 0)

        command = "chmod +x composer.sh"
        Upgrade.executioner(command, 0)

        command = "./composer.sh"
        Upgrade.executioner(command, 0)

    @staticmethod
    def downoad_and_install_raindloop():
        try:
            #######

            # if os.path.exists("/usr/local/CyberCP/public/rainloop"):
            #
            #     if os.path.exists("/usr/local/lscp/cyberpanel/rainloop/data"):
            #         pass
            #     else:
            #         command = "mv /usr/local/CyberCP/public/rainloop/data /usr/local/lscp/cyberpanel/rainloop/data"
            #         Upgrade.executioner(command, 0)
            #
            #         command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data"
            #         Upgrade.executioner(command, 0)
            #
            #     iPath = os.listdir('/usr/local/CyberCP/public/rainloop/rainloop/v/')
            #
            #     path = "/usr/local/CyberCP/public/snappymail/snappymail/v/%s/include.php" % (iPath[0])
            #
            #     data = open(path, 'r').readlines()
            #     writeToFile = open(path, 'w')
            #
            #     for items in data:
            #         if items.find("$sCustomDataPath = '';") > -1:
            #             writeToFile.writelines(
            #                 "			$sCustomDataPath = '/usr/local/lscp/cyberpanel/rainloop/data';\n")
            #         else:
            #             writeToFile.writelines(items)
            #
            #     writeToFile.close()
            #     return 0

            cwd = os.getcwd()

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            os.chdir("/usr/local/CyberCP/public")

            count = 1

            Upgrade.stdOut("Installing SnappyMail...", 0)
            
            while (1):
                command = 'wget -q https://github.com/the-djmaze/snappymail/releases/download/v%s/snappymail-%s.zip' % (
                    Upgrade.SnappyVersion, Upgrade.SnappyVersion)
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break

            #############

            count = 0

            if os.path.exists('/usr/local/CyberCP/public/snappymail'):
                shutil.rmtree('/usr/local/CyberCP/public/snappymail')

            while (1):
                command = 'unzip -q snappymail-%s.zip -d /usr/local/CyberCP/public/snappymail' % (Upgrade.SnappyVersion)

                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break
            try:
                os.remove("snappymail-%s.zip" % (Upgrade.SnappyVersion))
            except:
                pass

            #######

            os.chdir("/usr/local/CyberCP/public/snappymail")

            count = 0

            while (1):
                command = 'find . -type d -exec chmod 755 {} \;'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break

            #############

            count = 0

            while (1):
                command = 'find . -type f -exec chmod 644 {} \;'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break
            ######

            iPath = os.listdir('/usr/local/CyberCP/public/snappymail/snappymail/v/')

            path = "/usr/local/CyberCP/public/snappymail/snappymail/v/%s/include.php" % (iPath[0])

            data = open(path, 'r').readlines()
            writeToFile = open(path, 'w')

            for items in data:
                if items.find("$sCustomDataPath = '';") > -1:
                    writeToFile.writelines(
                        "			$sCustomDataPath = '/usr/local/lscp/cyberpanel/rainloop/data';\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            command = "mkdir -p /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/"
            Upgrade.executioner_silent(command, 'mkdir snappymail configs', 0)

            command = f'wget -q -O /usr/local/CyberCP/snappymail_cyberpanel.php  https://raw.githubusercontent.com/the-djmaze/snappymail/master/integrations/cyberpanel/install.php'
            Upgrade.executioner_silent(command, 'verify certificate', 0)

            command = f'/usr/local/lsws/lsphp83/bin/php /usr/local/CyberCP/snappymail_cyberpanel.php'
            Upgrade.executioner_silent(command, 'verify certificate', 0)

            # labsPath = '/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/application.ini'

            #             labsData = """[labs]
            # imap_folder_list_limit = 0
            # autocreate_system_folders = On
            # """
            #
            #             writeToFile = open(labsPath, 'a')
            #             writeToFile.write(labsData)
            #             writeToFile.close()

            includeFileOldPath = '/usr/local/CyberCP/public/snappymail/_include.php'
            includeFileNewPath = '/usr/local/CyberCP/public/snappymail/include.php'

            # if os.path.exists(includeFileOldPath):
            #     writeToFile = open(includeFileOldPath, 'a')
            #     writeToFile.write("\ndefine('APP_DATA_FOLDER_PATH', '/usr/local/lscp/cyberpanel/rainloop/data/');\n")
            #     writeToFile.close()

            # command = 'mv %s %s' % (includeFileOldPath, includeFileNewPath)
            # Upgrade.executioner(command, 'mkdir snappymail configs', 0)

            ## take care of auto create folders

            ## Disable local cert verification

            # command = "sed -i 's|verify_certificate = On|verify_certificate = Off|g' %s" % (labsPath)
            # Upgrade.executioner(command, 'verify certificate', 0)

            # labsData = open(labsPath, 'r').read()
            # labsDataLines = open(labsPath, 'r').readlines()
            #
            # if labsData.find('autocreate_system_folders') > -1:
            #     command = "sed -i 's|autocreate_system_folders = Off|autocreate_system_folders = On|g' %s" % (labsPath)
            #     Upgrade.executioner(command, 'mkdir snappymail configs', 0)
            # else:
            #     WriteToFile = open(labsPath, 'w')
            #     for lines in labsDataLines:
            #         if lines.find('[labs]') > -1:
            #             WriteToFile.write(lines)
            #             WriteToFile.write(f'autocreate_system_folders = On\n')
            #         else:
            #             WriteToFile.write(lines)
            #     WriteToFile.close()

            ##take care of imap_folder_list_limit

            # labsDataLines = open(labsPath, 'r').readlines()
            #
            # if labsData.find('imap_folder_list_limit') == -1:
            #     WriteToFile = open(labsPath, 'w')
            #     for lines in labsDataLines:
            #         if lines.find('[labs]') > -1:
            #             WriteToFile.write(lines)
            #             WriteToFile.write(f'imap_folder_list_limit = 0\n')
            #         else:
            #             WriteToFile.write(lines)
            #     WriteToFile.close()

            ### now download and install actual plugin

            #             command = f'mkdir /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/plugins/mailbox-detect'
            #             Upgrade.executioner(command, 'verify certificate', 0)
            #
            #             command = f'chmod 700 /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/plugins/mailbox-detect'
            #             Upgrade.executioner(command, 'verify certificate', 0)
            #
            #             command = f'chown lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/plugins/mailbox-detect'
            #             Upgrade.executioner(command, 'verify certificate', 0)
            #
            #             command = f'wget -O /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/plugins/mailbox-detect/index.php https://raw.githubusercontent.com/the-djmaze/snappymail/master/plugins/mailbox-detect/index.php'
            #             Upgrade.executioner(command, 'verify certificate', 0)
            #
            #             command = f'chmod 644 /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/plugins/mailbox-detect/index.php'
            #             Upgrade.executioner(command, 'verify certificate', 0)
            #
            #             command = f'chown lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/plugins/mailbox-detect/index.php'
            #             Upgrade.executioner(command, 'verify certificate', 0)
            #
            #             ### Enable plugins and enable mailbox creation plugin
            #
            #             labsDataLines = open(labsPath, 'r').readlines()
            #             PluginsActivator = 0
            #             WriteToFile = open(labsPath, 'w')
            #
            #
            #             for lines in labsDataLines:
            #                 if lines.find('[plugins]') > -1:
            #                     PluginsActivator = 1
            #                     WriteToFile.write(lines)
            #                 elif PluginsActivator and lines.find('enable = ') > -1:
            #                     WriteToFile.write(f'enable = On\n')
            #                 elif PluginsActivator and lines.find('enabled_list = ') > -1:
            #                     WriteToFile.write(f'enabled_list = "mailbox-detect"\n')
            #                 elif PluginsActivator == 1 and lines.find('[defaults]') > -1:
            #                     PluginsActivator = 0
            #                     WriteToFile.write(lines)
            #                 else:
            #                     WriteToFile.write(lines)
            #             WriteToFile.close()
            #
            #             ## enable auto create in the enabled plugin
            #             PluginsFilePath = '/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/plugin-mailbox-detect.json'
            #
            #             WriteToFile = open(PluginsFilePath, 'w')
            #             WriteToFile.write("""{
            #     "plugin": {
            #         "autocreate_system_folders": true
            #     }
            # }
            # """)
            #             WriteToFile.close()
            #
            #             command = f'chown lscpd:lscpd {PluginsFilePath}'
            #             Upgrade.executioner(command, 'verify certificate', 0)
            #
            #             command = f'chmod 600 {PluginsFilePath}'
            #             Upgrade.executioner(command, 'verify certificate', 0)

            os.chdir(cwd)
            
            Upgrade.stdOut("SnappyMail installation completed.", 0)

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [downoad_and_install_raindloop]", 0)

        return 1

    @staticmethod
    def downloadLink():
        try:
            version_number = VERSION
            version_build = str(BUILD)

            try:
                Content = {"version":version_number,"build":version_build}
                path = "/usr/local/CyberCP/version.txt"
                writeToFile = open(path, 'w')
                writeToFile.write(json.dumps(Content))
                writeToFile.close()
            except:
                pass

            return (version_number + "." + version_build + ".tar.gz")
        except BaseException as msg:
            Upgrade.stdOut(str(msg) + ' [downloadLink]')
            os._exit(0)

    @staticmethod
    def setupCLI():
        try:

            command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
            Upgrade.executioner(command, 'CLI Symlink', 0)

            command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
            Upgrade.executioner(command, 'CLI Permissions', 0)

        except OSError as msg:
            Upgrade.stdOut(str(msg) + " [setupCLI]")
            return 0

    @staticmethod
    def staticContent():

        command = "rm -rf /usr/local/CyberCP/public/static"
        Upgrade.executioner(command, 'Remove old static content', 0)

        ##

        if not os.path.exists("/usr/local/CyberCP/public"):
            os.mkdir("/usr/local/CyberCP/public")

        cwd = os.getcwd()

        os.chdir('/usr/local/CyberCP')

        command = '/usr/local/CyberPanel/bin/python manage.py collectstatic --noinput --clear'
        Upgrade.executioner(command, 'Remove old static content', 0)

        os.chdir(cwd)

        shutil.move("/usr/local/CyberCP/static", "/usr/local/CyberCP/public/")

    @staticmethod
    def upgradeVersion():
        try:

            import django
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            django.setup()
            from baseTemplate.models import version

            vers = version.objects.get(pk=1)
            vers.currentVersion = VERSION
            vers.build = str(BUILD)
            vers.save()
        except:
            pass

    @staticmethod
    def setupConnection(db=None):
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            if db == None:
                conn = mysql.connect(user='root', passwd=password)
            else:
                try:
                    conn = mysql.connect(db=db, user='root', passwd=password)
                except:
                    try:
                        conn = mysql.connect(host='127.0.0.1', port=3307, db=db, user='root', passwd=password)
                    except:
                        dbUser = settings.DATABASES['default']['USER']
                        password = settings.DATABASES['default']['PASSWORD']
                        host = settings.DATABASES['default']['HOST']
                        port = settings.DATABASES['default']['PORT']

                        if port == '':
                            conn = mysql.connect(host=host, port=3306, db=db, user=dbUser, passwd=password)
                        else:
                            conn = mysql.connect(host=host, port=int(port), db=db, user=dbUser, passwd=password)

            cursor = conn.cursor()
            return conn, cursor

        except BaseException as msg:
            Upgrade.stdOut(str(msg))
            return 0, 0

    @staticmethod
    def applyLoginSystemMigrations():
        try:

            connection, cursor = Upgrade.setupConnection('cyberpanel')

            try:
                cursor.execute(
                    'CREATE TABLE `baseTemplate_cyberpanelcosmetic` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `MainDashboardCSS` longtext NOT NULL)')
            except:
                pass

            # AI Scanner Tables
            try:
                cursor.execute('''
                    CREATE TABLE `ai_scanner_settings` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `admin_id` integer NOT NULL UNIQUE,
                        `api_key` varchar(255) DEFAULT NULL,
                        `balance` decimal(10,4) NOT NULL DEFAULT 0.0000,
                        `is_payment_configured` bool NOT NULL DEFAULT 0,
                        `created_at` datetime(6) NOT NULL,
                        `updated_at` datetime(6) NOT NULL,
                        KEY `ai_scanner_settings_admin_id_idx` (`admin_id`),
                        CONSTRAINT `ai_scanner_settings_admin_id_fk` FOREIGN KEY (`admin_id`) 
                        REFERENCES `loginSystem_administrator` (`id`) ON DELETE CASCADE
                    )
                ''')
            except:
                pass

            try:
                cursor.execute('''
                    CREATE TABLE `ai_scanner_history` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `admin_id` integer NOT NULL,
                        `scan_id` varchar(100) NOT NULL UNIQUE,
                        `domain` varchar(255) NOT NULL,
                        `scan_type` varchar(20) NOT NULL DEFAULT 'full',
                        `status` varchar(20) NOT NULL DEFAULT 'pending',
                        `cost_usd` decimal(10,6) DEFAULT NULL,
                        `files_scanned` integer NOT NULL DEFAULT 0,
                        `issues_found` integer NOT NULL DEFAULT 0,
                        `findings_json` longtext DEFAULT NULL,
                        `summary_json` longtext DEFAULT NULL,
                        `error_message` longtext DEFAULT NULL,
                        `started_at` datetime(6) NOT NULL,
                        `completed_at` datetime(6) DEFAULT NULL,
                        KEY `ai_scanner_history_admin_id_idx` (`admin_id`),
                        KEY `ai_scanner_history_scan_id_idx` (`scan_id`),
                        KEY `ai_scanner_history_started_at_idx` (`started_at`),
                        CONSTRAINT `ai_scanner_history_admin_id_fk` FOREIGN KEY (`admin_id`) 
                        REFERENCES `loginSystem_administrator` (`id`) ON DELETE CASCADE
                    )
                ''')
            except:
                pass

            try:
                cursor.execute('''
                    CREATE TABLE `ai_scanner_file_tokens` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `token` varchar(100) NOT NULL UNIQUE,
                        `scan_history_id` integer NOT NULL,
                        `domain` varchar(255) NOT NULL,
                        `wp_path` varchar(500) NOT NULL,
                        `expires_at` datetime(6) NOT NULL,
                        `created_at` datetime(6) NOT NULL,
                        `is_active` bool NOT NULL DEFAULT 1,
                        KEY `ai_scanner_file_tokens_scan_history_id_idx` (`scan_history_id`),
                        KEY `ai_scanner_file_tokens_token_idx` (`token`),
                        CONSTRAINT `ai_scanner_file_tokens_scan_history_id_fk` FOREIGN KEY (`scan_history_id`) 
                        REFERENCES `ai_scanner_history` (`id`) ON DELETE CASCADE
                    )
                ''')
            except:
                pass

            try:
                cursor.execute('''
                    CREATE TABLE `ai_scanner_status_updates` (
                        `scan_id` varchar(100) NOT NULL PRIMARY KEY,
                        `phase` varchar(50) NOT NULL,
                        `progress` integer NOT NULL DEFAULT 0,
                        `current_file` longtext DEFAULT NULL,
                        `files_discovered` integer NOT NULL DEFAULT 0,
                        `files_scanned` integer NOT NULL DEFAULT 0,
                        `files_remaining` integer NOT NULL DEFAULT 0,
                        `threats_found` integer NOT NULL DEFAULT 0,
                        `critical_threats` integer NOT NULL DEFAULT 0,
                        `high_threats` integer NOT NULL DEFAULT 0,
                        `activity_description` longtext DEFAULT NULL,
                        `last_updated` datetime(6) NOT NULL,
                        `created_at` datetime(6) NOT NULL,
                        KEY `ai_scanner_status_updates_scan_id_last_updated_idx` (`scan_id`, `last_updated` DESC)
                    )
                ''')
            except:
                pass

            # AI Scanner Scheduled Scans Tables
            try:
                cursor.execute('''
                    CREATE TABLE `ai_scanner_scheduled_scans` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `admin_id` integer NOT NULL,
                        `name` varchar(200) NOT NULL,
                        `domains` longtext NOT NULL,
                        `frequency` varchar(20) NOT NULL DEFAULT 'weekly',
                        `scan_type` varchar(20) NOT NULL DEFAULT 'full',
                        `time_of_day` time NOT NULL,
                        `day_of_week` integer DEFAULT NULL,
                        `day_of_month` integer DEFAULT NULL,
                        `status` varchar(20) NOT NULL DEFAULT 'active',
                        `last_run` datetime(6) DEFAULT NULL,
                        `next_run` datetime(6) DEFAULT NULL,
                        `created_at` datetime(6) NOT NULL,
                        `updated_at` datetime(6) NOT NULL,
                        `email_notifications` bool NOT NULL DEFAULT 1,
                        `notification_emails` longtext NOT NULL DEFAULT '',
                        `notify_on_threats` bool NOT NULL DEFAULT 1,
                        `notify_on_completion` bool NOT NULL DEFAULT 0,
                        `notify_on_failure` bool NOT NULL DEFAULT 1,
                        KEY `ai_scanner_scheduled_scans_admin_id_idx` (`admin_id`),
                        KEY `ai_scanner_scheduled_scans_status_next_run_idx` (`status`, `next_run`),
                        CONSTRAINT `ai_scanner_scheduled_scans_admin_id_fk` FOREIGN KEY (`admin_id`) 
                        REFERENCES `loginSystem_administrator` (`id`) ON DELETE CASCADE
                    )
                ''')
            except:
                pass

            try:
                cursor.execute('''
                    CREATE TABLE `ai_scanner_scheduled_executions` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `scheduled_scan_id` integer NOT NULL,
                        `execution_time` datetime(6) NOT NULL,
                        `status` varchar(20) NOT NULL DEFAULT 'pending',
                        `domains_scanned` longtext NOT NULL DEFAULT '',
                        `total_scans` integer NOT NULL DEFAULT 0,
                        `successful_scans` integer NOT NULL DEFAULT 0,
                        `failed_scans` integer NOT NULL DEFAULT 0,
                        `total_cost` decimal(10,6) NOT NULL DEFAULT 0.000000,
                        `scan_ids` longtext NOT NULL DEFAULT '',
                        `error_message` longtext DEFAULT NULL,
                        `started_at` datetime(6) DEFAULT NULL,
                        `completed_at` datetime(6) DEFAULT NULL,
                        KEY `ai_scanner_scheduled_executions_scheduled_scan_id_idx` (`scheduled_scan_id`),
                        KEY `ai_scanner_scheduled_executions_execution_time_idx` (`execution_time` DESC),
                        CONSTRAINT `ai_scanner_scheduled_executions_scheduled_scan_id_fk` FOREIGN KEY (`scheduled_scan_id`) 
                        REFERENCES `ai_scanner_scheduled_scans` (`id`) ON DELETE CASCADE
                    )
                ''')
            except:
                pass

            try:
                cursor.execute(
                    'CREATE TABLE `loginSystem_acl` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL UNIQUE, `adminStatus` integer NOT NULL DEFAULT 0, `versionManagement` integer NOT NULL DEFAULT 0, `createNewUser` integer NOT NULL DEFAULT 0, `deleteUser` integer NOT NULL DEFAULT 0, `resellerCenter` integer NOT NULL DEFAULT 0, `changeUserACL` integer NOT NULL DEFAULT 0, `createWebsite` integer NOT NULL DEFAULT 0, `modifyWebsite` integer NOT NULL DEFAULT 0, `suspendWebsite` integer NOT NULL DEFAULT 0, `deleteWebsite` integer NOT NULL DEFAULT 0, `createPackage` integer NOT NULL DEFAULT 0, `deletePackage` integer NOT NULL DEFAULT 0, `modifyPackage` integer NOT NULL DEFAULT 0, `createDatabase` integer NOT NULL DEFAULT 0, `deleteDatabase` integer NOT NULL DEFAULT 0, `listDatabases` integer NOT NULL DEFAULT 0, `createNameServer` integer NOT NULL DEFAULT 0, `createDNSZone` integer NOT NULL DEFAULT 0, `deleteZone` integer NOT NULL DEFAULT 0, `addDeleteRecords` integer NOT NULL DEFAULT 0, `createEmail` integer NOT NULL DEFAULT 0, `deleteEmail` integer NOT NULL DEFAULT 0, `emailForwarding` integer NOT NULL DEFAULT 0, `changeEmailPassword` integer NOT NULL DEFAULT 0, `dkimManager` integer NOT NULL DEFAULT 0, `createFTPAccount` integer NOT NULL DEFAULT 0, `deleteFTPAccount` integer NOT NULL DEFAULT 0, `listFTPAccounts` integer NOT NULL DEFAULT 0, `createBackup` integer NOT NULL DEFAULT 0, `restoreBackup` integer NOT NULL DEFAULT 0, `addDeleteDestinations` integer NOT NULL DEFAULT 0, `scheduleBackups` integer NOT NULL DEFAULT 0, `remoteBackups` integer NOT NULL DEFAULT 0, `manageSSL` integer NOT NULL DEFAULT 0, `hostnameSSL` integer NOT NULL DEFAULT 0, `mailServerSSL` integer NOT NULL DEFAULT 0)')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD token varchar(500)')
            except:
                pass

            try:
                cursor.execute("ALTER TABLE loginSystem_administrator ADD secretKey varchar(50) DEFAULT 'None'")
            except:
                pass

            try:
                cursor.execute('alter table databases_databases drop index dbUser;')
            except:
                pass

            try:
                cursor.execute("ALTER TABLE loginSystem_administrator ADD state varchar(15) DEFAULT 'ACTIVE'")
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD securityLevel integer DEFAULT 1')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD defaultSite integer DEFAULT 0')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD twoFA integer DEFAULT 0')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD api integer')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD acl_id integer')
            except:
                pass
            try:
                cursor.execute(
                    'ALTER TABLE loginSystem_administrator ADD FOREIGN KEY (acl_id) REFERENCES loginSystem_acl(id)')
            except:
                pass

            try:
                cursor.execute("insert into loginSystem_acl (id, name, adminStatus) values (1,'admin',1)")
            except:
                pass

            try:
                cursor.execute(
                    "insert into loginSystem_acl (id, name, adminStatus, createNewUser, deleteUser, createWebsite, resellerCenter, modifyWebsite, suspendWebsite, deleteWebsite, createPackage, deletePackage, modifyPackage, createNameServer, restoreBackup) values (2,'reseller',0,1,1,1,1,1,1,1,1,1,1,1,1)")
            except:
                pass
            try:
                cursor.execute(
                    "insert into loginSystem_acl (id, name, createDatabase, deleteDatabase, listDatabases, createDNSZone, deleteZone, addDeleteRecords, createEmail, deleteEmail, emailForwarding, changeEmailPassword, dkimManager, createFTPAccount, deleteFTPAccount, listFTPAccounts, createBackup, manageSSL) values (3,'user', 1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1)")
            except:
                pass

            try:
                cursor.execute("UPDATE loginSystem_administrator SET  acl_id = 1 where userName = 'admin'")
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_acl ADD config longtext')
            except:
                pass

            try:
                cursor.execute("UPDATE loginSystem_acl SET config = '%s' where name = 'admin'" % (Upgrade.AdminACL))
            except BaseException as msg:
                print(str(msg))
                try:
                    import sleep
                except:
                    from time import sleep
                from time import sleep
                sleep(10)

            try:
                cursor.execute(
                    "UPDATE loginSystem_acl SET config = '%s' where name = 'reseller'" % (Upgrade.ResellerACL))
            except:
                pass

            try:
                cursor.execute("UPDATE loginSystem_acl SET config = '%s' where name = 'user'" % (Upgrade.UserACL))
            except:
                pass

            try:
                cursor.execute("alter table loginSystem_administrator drop initUserAccountsLimit")
            except:
                pass

            try:
                cursor.execute(
                    "CREATE TABLE `websiteFunctions_aliasdomains` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `aliasDomain` varchar(75) NOT NULL)")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE `websiteFunctions_aliasdomains` ADD COLUMN `master_id` integer NOT NULL")
            except:
                pass
            try:
                cursor.execute(
                    "ALTER TABLE `websiteFunctions_aliasdomains` ADD CONSTRAINT `websiteFunctions_ali_master_id_726c433d_fk_websiteFu` FOREIGN KEY (`master_id`) REFERENCES `websiteFunctions_websites` (`id`)")
            except:
                pass

            try:
                cursor.execute('ALTER TABLE websiteFunctions_websites ADD config longtext')
            except:
                pass

            try:
                cursor.execute("ALTER TABLE websiteFunctions_websites MODIFY externalApp varchar(30)")
            except:
                pass

            try:
                cursor.execute("ALTER TABLE emailMarketing_smtphosts MODIFY userName varchar(200)")
            except:
                pass

            try:
                cursor.execute("ALTER TABLE emailMarketing_smtphosts MODIFY password varchar(200)")
            except:
                pass

            try:
                cursor.execute("ALTER TABLE websiteFunctions_backups MODIFY fileName varchar(200)")
            except:
                pass

            try:
                cursor.execute("ALTER TABLE loginSystem_acl ADD COLUMN listUsers INT DEFAULT 0;")
            except:
                pass

            try:
                cursor.execute("ALTER TABLE loginSystem_acl ADD COLUMN listEmails INT DEFAULT 1;")
            except:
                pass

            try:
                cursor.execute("ALTER TABLE loginSystem_acl ADD COLUMN listPackages INT DEFAULT 0;")
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_normalbackupdests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(25) NOT NULL,
  `config` longtext NOT NULL,
  PRIMARY KEY (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `cloudAPI_wpdeployments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `cloudAPI_wpdeploymen_owner_id_506ddf01_fk_websiteFu` (`owner_id`),
  CONSTRAINT `cloudAPI_wpdeploymen_owner_id_506ddf01_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_websites` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_normalbackupjobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(25) NOT NULL,
  `config` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_nor_owner_id_3a7a13db_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_nor_owner_id_3a7a13db_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_normalbackupdests` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_normalbackupsites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain_id` int(11) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_nor_domain_id_c03362bc_fk_websiteFu` (`domain_id`),
  KEY `websiteFunctions_nor_owner_id_c6ece6cc_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_nor_domain_id_c03362bc_fk_websiteFu` FOREIGN KEY (`domain_id`) REFERENCES `websiteFunctions_websites` (`id`),
  CONSTRAINT `websiteFunctions_nor_owner_id_c6ece6cc_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_normalbackupjobs` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_normalbackupjoblogs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `status` int(11) NOT NULL,
  `message` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_nor_owner_id_69403e73_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_nor_owner_id_69403e73_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_normalbackupjobs` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            try:
                cursor.execute('ALTER TABLE e_users ADD DiskUsage varchar(200)')
            except:
                pass

            try:
                cursor.execute(
                    'CREATE TABLE `websiteFunctions_wpplugins` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `Name` varchar(255) NOT NULL, `config` longtext NOT NULL, `owner_id` integer NOT NULL)')
            except:
                pass

            try:
                cursor.execute(
                    'ALTER TABLE `websiteFunctions_wpplugins` ADD CONSTRAINT `websiteFunctions_wpp_owner_id_493a02c7_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)')
            except:
                pass

            try:
                cursor.execute(
                    'CREATE TABLE `websiteFunctions_wpsites` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(255) NOT NULL, `path` varchar(255) NOT NULL, `FinalURL` varchar(255) NOT NULL, `AutoUpdates` varchar(100) NOT NULL, `PluginUpdates` varchar(15) NOT NULL, `ThemeUpdates` varchar(15) NOT NULL, `date` datetime(6) NOT NULL, `WPLockState` integer NOT NULL, `owner_id` integer NOT NULL)')
            except:
                pass

            try:
                cursor.execute(
                    'ALTER TABLE `websiteFunctions_wpsites` ADD CONSTRAINT `websiteFunctions_wps_owner_id_6d67df2a_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_websites` (`id`)')
            except:
                pass

            try:
                cursor.execute(
                    'CREATE TABLE `websiteFunctions_wpstaging` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `owner_id` integer NOT NULL, `wpsite_id` integer NOT NULL)')
            except:
                pass

            try:
                cursor.execute(
                    'ALTER TABLE `websiteFunctions_wpstaging` ADD CONSTRAINT `websiteFunctions_wps_owner_id_543d8aec_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_wpsites` (`id`);')
            except:
                pass

            try:
                cursor.execute(
                    'ALTER TABLE `websiteFunctions_wpstaging` ADD CONSTRAINT `websiteFunctions_wps_wpsite_id_82843593_fk_websiteFu` FOREIGN KEY (`wpsite_id`) REFERENCES `websiteFunctions_wpsites` (`id`)')
            except:
                pass

            try:
                cursor.execute(
                    "CREATE TABLE `websiteFunctions_wpsitesbackup` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `WPSiteID` integer NOT NULL, `WebsiteID` integer NOT NULL, `config` longtext NOT NULL, `owner_id` integer NOT NULL); ")
            except:
                pass

            try:
                cursor.execute(
                    "ALTER TABLE `websiteFunctions_wpsitesbackup` ADD CONSTRAINT `websiteFunctions_wps_owner_id_8a8dd0c5_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`); ")
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_remotebackupconfig` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `configtype` varchar(255) NOT NULL,
  `config` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_remotebackupschedule` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `Name` varchar(255) NOT NULL,
  `timeintervel` varchar(200) NOT NULL,
  `fileretention` varchar(200) NOT NULL,
  `lastrun` varchar(200) NOT NULL,
  `config` longtext NOT NULL,
  `RemoteBackupConfig_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_rem_RemoteBackupConfig_i_224c46fb_fk_websiteFu` (`RemoteBackupConfig_id`),
  CONSTRAINT `websiteFunctions_rem_RemoteBackupConfig_i_224c46fb_fk_websiteFu` FOREIGN KEY (`RemoteBackupConfig_id`) REFERENCES `websiteFunctions_remotebackupconfig` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_remotebackupsites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `WPsites` int(11) DEFAULT NULL,
  `database` int(11) DEFAULT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_rem_owner_id_d6c4475a_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_rem_owner_id_d6c4475a_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_remotebackupschedule` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """
CREATE TABLE `websiteFunctions_backupsv2` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `fileName` varchar(255) NOT NULL, `status` integer NOT NULL, `timeStamp` varchar(255) NOT NULL, `BasePath` longtext NOT NULL, `website_id` integer NOT NULL);            
"""
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE `websiteFunctions_backupsv2` ADD CONSTRAINT `websiteFunctions_bac_website_id_3a777e68_fk_websiteFu` FOREIGN KEY (`website_id`) REFERENCES `websiteFunctions_websites` (`id`);"

            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE `websiteFunctions_backupslogsv2` ADD CONSTRAINT `websiteFunctions_bac_owner_id_9e884ff9_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_backupsv2` (`id`);"

            try:
                cursor.execute(query)
            except:
                pass

            query = "CREATE TABLE `websiteFunctions_backupslogsv2` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `timeStamp` varchar(255) NOT NULL, `message` longtext NOT NULL, `owner_id` integer NOT NULL);"

            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE `websiteFunctions_backupslogsv2` ADD CONSTRAINT `websiteFunctions_bac_owner_id_9e884ff9_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_backupsv2` (`id`);"

            try:
                cursor.execute(query)
            except:
                pass

            try:
                cursor.execute("ALTER TABLE websiteFunctions_websites ADD COLUMN BackupLock INT DEFAULT 0;")
            except:
                pass

            ### update ftp issue for ubuntu 22

            try:
                cursor.execute(
                    'ALTER TABLE `users` CHANGE `Password` `Password` VARCHAR(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NOT NULL; ')
            except:
                pass

            query = "CREATE TABLE `IncBackups_oneclickbackups` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `planName` varchar(100) NOT NULL, `months` varchar(100) NOT NULL, `price` varchar(100) NOT NULL, `customer` varchar(255) NOT NULL, `subscription` varchar(255) NOT NULL UNIQUE, `sftpUser` varchar(100) NOT NULL, `config` longtext NOT NULL, `date` datetime(6) NOT NULL, `state` integer NOT NULL, `owner_id` integer NOT NULL);"
            try:
                cursor.execute(query)
            except:
                pass

            query = 'ALTER TABLE `IncBackups_oneclickbackups` ADD CONSTRAINT `IncBackups_oneclickb_owner_id_7b4250a4_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`);'
            try:
                cursor.execute(query)
            except:
                pass

            if Upgrade.FindOperatingSytem() == Ubuntu22 or Upgrade.FindOperatingSytem() == Ubuntu24:
                ### If ftp not installed then upgrade will fail so this command should not do exit

                command = "sed -i 's/MYSQLCrypt md5/MYSQLCrypt crypt/g' /etc/pure-ftpd/db/mysql.conf"
                Upgrade.executioner(command, command, 0)

                command = "systemctl restart pure-ftpd-mysql.service"
                Upgrade.executioner(command, command, 0)

            try:
                clAPVersion = Upgrade.FetchCloudLinuxAlmaVersionVersion()
                if isinstance(clAPVersion, str) and '-' in clAPVersion:
                    type = clAPVersion.split('-')[0]
                    version = int(clAPVersion.split('-')[1])

                    if type == 'al' and version >= 90:
                        command = "sed -i 's/MYSQLCrypt md5/MYSQLCrypt crypt/g' /etc/pure-ftpd/pureftpd-mysql.conf"
                        Upgrade.executioner(command, command, 0)
            except:
                pass

            try:
                connection.close()
            except:
                pass

        except OSError as msg:
            Upgrade.stdOut(str(msg) + " [applyLoginSystemMigrations]")

    @staticmethod
    def s3BackupMigrations():
        try:

            connection, cursor = Upgrade.setupConnection('cyberpanel')

            query = """CREATE TABLE `s3Backups_backupplan` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `bucket` varchar(50) NOT NULL,
  `freq` varchar(50) NOT NULL,
  `retention` int(11) NOT NULL,
  `type` varchar(5) NOT NULL,
  `lastRun` varchar(50) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `s3Backups_backupplan_owner_id_7d058ced_fk_loginSyst` (`owner_id`),
  CONSTRAINT `s3Backups_backupplan_owner_id_7d058ced_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            try:
                cursor.execute('ALTER TABLE s3Backups_backupplan ADD config longtext')
            except:
                pass

            query = """CREATE TABLE `s3Backups_websitesinplan` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `s3Backups_websitesin_owner_id_0e9a4fe3_fk_s3Backups` (`owner_id`),
  CONSTRAINT `s3Backups_websitesin_owner_id_0e9a4fe3_fk_s3Backups` FOREIGN KEY (`owner_id`) REFERENCES `s3Backups_backupplan` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `s3Backups_backuplogs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timeStamp` varchar(200) NOT NULL,
  `level` varchar(5) NOT NULL,
  `msg` varchar(500) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `s3Backups_backuplogs_owner_id_7b4653af_fk_s3Backups` (`owner_id`),
  CONSTRAINT `s3Backups_backuplogs_owner_id_7b4653af_fk_s3Backups` FOREIGN KEY (`owner_id`) REFERENCES `s3Backups_backupplan` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `s3Backups_backupplando` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `bucket` varchar(50) NOT NULL,
  `freq` varchar(50) NOT NULL,
  `retention` int(11) NOT NULL,
  `type` varchar(5) NOT NULL,
  `region` varchar(5) NOT NULL,
  `lastRun` varchar(50) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `s3Backups_backupplan_owner_id_1a3ec86d_fk_loginSyst` (`owner_id`),
  CONSTRAINT `s3Backups_backupplan_owner_id_1a3ec86d_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `s3Backups_websitesinplando` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `s3Backups_websitesin_owner_id_cef3ea04_fk_s3Backups` (`owner_id`),
  CONSTRAINT `s3Backups_websitesin_owner_id_cef3ea04_fk_s3Backups` FOREIGN KEY (`owner_id`) REFERENCES `s3Backups_backupplando` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `s3Backups_backuplogsdo` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timeStamp` varchar(200) NOT NULL,
  `level` varchar(5) NOT NULL,
  `msg` varchar(500) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `s3Backups_backuplogs_owner_id_c7cb5872_fk_s3Backups` (`owner_id`),
  CONSTRAINT `s3Backups_backuplogs_owner_id_c7cb5872_fk_s3Backups` FOREIGN KEY (`owner_id`) REFERENCES `s3Backups_backupplando` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            ##

            query = """CREATE TABLE `s3Backups_minionodes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `endPointURL` varchar(200) NOT NULL,
  `accessKey` varchar(200) NOT NULL,
  `secretKey` varchar(200) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `endPointURL` (`endPointURL`),
  UNIQUE KEY `accessKey` (`accessKey`),
  KEY `s3Backups_minionodes_owner_id_e50993d9_fk_loginSyst` (`owner_id`),
  CONSTRAINT `s3Backups_minionodes_owner_id_e50993d9_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `s3Backups_backupplanminio` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `freq` varchar(50) NOT NULL,
  `retention` int(11) NOT NULL,
  `lastRun` varchar(50) NOT NULL,
  `minioNode_id` int(11) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `s3Backups_backupplan_minioNode_id_a4eaf917_fk_s3Backups` (`minioNode_id`),
  KEY `s3Backups_backupplan_owner_id_d6830e67_fk_loginSyst` (`owner_id`),
  CONSTRAINT `s3Backups_backupplan_minioNode_id_a4eaf917_fk_s3Backups` FOREIGN KEY (`minioNode_id`) REFERENCES `s3Backups_minionodes` (`id`),
  CONSTRAINT `s3Backups_backupplan_owner_id_d6830e67_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `s3Backups_websitesinplanminio` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `s3Backups_websitesin_owner_id_224ce049_fk_s3Backups` (`owner_id`),
  CONSTRAINT `s3Backups_websitesin_owner_id_224ce049_fk_s3Backups` FOREIGN KEY (`owner_id`) REFERENCES `s3Backups_backupplanminio` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `s3Backups_backuplogsminio` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timeStamp` varchar(200) NOT NULL,
  `level` varchar(5) NOT NULL,
  `msg` varchar(500) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `s3Backups_backuplogs_owner_id_f19e1736_fk_s3Backups` (`owner_id`),
  CONSTRAINT `s3Backups_backuplogs_owner_id_f19e1736_fk_s3Backups` FOREIGN KEY (`owner_id`) REFERENCES `s3Backups_backupplanminio` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            try:
                connection.close()
            except:
                pass

        except OSError as msg:
            Upgrade.stdOut(str(msg) + " [applyLoginSystemMigrations]")

    @staticmethod
    def mailServerMigrations():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            try:
                cursor.execute(
                    'ALTER TABLE `e_domains` ADD COLUMN `childOwner_id` integer')
            except:
                pass

            try:
                cursor.execute(
                    'ALTER TABLE e_users ADD mail varchar(200)')
            except:
                pass

            try:
                cursor.execute(
                    'ALTER TABLE e_users MODIFY password varchar(200)')
            except:
                pass

            try:
                cursor.execute(
                    'ALTER TABLE e_forwardings DROP PRIMARY KEY;ALTER TABLE e_forwardings ADD id INT AUTO_INCREMENT PRIMARY KEY')
            except:
                pass

            query = """CREATE TABLE `emailPremium_domainlimits` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `limitStatus` int(11) NOT NULL,
  `monthlyLimit` int(11) NOT NULL,
  `monthlyUsed` int(11) NOT NULL,
  `domain_id` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `emailPremium_domainlimits_domain_id_303ab297_fk_e_domains_domain` (`domain_id`),
  CONSTRAINT `emailPremium_domainlimits_domain_id_303ab297_fk_e_domains_domain` FOREIGN KEY (`domain_id`) REFERENCES `e_domains` (`domain`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailPremium_emaillimits` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `limitStatus` int(11) NOT NULL,
  `monthlyLimits` int(11) NOT NULL,
  `monthlyUsed` int(11) NOT NULL,
  `hourlyLimit` int(11) NOT NULL,
  `hourlyUsed` int(11) NOT NULL,
  `emailLogs` int(11) NOT NULL,
  `email_id` varchar(80) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `emailPremium_emaillimits_email_id_1c111df5_fk_e_users_email` (`email_id`),
  CONSTRAINT `emailPremium_emaillimits_email_id_1c111df5_fk_e_users_email` FOREIGN KEY (`email_id`) REFERENCES `e_users` (`email`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailPremium_emaillogs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `destination` varchar(200) NOT NULL,
  `timeStamp` varchar(200) NOT NULL,
  `email_id` varchar(80) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `emailPremium_emaillogs_email_id_9ef49552_fk_e_users_email` (`email_id`),
  CONSTRAINT `emailPremium_emaillogs_email_id_9ef49552_fk_e_users_email` FOREIGN KEY (`email_id`) REFERENCES `e_users` (`email`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            try:
                connection.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def emailMarketingMigrationsa():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            query = """CREATE TABLE `emailMarketing_emailmarketing` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `userName` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `userName` (`userName`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailMarketing_emaillists` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `listName` varchar(50) NOT NULL,
  `dateCreated` varchar(200) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `listName` (`listName`),
  KEY `emailMarketing_email_owner_id_bf1b4530_fk_websiteFu` (`owner_id`),
  CONSTRAINT `emailMarketing_email_owner_id_bf1b4530_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_websites` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = 'ALTER TABLE emailMarketing_emaillists ADD COLUMN verified INT DEFAULT 0'

            try:
                cursor.execute(query)
            except:
                pass

            query = 'ALTER TABLE emailMarketing_emaillists ADD COLUMN notVerified INT DEFAULT 0'

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailMarketing_emailsinlist` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(50) NOT NULL,
  `firstName` varchar(20) NOT NULL,
  `lastName` varchar(20) NOT NULL,
  `verificationStatus` varchar(100) NOT NULL,
  `dateCreated` varchar(200) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `emailMarketing_email_owner_id_c5c27005_fk_emailMark` (`owner_id`),
  CONSTRAINT `emailMarketing_email_owner_id_c5c27005_fk_emailMark` FOREIGN KEY (`owner_id`) REFERENCES `emailMarketing_emaillists` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailMarketing_smtphosts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host` varchar(150) NOT NULL,
  `port` varchar(10) NOT NULL,
  `userName` varchar(50) NOT NULL,
  `password` varchar(50) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `host` (`host`),
  KEY `emailMarketing_smtph_owner_id_8b2d4ac7_fk_loginSyst` (`owner_id`),
  CONSTRAINT `emailMarketing_smtph_owner_id_8b2d4ac7_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailMarketing_emailtemplate` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `subject` varchar(1000) NOT NULL,
  `fromName` varchar(100) NOT NULL,
  `fromEmail` varchar(150) NOT NULL,
  `replyTo` varchar(150) NOT NULL,
  `emailMessage` varchar(30000) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `emailMarketing_email_owner_id_d27e1d00_fk_loginSyst` (`owner_id`),
  CONSTRAINT `emailMarketing_email_owner_id_d27e1d00_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailMarketing_emailjobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` varchar(200) NOT NULL,
  `host` varchar(1000) NOT NULL,
  `totalEmails` int(11) NOT NULL,
  `sent` int(11) NOT NULL,
  `failed` int(11) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `emailMarketing_email_owner_id_73ee4827_fk_emailMark` (`owner_id`),
  CONSTRAINT `emailMarketing_email_owner_id_73ee4827_fk_emailMark` FOREIGN KEY (`owner_id`) REFERENCES `emailMarketing_emailtemplate` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `mailServer_pipeprograms` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `source` varchar(80) NOT NULL,
  `destination` longtext NOT NULL,
  PRIMARY KEY (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `emailMarketing_validationlog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `status` int(11) NOT NULL,
  `message` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `emailMarketing_valid_owner_id_240ad36e_fk_emailMark` (`owner_id`),
  CONSTRAINT `emailMarketing_valid_owner_id_240ad36e_fk_emailMark` FOREIGN KEY (`owner_id`) REFERENCES `emailMarketing_emaillists` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            try:
                connection.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def dockerMigrations():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            query = """CREATE TABLE `dockerManager_containers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `cid` varchar(64) NOT NULL,
  `image` varchar(50) NOT NULL,
  `tag` varchar(50) NOT NULL,
  `memory` int(11) NOT NULL,
  `ports` longtext NOT NULL,
  `env` longtext NOT NULL,
  `startOnReboot` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `dockerManager_contai_admin_id_58fb62b7_fk_loginSyst` (`admin_id`),
  CONSTRAINT `dockerManager_contai_admin_id_58fb62b7_fk_loginSyst` FOREIGN KEY (`admin_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD config longtext')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE loginSystem_acl ADD config longtext')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE dockerManager_containers ADD volumes longtext')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE dockerManager_containers MODIFY COLUMN name VARCHAR(150);')
            except:
                pass

            try:
                connection.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def containerMigrations():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            query = """CREATE TABLE `containerization_containerlimits` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cpuPers` varchar(10) NOT NULL,
  `IO` varchar(10) NOT NULL,
  `IOPS` varchar(10) NOT NULL,
  `memory` varchar(10) NOT NULL,
  `networkSpeed` varchar(10) NOT NULL,
  `networkHexValue` varchar(10) NOT NULL,
  `enforce` int(11) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `containerization_con_owner_id_494eb637_fk_websiteFu` (`owner_id`),
  CONSTRAINT `containerization_con_owner_id_494eb637_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_websites` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_dockerpackages` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `Name` varchar(100) NOT NULL, `CPUs` integer NOT NULL, `Ram` integer NOT NULL, `Bandwidth` longtext NOT NULL, `DiskSpace` longtext NOT NULL, `config` longtext NOT NULL);"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_dockersites` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `ComposePath` longtext NOT NULL, `SitePath` longtext NOT NULL, `MySQLPath` longtext NOT NULL, `state` integer NOT NULL, `SiteType` integer NOT NULL, `MySQLDBName` varchar(100) NOT NULL, `MySQLDBNUser` varchar(100) NOT NULL, `CPUsMySQL` varchar(100) NOT NULL, `MemoryMySQL` varchar(100) NOT NULL, `port` varchar(100) NOT NULL, `CPUsSite` varchar(100) NOT NULL, `MemorySite` varchar(100) NOT NULL, `SiteName` varchar(255) NOT NULL UNIQUE, `finalURL` longtext NOT NULL, `blogTitle` longtext NOT NULL, `adminUser` varchar(100) NOT NULL, `adminEmail` varchar(100) NOT NULL, `admin_id` integer NOT NULL);"""
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE `websiteFunctions_dockersites` ADD CONSTRAINT `websiteFunctions_doc_admin_id_88f5cb6d_fk_websiteFu` FOREIGN KEY (`admin_id`) REFERENCES `websiteFunctions_websites` (`id`);"
            try:
                cursor.execute(query)
            except:
                pass

            query = "CREATE TABLE `websiteFunctions_packageassignment` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `package_id` integer NOT NULL, `user_id` integer NOT NULL);"
            try:
                cursor.execute(query)
            except:
                pass


            query = """ALTER TABLE `websiteFunctions_packageassignment` ADD CONSTRAINT `websiteFunctions_pac_package_id_420b6aff_fk_websiteFu` FOREIGN KEY (`package_id`) REFERENCES `websiteFunctions_dockerpackages` (`id`);"""
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE `websiteFunctions_packageassignment` ADD CONSTRAINT `websiteFunctions_pac_user_id_864958ce_fk_loginSyst` FOREIGN KEY (`user_id`) REFERENCES `loginSystem_administrator` (`id`);"
            try:
                cursor.execute(query)
            except:
                pass

            query = """ALTER TABLE `websiteFunctions_dockersites` ADD CONSTRAINT `websiteFunctions_doc_admin_id_88f5cb6d_fk_websiteFu` FOREIGN KEY (`admin_id`) REFERENCES `websiteFunctions_websites` (`id`);"""
            try:
                cursor.execute(query)
            except:
                pass

            try:
                connection.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def CLMigrations():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            query = """CREATE TABLE `CLManager_clpackages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `speed` varchar(50) NOT NULL,
  `vmem` varchar(50) NOT NULL,
  `pmem` varchar(50) NOT NULL,
  `io` varchar(50) NOT NULL,
  `iops` varchar(50) NOT NULL,
  `ep` varchar(50) NOT NULL,
  `nproc` varchar(50) NOT NULL,
  `inodessoft` varchar(50) NOT NULL,
  `inodeshard` varchar(50) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `CLManager_clpackages_owner_id_9898c1e8_fk_packages_package_id` (`owner_id`),
  CONSTRAINT `CLManager_clpackages_owner_id_9898c1e8_fk_packages_package_id` FOREIGN KEY (`owner_id`) REFERENCES `packages_package` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN allowFullDomain INT DEFAULT 1;"
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN enforceDiskLimits INT DEFAULT 0;"
            try:
                cursor.execute(query)
            except:
                pass

            try:
                connection.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def manageServiceMigrations():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            query = """CREATE TABLE `manageServices_pdnsstatus` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `serverStatus` int(11) NOT NULL,
  `type` varchar(6) NOT NULL,
  PRIMARY KEY (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            try:
                cursor.execute('alter table manageServices_pdnsstatus add masterServer varchar(200)')
            except:
                pass

            try:
                cursor.execute('alter table manageServices_pdnsstatus add masterIP varchar(200)')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE `manageServices_pdnsstatus` CHANGE `type` `type` VARCHAR(10) NULL;')
            except:
                pass

            query = '''CREATE TABLE `databases_dbmeta` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key` varchar(200) NOT NULL,
  `value` longtext NOT NULL,
  `database_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `databases_dbmeta_database_id_777997bc_fk_databases_databases_id` (`database_id`),
  CONSTRAINT `databases_dbmeta_database_id_777997bc_fk_databases_databases_id` FOREIGN KEY (`database_id`) REFERENCES `databases_databases` (`id`)
)'''

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `filemanager_trash` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `originalPath` varchar(500) NOT NULL,
  `fileName` varchar(200) NOT NULL,
  `website_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `filemanager_trash_website_id_e2762f3c_fk_websiteFu` (`website_id`),
  CONSTRAINT `filemanager_trash_website_id_e2762f3c_fk_websiteFu` FOREIGN KEY (`website_id`) REFERENCES `websiteFunctions_websites` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `databases_globaluserdb` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(200) NOT NULL,
  `password` varchar(500) NOT NULL,
  `token` varchar(20) NOT NULL,
  PRIMARY KEY (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = "CREATE TABLE `databases_databasesusers` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `username` varchar(50) NOT NULL UNIQUE, `owner_id` integer NOT NULL)"

            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE `databases_databasesusers` ADD CONSTRAINT `databases_databasesu_owner_id_908fc638_fk_databases` FOREIGN KEY (`owner_id`) REFERENCES `databases_databases` (`id`);"

            try:
                cursor.execute(query)
            except:
                pass

            try:
                connection.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def GeneralMigrations():
        try:

            cwd = os.getcwd()
            os.chdir('/usr/local/CyberCP')

            command = '/usr/local/CyberPanel/bin/python manage.py makemigrations'
            Upgrade.executioner(command, 'python manage.py makemigrations', 0)

            command = '/usr/local/CyberPanel/bin/python manage.py makemigrations'
            Upgrade.executioner(command, '/usr/local/CyberPanel/bin/python manage.py migrate', 0)

            os.chdir(cwd)

        except:
            pass

    @staticmethod
    def IncBackupMigrations():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            query = """CREATE TABLE `IncBackups_backupjob` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `destination` varchar(300) NOT NULL,
  `frequency` varchar(50) NOT NULL,
  `websiteData` int(11) NOT NULL,
  `websiteDatabases` int(11) NOT NULL,
  `websiteDataEmails` int(11) NOT NULL,
  PRIMARY KEY (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = 'ALTER TABLE IncBackups_backupjob ADD retention integer DEFAULT 0'

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `IncBackups_incjob` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` datetime(6) NOT NULL,
  `website_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IncBackups_incjob_website_id_aad31bf6_fk_websiteFu` (`website_id`),
  CONSTRAINT `IncBackups_incjob_website_id_aad31bf6_fk_websiteFu` FOREIGN KEY (`website_id`) REFERENCES `websiteFunctions_websites` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `IncBackups_jobsites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `website` varchar(300) NOT NULL,
  `job_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IncBackups_jobsites_job_id_494a1f69_fk_IncBackups_backupjob_id` (`job_id`),
  CONSTRAINT `IncBackups_jobsites_job_id_494a1f69_fk_IncBackups_backupjob_id` FOREIGN KEY (`job_id`) REFERENCES `IncBackups_backupjob` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `IncBackups_jobsnapshots` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` varchar(300) NOT NULL,
  `snapshotid` varchar(50) NOT NULL,
  `job_id` int(11) NOT NULL,
  `destination` varchar(200) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IncBackups_jobsnapshots_job_id_a8237ca8_fk_IncBackups_incjob_id` (`job_id`),
  CONSTRAINT `IncBackups_jobsnapshots_job_id_a8237ca8_fk_IncBackups_incjob_id` FOREIGN KEY (`job_id`) REFERENCES `IncBackups_incjob` (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_gitlogs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` datetime(6) NOT NULL,
  `type` varchar(5) NOT NULL,
  `message` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_git_owner_id_ce74c7de_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_git_owner_id_ce74c7de_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_websites` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_backupjob` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `logFile` varchar(1000) NOT NULL,
  `ipAddress` varchar(50) NOT NULL,
  `port` varchar(15) NOT NULL,
  `jobFailedSites` int(11) NOT NULL,
  `jobSuccessSites` int(11) NOT NULL,
  `location` int(11) NOT NULL,
  PRIMARY KEY (`id`)
)"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_backupjoblogs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `message` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  `status` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_bac_owner_id_af3d15f9_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_bac_owner_id_af3d15f9_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_backupjob` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_gdrive` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `auth` longtext NOT NULL,
  `runTime` varchar(20) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `websiteFunctions_gdr_owner_id_b5b1e86f_fk_loginSyst` (`owner_id`),
  CONSTRAINT `websiteFunctions_gdr_owner_id_b5b1e86f_fk_loginSyst` FOREIGN KEY (`owner_id`) REFERENCES `loginSystem_administrator` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_gdrivesites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(200) NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_gdr_owner_id_ff78b305_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_gdr_owner_id_ff78b305_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_gdrive` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE `websiteFunctions_gdrivejoblogs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `status` int(11) NOT NULL,
  `message` longtext NOT NULL,
  `owner_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `websiteFunctions_gdr_owner_id_4cf7983e_fk_websiteFu` (`owner_id`),
  CONSTRAINT `websiteFunctions_gdr_owner_id_4cf7983e_fk_websiteFu` FOREIGN KEY (`owner_id`) REFERENCES `websiteFunctions_gdrive` (`id`)
)"""

            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE `websiteFunctions_childdomains` ADD `alais` INT NOT NULL DEFAULT '0' AFTER `master_id`; "
            try:
                cursor.execute(query)
            except:
                pass


            try:
                connection.close()
            except:
                pass
        except:
            pass

    @staticmethod
    def enableServices():
        try:
            servicePath = '/home/cyberpanel/powerdns'
            writeToFile = open(servicePath, 'w+')
            writeToFile.close()

            servicePath = '/home/cyberpanel/postfix'
            writeToFile = open(servicePath, 'w+')
            writeToFile.close()

            servicePath = '/home/cyberpanel/pureftpd'
            writeToFile = open(servicePath, 'w+')
            writeToFile.close()
        except:
            pass

    @staticmethod
    def backupCriticalFiles():
        """Backup all critical configuration files before upgrade"""
        import tempfile
        backup_dir = tempfile.mkdtemp(prefix='cyberpanel_backup_')
        
        critical_files = [
            '/usr/local/CyberCP/CyberCP/settings.py',
            '/usr/local/CyberCP/.git/config',  # Git configuration
        ]
        
        # Also backup any custom configurations
        custom_configs = [
            '/usr/local/CyberCP/baseTemplate/static/baseTemplate/custom/',
            '/usr/local/CyberCP/public/phpmyadmin/config.inc.php',
            '/usr/local/CyberCP/rainloop/data/_data_/',
        ]
        
        # Backup Imunify360 directories and configuration
        imunify_paths = [
            '/usr/local/CyberCP/public/imunify',
            '/usr/local/CyberCP/public/imunifyav',
            '/etc/sysconfig/imunify360/integration.conf',
        ]

        for imunify_path in imunify_paths:
            if os.path.exists(imunify_path):
                if os.path.isdir(imunify_path):
                    custom_configs.append(imunify_path)
                else:
                    critical_files.append(imunify_path)
        
        backed_up_files = {}
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                try:
                    backup_path = os.path.join(backup_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, backup_path)
                    backed_up_files[file_path] = backup_path
                    Upgrade.stdOut(f"Backed up {file_path}")
                except Exception as e:
                    Upgrade.stdOut(f"Failed to backup {file_path}: {str(e)}")
        
        # Backup directories
        for dir_path in custom_configs:
            if os.path.exists(dir_path):
                try:
                    backup_path = os.path.join(backup_dir, os.path.basename(dir_path))
                    shutil.copytree(dir_path, backup_path)
                    backed_up_files[dir_path] = backup_path
                    Upgrade.stdOut(f"Backed up directory {dir_path}")
                except Exception as e:
                    Upgrade.stdOut(f"Failed to backup {dir_path}: {str(e)}")
        
        return backup_dir, backed_up_files
    
    @staticmethod
    def restoreCriticalFiles(backup_dir, backed_up_files):
        """Restore critical configuration files after upgrade"""
        for original_path, backup_path in backed_up_files.items():
            # Skip settings.py - we'll handle it separately to preserve INSTALLED_APPS
            if 'settings.py' in original_path:
                Upgrade.stdOut(f"Skipping {original_path} - will be handled separately")
                continue
            
            try:
                if os.path.isdir(backup_path):
                    if os.path.exists(original_path):
                        shutil.rmtree(original_path)
                    shutil.copytree(backup_path, original_path)
                else:
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(original_path), exist_ok=True)
                    shutil.copy2(backup_path, original_path)
                Upgrade.stdOut(f"Restored {original_path}")
            except Exception as e:
                Upgrade.stdOut(f"Failed to restore {original_path}: {str(e)}")
    
    @staticmethod
    def downloadAndUpgrade(versionNumbring, branch):
        try:
            ## Download latest version.

            ## Backup all critical files
            Upgrade.stdOut("Backing up critical configuration files...")
            backup_dir, backed_up_files = Upgrade.backupCriticalFiles()

            ## CyberPanel DB Creds
            dbName = settings.DATABASES['default']['NAME']
            dbUser = settings.DATABASES['default']['USER']
            password = settings.DATABASES['default']['PASSWORD']
            host = settings.DATABASES['default']['HOST']
            port = settings.DATABASES['default']['PORT']

            ## Root DB Creds

            rootdbName = settings.DATABASES['rootdb']['NAME']
            rootdbdbUser = settings.DATABASES['rootdb']['USER']
            rootdbpassword = settings.DATABASES['rootdb']['PASSWORD']

            ## Complete db string

            completDBString = """\nDATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '%s',
        'USER': '%s',
        'PASSWORD': '%s',
        'HOST': '%s',
        'PORT':'%s'
    },
    'rootdb': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '%s',
        'USER': '%s',
        'PASSWORD': '%s',
        'HOST': '%s',
        'PORT': '%s',
    },
}\n""" % (dbName, dbUser, password, host, port, rootdbName, rootdbdbUser, rootdbpassword, host, port)

            settingsFile = '/usr/local/CyberCP/CyberCP/settings.py'

            Upgrade.stdOut("Critical files backed up to: " + backup_dir)

            ## Always do a fresh clone for clean upgrade
            
            Upgrade.stdOut("Performing clean upgrade by removing and re-cloning CyberPanel...")
            
            # Set git config first
            command = 'git config --global user.email "support@cyberpanel.net"'
            if not Upgrade.executioner(command, command, 1):
                return 0, 'Failed to execute %s' % (command)

            command = 'git config --global user.name "CyberPanel"'
            if not Upgrade.executioner(command, command, 1):
                return 0, 'Failed to execute %s' % (command)
            
            # Change to parent directory
            os.chdir('/usr/local')

            # Remove old CyberCP directory
            if os.path.exists('CyberCP'):
                Upgrade.stdOut("Removing old CyberCP directory...")
                try:
                    shutil.rmtree('CyberCP')
                    Upgrade.stdOut("Old CyberCP directory removed successfully.")
                except Exception as e:
                    Upgrade.stdOut(f"Error removing CyberCP directory: {str(e)}")
                    # Try to restore backup if removal fails
                    Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)
                    return 0, 'Failed to remove old CyberCP directory'

            # Clone the new repository directly to CyberCP
            Upgrade.stdOut("Cloning fresh CyberPanel repository...")
            command = 'git clone https://github.com/usmannasir/cyberpanel CyberCP'
            if not Upgrade.executioner(command, command, 1):
                # Try to restore backup if clone fails
                Upgrade.stdOut("Clone failed, attempting to restore backup...")
                Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)
                return 0, 'Failed to clone CyberPanel repository'
            
            # Checkout the correct branch
            os.chdir('/usr/local/CyberCP')
            command = 'git checkout %s' % (branch)
            if not Upgrade.executioner(command, command, 1):
                Upgrade.stdOut(f"Warning: Failed to checkout branch {branch}, continuing with default branch")
            
            # Restore all backed up configuration files (except settings.py)
            Upgrade.stdOut("Restoring configuration files...")
            Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)

            ## Handle settings.py separately to preserve NEW INSTALLED_APPS while keeping old database credentials
            
            # Read the NEW settings file from the fresh clone (has new INSTALLED_APPS like 'aiScanner')
            settingsData = open(settingsFile, 'r').read()
            
            # Replace only the DATABASES section with our saved credentials
            import re
            
            # More precise pattern to match the entire DATABASES dictionary including nested dictionaries
            # This pattern looks for DATABASES = { ... } including the 'default' and 'rootdb' nested dicts
            database_pattern = r'DATABASES\s*=\s*\{[^}]*\{[^}]*\}[^}]*\{[^}]*\}[^}]*\}'
            
            # Replace the DATABASES section with our saved credentials from before upgrade
            settingsData = re.sub(database_pattern, completDBString.strip(), settingsData, flags=re.DOTALL)
            
            # Write back the updated settings
            writeToFile = open(settingsFile, 'w')
            writeToFile.write(settingsData)
            writeToFile.close()

            Upgrade.stdOut('Settings file updated with database credentials while preserving new INSTALLED_APPS!')

            Upgrade.staticContent()

            # Restore Imunify360 after upgrade
            Upgrade.restoreImunify360()

            # FINAL STEP: Ensure Imunify360 execute permissions are set
            Upgrade.finalImunifyPermissions()

            return 1, None

        except BaseException as msg:
            return 0, str(msg)

    @staticmethod
    def installLSCPD(branch):
        try:

            if Upgrade.SoftUpgrade == 0:

                Upgrade.stdOut("Starting LSCPD installation..")

                cwd = os.getcwd()

                os.chdir('/usr/local')

                command = 'yum -y install gcc gcc-c++ make autoconf glibc rcs'
                Upgrade.executioner(command, 'LSCPD Pre-reqs [one]', 0)

                ##

                lscpdPath = '/usr/local/lscp/bin/lscpd'

                if os.path.exists(lscpdPath):
                    os.remove(lscpdPath)

                try:
                    try:
                        result = subprocess.run('uname -a', capture_output=True, universal_newlines=True, shell=True)
                    except:
                        result = subprocess.run('uname -a', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

                    if result.stdout.find('aarch64') == -1:
                        lscpdSelection = 'lscpd-0.3.1'
                        if os.path.exists(Upgrade.UbuntuPath):
                            result = open(Upgrade.UbuntuPath, 'r').read()
                            if result.find('22.04') > -1 or result.find('24.04') > -1:
                                lscpdSelection = 'lscpd.0.4.0'
                    else:
                        lscpdSelection = 'lscpd.aarch64'

                except:

                    lscpdSelection = 'lscpd-0.3.1'
                    if os.path.exists(Upgrade.UbuntuPath):
                        result = open(Upgrade.UbuntuPath, 'r').read()
                        if result.find('22.04') > -1 or result.find('24.04') > -1:
                            lscpdSelection = 'lscpd.0.4.0'

                command = f'cp -f /usr/local/CyberCP/{lscpdSelection} /usr/local/lscp/bin/{lscpdSelection}'
                Upgrade.executioner(command, command, 0)

                command = 'rm -f /usr/local/lscp/bin/lscpd'
                Upgrade.executioner(command, command, 0)

                command = f'mv /usr/local/lscp/bin/{lscpdSelection} /usr/local/lscp/bin/lscpd'
                Upgrade.executioner(command, command, 0)

                command = f'chmod 755 {lscpdPath}'
                Upgrade.executioner(command, 'LSCPD Download.', 0)

                command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel which curl'
                Upgrade.executioner(command, 'LSCPD Pre-reqs [two]', 0)

                try:
                    pwd.getpwnam('lscpd')
                except KeyError:
                    command = 'adduser lscpd -M -d /usr/local/lscp'
                    Upgrade.executioner(command, 'Add user LSCPD', 0)

                try:
                    grp.getgrnam('lscpd')
                except KeyError:
                    command = 'groupadd lscpd'
                    Upgrade.executioner(command, 'Add group LSCPD', 0)

                command = 'usermod -a -G lscpd lscpd'
                Upgrade.executioner(command, 'Add group LSCPD', 0)

                command = 'usermod -a -G lsadm lscpd'
                Upgrade.executioner(command, 'Add group LSCPD', 0)

                command = 'systemctl daemon-reload'
                Upgrade.executioner(command, 'daemon-reload LSCPD', 0)

                command = 'systemctl restart lscpd'
                Upgrade.executioner(command, 'Restart LSCPD', 0)

                os.chdir(cwd)

                Upgrade.stdOut("LSCPD successfully installed!")

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [installLSCPD]")

    ### disable dkim signing in rspamd in ref to https://github.com/usmannasir/cyberpanel/issues/1176
    @staticmethod
    def FixRSPAMDConfig():
        RSPAMDConf = '/etc/rspamd'
        postfixConf = '/etc/postfix/main.cf'

        if os.path.exists(RSPAMDConf):
            DKIMPath = '/etc/rspamd/local.d/dkim_signing.conf'

            WriteToFile = open(DKIMPath, 'w')
            WriteToFile.write('enabled = false;\n')
            WriteToFile.close()

            if os.path.exists(postfixConf):
                appendpath = "/etc/postfix/main.cf"

                lines = open(appendpath, 'r').readlines()

                WriteToFile = open(appendpath, 'w')

                for line in lines:

                    if line.find('smtpd_milters') > -1:
                        continue
                    elif line.find('non_smtpd_milters') > -1:
                        continue
                    elif line.find('milter_default_action') > -1:
                        continue
                    else:
                        WriteToFile.write(line)

                RSPAMDConfContent = '''
### Please do not edit this line, editing this line could break configurations
smtpd_milters = inet:127.0.0.1:8891, inet:127.0.0.1:11332
non_smtpd_milters = $smtpd_milters
milter_default_action = accept
'''
                WriteToFile.write(RSPAMDConfContent)

                WriteToFile.close()

                command = 'systemctl restart postfix && systemctl restart rspamd'
                Upgrade.executioner(command, 'postfix and rspamd restart', 0, True)

    #### if you update this function needs to update this function on plogical.acl.py as well
    @staticmethod
    def fixPermissions():
        try:

            try:
                def generate_pass(length=14):
                    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
                    size = length
                    return ''.join(random.choice(chars) for x in range(size))

                content = """<?php
$_ENV['snappymail_INCLUDE_AS_API'] = true;
include '/usr/local/CyberCP/public/snappymail/index.php';

$oConfig = \snappymail\Api::Config();
$oConfig->SetPassword('%s');
echo $oConfig->Save() ? 'Done' : 'Error';

?>""" % (generate_pass())

                writeToFile = open('/usr/local/CyberCP/public/snappymail.php', 'w')
                writeToFile.write(content)
                writeToFile.close()

                command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/data"
                subprocess.call(shlex.split(command))

            except:
                pass

            Upgrade.stdOut("Fixing permissions..")

            command = "usermod -G lscpd,lsadm,nobody lscpd"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "usermod -G lscpd,lsadm,nogroup lscpd"
            Upgrade.executioner(command, 'chown core code', 0)

            ###### fix Core CyberPanel permissions

            command = "find /usr/local/CyberCP -type d -exec chmod 0755 {} \;"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "find /usr/local/CyberCP -type f -exec chmod 0644 {} \;"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chmod -R 755 /usr/local/CyberCP/bin"
            Upgrade.executioner(command, 'chown core code', 0)

            ## change owner

            command = "chown -R root:root /usr/local/CyberCP"
            Upgrade.executioner(command, 'chown core code', 0)

            ########### Fix LSCPD

            command = "find /usr/local/lscp -type d -exec chmod 0755 {} \;"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "find /usr/local/lscp -type f -exec chmod 0644 {} \;"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chmod -R 755 /usr/local/lscp/bin"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chmod -R 755 /usr/local/lscp/fcgi-bin"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp"
            Upgrade.executioner(command, 'chown core code', 0)

            ## change owner

            command = "chown -R root:root /usr/local/lscp"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chmod 700 /usr/local/CyberCP/cli/cyberPanel.py"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chmod 700 /usr/local/CyberCP/plogical/upgradeCritical.py"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chmod 755 /usr/local/CyberCP/postfixSenderPolicy/client.py"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chmod 640 /usr/local/CyberCP/CyberCP/settings.py"
            Upgrade.executioner(command, 'chown core code', 0)

            command = "chown root:cyberpanel /usr/local/CyberCP/CyberCP/settings.py"
            Upgrade.executioner(command, 'chown core code', 0)

            command = 'chmod +x /usr/local/CyberCP/CLManager/CLPackages.py'
            Upgrade.executioner(command, 'chmod CLPackages', 0)

            files = ['/etc/yum.repos.d/MariaDB.repo', '/etc/pdns/pdns.conf', '/etc/systemd/system/lscpd.service',
                     '/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                     '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                     '/etc/dovecot/dovecot.conf', '/usr/local/lsws/conf/httpd_config.xml',
                     '/usr/local/lsws/conf/modsec.conf', '/usr/local/lsws/conf/httpd.conf']

            for items in files:
                command = 'chmod 644 %s' % (items)
                Upgrade.executioner(command, 'chown core code', 0)

            impFile = ['/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                       '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                       '/etc/dovecot/dovecot.conf', '/etc/pdns/pdns.conf', '/etc/pure-ftpd/db/mysql.conf',
                       '/etc/powerdns/pdns.conf']

            for items in impFile:
                command = 'chmod 600 %s' % (items)
                Upgrade.executioner(command, 'chown core code', 0)

            command = 'chmod 640 /etc/postfix/*.cf'
            subprocess.call(command, shell=True)

            command = 'chmod 640 /etc/dovecot/*.conf'
            subprocess.call(command, shell=True)

            command = 'chmod 640 /etc/dovecot/dovecot-sql.conf.ext'
            subprocess.call(command, shell=True)

            fileM = ['/usr/local/lsws/FileManager/', '/usr/local/CyberCP/install/FileManager',
                     '/usr/local/CyberCP/serverStatus/litespeed/FileManager',
                     '/usr/local/lsws/Example/html/FileManager']

            for items in fileM:
                try:
                    shutil.rmtree(items)
                except:
                    pass

            command = 'chmod 755 /etc/pure-ftpd/'
            subprocess.call(command, shell=True)

            command = 'chmod 644 /etc/dovecot/dovecot.conf'
            subprocess.call(command, shell=True)

            command = 'chmod 644 /etc/postfix/main.cf'
            subprocess.call(command, shell=True)

            command = 'chmod 644 /etc/postfix/dynamicmaps.cf'
            subprocess.call(command, shell=True)

            command = 'chmod +x /usr/local/CyberCP/plogical/renew.py'
            Upgrade.executioner(command, command, 0)

            command = 'chmod +x /usr/local/CyberCP/CLManager/CLPackages.py'
            Upgrade.executioner(command, command, 0)

            clScripts = ['/usr/local/CyberCP/CLScript/panel_info.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxPackages.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxUsers.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py'
                , '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxDB.py', '/usr/local/CyberCP/CLScript/UserInfo.py']

            for items in clScripts:
                command = 'chmod +x %s' % (items)
                Upgrade.executioner(command, 0)

            command = 'chmod 600 /usr/local/CyberCP/plogical/adminPass.py'
            Upgrade.executioner(command, 0)

            command = 'chmod 600 /etc/cagefs/exclude/cyberpanelexclude'
            Upgrade.executioner(command, 0)

            command = "find /usr/local/CyberCP/ -name '*.pyc' -delete"
            Upgrade.executioner(command, 0)

            if os.path.exists(Upgrade.CentOSPath) or os.path.exists(Upgrade.openEulerPath):
                command = 'chown root:pdns /etc/pdns/pdns.conf'
                Upgrade.executioner(command, 0)

                command = 'chmod 640 /etc/pdns/pdns.conf'
                Upgrade.executioner(command, 0)
            else:
                command = 'chown root:pdns /etc/powerdns/pdns.conf'
                Upgrade.executioner(command, 0)

                command = 'chmod 640 /etc/powerdns/pdns.conf'
                Upgrade.executioner(command, 0)

            command = 'chmod 640 /usr/local/lscp/cyberpanel/logs/access.log'
            Upgrade.executioner(command, 0)

            command = '/usr/local/lsws/lsphp83/bin/php /usr/local/CyberCP/public/snappymail.php'
            Upgrade.executioner_silent(command, 'Configure SnappyMail')

            command = 'chmod 600 /usr/local/CyberCP/public/snappymail.php'
            Upgrade.executioner_silent(command, 'Secure SnappyMail config')

            ###

            WriteToFile = open('/etc/fstab', 'a')
            WriteToFile.write('proc    /proc        proc        defaults,hidepid=2    0 0\n')
            WriteToFile.close()

            command = 'mount -o remount,rw,hidepid=2 /proc'
            Upgrade.executioner(command, 0)

            ###

            CentOSPath = '/etc/redhat-release'
            openEulerPath = '/etc/openEuler-release'

            if not os.path.exists(CentOSPath) or not os.path.exists(openEulerPath):
                group = 'nobody'
            else:
                group = 'nogroup'

            command = 'chown root:%s /usr/local/lsws/logs' % (group)
            Upgrade.executioner(command, 0)

            command = 'chmod 750 /usr/local/lsws/logs'
            Upgrade.executioner(command, 0)

            ## symlink protection

            writeToFile = open('/usr/lib/sysctl.d/50-default.conf', 'a')
            writeToFile.writelines('fs.protected_hardlinks = 1\n')
            writeToFile.writelines('fs.protected_symlinks = 1\n')
            writeToFile.close()

            command = 'sysctl --system'
            Upgrade.executioner(command, 0)

            command = 'chmod 700 %s' % ('/home/cyberpanel')
            Upgrade.executioner(command, 0)

            destPrivKey = "/usr/local/lscp/conf/key.pem"

            command = 'chmod 600 %s' % (destPrivKey)
            Upgrade.executioner(command, 0)

            Upgrade.stdOut("Permissions updated.")

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [fixPermissions]")

    @staticmethod
    def AutoUpgradeAcme():
        command = '/root/.acme.sh/acme.sh --upgrade --auto-upgrade'
        Upgrade.executioner(command, command, 0)
        command = '/root/.acme.sh/acme.sh --set-default-ca  --server  letsencrypt'
        Upgrade.executioner(command, command, 0)

    @staticmethod
    def check_package_availability(package_name):
        """Check if a package is available in the repositories"""
        try:
            # Try to search for the package without installing
            if os.path.exists('/etc/yum.repos.d/') or os.path.exists('/etc/dnf/dnf.conf'):
                # RHEL-based systems
                command = f"dnf search --quiet {package_name} 2>/dev/null | grep -q '^Last metadata expiration' || yum search --quiet {package_name} 2>/dev/null | head -1"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return result.returncode == 0
            else:
                # Ubuntu/Debian systems
                command = f"apt-cache search {package_name} 2>/dev/null | head -1"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return result.returncode == 0 and result.stdout.strip() != ""
        except Exception as e:
            Upgrade.stdOut(f"Error checking package availability for {package_name}: {str(e)}", 0)
            return False

    @staticmethod
    def is_almalinux9():
        """Check if running on AlmaLinux 9"""
        if os.path.exists('/etc/almalinux-release'):
            try:
                with open('/etc/almalinux-release', 'r') as f:
                    content = f.read()
                    return 'release 9' in content
            except:
                return False
        return False

    @staticmethod
    def fix_almalinux9_mariadb():
        """Fix AlmaLinux 9 MariaDB installation issues"""
        if not Upgrade.is_almalinux9():
            return
        
        Upgrade.stdOut("Applying AlmaLinux 9 MariaDB fixes...", 1)
        
        try:
            # Disable problematic MariaDB MaxScale repository
            Upgrade.stdOut("Disabling problematic MariaDB MaxScale repository...", 1)
            command = "dnf config-manager --disable mariadb-maxscale 2>/dev/null || true"
            subprocess.run(command, shell=True, capture_output=True)
            
            # Remove problematic repository files
            Upgrade.stdOut("Removing problematic repository files...", 1)
            problematic_repos = [
                '/etc/yum.repos.d/mariadb-maxscale.repo',
                '/etc/yum.repos.d/mariadb-maxscale.repo.rpmnew'
            ]
            for repo_file in problematic_repos:
                if os.path.exists(repo_file):
                    os.remove(repo_file)
                    Upgrade.stdOut(f"Removed {repo_file}", 1)
            
            # Clean DNF cache
            Upgrade.stdOut("Cleaning DNF cache...", 1)
            command = "dnf clean all"
            subprocess.run(command, shell=True, capture_output=True)
            
            # Install MariaDB from official repository
            Upgrade.stdOut("Setting up official MariaDB repository...", 1)
            command = "curl -sS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | bash -s -- --mariadb-server-version='10.11'"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                Upgrade.stdOut(f"Warning: MariaDB repo setup failed: {result.stderr}", 0)
            
            # Install MariaDB packages
            Upgrade.stdOut("Installing MariaDB packages...", 1)
            mariadb_packages = "MariaDB-server MariaDB-client MariaDB-backup MariaDB-devel"
            command = f"dnf install -y {mariadb_packages}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                Upgrade.stdOut(f"Warning: MariaDB installation issues: {result.stderr}", 0)
            
            # Start and enable MariaDB service
            Upgrade.stdOut("Starting MariaDB service...", 1)
            services = ['mariadb', 'mysql', 'mysqld']
            for service in services:
                try:
                    command = f"systemctl start {service}"
                    result = subprocess.run(command, shell=True, capture_output=True)
                    if result.returncode == 0:
                        command = f"systemctl enable {service}"
                        subprocess.run(command, shell=True, capture_output=True)
                        Upgrade.stdOut(f"MariaDB service started as {service}", 1)
                        break
                except:
                    continue
            
            Upgrade.stdOut("AlmaLinux 9 MariaDB fixes completed", 1)
            
        except Exception as e:
            Upgrade.stdOut(f"Error applying AlmaLinux 9 MariaDB fixes: {str(e)}", 0)

    @staticmethod
    def get_available_php_versions():
        """Get list of available PHP versions based on OS"""
        # Check for AlmaLinux 9+ first
        if os.path.exists('/etc/almalinux-release'):
            try:
                with open('/etc/almalinux-release', 'r') as f:
                    content = f.read()
                    if 'release 9' in content or 'release 10' in content:
                        Upgrade.stdOut("AlmaLinux 9+ detected - checking available PHP versions", 1)
                        # AlmaLinux 9+ doesn't have PHP 7.1, 7.2, 7.3
                        php_versions = ['74', '80', '81', '82', '83', '84', '85']
                    else:
                        php_versions = ['71', '72', '73', '74', '80', '81', '82', '83', '84', '85']
            except:
                php_versions = ['71', '72', '73', '74', '80', '81', '82', '83', '84', '85']
        else:
            # Check other OS versions
            os_info = Upgrade.findOperatingSytem()
            if os_info in [Ubuntu24, CENTOS8]:
                php_versions = ['74', '80', '81', '82', '83', '84', '85']
            else:
                php_versions = ['71', '72', '73', '74', '80', '81', '82', '83', '84', '85']
        
        # Check availability of each version
        available_versions = []
        for version in php_versions:
            if Upgrade.check_package_availability(f'lsphp{version}'):
                available_versions.append(version)
            else:
                Upgrade.stdOut(f"PHP {version} not available on this OS", 0)
        
        return available_versions

    @staticmethod
    def fixLiteSpeedConfig():
        """Fix LiteSpeed configuration issues by creating missing files"""
        try:
            Upgrade.stdOut("Checking and fixing LiteSpeed configuration...", 1)
            
            # Check if LiteSpeed is installed
            if not os.path.exists('/usr/local/lsws'):
                Upgrade.stdOut("LiteSpeed not found at /usr/local/lsws", 0)
                return
            
            # Create missing configuration files
            config_files = [
                "/usr/local/lsws/conf/httpd_config.xml",
                "/usr/local/lsws/conf/httpd.conf",
                "/usr/local/lsws/conf/modsec.conf"
            ]
            
            for config_file in config_files:
                if not os.path.exists(config_file):
                    Upgrade.stdOut(f"Missing LiteSpeed config: {config_file}", 0)
                    
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(config_file), exist_ok=True)
                    
                    # Create minimal config file
                    if config_file.endswith('httpd_config.xml'):
                        with open(config_file, 'w') as f:
                            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                            f.write('<httpServerConfig>\n')
                            f.write('    <!-- Minimal LiteSpeed configuration -->\n')
                            f.write('    <listener>\n')
                            f.write('        <name>Default</name>\n')
                            f.write('        <address>*:8088</address>\n')
                            f.write('    </listener>\n')
                            f.write('</httpServerConfig>\n')
                    elif config_file.endswith('httpd.conf'):
                        with open(config_file, 'w') as f:
                            f.write('# Minimal LiteSpeed HTTP configuration\n')
                            f.write('# This file will be updated by CyberPanel\n')
                    elif config_file.endswith('modsec.conf'):
                        with open(config_file, 'w') as f:
                            f.write('# ModSecurity configuration\n')
                            f.write('# This file will be updated by CyberPanel\n')
                    
                    Upgrade.stdOut(f"Created minimal config: {config_file}", 1)
                else:
                    Upgrade.stdOut(f"LiteSpeed config exists: {config_file}", 1)
                    
        except Exception as e:
            Upgrade.stdOut(f"Error fixing LiteSpeed config: {str(e)}", 0)

    @staticmethod
    def installPHP73():
        try:
            Upgrade.stdOut("Installing PHP versions based on OS compatibility...", 1)
            
            # Get available PHP versions
            available_versions = Upgrade.get_available_php_versions()
            
            if not available_versions:
                Upgrade.stdOut("No PHP versions available for installation", 0)
                return
            
            Upgrade.stdOut(f"Installing available PHP versions: {', '.join(available_versions)}", 1)
            
            for version in available_versions:
                try:
                    if version in ['71', '72', '73', '74']:
                        # PHP 7.x versions with specific extensions
                        if Upgrade.installedOutput.find(f'lsphp{version}') == -1:
                            extensions = ['json', 'xmlrpc', 'xml', 'tidy', 'soap', 'snmp', 'recode', 'pspell', 'process', 'pgsql', 'pear', 'pdo', 'opcache', 'odbc', 'mysqlnd', 'mcrypt', 'mbstring', 'ldap', 'intl', 'imap', 'gmp', 'gd', 'enchant', 'dba', 'common', 'bcmath']
                            package_list = f"lsphp{version} " + " ".join([f"lsphp{version}-{ext}" for ext in extensions])
                            command = f"yum install -y {package_list}"
                            Upgrade.executioner(command, f'Install PHP {version}', 0)
                    else:
                        # PHP 8.x versions
                        if Upgrade.installedOutput.find(f'lsphp{version}') == -1:
                            command = f"yum install lsphp{version}* -y"
            subprocess.call(command, shell=True)
                            Upgrade.stdOut(f"Installed PHP {version}", 1)
                        
                except Exception as e:
                    Upgrade.stdOut(f"Error installing PHP {version}: {str(e)}", 0)
                    continue

        except:
            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install ' \
                      'lsphp7? lsphp7?-common lsphp7?-curl lsphp7?-dev lsphp7?-imap lsphp7?-intl lsphp7?-json ' \
                      'lsphp7?-ldap lsphp7?-mysql lsphp7?-opcache lsphp7?-pspell lsphp7?-recode ' \
                      'lsphp7?-sqlite3 lsphp7?-tidy'
            Upgrade.executioner(command, 'Install PHP 73, 0')

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp80*'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp81*'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp82*'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp83*'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp84*'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp85*'
            os.system(command)

        CentOSPath = '/etc/redhat-release'
        openEulerPath = '/etc/openEuler-release'

        # if not os.path.exists(CentOSPath) or not os.path.exists(openEulerPath):
        # command = 'cp /usr/local/lsws/lsphp71/bin/php /usr/bin/'
        # Upgrade.executioner(command, 'Set default PHP 7.0, 0')

    @staticmethod
    def someDirectories():
        command = "mkdir -p /usr/local/lscpd/admin/"
        Upgrade.executioner(command, 0)

        command = "mkdir -p /usr/local/lscp/cyberpanel/logs"
        Upgrade.executioner(command, 0)

    @staticmethod
    def upgradeDovecot():
        try:
            Upgrade.stdOut("Upgrading Dovecot..")
            CentOSPath = '/etc/redhat-release'
            openEulerPath = '/etc/openEuler-release'

            dovecotConfPath = '/etc/dovecot/'
            postfixConfPath = '/etc/postfix/'

            ## Take backup of configurations

            configbackups = '/home/cyberpanel/configbackups'

            command = 'mkdir %s' % (configbackups)
            Upgrade.executioner(command, 0)

            command = 'cp -pR %s %s' % (dovecotConfPath, configbackups)
            Upgrade.executioner(command, 0)

            command = 'cp -pR %s %s' % (postfixConfPath, configbackups)
            Upgrade.executioner(command, 0)

            if Upgrade.FindOperatingSytem() == CENTOS8 or Upgrade.FindOperatingSytem() == CENTOS7 or Upgrade.FindOperatingSytem() == openEuler22 or Upgrade.FindOperatingSytem() == openEuler20:

                command = "yum makecache -y"
                Upgrade.executioner(command, 0)

                command = "yum update -y"
                Upgrade.executioner(command, 0)

                if Upgrade.FindOperatingSytem() == CENTOS8:
                    command = 'dnf remove dovecot23 dovecot23-mysql -y'
                    Upgrade.executioner(command, 0)

                    command = 'dnf install --enablerepo=gf-plus dovecot23 dovecot23-mysql -y'
                    Upgrade.executioner(command, 0)

                import django
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
                django.setup()
                from mailServer.models import EUsers

                Upgrade.stdOut("Upgrading passwords...")
                for items in EUsers.objects.all():
                    if items.password.find('CRYPT') > -1:
                        continue
                    command = 'doveadm pw -p %s' % (items.password)
                    try:
                        items.password = subprocess.check_output(shlex.split(command)).decode("utf-8").strip('\n')
                    except Exception as e:
                        Upgrade.stdOut(f"Error hashing password for {items.email}: {str(e)}")
                        continue
                    items.save()

                command = "systemctl restart dovecot"
                Upgrade.executioner(command, 0)

                ### Postfix Upgrade

                command = 'yum remove postfix -y'
                Upgrade.executioner(command, 0)

                command = 'yum clean all'
                Upgrade.executioner(command, 0)

                if Upgrade.FindOperatingSytem() == CENTOS7:
                    command = 'yum makecache fast'
                else:
                    command = 'yum makecache -y'

                Upgrade.executioner(command, 0)

                if Upgrade.FindOperatingSytem() == CENTOS7:
                    command = 'yum install --enablerepo=gf-plus -y postfix3 postfix3-ldap postfix3-mysql postfix3-pcre'
                else:
                    command = 'dnf install --enablerepo=gf-plus postfix3 postfix3-mysql -y'

                Upgrade.executioner(command, 0)

                ### Restore dovecot/postfix conf

                command = 'cp -pR %s/dovecot/ /etc/' % (configbackups)
                Upgrade.executioner(command, 0)

                command = 'cp -pR %s/postfix/ /etc/' % (configbackups)
                Upgrade.executioner(command, 0)

                ## Restored

                command = 'systemctl restart postfix'
                Upgrade.executioner(command, 0)
            elif Upgrade.FindOperatingSytem() == Ubuntu20 or Upgrade.FindOperatingSytem() == Ubuntu22 or Upgrade.FindOperatingSytem() == Ubuntu24:

                debPath = '/etc/apt/sources.list.d/dovecot.list'
                # writeToFile = open(debPath, 'w')
                # writeToFile.write('deb https://repo.dovecot.org/ce-2.3-latest/ubuntu/focal focal main\n')
                # writeToFile.close()
                #
                # command = "apt update -y"
                # Upgrade.executioner(command, command)
                #
                # command = 'dpkg --configure -a'
                # subprocess.call(command, shell=True)
                #
                # command = 'apt --fix-broken install -y'
                # subprocess.call(command, shell=True)
                #
                # command = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical apt -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade -y'
                # subprocess.call(command, shell=True)

            dovecotConf = '/etc/dovecot/dovecot.conf'

            try:
                dovecotContent = open(dovecotConf, 'r').read()
            except Exception as e:
                Upgrade.stdOut(f"Error reading dovecot config: {str(e)}")
                dovecotContent = ""

            if dovecotContent and dovecotContent.find('service stats') == -1:
                writeToFile = open(dovecotConf, 'a')

                content = """\nservice stats {
    unix_listener stats-reader {
        user = vmail
        group = vmail
        mode = 0660
    }
    unix_listener stats-writer {
        user = vmail
        group = vmail
        mode = 0660
    }
}\n"""

                writeToFile.write(content)
                writeToFile.close()

            # Fix mailbox auto-creation issue
            if dovecotContent and dovecotContent.find('lda_mailbox_autocreate') == -1:
                Upgrade.stdOut("Enabling mailbox auto-creation in dovecot...")
                
                # Add mailbox auto-creation settings to protocol lda section
                try:
                    dovecotContent = open(dovecotConf, 'r').read()
                except Exception as e:
                    Upgrade.stdOut(f"Error reading dovecot config: {str(e)}")
                    dovecotContent = ""
                
                if dovecotContent and dovecotContent.find('protocol lda') > -1:
                    # Update existing protocol lda section
                    import re
                    pattern = r'(protocol lda\s*{[^}]*)'
                    replacement = r'\1\n    lda_mailbox_autocreate = yes\n    lda_mailbox_autosubscribe = yes'
                    if isinstance(dovecotContent, str):
                        dovecotContent = re.sub(pattern, replacement, dovecotContent)
                    
                    writeToFile = open(dovecotConf, 'w')
                    writeToFile.write(dovecotContent)
                    writeToFile.close()
                else:
                    # Add new protocol lda section
                    writeToFile = open(dovecotConf, 'a')
                    content = """\nprotocol lda {
    lda_mailbox_autocreate = yes
    lda_mailbox_autosubscribe = yes
}\n"""
                    writeToFile.write(content)
                    writeToFile.close()

                command = 'systemctl restart dovecot'
                Upgrade.executioner(command, command, 0)

                command = 'rm -rf %s' % (configbackups)
                Upgrade.executioner(command, command, 0)

            Upgrade.stdOut("Dovecot upgraded.")

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [upgradeDovecot]")

    @staticmethod
    def installRestic():
        CentOSPath = '/etc/redhat-release'
        openEulerPath = '/etc/openEuler-release'

        if os.path.exists(CentOSPath) or os.path.exists(openEulerPath):
            if Upgrade.installedOutput.find('restic') == -1:
                command = 'yum install restic -y'
                Upgrade.executioner(command, 'Install Restic')
                command = 'restic self-update'
                Upgrade.executioner(command, 'Install Restic')
        else:

            if Upgrade.installedOutput.find('restic/bionic,now 0.8') == -1:
                command = 'apt-get update -y'
                Upgrade.executioner(command, 'Install Restic')

                command = 'apt-get install restic -y'
                Upgrade.executioner(command, 'Install Restic')

                command = 'restic self-update'
                Upgrade.executioner(command, 'Install Restic')

    @staticmethod
    def UpdateMaxSSLCons():
        command = "sed -i 's|<maxConnections>2000</maxConnections>|<maxConnections>10000</maxConnections>|g' /usr/local/lsws/conf/httpd_config.xml"
        Upgrade.executioner(command, 0)

        command = "sed -i 's|<maxSSLConnections>200</maxSSLConnections>|<maxSSLConnections>10000</maxSSLConnections>|g' /usr/local/lsws/conf/httpd_config.xml"
        Upgrade.executioner(command, 0)

    @staticmethod
    def installCLScripts():
        try:

            CentOSPath = '/etc/redhat-release'
            openEulerPath = '/etc/openEuler-release'

            if os.path.exists(CentOSPath) or os.path.exists(openEulerPath):
                command = 'mkdir -p /opt/cpvendor/etc/'
                Upgrade.executioner(command, 0)

                content = """[integration_scripts]

panel_info = /usr/local/CyberCP/CLScript/panel_info.py
packages = /usr/local/CyberCP/CLScript/CloudLinuxPackages.py
users = /usr/local/CyberCP/CLScript/CloudLinuxUsers.py
domains = /usr/local/CyberCP/CLScript/CloudLinuxDomains.py
resellers = /usr/local/CyberCP/CLScript/CloudLinuxResellers.py
admins = /usr/local/CyberCP/CLScript/CloudLinuxAdmins.py
db_info = /usr/local/CyberCP/CLScript/CloudLinuxDB.py

[lvemanager_config]
ui_user_info = /usr/local/CyberCP/CLScript/UserInfo.py
base_path = /usr/local/lvemanager
run_service = 1
service_port = 9000
"""

                if not os.path.exists('/opt/cpvendor/etc/integration.ini'):
                    writeToFile = open('/opt/cpvendor/etc/integration.ini', 'w')
                    writeToFile.write(content)
                    writeToFile.close()

                command = 'mkdir -p /etc/cagefs/exclude'
                Upgrade.executioner(command, command, 0)

                content = """cyberpanel
docker
ftpuser
lscpd
opendkim
pdns
vmail
"""

                writeToFile = open('/etc/cagefs/exclude/cyberpanelexclude', 'w')
                writeToFile.write(content)
                writeToFile.close()

        except:
            pass

    @staticmethod
    def runSomeImportantBash():

        # Remove invalid crons from /etc/crontab Reference: https://github.com/usmannasir/cyberpanel/issues/216
        command = """sed -i '/CyberCP/d' /etc/crontab"""
        Upgrade.executioner(command, command, 0, True)

        # Ensure log directory exists for scheduled scans
        if not os.path.exists('/usr/local/lscp/logs'):
            try:
                os.makedirs('/usr/local/lscp/logs', mode=0o755)
            except:
                pass

        if os.path.exists('/usr/local/lsws/conf/httpd.conf'):
            # Setup /usr/local/lsws/conf/httpd.conf to use new Logformat standard for better stats and accesslogs
            command = """sed -i "s|^LogFormat.*|LogFormat '%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"' combined|g" /usr/local/lsws/conf/httpd.conf"""
            Upgrade.executioner(command, command, 0, True)

        # Fix all existing vhost confs to use new Logformat standard for better stats and accesslogs
        command = """find /usr/local/lsws/conf/vhosts/ -type f -name 'vhost.conf' -exec sed -i "s/.*CustomLog.*/    LogFormat '%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"' combined\n&/g" {} \;"""
        Upgrade.executioner(command, command, 0, True)

        # Install any Cyberpanel missing crons to root crontab so its visible to users via crontab -l as root user

        # Install findBWUsage cron if missing

        CentOSPath = '/etc/redhat-release'
        openEulerPath = '/etc/openEuler-release'

        if os.path.exists(CentOSPath) or os.path.exists(openEulerPath):
            cronPath = '/var/spool/cron/root'
        else:
            cronPath = '/var/spool/cron/crontabs/root'

        if os.path.exists(cronPath):
            data = open(cronPath, 'r').read()

            if data.find('findBWUsage') == -1:
                content = """
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py >/dev/null 2>&1
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup >/dev/null 2>&1
0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup >/dev/null 2>&1
0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py >/dev/null 2>&1
0 0 * * 4 /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py >/dev/null 2>&1
7 0 * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null
*/3 * * * * if ! find /home/*/public_html/ -maxdepth 2 -type f -newer /usr/local/lsws/cgid -name '.htaccess' -exec false {} +; then /usr/local/lsws/bin/lswsctrl restart; fi
* * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py run_scheduled_scans >/usr/local/lscp/logs/scheduled_scans.log 2>&1
"""

                writeToFile = open(cronPath, 'w')
                writeToFile.write(content)
                writeToFile.close()

            if data.find('IncScheduler.py') == -1:
                content = """
0 12 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Daily
0 0 * * 0 /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Weekly
"""
                writeToFile = open(cronPath, 'a')
                writeToFile.write(content)
                writeToFile.close()

            if data.find("IncScheduler.py '30 Minutes'") == -1:
                content = """
*/30 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '30 Minutes'
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '1 Hour'
0 */6 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '6 Hours'
0 */12 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '12 Hours'
0 1 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '1 Day'
0 0 */3 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '3 Days'
0 0 * * 0 /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '1 Week'
"""
                writeToFile = open(cronPath, 'a')
                writeToFile.write(content)
                writeToFile.close()

            # Add AI Scanner scheduled scans cron job if missing
            if data.find('run_scheduled_scans') == -1:
                content = """
* * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py run_scheduled_scans >/usr/local/lscp/logs/scheduled_scans.log 2>&1
"""
                writeToFile = open(cronPath, 'a')
                writeToFile.write(content)
                writeToFile.close()


        else:
            content = """
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py >/dev/null 2>&1
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup >/dev/null 2>&1
0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup >/dev/null 2>&1
0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py >/dev/null 2>&1
0 0 * * 4 /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py >/dev/null 2>&1
7 0 * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null
0 0 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Daily
0 0 * * 0 /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Weekly
* * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py run_scheduled_scans >/usr/local/lscp/logs/scheduled_scans.log 2>&1
"""
            writeToFile = open(cronPath, 'w')
            writeToFile.write(content)
            writeToFile.close()

        ### Check and remove OLS restart if lsws ent detected

        if not os.path.exists('/usr/local/lsws/bin/openlitespeed'):

            data = open(cronPath, 'r').readlines()

            writeToFile = open(cronPath, 'w')

            for items in data:
                if items.find('-maxdepth 2 -type f -newer') > -1:
                    pass
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

        if not os.path.exists(CentOSPath) or not os.path.exists(openEulerPath):
            command = 'chmod 600 %s' % (cronPath)
            Upgrade.executioner(command, 0)

    @staticmethod
    def UpdateConfigOfCustomACL():
        sys.path.append('/usr/local/CyberCP')
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
        import django
        django.setup()
        from loginSystem.models import ACL
        for acl in ACL.objects.all():
            if acl.name == 'admin' or acl.name == 'reseller' or acl.name == 'user':
                continue
            elif acl.config == '{}':
                acl.config = '{"adminStatus":%s, "versionManagement": %s, "createNewUser": %s, "listUsers": %s, "deleteUser": %s, "resellerCenter": %s, "changeUserACL": %s, "createWebsite": %s, "modifyWebsite": %s, "suspendWebsite": %s, "deleteWebsite": %s, "createPackage": %s, "listPackages": %s, "deletePackage": %s, "modifyPackage": %s, "createDatabase": %s, "deleteDatabase": %s, "listDatabases": %s, "createNameServer": %s, "createDNSZone": %s, "deleteZone": %s, "addDeleteRecords": %s, "createEmail": %s, "listEmails": %s, "deleteEmail": %s, "emailForwarding": %s, "changeEmailPassword": %s, "dkimManager": %s, "createFTPAccount": %s, "deleteFTPAccount": %s, "listFTPAccounts": %s, "createBackup": %s, "restoreBackup": %s, "addDeleteDestinations": %s, "scheduleBackups": %s, "remoteBackups": %s, "googleDriveBackups": %s, "manageSSL": %s, "hostnameSSL": %s, "mailServerSSL": %s }' \
                             % (str(acl.adminStatus), str(acl.versionManagement), str(acl.createNewUser),
                                str(acl.listUsers), str(acl.deleteUser), str(acl.resellerCenter),
                                str(acl.changeUserACL),
                                str(acl.createWebsite), str(acl.modifyWebsite), str(acl.suspendWebsite),
                                str(acl.deleteWebsite),
                                str(acl.createPackage), str(acl.listPackages), str(acl.deletePackage),
                                str(acl.modifyPackage),
                                str(acl.createDatabase), str(acl.deleteDatabase), str(acl.listDatabases),
                                str(acl.createNameServer),
                                str(acl.createDNSZone), str(acl.deleteZone), str(acl.addDeleteRecords),
                                str(acl.createEmail),
                                str(acl.listEmails), str(acl.deleteEmail), str(acl.emailForwarding),
                                str(acl.changeEmailPassword),
                                str(acl.dkimManager), str(acl.createFTPAccount), str(acl.deleteFTPAccount),
                                str(acl.listFTPAccounts),
                                str(acl.createBackup), str(acl.restoreBackup), str(acl.addDeleteDestinations),
                                str(acl.scheduleBackups), str(acl.remoteBackups), '1',
                                str(acl.manageSSL), str(acl.hostnameSSL), str(acl.mailServerSSL))
                acl.save()

    @staticmethod
    def CreateMissingPoolsforFPM():
        ##### apache configs

        CentOSPath = '/etc/redhat-release'

        if os.path.exists(CentOSPath):

            serverRootPath = '/etc/httpd'
            configBasePath = '/etc/httpd/conf.d/'
            php54Path = '/opt/remi/php54/root/etc/php-fpm.d/'
            php55Path = '/opt/remi/php55/root/etc/php-fpm.d/'
            php56Path = '/etc/opt/remi/php56/php-fpm.d/'
            php70Path = '/etc/opt/remi/php70/php-fpm.d/'
            php71Path = '/etc/opt/remi/php71/php-fpm.d/'
            php72Path = '/etc/opt/remi/php72/php-fpm.d/'
            php73Path = '/etc/opt/remi/php73/php-fpm.d/'

            php74Path = '/etc/opt/remi/php74/php-fpm.d/'

            php80Path = '/etc/opt/remi/php80/php-fpm.d/'
            php81Path = '/etc/opt/remi/php81/php-fpm.d/'
            php82Path = '/etc/opt/remi/php82/php-fpm.d/'

            php83Path = '/etc/opt/remi/php83/php-fpm.d/'
            php84Path = '/etc/opt/remi/php84/php-fpm.d/'
            php85Path = '/etc/opt/remi/php85/php-fpm.d/'

            serviceName = 'httpd'
            sockPath = '/var/run/php-fpm/'
            runAsUser = 'apache'
        else:
            serverRootPath = '/etc/apache2'
            configBasePath = '/etc/apache2/sites-enabled/'

            php54Path = '/etc/php/5.4/fpm/pool.d/'
            php55Path = '/etc/php/5.5/fpm/pool.d/'
            php56Path = '/etc/php/5.6/fpm/pool.d/'
            php70Path = '/etc/php/7.0/fpm/pool.d/'
            php71Path = '/etc/php/7.1/fpm/pool.d/'
            php72Path = '/etc/php/7.2/fpm/pool.d/'
            php73Path = '/etc/php/7.3/fpm/pool.d/'

            php74Path = '/etc/php/7.4/fpm/pool.d/'
            php80Path = '/etc/php/8.0/fpm/pool.d/'
            php81Path = '/etc/php/8.1/fpm/pool.d/'
            php82Path = '/etc/php/8.2/fpm/pool.d/'
            php83Path = '/etc/php/8.3/fpm/pool.d/'
            php84Path = '/etc/php/8.4/fpm/pool.d/'
            php85Path = '/etc/php/8.5/fpm/pool.d/'

            serviceName = 'apache2'
            sockPath = '/var/run/php/'
            runAsUser = 'www-data'

        #####

        if not os.path.exists(serverRootPath):
            return 1

        if os.path.exists(php54Path):
            content = f"""
[php54default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php5.4-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
"""
            WriteToFile = open(f'{php54Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php55Path):
            content = f'''
[php55default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php5.5-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php55Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php56Path):
            content = f'''
[php56default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php5.6-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php56Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php70Path):
            content = f'''
[php70default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php7.0-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php70Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php71Path):
            content = f'''
[php71default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php7.1-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php71Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php72Path):
            content = f'''
[php72default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php7.2-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php72Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php73Path):
            content = f'''
[php73default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php7.3-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php73Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php74Path):
            content = f'''
[php74default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php7.4-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php74Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php80Path):
            content = f'''
[php80default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php8.0-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3

'''
            WriteToFile = open(f'{php80Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php81Path):
            content = f'''
[php81default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php8.1-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3

'''
            WriteToFile = open(f'{php81Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()
        if os.path.exists(php82Path):
            content = f'''
[php82default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php8.2-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
            
'''
            WriteToFile = open(f'{php82Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php83Path):
            content = f'''
[php83default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php8.3-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php83Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php84Path):
            content = f'''
[php84default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php8.4-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php84Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

        if os.path.exists(php85Path):
            content = f'''
[php85default]
user = {runAsUser}
group = {runAsUser}
listen ={sockPath}php8.5-fpm.sock
listen.owner = {runAsUser}
listen.group = {runAsUser}
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
'''
            WriteToFile = open(f'{php85Path}www.conf', 'w')
            WriteToFile.write(content)
            WriteToFile.close()

    @staticmethod
    def setupPHPSymlink():
        try:
            # Try to find available PHP version (prioritize modern stable versions)
            # Priority: 8.3 (recommended), 8.2, 8.4, 8.5, 8.1, 8.0, then older versions
            php_versions = ['83', '82', '84', '85', '81', '80', '74', '73', '72', '71']
            selected_php = None
            
            for version in php_versions:
                if os.path.exists(f'/usr/local/lsws/lsphp{version}/bin/php'):
                    selected_php = version
                    Upgrade.stdOut(f"Found PHP {version}, using as default", 1)
                    break
            
            if not selected_php:
                # Try to install PHP 8.3 as fallback (modern stable version)
                Upgrade.stdOut("No PHP found, installing PHP 8.3 as fallback...")
                
                # Install PHP 8.3 based on OS
                if os.path.exists(Upgrade.CentOSPath) or os.path.exists(Upgrade.openEulerPath):
                    command = 'yum install lsphp83 lsphp83-* -y'
                    Upgrade.executioner(command, 'Install PHP 8.3', 0)
                else:
                    command = 'DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp83 lsphp83-*'
                    Upgrade.executioner(command, 'Install PHP 8.3', 0)
                
                # Verify installation
                if not os.path.exists('/usr/local/lsws/lsphp83/bin/php'):
                    Upgrade.stdOut('[ERROR] Failed to install PHP 8.3')
                    return 0
                selected_php = '83'
            
            # Remove existing PHP symlink if it exists
            if os.path.exists('/usr/bin/php'):
                os.remove('/usr/bin/php')

            # Create symlink to selected PHP version
            command = f'ln -s /usr/local/lsws/lsphp{selected_php}/bin/php /usr/bin/php'
            Upgrade.executioner(command, f'Setup PHP Symlink to {selected_php}', 0)

            Upgrade.stdOut(f"PHP symlink updated to PHP {selected_php} successfully.")

        except BaseException as msg:
            Upgrade.stdOut('[ERROR] ' + str(msg) + " [setupPHPSymlink]")
            return 0

        return 1

    @staticmethod
    def upgrade(branch):

        if branch.find('SoftUpgrade') > -1:
            Upgrade.SoftUpgrade = 1
            branch = branch.split(',')[1]

        # Upgrade.stdOut("Upgrades are currently disabled")
        # return 0

        if os.path.exists(Upgrade.CentOSPath) or os.path.exists(Upgrade.openEulerPath):
            command = 'yum list installed'
            try:
                Upgrade.installedOutput = subprocess.check_output(shlex.split(command)).decode()
            except Exception as e:
                Upgrade.stdOut(f"Error getting installed packages: {str(e)}")
                Upgrade.installedOutput = ""
        else:
            command = 'apt list'
            try:
                Upgrade.installedOutput = subprocess.check_output(shlex.split(command)).decode()
            except Exception as e:
                Upgrade.stdOut(f"Error getting installed packages: {str(e)}")
                Upgrade.installedOutput = ""

        # command = 'systemctl stop cpssh'
        # Upgrade.executioner(command, 'fix csf if there', 0)

        ## Add LSPHP7.4 TO LSWS Ent configs

        if not os.path.exists('/usr/local/lsws/bin/openlitespeed'):

            if os.path.exists('httpd_config.xml'):
                os.remove('httpd_config.xml')

            command = 'wget https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/install/litespeed/httpd_config.xml'
            Upgrade.executioner(command, command, 0)
            # os.remove('/usr/local/lsws/conf/httpd_config.xml')
            # shutil.copy('httpd_config.xml', '/usr/local/lsws/conf/httpd_config.xml')

        Upgrade.updateRepoURL()

        os.chdir("/usr/local")

        if os.path.exists(Upgrade.CentOSPath) or os.path.exists(Upgrade.openEulerPath):
            command = 'yum remove yum-plugin-priorities -y'
            Upgrade.executioner(command, 'remove yum-plugin-priorities', 0)

        ## Current Version

        ### if this is a soft upgrade from front end do not stop lscpd, as lscpd is controlling the front end

        if Upgrade.SoftUpgrade == 0:
            command = "systemctl stop lscpd"
            Upgrade.executioner(command, 'stop lscpd', 0)

        Upgrade.fixSudoers()
        # Upgrade.mountTemp()

        ### fix a temp issue causing upgrade problem

        fstab = "/etc/fstab"

        if open(fstab, 'r').read().find('/usr/.tempdisk')>-1:
            command = 'umount -l /tmp'
            Upgrade.executioner(command, 'tmp adjustment', 0)

            command = 'mount -t tmpfs -o size=2G tmpfs /tmp'
            Upgrade.executioner(command, 'tmp adjustment', 0)

        Upgrade.dockerUsers()
        Upgrade.setupPHPSymlink()
        Upgrade.setupComposer()

        ##

        versionNumbring = Upgrade.downloadLink()

        if os.path.exists('/usr/local/CyberPanel.' + versionNumbring):
            os.remove('/usr/local/CyberPanel.' + versionNumbring)

        ##

        # execPath = "sudo /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/csf.py"
        # execPath = execPath + " removeCSF"
        # Upgrade.executioner(execPath, 'fix csf if there', 0)

        Upgrade.downloadAndUpgrade(versionNumbring, branch)
        versionNumbring = Upgrade.downloadLink()
        Upgrade.download_install_phpmyadmin()
        Upgrade.downoad_and_install_raindloop()

        ##

        ##

        Upgrade.mailServerMigrations()
        Upgrade.emailMarketingMigrationsa()
        Upgrade.dockerMigrations()
        Upgrade.CLMigrations()
        Upgrade.IncBackupMigrations()
        Upgrade.installRestic()

        ##

        # Upgrade.setupVirtualEnv()

        ##

        Upgrade.applyLoginSystemMigrations()

        ## Put function here to update custom ACLs

        Upgrade.UpdateConfigOfCustomACL()

        Upgrade.s3BackupMigrations()
        Upgrade.containerMigrations()
        Upgrade.manageServiceMigrations()
        Upgrade.enableServices()

        # Apply AlmaLinux 9 fixes before other installations
        Upgrade.fix_almalinux9_mariadb()

        Upgrade.installPHP73()
        Upgrade.setupCLI()
        Upgrade.someDirectories()
        Upgrade.installLSCPD(branch)
        Upgrade.FixCurrentQuoatasSystem()
        
        ## Fix Apache configuration issues after upgrade
        Upgrade.fixApacheConfiguration()
        
        # Fix LiteSpeed configuration files if missing
        Upgrade.fixLiteSpeedConfig()

        ### General migrations are not needed any more

        # Upgrade.GeneralMigrations()

        # Upgrade.p3()

        ## Also disable email service upgrade

        # if os.path.exists(postfixPath):
        #     Upgrade.upgradeDovecot()

        ## Upgrade version

        Upgrade.fixPermissions()

        ##

        ### Disable version upgrade too

        # Upgrade.upgradeVersion()

        Upgrade.UpdateMaxSSLCons()

        ## Update LSCPD PHP

        phpPath = '/usr/local/lscp/fcgi-bin/lsphp'

        try:
            os.remove(phpPath)
        except:
            pass

        # Try to find available PHP binary in order of preference (modern stable first)
        php_versions = ['83', '82', '84', '85', '81', '80', '74', '73', '72', '71']
        php_binary_found = False
        
        for version in php_versions:
            php_binary = f'/usr/local/lsws/lsphp{version}/bin/lsphp'
            if os.path.exists(php_binary):
                command = f'cp {php_binary} {phpPath}'
        Upgrade.executioner(command, 0)
                Upgrade.stdOut(f"Using PHP {version} for LSCPD", 1)
                php_binary_found = True
                break
        
        if not php_binary_found:
            Upgrade.stdOut("Warning: No PHP binary found for LSCPD", 0)
            # Try to create a symlink to any available PHP
            try:
                command = 'find /usr/local/lsws -name "lsphp" -type f 2>/dev/null | head -1'
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    php_binary = result.stdout.strip()
                    command = f'cp {php_binary} {phpPath}'
                    Upgrade.executioner(command, 0)
                    Upgrade.stdOut(f"Using found PHP binary: {php_binary}", 1)
            except:
                pass

        if Upgrade.SoftUpgrade == 0:
            try:
                command = "systemctl start lscpd"
                Upgrade.executioner(command, 'Start LSCPD', 0)
            except:
                pass
            
            # Try to start other services if they exist
            # Enhanced service startup with AlmaLinux 9 support
            services_to_start = ['fastapi_ssh_server', 'cyberpanel']
            
            # Special handling for AlmaLinux 9 MariaDB service
            if Upgrade.is_almalinux9():
                Upgrade.stdOut("AlmaLinux 9 detected - applying enhanced service management", 1)
                mariadb_services = ['mariadb', 'mysql', 'mysqld']
                for service in mariadb_services:
                    try:
                        check_command = f"systemctl list-unit-files | grep -q {service}"
                        result = subprocess.run(check_command, shell=True, capture_output=True)
                        if result.returncode == 0:
                            command = f"systemctl restart {service}"
                            Upgrade.executioner(command, f'Restart {service} for AlmaLinux 9', 0)
                            command = f"systemctl enable {service}"
                            Upgrade.executioner(command, f'Enable {service} for AlmaLinux 9', 0)
                            Upgrade.stdOut(f"MariaDB service managed as {service} on AlmaLinux 9", 1)
                            break
                    except Exception as e:
                        Upgrade.stdOut(f"Could not manage MariaDB service {service}: {str(e)}", 0)
                        continue
            
            for service in services_to_start:
                try:
                    # Check if service exists
                    check_command = f"systemctl list-unit-files | grep -q {service}"
                    result = subprocess.run(check_command, shell=True, capture_output=True)
                    if result.returncode == 0:
                        command = f"systemctl start {service}"
                        Upgrade.executioner(command, f'Start {service}', 0)
                    else:
                        Upgrade.stdOut(f"Service {service} not found, skipping", 0)
                except Exception as e:
                    Upgrade.stdOut(f"Could not start {service}: {str(e)}", 0)

        # Remove CSF if installed and restore firewalld (CSF is being discontinued on August 31, 2025)
        if os.path.exists('/etc/csf'):
            print("CSF detected - removing CSF and restoring firewalld...")
            print("Note: ConfigServer Firewall (CSF) is being discontinued on August 31, 2025")
            
            # Remove CSF and restore firewalld
            execPath = "sudo /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/csf.py"
            execPath = execPath + " removeCSF"
            Upgrade.executioner(execPath, 'Remove CSF and restore firewalld', 0)
            
            print("CSF has been removed and firewalld has been restored.")



        # Remove configservercsf directory if it exists
        if os.path.exists('/usr/local/CyberCP/configservercsf'):
            command = 'rm -rf /usr/local/CyberCP/configservercsf'
            Upgrade.executioner(command, 'Remove configservercsf directory', 1)



        command = 'systemctl stop cpssh'
        Upgrade.executioner(command, 'fix csf if there', 0)
        Upgrade.AutoUpgradeAcme()
        Upgrade.installCLScripts()
        Upgrade.runSomeImportantBash()
        Upgrade.FixRSPAMDConfig()
        Upgrade.CreateMissingPoolsforFPM()

                # ## Handle ImunifyAV and Imunify360 separately

        # Both products use the same config file, so we need to read its content to determine which product
        integrationConfig = '/etc/sysconfig/imunify360/integration.conf'

        if os.path.exists(integrationConfig):
            try:
                with open(integrationConfig, 'r') as f:
                    configContent = f.read()

                # Check which product the config file is for by looking at the ui_path
                if 'ui_path =/usr/local/CyberCP/public/imunifyav' in configContent:
                    # This is ImunifyAV configuration
                    Upgrade.stdOut("Detected ImunifyAV configuration, reconfiguring...")
                    imunifyAVPath = '/usr/local/CyberCP/public/imunifyav'

                    if os.path.exists(imunifyAVPath):
                        execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/CLManager/CageFS.py"
                        command = execPath + " --function submitinstallImunifyAV"
                        Upgrade.executioner(command, command, 1)

                        # Set permissions on ImunifyAV execute file
                        imunifyAVExecute = '/usr/local/CyberCP/public/imunifyav/bin/execute.py'
                        if os.path.exists(imunifyAVExecute):
                            command = 'chmod +x ' + imunifyAVExecute
                            Upgrade.executioner(command, command, 1)
                            Upgrade.stdOut("ImunifyAV execute permissions set")
                        else:
                            Upgrade.stdOut("ImunifyAV execute.py file not found")
                    else:
                        Upgrade.stdOut("ImunifyAV directory not found despite config file existing")

                elif 'ui_path =/usr/local/CyberCP/public/imunify' in configContent:
                    # This is Imunify360 configuration
                    Upgrade.stdOut("Detected Imunify360 configuration, checking system installation...")
                    imunify360Path = '/usr/local/CyberCP/public/imunify'

                    if os.path.exists(imunify360Path):
                        # Check if Imunify360 is actually installed on the system
                        imunify360Installed = False
                        if os.path.exists('/usr/bin/imunify360-agent') or os.path.exists('/opt/imunify360'):
                            imunify360Installed = True
                            Upgrade.stdOut("Imunify360 system installation detected")

                        if imunify360Installed:
                            Upgrade.stdOut("Imunify360 directory found and system is installed, ensuring proper integration...")
                            # Reinstall Imunify360 firewall to ensure integration
                            command = "yum reinstall imunify360-firewall-generic -y" if os.path.exists(Upgrade.CentOSPath) else "apt install --reinstall imunify360-firewall-generic -y"
                            Upgrade.executioner(command, command, 1)
                        else:
                            Upgrade.stdOut("Imunify360 directory found but system not installed - manual installation may be needed")

                        # Set permissions on Imunify360 execute file
                        imunify360Execute = '/usr/local/CyberCP/public/imunify/bin/execute.py'
                        if os.path.exists(imunify360Execute):
                            command = f'chmod +x {imunify360Execute}'
                            Upgrade.executioner(command, f'Setting execute permissions on Imunify360 file', 0)
                            Upgrade.stdOut("Imunify360 execute permissions set")
                        else:
                            Upgrade.stdOut("Imunify360 execute.py file not found")
                    else:
                        Upgrade.stdOut("Imunify360 directory not found despite config file existing")

                else:
                    Upgrade.stdOut(f"Unknown product in integration config file. Config content: {configContent[:200]}...")

            except Exception as e:
                Upgrade.stdOut(f"Error reading integration config file: {str(e)}")
        else:
            Upgrade.stdOut("No Imunify integration config file found")

    @staticmethod
    def restoreImunify360():
        """Restore and reconfigure Imunify360 after upgrade"""
        try:
            Upgrade.stdOut("=== STARTING IMUNIFY360 RESTORATION ===")
            Upgrade.stdOut("Checking for Imunify360 restoration...")

            # Check if Imunify360 directories were restored
            imunifyPath = '/usr/local/CyberCP/public/imunify'
            imunifyAVPath = '/usr/local/CyberCP/public/imunifyav'
            configPath = '/etc/sysconfig/imunify360/integration.conf'

            Upgrade.stdOut(f"Checking if Imunify360 path exists: {imunifyPath}")
            Upgrade.stdOut(f"Path exists: {os.path.exists(imunifyPath)}")

            restored = False

            # Handle main Imunify360 firewall
            if os.path.exists(imunifyPath):
                Upgrade.stdOut("Imunify360 directory found, checking if reinstallation is needed...")
                # Check if Imunify360 is actually installed on the system
                if os.path.exists('/usr/bin/imunify360-agent') or os.path.exists('/opt/imunify360'):
                    Upgrade.stdOut("Imunify360 appears to be installed on system, ensuring proper integration...")
                    # Reinstall to ensure proper integration
                    command = "yum reinstall imunify360-firewall-generic -y" if os.path.exists(Upgrade.CentOSPath) else "apt install --reinstall imunify360-firewall-generic -y"
                    if Upgrade.executioner(command, command, 1):
                        Upgrade.stdOut("Imunify360 firewall reinstalled successfully")
                        restored = True
                    else:
                        Upgrade.stdOut("Warning: Failed to reinstall Imunify360 firewall")
                else:
                    Upgrade.stdOut("Imunify360 not found on system, skipping firewall reinstallation")

            # Handle ImunifyAV
            if os.path.exists(imunifyAVPath):
                Upgrade.stdOut("ImunifyAV directory found, reconfiguring...")
                if os.path.exists(configPath):
                    execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/CLManager/CageFS.py"
                    command = execPath + " --function submitinstallImunifyAV"
                    if Upgrade.executioner(command, command, 1):
                        Upgrade.stdOut("ImunifyAV reconfigured successfully")
                        restored = True

                    # Ensure execute permissions
                    executePath = '/usr/local/CyberCP/public/imunifyav/bin/execute.py'
                    if os.path.exists(executePath):
                        command = f'chmod +x {executePath}'
                        Upgrade.executioner(command, command, 1)

            # Handle main Imunify execute permissions - comprehensive solution for missing files
            if os.path.exists(imunifyPath):
                # First, check if the bin directory and execute.py file exist
                binDir = '/usr/local/CyberCP/public/imunify/bin'
                executeFile = '/usr/local/CyberCP/public/imunify/bin/execute.py'

                if not os.path.exists(binDir):
                    Upgrade.stdOut(f"Warning: Imunify360 bin directory missing at {binDir}")
                    # Try to find if execute.py exists elsewhere
                    findCommand = f'find {imunifyPath} -name "execute.py" -type f 2>/dev/null'
                    Upgrade.stdOut(f"Searching for execute.py files with command: {findCommand}")
                    findResult = subprocess.getstatusoutput(findCommand)
                    Upgrade.stdOut(f"Find command result: exit_code={findResult[0]}, output='{findResult[1]}'")

                    if findResult[0] == 0 and findResult[1].strip():
                        Upgrade.stdOut(f"Found execute.py files: {findResult[1]}")
                        # Set permissions on all found execute.py files
                        command = f'find {imunifyPath} -name "execute.py" -type f -exec chmod +x {{}} \\; 2>/dev/null || true'
                        Upgrade.executioner(command, 'Setting execute permissions on found execute.py files', 0)
                    else:
                        Upgrade.stdOut("No execute.py files found in Imunify360 directory - installation may be incomplete")
                else:
                    # Bin directory exists, try the direct approach
                    Upgrade.stdOut(f"Bin directory exists at {binDir}, attempting to set execute permissions")
                    Upgrade.stdOut(f"Checking if execute.py exists: {executeFile}")
                    Upgrade.stdOut(f"File exists: {os.path.exists(executeFile)}")

                    # Try direct chmod command first
                    if os.path.exists(executeFile):
                        Upgrade.stdOut("File exists, trying direct chmod command")
                        command = f'chmod +x {executeFile}'
                        Upgrade.stdOut(f"Executing direct command: {command}")
                        directResult = Upgrade.executioner(command, f'Direct chmod on {executeFile}', 0)
                        Upgrade.stdOut(f"Direct command result: {directResult}")

                        if directResult:
                            Upgrade.stdOut("SUCCESS: Direct chmod worked!")
                            restored = True
                        else:
                            Upgrade.stdOut("FAILED: Direct chmod failed, trying alternative")

                            # Try the community method as fallback
                            command = f'cd {imunifyPath} && chmod +x ./bin/execute.py 2>/dev/null || true'
                            Upgrade.stdOut(f"Trying community method: {command}")
                            communityResult = Upgrade.executioner(command, 'Community method chmod', 0)
                            Upgrade.stdOut(f"Community method result: {communityResult}")

                            if communityResult:
                                Upgrade.stdOut("SUCCESS: Community method worked!")
                                restored = True
                            else:
                                Upgrade.stdOut("FAILED: Both methods failed")
                    else:
                        Upgrade.stdOut(f"ERROR: execute.py file not found at {executeFile}")

                    # Try find method as final fallback
                    Upgrade.stdOut("Trying find method as final fallback")
                    command = f'find {imunifyPath} -name "execute.py" -type f -exec chmod +x {{}} \\; 2>/dev/null || true'
                    Upgrade.stdOut(f"Find command: {command}")
                    findResult = Upgrade.executioner(command, 'Find method chmod', 0)
                    Upgrade.stdOut(f"Find result: {findResult}")

                    if findResult and not restored:
                        Upgrade.stdOut("SUCCESS: Find method worked!")
                        restored = True

                restored = True  # Mark as restored even if files are missing, to indicate we processed it

            if restored:
                Upgrade.stdOut("Imunify360 restoration completed successfully")
            else:
                Upgrade.stdOut("No Imunify360 components found to restore")

        except Exception as e:
            Upgrade.stdOut(f"Error during Imunify360 restoration: {str(e)}")

    @staticmethod
    def finalImunifyPermissions():
        """FINAL STEP: Ensure Imunify360 execute permissions are set after everything else is complete"""
        try:
            Upgrade.stdOut("=== FINAL STEP: Setting Imunify360 Execute Permissions ===")

            executeFile = '/usr/local/CyberCP/public/imunify/bin/execute.py'

            if os.path.exists(executeFile):
                Upgrade.stdOut(f"Setting execute permissions on: {executeFile}")
                # Use the simplest, most reliable command
                command = f'chmod +x {executeFile}'
                result = Upgrade.executioner(command, f'Final chmod +x on {executeFile}', 0)

                if result:
                    Upgrade.stdOut("✅ SUCCESS: Imunify360 execute permissions set successfully!")
                else:
                    Upgrade.stdOut("❌ FAILED: Could not set Imunify360 execute permissions")

                # Verify the permissions were set
                try:
                    import stat
                    file_stat = os.stat(executeFile)
                    if file_stat.st_mode & stat.S_IXUSR:
                        Upgrade.stdOut("✅ VERIFIED: Execute permission confirmed on Imunify360 file")
                    else:
                        Upgrade.stdOut("❌ VERIFICATION FAILED: Execute permission not set")
                except Exception as verify_error:
                    Upgrade.stdOut(f"⚠️  Could not verify permissions: {str(verify_error)}")
            else:
                Upgrade.stdOut(f"⚠️  Imunify360 execute file not found: {executeFile}")

            Upgrade.stdOut("=== FINAL STEP COMPLETE ===")

        except Exception as e:
            Upgrade.stdOut(f"❌ ERROR in final permission setting: {str(e)}")

        Upgrade.installDNS_CyberPanelACMEFile()

        command = 'systemctl restart fastapi_ssh_server'
        Upgrade.executioner(command, command, 0)

        Upgrade.stdOut("Upgrade Completed.")

        ### remove log file path incase its there

        if Upgrade.SoftUpgrade:
            time.sleep(30)
            if os.path.exists(Upgrade.LogPathNew):
                os.remove(Upgrade.LogPathNew)

    @staticmethod
    def fixApacheConfigurationOld():
        """OLD VERSION - DO NOT USE - Fix Apache configuration issues after upgrade"""
        try:
            # Check if Apache is installed
            if Upgrade.FindOperatingSytem() == CENTOS7 or Upgrade.FindOperatingSytem() == CENTOS8 \
                    or Upgrade.FindOperatingSytem() == openEuler20 or Upgrade.FindOperatingSytem() == openEuler22:
                apache_service = 'httpd'
                apache_config_dir = '/etc/httpd'
            else:
                apache_service = 'apache2'
                apache_config_dir = '/etc/apache2'
            
            # Check if Apache is installed
            check_apache = f'systemctl is-enabled {apache_service} 2>/dev/null'
            result = subprocess.run(check_apache, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                Upgrade.stdOut("Fixing Apache configuration...")
                
                # 1. Ensure Apache ports are correctly configured
                command = 'grep -q "Listen 8083" /usr/local/lsws/conf/httpd_config.xml || echo "Apache port configuration might need manual check"'
                Upgrade.executioner(command, 'Check Apache ports', 1)
                
                # 2. Fix proxy rewrite rules for all vhosts
                # The issue: Both rewrite rules execute, causing incorrect proxying
                # Fix: Add proper HTTPS condition for SSL proxy rule
                command = '''find /usr/local/lsws/conf/vhosts/ -name "vhost.conf" -exec sed -i '
                    /^REWRITERULE.*proxyApacheBackendSSL/i\\
RewriteCond %{HTTPS}  =on
                ' {} \;'''
                Upgrade.executioner(command, 'Fix Apache SSL proxy condition', 1)
                
                # Also ensure the proxy backends are properly configured
                command = '''grep -q "extprocessor apachebackend" /usr/local/lsws/conf/httpd_config.conf || echo "
extprocessor apachebackend {
  type                    proxy
  address                 http://127.0.0.1:8083
  maxConns                100
  initTimeout             60
  retryTimeout            30
  respBuffer              0
}

extprocessor proxyApacheBackendSSL {
  type                    proxy
  address                 https://127.0.0.1:8082
  maxConns                100
  initTimeout             60
  retryTimeout            30
  respBuffer              0
}" >> /usr/local/lsws/conf/httpd_config.conf'''
                Upgrade.executioner(command, 'Ensure Apache proxy backends exist', 1)
                
                # 3. Ensure Apache is configured to listen on correct ports
                if Upgrade.FindOperatingSytem() in [CENTOS7, CENTOS8, openEuler20, openEuler22]:
                    apache_port_conf = '/etc/httpd/conf.d/00-port.conf'
                else:
                    apache_port_conf = '/etc/apache2/ports.conf'
                
                command = f'''
                grep -q "Listen 8082" {apache_port_conf} || echo "Listen 8082" >> {apache_port_conf}
                grep -q "Listen 8083" {apache_port_conf} || echo "Listen 8083" >> {apache_port_conf}
                '''
                Upgrade.executioner(command, 'Ensure Apache listens on 8082/8083', 1)
                
                # 4. Restart Apache service
                command = f'systemctl restart {apache_service}'
                Upgrade.executioner(command, f'Restart {apache_service}', 1)
                
                # 5. Fix PHP-FPM socket permissions and restart services
                for version in ['5.4', '5.5', '5.6', '7.0', '7.1', '7.2', '7.3', '7.4', '8.0', '8.1', '8.2', '8.3']:
                    if Upgrade.FindOperatingSytem() in [CENTOS7, CENTOS8, openEuler20, openEuler22]:
                        php_service = f'php{version.replace(".", "")}-php-fpm'
                        socket_dir = '/var/run/php-fpm'
                    else:
                        php_service = f'php{version}-fpm'
                        socket_dir = '/var/run/php'
                    
                    # Ensure socket directory exists with correct permissions
                    command = f'''
                    if systemctl is-active {php_service} >/dev/null 2>&1; then
                        mkdir -p {socket_dir}
                        chmod 755 {socket_dir}
                        systemctl restart {php_service}
                    fi
                    '''
                    Upgrade.executioner(command, f'Fix and restart {php_service}', 1)
                
                # 6. Reload LiteSpeed to apply proxy changes
                command = '/usr/local/lsws/bin/lswsctrl reload'
                Upgrade.executioner(command, 'Reload LiteSpeed', 1)
                
                Upgrade.stdOut("Apache configuration fixes completed.")
            else:
                Upgrade.stdOut("Apache not detected, skipping Apache fixes.")
                
        except Exception as e:
            Upgrade.stdOut(f"Error fixing Apache configuration: {str(e)}")
            pass

    @staticmethod
    def installQuota():
        try:

            if Upgrade.FindOperatingSytem() == CENTOS7 or Upgrade.FindOperatingSytem() == CENTOS8\
                    or Upgrade.FindOperatingSytem() == openEuler20 or Upgrade.FindOperatingSytem() == openEuler22:
                command = "yum install quota -y"
                Upgrade.executioner(command, command, 0, True)

                if Upgrade.edit_fstab('/', '/') == 0:
                    print("Quotas will not be abled as we failed to modify fstab file.")
                    return 0


                command = 'mount -o remount /'
                try:
                    mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                except:
                    mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            universal_newlines=True, shell=True)

                if mResult.returncode != 0:
                    fstab_path = '/etc/fstab'
                    backup_path = fstab_path + '.bak'
                    if os.path.exists(fstab_path):
                        os.remove(fstab_path)
                    shutil.copy(backup_path, fstab_path)

                    print("Re-mount failed, restoring original FSTab and existing quota setup.")
                    return 0

            ##

            if Upgrade.FindOperatingSytem() == Ubuntu22 or Upgrade.FindOperatingSytem() == Ubuntu24 or Upgrade.FindOperatingSytem() == Ubuntu18 \
                    or Upgrade.FindOperatingSytem() == Ubuntu20:

                print("Install Quota on Ubuntu")
                command = 'apt update -y'
                Upgrade.executioner(command, command, 0, True)

                command = 'apt install quota -y'
                Upgrade.executioner(command, command, 0, True)

                command = "find /lib/modules/ -type f -name '*quota_v*.ko*'"

                try:
                    output = subprocess.check_output(command, shell=True)
                    if output and output.decode("utf-8").find("quota/") == -1:
                        command = "sudo apt install linux-image-extra-virtual -y"
                        Upgrade.executioner(command, command, 0, True)
                except Exception as e:
                    Upgrade.stdOut(f"Error checking quota modules: {str(e)}")

                if Upgrade.edit_fstab('/', '/') == 0:
                    print("Quotas will not be abled as we are are failed to modify fstab file.")
                    return 0

                command = 'mount -o remount /'
                try:
                    mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                except:
                    mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             universal_newlines=True, shell=True)
                if mResult.returncode != 0:
                    fstab_path = '/etc/fstab'
                    backup_path = fstab_path + '.bak'
                    if os.path.exists(fstab_path):
                        os.remove(fstab_path)
                    shutil.copy(backup_path, fstab_path)

                    print("Re-mount failed, restoring original FSTab and existing quota setup.")
                    return 0

                command = 'quotacheck -ugm /'
                try:
                    mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                except:
                    mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             universal_newlines=True, shell=True)
                if mResult.returncode != 0:
                    fstab_path = '/etc/fstab'
                    backup_path = fstab_path + '.bak'
                    if os.path.exists(fstab_path):
                        os.remove(fstab_path)
                    shutil.copy(backup_path, fstab_path)

                    print("Re-mount failed, restoring original FSTab and existing quota setup.")
                    return 0

                ####

                command = "find /lib/modules/ -type f -name '*quota_v*.ko*'"
                try:
                    iResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                except:
                    iResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             universal_newlines=True, shell=True)
                print(repr(iResult.stdout))

                # Only if the first command works, run the rest

                if iResult.returncode == 0:
                    command = "echo '{}' | sed -n 's|/lib/modules/\\([^/]*\\)/.*|\\1|p' | sort -u".format(iResult.stdout)
                    try:
                        result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except:
                        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                 universal_newlines=True, shell=True)
                    fResult = result.stdout.rstrip('\n')
                    print(repr(result.stdout.rstrip('\n')))

                    command  = 'uname -r'
                    try:
                        ffResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except:
                        ffResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                universal_newlines=True, shell=True)
                    ffResult = ffResult.stdout.rstrip('\n')

                    command = f"apt-get install linux-modules-extra-{ffResult}"
                    Upgrade.executioner(command, command, 0, True)

                ###

                    command = f'modprobe quota_v1 -S {ffResult}'
                    try:
                        mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except:
                        mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                  universal_newlines=True, shell=True)
                    if mResult.returncode != 0:
                        fstab_path = '/etc/fstab'
                        backup_path = fstab_path + '.bak'
                        if os.path.exists(fstab_path):
                            os.remove(fstab_path)
                        shutil.copy(backup_path, fstab_path)

                        print("Re-mount failed, restoring original FSTab and existing quota setup.")
                        return 0

                    command = f'modprobe quota_v2 -S {ffResult}'
                    try:
                        mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except:
                        mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                 universal_newlines=True, shell=True)
                    if mResult.returncode != 0:
                        fstab_path = '/etc/fstab'
                        backup_path = fstab_path + '.bak'
                        if os.path.exists(fstab_path):
                            os.remove(fstab_path)
                        shutil.copy(backup_path, fstab_path)

                        print("Re-mount failed, restoring original FSTab and existing quota setup.")
                        return 0

            command = f'quotacheck -ugm /'
            try:
                mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
            except:
                mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         universal_newlines=True, shell=True)
            if mResult.returncode != 0:
                fstab_path = '/etc/fstab'
                backup_path = fstab_path + '.bak'
                if os.path.exists(fstab_path):
                    os.remove(fstab_path)
                shutil.copy(backup_path, fstab_path)

                print("Re-mount failed, restoring original FSTab and existing quota setup.")
                return 0

            command = f'quotaon -v /'
            try:
                mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
            except:
                mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         universal_newlines=True, shell=True)
            if mResult.returncode != 0:
                fstab_path = '/etc/fstab'
                backup_path = fstab_path + '.bak'
                if os.path.exists(fstab_path):
                    os.remove(fstab_path)
                shutil.copy(backup_path, fstab_path)

                print("Re-mount failed, restoring original FSTab and existing quota setup.")
                return 0

            return 1

        except BaseException as msg:
            print("[ERROR] installQuota. " + str(msg))
            return 0

    @staticmethod
    def edit_fstab(mount_point, options_to_add):
        try:
            retValue = 1
            # Backup the original fstab file
            fstab_path = '/etc/fstab'
            backup_path = fstab_path + '.bak'

            rData = open(fstab_path, 'r').read()

            if rData.find('xfs') > -1:
                options_to_add = 'uquota'
            else:
                options_to_add = 'usrquota,grpquota'

            if not os.path.exists(backup_path):
                shutil.copy(fstab_path, backup_path)

            # Read the fstab file
            with open(fstab_path, 'r') as file:
                lines = file.readlines()

            # Modify the appropriate line
            WriteToFile = open(fstab_path, 'w')
            for i, line in enumerate(lines):

                if line.find('\t') > -1:
                    parts = line.split('\t')
                else:
                    parts = line.split(' ')

                print(parts)
                try:
                    if parts[1] == '/' and parts[3].find(options_to_add) == -1 and len(parts[3]) > 4:

                        parts[3] = f'{parts[3]},{options_to_add}'
                        tempParts = [item for item in parts if item.strip()]
                        finalString = '\t'.join(tempParts)
                        print(finalString)
                        WriteToFile.write(finalString)

                    elif parts[1] == '/':

                        for ii, p in enumerate(parts):
                            if p.find('defaults') > -1 or p.find('discard') > -1 or p.find('errors=') > -1:
                                parts[ii] = f'{parts[ii]},{options_to_add}'
                                tempParts = [item for item in parts if item.strip()]
                                finalString = '\t'.join(tempParts)
                                print(finalString)
                                WriteToFile.write(finalString)
                    else:
                        WriteToFile.write(line)
                except:
                    WriteToFile.write(line)

            WriteToFile.close()

            return retValue
        except:
            return 0


    @staticmethod
    def FixCurrentQuoatasSystem():
        fstab_path = '/etc/fstab'

        data = open(fstab_path, 'r').read()

        if data.find("usrquota,grpquota") > -1 or data.find("uquota") > -1:
            print("Quotas already enabled.")


        if Upgrade.installQuota() == 1:

            print("We will attempt to bring new Quota system to old websites.")
            from websiteFunctions.models import Websites
            for website in Websites.objects.all():

                command = 'chattr -R -i /home/%s/' % (website.domain)
                Upgrade.executioner(command, command, 0, True)

                if website.package.enforceDiskLimits:
                    spaceString = f'{website.package.diskSpace}M {website.package.diskSpace}M'
                    command = f'setquota -u {website.externalApp} {spaceString} 0 0 /'
                    Upgrade.executioner(command, command, 0, True)

        else:
            print("Quotas can not be enabled continue to use chhtr.")

    @staticmethod
    def installDNS_CyberPanelACMEFile():
        filePath = '/root/.acme.sh/dns_cyberpanel.sh'
        if os.path.exists(filePath):
            os.remove(filePath)
        shutil.copy('/usr/local/CyberCP/install/dns_cyberpanel.sh', filePath)

        command = f'chmod +x {filePath}'
        Upgrade.executioner(command, command, 0, True)

    @staticmethod
    def fixApacheConfiguration():
        """
        Fix Apache configuration issues after upgrade, particularly for 503 errors
        when Apache is used as reverse proxy to OpenLiteSpeed
        """
        try:
            print("Starting Apache configuration fix...")
            
            # Check if Apache is installed
            osType = Upgrade.FindOperatingSytem()
            if osType in [CENTOS7, CENTOS8, CloudLinux7, CloudLinux8]:
                configBasePath = '/etc/httpd/conf.d/'
                serviceName = 'httpd'
            else:
                configBasePath = '/etc/apache2/sites-enabled/'
                serviceName = 'apache2'
            
            if not os.path.exists(configBasePath):
                print("Apache not installed, skipping Apache fixes.")
                return
            
            # Import required modules
            from websiteFunctions.models import Websites
            import re
            
            # Fix 1: Update Apache proxy configurations for domains actually using Apache
            print("Fixing Apache proxy configurations...")
            fixed_count = 0
            apache_domains = []
            
            # First, identify which domains are using Apache by checking for Apache vhost configs
            for config_file in os.listdir(configBasePath):
                if config_file.endswith('.conf'):
                    # Extract domain name from config file
                    domain_name = config_file.replace('.conf', '')
                    config_path = os.path.join(configBasePath, config_file)
                    
                    try:
                        # Read the configuration to verify it's an Apache proxy setup
                        with open(config_path, 'r') as f:
                            content = f.read()
                        
                        # Check if this is actually an Apache proxy configuration
                        # Look for common Apache proxy indicators
                        is_apache_proxy = False
                        if 'ProxyPass' in content and ('127.0.0.1:8082' in content or '127.0.0.1:8083' in content):
                            is_apache_proxy = True
                        elif 'RewriteRule' in content and 'apachebackend' in content:
                            is_apache_proxy = True
                        elif '<FilesMatch' in content and 'SetHandler' in content and 'proxy:unix:' in content:
                            is_apache_proxy = True
                        
                        if is_apache_proxy:
                            apache_domains.append(domain_name)
                            modified = False
                            
                            # Fix the proxy rewrite rules - add missing HTTPS condition
                            if 'RewriteRule ^/(.*)$ http://apachebackend/$1 [P,L]' in content and 'RewriteCond %{HTTPS} off' not in content:
                                # Find the RewriteRule for HTTP proxy
                                lines = content.split('\n')
                                new_lines = []
                                i = 0
                                while i < len(lines):
                                    line = lines[i]
                                    if 'RewriteRule ^/(.*)$ http://apachebackend/$1 [P,L]' in line:
                                        # Add the missing HTTPS condition before the rule
                                        indent = len(line) - len(line.lstrip())
                                        new_lines.append(' ' * indent + 'RewriteCond %{HTTPS} off')
                                        new_lines.append(line)
                                        modified = True
                                    else:
                                        new_lines.append(line)
                                    i += 1
                                
                                if modified:
                                    content = '\n'.join(new_lines)
                            
                            # Write back if modified
                            if modified:
                                with open(config_path, 'w') as f:
                                    f.write(content)
                                fixed_count += 1
                                print(f"Fixed Apache configuration for: {config_file}")
                    
                    except Exception as e:
                        print(f"Error processing {config_file}: {str(e)}")
            
            print(f"Found {len(apache_domains)} domains using Apache")
            print(f"Fixed {fixed_count} Apache configurations.")
            
            # If no domains are using Apache, skip the rest of the fixes
            if len(apache_domains) == 0:
                print("No domains found using Apache as reverse proxy. Skipping remaining Apache fixes.")
                return
            
            # Fix 2: Ensure Apache proxy backends are configured in OLS/LSWS
            print("Checking OpenLiteSpeed proxy backend configurations...")
            lsws_config = "/usr/local/lsws/conf/httpd_config.conf"
            
            if os.path.exists(lsws_config):
                with open(lsws_config, 'r') as f:
                    lsws_content = f.read()
                
                modified = False
                
                # Check for apachebackend extprocessor
                if 'extprocessor apachebackend' not in lsws_content:
                    # Add apachebackend configuration
                    backend_config = '''
extprocessor apachebackend {
  type                    proxy
  address                 127.0.0.1:8082
  maxConns                100
  initTimeout             60
  retryTimeout            60
  respBuffer              0
}
'''
                    lsws_content += backend_config
                    modified = True
                    print("Added apachebackend extprocessor configuration")
                
                # Check for proxyApacheBackendSSL extprocessor
                if 'extprocessor proxyApacheBackendSSL' not in lsws_content:
                    # Add proxyApacheBackendSSL configuration
                    ssl_backend_config = '''
extprocessor proxyApacheBackendSSL {
  type                    proxy
  address                 https://127.0.0.1:8083
  maxConns                100
  initTimeout             60
  retryTimeout            60
  respBuffer              0
}
'''
                    lsws_content += ssl_backend_config
                    modified = True
                    print("Added proxyApacheBackendSSL extprocessor configuration")
                
                if modified:
                    with open(lsws_config, 'w') as f:
                        f.write(lsws_content)
                    print("Updated OpenLiteSpeed configuration with Apache proxy backends")
            
            # Fix 3: Create/Update .htaccess files ONLY for domains actually using Apache
            print("Creating/Updating .htaccess files for Apache domains...")
            htaccess_fixed = 0
            htaccess_created = 0
            
            # Only process domains that we confirmed are using Apache
            for domain in apache_domains:
                try:
                    htaccess_path = f'/home/{domain}/public_html/.htaccess'
                    
                    # Check if .htaccess exists
                    if os.path.exists(htaccess_path):
                        with open(htaccess_path, 'r') as f:
                            htaccess_content = f.read()
                        
                        # Check if it's an Apache proxy configuration (case insensitive)
                        if 'apachebackend' in htaccess_content.lower():
                            # Check if it has proper HTTP/HTTPS handling
                            needs_update = False
                            
                            # Check for old style single rule
                            if 'REWRITERULE ^(.*)$ HTTP://apachebackend/$1 [P]' in htaccess_content:
                                needs_update = True
                            # Check if missing HTTPS conditions
                            elif 'RewriteCond %{HTTPS} off' not in htaccess_content or 'proxyApacheBackendSSL' not in htaccess_content:
                                needs_update = True
                            
                            if needs_update:
                                # Create proper .htaccess with both HTTP and HTTPS handling
                                new_htaccess = '''RewriteEngine On

# HTTP to backend
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ http://apachebackend/$1 [P,L]

# HTTPS to SSL backend  
RewriteCond %{HTTPS} on
RewriteRule ^(.*)$ https://proxyApacheBackendSSL/$1 [P,L]
'''
                                with open(htaccess_path, 'w') as f:
                                    f.write(new_htaccess)
                                htaccess_fixed += 1
                                print(f"Fixed .htaccess for: {domain}")
                    else:
                        # .htaccess doesn't exist - this domain might be missing it!
                        # Create the proper .htaccess file
                        print(f"Creating missing .htaccess for Apache domain: {domain}")
                        
                        # Ensure public_html exists
                        public_html_path = f'/home/{domain}/public_html'
                        if os.path.exists(public_html_path):
                            new_htaccess = '''RewriteEngine On

# HTTP to backend
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ http://apachebackend/$1 [P,L]

# HTTPS to SSL backend  
RewriteCond %{HTTPS} on
RewriteRule ^(.*)$ https://proxyApacheBackendSSL/$1 [P,L]
'''
                            with open(htaccess_path, 'w') as f:
                                f.write(new_htaccess)
                            
                            # Set proper permissions
                            try:
                                website = Websites.objects.get(domain=domain)
                                command = f'chown {website.externalApp}:{website.externalApp} {htaccess_path}'
                                Upgrade.executioner(command, command, 0, True)
                            except:
                                pass
                            
                            htaccess_created += 1
                            print(f"Created .htaccess for: {domain}")
                        else:
                            print(f"Warning: public_html not found for domain: {domain}")
                            
                except Exception as e:
                    print(f"Error updating .htaccess for {domain}: {str(e)}")
            
            print(f"Fixed {htaccess_fixed} .htaccess files.")
            print(f"Created {htaccess_created} missing .htaccess files.")
            
            # Fix 3b: Also fix OpenLiteSpeed vhost configurations that might have incorrect rewrite rules
            print("Fixing OpenLiteSpeed vhost configurations for Apache domains...")
            ols_fixed = 0
            
            for domain in apache_domains:
                try:
                    ols_vhost_path = f'/usr/local/lsws/conf/vhosts/{domain}/vhost.conf'
                    
                    if os.path.exists(ols_vhost_path):
                        with open(ols_vhost_path, 'r') as f:
                            vhost_content = f.read()
                        
                        # Check if it has the incorrect rewrite rules
                        if 'RewriteCond %{HTTPS}  !=on' in vhost_content and 'HTTP://proxyApacheBackendSSL' in vhost_content:
                            # This has the buggy configuration where HTTPS rule doesn't have proper condition
                            modified = False
                            
                            # Replace the buggy rewrite section
                            buggy_pattern = r'rewrite\s*{\s*enable\s*1\s*rules\s*<<<END_rules\s*RewriteEngine On\s*RewriteCond %{HTTPS}\s*!=on\s*REWRITERULE \^\(\.\*\)\$ HTTP://apachebackend/\$1 \[P,L\]\s*REWRITERULE \^\(\.\*\)\$ HTTP://proxyApacheBackendSSL/\$1 \[P,L\]\s*END_rules\s*}'
                            
                            correct_rewrite = '''rewrite  {
  enable                  1
  rules                   <<<END_rules
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ http://apachebackend/$1 [P,L]
RewriteCond %{HTTPS} on
RewriteRule ^(.*)$ https://proxyApacheBackendSSL/$1 [P,L]
  END_rules
}'''
                            
                            # Use a simpler approach - find and replace the section
                            import re
                            if isinstance(vhost_content, str) and vhost_content:
                                new_content = re.sub(
                                    r'rewrite\s*{[^}]+}',
                                    correct_rewrite,
                                    vhost_content,
                                    count=1
                                )
                            else:
                                new_content = vhost_content
                            
                            if new_content != vhost_content:
                                with open(ols_vhost_path, 'w') as f:
                                    f.write(new_content)
                                ols_fixed += 1
                                print(f"Fixed OLS vhost configuration for: {domain}")
                        
                except Exception as e:
                    print(f"Error fixing OLS vhost for {domain}: {str(e)}")
            
            if ols_fixed > 0:
                print(f"Fixed {ols_fixed} OpenLiteSpeed vhost configurations.")
            
            # Fix 4: Ensure Apache is listening on correct ports
            if osType in [CENTOS7, CENTOS8, CloudLinux7, CloudLinux8]:
                apache_conf = '/etc/httpd/conf/httpd.conf'
            else:
                ports_conf = '/etc/apache2/ports.conf'
                apache_conf = ports_conf if os.path.exists(ports_conf) else '/etc/apache2/apache2.conf'
            
            if os.path.exists(apache_conf):
                with open(apache_conf, 'r') as f:
                    conf_content = f.read()
                
                # Check if Apache is configured to listen on 8082 and 8083
                if 'Listen 8082' not in conf_content or 'Listen 8083' not in conf_content:
                    print("Fixing Apache listen ports...")
                    
                    # For Ubuntu/Debian, update ports.conf
                    if osType not in [CENTOS7, CENTOS8, CloudLinux7, CloudLinux8]:
                        if os.path.exists('/etc/apache2/ports.conf'):
                            with open('/etc/apache2/ports.conf', 'w') as f:
                                f.write('Listen 8082\nListen 8083\n')
                    else:
                        # For CentOS, update httpd.conf
                        lines = conf_content.split('\n')
                        new_lines = []
                        listen_added = False
                        
                        for line in lines:
                            if line.strip().startswith('Listen') and '80' in line and not listen_added:
                                new_lines.append('Listen 8082')
                                new_lines.append('Listen 8083')
                                listen_added = True
                            elif 'Listen 8082' not in line and 'Listen 8083' not in line:
                                new_lines.append(line)
                        
                        with open(apache_conf, 'w') as f:
                            f.write('\n'.join(new_lines))
                    
                    print("Fixed Apache listen ports")
            
            # Fix 5: Fix PHP-FPM socket permissions
            print("Fixing PHP-FPM socket permissions...")
            if osType in [CENTOS7, CENTOS8, CloudLinux7, CloudLinux8]:
                sock_path = '/var/run/php-fpm/'
            else:
                sock_path = '/var/run/php/'
            
            if os.path.exists(sock_path):
                # Set proper permissions
                command = f'chmod 755 {sock_path}'
                Upgrade.executioner(command, command, 0, True)
                
                # Fix ownership
                command = f'chown apache:apache {sock_path}' if osType in [CENTOS7, CENTOS8, CloudLinux7, CloudLinux8] else f'chown www-data:www-data {sock_path}'
                Upgrade.executioner(command, command, 0, True)
            
            # Restart services
            print("Restarting services...")
            
            # Restart Apache
            command = f'systemctl restart {serviceName}'
            Upgrade.executioner(command, command, 0, True)
            
            # Restart OpenLiteSpeed
            command = 'systemctl restart lsws'
            Upgrade.executioner(command, command, 0, True)
            
            # Restart PHP-FPM services
            if osType in [CENTOS7, CENTOS8, CloudLinux7, CloudLinux8]:
                for version in ['54', '55', '56', '70', '71', '72', '73', '74', '80', '81', '82', '83', '84']:
                    command = f'systemctl restart php{version}-php-fpm'
                    Upgrade.executioner(command, command, 0, True)
            else:
                for version in ['5.6', '7.0', '7.1', '7.2', '7.3', '7.4', '8.0', '8.1', '8.2', '8.3']:
                    command = f'systemctl restart php{version}-fpm'
                    Upgrade.executioner(command, command, 0, True)
            
            print("Apache configuration fix completed successfully!")
            
        except Exception as e:
            print(f"Error during Apache configuration fix: {str(e)}")



def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('branch', help='Install from branch name.')

    args = parser.parse_args()

    Upgrade.upgrade(args.branch)


if __name__ == "__main__":
    main()
