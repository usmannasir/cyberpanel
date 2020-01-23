#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from plogical.processUtilities import ProcessUtilities
import time
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

    def run(self):

        if self.function == 'createBackup':
            self.createBackup()

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
                    userToTry = items.dbUser
                    for it in dbusers:
                        dbuser = it
                        break

                    userToTry = mysqlUtilities.mysqlUtilities.fetchuser(items.dbName)

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
                logging.writeToFile(self.statusPath, '%s. [warning:179:prepMeta]' % (str(msg)), 1)

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
            metaFile.write(xmlpretty)
            metaFile.close()
            os.chmod(metaPath, 0o640)

            ## meta generated

            logging.statusWriter(self.statusPath, 'Meta data is ready..', 1)

            metaPathNew = '/home/%s/meta.xml' % (self.website.domain)
            command = 'mv %s %s' % (metaPath, metaPathNew)
            ProcessUtilities.executioner(command)

            command = 'chown %s:%s %s' % (self.website.externalApp, self.website.externalApp, metaPathNew)
            ProcessUtilities.executioner(command)

            return 1

        except BaseException as msg:
            logging.statusWriter(self.statusPath, "%s [207][5009]" % (str(msg)), 1)
            return 0

    def backupData(self):
        try:
            logging.statusWriter(self.statusPath, 'Backing up data..', 1)

            if self.backupDestinations == 'local':
                backupPath = '/home/%s' % (self.website.domain)
                command = 'restic -r %s backup %s --password-file %s --exclude %s' % (self.repoPath, backupPath, self.passwordFile, self.repoPath)
                snapShotid = ProcessUtilities.outputExecutioner(command).split(' ')[-2]

                newSnapshot = JobSnapshots(job=self.jobid, type='data:%s' % (backupPath), snapshotid=snapShotid, destination=self.backupDestinations)
                newSnapshot.save()


            elif self.backupDestinations[:4] == 'sftp':
                remotePath = '/home/backup/%s' % (self.website.domain)
                backupPath = '/home/%s' % (self.website.domain)
                command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s backup %s --password-file %s --exclude %s' % (self.backupDestinations, remotePath, backupPath, self.passwordFile, self.repoPath)
                snapShotid = ProcessUtilities.outputExecutioner(command).split(' ')[-2]
                newSnapshot = JobSnapshots(job=self.jobid, type='data:%s' % (remotePath), snapshotid=snapShotid,
                                           destination=self.backupDestinations)
                newSnapshot.save()

            logging.statusWriter(self.statusPath, 'Data for %s backed to %s.' % (self.website.domain, self.backupDestinations), 1)
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath,'%s. [IncJobs.backupData.223][5009]' % str(msg), 1)
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
                    command = 'restic -r %s backup %s --password-file %s' % (self.repoPath, dbPath, self.passwordFile)
                    snapShotid = ProcessUtilities.outputExecutioner(command).split(' ')[-2]

                    newSnapshot = JobSnapshots(job=self.jobid, type='database:%s' % (items.dbName), snapshotid=snapShotid, destination=self.backupDestinations)
                    newSnapshot.save()

                elif self.backupDestinations[:4] == 'sftp':
                    remotePath = '/home/backup/%s' % (self.website.domain)
                    command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s backup %s --password-file %s --exclude %s' % (
                    self.backupDestinations, remotePath, dbPath, self.passwordFile, self.repoPath)
                    snapShotid = ProcessUtilities.outputExecutioner(command).split(' ')[-2]
                    newSnapshot = JobSnapshots(job=self.jobid, type='database:%s' % (items.dbName), snapshotid=snapShotid,
                                               destination=self.backupDestinations)
                    newSnapshot.save()
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath,'%s. [IncJobs.backupDatabases.269][5009]' % str(msg), 1)
            return 0

    def emailBackup(self):
        try:
            logging.statusWriter(self.statusPath, 'Backing up emails..', 1)

            backupPath = '/home/vmail/%s' % (self.website.domain)

            if os.path.exists(backupPath):
                if self.backupDestinations == 'local':
                    logging.statusWriter(self.statusPath, 'hello world', 1)
                    command = 'restic -r %s backup %s --password-file %s' % (
                    self.repoPath, backupPath, self.passwordFile)
                    snapShotid = ProcessUtilities.outputExecutioner(command).split(' ')[-2]

                    newSnapshot = JobSnapshots(job=self.jobid, type='email:%s' % (backupPath), snapshotid=snapShotid,
                                               destination=self.backupDestinations)
                    newSnapshot.save()
                    logging.statusWriter(self.statusPath, 'hello world 2', 1)

                elif self.backupDestinations[:4] == 'sftp':
                    remotePath = '/home/backup/%s' % (self.website.domain)
                    command = 'export PATH=${PATH}:/usr/bin && restic -r %s:%s backup %s --password-file %s --exclude %s' % (
                        self.backupDestinations, remotePath, backupPath, self.passwordFile, self.repoPath)
                    snapShotid = ProcessUtilities.outputExecutioner(command).split(' ')[-2]
                    newSnapshot = JobSnapshots(job=self.jobid, type='email:%s' % (backupPath), snapshotid=snapShotid,
                                               destination=self.backupDestinations)
                    newSnapshot.save()

            logging.statusWriter(self.statusPath, 'Emails for %s backed to %s.' % (self.website.domain, self.backupDestinations), 1)
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath,'%s. [IncJobs.backupDatabases.269][5009]' % str(msg), 1)
            return 0

    def initiateRepo(self):
        try:
            logging.statusWriter(self.statusPath, 'Will first initiate backup repo..', 1)

            if self.backupDestinations == 'local':
                command = 'restic init --repo %s --password-file %s' % (self.repoPath, self.passwordFile)
                ProcessUtilities.executioner(command, self.website.externalApp)

            elif self.backupDestinations[:4] == 'sftp':
                remotePath = '/home/backup/%s' % (self.website.domain)
                command = 'export PATH=${PATH}:/usr/bin && restic init --repo %s:%s --password-file %s' % (self.backupDestinations, remotePath, self.passwordFile)
                ProcessUtilities.executioner(command)

            logging.statusWriter(self.statusPath, 'Repo %s initiated for %s.' % (self.backupDestinations, self.website.domain), 1)
            return 1
        except BaseException as msg:
            logging.statusWriter(self.statusPath,'%s. [IncJobs.initiateRepo.47][5009]' % str(msg), 1)
            return 0

    def createBackup(self):
        self.statusPath = self.extraArgs['tempPath']
        website = self.extraArgs['website']
        self.backupDestinations = self.extraArgs['backupDestinations']
        websiteData = self.extraArgs['websiteData']
        websiteEmails = self.extraArgs['websiteEmails']
        websiteSSLs = self.extraArgs['websiteSSLs']
        websiteDatabases = self.extraArgs['websiteDatabases']

        self.website = Websites.objects.get(domain=website)

        newJob = IncJob(website=self.website)
        newJob.save()

        self.jobid = newJob

        self.passwordFile = '/home/%s/%s' % (self.website.domain, self.website.domain)
        password = randomPassword.generate_pass()

        self.repoPath = '/home/%s/incbackup' % (self.website.domain)

        if not os.path.exists(self.passwordFile):
            command = 'echo "%s" > %s' % (password, self.passwordFile)
            ProcessUtilities.executioner(command, self.website.externalApp)


        if self.initiateRepo() == 0:
            return

        if self.prepareBackupMeta() == 0:
            return

        if websiteData:
            if self.backupData() == 0:
                return

        if websiteDatabases:
            if self.backupDatabases() == 0:
                return


        if websiteEmails:
            if self.emailBackup() == 0:
                return

        logging.statusWriter(self.statusPath, 'Completed', 1)