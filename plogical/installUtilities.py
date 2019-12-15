import subprocess
import sys
from plogical import CyberCPLogFileWriter as logging
import shutil
import pexpect
import os
import shlex
from plogical.processUtilities import ProcessUtilities

class installUtilities:

    Server_root_path = "/usr/local/lsws"

    @staticmethod
    def enableEPELRepo():
        try:
            cmd = []
            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("epel-release")
            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not add EPEL repo              " )
                print("###############################################")
            else:
                print("###############################################")
                print("          EPEL Repo Added                      ")
                print("###############################################")
        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0

        return 1


    @staticmethod
    def addLiteSpeedRepo():
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
            else:
                print("###############################################")
                print("          Litespeed Repo Added                 ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addLiteSpeedRepo]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addLiteSpeedRepo]")
            return 0

        return 1

    @staticmethod
    def installLiteSpeed():

        try:

            cmd = []

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("openlitespeed-1.4.26")

            res = subprocess.call(cmd)


            if res == 1:
                print("###############################################")
                print("         Could not install Litespeed          " )
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          Litespeed Installed                  ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installLiteSpeed]")
            return 0

        return 1


    @staticmethod
    def startLiteSpeed():

        try:

            cmd = []

            cmd.append("/usr/local/lsws/bin/lswsctrl")
            cmd.append("start")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not start Litespeed server      ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          Litespeed Started                    ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startLiteSpeed]")
            return 0

        return 1


    @staticmethod
    def reStartLiteSpeed():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "systemctl restart lsws"
            else:
                command = "/usr/local/lsws/bin/lswsctrl restart"

            ProcessUtilities.normalExecutioner(command)

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        return 1

    @staticmethod
    def reStartLiteSpeedSocket():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl restart lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl restart"

            return ProcessUtilities.executioner(command)

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0

    @staticmethod
    def stopLiteSpeedSocket():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl stop lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl stop"

            return ProcessUtilities.executioner(command)

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0


    @staticmethod
    def reStartOpenLiteSpeed(restart,orestart):
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl restart lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl restart"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not restart Litespeed serve     ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          Litespeed Re-Started                 ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartOpenLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartOpenLiteSpeed]")
            return 0
        return 1

    @staticmethod
    def changePortTo80():
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

            for items in data:
                if (items.find("*:8088") > -1):
                    writeDataToFile.writelines(items.replace("*:8088","*:80"))
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

        except IOError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [changePortTo80]")
            return 0

        return installUtilities.reStartLiteSpeed()


    @staticmethod
    def installAllPHPVersion():

        try:
            cmd = []

            cmd.append("yum")
            cmd.append("groupinstall")
            cmd.append("lsphp-all")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not install PHP Binaries        ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          PHP Binaries installed               ")
                print("###############################################")

                writeDataToFile = open(installUtilities.Server_root_path + "/conf/httpd_config.conf", "a")




        except OSError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installAllPHPVersion]")

            return 0

        except ValueError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installAllPHPVersion]")

            return 0

        return 1


    @staticmethod
    def installAllPHPToLitespeed():
        try:
            path = installUtilities.Server_root_path + "/conf/"
            if not os.path.exists(path):
                shutil.copytree("phpconfigs",path+"phpconfigs")

            php53 = "include phpconfigs/php53.conf\n"
            php54 = "include phpconfigs/php54.conf\n"
            php55 = "include phpconfigs/php55.conf\n"
            php56 = "include phpconfigs/php56.conf\n"
            php70 = "include phpconfigs/php70.conf\n"

            writeDataToFile = open(path+"httpd_config.conf", 'a')


            writeDataToFile.writelines(php53)
            writeDataToFile.writelines(php54)
            writeDataToFile.writelines(php55)
            writeDataToFile.writelines(php56)
            writeDataToFile.writelines(php70)

            writeDataToFile.close()

        except IOError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installAllPHPToLitespeed]")
            return 0

        return 1

    @staticmethod
    def installMainWebServer():
        if installUtilities.enableEPELRepo() == 1:
            if installUtilities.addLiteSpeedRepo() == 1:
                if installUtilities.installLiteSpeed() == 1:
                    if installUtilities.startLiteSpeed() == 1:
                        if installUtilities.installAllPHPVersion():
                            if installUtilities.installAllPHPToLitespeed():
                                return 1
                            else:
                                return 0
                        else:
                            return 0
                    else:
                        return 0
                else:
                    return 0
            else:
                return 0
        else:
            return 0

    @staticmethod
    def removeWebServer():

        try:
            cmd = []
            cmd.append("yum")
            cmd.append("-y")
            cmd.append("remove")
            cmd.append("openlitespeed-1.4.26")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Could not remove Litespeed           ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("            Litespeed Removed                  ")
                print("###############################################")


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0


        try:
            cmd = []
            cmd.append("yum")
            cmd.append("-y")
            cmd.append("remove")
            cmd.append("lsphp*")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("           Could not PHP Binaries              ")
                print("###############################################")
            else:

                print("###############################################")
                print("            PHP Binaries Removed              ")
                print("###############################################")
                sys.exit()

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0


        try:
            shutil.rmtree(installUtilities.Server_root_path)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0

        return 1

    @staticmethod
    def startMariaDB():

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
                sys.exit()
            else:
                print("###############################################")
                print("              MariaDB Started                  ")
                print("###############################################")


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startMariaDB]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startMariaDB]")
            return 0

        return 1

    @staticmethod
    def installMySQL(password):

        try:

            ############## Install mariadb ######################

            cmd = []

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("mariadb-server")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not install MariaDB             ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("              MariaDB Installed                ")
                print("###############################################")


        except OSError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installMySQL]")

            return 0

        except ValueError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installMySQL]")

            return 0


            ############## Start mariadb ######################

        installUtilities.startMariaDB()

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
                sys.exit()
            else:
                print("###############################################")
                print("          MariaDB Addded to startup            ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0

        if installUtilities.secureMysqlInstallation(password) == 1:
            return 1

        return 0

    @staticmethod
    def secureMysqlInstallation(password):

        try:
            expectation = "(enter for none):"
            securemysql = pexpect.spawn("mysql_secure_installation",maxread=20000)
            securemysql.expect(expectation)
            securemysql.sendcontrol('j')



            expectation = "password? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            expectation = "New password:"
            securemysql.expect(expectation)
            securemysql.sendline("1qaz@9xvps")

            expectation = "new password:"
            securemysql.expect(expectation)
            securemysql.sendline(password)

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


            if (securemysql.before.find("Thanks for using MariaDB!") > -1 or securemysql.after.find("Thanks for using MariaDB!")>-1):
                return 1

        except pexpect.EOF as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Exception EOF [installMySQL]")
            print("###########################Before########################################")
            print(securemysql.before)
            print("###########################After########################################")
            print(securemysql.after)
            print("########################################################################")
        except BaseException as msg:
            print("#############################Before#####################################")
            print(securemysql.before)
            print("############################After######################################")
            print(securemysql.after)
            print("########################################################################")
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installMySQL]")


        return 0


#installUtilities.installAllPHPToLitespeed()