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
        tempStatusPath = self.extraArgs['tempStatusPath']
        worker = None
        try:
            from .stagingSync import StagingSync
            from managePHP.phpManager import PHPManager
            child = ChildDomains.objects.get(domain=self.extraArgs['childDomain'])
            php = PHPManager.getPHPString(child.master.phpSelection)
            target = '/home/%s/public_html' % child.master.domain
            from cloudAPI.models import WPDeployments
            try:
                import json
                deployment = WPDeployments.objects.get(owner=child.master)
                subpath = json.loads(deployment.config).get('path', '')
                candidate = os.path.realpath(os.path.join(target, subpath))
                if os.path.commonpath([os.path.realpath(target), candidate]) != os.path.realpath(target):
                    raise ValueError('Invalid production WordPress path.')
                target = candidate
            except WPDeployments.DoesNotExist:
                pass
            worker = StagingSync(ProcessUtilities.outputExecutioner,
                                 lambda message: logging.statusWriter(tempStatusPath, message))
            worker.run(child.path, target, '/usr/local/lsws/lsphp%s/bin/php' % php,
                       copy_all=self.extraArgs.get('eraseCheck', False),
                       database=self.extraArgs.get('dbCheck', False),
                       copy_changed=self.extraArgs.get('copyChanged', False))
        except Exception as error:
            backup = worker.backup if worker else None
            logging.statusWriter(tempStatusPath, '%s. Recovery backup: %s [404]' % (error, backup or 'not created'))
