import time
import thread
import tarfile
import os
import shlex
import subprocess
from shutil import rmtree
import requests

class Upgrade:
    logPath = "/usr/local/lscp/logs/upgradeLog"


    @staticmethod
    def upgrade(currentVersion,currentBuild):

        upgradeLog = open(Upgrade.logPath,"w")

        if os.path.exists("/usr/local/CyberCP.tar.gz"):
            path = "/usr/local/CyberCP.tar.gz"
            command = 'wget http://cyberpanel.net/CyberCP.tar.gz'
            tarOpen = "CyberCP.tar.gz"
        else:
            path = "/usr/local/CyberPanel.1.4.tar.gz"
            command = 'wget http://cyberpanel.net/CyberPanel.1.4.tar.gz'
            tarOpen = "CyberPanel.1.4.tar.gz"



        settings = "/usr/local/CyberCP/CyberCP/settings.py"

        try:
            data = open(settings,'r').readlines()
        except:
            pass

        if os.path.exists(path):
            os.remove(path)

        if os.path.exists("/usr/local/CyberCP"):
            rmtree("/usr/local/CyberCP")

        ## Downloading CyberCP

        upgradeLog.writelines("Started download for latest Version.. \n")


        cmd = shlex.split(command)

        res = subprocess.call(cmd)


        ## Extracting latest version


        upgradeLog.writelines("Extracting Latest version.. \n")

        tar = tarfile.open(tarOpen)
        tar.extractall("/usr/local")
        tar.close()

        if os.path.exists("/usr/local/lscp/cyberpanel/static"):
            rmtree("/usr/local/lscp/cyberpanel/static")

        command = 'mv /usr/local/CyberCP/static /usr/local/lscp/cyberpanel'

        cmd = shlex.split(command)

        res = subprocess.call(cmd)


        ## Adjusting settings

        try:
            upgradeLog.writelines("Fixing Settings.. \n")

            writeToFile = open(settings,'w')

            for items in data:
                writeToFile.writelines(items)

            writeToFile.close()
        except:
            pass

        command = 'systemctl restart gunicorn.socket'

        cmd = shlex.split(command)

        res = subprocess.call(cmd)


        upgradeLog.writelines("Upgrade Completed")


        r = requests.post("http://localhost:5003/base/upgradeVersion")

        upgradeLog.writelines(r.text+"\n")

        upgradeLog.close()


        print("Upgrade Completed.")

    @staticmethod
    def initiateUpgrade(currentVersion,currentBuild):
        thread.start_new_thread(Upgrade.upgrade, (currentVersion, currentBuild))

Upgrade.upgrade("1","1")