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
from CyberCP import settings

class Upgrade:
    logPath = "/usr/local/lscp/logs/upgradeLog"

    @staticmethod
    def stdOut(message):
        print("\n\n")
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")
        print("[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + message + "\n")
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")

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
            Upgrade.stdOut('Setting up virtual enviroment for CyberPanel.')
            ##
            count = 0
            while (1):
                command = "yum install -y libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to install project dependant modules, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to install project dependant modules! [setupVirtualEnv]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("Project dependant modules installed successfully!!")
                    break

            ##

            count = 0
            while (1):
                command = "pip install virtualenv"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to install virtualenv, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed install virtualenv! [setupVirtualEnv]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("virtualenv installed successfully!")
                    break

            ####

            count = 0
            while (1):
                command = "virtualenv --system-site-packages /usr/local/CyberCP"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to setup virtualenv, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to setup virtualenv! [setupVirtualEnv]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("virtualenv setuped successfully!")
                    break

            ##

            env_path = '/usr/local/CyberCP'
            subprocess.call(['virtualenv', env_path])
            activate_this = os.path.join(env_path, 'bin', 'activate_this.py')
            execfile(activate_this, dict(__file__=activate_this))

            ##

            count = 0
            while (1):
                command = "pip install --ignore-installed -r /usr/local/CyberCP/requirments.txt"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to install project dependant modules, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut(
                            "Failed to install project dependant modules! [setupVirtualEnv]")
                        break
                else:
                    Upgrade.stdOut("Project dependant modules installed successfully!!")
                    break

            try:
                command = "systemctl stop gunicorn.socket"
                subprocess.call(shlex.split(command))
            except:
                pass

            try:
                command = "virtualenv --system-site-packages /usr/local/CyberCP"
                subprocess.call(shlex.split(command))
            except:
                pass

            Upgrade.stdOut('Virtual enviroment for CyberPanel successfully installed.')

        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [setupVirtualEnv]")
            os._exit(0)

    @staticmethod
    def upgradeOpenLiteSpeed():
        try:
            ##
            count = 0
            while (1):
                command = "yum upgrade -y openlitespeed"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to upgrade OpenLiteSpeed, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to upgrade OpenLiteSpeed! [upgradeOpenLiteSpeed]")
                else:
                    Upgrade.stdOut("OpenLiteSpeed successfully upgraded!")
                    break

            ##

        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [upgradeOpenLiteSpeed]")
            os._exit(0)

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

            try:
                command = 'systemctl daemon-reload'
                subprocess.call(shlex.split(command))
            except:
                pass

            try:
                command = 'systemctl restart gunicorn.socket'
                subprocess.call(shlex.split(command))
            except:
                pass

        except BaseException, msg:
            Upgrade.stdOut(str(msg) + " [updateGunicornConf]")
            os._exit(0)

    @staticmethod
    def fileManager():
        ## Copy File manager files

        count = 1
        while (1):
            command = "rm -rf /usr/local/lsws/Example/html/FileManager"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                Upgrade.stdOut(
                    "Trying to remove old File manager files, try number: " + str(count))
                if count == 3:
                    Upgrade.stdOut("Failed to remove old File manager files! [upgrade]")
                    os._exit(0)
            else:
                Upgrade.stdOut("Old File Manager files successfully removed!")
                break

        count = 1
        while (1):
            command = "mv /usr/local/CyberCP/install/FileManager /usr/local/lsws/Example/html"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                Upgrade.stdOut(
                    "Trying to upgrade File manager, try number: " + str(count))
                if count == 3:
                    Upgrade.stdOut("Failed to upgrade File manager! [upgrade]")
                    os._exit(0)
            else:
                Upgrade.stdOut("File manager successfully upgraded!")
                break

        try:
            command = "chmod -R 777 /usr/local/lsws/Example/html/FileManager"
            subprocess.call(shlex.split(command))
        except:
            pass

    @staticmethod
    def setupCLI():
        try:
            try:
                command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
                subprocess.call(shlex.split(command))
            except:
                pass

            try:
                command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
                subprocess.call(shlex.split(command))
            except:
                pass

        except OSError, msg:
            try:
                command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
                subprocess.call(shlex.split(command))
            except:
                pass

            Upgrade.stdOut(str(msg) + " [setupCLI]")
            return 0

    @staticmethod
    def staticContent():
        count = 1
        while (1):
            command = "rm -rf /usr/local/lscp/cyberpanel/static"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                Upgrade.stdOut(
                    "Trying to remove old static content, try number: " + str(count))
                if count == 3:
                    Upgrade.stdOut("Failed to remove old static content! [upgrade]")
                    os._exit(0)
            else:
                Upgrade.stdOut("Static content successfully removed!")
                break

        count = 1
        while (1):
            command = "mv /usr/local/CyberCP/static /usr/local/lscp/cyberpanel"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                Upgrade.stdOut(
                    "Trying to update static content, try number: " + str(count))
                if count == 3:
                    Upgrade.stdOut("Failed to update static content! [upgrade]")
                    os._exit(0)
            else:
                Upgrade.stdOut("Static content in place!")
                break

    @staticmethod
    def upgradeVersion():
        vers = version.objects.get(pk=1)
        getVersion = requests.get('https://cyberpanel.net/version.txt')
        latest = getVersion.json()
        vers.currentVersion = latest['version']
        vers.build = latest['build']
        vers.save()

    @staticmethod
    def applyLoginSystemMigrations():
        try:

            cwd = os.getcwd()
            os.chdir('/usr/local/CyberCP')

            try:
                command = "echo 'CREATE TABLE `loginSystem_acl` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL UNIQUE, `adminStatus` integer NOT NULL DEFAULT 0, `versionManagement` integer NOT NULL DEFAULT 0, `createNewUser` integer NOT NULL DEFAULT 0, `deleteUser` integer NOT NULL DEFAULT 0, `resellerCenter` integer NOT NULL DEFAULT 0, `changeUserACL` integer NOT NULL DEFAULT 0, `createWebsite` integer NOT NULL DEFAULT 0, `modifyWebsite` integer NOT NULL DEFAULT 0, `suspendWebsite` integer NOT NULL DEFAULT 0, `deleteWebsite` integer NOT NULL DEFAULT 0, `createPackage` integer NOT NULL DEFAULT 0, `deletePackage` integer NOT NULL DEFAULT 0, `modifyPackage` integer NOT NULL DEFAULT 0, `createDatabase` integer NOT NULL DEFAULT 0, `deleteDatabase` integer NOT NULL DEFAULT 0, `listDatabases` integer NOT NULL DEFAULT 0, `createNameServer` integer NOT NULL DEFAULT 0, `createDNSZone` integer NOT NULL DEFAULT 0, `deleteZone` integer NOT NULL DEFAULT 0, `addDeleteRecords` integer NOT NULL DEFAULT 0, `createEmail` integer NOT NULL DEFAULT 0, `deleteEmail` integer NOT NULL DEFAULT 0, `emailForwarding` integer NOT NULL DEFAULT 0, `changeEmailPassword` integer NOT NULL DEFAULT 0, `dkimManager` integer NOT NULL DEFAULT 0, `createFTPAccount` integer NOT NULL DEFAULT 0, `deleteFTPAccount` integer NOT NULL DEFAULT 0, `listFTPAccounts` integer NOT NULL DEFAULT 0, `createBackup` integer NOT NULL DEFAULT 0, `restoreBackup` integer NOT NULL DEFAULT 0, `addDeleteDestinations` integer NOT NULL DEFAULT 0, `scheDuleBackups` integer NOT NULL DEFAULT 0, `remoteBackups` integer NOT NULL DEFAULT 0, `manageSSL` integer NOT NULL DEFAULT 0, `hostnameSSL` integer NOT NULL DEFAULT 0, `mailServerSSL` integer NOT NULL DEFAULT 0);' | python manage.py dbshell"
                subprocess.check_output(command, shell=True)
            except:
                pass

            try:
                command = "echo 'ALTER TABLE loginSystem_administrator ADD acl_id integer;' | python manage.py dbshell"
                subprocess.call(command, shell=True)
            except:
                pass

            try:
                command = "echo 'ALTER TABLE loginSystem_administrator ADD FOREIGN KEY (acl_id) REFERENCES loginSystem_acl(id);' | python manage.py dbshell"
                subprocess.check_output(command, shell=True)
            except:
                pass

            dbName = settings.DATABASES['default']['NAME']
            dbUser = settings.DATABASES['default']['USER']
            password = settings.DATABASES['default']['PASSWORD']
            host = settings.DATABASES['default']['HOST']
            port = settings.DATABASES['default']['PORT']

            if len(port) == 0:
                port = '3306'

            try:
                passwordCMD = "use " + dbName+";insert into loginSystem_acl (id, name, adminStatus) values (1,'admin',1);"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";insert into loginSystem_acl (id, name, adminStatus, createNewUser, deleteUser, createWebsite, resellerCenter, modifyWebsite, suspendWebsite, deleteWebsite, createPackage, deletePackage, modifyPackage, createNameServer, restoreBackup) values (2,'reseller',0,1,1,1,1,1,1,1,1,1,1,1,1);"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";insert into loginSystem_acl (id, name, createDatabase, deleteDatabase, listDatabases, createDNSZone, deleteZone, addDeleteRecords, createEmail, deleteEmail, emailForwarding, changeEmailPassword, dkimManager, createFTPAccount, deleteFTPAccount, listFTPAccounts, createBackup, manageSSL) values (3,'user', 1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1);"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";UPDATE loginSystem_administrator SET  acl_id = 3;"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";UPDATE loginSystem_administrator SET  acl_id = 1 where userName = 'admin';"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";alter table loginSystem_administrator drop initUserAccountsLimit;"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";CREATE TABLE `websiteFunctions_aliasdomains` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `aliasDomain` varchar(75) NOT NULL);"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";ALTER TABLE `websiteFunctions_aliasdomains` ADD COLUMN `master_id` integer NOT NULL;"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            try:
                passwordCMD = "use " + dbName + ";ALTER TABLE `websiteFunctions_aliasdomains` ADD CONSTRAINT `websiteFunctions_ali_master_id_726c433d_fk_websiteFu` FOREIGN KEY (`master_id`) REFERENCES `websiteFunctions_websites` (`id`);"
                command = 'sudo mysql --host=' + host + ' --port=' + port + ' -u ' + dbUser + ' -p' + password + ' -e "' + passwordCMD + '"'
                cmd = shlex.split(command)
                subprocess.call(cmd)
            except:
                pass

            os.chdir(cwd)

        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [applyLoginSystemMigrations]")
            os._exit(0)

    @staticmethod
    def mailServerMigrations():
        try:
            os.chdir('/usr/local/CyberCP')
            try:
                command = "echo 'ALTER TABLE e_forwardings DROP PRIMARY KEY;ALTER TABLE e_forwardings ADD id INT AUTO_INCREMENT PRIMARY KEY;' | python manage.py dbshell"
                subprocess.check_output(command, shell=True)
            except:
                pass
            try:
                command = "python manage.py makemigrations emailPremium"
                subprocess.call(shlex.split(command))
            except:
                pass
            try:
                command = "python manage.py migrate emailPremium"
                subprocess.call(shlex.split(command))
            except:
                pass
        except:
            pass

    @staticmethod
    def emailMarketingMigrationsa():
        try:
            os.chdir('/usr/local/CyberCP')
            try:
                command = "python manage.py makemigrations emailMarketing"
                subprocess.call(shlex.split(command))
            except:
                pass
            try:
                command = "python manage.py migrate emailMarketing"
                subprocess.call(shlex.split(command))
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
    def downloadAndUpgrade(Version, versionNumbring):
        try:
            ## Download latest version.

            count = 0
            while (1):
                command = "wget https://cyberpanel.net/CyberPanel." + versionNumbring
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Downloading latest version, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to download latest version! [upgrade]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("Latest version successfully downloaded!")
                    break

            ## Backup settings file.

            Upgrade.stdOut("Backing up settings file.")

            shutil.copy("/usr/local/CyberCP/CyberCP/settings.py", "/usr/local/settings.py")

            Upgrade.stdOut("Settings file backed up.")

            if os.path.exists('/usr/local/CyberCP/bin'):
                shutil.rmtree('/usr/local/CyberCP/bin')

            ## Extract Latest files

            count = 1
            while (1):
                command = "tar zxf CyberPanel." + versionNumbring
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to extract new version, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to extract new version! [upgrade]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("New version successfully extracted!")
                    break

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


            Upgrade.stdOut('Restoring settings file!')


            writeToFile = open("/usr/local/CyberCP/CyberCP/settings.py", 'w')

            for items in data:
                if items.find("'filemanager',") > -1:
                    writeToFile.writelines(items)
                    if pluginCheck == 1:
                        writeToFile.writelines("    'pluginHolder',\n")
                    if emailMarketing == 1:
                        writeToFile.writelines("    'emailMarketing',\n")
                    if Version.currentVersion == '1.6':
                        writeToFile.writelines("    'emailPremium',\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            Upgrade.stdOut('Settings file restored!')

            ## Move static files

            Upgrade.staticContent()

            ## Upgrade File Manager

            Upgrade.fileManager()
        except:
            pass


    @staticmethod
    def installPYDNS():
        try:
            command = "pip install pydns"
            res = subprocess.call(shlex.split(command))
        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [installPYDNS]")
            return 0

    @staticmethod
    def installTLDExtract():
        try:
            count = 0
            while (1):
                command = "pip install tldextract"

                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to install tldextract, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut(
                            "Failed to install tldextract! [installTLDExtract]")
                        break
                else:
                    Upgrade.stdOut("tldextract successfully installed!  [pip]")
                    Upgrade.stdOut("tldextract successfully installed!  [pip]")
                    break
        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [installTLDExtract]")
            return 0

    @staticmethod
    def installLSCPD():
        try:

            Upgrade.stdOut("Starting LSCPD installation..")

            count = 0

            while(1):
                command = 'yum -y install gcc gcc-c++ make autoconf glibc rcs'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut("Trying to install LSCPD prerequisites, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to install LSCPD prerequisites.")
                        os._exit(0)
                else:
                    Upgrade.stdOut("LSCPD prerequisites successfully installed!")
                    break

            count = 0

            while(1):
                command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel which curl'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut("Trying to install LSCPD prerequisites, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to install LSCPD prerequisites.")
                        os._exit(0)
                else:
                    Upgrade.stdOut("LSCPD prerequisites successfully installed!")
                    break

            command = 'wget https://cyberpanel.net/lscp.tar.gz'
            cmd = shlex.split(command)
            subprocess.call(cmd)

            count = 0

            while(1):

                command = 'tar zxf lscp.tar.gz -C /usr/local/'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut("Trying to configure LSCPD, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut("Failed to configure LSCPD, exiting installer! [installLSCPD]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("LSCPD successfully configured!")
                    break

            try:
                os.remove("/usr/local/lscp/fcgi-bin/lsphp")
                shutil.copy("/usr/local/lsws/lsphp70/bin/lsphp","/usr/local/lscp/fcgi-bin/lsphp")
            except:
                pass

            command = 'adduser lscpd -M -d /usr/local/lscp'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            command = 'groupadd lscpd'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            command = 'usermod -a -G lscpd lscpd'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            command = 'usermod -a -G lsadm lscpd'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            command = 'chown -R lscpd:lscpd /usr/local/lscp/cyberpanel'
            cmd = shlex.split(command)
            subprocess.call(cmd)

            command = 'systemctl daemon-reload'
            cmd = shlex.split(command)
            subprocess.call(cmd)

            command = 'systemctl restart lscpd'
            cmd = shlex.split(command)
            subprocess.call(cmd)

            Upgrade.stdOut("LSCPD successfully installed!")
            Upgrade.stdOut("LSCPD successfully installed!")

        except OSError, msg:
            Upgrade.stdOut(str(msg) + " [installLSCPD]")
            return 0
        except ValueError, msg:
            Upgrade.stdOut(str(msg) + " [installLSCPD]")
            return 0

        return 1

    @staticmethod
    def upgrade():

        os.chdir("/usr/local")

        ## Current Version

        Version = version.objects.get(pk=1)

        try:
            command = "systemctl stop gunicorn.socket"
            subprocess.call(shlex.split(command))
        except:
            pass
        try:
            command = "systemctl stop lscpd"
            subprocess.call(shlex.split(command))
        except:
            pass

        ##

        versionNumbring = Upgrade.downloadLink()


        if os.path.exists('/usr/local/CyberPanel.' + versionNumbring):
            os.remove('/usr/local/CyberPanel.' + versionNumbring)

        if float(Version.currentVersion) < 1.6:
            Upgrade.stdOut('Upgrades works for version 1.6 onwards.')
            os._exit(0)

        ##
        Upgrade.installPYDNS()
        Upgrade.downloadAndUpgrade(Version, versionNumbring)


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
        Upgrade.enableServices()

        ## Upgrade OpenLiteSpeed

        Upgrade.upgradeOpenLiteSpeed()
        Upgrade.setupCLI()
        Upgrade.installLSCPD()
        time.sleep(3)

        ## Upgrade version

        Upgrade.upgradeVersion()

        try:
            command = "systemctl start lscpd"
            subprocess.call(shlex.split(command))
        except:
            pass

        Upgrade.stdOut("Upgrade Completed.")



Upgrade.upgrade()
