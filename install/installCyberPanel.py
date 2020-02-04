import shutil
import subprocess
import os
from mysqlUtilities import mysqlUtilities
import installLog as logging
import randomPassword
import errno
import MySQLdb as mariadb
import install

#distros
centos=0
ubuntu=1
cent8=2

class InstallCyberPanel:

    mysql_Root_password = ""
    mysqlPassword = ""

    def __init__(self, rootPath, cwd, distro, ent, serial = None, port = None, ftp = None, dns = None, publicip = None):
        self.server_root_path = rootPath
        self.cwd = cwd
        self.distro = distro
        self.ent = ent
        self.serial = serial
        self.port = port
        self.ftp = None
        self.dns = dns
        self.publicip = publicip

    @staticmethod
    def stdOut(message, log=0, exit=0, code=os.EX_OK):
        install.preFlightsChecks.stdOut(message, log, exit, code)

    def installLiteSpeed(self):
        if self.ent == 0:
            if self.distro == ubuntu:
                command = "apt-get -y install openlitespeed"
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            elif self.distro == centos:
                command = 'yum install -y openlitespeed'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            else:
                command = 'yum install -y openlitespeed'
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

                command = 'wget https://www.litespeedtech.com/packages/5.0/lsws-5.4.2-ent-x86_64-linux.tar.gz'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'tar zxf lsws-5.4.2-ent-x86_64-linux.tar.gz'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                writeSerial = open('lsws-5.4.2/serial.no', 'w')
                writeSerial.writelines(self.serial)
                writeSerial.close()

                shutil.copy('litespeed/install.sh', 'lsws-5.3.5/')
                shutil.copy('litespeed/functions.sh', 'lsws-5.3.5/')

                os.chdir('lsws-5.3.5')

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
        command = self.server_root_path+"bin/lswsctrl restart"
        install.preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

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
        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [fix_ols_configs]")
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

            res = os.system(command)
            if res != 0:
                InstallCyberPanel.stdOut("Failed to install PHP on Ubuntu.", 1, 1)

        elif self.distro == cent8 or self.distro == centos:
            command = 'yum -y groupinstall lsphp-all'
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)



        InstallCyberPanel.stdOut("LiteSpeed PHPs successfully installed!", 1)

        ## only php 71
        if self.distro == centos or self.distro == cent8:

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


        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setup_mariadb_repo]")
            return 0

    def installMySQL(self, mysql):

        ############## Install mariadb ######################

        if self.distro == ubuntu:
            command = "apt-get -y install mariadb-server"
        else:
            command = 'yum -y install mariadb-server'

        install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

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

            command = "mysql_install_db --user=mysql --datadir=/var/lib/mysql1"
            install.preFlightsChecks.call(command, self.distro, '[installMySQL]',
                                          'Install MySQL',
                                          1, 1, os.EX_OSERR)


            ##

            command = "systemctl start mysqld@1"
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            ##

            command = "systemctl enable mysqld@1"
            install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)



        ############## Start mariadb ######################

        self.startMariaDB()

    def changeMYSQLRootPassword(self):
        if self.distro == ubuntu:
            passwordCMD = "use mysql;update user set password=PASSWORD('" + InstallCyberPanel.mysql_Root_password + "') where User='root';UPDATE user SET plugin='' WHERE User='root';flush privileges;"
        else:
            passwordCMD = "use mysql;update user set password=PASSWORD('" + InstallCyberPanel.mysql_Root_password + "') where User='root';flush privileges;"

        command = 'mysql -u root -e "' + passwordCMD + '"'

        install.preFlightsChecks.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)

    def startMariaDB(self):

        ############## Start mariadb ######################
        if self.distro == cent8 or self.distro == ubuntu:
            command = 'systemctl start mariadb'
        else:
            command = "systemctl start mysql"
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
            self.stdOut("[ERROR] Error in setting: " + fileName + ": " + str(err), 1, 1, os.EX_OSERR)

        os.system('systemctl restart mysql')

        self.stdOut("MariaDB is now setup so it can support Cyberpanel's needs")

    def installPureFTPD(self):
        if self.distro == ubuntu:
            command = 'apt-get -y install ' + install.preFlightsChecks.pureFTPDServiceName(self.distro)
        else:
            command = "yum install -y pure-ftpd"

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


            command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'
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
                    shutil.copytree("pure-ftpd",ftpdPath)
                else:
                    shutil.copytree("pure-ftpd-one", ftpdPath)

            if self.distro == ubuntu:
                try:
                    os.mkdir('/etc/pure-ftpd/conf')
                    os.mkdir('/etc/pure-ftpd/auth')
                    os.mkdir('/etc/pure-ftpd/db')
                except OSError as err:
                    self.stdOut("[ERROR] Error creating extra pure-ftpd directories: " + str(err), ".  Should be ok", 1)

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
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                if os.path.exists('/etc/pure-ftpd/db/mysql.conf'):
                    os.remove('/etc/pure-ftpd/db/mysql.conf')
                    shutil.copy(ftpdPath+"/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')
                else:
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')

                command = 'echo 1 > /etc/pure-ftpd/conf/TLS'
                subprocess.call(command, shell=True)

                command = 'echo %s > /etc/pure-ftpd/conf/ForcePassiveIP' % (self.publicip)
                subprocess.call(command, shell=True)

                command = 'echo "40110 40210" > /etc/pure-ftpd/conf/PassivePortRange'
                subprocess.call(command, shell=True)

                command = 'wget http://mirrors.kernel.org/ubuntu/pool/universe/p/pure-ftpd/pure-ftpd-common_1.0.47-3_all.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'wget http://mirrors.kernel.org/ubuntu/pool/universe/p/pure-ftpd/pure-ftpd-mysql_1.0.47-3_amd64.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'dpkg --install --force-confold pure-ftpd-common_1.0.47-3_all.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'dpkg --install --force-confold pure-ftpd-mysql_1.0.47-3_amd64.deb'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'systemctl restart pure-ftpd-mysql.service'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            InstallCyberPanel.stdOut("PureFTPD configured!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installPureFTPDConfigurations]")
            return 0

    def installPowerDNS(self):
        try:

            if self.distro == ubuntu:
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
                        InstallCyberPanel.stdOut("[ERROR] Unable to remove existing /etc/resolv.conf to install PowerDNS: " +
                                                 str(e1), 1, 1, os.EX_OSERR)



                # try:
                #     f = open('/etc/resolv.conf', 'a')
                #     f.write('nameserver 8.8.8.8')
                #     f.close()
                # except IOError as e:
                #     InstallCyberPanel.stdOut("[ERROR] Unable to create /etc/resolv.conf: " + str(e) +
                #                              ".  This may need to be fixed manually as 'echo \"nameserver 8.8.8.8\"> "
                #                              "/etc/resolv.conf'", 1, 1, os.EX_OSERR)

            if self.distro == centos:
                command = 'curl -o /etc/yum.repos.d/powerdns-auth-42.repo ' \
                          'https://repo.powerdns.com/repo-files/centos-auth-42.repo'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            if self.distro == cent8:
                command = 'dnf config-manager --set-enabled PowerTools'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'curl -o /etc/yum.repos.d/powerdns-auth-master.repo https://repo.powerdns.com/repo-files/centos-auth-master.repo'
                install.preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

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
            if self.distro == centos or self.distro == cent8:
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


def Main(cwd, mysql, distro, ent, serial = None, port = "8090", ftp = None, dns = None, publicip = None):

    InstallCyberPanel.mysqlPassword = randomPassword.generate_pass()
    InstallCyberPanel.mysql_Root_password = randomPassword.generate_pass()

    file_name = '/etc/cyberpanel/mysqlPassword'
    if os.access(file_name, os.F_OK):
        password = open(file_name, 'r')
        InstallCyberPanel.mysql_Root_password = password.readline()
        password.close()
    else:
        password = open(file_name, "w")
        password.writelines(InstallCyberPanel.mysql_Root_password)
        command = 'chmod 640 %s' % (file_name)
        password.close()
        try:
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

    installer = InstallCyberPanel("/usr/local/lsws/",cwd, distro, ent, serial, port, ftp, dns, publicip)

    installer.installLiteSpeed()
    if ent == 0:
        installer.changePortTo80()
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

    if ftp == None:
        installer.installPureFTPD()
        installer.installPureFTPDConfigurations(mysql)
        installer.startPureFTPD()
    else:
        if ftp == 'ON':
            installer.installPureFTPD()
            installer.installPureFTPDConfigurations(mysql)
            installer.startPureFTPD()

    if dns == None:
        installer.installPowerDNS()
        installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
        installer.startPowerDNS()
    else:
        if dns == 'ON':
            installer.installPowerDNS()
            installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
            installer.startPowerDNS()