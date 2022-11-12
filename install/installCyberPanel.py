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


class InstallCyberPanel:
    mysql_Root_password = ""
    mysqlPassword = ""

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

    @staticmethod
    def stdOut(message, log=0, exit=0, code=os.EX_OK):
        install.preFlightsChecks.stdOut(message, log, exit, code)

    def installLiteSpeed(self):
        if self.ent == 0:
            if self.distro == ubuntu:
                command = "DEBIAN_FRONTEND=noninteractive apt-get -y install openlitespeed"
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
            elif self.distro == centos:
                command = 'yum install -y openlitespeed'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            else:
                command = 'dnf install -y openlitespeed'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        else:
            try:
                try:
                    command = 'groupadd nobody'
                    install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                except:
                    pass

                try:
                    command = 'usermod -a -G nobody nobody'
                    install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                except:
                    pass

                command = 'wget https://www.litespeedtech.com/packages/6.0/lsws-6.0-ent-x86_64-linux.tar.gz'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'tar zxf lsws-6.0-ent-x86_64-linux.tar.gz'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                if str.lower(self.serial) == 'trial':
                    command = 'wget -q --output-document=lsws-6.0/trial.key http://license.litespeedtech.com/reseller/trial.key'
                if self.serial == '1111-2222-3333-4444':
                    command = 'wget -q --output-document=/root/cyberpanel/install/lsws-6.0/trial.key http://license.litespeedtech.com/reseller/trial.key'
                    install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                else:
                    writeSerial = open('lsws-6.0/serial.no', 'w')
                    writeSerial.writelines(self.serial)
                    writeSerial.close()

                shutil.copy('litespeed/install.sh', 'lsws-6.0/')
                shutil.copy('litespeed/functions.sh', 'lsws-6.0/')

                os.chdir('lsws-6.0')

                command = 'chmod +x install.sh'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'chmod +x functions.sh'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = './install.sh'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                os.chdir(self.cwd)
                confPath = '/usr/local/lsws/conf/'
                shutil.copy('litespeed/httpd_config.xml', confPath)
                shutil.copy('litespeed/modsec.conf', confPath)
                shutil.copy('litespeed/httpd.conf', confPath)

                command = 'chown -R lsadm:lsadm ' + confPath
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            except BaseException as msg:
                logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installLiteSpeed]")
                return 0

            return 1

    def reStartLiteSpeed(self):
        command = self.server_root_path + "bin/lswsctrl restart"
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def fix_ols_configs(self):
        try:

            InstallCyberPanel.stdOut("Fixing OpenLiteSpeed configurations!", 1)

            ## remove example virtual host

            data = open(self.server_root_path + "conf/httpd_config.conf", 'r').readlines()

            writeDataToFile = open(self.server_root_path + "conf/httpd_config.conf", 'w')

            for items in data:
                if items.find("map") > -1 and items.find("Example") > -1:
                    continue
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("OpenLiteSpeed Configurations fixed!", 1)
        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [fix_ols_configs]")
            return 0

        return self.reStartLiteSpeed()

    def changePortTo80(self):
        try:
            InstallCyberPanel.stdOut("Changing default port to 80..", 1)

            data = open(self.server_root_path + "conf/httpd_config.conf").readlines()

            writeDataToFile = open(self.server_root_path + "conf/httpd_config.conf", 'w')

            for items in data:
                if (items.find("*:8088") > -1):
                    writeDataToFile.writelines(items.replace("*:8088", "*:80"))
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("Default port is now 80 for OpenLiteSpeed!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [changePortTo80]")
            return 0

        return self.reStartLiteSpeed()

    def installAllPHPVersions(self):

        if self.distro == ubuntu:
            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install ' \
                      'lsphp7? lsphp7?-common lsphp7?-curl lsphp7?-dev lsphp7?-imap lsphp7?-intl lsphp7?-json ' \
                      'lsphp7?-ldap lsphp7?-mysql lsphp7?-opcache lsphp7?-pspell lsphp7?-recode ' \
                      'lsphp7?-sqlite3 lsphp7?-tidy'

            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp80*'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp81*'
            os.system(command)

        elif self.distro == centos:
            command = 'yum -y groupinstall lsphp-all'
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        InstallCyberPanel.stdOut("LiteSpeed PHPs successfully installed!", 1)

        ## only php 71
        if self.distro == centos:
            command = 'yum install lsphp71 lsphp71-json lsphp71-xmlrpc lsphp71-xml lsphp71-soap lsphp71-snmp ' \
                      'lsphp71-recode lsphp71-pspell lsphp71-process lsphp71-pgsql lsphp71-pear lsphp71-pdo lsphp71-opcache ' \
                      'lsphp71-odbc lsphp71-mysqlnd lsphp71-mcrypt lsphp71-mbstring lsphp71-ldap lsphp71-intl lsphp71-imap ' \
                      'lsphp71-gmp lsphp71-gd lsphp71-enchant lsphp71-dba  lsphp71-common  lsphp71-bcmath -y'
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ## only php 72
            command = 'yum install -y lsphp72 lsphp72-json lsphp72-xmlrpc lsphp72-xml lsphp72-soap lsphp72-snmp ' \
                      'lsphp72-recode lsphp72-pspell lsphp72-process lsphp72-pgsql lsphp72-pear lsphp72-pdo lsphp72-opcache ' \
                      'lsphp72-odbc lsphp72-mysqlnd lsphp72-mcrypt lsphp72-mbstring lsphp72-ldap lsphp72-intl lsphp72-imap ' \
                      'lsphp72-gmp lsphp72-gd lsphp72-enchant lsphp72-dba  lsphp72-common  lsphp72-bcmath'

            install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ## only php 73
            command = 'yum install -y lsphp73 lsphp73-json lsphp73-xmlrpc lsphp73-xml lsphp73-tidy lsphp73-soap lsphp73-snmp ' \
                      'lsphp73-recode lsphp73-pspell lsphp73-process lsphp73-pgsql lsphp73-pear lsphp73-pdo lsphp73-opcache ' \
                      'lsphp73-odbc lsphp73-mysqlnd lsphp73-mcrypt lsphp73-mbstring lsphp73-ldap lsphp73-intl lsphp73-imap ' \
                      'lsphp73-gmp lsphp73-gd lsphp73-enchant lsphp73-dba  lsphp73-common  lsphp73-bcmath'

            install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ## only php 74
            command = 'yum install -y lsphp74 lsphp74-json lsphp74-xmlrpc lsphp74-xml lsphp74-tidy lsphp74-soap lsphp74-snmp ' \
                      'lsphp74-recode lsphp74-pspell lsphp74-process lsphp74-pgsql lsphp74-pear lsphp74-pdo lsphp74-opcache ' \
                      'lsphp74-odbc lsphp74-mysqlnd lsphp74-mcrypt lsphp74-mbstring lsphp74-ldap lsphp74-intl lsphp74-imap ' \
                      'lsphp74-gmp lsphp74-gd lsphp74-enchant lsphp74-dba lsphp74-common  lsphp74-bcmath'

            install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'yum install lsphp80* -y'
            subprocess.call(command, shell=True)

            command = 'yum install lsphp81* -y'
            subprocess.call(command, shell=True)

        if self.distro == cent8:
            command = 'dnf install lsphp71* lsphp72* lsphp73* lsphp74* lsphp80* --exclude lsphp73-pecl-zip --exclude *imagick* -y'
            subprocess.call(command, shell=True)

            command = 'dnf install lsphp81* --exclude *imagick* -y'
            subprocess.call(command, shell=True)
        
        if self.distro == openeuler:
            command = 'dnf install lsphp71* lsphp72* lsphp73* lsphp74* lsphp80* -y'
            subprocess.call(command, shell=True)

    def installMySQL(self, mysql):

        ############## Install mariadb ######################

        mRepo = '/etc/yum.repos.d/MariaDB.repo'

        if self.distro == ubuntu:

            if get_Ubuntu_release() == 18.10:
                command = 'DEBIAN_FRONTEND=noninteractive apt-get install software-properties-common -y'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = "apt-key adv --fetch-keys 'https://mariadb.org/mariadb_release_signing_key.asc'"
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "add-apt-repository 'deb [arch=amd64,arm64,ppc64el] https://mirror.yongbok.net/mariadb/repo/10.4/ubuntu bionic main'"
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = "DEBIAN_FRONTEND=noninteractive apt-get -y install mariadb-server"
        elif self.distro == centos:
            command = 'yum --enablerepo=mariadb -y install MariaDB-server MariaDB-client'
        elif self.distro == cent8 or self.distro == openeuler:
            ### check if cent8 which means Alma8 then add Mariadb 10.6 repo
#             if self.distro == cent8:
#                 content = """
# [mariadb]
# name = MariaDB
# baseurl = http://yum.mariadb.org/10.6/rhel8-amd64
# module_hotfixes=1
# gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
# gpgcheck=1
# """
#                 writeToFile = open('/etc/yum.repos.d/mariadb.repo', 'w')
#                 writeToFile.write(content)
#                 writeToFile.close()

            command = 'dnf -y install mariadb-server'

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

            command = 'mysql -u root -e "' + passwordCMD + '"'

            install.preFlightsChecks.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)

    def startMariaDB(self):

        if self.remotemysql == 'OFF':
            ############## Start mariadb ######################
            if self.distro == cent8 or self.distro == ubuntu:
                command = 'systemctl start mariadb'
            else:
                command = "systemctl start mariadb"

            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            ############## Enable mariadb at system startup ######################

            if os.path.exists('/etc/systemd/system/mysqld.service'):
                os.remove('/etc/systemd/system/mysqld.service')
            if os.path.exists('/etc/systemd/system/mariadb.service'):
                os.remove('/etc/systemd/system/mariadb.service')

            if self.distro == ubuntu:
                command = "systemctl enable mariadb"
            else:
                command = "systemctl enable mariadb"

            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

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
            data = open(fileName, 'r').readlines()

            writeDataToFile = open(fileName, 'w')
            for line in data:
                writeDataToFile.write(line.replace('utf8mb4', 'utf8'))
            writeDataToFile.close()
        except IOError as err:
            self.stdOut("[ERROR] Error in setting: " + fileName + ": " + str(err), 1, 1, os.EX_OSERR)

        os.system('systemctl restart mariadb')

        self.stdOut("MariaDB is now setup so it can support Cyberpanel's needs")

    def installPureFTPD(self):
        if self.distro == ubuntu:
            command = 'DEBIAN_FRONTEND=noninteractive apt install pure-ftpd-mysql -y'
            os.system(command)

            if get_Ubuntu_release() == 18.10:
                command = 'wget https://rep.cyberpanel.net/pure-ftpd-common_1.0.47-3_all.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'wget https://rep.cyberpanel.net/pure-ftpd-mysql_1.0.47-3_amd64.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'dpkg --install --force-confold pure-ftpd-common_1.0.47-3_all.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'dpkg --install --force-confold pure-ftpd-mysql_1.0.47-3_amd64.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        elif self.distro == centos:
            command = "yum install -y pure-ftpd"
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
        elif self.distro == cent8 or self.distro == openeuler:
            command = 'dnf install pure-ftpd -y'
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        ####### Install pureftpd to system startup

        command = "systemctl enable " + install.preFlightsChecks.pureFTPDServiceName(self.distro)
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        ###### FTP Groups and user settings settings

        command = 'groupadd -g 2001 ftpgroup'
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        command = 'useradd -u 2001 -s /bin/false -d /bin/null -c "pureftpd user" -g ftpgroup ftpuser'
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def startPureFTPD(self):
        ############## Start pureftpd ######################
        if self.distro == ubuntu:
            command = 'systemctl start pure-ftpd-mysql'
        else:
            command = 'systemctl start pure-ftpd'
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def installPureFTPDConfigurations(self, mysql):
        try:
            ## setup ssl for ftp

            InstallCyberPanel.stdOut("Configuring PureFTPD..", 1)

            try:
                os.mkdir("/etc/ssl/private")
            except:
                logging.InstallLog.writeToFile("[ERROR] Could not create directory for FTP SSL")

            if (self.distro == centos or self.distro == cent8 or self.distro == openeuler) or (
                    self.distro == ubuntu and get_Ubuntu_release() == 18.14):
                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'
            else:
                command = 'openssl req -x509 -nodes -days 7300 -newkey rsa:2048 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'

            install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

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
                try:
                    os.mkdir('/etc/pure-ftpd/conf')
                    os.mkdir('/etc/pure-ftpd/auth')
                    os.mkdir('/etc/pure-ftpd/db')
                except OSError as err:
                    self.stdOut("[ERROR] Error creating extra pure-ftpd directories: " + str(err), ".  Should be ok", 1)

            data = open(ftpdPath + "/pureftpd-mysql.conf", "r").readlines()

            writeDataToFile = open(ftpdPath + "/pureftpd-mysql.conf", "w")

            dataWritten = "MYSQLPassword " + InstallCyberPanel.mysqlPassword + '\n'
            for items in data:
                if items.find("MYSQLPassword") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            ftpConfPath = '/etc/pure-ftpd/pureftpd-mysql.conf'

            if self.remotemysql == 'ON':
                command = "sed -i 's|localhost|%s|g' %s" % (self.mysqlhost, ftpConfPath)
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|3306|%s|g' %s" % (self.mysqlport, ftpConfPath)
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|MYSQLSocket /var/lib/mysql/mysql.sock||g' %s" % (ftpConfPath)
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            if self.distro == ubuntu:

                if os.path.exists('/etc/pure-ftpd/db/mysql.conf'):
                    os.remove('/etc/pure-ftpd/db/mysql.conf')
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')
                else:
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')

                command = 'echo 1 > /etc/pure-ftpd/conf/TLS'
                subprocess.call(command, shell=True)

                command = 'echo %s > /etc/pure-ftpd/conf/ForcePassiveIP' % (self.publicip)
                subprocess.call(command, shell=True)

                command = 'echo "40110 40210" > /etc/pure-ftpd/conf/PassivePortRange'
                subprocess.call(command, shell=True)

                command = 'echo "no" > /etc/pure-ftpd/conf/UnixAuthentication'
                subprocess.call(command, shell=True)

                command = 'echo "/etc/pure-ftpd/db/mysql.conf" > /etc/pure-ftpd/conf/MySQLConfigFile'
                subprocess.call(command, shell=True)

                command = 'ln -s /etc/pure-ftpd/conf/MySQLConfigFile /etc/pure-ftpd/auth/30mysql'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'ln -s /etc/pure-ftpd/conf/UnixAuthentication /etc/pure-ftpd/auth/65unix'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'systemctl restart pure-ftpd-mysql.service'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            InstallCyberPanel.stdOut("PureFTPD configured!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installPureFTPDConfigurations]")
            return 0

    def installPowerDNS(self):
        try:

            if self.distro == ubuntu or self.distro == cent8 or self.distro == openeuler:
                command = 'systemctl stop systemd-resolved'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                command = 'systemctl disable systemd-resolved.service'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

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

            # if self.distro == cent8:
            #     command = 'dnf config-manager --set-enabled PowerTools'
            #     install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            #
            #     command = 'curl -o /etc/yum.repos.d/powerdns-auth-master.repo https://repo.powerdns.com/repo-files/centos-auth-master.repo'
            #     install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            if self.distro == ubuntu:
                command = "DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server pdns-backend-mysql"
                os.system(command)
                return 1
            else:
                command = 'yum -y install pdns pdns-backend-mysql'

            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

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

            data = open(dnsPath, "r").readlines()

            writeDataToFile = open(dnsPath, "w")

            dataWritten = "gmysql-password=" + mysqlPassword + "\n"

            for items in data:
                if items.find("gmysql-password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            if self.remotemysql == 'ON':
                command = "sed -i 's|gmysql-host=localhost|gmysql-host=%s|g' %s" % (self.mysqlhost, dnsPath)
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|gmysql-port=3306|gmysql-port=%s|g' %s" % (self.mysqlport, dnsPath)
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            InstallCyberPanel.stdOut("PowerDNS configured!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installPowerDNSConfigurations]")
            return 0
        return 1

    def startPowerDNS(self):

        ############## Start PowerDNS ######################

        command = 'systemctl enable pdns'
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'systemctl start pdns'
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)


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
        command = 'chmod 640 %s' % (file_name)
        install.preFlightsChecks.call(command, distro, '[chmod]',
                                      '',
                                      1, 0, os.EX_OSERR)
        command = 'chown root:cyberpanel %s' % (file_name)
        install.preFlightsChecks.call(command, distro, '[chmod]',
                                      '',
                                      1, 0, os.EX_OSERR)
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
