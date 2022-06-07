#!/usr/local/CyberCP/bin/python
import argparse
import os, sys
import shutil
import time

from loginSystem.models import Administrator
from plogical.acl import ACLManager


sys.path.append('/usr/local/CyberCP')
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess
from websiteFunctions.models import ChildDomains, Websites, WPSites, WPStaging, wpplugins
from plogical import randomPassword
from plogical.mysqlUtilities import mysqlUtilities
from databases.models import Databases
from plogical.installUtilities import installUtilities
from plogical.processUtilities import ProcessUtilities
from random import randint
import hashlib

class ApplicationInstaller(multi.Thread):

    LOCALHOST = 'localhost'
    REMOTE = 0
    PORT = '3306'
    MauticVersion = '4.1.2'
    PrestaVersion = '1.7.8.3'

    def __init__(self, installApp, extraArgs):
        multi.Thread.__init__(self)
        self.installApp = installApp
        self.extraArgs = extraArgs

        if extraArgs != None:
            try:
                self.tempStatusPath = self.extraArgs['tempStatusPath']
            except:
                pass
        self.data = self.extraArgs

    def run(self):
        try:

            if self.installApp == 'wordpress':
                self.installWordPress()
            elif self.installApp == 'joomla':
                self.installJoomla()
            elif self.installApp == 'prestashop':
                self.installPrestaShop()
            elif self.installApp == 'magento':
                self.installMagento()
            elif self.installApp == 'convertDomainToSite':
                self.convertDomainToSite()
            elif self.installApp == 'updatePackage':
                self.updatePackage()
            elif self.installApp == 'mautic':
                self.installMautic()
            elif self.installApp == 'wordpressInstallNew':
                self.wordpressInstallNew()
            elif self.installApp == 'UpdateWPTheme':
                self.UpdateWPTheme()
            elif self.installApp == 'UpdateWPPlugin':
                self.UpdateWPPlugin()
            elif self.installApp == 'DeleteThemes':
                self.DeleteThemes()
            elif self.installApp == 'DeletePlugins':
                self.DeletePlugins()
            elif self.installApp == 'ChangeStatusThemes':
                self.ChangeStatusThemes()
            elif self.installApp == 'CreateStagingNow':
                self.CreateStagingNow()
            elif self.installApp == 'DeploytoProduction':
                self.DeploytoProduction()
            elif self.installApp == 'WPCreateBackup':
                self.WPCreateBackup()

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [ApplicationInstaller.run]')

    def installMautic(self):
        try:

            admin = self.extraArgs['admin']
            domainName = self.extraArgs['domainName']
            home = self.extraArgs['home']
            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath
            username = self.extraArgs['username']
            password = self.extraArgs['password']
            email = self.extraArgs['email']

            FNULL = open(os.devnull, 'w')

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ''
            self.permPath = ''

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp
                self.masterDomain = website.master.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)
                self.permPath = website.path

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
                self.masterDomain = website.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)
                self.permPath = '/home/%s/public_html' % (website.domain)

            ## Security Check

            #command = 'chmod 755 %s' % (self.permPath)
            #ProcessUtilities.executioner(command, externalApp)

            if finalPath.find("..") > -1:
                raise BaseException("Specified path must be inside virtual host home.")

            if not os.path.exists(finalPath):
                command = 'mkdir -p ' + finalPath
                ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath, externalApp) == 0:
                raise BaseException('Directory is not empty.')

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Downloading Mautic Core,30')
            statusFile.close()

            command = "wget https://github.com/mautic/mautic/releases/download/%s/%s.zip" % (ApplicationInstaller.MauticVersion, ApplicationInstaller.MauticVersion)
            ProcessUtilities.outputExecutioner(command, externalApp, None, finalPath)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Extracting Mautic Core,50')
            statusFile.close()

            command = "unzip %s.zip" % (ApplicationInstaller.MauticVersion)
            ProcessUtilities.outputExecutioner(command, externalApp, None, finalPath)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Running Mautic installer,70')
            statusFile.close()

            if home == '0':
                path = self.extraArgs['path']
                finalURL = domainName + '/' + path
            else:
                finalURL = domainName

            ACLManager.CreateSecureDir()
            localDB = '%s/%s' % ('/usr/local/CyberCP/tmp', str(randint(1000, 9999)))

            localDBContent = """<?php
// Example local.php to test install (to adapt of course)
$parameters = array(
	// Do not set db_driver and mailer_from_name as they are used to assume Mautic is installed
	'db_host' => 'localhost',
	'db_table_prefix' => null,
	'db_port' => 3306,
	'db_name' => '%s',
	'db_user' => '%s',
	'db_password' => '%s',
	'db_backup_tables' => true,
	'db_backup_prefix' => 'bak_',
	'admin_email' => '%s',
	'admin_password' => '%s',
	'mailer_transport' => null,
	'mailer_host' => null,
	'mailer_port' => null,
	'mailer_user' => null,
	'mailer_password' => null,
	'mailer_api_key' => null,
	'mailer_encryption' => null,
	'mailer_auth_mode' => null,
);""" % (dbName, dbUser, dbPassword, email, password)

            writeToFile = open(localDB, 'w')
            writeToFile.write(localDBContent)
            writeToFile.close()

            command = 'rm -rf %s/app/config/local.php' % (finalPath)
            ProcessUtilities.executioner(command, externalApp)

            command = 'chown %s:%s %s' % (externalApp, externalApp, localDB)
            ProcessUtilities.executioner(command)

            command = 'cp %s %s/app/config/local.php' % (localDB, finalPath)
            ProcessUtilities.executioner(command, externalApp)

            command = "/usr/local/lsws/lsphp74/bin/php bin/console mautic:install http://%s -f" % (finalURL)
            result = ProcessUtilities.outputExecutioner(command, externalApp, None, finalPath)

            if result.find('Install complete') == -1:
                raise BaseException(result)

            os.remove(localDB)
            installUtilities.reStartLiteSpeedSocket()

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            # remove the downloaded files
            FNULL = open(os.devnull, 'w')

            homeDir = "/home/" + domainName + "/public_html"

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                groupName = 'nobody'
            else:
                groupName = 'nogroup'

            if not os.path.exists(homeDir):
                command = "chown " + externalApp + ":" + groupName + " " + homeDir
                ProcessUtilities.executioner(command, externalApp)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def updatePackage(self):
        try:

            package = self.extraArgs['package']

            from serverStatus.serverStatusUtil import ServerStatusUtil

            f = open(ServerStatusUtil.lswsInstallStatusPath, 'a')

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:

                if package == 'all':
                    command = 'DEBIAN_FRONTEND=noninteractive apt-get update -y'
                    f.write(ProcessUtilities.outputExecutioner(command))

                    f.flush()

                    command = 'apt-get upgrade -y'
                    f.write(ProcessUtilities.outputExecutioner(command))
                else:
                    command = 'apt-get install --only-upgrade %s -y' % (package)
                    f.write(ProcessUtilities.outputExecutioner(command))

                f.close()
            elif ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                if package == 'all':
                    command = 'yum update -y'
                    f.write(ProcessUtilities.outputExecutioner(command))
                else:
                    command = 'yum update %s -y' % (package)
                    f.write(ProcessUtilities.outputExecutioner(command))

            f.close()

            logging.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      'Package(s) upgraded successfully. [200]',
                                                      1)

        except BaseException as msg:
            from serverStatus.serverStatusUtil import ServerStatusUtil
            logging.statusWriter(ServerStatusUtil.lswsInstallStatusPath, 'Failed. Error: %s. [404]' % (str(msg)), 1)
            return 0

    def convertDomainToSite(self):
        try:

            from websiteFunctions.website import WebsiteManager
            import json, time

            request = self.extraArgs['request']

            ##

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Deleting domain as child..,20')
            statusFile.close()

            data = json.loads(request.body)

            if data['package'] == None or data['domainName'] == None or data['adminEmail'] == None \
                    or data['phpSelection'] == None or data['websiteOwner'] == None:
                raise BaseException('Please provide all values.')

            domainName = data['domainName']

            childDomain = ChildDomains.objects.get(domain=domainName)
            path = childDomain.path

            wm = WebsiteManager()

            wm.submitDomainDeletion(request.session['userID'], {'websiteName': domainName})
            time.sleep(5)

            ##

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Creating domain as website..,40')
            statusFile.close()

            resp = wm.submitWebsiteCreation(request.session['userID'], data)
            respData = json.loads(resp.content.decode('utf-8'))

            ##

            while True:
                respDataStatus = ProcessUtilities.outputExecutioner("cat " + respData['tempStatusPath'])

                if respDataStatus.find('[200]') > -1:
                    break
                elif respDataStatus.find('[404]') > -1:
                    statusFile = open(self.tempStatusPath, 'w')
                    statusFile.writelines(respDataStatus['currentStatus'] + '  [404]')
                    statusFile.close()
                    return 0
                else:
                    statusFile = open(self.tempStatusPath, 'w')
                    statusFile.writelines(respDataStatus)
                    statusFile.close()
                    time.sleep(1)

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Moving data..,80')
            statusFile.close()


            command = 'rm -rf  /home/%s/public_html' % (domainName)
            ProcessUtilities.executioner(command)

            command = 'mv %s /home/%s/public_html' % (path, domainName)
            ProcessUtilities.executioner(command)

            from filemanager.filemanager import FileManager

            fm = FileManager(None, None)
            fm.fixPermissions(domainName)

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Successfully converted. [200]')
            statusFile.close()

        except BaseException as msg:
            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def installWPCLI(self):
        try:
            command = 'wget -O /usr/bin/wp https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar'
            ProcessUtilities.executioner(command)

            command = 'chmod +x /usr/bin/wp'
            ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [ApplicationInstaller.installWPCLI]')

    def dataLossCheck(self, finalPath, tempStatusPath, user=None):

        if user == None:
            dirFiles = os.listdir(finalPath)

            if len(dirFiles) <= 3:
                return 1
            else:
                return 0
        else:
            command = 'ls %s | wc -l' % (finalPath)
            result = ProcessUtilities.outputExecutioner(command, user, True).rstrip('\n')

            if int(result) <= 3:
                return 1
            else:
                return 0

    def installGit(self):
        try:
            if os.path.exists("/etc/lsb-release"):
                command = 'apt -y install git'
                ProcessUtilities.executioner(command)
            else:

                command = 'yum install git -y'
                ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [ApplicationInstaller.installGit]')

    def dbCreation(self, tempStatusPath, website):
        passFile = "/etc/cyberpanel/mysqlPassword"

        try:
            import json
            jsonData = json.loads(open(passFile, 'r').read())
            mysqlhost = jsonData['mysqlhost']
            ApplicationInstaller.LOCALHOST = mysqlhost
            ApplicationInstaller.REMOTE = 1
            ApplicationInstaller.PORT = jsonData['mysqlport']
        except:
            pass

        try:
            dbName = randomPassword.generate_pass()
            dbUser = dbName
            dbPassword = randomPassword.generate_pass()

            ## DB Creation

            if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(
                    dbUser=dbUser).exists():
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines(
                    "This database or user is already taken." + " [404]")
                statusFile.close()
                return 0

            result = mysqlUtilities.createDatabase(dbName, dbUser, dbPassword)

            if result == 1:
                pass
            else:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines(
                    "Not able to create database." + " [404]")
                statusFile.close()
                return 0

            db = Databases(website=website, dbName=dbName, dbUser=dbUser)
            db.save()

            return dbName, dbUser, dbPassword

        except BaseException as msg:
            logging.writeToFile(str(msg) + '[ApplicationInstallerdbCreation]')

    def installWordPress(self):
        try:
            domainName = self.extraArgs['domainName']
            home = self.extraArgs['home']
            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath
            blogTitle = self.extraArgs['blogTitle']
            adminUser = self.extraArgs['adminUser']
            adminPassword = self.extraArgs['adminPassword']
            adminEmail = self.extraArgs['adminEmail']


            FNULL = open(os.devnull, 'w')

            ### Check WP CLI

            try:
                command = 'wp --info'
                outout = ProcessUtilities.outputExecutioner(command)

                if not outout.find('WP-CLI root dir:') > -1:
                    self.installWPCLI()
            except subprocess.CalledProcessError:
                self.installWPCLI()

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ''
            self.permPath = ''

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp
                self.masterDomain = website.master.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)
                self.permPath = website.path
            except BaseException as msg:

                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
                self.masterDomain = website.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)
                self.permPath = '/home/%s/public_html' % (website.domain)


            ## Security Check

            # command = 'chmod 755 %s' % (self.permPath)
            # ProcessUtilities.executioner(command)

            if finalPath.find("..") > -1:
                raise BaseException("Specified path must be inside virtual host home.")

            ### if directory already exists no issues.
            command = 'mkdir -p ' + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath, externalApp) == 0:
                raise BaseException('Directory is not empty.')

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Downloading WordPress Core,30')
            statusFile.close()

            try:
                command = "wp core download --allow-root --path=%s --version=%s" % (finalPath, self.extraArgs['version'])
            except:
                command = "wp core download --allow-root --path=" + finalPath

            result = ProcessUtilities.outputExecutioner(command, externalApp)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(str(result))

            if result.find('Success:') == -1:
                raise BaseException(result)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Configuring the installation,40')
            statusFile.close()

            command = "wp core config --dbname=" + dbName + " --dbuser=" + dbUser + " --dbpass=" + dbPassword + " --dbhost=%s:%s --dbprefix=wp_ --allow-root --path=" % (ApplicationInstaller.LOCALHOST, ApplicationInstaller.PORT) + finalPath
            result = ProcessUtilities.outputExecutioner(command, externalApp)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(str(result))

            if result.find('Success:') == -1:
                raise BaseException(result)

            if home == '0':
                path = self.extraArgs['path']
                finalURL = domainName + '/' + path
            else:
                finalURL = domainName

            command = 'wp core install --url="http://' + finalURL + '" --title="' + blogTitle + '" --admin_user="' + adminUser + '" --admin_password="' + adminPassword + '" --admin_email="' + adminEmail + '" --allow-root --path=' + finalPath
            result = ProcessUtilities.outputExecutioner(command, externalApp)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(str(result))

            if result.find('Success:') == -1:
                raise BaseException(result)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing LSCache Plugin,80')
            statusFile.close()

            command = "wp plugin install litespeed-cache --allow-root --path=" + finalPath
            result = ProcessUtilities.outputExecutioner(command, externalApp)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(str(result))

            if result.find('Success:') == -1:
                raise BaseException(result)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Activating LSCache Plugin,90')
            statusFile.close()

            command = "wp plugin activate litespeed-cache --allow-root --path=" + finalPath
            result = ProcessUtilities.outputExecutioner(command, externalApp)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(str(result))

            if result.find('Success:') == -1:
                raise BaseException(result)

            try:
                if self.extraArgs['updates']:
                    if self.extraArgs['updates'] == 'Disabled':
                        command = "wp config set WP_AUTO_UPDATE_CORE false --raw --allow-root --path=" + finalPath
                        result = ProcessUtilities.outputExecutioner(command, externalApp)

                        if result.find('Success:') == -1:
                            raise BaseException(result)
                    elif self.extraArgs['updates'] == 'Minor and Security Updates':
                        command = "wp config set WP_AUTO_UPDATE_CORE minor --allow-root --path=" + finalPath
                        result = ProcessUtilities.outputExecutioner(command, externalApp)

                        if result.find('Success:') == -1:
                            raise BaseException(result)
                    else:
                        command = "wp config set WP_AUTO_UPDATE_CORE true --raw --allow-root --path=" + finalPath
                        result = ProcessUtilities.outputExecutioner(command, externalApp)

                        if result.find('Success:') == -1:
                            raise BaseException(result)
            except:
                pass

            try:
                if self.extraArgs['appsSet'] == 'WordPress + LSCache + Classic Editor':

                    command = "wp plugin install classic-editor --allow-root --path=" + finalPath
                    result = ProcessUtilities.outputExecutioner(command, externalApp)

                    if result.find('Success:') == -1:
                        raise BaseException(result)

                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines('Activating Classic Editor Plugin,90')
                    statusFile.close()

                    command = "wp plugin activate classic-editor --allow-root --path=" + finalPath
                    result = ProcessUtilities.outputExecutioner(command, externalApp)

                    if result.find('Success:') == -1:
                        raise BaseException(result)

                elif self.extraArgs['appsSet'] == 'WordPress + LSCache + WooCommerce':

                    command = "wp plugin install woocommerce --allow-root --path=" + finalPath
                    result = ProcessUtilities.outputExecutioner(command, externalApp)

                    if result.find('Success:') == -1:
                        raise BaseException(result)

                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines('Activating WooCommerce Plugin,90')
                    statusFile.close()

                    command = "wp plugin activate woocommerce --allow-root --path=" + finalPath
                    result = ProcessUtilities.outputExecutioner(command, externalApp)

                    if result.find('Success:') == -1:
                        raise BaseException(result)

            except:
                pass




            ############## Install Save Plugin Buckets
            try:
                logging.writeToFile("plugin bucket list start")
                logging.writeToFile("plugin bucket list: %s" % str(self.extraArgs['AllPluginsList']))
                logging.writeToFile("plugin bucket saved: %s" % str(self.extraArgs['SavedPlugins']))
                if self.extraArgs['SavedPlugins'] == True:
                    AllPluginList= self.extraArgs['AllPluginsList']
                    for i in range(len(AllPluginList)):
                        # command = "wp plugin install " + AllPluginList[i]+ "--allow-root --path=" + finalPath
                        command = "wp plugin install %s --allow-root --path=%s" %(AllPluginList[i], finalPath)
                        result = ProcessUtilities.outputExecutioner(command, externalApp)

                        if result.find('Success:') == -1:
                            raise BaseException(result)

                        command = "wp plugin activate %s --allow-root --path=%s"  %(AllPluginList[i], finalPath)
                        result = ProcessUtilities.outputExecutioner(command, externalApp)
            except BaseException as msg:
                logging.writeToFile("Error in istall plugin bucket: %s"%str(msg))
                pass



            ##

            # from filemanager.filemanager import FileManager
            #
            # fm = FileManager(None, None)
            # fm.fixPermissions(self.masterDomain)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            # remove the downloaded files

            if not os.path.exists(ProcessUtilities.debugPath):

                try:
                    mysqlUtilities.deleteDatabase(dbName, dbUser)
                    db = Databases.objects.get(dbName=dbName)
                    db.delete()
                except:
                    pass

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def installPrestaShop(self):
        try:

            admin = self.extraArgs['admin']
            domainName = self.extraArgs['domainName']
            home = self.extraArgs['home']
            shopName = self.extraArgs['shopName']
            firstName = self.extraArgs['firstName']
            lastName = self.extraArgs['lastName']
            databasePrefix = self.extraArgs['databasePrefix']
            email = self.extraArgs['email']
            password = self.extraArgs['password']
            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath

            FNULL = open(os.devnull, 'w')

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ''
            self.permPath = ''

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp
                self.masterDomain = website.master.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path + "/"

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)
                self.permPath = website.path

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
                self.masterDomain = website.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)
                self.permPath = '/home/%s/public_html' % (website.domain)

            ## Security Check

            #command = 'chmod 755 %s' % (self.permPath)
            #ProcessUtilities.executioner(command)

            if finalPath.find("..") > -1:
                raise BaseException('Specified path must be inside virtual host home.')

            ### create folder if exists then move on
            command = 'mkdir -p ' + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath, externalApp) == 0:
                raise BaseException('Directory is not empty.')

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Downloading and extracting PrestaShop Core..,30')
            statusFile.close()

            command = "wget https://download.prestashop.com/download/releases/prestashop_%s.zip -P %s" % (ApplicationInstaller.PrestaVersion,
                finalPath)
            ProcessUtilities.executioner(command, externalApp)

            command = "unzip -o %sprestashop_%s.zip -d " % (finalPath, ApplicationInstaller.PrestaVersion) + finalPath
            ProcessUtilities.executioner(command, externalApp)

            command = "unzip -o %sprestashop.zip -d " % (finalPath) + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Configuring the installation,40')
            statusFile.close()

            if home == '0':
                path = self.extraArgs['path']
                # finalURL = domainName + '/' + path
                finalURL = domainName
            else:
                finalURL = domainName

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing and configuring PrestaShop..,60')
            statusFile.close()

            command = "php " + finalPath + "install/index_cli.php --domain=" + finalURL + \
                      " --db_server=localhost --db_name=" + dbName + " --db_user=" + dbUser + " --db_password=" + dbPassword \
                      + " --name='" + shopName + "' --firstname=" + firstName + " --lastname=" + lastName + \
                      " --email=" + email + " --password=" + password
            ProcessUtilities.executioner(command, externalApp)

            ##

            command = "rm -rf " + finalPath + "install"
            ProcessUtilities.executioner(command, externalApp)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            # remove the downloaded files

            homeDir = "/home/" + domainName + "/public_html"

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                groupName = 'nobody'
            else:
                groupName = 'nogroup'

            if not os.path.exists(homeDir):
                command = "chown -R " + externalApp + ":" + groupName + " " + homeDir
                ProcessUtilities.executioner(command, externalApp)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def installJoomla(self):
        return 0
        try:

            domainName = self.extraArgs['domain']
            password = self.extraArgs['password']
            prefix = self.extraArgs['prefix']
            home = self.extraArgs['home']
            siteName = self.extraArgs['siteName']

            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath

            permPath = '/home/%s/public_html' % (domainName)
            #command = 'chmod 755 %s' % (permPath)
            #ProcessUtilities.executioner(command)

            ## Get Joomla

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp
                self.masterDomain = website.master.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path + "/"

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)
                self.permPath = website.path

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
                self.masterDomain = website.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Installing Joomla Console..,30')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)
                self.permPath = '/home/%s/public_html' % (website.domain)

            ## Dataloss check

            command = 'ls -la %s' % (finalPath)
            result = ProcessUtilities.outputExecutioner(command, externalApp)

            if result.find('No such file or directory') > -1:
                command = 'mkdir %s' % (finalPath)
                ProcessUtilities.executioner(command, externalApp)

            if self.dataLossCheck(finalPath, tempStatusPath, externalApp) == 0:
                raise BaseException('Directory is not empty.')



            ### Decide joomla console path
            import getpass

            if getpass.getuser() == 'root':
                command = 'export COMPOSER_ALLOW_SUPERUSER=1;composer global require joomlatools/console'
                ProcessUtilities.outputExecutioner(command, externalApp, None, self.permPath)
                joomlaPath = '/root/.config/composer/vendor/bin/joomla'
            else:
                command = 'composer global require joomlatools/console'
                ProcessUtilities.outputExecutioner(command, externalApp, None, self.permPath)
                joomlaPath = '/home/%s/.config/composer/vendor/bin/joomla' % (self.masterDomain)

            ## Run the install command

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing Joomla..,40')
            statusFile.close()

            command = '%s site:create %s --mysql-login %s:%s --mysql-database %s --mysql_db_prefix=%s --www %s --sample-data=blog --skip-create-statement' % (joomlaPath, dbUser, dbUser, dbPassword, dbName, prefix , finalPath)

            result = ProcessUtilities.outputExecutioner(command, externalApp)

            if result.find('admin/admin') == -1:
                raise BaseException(result)

            ### Update password as per user requirments

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Updating admin password..,70')
            statusFile.close()

            try:

                salt = randomPassword.generate_pass(32)
                # return salt
                password_hash = hashlib.md5((password + salt).encode('utf-8')).hexdigest()
                password = password_hash + ":" + salt

                import MySQLdb.cursors as cursors
                import MySQLdb as mysql

                conn = mysql.connect(host='localhost', user=dbUser, passwd=dbPassword, port=3306,
                                     cursorclass=cursors.SSCursor)
                cursor = conn.cursor()

                cursor.execute("use %s;UPDATE j_users  SET password = '%s' where username = 'admin';FLUSH PRIVILEGES;" % (dbName, password))

                conn.close()
            except BaseException as msg:
                logging.writeToFile(str(msg))

            try:
                os.remove('/usr/local/CyberCP/joomla.zip')
                os.remove('/usr/local/CyberCP/lscache_plugin.zip')
                os.remove('/usr/local/CyberCP/pkg_lscache.xml')
                os.remove('/usr/local/CyberCP/pkg_script.php')
            except:
                pass

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing LiteSpeed Cache Joomla plugin..,80')
            statusFile.close()

            command = 'wget https://raw.githubusercontent.com/litespeedtech/lscache-joomla/master/package/lscache-1.3.1.zip -O /usr/local/CyberCP/joomla.zip'
            ProcessUtilities.executioner(command)

            command = 'unzip -o /usr/local/CyberCP/joomla.zip -d /usr/local/CyberCP/'
            ProcessUtilities.executioner(command)

            command = '%s extension:installfile %s --www %s /usr/local/CyberCP/lscache_plugin.zip' % (joomlaPath, dbUser, finalPath)
            ProcessUtilities.executioner(command)

            command = '%s extension:installfile %s --www %s /usr/local/CyberCP/com_lscache.zip' % (joomlaPath, dbUser, finalPath)
            ProcessUtilities.executioner(command)

            command = '%s extension:enable %s --www %s lscache' % (joomlaPath, dbUser, finalPath)

            ProcessUtilities.executioner(command)

            command = 'mv %s%s/* %s' % (finalPath, dbUser, finalPath)
            ProcessUtilities.executioner(command, None, True)

            command = 'mv %s%s/.[^.]* %s' % (finalPath, dbUser, finalPath)
            ProcessUtilities.executioner(command, None, True)

            command = "sed -i 's|$debug = 1|$debug = 0|g' %sconfiguration.php" % (finalPath)
            ProcessUtilities.executioner(command, None, True)

            ##

            from filemanager.filemanager import FileManager

            fm = FileManager(None, None)
            fm.fixPermissions(self.masterDomain)


            command = "sed -i \"s|sitename = '%s'|sitename = '%s'|g\" %sconfiguration.php" % (
            dbUser, siteName, finalPath)
            ProcessUtilities.executioner(command, externalApp, True)

            installUtilities.reStartLiteSpeedSocket()

            content = """
            =====================================================================
                    Joomla Successfully installed, login details below:
                                Username: admin
                                Password: %s
            =====================================================================
            """ % (self.extraArgs['password'])

            print(content)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0

        except BaseException as msg:
            # remove the downloaded files

            from filemanager.filemanager import FileManager

            fm = FileManager(None, None)
            fm.fixPermissions(self.masterDomain)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            permPath = '/home/%s/public_html' % (domainName)
            command = 'chmod 750 %s' % (permPath)
            ProcessUtilities.executioner(command)

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            logging.writeToFile(str(msg))
            return 0

    # def installMagento(self):
    #     try:
    #
    #         username = self.extraArgs['username']
    #         domainName = self.extraArgs['domainName']
    #         home = self.extraArgs['home']
    #         firstName = self.extraArgs['firstName']
    #         lastName = self.extraArgs['lastName']
    #         email = self.extraArgs['email']
    #         password = self.extraArgs['password']
    #         tempStatusPath = self.extraArgs['tempStatusPath']
    #         sampleData = self.extraArgs['sampleData']
    #         self.tempStatusPath = tempStatusPath
    #
    #         FNULL = open(os.devnull, 'w')
    #
    #         ## Open Status File
    #
    #         statusFile = open(tempStatusPath, 'w')
    #         statusFile.writelines('Setting up paths,0')
    #         statusFile.close()
    #
    #         finalPath = ''
    #         self.premPath = ''
    #
    #         try:
    #             website = ChildDomains.objects.get(domain=domainName)
    #             externalApp = website.master.externalApp
    #             self.masterDomain = website.master.domain
    #
    #             if home == '0':
    #                 path = self.extraArgs['path']
    #                 finalPath = website.path.rstrip('/') + "/" + path + "/"
    #             else:
    #                 finalPath = website.path + "/"
    #
    #             if website.master.package.dataBases > website.master.databases_set.all().count():
    #                 pass
    #             else:
    #                 raise BaseException( "Maximum database limit reached for this website.")
    #
    #             statusFile = open(tempStatusPath, 'w')
    #             statusFile.writelines('Setting up Database,20')
    #             statusFile.close()
    #
    #             dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)
    #             self.permPath = website.path
    #
    #         except:
    #             website = Websites.objects.get(domain=domainName)
    #             externalApp = website.externalApp
    #             self.masterDomain = website.domain
    #
    #             if home == '0':
    #                 path = self.extraArgs['path']
    #                 finalPath = "/home/" + domainName + "/public_html/" + path + "/"
    #             else:
    #                 finalPath = "/home/" + domainName + "/public_html/"
    #
    #             if website.package.dataBases > website.databases_set.all().count():
    #                 pass
    #             else:
    #                 raise BaseException( "Maximum database limit reached for this website.")
    #
    #             statusFile = open(tempStatusPath, 'w')
    #             statusFile.writelines('Setting up Database,20')
    #             statusFile.close()
    #
    #             dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)
    #             self.permPath = '/home/%s/public_html' % (website.domain)
    #
    #         ## Security Check
    #
    #         if finalPath.find("..") > -1:
    #             raise BaseException( "Specified path must be inside virtual host home.")
    #
    #         command = 'chmod 755 %s' % (self.permPath)
    #         ProcessUtilities.executioner(command)
    #
    #         if not os.path.exists(finalPath):
    #             command = 'mkdir -p ' + finalPath
    #             ProcessUtilities.executioner(command, externalApp)
    #
    #         ## checking for directories/files
    #
    #         if self.dataLossCheck(finalPath, tempStatusPath) == 0:
    #             raise BaseException('Directory not empty.')
    #
    #         ####
    #
    #         statusFile = open(tempStatusPath, 'w')
    #         statusFile.writelines('Downloading Magento Community Core via composer to document root ..,30')
    #         statusFile.close()
    #
    #         command = 'composer create-project --repository-url=https://repo.magento.com/ magento/project-community-edition %s' % (finalPath)
    #
    #         ProcessUtilities.executioner(command, externalApp)
    #
    #         ###
    #
    #         statusFile = open(tempStatusPath, 'w')
    #         statusFile.writelines('Configuring the installation,40')
    #         statusFile.close()
    #
    #         if home == '0':
    #             path = self.extraArgs['path']
    #             # finalURL = domainName + '/' + path
    #             finalURL = domainName
    #         else:
    #             finalURL = domainName
    #
    #         statusFile = open(tempStatusPath, 'w')
    #         statusFile.writelines('Installing and configuring Magento..,60')
    #         statusFile.close()
    #
    #         command = '/usr/local/lsws/lsphp73/bin/php -d memory_limit=512M %sbin/magento setup:install --base-url="http://%s" ' \
    #                   ' --db-host="localhost" --db-name="%s" --db-user="%s" --db-password="%s" --admin-firstname="%s" ' \
    #                   ' --admin-lastname="%s" --admin-email="%s" --admin-user="%s" --admin-password="%s" --language="%s" --timezone="%s" ' \
    #                   ' --use-rewrites=1 --search-engine="elasticsearch7" --elasticsearch-host="localhost" --elasticsearch-port="9200" ' \
    #                   ' --elasticsearch-index-prefix="%s"' \
    #                   % (finalPath, finalURL, dbName, dbUser, dbPassword, firstName, lastName, email, username, password, 'language', 'timezone', dbName )
    #
    #         result = ProcessUtilities.outputExecutioner(command, externalApp)
    #         logging.writeToFile(result)
    #
    #         ##
    #
    #         ProcessUtilities.executioner(command, externalApp)
    #
    #         ##
    #
    #         from filemanager.filemanager import FileManager
    #
    #         fm = FileManager(None, None)
    #         fm.fixPermissions(self.masterDomain)
    #
    #         installUtilities.reStartLiteSpeed()
    #
    #         statusFile = open(tempStatusPath, 'w')
    #         statusFile.writelines("Successfully Installed. [200]")
    #         statusFile.close()
    #         return 0
    #
    #
    #     except BaseException as msg:
    #         # remove the downloaded files
    #
    #         homeDir = "/home/" + domainName + "/public_html"
    #
    #         if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
    #             groupName = 'nobody'
    #         else:
    #             groupName = 'nogroup'
    #
    #         if not os.path.exists(homeDir):
    #             command = "chown -R " + externalApp + ":" + groupName + " " + homeDir
    #             ProcessUtilities.executioner(command, externalApp)
    #
    #         try:
    #             mysqlUtilities.deleteDatabase(dbName, dbUser)
    #             db = Databases.objects.get(dbName=dbName)
    #             db.delete()
    #         except:
    #             pass
    #
    #         permPath = '/home/%s/public_html' % (domainName)
    #         command = 'chmod 750 %s' % (permPath)
    #         ProcessUtilities.executioner(command)
    #
    #         statusFile = open(self.tempStatusPath, 'w')
    #         statusFile.writelines(str(msg) + " [404]")
    #         statusFile.close()
    #         return 0

    def DeployWordPress(self):
        try:

            if self.extraArgs['createSite']:
                logging.statusWriter(self.extraArgs['tempStatusPath'], 'Creating this application..,10')

                ## Create site

                import re
                from plogical.virtualHostUtilities import virtualHostUtilities
                tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))
                externalApp = "".join(re.findall("[a-zA-Z]+", self.extraArgs['domain']))[:5] + str(randint(1000, 9999))

                virtualHostUtilities.createVirtualHost(self.extraArgs['domain'], self.extraArgs['email'], 'PHP 7.4',
                                                       externalApp, 1, 1, 0,
                                                       'admin', 'Default', 0, tempStatusPath,
                                                       0)
                result = open(tempStatusPath, 'r').read()
                if result.find('[404]') > -1:
                    logging.statusWriter(self.extraArgs['tempStatusPath'], 'Failed to create application. Error: %s [404]' % (result))
                    return 0

            ## Install WordPress

            logging.statusWriter(self.extraArgs['tempStatusPath'], 'Installing WordPress.,50')

            currentTemp = self.extraArgs['tempStatusPath']
            self.extraArgs['domainName'] = self.extraArgs['domain']
            self.extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))
            self.extraArgs['blogTitle'] = self.extraArgs['title']
            self.extraArgs['adminUser'] = self.extraArgs['userName']
            self.extraArgs['adminPassword'] = self.extraArgs['password']
            self.extraArgs['adminEmail'] = self.extraArgs['email']

            self.installWordPress()

            result = open(self.extraArgs['tempStatusPath'], 'r').read()
            if result.find('[404]') > -1:
                self.extraArgs['tempStatusPath'] = currentTemp
                raise BaseException('Failed to install WordPress. Error: %s [404]' % (result))

            self.extraArgs['tempStatusPath'] = currentTemp


            logging.statusWriter(self.extraArgs['tempStatusPath'], 'Completed [200].')

            try:
                ### Save config in db

                from cloudAPI.models import WPDeployments
                from websiteFunctions.models import Websites
                import json

                website = Websites.objects.get(domain=self.extraArgs['domain'])
                del self.extraArgs['adminPassword']
                del self.extraArgs['password']
                del self.extraArgs['tempStatusPath']
                del self.extraArgs['domain']
                del self.extraArgs['adminEmail']
                del self.extraArgs['adminUser']
                del self.extraArgs['blogTitle']
                del self.extraArgs['appsSet']

                wpDeploy = WPDeployments(owner=website, config=json.dumps(self.extraArgs))
                wpDeploy.save()
            except:
                pass

            ## Set up cron if missing

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                localCronPath = "/var/spool/cron/root"
            else:
                localCronPath = "/var/spool/cron/crontabs/root"

            cronData = open(localCronPath, 'r').read()

            if cronData.find('WPAutoUpdates.py') == -1:
                writeToFile = open(localCronPath, 'a')
                writeToFile.write('0 12 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/WPAutoUpdates.py\n')
                writeToFile.close()

        except BaseException as msg:
            self.extraArgs['websiteName'] = self.extraArgs['domain']
            from websiteFunctions.website import WebsiteManager
            wm = WebsiteManager()
            wm.submitWebsiteDeletion(1, self.extraArgs)
            logging.statusWriter(self.extraArgs['tempStatusPath'], '%s [404].' % (str(msg)))

    def installWhmcs(self):
        try:

            admin = self.extraArgs['admin']
            domainName = self.extraArgs['domainName']
            home = self.extraArgs['home']
            firstName = self.extraArgs['firstName']
            lastName = self.extraArgs['lastName']
            email = self.extraArgs['email']
            username = self.extraArgs['username']
            password = self.extraArgs['password']
            whmcs_installer = self.extraArgs['whmcsinstallerpath']
            whmcs_licensekey = self.extraArgs['whmcslicensekey']
            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath

            FNULL = open(os.devnull, 'w')

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ''
            self.permPath = ''

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp
                self.masterDomain = website.master.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path + "/"

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)
                self.permPath = website.path

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
                self.masterDomain = website.domain

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    raise BaseException("Maximum database limit reached for this website.")

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)
                self.permPath = '/home/%s/public_html' % (website.domain)

            ## Security Check

            command = 'chmod 755 %s' % (self.permPath)
            ProcessUtilities.executioner(command)

            if finalPath.find("..") > -1:
                raise BaseException('Specified path must be inside virtual host home.')

            if not os.path.exists(finalPath):
                command = 'mkdir -p ' + finalPath
                ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath) == 0:
                raise BaseException('Directory is not empty.')

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Extracting WHMCS Installer zip..,30')
            statusFile.close()
            command = "unzip -qq %s -d %s" % (whmcs_installer, finalPath)
            ProcessUtilities.executioner(command, externalApp)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Configuring the installation,40')
            statusFile.close()

            if home == '0':
                path = self.extraArgs['path']
                # finalURL = domainName + '/' + path
                finalURL = domainName
            else:
                finalURL = domainName

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing and configuring WHMCS..,60')
            statusFile.close()

            command = "chown -R " + externalApp + ":" + groupName + " " + homeDir
            ProcessUtilities.executioner(command, externalApp)

            # Walk through whmcs webinstaller via curl with all except errors hidden https://stackoverflow.com/a/49502232
            # Accept EULA and generate configuration.php
            command = "curl %s/install/install.php?step=2 --insecure --silent --output /dev/null --show-error --fail" % (finalURL)
            ProcessUtilities.executioner(command, externalApp)

            command = "curl %s/install/install.php?step=2 --insecure --silent --output /dev/null --show-error --fail" % (finalURL)
            ProcessUtilities.executioner(command, externalApp)

            command = "mv %s/configuration.php.new %s/configuration.php" % (finalPath, finalPath)
            ProcessUtilities.executioner(command, externalApp)

            # Post database and license information to webinstaller form
            command = """
            curl %s/install/install.php?step=4" \
            -H 'Content-Type: application/x-www-form-urlencoded' \
            --data "licenseKey=%s&databaseHost=localhost&databasePort=&databaseUsername=%s&databasePassword=%s&databaseName=%s" \
            --compressed \
            --insecure \
            --silent \
            --output /dev/null \
            --show-error \
            --fail
            """ % (whmcs_licensekey, dbUser, dbPassword, dbName)

            # Post admin user and password information to webinstaller form
            command = """
            curl %s/install/install.php?step=5" \
            -H 'Content-Type: application/x-www-form-urlencoded' \
            --data "firstName=%s&lastName=%s&email=%s&username=%s&password=%s&confirmPassword=%s" \
            --compressed \
            --insecure \
            --silent \
            --output /dev/null \
            --show-error \
            --fail
            """ % (firstName, lastName, email, username, password, password)

            ##

            command = "rm -rf " + finalPath + "install"
            ProcessUtilities.executioner(command, externalApp)


            ### Update whmcs urls to siteurl

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Update whmcs urls to siteurl..,70')
            statusFile.close()

            try:

                import MySQLdb.cursors as cursors
                import MySQLdb as mysql

                conn = mysql.connect(host='localhost', user=dbUser, passwd=dbPassword, port=3306,
                                     cursorclass=cursors.SSCursor)
                cursor = conn.cursor()

                cursor.execute("use %s;UPDATE tblconfiguration SET value='%s' WHERE setting='SystemURL';" % (dbName, finalURL))
                cursor.execute("use %s;UPDATE tblconfiguration SET value='%s' WHERE setting='Domain';" % (dbName, finalURL))
                cursor.execute("use %s;UPDATE tblconfiguration SET value='%s' WHERE setting='SystemSSLURL';" % (dbName, finalURL))

                conn.close()
            except BaseException as msg:
                logging.writeToFile(str(msg))



            # Secure WHMCS configuration.php file : https://docs.whmcs.com/Further_Security_Steps#Secure_the_configuration.php_File
            command = "chmod 400 %s/configuration.php" % (finalPath)
            ProcessUtilities.executioner(command)

            ##

            from filemanager.filemanager import FileManager

            fm = FileManager(None, None)
            fm.fixPermissions(self.masterDomain)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            # remove the downloaded files

            homeDir = "/home/" + domainName + "/public_html"

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                groupName = 'nobody'
            else:
                groupName = 'nogroup'

            if not os.path.exists(homeDir):
                command = "chown -R " + externalApp + ":" + groupName + " " + homeDir
                ProcessUtilities.executioner(command, externalApp)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            command = 'chmod 750 %s' % (self.permPath)
            ProcessUtilities.executioner(command)

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def wordpressInstallNew(self):
        try:
            from websiteFunctions.website import WebsiteManager
            import json
            tempStatusPath = self.data['tempStatusPath']
            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating Website...,10')
            statusFile.close()


            DataToPass = {}

            currentTemp = self.extraArgs['tempStatusPath']
            DataToPass['domainName'] = self.data['domainName']
            DataToPass['adminEmail'] = self.data['adminEmail']
            DataToPass['phpSelection'] = "PHP 7.4"
            DataToPass['websiteOwner'] = self.data['websiteOwner']
            DataToPass['package'] = self.data['package']
            DataToPass['ssl'] = 1
            DataToPass['dkimCheck'] = 0
            DataToPass['openBasedir'] = 0
            DataToPass['mailDomain'] = 0
            UserID = self.data['adminID']

            try:
                website = Websites.objects.get(domain=DataToPass['domainName'])

                if ACLManager.checkOwnership(website.domain, self.extraArgs['adminID'], self.extraArgs['currentACL']) == 0:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines('You dont own this site.[404]')
                    statusFile.close()
            except:

                ab = WebsiteManager()
                coreResult = ab.submitWebsiteCreation(UserID, DataToPass)
                coreResult1 = json.loads((coreResult).content)
                logging.writeToFile("Creating website result....%s"%coreResult1)
                reutrntempath = coreResult1['tempStatusPath']
                while (1):
                    lastLine = open(reutrntempath, 'r').read()
                    logging.writeToFile("Error web creating lastline ....... %s" % lastLine)
                    if lastLine.find('[200]') > -1:
                        break
                    elif lastLine.find('[404]') > -1:
                        statusFile = open(currentTemp, 'w')
                        statusFile.writelines('Failed to Create Website: error: %s. [404]' % lastLine)
                        statusFile.close()
                        return 0
                    else:
                        statusFile = open(currentTemp, 'w')
                        statusFile.writelines('Creating Website....,20')
                        statusFile.close()
                        time.sleep(2)

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Installing WordPress....,30')
                statusFile.close()

            logging.writeToFile("Pluginbucket  ....... %s" % str(self.data['pluginbucket']))


            ## Install WordPress
                ## get save pluginbucket

            ###Get save plugin
            SavedPlugins = False
            AllPluginsList = []
            try:
                if(self.data['pluginbucket'] != 1):
                    bucktobj = wpplugins.objects.get(pk=self.data['pluginbucket'])
                    pluginlistt = json.loads(bucktobj.config)
                    SavedPlugins = True
                    for i in range(len(pluginlistt)):
                             AllPluginsList.append(pluginlistt[i])
            except BaseException as msg:
                logging.writeToFile("Error in Get save plugin  ....... %s" % str(msg))
                pass

            logging.writeToFile("AllPluginsList 1  ....... %s" % str(AllPluginsList))
            logging.writeToFile("SavedPlugins 1  ....... %s" % str(SavedPlugins))

            currentTemp = self.extraArgs['tempStatusPath']
            self.extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))
            self.extraArgs['SavedPlugins'] = SavedPlugins
            self.extraArgs['AllPluginsList'] = AllPluginsList
            self.installWordPress()

            while (1):
                lastLine = open(self.extraArgs['tempStatusPath'], 'r').read()

                if lastLine.find('[200]') > -1:
                    break
                elif lastLine.find('[404]') > -1:
                    statusFile = open(currentTemp, 'w')
                    statusFile.writelines('Failed to install WordPress: error: %s[404]' % lastLine)
                    statusFile.close()
                    return 0
                else:
                    statusFile = open(currentTemp, 'w')
                    statusFile.writelines('Installing WordPress....,50')
                    statusFile.close()
                    time.sleep(2)

            statusFile = open(currentTemp, 'w')
            statusFile.writelines('WordPress installed..,70')
            statusFile.close()


            webobj = Websites.objects.get(domain= self.extraArgs['domainName'])

            path ="/home/%s/public_html"%(self.extraArgs['domainName'])
            Finalurl = (self.extraArgs['domainName'])

            wpobj = WPSites(owner=webobj, title=self.extraArgs['blogTitle'], path=path, FinalURL=Finalurl,
                            AutoUpdates=(self.extraArgs['updates']), PluginUpdates=(self.extraArgs['Plugins']),
                            ThemeUpdates=(self.extraArgs['Themes']),)
            wpobj.save()

            statusFile = open(currentTemp, 'w')
            statusFile.writelines('WordPress installed..,[200]')
            statusFile.close()


        except BaseException as msg:
            logging.writeToFile("Error WP web creating  ....... %s" % str(msg))
            return 0

    def UpdateWPTheme(self):
        try:
            FinalPHPPath = self.data['FinalPHPPath']
            Vhuser=self.data['Vhuser']
            path=self.data['path']

            if self.data['Theme'] == 'all':
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme update --all --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)



            elif self.data['Theme'] == 'selected':

                ThemeList = ''

                for plugin in self.data['Themearray']:
                    ThemeList = '%s %s' % (ThemeList, plugin)

                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme update %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, ThemeList, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)


            else:
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme update %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, self.data['Theme'], path)
                stdoutput = ProcessUtilities.outputExecutioner(command)

        except BaseException as msg:
            logging.writeToFile("Error WP UpdateWPTheme ....... %s" % str(msg))
            return 0

    def UpdateWPPlugin(self):
        try:
            FinalPHPPath = self.data['FinalPHPPath']
            Vhuser=self.data['Vhuser']
            path=self.data['path']

            if self.data['plugin'] == 'all':
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme update --all --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)




            elif self.data['plugin'] == 'selected':

                pluginsList = ''

                for plug in self.data['pluginarray']:
                    pluginsList = '%s %s' % (pluginsList, plug)

                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin update %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, pluginsList, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)


            else:
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme update %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, self.data['plugin'], path)
                stdoutput = ProcessUtilities.outputExecutioner(command)

        except BaseException as msg:
            logging.writeToFile("Error WP UpdateWPTheme ....... %s" % str(msg))
            return 0

    def DeleteThemes(self):
        try:
            FinalPHPPath = self.data['FinalPHPPath']
            Vhuser = self.data['Vhuser']
            path = self.data['path']
            if self.data['Theme'] == 'selected':
                ThemeList = ''

                for plugin in self.data['Themearray']:
                    ThemeList = '%s %s' % (ThemeList, plugin)

                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme delete %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, ThemeList, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)

            else:
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme delete %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, self.data['Theme'], path)
                stdoutput = ProcessUtilities.outputExecutioner(command)


        except BaseException as msg:
            logging.writeToFile("Error WP DeleteThemes ....... %s" % str(msg))
            return 0

    def DeletePlugins(self):
        try:
            FinalPHPPath = self.data['FinalPHPPath']
            Vhuser = self.data['Vhuser']
            path = self.data['path']
            plugin = self.data['plugin']
            pluginarray = self.data['pluginarray']


            if plugin == 'selected':
                pluginsList = ''

                for plug in pluginarray:
                    pluginsList = '%s %s' % (pluginsList, plug)

                    command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin delete %s --skip-plugins --skip-themes --path=%s' % (Vhuser, FinalPHPPath, pluginsList, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)

            else:
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin delete %s --skip-plugins --skip-themes --path=%s' % (Vhuser, FinalPHPPath, plugin, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)


        except BaseException as msg:
            logging.writeToFile("Error WP DeletePlugins ....... %s" % str(msg))
            return 0

    def ChangeStatusThemes(self):
        try:
            FinalPHPPath = self.data['FinalPHPPath']
            Vhuser = self.data['Vhuser']
            path = self.data['path']
            Theme = self.data['Theme']

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme status %s --skip-plugins --skip-themes --path=%s' % (
            Vhuser, FinalPHPPath, Theme, path)
            stdoutput = ProcessUtilities.outputExecutioner(command)

            if stdoutput.find('Status: Active') > -1:
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme deactivate %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, Theme, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)

            else:

                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme activate %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, Theme, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)


        except BaseException as msg:
            logging.writeToFile("Error WP ChangeStatusThemes ....... %s" % str(msg))
            return 0

    def CreateStagingNow(self):
        try:
            from websiteFunctions.website import WebsiteManager
            import json

            ## Source object

            wpobj = WPSites.objects.get(pk=self.data['WPid'])

            ### Create secure folder
            ACLManager.CreateSecureDir()
            tempPath = '%s/%s' % ('/usr/local/CyberCP/tmp', str(randint(1000, 9999)))
            self.tempPath = tempPath

            command = f'mkdir -p {tempPath}'
            ProcessUtilities.executioner(command)

            command = f'chown -R {wpobj.owner.externalApp}:{wpobj.owner.externalApp} {tempPath}'
            ProcessUtilities.executioner(command)

            tempStatusPath = self.data['tempStatusPath']
            self.tempStatusPath = tempStatusPath
            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating Website...,15')
            statusFile.close()

            DataToPass = {}

            currentTemp = self.extraArgs['tempStatusPath']
            DataToPass['domainName'] = self.data['StagingDomain']
            DataToPass['adminEmail'] = wpobj.owner.adminEmail
            DataToPass['phpSelection'] = wpobj.owner.phpSelection
            DataToPass['websiteOwner'] = wpobj.owner.admin.userName
            DataToPass['package'] = 'Default'
            DataToPass['ssl'] = 1
            DataToPass['dkimCheck'] = 0
            DataToPass['openBasedir'] = 0
            DataToPass['mailDomain'] = 0
            UserID = self.data['adminID']

            ab = WebsiteManager()
            coreResult = ab.submitWebsiteCreation(UserID, DataToPass)
            coreResult1 = json.loads((coreResult).content)

            if os.path.exists('/usr/local/CyberCP/debug'):
                logging.writeToFile("Creating website result....%s" % coreResult1)

            reutrntempath = coreResult1['tempStatusPath']

            while (1):
                lastLine = open(reutrntempath, 'r').read()

                if lastLine.find('[200]') > -1:
                    break
                elif lastLine.find('[404]') > -1:
                    statusFile = open(currentTemp, 'w')
                    statusFile.writelines('Failed to Create Website: error: %s[404]' % lastLine)
                    statusFile.close()
                    return 0
                else:
                    statusFile = open(currentTemp, 'w')
                    statusFile.writelines('Creating Website....,20')
                    statusFile.close()
                    time.sleep(2)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing WordPress....,30')
            statusFile.close()

            ####No crreating DataBAse.............

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating DataBase....,30')
            statusFile.close()
            website = Websites.objects.get(domain=self.data['StagingDomain'])

            dbNameRestore, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating Staging....,50')
            statusFile.close()


            masterDomain= wpobj.owner.domain
            domain = self.data['StagingDomain']

            path= wpobj.path

            PHPVersion = website.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            ## Staging site

            StagingPath = f'/home/{website.domain}/public_html'

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp core download --path={StagingPath}'

            if ProcessUtilities.executioner(command, website.externalApp) == 0:
                raise BaseException('Failed to download wp core. [404]')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp core config --dbname={dbNameRestore} --dbuser={dbUser} --dbpass={dbPassword} --dbhost={ApplicationInstaller.LOCALHOST}:{ApplicationInstaller.PORT} --path={StagingPath}'
            if ProcessUtilities.executioner(command, website.externalApp) == 0:
                raise BaseException('WP Core congiruations failed. [404]')


            ### Get table prefix of master site

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config get table_prefix --skip-plugins --skip-themes --path={path}'
            TablePrefix = ProcessUtilities.outputExecutioner(command, wpobj.owner.externalApp).rstrip('\n')

            ## Export database from master site

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path={path} db export {tempPath}/dbexport-stage.sql'
            if ProcessUtilities.executioner(command, wpobj.owner.externalApp) == 0:
                raise BaseException('Failed to export database from master site. [404]')

            ## Copy wp content folder to securey path

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp theme path --skip-plugins --skip-themes --allow-root --path={path}'
            WpContentPath = ProcessUtilities.outputExecutioner(command, wpobj.owner.externalApp).splitlines()[-1].replace('themes', '')

            command = f'cp -R {WpContentPath} {tempPath}/'
            if ProcessUtilities.executioner(command, wpobj.owner.externalApp) == 0:
                raise BaseException('Failed to copy wp-content from master to temp folder. [404]')

            command = f'cp -f {path}/.htaccess {tempPath}/'

            if ProcessUtilities.executioner(command, wpobj.owner.externalApp) == 0:
                logging.writeToFile('While staging creation .htaccess file did not copy')

            ### Set table prefix

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config set table_prefix {TablePrefix} --path={StagingPath}'
            if ProcessUtilities.executioner(command, website.externalApp) == 0:
                raise BaseException('Failed to set table prefix on staging site. [404]')

            ### Change permissions of temp folder to staging site

            command = f'chown -R {website.externalApp}:{website.externalApp} {tempPath}'
            ProcessUtilities.executioner(command)


            ## Import Database

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path={StagingPath} --quiet db import {tempPath}/dbexport-stage.sql'
            if ProcessUtilities.executioner(command, website.externalApp) ==0:
                raise BaseException('Failed to import database on staging site. [404]')

            try:
                command = 'rm -f %s/dbexport-stage.sql' % (tempPath)
                ProcessUtilities.executioner(command, website.externalApp)
            except:
                pass

            ## Move wp-content from temp tp staging

            command = f'rm -rf {StagingPath}/wp-content'
            ProcessUtilities.executioner(command, website.externalApp)

            command = f'mv {tempPath}/wp-content {StagingPath}/'
            if ProcessUtilities.executioner(command, website.externalApp) == 0:
                raise BaseException('Failed to copy wp-content from temp to staging site. [404]')

            ## Copy htaccess

            command = f'cp -f {tempPath}/.htaccess {StagingPath}/'
            if ProcessUtilities.executioner(command, wpobj.owner.externalApp) == 0:
                logging.writeToFile('While staging creation .htaccess file did not copy')

            ## Search and replace url

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --path={StagingPath} "{masterDomain}" "{domain}"'
            if ProcessUtilities.executioner(command, website.externalApp) == 0:
                raise BaseException('search-replace failed 1. [404]')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --path={StagingPath} "www.{masterDomain}" "{domain}"'
            if ProcessUtilities.executioner(command,website.externalApp) == 0:
                raise BaseException('search-replace failed 2. [404]')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --path={StagingPath} "https://{domain}" "http://{domain}"'
            if ProcessUtilities.executioner(command,website.externalApp) == 0:
                raise BaseException('search-replace failed 3. [404]')

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeed()

            wpsite = WPSites(owner=website,  title=self.data['StagingName'],
                             path ="/home/%s/public_html"%(self.extraArgs['StagingDomain']),
                             FinalURL='%s' % (self.data['StagingDomain']))
            wpsite.save()

            command = f'rm -rf {tempPath}'
            ProcessUtilities.executioner(command)

            WPStaging(wpsite=wpsite, owner=wpobj).save()


            statusFile = open(currentTemp, 'w')
            statusFile.writelines('Staging site created,[200]')
            statusFile.close()

        except BaseException as msg:
            command = f'rm -rf {self.tempPath}'
            ProcessUtilities.executioner(command)
            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(f'{str(msg)}[404]')
            statusFile.close()
            return 0


    def DeploytoProduction(self):

        try:
            self.tempStatusPath = self.extraArgs['tempStatusPath']
            self.statgingID = self.extraArgs['statgingID']
            self.WPid = self.extraArgs['WPid']

            StagingSite = WPSites.objects.get(pk=self.statgingID)
            WPSite = WPSites.objects.get(pk=self.WPid)

            ### Create secure folder
            ACLManager.CreateSecureDir()
            self.tempPath = '%s/%s' % ('/usr/local/CyberCP/tmp', str(randint(1000, 9999)))

            command = f'mkdir -p {self.tempPath}'
            ProcessUtilities.executioner(command)

            command = f'chown -R {StagingSite.owner.externalApp}:{StagingSite.owner.externalApp} {self.tempPath}'
            ProcessUtilities.executioner(command)


            from managePHP.phpManager import PHPManager
            php = PHPManager.getPHPString(StagingSite.owner.phpSelection)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            ## Restore db

            logging.statusWriter(self.tempStatusPath, 'Creating database backup..,10')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path={StagingSite.path} db export {self.tempPath}/dbexport-stage.sql'
            if ProcessUtilities.executioner(command) == 0:
                raise BaseException('Failed to create database backup of staging site. [404]')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp theme path --skip-plugins --skip-themes --allow-root --path={WPSite.path}'
            WpContentPath = ProcessUtilities.outputExecutioner(command, StagingSite.owner.externalApp).splitlines()[-1].replace('themes', '')

            logging.statusWriter(self.tempStatusPath, 'Moving staging site content..,20')

            command = f'cp -R {StagingSite.path}/wp-content/ {self.tempPath}/'
            if ProcessUtilities.executioner(command, StagingSite.owner.externalApp) ==0:
                raise BaseException('Failed copy wp-content from staging to temp folder. [404]')

            command = f'cp -f {StagingSite.path}/.htaccess {self.tempPath}/'
            ProcessUtilities.executioner(command, StagingSite.owner.externalApp)

            ### First import db backup to main site

            command = f'chown -R {WPSite.owner.externalApp}:{WPSite.owner.externalApp} {self.tempPath}'
            ProcessUtilities.executioner(command)

            ## Import Database

            logging.statusWriter(self.tempStatusPath, 'Importing database..,60')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path={WPSite.path} --quiet db import {self.tempPath}/dbexport-stage.sql'
            if ProcessUtilities.executioner(command, WPSite.owner.externalApp) == 0:
                raise BaseException('Failed to import database backup into master site. [404]')

            try:
                command = 'rm -f %s/dbexport-stage.sql' % (self.tempPath)
                ProcessUtilities.executioner(command)
            except:
                pass

            logging.statusWriter(self.tempStatusPath, 'Moving content..,80')


            command = f'cp -R {self.tempPath}/wp-content/* {WpContentPath}'
            if ProcessUtilities.executioner(command, WPSite.owner.externalApp) == 0:
                raise BaseException('Failed to copy wp-content to master site. [404]')

            ## Search and replace url

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --path={WPSite.path} "{StagingSite.FinalURL}" "{WPSite.FinalURL}"'
            if ProcessUtilities.executioner(command, WPSite.owner.externalApp) == 0:
                raise BaseException('search-replace failed 1. [404]')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --path={WPSite.path} "www.{StagingSite.FinalURL}" "{WPSite.FinalURL}"'
            if ProcessUtilities.executioner(command, WPSite.owner.externalApp) == 0:
                raise BaseException('search-replace failed 2. [404]')

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --path={WPSite.path} "https://{WPSite.FinalURL}" "http://{WPSite.FinalURL}"'
            if ProcessUtilities.executioner(command, WPSite.owner.externalApp) == 0:
                raise BaseException('search-replace failed 3. [404]')

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeed()


            command = f'rm -rf {self.tempPath}'
            ProcessUtilities.executioner(command)


            logging.statusWriter(self.tempStatusPath, 'Completed.[200]')

            return 0
        except BaseException as msg:
            command = f'rm -rf {self.tempPath}'
            ProcessUtilities.executioner(command)
            mesg = '%s. [404]' % (str(msg))
            logging.statusWriter(self.tempStatusPath, mesg)

    def WPCreateBackup(self):
        try:
            from managePHP.phpManager import PHPManager
            import json
            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating BackUp...,10')
            statusFile.close()
            wpsite = WPSites.objects.get(pk=self.extraArgs['WPid'])

            website =Websites.objects.get(pk=wpsite.owner_id)
            PhpVersion = website.phpSelection
            VHuser = website.externalApp
            WPsitepath = wpsite.path
            websitedomain = website.domain


            php = PHPManager.getPHPString(PhpVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)
            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Getting DataBase...,20')
            statusFile.close()

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config get DB_NAME  --skip-plugins --skip-themes --path=%s' % (VHuser, FinalPHPPath, WPsitepath)
            stdoutput = ProcessUtilities.outputExecutioner(command)
            DataBaseName = stdoutput.rstrip("\n")


            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config get DB_USER  --skip-plugins --skip-themes --path=%s' % (
            VHuser, FinalPHPPath, WPsitepath)
            stdoutput = ProcessUtilities.outputExecutioner(command)
            DataBaseUser = stdoutput.rstrip("\n")



            ### Create secure folder
            ACLManager.CreateSecureDir()
            RandomPath = str(randint(1000, 9999))
            tempPath = '%s/%s' % ('/usr/local/CyberCP/tmp', RandomPath)
            self.tempPath = tempPath

            command = f'mkdir -p {tempPath}'
            ProcessUtilities.executioner(command)

            command = f'chown -R {wpsite.owner.externalApp}:{wpsite.owner.externalApp} {tempPath}'
            ProcessUtilities.executioner(command)

            ### Make directory for backup
            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating Backup Directory...,40')
            statusFile.close()

            command = "sudo -u %s mkdir -p %s/public_html" % (VHuser, tempPath)
            ProcessUtilities.executioner(command)

            config = {}
            config['WPtitle']=wpsite.title
            config['WPAutoUpdates']=wpsite.AutoUpdates
            config['WPFinalURL']=wpsite.FinalURL
            config['WPPluginUpdates']=wpsite.PluginUpdates
            config['WPThemeUpdates']=wpsite.ThemeUpdates
            config['WPowner_id']=wpsite.owner_id
            config["WPsitepath"] = wpsite.path
            config["DatabaseName"] = DataBaseName
            config["DatabaseUser"] = DataBaseUser
            config['RandomPath'] = RandomPath
            config["WebDomain"] = websitedomain
            config['WebadminEmail'] = website.adminEmail
            config['WebphpSelection'] = website.phpSelection
            config['Webssl'] = website.ssl
            config['Webstate'] = website.state
            config['WebVHuser'] = website.externalApp
            config['Webpackage_id'] = website.package_id
            config['Webadmin_id'] = website.admin_id

            ###############Create config.Json file


            command = "sudo -u %s touch /home/cyberpanel/config.json" % (VHuser)
            ProcessUtilities.executioner(command)
            ###### write into config
            json_object = json.dumps(config, indent=4)
            configPath = "/home/cyberpanel/config.json"
            file = open(configPath, "w")
            file.write(json_object)
            file.close()

            os.chmod(configPath, 0o600)

            command ="sudo -u %s cp -R /home/cyberpanel/config.json %s"%(VHuser, tempPath)
            ProcessUtilities.executioner(command)

            command = "rm -r /home/cyberpanel/config.json"
            ProcessUtilities.executioner(command)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Copying website data.....,50')
            statusFile.close()

            ############## Copy Public_htnl to backup
            command = "sudo -u %s cp -R %s* %s/public_html" % (VHuser, WPsitepath, tempPath)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            command = "sudo -u %s cp -R %s.[^.]* %s/public_html/" % (VHuser, WPsitepath, tempPath)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Copying DataBase.....,70')
            statusFile.close()


            ##### SQLDUMP database into new directory

            command = "mysqldump %s --result-file %s/%s.sql" % (DataBaseName, tempPath, DataBaseName)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            ######## Zip backup directory
            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Compressing backup files.....,90')
            statusFile.close()

            websitepath = "/home/%s"%websitedomain

            FinalZipPath = '%s/%s.zip' % (websitepath, RandomPath)
            command = "sudo -u %s tar -czvf %s -P %s" % (VHuser, FinalZipPath, tempPath)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)


            command = f'rm -rf {tempPath}'
            ProcessUtilities.executioner(command)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Created. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            command = f'rm -rf {self.tempPath}'
            ProcessUtilities.executioner(command)
            logging.writeToFile("Error WPCreateBackup ....... %s" % str(msg))
            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0



def main():
    parser = argparse.ArgumentParser(description='CyberPanel Application Installer')
    parser.add_argument('function', help='Specify a function to call!')
    parser.add_argument('--tempStatusPath', help='')
    parser.add_argument('--appsSet', help='')
    parser.add_argument('--domain', help='')
    parser.add_argument('--email', help='')
    parser.add_argument('--password', help='')
    parser.add_argument('--pluginUpdates', help='')
    parser.add_argument('--themeUpdates', help='')
    parser.add_argument('--title', help='')
    parser.add_argument('--updates', help='')
    parser.add_argument('--userName', help='')
    parser.add_argument('--version', help='')
    parser.add_argument('--path', help='')
    parser.add_argument('--createSite', help='')


    args = parser.parse_args()

    if args.function == "DeployWordPress":

        extraArgs = {}
        extraArgs['domain'] = args.domain
        extraArgs['tempStatusPath'] = args.tempStatusPath
        extraArgs['appsSet'] = args.appsSet
        extraArgs['email'] = args.email
        extraArgs['password'] = args.password
        extraArgs['pluginUpdates'] = args.pluginUpdates
        extraArgs['themeUpdates'] = args.themeUpdates
        extraArgs['title'] = args.title
        extraArgs['updates'] = args.updates
        extraArgs['userName'] = args.userName
        extraArgs['version'] = args.version
        extraArgs['createSite'] = int(args.createSite)

        if args.path != None:
            extraArgs['path'] = args.path
            extraArgs['home'] = '0'
        else:
            extraArgs['home'] = '1'

        ai = ApplicationInstaller(None, extraArgs)
        ai.DeployWordPress()


if __name__ == "__main__":
    main()
