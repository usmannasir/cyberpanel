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

    if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

        serverRootPath = '/etc/httpd'
        configBasePath = '/etc/httpd/conf.d/'
        php54Path = '/opt/remi/php54/root/etc/php-fpm.d/'
        php55Path = '/opt/remi/php55/root/etc/php-fpm.d/'
        php56Path = '/etc/opt/remi/php56/php-fpm.d/'
        php70Path = '/etc/opt/remi/php70/php-fpm.d/'
        php71Path = '/etc/opt/remi/php71/php-fpm.d/'
        php72Path = '/etc/opt/remi/php72/php-fpm.d/'
        php73Path = '/etc/opt/remi/php73/php-fpm.d/'

        php74Path = '/etc/opt/remi/php74/php-fpm.d/'
        php80Path = '/etc/opt/remi/php80/php-fpm.d/'
        php81Path = '/etc/opt/remi/php81/php-fpm.d/'
        php82Path = '/etc/opt/remi/php82/php-fpm.d/'

        serviceName = 'httpd'

    else:
        serverRootPath = '/etc/apache2'
        configBasePath = '/etc/apache2/sites-enabled/'

        php54Path = '/etc/php/5.4/fpm/pool.d/'
        php55Path = '/etc/php/5.5/fpm/pool.d/'
        php56Path = '/etc/php/5.6/fpm/pool.d/'
        php70Path = '/etc/php/7.0/fpm/pool.d/'
        php71Path = '/etc/php/7.1/fpm/pool.d/'
        php72Path = '/etc/php/7.2/fpm/pool.d/'
        php73Path = '/etc/php/7.3/fpm/pool.d/'
        php74Path = '/etc/php/7.4/fpm/pool.d/'

        php80Path = '/etc/php/8.0/fpm/pool.d/'
        php81Path = '/etc/php/8.1/fpm/pool.d/'
        php82Path = '/etc/php/8.2/fpm/pool.d/'
        php83Path = '/etc/php/8.3/fpm/pool.d/'
        php84Path = '/etc/php/8.4/fpm/pool.d/'

        serviceName = 'apache2'



    lswsMainConf = "/usr/local/lsws/conf/httpd_config.conf"

    count = 0
    if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
        sslBasePath = "/etc/httpd/conf.d/ssl/"
    else:
        sslBasePath = "/etc/apache2/conf-enabled/"

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
        elif php == '74':
            finalConfPath = ApacheVhost.php74Path + virtualHostName
        elif php == '80':
            finalConfPath = ApacheVhost.php80Path + virtualHostName
        elif php == '81':
            finalConfPath = ApacheVhost.php81Path + virtualHostName
        elif php == '82':
            finalConfPath = ApacheVhost.php82Path + virtualHostName
        elif php == '83':
            finalConfPath = ApacheVhost.php83Path + virtualHostName
        elif php == '84':
            finalConfPath = ApacheVhost.php84Path + virtualHostName

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

        if os.path.exists(ApacheVhost.php74Path + virtualHostName):
            return ApacheVhost.php74Path + virtualHostName

        if os.path.exists(ApacheVhost.php80Path + virtualHostName):
            return ApacheVhost.php80Path + virtualHostName

        if os.path.exists(ApacheVhost.php81Path + virtualHostName):
            return ApacheVhost.php81Path + virtualHostName

        if os.path.exists(ApacheVhost.php82Path + virtualHostName):
            return ApacheVhost.php82Path + virtualHostName

        if os.path.exists(ApacheVhost.php83Path + virtualHostName):
            return ApacheVhost.php83Path + virtualHostName



    @staticmethod
    def GenerateSelfSignedSSL(virtualHostName):
        if os.path.exists(ApacheVhost.sslBasePath):
            pass
        else:
            os.mkdir(ApacheVhost.sslBasePath)

        pathToStoreSSLPrivKey = ApacheVhost.sslBasePath + ".privkey.pem"
        pathToStoreSSLFullChain = ApacheVhost.sslBasePath + ".fullchain.pem"
        command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain
        ProcessUtilities.normalExecutioner(command)

    @staticmethod
    def perHostVirtualConf(administratorEmail,externalApp, virtualHostUser, phpVersion, virtualHostName):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                sockPath = '/var/run/php-fpm/'
                group = 'nobody'
            else:
                sockPath = '/var/run/php/'
                group = 'nogroup'

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
            currentConf = currentConf.replace('{sockPath}', sockPath)

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
            currentConf = currentConf.replace('{SSLBase}', ApacheVhost.sslBasePath)
            currentConf = currentConf.replace('{sockPath}', sockPath)

            confFile.write(currentConf)
            confFile.close()

            ##

            finalConfPath = ApacheVhost.DecidePHPPath(php, virtualHostName)

            confFile = open(finalConfPath, "w+")
            currentConf = vhostConfs.phpFpmPool
            currentConf = currentConf.replace('{www}', virtualHostUser)
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)
            currentConf = currentConf.replace('{sockPath}', sockPath)
            currentConf = currentConf.replace('{group}', group)

            confFile.write(currentConf)

            ApacheVhost.GenerateSelfSignedSSL(virtualHostName)

            command = f"systemctl restart {ApacheVhost.serviceName}"
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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                sockPath = '/var/run/php-fpm/'
                group = 'nobody'
            else:
                sockPath = '/var/run/php/'
                group = 'nogroup'

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
            currentConf = currentConf.replace('{sockPath}', sockPath)

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
            currentConf = currentConf.replace('{sockPath}', sockPath)
            currentConf = currentConf.replace('{SSLBase}', ApacheVhost.sslBasePath)

            confFile.write(currentConf)
            confFile.close()

            ## SSL Conf

            finalConfPath = ApacheVhost.DecidePHPPath(php, virtualHostName)

            confFile = open(finalConfPath, "w+")
            currentConf = vhostConfs.phpFpmPool
            currentConf = currentConf.replace('{www}', "".join(re.findall("[a-zA-Z]+", virtualHostName))[:7])
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)
            currentConf = currentConf.replace('{sockPath}', sockPath)
            currentConf = currentConf.replace('{group}', group)

            confFile.write(currentConf)

            ApacheVhost.GenerateSelfSignedSSL(virtualHostName)

            command = f"systemctl restart {ApacheVhost.serviceName}"
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

            command = f"systemctl restart {ApacheVhost.serviceName}"
            ProcessUtilities.normalExecutioner(command)

        except BaseException as msg:
            logging.writeToFile(str(msg))

    @staticmethod
    def perHostVirtualConfOLS(vhFile, administratorEmail):
        # General Configurations tab
        try:
            confFile = open(vhFile, "w+")
            virtualHostName = vhFile.split('/')[6]

            currentConf = vhostConfs.OLSLBConf
            currentConf = currentConf.replace('{adminEmails}', administratorEmail)
            currentConf = currentConf.replace('{domain}', virtualHostName)

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php54-php-fpm'
            else:
                phpService = f"php5.4-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('55', virtualHostName)
        if os.path.exists(phpPath):

            os.remove(phpPath)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php55-php-fpm'
            else:
                phpService = f"php5.5-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('56', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php56-php-fpm'
            else:
                phpService = f"php5.6-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('70', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php70-php-fpm'
            else:
                phpService = f"php7.0-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('71', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php71-php-fpm'
            else:
                phpService = f"php7.1-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('72', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php72-php-fpm'
            else:
                phpService = f"php7.2-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('73', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php73-php-fpm'
            else:
                phpService = f"php7.3-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('74', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php74-php-fpm'
            else:
                phpService = f"php7.4-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('80', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php80-php-fpm'
            else:
                phpService = f"php8.0-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('81', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php81-php-fpm'
            else:
                phpService = f"php8.1-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('82', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php82-php-fpm'
            else:
                phpService = f"php8.2-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

    @staticmethod
    def changePHP(phpVersion, vhFile):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                sockPath = '/var/run/php-fpm/'
                group = 'nobody'
            else:
                sockPath = '/var/run/php/'
                group = 'nogroup'

            virtualHostName = vhFile.split('/')[6]

            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'

            if not os.path.exists(finalConfPath):
                logging.writeToFile(f'Config path: {finalConfPath}')
                return 0

            ApacheVhost.deletePHPPath(virtualHostName)

            try:
                website = Websites.objects.get(domain=virtualHostName)
                externalApp = website.externalApp
            except:
                child = ChildDomains.objects.get(domain=virtualHostName)
                externalApp = child.master.externalApp

            php = PHPManager.getPHPString(phpVersion)

            finalConfPath = ApacheVhost.DecidePHPPath(php, virtualHostName)

            logging.writeToFile(f'apache php final path: {finalConfPath}')

            confFile = open(finalConfPath, "w+")
            currentConf = vhostConfs.phpFpmPool
            currentConf = currentConf.replace('{www}', externalApp)
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)
            currentConf = currentConf.replace('{sockPath}', sockPath)
            currentConf = currentConf.replace('{group}', group)

            confFile.write(currentConf)

            phpService = ApacheVhost.DecideFPMServiceName(phpVersion)

            command = f"systemctl stop {phpService}"
            ProcessUtilities.normalExecutioner(command)

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

            command = f"systemctl restart {ApacheVhost.serviceName}"
            ProcessUtilities.normalExecutioner(command)

            return 1
        except BaseException as msg:
            logging.writeToFile(str(msg))
            return 1


    @staticmethod
    def DecidePHPPathforManager(apache, phpVers):
        if apache == 0 or apache == None:
            phpVers = "php" + PHPManager.getPHPString(phpVers)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                path = "/usr/local/lsws/ls" + phpVers + "/etc/php.ini"
            else:
                initial = phpVers[3]
                final = phpVers[4]

                completeName = str(initial) + '.' + str(final)
                path = "/usr/local/lsws/ls" + phpVers + "/etc/php/" + completeName + "/litespeed/php.ini"
        else:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpVers = "php" + PHPManager.getPHPString(phpVers)
                path = f'/etc/opt/remi/{phpVers}/php.ini'
            else:
                path = f'/etc/php/{phpVers.split(" ")[1]}/fpm/php.ini'

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'PHP Path {path}')

        return path

    @staticmethod
    def DecideFPMServiceName(phpVersion):
        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            php = PHPManager.getPHPString(phpVersion)
            return f'php{php}-php-fpm'
        else:
            return f"{phpVersion.replace(' ', '').lower()}-fpm"