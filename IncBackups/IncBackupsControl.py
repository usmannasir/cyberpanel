#!/usr/local/CyberCP/bin/python
import os
import os.path
import shlex
import subprocess
import sys
import requests
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

import django

try:
    django.setup()
except:
    pass
import threading as multi
from plogical.processUtilities import ProcessUtilities
from .models import IncJob, JobSnapshots
from websiteFunctions.models import Websites
import plogical.randomPassword as randomPassword
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import plogical.mysqlUtilities as mysqlUtilities
import json
from django.shortcuts import HttpResponse

try:
    from plogical.virtualHostUtilities import virtualHostUtilities
    from plogical.mailUtilities import mailUtilities
except:
    pass


class IncJobs(multi.Thread):

    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs
        self.repoPath = ''
        self.passwordFile = ''
        self.statusPath = ''
        self.website = ''
        self.backupDestinations = ''
        self.jobid = 0
        self.metaPath = ''
        self.path = ''
        self.reconstruct = ''

    def run(self):

        if self.function == 'createBackup':
            self.createBackup()
        elif self.function == 'restorePoint':
            self.restorePoint()
        elif self.function == 'remoteRestore':
            self.restorePoint()

    def getRemoteBackups(self):
        if self.backupDestinations[:4] == 'sftp':
            path = '/home/backup/%s' % (self.website)
            command = 'export RESTIC_PASSWORD=%s PATH=${PATH}:/usr/bin && restic -r %s:%s snapshots' % (
                self.passwordFile, self.backupDestinations, path)
            return ProcessUtilities.outputExecutioner(command, self.externalApp).split('\n')
        else:
            key, secret = self.getAWSData()
            command = 'export RESTIC_PASSWORD=%s AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s  && restic -r s3:s3.amazonaws.com/%s snapshots' % (
                self.passwordFile, key, secret, self.website)
            return ProcessUtilities.outputExecutioner(command, self.externalApp).split('\n')

    def fetchCurrentBackups(self):
        try:
            self.website = self.extraArgs['website']
            self.backupDestinations = self.extraArgs['backupDestinations']
            self.passwordFile = self.extraArgs['password']

            result = self.getRemoteBackups()

            activator = 0
            json_data = []
            if result[0].find('unable to open config file') == -1:
                for items in reversed(result):

                    if items.find('---------------') > -1:
                        if activator == 0:
                            activator = 1
                            continue
                        else:
                            activator = 0

                    if activator:
                        entry = items.split(' ')
                        json_data.append({'id': entry[0],
                                          'date': "%s %s" % (entry[2], entry[3]),
                                          'host': entry[5],
                                          'path': entry[-1]
                                          })
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            logging.writeToFile(str(msg))

    ## Find restore path

    def findRestorePath(self):

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8 \
                or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
            self.restoreTarget = '/'
            return 1
        else:
            if self.jobid.type[:8] == 'database':
                self.restoreTarget = '/usr/local/CyberCP/tmp/'
            elif self.jobid.type[:4] == 'data':
                self.restoreTarget = '/home/'
            elif self.jobid.type[:5] == 'email':
                self.restoreTarget = '/home/vmail/'
            elif self.jobid.type[:4] == 'meta':
                self.restoreTarget = '/home/%s/' % (self.website)

    ####

    def getAWSData(self):
        key = self.backupDestinations.split('/')[-1]
        path = '/home/cyberpanel/aws/%s' % (key)
        secret = open(path, 'r').read()
        return key, secret

    ## Last argument delete is set when the snapshot is to be deleted from this repo, when this argument is set, any preceding argument is not used

    def awsFunction(self, fType, backupPath=None, snapshotID=None, bType=None, delete=None):
        try:
            if fType == 'backup':
                key, secret = self.getAWSData()

                # Define our excludes file for use with restic
                backupExcludesFile = '/home/%s/backup-exclude.conf' % (self.website.domain)
                resticBackupExcludeCMD = ' --exclude-file=%s' % (backupExcludesFile)

                command = 'AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s restic -r s3:s3.amazonaws.com/%s backup %s --password-file %s --exclude /home/%s/backup --exclude /home/%s/incbackup' % (
                    key, secret, self.website.domain, backupPath, self.passwordFile, self.website.domain, self.website.domain)

                # If /home/%s/backup-exclude.conf file exists lets pass this to restic by appending the command to end.
                if os.path.isfile(backupExcludesFile):
                    command = command + resticBackupExcludeCMD
                result = ProcessUtilities.outputExecutioner(command, self.externalApp)

                if result.find('saved') == -1:
                    logging.statusWriter(self.statusPath, '%s. [5009].' % (result), 1)
                    return 0

                snapShotid = result.split(' ')[-2]

                if bType == 'database':
                    newSnapshot = JobSnapshots(job=self.jobid,
                                               type='%s:%s' % (bType, backupPath.split('/')[-1].rstrip('.sql')),
                                               snapshotid=snapShotid,
                                               destination=self.backupDestinations)
                else:
                    newSnapshot = JobSnapshots(job=self.jobid, type='%s:%s' % (bType, backupPath),
                                               snapshotid=snapShotid,
                                               destination=self.backupDestinations)
                newSnapshot.save()
                return 1
            else:
                if self.reconstruct == 'remote':
                    self.backupDestinations = self.backupDestinations

                    key, secret = self.getAWSData()

                    command = 'export RESTIC_PASSWORD=%s AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s  && restic -r s3:s3.amazonaws.com/%s restore %s --target %s' % (
                        self.passwordFile,
                        key, secret, self.website, snapshotID, self.restoreTarget)

                    result = ProcessUtilities.outputExecutioner(command, self.externalApp)

                    if result.find('restoring') == -1:
                        logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                        return 0
                elif delete:

                    self.backupDestinations = self.jobid.destination

                    key, secret = self.getAWSData()

                    command = 'AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s restic -r s3:s3.amazonaws.com/%s forget %s --password-file %s' % (
                        key, secret, self.website, snapshotID, self.passwordFile)

                    result = ProcessUtilities.outputExecutioner(command, self.externalApp)

                    if result.find('removed snapshot') > -1 or result.find('deleted') > -1:
                        pass
                    else:
                        logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                        return 0

                    command = 'AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s restic -r s3:s3.amazonaws.com/%s prune --password-file %s' % (
                        key, secret, self.website, self.passwordFile)

                    ProcessUtilities.outputExecutioner(command, self.externalApp)
                else:
                    self.backupDestinations = self.jobid.destination

                    key, secret = self.getAWSData()

                    command = 'AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s restic -r s3:s3.amazonaws.com/%s restore %s --password-file %s --target %s' % (
                        key, secret, self.website, snapshotID, self.passwordFile, self.restoreTarget)

                    result = ProcessUtilities.outputExecutioner(command, self.externalApp)

                    if result.find('restoring') == -1:
                        logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                        return 0

                return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [88][5009]" % (str(msg)), 1)
            return 0

    ## Last argument delete is set when the snapshot is to be deleted from this repo, when this argument is set, any preceding argument is not used

    def localFunction(self, backupPath, type, restore=None, delete=None):

        if restore == None:
            # Define our excludes file for use with restic
            backupExcludesFile = '/home/%s/backup-exclude.conf' % (self.website.domain)
            resticBackupExcludeCMD = ' --exclude-file=%s' % (backupExcludesFile)

            command = 'restic -r %s backup %s --password-file %s --exclude %s --exclude /home/%s/backup' % (
                self.repoPath, backupPath, self.passwordFile, self.repoPath, self.website.domain)
            # If /home/%s/backup-exclude.conf file exists lets pass this to restic by appending the command to end.
            if os.path.isfile(backupExcludesFile):
                command = command + resticBackupExcludeCMD
            result = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if result.find('saved') == -1:
                logging.statusWriter(self.statusPath, '%s. [5009].' % (result), 1)
                return 0

            snapShotid = result.split(' ')[-2]

            if type == 'database':
                newSnapshot = JobSnapshots(job=self.jobid,
                                           type='%s:%s' % (type, backupPath.split('/')[-1].rstrip('.sql')),
                                           snapshotid=snapShotid,
                                           destination=self.backupDestinations)
            else:
                newSnapshot = JobSnapshots(job=self.jobid, type='%s:%s' % (type, backupPath), snapshotid=snapShotid,
                                           destination=self.backupDestinations)
            newSnapshot.save()
            return 1
        elif delete:

            repoLocation = '/home/%s/incbackup' % (self.website)

            command = 'restic -r %s forget %s --password-file %s' % (repoLocation, self.jobid.snapshotid, self.passwordFile)
            result = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if result.find('removed snapshot') > -1 or result.find('deleted') > -1:
                pass
            else:
                logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                return 0

            command = 'restic -r %s prune --password-file %s' % (repoLocation, self.passwordFile)
            ProcessUtilities.outputExecutioner(command, self.externalApp)

            return 1
        else:
            repoLocation = '/home/%s/incbackup' % (self.website)
            command = 'restic -r %s restore %s --target %s --password-file %s' % (
                repoLocation, self.jobid.snapshotid, self.restoreTarget, self.passwordFile)

            result = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if result.find('restoring') == -1:
                logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                return 0

            return 1

    ## Last argument delete is set when the snapshot is to be deleted from this repo, when this argument is set, any preceding argument is not used

    def sftpFunction(self, backupPath, type, restore=None, delete=None):
        return 0
        if restore == None:
            # Define our excludes file for use with restic
            backupExcludesFile = '/home/%s/backup-exclude.conf' % (self.website.domain)
            resticBackupExcludeCMD = ' --exclude-file=%s' % (backupExcludesFile)
            remotePath = '/home/backup/%s' % (self.website.domain)
            command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s backup %s --password-file %s --exclude %s --exclude /home/%s/backup' % (
                self.backupDestinations, remotePath, backupPath, self.passwordFile, self.repoPath, self.website.domain)
            # If /home/%s/backup-exclude.conf file exists lets pass this to restic by appending the command to end.
            if os.path.isfile(backupExcludesFile):
                command = command + resticBackupExcludeCMD
            result = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if result.find('saved') == -1:
                logging.statusWriter(self.statusPath, '%s. [5009].' % (result), 1)
                return 0

            snapShotid = result.split(' ')[-2]

            if type == 'database':
                newSnapshot = JobSnapshots(job=self.jobid,
                                           type='%s:%s' % (type, backupPath.split('/')[-1].rstrip('.sql')),
                                           snapshotid=snapShotid,
                                           destination=self.backupDestinations)
            else:
                newSnapshot = JobSnapshots(job=self.jobid, type='%s:%s' % (type, backupPath), snapshotid=snapShotid,
                                           destination=self.backupDestinations)
            newSnapshot.save()
            return 1
        elif delete:
            repoLocation = '/home/backup/%s' % (self.website)
            command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s forget %s --password-file %s' % (
                self.jobid.destination, repoLocation, self.jobid.snapshotid, self.passwordFile)
            result = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if result.find('removed snapshot') > -1 or result.find('deleted') > -1:
                pass
            else:
                logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                return 0

            command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s prune --password-file %s' % (self.jobid.destination, repoLocation, self.passwordFile)
            ProcessUtilities.outputExecutioner(command, self.externalApp)
        else:
            if self.reconstruct == 'remote':
                repoLocation = '/home/backup/%s' % (self.website)
                command = 'export RESTIC_PASSWORD=%s PATH=${PATH}:/usr/bin && restic -r %s:%s restore %s --target %s' % (
                    self.passwordFile,
                    self.backupDestinations, repoLocation, self.jobid, self.restoreTarget)
                result = ProcessUtilities.outputExecutioner(command, self.externalApp)
                if result.find('restoring') == -1:
                    logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                    return 0
            else:
                repoLocation = '/home/backup/%s' % (self.website)
                command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s restore %s --target %s --password-file %s' % (
                    self.jobid.destination, repoLocation, self.jobid.snapshotid, self.restoreTarget, self.passwordFile)
                result = ProcessUtilities.outputExecutioner(command, self.externalApp)
                if result.find('restoring') == -1:
                    logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                    return 0

            return 1

    def restoreData(self):
        try:

            if self.reconstruct == 'remote':
                if self.backupDestinations[:4] == 'sftp':
                    self.sftpFunction('none', 'none', 1)
                else:
                    if self.awsFunction('restore', '', self.jobid) == 0:
                        return 0
            else:
                if self.jobid.destination == 'local':
                    return self.localFunction('none', 'none', 1)
                elif self.jobid.destination[:4] == 'sftp':
                    return self.sftpFunction('none', 'none', 1)
                else:
                    return self.awsFunction('restore', '', self.jobid.snapshotid)

            return 1

        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [138][5009]" % (str(msg)), 1)
            return 0

    def restoreDatabase(self):
        try:

            if self.reconstruct == 'remote':
                if self.backupDestinations[:4] == 'sftp':
                    if self.sftpFunction('none', 'none', 1) == 0:
                        return 0
                else:
                    if self.awsFunction('restore', '', self.jobid) == 0:
                        return 0

                ## Restore proper permissions

                command = 'chown cyberpanel:cyberpanel /home/cyberpanel'
                ProcessUtilities.executioner(command)

                command = 'chmod 755 /home/cyberpanel'
                ProcessUtilities.executioner(command)

                ##

                if mysqlUtilities.mysqlUtilities.restoreDatabaseBackup(self.path.split('/')[-1].rstrip('.sql'),
                                                                       '/usr/local/CyberCP/tmp', 'dummy', 'dummy') == 0:
                    raise BaseException
            else:

                if self.jobid.destination == 'local':
                    if self.localFunction('none', 'none', 1) == 0:
                        return 0
                elif self.jobid.destination[:4] == 'sftp':
                    if self.sftpFunction('none', 'none', 1) == 0:
                        return 0
                else:
                    if self.awsFunction('restore', '', self.jobid.snapshotid) == 0:
                        return 0


                if mysqlUtilities.mysqlUtilities.restoreDatabaseBackup(self.jobid.type.split(':')[1].rstrip('.sql'),
                                                                       '/home/%s' % (self.website), 'dummy', 'dummy') == 0:
                    raise BaseException('Can not restore database backup.')

            try:
                if self.reconstruct == 'remote':
                    os.remove('/usr/local/CyberCP/tmp/%s' % (self.path.split('/')[-1]))
                else:
                    os.remove('/usr/local/CyberCP/tmp/%s.sql' % (self.jobid.type.split(':')[1]))
                    os.remove('/home/%s/%s.sql' % (self.website.domain, self.jobid.type.split(':')[1]))
            except BaseException as msg:
                logging.writeToFile(str(msg))

            return 1

        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [160][5009]" % (str(msg)), 1)
            return 0

    def restoreEmail(self):
        try:

            if self.reconstruct == 'remote':
                if self.backupDestinations[:4] == 'sftp':
                    if self.sftpFunction('none', 'none', 1) == 0:
                        return 0
                else:
                    if self.awsFunction('restore', '', self.jobid) == 0:
                        return 0
            else:
                if self.jobid.destination == 'local':
                    return self.localFunction('none', 'none', 1)
                elif self.jobid.destination[:4] == 'sftp':
                    return self.sftpFunction('none', 'none', 1)
                else:
                    return self.awsFunction('restore', '', self.jobid.snapshotid)

            return 1

        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [46][5009]" % (str(msg)), 1)
            return 0

    def reconstructWithMeta(self):
        try:

            if self.reconstruct == 'remote':
                if self.backupDestinations[:4] == 'sftp':
                    if self.sftpFunction('none', 'none', 1) == 0:
                        return 0
                else:
                    if self.awsFunction('restore', '', self.jobid) == 0:
                        return 0
            else:
                if self.jobid.destination == 'local':
                    if self.localFunction('none', 'none', 1) == 0:
                        return 0
                elif self.jobid.destination[:4] == 'sftp':
                    if self.sftpFunction('none', 'none', 1) == 0:
                        return 0
                else:
                    if self.awsFunction('restore', '', self.jobid.snapshotid) == 0:
                        return 0

            metaPathNew = '/home/%s/meta.xml' % (self.website)
            execPath = "nice -n 10 /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/restoreMeta.py"
            execPath = execPath + " submitRestore --metaPath %s --statusFile %s" % (metaPathNew, self.statusPath)
            result = ProcessUtilities.outputExecutioner(execPath)
            logging.statusWriter(self.statusPath, result, 1)

            try:
                os.remove(metaPathNew)
            except:
                pass

            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [46][5009]" % (str(msg)), 1)
            return 0

    def restorePoint(self):
        try:

            self.statusPath = self.extraArgs['tempPath']
            self.website = self.extraArgs['website']
            jobid = self.extraArgs['jobid']
            self.reconstruct = self.extraArgs['reconstruct']

            WebsiteObject = Websites.objects.get(domain=self.website)

            self.externalApp = WebsiteObject.externalApp

            if self.reconstruct == 'remote':

                self.findRestorePath()

                self.jobid = self.extraArgs['jobid']
                self.backupDestinations = self.extraArgs['backupDestinations']
                self.passwordFile = self.extraArgs['password']
                self.path = self.extraArgs['path']

                if self.path.find('.sql') > -1:
                    message = 'Restoring database..'
                    logging.statusWriter(self.statusPath, message, 1)
                    if self.restoreDatabase() == 0:
                        return 0
                    message = 'Database restored.'
                    logging.statusWriter(self.statusPath, message, 1)
                elif self.path == '/home/%s' % (self.website):
                    message = 'Restoring data..'
                    logging.statusWriter(self.statusPath, message, 1)
                    if self.restoreData() == 0:
                        return 0
                    message = 'Data restored..'
                    logging.statusWriter(self.statusPath, message, 1)
                elif self.path.find('vmail') > -1:
                    message = 'Restoring email..'
                    logging.statusWriter(self.statusPath, message, 1)
                    if self.restoreEmail() == 0:
                        return 0
                    message = 'Emails restored.'
                    logging.statusWriter(self.statusPath, message, 1)
                elif self.path.find('meta.xml') > -1:
                    message = 'Reconstructing with meta..'
                    logging.statusWriter(self.statusPath, message, 1)
                    if self.reconstructWithMeta() == 0:
                        return 0
                    message = 'Reconstructed'
                    logging.statusWriter(self.statusPath, message, 1)
            else:

                self.jobid = JobSnapshots.objects.get(pk=jobid)

                self.findRestorePath()

                message = 'Starting restore of %s for %s.' % (self.jobid.snapshotid, self.website)
                logging.statusWriter(self.statusPath, message, 1)
                self.passwordFile = '/home/%s/%s' % (self.website, self.website)

                ##

                if self.jobid.type[:8] == 'database':
                    message = 'Restoring database..'
                    logging.statusWriter(self.statusPath, message, 1)
                    self.restoreDatabase()
                    message = 'Database restored.'
                    logging.statusWriter(self.statusPath, message, 1)
                elif self.jobid.type[:4] == 'data':
                    message = 'Restoring data..'
                    logging.statusWriter(self.statusPath, message, 1)
                    if self.restoreData() == 0:
                        return 0
                    message = 'Data restored.'
                    logging.statusWriter(self.statusPath, message, 1)
                elif self.jobid.type[:5] == 'email':
                    message = 'Restoring email..'
                    logging.statusWriter(self.statusPath, message, 1)
                    self.restoreEmail()
                    message = 'Emails restored.'
                    logging.statusWriter(self.statusPath, message, 1)
                elif self.jobid.type[:4] == 'meta':
                    message = 'Reconstructing with meta..'
                    logging.statusWriter(self.statusPath, message, 1)
                    self.reconstructWithMeta()
                    message = 'Reconstructed'
                    logging.statusWriter(self.statusPath, message, 1)

            logging.statusWriter(self.statusPath, 'Completed', 1)
        except BaseException as msg:
            logging.statusWriter(self.extraArgs['tempPath'], str(msg), 1)

    ### Backup functions

    def prepareBackupMeta(self):
        try:

            ## Use the meta function from backup utils for future improvements.

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile('Creating meta for %s. [IncBackupsControl.py]' % (self.website.domain))

            from plogical.backupUtilities import backupUtilities
            status, message, metaPath = backupUtilities.prepareBackupMeta(self.website.domain, None, None, None, 0)

            ## meta generated

            if status == 1:
                logging.statusWriter(self.statusPath, 'Meta data is ready..', 1)
                metaPathNew = '/home/%s/meta.xml' % (self.website.domain)

                command = 'chown %s:%s %s' % (self.externalApp, self.externalApp, metaPath)
                ProcessUtilities.executioner(command)

                command = 'mv %s %s' % (metaPath, metaPathNew)
                ProcessUtilities.executioner(command, self.externalApp)
                return 1
            else:
                logging.statusWriter(self.statusPath, "%s [544][5009]" % (message), 1)
                return 0

        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [548][5009]" % (str(msg)), 1)
            return 0

    def backupData(self):
        try:
            logging.statusWriter(self.statusPath, 'Backing up data..', 1)
            backupPath = '/home/%s' % (self.website.domain)

            if self.backupDestinations == 'local':
                if self.localFunction(backupPath, 'data') == 0:
                    return 0
            elif self.backupDestinations[:4] == 'sftp':
                if self.sftpFunction(backupPath, 'data') == 0:
                    return 0
            else:
                if self.awsFunction('backup', backupPath, '', 'data') == 0:
                    return 0

            logging.statusWriter(self.statusPath,
                                 'Data for %s backed to %s.' % (self.website.domain, self.backupDestinations), 1)
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath, '%s. [IncJobs.backupData.223][5009]' % str(msg), 1)
            return 0

    def backupDatabases(self):
        try:
            logging.statusWriter(self.statusPath, 'Backing up databases..', 1)

            databases = self.website.databases_set.all()

            for items in databases:

                ###

                UploadPath = '/usr/local/CyberCP/tmp'

                if not os.path.exists(UploadPath):
                    command = 'mkdir %s' % (UploadPath)
                    ProcessUtilities.executioner(command)

                command = 'chown cyberpanel:cyberpanel %s' % (UploadPath)
                ProcessUtilities.executioner(command)

                command = 'chmod 711 %s' % (UploadPath)
                ProcessUtilities.executioner(command)

                ###

                if mysqlUtilities.mysqlUtilities.createDatabaseBackup(items.dbName, UploadPath) == 0:
                    return 0

                dbPath = '%s/%s.sql' % (UploadPath, items.dbName)
                dbPathNew = '/home/%s/%s.sql' % (self.website.domain, items.dbName)

                command = 'cp %s %s' % (dbPath, dbPathNew)
                ProcessUtilities.executioner(command, self.externalApp)

                if self.backupDestinations == 'local':
                    if self.localFunction(dbPathNew, 'database') == 0:
                        return 0
                elif self.backupDestinations[:4] == 'sftp':
                    if self.sftpFunction(dbPathNew, 'database') == 0:
                        return 0

                else:
                    if self.awsFunction('backup', dbPathNew, '', 'database') == 0:
                        return 0

                try:
                    dbPath = '/usr/local/CyberCP/tmp/%s.sql' % (items.dbName)
                    command = 'rm -f %s' % (dbPath)
                    ProcessUtilities.executioner(command, self.externalApp)
                except BaseException as msg:
                    logging.statusWriter(self.statusPath,
                                         'Failed to delete database: %s. [IncJobs.backupDatabases.456]' % str(msg), 1)

            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath, '%s. [IncJobs.backupDatabases.269][5009]' % str(msg), 1)
            return 0

    def emailBackup(self):
        try:
            logging.statusWriter(self.statusPath, 'Backing up emails..', 1)

            backupPath = '/home/vmail/%s' % (self.website.domain)

            if os.path.exists(backupPath):

                if self.backupDestinations == 'local':
                    if self.localFunction(backupPath, 'email') == 0:
                        return 0
                elif self.backupDestinations[:4] == 'sftp':
                    if self.sftpFunction(backupPath, 'email') == 0:
                        return 0
                else:
                    if self.awsFunction('backup', backupPath, '', 'email') == 0:
                        return 0

            logging.statusWriter(self.statusPath,
                                 'Emails for %s backed to %s.' % (self.website.domain, self.backupDestinations), 1)
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath, '%s. [IncJobs.emailBackup.269][5009]' % str(msg), 1)
            return 0

    def metaBackup(self):
        try:
            logging.statusWriter(self.statusPath, 'Backing up meta..', 1)

            backupPath = '/home/%s/meta.xml' % (self.website.domain)

            if self.backupDestinations == 'local':
                if self.localFunction(backupPath, 'meta') == 0:
                    return 0
            elif self.backupDestinations[:4] == 'sftp':
                if self.sftpFunction(backupPath, 'meta') == 0:
                    return 0
            else:
                if self.awsFunction('backup', backupPath, '', 'meta') == 0:
                    return 0

            logging.statusWriter(self.statusPath,
                                 'Meta for %s backed to %s.' % (self.website.domain, self.backupDestinations), 1)
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath, '%s. [IncJobs.metaBackup.269][5009]' % str(msg), 1)
            return 0

    def initiateRepo(self):
        try:
            logging.statusWriter(self.statusPath, 'Will first initiate backup repo..', 1)

            if self.backupDestinations == 'local':
                command = 'restic init --repo %s --password-file %s' % (self.repoPath, self.passwordFile)
                result = ProcessUtilities.outputExecutioner(command, self.externalApp)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(result)

                if result.find('config file already exists') == -1:
                    logging.statusWriter(self.statusPath, result, 1)

            elif self.backupDestinations[:4] == 'sftp':
                remotePath = '/home/backup/%s' % (self.website.domain)
                command = 'export PATH=${PATH}:/usr/bin && restic init --repo %s:%s --password-file %s' % (
                    self.backupDestinations, remotePath, self.passwordFile)
                result = ProcessUtilities.outputExecutioner(command, self.externalApp)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(result)

                if result.find('config file already exists') == -1:
                    logging.statusWriter(self.statusPath, result, 1)
            else:
                key, secret = self.getAWSData()
                command = 'AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s restic -r s3:s3.amazonaws.com/%s init --password-file %s' % (
                    key, secret, self.website.domain, self.passwordFile)
                result = ProcessUtilities.outputExecutioner(command, self.externalApp)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(result)

                if result.find('config file already exists') == -1:
                    logging.statusWriter(self.statusPath, result, 1)

            logging.statusWriter(self.statusPath,
                                 'Repo %s initiated for %s.' % (self.backupDestinations, self.website.domain), 1)
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath, '%s. [IncJobs.initiateRepo.47][5009]' % str(msg), 1)
            return 0

    def sendEmail(self, password):
        SUBJECT = "Backup Repository password for %s" % (self.website.domain)
        text = """Password: %s
This is password for your incremental backup repository, please save it in safe place as it will be required when you want to restore backup for this site on remote server.
""" % (password)

        sender = 'cyberpanel@%s' % (self.website.domain)
        TO = [self.website.adminEmail]
        message = """\
From: %s
To: %s
Subject: %s

%s
""" % (sender, ", ".join(TO), SUBJECT, text)
        mailUtilities.SendEmail(sender, TO, message)

    def createBackup(self):

        try:

            self.statusPath = self.extraArgs['tempPath']
            website = self.extraArgs['website']
            self.backupDestinations = self.extraArgs['backupDestinations']
            websiteData = self.extraArgs['websiteData']
            websiteEmails = self.extraArgs['websiteEmails']
            websiteDatabases = self.extraArgs['websiteDatabases']

            ### Checking if restic is installed before moving on

            command = 'restic'

            if ProcessUtilities.outputExecutioner(command).find('restic is a backup program which') == -1:
                try:

                    CentOSPath = '/etc/redhat-release'

                    if os.path.exists(CentOSPath):
                            command = 'yum install -y yum-plugin-copr'
                            ProcessUtilities.executioner(command)
                            command = 'yum copr enable -y copart/restic'
                            ProcessUtilities.executioner(command)
                            command = 'yum install -y restic'
                            ProcessUtilities.executioner(command)

                    else:
                        command = 'apt-get update -y'
                        ProcessUtilities.executioner(command)

                        command = 'apt-get install restic -y'
                        ProcessUtilities.executioner(command)

                except:
                    logging.statusWriter(self.statusPath,
                                         'It seems restic is not installed, for incremental backups to work '
                                         'restic must be installed. You can manually install restic using this '
                                         'guide -> https://go.cyberpanel.net/restic. [5009]', 1)
                    pass

                return 0

            ## Restic check completed.

            self.website = Websites.objects.get(domain=website)
            self.externalApp = self.website.externalApp

            self.jobid = IncJob(website=self.website)
            self.jobid.save()

            self.passwordFile = '/home/%s/%s' % (self.website.domain, self.website.domain)

            self.repoPath = '/home/%s/incbackup' % (self.website.domain)

            command = 'ls -la %s' % (self.passwordFile)
            output = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if output.find('No such file or directory') > -1:
                password = randomPassword.generate_pass()
                command = 'echo "%s" > %s' % (password, self.passwordFile)
                ProcessUtilities.executioner(command, self.externalApp, True)

                command = 'chmod 600 %s' % (self.passwordFile)
                ProcessUtilities.executioner(command, self.externalApp)

                self.sendEmail(password)

            ## Completed password generation

            if self.initiateRepo() == 0:
                return 0

            if self.prepareBackupMeta() == 0:
                return 0

            if websiteData:
                if self.backupData() == 0:
                    return 0

            if websiteDatabases:
                if self.backupDatabases() == 0:
                    return 0

            if websiteEmails:
                if self.emailBackup() == 0:
                    return 0

            ## Backup job done

            self.metaBackup()

            metaPathNew = '/home/%s/meta.xml' % (self.website.domain)

            try:
                command = 'rm -f %s' % (metaPathNew)
                ProcessUtilities.executioner(command)
            except BaseException as msg:
                logging.statusWriter(self.statusPath,
                                     'Failed to delete meta file: %s. [IncJobs.createBackup.591]' % str(msg), 1)

            logging.statusWriter(self.statusPath, 'Completed', 1)

        except BaseException as msg:
            logging.statusWriter(self.statusPath,
                                 'Failed to create incremental backup: %s. [5009][IncJobs.createBackup.913]' % str(msg), 1)


    ### Delete Snapshot

    def DeleteSnapShot(self, inc_job):
        try:

            self.statusPath = logging.fileName

            job_snapshots = inc_job.jobsnapshots_set.all()

            ### Fetch the website name from JobSnapshot object and set these variable as they are needed in called functions below

            self.website = job_snapshots[0].job.website.domain
            self.externalApp = job_snapshots[0].job.website.externalApp
            self.passwordFile = '/home/%s/%s' % (self.website, self.website)

            for job_snapshot in job_snapshots:

                ## Functions above use the self.jobid varilable to extract information about this snapshot, so this below variable needs to be set

                self.jobid = job_snapshot

                if self.jobid.destination == 'local':
                    self.localFunction('none', 'none', 0, 1)
                elif self.jobid.destination[:4] == 'sftp':
                    self.sftpFunction('none', 'none', 0, 1)
                else:
                    self.awsFunction('restore', '', self.jobid.snapshotid, None, 1)

            return 1

        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [903:DeleteSnapShot][5009]" % (str(msg)), 1)
            return 0