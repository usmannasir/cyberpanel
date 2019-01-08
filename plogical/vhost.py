#!/usr/local/CyberCP/bin/python2
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import shutil
import installUtilities
from websiteFunctions.models import Websites, ChildDomains, aliasDomains
import subprocess
import shlex
import CyberCPLogFileWriter as logging
from databases.models import Databases
from mysqlUtilities import mysqlUtilities
from dnsUtilities import DNS
from random import randint
from processUtilities import ProcessUtilities
from managePHP.phpManager import PHPManager


## If you want justice, you have come to the wrong place.


class vhost:

    Server_root = "/usr/local/lsws"
    cyberPanel = "/usr/local/CyberCP"

    @staticmethod
    def addUser(virtualHostUser, path):
        try:

            FNULL = open(os.devnull, 'w')
            if os.path.exists("/etc/lsb-release"):
                command = 'adduser --no-create-home --home ' + path + ' --disabled-login --gecos "" ' + virtualHostUser
            else:
                command = "adduser " + virtualHostUser + " -M -d " + path

            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            command = "groupadd " + virtualHostUser
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            command = "usermod -a -G " + virtualHostUser + " " + virtualHostUser
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addingUsers]")

    @staticmethod
    def createDirectories(path, virtualHostUser, pathHTML, pathLogs, confPath, completePathToConfigFile):
        try:
            FNULL = open(os.devnull, 'w')

            try:
                command = 'chmod 711 /home'
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)
            except:
                pass

            try:
                os.makedirs(path)

                command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

                command = "chmod 711 " + path
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [27 Not able create to directories for virtual host [createDirectories]]")
                return [0, "[27 Not able to directories for virtual host [createDirectories]]"]

            try:
                os.makedirs(pathHTML)

                command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + pathHTML
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [33 Not able to directories for virtual host [createDirectories]]")
                return [0, "[33 Not able to directories for virtual host [createDirectories]]"]

            try:
                os.makedirs(pathLogs)

                command = "chown " + "lscpd" + ":" + "lscpd" + " " + pathLogs
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


                if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                    command = "chmod -R 666 " + pathLogs
                else:
                    command = "chmod -R 755 " + pathLogs

                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [39 Not able to directories for virtual host [createDirectories]]")
                return [0, "[39 Not able to directories for virtual host [createDirectories]]"]

            try:
                ## For configuration files permissions will be changed later globally.
                os.makedirs(confPath)
            except OSError, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [45 Not able to directories for virtual host [createDirectories]]")
                return [0, "[45 Not able to directories for virtual host [createDirectories]]"]

            try:
                ## For configuration files permissions will be changed later globally.
                file = open(completePathToConfigFile, "w+")

                command = "chown " + "lsadm" + ":" + "lsadm" + " " + completePathToConfigFile
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except IOError, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectories]]")
                return [0, "[45 Not able to directories for virtual host [createDirectories]]"]

            return [1, 'None']

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectories]")
            return [0, str(msg)]

    @staticmethod
    def finalizeVhostCreation(virtualHostName, virtualHostUser):
        try:

            FNULL = open(os.devnull, 'w')

            shutil.copy("/usr/local/CyberCP/index.html", "/home/" + virtualHostName + "/public_html/index.html")

            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + "/home/" + virtualHostName + "/public_html/index.html"
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            vhostPath = vhost.Server_root + "/conf/vhosts"

            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [finalizeVhostCreation]")

    @staticmethod
    def createDirectoryForVirtualHost(virtualHostName,administratorEmail,virtualHostUser, phpVersion, openBasedir):

        path = "/home/" + virtualHostName
        pathHTML = "/home/" + virtualHostName + "/public_html"
        pathLogs = "/home/" + virtualHostName + "/logs"
        confPath = vhost.Server_root + "/conf/vhosts/"+virtualHostName
        completePathToConfigFile = confPath +"/vhost.conf"


        ## adding user

        vhost.addUser(virtualHostUser, path)

        ## Creating Directories

        result = vhost.createDirectories(path, virtualHostUser, pathHTML, pathLogs, confPath, completePathToConfigFile)

        if result[0] == 0:
            return [0, result[1]]


        ## Creating Per vhost Configuration File


        if vhost.perHostVirtualConf(completePathToConfigFile,administratorEmail,virtualHostUser,phpVersion, virtualHostName, openBasedir) == 1:
            return [1,"None"]
        else:
            return [0,"[61 Not able to create per host virtual configurations [perHostVirtualConf]"]

    @staticmethod
    def perHostVirtualConf(vhFile, administratorEmail,virtualHostUser, phpVersion, virtualHostName, openBasedir):
        # General Configurations tab
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
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

                php = PHPManager.getPHPString(phpVersion)

                extprocessor = "extprocessor "+virtualHostUser+" {\n"
                type = "  type                    lsapi\n"
                address = "  address                 UDS://tmp/lshttpd/"+virtualHostUser+".sock\n"
                maxConns = "  maxConns                10\n"
                env = "  env                     LSAPI_CHILDREN=10\n"
                initTimeout = "  initTimeout             600\n"
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
                location = "  location                /usr/local/lsws/Example/html/FileManager\n"
                allowBrowse = "  allowBrowse             1\n"
                autoIndex = "  autoIndex               1\n\n"

                accessControl = "  accessControl  {\n"
                allow = "    allow                 127.0.0.1, localhost\n"
                deny = "    deny                  0.0.0.0/0\n"
                accessControlEnds = "  }\n"

                rewriteInherit = """  rewrite  {
        enable               0
    
      }
      """

                phpIniOverride = "phpIniOverride  {\n"
                php_admin_value = 'php_admin_value open_basedir "/tmp:/usr/local/lsws/Example/html/FileManager:$VH_ROOT"\n'
                php_value = 'php_value display_errors "Off"\n'
                php_value_upload_max_size = 'php_value upload_max_filesize "200M"\n'
                php_value_post_max_size = 'php_value post_max_size "250M"\n'
                endPHPIniOverride = "}\n"


                defaultCharSet = "  addDefaultCharset       off\n"
                contextEnds = "}\n"

                confFile.writelines(context)
                confFile.writelines(location)
                confFile.writelines(allowBrowse)
                confFile.writelines(autoIndex)
                confFile.writelines(accessControl)
                confFile.writelines(allow)
                confFile.writelines(deny)
                confFile.writelines(accessControlEnds)
                confFile.write(rewriteInherit)

                confFile.writelines(phpIniOverride)
                if openBasedir == 1:
                    confFile.writelines(php_admin_value)
                confFile.write(php_value)
                confFile.write(php_value_upload_max_size)
                confFile.write(php_value_post_max_size)
                confFile.writelines(endPHPIniOverride)

                confFile.writelines(defaultCharSet)
                confFile.writelines(contextEnds)

                ## OpenBase Dir Protection

                phpIniOverride = "phpIniOverride  {\n"
                php_admin_value = 'php_admin_value open_basedir "/tmp:$VH_ROOT"\n'
                endPHPIniOverride = "}\n"

                confFile.writelines(phpIniOverride)
                if openBasedir == 1:
                    confFile.writelines(php_admin_value)
                confFile.writelines(endPHPIniOverride)


                htaccessAutoLoad = """
    rewrite  {
      enable                  1
      autoLoadHtaccess        1
    }
    """
                confFile.write(htaccessAutoLoad)

                confFile.close()

            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostVirtualConf]]")
                return 0
            return 1
        else:
            try:
                confFile = open(vhFile, "w+")

                doNotModify = '# Do not modify this file, this is auto-generated file.\n\n'

                VirtualHost = '<VirtualHost *:80>\n\n'
                ServerName = '    ServerName ' + virtualHostName + '\n'
                ServerAlias = '    ServerAlias www.' + virtualHostName + '\n'
                ScriptAlias = '    Alias /.filemanager/ /usr/local/lsws/FileManager\n'
                ServerAdmin = '    ServerAdmin ' + administratorEmail + '\n'
                SeexecUserGroup = '    SuexecUserGroup ' + virtualHostUser + ' ' + virtualHostUser + '\n'
                DocumentRoot = '    DocumentRoot /home/' + virtualHostName + '/public_html\n'
                CustomLogCombined = '    CustomLog /home/' + virtualHostName + '/logs/' + virtualHostName + '.access_log combined\n'

                confFile.writelines(doNotModify)
                confFile.writelines(VirtualHost)
                confFile.writelines(ServerName)
                confFile.writelines(ServerAlias)
                confFile.writelines(ScriptAlias)
                confFile.writelines(ServerAdmin)
                confFile.writelines(SeexecUserGroup)
                confFile.writelines(DocumentRoot)
                confFile.writelines(CustomLogCombined)

                DirectoryFileManager = """\n    <Directory /usr/local/lsws/FileManager>
                            Options +Includes -Indexes +ExecCGI
                            php_value display_errors "Off"
                            php_value upload_max_filesize "200M"
                            php_value post_max_size "250M"
                        </Directory>\n"""
                confFile.writelines(DirectoryFileManager)

                ## external app

                php = PHPManager.getPHPString(phpVersion)

                AddType = '    AddHandler application/x-httpd-php' + php + ' .php .php7 .phtml\n\n'
                VirtualHostEnd = '</VirtualHost>\n'

                confFile.writelines(AddType)
                confFile.writelines(VirtualHostEnd)

                confFile.close()
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostVirtualConf]]")
                return 0
            return 1


    @staticmethod
    def createNONSSLMapEntry(virtualHostName):
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

            map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"

            mapchecker = 1

            for items in data:
                if (mapchecker == 1 and (items.find("listener") > -1 and items.find("Default") > -1)):
                    writeDataToFile.writelines(items)
                    writeDataToFile.writelines(map)
                    mapchecker = 0
                else:
                    writeDataToFile.writelines(items)

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def createConfigInMainVirtualHostFile(virtualHostName):

        #virtualhost project.cyberpersons.com {
        #vhRoot / home / project.cyberpersons.com
        #configFile      $SERVER_ROOT / conf / vhosts /$VH_NAME / vhconf.conf
        #allowSymbolLink 1
        #enableScript 1
        #restrained 1
        #}

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                if vhost.createNONSSLMapEntry(virtualHostName) == 0:
                    return [0, "Failed to create NON SSL Map Entry [createConfigInMainVirtualHostFile]"]

                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                writeDataToFile.writelines("virtualHost " + virtualHostName + " {\n")
                writeDataToFile.writelines("  vhRoot                  /home/$VH_NAME\n")
                writeDataToFile.writelines("  configFile              $SERVER_ROOT/conf/vhosts/$VH_NAME/vhost.conf\n")
                writeDataToFile.writelines("  allowSymbolLink         1\n")
                writeDataToFile.writelines("  enableScript            1\n")
                writeDataToFile.writelines("  restrained              1\n")
                writeDataToFile.writelines("}\n")
                writeDataToFile.writelines("\n")

                writeDataToFile.close()


                writeDataToFile.close()
                return [1,"None"]
            except BaseException,msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]")
                return [0,"223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]
        else:
            try:
                writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'a')
                configFile = 'Include /usr/local/lsws/conf/vhosts/' + virtualHostName + '/vhost.conf\n'
                writeDataToFile.writelines(configFile)
                writeDataToFile.close()

                writeDataToFile.close()
                return [1, "None"]
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]

    @staticmethod
    def deleteVirtualHostConfigurations(virtualHostName):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                ## Deleting master conf
                numberOfSites = str(Websites.objects.count() + ChildDomains.objects.count())
                vhost.deleteCoreConf(virtualHostName, numberOfSites)

                delWebsite = Websites.objects.get(domain=virtualHostName)
                databases = Databases.objects.filter(website=delWebsite)

                childDomains = delWebsite.childdomains_set.all()

                ## Deleting child domains

                for items in childDomains:
                    numberOfSites = Websites.objects.count() + ChildDomains.objects.count()
                    vhost.deleteCoreConf(items.domain, numberOfSites)

                for items in databases:
                    mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

                delWebsite.delete()

                ## Deleting DNS Zone if there is any.

                DNS.deleteDNSZone(virtualHostName)

                installUtilities.installUtilities.reStartLiteSpeed()

                ## Delete mail accounts

                command = "sudo rm -rf /home/vmail/" + virtualHostName
                subprocess.call(shlex.split(command))
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1
        else:
            try:
                ## Deleting master conf
                numberOfSites = str(Websites.objects.count() + ChildDomains.objects.count())
                vhost.deleteCoreConf(virtualHostName, numberOfSites)

                delWebsite = Websites.objects.get(domain=virtualHostName)
                databases = Databases.objects.filter(website=delWebsite)

                childDomains = delWebsite.childdomains_set.all()

                ## Deleting child domains

                for items in childDomains:
                    numberOfSites = Websites.objects.count() + ChildDomains.objects.count()
                    vhost.deleteCoreConf(items.domain, numberOfSites)

                for items in databases:
                    mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

                delWebsite.delete()

                ## Deleting DNS Zone if there is any.

                DNS.deleteDNSZone(virtualHostName)

                installUtilities.installUtilities.reStartLiteSpeed()

                ## Delete mail accounts

                command = "sudo rm -rf /home/vmail/" + virtualHostName
                subprocess.call(shlex.split(command))
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1

    @staticmethod
    def deleteCoreConf(virtualHostName, numberOfSites):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                virtualHostPath = "/home/" + virtualHostName
                if os.path.exists(virtualHostPath):
                    shutil.rmtree(virtualHostPath)

                confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
                if os.path.exists(confPath):
                    shutil.rmtree(confPath)

                data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()

                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')

                check = 1
                sslCheck = 1

                for items in data:
                    if numberOfSites == 1:
                        if (items.find(' ' + virtualHostName) > -1 and items.find("  map                     " + virtualHostName) > -1):
                            continue
                        if (items.find(' ' + virtualHostName) > -1 and (items.find("virtualHost") > -1 or items.find("virtualhost") > -1)):
                            check = 0
                        if items.find("listener") > -1 and items.find("SSL") > -1:
                            sslCheck = 0
                        if (check == 1 and sslCheck == 1):
                            writeDataToFile.writelines(items)
                        if (items.find("}") > -1 and (check == 0 or sslCheck == 0)):
                            check = 1
                            sslCheck = 1
                    else:
                        if (items.find(' ' + virtualHostName) > -1 and items.find("  map                     " + virtualHostName) > -1):
                            continue
                        if (items.find(' ' + virtualHostName) > -1 and (items.find("virtualHost") > -1 or items.find("virtualhost") > -1)):
                            check = 0
                        if (check == 1):
                            writeDataToFile.writelines(items)
                        if (items.find("}") > -1 and check == 0):
                            check = 1
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1
        else:
            virtualHostPath = "/home/" + virtualHostName
            try:
                shutil.rmtree(virtualHostPath)
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host directory from /home continuing..]")

            try:
                confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
                shutil.rmtree(confPath)
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration directory from /conf ]")

            try:
                data = open("/usr/local/lsws/conf/httpd.conf").readlines()

                writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'w')

                for items in data:
                    if items.find('/' + virtualHostName + '/') > -1:
                        pass
                    else:
                        writeDataToFile.writelines(items)

                writeDataToFile.close()

            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1

    @staticmethod
    def checkIfVirtualHostExists(virtualHostName):
        if os.path.exists("/home/" + virtualHostName):
            return 1
        return 0

    @staticmethod
    def changePHP(vhFile, phpVersion):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                data = open(vhFile, "r").readlines()

                php = PHPManager.getPHPString(phpVersion)

                if not os.path.exists("/usr/local/lsws/lsphp" + str(php) + "/bin/lsphp"):
                    print 0, 'This PHP version is not available on your CyberPanel.'
                    return [0, "[This PHP version is not available on your CyberPanel. [changePHP]"]

                writeDataToFile = open(vhFile, "w")

                path = "  path                    /usr/local/lsws/lsphp" + str(php) + "/bin/lsphp\n"

                for items in data:
                    if items.find("/usr/local/lsws/lsphp") > -1 and items.find("path") > -1:
                        writeDataToFile.writelines(path)
                    else:
                        writeDataToFile.writelines(items)

                writeDataToFile.close()

                installUtilities.installUtilities.reStartLiteSpeed()

                print "1,None"
                return 1,'None'
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [changePHP]")
                print 0,str(msg)
                return [0, str(msg) + " [IO Error with per host config file [changePHP]"]
        else:
            try:
                data = open(vhFile, "r").readlines()

                php = PHPManager.getPHPString(phpVersion)

                if not os.path.exists("/usr/local/lsws/lsphp" + str(php) + "/bin/lsphp"):
                    print 0, 'This PHP version is not available on your CyberPanel.'
                    return [0, "[This PHP version is not available on your CyberPanel. [changePHP]"]

                writeDataToFile = open(vhFile, "w")

                finalString = '    AddHandler application/x-httpd-php' + str(php) + ' .php\n'

                for items in data:
                    if items.find("AddHandler application/x-httpd") > -1:
                        writeDataToFile.writelines(finalString)
                    else:
                        writeDataToFile.writelines(items)

                writeDataToFile.close()

                installUtilities.installUtilities.reStartLiteSpeed()

                print "1,None"
                return 1, 'None'
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [changePHP]]")
                print 0, str(msg)
                return [0, str(msg) + " [IO Error with per host config file [changePHP]]"]

    @staticmethod
    def addRewriteRules(virtualHostName, fileName=None):
        try:
            pass
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

    @staticmethod
    def findDomainBW(domainName, totalAllowed):
        try:
            path = "/home/" + domainName + "/logs/" + domainName + ".access_log"

            if not os.path.exists("/home/" + domainName + "/logs"):
                print "0,0"

            bwmeta = "/home/" + domainName + "/logs/bwmeta"

            if not os.path.exists(path):
                print "0,0"

            if os.path.exists(bwmeta):
                try:
                    data = open(bwmeta).readlines()
                    currentUsed = int(data[0].strip("\n"))

                    inMB = int(float(currentUsed) / (1024.0 * 1024.0))

                    if totalAllowed == 0:
                        totalAllowed = 999999

                    percentage = float(100) / float(totalAllowed)
                    percentage = float(percentage) * float(inMB)
                except:
                    print "0,0"

                if percentage > 100.0:
                    percentage = 100

                print str(inMB) + "," + str(percentage)
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

    @staticmethod
    def checkIfAliasExists(aliasDomain):
        try:
            alias = aliasDomains.objects.get(aliasDomain=aliasDomain)
            return 1
        except BaseException, msg:
            return 0

    @staticmethod
    def checkIfSSLAliasExists(data, aliasDomain):
        try:
            for items in data:
                if items.strip(',').strip('\n') == aliasDomain:
                    return 1
            return 0

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [checkIfSSLAliasExists]")
            return 1

    @staticmethod
    def createAliasSSLMap(confPath, masterDomain, aliasDomain):
        try:

            data = open(confPath, 'r').readlines()
            writeToFile = open(confPath, 'w')
            sslCheck = 0


            for items in data:
                if (items.find("listener SSL") > -1):
                    sslCheck = 1
                if items.find(masterDomain) > -1 and items.find('map') > -1 and sslCheck == 1:
                    data = filter(None, items.split(" "))
                    if data[1] == masterDomain:
                        if vhost.checkIfSSLAliasExists(data, aliasDomain) == 0:
                            writeToFile.writelines(items.rstrip('\n') + ", " + aliasDomain + "\n")
                            sslCheck = 0
                        else:
                            writeToFile.writelines(items)
                else:
                    writeToFile.writelines(items)

            writeToFile.close()
            installUtilities.installUtilities.reStartLiteSpeed()

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [createAliasSSLMap]")

    ## Child Domain Functions

    @staticmethod
    def finalizeDomainCreation(virtualHostUser, path):
        try:

            FNULL = open(os.devnull, 'w')

            shutil.copy("/usr/local/CyberCP/index.html", path + "/index.html")

            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path + "/index.html"
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            vhostPath = vhost.Server_root + "/conf/vhosts"
            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [finalizeDomainCreation]")

    @staticmethod
    def createDirectoryForDomain(masterDomain, domain, phpVersion, path, administratorEmail, virtualHostUser,
                                 openBasedir):

        FNULL = open(os.devnull, 'w')

        confPath = vhost.Server_root + "/conf/vhosts/" + domain
        completePathToConfigFile = confPath + "/vhost.conf"

        try:
            os.makedirs(path)
            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + path
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)
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

        if vhost.perHostDomainConf(path, masterDomain, domain, completePathToConfigFile,
                                   administratorEmail, phpVersion, virtualHostUser, openBasedir) == 1:
            return [1, "None"]
        else:
            return [0, "[359 Not able to create per host virtual configurations [perHostVirtualConf]"]

    @staticmethod
    def perHostDomainConf(path, masterDomain, domain, vhFile, administratorEmail, phpVersion, virtualHostUser, openBasedir):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
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

                ## OpenBase Dir Protection

                phpIniOverride = "phpIniOverride  {\n"
                php_admin_value = 'php_admin_value open_basedir "/tmp:/usr/local/lsws/Example/html/FileManager:$VH_ROOT"\n'
                endPHPIniOverride = "}\n"

                confFile.writelines(phpIniOverride)
                if openBasedir == 1:
                    confFile.writelines(php_admin_value)
                confFile.writelines(endPHPIniOverride)

                # php settings

                sockRandomPath = str(randint(1000, 9999))

                scripthandler = "scripthandler  {" + "\n"
                add = "  add                     lsapi:" + virtualHostUser + sockRandomPath + " php" + "\n"
                php_end = "}" + "\n" + "\n"

                confFile.writelines(scripthandler)
                confFile.writelines(add)
                confFile.writelines(php_end)

                ## external app

                php = PHPManager.getPHPString(phpVersion)

                extprocessor = "extprocessor " + virtualHostUser + sockRandomPath + " {\n"
                type = "  type                    lsapi\n"
                address = "  address                 UDS://tmp/lshttpd/" + virtualHostUser + sockRandomPath + ".sock\n"
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

                htaccessAutoLoad = """
    rewrite  {
      enable                  1
      autoLoadHtaccess        1
    }
    """
                confFile.write(htaccessAutoLoad)

                confFile.close()
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostDomainConf]]")
                return 0
            return 1
        else:
            try:

                confFile = open(vhFile, "w+")

                doNotModify = '# Do not modify this file, this is auto-generated file.\n\n'

                VirtualHost = '<VirtualHost *:80>\n\n'
                ServerName = '    ServerName ' + domain + '\n'
                ServerAlias = '    ServerAlias www.' + domain + '\n'
                ServerAdmin = '    ServerAdmin ' + administratorEmail + '\n'
                SeexecUserGroup = '    SuexecUserGroup ' + virtualHostUser + ' ' + virtualHostUser + '\n'
                DocumentRoot = '    DocumentRoot ' + path + '\n'
                CustomLogCombined = '    CustomLog /home/' + masterDomain + '/logs/' + masterDomain + '.access_log combined\n'

                confFile.writelines(doNotModify)
                confFile.writelines(VirtualHost)
                confFile.writelines(ServerName)
                confFile.writelines(ServerAlias)
                confFile.writelines(ServerAdmin)
                confFile.writelines(SeexecUserGroup)
                confFile.writelines(DocumentRoot)
                confFile.writelines(CustomLogCombined)

                ## external app

                php = php = PHPManager.getPHPString(phpVersion)

                AddType = '    AddHandler application/x-httpd-php' + php + ' .php .php7 .phtml\n\n'
                VirtualHostEnd = '</VirtualHost>\n'

                confFile.writelines(AddType)
                confFile.writelines(VirtualHostEnd)

                confFile.close()
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostDomainConf]]")
                return 0
            return 1


    @staticmethod
    def createConfigInMainDomainHostFile(domain, masterDomain):
        # virtualhost project.cyberpersons.com {
        # vhRoot / home / project.cyberpersons.com
        # configFile      $SERVER_ROOT / conf / vhosts /$VH_NAME / vhconf.conf
        # allowSymbolLink 1
        # enableScript 1
        # restrained 1
        # }

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                if vhost.createNONSSLMapEntry(domain) == 0:
                    return [0, "Failed to create NON SSL Map Entry [createConfigInMainVirtualHostFile]"]

                writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                writeDataToFile.writelines("\n")
                writeDataToFile.writelines("virtualHost " + domain + " {\n")
                writeDataToFile.writelines("  vhRoot                  /home/" + masterDomain + "\n")
                writeDataToFile.writelines("  configFile              $SERVER_ROOT/conf/vhosts/$VH_NAME/vhost.conf\n")
                writeDataToFile.writelines("  allowSymbolLink         1\n")
                writeDataToFile.writelines("  enableScript            1\n")
                writeDataToFile.writelines("  restrained              1\n")
                writeDataToFile.writelines("}\n")
                writeDataToFile.writelines("\n")

                writeDataToFile.close()

                return [1, "None"]

            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainDomainHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainDomainHostFile]]"]
        else:
            try:
                writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'a')
                configFile = 'Include /usr/local/lsws/conf/vhosts/' + domain + '/vhost.conf\n'
                writeDataToFile.writelines(configFile)
                writeDataToFile.close()
                return [1, "None"]
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainDomainHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainDomainHostFile]]"]
