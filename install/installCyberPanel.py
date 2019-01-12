import shutil
import subprocess
import os
from mysqlUtilities import mysqlUtilities
import installLog as logging
import shlex
import randomPassword
import errno
import MySQLdb as mariadb
import install

#distros
centos=0
ubuntu=1

class InstallCyberPanel:

    mysql_Root_password = ""
    mysqlPassword = ""

    def __init__(self, rootPath, cwd, distro, ent, serial = None):
        self.server_root_path = rootPath
        self.cwd = cwd
        self.distro = distro
        self.ent = ent
        self.serial = serial

    @staticmethod
    def stdOut(message, log=0, exit=0, code=os.EX_OK):
        install.preFlightsChecks.stdOut(message, log, exit, code)

    def installLiteSpeed(self):
        if self.ent == 0:
            if self.distro == ubuntu:
                command = "apt-get -y install openlitespeed"
            else:
                command = 'yum install -y openlitespeed'

            install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                          'Install LiteSpeed.',
                                          1, 1, os.EX_OSERR)
        else:
            try:
                try:
                    command = 'groupadd nobody'
                    install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                                  'groupadd nobody',
                                                  1, 0, os.EX_OSERR)
                except:
                    pass

                try:
                    command = 'usermod -a -G nobody nobody'
                    install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                                  'groupadd nobody',
                                                  1, 0, os.EX_OSERR)
                except:
                    pass

                command = 'wget https://www.litespeedtech.com/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz'
                install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                              'Install LiteSpeed Webserver Enterprise.',
                                              1, 1, os.EX_OSERR)

                command = 'tar zxf lsws-5.3.5-ent-x86_64-linux.tar.gz'
                install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                              'Install LiteSpeed Webserver Enterprise.',
                                              1, 1, os.EX_OSERR)

                writeSerial = open('lsws-5.3.5/serial.no', 'w')
                writeSerial.writelines(self.serial)
                writeSerial.close()

                shutil.copy('litespeed/install.sh', 'lsws-5.3.5/')
                shutil.copy('litespeed/functions.sh', 'lsws-5.3.5/')

                os.chdir('lsws-5.3.5')

                command = 'chmod +x install.sh'
                install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                              'Install LiteSpeed Webserver Enterprise.',
                                              1, 1, os.EX_OSERR)

                command = 'chmod +x functions.sh'
                install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                              'Install LiteSpeed Webserver Enterprise.',
                                              1, 1, os.EX_OSERR)

                command = './install.sh'
                install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                              'Install LiteSpeed Webserver Enterprise.',
                                              1, 1, os.EX_OSERR)

                os.chdir(self.cwd)
                confPath = '/usr/local/lsws/conf/'
                shutil.copy('litespeed/httpd_config.xml', confPath)
                shutil.copy('litespeed/modsec.conf', confPath)
                shutil.copy('litespeed/httpd.conf', confPath)

                command = 'chown -R lsadm:lsadm ' + confPath
                install.preFlightsChecks.call(command, self.distro, '[installLiteSpeed]',
                                              'Install LiteSpeed Webserver Enterprise.',
                                              1, 0, os.EX_OSERR)

            except OSError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
                return 0
            except ValueError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
                return 0

            return 1

    def reStartLiteSpeed(self):
        command = self.server_root_path+"bin/lswsctrl restart"
        install.preFlightsChecks.call(command, self.distro, '[reStartLiteSpeed]',
                                      'Restart LiteSpeed WebServer',
                                      1, 0, os.EX_OSERR)

    def fix_ols_configs(self):
        try:

            InstallCyberPanel.stdOut("Fixing OpenLiteSpeed configurations!", 1)

            ## remove example virtual host

            data = open(self.server_root_path+"conf/httpd_config.conf",'r').readlines()

            writeDataToFile = open(self.server_root_path + "conf/httpd_config.conf", 'w')

            for items in data:
                if items.find("map") > -1 and items.find("Example") > -1:
                    continue
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("OpenLiteSpeed Configurations fixed!", 1)
        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [fix_ols_configs]")
            return 0

        return self.reStartLiteSpeed()

    def changePortTo80(self):
        try:
            InstallCyberPanel.stdOut("Changing default port to 80..", 1)

            data = open(self.server_root_path+"conf/httpd_config.conf").readlines()

            writeDataToFile = open(self.server_root_path+"conf/httpd_config.conf", 'w')

            for items in data:
                if (items.find("*:8088") > -1):
                    writeDataToFile.writelines(items.replace("*:8088","*:80"))
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("Default port is now 80 for OpenLiteSpeed!", 1)

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [changePortTo80]")
            return 0

        return self.reStartLiteSpeed()

    def setupFileManager(self):
        if self.ent == 0:
            try:
                InstallCyberPanel.stdOut("Setting up Filemanager files..", 1)

                os.chdir(self.cwd)

                fileManagerPath = self.server_root_path+"Example/html/FileManager"
                shutil.copytree("FileManager",fileManagerPath)

                ## remove unnecessary files

                fileManagerPath = self.server_root_path + "Example/html/"

                shutil.rmtree(fileManagerPath+"protected")
                shutil.rmtree(fileManagerPath+"blocked")
                os.remove(fileManagerPath+"phpinfo.php")
                os.remove(fileManagerPath + "upload.html")
                os.remove(fileManagerPath + "upload.php")

                InstallCyberPanel.stdOut("Filemanager files are set!", 1)

            except BaseException, msg:
                logging.InstallLog.writeToFile(str(msg) + " [setupFileManager]")
        else:
            try:
                InstallCyberPanel.stdOut("Setting up Filemanager files..", 1)

                os.chdir(self.cwd)

                fileManagerPath = self.server_root_path + "/FileManager"
                shutil.copytree("FileManager", fileManagerPath)

                ## remove unnecessary files

                command = 'chmod -R 777 ' + fileManagerPath
                install.preFlightsChecks.call(command, self.distro, '[setupFileManager]',
                                              'Change Filemanager permissions.',
                                              1, 0, os.EX_OSERR)

                InstallCyberPanel.stdOut("Filemanager files are set!", 1)

            except BaseException, msg:
                logging.InstallLog.writeToFile(str(msg) + " [setupFileManager]")

    def installAllPHPVersions(self):

        if self.distro == ubuntu:
            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install ' \
                      'lsphp7? lsphp7?-common lsphp7?-curl lsphp7?-dev lsphp7?-imap lsphp7?-intl lsphp7?-json ' \
                      'lsphp7?-ldap lsphp7?-mysql lsphp7?-opcache lsphp7?-pspell lsphp7?-recode ' \
                      'lsphp7?-sqlite3 lsphp7?-tidy'

            res = os.system(command)
            if res != 0:
                InstallCyberPanel.stdOut("Failed to install PHP on Ubuntu.", 1, 1)

        else:
            command = 'yum -y groupinstall lsphp-all'

            install.preFlightsChecks.call(command, self.distro, '[installAllPHPVersions]',
                                          'Install PHP ALL',
                                          1, 1, os.EX_OSERR)

        InstallCyberPanel.stdOut("LiteSpeed PHPs successfully installed!", 1)

        ## only php 71
        if self.distro == centos:

            command = 'yum install lsphp71 lsphp71-json lsphp71-xmlrpc lsphp71-xml lsphp71-tidy lsphp71-soap lsphp71-snmp ' \
                      'lsphp71-recode lsphp71-pspell lsphp71-process lsphp71-pgsql lsphp71-pear lsphp71-pdo lsphp71-opcache ' \
                      'lsphp71-odbc lsphp71-mysqlnd lsphp71-mcrypt lsphp71-mbstring lsphp71-ldap lsphp71-intl lsphp71-imap ' \
                      'lsphp71-gmp lsphp71-gd lsphp71-enchant lsphp71-dba  lsphp71-common  lsphp71-bcmath -y'
            install.preFlightsChecks.call(command, self.distro, '[installAllPHPVersions]',
                                          'Install PHP 71',
                                          1, 0, os.EX_OSERR)
            ## only php 72
            command = 'yum install -y lsphp72 lsphp72-json lsphp72-xmlrpc lsphp72-xml lsphp72-tidy lsphp72-soap lsphp72-snmp ' \
                      'lsphp72-recode lsphp72-pspell lsphp72-process lsphp72-pgsql lsphp72-pear lsphp72-pdo lsphp72-opcache ' \
                      'lsphp72-odbc lsphp72-mysqlnd lsphp72-mcrypt lsphp72-mbstring lsphp72-ldap lsphp72-intl lsphp72-imap ' \
                      'lsphp72-gmp lsphp72-gd lsphp72-enchant lsphp72-dba  lsphp72-common  lsphp72-bcmath'

            install.preFlightsChecks.call(command, self.distro, '[installAllPHPVersions]',
                                          'Install PHP 72',
                                          1, 0, os.EX_OSERR)

            ## only php 72
            command = 'yum install -y lsphp73 lsphp73-json lsphp73-xmlrpc lsphp73-xml lsphp73-tidy lsphp73-soap lsphp73-snmp ' \
                      'lsphp73-recode lsphp73-pspell lsphp73-process lsphp73-pgsql lsphp73-pear lsphp73-pdo lsphp73-opcache ' \
                      'lsphp73-odbc lsphp73-mysqlnd lsphp73-mcrypt lsphp73-mbstring lsphp73-ldap lsphp73-intl lsphp73-imap ' \
                      'lsphp73-gmp lsphp73-gd lsphp73-enchant lsphp73-dba  lsphp73-common  lsphp73-bcmath'

            install.preFlightsChecks.call(command, self.distro, '[installAllPHPVersions]',
                                          'Install PHP 73',
                                          1, 0, os.EX_OSERR)

    def setup_mariadb_repo(self):
        try:

            if self.distro == ubuntu:
            # Only needed if the repo is broken or we need the latest version.
            # command = "apt-get -y install software-properties-common"
            # command = "apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8"
            # command = "add-apt-repository 'deb [arch=amd64] http://mirror.zol.co.zw/mariadb/repo/10.3/ubuntu bionic main'"
                return

            InstallCyberPanel.stdOut("Setting up MariaDB Repo..", 1)

            os.chdir(self.cwd)
            shutil.copy("mysql/MariaDB.repo","/etc/yum.repos.d/MariaDB.repo")

            InstallCyberPanel.stdOut("MariaDB repo set!", 1)


        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_mariadb_repo]")
            return 0

    def installMySQL(self, mysql):

        ############## Install mariadb ######################

        if self.distro == ubuntu:
            command = "apt-get -y install mariadb-server"
        else:
            command = 'yum -y install mariadb-server'

        install.preFlightsChecks.call(command, self.distro, '[installMySQL]',
                                      'Install MySQL',
                                      1, 1, os.EX_OSERR)

        ## Fix configurations if two MYSQL are used

        if mysql == 'Two':
            logging.InstallLog.writeToFile("Setting up MariaDB configurations!")
            InstallCyberPanel.stdOut("Setting up MariaDB configurations!")

            pathConf = "/etc/my.cnf"
            pathServiceFile = "/etc/systemd/system/mysqld@.service"

            if os.path.exists(pathConf):
                os.remove(pathConf)

            if os.path.exists(pathServiceFile):
                os.remove(pathServiceFile)

            os.chdir(self.cwd)

            shutil.copy("mysql/my.cnf", pathConf)
            shutil.copy("mysql/mysqld@.service", pathServiceFile)

            logging.InstallLog.writeToFile("MariaDB configurations set!")
            InstallCyberPanel.stdOut("MariaDB configurations set!")

            ##

            count = 0

            while (1):
                command = "mysql_install_db --user=mysql --datadir=/var/lib/mysql1"
                install.preFlightsChecks.call(command, self.distro, '[installMySQL]',
                                              'Install MySQL',
                                              1, 1, os.EX_OSERR)

            ##

            count = 0

            while (1):
                command = "systemctl start mysqld@1"
                res = subprocess.call(shlex.split(command))

                if install.preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    InstallCyberPanel.stdOut(
                        "Trying to start first MariaDB instance, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to start first MariaDB instance, exiting installer! [installMySQL]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("First MariaDB instance successfully started!")
                    InstallCyberPanel.stdOut("First MariaDB instance successfully started!")
                    break

            count = 0

            while (1):
                command = "systemctl enable mysqld@1"
                res = subprocess.call(shlex.split(command))

                if install.preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    InstallCyberPanel.stdOut(
                        "Trying to enable first MariaDB instance to start and system restart, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to enable first MariaDB instance to run at system restart, exiting installer! [installMySQL]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("First MariaDB instance successfully enabled at system restart!")
                    InstallCyberPanel.stdOut("First MariaDB instance successfully enabled at system restart!")
                    break


        ############## Start mariadb ######################

        self.startMariaDB()

    def changeMYSQLRootPassword(self):
        if self.distro == ubuntu:
            passwordCMD = "use mysql;update user set password=PASSWORD('" + InstallCyberPanel.mysql_Root_password + "') where User='root';UPDATE user SET plugin='' WHERE User='root';flush privileges;"
        else:
            passwordCMD = "use mysql;update user set password=PASSWORD('" + InstallCyberPanel.mysql_Root_password + "') where User='root';flush privileges;"

        command = 'mysql -u root -e "' + passwordCMD + '"'
        install.preFlightsChecks.call(command, self.distro, '[changeMYSQLRootPassword]', 'MYSQL Root Password change.',
                                      1, 1, os.EX_OSERR)

    def startMariaDB(self):

        ############## Start mariadb ######################

        command = "systemctl start mysql"
        install.preFlightsChecks.call(command, self.distro, '[startMariaDB]',
                                      'Start MySQL',
                                      1, 1, os.EX_OSERR)

        ############## Enable mariadb at system startup ######################

        if os.path.exists('/etc/systemd/system/mysqld.service'):
            os.remove('/etc/systemd/system/mysqld.service')
        if os.path.exists('/etc/systemd/system/mariadb.service'):
            os.remove('/etc/systemd/system/mariadb.service')

        if self.distro == ubuntu:
            command = "systemctl enable mariadb"
        else:
            command = "systemctl enable mariadb"

        install.preFlightsChecks.call(command, self.distro, '[installMySQL]',
                                      'Enable MySQL',
                                      1, 0, os.EX_OSERR)

    def fixMariaDB(self):
        self.stdOut("Setup MariaDB so it can support Cyberpanel's needs")

        conn = mariadb.connect(user='root', passwd=self.mysql_Root_password)
        cursor = conn.cursor()
        cursor.execute('set global innodb_file_per_table = on;')
        cursor.execute('set global innodb_file_format = Barracuda;')
        cursor.execute('set global innodb_large_prefix = on;')
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
            self.stdOut("Error in setting: " + fileName + ": " + str(err), 1, 1, os.EX_OSERR)

        os.system('systemctl restart mysql')

        self.stdOut("MariaDB is now setup so it can support Cyberpanel's needs")

    def installPureFTPD(self):
        if self.distro == ubuntu:
            command = 'apt-get -y install ' + install.preFlightsChecks.pureFTPDServiceName(self.distro)
        else:
            command = "yum install -y pure-ftpd"

        install.preFlightsChecks.call(command, self.distro, '[installPureFTPD]',
                                      'Install FTP',
                                      1, 1, os.EX_OSERR)

        ####### Install pureftpd to system startup

        command = "systemctl enable " + install.preFlightsChecks.pureFTPDServiceName(self.distro)
        install.preFlightsChecks.call(command, self.distro, '[installPureFTPD]',
                                      'Install FTP',
                                      1, 1, os.EX_OSERR)

        ###### FTP Groups and user settings settings

        command = 'groupadd -g 2001 ftpgroup'
        install.preFlightsChecks.call(command, self.distro, '[installPureFTPD]',
                                      'Install FTP',
                                      1, 1, os.EX_OSERR)

        command = 'useradd -u 2001 -s /bin/false -d /bin/null -c "pureftpd user" -g ftpgroup ftpuser'
        install.preFlightsChecks.call(command, self.distro, '[installPureFTPD]',
                                      'Install FTP',
                                      1, 1, os.EX_OSERR)

    def startPureFTPD(self):
        ############## Start pureftpd ######################
        if self.distro == ubuntu:
            command = 'systemctl start pure-ftpd-mysql'
        else:
            command = 'systemctl start pure-ftpd'
        install.preFlightsChecks.call(command, self.distro, '[startPureFTPD]',
                                      'Start FTP',
                                      1, 0, os.EX_OSERR)

    def installPureFTPDConfigurations(self, mysql):
        try:
            ## setup ssl for ftp

            InstallCyberPanel.stdOut("Configuring PureFTPD..", 1)

            try:
                os.mkdir("/etc/ssl/private")
            except:
                logging.InstallLog.writeToFile("Could not create directory for FTP SSL")


            command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'
            install.preFlightsChecks.call(command, self.distro, '[installPureFTPDConfigurations]',
                                          'FTP Configurations',
                                          1, 0, os.EX_OSERR)

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
                    shutil.copytree("pure-ftpd",ftpdPath)
                else:
                    shutil.copytree("pure-ftpd-one", ftpdPath)

            if self.distro == ubuntu:
                try:
                    os.mkdir('/etc/pure-ftpd/conf')
                    os.mkdir('/etc/pure-ftpd/auth')
                    os.mkdir('/etc/pure-ftpd/db')
                except OSError as err:
                    self.stdOut("Error creating extra pure-ftpd directories: " + str(err), ".  Should be ok", 1)

            data = open(ftpdPath+"/pureftpd-mysql.conf","r").readlines()

            writeDataToFile = open(ftpdPath+"/pureftpd-mysql.conf","w")

            dataWritten = "MYSQLPassword "+InstallCyberPanel.mysqlPassword+'\n'
            for items in data:
                if items.find("MYSQLPassword")>-1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)


            writeDataToFile.close()

            if self.distro == ubuntu:
                command = 'apt install pure-ftpd-mysql -y'
                install.preFlightsChecks.call(command, self.distro, '[installPureFTPDConfigurations]',
                                              'FTP Configurations',
                                              1, 1, os.EX_OSERR)

                if os.path.exists('/etc/pure-ftpd/db/mysql.conf'):
                    os.remove('/etc/pure-ftpd/db/mysql.conf')
                    shutil.copy(ftpdPath+"/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')
                else:
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')

                command = 'echo 1 > /etc/pure-ftpd/conf/TLS'
                subprocess.call(command, shell=True)

                command = 'systemctl restart pure-ftpd-mysql.service'
                install.preFlightsChecks.call(command, self.distro, '[installPureFTPDConfigurations]',
                                              'FTP Configurations',
                                              1, 0, os.EX_OSERR)

            InstallCyberPanel.stdOut("PureFTPD configured!", 1)

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPureFTPDConfigurations]")
            return 0

    def installPowerDNS(self):
        try:
            count = 0

            if self.distro == ubuntu:
                command = 'systemctl stop systemd-resolved'
                res = subprocess.call(shlex.split(command))
                if res != 0:
                    InstallCyberPanel.stdOut('Unable to stop systemd.resolved, prohits install of PowerDNS, error #' +
                                             str(res), 1, 1, os.EX_OSERR)
                command = 'systemctl disable systemd-resolved.service'
                res = subprocess.call(shlex.split(command))
                if res != 0:
                    InstallCyberPanel.stdOut(
                        'Unable to disable systemd.resolved, prohits install of PowerDNS, error #' +
                        str(res), 1, 1, os.EX_OSERR)
                try:
                    os.rename('/etc/resolv.conf', 'etc/resolved.conf')
                except OSError as e:
                    if e.errno != errno.EEXIST and e.errno != errno.ENOENT:
                        InstallCyberPanel.stdOut("Unable to rename /etc/resolv.conf to install PowerDNS: " +
                                                 str(e), 1, 1, os.EX_OSERR)
                    try:
                        os.remove('/etc/resolv.conf')
                    except OSError as e1:
                        InstallCyberPanel.stdOut("Unable to remove existing /etc/resolv.conf to install PowerDNS: " +
                                                 str(e1), 1, 1, os.EX_OSERR)
                try:
                    f = open('/etc/resolv.conf', 'w')
                    f.write('nameserver 8.8.8.8')
                    f.close()
                except IOError as e:
                    InstallCyberPanel.stdOut("Unable to create /etc/resolv.conf: " + str(e) +
                                             ".  This may need to be fixed manually as 'echo \"nameserver 8.8.8.8\"> "
                                             "/etc/resolv.conf'", 1, 1, os.EX_OSERR)

            if self.distro == centos:
                command = 'yum -y install epel-release yum-plugin-priorities'
                install.preFlightsChecks.call(command, self.distro, '[installPowerDNS]',
                                              'Install PowerDNS',
                                              1, 1, os.EX_OSERR)

                command = 'curl -o /etc/yum.repos.d/powerdns-auth-master.repo ' \
                          'https://repo.powerdns.com/repo-files/centos-auth-master.repo'
                install.preFlightsChecks.call(command, self.distro, '[installPowerDNS]',
                                              'Install PowerDNS',
                                              1, 1, os.EX_OSERR)

            if self.distro == ubuntu:
                command = "DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server pdns-backend-mysql"
                os.system(command)
                return 1
            else:
                command = 'yum -y install pdns pdns-backend-mysql'

            install.preFlightsChecks.call(command, self.distro, '[installPowerDNS]',
                                          'Install PowerDNS',
                                          1, 1, os.EX_OSERR)
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [powerDNS]")

    def installPowerDNSConfigurations(self, mysqlPassword, mysql):
        try:

            InstallCyberPanel.stdOut("Configuring PowerDNS..", 1)

            os.chdir(self.cwd)
            if self.distro == centos:
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

            #if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("PowerDNS configured!", 1)

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPowerDNSConfigurations]")
            return 0
        return 1

    def startPowerDNS(self):

        ############## Start PowerDNS ######################

        try:
            command = 'systemctl enable pdns'
            install.preFlightsChecks.call(command, self.distro, '[startPowerDNS]',
                                          'Start PowerDNS',
                                          1, 0, os.EX_OSERR)

            command = 'systemctl start pdns'
            install.preFlightsChecks.call(command, self.distro, '[startPowerDNS]',
                                          'Start PowerDNS',
                                          1, 0, os.EX_OSERR)
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPowerDNS]")

    def installLSCPD(self):
        try:

            InstallCyberPanel.stdOut("Starting LSCPD installation..", 1)

            os.chdir(self.cwd)

            if self.distro == ubuntu:
                command = "apt-get -y install gcc g++ make autoconf rcs"
            else:
                command = 'yum -y install gcc gcc-c++ make autoconf glibc rcs'

            install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                          'Install LSCPD',
                                          1, 1, os.EX_OSERR)

            if self.distro == ubuntu:
                command = "apt-get -y install libpcre3 libpcre3-dev openssl libexpat1 libexpat1-dev libgeoip-dev" \
                          " zlib1g zlib1g-dev libudns-dev whichman curl"
            else:
                command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel' \
                          ' which curl'
            install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                          'Install LSCPD',
                                          1, 1, os.EX_OSERR)


            command = 'tar zxf lscp.tar.gz -C /usr/local/'
            install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                          'Install LSCPD',
                                          1, 1, os.EX_OSERR)


            command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /usr/local/lscp/key.pem -out /usr/local/lscp/cert.pem'
            install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                          'Install LSCPD',
                                          1, 1, os.EX_OSERR)

            try:
                os.remove("/usr/local/lscp/fcgi-bin/lsphp")
                shutil.copy("/usr/local/lsws/lsphp70/bin/lsphp","/usr/local/lscp/fcgi-bin/lsphp")
            except:
                pass

            if self.distro == centos:
                command = 'adduser lscpd -M -d /usr/local/lscp'
            else:
                command = 'useradd lscpd -M -d /usr/local/lscp'

            install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                          'Install LSCPD',
                                          1, 0, os.EX_OSERR)

            if self.distro == centos:
                command = 'groupadd lscpd'
                install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                              'Install LSCPD',
                                              1, 0, os.EX_OSERR)
                # Added group in useradd for Ubuntu

            command = 'usermod -a -G lscpd lscpd'
            install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                          'Install LSCPD',
                                          1, 0, os.EX_OSERR)

            command = 'usermod -a -G lsadm lscpd'
            install.preFlightsChecks.call(command, self.distro, '[installLSCPD]',
                                          'Install LSCPD',
                                          1, 0, os.EX_OSERR)

            os.mkdir('/usr/local/lscp/cyberpanel')

            InstallCyberPanel.stdOut("LSCPD successfully installed!", 1)

        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPowerDNS]")


def Main(cwd, mysql, distro, ent, serial = None):

    InstallCyberPanel.mysqlPassword = randomPassword.generate_pass()
    InstallCyberPanel.mysql_Root_password = randomPassword.generate_pass()

    file_name = '/etc/cyberpanel/mysqlPassword'
    if os.access(file_name, os.F_OK):
        password = open(file_name, 'r')
        InstallCyberPanel.mysql_Root_password = password.readline()
    else:
        password = open(file_name, "w")
        password.writelines(InstallCyberPanel.mysql_Root_password)

    password.close()

    if distro == centos:
        InstallCyberPanel.mysqlPassword = randomPassword.generate_pass()
    else:
        InstallCyberPanel.mysqlPassword = InstallCyberPanel.mysql_Root_password

    installer = InstallCyberPanel("/usr/local/lsws/",cwd, distro, ent, serial)

    installer.installLiteSpeed()
    if ent == 0:
        installer.changePortTo80()
    installer.setupFileManager()
    installer.installAllPHPVersions()
    if ent == 0:
        installer.fix_ols_configs()


    installer.setup_mariadb_repo()
    installer.installMySQL(mysql)
    installer.changeMYSQLRootPassword()
    #installer.changeMYSQLRootPasswordCyberPanel(mysql)
    installer.startMariaDB()
    if distro == ubuntu:
        installer.fixMariaDB()

    mysqlUtilities.createDatabase("cyberpanel","cyberpanel",InstallCyberPanel.mysqlPassword)

    installer.installPureFTPD()
    installer.installPureFTPDConfigurations(mysql)
    installer.startPureFTPD()

    installer.installPowerDNS()
    installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
    installer.startPowerDNS()

    installer.installLSCPD()