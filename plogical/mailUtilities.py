import os.path
import shutil
import CyberCPLogFileWriter as logging
import subprocess
import argparse
import shlex


class mailUtilities:

    installLogPath = "/home/cyberpanel/modSecInstallLog"

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

    @staticmethod
    def generateKeys(domain):
        try:

            result = mailUtilities.setupDKIM(domain)
            if result[0] == 0:
                raise BaseException(result[1])
            else:
                print "1,None"

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [generateKeys]")
            print "0," + str(msg)


    @staticmethod
    def configureOpenDKIM():
            try:

                ## Configure OpenDKIM specific settings

                openDKIMConfigurePath = "/etc/opendkim.conf"

                configData = """
Mode	sv
Canonicalization	relaxed/simple
KeyTable	refile:/etc/opendkim/KeyTable
SigningTable	refile:/etc/opendkim/SigningTable
ExternalIgnoreList	refile:/etc/opendkim/TrustedHosts
InternalHosts	refile:/etc/opendkim/TrustedHosts
"""

                writeToFile = open(openDKIMConfigurePath, 'a')
                writeToFile.write(configData)
                writeToFile.close()

                ## Configure postfix specific settings

                postfixFilePath = "/etc/postfix/main.cf"

                configData = """
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = $smtpd_milters
milter_default_action = accept
"""

                writeToFile = open(postfixFilePath, 'a')
                writeToFile.write(configData)
                writeToFile.close()

                #### Restarting Postfix and OpenDKIM

                command = "systemctl start opendkim"
                subprocess.call(shlex.split(command))

                command = "systemctl enable opendkim"
                subprocess.call(shlex.split(command))

                ##

                command = "systemctl start postfix"
                subprocess.call(shlex.split(command))

                print "1,None"
                return



            except OSError, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [configureOpenDKIM]")
                print "0," + str(msg)
                return
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [configureOpenDKIM]")
                print "0," + str(msg)
            return

    @staticmethod
    def installOpenDKIM(install, openDKIMINstall):
        try:

            command = 'sudo yum install opendkim -y'

            cmd = shlex.split(command)

            with open(mailUtilities.installLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            if res == 1:
                writeToFile = open(mailUtilities.installLogPath, 'a')
                writeToFile.writelines("Can not be installed.[404]\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                return 0
            else:
                writeToFile = open(mailUtilities.installLogPath, 'a')
                writeToFile.writelines("OpenDKIM Installed.[200]\n")
                writeToFile.close()

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installOpenDKIM]")


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--domain', help='Domain name!')


    args = parser.parse_args()

    if args.function == "createEmailAccount":
        mailUtilities.createEmailAccount(args.domain)
    elif args.function == "generateKeys":
        mailUtilities.generateKeys(args.domain)
    elif args.function == "configureOpenDKIM":
        mailUtilities.configureOpenDKIM()

if __name__ == "__main__":
    main()