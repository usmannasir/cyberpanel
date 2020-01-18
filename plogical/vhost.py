#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
import shutil
from plogical import installUtilities

import subprocess
import shlex
from plogical import CyberCPLogFileWriter as logging

from plogical.mysqlUtilities import mysqlUtilities
from plogical.dnsUtilities import DNS
from random import randint
from plogical.processUtilities import ProcessUtilities
from managePHP.phpManager import PHPManager
from plogical.vhostConfs import vhostConfs
from ApachController.ApacheVhosts import ApacheVhost
try:
    from websiteFunctions.models import Websites, ChildDomains, aliasDomains
    from databases.models import Databases
except:
    pass
import pwd
import grp

## If you want justice, you have come to the wrong place.


class vhost:

    Server_root = "/usr/local/lsws"
    cyberPanel = "/usr/local/CyberCP"
    redisConf = '/usr/local/lsws/conf/dvhost_redis.conf'

    @staticmethod
    def addUser(virtualHostUser, path):
        try:

            FNULL = open(os.devnull, 'w')
            if os.path.exists("/etc/lsb-release"):
                command = 'adduser --no-create-home --home ' + path + ' --disabled-login --gecos "" ' + virtualHostUser
            else:
                command = "adduser " + virtualHostUser + " -M -d " + path

            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            command = "groupadd " + virtualHostUser
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            command = "usermod -a -G " + virtualHostUser + " " + virtualHostUser
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addingUsers]")

    @staticmethod
    def createDirectories(path, virtualHostUser, pathHTML, pathLogs, confPath, completePathToConfigFile):
        try:
            FNULL = open(os.devnull, 'w')

            try:
                command = 'chmod 711 /home'
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)
            except:
                pass

            try:
                os.makedirs(path)

                command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

                command = "chmod 711 " + path
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [27 Not able create to directories for virtual host [createDirectories]]")
                return [0, "[27 Not able to directories for virtual host [createDirectories]]"]

            try:
                os.makedirs(pathHTML)

                command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + pathHTML
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [33 Not able to directories for virtual host [createDirectories]]")
                return [0, "[33 Not able to directories for virtual host [createDirectories]]"]

            try:
                os.makedirs(pathLogs)

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                    groupName = 'nobody'
                else:
                    groupName = 'nogroup'

                command = "chown %s:%s %s" % ('root', groupName, pathLogs)
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


                if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                    command = "chmod -R 750 " + pathLogs
                else:
                    command = "chmod -R 750 " + pathLogs

                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [39 Not able to directories for virtual host [createDirectories]]")
                return [0, "[39 Not able to directories for virtual host [createDirectories]]"]

            try:
                ## For configuration files permissions will be changed later globally.
                os.makedirs(confPath)
            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [45 Not able to directories for virtual host [createDirectories]]")
                return [0, "[45 Not able to directories for virtual host [createDirectories]]"]

            try:
                ## For configuration files permissions will be changed later globally.
                file = open(completePathToConfigFile, "w+")

                command = "chown " + "lsadm" + ":" + "lsadm" + " " + completePathToConfigFile
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

                command = 'chmod 600 %s' % (completePathToConfigFile)
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except IOError as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectories]]")
                return [0, "[45 Not able to directories for virtual host [createDirectories]]"]

            return [1, 'None']

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectories]")
            return [0, str(msg)]

    @staticmethod
    def finalizeVhostCreation(virtualHostName, virtualHostUser):
        try:

            FNULL = open(os.devnull, 'w')

            shutil.copy("/usr/local/CyberCP/index.html", "/home/" + virtualHostName + "/public_html/index.html")

            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + "/home/" + virtualHostName + "/public_html/index.html"
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            vhostPath = vhost.Server_root + "/conf/vhosts"

            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [finalizeVhostCreation]")

    @staticmethod
    def createDirectoryForVirtualHost(virtualHostName,administratorEmail,virtualHostUser, phpVersion, openBasedir):

        path = "/home/" + virtualHostName
        pathHTML = "/home/" + virtualHostName + "/public_html"
        pathLogs = "/home/" + virtualHostName + "/logs"
        confPath = vhost.Server_root + "/conf/vhosts/"+virtualHostName
        completePathToConfigFile = confPath +"/vhost.conf"


        ## adding user

        vhost.addUser(virtualHostUser, path)

        ## Creating Directories

        result = vhost.createDirectories(path, virtualHostUser, pathHTML, pathLogs, confPath, completePathToConfigFile)

        if result[0] == 0:
            return [0, result[1]]


        ## Creating Per vhost Configuration File


        if vhost.perHostVirtualConf(completePathToConfigFile,administratorEmail,virtualHostUser,phpVersion, virtualHostName, openBasedir) == 1:
            return [1,"None"]
        else:
            return [0,"[61 Not able to create per host virtual configurations [perHostVirtualConf]"]

    @staticmethod
    def perHostVirtualConf(vhFile, administratorEmail,virtualHostUser, phpVersion, virtualHostName, openBasedir):
        # General Configurations tab
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                confFile = open(vhFile, "w+")

                php = PHPManager.getPHPString(phpVersion)

                currentConf = vhostConfs.olsMasterConf
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{virtualHostUser}', virtualHostUser)
                currentConf = currentConf.replace('{php}', php)
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{php}', php)

                if openBasedir == 1:
                    currentConf = currentConf.replace('{open_basedir}', 'php_admin_value open_basedir "/tmp:$VH_ROOT"')
                else:
                    currentConf = currentConf.replace('{open_basedir}', '')


                confFile.write(currentConf)
                confFile.close()

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostVirtualConf]]")
                return 0
            return 1
        else:
            try:

                if not os.path.exists(vhost.redisConf):
                    confFile = open(vhFile, "w+")
                    php = PHPManager.getPHPString(phpVersion)

                    currentConf = vhostConfs.lswsMasterConf

                    currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', php)

                    confFile.write(currentConf)

                    confFile.close()

                else:
                    currentConf = vhostConfs.lswsRediConfMaster

                    currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', phpVersion.lstrip('PHP '))
                    currentConf = currentConf.replace('{uid}', str(pwd.getpwnam(virtualHostUser).pw_uid))
                    currentConf = currentConf.replace('{gid}', str(grp.getgrnam(virtualHostUser).gr_gid))

                    command = 'redis-cli set %s' % (currentConf)
                    ProcessUtilities.executioner(command)


            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostVirtualConf]]")
                return 0
            return 1

    @staticmethod
    def createNONSSLMapEntry(virtualHostName):
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

            map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"

            mapchecker = 1

            for items in data:
                if (mapchecker == 1 and (items.find("listener") > -1 and items.find("Default") > -1)):
                    writeDataToFile.writelines(items)
                    writeDataToFile.writelines(map)
                    mapchecker = 0
                else:
                    writeDataToFile.writelines(items)

            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def createConfigInMainVirtualHostFile(virtualHostName):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                if vhost.createNONSSLMapEntry(virtualHostName) == 0:
                    return [0, "Failed to create NON SSL Map Entry [createConfigInMainVirtualHostFile]"]

                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                currentConf = vhostConfs.olsMasterMainConf
                currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
                writeDataToFile.write(currentConf)

                writeDataToFile.close()

                return [1,"None"]
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]")
                return [0,"223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]
        else:
            try:
                writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'a')
                configFile = 'Include /usr/local/lsws/conf/vhosts/' + virtualHostName + '/vhost.conf\n'
                writeDataToFile.writelines(configFile)
                writeDataToFile.close()

                writeDataToFile.close()
                return [1, "None"]
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]

    @staticmethod
    def deleteVirtualHostConfigurations(virtualHostName):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                ## Deleting master conf
                numberOfSites = str(Websites.objects.count() + ChildDomains.objects.count())
                vhost.deleteCoreConf(virtualHostName, numberOfSites)

                delWebsite = Websites.objects.get(domain=virtualHostName)

                ##

                databases = Databases.objects.filter(website=delWebsite)

                childDomains = delWebsite.childdomains_set.all()

                ## Deleting child domains

                for items in childDomains:
                    numberOfSites = Websites.objects.count() + ChildDomains.objects.count()
                    vhost.deleteCoreConf(items.domain, numberOfSites)

                for items in databases:
                    mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

                delWebsite.delete()

                ## Deleting DNS Zone if there is any.

                DNS.deleteDNSZone(virtualHostName)

                if not os.path.exists(vhost.redisConf):
                    installUtilities.installUtilities.reStartLiteSpeed()

                ## Delete mail accounts

                command = "sudo rm -rf /home/vmail/" + virtualHostName
                subprocess.call(shlex.split(command))
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1
        else:
            try:
                ## Deleting master conf
                numberOfSites = str(Websites.objects.count() + ChildDomains.objects.count())
                vhost.deleteCoreConf(virtualHostName, numberOfSites)

                delWebsite = Websites.objects.get(domain=virtualHostName)

                ## Cagefs

                command = '/usr/sbin/cagefsctl --disable %s' % (delWebsite.externalApp)
                ProcessUtilities.normalExecutioner(command)

                databases = Databases.objects.filter(website=delWebsite)

                childDomains = delWebsite.childdomains_set.all()

                ## Deleting child domains

                for items in childDomains:
                    numberOfSites = Websites.objects.count() + ChildDomains.objects.count()
                    vhost.deleteCoreConf(items.domain, numberOfSites)

                for items in databases:
                    mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

                delWebsite.delete()

                ## Deleting DNS Zone if there is any.

                DNS.deleteDNSZone(virtualHostName)

                installUtilities.installUtilities.reStartLiteSpeed()

                ## Delete mail accounts

                command = "sudo rm -rf /home/vmail/" + virtualHostName
                subprocess.call(shlex.split(command))
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1

    @staticmethod
    def deleteCoreConf(virtualHostName, numberOfSites):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                virtualHostPath = "/home/" + virtualHostName
                if os.path.exists(virtualHostPath):
                    shutil.rmtree(virtualHostPath)

                confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
                if os.path.exists(confPath):
                    shutil.rmtree(confPath)

                data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()

                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

                check = 1
                sslCheck = 1

                for items in data:
                    if numberOfSites == 1:
                        if (items.find(' ' + virtualHostName) > -1 and items.find("  map                     " + virtualHostName) > -1):
                            continue
                        if (items.find(' ' + virtualHostName) > -1 and (items.find("virtualHost") > -1 or items.find("virtualhost") > -1)):
                            check = 0
                        if items.find("listener") > -1 and items.find("SSL") > -1:
                            sslCheck = 0
                        if (check == 1 and sslCheck == 1):
                            writeDataToFile.writelines(items)
                        if (items.find("}") > -1 and (check == 0 or sslCheck == 0)):
                            check = 1
                            sslCheck = 1
                    else:
                        if (items.find(' ' + virtualHostName) > -1 and items.find("  map                     " + virtualHostName) > -1):
                            continue
                        if (items.find(' ' + virtualHostName) > -1 and (items.find("virtualHost") > -1 or items.find("virtualhost") > -1)):
                            check = 0
                        if (check == 1):
                            writeDataToFile.writelines(items)
                        if (items.find("}") > -1 and check == 0):
                            check = 1

                ## Delete Apache Conf

                ApacheVhost.DeleteApacheVhost(virtualHostName)

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1
        else:
            virtualHostPath = "/home/" + virtualHostName
            try:
                shutil.rmtree(virtualHostPath)
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host directory from /home continuing..]")

            if not os.path.exists(vhost.redisConf):
                try:
                    confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
                    shutil.rmtree(confPath)
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        str(msg) + " [Not able to remove virtual host configuration directory from /conf ]")

                try:
                    data = open("/usr/local/lsws/conf/httpd.conf").readlines()

                    writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'w')

                    for items in data:
                        if items.find('/' + virtualHostName + '/') > -1:
                            pass
                        else:
                            writeDataToFile.writelines(items)

                    writeDataToFile.close()

                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                    return 0
                return 1
            else:
                command = 'redis-cli delete "vhost:%s"' % (virtualHostName)
                ProcessUtilities.executioner(command)

    @staticmethod
    def checkIfVirtualHostExists(virtualHostName):
        if os.path.exists("/home/" + virtualHostName):
            return 1
        return 0

    @staticmethod
    def changePHP(vhFile, phpVersion):
        phpDetachUpdatePath = '/home/%s/.lsphp_restart.txt' % (vhFile.split('/')[-2])
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                if ApacheVhost.changePHP(phpVersion, vhFile) == 0:
                    data = open(vhFile, "r").readlines()

                    php = PHPManager.getPHPString(phpVersion)

                    if not os.path.exists("/usr/local/lsws/lsphp" + str(php) + "/bin/lsphp"):
                        print(0, 'This PHP version is not available on your CyberPanel.')
                        return [0, "[This PHP version is not available on your CyberPanel. [changePHP]"]

                    writeDataToFile = open(vhFile, "w")

                    path = "  path                    /usr/local/lsws/lsphp" + str(php) + "/bin/lsphp\n"

                    for items in data:
                        if items.find("/usr/local/lsws/lsphp") > -1 and items.find("path") > -1:
                            writeDataToFile.writelines(path)
                        else:
                            writeDataToFile.writelines(items)

                    writeDataToFile.close()

                    writeToFile = open(phpDetachUpdatePath, 'w')
                    writeToFile.close()

                    installUtilities.installUtilities.reStartLiteSpeed()
                    try:
                        os.remove(phpDetachUpdatePath)
                    except:
                        pass
                else:
                    php = PHPManager.getPHPString(phpVersion)
                    command = "systemctl restart php%s-php-fpm" % (php)
                    ProcessUtilities.normalExecutioner(command)

                print("1,None")
                return 1,'None'
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [changePHP]")
                print(0,str(msg))
                return [0, str(msg) + " [IO Error with per host config file [changePHP]"]
        else:
            try:
                data = open(vhFile, "r").readlines()

                php = PHPManager.getPHPString(phpVersion)

                if not os.path.exists("/usr/local/lsws/lsphp" + str(php) + "/bin/lsphp"):
                    print(0, 'This PHP version is not available on your CyberPanel.')
                    return [0, "[This PHP version is not available on your CyberPanel. [changePHP]"]

                writeDataToFile = open(vhFile, "w")

                finalString = '    AddHandler application/x-httpd-php' + str(php) + ' .php\n'

                for items in data:
                    if items.find("AddHandler application/x-httpd") > -1:
                        writeDataToFile.writelines(finalString)
                    else:
                        writeDataToFile.writelines(items)

                writeDataToFile.close()

                writeToFile = open(phpDetachUpdatePath, 'w')
                writeToFile.close()

                installUtilities.installUtilities.reStartLiteSpeed()
                try:
                    os.remove(phpDetachUpdatePath)
                except:
                    pass

                print("1,None")
                return 1, 'None'
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [changePHP]]")
                print(0, str(msg))
                return [0, str(msg) + " [IO Error with per host config file [changePHP]]"]

    @staticmethod
    def addRewriteRules(virtualHostName, fileName=None):
        try:
            pass
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with per host config file [changePHP]]")
            return 0

        return 1

    @staticmethod
    def checkIfRewriteEnabled(data):
        try:
            for items in data:
                if items.find(".htaccess") > -1:
                    return 1
            return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with per host config file [checkIfRewriteEnabled]]")
            return 0

    @staticmethod
    def findDomainBW(domainName, totalAllowed):
        try:
            path = "/home/" + domainName + "/logs/" + domainName + ".access_log"

            if not os.path.exists("/home/" + domainName + "/logs"):
                print("0,0")

            bwmeta = "/home/" + domainName + "/logs/bwmeta"

            if not os.path.exists(path):
                print("0,0")

            if os.path.exists(bwmeta):
                try:
                    data = open(bwmeta).readlines()
                    currentUsed = int(data[0].strip("\n"))

                    inMB = int(float(currentUsed) / (1024.0 * 1024.0))

                    if totalAllowed == 0:
                        totalAllowed = 999999

                    percentage = float(100) / float(totalAllowed)
                    percentage = float(percentage) * float(inMB)
                except:
                    print("0,0")

                if percentage > 100.0:
                    percentage = 100

                print(str(inMB) + "," + str(percentage))
            else:
                print("0,0")
        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            print("0,0")
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            print("0,0")

    @staticmethod
    def permissionControl(path):
        try:
            command = 'sudo chown -R  cyberpanel:cyberpanel ' + path
            cmd = shlex.split(command)
            res = subprocess.call(cmd)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def leaveControl(path):
        try:
            command = 'sudo chown -R  root:root ' + path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def checkIfAliasExists(aliasDomain):
        try:
            alias = aliasDomains.objects.get(aliasDomain=aliasDomain)
            return 1
        except BaseException as msg:
            return 0

    @staticmethod
    def checkIfSSLAliasExists(data, aliasDomain):
        try:
            for items in data:
                if items.strip(',').strip('\n') == aliasDomain:
                    return 1
            return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [checkIfSSLAliasExists]")
            return 1

    @staticmethod
    def createAliasSSLMap(confPath, masterDomain, aliasDomain):
        try:

            data = open(confPath, 'r').readlines()
            writeToFile = open(confPath, 'w')
            sslCheck = 0


            for items in data:
                if (items.find("listener SSL") > -1):
                    sslCheck = 1
                if items.find(masterDomain) > -1 and items.find('map') > -1 and sslCheck == 1:
                    data = [_f for _f in items.split(" ") if _f]
                    if data[1] == masterDomain:
                        if vhost.checkIfSSLAliasExists(data, aliasDomain) == 0:
                            writeToFile.writelines(items.rstrip('\n') + ", " + aliasDomain + "\n")
                            sslCheck = 0
                        else:
                            writeToFile.writelines(items)
                else:
                    writeToFile.writelines(items)

            writeToFile.close()
            installUtilities.installUtilities.reStartLiteSpeed()

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [createAliasSSLMap]")

    ## Child Domain Functions

    @staticmethod
    def finalizeDomainCreation(virtualHostUser, path):
        try:

            FNULL = open(os.devnull, 'w')

            shutil.copy("/usr/local/CyberCP/index.html", path + "/index.html")

            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path + "/index.html"
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            vhostPath = vhost.Server_root + "/conf/vhosts"
            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [finalizeDomainCreation]")

    @staticmethod
    def createDirectoryForDomain(masterDomain, domain, phpVersion, path, administratorEmail, virtualHostUser,
                                 openBasedir):

        FNULL = open(os.devnull, 'w')

        confPath = vhost.Server_root + "/conf/vhosts/" + domain
        completePathToConfigFile = confPath + "/vhost.conf"

        try:
            os.makedirs(path)
            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)
        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "329 [Not able to create directories for virtual host [createDirectoryForDomain]]")

        try:
            ## For configuration files permissions will be changed later globally.
            os.makedirs(confPath)
        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "335 [Not able to create directories for virtual host [createDirectoryForDomain]]")
            return [0, "[344 Not able to directories for virtual host [createDirectoryForDomain]]"]

        try:
            ## For configuration files permissions will be changed later globally.
            file = open(completePathToConfigFile, "w+")
        except IOError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectoryForDomain]]")
            return [0, "[351 Not able to directories for virtual host [createDirectoryForDomain]]"]

        if vhost.perHostDomainConf(path, masterDomain, domain, completePathToConfigFile,
                                   administratorEmail, phpVersion, virtualHostUser, openBasedir) == 1:
            return [1, "None"]
        else:
            return [0, "[359 Not able to create per host virtual configurations [createDirectoryForDomain]"]

    @staticmethod
    def perHostDomainConf(path, masterDomain, domain, vhFile, administratorEmail, phpVersion, virtualHostUser, openBasedir):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                php = PHPManager.getPHPString(phpVersion)
                externalApp = virtualHostUser + str(randint(1000, 9999))

                currentConf = vhostConfs.olsChildConf
                currentConf = currentConf.replace('{path}', path)
                currentConf = currentConf.replace('{masterDomain}', masterDomain)
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{externalApp}', externalApp)
                currentConf = currentConf.replace('{externalAppMaster}', virtualHostUser)
                currentConf = currentConf.replace('{php}', php)
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{php}', php)


                if openBasedir == 1:
                    currentConf = currentConf.replace('{open_basedir}', 'php_admin_value open_basedir "/tmp:$VH_ROOT"')
                else:
                    currentConf = currentConf.replace('{open_basedir}', '')

                confFile = open(vhFile, "w+")
                confFile.write(currentConf)
                confFile.close()

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostDomainConf]]")
                return 0
            return 1
        else:
            try:

                if not os.path.exists(vhost.redisConf):
                    confFile = open(vhFile, "w+")
                    php = PHPManager.getPHPString(phpVersion)

                    currentConf = vhostConfs.lswsChildConf

                    currentConf = currentConf.replace('{virtualHostName}', domain)
                    currentConf = currentConf.replace('{masterDomain}', masterDomain)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{path}', path)
                    currentConf = currentConf.replace('{php}', php)

                    confFile.write(currentConf)

                    confFile.close()

                else:
                    currentConf = vhostConfs.lswsRediConfChild

                    currentConf = currentConf.replace('{virtualHostName}', domain)
                    currentConf = currentConf.replace('{masterDomain}', masterDomain)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{path}', path)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', phpVersion.lstrip('PHP '))
                    currentConf = currentConf.replace('{uid}', str(pwd.getpwnam(virtualHostUser).pw_uid))
                    currentConf = currentConf.replace('{gid}', str(grp.getgrnam(virtualHostUser).gr_gid))

                    command = 'redis-cli set %s' % (currentConf)
                    ProcessUtilities.executioner(command)

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostDomainConf]]")
                return 0
            return 1


    @staticmethod
    def createConfigInMainDomainHostFile(domain, masterDomain):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                if vhost.createNONSSLMapEntry(domain) == 0:
                    return [0, "Failed to create NON SSL Map Entry [createConfigInMainVirtualHostFile]"]

                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                currentConf = vhostConfs.olsChildMainConf
                currentConf = currentConf.replace('{virtualHostName}', domain)
                currentConf = currentConf.replace('{masterDomain}', masterDomain)
                writeDataToFile.write(currentConf)

                writeDataToFile.close()

                return [1, "None"]

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainDomainHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainDomainHostFile]]"]
        else:
            try:
                writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'a')
                configFile = 'Include /usr/local/lsws/conf/vhosts/' + domain + '/vhost.conf\n'
                writeDataToFile.writelines(configFile)
                writeDataToFile.close()
                return [1, "None"]
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainDomainHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainDomainHostFile]]"]
