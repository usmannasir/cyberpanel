import CyberCPLogFileWriter as logging
import subprocess
import shlex
import argparse
from virtualHostUtilities import virtualHostUtilities
import os
import tarfile
import shutil
from mailUtilities import mailUtilities

class CSF:
    installLogPath = "/home/cyberpanel/csfInstallLog"
    csfURL = 'https://download.configserver.com/csf.tgz'

    @staticmethod
    def installCSF(install, csfInstall):
        try:

            mailUtilities.checkHome()

            ##

            command = 'sudo wget ' + CSF.csfURL
            cmd = shlex.split(command)

            with open(CSF.installLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            ##

            command = 'sudo tar -xzf csf.tgz'
            cmd = shlex.split(command)

            with open(CSF.installLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            ##

            os.chdir('csf')
            
            command = 'sudo ./install.sh'
            cmd = shlex.split(command)

            with open(CSF.installLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            os.chdir('/usr/local/CyberCP')

            writeToFile = open(CSF.installLogPath, 'a')
            writeToFile.writelines("CSF successfully Installed.[200]\n")
            writeToFile.close()

            command = 'sudo rm -rf csf'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            command = 'sudo rm -f csf.tgz'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            return 1
        except BaseException, msg:
            command = 'sudo rm -rf csf'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            command = 'sudo rm -f csf.tgz'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installModSec]")



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument('--tempConfigPath', help='Temporary path to configurations data!')
    parser.add_argument('--packName', help='ModSecurity supplier name!')
    parser.add_argument('--fileName', help='Filename to enable or disable!')

    args = parser.parse_args()

    if args.function == "installModSecConfigs":
        modSec.installModSecConfigs()
    elif args.function == "saveModSecConfigs":
        modSec.saveModSecConfigs(args.tempConfigPath)
    elif args.function == "saveModSecRules":
        modSec.saveModSecRules()
    elif args.function == "setupOWASPRules":
        modSec.setupOWASPRules()
    elif args.function == "installOWASP":
        modSec.installOWASP()
    elif args.function == "disableOWASP":
        modSec.disableOWASP()
    elif args.function == "setupComodoRules":
        modSec.setupComodoRules()
    elif args.function == "installComodo":
        modSec.installComodo()
    elif args.function == "disableComodo":
        modSec.disableComodo()
    elif args.function == "disableRuleFile":
        modSec.disableRuleFile(args.fileName, args.packName)
    elif args.function == "enableRuleFile":
        modSec.enableRuleFile(args.fileName, args.packName)

if __name__ == "__main__":
    main()