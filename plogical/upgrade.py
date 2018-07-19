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
                        Upgrade.InstallLog.writeToFile(
                            "Failed to install project dependant modules! [setupVirtualEnv]")
                        break
                else:
                    Upgrade.stdOut("Project dependant modules installed successfully!!")
                    break

            command = "systemctl stop gunicorn.socket"
            res = subprocess.call(shlex.split(command))

            command = "virtualenv --system-site-packages /usr/local/CyberCP"
            res = subprocess.call(shlex.split(command))


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


            command = 'systemctl daemon-reload'
            subprocess.call(shlex.split(command))

            command = 'systemctl restart gunicorn.socket'
            subprocess.call(shlex.split(command))

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

        command = "chmod -R 777 /usr/local/lsws/Example/html/FileManager"
        subprocess.call(shlex.split(command))

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
    def upgrade():

        os.chdir("/usr/local")

        ## Current Version

        Version = version.objects.get(pk=1)

        ##

        versionNumbring = Upgrade.downloadLink()

        if float(Version.currentVersion) < 1.6:
            Upgrade.stdOut('Upgrades works for version 1.6 onwards.')
            os._exit(0)

        ## RC Check

        rcCheck = 1

        if os.path.exists('/usr/local/CyberCP/postfixSenderPolicy'):
            rcCheck = 0

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

        shutil.copy("/usr/local/CyberCP/CyberCP/settings.py","/usr/local/settings.py")

        Upgrade.stdOut("Settings file backed up.")

        ## Remove Core Files

        count = 1
        while (1):
            command = "rm -rf /usr/local/CyberCP"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                Upgrade.stdOut(
                    "Trying to remove old version, trying again, try number: " + str(count))
                if count == 3:
                    Upgrade.stdOut("Failed to remove old version! [upgrade]")
                    os._exit(0)
            else:
                Upgrade.stdOut("Old version successfully removed!")
                break

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

        Upgrade.stdOut('Restoring settings file!')


        data = open("/usr/local/settings.py", 'r').readlines()
        writeToFile = open("/usr/local/CyberCP/CyberCP/settings.py", 'w')

        for items in data:
            if items.find("'filemanager',") > -1:
                writeToFile.writelines(items)
                if Version.currentVersion == '1.6':
                    writeToFile.writelines("    'emailPremium'\n")
            else:
                writeToFile.writelines(items)

        writeToFile.close()

        Upgrade.stdOut('Settings file restored!')

        ## Move static files

        Upgrade.staticContent()

        ## Upgrade File Manager

        Upgrade.fileManager()


        ## Install TLDExtract

        count = 1
        while (1):
            command = "pip install tldextract"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                Upgrade.stdOut(
                    "Trying to install tldextract, trying again, try number: " + str(count))
                if count == 3:
                    Upgrade.stdOut(
                        "Failed to install tldextract! [upgrade]")
                    os._exit(0)
            else:
                Upgrade.stdOut("tldextract successfully installed!  [pip]")
                break



        ## Install dnspython

        #command = "pip install dnspython"
        #subprocess.call(shlex.split(command))


        ## MailServer Model Changes

        if Version.currentVersion == '1.6' and rcCheck :
            os.chdir('/usr/local/CyberCP')

            count = 1
            while (1):
                command = "echo 'ALTER TABLE e_forwardings DROP PRIMARY KEY;ALTER TABLE e_forwardings ADD id INT AUTO_INCREMENT PRIMARY KEY;' | python manage.py dbshell"
                res = subprocess.check_output(command, shell=True)

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to patch database for email forwarding, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut(
                            "Failed to patch database for email forwarding! [upgrade]")
                        os._exit(0)

                else:
                    Upgrade.stdOut("Database successfully patched for email forwarding!")
                    break

            count = 1
            while (1):
                command = "python manage.py makemigrations emailPremium"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to setup migration file for email limits, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut(
                            "Failed to setup migration file for email limits! [upgrade]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("Migrations file for email limits successfully prepared!")
                    break

            count = 1
            while (1):
                command = "python manage.py migrate emailPremium"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    Upgrade.stdOut(
                        "Trying to execute migration file for email limits, trying again, try number: " + str(count))
                    if count == 3:
                        Upgrade.stdOut(
                            "Failed to execute migration file for email limits! [upgrade]")
                        os._exit(0)
                else:
                    Upgrade.stdOut("Migrations file for email limits successfully executed!")
                    break


        Upgrade.stdOut('Setting up virtual enviroment for CyberPanel.')
        Upgrade.setupVirtualEnv()
        Upgrade.stdOut('Virtual enviroment for CyberPanel successfully installed.')
        if Version.currentVersion == '1.6':
            Upgrade.updateGunicornConf()
        command = 'systemctl restart gunicorn.socket'
        subprocess.call(shlex.split(command))


        ## Upgrade OpenLiteSpeed

        Upgrade.upgradeOpenLiteSpeed()
        time.sleep(3)

        ## Upgrade version

        Upgrade.upgradeVersion()


        Upgrade.stdOut("Upgrade Completed.")



Upgrade.upgrade()