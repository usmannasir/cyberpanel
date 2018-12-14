import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import shlex
import subprocess
import shutil
import requests
import json
import time
from baseTemplate.models import version
import MySQLdb as mysql

class Upgrade:
    logPath = "/usr/local/lscp/logs/upgradeLog"

    @staticmethod
    def stdOut(message, do_exit = 0):
        print("\n\n")
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")
        print("[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + message + "\n")
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")

        if do_exit:
            os._exit(0)

    @staticmethod
    def executioner(command, component, do_exit = 0):
        try:
            count = 0
            while True:
                res = subprocess.call(shlex.split(command))
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
            return 0

    @staticmethod
    def downloadLink():
        try:
            url = "https://cyberpanel.net/version.txt"
            r = requests.get(url, verify=True)
            data = json.loads(r.text)
            version_number = str(data['version'])
            version_build = str(data['build'])
            return (version_number + "." + version_build + ".tar.gz")
        except BaseException, msg:
            Upgrade.stdOut(str(msg) + ' [downloadLink]')
            os._exit(0)

    @staticmethod
    def setupVirtualEnv():
        try:
            Upgrade.stdOut('Setting up virtual environment for CyberPanel.')
            ##

            command = "yum install -y libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel"
            Upgrade.executioner(command, 'VirtualEnv Pre-reqs', 0)


            ##

            command = "pip install virtualenv"
            Upgrade.executioner(command, 'VirtualEnv Install', 0)

            ####

            command = "virtualenv --system-site-packages /usr/local/CyberCP"
            Upgrade.executioner(command, 'Setting up VirtualEnv [One]', 1)


            ##

            env_path = '/usr/local/CyberCP'
            subprocess.call(['virtualenv', env_path])
            activate_this = os.path.join(env_path, 'bin', 'activate_this.py')
            execfile(activate_this, dict(__file__=activate_this))

            ##

            command = "pip install --ignore-installed -r /usr/local/CyberCP/requirments.txt"
            Upgrade.executioner(command, 'CyberPanel requirements', 1)

            command = "systemctl stop gunicorn.socket"
            Upgrade.executioner(command, '', 0)

            command = "virtualenv --system-site-packages /usr/local/CyberCP"
            Upgrade.executioner(command, 'Setting up VirtualEnv [Two]', 1)

            Upgrade.stdOut('Virtual enviroment for CyberPanel successfully installed.')
        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [setupVirtualEnv]", 0)

    @staticmethod
    def updateGunicornConf():
        try:
            path = '/etc/systemd/system/gunicorn.service'

            cont = """[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
PIDFile=/run/gunicorn/pid
User=cyberpanel
Group=cyberpanel
RuntimeDirectory=gunicorn
WorkingDirectory=/usr/local/CyberCP
ExecStart=/usr/local/CyberCP/bin/gunicorn --pid /run/gunicorn/gucpid   \
          --bind 127.0.0.1:5003 CyberCP.wsgi
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
PrivateTmp=true

[Install]
WantedBy=multi-user.target"""

            writeToFile = open(path, 'w')
            writeToFile.write(cont)
            writeToFile.close()

            ##

            command = 'systemctl daemon-reload'
            Upgrade.executioner(command, 'daemon-reload', 0)

            ##

            command = 'systemctl restart gunicorn.socket'
            Upgrade.executioner(command, 'restart gunicorn.socket', 0)
        except BaseException, msg:
            Upgrade.stdOut(str(msg) + " [updateGunicornConf]")

    @staticmethod
    def fileManager():
        ## Copy File manager files

        command = "rm -rf /usr/local/lsws/Example/html/FileManager"
        Upgrade.executioner(command, 'Remove old Filemanager', 0)

        if os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            command = "mv /usr/local/CyberCP/install/FileManager /usr/local/lsws/Example/html"
            Upgrade.executioner(command, 'Setup new Filemanager', 0)
        else:
            command = "mv /usr/local/CyberCP/install/FileManager /usr/local/lsws"
            Upgrade.executioner(command, 'Setup new Filemanager', 0)


        ##

        command = "chmod -R 777 /usr/local/lsws/Example/html/FileManager"
        Upgrade.executioner(command, 'Filemanager permissions change', 0)

    @staticmethod
    def setupCLI():
        try:

            command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
            Upgrade.executioner(command, 'CLI Symlink', 0)

            command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
            Upgrade.executioner(command, 'CLI Permissions', 0)

        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [setupCLI]")
            return 0

    @staticmethod
    def staticContent():

        command = "rm -rf /usr/local/lscp/cyberpanel/static"
        Upgrade.executioner(command, 'Remove old static content', 0)

        ##

        command = "mv /usr/local/CyberCP/static /usr/local/lscp/cyberpanel"
        Upgrade.executioner(command, 'Update new static content', 0)

    @staticmethod
    def upgradeVersion():
        try:
            vers = version.objects.get(pk=1)
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
            vers.currentVersion = latest['version']
            vers.build = latest['build']
            vers.save()
        except:
            pass

    @staticmethod
    def setupConnection(db = None):
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            if db == None:
                conn = mysql.connect(user='root', passwd=password)
            else:
                conn = mysql.connect(db=db, user='root', passwd=password)

            cursor = conn.cursor()
            return conn, cursor

        except BaseException, msg:
            Upgrade.stdOut(str(msg))
            return 0, 0

    @staticmethod
    def applyLoginSystemMigrations():
        try:

            connection, cursor = Upgrade.setupConnection('cyberpanel')

            try:
                cursor.execute('CREATE TABLE `loginSystem_acl` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL UNIQUE, `adminStatus` integer NOT NULL DEFAULT 0, `versionManagement` integer NOT NULL DEFAULT 0, `createNewUser` integer NOT NULL DEFAULT 0, `deleteUser` integer NOT NULL DEFAULT 0, `resellerCenter` integer NOT NULL DEFAULT 0, `changeUserACL` integer NOT NULL DEFAULT 0, `createWebsite` integer NOT NULL DEFAULT 0, `modifyWebsite` integer NOT NULL DEFAULT 0, `suspendWebsite` integer NOT NULL DEFAULT 0, `deleteWebsite` integer NOT NULL DEFAULT 0, `createPackage` integer NOT NULL DEFAULT 0, `deletePackage` integer NOT NULL DEFAULT 0, `modifyPackage` integer NOT NULL DEFAULT 0, `createDatabase` integer NOT NULL DEFAULT 0, `deleteDatabase` integer NOT NULL DEFAULT 0, `listDatabases` integer NOT NULL DEFAULT 0, `createNameServer` integer NOT NULL DEFAULT 0, `createDNSZone` integer NOT NULL DEFAULT 0, `deleteZone` integer NOT NULL DEFAULT 0, `addDeleteRecords` integer NOT NULL DEFAULT 0, `createEmail` integer NOT NULL DEFAULT 0, `deleteEmail` integer NOT NULL DEFAULT 0, `emailForwarding` integer NOT NULL DEFAULT 0, `changeEmailPassword` integer NOT NULL DEFAULT 0, `dkimManager` integer NOT NULL DEFAULT 0, `createFTPAccount` integer NOT NULL DEFAULT 0, `deleteFTPAccount` integer NOT NULL DEFAULT 0, `listFTPAccounts` integer NOT NULL DEFAULT 0, `createBackup` integer NOT NULL DEFAULT 0, `restoreBackup` integer NOT NULL DEFAULT 0, `addDeleteDestinations` integer NOT NULL DEFAULT 0, `scheDuleBackups` integer NOT NULL DEFAULT 0, `remoteBackups` integer NOT NULL DEFAULT 0, `manageSSL` integer NOT NULL DEFAULT 0, `hostnameSSL` integer NOT NULL DEFAULT 0, `mailServerSSL` integer NOT NULL DEFAULT 0)')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD token varchar(500)')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD acl_id integer')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD FOREIGN KEY (acl_id) REFERENCES loginSystem_acl(id)')
            except:
                pass

            try:
                cursor.execute("insert into loginSystem_acl (id, name, adminStatus) values (1,'admin',1)")
            except:
                pass

            try:
                cursor.execute("insert into loginSystem_acl (id, name, adminStatus, createNewUser, deleteUser, createWebsite, resellerCenter, modifyWebsite, suspendWebsite, deleteWebsite, createPackage, deletePackage, modifyPackage, createNameServer, restoreBackup) values (2,'reseller',0,1,1,1,1,1,1,1,1,1,1,1,1)")
            except:
                pass
            try:
                cursor.execute("insert into loginSystem_acl (id, name, createDatabase, deleteDatabase, listDatabases, createDNSZone, deleteZone, addDeleteRecords, createEmail, deleteEmail, emailForwarding, changeEmailPassword, dkimManager, createFTPAccount, deleteFTPAccount, listFTPAccounts, createBackup, manageSSL) values (3,'user', 1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1)")
            except:
                pass

            try:
                cursor.execute("UPDATE loginSystem_administrator SET  acl_id = 3")
            except:
                pass

            try:
                cursor.execute("UPDATE loginSystem_administrator SET  acl_id = 1 where userName = 'admin'")
            except:
                pass

            try:
                cursor.execute("alter table loginSystem_administrator drop initUserAccountsLimit")
            except:
                pass

            try:
                cursor.execute("CREATE TABLE `websiteFunctions_aliasdomains` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `aliasDomain` varchar(75) NOT NULL)")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE `websiteFunctions_aliasdomains` ADD COLUMN `master_id` integer NOT NULL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE `websiteFunctions_aliasdomains` ADD CONSTRAINT `websiteFunctions_ali_master_id_726c433d_fk_websiteFu` FOREIGN KEY (`master_id`) REFERENCES `websiteFunctions_websites` (`id`)")
            except:
                pass

            connection.close()

        except OSError, msg:
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

            connection.close()

        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [applyLoginSystemMigrations]")

    @staticmethod
    def mailServerMigrations():
        try:
            connection, cursor = Upgrade.setupConnection('cyberpanel')

            try:
                cursor.execute('ALTER TABLE e_forwardings DROP PRIMARY KEY;ALTER TABLE e_forwardings ADD id INT AUTO_INCREMENT PRIMARY KEY')
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

            connection.close()
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

            connection.close()
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
    def downloadAndUpgrade(versionNumbring):
        try:
            ## Download latest version.

            command = "wget https://cyberpanel.net/CyberPanel." + versionNumbring
            # command = "wget https://cyberpanel.net/CyberPanel.1.7.4.tar.gz"
            Upgrade.executioner(command, 'Download latest version', 1)

            ## Backup settings file.

            Upgrade.stdOut("Backing up settings file.")

            shutil.copy("/usr/local/CyberCP/CyberCP/settings.py", "/usr/local/settings.py")

            Upgrade.stdOut("Settings file backed up.")

            if os.path.exists('/usr/local/CyberCP/bin'):
                shutil.rmtree('/usr/local/CyberCP/bin')

            ## Extract Latest files

            # command = "tar zxf CyberPanel.1.7.4.tar.gz"
            command = "tar zxf CyberPanel." + versionNumbring
            Upgrade.executioner(command, 'Extract latest version', 1)

            ## Copy settings file

            data = open("/usr/local/settings.py", 'r').readlines()

            pluginCheck = 1
            for items in data:
                if items.find('pluginHolder') > -1:
                    pluginCheck = 0

            emailMarketing = 1
            for items in data:
                if items.find('emailMarketing') > -1:
                    emailMarketing = 0

            emailPremium = 1
            for items in data:
                if items.find('emailPremium') > -1:
                    emailPremium = 0

            s3Backups = 1
            for items in data:
                if items.find('s3Backups') > -1:
                    s3Backups = 0


            Upgrade.stdOut('Restoring settings file!')


            writeToFile = open("/usr/local/CyberCP/CyberCP/settings.py", 'w')

            for items in data:
                if items.find("'filemanager',") > -1:
                    writeToFile.writelines(items)
                    if pluginCheck == 1:
                        writeToFile.writelines("    'pluginHolder',\n")
                    if emailMarketing == 1:
                        writeToFile.writelines("    'emailMarketing',\n")
                    if emailPremium == 1:
                        writeToFile.writelines("    'emailPremium',\n")
                    if s3Backups == 1:
                        writeToFile.writelines("    's3Backups',\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            Upgrade.stdOut('Settings file restored!')

            ## Move static files

            Upgrade.staticContent()
        except:
            pass

    @staticmethod
    def installPYDNS():
        try:
            command = "pip install pydns"
            Upgrade.executioner(command, 'Install PyDNS', 1)
        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [installPYDNS]")
            return 0

    @staticmethod
    def installTLDExtract():
        try:
            command = "pip install tldextract"
            Upgrade.executioner(command, 'Install tldextract', 1)
        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [installTLDExtract]")
            return 0

    @staticmethod
    def installLSCPD():
        try:

            Upgrade.stdOut("Starting LSCPD installation..")

            command = 'yum -y install gcc gcc-c++ make autoconf glibc rcs'
            Upgrade.executioner(command, 'LSCPD Pre-reqs [one]', 0)

            ##

            command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel which curl'
            Upgrade.executioner(command, 'LSCPD Pre-reqs [two]', 0)


            command = 'wget https://cyberpanel.net/lscp.tar.gz'
            Upgrade.executioner(command, 'Download LSCPD [two]', 0)

            if os.path.exists('/usr/local/lscp.tar.gz'):
                os.remove('/usr/local/lscp.tar.gz')

            ##

            command = 'tar zxf lscp.tar.gz -C /usr/local/'
            Upgrade.executioner(command, 'Extract LSCPD [two]', 0)

            try:
                os.remove("/usr/local/lscp/fcgi-bin/lsphp")
                shutil.copy("/usr/local/lsws/lsphp70/bin/lsphp","/usr/local/lscp/fcgi-bin/lsphp")
            except:
                pass

            command = 'adduser lscpd -M -d /usr/local/lscp'
            Upgrade.executioner(command, 'Add user LSCPD', 0)

            command = 'groupadd lscpd'
            Upgrade.executioner(command, 'Add group LSCPD', 0)

            command = 'usermod -a -G lscpd lscpd'
            Upgrade.executioner(command, 'Add group LSCPD', 0)

            command = 'usermod -a -G lsadm lscpd'
            Upgrade.executioner(command, 'Add group LSCPD', 0)

            command = 'chown -R lscpd:lscpd /usr/local/lscp/cyberpanel'
            Upgrade.executioner(command, 'chown cyberpanel', 0)

            command = 'systemctl daemon-reload'
            Upgrade.executioner(command, 'daemon-reload LSCPD', 0)

            command = 'systemctl restart lscpd'
            Upgrade.executioner(command, 'Restart LSCPD', 0)

            Upgrade.stdOut("LSCPD successfully installed!")

        except BaseException, msg:
            Upgrade.stdOut(str(msg) + " [installLSCPD]")

    @staticmethod
    def fixPermissions():
        try:

            Upgrade.stdOut("Fixing permissions..")

            command = 'chown -R cyberpanel:cyberpanel /usr/local/CyberCP'
            Upgrade.executioner(command, 'chown core code', 0)

            command = 'chown -R cyberpanel:cyberpanel /usr/local/lscp'
            Upgrade.executioner(command, 'chown lscp', 0)

            command = 'chown -R lscpd:lscpd /usr/local/lscp/cyberpanel'
            Upgrade.executioner(command, 'chown static content', 0)

            Upgrade.stdOut("Permissions updated.")

        except BaseException, msg:
            Upgrade.stdOut(str(msg) + " [installLSCPD]")

    @staticmethod
    def upgrade():

        os.chdir("/usr/local")

        ## Current Version

        Version = version.objects.get(pk=1)

        command = "systemctl stop gunicorn.socket"
        Upgrade.executioner(command, 'stop gunicorn', 0)

        command = "systemctl stop lscpd"
        Upgrade.executioner(command, 'stop lscpd', 0)

        ##

        versionNumbring = Upgrade.downloadLink()


        if os.path.exists('/usr/local/CyberPanel.' + versionNumbring):
            os.remove('/usr/local/CyberPanel.' + versionNumbring)

        if float(Version.currentVersion) < 1.6:
            Upgrade.stdOut('Upgrades works for version 1.6 onwards.')
            os._exit(0)

        ##

        Upgrade.installPYDNS()
        Upgrade.downloadAndUpgrade(versionNumbring)

        ##

        Upgrade.installTLDExtract()

        ##

        Upgrade.mailServerMigrations()
        Upgrade.emailMarketingMigrationsa()

        ##

        Upgrade.setupVirtualEnv()
        Upgrade.updateGunicornConf()

        ##

        Upgrade.applyLoginSystemMigrations()
        Upgrade.s3BackupMigrations()
        Upgrade.enableServices()

        Upgrade.setupCLI()
        Upgrade.installLSCPD()
        Upgrade.fixPermissions()
        time.sleep(3)

        ## Upgrade version

        Upgrade.upgradeVersion()

        try:
            command = "systemctl start lscpd"
            Upgrade.executioner(command, 'Start LSCPD', 0)
        except:
            pass

        Upgrade.stdOut("Upgrade Completed.")

def main():
    Upgrade.upgrade()

if __name__ == "__main__":
    main()