#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import os
from websiteFunctions.models import Websites, ChildDomains
from plogical.vhostConfs import vhostConfs
from managePHP.phpManager import PHPManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
import re

class ApacheVhost:
    apacheInstallStatusPath = '/home/cyberpanel/apacheInstallStatus'
    serverRootPath = '/etc/httpd'
    configBasePath = '/etc/httpd/conf.d/'
    lswsMainConf = "/usr/local/lsws/conf/httpd_config.conf"
    php54Path = '/opt/remi/php54/root/etc/php-fpm.d/'
    php55Path = '/opt/remi/php55/root/etc/php-fpm.d/'
    php56Path = '/etc/opt/remi/php56/php-fpm.d/'
    php70Path = '/etc/opt/remi/php70/php-fpm.d/'
    php71Path = '/etc/opt/remi/php71/php-fpm.d/'
    php72Path = '/etc/opt/remi/php72/php-fpm.d/'
    php73Path = '/etc/opt/remi/php73/php-fpm.d/'
    count = 0
    sslBasePath = "/etc/httpd/conf.d/ssl/"

    @staticmethod
    def DecidePHPPath(php, virtualHostName):
        if php == '53' or php == '54':
          finalConfPath =  ApacheVhost.php54Path + virtualHostName
        elif php == '55':
            finalConfPath = ApacheVhost.php55Path + virtualHostName
        elif php == '56':
            finalConfPath = ApacheVhost.php56Path + virtualHostName
        elif php == '70':
            finalConfPath = ApacheVhost.php70Path + virtualHostName
        elif php == '71':
            finalConfPath = ApacheVhost.php71Path + virtualHostName
        elif php == '72':
            finalConfPath = ApacheVhost.php72Path + virtualHostName
        elif php == '73':
            finalConfPath = ApacheVhost.php73Path + virtualHostName

        return finalConfPath + '.conf'

    @staticmethod
    def whichPHPExists(virtualHostName):

        virtualHostName = virtualHostName + ".conf"

        if os.path.exists(ApacheVhost.php54Path + virtualHostName):
            return ApacheVhost.php54Path + virtualHostName

        if os.path.exists(ApacheVhost.php55Path + virtualHostName):
            return ApacheVhost.php55Path + virtualHostName

        if os.path.exists(ApacheVhost.php56Path + virtualHostName):
            return ApacheVhost.php56Path + virtualHostName

        if os.path.exists(ApacheVhost.php70Path + virtualHostName):
            return ApacheVhost.php70Path + virtualHostName

        if os.path.exists(ApacheVhost.php71Path + virtualHostName):
            return ApacheVhost.php71Path + virtualHostName

        if os.path.exists(ApacheVhost.php72Path + virtualHostName):
            return ApacheVhost.php72Path + virtualHostName

        if os.path.exists(ApacheVhost.php73Path + virtualHostName):
            return ApacheVhost.php73Path + virtualHostName

    @staticmethod
    def GenerateSelfSignedSSL(virtualHostName):
        if os.path.exists(ApacheVhost.sslBasePath):
            pass
        else:
            os.mkdir(ApacheVhost.sslBasePath)

        pathToStoreSSLPrivKey = ApacheVhost.sslBasePath + virtualHostName + ".privkey.pem"
        pathToStoreSSLFullChain = ApacheVhost.sslBasePath + virtualHostName + ".fullchain.pem"
        command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain
        ProcessUtilities.normalExecutioner(command)

    @staticmethod
    def perHostVirtualConf(administratorEmail,externalApp, virtualHostUser, phpVersion, virtualHostName):
        try:

            ## Non-SSL Conf

            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'
            confFile = open(finalConfPath, "w+")

            php = PHPManager.getPHPString(phpVersion)

            currentConf = vhostConfs.apacheConf
            currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
            currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
            currentConf = currentConf.replace('{virtualHostUser}', virtualHostUser)
            currentConf = currentConf.replace('{php}', php)
            currentConf = currentConf.replace('{adminEmails}', administratorEmail)
            currentConf = currentConf.replace('{externalApp}', virtualHostUser)

            confFile.write(currentConf)
            confFile.close()

            ## SSL Conf

            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'
            confFile = open(finalConfPath, "a")

            php = PHPManager.getPHPString(phpVersion)

            currentConf = vhostConfs.apacheConfSSL
            currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
            currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
            currentConf = currentConf.replace('{virtualHostUser}', virtualHostUser)
            currentConf = currentConf.replace('{php}', php)
            currentConf = currentConf.replace('{adminEmails}', administratorEmail)
            currentConf = currentConf.replace('{externalApp}', virtualHostUser)

            confFile.write(currentConf)
            confFile.close()

            ##

            finalConfPath = ApacheVhost.DecidePHPPath(php, virtualHostName)

            confFile = open(finalConfPath, "w+")
            currentConf = vhostConfs.phpFpmPool
            currentConf = currentConf.replace('{www}', virtualHostUser)
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)

            confFile.write(currentConf)

            ApacheVhost.GenerateSelfSignedSSL(virtualHostName)

            command = "systemctl restart httpd"
            ProcessUtilities.normalExecutioner(command)

            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def enableProxyInMainConf():
        try:
            data = open(ApacheVhost.lswsMainConf, 'r').readline()

            putProxyConf = 1
            putProxyConfSSL = 1

            for items in data:
                if items.find('apachebackend') > -1:
                    putProxyConf = 0
                if items.find('proxyApacheBackendSSL') > -1:
                    putProxyConfSSL = 0

            if putProxyConf:
                confFile = open(ApacheVhost.lswsMainConf, "a")
                confFile.write(vhostConfs.proxyApacheBackend)
                confFile.close()

            if putProxyConfSSL:
                confFile = open(ApacheVhost.lswsMainConf, "a")
                confFile.write(vhostConfs.proxyApacheBackendSSL)
                confFile.close()

            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def reWrite(domain_name):
        try:
            domainPath = '/home/' + domain_name + '/public_html/.htaccess'
            confFile = open(domainPath, "w+")
            confFile.write("REWRITERULE ^(.*)$ HTTP://apachebackend/$1 [P]")
            confFile.close()
            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def setupApacheVhost(administratorEmail,externalApp, virtualHostUser, phpVersion, virtualHostName):
        result = ApacheVhost.perHostVirtualConf(administratorEmail,externalApp, virtualHostUser, phpVersion, virtualHostName)
        if result[0] == 0:
            return [0, result[1]]

        result = ApacheVhost.enableProxyInMainConf()
        if result[0] == 0:
            return [0, result[1]]

        return [1, 'None']

    @staticmethod
    def perHostVirtualConfChild(administratorEmail, externalApp, virtualHostUser, phpVersion, virtualHostName, path):
        try:

            ## Non - SSL Conf

            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'
            confFile = open(finalConfPath, "w+")

            php = PHPManager.getPHPString(phpVersion)

            currentConf = vhostConfs.apacheConfChild
            currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
            currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
            currentConf = currentConf.replace('{php}', php)
            currentConf = currentConf.replace('{adminEmails}', administratorEmail)
            currentConf = currentConf.replace('{externalApp}', virtualHostUser)
            currentConf = currentConf.replace('{path}', path)

            confFile.write(currentConf)
            confFile.close()

            ## SSL Conf

            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'
            confFile = open(finalConfPath, "a")

            php = PHPManager.getPHPString(phpVersion)

            currentConf = vhostConfs.apacheConfChildSSL
            currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
            currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
            currentConf = currentConf.replace('{php}', php)
            currentConf = currentConf.replace('{adminEmails}', administratorEmail)
            currentConf = currentConf.replace('{externalApp}', virtualHostUser)
            currentConf = currentConf.replace('{path}', path)

            confFile.write(currentConf)
            confFile.close()

            ## SSL Conf

            finalConfPath = ApacheVhost.DecidePHPPath(php, virtualHostName)

            confFile = open(finalConfPath, "w+")
            currentConf = vhostConfs.phpFpmPool
            currentConf = currentConf.replace('{www}', "".join(re.findall("[a-zA-Z]+", virtualHostName))[:7])
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)

            confFile.write(currentConf)

            ApacheVhost.GenerateSelfSignedSSL(virtualHostName)

            command = "systemctl restart httpd"
            ProcessUtilities.normalExecutioner(command)

            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def setupApacheVhostChild(administratorEmail, externalApp, virtualHostUser, phpVersion, virtualHostName, path):
        result = ApacheVhost.perHostVirtualConfChild(administratorEmail, externalApp, virtualHostUser, phpVersion,
                                                virtualHostName, path)
        if result[0] == 0:
            return [0, result[1]]

        result = ApacheVhost.enableProxyInMainConf()
        if result[0] == 0:
            return [0, result[1]]

        return [1, 'None']

    @staticmethod
    def DeleteApacheVhost(virtualHostName):
        try:
            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'

            if os.path.exists(finalConfPath):
                os.remove(finalConfPath)

            ApacheVhost.deletePHPPath(virtualHostName)

            command = "systemctl restart httpd"
            ProcessUtilities.normalExecutioner(command)

        except BaseException as msg:
            logging.writeToFile(str(msg))

    @staticmethod
    def perHostVirtualConfOLS(vhFile, administratorEmail):
        # General Configurations tab
        try:
            confFile = open(vhFile, "w+")

            currentConf = vhostConfs.OLSLBConf
            currentConf = currentConf.replace('{adminEmails}', administratorEmail)

            confFile.write(currentConf)
            confFile.close()

        except BaseException as msg:
            logging.writeToFile(
                str(msg) + " [IO Error with per host config file [ApacheVhosts.perHostVirtualConf]]")

    @staticmethod
    def deletePHPPath(virtualHostName):

        phpPath = ApacheVhost.DecidePHPPath('54', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            command = "systemctl restart php%s-php-fpm" % ('54')
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('55', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            command = "systemctl restart php%s-php-fpm" % ('55')
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('56', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            command = "systemctl restart php%s-php-fpm" % ('56')
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('70', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            command = "systemctl restart php%s-php-fpm" % ('70')
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('71', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            command = "systemctl restart php%s-php-fpm" % ('71')
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('72', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            command = "systemctl restart php%s-php-fpm" % ('72')
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('73', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            command = "systemctl restart php%s-php-fpm" % ('73')
            ProcessUtilities.normalExecutioner(command)

    @staticmethod
    def changePHP(phpVersion, vhFile):
        try:

            virtualHostName = vhFile.split('/')[6]

            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'

            if not os.path.exists(finalConfPath):
                return 0

            ApacheVhost.deletePHPPath(virtualHostName)

            website = Websites.objects.get(domain=virtualHostName)

            php = PHPManager.getPHPString(phpVersion)

            finalConfPath = ApacheVhost.DecidePHPPath(php, virtualHostName)

            confFile = open(finalConfPath, "w+")
            currentConf = vhostConfs.phpFpmPool
            currentConf = currentConf.replace('{www}', website.externalApp)
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', website.externalApp)

            confFile.write(currentConf)

            command = "systemctl stop php%s-php-fpm" % (php)
            ProcessUtilities.normalExecutioner(command)

            command = "systemctl restart php%s-php-fpm" % (php)
            ProcessUtilities.normalExecutioner(command)

            return 1
        except BaseException as msg:
            logging.writeToFile(str(msg))
            return 1