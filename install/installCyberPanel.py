import shutil
import sys
import subprocess
import os
import pexpect
import random
from mysqlUtilities import mysqlUtilities
import installLog as logging
import shlex
import randomPassword


class InstallCyberPanel:

    mysql_Root_password = ""
    mysqlPassword = ""

    def __init__(self,rootPath,cwd):
        self.server_root_path = rootPath
        self.cwd = cwd


    def installLiteSpeed(self):
        try:

            cmd = []

            count = 0

            while (1):

                command = 'yum install -y openlitespeed'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)


                if res == 1:
                    print("###############################################")
                    print("         Could not install Litespeed           ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Openlitespeed is not installed from repo" + " [installLiteSpeed]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          Litespeed Installed                  ")
                    print("###############################################")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installLiteSpeed]")
            return 0

        return 1


    def install_ls_panel_config(self):

        try:

            shutil.rmtree("/usr/local/lsws/conf")

            os.chdir(self.cwd)

            shutil.copytree("litespeed/conf", "/usr/local/lsws/conf")



        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_ls_panel_config]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_ls_panel_config]")
            return 0

        return 1

    def reStartLiteSpeed(self):

        try:

            cmd = []

            cmd.append(self.server_root_path+"bin/lswsctrl")
            cmd.append("restart")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not restart Litespeed server    ")
                print("###############################################")
                logging.InstallLog.writeToFile("[reStartLiteSpeed]")
            else:
                print("###############################################")
                print("          Litespeed Re-Started                 ")
                print("###############################################")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        return 1

    def changePortTo80(self):
        try:
            data = open(self.server_root_path+"conf/httpd_config.conf").readlines()

            writeDataToFile = open(self.server_root_path+"conf/httpd_config.conf", 'w')

            for items in data:
                if (items.find("*:8088") > -1):
                    writeDataToFile.writelines(items.replace("*:8088","*:80"))
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [changePortTo80]")
            return 0

        return self.reStartLiteSpeed()

    def addLiteSpeedRepo(self):
        try:
            cmd = []

            cmd.append("rpm")
            cmd.append("-ivh")
            cmd.append("http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm")
            res = subprocess.call(cmd)
            if res == 1:
                print("###############################################")
                print("         Could not add Litespeed repo         " )
                print("###############################################")
                logging.InstallLog.writeToFile("[addLiteSpeedRepo]")
            else:
                print("###############################################")
                print("          Litespeed Repo Added                 ")
                print("###############################################")

        except OSError,msg:
            logging.InstallLog.writeToFile(str(msg) + " [addLiteSpeedRepo]")
            return 0
        except ValueError,msg:
            logging.InstallLog.writeToFile(str(msg) + " [addLiteSpeedRepo]")
            return 0

        return 1


    def installAllPHPVersions(self):
        try:

            cmd = []

            count = 0

            while (1):

                command = 'yum -y groupinstall lsphp-all'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("         Could not install PHP Binaries        ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("initial PHP Binaries not installed properly [installAllPHPVersions]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          PHP Binaries installed               ")
                    print("###############################################")

                    ## only php 71


                    command = 'yum install lsphp71 lsphp71-json lsphp71-xmlrpc lsphp71-xml lsphp71-tidy lsphp71-soap lsphp71-snmp lsphp71-recode lsphp71-pspell lsphp71-process lsphp71-pgsql lsphp71-pear lsphp71-pdo lsphp71-opcache lsphp71-odbc lsphp71-mysqlnd lsphp71-mcrypt lsphp71-mbstring lsphp71-ldap lsphp71-intl lsphp71-imap lsphp71-gmp lsphp71-gd lsphp71-enchant lsphp71-dba  lsphp71-common  lsphp71-bcmath -y'

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                    if res == 1:
                        print("###############################################")
                        print("         Could not install PHP 71        ")
                        print("###############################################")
                        logging.InstallLog.writeToFile("PHP71 Binaries not installed properly [installAllPHPVersions]")

                    else:
                        print("###############################################")
                        print("          PHP 71 installed               ")
                        print("###############################################")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installAllPHPVersion]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installAllPHPVersion]")
            return 0

        return 1


    def installAllPHPToLitespeed(self):
        try:
            os.chdir(self.cwd)


            path = self.server_root_path + "conf/"

            if not os.path.exists(path+"phpconfigs"):
                shutil.copytree("phpconfigs",path+"phpconfigs")

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installAllPHPToLitespeed]")
            return 0

        return 1

    def setup_mariadb_repo(self):
        try:

            os.chdir(self.cwd)

            shutil.copy("mysql/MariaDB.repo","/etc/yum.repos.d/MariaDB.repo")

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_mariadb_repo]")
            return 0
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_mariadb_repo]")
            return 0



    def installMySQL(self):

        try:

            ############## Install mariadb ######################

            cmd = []

            count = 0

            while (1):

                command = 'yum -y install mariadb-server'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("         Could not install MariaDB             ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Could not install MYSQL [installMySQL]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("              MariaDB Installed                ")
                    print("###############################################")
                    break

            ## fix configurations

            pathConf = "/etc/my.cnf"
            pathServiceFile = "/etc/systemd/system/mysqld@.service"

            if os.path.exists(pathConf):
                os.remove(pathConf)

            if os.path.exists(pathServiceFile):
                os.remove(pathServiceFile)

            os.chdir(self.cwd)

            shutil.copy("mysql/my.cnf",pathConf)
            shutil.copy("mysql/mysqld@.service",pathServiceFile)

            command = "mysql_install_db --user=mysql --datadir=/var/lib/mysql1"

            subprocess.call(shlex.split(command))

            command = "systemctl start mysqld@1"

            subprocess.call(shlex.split(command))

            command = "systemctl enable mysqld@1"

            subprocess.call(shlex.split(command))


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

            cmd = []

            cmd.append("systemctl")
            cmd.append("enable")
            cmd.append("mariadb")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("      Could not add mariadb to startup         ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not add mariadb to startup [installMySQL]")
            else:
                print("###############################################")
                print("          MariaDB Addded to startup            ")
                print("###############################################")

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0


        return 1

    def secureMysqlInstallation(self):
        try:
            expectation = "Enter current password"
            securemysql = pexpect.spawn("mysql_secure_installation", timeout=5)
            securemysql.expect(expectation)
            securemysql.sendline("")

            expectation = "root password? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            expectation = "New password:"
            securemysql.expect(expectation)
            securemysql.sendline(self.mysql_password)

            expectation = "new password:"
            securemysql.expect(expectation)
            securemysql.sendline(self.mysql_password)

            expectation = "anonymous users? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            expectation = "root login remotely? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            expectation = "test database and access to it? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            expectation = "Reload privilege tables now? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            securemysql.wait()

            if (securemysql.before.find("Thanks for using MariaDB!") > -1 or securemysql.after.find(
                    "Thanks for using MariaDB!") > -1):
                return 1

        except pexpect.EOF, msg:
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [secureMysqlInstallation]")
        except pexpect.TIMEOUT, msg:
            print securemysql.after
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [secureMysqlInstallation]")
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[secureMysqlInstallation]")

        return 0

    def changeMYSQLRootPassword(self):
        try:
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


        except pexpect.EOF, msg:
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [changeMYSQLRootPassword]")
        except pexpect.TIMEOUT, msg:
            print securemysql.before
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [changeMYSQLRootPassword]")
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[changeMYSQLRootPassword]")

        return 0

    def changeMYSQLRootPasswordCyberPanel(self):
        try:
            expectation = "Enter password:"
            securemysql = pexpect.spawn("mysql --host=127.0.0.1 --port=3307 -u root -p", timeout=5)
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

            cmd = []

            cmd.append("systemctl")
            cmd.append("start")
            cmd.append("mariadb")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("           Could not start MariaDB             ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not start MariaDB [startMariaDB]")
            else:
                print("###############################################")
                print("              MariaDB Started                  ")
                print("###############################################")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startMariaDB]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startMariaDB]")
            return 0

        return 1


    def installPureFTPD(self):
        try:

            cmd = []

            count = 0

            while (1):

                cmd.append("yum")
                cmd.append("install")
                cmd.append("-y")
                cmd.append("pure-ftpd")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("         Could not install PureFTPD            ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Could not install PureFTPD [installPureFTPD]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          PureFTPD Installed                   ")
                    print("###############################################")
                    break


            ####### Install pureftpd to system startup

            cmd = []

            cmd.append("systemctl")
            cmd.append("enable")
            cmd.append("pure-ftpd")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("      Could not add pureftpd to startup        ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not add pureftpd to startup [installPureFTPD]")
            else:
                print("###############################################")
                print("         pureftpd Addded to startup            ")
                print("###############################################")




            ###### FTP Groups and user settings settings


            cmd = []

            cmd.append("groupadd")
            cmd.append("-g")
            cmd.append("2001")
            cmd.append("ftpgroup")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Could not add FTP Group              ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not add FTP Group [installPureFTPD]")
            else:
                print("###############################################")
                print("             FTP Group Added                   ")
                print("###############################################")

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
                print("###############################################")
                print("          Could not add FTP User               ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not add FTP group [installPureFTPD]")
            else:
                print("###############################################")
                print("            FTP User Added                     ")
                print("###############################################")

            cmd = []

            cmd.append("usermod")
            cmd.append("-a")
            cmd.append("-G")
            cmd.append("nobody")
            cmd.append("ftpuser")


            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Could not add FTP User               ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not add FTP User [installPureFTPD]")
            else:
                print("###############################################")
                print("            FTP User Added                     ")
                print("###############################################")




        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPureFTPD]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPureFTPD]")
            return 0

        return 1

    def startPureFTPD(self):

        ############## Start mariadb ######################

        try:

            cmd = []

            cmd.append("systemctl")
            cmd.append("start")
            cmd.append("pure-ftpd")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("           Could not start pureftpd            ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not start pureftpd [installPureFTPD]")
            else:
                print("###############################################")
                print("              pureftpd Started                 ")
                print("###############################################")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPureFTPD]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPureFTPD]")
            return 0

        return 1


    def installPureFTPDConfigurations(self):

        try:
            os.chdir(self.cwd)
            ftpdPath = "/etc/pure-ftpd"

            if os.path.exists(ftpdPath):
                shutil.rmtree(ftpdPath)
                shutil.copytree("pure-ftpd",ftpdPath)
            else:
                shutil.copytree("pure-ftpd", ftpdPath)

            data = open(ftpdPath+"/pureftpd-mysql.conf","r").readlines()

            writeDataToFile = open(ftpdPath+"/pureftpd-mysql.conf","w")

            dataWritten = "MYSQLPassword "+InstallCyberPanel.mysqlPassword+'\n'


            for items in data:
                if items.find("MYSQLPassword")>-1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPureFTPDConfigurations]")
            return 0

        return 1

    def installPowerDNS(self):

        try:

            count = 0

            while (1):

                command = 'yum -y install epel-release yum-plugin-priorities'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    logging.InstallLog.writeToFile("plugin-priorities [installPowerDNS]")
                else:
                    pass

                command = 'curl -o /etc/yum.repos.d/powerdns-auth-master.repo https://repo.powerdns.com/repo-files/centos-auth-master.repo'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    logging.InstallLog.writeToFile("636 [installPowerDNS]")
                else:
                    pass

                command = 'yum -y install pdns pdns-backend-mysql'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)



                if res == 1:
                    print("###############################################")
                    print("          Can not install PowerDNS                ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Can not install PowerDNS [installPowerDNS]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          PowerDNS Installed                      ")
                    print("###############################################")
                    break



        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [powerDNS]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [powerDNS]")
            return 0

        return 1


    def installPowerDNSConfigurations(self,mysqlPassword):

        try:
            os.chdir(self.cwd)
            dnsPath = "/etc/pdns/pdns.conf"

            if os.path.exists(dnsPath):
                os.remove(dnsPath)
                shutil.copy("dns/pdns.conf", dnsPath)
            else:
                shutil.copy("dns/pdns.conf", dnsPath)

            data = open(dnsPath, "r").readlines()

            writeDataToFile = open(dnsPath, "w")

            dataWritten = "gmysql-password=" + mysqlPassword + "\n"

            for items in data:
                if items.find("gmysql-password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()


        except IOError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installPowerDNSConfigurations]")
            return 0

        return 1

    def startPowerDNS(self):

        ############## Start mariadb ######################

        try:

            cmd = []

            cmd.append("systemctl")
            cmd.append("enable")
            cmd.append("pdns")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("           Could not start PowerDNS                 ")
                print("###############################################")
                logging.InstallLog.writeToFile("Could not start PowerDNS" + " [startPowerDNS]")
            else:
                print("###############################################")
                print("              PowerDNS Started                      ")
                print("###############################################")

            command = 'systemctl start pdns'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)


            if res == 1:
                logging.InstallLog.writeToFile("734 [startPowerDNS]")
            else:
                pass


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPowerDNS]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [startPowerDNS]")
            return 0

        return 1

    def installCertBot(self):

        try:

            cmd = []

            count = 0

            while (1):

                cmd.append("yum")
                cmd.append("-y")
                cmd.append("install")
                cmd.append("yum-utils")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("         Could not install yum utils             ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("yum utils not installed" + " [installCertBot]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("            yum utils Installed                  ")
                    print("###############################################")
                    break

            cmd = []

            count = 0

            while (1):

                cmd.append("yum-config-manager")
                cmd.append("--enable")
                cmd.append("rhui-REGION-rhel-server-extras")
                cmd.append("rhui-REGION-rhel-server-optional")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("         Could not install yum-config-manager             ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("yum-config-manager --enable failed" + " [installCertBot]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("            yum-config-manager Installed                  ")
                    print("###############################################")
                    break

            cmd = []

            count = 0

            while (1):

                cmd.append("yum")
                cmd.append("-y")
                cmd.append("install")
                cmd.append("certbot")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("         Could not install CertBot             ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Certbot not installed" + " [installCertBot]")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("            Certbot Installed                  ")
                    print("###############################################")
                    break




        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installCertBot]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installCertBot]")
            return 0

        return 1



    def installLSCPD(self):
        try:

            os.chdir(self.cwd)

            command = 'yum -y install epel-release'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("836 [installLSCPD]")
            else:
                pass

            command = 'yum -y install gcc gcc-c++ make autoconf glibc rcs'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("846 [installLSCPD]")
            else:
                pass


            command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)


            if res == 1:
                logging.InstallLog.writeToFile("860 [installLSCPD]")
            else:
                pass


            command = 'tar zxf openlitespeed-1.4.28.tgz'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("872 [installLSCPD]")
            else:
                pass

            os.chdir("openlitespeed-1.4.28")

            command = './configure --with-lscpd --prefix=/usr/local/lscp'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("885 [installLSCPD]")
            else:
                pass

            command = 'make'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("896 [installLSCPD]")
            else:
                pass

            command = 'make install'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("907 [installLSCPD]")
            else:
                pass

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /usr/local/lscp/key.pem -out /usr/local/lscp/cert.pem'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("918 [installLSCPD]")
            else:
                pass

            try:
                os.remove("/usr/local/lscp/fcgi-bin/lsphp")
                shutil.copy("/usr/local/lsws/lsphp70/bin/lsphp","/usr/local/lscp/fcgi-bin/lsphp")
            except:
                pass


            if res == 0:

                print("###############################################")
                print("          LSCPD Installed                ")
                print("###############################################")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installLSCPD]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installLSCPD]")
            return 0

        return 1





def Main(cwd):
    InstallCyberPanel.mysqlPassword = randomPassword.generate_pass()

    InstallCyberPanel.mysql_Root_password = randomPassword.generate_pass()

    os.mkdir("/etc/cyberpanel")


    password = open("/etc/cyberpanel/mysqlPassword","w")
    password.writelines(InstallCyberPanel.mysql_Root_password)
    password.close()


    installer = InstallCyberPanel("/usr/local/lsws/",cwd)


    installer.installLiteSpeed()
    installer.install_ls_panel_config()
    installer.changePortTo80()

    #installer.addLiteSpeedRepo()

    installer.installAllPHPVersions()
    installer.installAllPHPToLitespeed()

    installer.setup_mariadb_repo()
    installer.installMySQL()
    installer.changeMYSQLRootPassword()
    installer.changeMYSQLRootPasswordCyberPanel()
    installer.startMariaDB()

    mysqlUtilities.createDatabaseCyberPanel("cyberpanel","cyberpanel",InstallCyberPanel.mysqlPassword)


    installer.installPureFTPD()
    installer.installPureFTPDConfigurations()
    installer.startPureFTPD()

    installer.installPowerDNS()
    installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword)
    installer.startPowerDNS()


    installer.installCertBot()
    installer.installLSCPD()



def test():
    installer = InstallCyberPanel("/usr/local/lsws/", "/home")
    installer.installLSCPD()