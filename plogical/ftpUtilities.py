import mysqlUtilities as sql
import subprocess
import CyberCPLogFileWriter as logging
import os
import shlex


class FTPUtilities:


    # This function will only install FTP
    @staticmethod
    def installProFTPD():
        try:
            cmd = []


            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("proftpd-mysql")
            res = subprocess.call(cmd)
            if res == 1:
                print("###############################################")
                print("         Could not install ProFTPD              ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          ProFTPD Installed                     ")
                print("###############################################")
        except OSError,msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installProFTPD]")
            return 0
        except ValueError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installProFTPD]")
            return 0

        return 1



    @staticmethod
    def createFTPDataBaseinMariaDB(username,password):
        try:

            #Create DB
            #sql.mysqlUtilities.createDatabase("1qaz@9xvps", "ftp", username, password)

            #Add group
            cmd = []

            cmd.append("groupadd")
            cmd.append("-g")
            cmd.append("2001")
            cmd.append("ftpgroup")

            res = subprocess.call(cmd)
            if res == 1:
                print "Group adding failed"
            else:
                print "Group added"

            #Add user to group

            cmd = []

            cmd.append("useradd")
            cmd.append("-u")
            cmd.append("2001")
            cmd.append("-s")
            cmd.append("/bin/false")
            cmd.append("-d")
            cmd.append("/bin/null")
            cmd.append("-c")
            cmd.append("\"proftpd user\"")
            cmd.append("-g")
            cmd.append("ftpgroup")
            cmd.append("ftpuser")

            res = subprocess.call(cmd)
            if res == 1:
                print "User adding failed"
            else:
                print "User added"

            #query = "CREATE TABLE ftp_ftpuser (id int(10) unsigned NOT NULL auto_increment,userid varchar(32) NOT NULL default '',passwd varchar(32) NOT NULL default '',uid smallint(6) NOT NULL default '2001',gid smallint(6) NOT NULL default '2001',homedir varchar(255) NOT NULL default '',shell varchar(16) NOT NULL default '/sbin/nologin',count int(11) NOT NULL default '0',accessed datetime NOT NULL default '0000-00-00 00:00:00',modified datetime NOT NULL default '0000-00-00 00:00:00',PRIMARY KEY (id),UNIQUE KEY userid (userid)) ENGINE=MyISAM COMMENT='ProFTP user table';"
            #sql.mysqlUtilities.SendQuery(username,password,"ftp", query)

            #query = "CREATE TABLE ftpgroup (groupname varchar(16) NOT NULL default '',gid smallint(6) NOT NULL default '2001',members varchar(16) NOT NULL default '',KEY groupname (groupname)) ENGINE=MyISAM COMMENT='ProFTP group table';"
            #sql.mysqlUtilities.SendQuery(username, password, "ftp", query)

            #query = "INSERT INTO ftpgroup (groupname, gid, members) VALUES ('ftpgroup', '2001', 'ftp_ftpuser');"
            #sql.mysqlUtilities.SendQuery(username, password, "ftp", query)

            # File Write
            lines = open("/etc/proftpd.conf").readlines()
            data = open("/etc/proftpd.conf", "w")

            line1 = "\nLoadModule mod_sql.c\n"
            line2 = "LoadModule mod_sql_mysql.c\n\n"

            line3 = "SQLAuthTypes            Plaintext Crypt\n"
            line4 = "SQLAuthenticate         users groups\n\n"

            line5 = "SQLConnectInfo  cybercp@localhost "+username+" "+password+"\n"
            line6 = "SQLUserInfo     ftp_ftp_ftpuser userid passwd uid gid homedir shell\n"
            line7 = "SQLGroupInfo    ftp_ftpgroup groupname gid members\n\n"

            line8 = "SQLLog PASS updatecount\n"
            line9 = "SQLNamedQuery updatecount UPDATE \"count=count+1, accessed=now() WHERE userid='%u'\" ftp_ftpuser\n\n"

            line10 = "SQLLog  STOR,DELE modified\n"
            line11 = "SQLNamedQuery modified UPDATE \"modified=now() WHERE userid='%u'\" ftp_ftpuser"

            Auth0 = "\n#AuthPAMConfig\n"
            Auth1 = "#AuthOrder\n"
            for items in lines:
                if ((items.find("AuthPAMConfig") > -1)):
                    data.writelines(Auth0)
                    continue

                if ((items.find("AuthOrder") > -1)):
                    data.writelines(Auth1)
                    continue

                data.writelines(items)


            data.writelines(line1)
            data.writelines(line2)
            data.writelines(line3)
            data.writelines(line4)
            data.writelines(line5)
            data.writelines(line6)
            data.writelines(line7)
            data.writelines(line8)
            data.writelines(line9)
            data.writelines(line10)
            data.writelines(line11)

            data.close()

            #File Write End

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with proftpd config file [createFTPDataBaseinMariaDB]]")
            return 0
        return 1

    @staticmethod
    def createNewFTPAccount(udb,upass,username,password,path):
        try:

            cmd = []
            cmd.append("chown")
            cmd.append("-R")
            cmd.append("ftpuser:2001")
            cmd.append(path)

            res = subprocess.call(cmd)
            if res == 1:
                print "Permissions not changed."
            else:
                print "User permissions setted."

            query = "INSERT INTO ftp_ftpuser (userid,passwd,homedir) VALUES ('" + username + "'" +","+"'"+password+"'"+","+"'"+path+"'"+");"
            print query
            sql.mysqlUtilities.SendQuery(udb,upass, "ftp", query)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [createNewFTPAccount]")
            return 0

        return 1


    @staticmethod
    def changePermissions(directory):

        try:

            command = "sudo chmod -R 775 " + directory

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                print "Permissions not changed."
                return 0
            else:
                print "User permissions setted."



            command = "sudo chown -R nobody:cyberpanel " + directory

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                return 0
            else:
                return 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [createNewFTPAccount]")
            return 0

        return 1

