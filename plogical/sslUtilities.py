import CyberCPLogFileWriter as logging
from virtualHostUtilities import virtualHostUtilities
import shutil
import pexpect
import os
import sys
import shlex
import subprocess

class sslUtilities:

    @staticmethod
    def installSSLForDomain(virtualHostName):

        pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHostName

        confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + virtualHostName
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
                sslProtocol = "  sslProtocol             31" + "\n"
                map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"
                final = "}" + "\n" + "\n"

                writeDataToFile.writelines("\n")
                writeDataToFile.writelines("\n")
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
                writeDataToFile.writelines("\n")
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
                    sslProtocol = "  sslProtocol             31" + "\n"
                    final = "}"

                    writeSSLConfig.writelines("\n")
                    writeSSLConfig.writelines("\n")
                    writeSSLConfig.writelines("\n")

                    writeSSLConfig.writelines(vhssl)
                    writeSSLConfig.writelines(keyFile)
                    writeSSLConfig.writelines(certFile)
                    writeSSLConfig.writelines(certChain)
                    writeSSLConfig.writelines(sslProtocol)
                    writeSSLConfig.writelines(final)


                    writeSSLConfig.writelines("\n")
                    writeSSLConfig.writelines("\n")
                    writeSSLConfig.writelines("\n")

                    writeSSLConfig.close()





        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [createConfigInMainVirtualHostFile]]")
            return 0
        return 1



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
    def obtainSSLForADomain(virtualHostName,adminEmail,sslpath):

        try:

            #if virtualHostName.count(".")==1:
            #    command = "certbot certonly -n --agree-tos --email " + adminEmail + " --webroot -w " + sslpath + " -d " + virtualHostName + " -d www." + virtualHostName
            #else:
            #    command = "certbot certonly -n --agree-tos --email " + adminEmail + " --webroot -w " + sslpath + " -d " + virtualHostName


            command = "certbot certonly -n --agree-tos --email " + adminEmail + " --webroot -w " + sslpath + " -d " + virtualHostName



            expectation = []

            expectation.append("not exist or is not a directory") #0
            expectation.append("Congratulations!") #1
            expectation.append("no action taken.") #2
            expectation.append("you should also verify") #3
            expectation.append("that you are serving files from the webroot path") #4
            expectation.append("Enter email address") #5
            expectation.append("There were too many requests") # 6

            try:

                obtainSSL = pexpect.spawn(command)

                index = obtainSSL.expect(expectation)

                obtainSSL.logfile = sys.stdout

                if index==0:
                    obtainSSL.kill(0)
                    return "Directory Error 1"
                elif index==1:
                    logging.CyberCPLogFileWriter.writeToFile(virtualHostName + " SSL OK")
                elif index==2:
                    logging.CyberCPLogFileWriter.writeToFile(virtualHostName + " SSL OK")
                elif index==3:

                    pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHostName

                    try:
                        os.mkdir(pathToStoreSSL)
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(
                            str(msg) + " [Can not create directory to store SSL [obtainSSLForADomain]]")

                    pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                    pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"


                    command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                    return 1
                elif index == 4:

                    pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHostName

                    try:
                        os.mkdir(pathToStoreSSL)
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(
                            str(msg) + " [Can not create directory to stroe SSL [obtainSSLForADomain]]")

                    pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                    pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

                    command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                    return 1
                elif index ==5 :
                    obtainSSL.sendline(adminEmail)

                    expectation = "(A)gree/(C)ancel:"
                    obtainSSL.expect(expectation)
                    obtainSSL.sendline("A")

                    expectation = "(Y)es/(N)o:"
                    obtainSSL.expect(expectation)
                    obtainSSL.sendline("Y")

                    expectation = "(Y)es/(N)o:"
                    obtainSSL.expect(expectation)
                    obtainSSL.sendline("Y")

                    expectation = []

                    expectation.append("not exist or is not a directory")  # 0
                    expectation.append("Congratulations!")  # 1
                    expectation.append("no action taken.")  # 2

                    index = obtainSSL.expect(expectation)

                    if index==0:
                        obtainSSL.kill(0)
                        return "Directory Error 2"
                    elif index==1:
                        logging.CyberCPLogFileWriter.writeToFile(virtualHostName + " SSL OK")
                    elif index==2:
                        logging.CyberCPLogFileWriter.writeToFile(virtualHostName + " SSL OK")

                elif index==6:
                    return "Too many SSL requests for this domain, please try to get SSL at later time."


            except pexpect.EOF,msg:
                logging.CyberCPLogFileWriter.writeToFile("#######################################")
                logging.CyberCPLogFileWriter.writeToFile(str(obtainSSL.before))
                logging.CyberCPLogFileWriter.writeToFile("#######################################")
                logging.CyberCPLogFileWriter.writeToFile(str(obtainSSL.after))
                logging.CyberCPLogFileWriter.writeToFile("#######################################")

                pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHostName

                try:
                    os.mkdir(pathToStoreSSL)
                except BaseException, msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        str(msg) + " [Can not create directory to stroe SSL [obtainSSLForADomain]]")

                pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

                command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain

                cmd = shlex.split(command)

                res = subprocess.call(cmd)


                return 1

            except pexpect.TIMEOUT, msg:
                logging.CyberCPLogFileWriter.writeToFile("#######################################")
                logging.CyberCPLogFileWriter.writeToFile(str(obtainSSL.before))
                logging.CyberCPLogFileWriter.writeToFile("#######################################")
                logging.CyberCPLogFileWriter.writeToFile(str(obtainSSL.after))
                logging.CyberCPLogFileWriter.writeToFile("#######################################")

                pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHostName

                try:
                    os.mkdir(pathToStoreSSL)
                except BaseException, msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        str(msg) + " [Can not create directory to stroe SSL [obtainSSLForADomain]]")

                pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

                command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                return 1



            ###### Copy SSL To config location ######


            pathToStoreSSL = virtualHostUtilities.Server_root+"/conf/vhosts/" +"SSL-"+virtualHostName


            try:
                os.mkdir(pathToStoreSSL)
            except BaseException,msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Directory for SSL already exists.. Continuing [obtainSSLForADomain]]")


            srcPrivKey = "/etc/letsencrypt/live/" + virtualHostName + "/privkey.pem"
            srcFullChain = "/etc/letsencrypt/live/" + virtualHostName + "/fullchain.pem"

            pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
            pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

            shutil.copy(srcPrivKey, pathToStoreSSLPrivKey)
            shutil.copy(srcFullChain, pathToStoreSSLFullChain)

            return 1
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [obtainSSLForADomain]]")
            return 0