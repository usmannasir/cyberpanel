import os.path
import shutil
import CyberCPLogFileWriter as logging
import subprocess
import argparse
import shlex


class mailUtilities:

    @staticmethod
    def createEmailAccount(domain):
        try:

            path = "/usr/local/CyberCP/install/rainloop/cyberpanel.net.ini"

            if not os.path.exists("/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/"):
                os.makedirs("/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/")

            finalPath = "/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/" + domain + ".ini"

            if not os.path.exists(finalPath):
                shutil.copy(path, finalPath)

            command = 'chown -R nobody:nobody /usr/local/lscp/rainloop'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            command = 'chown -R nobody:nobody /usr/local/lscp/cyberpanel/rainloop/data/_data_'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            print "1,None"

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [createEmailAccount]")
            print "0," + str(msg)


    @staticmethod
    def setupDKIM(virtualHostName):
        try:
            ## Generate DKIM Keys

            if os.path.exists("/etc/opendkim/keys/" + virtualHostName):
                return 1, "None"

            os.mkdir("/etc/opendkim/keys/" + virtualHostName)

            ## Generate keys

            command = "opendkim-genkey -D /etc/opendkim/keys/" + virtualHostName + " -d " + virtualHostName + " -s default"
            subprocess.call(shlex.split(command))

            ## Fix permissions

            command = "chown -R root:opendkim /etc/opendkim/keys/" + virtualHostName
            subprocess.call(shlex.split(command))

            command = "chmod 640 /etc/opendkim/keys/" + virtualHostName + "/default.private"
            subprocess.call(shlex.split(command))

            command = "chmod 644 /etc/opendkim/keys/" + virtualHostName + "/default.txt"
            subprocess.call(shlex.split(command))

            ## Edit key file

            keyTable = "/etc/opendkim/KeyTable"
            configToWrite = "default._domainkey." + virtualHostName + " " + virtualHostName + ":default:/etc/opendkim/keys/" + virtualHostName + "/default.private\n"

            writeToFile = open(keyTable, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Edit signing table

            signingTable = "/etc/opendkim/SigningTable"
            configToWrite = "*@" + virtualHostName + " default._domainkey." + virtualHostName + "\n"

            writeToFile = open(signingTable, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Trusted hosts

            trustedHosts = "/etc/opendkim/TrustedHosts"
            configToWrite = virtualHostName + "\n"

            writeToFile = open(trustedHosts, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Restart postfix and OpenDKIM

            command = "systemctl restart opendkim"
            subprocess.call(shlex.split(command))

            command = "systemctl restart postfix"
            subprocess.call(shlex.split(command))

            return 1, "None"

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [setupDKIM]")
            return 0, str(msg)

    @staticmethod
    def checkIfDKIMInstalled():
        try:

            path = "/etc/opendkim.conf"

            if os.path.exists(path):
                return 1
            else:
                return 0

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [checkIfDKIMInstalled]")
            return 0


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--domain', help='Domain name!')


    args = parser.parse_args()

    if args.function == "createEmailAccount":
        mailUtilities.createEmailAccount(args.domain)

if __name__ == "__main__":
    main()