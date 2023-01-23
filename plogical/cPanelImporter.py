#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import argparse
from plogical.processUtilities import ProcessUtilities
from random import randint
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import re
import shutil
from dns.models import Domains, Records
from manageServices.models import PDNSStatus
from loginSystem.models import Administrator
from plogical.dnsUtilities import DNS
import MySQLdb as mysql
import MySQLdb.cursors as cursors
import shlex
import subprocess
from databases.models import Databases
from websiteFunctions.models import Websites, ChildDomains as CDomains
from plogical.vhost import vhost
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.mailUtilities import mailUtilities
from mailServer.models import EUsers
import time

class ChildDomains:

    def __init__(self, domain, addon):
        self.domain = domain
        self.addon = addon


class cPanelImporter:
    MailDir = 1
    MdBox = 0
    mainBackupPath = '/home/backup/'

    def __init__(self, backupFile, logFile):
        self.backupFile = backupFile
        self.fileName = backupFile.split('/')[-1].replace('.tar.gz', '')
        self.logFile = logFile
        self.PHPVersion = ''
        self.email = ''
        self.mainDomain = ''
        self.homeDir = ''
        self.documentRoot = ''
        self.mailFormat = 1
        self.externalApp = ''

        ## New

        self.MainSite = []
        self.OtherDomains = []
        self.OtherDomainNames = []
        self.InheritPHP = ''

    def LoadDomains(self):
        try:
            ###
            CompletPathToExtractedArchive = cPanelImporter.mainBackupPath + self.fileName
            ### Find Domain Name
            import json
            UserData = json.loads(open('%s/userdata/cache.json' % (CompletPathToExtractedArchive), 'r').read())

            for key, value in UserData.items():
                if value[2] == 'main':
                    self.MainSite = value
                    self.PHPVersion = value[9]
                    self.InheritPHP = self.PHPDecider()
                else:
                    self.OtherDomainNames.append(key)
                    self.OtherDomains.append(value)

        except BaseException as msg:
            print(str(msg))

    def PHPDecider(self):

        if self.PHPVersion == 'inherit':
            self.PHPVersion = 'PHP 7.4'
        if self.PHPVersion.find('53') > -1:
            self.PHPVersion = 'PHP 5.3'
        elif self.PHPVersion.find('54') > -1:
            self.PHPVersion = 'PHP 5.4'
        elif self.PHPVersion.find('55') > -1:
            self.PHPVersion = 'PHP 5.5'
        elif self.PHPVersion.find('56') > -1:
            self.PHPVersion = 'PHP 5.6'
        elif self.PHPVersion.find('70') > -1:
            self.PHPVersion = 'PHP 7.0'
        elif self.PHPVersion.find('71') > -1:
            self.PHPVersion = 'PHP 7.1'
        elif self.PHPVersion.find('72') > -1:
            self.PHPVersion = 'PHP 7.2'
        elif self.PHPVersion.find('73') > -1:
            self.PHPVersion = 'PHP 7.3'
        elif self.PHPVersion.find('74') > -1:
            self.PHPVersion = 'PHP 7.4'
        elif self.PHPVersion.find('80') > -1:
            self.PHPVersion = 'PHP 8.0'
        elif self.PHPVersion.find('81') > -1:
            self.PHPVersion = 'PHP 8.1'
            
        if self.PHPVersion == '':
            if self.InheritPHP != '':
                self.PHPVersion = self.InheritPHP
            else:
                self.PHPVersion = 'PHP 7.4'

        return self.PHPVersion

    def SetupSSL(self, path, domain):

        data = open(path, 'r').readlines()

        Key = []
        Cert = []

        KeyCheck = 1
        CertCheck = 0

        for items in data:
            if KeyCheck == 1 and items.find('-----END RSA PRIVATE KEY-----') > -1:
                KeyCheck = 0
                CertCheck = 1
                Key.append(items)
                continue
            else:
                Key.append(items)

            if CertCheck == 1:
                Cert.append(items)


        KeyPath = '/home/cyberpanel/%s' % (str(randint(1000, 9999)))

        writeToFile = open(KeyPath, 'w')

        for items in Key:
            writeToFile.writelines(items)

        writeToFile.close()

        ##

        CertPath = '/home/cyberpanel/%s' % (str(randint(1000, 9999)))

        writeToFile = open(CertPath, 'w')

        for items in Cert:
            writeToFile.writelines(items)

        writeToFile.close()

        virtualHostUtilities.saveSSL(domain, KeyPath, CertPath)

    def ExtractBackup(self):
        try:

            message = 'Extracting main cPanel archive file: %s' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            if not os.path.exists(cPanelImporter.mainBackupPath):
                os.mkdir(cPanelImporter.mainBackupPath)

            os.chdir(cPanelImporter.mainBackupPath)

            command = 'tar -xf %s --directory %s' % (self.backupFile, cPanelImporter.mainBackupPath)
            ProcessUtilities.normalExecutioner(command)

            message = '%s successfully extracted.' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            return 1

        except BaseException as msg:
            message = 'Failed to extract backup for file %s, error message: %s. [ExtractBackup]' % (
            self.backupFile, str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0

    def CreateMainWebsite(self):
        try:

            message = 'Creating main account from archive file: %s' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            ## Paths

            DomainName = self.MainSite[3]
            self.mainDomain = DomainName
            CompletPathToExtractedArchive = cPanelImporter.mainBackupPath + self.fileName
            DomainMeta = '%s/userdata/%s' % (CompletPathToExtractedArchive, DomainName)

            ### Find Domain Name

            message = 'Detected main domain for this file is: %s.' % (DomainName)
            logging.statusWriter(self.logFile, message, 1)

            ## Find PHP Version

            message = 'Finding PHP version for %s.' % (DomainName)
            logging.statusWriter(self.logFile, message, 1)

            self.PHPVersion = self.MainSite[9]
            self.PHPDecider()

            message = 'PHP version of %s is %s.' % (DomainName, self.PHPVersion)
            logging.statusWriter(self.logFile, message, 1)

            ## Find Email

            message = 'Finding Server Admin email for %s.' % (DomainName)
            logging.statusWriter(self.logFile, message, 1)

            data = open(DomainMeta, 'r').readlines()

            for items in data:
                if items.find('serveradmin') > -1:
                    self.email = items.split(' ')[-1].replace('\n', '')
                    break

            message = 'Server Admin email for %s is %s.' % (DomainName, self.email)
            logging.statusWriter(self.logFile, message, 1)

            ## Create Site

            message = 'Calling core to create %s.' % (DomainName)
            logging.statusWriter(self.logFile, message, 1)

            self.externalApp = "".join(re.findall("[a-zA-Z]+", DomainName))[:7]

            try:
                counter = 0
                while True:
                    tWeb = Websites.objects.get(externalApp=self.externalApp)
                    self.externalApp = '%s%s' % (tWeb.externalApp, str(counter))
                    counter = counter + 1
                    print(self.externalApp)
            except BaseException as msg:
                logging.statusWriter(self.logFile, str(msg), 1)
                time.sleep(2)


            result = virtualHostUtilities.createVirtualHost(DomainName, self.email, self.PHPVersion, self.externalApp, 1, 0,
                                                            0, 'admin', 'Default', 0)

            if result[0] == 1:
                pass
            else:
                message = 'Failed to create main site %s from archive file: %s' % (DomainName, self.backupFile)
                logging.statusWriter(self.logFile, message, 1)
                return 0

            message = 'Successfully created %s from core.' % (DomainName)
            logging.statusWriter(self.logFile, message, 1)

            ### Let see if there is SSL

            message = 'Detecting SSL for %s.' % (DomainName)
            logging.statusWriter(self.logFile, message, 1)

            SSLPath = '%s/apache_tls/%s' % (CompletPathToExtractedArchive, DomainName)

            if os.path.exists(SSLPath):
                message = 'SSL found for %s, setting up.' % (DomainName)
                logging.statusWriter(self.logFile, message, 1)
                self.SetupSSL(SSLPath, DomainName)
                message = 'SSL set up OK for %s.' % (DomainName)
                logging.statusWriter(self.logFile, message, 1)
            else:
                message = 'SSL not detected for %s, you can later issue SSL from Manage SSL in CyberPanel.' % (DomainName)
                logging.statusWriter(self.logFile, message, 1)

            ## Document root

            message = 'Restoring document root files for %s.' % (DomainName)
            logging.statusWriter(self.logFile, message, 1)

            message = 'self.MainSite[4] %s.' % (self.MainSite[4])
            logging.statusWriter(self.logFile, message, 1)

            message = 'self.MainSite[0] %s.' % (self.MainSite[0])
            logging.statusWriter(self.logFile, message, 1)

            if self.MainSite[4].find('home/') > -1:
                self.homeDir = self.MainSite[4].replace('/home/%s/' % (self.MainSite[0]), '')
            else:
                self.homeDir = self.MainSite[4].replace('/home2/%s/' % (self.MainSite[0]), '')

            message = 'self.homeDir %s.' % (self.homeDir)
            logging.statusWriter(self.logFile, message, 1)

            nowPath = '/home/%s/public_html' % (DomainName)
            if os.path.exists(nowPath):
                shutil.rmtree(nowPath)

            movePath = '%s/homedir/%s' % (
            CompletPathToExtractedArchive, self.homeDir)

            shutil.copytree(movePath, nowPath, symlinks=True)

            message = 'Main site %s created from archive file: %s' % (DomainName, self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            return 1

        except BaseException as msg:
            message = 'Failed to create main website from backup file %s, error message: %s.' % (
            self.backupFile, str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0

    def CreateChildDomains(self):
        try:

            message = 'Creating child domains from archive file: %s' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            CompletPathToExtractedArchive = cPanelImporter.mainBackupPath + self.fileName

            ### Find Possible Child Domains

            message = 'Finding Addon/Subdomains from backup file %s. Account main domain was %s.' % (self.backupFile, self.mainDomain)
            logging.statusWriter(self.logFile, message, 1)

            message = 'Following Addon/Subdomains found for backup file %s. Account main domain was %s.' % (
            self.backupFile, self.mainDomain)
            logging.statusWriter(self.logFile, message, 1)

            for items in self.OtherDomainNames:
                print(items)

            ## Starting Child-domains creation

            message = 'Starting Addon/Subdomains creation from backup file %s. Account main domain was %s.' % (
                self.backupFile, self.mainDomain)
            logging.statusWriter(self.logFile, message, 1)

            counter = 0

            for items in self.OtherDomainNames:

                try:

                    message = 'Creating %s.' % (items)
                    logging.statusWriter(self.logFile, message, 1)

                    path = '/home/' + self.mainDomain + '/' + items

                    ## Find PHP Version

                    self.PHPVersion = self.OtherDomains[counter][9]
                    self.PHPDecider()

                    message = 'Calling core to create %s.' % (items)
                    logging.statusWriter(self.logFile, message, 1)

                    result = virtualHostUtilities.createDomain(self.mainDomain, items, self.PHPVersion, path, 1, 0,
                                                               0, 'admin', 0)

                    if result[0] == 1:
                        message = 'Child domain %s created from archive file: %s' % (items, self.backupFile)
                        logging.statusWriter(self.logFile, message, 1)
                    else:
                        message = 'Failed to create Child domain %s from archive file: %s' % (items, self.backupFile)
                        logging.statusWriter(self.logFile, message, 1)

                    ## Setup SSL

                    message = 'Detecting SSL for %s.' % (items)
                    logging.statusWriter(self.logFile, message, 1)

                    SSLPath = '%s/apache_tls/%s' % (CompletPathToExtractedArchive, items)

                    if os.path.exists(SSLPath):
                        message = 'SSL found for %s, setting up.' % (items)
                        logging.statusWriter(self.logFile, message, 1)
                        self.SetupSSL(SSLPath, items)
                        message = 'SSL set up OK for %s.' % (items)
                        logging.statusWriter(self.logFile, message, 1)
                    else:
                        SSLPath = '%s/apache_tls/%s.%s' % (CompletPathToExtractedArchive, items, self.mainDomain)
                        if os.path.exists(SSLPath):
                            message = 'SSL found for %s, setting up.' % (items)
                            logging.statusWriter(self.logFile, message, 1)
                            self.SetupSSL(SSLPath, items)
                            message = 'SSL set up OK for %s.' % (items)
                            logging.statusWriter(self.logFile, message, 1)
                        else:
                            message = 'SSL not detected for %s, you can later issue SSL from Manage SSL in CyberPanel.' % (
                                items)
                            logging.statusWriter(self.logFile, message, 1)

                    ## Creating Document root for childs

                    message = 'Restoring document root files for %s.' % (items)
                    logging.statusWriter(self.logFile, message, 1)


                    message = 'self.OtherDomains[counter][4] %s.' % (self.OtherDomains[counter][4])
                    logging.statusWriter(self.logFile, message, 1)

                    message = 'self.MainSite[0] %s.' % (self.MainSite[0])
                    logging.statusWriter(self.logFile, message, 1)

                    if self.OtherDomains[counter][4].find('home/') > -1:
                        ChildDocRoot = self.OtherDomains[counter][4].replace('/home/%s/' % (self.MainSite[0]), '')
                    else:
                        ChildDocRoot = self.OtherDomains[counter][4].replace('/home2/%s/' % (self.MainSite[0]), '')


                    #ChildDocRoot = self.OtherDomains[counter][4].replace('/home/%s/' % (self.MainSite[0]), '')

                    message = 'ChildDocRoot %s.' % (ChildDocRoot)
                    logging.statusWriter(self.logFile, message, 1)

                    if os.path.exists(path):
                        shutil.rmtree(path)

                    movePath = '%s/homedir/%s' % (CompletPathToExtractedArchive, ChildDocRoot)
                    logging.statusWriter(self.logFile, 'Document root in cPanel Backup for %s is %s' % (items, movePath), 1)

                    if os.path.exists(movePath):
                        shutil.copytree(movePath, path)

                    message = 'Successfully created child domain.'
                    logging.statusWriter(self.logFile, message, 1)

                    counter = counter + 1

                except BaseException as msg:
                    message = 'Failed to create child domain from backup file %s, error message: %s. Moving on..' % (
                        self.backupFile, str(msg))
                    logging.statusWriter(self.logFile, message, 1)
                    counter = counter + 1

            return 1

        except BaseException as msg:
            message = 'Failed to create child domain from backup file %s, error message: %s.' % (
            self.backupFile, str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0

    def createDummyChild(self, childDomain):
        path = '/home/%s/public_html/%s' % (self.mainDomain, childDomain)
        virtualHostUtilities.createDomain(self.mainDomain, childDomain, self.PHPVersion, path, 0, 0,
                                                   0, 'admin', 0)

    def CreateDNSRecords(self):
        try:

            message = 'We are going to create DNS records now, please note we will not create DKIM records. Make sure to create them from CyberPanel interface using our DKIM manager.'
            logging.statusWriter(self.logFile, message, 1)

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
            admin = Administrator.objects.get(userName='admin')

            CompletPathToExtractedArchive = cPanelImporter.mainBackupPath + self.fileName
            DNSZonesPath = '%s/dnszones' % (CompletPathToExtractedArchive)

            for items in os.listdir(DNSZonesPath):
                topLevelDomain = items.replace('.db', '', 1)

                message = 'Creating DNS records for %s' % (topLevelDomain)
                logging.statusWriter(self.logFile, message, 1)

                try:
                    Domains.objects.get(name=topLevelDomain).delete()
                except:
                    pass

                try:
                    pdns = PDNSStatus.objects.get(pk=1)
                    if pdns.type == 'MASTER':
                        zone = Domains(admin=admin, name=topLevelDomain, type="MASTER")
                        zone.save()
                    else:
                        zone = Domains(admin=admin, name=topLevelDomain, type="NATIVE")
                        zone.save()
                except:
                    zone = Domains(admin=admin, name=topLevelDomain, type="NATIVE")
                    zone.save()
                    pass

                content = "ns1." + topLevelDomain + " hostmaster." + topLevelDomain + " 1 10800 3600 604800 3600"

                soaRecord = Records(domainOwner=zone,
                                    domain_id=zone.id,
                                    name=topLevelDomain,
                                    type="SOA",
                                    content=content,
                                    ttl=3600,
                                    prio=0,
                                    disabled=0,
                                    auth=1)
                soaRecord.save()

                CurrentZonePath = '%s/%s' % (DNSZonesPath, items)

                data = open(CurrentZonePath, 'r').readlines()

                SOACheck = 0
                start = 0

                for items in data:
                    try:
                        if items.find('SOA') > -1:
                            SOACheck = 1
                            continue

                        if SOACheck == 1 and items.find(')') > -1:
                            SOACheck = 0
                            start = 1
                            continue
                        else:
                            pass

                        if start == 1:
                            if len(items) > 3:
                                if items.find("DKIM1") > -1:
                                    continue
                                RecordsData = items.split('\t')

                                if RecordsData[3] == 'A':
                                    RecordsData[4] = ipAddress

                                if RecordsData[0].find(topLevelDomain) > -1:
                                    if RecordsData[3] == 'MX':
                                        DNS.createDNSRecord(zone, RecordsData[0].rstrip('.'), RecordsData[3],RecordsData[5].rstrip('.').rstrip('.\n'), int(RecordsData[4]), RecordsData[1])
                                    else:
                                        DNS.createDNSRecord(zone, RecordsData[0].rstrip('.'), RecordsData[3], RecordsData[4].rstrip('.').rstrip('.\n'), 0, RecordsData[1])
                                else:
                                    if RecordsData[3] == 'MX':
                                        DNS.createDNSRecord(zone, RecordsData[0] + '.' + topLevelDomain, RecordsData[3],
                                                            RecordsData[5].rstrip('.').rstrip('.\n'), RecordsData[4],
                                                            RecordsData[1])
                                    else:
                                        DNS.createDNSRecord(zone, RecordsData[0] + '.' + topLevelDomain , RecordsData[3], RecordsData[4].rstrip('.').rstrip('.\n'), 0,
                                                            RecordsData[1])
                    except BaseException as msg:
                        message = 'Failed while creating DNS entry for %s, error message: %s.' % (topLevelDomain, str(msg))
                        logging.statusWriter(self.logFile, message, 1)

                message = 'DNS records successfully created for %s.' % (topLevelDomain)
                logging.statusWriter(self.logFile, message, 1)

            return 1

        except BaseException as msg:
            message = 'Failed to create DNS records from file %s, error message: %s.' % (
            self.backupFile, str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0

    def setupConnection(self, db=None):
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]
            password = password.replace('\n', '').replace('\r', '')

            conn = mysql.connect(user='root', passwd=password, cursorclass=cursors.SSCursor)
            cursor = conn.cursor()

            return conn, cursor

        except BaseException as msg:
            message = 'Failed to connect to database, error message: %s. [ExtractBackup]' % (str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0, 0

    def RestoreDatabases(self):
        try:

            message = 'Restoring databases from %s.' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            ##
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]
            ##


            connection, cursor = self.setupConnection()

            CompletPathToExtractedArchive = cPanelImporter.mainBackupPath + self.fileName

            DatabasesPath = '%s/mysql' % (CompletPathToExtractedArchive)

            for items in os.listdir(DatabasesPath):
                if items.find('roundcube') > -1:
                    continue
                if items.endswith('.sql'):
                    message = 'Restoring MySQL dump for %s.' % (items.replace('.sql', ''))
                    logging.statusWriter(self.logFile, message, 1)

                    try:
                        cursor.execute("CREATE DATABASE `%s`" % (items.replace('.sql', '')))
                    except BaseException as msg:
                        message = 'Failed while restoring database %s from backup file %s, error message: %s' % (items.replace('.sql', ''), self.backupFile, str(msg))
                        logging.statusWriter(self.logFile, message, 1)

                    command = 'sudo mysql -u root -p' + password + ' ' + items.replace('.sql', '')

                    cmd = shlex.split(command)

                    DBPath = "%s/%s" % (DatabasesPath, items)

                    with open(DBPath, 'r') as f:
                        res = subprocess.call(cmd, stdin=f)

                    website = Websites.objects.get(domain=self.mainDomain)

                    ## Trying to figure out dbname

                    CommandsPath = '%s/mysql.sql' % (CompletPathToExtractedArchive)

                    data = open(CommandsPath, 'r').readlines()

                    for inItems in data:
                        if inItems.find('GRANT ALL PRIVILEGES') > -1 and inItems.find('localhost') > -1 and inItems.find('_test') == -1:
                            cDBName = inItems.split('`')[1].replace('\\', '')
                            logging.statusWriter(self.logFile, inItems, 1)
                            if cDBName == items.replace('.sql', ''):
                                cDBUser = inItems.replace("`","'").replace("\\","").split("'")[1]
                                message = 'Database user for %s is %s.' % (cDBName, cDBUser)
                                logging.statusWriter(self.logFile, message, 1)
                                if Databases.objects.filter(dbUser=cDBUser).count() > 0:
                                    continue
                                break


                    db = Databases(website=website, dbName=items.replace('.sql', ''), dbUser=cDBUser)
                    db.save()

                    message = 'MySQL dump successfully restored for %s.' % (items.replace('.sql', ''))
                    logging.statusWriter(self.logFile, message, 1)

            message = 'Creating Database users from backup file %s.' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            CommandsPath = '%s/mysql.sql' % (CompletPathToExtractedArchive)

            data = open(CommandsPath, 'r').readlines()

            for items in data:
                if items.find("--") > -1 or items.find("'cyberpanel'@") > -1:
                    continue
                try:
                    cursor.execute(items)
                except BaseException as msg:
                    message = 'Failed while restoring database %s from backup file %s, error message: %s' % (
                    items.replace('.sql', ''), self.backupFile, str(msg))
                    logging.statusWriter(self.logFile, message, 1)

            connection.close()

            message = 'Databases successfully restored.'
            logging.statusWriter(self.logFile, message, 1)

            return 1

        except BaseException as msg:
            message = 'Failed to restore databases from file %s, error message: %s.' % (
            self.backupFile, str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0

    def FixPermissions(self):
        from filemanager.filemanager import FileManager
        fm = FileManager(None, None)
        fm.fixPermissions(self.mainDomain)
        
    def createCronJobs(self):
        try:
            
            message = 'Restoring cron jobs from %s.' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)
            
            CompletPathToExtractedArchive = cPanelImporter.mainBackupPath + self.fileName            
            cronPath = '%s/cron' % (CompletPathToExtractedArchive)
            
            
            if len(os.listdir(cronPath)) == 0:
                message = 'No Cron Job file found.'
                logging.statusWriter(self.logFile, message, 1)
                return 1
            
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                localCronPath = "/var/spool/cron/" + self.externalApp
            else:
                localCronPath = "/var/spool/cron/crontabs/" + self.externalApp
                
            localCronFile = open(localCronPath, "a+")
                
            commandT = 'touch %s' % (localCronPath)
            ProcessUtilities.executioner(commandT, 'root')
            commandT = 'chown %s:%s %s' % (self.externalApp, self.externalApp, localCronPath)
            ProcessUtilities.executioner(commandT, 'root')

            # There's only single file usually but running for all found
            for item in os.listdir(cronPath):
                cronFile = open('%s/%s' % (cronPath, item), 'r')
                cronJobs = cronFile.readlines()
                
                # Filter actual jobs and remove variables and last new line character
                for job in cronJobs:
                    if len(job.split(' ')) > 1:
                        # Valid enough, add it to user
                        localCronFile.write(job)
                    
            message = 'Cron Jobs successfully restored.'
            logging.statusWriter(self.logFile, message, 1)

            return 1
        
        except BaseException as msg:
            message = 'Failed to restore Cron Jobs from file %s, error message: %s.' % (
            self.backupFile, str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0

    def DeleteSite(self):
        vhost.deleteVirtualHostConfigurations(self.mainDomain)

    def checkIfExists(self, virtualHostName):
        if Websites.objects.filter(domain=virtualHostName).count() > 0:
            return 1

        if CDomains.objects.filter(domain=virtualHostName).count() > 0:
            return 1

        return 0

    def RestoreEmails(self):
        try:

            message = 'Restoring emails from archive file: %s' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            CompletPathToExtractedArchive = cPanelImporter.mainBackupPath + self.fileName

            ### Find Mail Format
            UserData = '%s/homedir/mail' % (CompletPathToExtractedArchive)
            FormatPath = '%s/mailbox_format.cpanel' % (UserData)

            message = 'Detecting email format from %s.' % (self.backupFile)
            logging.statusWriter(self.logFile, message, 1)

            try:

                Format = open(FormatPath, 'r').read()

                if Format.find('mdbox') > -1:
                    self.mailFormat = cPanelImporter.MdBox
                    message = 'Mdbox format detected from %s.' % (self.backupFile)
                    logging.statusWriter(self.logFile, message, 1)
                else:
                    self.mailFormat = cPanelImporter.MailDir
                    message = 'Maildir format detected from %s.' % (self.backupFile)
                    logging.statusWriter(self.logFile, message, 1)
            except:
                self.mailFormat = cPanelImporter.MailDir

            ####


            for items in os.listdir(UserData):
                FinalMailDomainPath = '%s/%s' % (UserData, items)
                if os.path.isdir(FinalMailDomainPath):
                    if items[0] == '.':
                        continue
                    if items.find('.') > -1:
                        for it in os.listdir(FinalMailDomainPath):
                            try:
                                if self.checkIfExists(items) == 0:
                                    self.createDummyChild(items)

                                mailUtilities.createEmailAccount(items, it, 'cyberpanel')
                                finalEmailUsername = it + "@" + items
                                message = 'Starting restore for %s.' % (finalEmailUsername)
                                logging.statusWriter(self.logFile, message, 1)
                                eUser = EUsers.objects.get(email=finalEmailUsername)


                                if self.mailFormat == cPanelImporter.MailDir:
                                    eUser.mail = 'maildir:/home/vmail/%s/%s/Maildir' % (items, it)
                                    MailPath = '/home/vmail/%s/%s' % (items, it)

                                    command = 'mkdir -p %s' % (MailPath)
                                    ProcessUtilities.normalExecutioner(command)

                                    command = 'rm -rf %s/Maildir' % (MailPath)
                                    ProcessUtilities.normalExecutioner(command)

                                    MailPathInBackup = '%s/%s' % (FinalMailDomainPath, it)

                                    command = 'mv %s %s/Maildir' % (MailPathInBackup, MailPath)
                                    subprocess.call(command, shell=True)

                                else:
                                    eUser.mail = 'mdbox:/home/vmail/%s/%s/Mdbox' % (items, it)
                                    MailPath = '/home/vmail/%s/%s' % (items, it)

                                    command = 'mkdir -p %s' % (MailPath)
                                    ProcessUtilities.normalExecutioner(command)

                                    command = 'rm -rf %s/Mdbox' % (MailPath)
                                    ProcessUtilities.normalExecutioner(command)

                                    MailPathInBackup = '%s/%s' % (FinalMailDomainPath, it)

                                    command = 'mv %s %s/Mdbox' % (MailPathInBackup, MailPath)
                                    subprocess.call(command, shell=True)

                                ## Also update password

                                PasswordPath = '%s/homedir/etc/%s/shadow' % (CompletPathToExtractedArchive, items)
                                PasswordData = open(PasswordPath, 'r').readlines()

                                for i in PasswordData:
                                    if i.find(it) > -1:
                                        finalPassword = '%s%s' % ('{CRYPT}', i.split(':')[1])
                                        eUser.password = finalPassword

                                eUser.save()

                                message = 'Restore completed for %s.' % (finalEmailUsername)
                                logging.statusWriter(self.logFile, message, 1)
                            except BaseException as msg:
                                message = 'Failed to restore emails from archive file %s, For domain: %s. error message: %s. [ExtractBackup]' % (
                                    self.backupFile, items, str(msg))
                                logging.statusWriter(self.logFile, message, 1)

            command = 'chown -R vmail:vmail /home/vmail'
            ProcessUtilities.normalExecutioner(command)

            message = 'Emails successfully restored'
            logging.statusWriter(self.logFile, message, 1)


            return 1

        except BaseException as msg:
            message = 'Failed to restore emails from archive file %s, error message: %s. [ExtractBackup]' % (
            self.backupFile, str(msg))
            logging.statusWriter(self.logFile, message, 1)
            return 0

    def MainController(self):

        if self.ExtractBackup():
            pass
        else:
            return

        self.LoadDomains()

        if self.CreateMainWebsite():
            pass
        else:
            return 0

        if self.CreateChildDomains():
            pass
        else:
            return 0

        if self.CreateDNSRecords():
            pass
        else:
            return 0

        if self.RestoreDatabases():
            pass
        else:
            return 0

        if self.createCronJobs():
            pass
        else:
            pass

        self.RestoreEmails()
        self.FixPermissions()

        message = 'Backup file %s successfully restored.' % (self.backupFile)
        logging.statusWriter(self.logFile, message, 1)

        return 1


def main():
    LogFile = '/home/cyberpanel/%s' % (str(randint(1000, 9999)))
    message = 'Backup logs to be generated in %s' % (LogFile)
    print(message)

    parser = argparse.ArgumentParser(description='CyberPanel cPanel Importer')
    parser.add_argument('--path', help='Path where cPanel .tar.gz files are stored.')

    args = parser.parse_args()

    for items in os.listdir(args.path):
        if items.endswith('.tar.gz'):
            finalPath = '%s/%s' % (args.path.rstrip('/'), items)
            try:
                cI = cPanelImporter(finalPath, LogFile)
                if cI.MainController():
                    pass
                else:
                    pass
            except:
                pass

if __name__ == "__main__":
    main()
