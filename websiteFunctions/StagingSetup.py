#!/usr/local/CyberCP/bin/python
import shlex
import subprocess
import threading as multi
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.processUtilities import ProcessUtilities
from .models import Websites, ChildDomains
from plogical.applicationInstaller import ApplicationInstaller
from plogical.mysqlUtilities import mysqlUtilities
from plogical.wordpressInstallerUtilities import worker_failure_reason
from random import randint
import os
import secrets
from managePHP.phpConfig import stored_php_selection
from .stagingClone import StagingCopy


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
        """Copy a WordPress website into a new child domain.

        The status ends with [200] once the copy has its own database and
        answers under the new domain. When a step that the copy depends on
        fails, it ends with [404] and the reason, after what this job created
        (the child domain with its folder, its database) has been removed
        again. Nothing that was there before the job is removed.
        """
        tempStatusPath = self.extraArgs['tempStatusPath']
        self.tempStatusPath = tempStatusPath
        installer = ApplicationInstaller(None, None)
        made = {}
        try:
            self.cloneWebsite(installer, made)
        except BaseException as msg:
            logging.writeToFile('%s [StagingSetup.startCloning]' % str(msg))
            removal = self.removeCloneParts(installer, made)
            logging.statusWriter(tempStatusPath, '%s. %s[404]' % (worker_failure_reason(str(msg)), removal))
            return 0
        logging.statusWriter(tempStatusPath, 'Completed,[200]')
        return 0

    def cloneWebsite(self, installer, made):
        """Create the child domain and fill it with a working copy; record in `made` what was created."""
        tempStatusPath = self.tempStatusPath
        masterDomain = self.extraArgs['masterDomain']
        domain = self.extraArgs['domain']
        admin = self.extraArgs['admin']

        website = Websites.objects.get(domain=masterDomain)
        user = website.externalApp

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
                installer.installWPCLI()
        except subprocess.CalledProcessError:
            installer.installWPCLI()

        configPath = '%s/wp-config.php' % (masterPath)

        ## Check if WP Detected on Main Site

        command = 'ls -la %s' % (configPath)
        output = ProcessUtilities.outputExecutioner(command)

        if output.find('No such file or') > -1:
            raise BaseException('WordPress is not detected')

        def site(command, withErrors=True):
            return ApplicationInstaller.siteCommand(command, user, withErrors)

        copy = StagingCopy(site, lambda message: logging.statusWriter(tempStatusPath, message))

        # Read from the site before anything is created for the copy.
        facts = copy.read_source(FinalPHPPath, masterPath)

        ## Creating Child Domain

        path = "/home/" + masterDomain + "/" + domain

        if Websites.objects.filter(domain=domain).exists() or ChildDomains.objects.filter(domain=domain).exists():
            raise BaseException('%s already exists on this server; choose another name for the staging site' % domain)
        # The folder becomes the copy's and is removed with it when the job
        # fails, so it must not be there yet.
        found = installer.pathPresent(path)
        if found is not False:
            raise BaseException('The folder %s %s; choose another name for the staging site' % (
                path, 'already exists' if found else 'could not be checked'))
        # What the creation of the domain would find already there and use.
        keep = installer.foundBeforeCreation(domain)

        logging.statusWriter(tempStatusPath, 'Creating domain for staging environment..,5')
        phpSelection = stored_php_selection(website.phpSelection)
        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " createDomain --masterDomain " + shlex.quote(masterDomain) + " --virtualHostName " + shlex.quote(domain) + \
                   " --phpVersion " + shlex.quote(phpSelection) + " --ssl 1 --dkimCheck 0 --openBasedir 0 --path " + shlex.quote(path) + ' --websiteOwner ' \
                   + shlex.quote(admin.userName) + ' --tempStatusPath  %s' % shlex.quote(tempStatusPath + '1') + " --apache 0"

        ProcessUtilities.executioner(execPath)

        domainCreationStatusPath = tempStatusPath + '1'

        try:
            with open(domainCreationStatusPath, 'r') as status:
                data = status.read()
        except OSError:
            data = ''

        if data.find('[200]') == -1:
            # A failed creation takes back its configuration and record, not
            # the folder it made.
            made['folder'] = (path, user)
            raise BaseException('Failed to create child-domain for staging environment: %s' % (
                worker_failure_reason(data) if data.find('[404]') > -1 else 'the domain was not created'))
        made['child'] = (domain, keep)

        logging.statusWriter(tempStatusPath, 'Domain successfully created..,15')

        ## Database of the copy

        created = installer.dbCreation(tempStatusPath, website)
        if not isinstance(created, tuple):
            try:
                with open(tempStatusPath, 'r') as status:
                    written = status.read()
            except OSError:
                written = ''
            raise BaseException('The database for the staging site could not be created: %s' % (
                worker_failure_reason(written) if written.find('[404]') > -1 else 'see the CyberPanel log'))
        dbNameRestore, dbUser, dbPassword = created
        made['database'] = (dbNameRestore, dbUser)

        # The site's database passes through a file of the site's user that
        # no one can find: outside every document root, under a random name.
        dump = '/home/%s/.staging-%s.sql' % (masterDomain, secrets.token_hex(16))
        try:
            copy.run(FinalPHPPath, masterPath, facts, path,
                     (dbNameRestore, dbUser, dbPassword,
                      '%s:%s' % (ApplicationInstaller.LOCALHOST, ApplicationInstaller.PORT)),
                     dump, replaceDomain, domain)
        finally:
            site('rm -f -- %s' % shlex.quote(dump))

        logging.statusWriter(tempStatusPath, 'Fixing permissions..,90')

        # The copy is complete and was made by the site's own user: a repair
        # that fails leaves it working, so it is logged and is no failure.
        try:
            from filemanager.filemanager import FileManager
            FileManager(None, None).fixPermissions(masterDomain)
        except BaseException as msg:
            logging.writeToFile('Staging site %s was created; the permissions of %s could not be repaired: %s' % (
                domain, masterDomain, str(msg)))

        from plogical.installUtilities import installUtilities
        installUtilities.reStartLiteSpeed()

    def removeCloneParts(self, installer, made):
        """Remove what a failed clone created; return the sentences that say what became of it."""
        sentences = []
        database = made.get('database')
        if database:
            try:
                from databases.models import Databases
                removed = mysqlUtilities.deleteDatabase(database[0], database[1]) == 1
                if removed:
                    Databases.objects.filter(dbName=database[0]).delete()
            except BaseException as msg:
                logging.writeToFile('%s [StagingSetup.removeCloneParts]' % str(msg))
                removed = False
            if not removed:
                sentences.append('The database %s that was created for this job could not be removed; '
                                 'delete it under Databases.' % database[0])
        if made.get('child'):
            sentences.append(installer.removeCreatedChildDomain(*made['child']))
        elif made.get('folder'):
            # A creation that failed leaves its folder empty, or makes none:
            # rmdir removes such a folder and nothing else.
            path, user = made['folder']
            try:
                ApplicationInstaller.siteCommand('rmdir -- %s' % shlex.quote(path), user)
            except BaseException as msg:
                logging.writeToFile('%s [StagingSetup.removeCloneParts]' % str(msg))
        return ' '.join(sentences) + ' ' if sentences else ''

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
