import sys
import subprocess
import shutil
import installLog as logging
import argparse
import os
import shlex
import socket
from firewallUtilities import FirewallUtilities



class preFlightsChecks:

    def __init__(self,rootPath,ip,path,cwd,cyberPanelPath):
        self.ipAddr = ip
        self.path = path
        self.cwd = cwd
        self.server_root_path = rootPath
        self.cyberPanelPath = cyberPanelPath

    def yum_update(self):
        try:

            cmd = []

            count = 0

            while (1):

                command = 'yum update -y'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not run yum_update                ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Could not install unzip")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          yum_update successfull               ")
                    print("###############################################")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [yum_update]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [yum_update]")
            return 0

        return 1

    def setup_account_cyberpanel(self):
        try:
            command = "yum install sudo -y"

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ##

            command = "adduser cyberpanel"

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ##

            command = "usermod -aG wheel cyberpanel"

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ###############################

            path = "/etc/sudoers"

            data = open(path, 'r').readlines()

            writeToFile = open(path, 'w')

            for items in data:
                if items.find("wheel	ALL=(ALL)	NOPASSWD: ALL") > -1:
                    writeToFile.writelines("%wheel	ALL=(ALL)	NOPASSWD: ALL")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            ###############################

            command = "mkdir /etc/letsencrypt"

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ##

        except:
            logging.InstallLog.writeToFile("[116] setup_account_cyberpanel")

    def checkPythonVersion(self):

        if sys.version_info[0] == 2 and sys.version_info[1] == 7:
            return 1
        else:
            print("You are running Unsupported python version, please install python 2.7.")
            sys.exit()

    def installCyberPanelRepo(self):

        cmd = []

        count = 0

        while(1):
            cmd.append("rpm")
            cmd.append("-ivh")
            cmd.append("http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm")
            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not add CyberPanel repo         ")
                print("###############################################")
                logging.InstallLog.writeToFile("[installCyberPanelRepo]")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("          CyberPanel Repo Added                ")
                print("###############################################")
                break

    def enableEPELRepo(self):
        try:
            cmd = []

            count = 0

            while (1):
                cmd.append("yum")
                cmd.append("-y")
                cmd.append("install")
                cmd.append("epel-release")
                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("         Could not add EPEL repo              " )
                    print("###############################################")
                    logging.InstallLog.writeToFile("Not able to add epel repo")
                    count = count + 1
                    print("Trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          EPEL Repo Added                      ")
                    print("###############################################")
                    break

        except OSError,msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0
        except ValueError,msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0

        return 1

    def install_pip(self):
        cmd = []

        count = 0

        while (1):
            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("python-pip")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install PIP                  ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install PIP [install_pip]")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("             PIP Installed                     ")
                print("###############################################")
                break

    def install_python_setup_tools(self):
        cmd = []

        count = 0

        while (1):

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("python-setuptools")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("      Can not install python setup tool        ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install python setup tool")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("         Python setup tools installed          ")
                print("###############################################")
                break

    def install_python_dev(self):
        cmd = []

        count = 0

        while (1):

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("python-devel")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("  Can not install Python Development Package    ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install Python Development Package")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("   Python Development Package Installed        ")
                print("###############################################")
                break

    def install_python_requests(self):
        try:
            import requests
        except:

            cmd = []

            count = 0

            while (1):
                cmd.append("pip")
                cmd.append("install")
                cmd.append("requests")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("       Can not install  Python Requests        ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Can not install  Python Requests")
                    count = count + 1
                    print("Trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("       Python Requests Installed               ")
                    print("###############################################")
                    break

    def install_gcc(self):

        cmd = []

        count = 0

        while (1):

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("gcc")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install GCC                  ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install GCC")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("             GCC Installed                     ")
                print("###############################################")
                break

    def install_pexpect(self):

        try:
            import pexpect
        except:
            cmd = []

            count = 0

            while (1):
                cmd.append("pip")
                cmd.append("install")
                cmd.append("pexpect")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not install PEXPECT              ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Can not install PEXPECT")
                    count = count + 1
                    print("Trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("             PEXPECT Installed                 ")
                    print("###############################################")
                    break

    def install_django(self):
        cmd = []

        count = 0

        while (1):

            cmd.append("pip")
            cmd.append("install")
            cmd.append("django==1.11")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install DJANGO               ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install DJANGO")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("             DJANGO Installed                 ")
                print("###############################################")
                break

    def install_python_mysql_library(self):
        cmd = []

        count = 0

        while (1):

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("MySQL-python")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("       Can not install MYSQL Library           ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install MYSQL Library")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("        MYSQL Library Installed                ")
                print("###############################################")
                break

    def install_wget(self):
        cmd = []

        count = 0

        while (1):

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("wget")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install wget                 ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install wget")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("             wget Installed                    ")
                print("###############################################")
                break


    def install_gunicorn(self):
        cmd = []

        count = 0

        while (1):

            cmd.append("easy_install")
            cmd.append("gunicorn")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install gunicorn             ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install gunicorn")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("             gunicorn Installed                ")
                print("###############################################")
                break

    def setup_gunicorn(self):
        try:

            os.chdir(self.cwd)

            service = "/etc/systemd/system/gunicorn.service"
            socket = "/etc/systemd/system/gunicorn.socket"
            conf = "/etc/tmpfiles.d/gunicorn.conf"


            shutil.copy("gun-configs/gunicorn.service",service)
            shutil.copy("gun-configs/gunicorn.socket",socket)
            shutil.copy("gun-configs/gunicorn.conf", conf)

            ### Enable at system startup

            cmd = []

            cmd.append("systemctl")
            cmd.append("enable")
            cmd.append("gunicorn.socket")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("     Can not add gunicorn to system startup    ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not add gunicorn to system startup")
            else:
                print("###############################################")
                print("          Added gunicorn to system startup     ")
                print("###############################################")

            cmd = []

            cmd.append("systemctl")
            cmd.append("start")
            cmd.append("gunicorn.socket")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("     Can not start gunicorn socket             ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not start gunicorn socket")
            else:
                print("###############################################")
                print("         Gunicorn socket started               ")
                print("###############################################")


        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_gunicorn]")
            print "Not able to setup gunicorn, see install log."

    def install_psutil(self):

        try:
            import psutil
        except:

            cmd = []

            count = 0

            while (1):

                cmd = []

                cmd.append("easy_install")
                cmd.append("psutil")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not install psutil               ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Can not install psutil")
                    count = count + 1
                    print("Trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("             psutil Installed                  ")
                    print("###############################################")
                    break


    def install_argparse(self):

        try:
            import argparse
        except:

            cmd = []

            count = 0

            while (1):
                cmd.append("pip")
                cmd.append("install")
                cmd.append("argparse")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not install argparse             ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Can not install argparse")
                    count = count + 1
                    print("Trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("             argparse Installed                ")
                    print("###############################################")
                    break

    def fix_selinux_issue(self):
        try:
            cmd = []

            cmd.append("setsebool")
            cmd.append("-P")
            cmd.append("httpd_can_network_connect")
            cmd.append("1")

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("fix_selinux_issue problem")
            else:
                pass
        except:
            logging.InstallLog.writeToFile("fix_selinux_issue problem")

    def install_psmisc(self):

        cmd = []

        count = 0

        while (1):
            cmd = []

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("psmisc")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install psmisc               ")
                print("###############################################")
                logging.InstallLog.writeToFile("install_psmisc")
                count = count + 1
                print("Trying again, try number: " + str(count) + "\n")
                if count == 3:
                    break
            else:
                print("###############################################")
                print("             psmisc Installed                   ")
                print("###############################################")
                break


    def download_install_CyberPanel(self,mysqlPassword):
        try:

            if subprocess.check_output('systemd-detect-virt').find("openvz")>-1:
                cmd = []

                cmd.append("pip")
                cmd.append("install")
                cmd.append("--upgrade")
                cmd.append("requests")

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("       Can not upgrade  Python Requests    ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Can not upgrade  Python Requests")
                else:
                    print("###############################################")
                    print("     Python Requests Upgraded        ")
                    print("###############################################")
        except:
            pass


        os.chdir(self.path)

        cmd = []

        cmd.append("wget")
        cmd.append("http://cyberpanel.net/CyberPanel.1.6.0.tar.gz")

        res = subprocess.call(cmd)

        if res == 1:
            print("###############################################")
            print("           Could Not Download CyberPanel          ")
            print("###############################################")
            logging.InstallLog.writeToFile("Could Not Download CyberPanel")
        else:
            print("###############################################")
            print("              CyberPanel Downloaded               ")
            print("###############################################")


        cmd = []

        cmd.append("tar")
        cmd.append("zxf")
        cmd.append("CyberPanel.1.6.0.tar.gz")

        res = subprocess.call(cmd)

        ### update password:

        passFile = "/etc/cyberpanel/mysqlPassword"

        f = open(passFile)
        data = f.read()
        password = data.split('\n', 1)[0]


        path = self.cyberPanelPath+"/CyberCP/settings.py"

        data = open(path, "r").readlines()

        writeDataToFile = open(path, "w")

        counter = 0

        for items in data:
            if items.find("'PASSWORD':") > -1:
                if counter == 0:
                    writeDataToFile.writelines("        'PASSWORD': '" + mysqlPassword + "'," + "\n")
                    counter = counter + 1
                else:
                    writeDataToFile.writelines("        'PASSWORD': '" + password + "'," + "\n")

            else:
                writeDataToFile.writelines(items)

        writeDataToFile.close()



        ###


        os.chdir("CyberCP")

        cmd = []

        cmd.append("python")
        cmd.append("manage.py")
        cmd.append("makemigrations")

        res = subprocess.call(cmd)

        if res == 1:
            logging.InstallLog.writeToFile("migrations failed")
        else:
            pass

        cmd = []

        cmd.append("python")
        cmd.append("manage.py")
        cmd.append("migrate")

        res = subprocess.call(cmd)

        if res == 1:
            logging.InstallLog.writeToFile("migrations failed")
        else:
            pass

        command = 'mv static /usr/local/lscp/cyberpanel'

        cmd = shlex.split(command)

        res = subprocess.call(cmd)


        if res == 1:

            print("###################################################################")
            print("         Could not install CyberPanel, consult install log         ")
            print("###################################################################")

            logging.InstallLog.writeToFile("Could not install CyberPanel")
        else:
            print("###################################################################")
            print("                CyberPanel Successfully Installed                  ")
            print("                                                                   ")

            print("                                                                   ")
            print("                                                                   ")

            print("                Visit: https://"+self.ipAddr+":8090                ")
            print("                Username: admin                                    ")
            print("                Password: 1234567                                  ")

            print("###################################################################")

            ## fix permissions

            command = "chmod -R 744 /usr/local/CyberCP"

            res = subprocess.call(shlex.split(command))

            if res == 1:
                logging.InstallLog.writeToFile("[805] Permissions fix failed!")
            else:
                pass


            ## change owner

            command = "chown -R cyberpanel:cyberpanel /usr/local/CyberCP"

            res = subprocess.call(shlex.split(command))

            if res == 1:
                logging.InstallLog.writeToFile("[805] Permissions fix failed!")
            else:
                pass

    def install_unzip(self):
        try:

            cmd = []

            count = 0

            while (1):

                command = 'yum -y install unzip'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not install unzip                ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Could not install unzip")
                    count = count + 1
                    print("Trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          Unzip Installed                      ")
                    print("###############################################")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_unzip]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_unzip]")
            return 0

        return 1

    def install_zip(self):
        try:

            cmd = []

            count = 0

            while (1):

                command = 'yum -y install zip'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not install zip                ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Could not install unzip")
                    count = count + 1
                    print("Trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          zip Installed                      ")
                    print("###############################################")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_zip]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_zip]")
            return 0

        return 1

    def download_install_phpmyadmin(self):
        try:

            os.chdir("/usr/local/lscp/cyberpanel/")

            command = 'wget https://files.phpmyadmin.net/phpMyAdmin/4.7.5/phpMyAdmin-4.7.5-all-languages.zip'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not download PHPMYAdmin          ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not download PHPMYAdmin")
            else:
                print("###############################################")
                print("          PHPMYAdmin Downloaded                ")
                print("###############################################")

            command = 'unzip phpMyAdmin-4.7.5-all-languages.zip'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("746 [download_install_phpmyadmin]")
            else:
                pass

            os.remove("phpMyAdmin-4.7.5-all-languages.zip")

            command = 'mv phpMyAdmin-4.7.5-all-languages phpmyadmin'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("610 [download_install_phpmyadmin]")
            else:
                pass

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [download_install_phpmyadmin]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [download_install_phpmyadmin]")
            return 0

        return 1


    ###################################################### Email setup


    def install_postfix_davecot(self):
        try:

            command = 'yum -y --enablerepo=centosplus install postfix'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install postfix                ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install postfix")
            else:
                print("###############################################")
                print("          postfix Installed                      ")
                print("###############################################")

            command = 'yum -y install dovecot dovecot-mysql'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Can not install dovecot                ")
                print("###############################################")
                logging.InstallLog.writeToFile("Can not install dovecot")
            else:
                print("###############################################")
                print("          dovecot Installed                      ")
                print("###############################################")



        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_postfix_davecot]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_postfix_davecot]")
            return 0

        return 1


    def setup_email_Passwords(self,mysqlPassword):
        try:
           os.chdir(self.cwd)

           mysql_virtual_domains = "email-configs/mysql-virtual_domains.cf"
           mysql_virtual_forwardings = "email-configs/mysql-virtual_forwardings.cf"
           mysql_virtual_mailboxes = "email-configs/mysql-virtual_mailboxes.cf"
           mysql_virtual_email2email = "email-configs/mysql-virtual_email2email.cf"
           davecotmysql = "email-configs/dovecot-sql.conf.ext"

           ### update password:

           data = open(davecotmysql, "r").readlines()

           writeDataToFile = open(davecotmysql, "w")

           dataWritten = "connect = host=127.0.0.1 dbname=cyberpanel user=cyberpanel password="+mysqlPassword+" port=3307\n"

           for items in data:
               if items.find("connect") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_domains, "r").readlines()

           writeDataToFile = open(mysql_virtual_domains, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_forwardings, "r").readlines()

           writeDataToFile = open(mysql_virtual_forwardings, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_mailboxes, "r").readlines()

           writeDataToFile = open(mysql_virtual_mailboxes, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_email2email, "r").readlines()

           writeDataToFile = open(mysql_virtual_email2email, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()




        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_email_Passwords]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_email_Passwords]")
            return 0

        return 1



    def setup_postfix_davecot_config(self):
        try:
           os.chdir(self.cwd)

           mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
           mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
           mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
           mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
           main = "/etc/postfix/main.cf"
           master = "/etc/postfix/master.cf"
           davecot = "/etc/dovecot/dovecot.conf"
           davecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"



           if os.path.exists(mysql_virtual_domains):
               os.remove(mysql_virtual_domains)

           if os.path.exists(mysql_virtual_forwardings):
               os.remove(mysql_virtual_forwardings)

           if os.path.exists(mysql_virtual_mailboxes):
               os.remove(mysql_virtual_mailboxes)

           if os.path.exists(mysql_virtual_email2email):
               os.remove(mysql_virtual_email2email)

           if os.path.exists(main):
               os.remove(main)

           if os.path.exists(master):
               os.remove(master)

           if os.path.exists(davecot):
               os.remove(davecot)

           if os.path.exists(davecotmysql):
               os.remove(davecotmysql)



           ###############Getting SSL


           command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/postfix/key.pem -out /etc/postfix/cert.pem'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)


           if res == 1:
               logging.InstallLog.writeToFile("830 [setup_postfix_davecot_config]")
           else:
               pass

           command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/dovecot/key.pem -out /etc/dovecot/cert.pem'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
              logging.InstallLog.writeToFile("1072 [setup_postfix_davecot_config]")
           else:
               pass



               ########### Copy config files


           shutil.copy("email-configs/mysql-virtual_domains.cf","/etc/postfix/mysql-virtual_domains.cf")
           shutil.copy("email-configs/mysql-virtual_forwardings.cf", "/etc/postfix/mysql-virtual_forwardings.cf")
           shutil.copy("email-configs/mysql-virtual_mailboxes.cf", "/etc/postfix/mysql-virtual_mailboxes.cf")
           shutil.copy("email-configs/mysql-virtual_email2email.cf", "/etc/postfix/mysql-virtual_email2email.cf")
           shutil.copy("email-configs/main.cf", main)
           shutil.copy("email-configs/master.cf",master)
           shutil.copy("email-configs/dovecot.conf",davecot)
           shutil.copy("email-configs/dovecot-sql.conf.ext",davecotmysql)



           ######################################## Permissions

           command = 'chmod o= /etc/postfix/mysql-virtual_domains.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("859 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chmod o= /etc/postfix/mysql-virtual_forwardings.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1114 [setup_postfix_davecot_config]")
           else:
               pass


           ##

           command = 'chmod o= /etc/postfix/mysql-virtual_mailboxes.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("886 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chmod o= /etc/postfix/mysql-virtual_email2email.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1141 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chmod o= '+main

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("911 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chmod o= '+master

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("924 [setup_postfix_davecot_config]")
           else:
               pass


           #######################################

           command = 'chgrp postfix /etc/postfix/mysql-virtual_domains.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("936 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chgrp postfix /etc/postfix/mysql-virtual_forwardings.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("952 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chgrp postfix /etc/postfix/mysql-virtual_mailboxes.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("965 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chgrp postfix /etc/postfix/mysql-virtual_email2email.cf'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("978 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chgrp postfix '+main

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("991 [setup_postfix_davecot_config]")
           else:
               pass

           ##

           command = 'chgrp postfix ' + master

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1004 [setup_postfix_davecot_config]")
           else:
               pass


           ######################################## users and groups


           command = 'groupadd -g 5000 vmail'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1019 [setup_postfix_davecot_config]")
           else:
               pass

           command = 'useradd -g vmail -u 5000 vmail -d /home/vmail -m'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1030 [setup_postfix_davecot_config]")
           else:
               pass


           ######################################## Further configurations

           hostname = socket.gethostname()

           ################################### Restart postix

           command = 'systemctl enable postfix.service'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1048 [setup_postfix_davecot_config]")
           else:
               pass

           command = 'systemctl start  postfix.service'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1059 [setup_postfix_davecot_config]")
           else:
               pass

           ######################################## Permissions

           command = 'chgrp dovecot /etc/dovecot/dovecot-sql.conf.ext'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1072 [setup_postfix_davecot_config]")
           else:
               pass

           command = 'chmod o= /etc/dovecot/dovecot-sql.conf.ext'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1083 [setup_postfix_davecot_config]")
           else:
               pass

           ################################### Restart davecot

           command = 'systemctl enable dovecot.service'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1096 [setup_postfix_davecot_config]")
           else:
               pass

           command = 'systemctl start  dovecot.service'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1107 [setup_postfix_davecot_config]")
           else:
               pass

           command = 'systemctl restart  postfix.service'

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1118 [setup_postfix_davecot_config]")
           else:
               pass


           ## chaging permissions for main.cf

           command = "chmod 755 /etc/postfix/main.cf"

           cmd = shlex.split(command)

           res = subprocess.call(cmd)

           if res == 1:
               logging.InstallLog.writeToFile("1453 [setup_postfix_davecot_config]")
           else:
               pass


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_postfix_davecot_config]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_postfix_davecot_config]")
            return 0

        return 1


    def downoad_and_install_raindloop(self):
        try:

            command = 'chown -R nobody:nobody /usr/local/lscp/cyberpanel/'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("[downoad_and_install_rainloop]")
            else:
                pass



            os.chdir("/usr/local/lscp/cyberpanel")

            command = 'wget https://www.rainloop.net/repository/webmail/rainloop-community-latest.zip'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("[downoad_and_install_rainloop]")
            else:
                pass


            command = 'unzip rainloop-community-latest.zip -d /usr/local/lscp/cyberpanel/rainloop'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("[downoad_and_install_rainloop]")
            else:
                pass

            os.remove("rainloop-community-latest.zip")


            os.chdir("/usr/local/lscp/cyberpanel/rainloop")

            command = 'find . -type d -exec chmod 755 {} \;'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("permissions [downoad_and_install_rainloop]")
            else:
                pass

            command = 'find . -type f -exec chmod 644 {} \;'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("permissions [downoad_and_install_rainloop]")
            else:
                pass

            command = 'chown -R nobody:nobody .'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("permissions [downoad_and_install_rainloop]")
            else:
                pass




        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [downoad_and_install_rainloop]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [downoad_and_install_rainloop]")
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
                logging.InstallLog.writeToFile("Could not restart Litespeed server 1428")
            else:
                pass


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        return 1


    def installFirewalld(self):
        try:

            print("###############################################")
            print("          Enabling Firewall                ")
            print("###############################################")


            command = 'yum -y install firewalld'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("1268 [installFirewalld]")
            else:
                pass


            command = 'systemctl start firewalld'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("1280 [installFirewalld]")
            else:
                pass

            command = 'systemctl enable firewalld'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("1291 [installFirewalld]")
            else:
                pass


            FirewallUtilities.addRule("tcp","8090")
            FirewallUtilities.addRule("tcp", "80")
            FirewallUtilities.addRule("tcp", "443")
            FirewallUtilities.addRule("tcp", "21")
            FirewallUtilities.addRule("tcp", "25")
            FirewallUtilities.addRule("tcp", "587")
            FirewallUtilities.addRule("tcp", "465")
            FirewallUtilities.addRule("tcp", "110")
            FirewallUtilities.addRule("tcp", "143")
            FirewallUtilities.addRule("tcp", "993")
            FirewallUtilities.addRule("udp", "53")
            FirewallUtilities.addRule("tcp", "53")
            FirewallUtilities.addRule("tcp", "40110-40210")

            print("###############################################")
            print("          Firewall Enabled                ")
            print("###############################################")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0

        return 1

    def setupLSCPDDaemon(self):
        try:

            print("###############################################")
            print("          Enabling LSCPD Daemon                ")
            print("###############################################")

            os.chdir(self.cwd)


            shutil.copy("lscpd/lscpd.service","/etc/systemd/system/lscpd.service")
            shutil.copy("lscpd/lscpdctrl","/usr/local/lscp/bin/lscpdctrl")

            command = 'chmod +x /usr/local/lscp/bin/lscpdctrl'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("1586 [setupLSCPDDaemon]")
            else:
                pass


            command = 'systemctl enable lscpd.service'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("1598 [setupLSCPDDaemon]")
            else:
                pass

            command = 'systemctl start lscpd'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("1609 [setupLSCPDDaemon]")
            else:
                pass



            print("###############################################")
            print("          LSCPD Enabled                ")
            print("###############################################")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupLSCPDDaemon]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupLSCPDDaemon]")
            return 0

        return 1

    def setup_cron(self):

        try:

            ## first install crontab

            file = open("installLogs.txt", 'a')

            command = 'yum install cronie -y'

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=file)

            if res == 1:
                logging.InstallLog.writeToFile("1725 [Cron is not installed]")
            else:
                pass

            command = 'systemctl enable crond'

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=file)

            if res == 1:
                logging.InstallLog.writeToFile("1737 [Cron is not enabled]")
            else:
                pass

            command = 'systemctl start crond'

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=file)

            if res == 1:
                logging.InstallLog.writeToFile("1748 [Cron is not started]")
            else:
                pass

            ##

            cronFile = open("/etc/crontab", "a")
            cronFile.writelines("0 * * * * root python /usr/local/CyberCP/plogical/findBWUsage.py" + "\n")
            cronFile.close()

            command = 'chmod +x /usr/local/CyberCP/plogical/findBWUsage.py'

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=file)

            if res == 1:
                logging.InstallLog.writeToFile("1428 [setup_cron]")
            else:
                pass

            command = 'systemctl restart crond.service'

            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=file)

            if res == 1:
                logging.InstallLog.writeToFile("1440 [setup_cron]")
            else:
                pass

            file.close()



        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_cron]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_cron]")
            return 0

        return 1


    def install_default_keys(self):
        try:
            count = 0

            path = "/root/.ssh"

            if not os.path.exists(path):
                os.mkdir(path)

            while (1):

                command = "ssh-keygen -f /root/.ssh/cyberpanel -t rsa -N ''"

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not add default Keys                ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("install_default_keys")
                    count = count + 1
                    print("Trying again, try number: " + str(count)+"\n")
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          Default Keys Added                      ")
                    print("###############################################")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_default_keys]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_default_keys]")
            return 0

        return 1

    def install_rsync(self):
        try:

            cmd = []

            count = 0

            while (1):

                command = 'yum -y install rsync'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    print("###############################################")
                    print("          Can not install rsync                ")
                    print("###############################################")
                    logging.InstallLog.writeToFile("Could not install rsync")
                    count = count + 1
                    print("Trying again, try number: " + str(count))
                    if count == 3:
                        break
                else:
                    print("###############################################")
                    print("          rsync Installed                      ")
                    print("###############################################")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_rsync]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_rsync]")
            return 0

        return 1

    def test_Requests(self):
        try:
            import requests
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
        except BaseException,msg:

            command = "pip uninstall --yes requests"
            subprocess.call(shlex.split(command))

            command = "pip install requests==2.2.1"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                print("###############################################")
                print("          Requests Test Ran                ")
                print("###############################################")
            else:
                print("###############################################")
                print("          Request Test Fail                ")
                print("###############################################")



            logging.InstallLog.writeToFile(str(msg) + " [test_Requests]")
            return 0




def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('publicip', help='Please enter public IP for your VPS or dedicated server.')
    args = parser.parse_args()

    cwd = os.getcwd()

    checks = preFlightsChecks("/usr/local/lsws/",args.publicip,"/usr/local",cwd,"/usr/local/CyberCP")


    checks.checkPythonVersion()
    checks.setup_account_cyberpanel()
    checks.yum_update()
    checks.installCyberPanelRepo()
    checks.enableEPELRepo()
    checks.install_pip()
    checks.install_python_dev()
    checks.install_gcc()
    checks.install_python_setup_tools()
    checks.install_django()
    checks.install_pexpect()
    checks.install_python_mysql_library()
    checks.install_wget()
    checks.install_gunicorn()
    checks.install_psutil()
    checks.setup_gunicorn()

    import installCyberPanel

    installCyberPanel.Main(cwd)
    checks.fix_selinux_issue()
    checks.install_psmisc()
    checks.install_postfix_davecot()
    checks.setup_email_Passwords(installCyberPanel.InstallCyberPanel.mysqlPassword)
    checks.setup_postfix_davecot_config()


    checks.install_unzip()
    checks.install_zip()
    checks.install_rsync()

    checks.downoad_and_install_raindloop()


    checks.download_install_phpmyadmin()

    checks.installFirewalld()

    checks.setupLSCPDDaemon()
    checks.install_python_requests()
    checks.install_default_keys()

    checks.test_Requests()
    checks.download_install_CyberPanel(installCyberPanel.InstallCyberPanel.mysqlPassword)
    checks.setup_cron()


if __name__ == "__main__":
    main()
