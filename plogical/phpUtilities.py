import pexpect
import CyberCPLogFileWriter as logging
import subprocess
import shlex
import thread

class phpUtilities:

    @staticmethod
    def installPHPExtension(extension,extensions):
        try:

            command = 'yum install '+extension +' -y'

            cmd = shlex.split(command)

            with open('/usr/local/lscp/logs/phpExtensionRequestLog', 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            if res == 1:
                writeToFile = open('/usr/local/lscp/logs/phpExtensionRequestLog', 'a')
                writeToFile.writelines("Can not be installed.\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                return 0
            else:
                writeToFile = open('/usr/local/lscp/logs/phpExtensionRequestLog', 'a')
                writeToFile.writelines("PHP Extension Installed.\n")
                writeToFile.close()

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installPHPExtension]")

    @staticmethod
    def unInstallPHPExtension(extension,extensions):
        try:

            command = 'rpm --nodeps -e  ' + extension + ' -v'

            cmd = shlex.split(command)

            with open('/usr/local/lscp/logs/phpExtensionRequestLog', 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            if res == 1:
                writeToFile = open('/usr/local/lscp/logs/phpExtensionRequestLog', 'a')
                writeToFile.writelines("Can not un-install Extension.\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                return 0
            else:
                writeToFile = open('/usr/local/lscp/logs/phpExtensionRequestLog', 'a')
                writeToFile.writelines("PHP Extension Removed.\n")
                writeToFile.close()

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[unInstallPHPExtension]")

    @staticmethod
    def initiateInstall(extension):
        try:
            thread.start_new_thread(phpUtilities.installPHPExtension, (extension, extension))
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateInstall]")


    @staticmethod
    def initiateRemoval(extension):
        try:
            thread.start_new_thread(phpUtilities.unInstallPHPExtension, (extension, extension))
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateRestore]")