import CyberCPLogFileWriter as logging
import subprocess
import shlex

class modSec:
    installLogPath = "/home/cyberpanel/modSecInstallLog"

    @staticmethod
    def installModSec(install, modSecInstall):
        try:

            command = 'sudo yum install ols-modsecurity -y'

            cmd = shlex.split(command)

            with open(modSec.installLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            if res == 1:
                writeToFile = open(modSec.installLogPath, 'a')
                writeToFile.writelines("Can not be installed.[404]\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                return 0
            else:
                writeToFile = open(modSec.installLogPath, 'a')
                writeToFile.writelines("ModSecurity Installed.[200]\n")
                writeToFile.close()

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installModSec]")