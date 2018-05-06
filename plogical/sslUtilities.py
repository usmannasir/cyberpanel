import CyberCPLogFileWriter as logging
import shutil
import os
import shlex
import subprocess
import socket

class sslUtilities:

    Server_root = "/usr/local/lsws"

    @staticmethod
    def installSSLForDomain(virtualHostName):


        pathToStoreSSL = sslUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHostName

        confPath = sslUtilities.Server_root + "/conf/vhosts/" + virtualHostName
        completePathToConfigFile = confPath + "/vhost.conf"

        try:
            map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"

            if(sslUtilities.checkSSLListener()!=1):
                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                listener = "listener SSL {" + "\n"
                address = "  address                 *:443" + "\n"
                secure = "  secure                  1" + "\n"
                keyFile = "  keyFile                 " + pathToStoreSSL + "/privkey.pem" + "\n"
                certFile = "  certFile                " + pathToStoreSSL + "/fullchain.pem" + "\n"
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
                data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')
                sslCheck = 0

                for items in data:
                    if (items.find("listener SSL")>-1):
                        sslCheck = 1

                    writeDataToFile.writelines(items)

                    if (sslCheck == 1):
                        writeDataToFile.writelines(map)
                        sslCheck = 0
                writeDataToFile.close()

                ###################### Write per host Configs for SSL ###################

                data = open(completePathToConfigFile,"r").readlines()

                ## check if vhssl is already in vhconf file

                vhsslPresense = 0

                for items in data:
                    if items.find("vhssl")>-1:
                        vhsslPresense = 1


                if vhsslPresense == 0:
                    writeSSLConfig = open(completePathToConfigFile,"a")

                    vhssl = "vhssl  {" + "\n"
                    keyFile = "  keyFile                 " + pathToStoreSSL + "/privkey.pem" + "\n"
                    certFile = "  certFile                " + pathToStoreSSL + "/fullchain.pem" + "\n"
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

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installSSLForDomain]]")
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
    def obtainSSLForADomain(virtualHostName,adminEmail,sslpath):
        try:

            ## Obtaining Server IP

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            serverIPAddress = ipData.split('\n', 1)[0]

            ## Obtaining Domain IPs

            ipRecords = sslUtilities.getDNSRecords(virtualHostName)


            if ipRecords[0] == 1:

                if serverIPAddress == ipRecords[1] and serverIPAddress == ipRecords[2]:
                    command = "certbot certonly -n --expand --agree-tos --email " + adminEmail + " --webroot -w " + sslpath + " -d " + virtualHostName + " -d www." + virtualHostName
                    logging.CyberCPLogFileWriter.writeToFile(
                        "SSL successfully issued for domain : " + virtualHostName + " and www." + virtualHostName)
                else:
                    if serverIPAddress == ipRecords[2]:
                        command = "certbot certonly -n --agree-tos --email " + adminEmail + " --webroot -w " + sslpath + " -d " + virtualHostName
                        logging.CyberCPLogFileWriter.writeToFile(
                            "SSL is issued without 'www' due to DNS error for domain : " + virtualHostName)
                    else:
                        logging.CyberCPLogFileWriter.writeToFile(
                            "DNS Records for " + virtualHostName + " does not point to this server, issuing self signed certificate.")
                        return 0
            else:
                logging.CyberCPLogFileWriter.writeToFile(
                    "Failed to obtain DNS records for " + virtualHostName + ", issuing self signed certificate.")
                return 0


            ## SSL Paths


            pathToStoreSSL = sslUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHostName

            if not os.path.exists(pathToStoreSSL):
                os.mkdir(pathToStoreSSL)

            pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
            pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

            srcPrivKey = "/etc/letsencrypt/live/" + virtualHostName + "/privkey.pem"
            srcFullChain = "/etc/letsencrypt/live/" + virtualHostName + "/fullchain.pem"

            ##

            output = subprocess.check_output(shlex.split(command))


            if output.find('Congratulations!')  > -1 or output.find('no action taken.') > -1:

                ###### Copy SSL To config location ######

                shutil.copy(srcPrivKey, pathToStoreSSLPrivKey)
                shutil.copy(srcFullChain, pathToStoreSSLFullChain)

                return 1

            elif output.find('Failed authorization procedure')  > -1:
                logging.CyberCPLogFileWriter.writeToFile('Failed authorization procedure for ' + virtualHostName + " while issuing Let's Encrypt SSL.")
                return 0
            elif output.find('Too many SSL requests for this domain, please try to get SSL at later time.') > -1:
                logging.CyberCPLogFileWriter.writeToFile(
                    'Too many SSL requests for ' + virtualHostName + " please try to get SSL at later time.")
                return 0

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Failed to obtain SSL. [obtainSSLForADomain]]")
            return 0


def issueSSLForDomain(domain,adminEmail,sslpath):
    try:

        if sslUtilities.obtainSSLForADomain(domain, adminEmail, sslpath) == 1:

            if sslUtilities.installSSLForDomain(domain) == 1:
                return [1, "None"]
            else:
                return [0, "210 Failed to install SSL for domain. [issueSSLForDomain]"]
        else:
            pathToStoreSSL = sslUtilities.Server_root + "/conf/vhosts/" + "SSL-" + domain

            if not os.path.exists(pathToStoreSSL):
                os.mkdir(pathToStoreSSL)

            pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
            pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

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
