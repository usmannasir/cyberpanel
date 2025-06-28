import shutil
import subprocess
import os
from mysqlUtilities import mysqlUtilities
import installLog as logging
import randomPassword
import errno
import MySQLdb as mariadb
import install
from os.path import exists
import time
from installHelpers import PackageManager, ServiceManager, ConfigFileHandler, CommandExecutor, PHPInstaller, FileSystemHelper

# distros
centos = 0
ubuntu = 1
cent8 = 2
openeuler = 3


def get_Ubuntu_release():
    release = -1
    if exists("/etc/lsb-release"):
        distro_file = "/etc/lsb-release"
        with open(distro_file) as f:
            for line in f:
                if line[:16] == "DISTRIB_RELEASE=":
                    release = float(line[16:])

        if release == -1:
            print("Can't find distro release name in " + distro_file + " - fatal error")

    else:
        logging.InstallLog.writeToFile("Can't find linux release file - fatal error")
        print("Can't find linux release file - fatal error")
        os._exit(os.EX_UNAVAILABLE)

    return release


def FetchCloudLinuxAlmaVersionVersion():
    if os.path.exists('/etc/os-release'):
        data = open('/etc/os-release', 'r').read()
        if (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('8.9') > -1 or data.find('Anatoly Levchenko') > -1 or data.find('VERSION="8.') > -1):
            return 'cl-89'
        elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('8.8') > -1 or data.find('Anatoly Filipchenko') > -1):
            return 'cl-88'
        elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('9.4') > -1 or data.find('VERSION="9.') > -1):
            return 'cl-88'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('8.9') > -1 or data.find('Midnight Oncilla') > -1 or data.find('VERSION="8.') > -1):
            return 'al-88'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('8.7') > -1 or data.find('Stone Smilodon') > -1):
            return 'al-87'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('9.4') > -1 or data.find('9.3') > -1 or data.find('Shamrock Pampas') > -1 or data.find('Seafoam Ocelot') > -1 or data.find('VERSION="9.') > -1):
            return 'al-93'
    else:
        return -1

class InstallCyberPanel:
    mysql_Root_password = ""
    mysqlPassword = ""
    CloudLinux8 = 0

    @staticmethod
    def ISARM():

        try:
            command = 'uname -a'
            try:
                result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
            except:
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

            if 'aarch64' in result.stdout:
                return True
            else:
                return False
        except:
            return False

    @staticmethod
    def OSFlags():
        if os.path.exists("/etc/redhat-release"):
            data = open('/etc/redhat-release', 'r').read()

            if data.find('CloudLinux 8') > -1 or data.find('cloudlinux 8') > -1:
                InstallCyberPanel.CloudLinux8 = 1

    def __init__(self, rootPath, cwd, distro, ent, serial=None, port=None, ftp=None, dns=None, publicip=None,
                 remotemysql=None, mysqlhost=None, mysqldb=None, mysqluser=None, mysqlpassword=None, mysqlport=None):
        self.server_root_path = rootPath
        self.cwd = cwd
        self.distro = distro
        self.ent = ent
        self.serial = serial
        self.port = port
        self.ftp = None
        self.dns = dns
        self.publicip = publicip
        self.remotemysql = remotemysql
        self.mysqlhost = mysqlhost
        self.mysqluser = mysqluser
        self.mysqlpassword = mysqlpassword
        self.mysqlport = mysqlport
        self.mysqldb = mysqldb

        ## TURN ON OS FLAGS FOR SPECIFIC NEEDS LATER

        InstallCyberPanel.OSFlags()

    @staticmethod
    def stdOut(message, log=0, exit=0, code=os.EX_OK):
        install.preFlightsChecks.stdOut(message, log, exit, code)

    def installLiteSpeed(self):
        if self.ent == 0:
            PackageManager.install_packages('openlitespeed', self.distro, ubuntu, centos, cent8, openeuler, 
                                          use_shell=(self.distro == ubuntu))

        else:
            try:
                try:
                    CommandExecutor.execute('groupadd nobody', self.distro, exit_on_error=False)
                except:
                    pass

                try:
                    CommandExecutor.execute('usermod -a -G nobody nobody', self.distro, exit_on_error=False)
                except:
                    pass

                if InstallCyberPanel.ISARM():
                    command = 'wget https://www.litespeedtech.com/packages/6.0/lsws-6.2-ent-aarch64-linux.tar.gz'
                else:
                    command = 'wget https://www.litespeedtech.com/packages/6.0/lsws-6.2-ent-x86_64-linux.tar.gz'

                CommandExecutor.execute(command, self.distro)

                if InstallCyberPanel.ISARM():
                    command = 'tar zxf lsws-6.2-ent-aarch64-linux.tar.gz'
                else:
                    command = 'tar zxf lsws-6.2-ent-x86_64-linux.tar.gz'

                CommandExecutor.execute(command, self.distro)

                if str.lower(self.serial) == 'trial':
                    command = 'wget -q --output-document=lsws-6.2/trial.key http://license.litespeedtech.com/reseller/trial.key'
                if self.serial == '1111-2222-3333-4444':
                    command = 'wget -q --output-document=/root/cyberpanel/install/lsws-6.2/trial.key http://license.litespeedtech.com/reseller/trial.key'
                    CommandExecutor.execute(command, self.distro)
                else:
                    writeSerial = open('lsws-6.2/serial.no', 'w')
                    writeSerial.writelines(self.serial)
                    writeSerial.close()

                shutil.copy('litespeed/install.sh', 'lsws-6.2/')
                shutil.copy('litespeed/functions.sh', 'lsws-6.2/')

                os.chdir('lsws-6.2')

                CommandExecutor.execute('chmod +x install.sh', self.distro)
                CommandExecutor.execute('chmod +x functions.sh', self.distro)
                CommandExecutor.execute('./install.sh', self.distro)

                os.chdir(self.cwd)
                confPath = '/usr/local/lsws/conf/'
                shutil.copy('litespeed/httpd_config.xml', confPath)
                shutil.copy('litespeed/modsec.conf', confPath)
                shutil.copy('litespeed/httpd.conf', confPath)

                CommandExecutor.execute('chown -R lsadm:lsadm ' + confPath, self.distro, exit_on_error=False)

            except BaseException as msg:
                logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installLiteSpeed]")
                return 0

            return 1

    def reStartLiteSpeed(self):
        command = self.server_root_path + "bin/lswsctrl restart"
        CommandExecutor.execute(command, self.distro, exit_on_error=False)

    def fix_ols_configs(self):
        try:
            InstallCyberPanel.stdOut("Fixing OpenLiteSpeed configurations!", 1)

            ## remove example virtual host
            config_path = self.server_root_path + "conf/httpd_config.conf"
            data = open(config_path, 'r').readlines()

            with open(config_path, 'w') as writeDataToFile:
                for items in data:
                    if not (items.find("map") > -1 and items.find("Example") > -1):
                        writeDataToFile.writelines(items)

            InstallCyberPanel.stdOut("OpenLiteSpeed Configurations fixed!", 1)
        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [fix_ols_configs]")
            return 0

        return self.reStartLiteSpeed()

    def changePortTo80(self):
        try:
            InstallCyberPanel.stdOut("Changing default port to 80..", 1)

            config_path = self.server_root_path + "conf/httpd_config.conf"
            replacements = [("*:8088", "*:80")]
            
            # Use sed for simple replacement
            ConfigFileHandler.sed_replace(config_path, "*:8088", "*:80", self.distro)

            InstallCyberPanel.stdOut("Default port is now 80 for OpenLiteSpeed!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [changePortTo80]")
            return 0

        return self.reStartLiteSpeed()

    def installAllPHPVersions(self):
        if self.distro == ubuntu:
            PHPInstaller.install_php_ubuntu()
        else:
            PHPInstaller.install_php_centos(self.distro, centos, cent8, openeuler)
        
        InstallCyberPanel.stdOut("LiteSpeed PHPs successfully installed!", 1)

    def installMySQL(self, mysql):

        ############## Install mariadb ######################

        if self.distro == ubuntu:
            PackageManager.install_packages('software-properties-common', self.distro, ubuntu, centos, cent8, openeuler, use_shell=True)
            PackageManager.install_packages('apt-transport-https curl', self.distro, ubuntu, centos, cent8, openeuler, use_shell=True)
            
            FileSystemHelper.create_directory('/etc/apt/keyrings')
            CommandExecutor.execute("curl -o /etc/apt/keyrings/mariadb-keyring.pgp 'https://mariadb.org/mariadb_release_signing_key.pgp'", self.distro)
            RepoPath = '/etc/apt/sources.list.d/mariadb.sources'
            # Determine the Ubuntu codename for MariaDB repo
            ubuntu_version = get_Ubuntu_release()
            if ubuntu_version >= 24.04:
                suite = 'noble'  # Ubuntu 24.04 LTS
            elif ubuntu_version >= 22.04:
                suite = 'jammy'  # Ubuntu 22.04 LTS
            else:
                suite = 'focal'  # Ubuntu 20.04 LTS and earlier
                
            RepoContent = f"""
# MariaDB 10.11 repository list - created 2023-12-11 07:53 UTC
# https://mariadb.org/download/
X-Repolib-Name: MariaDB
Types: deb
# deb.mariadb.org is a dynamic mirror if your preferred mirror goes offline. See https://mariadb.org/mirrorbits/ for details.
# URIs: https://deb.mariadb.org/10.11/ubuntu
URIs: https://mirrors.gigenet.com/mariadb/repo/10.11/ubuntu
Suites: {suite}
Components: main main/debug
Signed-By: /etc/apt/keyrings/mariadb-keyring.pgp
"""

            if get_Ubuntu_release() > 21.00:
                # Use the MariaDB repository setup script which automatically handles different Ubuntu versions
                command = 'curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash -s -- --mariadb-server-version=10.11'
                CommandExecutor.execute(command, self.distro, exit_code=os.EX_OSERR)
            #     WriteToFile = open(RepoPath, 'w')
            #     WriteToFile.write(RepoContent)
            #     WriteToFile.close()



            command = 'DEBIAN_FRONTEND=noninteractive apt-get update -y'
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)


            command = "DEBIAN_FRONTEND=noninteractive apt-get install mariadb-server -y"
        elif self.distro == centos:

            RepoPath = '/etc/yum.repos.d/mariadb.repo'
            RepoContent = f"""
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/10.11/rhel8-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1            
"""
            WriteToFile = open(RepoPath, 'w')
            WriteToFile.write(RepoContent)
            WriteToFile.close()

            command = 'dnf install mariadb-server -y'
        elif self.distro == cent8 or self.distro == openeuler:

            clAPVersion = FetchCloudLinuxAlmaVersionVersion()
            type = clAPVersion.split('-')[0]
            version = int(clAPVersion.split('-')[1])


            if type == 'cl' and version >= 88:
                CommandExecutor.execute('yum remove db-governor db-governor-mysql -y', self.distro)
                PackageManager.install_packages('governor-mysql', self.distro, ubuntu, centos, cent8, openeuler)
                CommandExecutor.execute('/usr/share/lve/dbgovernor/mysqlgovernor.py --mysql-version=mariadb106', self.distro)
                command = '/usr/share/lve/dbgovernor/mysqlgovernor.py --install --yes'

            else:
                CommandExecutor.execute('curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash -s -- --mariadb-server-version=10.11', self.distro)
                CommandExecutor.execute('yum remove mariadb* -y', self.distro)
                CommandExecutor.execute('sudo dnf -qy module disable mariadb', self.distro)
                CommandExecutor.execute('sudo dnf module reset mariadb -y', self.distro)


                command = 'dnf install MariaDB-server MariaDB-client MariaDB-backup -y'

        install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        ############## Start mariadb ######################

        self.startMariaDB()

    def changeMYSQLRootPassword(self):
        if self.remotemysql == 'OFF':
            if self.distro == ubuntu:
                passwordCMD = "use mysql;DROP DATABASE IF EXISTS test;DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%%';GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY '%s';UPDATE user SET plugin='' WHERE User='root';flush privileges;" % (
                    InstallCyberPanel.mysql_Root_password)
            else:
                passwordCMD = "use mysql;DROP DATABASE IF EXISTS test;DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%%';GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY '%s';flush privileges;" % (
                    InstallCyberPanel.mysql_Root_password)

            command = 'mariadb -u root -e "' + passwordCMD + '"'

            install.preFlightsChecks.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)

    def startMariaDB(self):
        if self.remotemysql == 'OFF':
            ############## Start mariadb ######################
            ServiceManager.start_service('mariadb', self.distro)

            ############## Enable mariadb at system startup ######################
            if os.path.exists('/etc/systemd/system/mysqld.service'):
                os.remove('/etc/systemd/system/mysqld.service')
            if os.path.exists('/etc/systemd/system/mariadb.service'):
                os.remove('/etc/systemd/system/mariadb.service')

            ServiceManager.enable_service('mariadb', self.distro)

    def fixMariaDB(self):
        self.stdOut("Setup MariaDB so it can support Cyberpanel's needs")

        conn = mariadb.connect(user='root', passwd=self.mysql_Root_password)
        cursor = conn.cursor()
        cursor.execute('set global innodb_file_per_table = on;')
        try:
            cursor.execute('set global innodb_file_format = Barracuda;')
            cursor.execute('set global innodb_large_prefix = on;')
        except BaseException as msg:
            self.stdOut('%s. [ERROR:335]' % (str(msg)))
        cursor.close()
        conn.close()

        try:
            fileName = '/etc/mysql/mariadb.conf.d/50-server.cnf'
            ConfigFileHandler.sed_replace(fileName, 'utf8mb4', 'utf8', self.distro)
        except IOError as err:
            self.stdOut("[ERROR] Error in setting: " + fileName + ": " + str(err), 1, 1, os.EX_OSERR)

        ServiceManager.restart_service('mariadb', self.distro)

        self.stdOut("MariaDB is now setup so it can support Cyberpanel's needs")

    def installPureFTPD(self):
        if self.distro == ubuntu:
            command = 'DEBIAN_FRONTEND=noninteractive apt install pure-ftpd-mysql -y'
            os.system(command)

            if get_Ubuntu_release() == 18.10:
                urls = [
                    'https://rep.cyberpanel.net/pure-ftpd-common_1.0.47-3_all.deb',
                    'https://rep.cyberpanel.net/pure-ftpd-mysql_1.0.47-3_amd64.deb'
                ]
                packages = [
                    'pure-ftpd-common_1.0.47-3_all.deb',
                    'pure-ftpd-mysql_1.0.47-3_amd64.deb'
                ]
                
                for url in urls:
                    CommandExecutor.execute(f'wget {url}', self.distro)
                
                for package in packages:
                    CommandExecutor.execute(f'dpkg --install --force-confold {package}', self.distro)
        else:
            PackageManager.install_packages('pure-ftpd', self.distro, ubuntu, centos, cent8, openeuler)

        ####### Install pureftpd to system startup
        service_name = install.preFlightsChecks.pureFTPDServiceName(self.distro)
        ServiceManager.enable_service(service_name, self.distro)

        ###### FTP Groups and user settings settings
        FileSystemHelper.create_user_and_group('ftpuser', 'ftpgroup', 2001, 2001, 
                                             shell='/bin/false', home='/bin/null', distro=self.distro)

    def startPureFTPD(self):
        ############## Start pureftpd ######################
        service_name = 'pure-ftpd-mysql' if self.distro == ubuntu else 'pure-ftpd'
        ServiceManager.start_service(service_name, self.distro)

    def installPureFTPDConfigurations(self, mysql):
        try:
            ## setup ssl for ftp

            InstallCyberPanel.stdOut("Configuring PureFTPD..", 1)

            FileSystemHelper.create_directory("/etc/ssl/private")

            if (self.distro == centos or self.distro == cent8 or self.distro == openeuler) or (
                    self.distro == ubuntu and get_Ubuntu_release() == 18.14):
                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'
            else:
                command = 'openssl req -x509 -nodes -days 7300 -newkey rsa:2048 -subj "/C=US/ST=Denial/L=Sprinal-ield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'

            CommandExecutor.execute(command, self.distro, exit_on_error=False)

            os.chdir(self.cwd)
            ftpdPath = "/etc/pure-ftpd"

            if os.path.exists(ftpdPath):
                shutil.rmtree(ftpdPath)
                if mysql == 'Two':
                    shutil.copytree("pure-ftpd", ftpdPath)
                else:
                    shutil.copytree("pure-ftpd-one", ftpdPath)
            else:
                if mysql == 'Two':
                    shutil.copytree("pure-ftpd", ftpdPath)
                else:
                    shutil.copytree("pure-ftpd-one", ftpdPath)

            if self.distro == ubuntu:
                for dir_path in ['/etc/pure-ftpd/conf', '/etc/pure-ftpd/auth', '/etc/pure-ftpd/db']:
                    FileSystemHelper.create_directory(dir_path)

            # Update MySQL password in pureftpd config
            pureftpd_config = ftpdPath + "/pureftpd-mysql.conf"
            replacements = [("MYSQLPassword", "MYSQLPassword " + InstallCyberPanel.mysqlPassword)]
            ConfigFileHandler.replace_in_file(pureftpd_config, replacements)

            ftpConfPath = '/etc/pure-ftpd/pureftpd-mysql.conf'

            if self.remotemysql == 'ON':
                ConfigFileHandler.sed_replace(ftpConfPath, 'localhost', self.mysqlhost, self.distro)
                ConfigFileHandler.sed_replace(ftpConfPath, '3306', self.mysqlport, self.distro)
                ConfigFileHandler.sed_replace(ftpConfPath, 'MYSQLSocket /var/lib/mysql/mysql.sock', '', self.distro)

            if self.distro == ubuntu:

                if os.path.exists('/etc/pure-ftpd/db/mysql.conf'):
                    os.remove('/etc/pure-ftpd/db/mysql.conf')
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')
                else:
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')

                # Write configuration values to files
                config_values = [
                    ('1', '/etc/pure-ftpd/conf/TLS'),
                    (str(self.publicip), '/etc/pure-ftpd/conf/ForcePassiveIP'),
                    ('40110 40210', '/etc/pure-ftpd/conf/PassivePortRange'),
                    ('no', '/etc/pure-ftpd/conf/UnixAuthentication'),
                    ('/etc/pure-ftpd/db/mysql.conf', '/etc/pure-ftpd/conf/MySQLConfigFile')
                ]
                
                for value, filepath in config_values:
                    with open(filepath, 'w') as f:
                        f.write(value)

                CommandExecutor.execute('ln -s /etc/pure-ftpd/conf/MySQLConfigFile /etc/pure-ftpd/auth/30mysql', self.distro)
                CommandExecutor.execute('ln -s /etc/pure-ftpd/conf/UnixAuthentication /etc/pure-ftpd/auth/65unix', self.distro)
                ServiceManager.restart_service('pure-ftpd-mysql.service', self.distro)




                ubuntu_version = get_Ubuntu_release()
                if ubuntu_version > 21.00:
                    ### change mysql md5 to crypt for Ubuntu 22.04+ including 24.04
                    ConfigFileHandler.sed_replace('/etc/pure-ftpd/db/mysql.conf', 'MYSQLCrypt md5', 'MYSQLCrypt crypt', self.distro)
                    ServiceManager.restart_service('pure-ftpd-mysql.service', self.distro)
            else:

                try:
                    clAPVersion = FetchCloudLinuxAlmaVersionVersion()
                    type = clAPVersion.split('-')[0]
                    version = int(clAPVersion.split('-')[1])

                    if type == 'al' and version >= 90:
                        ConfigFileHandler.sed_replace('/etc/pure-ftpd/pureftpd-mysql.conf', 'MYSQLCrypt md5', 'MYSQLCrypt crypt', self.distro)
                except:
                    pass



            InstallCyberPanel.stdOut("PureFTPD configured!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installPureFTPDConfigurations]")
            return 0

    def installPowerDNS(self):
        try:
            if self.distro == ubuntu or self.distro == cent8 or self.distro == openeuler:
                ServiceManager.stop_service('systemd-resolved', self.distro, exit_on_error=False)
                ServiceManager.disable_service('systemd-resolved.service', self.distro, exit_on_error=False)

                try:
                    os.rename('/etc/resolv.conf', 'etc/resolved.conf')
                except OSError as e:
                    if e.errno != errno.EEXIST and e.errno != errno.ENOENT:
                        InstallCyberPanel.stdOut("[ERROR] Unable to rename /etc/resolv.conf to install PowerDNS: " +
                                                 str(e), 1, 1, os.EX_OSERR)
                    try:
                        os.remove('/etc/resolv.conf')
                    except OSError as e1:
                        InstallCyberPanel.stdOut(
                            "[ERROR] Unable to remove existing /etc/resolv.conf to install PowerDNS: " +
                            str(e1), 1, 1, os.EX_OSERR)

                # try:
                #     f = open('/etc/resolv.conf', 'a')
                #     f.write('nameserver 8.8.8.8')
                #     f.close()
                # except IOError as e:
                #     InstallCyberPanel.stdOut("[ERROR] Unable to create /etc/resolv.conf: " + str(e) +
                #                              ".  This may need to be fixed manually as 'echo \"nameserver 8.8.8.8\"> "
                #                              "/etc/resolv.conf'", 1, 1, os.EX_OSERR)

            if self.distro == ubuntu:
                command = "DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server pdns-backend-mysql"
                os.system(command)
                return 1
            else:
                PackageManager.install_packages('pdns pdns-backend-mysql', self.distro, ubuntu, centos, cent8, openeuler)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [powerDNS]")

    def installPowerDNSConfigurations(self, mysqlPassword, mysql):
        try:

            InstallCyberPanel.stdOut("Configuring PowerDNS..", 1)

            os.chdir(self.cwd)
            if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                dnsPath = "/etc/pdns/pdns.conf"
            else:
                dnsPath = "/etc/powerdns/pdns.conf"

            if os.path.exists(dnsPath):
                os.remove(dnsPath)
                if mysql == 'Two':
                    shutil.copy("dns/pdns.conf", dnsPath)
                else:
                    shutil.copy("dns-one/pdns.conf", dnsPath)
            else:
                if mysql == 'Two':
                    shutil.copy("dns/pdns.conf", dnsPath)
                else:
                    shutil.copy("dns-one/pdns.conf", dnsPath)

            # Update MySQL password in PowerDNS config
            replacements = [("gmysql-password", "gmysql-password=" + mysqlPassword)]
            ConfigFileHandler.replace_in_file(dnsPath, replacements)

            if self.remotemysql == 'ON':
                ConfigFileHandler.sed_replace(dnsPath, 'gmysql-host=localhost', f'gmysql-host={self.mysqlhost}', self.distro)
                ConfigFileHandler.sed_replace(dnsPath, 'gmysql-port=3306', f'gmysql-port={self.mysqlport}', self.distro)

            InstallCyberPanel.stdOut("PowerDNS configured!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installPowerDNSConfigurations]")
            return 0
        return 1

    def startPowerDNS(self):
        ############## Start PowerDNS ######################
        ServiceManager.enable_service('pdns', self.distro)
        ServiceManager.start_service('pdns', self.distro)


def Main(cwd, mysql, distro, ent, serial=None, port="8090", ftp=None, dns=None, publicip=None, remotemysql=None,
         mysqlhost=None, mysqldb=None, mysqluser=None, mysqlpassword=None, mysqlport=None):
    InstallCyberPanel.mysqlPassword = randomPassword.generate_pass()
    InstallCyberPanel.mysql_Root_password = randomPassword.generate_pass()

    file_name = '/etc/cyberpanel/mysqlPassword'

    if remotemysql == 'OFF':
        if os.access(file_name, os.F_OK):
            password = open(file_name, 'r')
            InstallCyberPanel.mysql_Root_password = password.readline()
            password.close()
        else:
            password = open(file_name, "w")
            password.writelines(InstallCyberPanel.mysql_Root_password)
            password.close()
    else:
        mysqlData = {'remotemysql': remotemysql, 'mysqlhost': mysqlhost, 'mysqldb': mysqldb, 'mysqluser': mysqluser,
                     'mysqlpassword': mysqlpassword, 'mysqlport': mysqlport}
        from json import dumps
        writeToFile = open(file_name, 'w')
        writeToFile.write(dumps(mysqlData))
        writeToFile.close()

        if install.preFlightsChecks.debug:
            print(open(file_name, 'r').read())
            time.sleep(10)

    try:
        CommandExecutor.execute(f'chmod 640 {file_name}', distro, '[chmod]', exit_on_error=False)
        CommandExecutor.execute(f'chown root:cyberpanel {file_name}', distro, '[chmod]', exit_on_error=False)
    except:
        pass

    if distro == centos:
        InstallCyberPanel.mysqlPassword = randomPassword.generate_pass()
    else:
        InstallCyberPanel.mysqlPassword = InstallCyberPanel.mysql_Root_password

    installer = InstallCyberPanel("/usr/local/lsws/", cwd, distro, ent, serial, port, ftp, dns, publicip, remotemysql,
                                  mysqlhost, mysqldb, mysqluser, mysqlpassword, mysqlport)

    logging.InstallLog.writeToFile('Installing LiteSpeed Web server,40')
    installer.installLiteSpeed()
    if ent == 0:
        installer.changePortTo80()
    logging.InstallLog.writeToFile('Installing Optimized PHPs..,50')
    installer.installAllPHPVersions()
    if ent == 0:
        installer.fix_ols_configs()

    logging.InstallLog.writeToFile('Installing MySQL,60')
    installer.installMySQL(mysql)
    installer.changeMYSQLRootPassword()

    installer.startMariaDB()

    if remotemysql == 'OFF':
        if distro == ubuntu:
            installer.fixMariaDB()

    mysqlUtilities.createDatabase("cyberpanel", "cyberpanel", InstallCyberPanel.mysqlPassword, publicip)

    if ftp is None:
        installer.installPureFTPD()
        installer.installPureFTPDConfigurations(mysql)
        installer.startPureFTPD()
    else:
        if ftp == 'ON':
            installer.installPureFTPD()
            installer.installPureFTPDConfigurations(mysql)
            installer.startPureFTPD()

    if dns is None:
        installer.installPowerDNS()
        installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
        installer.startPowerDNS()
    else:
        if dns == 'ON':
            installer.installPowerDNS()
            installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
            installer.startPowerDNS()
