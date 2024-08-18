#!/usr/local/CyberCP/bin/python
import os
import subprocess
import shlex
import plogical.CyberCPLogFileWriter as logging
from ApachController.ApacheVhosts import ApacheVhost
from plogical.processUtilities import ProcessUtilities


class ApacheController:
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

        serviceName = 'apache2'

    mpmConfigs = """# Select the MPM module which should be used by uncommenting exactly
# one of the following LoadModule lines:

# prefork MPM: Implements a non-threaded, pre-forking web server
# See: http://httpd.apache.org/docs/2.4/mod/prefork.html
#LoadModule mpm_prefork_module modules/mod_mpm_prefork.so

# worker MPM: Multi-Processing Module implementing a hybrid
# multi-threaded multi-process web server
# See: http://httpd.apache.org/docs/2.4/mod/worker.html
#
#LoadModule mpm_worker_module modules/mod_mpm_worker.so

# event MPM: A variant of the worker MPM with the goal of consuming
# threads only for connections with active processing
# See: http://httpd.apache.org/docs/2.4/mod/event.html
#
LoadModule mpm_event_module modules/mod_mpm_event.so

<IfModule mpm_event_module>
    StartServers 2
    MinSpareThreads          25
    MaxSpareThreads          75
    ThreadLimit                      64
    ThreadsPerChild          25
    MaxRequestWorkers    30
    MaxConnectionsPerChild    1000
</IfModule>"""
    mpmConfigsPath = "/etc/httpd/conf.modules.d/00-mpm.conf"

    @staticmethod
    def checkIfApacheInstalled():
        try:
            if os.path.exists(ApacheController.php80Path):
                return 1
            else:
                return 0

            # if os.path.exists(ApacheVhost.php54Path):
            #     pass
            # else:
            #     return 0
            #
            # if os.path.exists(ApacheVhost.php55Path):
            #     pass
            # else:
            #     return 0
            #
            # if os.path.exists(ApacheVhost.php56Path):
            #     pass
            # else:
            #     return 0
            #
            # if os.path.exists(ApacheVhost.php70Path):
            #     pass
            # else:
            #     return 0
            #
            # if os.path.exists(ApacheVhost.php71Path):
            #     pass
            # else:
            #     return 0
            #
            # if os.path.exists(ApacheVhost.php72Path):
            #     pass
            # else:
            #     return 0
            #
            # if os.path.exists(ApacheVhost.php73Path):
            #     return 1
            # else:
            #     return 0


        except BaseException as msg:
            message = "%s. [%s]" % (str(msg), '[ApacheController.checkIfApacheInstalled]')
            logging.CyberCPLogFileWriter.writeToFile(message)

    @staticmethod
    def executioner(command):
        try:
            # subprocess.call(shlex.split(command))
            res = subprocess.call(shlex.split(command))
            if res == 1:
                return 0
            else:
                return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def InstallApache():
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = "yum install -y httpd httpd-tools mod_ssl php-fpm"
            else:
                command = "apt update -y && sudo apt upgrade -y && apt install apache2 -y"

            if ProcessUtilities.executioner(command, None, True) == 0:
                return "Failed to install Apache and PHP-FPM."

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

                # command = "yum -y install centos-release-scl yum-utils"
                # if ProcessUtilities.executioner(command) == 0:
                #     return "Failed to centos-release-scl and yum-utils"
                #
                # command = "yum-config-manager --enable rhel-server-rhscl-7-rpms"
                # if ProcessUtilities.executioner(command) == 0:
                #     return "Failed to --enable rhel-server-rhscl-7-rpms"

                sslPath = "/etc/httpd/conf.d/ssl.conf"

                if os.path.exists(sslPath):
                    os.remove(sslPath)

                confPath = ApacheVhost.serverRootPath + "/conf/httpd.conf"

                CurrentConf = open(confPath, 'r').read()

                if CurrentConf.find('Listen 8083') == -1:

                    data = open(confPath, 'r').readlines()
                    writeToFile = open(confPath, 'w')

                    for items in data:
                        if items.find("Listen") > -1 and items.find("80") > -1 and items.find('#') == -1:
                            writeToFile.writelines("Listen 8083\nListen 8082\n")
                        elif items.find("User") > -1 and items.find('#') == -1:
                            writeToFile.writelines("User nobody\n")
                        elif items.find("Group") > -1 and items.find('#') == -1:
                            writeToFile.writelines("Group nobody\n")
                            writeToFile.writelines('SetEnv LSWS_EDITION Openlitespeed\nSetEnv X-LSCACHE on\n')
                        elif items[0] == "#":
                            continue
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()

                    # MPM Module Configurations

                    writeToFile = open(ApacheController.mpmConfigsPath, 'w')
                    writeToFile.write(ApacheController.mpmConfigs)
                    writeToFile.close()


            else:

                confPath = ApacheVhost.serverRootPath + "/apache2.conf"

                portsPath = '/etc/apache2/ports.conf'

                WriteToFile = open(portsPath, 'w')
                WriteToFile.write('Listen 8083\nListen 8082\n')
                WriteToFile.close()



                command = f"sed -i 's/User ${{APACHE_RUN_USER}}/User nobody/g' {confPath}"
                if ProcessUtilities.executioner(command, None, True) == 0:
                    return "Apache run user change failed"

                command = f"sed -i 's/Group ${{APACHE_RUN_GROUP}}/Group nogroup/g' {confPath}"
                if ProcessUtilities.executioner(command, None, True) == 0:
                    return "Apache run group change failed"

                command = 'apt-get install apache2-suexec-pristine -y'
                if ProcessUtilities.executioner(command, None, True) == 0:
                    return "Apache run apache2-suexec-pristine"

                command = 'a2enmod suexec proxy ssl proxy_fcgi proxy rewrite headers'
                if ProcessUtilities.executioner(command, None, True) == 0:
                    return "Apache run suexec proxy ssl"


                WriteToFile = open(confPath, 'a')
                WriteToFile.writelines('\nSetEnv LSWS_EDITION Openlitespeed\nSetEnv X-LSCACHE on\n')
                WriteToFile.close()

            ###

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                serviceName = 'httpd'
            else:
                serviceName = 'apache2'

            command = f"systemctl start {serviceName}.service"
            ApacheController.executioner(command)
            command = f"systemctl enable {serviceName}.service"
            ApacheController.executioner(command)

            return 1

        except BaseException as msg:
            return str(msg)

    @staticmethod
    def phpVersions():
        # Version 5.4

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            if ProcessUtilities.alma9check == 1:
                command = 'yum install -y https://rpms.remirepo.net/enterprise/remi-release-9.rpm'
            else:
                command = 'yum install -y https://rpms.remirepo.net/enterprise/remi-release-8.rpm'
            ApacheController.executioner(command)

            command = "yum install -y php?? php??-php-fpm  php??-php-mysql php??-php-curl php??-php-gd php??-php-mbstring php??-php-xml php??-php-zip php??-php-intl"
            if ProcessUtilities.executioner(command, None, True) == 0:
                return "Failed to install php54-fpm"


        else:

            command = 'apt-get install software-properties-common -y'
            if ProcessUtilities.executioner(command, None, True) == 0:
                return "Failed to install software-properties-common"

            command = 'apt install python-software-properties -y'
            if ProcessUtilities.executioner(command, None, True) == 0:
                return "Failed to install python-software-properties"

            command = 'add-apt-repository ppa:ondrej/php -y'
            if ProcessUtilities.executioner(command, None, True) == 0:
                return "Failed to ppa:ondrej/php"

            command = "DEBIAN_FRONTEND=noninteractive apt-get install -y php-fpm php?.?-fpm php?.?-fpm php?.?-mysql php?.?-curl php?.?-gd php?.?-mbstring php?.?-xml php?.?-zip php?.?-intl"

            if ProcessUtilities.executioner(command, None, True) == 0:
                return "Failed to install Apache and PHP-FPM."

        from plogical.upgrade import Upgrade
        Upgrade.CreateMissingPoolsforFPM()

        # try:
        #     wwwConfPath = ApacheVhost.php54Path + "/www.conf"
        #
        #     if os.path.exists(wwwConfPath):
        #         os.remove(wwwConfPath)
        #
        #     wwwConfPath = ApacheVhost.php55Path + "/www.conf"
        #
        #     if os.path.exists(wwwConfPath):
        #         os.remove(wwwConfPath)
        #
        #     wwwConfPath = ApacheVhost.php56Path + "/www.conf"
        #
        #     if os.path.exists(wwwConfPath):
        #         os.remove(wwwConfPath)
        #
        #     wwwConfPath = ApacheVhost.php70Path + "/www.conf"
        #
        #     if os.path.exists(wwwConfPath):
        #         os.remove(wwwConfPath)
        #
        #     wwwConfPath = ApacheVhost.php71Path + "/www.conf"
        #
        #     if os.path.exists(wwwConfPath):
        #         os.remove(wwwConfPath)
        #
        #     wwwConfPath = ApacheVhost.php72Path + "/www.conf"
        #
        #     if os.path.exists(wwwConfPath):
        #         os.remove(wwwConfPath)
        #
        #     wwwConfPath = ApacheVhost.php73Path + "/www.conf"
        #
        #     if os.path.exists(wwwConfPath):
        #         os.remove(wwwConfPath)
        # except:
        #     pass

        return 1

    @staticmethod
    def setupApache(statusFile):
        try:

            logging.CyberCPLogFileWriter.statusWriter(statusFile, 'Starting Apache installation. It may take some time..,70')

            result = ApacheController.InstallApache()

            if result != 1:
                return [0,result]

            logging.CyberCPLogFileWriter.statusWriter(statusFile,
                                                          'Installing PHP-FPM Versions. It may take some time..,80')

            result = ApacheController.phpVersions()

            if result != 1:
                return [0,result]

            return [1, 'None']
        except BaseException as msg:
            return [0, str(msg)]