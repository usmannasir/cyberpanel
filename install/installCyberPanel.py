import shutil
import subprocess
import os
import pexpect
from mysqlUtilities import mysqlUtilities
import installLog as logging
import shlex
import randomPassword
import errno
import MySQLdb as mariadb
import install
import stat

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
            try:
                count = 0
                while (1):

                    if self.distro == ubuntu:
                        command = "apt-get -y install openlitespeed"
                    else:
                        command = 'yum install -y openlitespeed'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                    if res == 1:
                        count = count + 1
                        InstallCyberPanel.stdOut("Trying to install OpenLiteSpeed, trying again, try number: " + str(count))
                        if count == 3:
                            logging.InstallLog.writeToFile("Failed to install OpenLiteSpeed, exiting installer! [installLiteSpeed]")
                            InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                            os._exit(0)
                    else:
                        logging.InstallLog.writeToFile("OpenLiteSpeed successfully installed!")
                        InstallCyberPanel.stdOut("OpenLiteSpeed successfully installed!")
                        break
            except OSError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
                return 0
            except ValueError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
                return 0

            return 1
        else:
            try:
                count = 0
                while (1):

                    command = 'wget https://www.litespeedtech.com/packages/5.0/lsws-5.3-ent-x86_64-linux.tar.gz'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                    command = 'tar zxf lsws-5.3-ent-x86_64-linux.tar.gz'
                    subprocess.call(shlex.split(command))

                    writeSerial = open('lsws-5.3/serial.no', 'w')
                    writeSerial.writelines(self.serial)
                    writeSerial.close()

                    shutil.copy('litespeed/install.sh', 'lsws-5.3/')
                    shutil.copy('litespeed/functions.sh', 'lsws-5.3/')

                    os.chdir('lsws-5.3')

                    command = 'chmod +x install.sh'
                    subprocess.call(shlex.split(command))

                    command = 'chmod +x functions.sh'
                    subprocess.call(shlex.split(command))

                    command = './install.sh'
                    res = subprocess.call(shlex.split(command))

                    if res == 1:
                        logging.InstallLog.writeToFile(
                            "Failed to install LiteSpeed Enterprise! [installLiteSpeed]")
                        InstallCyberPanel.stdOut("Failed to install LiteSpeed Enterprise!")
                        os._exit(0)

                    os.chdir(self.cwd)
                    confPath = '/usr/local/lsws/conf/'
                    shutil.copy('litespeed/httpd_config.xml', confPath)
                    shutil.copy('litespeed/modsec.conf', confPath)
                    shutil.copy('litespeed/httpd.conf', confPath)

                    command = 'chown -R lsadm:lsadm ' + confPath
                    subprocess.call(shlex.split(command))
                    break
            except OSError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
                return 0
            except ValueError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
                return 0

            return 1

    def reStartLiteSpeed(self):

        try:
            cmd = []
            count = 0

            while(1):
                cmd.append(self.server_root_path+"bin/lswsctrl")
                cmd.append("restart")

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to restart OpenLiteSpeed, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to restart OpenLiteSpeed, you can do this manually later using: systemctl restart lsws! [reStartLiteSpeed]")
                        break
                else:
                    logging.InstallLog.writeToFile("OpenLiteSpeed successfully restarted!")
                    InstallCyberPanel.stdOut("OpenLiteSpeed successfully restarted!")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        return 1

    def fix_ols_configs(self):
        try:

            InstallCyberPanel.stdOut("Fixing OpenLiteSpeed configurations!")
            logging.InstallLog.writeToFile("Fixing OpenLiteSpeed configurations!")

            ## cache module settings
            cacheStart = "module cache {\n"
            ls_enabled = "ls_enabled 1\n"
            enableCache = "enableCache 0\n"
            qsCache = "qsCache 1\n"
            reqCookieCache = "reqCookieCache 1\n"
            respCookieCache = "respCookieCache 1\n"
            ignoreReqCacheCtrl = "ignoreReqCacheCtrl 1\n"
            ignoreRespCacheCtrl = "ignoreRespCacheCtrl 0\n"
            enablePrivateCache = "enablePrivateCache 0\n"
            privateExpireInSeconds = "privateExpireInSeconds 1000\n"
            expireInSeconds = "expireInSeconds 1000\n"
            storagePath = "storagePath cachedata\n"
            checkPrivateCache = "checkPrivateCache 1\n"
            checkPublicCache = "checkPublicCache 1\n"
            cacheEnd = "}\n"

            writeDataToFile = open(self.server_root_path+"conf/httpd_config.conf", 'a')

            writeDataToFile.writelines(cacheStart)
            writeDataToFile.writelines(ls_enabled)
            writeDataToFile.writelines(enableCache)
            writeDataToFile.writelines(qsCache)
            writeDataToFile.writelines(reqCookieCache)
            writeDataToFile.writelines(respCookieCache)
            writeDataToFile.writelines(ignoreReqCacheCtrl)
            writeDataToFile.writelines(ignoreRespCacheCtrl)
            writeDataToFile.writelines(enablePrivateCache)
            writeDataToFile.writelines(privateExpireInSeconds)
            writeDataToFile.writelines(expireInSeconds)
            writeDataToFile.writelines(storagePath)
            writeDataToFile.writelines(checkPrivateCache)
            writeDataToFile.writelines(checkPublicCache)
            writeDataToFile.writelines(cacheEnd)
            writeDataToFile.writelines("\n")
            writeDataToFile.writelines("\n")

            writeDataToFile.close()

            ## remove example virtual host

            data = open(self.server_root_path+"conf/httpd_config.conf",'r').readlines()

            writeDataToFile = open(self.server_root_path + "conf/httpd_config.conf", 'w')

            for items in data:
                if items.find("map") > -1 and items.find("Example") > -1:
                    continue
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("OpenLiteSpeed Configurations fixed!")
            logging.InstallLog.writeToFile("OpenLiteSpeed Configurations fixed!")


        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [fix_ols_configs]")
            return 0

        return self.reStartLiteSpeed()

    def changePortTo80(self):
        try:
            InstallCyberPanel.stdOut("Changing default port to 80..")
            logging.InstallLog.writeToFile("Changing default port to 80..")

            data = open(self.server_root_path+"conf/httpd_config.conf").readlines()

            writeDataToFile = open(self.server_root_path+"conf/httpd_config.conf", 'w')

            for items in data:
                if (items.find("*:8088") > -1):
                    writeDataToFile.writelines(items.replace("*:8088","*:80"))
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("Default port is now 80 for OpenLiteSpeed!")
            logging.InstallLog.writeToFile("Default port is now 80 for OpenLiteSpeed!")

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [changePortTo80]")
            return 0

        return self.reStartLiteSpeed()

    def setupFileManager(self):
        if self.ent == 0:
            try:
                logging.InstallLog.writeToFile("Setting up Filemanager files..")
                InstallCyberPanel.stdOut("Setting up Filemanager files..")

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

                logging.InstallLog.writeToFile("Filemanager files are set!")
                InstallCyberPanel.stdOut("Filemanager files are set!")

            except OSError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [setupFileManager]")
                return 0
            except ValueError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [setupFileManager]")
                return 0

            return 1
        else:
            try:
                logging.InstallLog.writeToFile("Setting up Filemanager files..")
                InstallCyberPanel.stdOut("Setting up Filemanager files..")

                os.chdir(self.cwd)

                fileManagerPath = self.server_root_path + "/FileManager"
                shutil.copytree("FileManager", fileManagerPath)

                ## remove unnecessary files

                command = 'chmod -R 777 ' + fileManagerPath
                subprocess.call(shlex.split(command))

                logging.InstallLog.writeToFile("Filemanager files are set!")
                InstallCyberPanel.stdOut("Filemanager files are set!")

            except OSError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [setupFileManager]")
                return 0
            except ValueError, msg:
                logging.InstallLog.writeToFile(str(msg) + " [setupFileManager]")
                return 0

            return 1

    def installAllPHPVersions(self):
        try:
            count = 0

            while (1):

                if self.distro == ubuntu:
                    command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install ' \
                              'lsphp7? lsphp7?-common lsphp7?-curl lsphp7?-dev lsphp7?-imap lsphp7?-intl lsphp7?-json ' \
                              'lsphp7?-ldap lsphp7?-mysql lsphp7?-opcache lsphp7?-pspell lsphp7?-recode ' \
                              'lsphp7?-sqlite3 lsphp7?-tidy'
                    res = os.system(command)
                else:
                    command = 'yum -y groupinstall lsphp-all'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut(
                        "Trying to install LiteSpeed PHPs, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install LiteSpeed PHPs, exiting installer! [installAllPHPVersions]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("LiteSpeed PHPs successfully installed!")
                    InstallCyberPanel.stdOut("LiteSpeed PHPs successfully installed!")

                    ## only php 71
                    if self.distro == centos:
                        count = 0
                        while (1):
                            command = 'yum install lsphp71 lsphp71-json lsphp71-xmlrpc lsphp71-xml lsphp71-tidy lsphp71-soap lsphp71-snmp lsphp71-recode lsphp71-pspell lsphp71-process lsphp71-pgsql lsphp71-pear lsphp71-pdo lsphp71-opcache lsphp71-odbc lsphp71-mysqlnd lsphp71-mcrypt lsphp71-mbstring lsphp71-ldap lsphp71-intl lsphp71-imap lsphp71-gmp lsphp71-gd lsphp71-enchant lsphp71-dba  lsphp71-common  lsphp71-bcmath -y'
                            cmd = shlex.split(command)
                            res = subprocess.call(cmd)
                            if res == 1:
                                count = count + 1
                                InstallCyberPanel.stdOut(
                                    "Trying to install LiteSpeed PHP 7.1, trying again, try number: " + str(count))
                                if count == 3:
                                    logging.InstallLog.writeToFile(
                                        "Failed to install LiteSpeed PHP 7.1, exiting installer! [installAllPHPVersions]")
                                    InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                                    os._exit(0)
                            else:
                                logging.InstallLog.writeToFile("LiteSpeed PHP 7.1 successfully installed!")
                                InstallCyberPanel.stdOut("LiteSpeed PHP 7.1 successfully installed!")
                                break

                        ## only php 72
                        count = 0
                        while (1):
                            command = 'yum install -y lsphp72 lsphp72-json lsphp72-xmlrpc lsphp72-xml lsphp72-tidy lsphp72-soap lsphp72-snmp lsphp72-recode lsphp72-pspell lsphp72-process lsphp72-pgsql lsphp72-pear lsphp72-pdo lsphp72-opcache lsphp72-odbc lsphp72-mysqlnd lsphp72-mcrypt lsphp72-mbstring lsphp72-ldap lsphp72-intl lsphp72-imap lsphp72-gmp lsphp72-gd lsphp72-enchant lsphp72-dba  lsphp72-common  lsphp72-bcmath'
                            cmd = shlex.split(command)
                            res = subprocess.call(cmd)
                            if res == 1:
                                count = count + 1
                                InstallCyberPanel.stdOut(
                                    "Trying to install LiteSpeed PHP 7.1, trying again, try number: " + str(count))
                                if count == 3:
                                    logging.InstallLog.writeToFile(
                                        "Failed to install LiteSpeed PHP 7.1, exiting installer! [installAllPHPVersions]")
                                    InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                                    os._exit(0)
                            else:
                                logging.InstallLog.writeToFile("LiteSpeed PHP 7.1 successfully installed!")
                                InstallCyberPanel.stdOut("LiteSpeed PHP 7.1 successfully installed!")
                                break

                    ## break for outer loop
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installAllPHPVersion]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installAllPHPVersion]")
            return 0

        return 1

    def setup_mariadb_repo(self):
        try:

            if self.distro == ubuntu:
            # Only needed if the repo is broken or we need the latest version.
            # command = "apt-get -y install software-properties-common"
            # command = "apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8"
            # command = "add-apt-repository 'deb [arch=amd64] http://mirror.zol.co.zw/mariadb/repo/10.3/ubuntu bionic main'"
                return

            logging.InstallLog.writeToFile("Setting up MariaDB Repo..")
            InstallCyberPanel.stdOut("Setting up MariaDB Repo..")

            os.chdir(self.cwd)
            shutil.copy("mysql/MariaDB.repo","/etc/yum.repos.d/MariaDB.repo")

            logging.InstallLog.writeToFile("MariaDB repo set!")
            InstallCyberPanel.stdOut("MariaDB repo set!")

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_mariadb_repo]")
            return 0
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_mariadb_repo]")
            return 0

    def installMySQL(self, mysql):

        try:
            ############## Install mariadb ######################

            count = 0

            while (1):
                if self.distro == ubuntu:
                    command = "apt-get -y install mariadb-server"
                else:
                    command = 'yum -y install mariadb-server'
                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to install MariaDB, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to install MariaDB, exiting installer! [installMySQL]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("MariaDB successfully installed!")
                    InstallCyberPanel.stdOut("MariaDB successfully installed!")
                    break

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

                    res = subprocess.call(shlex.split(command))

                    if res == 1:
                        count = count + 1
                        InstallCyberPanel.stdOut(
                            "Trying to create data directories for second MariaDB instance, trying again, try number: " + str(
                                count))
                        if count == 3:
                            logging.InstallLog.writeToFile(
                                "Failed to create data directories for second MariaDB instance, exiting installer! [installMySQL]")
                            InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                            os._exit(0)
                    else:
                        logging.InstallLog.writeToFile("Data directories created for second MariaDB instance!")
                        InstallCyberPanel.stdOut("Data directories created for second MariaDB instance!")
                        break

                ##

                count = 0

                while (1):
                    command = "systemctl start mysqld@1"
                    res = subprocess.call(shlex.split(command))

                    if res == 1:
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

                    if res == 1:
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


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installMySQL]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installMySQL]")
            return 0


        ############## Start mariadb ######################

        self.startMariaDB()

        ############## Enable mariadb at system startup ######################

        try:

            count = 0

            while(1):

                if self.distro == ubuntu:
                    command = "systemctl enable mariadb"
                else:
                    command = "systemctl enable mysql"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to enable MariaDB instance to start and system restart, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to enable MariaDB instance to run at system restart, you can do this later using systemctl enable mysql! [installMySQL]")
                        break
                else:
                    logging.InstallLog.writeToFile("MariaDB instance successfully enabled at system restart!")
                    InstallCyberPanel.stdOut("MariaDB instance successfully enabled at system restart!")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0


        return 1

    def changeMYSQLRootPassword(self):
        try:

            logging.InstallLog.writeToFile("Changing MariaDB root password..")
            InstallCyberPanel.stdOut("Changing MariaDB root password..")


            expectation = "Enter password:"
            securemysql = pexpect.spawn("mysql -u root -p", timeout=5)
            securemysql.expect(expectation)
            securemysql.sendline("")

            expectation = "clear the current input statement."
            securemysql.expect(expectation)
            securemysql.sendline("use mysql;")

            expectation = "Database changed"
            securemysql.expect(expectation)
            securemysql.sendline("update user set password=PASSWORD('"+InstallCyberPanel.mysql_Root_password+"') where User='root';")

            expectation = "Query OK"
            securemysql.expect(expectation)
            securemysql.sendline("flush privileges;")

            expectation = "Query OK"
            securemysql.expect(expectation)
            securemysql.sendline("quit")

            securemysql.wait()

            logging.InstallLog.writeToFile("MariaDB root password changed!")
            InstallCyberPanel.stdOut("MariaDB root password changed!")


        except pexpect.EOF, msg:
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [changeMYSQLRootPassword]")
        except pexpect.TIMEOUT, msg:
            print securemysql.before
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [changeMYSQLRootPassword]")
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[changeMYSQLRootPassword]")

        return 0

    def changeMYSQLRootPasswordCyberPanel(self, mysql):
        try:

            logging.InstallLog.writeToFile("Changing CyberPanel MariaDB root password..")
            InstallCyberPanel.stdOut("Changing CyberPanel MariaDB root password..")

            expectation = "Enter password:"
            if mysql == 'Two':
                securemysql = pexpect.spawn("mysql --host=127.0.0.1 --port=3307 -u root -p", timeout=5)
            else:
                securemysql = pexpect.spawn("mysql -u root -p", timeout=5)

            securemysql.expect(expectation)
            securemysql.sendline("")

            expectation = "clear the current input statement."
            securemysql.expect(expectation)
            securemysql.sendline("use mysql;")

            expectation = "Database changed"
            securemysql.expect(expectation)
            securemysql.sendline("update user set password=PASSWORD('"+InstallCyberPanel.mysql_Root_password+"') where User='root';")

            expectation = "Query OK"
            securemysql.expect(expectation)
            securemysql.sendline("flush privileges;")

            expectation = "Query OK"
            securemysql.expect(expectation)
            securemysql.sendline("quit")

            securemysql.wait()

            logging.InstallLog.writeToFile("CyberPanel MariaDB root password changed!")
            InstallCyberPanel.stdOut("CyberPanel MariaDB root password changed!")


        except pexpect.EOF, msg:
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [changeMYSQLRootPasswordCyberPanel]")
        except pexpect.TIMEOUT, msg:
            print securemysql.before
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [changeMYSQLRootPasswordCyberPanel]")
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[changeMYSQLRootPasswordCyberPanel]")

        return 0

    def startMariaDB(self):

        ############## Start mariadb ######################

        try:
            count = 0

            while(1):
                command = "systemctl start mysql"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to start MariaDB instance, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to start MariaDB instance, exiting installer! [startMariaDB]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("MariaDB instance successfully started!")
                    InstallCyberPanel.stdOut("MariaDB instance successfully started!")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startMariaDB]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startMariaDB]")
            return 0

        return 1

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
        try:

            count = 0
            while (1):
                if self.distro == ubuntu:
                    command = 'apt-get -y install ' + install.preFlightsChecks.pureFTPDServiceName(self.distro)
                else:
                    command = "yum install -y pure-ftpd"

                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to install PureFTPD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to install PureFTPD, exiting installer! [installPureFTPD]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("PureFTPD successfully installed!")
                    InstallCyberPanel.stdOut("PureFTPD successfully installed!")
                    break


            ####### Install pureftpd to system startup

            count = 0

            while(1):

                command = "systemctl enable " + install.preFlightsChecks.pureFTPDServiceName(self.distro)
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to enable PureFTPD to start and system restart, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to enable PureFTPD to run at system restart, exiting installer! [installPureFTPD]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("PureFTPD successfully enabled at system restart!")
                    InstallCyberPanel.stdOut("PureFTPD successfully enabled at system restart!")
                    break




            ###### FTP Groups and user settings settings

            count = 0

            while(1):
                cmd = []
                cmd.append("groupadd")
                cmd.append("-g")
                cmd.append("2001")
                cmd.append("ftpgroup")

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to create group for FTP, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to create group for FTP, exiting installer! [installPureFTPD]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("System group for FTP successfully created!")
                    InstallCyberPanel.stdOut("System group for FTP successfully created!")
                    break

            count = 0

            while(1):

                cmd = []

                cmd.append("useradd")
                cmd.append("-u")
                cmd.append("2001")
                cmd.append("-s")
                cmd.append("/bin/false")
                cmd.append("-d")
                cmd.append("/bin/null")
                cmd.append("-c")
                cmd.append('"pureftpd user"')
                cmd.append("-g")
                cmd.append("ftpgroup")
                cmd.append("ftpuser")


                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to create user for FTP, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to create user for FTP, exiting installer! [installPureFTPD]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("System user for FTP successfully created!")
                    InstallCyberPanel.stdOut("System user for FTP successfully created!")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPureFTPD]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPureFTPD]")
            return 0

        return 1


    def startPureFTPD(self):

        ############## Start pureftpd ######################

        try:

            count = 0

            while(1):
                if self.distro == ubuntu:
                    command = 'systemctl start pure-ftpd-mysql'
                else:
                    command = 'systemctl start pure-ftpd'
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to start PureFTPD instance, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to start PureFTPD instance, you can do this manually later using systemctl start pure-ftpd [startPureFTPD]")
                        break
                else:
                    logging.InstallLog.writeToFile("PureFTPD instance successfully started!")
                    InstallCyberPanel.stdOut("PureFTPD instance successfully started!")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPureFTPD]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPureFTPD]")
            return 0

        return 1

    def installPureFTPDConfigurations(self, mysql):

        try:
            ## setup ssl for ftp

            logging.InstallLog.writeToFile("Configuring PureFTPD..")
            InstallCyberPanel.stdOut("Configuring PureFTPD..")

            try:
                os.mkdir("/etc/ssl/private")
            except:
                logging.InstallLog.writeToFile("Could not create directory for FTP SSL")

            count = 0

            while(1):
                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to create SSL for PureFTPD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to create SSL for PureFTPD! [installPureFTPDConfigurations]")
                        break
                else:
                    logging.InstallLog.writeToFile("SSL for PureFTPD successfully created!")
                    InstallCyberPanel.stdOut("SSL for PureFTPD successfully created!")
                    break


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

            if self.distro == ubuntu:
                os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)
            writeDataToFile.close()

            if self.distro == ubuntu:
                os.chmod(ftpdPath + '/pureftpd-ldap.conf', stat.S_IRUSR | stat.S_IWUSR)
                os.chmod(ftpdPath + '/pureftpd-pgsql.conf', stat.S_IRUSR | stat.S_IWUSR)

            if self.distro == ubuntu:
                command = 'apt install pure-ftpd-mysql -y'
                subprocess.call(shlex.split(command))

                if os.path.exists('/etc/pure-ftpd/db/mysql.conf'):
                    os.remove('/etc/pure-ftpd/db/mysql.conf')
                    shutil.copy(ftpdPath+"/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')
                else:
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')

                command = 'echo 1 > /etc/pure-ftpd/conf/TLS'
                subprocess.call(command, shell=True)

                command = 'systemctl restart pure-ftpd-mysql.service'
                subprocess.call(shlex.split(command))

            logging.InstallLog.writeToFile("PureFTPD configured!")
            InstallCyberPanel.stdOut("PureFTPD configured!")

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPureFTPDConfigurations]")
            return 0

        return 1

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
                while (1):
                    command = 'yum -y install epel-release yum-plugin-priorities'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                    if res == 1:
                        count = count + 1
                        InstallCyberPanel.stdOut(
                            "Trying to install PowerDNS Repositories, trying again, try number: " + str(count))
                        if count == 3:
                            logging.InstallLog.writeToFile(
                                "Failed to install PowerDNS Repositories, exiting installer! [installPowerDNS]")
                            InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                            os._exit(0)
                    else:
                        logging.InstallLog.writeToFile("PowerDNS Repositories successfully installed!")
                        InstallCyberPanel.stdOut("PowerDNS Repositories successfully installed!")
                        break

                count = 0

                while (1):

                    command = 'curl -o /etc/yum.repos.d/powerdns-auth-master.repo ' \
                              'https://repo.powerdns.com/repo-files/centos-auth-master.repo'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                    if res == 1:
                        count = count + 1
                        InstallCyberPanel.stdOut(
                            "Trying to install PowerDNS Repositories, trying again, try number: " + str(count))
                        if count == 3:
                            logging.InstallLog.writeToFile(
                                "Failed to install PowerDNS Repositories, exiting installer! [installPowerDNS]")
                            InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                            os._exit(0)
                    else:
                        logging.InstallLog.writeToFile("PowerDNS Repositories successfully installed!")
                        InstallCyberPanel.stdOut("PowerDNS Repositories successfully installed!")
                        break

            count = 1

            while (1):
                if self.distro == ubuntu:
                    command = "DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server pdns-backend-mysql"
                    res = os.system(command)
                else:
                    command = 'yum -y install pdns pdns-backend-mysql'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to install PowerDNS, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install PowerDNS, exiting installer! [installPowerDNS]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("PowerDNS successfully installed!")
                    InstallCyberPanel.stdOut("PowerDNS successfully installed!")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [powerDNS]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [powerDNS]")
            return 0

        return 1

    def installPowerDNSConfigurations(self, mysqlPassword, mysql):
        try:

            logging.InstallLog.writeToFile("Configuring PowerDNS..")
            InstallCyberPanel.stdOut("Configuring PowerDNS..")

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
            if self.distro == ubuntu:
                os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            logging.InstallLog.writeToFile("PowerDNS configured!")
            InstallCyberPanel.stdOut("PowerDNS configured!")

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPowerDNSConfigurations]")
            return 0
        return 1

    def startPowerDNS(self):

        ############## Start PowerDNS ######################

        try:

            count = 0

            while(1):

                cmd = []

                cmd.append("systemctl")
                cmd.append("enable")
                cmd.append("pdns")

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to enable PowerDNS to start and system restart, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to enable PowerDNS to run at system restart, you can manually do this later using systemctl enable pdns! [startPowerDNS]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        break
                else:
                    logging.InstallLog.writeToFile("PowerDNS successfully enabled at system restart!")
                    InstallCyberPanel.stdOut("PowerDNS successfully enabled at system restart!")
                    break

            count = 1

            while(1):
                command = 'systemctl start pdns'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to start PowerDNS instance, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to start PowerDNS instance, exiting installer! [startPowerDNS]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("PowerDNS instance successfully started!")
                    InstallCyberPanel.stdOut("PowerDNS instance successfully started!")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPowerDNS]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPowerDNS]")
            return 0

        return 1

    def installLSCPD(self):
        try:

            logging.InstallLog.writeToFile("Starting LSCPD installation..")
            InstallCyberPanel.stdOut("Starting LSCPD installation..")

            os.chdir(self.cwd)

            count = 0

            while (1):
                if self.distro == ubuntu:
                    command = "apt-get -y install gcc g++ make autoconf rcs"
                else:
                    command = 'yum -y install gcc gcc-c++ make autoconf glibc rcs'

                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to install LSCPD prerequisites, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to install LSCPD prerequisites, exiting installer! [installLSCPD]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("LSCPD prerequisites successfully installed!")
                    InstallCyberPanel.stdOut("LSCPD prerequisites successfully installed!")
                    break

            count = 0

            while(1):
                if self.distro == ubuntu:
                    command = "apt-get -y install libpcre3 libpcre3-dev openssl libexpat1 libexpat1-dev libgeoip-dev" \
                              " zlib1g zlib1g-dev libudns-dev whichman curl"
                else:
                    command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel' \
                              ' which curl'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to install LSCPD prerequisites, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to install LSCPD prerequisites, exiting installer! [installLSCPD]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("LSCPD prerequisites successfully installed!")
                    InstallCyberPanel.stdOut("LSCPD prerequisites successfully installed!")
                    break

            count = 0

            while(1):

                command = 'tar zxf lscp.tar.gz -C /usr/local/'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to configure LSCPD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to configure LSCPD, exiting installer! [installLSCPD]")
                        InstallCyberPanel.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("LSCPD successfully configured!")
                    InstallCyberPanel.stdOut("LSCPD successfully extracted!")
                    break

            count = 0
            while(1):

                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /usr/local/lscp/key.pem -out /usr/local/lscp/cert.pem'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    InstallCyberPanel.stdOut("Trying to create SSL for LSCPD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to create SSL for LSCPD! [installLSCPD]")
                        break
                else:
                    logging.InstallLog.writeToFile("SSL for LSCPD successfully created!")
                    InstallCyberPanel.stdOut("SSL for LSCPD successfully created!")
                    break

            try:
                os.remove("/usr/local/lscp/fcgi-bin/lsphp")
                shutil.copy("/usr/local/lsws/lsphp70/bin/lsphp","/usr/local/lscp/fcgi-bin/lsphp")
            except:
                pass

            if self.distro == centos:
                command = 'adduser lscpd -M -d /usr/local/lscp'
            else:
                command = 'useradd lscpd -M -d /usr/local/lscp'

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if self.distro == centos:
                command = 'groupadd lscpd'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)
                # Added group in useradd for Ubuntu

            command = 'usermod -a -G lscpd lscpd'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            command = 'usermod -a -G lsadm lscpd'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            os.mkdir('/usr/local/lscp/cyberpanel')

            logging.InstallLog.writeToFile("LSCPD successfully installed!")
            InstallCyberPanel.stdOut("LSCPD successfully installed!")

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installLSCPD]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installLSCPD]")
            return 0

        return 1



def Main(cwd, mysql, distro, ent):

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

    installer = InstallCyberPanel("/usr/local/lsws/",cwd, distro, ent)

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
    installer.changeMYSQLRootPasswordCyberPanel(mysql)
    installer.startMariaDB()
    if distro == ubuntu:
        installer.fixMariaDB()

    mysqlUtilities.createDatabaseCyberPanel("cyberpanel","cyberpanel",InstallCyberPanel.mysqlPassword, mysql)

    installer.installPureFTPD()
    installer.installPureFTPDConfigurations(mysql)
    installer.startPureFTPD()

    installer.installPowerDNS()
    installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
    installer.startPowerDNS()

    installer.installLSCPD()