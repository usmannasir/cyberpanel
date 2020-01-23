#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys

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
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom
from backup.models import DBUsers
import plogical.mysqlUtilities as mysqlUtilities
from plogical.backupUtilities import backupUtilities
from plogical.dnsUtilities import DNS
from mailServer.models import Domains as eDomains
from random import randint
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
            return ProcessUtilities.outputExecutioner(command).split('\n')
        else:
            key, secret = self.getAWSData()
            command = 'export RESTIC_PASSWORD=%s AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s  && restic -r s3:s3.amazonaws.com/%s snapshots' % (
                self.passwordFile, key, secret, self.website)
            return ProcessUtilities.outputExecutioner(command).split('\n')

    def fetchCurrentBackups(self):
        try:
            self.website = self.extraArgs['website']
            self.backupDestinations = self.extraArgs['backupDestinations']
            self.passwordFile = self.extraArgs['password']

            result = self.getRemoteBackups()

            activator = 0
            json_data = "["
            checker = 0

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

                        dic = {'id': entry[0],
                               'date': "%s %s" % (entry[2], entry[3]),
                               'host': entry[5],
                               'path': entry[-1]
                               }

                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            logging.writeToFile(str(msg))

    ####

    def getAWSData(self):
        key = self.backupDestinations.split('/')[-1]
        path = '/home/cyberpanel/aws/%s' % (key)
        secret = open(path, 'r').read()
        return key, secret

    def awsFunction(self, fType, backupPath=None, snapshotID=None, bType=None):
        try:
            if fType == 'backup':
                key, secret = self.getAWSData()

                command = 'export AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s  && restic -r s3:s3.amazonaws.com/%s backup %s --password-file %s' % (
                    key, secret, self.website.domain, backupPath, self.passwordFile)

                result = ProcessUtilities.outputExecutioner(command)

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

                    command = 'export RESTIC_PASSWORD=%s AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s  && restic -r s3:s3.amazonaws.com/%s restore %s --target /' % (
                        self.passwordFile,
                        key, secret, self.website, snapshotID)

                    result = ProcessUtilities.outputExecutioner(command)

                    if result.find('restoring') == -1:
                        logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                        return 0
                else:
                    self.backupDestinations = self.jobid.destination

                    key, secret = self.getAWSData()

                    command = 'export AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s  && restic -r s3:s3.amazonaws.com/%s restore %s --password-file %s --target /' % (
                        key, secret, self.website, snapshotID, self.passwordFile)

                    result = ProcessUtilities.outputExecutioner(command)

                    if result.find('restoring') == -1:
                        logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                        return 0

                return 1


        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [88][5009]" % (str(msg)), 1)
            return 0

    def localFunction(self, backupPath, type, restore=None):
        if restore == None:
            command = 'restic -r %s backup %s --password-file %s --exclude %s' % (
                self.repoPath, backupPath, self.passwordFile, self.repoPath)
            result = ProcessUtilities.outputExecutioner(command)

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
        else:
            repoLocation = '/home/%s/incbackup' % (self.website)
            command = 'restic -r %s restore %s --target / --password-file %s' % (
                repoLocation, self.jobid.snapshotid, self.passwordFile)

            result = ProcessUtilities.outputExecutioner(command)

            if result.find('restoring') == -1:
                logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                return 0

            return 1

    def sftpFunction(self, backupPath, type, restore=None):
        if restore == None:
            remotePath = '/home/backup/%s' % (self.website.domain)
            command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s backup %s --password-file %s --exclude %s' % (
                self.backupDestinations, remotePath, backupPath, self.passwordFile, self.repoPath)
            result = ProcessUtilities.outputExecutioner(command)

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
        else:
            if self.reconstruct == 'remote':
                repoLocation = '/home/backup/%s' % (self.website)
                command = 'export RESTIC_PASSWORD=%s PATH=${PATH}:/usr/bin && restic -r %s:%s restore %s --target /' % (
                    self.passwordFile,
                    self.backupDestinations, repoLocation, self.jobid)
                result = ProcessUtilities.outputExecutioner(command)
                if result.find('restoring') == -1:
                    logging.statusWriter(self.statusPath, 'Failed: %s. [5009]' % (result), 1)
                    return 0
            else:
                repoLocation = '/home/backup/%s' % (self.website)
                command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s restore %s --target / --password-file %s' % (
                    self.jobid.destination, repoLocation, self.jobid.snapshotid, self.passwordFile)
                result = ProcessUtilities.outputExecutioner(command)
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
                                                                       '/home/cyberpanel', 'dummy', 'dummy') == 0:
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
                                                                       '/home/cyberpanel', 'dummy', 'dummy') == 0:
                    raise BaseException('Can not restore database backup.')

            try:
                if self.reconstruct == 'remote':
                    os.remove('/home/cyberpanel/%s' % (self.path.split('/')[-1]))
                else:
                    os.remove('/home/cyberpanel/%s.sql' % (self.jobid.type.split(':')[1]))
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

            if self.reconstruct == 'remote':
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

            ######### Generating meta

            ## XML Generation

            metaFileXML = Element('metaFile')

            child = SubElement(metaFileXML, 'masterDomain')
            child.text = self.website.domain

            child = SubElement(metaFileXML, 'phpSelection')
            child.text = self.website.phpSelection

            child = SubElement(metaFileXML, 'externalApp')
            child.text = self.website.externalApp

            childDomains = self.website.childdomains_set.all()

            databases = self.website.databases_set.all()

            ## Child domains XML

            childDomainsXML = Element('ChildDomains')

            for items in childDomains:
                childDomainXML = Element('domain')

                child = SubElement(childDomainXML, 'domain')
                child.text = items.domain
                child = SubElement(childDomainXML, 'phpSelection')
                child.text = items.phpSelection
                child = SubElement(childDomainXML, 'path')
                child.text = items.path

                childDomainsXML.append(childDomainXML)

            metaFileXML.append(childDomainsXML)

            ## Databases XML

            databasesXML = Element('Databases')

            for items in databases:
                try:
                    dbuser = DBUsers.objects.get(user=items.dbUser)
                    userToTry = items.dbUser
                except:
                    dbusers = DBUsers.objects.all().filter(user=items.dbUser)
                    for it in dbusers:
                        dbuser = it
                        break

                    userToTry = mysqlUtilities.mysqlUtilities.fetchuser(items.dbName)

                    if userToTry == 0 or userToTry == 1:
                        continue

                    try:
                        dbuser = DBUsers.objects.get(user=userToTry)
                    except:
                        dbusers = DBUsers.objects.all().filter(user=userToTry)
                        for it in dbusers:
                            dbuser = it
                            break


                databaseXML = Element('database')

                child = SubElement(databaseXML, 'dbName')
                child.text = items.dbName
                child = SubElement(databaseXML, 'dbUser')
                child.text = userToTry
                child = SubElement(databaseXML, 'password')
                child.text = dbuser.password

                databasesXML.append(databaseXML)

            metaFileXML.append(databasesXML)

            ## Get Aliases

            aliasesXML = Element('Aliases')

            aliases = backupUtilities.getAliases(self.website.domain)

            for items in aliases:
                child = SubElement(aliasesXML, 'alias')
                child.text = items

            metaFileXML.append(aliasesXML)

            ## Finish Alias

            ## DNS Records XML

            try:

                dnsRecordsXML = Element("dnsrecords")
                dnsRecords = DNS.getDNSRecords(self.website.domain)

                for items in dnsRecords:
                    dnsRecordXML = Element('dnsrecord')

                    child = SubElement(dnsRecordXML, 'type')
                    child.text = items.type
                    child = SubElement(dnsRecordXML, 'name')
                    child.text = items.name
                    child = SubElement(dnsRecordXML, 'content')
                    child.text = items.content
                    child = SubElement(dnsRecordXML, 'priority')
                    child.text = str(items.prio)

                    dnsRecordsXML.append(dnsRecordXML)

                metaFileXML.append(dnsRecordsXML)

            except BaseException as msg:
                logging.statusWriter(self.statusPath, '%s. [158:prepMeta]' % (str(msg)), 1)

            ## Email accounts XML

            try:
                emailRecordsXML = Element('emails')
                eDomain = eDomains.objects.get(domain=self.website.domain)
                emailAccounts = eDomain.eusers_set.all()

                for items in emailAccounts:
                    emailRecordXML = Element('emailAccount')

                    child = SubElement(emailRecordXML, 'email')
                    child.text = items.email
                    child = SubElement(emailRecordXML, 'password')
                    child.text = items.password

                    emailRecordsXML.append(emailRecordXML)

                metaFileXML.append(emailRecordsXML)
            except BaseException as msg:
                pass
                #logging.statusWriter(self.statusPath, '%s. [warning:179:prepMeta]' % (str(msg)), 1)

            ## Email meta generated!

            def prettify(elem):
                """Return a pretty-printed XML string for the Element.
                """
                rough_string = ElementTree.tostring(elem, 'utf-8')
                reparsed = minidom.parseString(rough_string)
                return reparsed.toprettyxml(indent="  ")

            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018/meta.xml -- metaPath

            metaPath = '/home/cyberpanel/%s' % (str(randint(1000, 9999)))

            xmlpretty = prettify(metaFileXML).encode('ascii', 'ignore')
            metaFile = open(metaPath, 'w')
            metaFile.write(xmlpretty.decode('utf-8'))
            metaFile.close()
            os.chmod(metaPath, 0o640)

            ## meta generated

            logging.statusWriter(self.statusPath, 'Meta data is ready..', 1)

            metaPathNew = '/home/%s/meta.xml' % (self.website.domain)
            command = 'mv %s %s' % (metaPath, metaPathNew)
            ProcessUtilities.executioner(command)

            return 1

        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [207][5009]" % (str(msg)), 1)
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
                if mysqlUtilities.mysqlUtilities.createDatabaseBackup(items.dbName, '/home/cyberpanel') == 0:
                    return 0

                dbPath = '/home/cyberpanel/%s.sql' % (items.dbName)

                if self.backupDestinations == 'local':
                    if self.localFunction(dbPath, 'database') == 0:
                        return 0
                elif self.backupDestinations[:4] == 'sftp':
                    if self.sftpFunction(dbPath, 'database') == 0:
                        return 0
                else:
                    if self.awsFunction('backup', dbPath, '', 'database') == 0:
                        return 0

                try:
                    os.remove('/home/cyberpanel/%s.sql' % (items.dbName))
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
                result = ProcessUtilities.outputExecutioner(command)
                if result.find('config file already exists') == -1:
                    logging.statusWriter(self.statusPath, result, 1)

            elif self.backupDestinations[:4] == 'sftp':
                remotePath = '/home/backup/%s' % (self.website.domain)
                command = 'export PATH=${PATH}:/usr/bin && restic init --repo %s:%s --password-file %s' % (
                    self.backupDestinations, remotePath, self.passwordFile)
                result = ProcessUtilities.outputExecutioner(command)
                if result.find('config file already exists') == -1:
                    logging.statusWriter(self.statusPath, result, 1)
            else:
                key, secret = self.getAWSData()
                command = 'export AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s  && restic -r s3:s3.amazonaws.com/%s init --password-file %s' % (
                    key, secret, self.website.domain, self.passwordFile)
                result = ProcessUtilities.outputExecutioner(command)
                if result.find('config file already exists') == -1:
                    logging.statusWriter(self.statusPath, result, 1)
                return 1

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
        self.statusPath = self.extraArgs['tempPath']
        website = self.extraArgs['website']
        self.backupDestinations = self.extraArgs['backupDestinations']
        websiteData = self.extraArgs['websiteData']
        websiteEmails = self.extraArgs['websiteEmails']
        websiteDatabases = self.extraArgs['websiteDatabases']

        ### Checking if restic is installed before moving on

        command = 'restic'
        if ProcessUtilities.outputExecutioner(command).find('restic is a backup program which') == -1:
            logging.statusWriter(self.statusPath, 'It seems restic is not installed, for incremental backups to work '
                                                  'restic must be installed. You can manually install restic using this '
                                                  'guide -> http://go.cyberpanel.net/restic. [5009]', 1)
            return 0

        ## Restic check completed.

        self.website = Websites.objects.get(domain=website)

        self.jobid = IncJob(website=self.website)
        self.jobid.save()

        self.passwordFile = '/home/%s/%s' % (self.website.domain, self.website.domain)

        self.repoPath = '/home/%s/incbackup' % (self.website.domain)

        if not os.path.exists(self.passwordFile):
            password = randomPassword.generate_pass()
            command = 'echo "%s" > %s' % (password, self.passwordFile)
            ProcessUtilities.executioner(command, self.website.externalApp, True)

            command = 'chmod 600 %s' % (self.passwordFile)
            ProcessUtilities.executioner(command)

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
