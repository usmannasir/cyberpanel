import os
import os.path
import sys
import argparse
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
import shlex
import subprocess
import shutil
import requests
import json
import time
import MySQLdb as mysql
from CyberCP import settings
import random
import string


class Upgrade:
    logPath = "/usr/local/lscp/logs/upgradeLog"
    cdn = 'cdn.cyberpanel.sh'

    @staticmethod
    def stdOut(message, do_exit=0):
        print("\n\n")
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))
        print(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] " + message + "\n"))
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))

        if do_exit:
            os._exit(0)

    @staticmethod
    def executioner(command, component, do_exit=0):
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

        command = "adduser docker"
        Upgrade.executioner(command, 'adduser docker', 0)

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

            command = 'wget -O /usr/local/CyberCP/public/phpmyadmin.zip https://%s/misc/phpmyadmin.zip' % (
                Upgrade.cdn)
            Upgrade.executioner(command, 0)

            command = 'unzip /usr/local/CyberCP/public/phpmyadmin.zip -d /usr/local/CyberCP/public/'
            Upgrade.executioner(command, 0)

            command = 'mv /usr/local/CyberCP/public/phpMyAdmin-5.0.0-all-languages /usr/local/CyberCP/public/phpmyadmin'
            Upgrade.executioner(command, 0)

            command = 'rm -f /usr/local/CyberCP/public/phpmyadmin.zip'
            Upgrade.executioner(command, 0)

            ## Write secret phrase

            rString = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

            data = open('/usr/local/CyberCP/public/phpmyadmin/config.sample.inc.php', 'r').readlines()

            writeToFile = open('/usr/local/CyberCP/public/phpmyadmin/config.inc.php', 'w')

            for items in data:
                if items.find('blowfish_secret') > -1:
                    writeToFile.writelines(
                        "$cfg['blowfish_secret'] = '" + rString + "'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.writelines("$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';\n")

            writeToFile.close()

            os.mkdir('/usr/local/CyberCP/public/phpmyadmin/tmp')

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

            if os.path.exists("/usr/local/CyberCP/public/rainloop"):

                if os.path.exists("/usr/local/lscp/cyberpanel/rainloop/data"):
                    pass
                else:
                    command = "mv /usr/local/CyberCP/public/rainloop/data /usr/local/lscp/cyberpanel/rainloop/data"
                    Upgrade.executioner(command, 0)

                    command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data"
                    Upgrade.executioner(command, 0)

                path = "/usr/local/CyberCP/public/rainloop/rainloop/v/1.12.1/include.php"

                data = open(path, 'r').readlines()
                writeToFile = open(path, 'w')

                for items in data:
                    if items.find("$sCustomDataPath = '';") > -1:
                        writeToFile.writelines(
                            "			$sCustomDataPath = '/usr/local/lscp/cyberpanel/rainloop/data';\n")
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()
                return 0

            cwd = os.getcwd()

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            os.chdir("/usr/local/CyberCP/public")

            count = 1

            while (1):
                command = 'wget https://www.rainloop.net/repository/webmail/rainloop-community-latest.zip'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break

            #############

            count = 0

            while (1):
                command = 'unzip rainloop-community-latest.zip -d /usr/local/CyberCP/public/rainloop'

                cmd = shlex.split(command)
                res = subprocess.call(cmd)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break

            os.remove("rainloop-community-latest.zip")

            #######

            os.chdir("/usr/local/CyberCP/public/rainloop")

            count = 0

            while (1):
                command = 'find . -type d -exec chmod 755 {} \;'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)
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
                res = subprocess.call(cmd)
                if res != 0:
                    count = count + 1
                    if count == 3:
                        break
                else:
                    break
            ######

            iPath = os.listdir('/usr/local/CyberCP/public/rainloop/rainloop/v/')

            path = "/usr/local/CyberCP/public/rainloop/rainloop/v/%s/include.php" % (iPath[0])

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
            Upgrade.executioner(command, 'mkdir rainloop configs', 0)

            labsPath = '/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/application.ini'

            labsData = """[labs]
            imap_folder_list_limit = 0
            """

            writeToFile = open(labsPath, 'w')
            writeToFile.write(labsData)
            writeToFile.close()

            os.chdir(cwd)

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [downoad_and_install_raindloop]", 0)

        return 1

    @staticmethod
    def downloadLink():
        try:
            url = "https://cyberpanel.net/version.txt"
            r = requests.get(url, verify=True)
            data = json.loads(r.text)
            version_number = str(data['version'])
            version_build = str(data['build'])

            try:
                path = "/usr/local/CyberCP/version.txt"
                writeToFile = open(path, 'w')
                writeToFile.writelines(version_number + '\n')
                writeToFile.writelines(version_build)
                writeToFile.close()
            except:
                pass

            return (version_number + "." + version_build + ".tar.gz")
        except BaseException as msg:
            Upgrade.stdOut(str(msg) + ' [downloadLink]')
            os._exit(0)

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

        shutil.move("/usr/local/CyberCP/static", "/usr/local/CyberCP/public/")

    @staticmethod
    def upgradeVersion():
        try:

            import django
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            django.setup()
            from baseTemplate.models import version

            vers = version.objects.get(pk=1)
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
            vers.currentVersion = latest['version']
            vers.build = latest['build']
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
                    'CREATE TABLE `loginSystem_acl` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL UNIQUE, `adminStatus` integer NOT NULL DEFAULT 0, `versionManagement` integer NOT NULL DEFAULT 0, `createNewUser` integer NOT NULL DEFAULT 0, `deleteUser` integer NOT NULL DEFAULT 0, `resellerCenter` integer NOT NULL DEFAULT 0, `changeUserACL` integer NOT NULL DEFAULT 0, `createWebsite` integer NOT NULL DEFAULT 0, `modifyWebsite` integer NOT NULL DEFAULT 0, `suspendWebsite` integer NOT NULL DEFAULT 0, `deleteWebsite` integer NOT NULL DEFAULT 0, `createPackage` integer NOT NULL DEFAULT 0, `deletePackage` integer NOT NULL DEFAULT 0, `modifyPackage` integer NOT NULL DEFAULT 0, `createDatabase` integer NOT NULL DEFAULT 0, `deleteDatabase` integer NOT NULL DEFAULT 0, `listDatabases` integer NOT NULL DEFAULT 0, `createNameServer` integer NOT NULL DEFAULT 0, `createDNSZone` integer NOT NULL DEFAULT 0, `deleteZone` integer NOT NULL DEFAULT 0, `addDeleteRecords` integer NOT NULL DEFAULT 0, `createEmail` integer NOT NULL DEFAULT 0, `deleteEmail` integer NOT NULL DEFAULT 0, `emailForwarding` integer NOT NULL DEFAULT 0, `changeEmailPassword` integer NOT NULL DEFAULT 0, `dkimManager` integer NOT NULL DEFAULT 0, `createFTPAccount` integer NOT NULL DEFAULT 0, `deleteFTPAccount` integer NOT NULL DEFAULT 0, `listFTPAccounts` integer NOT NULL DEFAULT 0, `createBackup` integer NOT NULL DEFAULT 0, `restoreBackup` integer NOT NULL DEFAULT 0, `addDeleteDestinations` integer NOT NULL DEFAULT 0, `scheDuleBackups` integer NOT NULL DEFAULT 0, `remoteBackups` integer NOT NULL DEFAULT 0, `manageSSL` integer NOT NULL DEFAULT 0, `hostnameSSL` integer NOT NULL DEFAULT 0, `mailServerSSL` integer NOT NULL DEFAULT 0)')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE loginSystem_administrator ADD token varchar(500)')
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
                cursor.execute('ALTER TABLE dockerManager_containers ADD volumes longtext')
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
    def installGit():
        try:
            if os.path.exists("/etc/lsb-release"):
                command = 'apt -y install git'
                Upgrade.executioner(command, 'installGit', 0)
            else:
                command = 'sudo yum -y install http://repo.iotti.biz/CentOS/7/noarch/lux-release-7-1.noarch.rpm'
                Upgrade.executioner(command, 'installGit', 0)

                command = 'sudo yum install git -y'
                Upgrade.executioner(command, 'installGit', 0)

        except BaseException as msg:
            pass

    @staticmethod
    def downloadAndUpgrade(versionNumbring, branch):
        try:
            ## Download latest version.

            Upgrade.installGit()

            ## Backup settings file.

            Upgrade.stdOut("Backing up settings file.")

            shutil.copy("/usr/local/CyberCP/CyberCP/settings.py", "/usr/local/settings.py")

            Upgrade.stdOut("Settings file backed up.")

            ## Extract Latest files

            os.chdir('/usr/local')

            if os.path.exists('cyberpanel'):
                shutil.rmtree('cyberpanel')

            if os.path.exists('CyberCP'):
                shutil.rmtree('CyberCP')

            command = 'git clone https://github.com/usmannasir/cyberpanel'
            Upgrade.executioner(command, 'Download CyberPanel', 1)

            shutil.move('cyberpanel', 'CyberCP')

            if branch != 'stable':
                os.chdir('CyberCP')
                command = 'git checkout %s' % (branch)
                Upgrade.executioner(command, command, 1)
                os.chdir('/usr/local')




            ## Copy settings file

            data = open("/usr/local/settings.py", 'r').readlines()

            csrfCheck = 1
            for items in data:
                if items.find('CsrfViewMiddleware') > -1:
                    csrfCheck = 0

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

            dockerManager = 1
            for items in data:
                if items.find('dockerManager') > -1:
                    dockerManager = 0

            containerization = 1
            for items in data:
                if items.find('containerization') > -1:
                    containerization = 0

            manageServices = 1
            for items in data:
                if items.find('manageServices') > -1:
                    manageServices = 0

            CLManager = 1
            for items in data:
                if items.find('CLManager') > -1:
                    CLManager = 0

            IncBackups = 1
            for items in data:
                if items.find('IncBackups') > -1:
                    IncBackups = 0

            WebTerminal = 1
            for items in data:
                if items.find('WebTerminal') > -1:
                    WebTerminal = 0

            SESSION_COOKIE_SECURE = 0

            for items in data:
                if items.find('SESSION_COOKIE_SECURE') > -1:
                    SESSION_COOKIE_SECURE = 0

            DATABASE_ROUTERS = 1

            for items in data:
                if items.find('DATABASE_ROUTERS') > -1:
                    DATABASE_ROUTERS = 0

            Upgrade.stdOut('Restoring settings file!')

            writeToFile = open("/usr/local/CyberCP/CyberCP/settings.py", 'w')

            for items in data:
                if items.find('csf') > -1 or items.find('SESSION_COOKIE_SECURE') > -1 or items.find('CSRF_COOKIE_SECURE') > -1:
                    continue
                if items.find("CommonMiddleware") > -1:
                    if csrfCheck == 1:
                        writeToFile.writelines("    'django.middleware.csrf.CsrfViewMiddleware',\n")

                if items.find('DATABASE_ROUTERS') > -1:
                    writeToFile.writelines(items)
                    if SESSION_COOKIE_SECURE == 1:
                        con = """SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
"""
                        writeToFile.writelines(con)

                elif items.find("'filemanager',") > -1:
                    writeToFile.writelines(items)
                    if pluginCheck == 1:
                        writeToFile.writelines("    'pluginHolder',\n")
                    if emailMarketing == 1:
                        writeToFile.writelines("    'emailMarketing',\n")
                    if emailPremium == 1:
                        writeToFile.writelines("    'emailPremium',\n")
                    if s3Backups == 1:
                        writeToFile.writelines("    's3Backups',\n")
                    if dockerManager == 1:
                        writeToFile.writelines("    'dockerManager',\n")

                    if containerization == 1:
                        writeToFile.writelines("    'containerization',\n")

                    if manageServices == 1:
                        writeToFile.writelines("    'manageServices',\n")


                    if CLManager == 1:
                        writeToFile.writelines("    'CLManager',\n")

                    if IncBackups == 1:
                        writeToFile.writelines("    'IncBackups',\n")

                    if WebTerminal == 1:
                        writeToFile.writelines("    'WebTerminal',\n")

                else:
                    writeToFile.writelines(items)

            ##

            DATA_UPLOAD_MAX_MEMORY_SIZE = 1
            for items in data:
                if items.find('DATA_UPLOAD_MAX_MEMORY_SIZE') > -1:
                    DATA_UPLOAD_MAX_MEMORY_SIZE = 0
                    writeToFile.writelines("\nDATA_UPLOAD_MAX_MEMORY_SIZE = 52428800\n")

            if DATA_UPLOAD_MAX_MEMORY_SIZE == 1:
                writeToFile.writelines("\nDATA_UPLOAD_MAX_MEMORY_SIZE = 52428800\n")

            ##

            MEDIA_URL = 1
            for items in data:
                if items.find('MEDIA_URL') > -1:
                    MEDIA_URL = 0

            if MEDIA_URL == 1:
                writeToFile.writelines("MEDIA_URL = '/home/cyberpanel/media/'\n")
                writeToFile.writelines('MEDIA_ROOT = MEDIA_URL\n')


            if items.find('MEDIA_ROOT = MEDIA_URLDATA_UPLOAD_MAX_MEMORY_SIZE') > -1:
                writeToFile.writelines('MEDIA_ROOT = MEDIA_URL\n')



            ##

            if DATABASE_ROUTERS == 1:
                writeToFile.writelines("\nDATABASE_ROUTERS = ['backup.backupRouter.backupRouter']\n")

            writeToFile.close()

            Upgrade.stdOut('Settings file restored!')

            ## Move static files

            Upgrade.staticContent()
        except:
            pass

    @staticmethod
    def installLSCPD():
        try:

            Upgrade.stdOut("Starting LSCPD installation..")

            cwd = os.getcwd()

            os.chdir('/usr/local')

            command = 'yum -y install gcc gcc-c++ make autoconf glibc rcs'
            Upgrade.executioner(command, 'LSCPD Pre-reqs [one]', 0)

            ##

            lscpdPath = '/usr/local/lscp/bin/lscpd'

            if os.path.exists(lscpdPath):
                os.remove(lscpdPath)

            command = 'wget  https://raw.githubusercontent.com/usmannasir/cyberpanel/v1.9.4/lscpd-0.2.4 -P /usr/local/lscp/bin/'
            Upgrade.executioner(command, command, 0)

            command = 'rm -f /usr/local/lscp/bin/lscpd'
            Upgrade.executioner(command, command, 0)

            command = 'mv /usr/local/lscp/bin/lscpd-0.2.4 /usr/local/lscp/bin/lscpd'
            Upgrade.executioner(command, command, 0)

            command = 'chmod 755 %s' % (lscpdPath)
            Upgrade.executioner(command, 'LSCPD Download.', 0)

            command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel which curl'
            Upgrade.executioner(command, 'LSCPD Pre-reqs [two]', 0)

            command = 'adduser lscpd -M -d /usr/local/lscp'
            Upgrade.executioner(command, 'Add user LSCPD', 0)

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

    @staticmethod
    def fixPermissions():
        try:

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

            command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data"
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

            clScripts = ['/usr/local/CyberCP/CLScript/panel_info.py', '/usr/local/CyberCP/CLScript/CloudLinuxPackages.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxUsers.py', '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py'
                ,'/usr/local/CyberCP/CLScript/CloudLinuxResellers.py', '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
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

            Upgrade.stdOut("Permissions updated.")

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [installLSCPD]")

    @staticmethod
    def AutoUpgradeAcme():
        command = '/root/.acme.sh/acme.sh --upgrade --auto-upgrade'
        Upgrade.executioner(command, command, 0)

    @staticmethod
    def installPHP73():
        try:
            command = 'yum install -y lsphp73 lsphp73-json lsphp73-xmlrpc lsphp73-xml lsphp73-tidy lsphp73-soap lsphp73-snmp ' \
                      'lsphp73-recode lsphp73-pspell lsphp73-process lsphp73-pgsql lsphp73-pear lsphp73-pdo lsphp73-opcache ' \
                      'lsphp73-odbc lsphp73-mysqlnd lsphp73-mcrypt lsphp73-mbstring lsphp73-ldap lsphp73-intl lsphp73-imap ' \
                      'lsphp73-gmp lsphp73-gd lsphp73-enchant lsphp73-dba  lsphp73-common  lsphp73-bcmath'
            Upgrade.executioner(command, 'Install PHP 73, 0')

            command = 'yum install -y lsphp74 lsphp74-json lsphp74-xmlrpc lsphp74-xml lsphp74-tidy lsphp74-soap lsphp74-snmp ' \
                      'lsphp74-recode lsphp74-pspell lsphp74-process lsphp74-pgsql lsphp74-pear lsphp74-pdo lsphp74-opcache ' \
                      'lsphp74-odbc lsphp74-mysqlnd lsphp74-mcrypt lsphp74-mbstring lsphp74-ldap lsphp74-intl lsphp74-imap ' \
                      'lsphp74-gmp lsphp74-gd lsphp74-enchant lsphp74-dba lsphp74-common  lsphp74-bcmath'

            Upgrade.executioner(command, 'Install PHP 74, 0')
        except:
            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install ' \
                      'lsphp7? lsphp7?-common lsphp7?-curl lsphp7?-dev lsphp7?-imap lsphp7?-intl lsphp7?-json ' \
                      'lsphp7?-ldap lsphp7?-mysql lsphp7?-opcache lsphp7?-pspell lsphp7?-recode ' \
                      'lsphp7?-sqlite3 lsphp7?-tidy'
            Upgrade.executioner(command, 'Install PHP 73, 0')

        CentOSPath = '/etc/redhat-release'

        if not os.path.exists(CentOSPath):
            command = 'cp /usr/local/lsws/lsphp71/bin/php /usr/bin/'
            Upgrade.executioner(command, 'Set default PHP 7.0, 0')

    @staticmethod
    def someDirectories():
        command = "mkdir -p /usr/local/lscpd/admin/"
        Upgrade.executioner(command, 0)

        command = "mkdir -p /usr/local/lscp/cyberpanel/logs"
        Upgrade.executioner(command, 0)

    @staticmethod
    def upgradePDNS():
        command = "yum install epel-release && curl -o /etc/yum.repos.d/powerdns-auth-42.repo https://repo.powerdns.com/repo-files/centos-auth-42.repo && yum --enablerepo=epel install pdns"
        subprocess.call(command, shell=True)

    @staticmethod
    def upgradeDovecot():
        try:
            Upgrade.stdOut("Upgrading Dovecot..")
            CentOSPath = '/etc/redhat-release'

            if os.path.exists(CentOSPath):
                path = '/etc/yum.repos.d/dovecot.repo'
                content = """[dovecot-2.3-latest]
name=Dovecot 2.3 CentOS $releasever - $basearch
baseurl=http://repo.dovecot.org/ce-2.3-latest/centos/$releasever/RPMS/$basearch
gpgkey=https://repo.dovecot.org/DOVECOT-REPO-GPG
gpgcheck=1
enabled=1"""
                writeToFile = open(path, 'w')
                writeToFile.write(content)
                writeToFile.close()

                command = "yum makecache -y"
                Upgrade.executioner(command, 0)

                command = "yum update -y"
                Upgrade.executioner(command, 0)

                ## Remove Default Password Scheme

                path = '/etc/dovecot/dovecot-sql.conf.ext'

                data = open(path, 'r').readlines()

                updatePasswords = 1

                writeToFile = open(path, 'w')
                for items in data:
                    if items.find('default_pass_scheme') > -1:
                        updatePasswords = 0
                        continue
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()

                import django
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
                django.setup()
                from mailServer.models import EUsers

                Upgrade.stdOut("Upgrading passwords...")
                for items in EUsers.objects.all():
                    if items.password.find('CRYPT') > -1:
                        continue
                    command = 'doveadm pw -p %s' % (items.password)
                    items.password = subprocess.check_output(shlex.split(command)).decode("utf-8").strip('\n')
                    items.save()

                command = "systemctl restart dovecot"
                Upgrade.executioner(command, 0)



                ### Postfix Upgrade

                try:
                    shutil.copy('/etc/postfix/master.cf', '/etc/master.cf')
                except:
                    pass

                try:
                    shutil.copy('/etc/postfix/main.cf', '/etc/main.cf')
                except:
                    pass

                gf = '/etc/yum.repos.d/gf.repo'

                gfContent = """[gf]
name=Ghettoforge packages that won't overwrite core distro packages.
mirrorlist=http://mirrorlist.ghettoforge.org/el/7/gf/$basearch/mirrorlist
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-gf.el7
failovermethod=priority

[gf-plus]
name=Ghettoforge packages that will overwrite core distro packages.
mirrorlist=http://mirrorlist.ghettoforge.org/el/7/plus/$basearch/mirrorlist
# Please read http://ghettoforge.org/index.php/Usage *before* enabling this repository!
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-gf.el7
failovermethod=priority
"""
                writeToFile = open(gf, 'w')
                writeToFile.write(gfContent)
                writeToFile.close()

                command = 'yum remove postfix -y'
                Upgrade.executioner(command, 0)

                command = 'rpm -Uvh http://mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el7.noarch.rpm'
                Upgrade.executioner(command, 0)

                command = 'yum clean all'
                Upgrade.executioner(command, 0)

                command = 'yum makecache fast'
                Upgrade.executioner(command, 0)

                command = 'yum install -y postfix3 postfix3-mysql'
                Upgrade.executioner(command, 0)

                try:
                    shutil.move('/etc/master.cf', '/etc/postfix/master.cf')
                except:
                    pass
                try:
                    shutil.move('/etc/main.cf', '/etc/postfix/main.cf')
                except:
                    pass

                command = 'systemctl restart postfix'
                Upgrade.executioner(command, 0)

            else:
                command = 'curl https://repo.dovecot.org/DOVECOT-REPO-GPG | gpg --import'
                subprocess.call(command, shell=True)

                command = 'gpg --export ED409DA1 > /etc/apt/trusted.gpg.d/dovecot.gpg'
                subprocess.call(command, shell=True)

                debPath = '/etc/apt/sources.list.d/dovecot.list'
                writeToFile = open(debPath, 'w')
                writeToFile.write('deb https://repo.dovecot.org/ce-2.3-latest/ubuntu/bionic bionic main\n')
                writeToFile.close()

                try:
                    command = 'apt update -y'
                    Upgrade.executioner(command, 0)
                except:
                    pass

                try:
                    command = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical sudo apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" --only-upgrade install dovecot-mysql -y'
                    subprocess.call(command, shell=True)

                    command = 'dpkg --configure -a'
                    Upgrade.executioner(command, 0)

                    command = 'apt --fix-broken install -y'
                    Upgrade.executioner(command, 0)

                    command = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical sudo apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" --only-upgrade install dovecot-mysql -y'
                    subprocess.call(command, shell=True)
                except:
                    pass

                ## Remove Default Password Scheme

                path = '/etc/dovecot/dovecot-sql.conf.ext'

                data = open(path, 'r').readlines()

                updatePasswords = 0

                writeToFile = open(path, 'w')
                for items in data:
                    if items.find('default_pass_scheme') > -1:
                        updatePasswords = 1
                        continue
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()

                Upgrade.stdOut("Upgrading passwords...")

                import django
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
                django.setup()
                from mailServer.models import EUsers

                for items in EUsers.objects.all():
                    if items.password.find('CRYPT') > -1:
                        continue
                    command = 'doveadm pw -p %s' % (items.password)
                    items.password = subprocess.check_output(shlex.split(command)).decode("utf-8").strip('\n')
                    items.save()


                command = "systemctl restart dovecot"
                Upgrade.executioner(command, 0)

            dovecotConf = '/etc/dovecot/dovecot.conf'

            dovecotContent = open(dovecotConf, 'r').read()

            if dovecotContent.find('service stats') == -1:
                writeToFile  = open(dovecotConf, 'a')

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

                command = 'systemctl restart dovecot'
                Upgrade.executioner(command, command, 0)

            Upgrade.stdOut("Dovecot upgraded.")

        except BaseException as msg:
            Upgrade.stdOut(str(msg) + " [upgradeDovecot]")

    @staticmethod
    def installRestic():
        CentOSPath = '/etc/redhat-release'

        if os.path.exists(CentOSPath):
            command = 'yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/copart/restic/repo/epel-7/copart-restic-epel-7.repo'
            Upgrade.executioner(command, 'Add restic repo.')

            command = 'yum install restic -y'
            Upgrade.executioner(command, 'Install Restic')
        else:
            command = 'apt-get update -y'
            Upgrade.executioner(command, 'Install Restic')

            command = 'apt-get install restic -y'
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

            if os.path.exists(CentOSPath):
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
        subprocess.call(command, shell=True)

        # Setup /usr/local/lsws/conf/httpd.conf to use new Logformat standard for better stats and accesslogs
        command = """sed -i "s|^LogFormat.*|LogFormat '%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"' combined|g" /usr/local/lsws/conf/httpd.conf"""
        subprocess.call(command, shell=True)

        # Fix all existing vhost confs to use new Logformat standard for better stats and accesslogs
        command = """find /usr/local/lsws/conf/vhosts/ -type f -name 'vhost.conf' -exec sed -i "s/.*CustomLog.*/    LogFormat '%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"' combined\n&/g" {} \;"""
        subprocess.call(command, shell=True)

        # Install any Cyberpanel missing crons to root crontab so its visible to users via crontab -l as root user

        # Install findBWUsage cron if missing

        command = """command="/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py"; job="0 * * * * $command >/dev/null 2>&1"; cat <(grep -Fiv "$command" <(crontab -l)) <(echo "$job") | crontab -"""
        subprocess.call(command, shell=True)

        # Install postfix hourly cron if missing

        command = """command="/usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup"; job="0 * * * * $command >/dev/null 2>&1"; cat <(grep -Fiv "$command" <(crontab -l)) <(echo "$job") | crontab -"""
        subprocess.call(command, shell=True)

        # Install postfix monthly cron if missing

        command = """command="/usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup"; job="0 0 1 * * $command >/dev/null 2>&1"; cat <(grep -Fiv "$command" <(crontab -l)) <(echo "$job") | crontab -"""
        subprocess.call(command, shell=True)

        # Install upgradeCritical cron if missing

        command = """command="/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py"; job="0 2 * * * $command >/dev/null 2>&1"; cat <(grep -Fiv "$command" <(crontab -l)) <(echo "$job") | crontab -"""
        subprocess.call(command, shell=True)

        # Install upgradeCritical cron if missing

        command = """command="/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py"; job="0 2 * * * $command >/dev/null 2>&1"; cat <(grep -Fiv "$command" <(crontab -l)) <(echo "$job") | crontab -"""
        subprocess.call(command, shell=True)



    @staticmethod
    def upgrade(branch):

        # Upgrade.stdOut("Upgrades are currently disabled")
        # return 0

        command = 'systemctl stop cpssh'
        Upgrade.executioner(command, 'fix csf if there', 0)


        ## Add LSPHP7.4 TO LSWS Ent configs

        if not os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            command = 'wget https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/install/litespeed/httpd_config.xml'
            Upgrade.executioner(command, command, 0)
            #os.remove('/usr/local/lsws/conf/httpd_config.xml')
            #shutil.copy('httpd_config.xml', '/usr/local/lsws/conf/httpd_config.xml')

        postfixPath = '/home/cyberpanel/postfix'
        pdns = '/home/cyberpanel/pdns'
        pureftpd = '/home/cyberpanel/ftp'

        Upgrade.updateRepoURL()

        os.chdir("/usr/local")

        command = 'yum remove yum-plugin-priorities -y'
        Upgrade.executioner(command, 'remove yum-plugin-priorities', 0)

        ## Current Version


        command = "systemctl stop lscpd"
        Upgrade.executioner(command, 'stop lscpd', 0)

        Upgrade.fixSudoers()
        Upgrade.mountTemp()
        Upgrade.dockerUsers()
        Upgrade.setupComposer()

        ##

        versionNumbring = Upgrade.downloadLink()

        if os.path.exists('/usr/local/CyberPanel.' + versionNumbring):
            os.remove('/usr/local/CyberPanel.' + versionNumbring)

        ##

        Upgrade.downloadAndUpgrade(versionNumbring, branch)
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

        #Upgrade.setupVirtualEnv()

        ##

        Upgrade.applyLoginSystemMigrations()
        Upgrade.s3BackupMigrations()
        Upgrade.containerMigrations()
        Upgrade.manageServiceMigrations()
        Upgrade.enableServices()

        Upgrade.installPHP73()
        Upgrade.setupCLI()
        Upgrade.someDirectories()
        Upgrade.installLSCPD()
        Upgrade.GeneralMigrations()
        #Upgrade.p3()

        if os.path.exists(postfixPath):
            Upgrade.upgradeDovecot()
        time.sleep(3)

        ## Upgrade version
        Upgrade.fixPermissions()
        Upgrade.upgradeVersion()
        Upgrade.UpdateMaxSSLCons()

        ## Update LSCPD PHP

        phpPath = '/usr/local/lscp/fcgi-bin/lsphp'

        try:
            os.remove(phpPath)
        except:
            pass

        command = 'cp /usr/local/lsws/lsphp73/bin/lsphp %s' % (phpPath)
        Upgrade.executioner(command, 0)


        try:
            command = "systemctl start lscpd"
            Upgrade.executioner(command, 'Start LSCPD', 0)
        except:
            pass


        command = 'csf -uf'
        Upgrade.executioner(command, 'fix csf if there', 0)
        command = 'systemctl start cpssh'
        Upgrade.executioner(command, 'fix csf if there', 0)
        Upgrade.AutoUpgradeAcme()
        Upgrade.installCLScripts()
        Upgrade.runSomeImportantBash()

        Upgrade.stdOut("Upgrade Completed.")


def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('branch', help='Install from branch name.')

    args = parser.parse_args()

    Upgrade.upgrade(args.branch)


if __name__ == "__main__":
    main()
