import json
import os
import os.path
import sys
import argparse
import pwd
import grp
import re

sys.path.append('/usr/local/CyberCP')
_install_dir = '/usr/local/CyberCP/install'
if _install_dir not in sys.path:
    sys.path.insert(0, _install_dir)
import ols_binaries_config
import ols_version_policy
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    from plogical.errorSanitizer import ErrorSanitizer
except Exception:
    class ErrorSanitizer(object):
        @staticmethod
        def log_error_securely(exc, context=''):
            try:
                print('%s: %s' % (context, exc))
            except Exception:
                pass
try:
    from plogical.installUtilities import installUtilities
except Exception:
    installUtilities = None
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
                print("  mariadb -u root -p")
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

VERSION = '2.5.5'
BUILD = 'dev'

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
Debian11 = 10
Debian12 = 11
Debian13 = 12


class Upgrade:
    logPath = "/usr/local/lscp/logs/upgradeLog"
    cdn = 'cdn.cyberpanel.sh'
    installedOutput = ''
    CentOSPath = '/etc/redhat-release'
    UbuntuPath = '/etc/lsb-release'
    openEulerPath = '/etc/openEuler-release'
    DebianPath = '/etc/os-release'
    FromCloud = 0
    SnappyVersion = '2.38.2'
    LogPathNew = '/home/cyberpanel/upgrade_logs'
    ProgressPathNew = '/home/cyberpanel/upgrade_progress'
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
    def write_upgrade_progress(pct, monotonic=False):
        """Persist 0–100 for Version Management polling; optional monotonic increase."""
        try:
            pct = int(pct)
            pct = max(0, min(100, pct))
            parent = os.path.dirname(Upgrade.ProgressPathNew)
            if not os.path.isdir(parent):
                os.makedirs(parent, mode=0o750, exist_ok=True)
            if monotonic and os.path.isfile(Upgrade.ProgressPathNew):
                try:
                    with open(Upgrade.ProgressPathNew, 'r') as rf:
                        cur = int(json.loads(rf.read()).get('pct', 0))
                    pct = max(pct, cur)
                except (ValueError, TypeError, json.JSONDecodeError, OSError):
                    pass
            with open(Upgrade.ProgressPathNew, 'w') as wf:
                wf.write(json.dumps({'pct': pct}))
        except (OSError, TypeError, ValueError):
            pass

    @staticmethod
    def _upgrade_init_files_and_progress():
        """Create log/progress files before first stdOut so UI polling never hits cat errors."""
        try:
            parent = '/home/cyberpanel'
            if not os.path.isdir(parent):
                os.makedirs(parent, mode=0o750, exist_ok=True)
            with open(Upgrade.LogPathNew, 'a'):
                pass
            Upgrade.write_upgrade_progress(0)
        except (OSError, TypeError, ValueError):
            pass

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
    def _read_os_release_id_and_major():
        id_name = None
        major = None
        try:
            if not os.path.exists('/etc/os-release'):
                return id_name, major
            for line in open('/etc/os-release', 'r'):
                line = line.strip()
                if line.startswith('ID='):
                    id_name = line.split('=', 1)[1].strip().strip('"').lower()
                elif line.startswith('VERSION_ID='):
                    v = line.split('=', 1)[1].strip().strip('"')
                    major = int(v.split('.')[0])
        except (OSError, ValueError, TypeError):
            pass
        return id_name, major

    @staticmethod
    def _reject_el7_runtime():
        id_name, major = Upgrade._read_os_release_id_and_major()
        if major == 7 and id_name in ('centos', 'cloudlinux'):
            raise RuntimeError(
                'CentOS 7 and CloudLinux 7 are no longer supported (EOL). '
                'Migrate to AlmaLinux 8, 9, or 10.'
            )

    @staticmethod
    def decideCentosVersion():
        Upgrade._reject_el7_runtime()
        id_name, major = Upgrade._read_os_release_id_and_major()
        if major is not None and major >= 8:
            return CENTOS8
        if os.path.exists(Upgrade.CentOSPath):
            result = open(Upgrade.CentOSPath, 'r').read()
            if 'release 8' in result or 'release 9' in result or 'release 10' in result:
                return CENTOS8
        if id_name in ('almalinux', 'rocky', 'rhel', 'centos', 'cloudlinux'):
            return CENTOS8
        return CENTOS8

    @staticmethod
    def FindOperatingSytem():
        Upgrade._reject_el7_runtime()
        id_name, major = Upgrade._read_os_release_id_and_major()
        if id_name in ('almalinux', 'rocky', 'rhel', 'centos', 'cloudlinux'):
            if major is not None and major >= 8:
                return CENTOS8

        if os.path.exists(Upgrade.CentOSPath):
            result = open(Upgrade.CentOSPath, 'r').read()

            if result.find('CentOS Linux release 8') > -1 or result.find('CloudLinux release 8') > -1:
                return CENTOS8
            if 'release 9' in result or 'release 10' in result:
                return CENTOS8
            id_name, major = Upgrade._read_os_release_id_and_major()
            if major is not None and major >= 8:
                return CENTOS8
            if id_name in ('almalinux', 'rocky', 'rhel'):
                return CENTOS8
            Upgrade._reject_el7_runtime()

        elif os.path.exists(Upgrade.openEulerPath):
            result = open(Upgrade.openEulerPath, 'r').read()

            if result.find('20.03') > -1:
                return openEuler20
            elif result.find('22.03') > -1:
                return openEuler22

        elif os.path.exists(Upgrade.DebianPath):
            result = open(Upgrade.DebianPath, 'r').read()

            if result.find('Debian GNU/Linux 11') > -1:
                return Debian11
            elif result.find('Debian GNU/Linux 12') > -1:
                return Debian12
            elif result.find('Debian GNU/Linux 13') > -1:
                return Debian13
            else:
                return Debian11  # Default to Debian 11 for older versions

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

        try:
            if 'Upgrade Completed' in message:
                Upgrade.write_upgrade_progress(100)
            elif os.path.isfile(Upgrade.LogPathNew):
                sz = os.path.getsize(Upgrade.LogPathNew)
                est = min(92, 4 + int(sz / 6000))
                Upgrade.write_upgrade_progress(est, monotonic=True)
        except (OSError, TypeError, ValueError):
            pass

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
    def add_litespeed_repo():
        """Add LiteSpeed repository (repo.litespeed.sh) for openlitespeed packages."""
        return Upgrade.executioner_silent('wget -q -O - https://repo.litespeed.sh | bash', 'LiteSpeed repo', 0, shell=True)

    @staticmethod
    def get_installed_ols_version():
        """Return installed OpenLiteSpeed version as (major, minor, patch) or None."""
        try:
            for binary in ('/usr/local/lsws/bin/lshttpd', '/usr/local/lsws/bin/openlitespeed'):
                if not os.path.exists(binary):
                    continue
                result = subprocess.run(
                    [binary, '-v'],
                    capture_output=True,
                    timeout=5,
                    universal_newlines=True,
                    env=dict(os.environ, PATH=os.environ.get('PATH', '/usr/bin:/bin'))
                )
                out = (result.stdout or '') + (result.stderr or '')
                m = re.search(r'(\d+)\.(\d+)\.(\d+)', out)
                if m:
                    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return None
        except Exception:
            return None

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

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'mountTemp')
            Upgrade.stdOut("Failed to mount temporary filesystem [mountTemp]", 0)

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
    def detectArchitecture():
        """Detect system architecture - custom binaries only for x86_64"""
        try:
            import platform
            arch = platform.machine()
            return arch == "x86_64"
        except Exception as msg:
            Upgrade.stdOut(str(msg) + " [detectArchitecture]", 0)
            return False

    @staticmethod
    def detectPlatform():
        """Detect OS platform for binary selection (rhel8, rhel9, ubuntu)"""
        try:
            # Check for Ubuntu
            if os.path.exists('/etc/lsb-release'):
                with open('/etc/lsb-release', 'r') as f:
                    content = f.read()
                    if 'Ubuntu' in content or 'ubuntu' in content:
                        return 'ubuntu'

            # Check for RHEL-based distributions
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read().lower()

                    # Check for version 8.x (RHEL, AlmaLinux, Rocky, CloudLinux, CentOS 8)
                    if 'version="8.' in content or 'version_id="8.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel8'

                    # Check for version 9.x
                    if 'version="9.' in content or 'version_id="9.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel9'

                    # AlmaLinux/RHEL/Rocky 10.x (use rhel9 CyberPanel bundle until a dedicated EL10 build ships)
                    if 'version="10.' in content or 'version_id="10.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel9'

            # Default to rhel8 if can't detect (safer default - rhel9 binaries may require GLIBC 2.35)
            Upgrade.stdOut("WARNING: Could not detect platform, defaulting to rhel8", 0)
            return 'rhel8'

        except Exception as msg:
            Upgrade.stdOut(f"ERROR detecting platform: {msg}, defaulting to rhel8", 0)
            return 'rhel8'

    @staticmethod
    def getSystemGLIBCVersion():
        """Get the system's GLIBC version"""
        try:
            import subprocess
            # Try to get GLIBC version from ldd
            result = subprocess.run(['ldd', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # ldd --version output format: "ldd (GNU libc) 2.34"
                for line in result.stdout.split('\n'):
                    if 'GNU libc' in line or 'glibc' in line.lower():
                        import re
                        version_match = re.search(r'(\d+)\.(\d+)', line)
                        if version_match:
                            major = int(version_match.group(1))
                            minor = int(version_match.group(2))
                            return (major, minor)
            
            # Fallback: try to read from libc.so.6
            try:
                result = subprocess.run(['/lib64/libc.so.6'], capture_output=True, text=True, timeout=5)
                if result.returncode != 0 and 'version' in result.stderr.lower():
                    import re
                    version_match = re.search(r'(\d+)\.(\d+)', result.stderr)
                    if version_match:
                        major = int(version_match.group(1))
                        minor = int(version_match.group(2))
                        return (major, minor)
            except:
                pass
            
            # If we can't detect, assume a safe minimum
            Upgrade.stdOut("WARNING: Could not detect GLIBC version, assuming 2.34", 0)
            return (2, 34)
        except Exception as msg:
            Upgrade.stdOut(f"WARNING: Error detecting GLIBC version: {msg}, assuming 2.34", 0)
            return (2, 34)

    @staticmethod
    def checkBinaryGLIBCRequirements(binary_path):
        """Check GLIBC version requirements of a binary file"""
        try:
            import subprocess
            import re
            
            # Use objdump to check GLIBC version requirements
            # objdump -T shows dynamic symbols and their GLIBC version requirements
            result = subprocess.run(['objdump', '-T', binary_path], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                # objdump might not be available, try readelf
                result = subprocess.run(['readelf', '-d', binary_path], capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    Upgrade.stdOut("WARNING: Could not check binary GLIBC requirements (objdump/readelf not available)", 0)
                    return None
            
            # Look for GLIBC version requirements in the output
            # Format: GLIBC_2.35, GLIBC_2.34, etc.
            max_version = None
            for line in result.stdout.split('\n') + result.stderr.split('\n'):
                # Look for GLIBC version symbols
                matches = re.findall(r'GLIBC_(\d+)\.(\d+)', line)
                for match in matches:
                    major = int(match[0])
                    minor = int(match[1])
                    if max_version is None or (major, minor) > max_version:
                        max_version = (major, minor)
            
            return max_version
            
        except FileNotFoundError:
            # objdump/readelf not available
            Upgrade.stdOut("WARNING: objdump/readelf not available, skipping GLIBC check", 0)
            return None
        except Exception as msg:
            Upgrade.stdOut(f"WARNING: Error checking binary GLIBC requirements: {msg}", 0)
            return None

    @staticmethod
    def verifyBinaryCompatibility(binary_path):
        """Verify that a binary is compatible with the system's GLIBC version"""
        try:
            system_glibc = Upgrade.getSystemGLIBCVersion()
            binary_glibc = Upgrade.checkBinaryGLIBCRequirements(binary_path)
            
            if binary_glibc is None:
                # Can't check, but we can try a test run
                Upgrade.stdOut("Cannot verify GLIBC requirements, performing test run...", 0)
                return Upgrade.testBinaryExecution(binary_path)
            
            Upgrade.stdOut(f"System GLIBC: {system_glibc[0]}.{system_glibc[1]}", 0)
            Upgrade.stdOut(f"Binary requires GLIBC: {binary_glibc[0]}.{binary_glibc[1]}", 0)
            
            # Check if binary requires newer GLIBC than system has
            if binary_glibc > system_glibc:
                Upgrade.stdOut(f"ERROR: Binary requires GLIBC {binary_glibc[0]}.{binary_glibc[1]}, but system has {system_glibc[0]}.{system_glibc[1]}", 0)
                return False
            
            Upgrade.stdOut("GLIBC compatibility check passed", 0)
            return True
            
        except Exception as msg:
            Upgrade.stdOut(f"WARNING: Error verifying binary compatibility: {msg}", 0)
            # If we can't verify, try test execution
            return Upgrade.testBinaryExecution(binary_path)

    @staticmethod
    def testBinaryExecution(binary_path):
        """Test if binary can execute (checks GLIBC compatibility indirectly)"""
        try:
            import subprocess
            # Try to run the binary with --version or -v flag
            # This will fail immediately if GLIBC is incompatible
            # The error format is: "./binary: /lib64/libc.so.6: version `GLIBC_X.Y' not found"
            result = subprocess.run([binary_path, '--version'], capture_output=True, text=True, timeout=5)
            
            # Check both stdout and stderr for GLIBC errors
            output = result.stdout + result.stderr
            
            # Look for GLIBC version not found errors
            if 'GLIBC' in output and ('not found' in output or 'version' in output.lower()):
                # Extract the required GLIBC version from error message
                import re
                glibc_match = re.search(r"GLIBC_(\d+)\.(\d+)'?\s+not found", output)
                if glibc_match:
                    required_major = int(glibc_match.group(1))
                    required_minor = int(glibc_match.group(2))
                    Upgrade.stdOut(f"ERROR: Binary requires GLIBC {required_major}.{required_minor} which is not available", 0)
                else:
                    Upgrade.stdOut(f"ERROR: Binary GLIBC compatibility test failed: {output[:200]}", 0)
                return False
            
            # If binary executed (even with non-zero return code for --version), it's compatible
            if result.returncode == 0 or len(result.stdout) > 0:
                return True
            
            # If we get here, binary might not support --version, try -v
            result = subprocess.run([binary_path, '-v'], capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            
            if 'GLIBC' in output and ('not found' in output or 'version' in output.lower()):
                import re
                glibc_match = re.search(r"GLIBC_(\d+)\.(\d+)'?\s+not found", output)
                if glibc_match:
                    required_major = int(glibc_match.group(1))
                    required_minor = int(glibc_match.group(2))
                    Upgrade.stdOut(f"ERROR: Binary requires GLIBC {required_major}.{required_minor} which is not available", 0)
                else:
                    Upgrade.stdOut(f"ERROR: Binary GLIBC compatibility test failed: {output[:200]}", 0)
                return False
            
            # If no GLIBC error and we got some output, assume compatible
            if len(output) > 0:
                return True
            
            # If binary doesn't support --version/-v, try to check if it's executable
            # by checking file type
            try:
                result = subprocess.run(['file', binary_path], capture_output=True, text=True, timeout=5)
                if 'ELF' in result.stdout and 'executable' in result.stdout:
                    Upgrade.stdOut("WARNING: Cannot test binary execution, but file appears valid", 0)
                    return True
            except:
                pass
            
            # Conservative approach: if we can't verify, assume incompatible to be safe
            Upgrade.stdOut("WARNING: Could not verify binary execution, skipping installation for safety", 0)
            return False
            
        except subprocess.TimeoutExpired:
            Upgrade.stdOut("WARNING: Binary test timed out, assuming compatible", 0)
            return True
        except FileNotFoundError as e:
            # Binary file not found or command not found
            Upgrade.stdOut(f"ERROR: Binary test failed - file or command not found: {e}", 0)
            return False
        except Exception as msg:
            # Check if it's a GLIBC error in the exception itself
            error_str = str(msg)
            if 'GLIBC' in error_str and 'not found' in error_str:
                Upgrade.stdOut(f"ERROR: Binary GLIBC compatibility test failed: {error_str}", 0)
                return False
            
            Upgrade.stdOut(f"WARNING: Could not test binary execution: {msg}", 0)
            # Conservative approach: if we can't test, assume incompatible to be safe
            return False

    @staticmethod
    def downloadCustomBinary(url, destination, expected_sha256=None):
        """Download custom binary file with optional checksum verification"""
        try:
            Upgrade.stdOut(f"Downloading {os.path.basename(destination)}...", 0)

            # Use wget for better progress display
            command = f'wget -q --show-progress {url} -O {destination}'
            res = subprocess.call(shlex.split(command))

            # Check if file was downloaded successfully by verifying it exists and has reasonable size
            if os.path.exists(destination):
                file_size = os.path.getsize(destination)
                # Verify file size is reasonable (at least 10KB to avoid error pages/empty files)
                if file_size > 10240:  # 10KB
                    if file_size > 1048576:  # 1MB
                        Upgrade.stdOut(f"Downloaded successfully ({file_size / (1024*1024):.2f} MB)", 0)
                    else:
                        Upgrade.stdOut(f"Downloaded successfully ({file_size / 1024:.2f} KB)", 0)

                    # Verify checksum if provided (skip when empty — e.g. cyberpanel_ols 2.7.x module without published hash)
                    if expected_sha256:
                        Upgrade.stdOut("Verifying checksum...", 0)
                        import hashlib
                        sha256_hash = hashlib.sha256()
                        with open(destination, "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                        actual_sha256 = sha256_hash.hexdigest()

                        if actual_sha256 == expected_sha256:
                            Upgrade.stdOut("Checksum verified successfully", 0)
                            return True
                        else:
                            Upgrade.stdOut(f"ERROR: Checksum mismatch!", 0)
                            Upgrade.stdOut(f"Expected: {expected_sha256}", 0)
                            Upgrade.stdOut(f"Got:      {actual_sha256}", 0)
                            return False
                    else:
                        return True
                else:
                    Upgrade.stdOut(f"ERROR: Downloaded file too small ({file_size} bytes)", 0)
                    return False
            else:
                Upgrade.stdOut("ERROR: Download failed - file not found", 0)
                return False

        except Exception as msg:
            Upgrade.stdOut(f"ERROR: {msg} [downloadCustomBinary]", 0)
            return False

    @staticmethod
    def installCustomOLSBinaries():
        """Install custom OpenLiteSpeed binaries with PHP config support"""
        try:
            Upgrade.stdOut("Installing Custom OpenLiteSpeed Binaries", 0)
            Upgrade.stdOut("=" * 50, 0)

            # Check architecture
            if not Upgrade.detectArchitecture():
                Upgrade.stdOut("WARNING: Custom binaries only available for x86_64", 0)
                Upgrade.stdOut("Skipping custom binary installation", 0)
                Upgrade.stdOut("Standard OLS will be used", 0)
                return True  # Not a failure, just skip

            # Detect platform
            platform = Upgrade.detectPlatform()
            Upgrade.stdOut(f"Detected platform: {platform}", 0)

            config = ols_binaries_config.BINARY_CONFIGS.get(platform)
            if not config:
                Upgrade.stdOut(f"ERROR: No binaries available for platform {platform}", 0)
                Upgrade.stdOut("Skipping custom binary installation", 0)
                return True  # Not fatal

            OLS_BINARY_URL = config['url']
            OLS_BINARY_SHA256 = config['sha256']
            MODULE_URL = config['module_url']
            MODULE_SHA256 = (config.get('module_sha256') or '').strip() or None
            MODSEC_URL = config.get('modsec_url')
            MODSEC_SHA256 = (config.get('modsec_sha256') or '').strip() or None
            OLS_BINARY_PATH = "/usr/local/lsws/bin/openlitespeed"
            MODULE_PATH = "/usr/local/lsws/modules/cyberpanel_ols.so"
            MODSEC_PATH = "/usr/local/lsws/modules/mod_security.so"

            # Create backup
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_dir = f"/usr/local/lsws/backup-{timestamp}"

            try:
                os.makedirs(backup_dir, exist_ok=True)
                if os.path.exists(OLS_BINARY_PATH):
                    shutil.copy2(OLS_BINARY_PATH, f"{backup_dir}/openlitespeed.backup")
                    Upgrade.stdOut(f"Backup created at: {backup_dir}", 0)
                # Also backup existing ModSecurity if it exists
                if os.path.exists(MODSEC_PATH):
                    shutil.copy2(MODSEC_PATH, f"{backup_dir}/mod_security.so.backup")
            except Exception as e:
                Upgrade.stdOut(f"WARNING: Could not create backup: {e}", 0)

            # Download binaries to temp location
            tmp_binary = "/tmp/openlitespeed-custom"
            tmp_module = "/tmp/cyberpanel_ols.so"
            tmp_modsec = "/tmp/mod_security.so"

            Upgrade.stdOut("Downloading custom binaries...", 0)

            # Download OpenLiteSpeed binary with checksum verification
            if not Upgrade.downloadCustomBinary(OLS_BINARY_URL, tmp_binary, OLS_BINARY_SHA256):
                Upgrade.stdOut("ERROR: Failed to download or verify OLS binary", 0)
                Upgrade.stdOut("Continuing with standard OLS", 0)
                return True  # Not fatal, continue with standard OLS

            # CRITICAL: Verify GLIBC compatibility before installation.
            # rhel9 OLS 2.5.1 needs GLIBC 2.35 (Alma/RHEL 10); AlmaLinux 9 is 2.34.
            # Fall back to the rhel8 core artifact (same feature set, older GLIBC) so
            # EL9 still gets core 2.5.1 + module 2.7.5 instead of skipping the whole overlay.
            Upgrade.stdOut("Verifying GLIBC compatibility...", 0)
            skip_core_binary = False
            if not Upgrade.verifyBinaryCompatibility(tmp_binary):
                Upgrade.stdOut("=" * 50, 0)
                Upgrade.stdOut("WARNING: Primary OLS binary GLIBC incompatible with this system", 0)
                fallback_ok = False
                if platform == 'rhel9':
                    fb = ols_binaries_config.BINARY_CONFIGS.get('rhel8')
                    if fb:
                        Upgrade.stdOut("Trying rhel8 OpenLiteSpeed 2.5.1 artifact as EL9-compatible fallback...", 0)
                        try:
                            if os.path.exists(tmp_binary):
                                os.remove(tmp_binary)
                        except Exception:
                            pass
                        if Upgrade.downloadCustomBinary(fb['url'], tmp_binary, fb['sha256'])                                 and Upgrade.verifyBinaryCompatibility(tmp_binary):
                            OLS_BINARY_URL = fb['url']
                            OLS_BINARY_SHA256 = fb['sha256']
                            # Keep rhel9 module/modsec URLs (module only needs GLIBC <= 2.33).
                            fallback_ok = True
                            Upgrade.stdOut("rhel8 OLS core is GLIBC-compatible; continuing with rhel9 module", 0)
                if not fallback_ok:
                    Upgrade.stdOut("Skipping custom OLS *core* binary; will still try to install cyberpanel_ols module", 0)
                    Upgrade.stdOut("=" * 50, 0)
                    try:
                        if os.path.exists(tmp_binary):
                            os.remove(tmp_binary)
                    except Exception:
                        pass
                    skip_core_binary = True
                else:
                    Upgrade.stdOut("=" * 50, 0)

            # Download cyberpanel_ols module (checksum optional - v2.7.x may ship without published hash)
            module_downloaded = False
            if MODULE_URL:
                if not Upgrade.downloadCustomBinary(MODULE_URL, tmp_module, MODULE_SHA256):
                    Upgrade.stdOut("ERROR: Failed to download or verify module", 0)
                    Upgrade.stdOut("Continuing with standard OLS", 0)
                    return True  # Not fatal, continue with standard OLS
                module_downloaded = True
            else:
                Upgrade.stdOut("Note: No CyberPanel module for this platform", 0)

            # Download compatible ModSecurity if existing ModSecurity is installed
            # This prevents ABI incompatibility crashes (Signal 11/SIGSEGV)
            modsec_downloaded = False
            if os.path.exists(MODSEC_PATH) and MODSEC_URL:
                Upgrade.stdOut("Existing ModSecurity detected - downloading compatible version...", 0)
                if Upgrade.downloadCustomBinary(MODSEC_URL, tmp_modsec, MODSEC_SHA256):
                    modsec_downloaded = True
                else:
                    Upgrade.stdOut("WARNING: Failed to download compatible ModSecurity", 0)
                    Upgrade.stdOut("ModSecurity may crash due to ABI incompatibility", 0)
                    Upgrade.stdOut("Consider manually updating ModSecurity after upgrade", 0)

            # Install OpenLiteSpeed binary (unless GLIBC forced a core skip)
            Upgrade.stdOut("Installing custom binaries...", 0)

            if not skip_core_binary:
                try:
                    # Make binary executable before moving
                    os.chmod(tmp_binary, 0o755)

                    # Final compatibility test before installation
                    if not Upgrade.testBinaryExecution(tmp_binary):
                        Upgrade.stdOut("ERROR: Final binary compatibility test failed", 0)
                        Upgrade.stdOut("Skipping installation to prevent OpenLiteSpeed failure", 0)
                        try:
                            if os.path.exists(tmp_binary):
                                os.remove(tmp_binary)
                        except Exception:
                            pass
                        # Still allow module install below
                        skip_core_binary = True
                    else:
                        shutil.move(tmp_binary, OLS_BINARY_PATH)
                        os.chmod(OLS_BINARY_PATH, 0o755)
                        Upgrade.stdOut("Installed OpenLiteSpeed binary", 0)
                except Exception as e:
                    if not skip_core_binary:
                        Upgrade.stdOut(f"ERROR: Failed to install binary: {e}", 0)
                        try:
                            if os.path.exists(f"{backup_dir}/openlitespeed.backup"):
                                shutil.copy2(f"{backup_dir}/openlitespeed.backup", OLS_BINARY_PATH)
                                Upgrade.stdOut("Restored original binary from backup", 0)
                        except Exception:
                            pass
                        return False
            else:
                Upgrade.stdOut("Skipping OLS core binary install (GLIBC); installing module only if available", 0)

            # Install module (if downloaded)
            if module_downloaded:
                try:
                    os.makedirs(os.path.dirname(MODULE_PATH), exist_ok=True)
                    shutil.move(tmp_module, MODULE_PATH)
                    os.chmod(MODULE_PATH, 0o644)
                    Upgrade.stdOut("Installed CyberPanel module", 0)
                except Exception as e:
                    Upgrade.stdOut(f"ERROR: Failed to install module: {e}", 0)
                    return False

            # Install compatible ModSecurity (if downloaded)
            if modsec_downloaded:
                try:
                    shutil.move(tmp_modsec, MODSEC_PATH)
                    os.chmod(MODSEC_PATH, 0o644)
                    Upgrade.stdOut("Installed compatible ModSecurity module", 0)
                except Exception as e:
                    Upgrade.stdOut(f"WARNING: Failed to install ModSecurity: {e}", 0)
                    # Non-fatal, continue

            # Verify installation - test binary before restart
            if os.path.exists(OLS_BINARY_PATH):
                if not module_downloaded or os.path.exists(MODULE_PATH):
                    Upgrade.stdOut("Verifying new binary...", 0)
                    try:
                        result = subprocess.run(
                            [OLS_BINARY_PATH, '-v'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode != 0:
                            raise Exception(f"Binary test failed with exit code {result.returncode}")

                        version_output = result.stdout if result.stdout else result.stderr
                        if 'LiteSpeed' in version_output or 'OpenLiteSpeed' in version_output:
                            Upgrade.stdOut("Binary version check passed", 0)
                        else:
                            Upgrade.stdOut("WARNING: Could not verify binary version", 0)
                    except subprocess.TimeoutExpired:
                        Upgrade.stdOut("WARNING: Binary version check timed out", 0)
                    except Exception as e:
                        Upgrade.stdOut(f"ERROR: Binary verification failed: {e}", 0)
                        Upgrade.stdOut("Initiating auto-rollback...", 0)
                        if Upgrade.rollbackOLSBinary(backup_dir, OLS_BINARY_PATH, MODULE_PATH if module_downloaded else None):
                            Upgrade.stdOut("Rollback completed successfully", 0)
                        else:
                            Upgrade.stdOut("WARNING: Rollback may have failed", 0)
                        return False

                    Upgrade.stdOut("=" * 50, 0)
                    Upgrade.stdOut("Custom Binaries Installed Successfully", 0)
                    Upgrade.stdOut("Features enabled:", 0)
                    Upgrade.stdOut("  - Static-linked cross-platform binary", 0)
                    if module_downloaded:
                        Upgrade.stdOut("  - Apache-style .htaccess support", 0)
                        Upgrade.stdOut("  - php_value/php_flag directives", 0)
                        Upgrade.stdOut("  - Enhanced header control", 0)
                    Upgrade.stdOut(f"Backup: {backup_dir}", 0)
                    Upgrade.stdOut("=" * 50, 0)
                    # Configure module after installation
                    Upgrade.configureCustomModule()
                    conf_path = '/usr/local/lsws/conf/httpd_config.conf'
                    try:
                        with open(conf_path, 'r') as f:
                            content = f.read()
                        if 'autoSSL' not in content:
                            content = re.sub(
                                r'(adminEmails\s+\S+)',
                                r'\1\nautoSSL                   1\nacmeEmail                 admin@cyberpanel.net',
                                content,
                                count=1
                            )
                            with open(conf_path, 'w') as f:
                                f.write(content)
                            Upgrade.stdOut("Auto-SSL enabled in httpd_config.conf", 0)
                    except Exception as e:
                        Upgrade.stdOut(f"WARNING: Could not enable Auto-SSL: {e}", 0)
                    return True

            Upgrade.stdOut("ERROR: Installation verification failed", 0)
            if Upgrade.rollbackOLSBinary(backup_dir, OLS_BINARY_PATH, MODULE_PATH if module_downloaded else None):
                Upgrade.stdOut("Rollback completed successfully", 0)
            return False

        except Exception as msg:
            Upgrade.stdOut(f"ERROR: {msg} [installCustomOLSBinaries]", 0)
            Upgrade.stdOut("Continuing with standard OLS", 0)
            return True  # Non-fatal error, continue

    @staticmethod
    def rollbackOLSBinary(backup_dir, binary_path, module_path=None):
        """Rollback OpenLiteSpeed binary to previous version from backup"""
        try:
            Upgrade.stdOut("Rolling back to previous binary...", 0)

            backup_binary = os.path.join(backup_dir, "openlitespeed.backup")

            if os.path.exists(backup_binary):
                Upgrade.stdOut("Stopping OpenLiteSpeed for rollback...", 0)
                subprocess.run(['/usr/local/lsws/bin/lswsctrl', 'stop'],
                               capture_output=True, timeout=30)

                shutil.copy2(backup_binary, binary_path)
                os.chmod(binary_path, 0o755)
                Upgrade.stdOut(f"Restored binary from {backup_binary}", 0)

                Upgrade.stdOut("Starting OpenLiteSpeed after rollback...", 0)
                subprocess.run(['/usr/local/lsws/bin/lswsctrl', 'start'],
                               capture_output=True, timeout=30)

                import time
                time.sleep(3)

                result = subprocess.run(['pgrep', '-f', 'openlitespeed'],
                                        capture_output=True)
                if result.returncode == 0:
                    Upgrade.stdOut("OpenLiteSpeed started successfully after rollback", 0)
                    return True
                Upgrade.stdOut("WARNING: OpenLiteSpeed may not have started after rollback", 0)
                return True
            Upgrade.stdOut(f"ERROR: Backup not found at {backup_binary}", 0)
            return False

        except Exception as e:
            Upgrade.stdOut(f"ERROR during rollback: {e}", 0)
            return False

    @staticmethod
    def configureCustomModule():
        """Configure CyberPanel module in OpenLiteSpeed config"""
        try:
            Upgrade.stdOut("Configuring CyberPanel module...", 0)

            CONFIG_FILE = "/usr/local/lsws/conf/httpd_config.conf"

            if not os.path.exists(CONFIG_FILE):
                Upgrade.stdOut("WARNING: Config file not found", 0)
                Upgrade.stdOut("Module will be auto-loaded", 0)
                return True

            # Check if module is already configured
            with open(CONFIG_FILE, 'r') as f:
                content = f.read()
            if 'cyberpanel_ols' in content:
                # Re-enable if ls_enabled 0 (upstream #1801 / 6b4059f8).
                import re
                new_content = re.sub(
                    r'(module\s+cyberpanel_ols\s*\{.*?\})',
                    lambda m: re.sub(r'ls_enabled\s+0', 'ls_enabled          1', m.group(0)),
                    content,
                    flags=re.DOTALL,
                )
                if new_content != content:
                    shutil.copy2(CONFIG_FILE, f"{CONFIG_FILE}.backup")
                    with open(CONFIG_FILE, 'w') as f:
                        f.write(new_content)
                    Upgrade.stdOut("Module was disabled (ls_enabled 0); re-enabled LSCache module", 0)
                else:
                    Upgrade.stdOut("Module already configured", 0)
                return True

            # Add module configuration
            module_config = """
module cyberpanel_ols {
  ls_enabled          1
}
"""
            # Backup config
            shutil.copy2(CONFIG_FILE, f"{CONFIG_FILE}.backup")

            # Append module config
            with open(CONFIG_FILE, 'a') as f:
                f.write(module_config)

            Upgrade.stdOut("Module configured successfully", 0)
            return True

        except Exception as msg:
            Upgrade.stdOut(f"WARNING: Module configuration failed: {msg}", 0)
            Upgrade.stdOut("Module may still work via auto-load", 0)
            return True  # Non-fatal


    @staticmethod
    def ensureCyberPanelPhpmyadminOls():
        try:
            from plogical.cyberpanelOlsPhpmyadmin import ensure_cyberpanel_phpmyadmin_ols
            Upgrade.stdOut("Configuring OpenLiteSpeed phpMyAdmin PHP contexts...", 1)
            ensure_cyberpanel_phpmyadmin_ols(restart=True, verify=True)
            Upgrade.stdOut("phpMyAdmin OLS configuration applied", 1)
            return True
        except Exception as e:
            Upgrade.stdOut("WARNING: phpMyAdmin OLS setup failed: %s" % str(e), 0)
            return False

    @staticmethod
    def enable_autossl_httpd_defaults():
        """Ensure autoSSL/acmeEmail appear once in httpd_config.conf (same logic as custom OLS path)."""
        conf_path = '/usr/local/lsws/conf/httpd_config.conf'
        try:
            import re
            with open(conf_path, 'r') as f:
                content = f.read()
            if 'autoSSL' not in content:
                content = re.sub(
                    r'(adminEmails\s+\S+)',
                    r'\1\nautoSSL                   1\nacmeEmail                 admin@cyberpanel.net',
                    content,
                    count=1
                )
                with open(conf_path, 'w') as f:
                    f.write(content)
                Upgrade.stdOut("Auto-SSL enabled in httpd_config.conf", 0)
        except Exception as e:
            Upgrade.stdOut(f"WARNING: Could not enable Auto-SSL: {e}", 0)

    @staticmethod
    def restart_openlitespeed_verify_optional_rollback():
        """Restart OLS after binary/module changes; rollback custom binary if worker missing."""
        Upgrade.stdOut("Restarting OpenLiteSpeed...", 0)
        Upgrade.executioner('/usr/local/lsws/bin/lswsctrl restart', 'Restart OpenLiteSpeed', 0)
        import time
        time.sleep(5)
        result = subprocess.run(['pgrep', '-f', 'openlitespeed'],
                                capture_output=True)
        if result.returncode != 0:
            Upgrade.stdOut("WARNING: OpenLiteSpeed may not have started after upgrade!", 0)
            Upgrade.stdOut("Attempting auto-rollback...", 0)
            backup_base = '/usr/local/lsws'
            try:
                backups = [d for d in os.listdir(backup_base) if d.startswith('backup-')]
                if backups:
                    backups.sort(reverse=True)
                    latest_backup = os.path.join(backup_base, backups[0])
                    if Upgrade.rollbackOLSBinary(latest_backup, '/usr/local/lsws/bin/openlitespeed'):
                        Upgrade.stdOut("Auto-rollback completed successfully", 0)
                    else:
                        Upgrade.stdOut("ERROR: Auto-rollback failed! Manual intervention may be required.", 0)
                else:
                    Upgrade.stdOut("ERROR: No backup found for rollback!", 0)
            except Exception as e:
                Upgrade.stdOut(f"ERROR during rollback probe: {e}", 0)
        else:
            Upgrade.stdOut("OpenLiteSpeed restarted successfully", 0)

    @staticmethod
    def upgrade_openlitespeed_repo_first_then_optional_overlay():
        """
        Match install.py: add LiteSpeed repo, upgrade openlitespeed package, then overlay
        CyberPanel binaries only if upstream version is below MIN_OFFICIAL_OLS.
        """
        if not os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            return
        min_t = ols_version_policy.MIN_OFFICIAL_OLS
        min_label = '%d.%d.%d' % (min_t[0], min_t[1], min_t[2])
        Upgrade.add_litespeed_repo()
        if os.path.exists(Upgrade.CentOSPath) or os.path.exists(Upgrade.openEulerPath):
            Upgrade.executioner('dnf -y upgrade openlitespeed || true', 'dnf upgrade openlitespeed (non-fatal)', 0)
            Upgrade.executioner('yum -y upgrade openlitespeed || true', 'yum upgrade openlitespeed (non-fatal)', 0)
            Upgrade.executioner('dnf install -y openlitespeed || yum install -y openlitespeed', 'Upgrade OpenLiteSpeed package', 0)
        else:
            Upgrade.executioner(
                'apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install --only-upgrade openlitespeed 2>/dev/null || DEBIAN_FRONTEND=noninteractive apt-get -y install openlitespeed',
                'Upgrade OpenLiteSpeed package',
                0,
                shell=True
            )
        ols_ver = Upgrade.get_installed_ols_version()
        if ols_ver and ols_ver >= min_t:
            Upgrade.stdOut(
                "OpenLiteSpeed %s meets minimum official version %s; keeping official binary (no CyberPanel overlay)."
                % ('%d.%d.%d' % ols_ver, min_label),
                0
            )
            return
        Upgrade.stdOut(
            "OpenLiteSpeed below official minimum %s or version unknown; attempting CyberPanel binary overlay..."
            % min_label,
            0
        )
        if not Upgrade.installCustomOLSBinaries():
            Upgrade.stdOut("CyberPanel OpenLiteSpeed overlay skipped or failed; continuing upgrade.", 0)
            return
        Upgrade.configureCustomModule()
        Upgrade.enable_autossl_httpd_defaults()
        Upgrade.restart_openlitespeed_verify_optional_rollback()

    @staticmethod
    def download_install_phpmyadmin():
        try:
            cwd = os.getcwd()
            pma_dir = '/usr/local/CyberCP/public/phpmyadmin'
            tmp_config = '/tmp/cyberpanel_pma_config.inc.php'
            tmp_signon = '/tmp/cyberpanel_pma_phpmyadminsignin.php'

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            # Preserve existing config and signon before removing phpmyadmin (for up/downgrade)
            saved_config = False
            saved_signon = False
            if os.path.isdir(pma_dir):
                if os.path.isfile(os.path.join(pma_dir, 'config.inc.php')):
                    try:
                        shutil.copy2(os.path.join(pma_dir, 'config.inc.php'), tmp_config)
                        saved_config = True
                    except Exception:
                        pass
                if os.path.isfile(os.path.join(pma_dir, 'phpmyadminsignin.php')):
                    try:
                        shutil.copy2(os.path.join(pma_dir, 'phpmyadminsignin.php'), tmp_signon)
                        saved_signon = True
                    except Exception:
                        pass

            try:
                shutil.rmtree(pma_dir)
            except Exception:
                pass

            # Version: /etc/cyberpanel/phpmyadmin_version, then latest from API, then fallback
            phpmyadmin_version = '5.2.3'
            version_file = '/etc/cyberpanel/phpmyadmin_version'
            if os.path.isfile(version_file):
                try:
                    with open(version_file, 'r') as f:
                        raw = (f.read() or '').strip()
                    if raw and len(raw) < 20 and all(c.isdigit() or c == '.' for c in raw):
                        phpmyadmin_version = raw
                        Upgrade.stdOut(f"Using phpMyAdmin version from {version_file}: {phpmyadmin_version}", 0)
                except Exception:
                    pass
            if phpmyadmin_version == '5.2.3':
                try:
                    from plogical.versionFetcher import get_latest_phpmyadmin_version
                    latest_version = get_latest_phpmyadmin_version()
                    if latest_version and latest_version != phpmyadmin_version:
                        Upgrade.stdOut(f"Using latest phpMyAdmin version: {latest_version}", 0)
                        phpmyadmin_version = latest_version
                    else:
                        Upgrade.stdOut(f"Using fallback phpMyAdmin version: {phpmyadmin_version}", 0)
                except Exception as e:
                    Upgrade.stdOut(f"Failed to fetch latest phpMyAdmin version, using fallback: {e}", 0)

            Upgrade.stdOut("Installing phpMyAdmin...", 0)

            tarball = '/usr/local/CyberCP/public/phpmyadmin.tar.gz'
            command = f'wget -q -O {tarball} https://files.phpmyadmin.net/phpMyAdmin/{phpmyadmin_version}/phpMyAdmin-{phpmyadmin_version}-all-languages.tar.gz'
            Upgrade.executioner_silent(command, f'Download phpMyAdmin {phpmyadmin_version}')
            if not os.path.isfile(tarball) or os.path.getsize(tarball) < 1000000:
                raise RuntimeError('phpMyAdmin download failed or file too small (check files.phpmyadmin.net)')

            command = 'tar -xzf /usr/local/CyberCP/public/phpmyadmin.tar.gz -C /usr/local/CyberCP/public/'
            Upgrade.executioner_silent(command, 'Extract phpMyAdmin')

            import glob
            extracted = glob.glob('/usr/local/CyberCP/public/phpMyAdmin-*-all-languages')
            if not extracted:
                extracted = glob.glob('/usr/local/CyberCP/public/phpMyAdmin-*')
            if extracted:
                if os.path.exists(pma_dir):
                    shutil.rmtree(pma_dir)
                os.rename(extracted[0], pma_dir)
            else:
                Upgrade.executioner('mv /usr/local/CyberCP/public/phpMyAdmin-*-all-languages /usr/local/CyberCP/public/phpmyadmin', 0)

            command = 'rm -f /usr/local/CyberCP/public/phpmyadmin.tar.gz'
            Upgrade.executioner_silent(command, 'Cleanup phpMyAdmin tar.gz')

            if not os.path.isdir(pma_dir):
                raise RuntimeError('phpMyAdmin directory was not created after extract/mv')
            Upgrade.stdOut("phpMyAdmin installation completed.", 0)

            # Restore preserved config/signon and apply minimal overrides, or create new config
            if saved_config and os.path.isfile(tmp_config):
                shutil.copy2(tmp_config, os.path.join(pma_dir, 'config.inc.php'))
                try:
                    os.remove(tmp_config)
                except Exception:
                    pass
                # Ensure TempDir and host/port present (append if missing)
                with open(os.path.join(pma_dir, 'config.inc.php'), 'r') as f:
                    cfg_content = f.read()
                if "TempDir" not in cfg_content:
                    with open(os.path.join(pma_dir, 'config.inc.php'), 'a') as f:
                        f.write("\n$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';\n")
                if "'host'" not in cfg_content and 'host' not in cfg_content:
                    with open(os.path.join(pma_dir, 'config.inc.php'), 'a') as f:
                        f.write("$cfg['Servers'][$i]['host'] = '127.0.0.1';\n$cfg['Servers'][$i]['port'] = '3306';\n")
            else:
                rString = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
                data = open(os.path.join(pma_dir, 'config.sample.inc.php'), 'r').readlines()
                writeToFile = open(os.path.join(pma_dir, 'config.inc.php'), 'w')
                writeE = 1
                phpMyAdminContent = """
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonSession'] = 'SignonSession';
$cfg['Servers'][$i]['SignonURL'] = 'phpmyadminsignin.php';
$cfg['Servers'][$i]['LogoutURL'] = 'phpmyadminsignin.php?logout';
$cfg['Servers'][$i]['host'] = '127.0.0.1';
$cfg['Servers'][$i]['port'] = '3306';
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

            os.makedirs('/usr/local/CyberCP/public/phpmyadmin/tmp', exist_ok=True)

            if saved_signon and os.path.isfile(tmp_signon):
                shutil.copy2(tmp_signon, os.path.join(pma_dir, 'phpmyadminsignin.php'))
                try:
                    os.remove(tmp_signon)
                except Exception:
                    pass
            else:
                command = 'cp /usr/local/CyberCP/plogical/phpmyadminsignin.php /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php'
                Upgrade.executioner(command, 0)

            passFile = "/etc/cyberpanel/mysqlPassword"
            try:
                import json
                jsonData = json.loads(open(passFile, 'r').read())
                mysqlhost = jsonData.get('mysqlhost', '127.0.0.1') or '127.0.0.1'
                if mysqlhost == 'localhost':
                    mysqlhost = '127.0.0.1'
                command = "sed -i 's|localhost|%s|g' /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php" % (mysqlhost)
                Upgrade.executioner(command, 0)
            except Exception:
                pass

            command = 'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin'
            Upgrade.executioner_silent(command, 'chown phpMyAdmin')
            command = 'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp'
            Upgrade.executioner_silent(command, 'chown phpMyAdmin tmp')

            # Ensure signin file exists (idempotent; fixes 404 if copy failed earlier)
            signin_dest = os.path.join(pma_dir, 'phpmyadminsignin.php')
            signin_src = '/usr/local/CyberCP/plogical/phpmyadminsignin.php'
            if not os.path.isfile(signin_dest) and os.path.isfile(signin_src):
                try:
                    shutil.copy2(signin_src, signin_dest)
                except Exception:
                    pass

            try:
                from plogical.phpmyadmin_utils import ensure_phpmyadmin_sso
                ensure_phpmyadmin_sso()
            except Exception:
                pass

            os.chdir(cwd)
            Upgrade.ensureCyberPanelPhpmyadminOls()

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'download_install_phpmyadmin')
            Upgrade.stdOut("Failed to download and install phpMyAdmin [download_install_phpmyadmin]", 0)

    @staticmethod
    def setupComposer():
        composer_sh = '/tmp/composer.sh'
        try:
            if os.path.exists(composer_sh):
                os.remove(composer_sh)
            # Download to known path so chmod/run work regardless of cwd
            command = "wget -q https://cyberpanel.sh/composer.sh -O " + composer_sh
            Upgrade.executioner(command, 0)
            if not os.path.isfile(composer_sh):
                command = "curl -sSL https://cyberpanel.sh/composer.sh -o " + composer_sh
                Upgrade.executioner(command, 0)
            if not os.path.isfile(composer_sh):
                Upgrade.stdOut("composer.sh download failed, skipping", 0)
                return
            command = "chmod +x " + composer_sh
            Upgrade.executioner(command, 0)
            command = "bash " + composer_sh
            Upgrade.executioner(command, 0)
        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'setupComposer')
            Upgrade.stdOut("setupComposer error (non-fatal)", 0)

    @staticmethod
    def downoad_and_install_raindloop():
        try:
            # Data preservation: only /usr/local/CyberCP/public/snappymail (app files) is replaced.
            # Data under /usr/local/lscp/cyberpanel/snappymail/data and public/snappymail/data is never deleted.
            cwd = os.getcwd()

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            # Version: /etc/cyberpanel/snappymail_version, then latest from API, then fallback
            snappy_version = Upgrade.SnappyVersion
            version_file = '/etc/cyberpanel/snappymail_version'
            if os.path.isfile(version_file):
                try:
                    with open(version_file, 'r') as f:
                        raw = (f.read() or '').strip()
                    if raw and len(raw) < 20 and all(c.isdigit() or c == '.' for c in raw):
                        snappy_version = raw
                        Upgrade.stdOut(f"Using SnappyMail version from {version_file}: {snappy_version}", 0)
                except Exception:
                    pass
            if snappy_version == Upgrade.SnappyVersion:
                try:
                    from plogical.versionFetcher import get_latest_snappymail_version
                    latest_version = get_latest_snappymail_version()
                    if latest_version and latest_version != Upgrade.SnappyVersion:
                        Upgrade.stdOut(f"Using latest SnappyMail version: {latest_version}", 0)
                        snappy_version = latest_version
                    else:
                        Upgrade.stdOut(f"Using fallback SnappyMail version: {Upgrade.SnappyVersion}", 0)
                except Exception as e:
                    Upgrade.stdOut(f"Failed to fetch latest SnappyMail version, using fallback: {e}", 0)

            os.chdir("/usr/local/CyberCP/public")

            count = 1

            Upgrade.stdOut("Installing SnappyMail...", 0)
            
            while (1):
                command = 'wget -q https://github.com/the-djmaze/snappymail/releases/download/v%s/snappymail-%s.zip' % (
                    snappy_version, snappy_version)
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

            # Replace only app tree; data dirs (/usr/local/lscp/cyberpanel/snappymail/data, etc.) are preserved.
            # Symlinks to lscp must be unlinked (not rmtree) so restrained vhRoot stays valid.
            _sm_public = '/usr/local/CyberCP/public/snappymail'
            if os.path.islink(_sm_public):
                os.unlink(_sm_public)
            elif os.path.isdir(_sm_public):
                shutil.rmtree(_sm_public)
            elif os.path.exists(_sm_public):
                os.remove(_sm_public)

            while (1):
                command = 'unzip -q snappymail-%s.zip -d /usr/local/CyberCP/public/snappymail' % (snappy_version,)

                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break
            try:
                os.remove("snappymail-%s.zip" % (snappy_version,))
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

            _sm_root = "/usr/local/CyberCP/public/snappymail"
            _sm_index = os.path.join(_sm_root, "index.php")
            _sm_ver = os.path.join(_sm_root, "snappymail", "v")
            if not os.path.isfile(_sm_index):
                raise RuntimeError("SnappyMail index.php missing after unzip (check download/network).")
            if not os.path.isdir(_sm_ver):
                raise RuntimeError("SnappyMail snappymail/v missing after unzip.")

            iPath = os.listdir(_sm_ver)

            path = "/usr/local/CyberCP/public/snappymail/snappymail/v/%s/include.php" % (iPath[0])

            data = open(path, 'r').readlines()
            writeToFile = open(path, 'w')

            for items in data:
                if items.find("$sCustomDataPath = '';") > -1:
                    writeToFile.writelines(
                        "			$sCustomDataPath = '/usr/local/lscp/cyberpanel/snappymail/data';\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            # Create snappymail data directories (rainloop is deprecated in 2.5.5)
            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/"
            Upgrade.executioner_silent(command, 'mkdir snappymail configs', 0)

            bundled_sm = '/usr/local/CyberCP/snappymail_cyberpanel.php'
            if not os.path.isfile(bundled_sm):
                command = (
                    'wget -q -O %s https://raw.githubusercontent.com/the-djmaze/snappymail/master/integrations/cyberpanel/install.php'
                    % bundled_sm
                )
                Upgrade.executioner_silent(command, 'download snappymail cyberpanel helper', 0)
                if os.path.isfile(bundled_sm):
                    try:
                        with open(bundled_sm, 'r', encoding='utf-8', errors='replace') as f:
                            sm_helper = f.read()
                        sm_helper = sm_helper.replace(
                            '/usr/local/lscp/cyberpanel/rainloop/data/',
                            '/usr/local/lscp/cyberpanel/snappymail/data/'
                        )
                        with open(bundled_sm, 'w', encoding='utf-8') as f:
                            f.write(sm_helper)
                    except Exception:
                        pass

            snappy_php = None
            for php_bin in (
                '/usr/local/lsws/lsphp83/bin/php',
                '/usr/local/lsws/lsphp82/bin/php',
                '/usr/local/lsws/lsphp81/bin/php',
                '/usr/local/lsws/lsphp80/bin/php',
                'php',
            ):
                if php_bin == 'php' or os.path.isfile(php_bin):
                    snappy_php = php_bin
                    break
            if snappy_php and os.path.isfile(bundled_sm):
                command = '%s %s' % (snappy_php, bundled_sm)
                Upgrade.executioner_silent(command, 'snappymail cyberpanel configuration', 0)

            Upgrade.fixSnappymailIncludeDataPath()

            try:
                from plogical.snappymail_plugin_utilities import install_and_enable_list_unsubscribe_header_plugin
                if install_and_enable_list_unsubscribe_header_plugin():
                    Upgrade.stdOut("SnappyMail list-unsubscribe-header plugin installed and enabled", 0)
            except BaseException as plug_msg:
                Upgrade.stdOut("Warning: list-unsubscribe SnappyMail plugin: " + str(plug_msg), 0)

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
            
            # Migrate data from old rainloop folder to new snappymail folder (2.4.4 -> 2.5.5 upgrade)
            Upgrade.migrateRainloopToSnappymail()
            Upgrade.fixSnappymailIncludeDataPath()

            Upgrade.stdOut("SnappyMail installation completed.", 0)

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'downoad_and_install_raindloop')
            Upgrade.stdOut("Failed to download and install Rainloop [downoad_and_install_raindloop]", 0)

        return 1

    @staticmethod
    def downloadLink():
        try:
            version_number = VERSION
            version_build = BUILD

            try:
                Content = {"version":version_number,"build":version_build}
                path = "/usr/local/CyberCP/version.txt"
                writeToFile = open(path, 'w')
                writeToFile.write(json.dumps(Content))
                writeToFile.close()
            except:
                pass

            return (version_number + "." + str(version_build) + ".tar.gz")
        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'downloadLink')
            Upgrade.stdOut("Failed to download required files [downloadLink]")
            os._exit(0)

    @staticmethod
    def setupCLI():
        try:

            command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
            Upgrade.executioner(command, 'CLI Symlink', 0)

            command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
            Upgrade.executioner(command, 'CLI Permissions', 0)

        except OSError as e:
            ErrorSanitizer.log_error_securely(e, 'setupCLI')
            Upgrade.stdOut("Failed to setup CLI [setupCLI]")
            return 0

    @staticmethod
    def downloadCDNLibraries():
        """
        Download CDN libraries (qrious, chart.js) locally to eliminate tracking prevention warnings.
        These files are downloaded before collectstatic runs so they're included in the static files.
        Tries latest version first, falls back to hardcoded version if latest fails.
        """
        try:
            custom_js_dir = '/usr/local/CyberCP/baseTemplate/static/baseTemplate/custom-js'
            
            # Ensure directory exists
            if not os.path.exists(custom_js_dir):
                os.makedirs(custom_js_dir, mode=0o755)
            
            # Download qrious.min.js - try latest first, fallback to known working version
            qrious_path = os.path.join(custom_js_dir, 'qrious.min.js')
            qrious_urls = [
                'https://cdn.jsdelivr.net/npm/qrious@latest/dist/qrious.min.js',  # Try latest first
                'https://cdn.jsdelivr.net/npm/qrious@4.0.2/dist/qrious.min.js'   # Fallback to known working version
            ]
            qrious_downloaded = False
            for qrious_url in qrious_urls:
                command = f'wget -q --timeout=30 {qrious_url} -O {qrious_path}'
                result = subprocess.call(shlex.split(command))
                if result == 0 and os.path.exists(qrious_path) and os.path.getsize(qrious_path) > 1000:  # At least 1KB
                    os.chmod(qrious_path, 0o644)
                    version_info = "latest" if "latest" in qrious_url else "4.0.2"
                    Upgrade.stdOut(f"Downloaded qrious.min.js ({version_info})", 0)
                    qrious_downloaded = True
                    break
            if not qrious_downloaded:
                Upgrade.stdOut("Warning: Failed to download qrious.min.js, continuing anyway", 0)
            
            # Download chart.js - try latest first, fallback to known working version
            chartjs_path = os.path.join(custom_js_dir, 'chart.umd.min.js')
            chartjs_urls = [
                'https://cdn.jsdelivr.net/npm/chart.js@latest/dist/chart.umd.min.js',  # Try latest first
                'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'   # Fallback to known working version
            ]
            chartjs_downloaded = False
            for chartjs_url in chartjs_urls:
                command = f'wget -q --timeout=30 {chartjs_url} -O {chartjs_path}'
                result = subprocess.call(shlex.split(command))
                if result == 0 and os.path.exists(chartjs_path) and os.path.getsize(chartjs_path) > 100000:  # At least 100KB
                    os.chmod(chartjs_path, 0o644)
                    version_info = "latest" if "latest" in chartjs_url else "4.4.1"
                    Upgrade.stdOut(f"Downloaded chart.umd.min.js ({version_info})", 0)
                    chartjs_downloaded = True
                    # Create copy for chart.js compatibility (some code may expect chart.js name)
                    chartjs_compat_path = os.path.join(custom_js_dir, 'chart.js')
                    if not os.path.exists(chartjs_compat_path):
                        shutil.copy2(chartjs_path, chartjs_compat_path)
                    break
            if not chartjs_downloaded:
                Upgrade.stdOut("Warning: Failed to download chart.umd.min.js, continuing anyway", 0)
                
        except BaseException as msg:
            ErrorSanitizer.log_error_securely(msg, 'downloadCDNLibraries')
            Upgrade.stdOut(f"Warning: Error downloading CDN libraries: {str(msg)}, continuing anyway", 0)

    @staticmethod
    def ensure_gunicorn_in_cybercp_venv():
        """gunicorn is required by cyberpanel.service but may be missing after partial pip runs."""
        vpy = '/usr/local/CyberCP/bin/python'
        if not os.path.isfile(vpy):
            return
        rc = subprocess.call(
            [vpy, '-m', 'pip', 'install', '--no-cache-dir', 'gunicorn>=21,<24'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if rc != 0:
            Upgrade.stdOut('ERROR: Could not pip install gunicorn into CyberCP venv.', 0)
            raise SystemExit(1)

    @staticmethod
    def verify_cybercp_venv_core_modules():
        """Abort upgrade if the CyberCP venv cannot import runtime modules (matches shell verify)."""
        vpy = '/usr/local/CyberCP/bin/python'
        if not os.path.isfile(vpy):
            return
        mods = (
            'django',
            'MySQLdb',
            'OpenSSL',
            'paramiko',
            'requests',
            'fastapi',
            'cryptography',
            'gunicorn',
        )
        code = ';'.join('import %s' % m for m in mods)
        rc = subprocess.call([vpy, '-c', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if rc != 0:
            Upgrade.stdOut(
                'ERROR: CyberCP venv is missing required modules. '
                'Install build deps, then: /usr/local/CyberCP/bin/pip install -r /usr/local/requirments.txt',
                0,
            )
            raise SystemExit(1)

    @staticmethod
    def staticContent():

        py_chk = Upgrade._python_for_manage()
        if py_chk:
            chk = subprocess.run(
                [py_chk, '-c', 'import django'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if chk.returncode != 0:
                Upgrade.stdOut(
                    'Skipping collectstatic: Django is not importable yet. '
                    'After pip install completes, run: '
                    'cd /usr/local/CyberCP && DJANGO_SETTINGS_MODULE=CyberCP.settings '
                    f'{py_chk} manage.py collectstatic --noinput',
                    0,
                )
                return

        command = "rm -rf /usr/local/CyberCP/public/static"
        Upgrade.executioner(command, 'Remove old static content', 0)

        ##

        if not os.path.exists("/usr/local/CyberCP/public"):
            os.mkdir("/usr/local/CyberCP/public")

        # Download CDN libraries before collectstatic runs
        Upgrade.downloadCDNLibraries()

        cwd = os.getcwd()

        os.chdir('/usr/local/CyberCP')
        py = Upgrade._python_for_manage()
        command = py + ' manage.py collectstatic --noinput --clear --verbosity 0'
        Upgrade.executioner(command, 'Remove old static content', 0)

        os.chdir(cwd)

        shutil.move("/usr/local/CyberCP/static", "/usr/local/CyberCP/public/")

        # LiteSpeed serves /static/ from public/static; merge any leftover STATIC_ROOT
        # and guarantee webmail assets (e.g. after partial runs or collectstatic-only paths).
        try:
            from plogical import panel_static_sync

            if not panel_static_sync.ensure_litespeed_panel_static_complete():
                Upgrade.stdOut(
                    "Warning: public/static/webmail/webmail.js missing after staticContent; "
                    "check webmail app and permissions.",
                    0,
                )
        except BaseException as sync_err:
            ErrorSanitizer.log_error_securely(sync_err, 'panel_static_sync_after_staticContent')
            Upgrade.stdOut("Warning: panel static sync failed: %s" % (str(sync_err),), 0)

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
    def rotateInvalidAPITokens():
        try:
            import django
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            django.setup()
            from loginSystem.models import Administrator
            from plogical.securityUtils import ensure_api_token

            rotated = 0
            for account in Administrator.objects.exclude(api=0).only('id', 'token'):
                if ensure_api_token(account):
                    rotated += 1
            if rotated:
                Upgrade.stdOut('Rotated %s invalid API access token(s).' % rotated, 0)
        except Exception as msg:
            Upgrade.stdOut('Unable to rotate invalid API access tokens: %s' % msg, 0)

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

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'database_connection')
            Upgrade.stdOut("Failed to establish database connection")
            return 0, 0

    @staticmethod
    def getMachineIP():
        try:
            with open('/etc/cyberpanel/machineIP', 'r') as ip_file:
                return ip_file.readline().strip()
        except Exception:
            return ''

    @staticmethod
    def localCyberPanelDatabaseAccountHosts(database_host, machine_ip):
        """Return the MySQL accounts used by a local panel database."""
        if database_host in ('', 'localhost', '127.0.0.1', '::1'):
            # The installer creates both accounts so socket and TCP connections
            # keep working when a local service uses a different connection mode.
            return ('localhost', '127.0.0.1')
        if machine_ip and database_host == machine_ip:
            return (machine_ip,)
        return ()

    @staticmethod
    def repairLocalCyberPanelDatabaseAccess():
        """Restore the configured credentials for a local panel database."""
        connection = None

        try:
            database = settings.DATABASES['default']
            database_host = str(database.get('HOST') or '').strip()
            machine_ip = Upgrade.getMachineIP()
            account_hosts = Upgrade.localCyberPanelDatabaseAccountHosts(
                database_host, machine_ip,
            )

            if (database.get('NAME') != 'cyberpanel' or
                    database.get('USER') != 'cyberpanel' or
                    not database.get('PASSWORD') or not account_hosts):
                return 0

            connection, cursor = Upgrade.setupConnection()
            if connection == 0:
                return 0

            for account_host in account_hosts:
                cursor.execute(
                    'SELECT 1 FROM mysql.user WHERE User = %s AND Host = %s',
                    ('cyberpanel', account_host),
                )

                if cursor.fetchone():
                    cursor.execute(
                        'ALTER USER %s@%s IDENTIFIED BY %s',
                        ('cyberpanel', account_host, database['PASSWORD']),
                    )
                else:
                    cursor.execute(
                        'CREATE USER %s@%s IDENTIFIED BY %s',
                        ('cyberpanel', account_host, database['PASSWORD']),
                    )

                cursor.execute(
                    'GRANT ALL PRIVILEGES ON `cyberpanel`.* TO %s@%s',
                    ('cyberpanel', account_host),
                )
            cursor.execute('FLUSH PRIVILEGES')
            connection.close()
            return 1
        except Exception:
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass
            Upgrade.stdOut(
                'Unable to verify the local CyberPanel database account during upgrade.',
                0,
            )
            return 0

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

            # AI Scanner File Operation Audit Tables
            try:
                cursor.execute('''
                    CREATE TABLE `scanner_file_operations` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `scan_id` varchar(255) NOT NULL,
                        `operation` varchar(20) NOT NULL,
                        `file_path` varchar(500) NOT NULL,
                        `backup_path` varchar(500) DEFAULT NULL,
                        `success` bool NOT NULL DEFAULT 0,
                        `error_message` longtext DEFAULT NULL,
                        `ip_address` varchar(45) DEFAULT NULL,
                        `user_agent` varchar(255) DEFAULT NULL,
                        `created_at` datetime(6) NOT NULL,
                        KEY `scanner_file_operations_scan_id_idx` (`scan_id`),
                        KEY `scanner_file_operations_created_at_idx` (`created_at`),
                        KEY `scanner_file_operations_scan_created_idx` (`scan_id`, `created_at`)
                    )
                ''')
            except:
                pass

            try:
                cursor.execute('''
                    CREATE TABLE `scanner_api_rate_limits` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `scan_id` varchar(255) NOT NULL,
                        `endpoint` varchar(100) NOT NULL,
                        `request_count` integer NOT NULL DEFAULT 0,
                        `last_request_at` datetime(6) NOT NULL,
                        UNIQUE KEY `scanner_api_rate_limits_scan_endpoint_unique` (`scan_id`, `endpoint`),
                        KEY `scanner_api_rate_limits_scan_endpoint_idx` (`scan_id`, `endpoint`)
                    )
                ''')
            except:
                pass

            # CyberMail Email Delivery Tables
            try:
                cursor.execute('''
                    CREATE TABLE `cybermail_accounts` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `admin_id` integer NOT NULL UNIQUE,
                        `platform_account_id` integer DEFAULT NULL,
                        `api_key` varchar(255) NOT NULL DEFAULT '',
                        `email` varchar(255) NOT NULL DEFAULT '',
                        `plan_name` varchar(100) NOT NULL DEFAULT 'Free',
                        `plan_slug` varchar(50) NOT NULL DEFAULT 'free',
                        `emails_per_month` integer NOT NULL DEFAULT 15000,
                        `is_connected` bool NOT NULL DEFAULT 0,
                        `relay_enabled` bool NOT NULL DEFAULT 0,
                        `smtp_credential_id` integer DEFAULT NULL,
                        `smtp_username` varchar(255) NOT NULL DEFAULT '',
                        `smtp_host` varchar(255) NOT NULL DEFAULT 'mail.cyberpersons.com',
                        `smtp_port` integer NOT NULL DEFAULT 587,
                        `created_at` datetime(6) NOT NULL,
                        `updated_at` datetime(6) NOT NULL,
                        CONSTRAINT `cybermail_accounts_admin_id_fk` FOREIGN KEY (`admin_id`)
                        REFERENCES `loginSystem_administrator` (`id`) ON DELETE CASCADE
                    )
                ''')
            except:
                pass

            try:
                cursor.execute('''
                    CREATE TABLE `cybermail_domains` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `account_id` integer NOT NULL,
                        `domain` varchar(255) NOT NULL DEFAULT '',
                        `platform_domain_id` integer DEFAULT NULL,
                        `status` varchar(50) NOT NULL DEFAULT 'pending',
                        `spf_verified` bool NOT NULL DEFAULT 0,
                        `dkim_verified` bool NOT NULL DEFAULT 0,
                        `dmarc_verified` bool NOT NULL DEFAULT 0,
                        `dns_configured` bool NOT NULL DEFAULT 0,
                        `created_at` datetime(6) NOT NULL,
                        KEY `cybermail_domains_account_id_idx` (`account_id`),
                        CONSTRAINT `cybermail_domains_account_id_fk` FOREIGN KEY (`account_id`)
                        REFERENCES `cybermail_accounts` (`id`) ON DELETE CASCADE
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
            except Exception as e:
                ErrorSanitizer.log_error_securely(e, 'applyLoginSystemMigrations')
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

            if Upgrade.FindOperatingSytem() == Ubuntu22 or Upgrade.FindOperatingSytem() == Ubuntu24 or Upgrade.FindOperatingSytem() == Debian11 or Upgrade.FindOperatingSytem() == Debian12 or Upgrade.FindOperatingSytem() == Debian13:
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
    def homeDirectoryMigrations():
        """Create home_directories and user_home_mappings tables if missing (Modify Website home directory feature)."""
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `home_directories` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `name` varchar(50) NOT NULL UNIQUE,
                        `path` varchar(255) NOT NULL UNIQUE,
                        `is_active` tinyint(1) NOT NULL DEFAULT 1,
                        `is_default` tinyint(1) NOT NULL DEFAULT 0,
                        `max_users` integer NOT NULL DEFAULT 0,
                        `description` longtext,
                        `created_at` datetime(6) NOT NULL,
                        `updated_at` datetime(6) NOT NULL
                    )
                """)
            except Exception:
                pass
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `user_home_mappings` (
                        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `user_id` integer NOT NULL UNIQUE,
                        `home_directory_id` integer NOT NULL,
                        `created_at` datetime(6) NOT NULL,
                        `updated_at` datetime(6) NOT NULL,
                        CONSTRAINT `user_home_mappings_user_id_fk` FOREIGN KEY (`user_id`)
                            REFERENCES `loginSystem_administrator` (`id`) ON DELETE CASCADE,
                        CONSTRAINT `user_home_mappings_home_directory_id_fk` FOREIGN KEY (`home_directory_id`)
                            REFERENCES `home_directories` (`id`) ON DELETE CASCADE
                    )
                """)
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass
        except Exception:
            pass

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

            # Email Filtering Tables - Catch-All, Plus-Addressing, Pattern Forwarding
            query = """CREATE TABLE IF NOT EXISTS `e_catchall` (
  `domain_id` varchar(50) NOT NULL,
  `destination` varchar(255) NOT NULL,
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`domain_id`),
  KEY `idx_e_catchall_domain_id` (`domain_id`)
) ENGINE=InnoDB"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE IF NOT EXISTS `e_server_settings` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `plus_addressing_enabled` tinyint(1) NOT NULL DEFAULT 0,
  `plus_addressing_delimiter` varchar(1) NOT NULL DEFAULT '+',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE IF NOT EXISTS `e_plus_override` (
  `domain_id` varchar(50) NOT NULL,
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`domain_id`),
  KEY `idx_e_plus_override_domain_id` (`domain_id`)
) ENGINE=InnoDB"""
            try:
                cursor.execute(query)
            except:
                pass

            query = """CREATE TABLE IF NOT EXISTS `e_pattern_forwarding` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain_id` varchar(50) NOT NULL,
  `pattern` varchar(255) NOT NULL,
  `destination` varchar(255) NOT NULL,
  `pattern_type` varchar(20) NOT NULL DEFAULT 'wildcard',
  `priority` int(11) NOT NULL DEFAULT 100,
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `idx_e_pattern_forwarding_domain_id` (`domain_id`)
) ENGINE=InnoDB"""
            try:
                cursor.execute(query)
            except:
                pass

            # Seed singleton row for global email settings if missing.
            try:
                cursor.execute("""INSERT INTO `e_server_settings` (`id`, `plus_addressing_enabled`, `plus_addressing_delimiter`)
SELECT 1, 0, '+'
WHERE NOT EXISTS (SELECT 1 FROM `e_server_settings` WHERE `id` = 1)""")
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

            # Add new fields for network configuration and extra options
            try:
                cursor.execute('ALTER TABLE dockerManager_containers ADD network VARCHAR(100) DEFAULT "bridge"')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE dockerManager_containers ADD network_mode VARCHAR(50) DEFAULT "bridge"')
            except:
                pass

            try:
                cursor.execute('ALTER TABLE dockerManager_containers ADD extra_options LONGTEXT DEFAULT "{}"')
            except:
                pass

            try:
                connection.close()
            except:
                pass
        except:
            pass

        # Sync Django migration state so manage.py migrate sees dockerManager as applied
        try:
            cwd = os.getcwd()
            os.chdir('/usr/local/CyberCP')
            py = Upgrade._python_for_manage()
            command = py + ' manage.py migrate dockerManager --noinput'
            Upgrade.executioner(command, 'migrate dockerManager', 0)
            os.chdir(cwd)
        except Exception:
            try:
                os.chdir(cwd)
            except Exception:
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

            ## Resource Limits columns for cgroups v2 integration
            query = "ALTER TABLE packages_package ADD COLUMN memoryLimitMB INT DEFAULT 1024;"
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN cpuCores INT DEFAULT 1;"
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN ioLimitMBPS INT DEFAULT 10;"
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN inodeLimit INT DEFAULT 400000;"
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN maxConnections INT DEFAULT 10;"
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN procSoftLimit INT DEFAULT 400;"
            try:
                cursor.execute(query)
            except:
                pass

            query = "ALTER TABLE packages_package ADD COLUMN procHardLimit INT DEFAULT 500;"
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
    def setupSieve():
        """Enable Sieve plugin and ManageSieve for email filtering (idempotent)"""
        try:
            if not os.path.exists('/etc/dovecot/dovecot.conf'):
                Upgrade.stdOut("Dovecot not installed, skipping Sieve setup.", 0)
                return

            ## Ensure cyrus-sasl-plain is installed (needed for SMTP relay on RHEL/Alma/CentOS)
            if os.path.exists('/etc/redhat-release'):
                command = 'dnf install -y cyrus-sasl-plain'
                ProcessUtilities.executioner(command)

            import re

            dovecot_conf = '/etc/dovecot/dovecot.conf'
            with open(dovecot_conf, 'r') as f:
                content = f.read()

            changed = False

            # Add sieve to protocols if missing
            protocols_match = re.search(r'^protocols\s*=\s*(.+)$', content, re.MULTILINE)
            if protocols_match and 'sieve' not in protocols_match.group(1):
                content = content.replace(protocols_match.group(0),
                    protocols_match.group(0) + ' sieve')
                changed = True

            # Add sieve plugin to protocol lda mail_plugins if missing
            lda_match = re.search(r'(protocol lda\s*\{[^}]*mail_plugins\s*=\s*)([^\n]+)', content)
            if lda_match and 'sieve' not in lda_match.group(2):
                content = content.replace(lda_match.group(0),
                    lda_match.group(1) + lda_match.group(2).rstrip() + ' sieve')
                changed = True

            # Add lda_mailbox_autocreate/autosubscribe for sieve fileinto
            if 'lda_mailbox_autocreate' not in content:
                lda_plugins = re.search(r'(protocol lda\s*\{[^}]*mail_plugins\s*=[^\n]+\n)', content)
                if lda_plugins:
                    content = content.replace(lda_plugins.group(0),
                        lda_plugins.group(0) +
                        '    lda_mailbox_autocreate = yes\n    lda_mailbox_autosubscribe = yes\n')
                    changed = True

            # Add sieve storage settings to plugin section
            if 'sieve_dir' not in content:
                plugin_match = re.search(r'(plugin\s*\{[^}]*)(})', content)
                if plugin_match:
                    content = content.replace(plugin_match.group(0),
                        plugin_match.group(1) +
                        '\n  sieve = ~/sieve/.dovecot.sieve\n  sieve_dir = ~/sieve\n\n' +
                        plugin_match.group(2))
                    changed = True

            if changed:
                with open(dovecot_conf, 'w') as f:
                    f.write(content)

            # Fix dovecot-sql.conf.ext to include home directory for sieve storage
            sql_conf = '/etc/dovecot/dovecot-sql.conf.ext'
            if os.path.exists(sql_conf):
                with open(sql_conf, 'r') as f:
                    sql_content = f.read()
                if 'as home' not in sql_content and 'user_query' in sql_content:
                    sql_content = re.sub(
                        r"(user_query\s*=\s*SELECT\s+'5000'\s+as\s+uid,\s+'5000'\s+as\s+gid,\s+mail)\s+(FROM\s+e_users\s+WHERE\s+email='%u';)",
                        r"\1, CONCAT('/home/vmail/', SUBSTRING_INDEX(email, '@', -1), '/', SUBSTRING_INDEX(email, '@', 1)) as home \2",
                        sql_content)
                    with open(sql_conf, 'w') as f:
                        f.write(sql_content)

            # Write ManageSieve config if not properly configured
            managesieve_conf = '/etc/dovecot/conf.d/20-managesieve.conf'
            write_managesieve = True
            if os.path.exists(managesieve_conf):
                with open(managesieve_conf, 'r') as f:
                    existing = f.read()
                if 'inet_listener sieve' in existing and 'service managesieve' in existing:
                    write_managesieve = False

            if write_managesieve:
                os.makedirs('/etc/dovecot/conf.d', exist_ok=True)
                with open(managesieve_conf, 'w') as f:
                    f.write("""protocols = $protocols sieve

service managesieve-login {
  inet_listener sieve {
    port = 4190
  }
}

service managesieve {
  process_limit = 256
}

protocol sieve {
  managesieve_notify_capability = mailto
  managesieve_sieve_capability = fileinto reject envelope encoded-character vacation subaddress comparator-i;ascii-numeric relational regex imap4flags copy include variables body enotify environment mailbox date index ihave duplicate mime foreverypart extracttext
}
""")

            # Install sieve packages if missing
            if os.path.exists('/etc/lsb-release') or os.path.exists('/etc/debian_version'):
                Upgrade.executioner('apt-get install -y dovecot-sieve dovecot-managesieved', 'Install Sieve packages', 0)
            else:
                Upgrade.executioner('yum install -y dovecot-pigeonhole', 'Install Sieve packages', 0)

            # Open firewall port
            try:
                from plogical.firewallUtilities import FirewallUtilities
                FirewallUtilities.addSieveFirewallRule()
            except:
                pass

            subprocess.call(['systemctl', 'restart', 'dovecot'])
            Upgrade.stdOut("Sieve setup complete!", 0)

        except BaseException as msg:
            Upgrade.stdOut("setupSieve error: " + str(msg), 0)

    @staticmethod
    def setupWebmail():
        """Set up Dovecot master user and webmail config for SSO (idempotent)"""
        try:
            # Skip if no mail server installed
            if not os.path.exists('/etc/dovecot/dovecot.conf'):
                Upgrade.stdOut("Dovecot not installed, skipping webmail setup.", 0)
                return

            # Always run migrations and dovecot.conf patching even if conf exists
            already_configured = os.path.exists('/etc/cyberpanel/webmail.conf') and \
                                 os.path.exists('/etc/dovecot/master-users')

            if not already_configured:
                Upgrade.stdOut("Setting up webmail master user for SSO...", 0)

                from plogical.randomPassword import generate_pass

                master_password = generate_pass(32)

                # Hash the password using doveadm
                result = subprocess.run(
                    ['doveadm', 'pw', '-s', 'SHA512-CRYPT', '-p', master_password],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    Upgrade.stdOut("doveadm pw failed: " + result.stderr, 0)
                    return

                password_hash = result.stdout.strip()

                # Write /etc/dovecot/master-users
                with open('/etc/dovecot/master-users', 'w') as f:
                    f.write('cyberpanel_master:' + password_hash + '\n')
                os.chmod('/etc/dovecot/master-users', 0o600)
                subprocess.call(['chown', 'dovecot:dovecot', '/etc/dovecot/master-users'])

                # Write /etc/cyberpanel/webmail.conf
                webmail_conf = {
                    'master_user': 'cyberpanel_master',
                    'master_password': master_password
                }
                with open('/etc/cyberpanel/webmail.conf', 'w') as f:
                    json.dump(webmail_conf, f)
                os.chmod('/etc/cyberpanel/webmail.conf', 0o600)
                subprocess.call(['chown', 'cyberpanel:cyberpanel', '/etc/cyberpanel/webmail.conf'])

            # Patch dovecot.conf if master user config not present
            dovecot_conf_path = '/etc/dovecot/dovecot.conf'
            with open(dovecot_conf_path, 'r') as f:
                dovecot_content = f.read()

            if 'auth_master_user_separator' not in dovecot_content:
                master_block = """auth_master_user_separator = *

passdb {
    driver = passwd-file
    master = yes
    args = /etc/dovecot/master-users
    result_success = continue
}

"""
                dovecot_content = dovecot_content.replace(
                    'passdb {',
                    master_block + 'passdb {',
                    1  # Only replace the first occurrence
                )
                with open(dovecot_conf_path, 'w') as f:
                    f.write(dovecot_content)

            # Run webmail migrations
            Upgrade.executioner(
                'python /usr/local/CyberCP/manage.py makemigrations webmail',
                'Webmail makemigrations', shell=True
            )
            Upgrade.executioner(
                'python /usr/local/CyberCP/manage.py migrate',
                'Webmail migrate', shell=True
            )

            # Fix webmail.conf ownership for lscpd (may be wrong on existing installs)
            if os.path.exists('/etc/cyberpanel/webmail.conf'):
                subprocess.call(['chown', 'cyberpanel:cyberpanel', '/etc/cyberpanel/webmail.conf'])
                os.chmod('/etc/cyberpanel/webmail.conf', 0o600)

            # Restart Dovecot
            subprocess.call(['systemctl', 'restart', 'dovecot'])

            Upgrade.stdOut("Webmail master user setup complete!", 0)

        except BaseException as msg:
            Upgrade.stdOut("setupWebmail error: " + str(msg), 0)

    @staticmethod
    def fixMailTLS():
        """Ensure Postfix/Dovecot TLS cert files exist at expected paths.

        On Ubuntu, the install creates dirs at /etc/pki/dovecot/ but never
        copies the self-signed certs there. This breaks STARTTLS and prevents
        external mail servers (Gmail, etc.) from delivering inbound mail.
        """
        try:
            cert_path = '/etc/pki/dovecot/certs/dovecot.pem'
            key_path = '/etc/pki/dovecot/private/dovecot.pem'

            # Skip if certs already exist
            if os.path.exists(cert_path) and os.path.exists(key_path):
                return

            # Skip if no mail server
            if not os.path.exists('/etc/dovecot/dovecot.conf'):
                return

            Upgrade.stdOut("Fixing mail TLS certificates...", 0)

            os.makedirs('/etc/pki/dovecot/certs', exist_ok=True)
            os.makedirs('/etc/pki/dovecot/private', exist_ok=True)

            # Prefer existing Dovecot self-signed certs
            if os.path.exists('/etc/dovecot/cert.pem') and os.path.exists('/etc/dovecot/key.pem'):
                import shutil
                shutil.copy2('/etc/dovecot/cert.pem', cert_path)
                shutil.copy2('/etc/dovecot/key.pem', key_path)
            else:
                # Generate a new self-signed cert
                hostname = ProcessUtilities.outputExecutioner(
                    'hostname').strip() or 'localhost'
                subprocess.call([
                    'openssl', 'req', '-x509', '-nodes', '-days', '3650',
                    '-newkey', 'rsa:2048',
                    '-subj', '/CN=%s' % hostname,
                    '-keyout', key_path,
                    '-out', cert_path
                ])

            os.chmod(cert_path, 0o644)
            os.chmod(key_path, 0o600)

            # Restart Postfix to pick up the certs
            subprocess.call(['systemctl', 'restart', 'postfix'])

            Upgrade.stdOut("Mail TLS certificates fixed.", 0)

        except BaseException as msg:
            Upgrade.stdOut("fixMailTLS error: " + str(msg), 0)

    @staticmethod
    def repairDovecot24SNIPaths():
        dovecot_conf = '/etc/dovecot/dovecot.conf'
        if not os.path.isfile(dovecot_conf):
            return

        with open(dovecot_conf, 'r') as conf_file:
            content = conf_file.read()

        if 'dovecot_config_version = 2.4.0' not in content:
            return

        from plogical.virtualHostUtilities import virtualHostUtilities
        normalized = virtualHostUtilities.normalizeDovecotSNIPaths(content)

        if normalized != content:
            conf_stat = os.stat(dovecot_conf)
            temporary_conf = dovecot_conf + '.cyberpanel-sni.tmp'
            try:
                with open(temporary_conf, 'w') as conf_file:
                    conf_file.write(normalized)
                    conf_file.flush()
                    os.fsync(conf_file.fileno())
                os.chmod(temporary_conf, conf_stat.st_mode & 0o7777)
                os.chown(temporary_conf, conf_stat.st_uid, conf_stat.st_gid)
                os.replace(temporary_conf, dovecot_conf)
                Upgrade.stdOut("Updated Dovecot 2.4 SNI certificate paths.", 0)
            finally:
                if os.path.exists(temporary_conf):
                    os.remove(temporary_conf)

        validation = subprocess.run(
            ['doveconf', '-n'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if validation.returncode != 0:
            raise RuntimeError(
                'Dovecot configuration validation failed after SNI path repair.'
            )

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
    def firewallMigrations():
        """Ensure firewall app tables exist (e.g. firewall_bannedips for Ban IP). Upgrade does not run GeneralMigrations(), so run migrate firewall explicitly."""
        try:
            cwd = os.getcwd()
            os.chdir('/usr/local/CyberCP')
            py = Upgrade._python_for_manage()
            command = py + ' manage.py migrate firewall --noinput'
            Upgrade.executioner(command, 'Run firewall migrations (firewall_bannedips)', 0)
            os.chdir(cwd)
        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'firewallMigrations')
            try:
                os.chdir(cwd)
            except Exception:
                pass
        Upgrade.syncBannedIPsJsonToDb()

    @staticmethod
    def syncBannedIPsJsonToDb():
        """Sync banned IPs from JSON (e.g. from base dashboard Ban IP) into firewall_bannedips so Firewall > Banned IPs shows all."""
        try:
            import json
            for path in ['/usr/local/CyberCP/data/banned_ips.json', '/etc/cyberpanel/banned_ips.json']:
                if not os.path.exists(path):
                    continue
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                except Exception:
                    continue
                if not isinstance(data, list):
                    continue
                connection, cursor = Upgrade.setupConnection('cyberpanel')
                if not cursor:
                    continue
                try:
                    cursor.execute('SELECT id FROM loginSystem_administrator ORDER BY id ASC LIMIT 1')
                    row = cursor.fetchone()
                    admin_id = int(row[0]) if row else 1
                except Exception:
                    admin_id = 1
                for b in data:
                    if not b.get('active', True):
                        continue
                    ip_val = (b.get('ip') or '').strip()
                    if not ip_val or len(ip_val) > 45:
                        continue
                    reason = (b.get('reason') or 'Banned from dashboard')[:255]
                    banned_on = b.get('banned_on')
                    if isinstance(banned_on, (int, float)):
                        from_unixtime = banned_on
                    else:
                        from_unixtime = int(__import__('time').time())
                    try:
                        cursor.execute(
                            """INSERT IGNORE INTO firewall_bannedips (ip_address, reason, duration, banned_on, expires, active, admin_id)
                               VALUES (%s, %s, 'permanent', FROM_UNIXTIME(%s), NULL, 1, %s)""",
                            (ip_val, reason, from_unixtime, admin_id)
                        )
                    except Exception:
                        pass
                try:
                    connection.close()
                except Exception:
                    pass
                break
        except Exception as e:
            try:
                ErrorSanitizer.log_error_securely(e, 'syncBannedIPsJsonToDb')
            except Exception:
                pass

    @staticmethod
    def _python_for_manage():
        """Resolve Python for manage.py (avoid FileNotFoundError when venv python missing)."""
        from plogical.cyberpanel_python import resolve_cyberpanel_python
        return resolve_cyberpanel_python()

    @staticmethod
    def GeneralMigrations():
        try:

            cwd = os.getcwd()
            os.chdir('/usr/local/CyberCP')
            py = Upgrade._python_for_manage()

            command = py + ' manage.py makemigrations'
            Upgrade.executioner(command, 'python manage.py makemigrations', 0)

            command = py + ' manage.py makemigrations'
            Upgrade.executioner(command, py + ' manage.py migrate', 0)

            os.chdir(cwd)

        except:
            pass

    @staticmethod
    def fixBaseTemplateMigrations():
        """
        Fix baseTemplate migrations to prevent NodeNotFoundError on AlmaLinux 9 and Ubuntu 24
        """
        try:
            Upgrade.stdOut("Fixing baseTemplate migrations for AlmaLinux 9 and Ubuntu 24 compatibility...")
            
            # Ensure baseTemplate migrations directory exists
            migrations_dir = "/usr/local/CyberCP/baseTemplate/migrations"
            if not os.path.exists(migrations_dir):
                os.makedirs(migrations_dir)
                Upgrade.stdOut("Created baseTemplate migrations directory")

            # Create __init__.py if it doesn't exist
            init_file = os.path.join(migrations_dir, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write("")
                Upgrade.stdOut("Created baseTemplate migrations __init__.py")

            # Create 0001_initial.py if it doesn't exist
            initial_migration = os.path.join(migrations_dir, "0001_initial.py")
            if not os.path.exists(initial_migration):
                initial_content = '''# Generated by Django 3.2.25 on 2024-01-01 00:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CyberPanelCosmetic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('MainDashboardCSS', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='UserNotificationPreferences',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('backup_notification_dismissed', models.BooleanField(default=False, help_text='Whether user has dismissed the backup notification')),
                ('ai_scanner_notification_dismissed', models.BooleanField(default=False, help_text='Whether user has dismissed the AI scanner notification')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'User Notification Preferences',
                'verbose_name_plural': 'User Notification Preferences',
            },
        ),
        migrations.CreateModel(
            name='version',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=10)),
                ('build', models.IntegerField()),
            ],
        ),
    ]
'''
                with open(initial_migration, 'w') as f:
                    f.write(initial_content)
                Upgrade.stdOut("Created baseTemplate 0001_initial.py migration")

            # Create 0002_usernotificationpreferences.py if it doesn't exist
            notification_migration = os.path.join(migrations_dir, "0002_usernotificationpreferences.py")
            if not os.path.exists(notification_migration):
                notification_content = '''# Generated by Django 3.2.25 on 2024-01-01 00:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('baseTemplate', '0001_initial'),
        ('loginSystem', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationpreferences',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preferences', to='loginSystem.administrator'),
        ),
    ]
'''
                with open(notification_migration, 'w') as f:
                    f.write(notification_content)
                Upgrade.stdOut("Created baseTemplate 0002_usernotificationpreferences.py migration")

            # Set proper permissions
            command = "chown -R root:root " + migrations_dir
            Upgrade.executioner(command, 0)
            
            command = "chmod -R 755 " + migrations_dir
            Upgrade.executioner(command, 0)

            # Update Django settings to include DEFAULT_AUTO_FIELD if not present
            settings_file = "/usr/local/CyberCP/CyberCP/settings.py"
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings_content = f.read()
                
                if "DEFAULT_AUTO_FIELD" not in settings_content:
                    with open(settings_file, 'a') as f:
                        f.write("\n# Default primary key field type\n")
                        f.write("# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field\n")
                        f.write("DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'\n")
                    Upgrade.stdOut("Added DEFAULT_AUTO_FIELD to Django settings")

            Upgrade.stdOut("baseTemplate migrations fixed successfully")

        except Exception as e:
            Upgrade.stdOut("Error fixing baseTemplate migrations: " + str(e))

    @staticmethod
    def fixSnappymailIncludeDataPath():
        """
        Ensure SnappyMail include.php points at snappymail/data (not removed rainloop/data).
        Fresh 2.5.5 installs skip rainloop migration but still get a wrong path from upstream install.php.
        """
        old_path = '/usr/local/lscp/cyberpanel/rainloop/data'
        new_path = '/usr/local/lscp/cyberpanel/snappymail/data'
        include_file = '/usr/local/CyberCP/public/snappymail/include.php'
        try:
            if os.path.isfile(include_file):
                with open(include_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                if old_path in content or 'rainloop/data' in content:
                    content = content.replace(old_path, new_path).replace(
                        'rainloop/data', 'snappymail/data'
                    )
                    with open(include_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    Upgrade.stdOut('Updated include.php to use snappymail data path.', 0)
            try:
                version_root = '/usr/local/CyberCP/public/snappymail/snappymail/v/'
                if os.path.isdir(version_root):
                    for ver in os.listdir(version_root):
                        version_include = os.path.join(version_root, ver, 'include.php')
                        if not os.path.isfile(version_include):
                            continue
                        with open(version_include, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        if "$sCustomDataPath = '';" in content:
                            content = content.replace(
                                "$sCustomDataPath = '';",
                                "$sCustomDataPath = '/usr/local/lscp/cyberpanel/snappymail/data';"
                            )
                            with open(version_include, 'w', encoding='utf-8') as f:
                                f.write(content)
                            Upgrade.stdOut('Updated version include.php custom data path.', 0)
                        elif old_path in content:
                            content = content.replace(old_path, new_path)
                            with open(version_include, 'w', encoding='utf-8') as f:
                                f.write(content)
            except Exception as ver_exc:
                Upgrade.stdOut('Warning: version include.php path fix: ' + str(ver_exc), 0)
            os.makedirs(new_path, mode=0o755, exist_ok=True)
            os.makedirs(os.path.join(new_path, '_data_', '_default_', 'configs'), mode=0o755, exist_ok=True)
        except Exception as e:
            Upgrade.stdOut('Warning: fixSnappymailIncludeDataPath: ' + str(e), 0)

    @staticmethod
    def migrateRainloopToSnappymail():
        """
        Migrate data from old rainloop folder to new snappymail folder
        This migration is for upgrading from CyberPanel 2.4.4 to 2.5.5-dev
        """
        try:
            old_data_path = '/usr/local/lscp/cyberpanel/rainloop/data'
            new_data_path = '/usr/local/lscp/cyberpanel/snappymail/data'
            
            # Check if old rainloop data exists
            if not os.path.exists(old_data_path):
                Upgrade.stdOut("No old rainloop data found, skipping migration.", 0)
                return 0
            
            # Check if old data directory has actual content
            try:
                old_data_contents = os.listdir(old_data_path)
                if not old_data_contents or old_data_contents == []:
                    Upgrade.stdOut("Old rainloop data directory is empty, skipping migration.", 0)
                    return 0
            except:
                Upgrade.stdOut("Could not read old rainloop data directory, skipping migration.", 0)
                return 0
            
            # Check if new snappymail data already exists and has content
            if os.path.exists(new_data_path):
                try:
                    new_data_contents = os.listdir(new_data_path)
                    # If new directory has content (more than just empty subdirs), don't migrate
                    if new_data_contents and len(new_data_contents) > 0:
                        # Check if _data_ directory exists and has content
                        data_dir = os.path.join(new_data_path, '_data_')
                        if os.path.exists(data_dir):
                            default_dir = os.path.join(data_dir, '_default_')
                            if os.path.exists(default_dir):
                                default_contents = os.listdir(default_dir)
                                # If configs, domains, or storage exist, assume migration already done
                                if any(item in default_contents for item in ['configs', 'domains', 'storage']):
                                    Upgrade.stdOut("SnappyMail data already exists, skipping migration.", 0)
                                    return 0
                except:
                    pass
            
            Upgrade.stdOut("Migrating rainloop data to snappymail...", 0)
            
            # Ensure new data directory structure exists
            os.makedirs(new_data_path, exist_ok=True)
            os.makedirs(os.path.join(new_data_path, '_data_', '_default_'), exist_ok=True)
            
            # Use rsync to copy data (preserves permissions, ownership, and handles large files)
            import subprocess
            import shlex
            
            # Copy all data from old to new location
            command = f'rsync -av --ignore-existing {old_data_path}/ {new_data_path}/'
            cmd = shlex.split(command)
            result = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if result == 0:
                # Set proper ownership for migrated data
                command = "chown -R lscpd:lscpd " + new_data_path
                Upgrade.executioner_silent(command, 'Set ownership for migrated data', 0)
                
                # Set proper permissions
                command = "chmod -R 775 " + new_data_path
                Upgrade.executioner_silent(command, 'Set permissions for migrated data', 0)
                
                Upgrade.stdOut("Successfully migrated rainloop data to snappymail.", 0)
                
                # Update include.php to use new snappymail path
                include_file = '/usr/local/CyberCP/public/snappymail/include.php'
                if os.path.exists(include_file):
                    try:
                        with open(include_file, 'r') as f:
                            content = f.read()
                        
                        # Replace rainloop path with snappymail path
                        content = content.replace(
                            '/usr/local/lscp/cyberpanel/rainloop/data',
                            '/usr/local/lscp/cyberpanel/snappymail/data'
                        )
                        
                        with open(include_file, 'w') as f:
                            f.write(content)
                        
                        Upgrade.stdOut("Updated include.php to use snappymail data path.", 0)
                    except Exception as e:
                        Upgrade.stdOut(f"Warning: Could not update include.php: {str(e)}", 0)
                
                # Also update the version-specific include.php if it exists
                try:
                    iPath = os.listdir('/usr/local/CyberCP/public/snappymail/snappymail/v/')
                    if iPath:
                        version_include = f"/usr/local/CyberCP/public/snappymail/snappymail/v/{iPath[0]}/include.php"
                        if os.path.exists(version_include):
                            with open(version_include, 'r') as f:
                                content = f.read()
                            
                            # Replace rainloop path with snappymail path
                            content = content.replace(
                                '/usr/local/lscp/cyberpanel/rainloop/data',
                                '/usr/local/lscp/cyberpanel/snappymail/data'
                            )
                            
                            with open(version_include, 'w') as f:
                                f.write(content)
                            
                            Upgrade.stdOut("Updated version-specific include.php to use snappymail data path.", 0)
                except:
                    pass
                
                # Replace ALL rainloop path/URL references in migrated SnappyMail data (configs, domains, plugins)
                try:
                    data_extensions = ('.ini', '.json', '.php', '.cfg')
                    replace_count = 0
                    for root, _dirs, files in os.walk(new_data_path):
                        for name in files:
                            if name.endswith(data_extensions):
                                path = os.path.join(root, name)
                                try:
                                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                                        content = f.read()
                                    new_content = content.replace(
                                        '/usr/local/lscp/cyberpanel/rainloop/data',
                                        '/usr/local/lscp/cyberpanel/snappymail/data'
                                    ).replace(
                                        '/rainloop/',
                                        '/snappymail/'
                                    ).replace(
                                        'rainloop/data',
                                        'snappymail/data'
                                    )
                                    if new_content != content:
                                        with open(path, 'w', encoding='utf-8') as f:
                                            f.write(new_content)
                                        replace_count += 1
                                except (IOError, OSError):
                                    pass
                    if replace_count > 0:
                        Upgrade.stdOut(f"Updated rainloop→snappymail links in {replace_count} config file(s).", 0)
                except Exception as e:
                    Upgrade.stdOut(f"Warning: Could not replace rainloop links in data files: {str(e)}", 0)
                
                # Redirect /rainloop to /snappymail so old bookmarks and links keep working
                try:
                    htaccess_path = '/usr/local/CyberCP/public/.htaccess'
                    redirect_block = (
                        '\n# Redirect old RainLoop URL to SnappyMail (2.5.5 upgrade)\n'
                        '<IfModule mod_rewrite.c>\n'
                        'RewriteEngine On\n'
                        'RewriteRule ^rainloop/?(.*)$ /snappymail/$1 [R=301,L]\n'
                        '</IfModule>\n'
                    )
                    if os.path.exists(htaccess_path):
                        with open(htaccess_path, 'r', encoding='utf-8', errors='replace') as f:
                            existing = f.read()
                        if 'Redirect old RainLoop URL to SnappyMail' not in existing:
                            with open(htaccess_path, 'a', encoding='utf-8') as f:
                                f.write(redirect_block)
                            Upgrade.stdOut("Added /rainloop→/snappymail redirect to .htaccess.", 0)
                    else:
                        with open(htaccess_path, 'w', encoding='utf-8') as f:
                            f.write(redirect_block)
                        Upgrade.stdOut("Created .htaccess with /rainloop→/snappymail redirect.", 0)
                except Exception as e:
                    Upgrade.stdOut(f"Warning: Could not add rainloop redirect to .htaccess: {str(e)}", 0)
                
                return 1
            else:
                Upgrade.stdOut("Warning: Data migration completed with errors. Please verify manually.", 0)
                return 0
                
        except Exception as e:
            Upgrade.stdOut(f"Error during rainloop to snappymail migration: {str(e)}", 0)
            return 0

    @staticmethod
    def pdnsSchemaMigrations():
        """
        Bring the PowerDNS gmysql schema up to PDNS 4.7+/5.x expectations.
        Customers can otherwise hit a total DNS outage when an unrelated
        `dnf update` pulls in PDNS 5.x and the new binary fails with
        `Unknown column 'domains.catalog' in 'SELECT'`. Idempotent.
        """
        try:
            from plogical.pdnsSchemaMigration import migrate_pdns_schema
            results = migrate_pdns_schema(restart_service=True)
            if results.get('applied'):
                Upgrade.stdOut(
                    'PDNS schema migration applied: ' +
                    ', '.join(results['applied']), 0)
            if results.get('errors'):
                Upgrade.stdOut(
                    'PDNS schema migration errors: ' + str(results['errors']),
                    0)
        except BaseException as msg:
            Upgrade.stdOut('pdnsSchemaMigrations error: ' + str(msg), 0)

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
    def fixSubdomainLogConfigurations():
        """Fix subdomain log configurations during upgrade"""
        try:
            # Check if this fix has already been applied
            fix_marker_file = '/usr/local/lscp/logs/subdomain_log_fix_applied'
            if os.path.exists(fix_marker_file):
                Upgrade.stdOut("Subdomain log fix already applied - skipping")
                return
            
            Upgrade.stdOut("=== FIXING SUBDOMAIN LOG CONFIGURATIONS ===")
            
            # Import required modules
            import sys
            import os
            sys.path.append('/usr/local/CyberCP')
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            
            try:
                import django
                django.setup()
                
                from websiteFunctions.models import ChildDomains
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                from plogical.processUtilities import ProcessUtilities
                import re
                import shutil
                from datetime import datetime
                
                # Get all child domains
                child_domains = ChildDomains.objects.all()
                
                if not child_domains:
                    Upgrade.stdOut("No child domains found - skipping subdomain log fix")
                    return
                
                Upgrade.stdOut(f"Found {len(child_domains)} child domains to check")
                
                fixed_count = 0
                skipped_count = 0
                
                for child_domain in child_domains:
                    domain_name = child_domain.domain
                    master_domain = child_domain.master.domain
                    
                    vhost_conf_path = f"/usr/local/lsws/conf/vhosts/{domain_name}/vhost.conf"
                    
                    if not os.path.exists(vhost_conf_path):
                        Upgrade.stdOut(f"⚠️  Skipping {domain_name}: vHost config not found")
                        skipped_count += 1
                        continue
                    
                    try:
                        # Read current configuration
                        with open(vhost_conf_path, 'r') as f:
                            config_content = f.read()
                        
                        # Check if fix is needed
                        if f'{master_domain}.error_log' not in config_content and f'{master_domain}.access_log' not in config_content:
                            Upgrade.stdOut(f"✅ {domain_name}: Already has correct log configuration")
                            skipped_count += 1
                            continue
                        
                        # Create backup
                        backup_path = f"{vhost_conf_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(vhost_conf_path, backup_path)
                        
                        # Fix the configuration
                        fixed_content = config_content
                        
                        # Fix error log path
                        fixed_content = re.sub(
                            rf'errorlog\s+\$VH_ROOT/logs/{re.escape(master_domain)}\.error_log',
                            f'errorlog $VH_ROOT/logs/{domain_name}.error_log',
                            fixed_content
                        )
                        
                        # Fix access log path
                        fixed_content = re.sub(
                            rf'accesslog\s+\$VH_ROOT/logs/{re.escape(master_domain)}\.access_log',
                            f'accesslog $VH_ROOT/logs/{domain_name}.access_log',
                            fixed_content
                        )
                        
                        # Fix CustomLog paths (for Apache configurations)
                        fixed_content = re.sub(
                            rf'CustomLog\s+/home/{re.escape(master_domain)}/logs/{re.escape(master_domain)}\.access_log',
                            f'CustomLog /home/{domain_name}/logs/{domain_name}.access_log',
                            fixed_content
                        )
                        
                        # Write the fixed configuration
                        with open(vhost_conf_path, 'w') as f:
                            f.write(fixed_content)
                        
                        # Set proper ownership
                        ProcessUtilities.executioner(f'chown lsadm:lsadm {vhost_conf_path}')
                        
                        # Create the log directory if it doesn't exist
                        log_dir = f"/home/{master_domain}/logs"
                        if not os.path.exists(log_dir):
                            os.makedirs(log_dir, exist_ok=True)
                            ProcessUtilities.executioner(f'chown -R {child_domain.master.externalApp}:{child_domain.master.externalApp} {log_dir}')
                        
                        # Create separate log files for the child domain
                        error_log_path = f"{log_dir}/{domain_name}.error_log"
                        access_log_path = f"{log_dir}/{domain_name}.access_log"
                        
                        # Create empty log files if they don't exist
                        for log_path in [error_log_path, access_log_path]:
                            if not os.path.exists(log_path):
                                with open(log_path, 'w') as f:
                                    f.write('')
                                ProcessUtilities.executioner(f'chown {child_domain.master.externalApp}:{child_domain.master.externalApp} {log_path}')
                                ProcessUtilities.executioner(f'chmod 644 {log_path}')
                        
                        Upgrade.stdOut(f"✅ Fixed log configuration for {domain_name}")
                        logging.writeToFile(f'Fixed subdomain log configuration for {domain_name} during upgrade')
                        fixed_count += 1
                        
                    except Exception as e:
                        Upgrade.stdOut(f"❌ Failed to fix {domain_name}: {str(e)}")
                        logging.writeToFile(f'Error fixing subdomain logs for {domain_name} during upgrade: {str(e)}')
                
                # Restart LiteSpeed to apply changes if any were made
                if fixed_count > 0:
                    Upgrade.stdOut("Restarting LiteSpeed to apply log configuration changes...")
                    ProcessUtilities.executioner('systemctl restart lsws')
                
                Upgrade.stdOut(f"=== SUBDOMAIN LOG FIX COMPLETE ===")
                Upgrade.stdOut(f"Fixed: {fixed_count} domains")
                Upgrade.stdOut(f"Skipped: {skipped_count} domains")
                
                # Create marker file to indicate fix has been applied
                try:
                    with open(fix_marker_file, 'w') as f:
                        f.write(f"Subdomain log fix applied on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Fixed domains: {fixed_count}\n")
                        f.write(f"Skipped domains: {skipped_count}\n")
                except:
                    pass
                
            except ImportError as e:
                Upgrade.stdOut(f"⚠️  Django not available during upgrade: {str(e)}")
                Upgrade.stdOut("Subdomain log fix will be applied on next CyberPanel restart")
                
        except Exception as e:
            Upgrade.stdOut(f"❌ Error in subdomain log fix: {str(e)}")
            logging.writeToFile(f'Error in subdomain log fix during upgrade: {str(e)}')

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
    def rabbitMQMigrations():
        marker_path = '/home/cyberpanel/rabbitmq'
        rabbitmq_service_files = [
            '/usr/lib/systemd/system/rabbitmq-server.service',
            '/lib/systemd/system/rabbitmq-server.service'
        ]
        rabbitmq_binary_paths = [
            '/usr/sbin/rabbitmq-server',
            '/usr/lib/rabbitmq/bin/rabbitmq-server'
        ]

        try:
            rabbitmq_installed = any(os.path.exists(path) for path in rabbitmq_service_files + rabbitmq_binary_paths)

            if rabbitmq_installed:
                if not os.path.exists(marker_path):
                    writeToFile = open(marker_path, 'w+')
                    writeToFile.close()
                    Upgrade.stdOut('RabbitMQ detected during upgrade. Marker file created.', 0)

                Upgrade.executioner('systemctl enable rabbitmq-server', 'Enable RabbitMQ service', 0)
                Upgrade.executioner('systemctl start rabbitmq-server', 'Start RabbitMQ service', 0)
            else:
                if os.path.exists(marker_path):
                    os.remove(marker_path)
                    Upgrade.stdOut('RabbitMQ marker removed because service is not installed.', 0)
        except BaseException as msg:
            Upgrade.stdOut('RabbitMQ migration failed: ' + str(msg), 0)

    @staticmethod
    def redisMigrations():
        marker_path = '/home/cyberpanel/redis'
        redis_binary = '/usr/bin/redis-server'
        redis_service_files = [
            '/usr/lib/systemd/system/redis.service',
            '/lib/systemd/system/redis.service'
        ]

        try:
            redis_installed = os.path.exists(redis_binary) or any(os.path.exists(path) for path in redis_service_files)
            if redis_installed:
                if not os.path.exists(marker_path):
                    writeToFile = open(marker_path, 'w+')
                    writeToFile.close()
                    Upgrade.stdOut('Redis detected during upgrade. Marker file created.', 0)
                Upgrade.executioner('systemctl enable redis', 'Enable Redis service', 0)
                Upgrade.executioner('systemctl start redis', 'Start Redis service', 0)
            else:
                if os.path.exists(marker_path):
                    os.remove(marker_path)
                    Upgrade.stdOut('Redis marker removed because service is not installed.', 0)
        except BaseException as msg:
            Upgrade.stdOut('Redis migration failed: ' + str(msg), 0)

    @staticmethod
    def elasticSearchMigrations():
        marker_path = '/home/cyberpanel/elasticsearch'
        es_binary = '/usr/share/elasticsearch/bin/elasticsearch'
        es_service_files = [
            '/usr/lib/systemd/system/elasticsearch.service',
            '/lib/systemd/system/elasticsearch.service'
        ]

        try:
            es_installed = os.path.exists(es_binary) or any(os.path.exists(path) for path in es_service_files)
            if es_installed:
                if not os.path.exists(marker_path):
                    writeToFile = open(marker_path, 'w+')
                    writeToFile.close()
                    Upgrade.stdOut('Elasticsearch detected during upgrade. Marker file created.', 0)
                Upgrade.executioner('systemctl enable elasticsearch', 'Enable Elasticsearch service', 0)
                Upgrade.executioner('systemctl start elasticsearch', 'Start Elasticsearch service', 0)
            else:
                if os.path.exists(marker_path):
                    os.remove(marker_path)
                    Upgrade.stdOut('Elasticsearch marker removed because service is not installed.', 0)
        except BaseException as msg:
            Upgrade.stdOut('Elasticsearch migration failed: ' + str(msg), 0)

    @staticmethod
    def backupCriticalFiles():
        """Backup all critical configuration files before upgrade"""
        import tempfile
        backup_dir = tempfile.mkdtemp(prefix='cyberpanel_backup_')
        
        critical_files = [
            '/usr/local/CyberCP/CyberCP/settings.py',
            '/usr/local/CyberCP/.git/config',  # Git configuration
            '/usr/local/lsws/conf/httpd_config.conf',  # OpenLiteSpeed config - critical for preventing port binding failures
        ]
        
        # Also backup any custom configurations
        custom_configs = [
            '/usr/local/CyberCP/baseTemplate/static/baseTemplate/custom/',
            '/usr/local/CyberCP/public/phpmyadmin/config.inc.php',
            '/usr/local/lscp/cyberpanel/snappymail/data/_data_/',
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

            # Remove old CyberCP directory (quarantine if rmtree fails — e.g. busy files)
            if os.path.exists('CyberCP'):
                Upgrade.stdOut("Removing old CyberCP directory...")
                try:
                    shutil.rmtree('CyberCP')
                    Upgrade.stdOut("Old CyberCP directory removed successfully.")
                except OSError as e:
                    Upgrade.stdOut("rmtree failed (%s); quarantining old CyberCP..." % str(e))
                    quarantine = '/usr/local/CyberCP.legacy.%s' % int(time.time())
                    try:
                        shutil.move('CyberCP', quarantine)
                        Upgrade.stdOut("Moved old tree to %s" % quarantine)
                    except OSError as e2:
                        Upgrade.stdOut(f"Error removing or moving CyberCP directory: {str(e2)}")
                        Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)
                        return 0, 'Failed to remove or quarantine old CyberCP directory'

            # Clone the new repository (use CYBERPANEL_GIT_USER for fork, e.g. master3395)
            git_user = os.environ.get('CYBERPANEL_GIT_USER', 'usmannasir')
            upstream_user = os.environ.get('CYBERPANEL_UPSTREAM_GIT_USER', 'usmannasir')
            checkout_ok = False

            Upgrade.stdOut("Cloning fresh CyberPanel repository...")
            command = 'git clone https://github.com/%s/cyberpanel CyberCP' % git_user
            if not Upgrade.executioner(command, command, 1):
                Upgrade.stdOut("Clone failed, attempting to restore backup...")
                Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)
                return 0, 'Failed to clone CyberPanel repository'

            os.chdir('/usr/local/CyberCP')
            command = 'git checkout %s' % (branch)
            if Upgrade.executioner(command, command, 1):
                checkout_ok = True

            if not checkout_ok and git_user != upstream_user:
                Upgrade.stdOut("Branch not found on primary repo, trying upstream (%s)..." % upstream_user)
                os.chdir('/usr/local')
                if os.path.exists('CyberCP'):
                    try:
                        shutil.rmtree('CyberCP')
                    except OSError as e:
                        Upgrade.stdOut("rmtree failed (%s); quarantining..." % str(e))
                        quarantine = '/usr/local/CyberCP.legacy.%s' % int(time.time())
                        try:
                            shutil.move('CyberCP', quarantine)
                        except OSError as e2:
                            Upgrade.stdOut("Error removing CyberCP: %s" % str(e2))
                            Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)
                            return 0, 'Failed to remove CyberCP for upstream clone'
                command = 'git clone https://github.com/%s/cyberpanel CyberCP' % upstream_user
                if not Upgrade.executioner(command, command, 1):
                    Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)
                    return 0, 'Failed to clone upstream CyberPanel repository'
                os.chdir('/usr/local/CyberCP')
                command = 'git checkout %s' % (branch)
                if Upgrade.executioner(command, command, 1):
                    checkout_ok = True

            if not checkout_ok:
                Upgrade.restoreCriticalFiles(backup_dir, backed_up_files)
                return 0, 'Branch %s not found on primary or upstream repo; ensure it exists.' % branch

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

            # Fresh clone ships bin/lswsgi but cron and scripts expect /usr/local/CyberCP/bin/python (venv path removed on many installs).
            try:
                from plogical.cyberpanel_python import ensure_cyberpanel_bin_python_shim
                ensure_cyberpanel_bin_python_shim()
                Upgrade.stdOut("Ensured /usr/local/CyberCP/bin/python shim after clone.", 0)
            except BaseException as shim_err:
                Upgrade.stdOut("Warning: could not ensure CyberCP bin/python shim: %s" % str(shim_err), 0)

            return 1, None

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'installLSCPD')
            return 0, "Failed to install LSCPD"

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

                from plogical import lscpd_integrity
                if not lscpd_integrity.verify_bundled_binary(lscpdSelection):
                    Upgrade.stdOut(
                        'ERROR: lscpd binary failed integrity check; aborting install of %s'
                        % lscpdSelection
                    )
                else:
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

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'installLSCPD')
            Upgrade.stdOut("Failed to install LSCPD [installLSCPD]")

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

            command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail"
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

            for path in ('/usr/local/CyberCP/.env', '/usr/local/CyberCP/secret_key'):
                if os.path.exists(path):
                    command = "chown root:cyberpanel %s" % path
                    Upgrade.executioner(command, 'chown panel secrets', 0)
                    command = "chmod 640 %s" % path
                    Upgrade.executioner(command, 'chmod panel secrets', 0)

            backup_env = '/usr/local/CyberCP/.env.backup'
            if os.path.exists(backup_env):
                command = "chown root:root %s" % backup_env
                Upgrade.executioner(command, 'chown environment backup', 0)
                command = "chmod 600 %s" % backup_env
                Upgrade.executioner(command, 'chmod environment backup', 0)

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

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'fixPermissions')
            Upgrade.stdOut("Failed to fix permissions [fixPermissions]")

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
            # CRITICAL: Remove MariaDB-server-compat* before any MariaDB install (conflicts with 11.x)
            Upgrade.stdOut("Removing conflicting MariaDB-server-compat packages...", 1)
            try:
                # Multiple aggressive removal attempts to ensure compat package is gone
                # Step 1: Try dnf remove with allowerasing
                subprocess.run("dnf remove -y --allowerasing 'MariaDB-server-compat*' 2>/dev/null || true", shell=True, timeout=60)
                
                # Step 2: Force remove with rpm
                subprocess.run("rpm -e --nodeps MariaDB-server-compat-12.1.2-1.el9.noarch 2>/dev/null; true", shell=True, timeout=30)  # cleanup if present from previous 12.1
                
                # Step 3: Find and remove any remaining compat packages
                r = subprocess.run("rpm -qa 2>/dev/null | grep -i MariaDB-server-compat", shell=True, capture_output=True, text=True, timeout=30)
                for line in (r.stdout or "").strip().splitlines():
                    pkg = (line.strip().split() or [""])[0]
                    if pkg and "MariaDB-server-compat" in pkg:
                        Upgrade.stdOut(f"Force removing remaining compat package: {pkg}", 1)
                        subprocess.run(["rpm", "-e", "--nodeps", pkg], timeout=30)
                
                # Step 4: Verify removal and exclude from future installs
                r = subprocess.run("rpm -qa 2>/dev/null | grep -i MariaDB-server-compat", shell=True, capture_output=True, text=True, timeout=30)
                if r.stdout.strip():
                    Upgrade.stdOut(f"Warning: Some compat packages still present: {r.stdout.strip()}", 0)
                    # Add to dnf exclude to prevent reinstallation
                    subprocess.run("dnf config-manager --setopt exclude='MariaDB-server-compat*' --save 2>/dev/null || true", shell=True, timeout=30)
                else:
                    Upgrade.stdOut("Successfully removed all MariaDB-server-compat packages", 1)
            except Exception as e:
                Upgrade.stdOut("Warning: compat cleanup: " + str(e), 0)

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
            
            # Install MariaDB from official repository (version from /etc/cyberpanel/mariadb_version or default 11.8)
            # Accept any major.minor supported by mariadb_repo_setup (10.3-10.11, 11.0-11.8, 12.0-12.x); safe regex to avoid injection
            mariadb_ver = "11.8"
            try:
                mariadb_version_file = "/etc/cyberpanel/mariadb_version"
                if os.path.isfile(mariadb_version_file):
                    with open(mariadb_version_file, "r") as f:
                        raw = (f.read() or "").strip()
                    if raw:
                        import re
                        m = re.match(r'^(\d+)\.(\d+)(?:\.\d+)*$', raw)
                        if m:
                            major, minor = int(m.group(1)), int(m.group(2))
                            if (major == 10 and 3 <= minor <= 11) or (major == 11 and 0 <= minor <= 8) or (major == 12 and 0 <= minor <= 99):
                                mariadb_ver = "%d.%d" % (major, minor)
            except Exception:
                pass
            Upgrade.stdOut("Setting up official MariaDB %s repository..." % mariadb_ver, 1)
            command = "curl -sS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | bash -s -- --mariadb-server-version='%s'" % mariadb_ver
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                Upgrade.stdOut(f"Warning: MariaDB repo setup failed: {result.stderr}", 0)
            
            # Install MariaDB packages with exclude to prevent compat package conflicts
            Upgrade.stdOut("Installing MariaDB packages...", 1)
            mariadb_packages = "MariaDB-server MariaDB-client MariaDB-backup MariaDB-devel"
            # Use --exclude to prevent compat package from being installed
            command = f"dnf install -y --exclude='MariaDB-server-compat*' {mariadb_packages}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                # Check if it's a compat package conflict
                error_output = result.stderr + result.stdout
                if "MariaDB-server-compat" in error_output or "conflicts" in error_output.lower():
                    Upgrade.stdOut("Compat package conflict detected, trying with --allowerasing...", 1)
                    command = f"dnf install -y --allowerasing --exclude='MariaDB-server-compat*' {mariadb_packages}"
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        Upgrade.stdOut(f"Error: MariaDB installation failed: {result.stderr}", 0)
                        return False
                else:
                    Upgrade.stdOut(f"Warning: MariaDB installation issues: {result.stderr}", 0)
                    return False
            
            # Verify MariaDB was installed successfully
            if not os.path.exists('/usr/bin/mysql') and not os.path.exists('/usr/bin/mariadb'):
                Upgrade.stdOut("Error: MariaDB binaries not found after installation", 0)
                return False
            
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
            
            # Post-install guard: preUpgrade can leave server/client packages removed
            ensure_script = "/usr/local/CyberCP/CPScripts/ensure-mariadb-server.sh"
            if os.path.isfile(ensure_script):
                try:
                    result = subprocess.run(["bash", ensure_script], capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        Upgrade.stdOut("ensure-mariadb-server.sh completed", 1)
                    else:
                        Upgrade.stdOut(f"Warning: ensure-mariadb-server.sh failed: {result.stderr}", 0)
                except Exception as guard_err:
                    Upgrade.stdOut(f"Warning: ensure-mariadb-server.sh error: {guard_err}", 0)

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
                    if 'release 10' in content:
                        Upgrade.stdOut("AlmaLinux 10 detected - checking available PHP versions", 1)
                        php_versions = ['81', '82', '83', '84', '85']
                    elif 'release 9' in content:
                        Upgrade.stdOut("AlmaLinux 9 detected - checking available PHP versions", 1)
                        php_versions = ['74', '80', '81', '82', '83', '84', '85']
                    else:
                        php_versions = ['71', '72', '73', '74', '80', '81', '82', '83', '84', '85']
            except:
                php_versions = ['71', '72', '73', '74', '80', '81', '82', '83', '84', '85']
        else:
            # Check other OS versions
            os_info = Upgrade.findOperatingSytem()
            if os_info in [Ubuntu24, CENTOS8, Debian13]:
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
        """Fix LiteSpeed configuration issues by creating missing files and fixing permissions"""
        try:
            Upgrade.stdOut("Checking and fixing LiteSpeed configuration...", 1)
            
            # Check if LiteSpeed is installed
            if not os.path.exists('/usr/local/lsws'):
                Upgrade.stdOut("LiteSpeed not found at /usr/local/lsws", 0)
                return
            
            # Fix LiteSpeed permissions first
            Upgrade.stdOut("Fixing LiteSpeed permissions...", 1)
            litespeed_dirs = ['/usr/local/lsws', '/usr/local/lscp', '/usr/local/CyberCP']
            for directory in litespeed_dirs:
                if os.path.exists(directory):
                    command = f'chown -R lscpd:lscpd {directory}'
                    Upgrade.executioner(command, f'Fix ownership for {directory}', 0)
                    
                    command = f'chmod -R 755 {directory}'
                    Upgrade.executioner(command, f'Fix permissions for {directory}', 0)
            
            # Create missing configuration files
            config_files = [
                "/usr/local/lsws/conf/httpd_config.xml",
                "/usr/local/lsws/conf/httpd.conf",
                "/usr/local/lscp/conf/httpd_config.xml",
                "/usr/local/lscp/conf/httpd.conf"
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
                    
                    # Set proper permissions
                    os.chmod(config_file, 0o644)
                    command = f'chown lscpd:lscpd {config_file}'
                    Upgrade.executioner(command, f'Fix config ownership: {config_file}', 0)
                    
                    Upgrade.stdOut(f"Created minimal config: {config_file}", 1)
                else:
                    Upgrade.stdOut(f"LiteSpeed config exists: {config_file}", 1)
            
            # Create PHP socket directory if it doesn't exist
            php_sock_dir = '/var/run/php/'
            if not os.path.exists(php_sock_dir):
                Upgrade.stdOut("Creating PHP socket directory...", 1)
                os.makedirs(php_sock_dir, exist_ok=True)
                command = f'chmod 755 {php_sock_dir}'
                Upgrade.executioner(command, 'Fix PHP socket directory permissions', 0)
                
                # Set ownership based on distribution
                osType = Upgrade.decideDistro()
                if osType in [Upgrade.centos, Upgrade.cent8, Upgrade.cloudlinux]:
                    command = f'chown apache:apache {php_sock_dir}'
                else:
                    command = f'chown www-data:www-data {php_sock_dir}'
                Upgrade.executioner(command, 'Fix PHP socket directory ownership', 0)
            
            # Restart LiteSpeed services to apply changes
            Upgrade.stdOut("Restarting LiteSpeed services...", 1)
            litespeed_services = ['lsws', 'lscpd']
            for service in litespeed_services:
                command = f'systemctl restart {service}'
                Upgrade.executioner(command, f'Restart {service}', 0)
                
                command = f'systemctl enable {service}'
                Upgrade.executioner(command, f'Enable {service}', 0)
                
                # Verify service is running
                command = f'systemctl is-active {service}'
                try:
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    if result.stdout.strip() == 'active':
                        Upgrade.stdOut(f"{service} is running successfully", 1)
                    else:
                        Upgrade.stdOut(f"{service} status: {result.stdout.strip()}", 0)
                except:
                    Upgrade.stdOut(f"Could not verify {service} status", 0)
                    
        except Exception as e:
            Upgrade.stdOut(f"Error fixing LiteSpeed config: {str(e)}", 0)

    @staticmethod
    def fixServiceConfiguration():
        """Comprehensive service configuration fix for common 503 error causes"""
        try:
            Upgrade.stdOut("Applying comprehensive service configuration fixes...", 1)
            
            # Upgrade pip first for better package compatibility
            Upgrade.upgradePip()
            
            # Fix PowerDNS configuration
            Upgrade.fixPowerDNSConfig()
            
            # Fix Pure-FTPd configuration
            Upgrade.fixPureFTPdConfig()
            
            # Fix database connectivity
            Upgrade.fixDatabaseConnectivity()
            
            # Fix PHP-FPM services
            Upgrade.fixPHPFPMServices()
            
            # Final service restart and verification
            Upgrade.restartAndVerifyServices()
            
        except Exception as e:
            Upgrade.stdOut(f"Error in service configuration fix: {str(e)}", 0)

    @staticmethod
    def upgradePip():
        """Upgrade pip to latest version for better package compatibility"""
        try:
            Upgrade.stdOut("Upgrading pip to latest version...", 1)
            python_path = Upgrade._python_for_manage()
            if not python_path:
                Upgrade.stdOut("No Python executable found for pip upgrade", 0)
                return False
            
            # Upgrade pip and essential packages
            upgrade_command = f"{python_path} -m pip install --upgrade pip setuptools wheel packaging"
            result = Upgrade.executioner(upgrade_command, "Upgrade pip", 0)
            
            if result == 1:
                Upgrade.stdOut("pip upgraded successfully", 1)
                return True
            else:
                Upgrade.stdOut("WARNING: pip upgrade failed, continuing with current version", 0)
                return False
                
        except Exception as e:
            Upgrade.stdOut(f"Error upgrading pip: {str(e)}", 0)
            return False

    @staticmethod
    def fixPowerDNSConfig():
        """Fix PowerDNS configuration issues"""
        try:
            Upgrade.stdOut("Fixing PowerDNS configuration...", 1)
            
            # Check if PowerDNS is installed
            if not os.path.exists('/home/cyberpanel/powerdns'):
                Upgrade.stdOut("PowerDNS not enabled, skipping...", 1)
                return
            
            # Determine correct service name
            pdns_service = None
            result = subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True)
            if 'pdns.service' in result.stdout:
                pdns_service = 'pdns'
            elif 'powerdns.service' in result.stdout:
                pdns_service = 'powerdns'
            
            if not pdns_service:
                Upgrade.stdOut("PowerDNS service not found", 0)
                return
            
            # Fix PowerDNS configuration files
            config_files = ['/etc/pdns/pdns.conf', '/etc/powerdns/pdns.conf']
            for config_file in config_files:
                if os.path.exists(config_file):
                    Upgrade.stdOut(f"Configuring PowerDNS: {config_file}", 1)
                    
                    # Read existing content
                    with open(config_file, 'r') as f:
                        content = f.read()
                    
                    # Add missing configuration if not present
                    if 'gmysql-password=' not in content:
                        content += '\ngmysql-password=cyberpanel\n'
                    if 'launch=' not in content:
                        content += 'launch=gmysql\n'
                    
                    # Write back the configuration
                    with open(config_file, 'w') as f:
                        f.write(content)
                    
                    # Set proper permissions
                    os.chmod(config_file, 0o644)
                    command = f'chown root:root {config_file}'
                    Upgrade.executioner(command, f'Fix PowerDNS config ownership', 0)
                    break
            
            # Restart PowerDNS service
            command = f'systemctl restart {pdns_service}'
            Upgrade.executioner(command, f'Restart PowerDNS', 0)
            
            command = f'systemctl enable {pdns_service}'
            Upgrade.executioner(command, f'Enable PowerDNS', 0)
            
            # Verify service is running
            command = f'systemctl is-active {pdns_service}'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.stdout.strip() == 'active':
                Upgrade.stdOut("PowerDNS is running successfully", 1)
            else:
                Upgrade.stdOut(f"PowerDNS status: {result.stdout.strip()}", 0)
                
        except Exception as e:
            Upgrade.stdOut(f"Error fixing PowerDNS config: {str(e)}", 0)

    @staticmethod
    def fixPureFTPdConfig():
        """Fix Pure-FTPd configuration issues"""
        try:
            Upgrade.stdOut("Fixing Pure-FTPd configuration...", 1)
            
            # Check if Pure-FTPd is installed
            if not os.path.exists('/home/cyberpanel/pureftpd'):
                Upgrade.stdOut("Pure-FTPd not enabled, skipping...", 1)
                return
            
            # Determine correct service name
            ftp_service = None
            result = subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True)
            if 'pure-ftpd.service' in result.stdout:
                ftp_service = 'pure-ftpd'
            elif 'pureftpd.service' in result.stdout:
                ftp_service = 'pureftpd'
            
            if not ftp_service:
                Upgrade.stdOut("Pure-FTPd service not found", 0)
                return
            
            # Fix Pure-FTPd configuration files
            config_files = ['/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/db/mysql.conf']
            for config_file in config_files:
                if os.path.exists(config_file):
                    Upgrade.stdOut(f"Configuring Pure-FTPd: {config_file}", 1)
                    
                    # Fix MySQL password configuration
                    command = f"sed -i 's/MYSQLPassword.*/MYSQLPassword cyberpanel/' {config_file}"
                    Upgrade.executioner(command, f'Fix Pure-FTPd MySQL password', 0)
                    
                    # Fix MySQL crypt method for Ubuntu 24.04 compatibility
                    command = f"sed -i 's/MYSQLCrypt md5/MYSQLCrypt crypt/g' {config_file}"
                    Upgrade.executioner(command, f'Fix Pure-FTPd MySQL crypt method', 0)
                    
                    # Set proper permissions
                    os.chmod(config_file, 0o644)
                    command = f'chown root:root {config_file}'
                    Upgrade.executioner(command, f'Fix Pure-FTPd config ownership', 0)
            
            # Restart Pure-FTPd service
            command = f'systemctl restart {ftp_service}'
            Upgrade.executioner(command, f'Restart Pure-FTPd', 0)
            
            command = f'systemctl enable {ftp_service}'
            Upgrade.executioner(command, f'Enable Pure-FTPd', 0)
            
            # Verify service is running
            command = f'systemctl is-active {ftp_service}'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.stdout.strip() == 'active':
                Upgrade.stdOut("Pure-FTPd is running successfully", 1)
            else:
                Upgrade.stdOut(f"Pure-FTPd status: {result.stdout.strip()}", 0)
                
        except Exception as e:
            Upgrade.stdOut(f"Error fixing Pure-FTPd config: {str(e)}", 0)

    @staticmethod
    def fixDatabaseConnectivity():
        """Fix database connectivity issues"""
        try:
            Upgrade.stdOut("Fixing database connectivity...", 1)
            
            # Determine database service name
            db_service = None
            result = subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True)
            if 'mariadb.service' in result.stdout:
                db_service = 'mariadb'
            elif 'mysql.service' in result.stdout:
                db_service = 'mysql'
            elif 'mysqld.service' in result.stdout:
                db_service = 'mysqld'
            
            if not db_service:
                Upgrade.stdOut("Database service not found", 0)
                return
            
            # Ensure database service is running
            command = f'systemctl restart {db_service}'
            Upgrade.executioner(command, f'Restart database service', 0)
            
            command = f'systemctl enable {db_service}'
            Upgrade.executioner(command, f'Enable database service', 0)
            
            # Wait for database to be ready
            Upgrade.stdOut("Waiting for database to be ready...", 1)
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    result = subprocess.run(['mysqladmin', 'ping', '-h', 'localhost', '--silent'], 
                                          capture_output=True)
                    if result.returncode == 0:
                        Upgrade.stdOut("Database is ready", 1)
                        break
                except:
                    pass
                time.sleep(2)
            
            # Ensure cyberpanel database exists (prefer mariadb CLI; mysql is deprecated)
            try:
                _mdb = shutil.which('mariadb') or 'mysql'
                result = subprocess.run([_mdb, '-e', 'USE cyberpanel;'], capture_output=True)
                if result.returncode != 0:
                    Upgrade.stdOut("Creating cyberpanel database...", 1)
                    commands = [
                        _mdb + ' -e "CREATE DATABASE IF NOT EXISTS cyberpanel;"',
                        _mdb + ' -e "CREATE USER IF NOT EXISTS \'cyberpanel\'@\'localhost\' IDENTIFIED BY \'cyberpanel\';"',
                        _mdb + ' -e "GRANT ALL PRIVILEGES ON cyberpanel.* TO \'cyberpanel\'@\'localhost\';"',
                        _mdb + ' -e "FLUSH PRIVILEGES;"'
                    ]
                    for cmd in commands:
                        Upgrade.executioner(cmd, 'Setup cyberpanel database', 0)
            except:
                Upgrade.stdOut("Could not verify cyberpanel database", 0)
                
        except Exception as e:
            Upgrade.stdOut(f"Error fixing database connectivity: {str(e)}", 0)

    @staticmethod
    def fixPHPFPMServices():
        """Fix PHP-FPM services"""
        try:
            Upgrade.stdOut("Fixing PHP-FPM services...", 1)
            
            # Get available PHP versions
            php_versions = Upgrade.get_available_php_versions()
            
            for version in php_versions:
                # Determine FPM service name based on distribution
                osType = Upgrade.decideDistro()
                if osType in [Upgrade.centos, Upgrade.cent8, Upgrade.cloudlinux]:
                    fpm_service = f'php{version}-php-fpm'
                else:
                    fpm_service = f'php{version}-fpm'
                
                # Check if service exists and restart it
                result = subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True)
                if f'{fpm_service}.service' in result.stdout:
                    Upgrade.stdOut(f"Restarting PHP-FPM {version}...", 1)
                    command = f'systemctl restart {fpm_service}'
                    Upgrade.executioner(command, f'Restart PHP-FPM {version}', 0)
                    
                    command = f'systemctl enable {fpm_service}'
                    Upgrade.executioner(command, f'Enable PHP-FPM {version}', 0)
                    
                    # Verify service is running
                    command = f'systemctl is-active {fpm_service}'
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    if result.stdout.strip() == 'active':
                        Upgrade.stdOut(f"PHP-FPM {version} is running", 1)
                    else:
                        Upgrade.stdOut(f"PHP-FPM {version} status: {result.stdout.strip()}", 0)
                        
        except Exception as e:
            Upgrade.stdOut(f"Error fixing PHP-FPM services: {str(e)}", 0)

    @staticmethod
    def restartAndVerifyServices():
        """Restart and verify all critical services"""
        try:
            Upgrade.stdOut("Restarting and verifying critical services...", 1)
            
            # Reload systemd daemon
            command = 'systemctl daemon-reload'
            Upgrade.executioner(command, 'Reload systemd daemon', 0)
            
            # Restart critical services in order
            critical_services = ['lsws', 'lscpd']
            all_services_ok = True
            
            for service in critical_services:
                # Check if service exists before trying to manage it
                check_command = f'systemctl list-unit-files | grep -q "{service}.service"'
                result = subprocess.run(check_command, shell=True, capture_output=True)
                
                if result.returncode != 0:
                    Upgrade.stdOut(f"Service {service} not found, skipping management", 1)
                    continue
                
                Upgrade.stdOut(f"Restarting {service}...", 1)
                command = f'systemctl restart {service}'
                Upgrade.executioner(command, f'Restart {service}', 0)
                
                command = f'systemctl enable {service}'
                Upgrade.executioner(command, f'Enable {service}', 0)
                
                # Verify service is running
                command = f'systemctl is-active {service}'
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.stdout.strip() == 'active':
                    Upgrade.stdOut(f"✓ {service} is running successfully", 1)
                else:
                    Upgrade.stdOut(f"✗ {service} is not running (status: {result.stdout.strip()})", 0)
                    all_services_ok = False
            
            if all_services_ok:
                Upgrade.stdOut("All critical services are running successfully!", 1)
                Upgrade.stdOut("CyberPanel should now be accessible at https://your-server-ip:8090", 1)
                Upgrade.ensureCyberPanelPhpmyadminOls()
            else:
                Upgrade.stdOut("Some critical services are not running properly", 0)
                Upgrade.stdOut("Please check the logs and consider a server restart", 0)
                
        except Exception as e:
            Upgrade.stdOut(f"Error in service verification: {str(e)}", 0)

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
                    if version in ['74']:
                        # PHP 7.4 only (legacy support) with specific extensions
                        if Upgrade.installedOutput.find(f'lsphp{version}') == -1:
                            extensions = ['json', 'xmlrpc', 'xml', 'tidy', 'soap', 'snmp', 'recode', 'pspell', 'process', 'pgsql', 'pear', 'pdo', 'opcache', 'odbc', 'mysqlnd', 'mcrypt', 'mbstring', 'ldap', 'intl', 'imap', 'gmp', 'gd', 'enchant', 'dba', 'common', 'bcmath']
                            package_list = f"lsphp{version} " + " ".join([f"lsphp{version}-{ext}" for ext in extensions])
                            command = f"yum install -y {package_list}"
                            Upgrade.executioner(command, f'Install PHP {version}', 0)
                    elif version in ['80', '81', '82', '83', '84', '85']:
                        # PHP 8.x versions (including 8.5 beta)
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
            Upgrade.executioner(command, 'Install PHP 7.x', 0)

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

        command = "mkdir -p /usr/local/CyberCP/data"
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

            if Upgrade.FindOperatingSytem() == CENTOS8 or Upgrade.FindOperatingSytem() == openEuler22 or Upgrade.FindOperatingSytem() == openEuler20:

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

                command = 'yum makecache -y'
                Upgrade.executioner(command, 0)
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
            elif Upgrade.FindOperatingSytem() == Ubuntu20 or Upgrade.FindOperatingSytem() == Ubuntu22 or Upgrade.FindOperatingSytem() == Ubuntu24 or Upgrade.FindOperatingSytem() == Debian11 or Upgrade.FindOperatingSytem() == Debian12 or Upgrade.FindOperatingSytem() == Debian13:

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

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'upgradeDovecot')
            Upgrade.stdOut("Failed to upgrade Dovecot [upgradeDovecot]")

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

            try:
                from plogical.cyberpanel_python import ensure_cyberpanel_bin_python_shim
                ensure_cyberpanel_bin_python_shim()
            except BaseException:
                pass

            if data.find('findBWUsage') == -1:
                # Randomize acme.sh and renew.py cron schedules to avoid traffic spikes to Let's Encrypt
                # Each installation gets a random day (0-6 Sun-Sat), hour, and minute to spread load
                acme_hour = random.randint(0, 23)
                acme_minute = random.randint(0, 59)
                renew_weekday = random.randint(0, 6)  # 0=Sun, 1=Mon, ..., 6=Sat
                renew_hour = random.randint(0, 23)
                renew_minute = random.randint(0, 59)
                
                content = """
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py >/dev/null 2>&1
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup >/dev/null 2>&1
0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup >/dev/null 2>&1
0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py >/dev/null 2>&1
%d %d * * %d /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py >/dev/null 2>&1
%d %d * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null
0 1 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py ssl_reconcile --all >/dev/null 2>&1
*/3 * * * * if ! find /home/*/public_html/ -maxdepth 2 -type f -newer /usr/local/lsws/cgid -name '.htaccess' -exec false {} +; then /usr/local/lsws/bin/lswsctrl restart; fi
* * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py run_scheduled_scans >/usr/local/lscp/logs/scheduled_scans.log 2>&1
"""

                writeToFile = open(cronPath, 'w')
                writeToFile.write(content % (renew_minute, renew_hour, renew_weekday, acme_minute, acme_hour))
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

            # PDNS service watchdog (catalog-zone schema bug + general
            # restart-loop detector). See plogical/pdnsHealthCheck.py.
            if data.find('pdnsHealthCheck.py') == -1:
                content = """
*/5 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/pdnsHealthCheck.py >/dev/null 2>&1
"""
                writeToFile = open(cronPath, 'a')
                writeToFile.write(content)
                writeToFile.close()


        else:
            try:
                from plogical.cyberpanel_python import ensure_cyberpanel_bin_python_shim
                ensure_cyberpanel_bin_python_shim()
            except BaseException:
                pass
            # Randomize acme.sh and renew.py cron schedules to avoid traffic spikes to Let's Encrypt
            # Each installation gets a random day (0-6 Sun-Sat), hour, and minute to spread load
            acme_hour = random.randint(0, 23)
            acme_minute = random.randint(0, 59)
            renew_weekday = random.randint(0, 6)  # 0=Sun, 1=Mon, ..., 6=Sat
            renew_hour = random.randint(0, 23)
            renew_minute = random.randint(0, 59)
            
            content = """
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py >/dev/null 2>&1
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup >/dev/null 2>&1
0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup >/dev/null 2>&1
0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py >/dev/null 2>&1
%d %d * * %d /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py >/dev/null 2>&1
%d %d * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null
0 1 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py ssl_reconcile --all >/dev/null 2>&1
0 0 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Daily
0 0 * * 0 /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Weekly
* * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py run_scheduled_scans >/usr/local/lscp/logs/scheduled_scans.log 2>&1
*/5 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/pdnsHealthCheck.py >/dev/null 2>&1
""" % (renew_minute, renew_hour, renew_weekday, acme_minute, acme_hour)
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
            try:
                effective_admin_status = int(json.loads(acl.config).get('adminStatus', 0) or 0)
            except (TypeError, ValueError, json.JSONDecodeError):
                effective_admin_status = 0
            if acl.adminStatus != effective_admin_status:
                acl.adminStatus = effective_admin_status
            acl.save()

    @staticmethod
    def CreateMissingPoolsforFPM():
        """
        Create missing PHP-FPM pool configurations for all PHP versions.
        This function ensures all PHP versions have proper pool configurations
        to prevent ImunifyAV/Imunify360 installation failures.
        """
        try:
            # Detect OS and set paths
            CentOSPath = '/etc/redhat-release'
            
            if os.path.exists(CentOSPath):
                # CentOS/RHEL/CloudLinux paths
                serverRootPath = '/etc/httpd'
                configBasePath = '/etc/httpd/conf.d/'
                sockPath = '/var/run/php-fpm/'
                runAsUser = 'apache'
                group = 'nobody'
                
                # Define PHP pool paths for CentOS
                php_paths = {
                    '5.4': '/opt/remi/php54/root/etc/php-fpm.d/',
                    '5.5': '/opt/remi/php55/root/etc/php-fpm.d/',
                    '5.6': '/etc/opt/remi/php56/php-fpm.d/',
                    '7.0': '/etc/opt/remi/php70/php-fpm.d/',
                    '7.1': '/etc/opt/remi/php71/php-fpm.d/',
                    '7.2': '/etc/opt/remi/php72/php-fpm.d/',
                    '7.3': '/etc/opt/remi/php73/php-fpm.d/',
                    '7.4': '/etc/opt/remi/php74/php-fpm.d/',
                    '8.0': '/etc/opt/remi/php80/php-fpm.d/',
                    '8.1': '/etc/opt/remi/php81/php-fpm.d/',
                    '8.2': '/etc/opt/remi/php82/php-fpm.d/',
                    '8.3': '/etc/opt/remi/php83/php-fpm.d/',
                    '8.4': '/etc/opt/remi/php84/php-fpm.d/',
                    '8.5': '/etc/opt/remi/php85/php-fpm.d/'
                }
            else:
                # Ubuntu/Debian paths
                serverRootPath = '/etc/apache2'
                configBasePath = '/etc/apache2/sites-enabled/'
                sockPath = '/var/run/php/'
                runAsUser = 'www-data'
                group = 'nogroup'
                
                # Define PHP pool paths for Ubuntu
                php_paths = {
                    '5.4': '/etc/php/5.4/fpm/pool.d/',
                    '5.5': '/etc/php/5.5/fpm/pool.d/',
                    '5.6': '/etc/php/5.6/fpm/pool.d/',
                    '7.0': '/etc/php/7.0/fpm/pool.d/',
                    '7.1': '/etc/php/7.1/fpm/pool.d/',
                    '7.2': '/etc/php/7.2/fpm/pool.d/',
                    '7.3': '/etc/php/7.3/fpm/pool.d/',
                    '7.4': '/etc/php/7.4/fpm/pool.d/',
                    '8.0': '/etc/php/8.0/fpm/pool.d/',
                    '8.1': '/etc/php/8.1/fpm/pool.d/',
                    '8.2': '/etc/php/8.2/fpm/pool.d/',
                    '8.3': '/etc/php/8.3/fpm/pool.d/',
                    '8.4': '/etc/php/8.4/fpm/pool.d/',
                    '8.5': '/etc/php/8.5/fpm/pool.d/'
                }

            # Check if server root exists
            if not os.path.exists(serverRootPath):
                logging.CyberCPLogFileWriter.writeToFile(f'Server root path not found: {serverRootPath}')
                return 1

            # Create pool configurations for all PHP versions
            for version, pool_path in php_paths.items():
                if os.path.exists(pool_path):
                    www_conf = os.path.join(pool_path, 'www.conf')
                    
                    # Skip if www.conf already exists
                    if os.path.exists(www_conf):
                        logging.CyberCPLogFileWriter.writeToFile(f'PHP {version} pool config already exists: {www_conf}')
                        continue
                    
                    # Create the pool configuration
                    pool_name = f'php{version.replace(".", "")}default'
                    sock_name = f'php{version}-fpm.sock'
                    
                    content = f'''[{pool_name}]
user = {runAsUser}
group = {runAsUser}
listen = {sockPath}{sock_name}
listen.owner = {runAsUser}
listen.group = {group}
listen.mode = 0660
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
pm.max_requests = 1000
pm.status_path = /status
ping.path = /ping
ping.response = pong
request_terminate_timeout = 300
request_slowlog_timeout = 10
slowlog = /var/log/php{version}-fpm-slow.log
'''
                    
                    try:
                        # Write the configuration file
                        with open(www_conf, 'w') as f:
                            f.write(content)
                        
                        # Set proper permissions
                        os.chown(www_conf, 0, 0)  # root:root
                        os.chmod(www_conf, 0o644)
                        
                        logging.CyberCPLogFileWriter.writeToFile(f'Created PHP {version} pool config: {www_conf}')
                        
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f'Error creating PHP {version} pool config: {str(e)}')
                else:
                    logging.CyberCPLogFileWriter.writeToFile(f'PHP {version} pool directory not found: {pool_path}')

            # Restart PHP-FPM services to apply configurations
            Upgrade.restartPHPFPMServices()
            
            return 0
            
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error in CreateMissingPoolsforFPM: {str(e)}')
            return 1

    @staticmethod
    def restartPHPFPMServices():
        """
        Restart all PHP-FPM services to apply new pool configurations.
        This ensures that ImunifyAV/Imunify360 installation will work properly.
        """
        try:
            # Define all possible PHP versions
            php_versions = ['5.4', '5.5', '5.6', '7.0', '7.1', '7.2', '7.3', '7.4', '8.0', '8.1', '8.2', '8.3', '8.4', '8.5']
            
            restarted_count = 0
            total_count = 0
            
            for version in php_versions:
                service_name = f'php{version}-fpm'
                
                # Check if service exists
                try:
                    result = subprocess.run(['systemctl', 'list-unit-files', service_name], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and service_name in result.stdout:
                        total_count += 1
                        
                        # Restart the service
                        restart_result = subprocess.run(['systemctl', 'restart', service_name], 
                                                      capture_output=True, text=True, timeout=30)
                        
                        if restart_result.returncode == 0:
                            # Check if service is actually running
                            status_result = subprocess.run(['systemctl', 'is-active', service_name], 
                                                         capture_output=True, text=True, timeout=10)
                            if status_result.returncode == 0 and 'active' in status_result.stdout:
                                restarted_count += 1
                                logging.CyberCPLogFileWriter.writeToFile(f'Successfully restarted {service_name}')
                            else:
                                logging.CyberCPLogFileWriter.writeToFile(f'Warning: {service_name} restarted but not active')
                        else:
                            logging.CyberCPLogFileWriter.writeToFile(f'Failed to restart {service_name}: {restart_result.stderr}')
                            
                except subprocess.TimeoutExpired:
                    logging.CyberCPLogFileWriter.writeToFile(f'Timeout restarting {service_name}')
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Error restarting {service_name}: {str(e)}')
            
            logging.CyberCPLogFileWriter.writeToFile(f'PHP-FPM restart summary: {restarted_count}/{total_count} services restarted successfully')
            return restarted_count, total_count
            
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error in restartPHPFPMServices: {str(e)}')
            return 0, 0

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
            
            # Remove existing PHP symlink if it exists (os.path.lexists catches broken symlinks too)
            if os.path.lexists('/usr/bin/php'):
                os.remove('/usr/bin/php')

            # Create symlink to selected PHP version
            command = f'ln -s /usr/local/lsws/lsphp{selected_php}/bin/php /usr/bin/php'
            Upgrade.executioner(command, f'Setup PHP Symlink to {selected_php}', 0)

            Upgrade.stdOut(f"PHP symlink updated to PHP {selected_php} successfully.")

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'setupPHPSymlink')
            Upgrade.stdOut('[ERROR] Failed to setup PHP symlink [setupPHPSymlink]')
            return 0

        return 1

    @staticmethod
    def upgrade(branch):

        if branch.find('SoftUpgrade') > -1:
            Upgrade.SoftUpgrade = 1
            branch = branch.split(',')[1]

        Upgrade._upgrade_init_files_and_progress()
        Upgrade.write_upgrade_progress(6)

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

        Upgrade.write_upgrade_progress(12, monotonic=True)

        # command = 'systemctl stop cpssh'
        # Upgrade.executioner(command, 'fix csf if there', 0)

        ## Add LSPHP7.4 TO LSWS Ent configs

        if not os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            # This is Enterprise LSWS
            if os.path.exists('httpd_config.xml'):
                os.remove('httpd_config.xml')

            command = 'wget https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/install/litespeed/httpd_config.xml'
            Upgrade.executioner(command, command, 0)
            # os.remove('/usr/local/lsws/conf/httpd_config.xml')
            # shutil.copy('httpd_config.xml', '/usr/local/lsws/conf/httpd_config.xml')
        else:
            Upgrade.stdOut(
                "Detected OpenLiteSpeed; package upgrade and optional binary overlay run in a later step (repo first).",
                0
            )

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

        # OpenLiteSpeed: LiteSpeed repo and package upgrade first; CyberPanel overlay only if below MIN_OFFICIAL_OLS
        Upgrade.upgrade_openlitespeed_repo_first_then_optional_overlay()

        ##

        versionNumbring = Upgrade.downloadLink()

        if os.path.exists('/usr/local/CyberPanel.' + versionNumbring):
            os.remove('/usr/local/CyberPanel.' + versionNumbring)

        ##

        # execPath = "sudo /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/csf.py"
        # execPath = execPath + " removeCSF"
        # Upgrade.executioner(execPath, 'fix csf if there', 0)

        Upgrade.repairLocalCyberPanelDatabaseAccess()

        clone_attempts = int(os.environ.get('CYBERPANEL_UPGRADE_CLONE_ATTEMPTS', '2'))
        if clone_attempts < 1:
            clone_attempts = 1
        download_ok = False
        download_err = None
        for attempt in range(1, clone_attempts + 1):
            ok, download_err = Upgrade.downloadAndUpgrade(versionNumbring, branch)
            if ok:
                download_ok = True
                break
            Upgrade.stdOut(
                'downloadAndUpgrade failed (attempt %d/%d): %s'
                % (attempt, clone_attempts, download_err or 'unknown'), 0)
            if attempt < clone_attempts:
                Upgrade.stdOut('Retrying full CyberPanel tree replacement in 5 seconds...', 0)
                time.sleep(5)
        if not download_ok:
            Upgrade.stdOut(
                'CRITICAL: CyberPanel code update failed after %d attempt(s): %s. '
                'The panel was not replaced with the new branch. Check logs and disk permissions on /usr/local.'
                % (clone_attempts, download_err or 'unknown'), 0)
            if Upgrade.SoftUpgrade == 0:
                Upgrade.executioner('systemctl start lscpd', 'Start LSCPD after failed code update', 0)
            sys.exit(1)

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
        Upgrade.homeDirectoryMigrations()
        Upgrade.rotateInvalidAPITokens()

        ## Put function here to update custom ACLs

        Upgrade.UpdateConfigOfCustomACL()

        Upgrade.s3BackupMigrations()
        Upgrade.containerMigrations()
        Upgrade.manageServiceMigrations()
        Upgrade.pdnsSchemaMigrations()
        Upgrade.firewallMigrations()
        Upgrade.repairDovecot24SNIPaths()
        Upgrade.fixMailTLS()
        Upgrade.setupWebmail()
        Upgrade.setupSieve()
        Upgrade.enableServices()
        Upgrade.elasticSearchMigrations()
        Upgrade.redisMigrations()
        Upgrade.rabbitMQMigrations()

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
        
        # Fix comprehensive service configuration issues (503 error prevention)
        Upgrade.fixServiceConfiguration()
        
        # Fix subdomain log configurations
        Upgrade.fixSubdomainLogConfigurations()

        ### General migrations are not needed any more

        # Upgrade.GeneralMigrations()
        
        # Fix baseTemplate migrations for AlmaLinux 9 and Ubuntu 24 compatibility
        Upgrade.fixBaseTemplateMigrations()

        # Upgrade.p3()

        ## Also disable email service upgrade

        # if os.path.exists(postfixPath):
        #     Upgrade.upgradeDovecot()

        ## Upgrade version

        Upgrade.fixPermissions()

        try:
            from plogical.installUtilities import installUtilities
            installUtilities.installLswsCyberpanelConfPermsHook()
            installUtilities.repairHttpdMisplacedListenerMaps()
        except Exception as msg:
            Upgrade.stdOut('WARNING: LSWS preview/permission repair skipped: %s' % str(msg), 0)

        Upgrade.ensure_gunicorn_in_cybercp_venv()
        Upgrade.verify_cybercp_venv_core_modules()

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

                from plogical.imunify_integration import (
                    detect_imunify_product,
                    ensure_clscripts_executable,
                    integration_conf_needs_repair,
                    repair_integration_conf,
                )

                product = detect_imunify_product(configContent)
                if product and integration_conf_needs_repair(integrationConfig):
                    repair_integration_conf(integrationConfig)
                ensure_clscripts_executable()

                if product == 'av':
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

                elif product == '360':
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

        try:
            from plogical import fastapi_ssh_config

            fastapi_ssh_config.apply_security_migration()
            Upgrade.stdOut(
                "Applied Web Terminal (fastapi_ssh_server) security migration.", 1
            )
        except Exception as exc:
            Upgrade.stdOut(
                "Warning: fastapi_ssh_server security migration skipped: %s" % str(exc),
                0,
            )

        command = 'systemctl enable --now fastapi_ssh_server'
        Upgrade.executioner(command, command, 0)

        Upgrade.stdOut("Upgrade Completed.")

        ### remove log file path incase its there

        if Upgrade.SoftUpgrade:
            time.sleep(30)
            if os.path.exists(Upgrade.LogPathNew):
                os.remove(Upgrade.LogPathNew)
            try:
                if os.path.isfile(Upgrade.ProgressPathNew):
                    os.remove(Upgrade.ProgressPathNew)
            except OSError:
                pass

    @staticmethod
    def fixApacheConfigurationOld():
        """OLD VERSION - DO NOT USE - Fix Apache configuration issues after upgrade"""
        try:
            # Check if Apache is installed
            if Upgrade.FindOperatingSytem() == CENTOS8 \
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
                if Upgrade.FindOperatingSytem() in [CENTOS8, openEuler20, openEuler22]:
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
                    if Upgrade.FindOperatingSytem() in [CENTOS8, openEuler20, openEuler22]:
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

            if Upgrade.FindOperatingSytem() == CENTOS8\
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
                    or Upgrade.FindOperatingSytem() == Ubuntu20 or Upgrade.FindOperatingSytem() == Debian11 or Upgrade.FindOperatingSytem() == Debian12 or Upgrade.FindOperatingSytem() == Debian13:

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

        except Exception as e:
            ErrorSanitizer.log_error_securely(e, 'installQuota')
            print("[ERROR] installQuota. Failed to install quota")
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
            if osType in [CENTOS8, CloudLinux8]:
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
                def modify_apache_backends(lines):
                    """Modify config to add Apache proxy backends if missing"""
                    content = ''.join(lines)
                    modified_lines = lines[:]
                    
                    # Check for apachebackend extprocessor
                    if 'extprocessor apachebackend' not in content:
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
                        modified_lines.append(backend_config)
                        print("Added apachebackend extprocessor configuration")
                    
                    # Check for proxyApacheBackendSSL extprocessor
                    if 'extprocessor proxyApacheBackendSSL' not in content:
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
                        modified_lines.append(ssl_backend_config)
                        print("Added proxyApacheBackendSSL extprocessor configuration")
                    
                    return modified_lines
                
                # Use safe modification with backup and validation
                success, error = installUtilities.safeModifyHttpdConfig(
                    modify_apache_backends,
                    "Add Apache proxy backend configurations"
                )
                
                if success:
                    print("Updated OpenLiteSpeed configuration with Apache proxy backends")
                else:
                    print(f"WARNING: Failed to update OpenLiteSpeed configuration: {error}")
                    Upgrade.stdOut(f"Failed to update OpenLiteSpeed config: {error}", 0)
            
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
            if osType in [CENTOS8, CloudLinux8]:
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
                    if osType not in [CENTOS8, CloudLinux8]:
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
            if osType in [CENTOS8, CloudLinux8]:
                sock_path = '/var/run/php-fpm/'
            else:
                sock_path = '/var/run/php/'
            
            if os.path.exists(sock_path):
                # Set proper permissions
                command = f'chmod 755 {sock_path}'
                Upgrade.executioner(command, command, 0, True)
                
                # Fix ownership
                command = f'chown apache:apache {sock_path}' if osType in [CENTOS8, CloudLinux8] else f'chown www-data:www-data {sock_path}'
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
            if osType in [CENTOS8, CloudLinux8]:
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
