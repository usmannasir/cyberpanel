#!/usr/local/CyberCP/bin/python
import os
import subprocess
import shlex
import plogical.CyberCPLogFileWriter as logging
from ApachController.ApacheVhosts import ApacheVhost


class ApacheController:
    apacheInstallStatusPath = '/home/cyberpanel/apacheInstallStatus'
    serverRootPath = '/etc/httpd'
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
            if os.path.exists(ApacheController.serverRootPath):
                pass
            else:
                return 0

            if os.path.exists(ApacheVhost.php54Path):
                pass
            else:
                return 0

            if os.path.exists(ApacheVhost.php55Path):
                pass
            else:
                return 0

            if os.path.exists(ApacheVhost.php56Path):
                pass
            else:
                return 0

            if os.path.exists(ApacheVhost.php70Path):
                pass
            else:
                return 0

            if os.path.exists(ApacheVhost.php71Path):
                pass
            else:
                return 0

            if os.path.exists(ApacheVhost.php72Path):
                pass
            else:
                return 0

            if os.path.exists(ApacheVhost.php73Path):
                return 1
            else:
                return 0
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

            command = "yum install -y httpd httpd-tools mod_ssl php-fpm"
            if ApacheController.executioner(command) == 0:
                return "Failed to install Apache and PHP-FPM."

            command = "yum -y install centos-release-scl yum-utils"
            if ApacheController.executioner(command) == 0:
                return "Failed to centos-release-scl and yum-utils"

            command = "yum-config-manager --enable rhel-server-rhscl-7-rpms"
            if ApacheController.executioner(command) == 0:
                return "Failed to --enable rhel-server-rhscl-7-rpms"


            ## Minor Configuration changes.

            sslPath = "/etc/httpd/conf.d/ssl.conf"

            if os.path.exists(sslPath):
                os.remove(sslPath)

            confPath = ApacheVhost.serverRootPath + "/conf/httpd.conf"

            data = open(confPath, 'r').readlines()
            writeToFile = open(confPath, 'w')

            for items in data:
                if items.find("Listen") > -1 and items.find("80") > -1 and items.find('#') == -1:
                    writeToFile.writelines("Listen 8081\nListen 8082\n")
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

            writeToFile = open(ApacheController.mpmConfigsPath , 'w')
            writeToFile.write(ApacheController.mpmConfigs)
            writeToFile.close()

            ###

            command = "systemctl start httpd.service"
            ApacheController.executioner(command)
            command = "systemctl enable httpd.service"
            ApacheController.executioner(command)

            return 1

        except BaseException as msg:
            return str(msg)

    @staticmethod
    def phpVersions():
        # Version 5.4

        command = 'yum install -y http://rpms.remirepo.net/enterprise/remi-release-7.rpm'
        ApacheController.executioner(command)

        command = 'yum-config-manager --enable remi-php'
        ApacheController.executioner(command)


        command = 'yum install -y php54-php-fpm php54-php-gd php54-php-xml php54-php-twig php54-php-zstd php54-php-tidy' \
                  'php54-php-suhosin php54-php-soap php54-php-snmp php54-php-snappy php54-php-smbclient' \
                  'php54-php-process php54-php-pimple php54-php-pgsql php54-php-pear.noarch php54-php-pdo' \
                  'php54-php-mysqlnd php54-php-mssql php54-php-mcrypt php54-php-mbstring php54-php-maxminddb' \
                  'php54-php-common php54-php-imap php54-php-intl php54-php-tarantool php54-php-pspell php54-php-oci8' \
                  'php54-php-bcmath php54-php-litespeed php54-php-recode php54-php-odbc'
        if ApacheController.executioner(command) == 0:
            return "Failed to install php54-fpm"

        # Version 5.5
        command = 'yum install -y php55-php-fpm php55-php-gd php55-php-xml php55-php-twig php55-php-zstd php55-php-tidy' \
                  'php55-php-suhosin php55-php-soap php55-php-snmp php55-php-snappy php55-php-smbclient ' \
                  'php55-php-process php55-php-pimple php55-php-pgsql php55-php-pear.noarch php55-php-pdo' \
                  'php55-php-mysqlnd php55-php-mssql php55-php-mcrypt php55-php-mbstring php55-php-maxminddb' \
                  'php55-php-common php55-php-imap php55-php-intl php55-php-tarantool php55-php-pspell php55-php-oci8' \
                  'php55-php-litespeed php55-php-bcmath php55-php-odbc php55-php-recode'
        if ApacheController.executioner(command) == 0:
            return "Failed to install php55-fpm"

        # Version 5.6
        command = 'yum install -y php56-php-fpm php56-php-gd php56-php-xml php56-php-twig php56-php-zstd php56-php-tidy' \
                  'php56-php-suhosin php56-php-soap php56-php-snmp php56-php-snappy php56-php-smbclient' \
                  'php56-php-process php56-php-pimple php56-php-pgsql php56-php-pear.noarch php56-php-pdo ' \
                  'php56-php-mysqlnd php56-php-mssql php56-php-mcrypt php56-php-mbstring php56-php-maxminddb' \
                  'php56-php-common php56-php-imap php56-php-intl php56-php-tarantool php56-php-recode' \
                  'php56-php-odbc php56-php-oci8 php56-php-litespeed php56-php-bcmath php56-php-pspell'
        if ApacheController.executioner(command) == 0:
            return "Failed to install php56-fpm"

        # Version 7.0
        command = 'yum install -y php70-php-fpm php70-php-gd php70-php-xml php70-php-twig php70-php-zstd php70-php-tidy' \
                  'php70-php-suhosin php70-php-soap php70-php-snmp php70-php-snappy php70-php-smbclient' \
                  'php70-php-process php70-php-pimple php70-php-pgsql php70-php-pear.noarch php70-php-pdo ' \
                  'php70-php-mysqlnd php70-php-mssql php70-php-mcrypt php70-php-mbstring php70-php-maxminddb' \
                  'php70-php-common php70-php-imap php70-php-intl php70-php-tarantool php70-php-recode' \
                  'php70-php-odbc php70-php-oci8 php70-php-litespeed php70-php-bcmath php70-php-pspell'
        if ApacheController.executioner(command) == 0:
            return "Failed to install php70-fpm"

        # Version 7.1
        command = 'yum install -y php71-php-fpm php71-php-gd php71-php-xml php71-php-twig php71-php-zstd php71-php-tidy' \
                  'php71-php-suhosin php71-php-soap php71-php-snmp php71-php-snappy php71-php-smbclient' \
                  'php71-php-process php71-php-pimple php71-php-pgsql php71-php-pear.noarch php71-php-pdo ' \
                  'php71-php-mysqlnd php71-php-mssql php71-php-mcrypt php71-php-mbstring php71-php-maxminddb' \
                  'php71-php-common php71-php-imap php71-php-intl php71-php-tarantool php71-php-recode' \
                  'php71-php-odbc php71-php-oci8 php71-php-litespeed php71-php-bcmath php71-php-pspell'
        if ApacheController.executioner(command) == 0:
            return "Failed to install php71-fpm"

        # Version 7.2
        command = 'yum install -y php72-php-fpm php72-php-gd php72-php-xml php72-php-twig php72-php-zstd php72-php-tidy' \
                  'php72-php-suhosin php72-php-soap php72-php-snmp php72-php-snappy php72-php-smbclient' \
                  'php72-php-process php72-php-pimple php72-php-pgsql php72-php-pear.noarch php72-php-pdo ' \
                  'php72-php-mysqlnd php72-php-mssql php72-php-mcrypt php72-php-mbstring php72-php-maxminddb' \
                  'php72-php-common php72-php-imap php72-php-intl php72-php-tarantool php72-php-recode' \
                  'php72-php-odbc php72-php-oci8 php72-php-litespeed php72-php-bcmath php72-php-pspell'
        if ApacheController.executioner(command) == 0:
            return "Failed to install php72-fpm"

        # Version 7.3
        command = 'yum install -y php73-php-fpm php73-php-gd php73-php-xml php73-php-twig php73-php-zstd php73-php-tidy' \
                  'php73-php-suhosin php73-php-soap php73-php-snmp php73-php-snappy php73-php-smbclient' \
                  'php73-php-process php73-php-pimple php73-php-pgsql php73-php-pear.noarch php73-php-pdo ' \
                  'php73-php-mysqlnd php73-php-mssql php73-php-mcrypt php73-php-mbstring php73-php-maxminddb' \
                  'php73-php-common php73-php-imap php73-php-intl php73-php-tarantool php73-php-recode' \
                  'php73-php-odbc php73-php-oci8 php73-php-litespeed php73-php-bcmath php73-php-pspell'


        if ApacheController.executioner(command) == 0:
            return "Failed to install php73-fpm"

        try:
            wwwConfPath = ApacheVhost.php54Path + "/www.conf"

            if os.path.exists(wwwConfPath):
                os.remove(wwwConfPath)

            wwwConfPath = ApacheVhost.php55Path + "/www.conf"

            if os.path.exists(wwwConfPath):
                os.remove(wwwConfPath)

            wwwConfPath = ApacheVhost.php56Path + "/www.conf"

            if os.path.exists(wwwConfPath):
                os.remove(wwwConfPath)

            wwwConfPath = ApacheVhost.php70Path + "/www.conf"

            if os.path.exists(wwwConfPath):
                os.remove(wwwConfPath)

            wwwConfPath = ApacheVhost.php71Path + "/www.conf"

            if os.path.exists(wwwConfPath):
                os.remove(wwwConfPath)

            wwwConfPath = ApacheVhost.php72Path + "/www.conf"

            if os.path.exists(wwwConfPath):
                os.remove(wwwConfPath)

            wwwConfPath = ApacheVhost.php73Path + "/www.conf"

            if os.path.exists(wwwConfPath):
                os.remove(wwwConfPath)
        except:
            pass

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