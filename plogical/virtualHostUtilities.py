#!/usr/local/CyberCP/bin/python2
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import shutil
import argparse
import installUtilities
import sslUtilities
from os.path import join
from os import listdir, rmdir
from shutil import move
from multiprocessing import Process
from websiteFunctions.models import Websites, ChildDomains, aliasDomains
from loginSystem.models import Administrator
from packages.models import Package
import subprocess
import shlex
from plogical.mailUtilities import mailUtilities
import CyberCPLogFileWriter as logging
from dnsUtilities import DNS
from vhost import vhost
from applicationInstaller import ApplicationInstaller
from acl import ACLManager
from processUtilities import ProcessUtilities

## If you want justice, you have come to the wrong place.


class virtualHostUtilities:

    Server_root = "/usr/local/lsws"
    cyberPanel = "/usr/local/CyberCP"
    @staticmethod
    def createVirtualHost(virtualHostName, administratorEmail, phpVersion, virtualHostUser, ssl,
                          dkimCheck, openBasedir, websiteOwner, packageName, tempStatusPath = '/home/cyberpanel/fakePath'):
        try:

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Running some checks..,0')

            ####### Limitations check

            admin = Administrator.objects.get(userName=websiteOwner)

            if ACLManager.websitesLimitCheck(admin, 1) == 0:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'You\'ve reached maximum websites limit as a reseller. [404]')
                return 0, 'You\'ve reached maximum websites limit as a reseller.'

            ####### Limitations Check End

            if Websites.objects.filter(domain=virtualHostName).count() > 0:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'This website already exists. [404]')
                return 0, "This website already exists."

            if ChildDomains.objects.filter(domain=virtualHostName).count() > 0:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'This website already exists as child domain. [404]')
                return 0, "This website already exists as child domain."

            ####### Limitations Check End

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Creating DNS records..,10')

            ##### Zone creation

            DNS.dnsTemplate(virtualHostName, admin)

            ## Zone creation

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Setting up directories..,25')

            if vhost.checkIfVirtualHostExists(virtualHostName) == 1:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Virtual Host Directory already exists. [404]')
                return 0, "Virtual Host Directory already exists!"

            if vhost.checkIfAliasExists(virtualHostName) == 1:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'This domain exists as Alias. [404]')
                return 0, "This domain exists as Alias."

            if dkimCheck == 1:
                if mailUtilities.checkIfDKIMInstalled() == 0:
                    raise BaseException("OpenDKIM is not installed, install OpenDKIM from DKIM Manager.")

                retValues = mailUtilities.setupDKIM(virtualHostName)
                if retValues[0] == 0:
                    raise BaseException(retValues[1])

            retValues = vhost.createDirectoryForVirtualHost(virtualHostName, administratorEmail,
                                                                           virtualHostUser, phpVersion, openBasedir)
            if retValues[0] == 0:
                raise BaseException(retValues[1])

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Creating configurations..,50')

            retValues = vhost.createConfigInMainVirtualHostFile(virtualHostName)
            if retValues[0] == 0:
                raise BaseException(retValues[1])

            selectedPackage = Package.objects.get(packageName=packageName)

            website = Websites(admin=admin, package=selectedPackage, domain=virtualHostName,
                               adminEmail=administratorEmail,
                               phpSelection=phpVersion, ssl=ssl, externalApp=virtualHostUser)

            website.save()


            if ssl == 1:
                sslPath = "/home/" + virtualHostName + "/public_html"
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Setting up SSL..,70')
                installUtilities.installUtilities.reStartLiteSpeed()
                retValues = sslUtilities.issueSSLForDomain(virtualHostName, administratorEmail, sslPath)
                if retValues[0] == 0:
                    raise BaseException(retValues[1])
                else:
                    installUtilities.installUtilities.reStartLiteSpeed()

            if ssl == 0:
                installUtilities.installUtilities.reStartLiteSpeed()

            vhost.finalizeVhostCreation(virtualHostName, virtualHostUser)

            ## Create Configurations ends here

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'DKIM Setup..,90')


            ## DKIM Check

            if dkimCheck == 1:
                DNS.createDKIMRecords(virtualHostName)

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Website successfully created. [200]')

            return 1, 'None'

        except BaseException, msg:
            vhost.deleteVirtualHostConfigurations(virtualHostName)
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [createVirtualHost]")
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + " [404]")
            return 0, str(msg)

    @staticmethod
    def issueSSL(virtualHost, path, adminEmail):
        try:

            retValues = sslUtilities.issueSSLForDomain(virtualHost, adminEmail, path)

            if retValues[0] == 0:
                print "0," + str(retValues[1])
                return 0, str(retValues[1])

            installUtilities.installUtilities.reStartLiteSpeed()

            print "1,None"
            return 1, None

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [issueSSL]")
            print "0," + str(msg)
            return 0, str(msg)

    @staticmethod
    def getAccessLogs(fileName, page):
        try:

            numberOfTotalLines = int(subprocess.check_output(["wc", "-l", fileName]).split(" ")[0])

            if numberOfTotalLines < 25:
                data = subprocess.check_output(["cat", fileName])
            else:
                if page == 1:
                    end = numberOfTotalLines
                    start = end - 24
                    if start <= 0:
                        start = 1
                    startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                    command = "sed -n " + startingAndEnding + " " + fileName
                    proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    data = proc.stdout.read()
                else:
                    end = numberOfTotalLines - ((page - 1) * 25)
                    start = end - 24
                    if start <= 0:
                        start = 1
                    startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                    command = "sed -n " + startingAndEnding + " " + fileName
                    proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    data = proc.stdout.read()
            print data
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [getAccessLogs]")
            print "1,None"

    @staticmethod
    def getErrorLogs(fileName, page):
        try:

            numberOfTotalLines = int(subprocess.check_output(["wc", "-l", fileName]).split(" ")[0])

            if numberOfTotalLines < 25:
                data = subprocess.check_output(["cat", fileName])
            else:
                if page == 1:
                    end = numberOfTotalLines
                    start = end - 24
                    if start <= 0:
                        start = 1
                    startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                    command = "sed -n " + startingAndEnding + " " + fileName
                    proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    data = proc.stdout.read()
                else:
                    end = numberOfTotalLines - ((page - 1) * 25)
                    start = end - 24
                    if start <= 0:
                        start = 1
                    startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                    command = "sed -n " + startingAndEnding + " " + fileName
                    proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    data = proc.stdout.read()
            print data
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [getErrorLogs]")
            print "1,None"

    @staticmethod
    def saveVHostConfigs(fileName, tempPath):
        try:

            vhost = open(fileName, "w")

            vhost.write(open(tempPath, "r").read())

            vhost.close()

            if os.path.exists(tempPath):
                os.remove(tempPath)

            installUtilities.installUtilities.reStartLiteSpeed()

            print "1,None"

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveVHostConfigs]")
            print "0," + str(msg)

    @staticmethod
    def saveRewriteRules(virtualHost, fileName, tempPath):
        try:

            vhost.addRewriteRules(virtualHost, fileName)

            vhostFile = open(fileName, "w")
            vhostFile.write(open(tempPath, "r").read())
            vhostFile.close()

            if os.path.exists(tempPath):
                os.remove(tempPath)

            installUtilities.installUtilities.reStartLiteSpeed()

            print "1,None"

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveRewriteRules]")
            print "0," + str(msg)

    @staticmethod
    def installWordPress(domainName, finalPath, virtualHostUser, dbName, dbUser, dbPassword):
        try:

            FNULL = open(os.devnull, 'w')

            if not os.path.exists(finalPath):
                os.makedirs(finalPath)

            ## checking for directories/files

            dirFiles = os.listdir(finalPath)

            if len(dirFiles) == 1:
                if dirFiles[0] == ".well-known":
                    pass
                else:
                    print "0,Target directory should be empty before installation, otherwise data loss could occur."
                    return
            elif len(dirFiles) == 0:
                pass
            else:
                print "0,Target directory should be empty before installation, otherwise data loss could occur."
                return

            ## Get wordpress


            if not os.path.exists("latest.tar.gz"):
                command = 'wget --no-check-certificate http://wordpress.org/latest.tar.gz -O latest.tar.gz'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            command = 'tar -xzvf latest.tar.gz -C ' + finalPath

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            ## Get plugin

            if not os.path.exists("litespeed-cache.1.1.5.1.zip"):
                command = 'wget --no-check-certificate https://downloads.wordpress.org/plugin/litespeed-cache.1.1.5.1.zip'

                cmd = shlex.split(command)

                res = subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            command = 'unzip litespeed-cache.1.1.5.1.zip -d ' + finalPath

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            root = finalPath

            for filename in listdir(join(root, 'wordpress')):
                move(join(root, 'wordpress', filename), join(root, filename))

            rmdir(root + "wordpress")

            shutil.copytree(finalPath + "litespeed-cache", finalPath + "wp-content/plugins/litespeed-cache")
            shutil.rmtree(finalPath + "litespeed-cache")

            ## edit config file

            wpconfigfile = finalPath + "wp-config-sample.php"

            data = open(wpconfigfile, "r").readlines()

            writeDataToFile = open(wpconfigfile, "w")

            defDBName = "define('DB_NAME', '" + dbName + "');" + "\n"
            defDBUser = "define('DB_USER', '" + dbUser + "');" + "\n"
            defDBPassword = "define('DB_PASSWORD', '" + dbPassword + "');" + "\n"

            for items in data:
                if items.find("DB_NAME") > -1:
                    if items.find("database_name_here") > -1:
                        writeDataToFile.writelines(defDBName)
                elif items.find("DB_USER") > -1:
                    if items.find("username_here") > -1:
                        writeDataToFile.writelines(defDBUser)
                elif items.find("DB_PASSWORD") > -1:
                    writeDataToFile.writelines(defDBPassword)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            os.rename(wpconfigfile, finalPath + 'wp-config.php')

            command = "chown -R " + virtualHostUser + ":" + virtualHostUser + " " + "/home/" + domainName + "/public_html/"

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            vhost.addRewriteRules(domainName)

            installUtilities.installUtilities.reStartLiteSpeed()

            print "1,None"


        except BaseException, msg:
            # remove the downloaded files
            try:

                shutil.rmtree(finalPath)
            except:
                logging.CyberCPLogFileWriter.writeToFile("shutil.rmtree(finalPath)")

            homeDir = "/home/" + domainName + "/public_html"

            if not os.path.exists(homeDir):
                FNULL = open(os.devnull, 'w')
                os.mkdir(homeDir)
                command = "chown -R " + virtualHostUser + ":" + virtualHostUser + " " + homeDir
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            print "0," + str(msg)
            return

    @staticmethod
    def installJoomla(domainName, finalPath, virtualHostUser, dbName, dbUser, dbPassword, username, password, prefix,
                      sitename, tempStatusPath):
        try:

            extraArgs = {}
            extraArgs['domainName'] = domainName
            extraArgs['finalPath'] = finalPath
            extraArgs['virtualHostUser'] = virtualHostUser
            extraArgs['dbName'] = dbName
            extraArgs['dbUser'] = dbUser
            extraArgs['dbPassword'] = dbPassword
            extraArgs['username'] = username
            extraArgs['password'] = password
            extraArgs['prefix'] = prefix
            extraArgs['sitename'] = sitename
            extraArgs['tempStatusPath'] = tempStatusPath

            background = ApplicationInstaller('joomla', extraArgs)
            background.start()


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [installJoomla]')

    @staticmethod
    def issueSSLForHostName(virtualHost, path):
        try:

            destPrivKey = "/usr/local/lscp/key.pem"
            destCert = "/usr/local/lscp/cert.pem"

            pathToStoreSSLFullChain = '/etc/letsencrypt/live/' + virtualHost + '/fullchain.pem'
            pathToStoreSSLPrivKey = '/etc/letsencrypt/live/' + virtualHost + '/privkey.pem'

            ## removing old certs for lscpd
            if os.path.exists(destPrivKey):
                os.remove(destPrivKey)
            if os.path.exists(destCert):
                os.remove(destCert)



            adminEmail = "email@" + virtualHost

            if not os.path.exists(pathToStoreSSLFullChain):
                retValues = sslUtilities.issueSSLForDomain(virtualHost, adminEmail, path)

                if retValues[0] == 0:
                    print "0," + str(retValues[1])
                    return 0, retValues[1]

            shutil.copy(pathToStoreSSLPrivKey, destPrivKey)
            shutil.copy(pathToStoreSSLFullChain, destCert)

            command = 'systemctl restart lscpd'
            cmd = shlex.split(command)
            subprocess.call(cmd)

            print "1,None"
            return 1,'None'


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [issueSSLForHostName]")
            print "0," + str(msg)
            return 0, str(msg)

    @staticmethod
    def issueSSLForMailServer(virtualHost, path):
        try:

            srcFullChain = '/etc/letsencrypt/live/' + virtualHost + '/fullchain.pem'
            srcPrivKey = '/etc/letsencrypt/live/' + virtualHost + '/privkey.pem'

            if not os.path.exists(srcFullChain):
                adminEmail = "email@" + virtualHost
                retValues = sslUtilities.issueSSLForDomain(virtualHost, adminEmail, path)

                if retValues[0] == 0:
                    print "0," + str(retValues[1])
                    return 0, retValues[1]

            ## MailServer specific functions

            if os.path.exists("/etc/postfix/cert.pem"):
                os.remove("/etc/postfix/cert.pem")

            if os.path.exists("/etc/postfix/key.pem"):
                os.remove("/etc/postfix/key.pem")

            if os.path.exists("/etc/pki/dovecot/private/dovecot.pem"):
                os.remove("/etc/pki/dovecot/private/dovecot.pem")

            if os.path.exists("/etc/pki/dovecot/certs/dovecot.pem"):
                os.remove("/etc/pki/dovecot/certs/dovecot.pem")

            if os.path.exists("/etc/dovecot/key.pem"):
                os.remove("/etc/dovecot/key.pem")

            if os.path.exists("/etc/dovecot/cert.pem"):
                os.remove("/etc/dovecot/cert.pem")

            ## Postfix

            shutil.copy(srcPrivKey, "/etc/postfix/key.pem")
            shutil.copy(srcFullChain, "/etc/postfix/cert.pem")

            ## Dovecot

            shutil.copy(srcPrivKey, "/etc/pki/dovecot/private/dovecot.pem")
            shutil.copy(srcFullChain, "/etc/pki/dovecot/certs/dovecot.pem")

            ## Dovecot 2ND

            shutil.copy(srcPrivKey, "/etc/dovecot/key.pem")
            shutil.copy(srcFullChain, "/etc/dovecot/cert.pem")

            ## Update postmaster address dovecot

            filePath = "/etc/dovecot/dovecot.conf"

            data = open(filePath, 'r').readlines()

            writeFile = open(filePath, 'w')

            for items in data:
                if items.find('postmaster_address') > -1:
                    writeFile.writelines('    postmaster_address = postmaster@' + virtualHost + '\n')
                else:
                    writeFile.writelines(items)

            writeFile.close()

            ## Update myhostname address postfix

            filePath = "/etc/postfix/main.cf"

            data = open(filePath, 'r').readlines()

            writeFile = open(filePath, 'w')

            for items in data:
                if items.find('myhostname') > -1:
                    writeFile.writelines('myhostname = ' + virtualHost + '\n')
                else:
                    writeFile.writelines(items)

            writeFile.close()

            p = Process(target=mailUtilities.restartServices, args=())
            p.start()

            print "1,None"
            return 1,'None'

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [issueSSLForHostName]")
            print "0," + str(msg)
            return 0,str(msg)

    @staticmethod
    def createAlias(masterDomain, aliasDomain, ssl, sslPath, administratorEmail, owner=None):
        try:

            admin = Administrator.objects.get(userName=owner)
            DNS.dnsTemplate(aliasDomain, admin)


            if vhost.checkIfAliasExists(aliasDomain) == 1:
                print "0, This domain already exists as vHost or Alias."
                return

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")
                data = open(confPath, 'r').readlines()
                writeToFile = open(confPath, 'w')
                listenerTrueCheck = 0

                for items in data:
                    if items.find("listener") > -1 and items.find("Default") > -1:
                        listenerTrueCheck = 1
                    if items.find(' ' + masterDomain) > -1 and items.find('map') > -1 and listenerTrueCheck == 1:
                        data = filter(None, items.split(" "))
                        if data[1] == masterDomain:
                            writeToFile.writelines(items.rstrip('\n') + ", " + aliasDomain + "\n")
                            listenerTrueCheck = 0
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()
            else:
                completePathToConf = virtualHostUtilities.Server_root + '/conf/vhosts/' + masterDomain + '/vhost.conf'
                data = open(completePathToConf, 'r').readlines()

                writeToFile = open(completePathToConf, 'w')

                for items in data:
                    if items.find('ServerAlias') > -1:
                        items = items.strip('\n')
                        writeToFile.writelines(items + " " + aliasDomain + "\n")
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()

            installUtilities.installUtilities.reStartLiteSpeed()

            if ssl == 1:
                retValues = sslUtilities.issueSSLForDomain(masterDomain, administratorEmail, sslPath, aliasDomain)
                if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                    if retValues[0] == 0:
                        print "0," + str(retValues[1])
                        return
                    else:
                        vhost.createAliasSSLMap(confPath, masterDomain, aliasDomain)
                else:
                    retValues = sslUtilities.issueSSLForDomain(masterDomain, administratorEmail, sslPath, aliasDomain)
                    if retValues[0] == 0:
                        print "0," + str(retValues[1])
                        return

            website = Websites.objects.get(domain=masterDomain)

            newAlias = aliasDomains(master=website, aliasDomain = aliasDomain)
            newAlias.save()

            print "1,None"

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [createAlias]")
            print "0," + str(msg)

    @staticmethod
    def issueAliasSSL(masterDomain, aliasDomain, sslPath, administratorEmail):
        try:

            retValues = sslUtilities.issueSSLForDomain(masterDomain, administratorEmail, sslPath, aliasDomain)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")
                if retValues[0] == 0:
                    print "0," + str(retValues[1])
                    return
                else:
                    vhost.createAliasSSLMap(confPath, masterDomain, aliasDomain)
            else:
                if retValues[0] == 0:
                    print "0," + str(retValues[1])
                    return

            print "1,None"

        except BaseException, msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [issueAliasSSL]")
            print "0," + str(msg)

    @staticmethod
    def deleteAlias(masterDomain, aliasDomain):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

                data = open(confPath, 'r').readlines()
                writeToFile = open(confPath, 'w')
                aliases = []

                for items in data:
                    if items.find(masterDomain) > -1 and items.find('map') > -1:
                        data = filter(None, items.split(" "))
                        if data[1] == masterDomain:
                            length = len(data)
                            for i in range(3, length):
                                currentAlias = data[i].rstrip(',').strip('\n')
                                if currentAlias != aliasDomain:
                                    aliases.append(currentAlias)

                            aliasString = ""

                            for alias in aliases:
                                aliasString = ", " + alias

                            writeToFile.writelines(
                                '  map                     ' + masterDomain + " " + masterDomain + aliasString + "\n")
                            aliases = []
                            aliasString = ""
                        else:
                            writeToFile.writelines(items)

                    else:
                        writeToFile.writelines(items)

                writeToFile.close()
                installUtilities.installUtilities.reStartLiteSpeed()

                delAlias = aliasDomains.objects.get(aliasDomain=aliasDomain)
                delAlias.delete()

                print "1,None"
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [deleteAlias]")
                print "0," + str(msg)
        else:
            try:

                completePathToConf = virtualHostUtilities.Server_root + '/conf/vhosts/' + masterDomain + '/vhost.conf'
                data = open(completePathToConf, 'r').readlines()

                writeToFile = open(completePathToConf, 'w')

                for items in data:
                    if items.find('ServerAlias') > -1:
                        writeToFile.writelines(items.replace(' ' + aliasDomain, ''))
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()
                installUtilities.installUtilities.reStartLiteSpeed()

                alias = aliasDomains.objects.get(aliasDomain=aliasDomain)
                alias.delete()

                print "1,None"
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [deleteAlias]")
                print "0," + str(msg)

    @staticmethod
    def changeOpenBasedir(domainName, openBasedirValue):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domainName
                completePathToConfigFile = confPath + "/vhost.conf"

                data = open(completePathToConfigFile, 'r').readlines()


                if openBasedirValue == 'Disable':
                    writeToFile = open(completePathToConfigFile, 'w')
                    for items in data:
                        if items.find('php_admin_value') > -1:
                            continue
                        writeToFile.writelines(items)
                    writeToFile.close()
                else:

                    ## Check if phpini already active

                    fileManagerCheck = 0

                    writeToFile = open(completePathToConfigFile, 'w')
                    for items in data:

                        if items.find('context /.filemanager') > -1:
                            writeToFile.writelines(items)
                            fileManagerCheck = 1
                            continue

                        if items.find('phpIniOverride') > -1:
                            writeToFile.writelines(items)
                            if fileManagerCheck == 1:
                                writeToFile.writelines('php_admin_value open_basedir "/tmp:/usr/local/lsws/Example/html/FileManager:$VH_ROOT"\n')
                                fileManagerCheck = 0
                                continue
                            else:
                                writeToFile.writelines('php_admin_value open_basedir "/tmp:$VH_ROOT"\n')
                                continue

                        writeToFile.writelines(items)

                    writeToFile.close()

                installUtilities.installUtilities.reStartLiteSpeed()
                print "1,None"
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [changeOpenBasedir]")
                print "0," + str(msg)
        else:
            try:
                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domainName
                completePathToConfigFile = confPath + "/vhost.conf"

                data = open(completePathToConfigFile, 'r').readlines()

                if openBasedirValue == 'Disable':
                    writeToFile = open(completePathToConfigFile, 'w')
                    for items in data:
                        if items.find('open_basedir') > -1:
                            continue
                        writeToFile.writelines(items)
                    writeToFile.close()
                else:

                    ## Check if phpini already active
                    path = ''

                    try:
                        childDomain = ChildDomains.objects.get(domain=domainName)
                        path = childDomain.path
                    except:
                        path = '/home/' + domainName + '/public_html'

                    activate = 0
                    writeToFile = open(completePathToConfigFile, 'w')
                    for items in data:
                        if items.find('CustomLog ') > -1:
                            activate = 1
                            writeToFile.writelines(items)
                            continue

                        if activate == 1:
                            activate = 0
                            if items.find('open_basedir') > -1:
                                writeToFile.writelines(items)
                                continue
                            else:
                                writeToFile.writelines(
                                    '        php_admin_value open_basedir /usr/local/lsws/FileManager:/tmp:' + path + '\n')
                                writeToFile.writelines(items)
                                continue
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()

                installUtilities.installUtilities.reStartLiteSpeed()
                print "1,None"
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [changeOpenBasedir]")
                print "0," + str(msg)

    @staticmethod
    def saveSSL(virtualHost, keyPath, certPath):
        try:

            pathToStoreSSL = '/etc/letsencrypt/live/' + virtualHost

            command = 'mkdir -p ' + pathToStoreSSL
            subprocess.call(shlex.split(command))

            pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
            pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

            privkey = open(pathToStoreSSLPrivKey, 'w')
            privkey.write(open(keyPath, "r").read())
            privkey.close()

            fullchain = open(pathToStoreSSLFullChain, 'w')
            fullchain.write(open(certPath, "r").read())
            fullchain.close()

            os.remove(keyPath)
            os.remove(certPath)


            sslUtilities.sslUtilities.installSSLForDomain(virtualHost)

            installUtilities.installUtilities.reStartLiteSpeed()

            FNULL = open(os.devnull, 'w')

            command = "chown " + "lsadm" + ":" + "lsadm" + " " + pathToStoreSSL
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            print "1,None"

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveSSL]")
            print "0," + str(msg)

    @staticmethod
    def createDomain(masterDomain, virtualHostName, phpVersion, path, ssl, dkimCheck, openBasedir, owner, tempStatusPath = '/home/cyberpanel/fakePath'):
        try:

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Running some checks..,0')

            ## Check if this domain either exists as website or child domain

            admin = Administrator.objects.get(userName=owner)
            DNS.dnsTemplate(virtualHostName, admin)


            if Websites.objects.filter(domain=virtualHostName).count() > 0:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'This Domain already exists as a website. [404]')
                return 0, "This Domain already exists as a website."

            if ChildDomains.objects.filter(domain=virtualHostName).count() > 0:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'This domain already exists as child domain. [404]')
                return 0, "This domain already exists as child domain."

            ####### Limitations check

            master = Websites.objects.get(domain=masterDomain)
            domainsInPackage = master.package.allowedDomains

            if domainsInPackage == 0:
                pass
            elif domainsInPackage > master.childdomains_set.all().count():
                pass
            else:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath,
                                                          'Exceeded maximum number of domains for this package. [404]')
                return 0, "Exceeded maximum number of domains for this package"


            ####### Limitations Check End


            if vhost.checkIfVirtualHostExists(virtualHostName) == 1:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath,'Virtual Host Directory already exists. [404]')
                return 0, "Virtual Host Directory already exists!"

            if vhost.checkIfAliasExists(virtualHostName) == 1:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath,'This domain exists as Alias. [404]')
                return 0, "This domain exists as Alias."


            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'DKIM Setup..,30')

            if dkimCheck == 1:
                if mailUtilities.checkIfDKIMInstalled() == 0:
                    raise BaseException("OpenDKIM is not installed, install OpenDKIM from DKIM Manager.")

                retValues = mailUtilities.setupDKIM(virtualHostName)
                if retValues[0] == 0:
                    raise BaseException(retValues[1])

            FNULL = open(os.devnull, 'w')

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Creating configurations..,50')

            retValues = vhost.createDirectoryForDomain(masterDomain, virtualHostName, phpVersion, path,
                                                             master.adminEmail, master.externalApp, openBasedir)
            if retValues[0] == 0:
                raise BaseException(retValues[1])

            retValues = vhost.createConfigInMainDomainHostFile(virtualHostName, masterDomain)

            if retValues[0] == 0:
                raise BaseException(retValues[1])

            ## Now restart litespeed after initial configurations are done

            website = ChildDomains(master=master, domain=virtualHostName, path=path, phpSelection=phpVersion, ssl=ssl)
            website.save()

            if ssl == 1:
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Creating SSL..,50')
                installUtilities.installUtilities.reStartLiteSpeed()
                retValues = sslUtilities.issueSSLForDomain(virtualHostName, master.adminEmail, path)
                installUtilities.installUtilities.reStartLiteSpeed()
                if retValues[0] == 0:
                    raise BaseException(retValues[1])

            ## Final Restart
            if ssl == 0:
                installUtilities.installUtilities.reStartLiteSpeed()

            vhost.finalizeDomainCreation(master.externalApp, path)

            ## DKIM Check

            if dkimCheck == 1:
                DNS.createDKIMRecords(virtualHostName)


            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Domain successfully created. [200]')
            return 1, "None"

        except BaseException, msg:
            numberOfWebsites = Websites.objects.count() + ChildDomains.objects.count()
            vhost.deleteCoreConf(virtualHostName, numberOfWebsites)
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + ". [404]")
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [createDomain]")
            return 0, str(msg)

    @staticmethod
    def deleteDomain(virtualHostName):
        try:

            numberOfWebsites = Websites.objects.count() + ChildDomains.objects.count()
            vhost.deleteCoreConf(virtualHostName, numberOfWebsites)
            delWebsite = ChildDomains.objects.get(domain=virtualHostName)
            delWebsite.delete()
            installUtilities.installUtilities.reStartLiteSpeed()

            print "1,None"
            return 1,'None'

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [deleteDomain]")
            print "0," + str(msg)
            return 0,str(msg)

    @staticmethod
    def getDiskUsage(path, totalAllowed):
        try:

            totalUsageInMB = subprocess.check_output(["sudo", "du", "-hs", path, "--block-size=1M"]).split()[0]

            percentage = float(100) / float(totalAllowed)

            percentage = float(percentage) * float(totalUsageInMB)

            data = [int(totalUsageInMB), int(percentage)]
            return data
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [getDiskUsage]")
            return [int(0), int(0)]

    @staticmethod
    def permissionControl(path):
        try:
            command = 'sudo chown -R  cyberpanel:cyberpanel ' + path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def leaveControl(path):
        try:
            command = 'sudo chown -R  root:root ' + path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--virtualHostName', help='Domain name!')
    parser.add_argument('--administratorEmail', help='Administration Email!')
    parser.add_argument('--phpVersion', help='PHP Version')
    parser.add_argument("--virtualHostUser", help="Virtual Host Directory Owner and Group!")
    parser.add_argument("--numberOfSites", help="Number of sites!")
    parser.add_argument("--ssl", help="Weather to activate SSL")
    parser.add_argument("--sslPath", help="Path to website document root!")
    parser.add_argument('--dkimCheck', help='To enable or disable DKIM support for domain.')
    parser.add_argument('--openBasedir', help='To enable or disable open_basedir protection for domain.')
    parser.add_argument('--websiteOwner', help='Website Owner Name')
    parser.add_argument('--package', help='Website package')
    parser.add_argument('--restore', help='Restore Check.')


    ## arguments for creation child domains

    parser.add_argument('--masterDomain', help='Master Domain Needed While Creating Child Domains!')
    parser.add_argument('--path', help='Path Needed for Child domains Creation!')
    parser.add_argument('--restart', help='OLS Restart Frequency while child domain creation!')

    ## arguments for logs

    parser.add_argument('--page', help='Page number to fetch logs!')

    ## arguments for configuration files

    parser.add_argument('--tempPath', help='Temporary path where configuration data is placed!')


    ## save ssl arguments

    parser.add_argument('--tempKeyPath', help='Temporary path to store key!')
    parser.add_argument('--tempCertPath', help='Temporary path to store cert!')
    parser.add_argument('--sslCheck', help='Weather SSL is already activated or not!')

    ## install wordpress arguments

    parser.add_argument('--dbName', help='Database Name!')
    parser.add_argument('--dbUser', help='Database User!')
    parser.add_argument('--dbPassword', help='Database Password!')

    ## calculate bw arguments

    parser.add_argument('--bandwidth', help='Pack Bandwidth!')

    ## extras
    parser.add_argument('--username', help='Admin Username!')
    parser.add_argument('--password', help='Admin Password!')
    parser.add_argument('--prefix', help='Database Prefix!')
    parser.add_argument('--sitename', help='Site Name!')

    ## Arguments for alias domain

    parser.add_argument('--aliasDomain', help='Alias Domain!')

    ## Arguments for OpenBasedir

    parser.add_argument('--openBasedirValue', help='open_base dir protection value!')
    parser.add_argument('--tempStatusPath', help='Temporary Status file path.')

    args = parser.parse_args()

    if args.function == "createVirtualHost":
        try:
            dkimCheck = int(args.dkimCheck)
        except:
            dkimCheck = 0

        try:
            openBasedir = int(args.openBasedir)
        except:
            openBasedir = 0

        try:
            tempStatusPath = args.tempStatusPath
        except:
            tempStatusPath = '/home/cyberpanel/fakePath'

        virtualHostUtilities.createVirtualHost(args.virtualHostName, args.administratorEmail, args.phpVersion, args.virtualHostUser, int(args.ssl), dkimCheck, openBasedir, args.websiteOwner, args.package, tempStatusPath)
    elif args.function == "deleteVirtualHostConfigurations":
        vhost.deleteVirtualHostConfigurations(args.virtualHostName)
    elif args.function == "createDomain":
        try:
            dkimCheck = int(args.dkimCheck)
        except:
            dkimCheck = 0

        try:
            openBasedir = int(args.openBasedir)
        except:
            openBasedir = 0

        try:
            tempStatusPath = args.tempStatusPath
        except:
            tempStatusPath = '/home/cyberpanel/fakePath'

        virtualHostUtilities.createDomain(args.masterDomain, args.virtualHostName, args.phpVersion, args.path, int(args.ssl), dkimCheck, openBasedir, args.websiteOwner, tempStatusPath)
    elif args.function == "issueSSL":
        virtualHostUtilities.issueSSL(args.virtualHostName,args.path,args.administratorEmail)
    elif args.function == "changePHP":
        vhost.changePHP(args.path,args.phpVersion)
    elif args.function == "getAccessLogs":
        virtualHostUtilities.getAccessLogs(args.path,int(args.page))
    elif args.function == "getErrorLogs":
        virtualHostUtilities.getErrorLogs(args.path,int(args.page))
    elif args.function == "saveVHostConfigs":
        virtualHostUtilities.saveVHostConfigs(args.path,args.tempPath)
    elif args.function == "saveRewriteRules":
        virtualHostUtilities.saveRewriteRules(args.virtualHostName,args.path,args.tempPath)
    elif args.function == "saveSSL":
        virtualHostUtilities.saveSSL(args.virtualHostName,args.tempKeyPath,args.tempCertPath)
    elif args.function == "installWordPress":
        virtualHostUtilities.installWordPress(args.virtualHostName,args.path,args.virtualHostUser,args.dbName,args.dbUser,args.dbPassword)
    elif args.function == "installJoomla":
        virtualHostUtilities.installJoomla(args.virtualHostName,args.path,args.virtualHostUser,args.dbName,args.dbUser,args.dbPassword,args.username,args.password,args.prefix,args.sitename, args.tempStatusPath)
    elif args.function == "issueSSLForHostName":
        virtualHostUtilities.issueSSLForHostName(args.virtualHostName,args.path)
    elif args.function == "issueSSLForMailServer":
        virtualHostUtilities.issueSSLForMailServer(args.virtualHostName,args.path)
    elif args.function == "findDomainBW":
        vhost.findDomainBW(args.virtualHostName, int(args.bandwidth))
    elif args.function == 'createAlias':
        virtualHostUtilities.createAlias(args.masterDomain,args.aliasDomain,int(args.ssl),args.sslPath, args.administratorEmail, args.websiteOwner)
    elif args.function == 'issueAliasSSL':
        virtualHostUtilities.issueAliasSSL(args.masterDomain, args.aliasDomain, args.sslPath, args.administratorEmail)
    elif args.function == 'deleteAlias':
        virtualHostUtilities.deleteAlias(args.masterDomain, args.aliasDomain)
    elif args.function == 'changeOpenBasedir':
        virtualHostUtilities.changeOpenBasedir(args.virtualHostName, args.openBasedirValue)
    elif args.function == 'deleteDomain':
        virtualHostUtilities.deleteDomain(args.virtualHostName)

if __name__ == "__main__":
    main()
