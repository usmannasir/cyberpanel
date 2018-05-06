import os.path
import shutil
import CyberCPLogFileWriter as logging
import subprocess
import argparse
import shlex
import installUtilities
from random import randint
import sslUtilities
from os.path import join
from os import listdir, rmdir
from shutil import move
import randomPassword as randomPassword
from mailUtilities import mailUtilities


class virtualHostUtilities:

    Server_root = "/usr/local/lsws"
    cyberPanel = "/usr/local/CyberCP"

    @staticmethod
    def createDirectoryForVirtualHost(virtualHostName,administratorEmail,virtualHostUser, phpVersion):

        path = "/home/" + virtualHostName
        pathHTML = "/home/" + virtualHostName + "/public_html"
        pathLogs = "/home/" + virtualHostName + "/logs"
        confPath = virtualHostUtilities.Server_root + "/conf/vhosts/"+virtualHostName
        completePathToConfigFile = confPath +"/vhost.conf"

        FNULL = open(os.devnull, 'w')

        ## adding user

        command = "adduser "+virtualHostUser + " -M -d " + path

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        command = "groupadd " + virtualHostUser

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        command = "usermod -a -G "+virtualHostUser +" "+virtualHostUser

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        ## adding user ends


        try:
            os.makedirs(path)

            command = "chown "+virtualHostUser+":"+virtualHostUser+" " + path
            cmd = shlex.split(command)
            subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [27 Not able create to directories for virtual host [createDirectoryForVirtualHost]]")
            return [0,"[27 Not able to directories for virtual host [createDirectoryForVirtualHost]]"]

        try:
            os.makedirs(pathHTML)

            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + pathHTML
            cmd = shlex.split(command)
            subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [33 Not able to directories for virtual host [createDirectoryForVirtualHost]]")
            return [0, "[33 Not able to directories for virtual host [createDirectoryForVirtualHost]]"]

        try:
            os.makedirs(pathLogs)

            command = "chown " + "nobody" + ":" + "nobody" + " " + pathLogs
            cmd = shlex.split(command)
            subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

            command = "chmod -R 666 " + pathLogs
            cmd = shlex.split(command)
            subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [39 Not able to directories for virtual host [createDirectoryForVirtualHost]]")
            return [0, "[39 Not able to directories for virtual host [createDirectoryForVirtualHost]]"]

        try:
            ## For configuration files permissions will be changed later globally.
            os.makedirs(confPath)
        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [45 Not able to directories for virtual host [createDirectoryForVirtualHost]]")
            return [0, "[45 Not able to directories for virtual host [createDirectoryForVirtualHost]]"]



        try:
            ## For configuration files permissions will be changed later globally.
            file = open(completePathToConfigFile, "w+")

            command = "chown " + "lsadm" + ":" + "lsadm" + " " + completePathToConfigFile
            cmd = shlex.split(command)
            subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        except IOError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectoryForVirtualHost]]")
            return [0, "[45 Not able to directories for virtual host [createDirectoryForVirtualHost]]"]


        if virtualHostUtilities.perHostVirtualConf(completePathToConfigFile,administratorEmail,virtualHostUser,phpVersion) == 1:
            command = "chmod -R 766 " + pathHTML
            #subprocess.call(shlex.split(command))
            return [1,"None"]
        else:
            return [0,"[61 Not able to create per host virtual configurations [perHostVirtualConf]"]


    @staticmethod
    def perHostVirtualConf(vhFile, administratorEmail,virtualHostUser, phpVersion):

        # General Configurations tab

        try:
            confFile = open(vhFile, "w+")

            docRoot = "docRoot                   $VH_ROOT/public_html" + "\n"
            vhDomain = "vhDomain                  $VH_NAME" + "\n"
            vhAliases = "vhAliases                 www.$VH_NAME"+ "\n"
            adminEmails = "adminEmails               " + administratorEmail + "\n"
            enableGzip = "enableGzip                1" + "\n"
            enableIpGeo = "enableIpGeo               1" + "\n" + "\n"

            confFile.writelines(docRoot)
            confFile.writelines(vhDomain)
            confFile.writelines(vhAliases)
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
            add = "  add                     lsapi:"+virtualHostUser+" php" + "\n"
            php_end = "}" + "\n" + "\n"

            confFile.writelines(scripthandler)
            confFile.writelines(add)
            confFile.writelines(php_end)


            ## external app

            if phpVersion == "PHP 5.3":
                php = "53"
            elif phpVersion == "PHP 5.4":
                php = "55"
            elif phpVersion == "PHP 5.5":
                php = "55"
            elif phpVersion == "PHP 5.6":
                php = "56"
            elif phpVersion == "PHP 7.0":
                php = "70"
            elif phpVersion == "PHP 7.1":
                php = "71"
            elif phpVersion == "PHP 7.2":
                php = "72"

            extprocessor = "extprocessor "+virtualHostUser+" {\n"
            type = "  type                    lsapi\n"
            address = "  address                 UDS://tmp/lshttpd/"+virtualHostUser+".sock\n"
            maxConns = "  maxConns                10\n"
            env = "  env                     LSAPI_CHILDREN=10\n"
            initTimeout = "  initTimeout             60\n"
            retryTimeout = "  retryTimeout            0\n"
            persistConn = "  persistConn             1\n"
            persistConnTimeout = "  pcKeepAliveTimeout      1\n"
            respBuffer = "  respBuffer              0\n"
            autoStart = "  autoStart               1\n"
            path = "  path                    /usr/local/lsws/lsphp"+php+"/bin/lsphp\n"
            extUser = "  extUser                 " + virtualHostUser + "\n"
            extGroup = "  extGroup                 " + virtualHostUser + "\n"
            memSoftLimit = "  memSoftLimit            2047M\n"
            memHardLimit = "  memHardLimit            2047M\n"
            procSoftLimit = "  procSoftLimit           400\n"
            procHardLimit = "  procHardLimit           500\n"
            extprocessorEnd = "}\n"

            confFile.writelines(extprocessor)
            confFile.writelines(type)
            confFile.writelines(address)
            confFile.writelines(maxConns)
            confFile.writelines(env)
            confFile.writelines(initTimeout)
            confFile.writelines(retryTimeout)
            confFile.writelines(persistConn)
            confFile.writelines(persistConnTimeout)
            confFile.writelines(respBuffer)
            confFile.writelines(autoStart)
            confFile.writelines(path)
            confFile.writelines(extUser)
            confFile.writelines(extGroup)
            confFile.writelines(memSoftLimit)
            confFile.writelines(memHardLimit)
            confFile.writelines(procSoftLimit)
            confFile.writelines(procHardLimit)
            confFile.writelines(extprocessorEnd)

            ## File Manager defination

            context = "context /.filemanager {\n"
            type = "  type                    NULL\n"
            location = "  location                /usr/local/lsws/Example/html/FileManager\n"
            allowBrowse = "  allowBrowse             1\n"
            autoIndex = "  autoIndex               1\n\n"

            accessControl = "  accessControl  {\n"
            allow = "    allow                 127.0.0.1, localhost\n"
            deny = "    deny                  0.0.0.0/0\n"
            accessControlEnds = "  }\n"


            defaultCharSet = "  addDefaultCharset       off\n"
            contextEnds = "}\n"

            confFile.writelines(context)
            confFile.writelines(type)
            confFile.writelines(location)
            confFile.writelines(allowBrowse)
            confFile.writelines(autoIndex)
            confFile.writelines(accessControl)
            confFile.writelines(allow)
            confFile.writelines(deny)
            confFile.writelines(accessControlEnds)
            confFile.writelines(defaultCharSet)
            confFile.writelines(contextEnds)

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
            return [1,"None"]

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]")
            return [0,"223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]


    @staticmethod
    def createDirectoryForDomain(masterDomain, domain, phpVersion, path, administratorEmail,virtualHostUser):

        FNULL = open(os.devnull, 'w')

        confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domain
        completePathToConfigFile = confPath + "/vhost.conf"

        try:
            os.makedirs(path)
            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path
            cmd = shlex.split(command)
            subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)
        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "329 [Not able to create directories for virtual host [createDirectoryForDomain]]")

        try:
            ## For configuration files permissions will be changed later globally.
            os.makedirs(confPath)
        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "335 [Not able to create directories for virtual host [createDirectoryForDomain]]")
            return [0, "[344 Not able to directories for virtual host [createDirectoryForDomain]]"]

        try:
            ## For configuration files permissions will be changed later globally.
            file = open(completePathToConfigFile, "w+")
        except IOError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectoryForDomain]]")
            return [0, "[351 Not able to directories for virtual host [createDirectoryForDomain]]"]


        if virtualHostUtilities.perHostDomainConf(path, masterDomain, completePathToConfigFile,
                                                  administratorEmail, phpVersion,virtualHostUser) == 1:
            return [1,"None"]
        else:
            return [0, "[359 Not able to create per host virtual configurations [perHostVirtualConf]"]

    @staticmethod
    def perHostDomainConf(path, masterDomain, vhFile, administratorEmail, phpVersion,virtualHostUser):

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
            vhAliases = "vhAliases                 www.$VH_NAME" + "\n"
            adminEmails = "adminEmails               " + administratorEmail + "\n"
            enableGzip = "enableGzip                1" + "\n"
            enableIpGeo = "enableIpGeo               1" + "\n" + "\n"

            confFile.writelines(docRoot)
            confFile.writelines(vhDomain)
            confFile.writelines(vhAliases)
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

            sockRandomPath = str(randint(1000, 9999))

            scripthandler = "scripthandler  {" + "\n"
            add = "  add                     lsapi:" + virtualHostUser+sockRandomPath + " php" + "\n"
            php_end = "}" + "\n" + "\n"

            confFile.writelines(scripthandler)
            confFile.writelines(add)
            confFile.writelines(php_end)

            ## external app

            if phpVersion == "PHP 5.3":
                php = "53"
            elif phpVersion == "PHP 5.4":
                php = "55"
            elif phpVersion == "PHP 5.5":
                php = "55"
            elif phpVersion == "PHP 5.6":
                php = "56"
            elif phpVersion == "PHP 7.0":
                php = "70"
            elif phpVersion == "PHP 7.1":
                php = "71"
            elif phpVersion == "PHP 7.2":
                php = "72"


            extprocessor = "extprocessor " + virtualHostUser+sockRandomPath + " {\n"
            type = "  type                    lsapi\n"
            address = "  address                 UDS://tmp/lshttpd/" + virtualHostUser+sockRandomPath + ".sock\n"
            maxConns = "  maxConns                10\n"
            env = "  env                     LSAPI_CHILDREN=10\n"
            initTimeout = "  initTimeout             60\n"
            retryTimeout = "  retryTimeout            0\n"
            persistConn = "  persistConn             1\n"
            persistConnTimeout = "  pcKeepAliveTimeout      1\n"
            respBuffer = "  respBuffer              0\n"
            autoStart = "  autoStart               1\n"
            path = "  path                    /usr/local/lsws/lsphp" + php + "/bin/lsphp\n"
            extUser = "  extUser                 " + virtualHostUser + "\n"
            extGroup = "  extGroup                 " + virtualHostUser + "\n"
            memSoftLimit = "  memSoftLimit            2047M\n"
            memHardLimit = "  memHardLimit            2047M\n"
            procSoftLimit = "  procSoftLimit           400\n"
            procHardLimit = "  procHardLimit           500\n"
            extprocessorEnd = "}\n"

            confFile.writelines(extprocessor)
            confFile.writelines(type)
            confFile.writelines(address)
            confFile.writelines(maxConns)
            confFile.writelines(env)
            confFile.writelines(initTimeout)
            confFile.writelines(retryTimeout)
            confFile.writelines(persistConn)
            confFile.writelines(persistConnTimeout)
            confFile.writelines(respBuffer)
            confFile.writelines(autoStart)
            confFile.writelines(path)
            confFile.writelines(extUser)
            confFile.writelines(extGroup)
            confFile.writelines(memSoftLimit)
            confFile.writelines(memHardLimit)
            confFile.writelines(procSoftLimit)
            confFile.writelines(procHardLimit)
            confFile.writelines(extprocessorEnd)

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

            return [1,"None"]

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with main config file [createConfigInMainVirtualHostFile]]")
            return [0, "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]

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
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
            return 0

        return 1


    @staticmethod
    def checkIfVirtualHostExists(virtualHostName):
        if os.path.exists("/home/"+virtualHostName):
            return 1
        return 0

    @staticmethod
    def changePHP(vhFile,phpVersion):

        # General Configurations tab

        finalphp = 0

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
            elif phpVersion == "PHP 7.2":
                finalphp = 72

            writeDataToFile = open(vhFile,"w")

            sockRandomPath = str(randint(1000, 9999))

            address = "  address                 UDS://tmp/lshttpd/" + sockRandomPath + ".sock\n"
            path = "  path                    /usr/local/lsws/lsphp" + str(finalphp) + "/bin/lsphp\n"

            for items in data:
                if items.find("/usr/local/lsws/lsphp") > -1 and items.find("path") > -1:
                    writeDataToFile.writelines(path)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            installUtilities.installUtilities.reStartLiteSpeed()

            print "1,None"

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with per host config file [changePHP]]")
            return [0,str(msg) + " [IO Error with per host config file [changePHP]]"]

    @staticmethod
    def getDiskUsage(path, totalAllowed):
        try:

            totalUsageInMB = subprocess.check_output(["sudo","du", "-hs",path,"--block-size=1M"]).split()[0]

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

            command = "sudo mv " + confPath + " " + confPath+"-suspended"
            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [suspendVirtualHost]")
            return 0
        return 1

    @staticmethod
    def UnsuspendVirtualHost(virtualHostName):
        try:

            confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + virtualHostName

            command = "sudo mv " + confPath + "-suspended" + " " + confPath
            subprocess.call(shlex.split(command))

            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + confPath
            cmd = shlex.split(command)
            subprocess.call(cmd)


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [UnsuspendVirtualHost]")
            return 0
        return 1

    @staticmethod
    def findDomainBW(domainName,totalAllowed):
        try:
            path = "/home/"+domainName+"/logs/"+domainName+".access_log"

            if not os.path.exists("/home/"+domainName+"/logs"):
                print "0,0"

            bwmeta = "/home/" + domainName + "/logs/bwmeta"

            if not os.path.exists(path):
                print "0,0"



            if os.path.exists(bwmeta):
                try:
                    data = open(bwmeta).readlines()
                    currentUsed = int(data[0].strip("\n"))

                    inMB = int(float(currentUsed)/(1024.0*1024.0))

                    percentage = float(100) / float(totalAllowed)

                    percentage = float(percentage) * float(inMB)
                except:
                    print "0,0"

                if percentage > 100.0:
                    percentage = 100

                print str(inMB)+","+str(percentage)
            else:
                print "0,0"


        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            print "0,0"
        except ValueError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            print "0,0"

    @staticmethod
    def permissionControl(path):
        try:
            command = 'sudo chown -R  cyberpanel:cyberpanel ' + path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def leaveControl(path):
        try:
            command = 'sudo chown -R  root:root ' + path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))


def createVirtualHost(virtualHostName,administratorEmail,phpVersion,virtualHostUser,numberOfSites,ssl,sslPath,dkimCheck):
    try:
        if virtualHostUtilities.checkIfVirtualHostExists(virtualHostName) == 1:
            print "0,Virtual Host Directory already exists!"
            return

        if dkimCheck == 1:
            if mailUtilities.checkIfDKIMInstalled() == 0:
                print "0, OpenDKIM is not installed, install OpenDKIM from DKIM Manager."
                return

            result = mailUtilities.setupDKIM(virtualHostName)
            if result[0] == 0:
                raise BaseException(result[1])

        FNULL = open(os.devnull, 'w')

        retValues = virtualHostUtilities.createDirectoryForVirtualHost(virtualHostName, administratorEmail,virtualHostUser, phpVersion)
        if retValues[0] == 0:
            virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostName, numberOfSites)
            print "0,"+str(retValues[1])
            return

        retValues = virtualHostUtilities.createConfigInMainVirtualHostFile(virtualHostName)
        if retValues[0] == 0:
            virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostName, numberOfSites)
            print "0,"+str(retValues[1])

        if ssl == 1:
            installUtilities.installUtilities.reStartLiteSpeed()
            retValues = sslUtilities.issueSSLForDomain(virtualHostName, administratorEmail, sslPath)
            if retValues[0] == 0:
                virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostName, numberOfSites)
                print "0,"+str(retValues[1])
                return

        installUtilities.installUtilities.reStartLiteSpeed()

        shutil.copy("/usr/local/CyberCP/index.html","/home/" + virtualHostName + "/public_html/index.html")

        command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + "/home/" + virtualHostName + "/public_html/index.html"
        cmd = shlex.split(command)
        subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        vhostPath = virtualHostUtilities.Server_root + "/conf/vhosts"

        command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
        cmd = shlex.split(command)
        subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)


        print "1,None"


    except BaseException,msg:
        virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostName, numberOfSites)
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [createVirtualHost]")
        print "0,"+str(msg)

def createDomain(masterDomain, virtualHostName, phpVersion, path,administratorEmail,virtualHostUser,restart,numberOfSites,ssl, dkimCheck):
    try:
        if virtualHostUtilities.checkIfVirtualHostExists(virtualHostName) == 1:
            print "0,Virtual Host Directory already exists!"
            return


        if dkimCheck == 1:
            if mailUtilities.checkIfDKIMInstalled() == 0:
                print "0, OpenDKIM is not installed, install OpenDKIM from DKIM Manager."
                return

            result = mailUtilities.setupDKIM(virtualHostName)
            if result[0] == 0:
                raise BaseException(result[1])

        FNULL = open(os.devnull, 'w')

        retValues = virtualHostUtilities.createDirectoryForDomain(masterDomain, virtualHostName, phpVersion, path,administratorEmail,virtualHostUser)
        if retValues[0] == 0:
            virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostUtilities,numberOfSites)
            print "0,"+str(retValues[1])
            return

        retValues = virtualHostUtilities.createConfigInMainDomainHostFile(virtualHostName, masterDomain)

        if retValues[0] == 0:
            virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostUtilities, numberOfSites)
            print "0," + str(retValues[1])
            return

        ## Now restart litespeed after initial configurations are done

        installUtilities.installUtilities.reStartLiteSpeed()

        if ssl == 1:
            retValues = sslUtilities.issueSSLForDomain(virtualHostName, administratorEmail, path)
            if retValues[0] == 0:
                virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostName, numberOfSites)
                print "0,"+str(retValues[1])
                return


        ## final Restart

        installUtilities.installUtilities.reStartLiteSpeed()

        shutil.copy("/usr/local/CyberCP/index.html",path + "/index.html")

        command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path + "/index.html"
        cmd = shlex.split(command)
        subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        vhostPath = virtualHostUtilities.Server_root + "/conf/vhosts"
        command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
        cmd = shlex.split(command)
        subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        print "1,None"


    except BaseException,msg:
        virtualHostUtilities.deleteVirtualHostConfigurations(virtualHostName, numberOfSites)
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [createDomain]")
        print "0,"+str(msg)

def issueSSL(virtualHost,path,adminEmail):
    try:

        FNULL = open(os.devnull, 'w')

        srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
        srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"

        pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHost

        pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
        pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

        if os.path.exists(pathToStoreSSLPrivKey):
            os.remove(pathToStoreSSLPrivKey)
        if os.path.exists(pathToStoreSSLFullChain):
            os.remove(pathToStoreSSLFullChain)

        retValues = sslUtilities.issueSSLForDomain(virtualHost, adminEmail, path)

        if retValues[0] == 0:
            print "0," + str(retValues[1])
            return

        installUtilities.installUtilities.reStartLiteSpeed()

        vhostPath = virtualHostUtilities.Server_root + "/conf/vhosts"
        command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
        cmd = shlex.split(command)
        subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        print "1,None"
        return





    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [issueSSL]")
        print "0,"+str(msg)

def getAccessLogs(fileName,page):
    try:

        numberOfTotalLines = int(subprocess.check_output(["wc", "-l", fileName]).split(" ")[0])

        if numberOfTotalLines < 25:
            data = subprocess.check_output(["cat", fileName])
        else:
            if page == 1:
                end = numberOfTotalLines
                start = end - 24
                if start <= 0:
                    start = 1
                startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                command = "sed -n " + startingAndEnding + " " + fileName
                proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                data = proc.stdout.read()
            else:
                end = numberOfTotalLines - ((page - 1) * 25)
                start = end - 24
                if start <= 0:
                    start = 1
                startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                command = "sed -n " + startingAndEnding + " " + fileName
                proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                data = proc.stdout.read()
        print data
    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [getAccessLogs]")
        print "1,None"

def getErrorLogs(fileName,page):
    try:

        numberOfTotalLines = int(subprocess.check_output(["wc", "-l", fileName]).split(" ")[0])

        if numberOfTotalLines < 25:
            data = subprocess.check_output(["cat", fileName])
        else:
            if page == 1:
                end = numberOfTotalLines
                start = end - 24
                if start <= 0:
                    start = 1
                startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                command = "sed -n " + startingAndEnding + " " + fileName
                proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                data = proc.stdout.read()
            else:
                end = numberOfTotalLines - ((page - 1) * 25)
                start = end - 24
                if start <= 0:
                    start = 1
                startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
                command = "sed -n " + startingAndEnding + " " + fileName
                proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                data = proc.stdout.read()
        print data
    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [getErrorLogs]")
        print "1,None"

def saveVHostConfigs(fileName,tempPath):
    try:

        vhost = open(fileName, "w")

        vhost.write(open(tempPath,"r").read())

        vhost.close()

        if os.path.exists(tempPath):
            os.remove(tempPath)

        installUtilities.installUtilities.reStartLiteSpeed()

        print "1,None"

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [saveVHostConfigs]")
        print "0,"+str(msg)

def saveRewriteRules(virtualHost,fileName,tempPath):
    try:

        virtualHostUtilities.addRewriteRules(virtualHost)

        vhost = open(fileName, "w")

        vhost.write(open(tempPath,"r").read())

        vhost.close()

        if os.path.exists(tempPath):
            os.remove(tempPath)

        installUtilities.installUtilities.reStartLiteSpeed()

        print "1,None"

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [saveRewriteRules]")
        print "0,"+str(msg)

def installWordPress(domainName,finalPath,virtualHostUser,dbName,dbUser,dbPassword):
    try:

        FNULL = open(os.devnull, 'w')

        if not os.path.exists(finalPath):
            os.makedirs(finalPath)

        ## checking for directories/files

        dirFiles = os.listdir(finalPath)

        if len(dirFiles) == 1:
            if dirFiles[0] == ".well-known":
                pass
            else:
                print "0,Target directory should be empty before installation, otherwise data loss could occur."
                return
        elif len(dirFiles) == 0:
            pass
        else:
            print "0,Target directory should be empty before installation, otherwise data loss could occur."
            return


        ## Get wordpress


        if not os.path.exists("latest.tar.gz"):
            command = 'wget --no-check-certificate http://wordpress.org/latest.tar.gz -O latest.tar.gz'
            cmd = shlex.split(command)
            res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        command = 'tar -xzvf latest.tar.gz -C ' + finalPath

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        ## Get plugin

        if not os.path.exists("litespeed-cache.1.1.5.1.zip"):
            command = 'wget --no-check-certificate https://downloads.wordpress.org/plugin/litespeed-cache.1.1.5.1.zip'

            cmd = shlex.split(command)

            res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        command = 'unzip litespeed-cache.1.1.5.1.zip -d ' + finalPath

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        root = finalPath

        for filename in listdir(join(root, 'wordpress')):
            move(join(root, 'wordpress', filename), join(root, filename))

        rmdir(root + "wordpress")

        shutil.copytree(finalPath + "litespeed-cache", finalPath + "wp-content/plugins/litespeed-cache")
        shutil.rmtree(finalPath + "litespeed-cache")



        ## edit config file

        wpconfigfile = finalPath + "wp-config-sample.php"

        data = open(wpconfigfile, "r").readlines()

        writeDataToFile = open(wpconfigfile, "w")

        defDBName = "define('DB_NAME', '" + dbName + "');" + "\n"
        defDBUser = "define('DB_USER', '" + dbUser + "');" + "\n"
        defDBPassword = "define('DB_PASSWORD', '" + dbPassword + "');" + "\n"

        for items in data:
            if items.find("DB_NAME") > -1:
                if items.find("database_name_here") > -1:
                    writeDataToFile.writelines(defDBName)
            elif items.find("DB_USER") > -1:
                if items.find("username_here") > -1:
                    writeDataToFile.writelines(defDBUser)
            elif items.find("DB_PASSWORD") > -1:
                writeDataToFile.writelines(defDBPassword)
            else:
                writeDataToFile.writelines(items)

        writeDataToFile.close()

        os.rename(wpconfigfile, finalPath + 'wp-config.php')

        command = "chown -R "+virtualHostUser+":"+virtualHostUser+" " + "/home/" + domainName + "/public_html/"

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        virtualHostUtilities.addRewriteRules(domainName)

        installUtilities.installUtilities.reStartLiteSpeed()

        print "1,None"


    except BaseException, msg:
        # remove the downloaded files
        try:

            shutil.rmtree(finalPath)
        except:
            logging.CyberCPLogFileWriter.writeToFile("shutil.rmtree(finalPath)")

        homeDir = "/home/" + domainName + "/public_html"

        if not os.path.exists(homeDir):
            FNULL = open(os.devnull, 'w')
            os.mkdir(homeDir)
            command = "chown -R "+virtualHostUser+":"+virtualHostUser+" " + homeDir
            cmd = shlex.split(command)
            res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        print "0," + str(msg)
        return


def installJoomla(domainName,finalPath,virtualHostUser,dbName,dbUser,dbPassword,username,password,prefix,sitename):

    try:
        FNULL = open(os.devnull, 'w')


        if not os.path.exists(finalPath):
            os.makedirs(finalPath)

        ## checking for directories/files

        dirFiles = os.listdir(finalPath)

        if len(dirFiles) == 1:
            if dirFiles[0] == ".well-known":
                pass
            else:
                print "0,Target directory should be empty before installation, otherwise data loss could occur."
                return
        elif len(dirFiles) == 0:
            pass
        else:
            print "0,Target directory should be empty before installation, otherwise data loss could occur."
            return

        ## Get Joomla

        os.chdir(finalPath)


        if not os.path.exists("staging.zip"):
            command = 'wget --no-check-certificate https://github.com/joomla/joomla-cms/archive/staging.zip -P ' + finalPath
            cmd = shlex.split(command)
            res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)
        else: 
            print "0,File already exists"
            return

        command = 'unzip '+finalPath+'staging.zip -d ' + finalPath

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        os.remove(finalPath+'staging.zip')

        command = 'cp -r '+finalPath+'joomla-cms-staging/. ' + finalPath
        cmd = shlex.split(command)
        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        shutil.rmtree(finalPath + "joomla-cms-staging")
        os.rename(finalPath+"installation/configuration.php-dist", finalPath+"configuration.php")
        os.rename(finalPath+"robots.txt.dist", finalPath+"robots.txt")
        os.rename(finalPath+"htaccess.txt", finalPath+".htaccess")

        ## edit config file

        configfile = finalPath + "configuration.php"

        data = open(configfile, "r").readlines()

        writeDataToFile = open(configfile, "w")

        secret = randomPassword.generate_pass()

        defDBName = "   public $user = '"+dbName+"';" + "\n"
        defDBUser = "   public $db = '"+dbUser+"';" + "\n"
        defDBPassword = "   public $password = '"+dbPassword+"';" + "\n"
        secretKey = "   public $secret = '"+secret+"';" + "\n"
        logPath = "   public $log_path = '"+finalPath+"administrator/logs';" + "\n"
        tmpPath = "   public $tmp_path = '"+finalPath+"administrator/tmp';" + "\n"
        dbprefix = "   public $dbprefix = '"+prefix+"';" + "\n"
        sitename = "   public $sitename = '"+sitename+"';" + "\n"

        for items in data:
            if items.find("public $user ") > -1:
                writeDataToFile.writelines(defDBUser)
            elif items.find("public $password ") > -1:
                writeDataToFile.writelines(defDBPassword)
            elif items.find("public $db ") > -1:
                writeDataToFile.writelines(defDBName)
            elif items.find("public $log_path ") > -1:
                writeDataToFile.writelines(logPath)
            elif items.find("public $tmp_path ") > -1:
                writeDataToFile.writelines(tmpPath)
            elif items.find("public $secret ") > -1:
                writeDataToFile.writelines(secretKey)
            elif items.find("public $dbprefix ") > -1:
                writeDataToFile.writelines(dbprefix)
            elif items.find("public $sitename ") > -1:
                writeDataToFile.writelines(sitename)
            elif items.find("/*") > -1:
                pass
            elif items.find(" *") > -1:
                pass
            else:
                writeDataToFile.writelines(items)

        writeDataToFile.close()

        #Rename SQL db prefix

        f1 = open(finalPath+'installation/sql/mysql/joomla.sql', 'r')
        f2 = open('installation/sql/mysql/joomlaInstall.sql', 'w')
        for line in f1:
            f2.write(line.replace('#__', prefix))
        f1.close()
        f2.close()

        #Restore SQL
        proc = subprocess.Popen(["mysql", "--user=%s" % dbUser, "--password=%s" % dbPassword, dbName],stdin=subprocess.PIPE,stdout=subprocess.PIPE)

        usercreation = """INSERT INTO `%susers`
        (`name`, `username`, `password`, `params`)
        VALUES ('Administrator', '%s',
        '%s', '');
        INSERT INTO `%suser_usergroup_map` (`user_id`,`group_id`)
        VALUES (LAST_INSERT_ID(),'8');""" % (prefix, username, password, prefix)

        out, err = proc.communicate(file(finalPath + 'installation/sql/mysql/joomlaInstall.sql').read() + "\n" + usercreation)

        shutil.rmtree(finalPath + "installation")

        htaccessCache = """ 
<IfModule LiteSpeed>
RewriteEngine on
CacheLookup on
CacheDisable public /
RewriteCond %{REQUEST_METHOD} ^HEAD|GET$
RewriteCond %{ORG_REQ_URI} !/administrator
RewriteRule .* - [E=cache-control:max-age=120]
</IfModule>
        """

        f=open(finalPath + '.htaccess', "a+")
        f.write(htaccessCache)
        f.close() 

        command = "chown -R "+virtualHostUser+":"+virtualHostUser+" " + "/home/" + domainName + "/public_html/"

        cmd = shlex.split(command)

        res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)

        virtualHostUtilities.addRewriteRules(domainName)

        installUtilities.installUtilities.reStartLiteSpeed()

        print "1,None"
        return

    except BaseException, msg:
        # remove the downloaded files
        try:
            shutil.rmtree(finalPath)
        except:
            logging.CyberCPLogFileWriter.writeToFile("shutil.rmtree(finalPath)")

        homeDir = "/home/" + domainName + "/public_html"

        if not os.path.exists(homeDir):
            FNULL = open(os.devnull, 'w')
            os.mkdir(homeDir)
            command = "chown -R "+virtualHostUser+":"+virtualHostUser+" " + homeDir
            cmd = shlex.split(command)
            res = subprocess.call(cmd,stdout=FNULL, stderr=subprocess.STDOUT)
        return

def issueSSLForHostName(virtualHost,path):
    try:

        FNULL = open(os.devnull, 'w')

        srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
        srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"

        pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHost

        pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
        pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

        destPrivKey = "/usr/local/lscp/key.pem"
        destCert = "/usr/local/lscp/cert.pem"

        ## removing old certs

        if os.path.exists(pathToStoreSSLPrivKey):
            os.remove(pathToStoreSSLPrivKey)
        if os.path.exists(pathToStoreSSLFullChain):
            os.remove(pathToStoreSSLFullChain)

        ## removing old certs for lscpd
        if os.path.exists(destPrivKey):
            os.remove(destPrivKey)
        if os.path.exists(destCert):
            os.remove(destCert)

        adminEmail = "email@" + virtualHost

        if not (os.path.exists(srcPrivKey) and os.path.exists(srcFullChain)):

            retValues = sslUtilities.issueSSLForDomain(virtualHost, adminEmail, path)

            if retValues[0] == 0:
                print "0," + str(retValues[1])
                return

            ## lcpd specific functions

            shutil.copy(srcPrivKey, destPrivKey)
            shutil.copy(srcFullChain, destCert)

            command = 'systemctl restart lscpd'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            vhostPath = virtualHostUtilities.Server_root + "/conf/vhosts"
            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            print "1,None"
        else:
            ###### Copy SSL To config location ######

            try:
                os.mkdir(pathToStoreSSL)
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Directory for SSL already exists.. Continuing [issueSSLForHostName]]")

            srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
            srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"

            shutil.copy(srcPrivKey, pathToStoreSSLPrivKey)
            shutil.copy(srcFullChain, pathToStoreSSLFullChain)

            ## lcpd specific functions

            shutil.copy(srcPrivKey, destPrivKey)
            shutil.copy(srcFullChain, destCert)

            command = 'systemctl restart lscpd'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            vhostPath = virtualHostUtilities.Server_root + "/conf/vhosts"
            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            print "1,None"
            return

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [issueSSLForHostName]")
        print "0,"+str(msg)

def issueSSLForMailServer(virtualHost,path):
    try:

        FNULL = open(os.devnull, 'w')

        srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
        srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"

        pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHost

        pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
        pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"


        ## removing old certs

        if os.path.exists(pathToStoreSSLPrivKey):
            os.remove(pathToStoreSSLPrivKey)
        if os.path.exists(pathToStoreSSLFullChain):
            os.remove(pathToStoreSSLFullChain)


        adminEmail = "email@" + virtualHost

        if not (os.path.exists(srcPrivKey) and os.path.exists(srcFullChain)):

            retValues = sslUtilities.issueSSLForDomain(virtualHost, adminEmail, path)

            if retValues[0] == 0:
                print "0," + str(retValues[1])
                return


        else:
            ###### Copy SSL To config location ######

            try:
                os.mkdir(pathToStoreSSL)
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Directory for SSL already exists.. Continuing [issueSSLForHostName]]")

            srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
            srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"

            shutil.copy(srcPrivKey, pathToStoreSSLPrivKey)
            shutil.copy(srcFullChain, pathToStoreSSLFullChain)


        ## MailServer specific functions

        if os.path.exists("/etc/postfix/cert.pem"):
            os.remove("/etc/postfix/cert.pem")

        if os.path.exists("/etc/postfix/key.pem"):
            os.remove("/etc/postfix/key.pem")

        if os.path.exists("/etc/pki/dovecot/private/dovecot.pem"):
            os.remove("/etc/pki/dovecot/private/dovecot.pem")

        if os.path.exists("/etc/pki/dovecot/certs/dovecot.pem"):
            os.remove("/etc/pki/dovecot/certs/dovecot.pem")

        if os.path.exists("/etc/dovecot/key.pem"):
            os.remove("/etc/dovecot/key.pem")

        if os.path.exists("/etc/dovecot/cert.pem"):
            os.remove("/etc/dovecot/cert.pem")


        ## Postfix

        shutil.copy(srcPrivKey, "/etc/postfix/key.pem")
        shutil.copy(srcFullChain, "/etc/postfix/cert.pem")

        ## Dovecot

        shutil.copy(srcPrivKey, "/etc/pki/dovecot/private/dovecot.pem")
        shutil.copy(srcFullChain, "/etc/pki/dovecot/certs/dovecot.pem")

        ## Dovecot 2ND

        shutil.copy(srcPrivKey, "/etc/dovecot/key.pem")
        shutil.copy(srcFullChain, "/etc/dovecot/cert.pem")


        vhostPath = virtualHostUtilities.Server_root + "/conf/vhosts"
        command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
        cmd = shlex.split(command)
        subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        ## Update postmaster address dovecot

        filePath = "/etc/dovecot/dovecot.conf"

        data = open(filePath,'r').readlines()

        writeFile = open(filePath,'w')

        for items in data:
            if items.find('postmaster_address') > -1:
                writeFile.writelines('    postmaster_address = postmaster@' + virtualHost + '\n')
            else:
                writeFile.writelines(items)

        writeFile.close()

        ## Update myhostname address postfix

        filePath = "/etc/postfix/main.cf"

        data = open(filePath, 'r').readlines()

        writeFile = open(filePath, 'w')

        for items in data:
            if items.find('myhostname') > -1:
                writeFile.writelines('myhostname = ' + virtualHost + '\n')
            else:
                writeFile.writelines(items)

        writeFile.close()

        command = 'systemctl restart postfix'
        subprocess.call(shlex.split(command))

        command = 'systemctl restart dovecot'
        subprocess.call(shlex.split(command))

        print "1,None"

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [issueSSLForHostName]")
        print "0,"+str(msg)



def saveSSL(virtualHost,pathToStoreSSL,keyPath,certPath,sslCheck):
    try:

        if not os.path.exists(pathToStoreSSL):
            os.mkdir(pathToStoreSSL)

        pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
        pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

        privkey = open(pathToStoreSSLPrivKey, 'w')
        privkey.write(open(keyPath,"r").read())
        privkey.close()

        fullchain = open(pathToStoreSSLFullChain, 'w')
        fullchain.write(open(certPath,"r").read())
        fullchain.close()

        if sslCheck == "0":
            sslUtilities.sslUtilities.installSSLForDomain(virtualHost)

        installUtilities.installUtilities.reStartLiteSpeed()

        FNULL = open(os.devnull, 'w')

        command = "chown " + "lsadm" + ":" + "lsadm" + " " + pathToStoreSSL
        cmd = shlex.split(command)
        subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


        print "1,None"

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [saveSSL]")
        print "0,"+str(msg)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--virtualHostName', help='Domain name!')
    parser.add_argument('--administratorEmail', help='Administration Email!')
    parser.add_argument('--phpVersion', help='PHP Version')
    parser.add_argument("--virtualHostUser", help="Virtual Host Directory Owner and Group!")
    parser.add_argument("--numberOfSites", help="Number of sites!")
    parser.add_argument("--ssl", help="Weather to activate SSL")
    parser.add_argument("--sslPath", help="Path to website document root!")
    parser.add_argument('--dkimCheck', help='To enable or disable DKIM support for domain.')


    ## arguments for creation child domains

    parser.add_argument('--masterDomain', help='Master Domain Needed While Creating Child Domains!')
    parser.add_argument('--path', help='Path Needed for Child domains Creation!')
    parser.add_argument('--restart', help='OLS Restart Frequency while child domain creation!')

    ## arguments for logs

    parser.add_argument('--page', help='Page number to fetch logs!')

    ## arguments for configuration files

    parser.add_argument('--tempPath', help='Temporary path where configuration data is placed!')


    ## save ssl arguments

    parser.add_argument('--tempKeyPath', help='Temporary path to store key!')
    parser.add_argument('--tempCertPath', help='Temporary path to store cert!')
    parser.add_argument('--sslCheck', help='Weather SSL is already activated or not!')

    ## install wordpress arguments

    parser.add_argument('--dbName', help='Database Name!')
    parser.add_argument('--dbUser', help='Database User!')
    parser.add_argument('--dbPassword', help='Database Password!')

    ## calculate bw arguments

    parser.add_argument('--bandwidth', help='Pack Bandwidth!')

    ## extras
    parser.add_argument('--username', help='Admin Username!')
    parser.add_argument('--password', help='Admin Password!')
    parser.add_argument('--prefix', help='Database Prefix!')
    parser.add_argument('--sitename', help='Site Name!')

    args = parser.parse_args()

    if args.function == "createVirtualHost":
        try:
            dkimCheck = int(args.dkimCheck)
        except:
            dkimCheck = 0
        createVirtualHost(args.virtualHostName,args.administratorEmail,args.phpVersion,args.virtualHostUser,int(args.numberOfSites),int(args.ssl),args.sslPath,dkimCheck)
    elif args.function == "deleteVirtualHostConfigurations":
        virtualHostUtilities.deleteVirtualHostConfigurations(args.virtualHostName,int(args.numberOfSites))
    elif args.function == "createDomain":
        try:
            dkimCheck = int(args.dkimCheck)
        except:
            dkimCheck = 0
        createDomain(args.masterDomain, args.virtualHostName, args.phpVersion, args.path,args.administratorEmail,args.virtualHostUser,args.restart,int(args.numberOfSites),int(args.ssl),dkimCheck)
    elif args.function == "issueSSL":
        issueSSL(args.virtualHostName,args.path,args.administratorEmail)
    elif args.function == "changePHP":
        virtualHostUtilities.changePHP(args.path,args.phpVersion)
    elif args.function == "getAccessLogs":
        getAccessLogs(args.path,int(args.page))
    elif args.function == "getErrorLogs":
        getErrorLogs(args.path,int(args.page))
    elif args.function == "saveVHostConfigs":
        saveVHostConfigs(args.path,args.tempPath)
    elif args.function == "saveRewriteRules":
        saveRewriteRules(args.virtualHostName,args.path,args.tempPath)
    elif args.function == "saveSSL":
        saveSSL(args.virtualHostName,args.path,args.tempKeyPath,args.tempCertPath,args.sslCheck)
    elif args.function == "installWordPress":
        installWordPress(args.virtualHostName,args.path,args.virtualHostUser,args.dbName,args.dbUser,args.dbPassword)
    elif args.function == "installJoomla":
        installJoomla(args.virtualHostName,args.path,args.virtualHostUser,args.dbName,args.dbUser,args.dbPassword,args.username,args.password,args.prefix,args.sitename)
    elif args.function == "issueSSLForHostName":
        issueSSLForHostName(args.virtualHostName,args.path)
    elif args.function == "issueSSLForMailServer":
        issueSSLForMailServer(args.virtualHostName,args.path)
    elif args.function == "findDomainBW":
        virtualHostUtilities.findDomainBW(args.virtualHostName, int(args.bandwidth))

if __name__ == "__main__":
    main()