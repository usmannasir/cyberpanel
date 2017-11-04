import os.path
import pwd
import grp
import shutil
import logging
import CyberCPLogFileWriter as logging
import subprocess
import shlex


class virtualHostUtilities:

    Server_root = "/usr/local/lsws"


    @staticmethod
    def createDirectoryForVirtualHost(virtualHostName,administratorEmail, phpVersion):

        path = "/home/" + virtualHostName
        pathHTML = "/home/" + virtualHostName + "/public_html"
        pathLogs = "/home/" + virtualHostName + "/logs"
        confPath = virtualHostUtilities.Server_root + "/conf/vhosts/"+virtualHostName
        completePathToConfigFile = confPath +"/vhost.conf"


        try:
            os.makedirs(path)
        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to create directories for virtual host: "+ path+" [createDirectoryForVirtualHost]]")
            return 0

        try:
            os.makedirs(pathHTML)
        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to create  directories for virtual host "+ pathHTML+"  [createDirectoryForVirtualHost]]")
            return 0

        try:
            os.makedirs(pathLogs)
        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able create to directories for virtual host "+ pathLogs+"  [createDirectoryForVirtualHost]]")
            return 0

        try:
            os.makedirs(confPath)
        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able create to directories for virtual host "+ confPath+"  [createDirectoryForVirtualHost]]")
            return 0



        try:
            file = open(completePathToConfigFile, "w+")
        except IOError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectoryForVirtualHost]]")
            return 0

        #try:

            #command = "sudo chown -R nobody:cyberpanel " + completePathToConfigFile

            #cmd = shlex.split(command)

            #res = subprocess.call(cmd)


            #command = "sudo chown -R nobody:cyberpanel /home"

            #cmd = shlex.split(command)

            #res = subprocess.call(cmd)


        #except BaseException,msg:
        #    logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectoryForVirtualHost]]")


        if virtualHostUtilities.perHostVirtualConf(completePathToConfigFile,administratorEmail,phpVersion) == 1:
            return 1
        else:
            return 0


    @staticmethod
    def perHostVirtualConf(vhFile, administratorEmail, phpVersion):

        # General Configurations tab

        try:
            confFile = open(vhFile, "w+")

            docRoot = "docRoot                   $VH_ROOT/public_html" + "\n"
            vhDomain = "vhDomain                  $VH_NAME" + "\n"
            adminEmails = "adminEmails               " + administratorEmail + "\n"
            enableGzip = "enableGzip                1" + "\n"
            enableIpGeo = "enableIpGeo               1" + "\n" + "\n"

            confFile.writelines(docRoot)
            confFile.writelines(vhDomain)
            confFile.writelines(adminEmails)
            confFile.writelines(enableGzip)
            confFile.writelines(enableIpGeo)

            # Index file settings

            index = "index  {" + "\n"
            userServer = "  useServer               0" + "\n"
            indexFiles = "  indexFiles              index.php, index.html" + "\n"
            index_end = "}" + "\n" + "\n"

            confFile.writelines(index)
            confFile.writelines(userServer)
            confFile.writelines(indexFiles)
            confFile.writelines(index_end)

            # Error Log Settings


            error_log = "errorlog $VH_ROOT/logs/$VH_NAME.error_log {" + "\n"
            useServer = "  useServer               0" + "\n"
            logLevel = "  logLevel                ERROR" + "\n"
            rollingSize = "  rollingSize             10M" + "\n"
            error_log_end = "}" + "\n" + "\n"

            confFile.writelines(error_log)
            confFile.writelines(useServer)
            confFile.writelines(logLevel)
            confFile.writelines(rollingSize)
            confFile.writelines(error_log_end)

            # Access Log Settings

            access_Log = "accesslog $VH_ROOT/logs/$VH_NAME.access_log {" + "\n"
            useServer = "  useServer               0" + "\n"
            logFormat = '  logFormat               "%v %h %l %u %t \"%r\" %>s %b"' + "\n"
            logHeaders = "  logHeaders              5" + "\n"
            rollingSize = "  rollingSize             10M" + "\n"
            keepDays = "  keepDays                10"
            compressArchive = "  compressArchive         1" + "\n"
            access_Log_end = "}" + "\n" + "\n"

            confFile.writelines(access_Log)
            confFile.writelines(useServer)
            confFile.writelines(logFormat)
            confFile.writelines(logHeaders)
            confFile.writelines(rollingSize)
            confFile.writelines(keepDays)
            confFile.writelines(compressArchive)
            confFile.writelines(access_Log_end)

            # php settings

            scripthandler = "scripthandler  {" + "\n"
            add = ""
            php_end = "}" + "\n" + "\n"

            if phpVersion == "PHP 5.3":
                add = "  add                     lsapi:php53 php" + "\n"
            elif phpVersion == "PHP 5.4":
                add = "  add                     lsapi:php54 php" + "\n"
            elif phpVersion == "PHP 5.5":
                add = "  add                     lsapi:php55 php" + "\n"
            elif phpVersion == "PHP 5.6":
                add = "  add                     lsapi:php56 php" + "\n"
            elif phpVersion == "PHP 7.0":
                add = "  add                     lsapi:php70 php" + "\n"
            elif phpVersion == "PHP 7.1":
                add = "  add                     lsapi:php71 php" + "\n"

            confFile.writelines(scripthandler)
            confFile.writelines(add)
            confFile.writelines(php_end)

            confFile.close()

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with per host config file [perHostVirtualConf]]")
            return 0
        return 1



    @staticmethod
    def createConfigInMainVirtualHostFile(virtualHostName):

        #virtualhost project.cyberpersons.com {
        #vhRoot / home / project.cyberpersons.com
        #configFile      $SERVER_ROOT / conf / vhosts /$VH_NAME / vhconf.conf
        #allowSymbolLink 1
        #enableScript 1
        #restrained 1
        #}

        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

            spaceonback = "  "
            space = "                  "
            space2 = "              "
            space3 = "         "
            space4 = "            "
            space5 = "              "


            firstLine = "virtualHost " + virtualHostName + " {" + "\n"
            secondLine = spaceonback + "vhRoot"+ space +"/home/" + "$VH_NAME" + "\n"
            thirdLine = spaceonback + "configFile" + space2 + "$SERVER_ROOT" +"/conf/" +"vhosts/" + "$VH_NAME" +"/vhost.conf" + "\n"
            forthLine = spaceonback + "allowSymbolLink" + space3 + "1"  + "\n"
            fifthLine = spaceonback + "enableScript" + space4 + "1"  + "\n"
            sixthLine = spaceonback + "restrained" + space5 + "1"  + "\n"
            seventhLine = "}"  + "\n"
            map = "  map                     "+virtualHostName+" "+virtualHostName+ "\n"


            checker = 1
            mapchecker = 1

            for items in data:
                if ((items.find("virtualHost") > -1 or items.find("virtualhost") > -1)  and checker == 1):
                    writeDataToFile.writelines(firstLine)
                    writeDataToFile.writelines(secondLine)
                    writeDataToFile.writelines(thirdLine)
                    writeDataToFile.writelines(forthLine)
                    writeDataToFile.writelines(fifthLine)
                    writeDataToFile.writelines(sixthLine)
                    writeDataToFile.writelines(seventhLine)
                    writeDataToFile.writelines("\n")
                    writeDataToFile.writelines(items)
                    checker = 0
                elif((items.find("listener Default{") > -1 or items.find("Default {")>-1) and mapchecker == 1):
                    writeDataToFile.writelines(items)
                    writeDataToFile.writelines(map)
                    mapchecker=0

                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [createConfigInMainVirtualHostFile]]")
            return 0
        return 1

    @staticmethod
    def createDirectoryForDomain(masterDomain, domain, phpVersion, path, administratorEmail):

        confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domain
        completePathToConfigFile = confPath + "/vhost.conf"

        try:
            os.makedirs(path)
        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [Not able create to directories for virtual host [createDirectoryForDomain]]")

        try:
            os.makedirs(confPath)
        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [Not able create to directories for virtual host [createDirectoryForDomain]]")

        try:
            file = open(completePathToConfigFile, "w+")
        except IOError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectoryForDomain]]")
            return 0

        #try:
         #   uid = pwd.getpwnam("lsadm").pw_uid
        #    gid = grp.getgrnam("lsadm").gr_gid
         #   os.chown(confPath, uid, gid)
        #    os.chown(completePathToConfigFile, uid, gid)

         #   uid = pwd.getpwnam("nobody").pw_uid
         #   gid = grp.getgrnam("nobody").gr_gid

         #   os.chown("/home", uid, gid)
         #   os.chown(path, uid, gid)

        #except BaseException, msg:
            #logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectoryForDomain]]")

        if virtualHostUtilities.perHostDomainConf(path, masterDomain, domain, completePathToConfigFile,
                                                  administratorEmail, phpVersion) == 1:
            return 1
        else:
            return 0

    @staticmethod
    def perHostDomainConf(path, masterDomain, domain, vhFile, administratorEmail, phpVersion):

        # General Configurations tab

        # virtualhost project.cyberpersons.com {
        # vhRoot / home / project.cyberpersons.com
        # configFile      $SERVER_ROOT / conf / vhosts /$VH_NAME / vhconf.conf
        # allowSymbolLink 1
        # enableScript 1
        # restrained 1
        # }

        try:
            confFile = open(vhFile, "w+")

            docRoot = "docRoot                   " + path + "\n"
            vhDomain = "vhDomain                  $VH_NAME" + "\n"
            adminEmails = "adminEmails               " + administratorEmail + "\n"
            enableGzip = "enableGzip                1" + "\n"
            enableIpGeo = "enableIpGeo               1" + "\n" + "\n"

            confFile.writelines(docRoot)
            confFile.writelines(vhDomain)
            confFile.writelines(adminEmails)
            confFile.writelines(enableGzip)
            confFile.writelines(enableIpGeo)

            # Index file settings

            index = "index  {" + "\n"
            userServer = "  useServer               0" + "\n"
            indexFiles = "  indexFiles              index.php, index.html" + "\n"
            index_end = "}" + "\n" + "\n"

            confFile.writelines(index)
            confFile.writelines(userServer)
            confFile.writelines(indexFiles)
            confFile.writelines(index_end)

            # Error Log Settings


            error_log = "errorlog $VH_ROOT/logs/" + masterDomain + ".error_log {" + "\n"
            useServer = "  useServer               0" + "\n"
            logLevel = "  logLevel                ERROR" + "\n"
            rollingSize = "  rollingSize             10M" + "\n"
            error_log_end = "}" + "\n" + "\n"

            confFile.writelines(error_log)
            confFile.writelines(useServer)
            confFile.writelines(logLevel)
            confFile.writelines(rollingSize)
            confFile.writelines(error_log_end)

            # Access Log Settings

            access_Log = "accesslog $VH_ROOT/logs/" + masterDomain + ".access_log {" + "\n"
            useServer = "  useServer               0" + "\n"
            logFormat = '  logFormat               "%v %h %l %u %t \"%r\" %>s %b"' + "\n"
            logHeaders = "  logHeaders              5" + "\n"
            rollingSize = "  rollingSize             10M" + "\n"
            keepDays = "  keepDays                10"
            compressArchive = "  compressArchive         1" + "\n"
            access_Log_end = "}" + "\n" + "\n"

            confFile.writelines(access_Log)
            confFile.writelines(useServer)
            confFile.writelines(logFormat)
            confFile.writelines(logHeaders)
            confFile.writelines(rollingSize)
            confFile.writelines(keepDays)
            confFile.writelines(compressArchive)
            confFile.writelines(access_Log_end)

            # php settings

            scripthandler = "scripthandler  {" + "\n"
            add = ""
            php_end = "}" + "\n" + "\n"

            if phpVersion == "PHP 5.3":
                add = "  add                     lsapi:php53 php" + "\n"
            elif phpVersion == "PHP 5.4":
                add = "  add                     lsapi:php54 php" + "\n"
            elif phpVersion == "PHP 5.5":
                add = "  add                     lsapi:php55 php" + "\n"
            elif phpVersion == "PHP 5.6":
                add = "  add                     lsapi:php56 php" + "\n"
            elif phpVersion == "PHP 7.0":
                add = "  add                     lsapi:php70 php" + "\n"
            elif phpVersion == "PHP 7.1":
                add = "  add                     lsapi:php71 php" + "\n"

            confFile.writelines(scripthandler)
            confFile.writelines(add)
            confFile.writelines(php_end)

            confFile.close()

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with per host config file [perHostDomainConf]]")
            return 0
        return 1

    @staticmethod
    def createConfigInMainDomainHostFile(domain,masterDomain):

        # virtualhost project.cyberpersons.com {
        # vhRoot / home / project.cyberpersons.com
        # configFile      $SERVER_ROOT / conf / vhosts /$VH_NAME / vhconf.conf
        # allowSymbolLink 1
        # enableScript 1
        # restrained 1
        # }

        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

            spaceonback = "  "
            space = "                  "
            space2 = "              "
            space3 = "         "
            space4 = "            "
            space5 = "              "

            firstLine = "virtualHost " + domain + " {" + "\n"
            secondLine = spaceonback + "vhRoot" + space + "/home/" + masterDomain + "\n"
            thirdLine = spaceonback + "configFile" + space2 + "$SERVER_ROOT" + "/conf/" + "vhosts/" + "$VH_NAME" + "/vhost.conf" + "\n"
            forthLine = spaceonback + "allowSymbolLink" + space3 + "1" + "\n"
            fifthLine = spaceonback + "enableScript" + space4 + "1" + "\n"
            sixthLine = spaceonback + "restrained" + space5 + "1" + "\n"
            seventhLine = "}" + "\n"
            map = "  map                     " + domain + " " + domain + "\n"

            checker = 1
            mapchecker = 1

            for items in data:
                if ((items.find("virtualHost") > -1 or items.find("virtualhost") > -1) and checker == 1):
                    writeDataToFile.writelines(firstLine)
                    writeDataToFile.writelines(secondLine)
                    writeDataToFile.writelines(thirdLine)
                    writeDataToFile.writelines(forthLine)
                    writeDataToFile.writelines(fifthLine)
                    writeDataToFile.writelines(sixthLine)
                    writeDataToFile.writelines(seventhLine)
                    writeDataToFile.writelines("\n")
                    writeDataToFile.writelines(items)
                    checker = 0
                elif ((items.find("listener Default{") > -1 or items.find("Default {") > -1) and mapchecker == 1):
                    writeDataToFile.writelines(items)
                    writeDataToFile.writelines(map)
                    mapchecker = 0

                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with main config file [createConfigInMainVirtualHostFile]]")
            return 0
        return 1

    @staticmethod
    def deleteVirtualHostConfigurations(virtualHostName,numberOfSites):

        virtualHostPath = "/home/" + virtualHostName
        try:
            shutil.rmtree(virtualHostPath)
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to remove virtual host directory from /home continuing..]")

        try:
            confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + virtualHostName
            shutil.rmtree(confPath)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to remove virtual host configuration directory from /conf ]")

        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()

            writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

            check = 1
            sslCheck=1

            for items in data:

                if numberOfSites == 1:

                    if (items.find(virtualHostName) > -1 and items.find("  map                     " + virtualHostName) > -1):
                        continue
                    if (items.find(virtualHostName) > -1 and (items.find("virtualHost") > -1 or items.find("virtualhost") > -1)):
                        check = 0
                    if (items.find("listener SSL {") > -1):
                            sslCheck = 0
                    if (check == 1 and sslCheck == 1):
                        writeDataToFile.writelines(items)
                    if (items.find("}") > -1 and (check == 0 or sslCheck == 0)):
                        check = 1
                        sslCheck = 1
                else:
                    if (items.find(virtualHostName) > -1 and items.find("  map                     "+virtualHostName) > -1):
                        continue
                    if (items.find(virtualHostName) > -1 and (items.find("virtualHost") > -1 or items.find("virtualhost") > -1)):
                        check = 0
                    if(check==1):
                        writeDataToFile.writelines(items)
                    if(items.find("}")>-1 and check == 0):
                        check = 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to remove virtual host configuration main configuration file]")
            return 0

        return 1


    @staticmethod
    def checkIfVirtualHostExists(virtualHostName):
        if os.path.exists("/home/"+virtualHostName):
            return 1

    @staticmethod
    def changePHP(vhFile,phpVersion):

        # General Configurations tab

        try:
            data = open(vhFile, "r").readlines()

            if phpVersion == "PHP 5.3":
                finalphp = 53
            elif phpVersion == "PHP 5.4":
                finalphp = 54
            elif phpVersion == "PHP 5.5":
                finalphp = 55
            elif phpVersion == "PHP 5.6":
                finalphp = 56
            elif phpVersion == "PHP 7.0":
                finalphp = 70
            elif phpVersion == "PHP 7.1":
                finalphp = 71

            writeDataToFile = open(vhFile,"w")

            add = "  add                     lsapi:php"+str(finalphp)+" php" + "\n"

            for items in data:
                if items.find("add") > -1 and items.find("lsapi:") > -1 and items.find("php") > -1:
                    writeDataToFile.writelines(add)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with per host config file [changePHP]]")
            return 0
        return 1


    @staticmethod
    def getDiskUsage(path, totalAllowed):
        try:

            totalUsageInMB = subprocess.check_output(["du", "-hs",path,"--block-size=1M"]).split()[0]

            percentage = float(100)/float(totalAllowed)

            percentage = float(percentage) *  float(totalUsageInMB)

            data = [int(totalUsageInMB),int(percentage)]
            return data
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg)+ " [getDiskUsage]")
            return [int(0), int(0)]

    @staticmethod
    def addRewriteRules(virtualHostName):

        try:
            path = virtualHostUtilities.Server_root + "/conf/vhosts/" + virtualHostName + "/vhost.conf"

            data = open(path, "r").readlines()

            dataToWritten = "rewriteFile           /home/"+virtualHostName+"/public_html/.htaccess"+"\n"

            ### Data if re-writes are not already enabled

            rewrite = "rewrite  {\n"
            enables = "  enable                  1\n"
            rules ="  rules                   <<<END_rules\n"
            endRules = "  END_rules\n"
            end = "}\n\n"



            if virtualHostUtilities.checkIfRewriteEnabled(data) == 1:
                pass
            else:
                writeDataToFile = open(path, "a")

                writeDataToFile.writelines("\n")
                writeDataToFile.writelines("\n")
                writeDataToFile.writelines(rewrite)
                writeDataToFile.writelines(enables)
                writeDataToFile.writelines(rules)
                writeDataToFile.writelines(dataToWritten)
                writeDataToFile.writelines(endRules)
                writeDataToFile.writelines(end)

                writeDataToFile.close()


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with per host config file [changePHP]]")
            return 0

        return 1

    @staticmethod
    def checkIfRewriteEnabled(data):
        try:
            for items in data:
                if items.find(".htaccess") > -1:
                    return 1
            return 0

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with per host config file [checkIfRewriteEnabled]]")
            return 0
        return 1

    @staticmethod
    def suspendVirtualHost(virtualHostName):
        try:

            confPath = virtualHostUtilities.Server_root + "/conf/vhosts/"+virtualHostName

            shutil.move(confPath,confPath+"-suspended")

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [suspendVirtualHost]")
            return 0
        return 1

    @staticmethod
    def UnsuspendVirtualHost(virtualHostName):
        try:

            confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + virtualHostName

            shutil.move(confPath + "-suspended",confPath)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [UnsuspendVirtualHost]")
            return 0
        return 1

    @staticmethod
    def permissionControl(path):
        try:
            command = 'sudo chown -R  cyberpanel:cyberpanel '+path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def leaveControl(path):
        try:
            command = 'sudo chown -R  root:root ' + path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))