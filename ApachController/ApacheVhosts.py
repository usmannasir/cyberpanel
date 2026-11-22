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
from managePHP.phpConfig import fpm_pool_name, fpm_service_for_selection, managed_ini_path
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from ApachController import apacheConfigCheck
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
        php83Path = '/etc/opt/remi/php83/php-fpm.d/'
        php84Path = '/etc/opt/remi/php84/php-fpm.d/'
        php85Path = '/etc/opt/remi/php85/php-fpm.d/'

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
        php85Path = '/etc/php/8.5/fpm/pool.d/'

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
        elif php == '85':
            finalConfPath = ApacheVhost.php85Path + virtualHostName

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'Decided path in DecidePHPPath {finalConfPath}.conf')

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

        if os.path.exists(ApacheVhost.php84Path + virtualHostName):
            return ApacheVhost.php84Path + virtualHostName

        if os.path.exists(ApacheVhost.php85Path + virtualHostName):
            return ApacheVhost.php85Path + virtualHostName



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
            currentConf = currentConf.replace('{www}', fpm_pool_name(externalApp, virtualHostName))
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)
            currentConf = currentConf.replace('{sockPath}', sockPath)
            currentConf = currentConf.replace('{group}', group)

            confFile.write(currentConf)
            # The pool is complete on disk before anything reads it.
            confFile.close()

            ApacheVhost.GenerateSelfSignedSSL(virtualHostName)

            # Apache is restarted by the caller, once it accepts these files.
            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def enableProxyInMainConf():
        try:
            # Each backend is defined once, however many websites use it,
            # and on the port its virtual hosts listen on: 8083 without SSL,
            # 8082 with it. Blocks an earlier release repeated for every
            # website, or wrote with the two ports exchanged, are removed.
            with open(ApacheVhost.lswsMainConf, 'r') as confFile:
                data = confFile.read()

            updated = apacheConfigCheck.with_proxy_backends(
                data, vhostConfs.proxyApacheBackend, vhostConfs.proxyApacheBackendSSL)
            if updated != data:
                apacheConfigCheck.replace_file(ApacheVhost.lswsMainConf, updated)

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
    def configTest():
        """Apache's own check of its whole configuration, as (passed, what Apache said)."""
        rpmFamily = ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8
        return apacheConfigCheck.config_test(apacheConfigCheck.config_test_command(rpmFamily))

    @staticmethod
    def restartService():
        """Restart Apache. Returns None, or a text saying that it did not come up."""
        command = f"systemctl restart {ApacheVhost.serviceName}"
        if ProcessUtilities.normalExecutioner(command) == 1:
            return None
        return 'Apache did not start; see "systemctl status %s".' % ApacheVhost.serviceName

    @staticmethod
    def restartApache():
        """Restart Apache unless it refuses its configuration.

        A running Apache keeps serving with the configuration it loaded.
        Restarting it with one it refuses would stop every website on the
        Apache backend, so it is then left running. Returns None, or a text
        saying why Apache was not restarted or did not come up.
        """
        passed, output = ApacheVhost.configTest()
        if not passed:
            return 'Apache was not restarted because its configuration test did not pass: %s' % apacheConfigCheck.said(output)
        return ApacheVhost.restartService()

    @staticmethod
    def restoreVhost(source, finalConfPath):
        """Put the virtual host of a backup in place of the one just made for the restored website.

        It stays only if every account it names exists here and Apache
        accepts it; otherwise the virtual host made for the website is kept.
        A backup names the account the website had on its old server, which
        a restore may have had to replace. Returns [1, 'None'] or [0, reason].
        """
        try:
            with open(source, 'r') as backup:
                content = backup.read()

            def change():
                unknown = apacheConfigCheck.unknown_accounts(apacheConfigCheck.vhost_accounts(content))
                if unknown:
                    return 'The virtual host in the backup names the system account %s, which does not exist ' \
                           'on this server; the virtual host made for the restored website was kept.' % ', '.join(unknown)
                with open(finalConfPath, 'w') as vhost:
                    vhost.write(content)
                return None

            return list(apacheConfigCheck.apply_change(
                [finalConfPath], change, ApacheVhost.configTest, ApacheVhost.restartService))
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def checkedSetup(virtualHostName, phpVersion, accounts, write):
        """Put a website on the Apache backend, or change nothing and say why.

        write creates the virtual host and the PHP-FPM pool. They stay only
        if the system account they name exists, Apache accepts its
        configuration with them and comes up; otherwise the files are what
        they were, Apache keeps serving the other websites, and the reason
        is returned as [0, reason].
        """
        try:
            for account in accounts:
                problem = apacheConfigCheck.account_problem(account)
                if problem is not None:
                    return [0, '%s Apache and PHP-FPM cannot run this website without it.' % problem]

            vhostPath = ApacheVhost.configBasePath + virtualHostName + '.conf'
            poolPath = ApacheVhost.DecidePHPPath(PHPManager.getPHPString(phpVersion), virtualHostName)
            if not os.path.isdir(os.path.dirname(poolPath)):
                return [0, 'PHP-FPM for %s is not installed on this server (%s does not exist), so Apache '
                           'cannot run PHP for this website.' % (phpVersion, os.path.dirname(poolPath))]

            def change():
                result = write()
                return None if result[0] == 1 else result[1]

            status, reason = apacheConfigCheck.apply_change(
                [vhostPath, poolPath], change, ApacheVhost.configTest, ApacheVhost.restartService)
            if status == 0:
                return [0, reason]

            result = ApacheVhost.enableProxyInMainConf()
            if result[0] == 0:
                return [0, result[1]]

            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def setupApacheVhost(administratorEmail,externalApp, virtualHostUser, phpVersion, virtualHostName):
        return ApacheVhost.checkedSetup(
            virtualHostName, phpVersion, (externalApp, virtualHostUser),
            lambda: ApacheVhost.perHostVirtualConf(administratorEmail, externalApp, virtualHostUser, phpVersion,
                                                   virtualHostName))

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
            currentConf = currentConf.replace('{www}', fpm_pool_name(externalApp, virtualHostName))
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)
            currentConf = currentConf.replace('{sockPath}', sockPath)
            currentConf = currentConf.replace('{group}', group)

            confFile.write(currentConf)
            # The pool is complete on disk before anything reads it.
            confFile.close()

            ApacheVhost.GenerateSelfSignedSSL(virtualHostName)

            # Apache is restarted by the caller, once it accepts these files.
            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]

    @staticmethod
    def setupApacheVhostChild(administratorEmail, externalApp, virtualHostUser, phpVersion, virtualHostName, path):
        return ApacheVhost.checkedSetup(
            virtualHostName, phpVersion, (externalApp, virtualHostUser),
            lambda: ApacheVhost.perHostVirtualConfChild(administratorEmail, externalApp, virtualHostUser,
                                                        phpVersion, virtualHostName, path))

    @staticmethod
    def DeleteApacheVhost(virtualHostName):
        try:
            finalConfPath = ApacheVhost.configBasePath + virtualHostName + '.conf'
            onApache = os.path.exists(finalConfPath)

            if onApache:
                os.remove(finalConfPath)

            ApacheVhost.deletePHPPath(virtualHostName)

            # A pool that an upgrade set aside goes with the website.
            rpmFamily = ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8
            for leftover in apacheConfigCheck.pools_set_aside(virtualHostName + '.conf', rpmFamily):
                os.remove(leftover)

            # Apache is restarted only for a website it was serving.
            if onApache:
                problem = ApacheVhost.restartApache()
                if problem is not None:
                    logging.writeToFile('%s [DeleteApacheVhost]' % problem)

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

        phpPath = ApacheVhost.DecidePHPPath('83', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php83-php-fpm'
            else:
                phpService = f"php8.3-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('84', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php84-php-fpm'
            else:
                phpService = f"php8.4-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

        phpPath = ApacheVhost.DecidePHPPath('85', virtualHostName)
        if os.path.exists(phpPath):
            os.remove(phpPath)
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php85-php-fpm'
            else:
                phpService = f"php8.5-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

    @staticmethod
    def changePHP(phpVersion, vhFile):
        # Returns 0 for a website that is not on the Apache backend, 1 when
        # its PHP was changed, and otherwise a text saying why nothing was
        # changed.
        try:
            logging.writeToFile(f"PHP version passed to Apache function: {phpVersion}")

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

            try:
                website = Websites.objects.get(domain=virtualHostName)
                externalApp = website.externalApp
            except:
                child = ChildDomains.objects.get(domain=virtualHostName)
                externalApp = child.master.externalApp

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f"PHP version before getPHPString: {phpVersion}")

            php = PHPManager.getPHPString(phpVersion)

            finalConfPath = ApacheVhost.DecidePHPPath(php, virtualHostName)

            logging.writeToFile(f'apache php final path: {finalConfPath}')

            # The pool the website has is removed only when the new one can
            # work: PHP-FPM stops for every website of a version when one
            # pool names an account that does not exist.
            problem = apacheConfigCheck.account_problem(externalApp)
            if problem is None and not os.path.isdir(os.path.dirname(finalConfPath)):
                problem = 'PHP-FPM for %s is not installed on this server (%s does not exist).' % (
                    phpVersion, os.path.dirname(finalConfPath))
            if problem is not None:
                logging.writeToFile('%s [ApacheVhost.changePHP]' % problem)
                return '%s The PHP version of %s was not changed.' % (problem, virtualHostName)

            ApacheVhost.deletePHPPath(virtualHostName)

            confFile = open(finalConfPath, "w+")
            currentConf = vhostConfs.phpFpmPool
            currentConf = currentConf.replace('{www}', fpm_pool_name(externalApp, virtualHostName))
            currentConf = currentConf.replace('{Sock}', virtualHostName)
            currentConf = currentConf.replace('{externalApp}', externalApp)
            currentConf = currentConf.replace('{sockPath}', sockPath)
            currentConf = currentConf.replace('{group}', group)

            confFile.write(currentConf)

            ### minor bug fix of updating default php conf user in selected fpm

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                defaultConfPath = finalConfPath.replace(virtualHostName, 'www')

                command = f"sed -i 's/www-data/apache/g' {defaultConfPath}"
                ProcessUtilities.executioner(command)

            # The pool file is complete on disk before the service reads it.
            confFile.close()

            ProcessUtilities.normalExecutioner(ApacheVhost.fpmServiceCommand(ApacheVhost.fpmReload, phpVersion))

            # A website that an upgrade closed because its account was
            # missing is open again now that the account exists and the pool
            # is written; the pool that was set aside is not needed any more.
            vhostPath = ApacheVhost.configBasePath + virtualHostName + '.conf'
            if apacheConfigCheck.reopen_virtual_host(vhostPath):
                logging.writeToFile('The virtual host of %s was reopened. [ApacheVhost.changePHP]' % virtualHostName)
            rpmFamily = ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8
            for leftover in apacheConfigCheck.pools_set_aside(virtualHostName + '.conf', rpmFamily):
                os.remove(leftover)

            problem = ApacheVhost.restartApache()
            if problem is not None:
                logging.writeToFile('%s [ApacheVhost.changePHP]' % problem)

            return 1
        except BaseException as msg:
            logging.writeToFile(str(msg))
            return 1


    @staticmethod
    def DecidePHPPathforManager(apache, phpVers):
        # The path is built from the digits of a checked selection; a
        # selection of any other shape raises ValueError. apache is absent
        # (None or 0) for LiteSpeed PHP and anything else for the PHP-FPM of
        # the Apache backend, as the pages send it.
        rpmFamily = ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8
        path = managed_ini_path(phpVers, not (apache == 0 or apache == None), rpmFamily)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'PHP Path {path}')

        return path

    @staticmethod
    def DecideFPMServiceName(phpVersion):
        # The name is built from the digits of a checked selection; a selection
        # of any other shape raises ValueError.
        rpmFamily = ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8
        return fpm_service_for_selection(phpVersion, rpmFamily)

    # What a change to one website's pool does to the PHP-FPM service that
    # all websites of that PHP version share: php-fpm re-reads its pools and
    # keeps its listening sockets, so the other websites stay reachable. A
    # service that is not running, or cannot reload, is (re)started instead.
    fpmReload = 'reload-or-restart'

    @staticmethod
    def fpmServiceCommand(action, phpVersion):
        """The systemctl argument list that acts on the PHP-FPM service of a PHP selection.

        Run it as a list (ProcessUtilities.normalExecutioner accepts one). The
        unit is one argument after `--`, so it is never read as an option.
        """
        if action not in ('stop', 'start', 'restart', 'reload', ApacheVhost.fpmReload):
            raise ValueError('Unsupported service action.')
        return ['systemctl', action, '--', ApacheVhost.DecideFPMServiceName(phpVersion)]