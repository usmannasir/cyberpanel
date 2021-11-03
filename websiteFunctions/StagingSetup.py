#!/usr/local/CyberCP/bin/python
import subprocess
import threading as multi
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.processUtilities import ProcessUtilities
from .models import Websites, ChildDomains
from plogical.applicationInstaller import ApplicationInstaller
from plogical.mysqlUtilities import mysqlUtilities
from random import randint
import os


class StagingSetup(multi.Thread):

    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.function == 'startCloning':
                self.startCloning()
            elif self.function == 'startSyncing':
                self.startSyncing()
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [StagingSetup.run]')

    def startCloning(self):
        global ApplicationInstaller
        try:
            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath
            masterDomain = self.extraArgs['masterDomain']
            domain = self.extraArgs['domain']
            admin = self.extraArgs['admin']

            website = Websites.objects.get(domain=masterDomain)

            from managePHP.phpManager import PHPManager
            php = PHPManager.getPHPString(website.phpSelection)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            try:
                import json
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                masterPath = '/home/%s/public_html/%s' % (masterDomain, path)
                replaceDomain = '%s/%s' % (masterDomain, path)
            except:
                masterPath = '/home/%s/public_html' % (masterDomain)
                replaceDomain = masterDomain

            ### Check WP CLI

            try:
                command = 'wp --info'
                outout = ProcessUtilities.outputExecutioner(command)

                if not outout.find('WP-CLI root dir:') > -1:
                    from plogical.applicationInstaller import ApplicationInstaller
                    ai = ApplicationInstaller(None, None)
                    ai.installWPCLI()
            except subprocess.CalledProcessError:
                from plogical.applicationInstaller import ApplicationInstaller
                ai = ApplicationInstaller(None, None)
                ai.installWPCLI()

            configPath = '%s/wp-config.php' % (masterPath)

            ## Check if WP Detected on Main Site

            command = 'ls -la %s' % (configPath)
            output = ProcessUtilities.outputExecutioner(command)

            if output.find('No such file or') > -1:
                logging.statusWriter(tempStatusPath, 'WordPress is not detected. [404]')
                return 0

            ##

            command = 'chmod 755 %s' % (masterPath)
            ProcessUtilities.executioner(command)

            ## Creating Child Domain

            path = "/home/" + masterDomain + "/" + domain

            logging.statusWriter(tempStatusPath, 'Creating domain for staging environment..,5')
            phpSelection = website.phpSelection
            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createDomain --masterDomain " + masterDomain + " --virtualHostName " + domain + \
                       " --phpVersion '" + phpSelection + "' --ssl 1 --dkimCheck 0 --openBasedir 0 --path " + path + ' --websiteOwner ' \
                       + admin.userName + ' --tempStatusPath  %s' % (tempStatusPath + '1') + " --apache 0"

            ProcessUtilities.executioner(execPath)

            domainCreationStatusPath = tempStatusPath + '1'

            data = open(domainCreationStatusPath, 'r').read()

            if data.find('[200]') > -1:
                pass
            else:
                logging.statusWriter(tempStatusPath, 'Failed to create child-domain for staging environment. [404]')
                return 0

            logging.statusWriter(tempStatusPath, 'Domain successfully created..,15')

            ### Get table prefix of master site

            command = '%s -d error_reporting=0 /usr/bin/wp config get table_prefix --allow-root --skip-plugins --skip-themes --path=%s' % (
            FinalPHPPath, masterPath)
            TablePrefix = ProcessUtilities.outputExecutioner(command).rstrip('\n')

            ###

            ## Creating WP Site and setting Database

            command = '%s -d error_reporting=0 /usr/bin/wp core download --path=%s' % (FinalPHPPath, path)
            ProcessUtilities.executioner(command, website.externalApp)

            logging.statusWriter(tempStatusPath, 'Creating and copying database..,50')

            dbNameRestore, dbUser, dbPassword = ApplicationInstaller(None, None).dbCreation(tempStatusPath, website)

            command = '%s -d error_reporting=0 /usr/bin/wp core config --dbname=%s --dbuser=%s --dbpass=%s --dbhost=%s:%s --path=%s' % (FinalPHPPath, dbNameRestore, dbUser, dbPassword, ApplicationInstaller.LOCALHOST, ApplicationInstaller.PORT, path)
            ProcessUtilities.executioner(command, website.externalApp)

            ### Set table prefix

            command = '%s -d error_reporting=0 /usr/bin/wp config set table_prefix %s --path=%s' % (FinalPHPPath, TablePrefix , path)
            ProcessUtilities.executioner(command, website.externalApp)

            ## Exporting and importing database

            command = '%s -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path=%s db export %s/dbexport-stage.sql' % (FinalPHPPath, masterPath, path)
            ProcessUtilities.executioner(command)

            ## Import

            command = '%s -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path=%s --quiet db import %s/dbexport-stage.sql' % (FinalPHPPath, path, path)
            ProcessUtilities.executioner(command)


            try:
                command = 'rm -f %s/dbexport-stage.sql' % (path)
                ProcessUtilities.executioner(command)
            except:
                pass

            ## Sync WP-Content Folder

            command = '%s -d error_reporting=0 /usr/bin/wp theme path --skip-plugins --skip-themes --allow-root --path=%s' % (FinalPHPPath, masterPath)
            WpContentPath = ProcessUtilities.outputExecutioner(command).splitlines()[-1].replace('themes', '')

            command = 'cp -R %s %s/' % (WpContentPath, path)
            ProcessUtilities.executioner(command)

            ## Copy htaccess

            command = 'cp -f %s/.htaccess %s/' % (WpContentPath.replace('/wp-content/', ''), path)
            ProcessUtilities.executioner(command)

            ## Search and replace url

            command = '%s -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --allow-root --path=%s "%s" "%s"' % (FinalPHPPath, path, replaceDomain, domain)
            ProcessUtilities.executioner(command)

            command = '%s -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --allow-root --path=%s "www.%s" "%s"' % (FinalPHPPath, path, domain, domain)
            ProcessUtilities.executioner(command)

            command = '%s -d error_reporting=0 /usr/bin/wp search-replace --skip-plugins --skip-themes --allow-root --path=%s "https://%s" "http://%s"' % (
            FinalPHPPath, path, domain, domain)
            ProcessUtilities.executioner(command)

            logging.statusWriter(tempStatusPath, 'Fixing permissions..,90')

            from filemanager.filemanager import FileManager

            fm = FileManager(None, None)
            fm.fixPermissions(masterDomain)

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeed()

            logging.statusWriter(tempStatusPath, 'Completed,[200]')

            return 0
        except BaseException as msg:
            mesg = '%s. [168][404]' % (str(msg))
            logging.statusWriter(self.tempStatusPath, mesg)

    def startSyncing(self):
        try:
            tempStatusPath = self.extraArgs['tempStatusPath']
            childDomain = self.extraArgs['childDomain']
            #eraseCheck = self.extraArgs['eraseCheck']
            dbCheck = self.extraArgs['dbCheck']
            #copyChanged = self.extraArgs['copyChanged']


            child = ChildDomains.objects.get(domain=childDomain)

            from managePHP.phpManager import PHPManager
            php = PHPManager.getPHPString(child.master.phpSelection)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            try:
                import json
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=child.master)
                path = json.loads(wpd.config)['path']
                masterPath = '/home/%s/public_html/%s' % (child.master.domain, path)
                replaceDomain = '%s/%s' % (child.master.domain, path)
            except:
                masterPath = '/home/%s/public_html' % (child.master.domain)
                replaceDomain = child.master.domain

            command = 'chmod 755 /home/%s/public_html' % (child.master.domain)
            ProcessUtilities.executioner(command)

            configPath = '%s/wp-config.php' % (child.path)

            if not os.path.exists(configPath):
                logging.statusWriter(tempStatusPath, 'WordPress is not detected. [404]')
                return 0

            ## Restore db

            logging.statusWriter(tempStatusPath, 'Syncing databases..,10')

            command = '%s -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path=%s db export %s/dbexport-stage.sql' % (FinalPHPPath, child.path, masterPath)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            ## Restore to master domain

            command = '%s -d error_reporting=0 /usr/bin/wp --allow-root --skip-plugins --skip-themes --path=%s --quiet db import %s/dbexport-stage.sql' % (FinalPHPPath, masterPath, masterPath)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            try:
                command = 'rm -f %s/dbexport-stage.sql' % (masterPath)
                ProcessUtilities.executioner(command)
            except:
                pass

            ## Sync WP-Content Folder

            logging.statusWriter(tempStatusPath, 'Syncing data..,50')

            command = '%s -d error_reporting=0 /usr/bin/wp theme path --allow-root --skip-plugins --skip-themes --path=%s' % (FinalPHPPath, masterPath)
            WpContentPath = ProcessUtilities.outputExecutioner(command).splitlines()[-1].replace('wp-content/themes', '')

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(WpContentPath)

            command = 'cp -R %s/wp-content/ %s' % (child.path, WpContentPath)
            ProcessUtilities.executioner(command)

            ## COPY Htaccess

            command = 'cp -f %s/.htaccess %s' % (child.path, WpContentPath)
            ProcessUtilities.executioner(command)

            ## Search and replace url

            command = '%s -d error_reporting=0 /usr/bin/wp search-replace --allow-root --skip-plugins --skip-themes --path=%s "%s" "%s"' % (FinalPHPPath, masterPath, child.domain, replaceDomain)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            command = '%s -d error_reporting=0 /usr/bin/wp search-replace --allow-root --skip-plugins --skip-themes --path=%s "www.%s" "%s"' % (FinalPHPPath,masterPath, child.domain, replaceDomain)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            command = '%s -d error_reporting=0 /usr/bin/wp search-replace --allow-root --skip-plugins --skip-themes --path=%s "https://%s" "http://%s"' % (FinalPHPPath,
            masterPath, replaceDomain, replaceDomain)
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)

            from filemanager.filemanager import FileManager

            fm = FileManager(None, None)
            fm.fixPermissions(child.master.domain)

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeed()

            logging.statusWriter(tempStatusPath, 'Completed,[200]')

            return 0
        except BaseException as msg:
            mesg = '%s. [404]' % (str(msg))
            logging.statusWriter(tempStatusPath, mesg)
