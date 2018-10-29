import CyberCPLogFileWriter as logging
import shutil
import os
import shlex
import subprocess
import socket

class sslUtilities:

    Server_root = "/usr/local/lsws"

    @staticmethod
    def checkIfSSLMap(virtualHostName):
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()

            sslCheck = 0

            for items in data:
                if items.find("listener") >-1 and items.find("SSL") > -1:
                    sslCheck = 1
                    continue
                if sslCheck == 1:
                    if items.find("}") > -1:
                        return 0
                if items.find(virtualHostName) > -1 and sslCheck == 1:
                    data = filter(None, items.split(" "))
                    if data[1] == virtualHostName:
                        return 1

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [checkIfSSLMap]]")
            return 0

    @staticmethod
    def checkSSLListener():
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            for items in data:
                if items.find("listener SSL") > -1:
                    return 1

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [checkSSLListener]]")
            return str(msg)
        return 0

    @staticmethod
    def getDNSRecords(virtualHostName):
        try:

            withoutWWW = socket.gethostbyname(virtualHostName)
            withWWW = socket.gethostbyname('www.' + virtualHostName)

            return [1, withWWW, withoutWWW]

        except BaseException, msg:
            return [0, "347 " + str(msg) + " [issueSSLForDomain]"]

    @staticmethod
    def installSSLForDomain(virtualHostName):

        confPath = sslUtilities.Server_root + "/conf/vhosts/" + virtualHostName
        completePathToConfigFile = confPath + "/vhost.conf"

        try:
            map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"

            if sslUtilities.checkSSLListener() != 1:

                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                listener = "listener SSL {" + "\n"
                address = "  address                 *:443" + "\n"
                secure = "  secure                  1" + "\n"
                keyFile = "  keyFile                  /etc/letsencrypt/live/" + virtualHostName + "/privkey.pem\n"
                certFile = "  certFile                 /etc/letsencrypt/live/" + virtualHostName + "/fullchain.pem\n"
                certChain = "  certChain               1" + "\n"
                sslProtocol = "  sslProtocol             30" + "\n"
                map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"
                final = "}" + "\n" + "\n"

                writeDataToFile.writelines("\n")
                writeDataToFile.writelines(listener)
                writeDataToFile.writelines(address)
                writeDataToFile.writelines(secure)
                writeDataToFile.writelines(keyFile)
                writeDataToFile.writelines(certFile)
                writeDataToFile.writelines(certChain)
                writeDataToFile.writelines(sslProtocol)
                writeDataToFile.writelines(map)
                writeDataToFile.writelines(final)
                writeDataToFile.writelines("\n")
                writeDataToFile.close()


            else:

                if sslUtilities.checkIfSSLMap(virtualHostName) == 0:

                    data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
                    writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')
                    sslCheck = 0

                    for items in data:
                        if items.find("listener") > -1 and items.find("SSL") > -1:
                            sslCheck = 1

                        if (sslCheck == 1):
                            writeDataToFile.writelines(items)
                            writeDataToFile.writelines(map)
                            sslCheck = 0
                        else:
                            writeDataToFile.writelines(items)
                    writeDataToFile.close()

                ###################### Write per host Configs for SSL ###################

                data = open(completePathToConfigFile, "r").readlines()

                ## check if vhssl is already in vhconf file

                vhsslPresense = 0

                for items in data:
                    if items.find("vhssl") > -1:
                        vhsslPresense = 1

                if vhsslPresense == 0:
                    writeSSLConfig = open(completePathToConfigFile, "a")

                    vhssl = "vhssl  {" + "\n"
                    keyFile = "  keyFile                 /etc/letsencrypt/live/" + virtualHostName + "/privkey.pem\n"
                    certFile = "  certFile                /etc/letsencrypt/live/" + virtualHostName + "/fullchain.pem\n"
                    certChain = "  certChain               1" + "\n"
                    sslProtocol = "  sslProtocol             30" + "\n"
                    final = "}"

                    writeSSLConfig.writelines("\n")

                    writeSSLConfig.writelines(vhssl)
                    writeSSLConfig.writelines(keyFile)
                    writeSSLConfig.writelines(certFile)
                    writeSSLConfig.writelines(certChain)
                    writeSSLConfig.writelines(sslProtocol)
                    writeSSLConfig.writelines(final)

                    writeSSLConfig.writelines("\n")

                    writeSSLConfig.close()

            return 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installSSLForDomain]]")
            return 0

    @staticmethod
    def obtainSSLForADomain(virtualHostName,adminEmail,sslpath, aliasDomain = None):
        try:

            if not os.path.exists('/root/.acme.sh/acme.sh'):
                command = 'wget -O -  https://get.acme.sh | sh'
                subprocess.call(command, shell=True)

            if aliasDomain == None:

                existingCertPath = '/etc/letsencrypt/live/' + virtualHostName
                if not os.path.exists(existingCertPath):
                    command = 'mkdir -p ' + existingCertPath
                    subprocess.call(shlex.split(command))

                try:
                    logging.CyberCPLogFileWriter.writeToFile("Trying to obtain SSL for: " + virtualHostName + " and: www." + virtualHostName)

                    command = "/root/.acme.sh/acme.sh --issue -d " + virtualHostName + " -d www." + virtualHostName \
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w ' + sslpath + ' --force'

                    output = subprocess.check_output(shlex.split(command))
                    logging.CyberCPLogFileWriter.writeToFile("Successfully obtained SSL for: " + virtualHostName + " and: www." + virtualHostName)


                except subprocess.CalledProcessError:
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Failed to obtain SSL for: " + virtualHostName + " and: www." + virtualHostName)

                    try:
                        logging.CyberCPLogFileWriter.writeToFile("Trying to obtain SSL for: " + virtualHostName)
                        command = "/root/.acme.sh/acme.sh --issue -d " + virtualHostName + ' --cert-file ' + existingCertPath \
                                  + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                                  + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w ' + sslpath + ' --force'
                        output = subprocess.check_output(shlex.split(command))
                        logging.CyberCPLogFileWriter.writeToFile("Successfully obtained SSL for: " + virtualHostName)
                    except subprocess.CalledProcessError:
                        logging.CyberCPLogFileWriter.writeToFile('Failed to obtain SSL, issuing self-signed SSL for: ' + virtualHostName)
                        return 0
            else:

                existingCertPath = '/etc/letsencrypt/live/' + virtualHostName
                if not os.path.exists(existingCertPath):
                    command = 'mkdir -p ' + existingCertPath
                    subprocess.call(shlex.split(command))

                try:
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Trying to obtain SSL for: " + virtualHostName + ", www." + virtualHostName + ", " + aliasDomain + " and www." + aliasDomain + ",")

                    command = "/root/.acme.sh/acme.sh --issue -d " + virtualHostName + " -d www." + virtualHostName \
                              + ' -d ' + aliasDomain + ' -d www.' + aliasDomain\
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w ' + sslpath + ' --force'

                    output = subprocess.check_output(shlex.split(command))
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Successfully obtained SSL for: " + virtualHostName + ", www." + virtualHostName + ", " + aliasDomain + "and www." + aliasDomain + ",")


                except subprocess.CalledProcessError:
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Failed to obtain SSL for: " + virtualHostName + ", www." + virtualHostName + ", " + aliasDomain + "and www." + aliasDomain + ",")
                    return 0

            ##

            if output.find('Cert success') > -1:
                return 1
            else:
                return 0

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Failed to obtain SSL. [obtainSSLForADomain]]")
            return 0


def issueSSLForDomain(domain, adminEmail, sslpath, aliasDomain = None):
    try:

        if sslUtilities.obtainSSLForADomain(domain, adminEmail, sslpath, aliasDomain) == 1:

            if sslUtilities.installSSLForDomain(domain) == 1:
                return [1, "None"]
            else:
                return [0, "210 Failed to install SSL for domain. [issueSSLForDomain]"]
        else:
            pathToStoreSSL = "/etc/letsencrypt/live/" + domain
            command = 'mkdir -p ' + pathToStoreSSL
            subprocess.call(shlex.split(command))

            pathToStoreSSLPrivKey = "/etc/letsencrypt/live/" + domain + "/privkey.pem"
            pathToStoreSSLFullChain = "/etc/letsencrypt/live/" + domain + "/fullchain.pem"

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain
            cmd = shlex.split(command)
            subprocess.call(cmd)

            if sslUtilities.installSSLForDomain(domain) == 1:
                logging.CyberCPLogFileWriter.writeToFile("Self signed SSL issued for " + domain + ".")
                return [1, "None"]
            else:
                return [0, "220 Failed to install SSL for domain. [issueSSLForDomain]"]

    except BaseException,msg:
        return [0, "347 "+ str(msg)+ " [issueSSLForDomain]"]