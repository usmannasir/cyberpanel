import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import pexpect
import CyberCPLogFileWriter as logging
import subprocess
import shlex
from shutil import make_archive,rmtree
import mysqlUtilities
import tarfile
from multiprocessing import Process
import signal
from installUtilities import installUtilities
import argparse
from virtualHostUtilities import virtualHostUtilities
from sslUtilities import sslUtilities
from websiteFunctions.models import Websites, ChildDomains, Backups
from databases.models import Databases
from loginSystem.models import Administrator
from dnsUtilities import DNS
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom
from backup.models import DBUsers
from mailServer.models import Domains as eDomains
import time
from plogical.mailUtilities import mailUtilities
from shutil import copy

## I am not the monster that you think I am..

class backupUtilities:

    completeKeyPath  = "/home/cyberpanel/.ssh"
    destinationsPath = "/home/cyberpanel/destinations"
    licenseKey = '/usr/local/lsws/conf/license.key'

    @staticmethod
    def prepareBackupMeta(backupDomain, backupName, tempStoragePath, backupPath):
        try:
            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018 -- tempStoragePath
            ## /home/example.com/backup - backupPath

            if not os.path.exists(backupPath):
                os.mkdir(backupPath)

            if not os.path.exists(tempStoragePath):
                os.mkdir(tempStoragePath)

            website = Websites.objects.get(domain=backupDomain)

            ######### Generating meta

            ## XML Generation

            metaFileXML = Element('metaFile')

            child = SubElement(metaFileXML, 'masterDomain')
            child.text = backupDomain

            child = SubElement(metaFileXML, 'phpSelection')
            child.text = website.phpSelection

            child = SubElement(metaFileXML, 'externalApp')
            child.text = website.externalApp

            childDomains = website.childdomains_set.all()

            databases = website.databases_set.all()

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
                dbuser = DBUsers.objects.get(user=items.dbUser)

                databaseXML = Element('database')

                child = SubElement(databaseXML, 'dbName')
                child.text = items.dbName
                child = SubElement(databaseXML, 'dbUser')
                child.text = items.dbUser
                child = SubElement(databaseXML, 'password')
                child.text = dbuser.password

                databasesXML.append(databaseXML)

            metaFileXML.append(databasesXML)

            ## Get Aliases

            aliasesXML = Element('Aliases')

            aliases = backupUtilities.getAliases(backupDomain)

            for items in aliases:
                child = SubElement(aliasesXML, 'alias')
                child.text = items

            metaFileXML.append(aliasesXML)

            ## Finish Alias

            ## DNS Records XML

            try:

                dnsRecordsXML = Element("dnsrecords")
                dnsRecords = DNS.getDNSRecords(backupDomain)

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

            except:
                pass

            ## Email accounts XML

            try:
                emailRecordsXML = Element('emails')
                eDomain = eDomains.objects.get(domain=backupDomain)
                emailAccounts = eDomain.eusers_set.all()

                for items in emailAccounts:
                    emailRecordXML = Element('emailAccount')

                    child = SubElement(emailRecordXML, 'email')
                    child.text = items.email
                    child = SubElement(emailRecordXML, 'password')
                    child.text = items.password

                    emailRecordsXML.append(emailRecordXML)

                metaFileXML.append(emailRecordsXML)

            except:
                pass

            ## Email meta generated!


            def prettify(elem):
                """Return a pretty-printed XML string for the Element.
                """
                rough_string = ElementTree.tostring(elem, 'utf-8')
                reparsed = minidom.parseString(rough_string)
                return reparsed.toprettyxml(indent="  ")

            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018/meta.xml -- metaPath
            metaPath = os.path.join(tempStoragePath, "meta.xml")

            xmlpretty = prettify(metaFileXML).encode('ascii', 'ignore')
            metaFile = open(metaPath, 'w')
            metaFile.write(xmlpretty)
            metaFile.close()

            ## meta generated


            newBackup = Backups(website=website, fileName=backupName, date=time.strftime("%I-%M-%S-%a-%b-%Y"),
                                size=0, status=0)
            newBackup.save()

            return 1,'None'


        except BaseException, msg:
            return 0,str(msg)

    @staticmethod
    def startBackup(tempStoragePath, backupName, backupPath):
        try:

            ##### Writing the name of backup file.

            ## /home/example.com/backup/backupFileName

            backupFileNamePath = os.path.join(backupPath,"backupFileName")
            logging.CyberCPLogFileWriter.statusWriter(backupFileNamePath, backupName)

            #####

            status = os.path.join(backupPath,'status')

            logging.CyberCPLogFileWriter.statusWriter(status, "Making archive of home directory.\n")

            ##### Parsing XML Meta file!

            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018 -- tempStoragePath
            backupMetaData = ElementTree.parse(os.path.join(tempStoragePath,'meta.xml'))

            ##### Making archive of home directory

            domainName = backupMetaData.find('masterDomain').text

            ## Saving original vhost conf file

            completPathToConf = virtualHostUtilities.Server_root + '/conf/vhosts/' + domainName + '/vhost.conf'

            if os.path.exists(backupUtilities.licenseKey):
                copy(completPathToConf, tempStoragePath + '/vhost.conf')

            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018 -- tempStoragePath
            ## shutil.make_archive

            make_archive(os.path.join(tempStoragePath,"public_html"), 'gztar', os.path.join("/home",domainName,"public_html"))

            ##### Saving SSL Certificates if any

            sslStoragePath = '/etc/letsencrypt/live/' + domainName

            if os.path.exists(sslStoragePath):
                try:
                    copy(os.path.join(sslStoragePath, "cert.pem"), os.path.join(tempStoragePath, domainName + ".cert.pem"))
                    copy(os.path.join(sslStoragePath, "fullchain.pem"), os.path.join(tempStoragePath, domainName + ".fullchain.pem"))
                    copy(os.path.join(sslStoragePath, "privkey.pem"), os.path.join(tempStoragePath, domainName + ".privkey.pem"))
                except:
                    pass

            ## backup email accounts

            logging.CyberCPLogFileWriter.statusWriter(status, "Backing up email accounts!\n")

            try:
                make_archive(os.path.join(tempStoragePath,domainName),'gztar',os.path.join("/home","vmail",domainName))
            except:
                pass

            ## Backing up databases
            databases = backupMetaData.findall('Databases/database')

            for database in databases:

                dbName = database.find('dbName').text

                logging.CyberCPLogFileWriter.statusWriter(status, "Backing up database: " + dbName)

                if mysqlUtilities.mysqlUtilities.createDatabaseBackup(dbName, tempStoragePath) == 0:
                    raise BaseException


            ## Child Domains SSL.


            childDomains = backupMetaData.findall('ChildDomains/domain')

            try:
                for childDomain in childDomains:

                    actualChildDomain = childDomain.find('domain').text

                    if os.path.exists(backupUtilities.licenseKey):
                        completPathToConf = virtualHostUtilities.Server_root + '/conf/vhosts/' + actualChildDomain + '/vhost.conf'
                        copy(completPathToConf, tempStoragePath + '/' + actualChildDomain + '.vhost.conf')

                        ### Storing SSL for child domainsa

                    sslStoragePath = '/etc/letsencrypt/live/' + actualChildDomain

                    if os.path.exists(sslStoragePath):
                        try:
                            copy(os.path.join(sslStoragePath, "cert.pem"),
                                 os.path.join(tempStoragePath, actualChildDomain + ".cert.pem"))
                            copy(os.path.join(sslStoragePath, "fullchain.pem"),
                                 os.path.join(tempStoragePath, actualChildDomain + ".fullchain.pem"))
                            copy(os.path.join(sslStoragePath, "privkey.pem"),
                                 os.path.join(tempStoragePath, actualChildDomain + ".privkey.pem"))
                            make_archive(os.path.join(tempStoragePath, "sslData-" + domainName), 'gztar',
                                         sslStoragePath)
                        except:
                            pass

            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

            ##### Saving SSL Certificates if any

            ## shutil.make_archive. Creating final package.

            make_archive(os.path.join(backupPath,backupName), 'gztar', tempStoragePath)
            rmtree(tempStoragePath)

            logging.CyberCPLogFileWriter.statusWriter(status, "Completed\n")

        except BaseException,msg:
            try:
                os.remove(os.path.join(backupPath,backupName+".tar.gz"))
            except:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

            try:
                rmtree(tempStoragePath)
            except:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

            status = os.path.join(backupPath,'status'), "w"
            logging.CyberCPLogFileWriter.statusWriter(status, "Aborted, "+ str(msg) + ". [5009]")
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

    @staticmethod
    def initiateBackup(tempStoragePath,backupName,backupPath):
        try:
            p = Process(target=backupUtilities.startBackup, args=(tempStoragePath,backupName,backupPath,))
            p.start()
            pid = open(backupPath + 'pid', "w")
            pid.write(str(p.pid))
            pid.close()
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateBackup]")

    @staticmethod
    def createWebsiteFromBackup(backupFileOrig, dir):
        try:
            backupFile = backupFileOrig.strip(".tar.gz")
            originalFile = "/home/backup/" + backupFileOrig

            if os.path.exists(backupFileOrig):
                path = backupFile
            elif not os.path.exists(originalFile):
                dir = dir
                path = "/home/backup/transfer-" + str(dir) + "/" + backupFile
            else:
                path = "/home/backup/" + backupFile

            admin = Administrator.objects.get(pk=1)

            ## open meta file to read data

            ## Parsing XML Meta file!

            backupMetaData = ElementTree.parse(os.path.join(path, 'meta.xml'))

            domain = backupMetaData.find('masterDomain').text
            phpSelection = backupMetaData.find('phpSelection').text
            externalApp = backupMetaData.find('externalApp').text

            ## Pre-creation checks

            if Websites.objects.filter(domain=domain).count() > 0:
                raise BaseException('This website already exists.')


            if ChildDomains.objects.filter(domain=domain).count() > 0:
                raise BaseException("This website already exists as child domain.")


            ####### Pre-creation checks ends


            ## Create Configurations

            result = virtualHostUtilities.createVirtualHost(domain, admin.email, phpSelection, externalApp, 0, 1, 0,
                                                            admin.userName, 'Default')

            if result[0] == 0:
                raise BaseException(result[1])

            ## Create Configurations ends here

            ## Create databases

            databases = backupMetaData.findall('Databases/database')
            website = Websites.objects.get(domain=domain)

            for database in databases:
                dbName = database.find('dbName').text
                dbUser = database.find('dbUser').text

                if mysqlUtilities.mysqlUtilities.createDatabase(dbName, dbUser, "cyberpanel") == 0:
                    raise BaseException("Failed to create Databases!")

                newDB = Databases(website=website, dbName=dbName, dbUser=dbUser)
                newDB.save()

            ## Create dns zone

            dnsrecords = backupMetaData.findall('dnsrecords/dnsrecord')

            DNS.createDNSZone(domain, admin)

            zone = DNS.getZoneObject(domain)

            for dnsrecord in dnsrecords:

                recordType = dnsrecord.find('type').text
                value = dnsrecord.find('name').text
                content = dnsrecord.find('content').text
                prio = int(dnsrecord.find('priority').text)

                DNS.createDNSRecord(zone, value, recordType, content, prio, 3600)


            return 1,'None'

        except BaseException, msg:
            return 0, str(msg)

    @staticmethod
    def startRestore(backupName, dir):
        try:

            if dir == "CyberPanelRestore":
                backupFileName = backupName.strip(".tar.gz")
                completPath = os.path.join("/home","backup",backupFileName) ## without extension
                originalFile = os.path.join("/home","backup",backupName) ## with extension
            elif dir == 'CLI':
                completPath = backupName.strip(".tar.gz")  ## without extension
                originalFile = backupName  ## with extension
            else:
                backupFileName = backupName.strip(".tar.gz")
                completPath = "/home/backup/transfer-"+str(dir)+"/"+backupFileName ## without extension
                originalFile = "/home/backup/transfer-"+str(dir)+"/"+backupName ## with extension



            pathToCompressedHome = os.path.join(completPath,"public_html.tar.gz")

            if not os.path.exists(completPath):
                os.mkdir(completPath)

            ## Writing pid of restore process

            pid = os.path.join(completPath,'pid')

            logging.CyberCPLogFileWriter.statusWriter(pid, str(os.getpid()))

            status = os.path.join(completPath,'status')
            logging.CyberCPLogFileWriter.statusWriter(status, "Extracting Main Archive!")

            ## Converting /home/backup/backup-example-06-50-03-Thu-Feb-2018.tar.gz -> /home/backup/backup-example-06-50-03-Thu-Feb-2018

            tar = tarfile.open(originalFile)
            tar.extractall(completPath)
            tar.close()


            logging.CyberCPLogFileWriter.statusWriter(status, "Creating Accounts,Databases and DNS records!")

            ########### Creating website and its dabases

            ## extracting master domain for later use
            backupMetaData = ElementTree.parse(os.path.join(completPath, "meta.xml"))
            masterDomain = backupMetaData.find('masterDomain').text

            result = backupUtilities.createWebsiteFromBackup(backupName, dir)

            if result[0] == 1:
                ## Let us try to restore SSL.

                sslStoragePath = completPath + "/" + masterDomain + ".cert.pem"

                if os.path.exists(sslStoragePath):
                    sslHome = '/etc/letsencrypt/live/' + masterDomain

                    try:
                        if not os.path.exists(sslHome):
                            os.mkdir(sslHome)

                        copy(completPath + "/" + masterDomain + ".cert.pem", sslHome + "/cert.pem")
                        copy(completPath + "/" + masterDomain + ".privkey.pem", sslHome + "/privkey.pem")
                        copy(completPath + "/" + masterDomain + ".fullchain.pem", sslHome + "/fullchain.pem")

                        sslUtilities.installSSLForDomain(masterDomain)
                    except:
                        pass

            else:
                logging.CyberCPLogFileWriter.statusWriter(status, "Error Message: " + result[1] + ". Not able to create Account, Databases and DNS Records, aborting. [5009]")
                return 0

            ########### Creating child/sub/addon/parked domains

            logging.CyberCPLogFileWriter.statusWriter(status, "Creating Child Domains!")

            ## Reading meta file to create subdomains

            externalApp = backupMetaData.find('externalApp').text
            websiteHome = os.path.join("/home",masterDomain,"public_html")

            ### Restoring Child Domains if any.

            childDomains = backupMetaData.findall('ChildDomains/domain')

            try:
                for childDomain in childDomains:

                    domain = childDomain.find('domain').text
                    phpSelection = childDomain.find('phpSelection').text
                    path = childDomain.find('path').text

                    retValues = virtualHostUtilities.createDomain(masterDomain, domain, phpSelection, path, 0, 0, 0, 'admin')

                    if retValues[0] == 1:
                        if os.path.exists(websiteHome):
                            rmtree(websiteHome)

                        ## Let us try to restore SSL for Child Domains.

                        try:

                            if os.path.exists(backupUtilities.licenseKey):
                                if os.path.exists(completPath + '/' + domain + '.vhost.conf'):
                                    completPathToConf = virtualHostUtilities.Server_root + '/conf/vhosts/' + domain + '/vhost.conf'
                                    copy(completPath + '/' + domain + '.vhost.conf', completPathToConf)

                            sslStoragePath = completPath + "/" + domain + ".cert.pem"

                            if os.path.exists(sslStoragePath):
                                sslHome = '/etc/letsencrypt/live/' + domain

                                try:
                                    if not os.path.exists(sslHome):
                                        os.mkdir(sslHome)

                                    copy(completPath + "/" + domain + ".cert.pem", sslHome + "/cert.pem")
                                    copy(completPath + "/" + domain + ".privkey.pem", sslHome + "/privkey.pem")
                                    copy(completPath + "/" + domain + ".fullchain.pem",
                                         sslHome + "/fullchain.pem")

                                    sslUtilities.installSSLForDomain(domain)
                                except:
                                    pass
                        except:
                            logging.CyberCPLogFileWriter.writeToFile('While restoring backup we had minor issues for rebuilding vhost conf for: ' + domain + '. However this will be auto healed.')

                        continue
                    else:
                        logging.CyberCPLogFileWriter.statusWriter(status, "Error Message: " + retValues[1] + ". Not able to create child domains, aborting. [5009]")
                        return 0
            except BaseException, msg:
                status = open(os.path.join(completPath,'status'), "w")
                status.write("Error Message: " + str(msg) +". Not able to create child domains, aborting. [5009]")
                status.close()
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")
                return 0

            ## Restore Aliases

            logging.CyberCPLogFileWriter.statusWriter(status, "Restoring Domain Aliases!")

            aliases = backupMetaData.findall('Aliases/alias')

            for items in aliases:
                virtualHostUtilities.createAlias(masterDomain, items.text, 0, "", "", "admin")

            ## Restoring email accounts

            logging.CyberCPLogFileWriter.statusWriter(status, "Restoring email accounts!")

            emailAccounts = backupMetaData.findall('emails/emailAccount')

            try:
                for emailAccount in emailAccounts:

                    email = emailAccount.find('email').text
                    username = email.split("@")[0]
                    password = emailAccount.find('password').text

                    result = mailUtilities.createEmailAccount(masterDomain, username, password)
                    if result[0] == 0:
                        raise BaseException(result[1])

            except BaseException, msg:
                logging.CyberCPLogFileWriter.statusWriter(status, "Error Message: " + str(msg) +". Not able to create email accounts, aborting. [5009]")
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")
                return 0

            ## Emails restored

            ## restoring databases

            logging.CyberCPLogFileWriter.statusWriter(status, "Restoring Databases!")

            databases = backupMetaData.findall('Databases/database')

            for database in databases:
                dbName = database.find('dbName').text
                password = database.find('password').text
                if mysqlUtilities.mysqlUtilities.restoreDatabaseBackup(dbName, completPath, password) == 0:
                    raise BaseException

            ## Databases restored

            logging.CyberCPLogFileWriter.statusWriter(status, "Extracting web home data!")

            # /home/backup/backup-example-06-50-03-Thu-Feb-2018/public_html.tar.gz

            tar = tarfile.open(pathToCompressedHome)
            tar.extractall(websiteHome)
            tar.close()

            ## extracting email accounts

            logging.CyberCPLogFileWriter.statusWriter(status, "Extracting email accounts!")

            try:
                pathToCompressedEmails = os.path.join(completPath, masterDomain + ".tar.gz")
                emailHome = os.path.join("/home","vmail",masterDomain)

                tar = tarfile.open(pathToCompressedEmails)
                tar.extractall(emailHome)
                tar.close()

                ## Change permissions

                command = "chmod -r vmail:vmail " + emailHome
                subprocess.call(shlex.split(command))

            except:
                pass

            ## emails extracted

            if os.path.exists(backupUtilities.licenseKey):
                completPathToConf = virtualHostUtilities.Server_root + '/conf/vhosts/' + masterDomain + '/vhost.conf'
                if os.path.exists(completPath + '/vhost.conf'):
                    copy(completPath + '/vhost.conf', completPathToConf)

            logging.CyberCPLogFileWriter.statusWriter(status, "Done")

            installUtilities.reStartLiteSpeed()

            command = "chown -R " + externalApp + ":" + externalApp + " " + websiteHome
            cmd = shlex.split(command)
            subprocess.call(cmd)

        except BaseException, msg:
            status = os.path.join(completPath, 'status')
            logging.CyberCPLogFileWriter.statusWriter(status, str(msg) + " [5009]")
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")

    @staticmethod
    def initiateRestore(backupName,dir):
        try:
            p = Process(target=backupUtilities.startRestore, args=(backupName, dir,))
            p.start()
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateRestore]")

    @staticmethod
    def sendKey(IPAddress, password,port):
        try:

            expectation = []
            expectation.append("password:")
            expectation.append("Password:")
            expectation.append("Permission denied")

            command = "scp -o StrictHostKeyChecking=no -P "+ port +" /root/.ssh/cyberpanel.pub root@" + IPAddress + ":/root/.ssh/authorized_keys"
            setupKeys = pexpect.spawn(command, timeout=3)

            index = setupKeys.expect(expectation)

            ## on first login attempt send password

            if index == 0:
                setupKeys.sendline(password)
                setupKeys.expect("100%")
                setupKeys.wait()
            elif index == 1:
                setupKeys.sendline(password)
                setupKeys.expect("100%")
                setupKeys.wait()
            elif index == 2:
                return [0, 'Please enable password authentication on your remote server.']
            else:
                raise BaseException

            return [1, "None"]

        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return [0, "TIMEOUT [sendKey]"]
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return [0,  "EOF [sendKey]"]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return [0, str(msg) + " [sendKey]"]

    @staticmethod
    def setupSSHKeys(IPAddress, password,port):
        try:
            ## Checking for host verification

            backupUtilities.host_key_verification(IPAddress)

            if backupUtilities.checkIfHostIsUp(IPAddress) == 1:
                pass
            else:
                logging.CyberCPLogFileWriter.writeToFile("Host is Down.")
                #return [0,"Host is Down."]

            expectation = []
            expectation.append("password:")
            expectation.append("Password:")
            expectation.append("Permission denied")

            command = "ssh -o StrictHostKeyChecking=no -p "+ port +" root@"+IPAddress+' "mkdir /root/.ssh || rm -f /root/.ssh/temp && rm -f /root/.ssh/authorized_temp && cp /root/.ssh/authorized_keys /root/.ssh/temp"'
            setupKeys = pexpect.spawn(command, timeout=3)

            index = setupKeys.expect(expectation)

            ## on first login attempt send password

            if index == 0:
                setupKeys.sendline(password)
            elif index == 1:
                setupKeys.sendline(password)
            elif index == 2:
                return [0, 'Please enable password authentication on your remote server.']
            else:
                raise BaseException

            ## if it again give you password, than provided password is wrong

            expectation = []
            expectation.append("please try again.")
            expectation.append("Password:")
            expectation.append(pexpect.EOF)

            index = setupKeys.expect(expectation)

            if index == 0:
                return [0,"Wrong Password!"]
            elif index == 1:
                return [0, "Wrong Password!"]
            elif index == 2:
                setupKeys.wait()

                sendKey = backupUtilities.sendKey(IPAddress, password, port)

                if sendKey[0] == 1:
                    return [1, "None"]
                else:
                    return [0,sendKey[1]]


        except pexpect.TIMEOUT, msg:
            return [0, str(msg) + " [TIMEOUT setupSSHKeys]"]
        except BaseException, msg:
            return [0, str(msg) + " [setupSSHKeys]"]

    @staticmethod
    def checkIfHostIsUp(IPAddress):
        try:
            if subprocess.check_output(['ping', IPAddress, '-c 1']).find("0% packet loss") > -1:
                return 1
            else:
                return 0
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[checkIfHostIsUp]")

    @staticmethod
    def checkConnection(IPAddress):
        try:

            try:
                destinations = backupUtilities.destinationsPath
                data = open(destinations, 'r').readlines()
                port = data[1].strip("\n")
            except:
                port = "22"

            expectation = []
            expectation.append("password:")
            expectation.append("Password:")
            expectation.append("Last login")
            expectation.append(pexpect.EOF)
            expectation.append(pexpect.TIMEOUT)

            checkConn = pexpect.spawn("sudo ssh -i /root/.ssh/cyberpanel -o StrictHostKeyChecking=no -p "+ port+" root@"+IPAddress, timeout=3)
            index = checkConn.expect(expectation)

            if index == 0:
                subprocess.call(['kill', str(checkConn.pid)])
                logging.CyberCPLogFileWriter.writeToFile("Remote Server is not able to authenticate for transfer to initiate, IP Address:" + IPAddress)
                return [0,"Remote Server is not able to authenticate for transfer to initiate."]
            elif index == 1:
                subprocess.call(['kill', str(checkConn.pid)])
                logging.CyberCPLogFileWriter.writeToFile(
                    "Remote Server is not able to authenticate for transfer to initiate, IP Address:" + IPAddress)
                return [0, "Remote Server is not able to authenticate for transfer to initiate."]
            elif index == 2:
                subprocess.call(['kill', str(checkConn.pid)])
                return [1, "None"]
            elif index == 4:
                subprocess.call(['kill', str(checkConn.pid)])
                return [1, "None"]
            else:
                subprocess.call(['kill', str(checkConn.pid)])
                return [1, "None"]

        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile("Timeout "+IPAddress+ " [checkConnection]")
            return [0, "371 Timeout while making connection to this server [checkConnection]"]
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile("EOF "+IPAddress+ "[checkConnection]")
            return [0, "374 Remote Server is not able to authenticate for transfer to initiate. [checkConnection]"]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg)+" " +IPAddress+ " [checkConnection]")
            return [0, "377 Remote Server is not able to authenticate for transfer to initiate. [checkConnection]"]

    @staticmethod
    def verifyHostKey(IPAddress):
        try:
            backupUtilities.host_key_verification(IPAddress)

            password = "hello" ## dumb password, not used anywhere.

            expectation = []

            expectation.append("continue connecting (yes/no)?")
            expectation.append("password:")

            setupSSHKeys = pexpect.spawn("ssh cyberpanel@" + IPAddress, timeout=3)

            index = setupSSHKeys.expect(expectation)

            if index == 0:
                setupSSHKeys.sendline("yes")

                setupSSHKeys.expect("password:")
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("password:")
                expectation.append(pexpect.EOF)


                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]
                elif innerIndex == 1:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]

            elif index == 1:

                setupSSHKeys.expect("password:")
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("password:")
                expectation.append(pexpect.EOF)

                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]
                elif innerIndex == 1:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]


        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile("Timeout [verifyHostKey]")
            return [0,"Timeout [verifyHostKey]"]
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile("EOF [verifyHostKey]")
            return [0,"EOF [verifyHostKey]"]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [verifyHostKey]")
            return [0,str(msg)+" [verifyHostKey]"]

    @staticmethod
    def createBackupDir(IPAddress,port):

        try:
            command = "sudo ssh -o StrictHostKeyChecking=no -p "+ port +" -i /root/.ssh/cyberpanel root@"+IPAddress+" mkdir /home/backup"
            subprocess.call(shlex.split(command))

            command = "sudo ssh -o StrictHostKeyChecking=no -p " + port + " -i /root/.ssh/cyberpanel root@" + IPAddress + ' "cat /root/.ssh/authorized_keys /root/.ssh/temp > /root/.ssh/authorized_temp"'
            subprocess.call(shlex.split(command))

            command = "sudo ssh -o StrictHostKeyChecking=no -p " + port + " -i /root/.ssh/cyberpanel root@" + IPAddress + ' "cat /root/.ssh/authorized_temp > /root/.ssh/authorized_keys"'
            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createBackupDir]")
            return 0

    @staticmethod
    def host_key_verification(IPAddress):
        try:
            command = 'sudo ssh-keygen -R ' + IPAddress
            subprocess.call(shlex.split(command))
            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [host_key_verification]")
            return 0

    @staticmethod
    def getAliases(masterDomain):
        try:
            aliases = []
            master = Websites.objects.get(domain=masterDomain)
            aliasDomains = master.aliasdomains_set.all()

            for items in aliasDomains:
                aliases.append(items.aliasDomain)

            return aliases

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [getAliases]")
            print 0


def submitBackupCreation(tempStoragePath, backupName, backupPath, backupDomain):
    try:
        ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018 -- tempStoragePath
        ## backup-example-06-50-03-Thu-Feb-2018 -- backup name
        ## /home/example.com/backup - backupPath
        ## /home/cyberpanel/1047.xml - metaPath

        status = os.path.join(backupPath, 'status')
        result = backupUtilities.prepareBackupMeta(backupDomain, backupName, tempStoragePath, backupPath)

        if result[0] == 0:
            logging.CyberCPLogFileWriter.writeToFile(result[1] + ' [5009]')
            logging.CyberCPLogFileWriter.statusWriter(status, result[1] + ' [5009]')
            return


        p = Process(target=backupUtilities.startBackup, args=(tempStoragePath, backupName, backupPath,))
        p.start()
        pid = open(os.path.join(backupPath, 'pid'), "w")
        pid.write(str(p.pid))
        pid.close()


    except BaseException, msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [submitBackupCreation]")

def cancelBackupCreation(backupCancellationDomain,fileName):
    try:

        path = "/home/" + backupCancellationDomain + "/backup/pid"

        pid = open(path, "r").readlines()[0]

        try:
            os.kill(int(pid), signal.SIGKILL)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

        backupPath = "/home/" + backupCancellationDomain + "/backup/"

        tempStoragePath = backupPath + fileName

        try:
            os.remove(tempStoragePath + ".tar.gz")
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

        try:
            rmtree(tempStoragePath)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

        status = open(backupPath + 'status', "w")
        status.write("Aborted manually. [5009]")
        status.close()
    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [cancelBackupCreation]")
        print "0,"+str(msg)

def submitRestore(backupFile,dir):
    try:

        p = Process(target=backupUtilities.startRestore, args=(backupFile, dir,))
        p.start()

        print "1,None"

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [cancelBackupCreation]")
        print "0,"+str(msg)

def submitDestinationCreation(ipAddress, password, port):
    setupKeys = backupUtilities.setupSSHKeys(ipAddress, password, port)

    if setupKeys[0] == 1:
        backupUtilities.createBackupDir(ipAddress, port)
        print "1,None"
    else:
        print setupKeys[1]


def getConnectionStatus(ipAddress):
    try:
        checkCon = backupUtilities.checkConnection(ipAddress)

        if checkCon[0] == 1:
            print "1,None"
        else:
            print checkCon[1]

    except BaseException, msg:
        print str(msg)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--tempStoragePath', help='')
    parser.add_argument('--backupName', help='!')
    parser.add_argument('--backupPath', help='')
    parser.add_argument('--backupDomain', help='')
    parser.add_argument('--metaPath', help='')

    ## Destination Creation

    parser.add_argument('--ipAddress', help='')
    parser.add_argument('--password', help='')
    parser.add_argument('--port', help='')

    ## backup cancellation arguments

    parser.add_argument('--backupCancellationDomain', help='')
    parser.add_argument('--fileName', help='')

    ## backup restore arguments

    parser.add_argument('--backupFile', help='')
    parser.add_argument('--dir', help='')




    args = parser.parse_args()

    if args.function == "submitBackupCreation":
        submitBackupCreation(args.tempStoragePath,args.backupName,args.backupPath, args.backupDomain)
    elif args.function == "cancelBackupCreation":
        cancelBackupCreation(args.backupCancellationDomain,args.fileName)
    elif args.function == "submitRestore":
        submitRestore(args.backupFile,args.dir)
    elif args.function == "submitDestinationCreation":
        submitDestinationCreation(args.ipAddress, args.password, args.port)
    elif args.function == "getConnectionStatus":
        getConnectionStatus(args.ipAddress)

if __name__ == "__main__":
    main()