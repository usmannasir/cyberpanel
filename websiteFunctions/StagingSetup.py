#!/usr/local/CyberCP/bin/python
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
        try:
            tempStatusPath = self.extraArgs['tempStatusPath']
            self.tempStatusPath = tempStatusPath
            masterDomain = self.extraArgs['masterDomain']
            domain = self.extraArgs['domain']
            admin = self.extraArgs['admin']

            website = Websites.objects.get(domain=masterDomain)

            ## Creating Child Domain

            path = "/home/" + masterDomain + "/public_html/" + domain

            logging.statusWriter(tempStatusPath, 'Creating domain for staging environment..,5')
            phpSelection = 'PHP 7.1'
            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createDomain --masterDomain " + masterDomain + " --virtualHostName " + domain + \
                       " --phpVersion '" + phpSelection + "' --ssl 0 --dkimCheck 0 --openBasedir 0 --path " + path + ' --websiteOwner ' \
                       + admin.userName + ' --tempStatusPath  %s' % (tempStatusPath + '1') + " --apache 0"

            ProcessUtilities.executioner(execPath)

            domainCreationStatusPath = tempStatusPath + '1'

            data = open(domainCreationStatusPath, 'r').read()

            if data.find('[200]') > -1:
                pass
            else:
                logging.statusWriter(tempStatusPath, 'Failed to create child-domain for staging enviroment. [404]')
                return 0

            logging.statusWriter(tempStatusPath, 'Domain successfully created..,15')

            ## Copying Data

            masterPath = '/home/%s/public_html' % (masterDomain)

            command = 'rsync -avzh --exclude "%s" --exclude "wp-content/backups" --exclude "wp-content/updraft" --exclude "wp-content/cache" --exclude "wp-content/plugins/litespeed-cache" %s/ %s' % (
            domain, masterPath, path)
            ProcessUtilities.executioner(command, website.externalApp)

            logging.statusWriter(tempStatusPath, 'Data copied..,50')

            ## Creating Database

            logging.statusWriter(tempStatusPath, 'Creating and copying database..,50')

            dbNameRestore, dbUser, dbPassword = ApplicationInstaller(None, None).dbCreation(tempStatusPath, website)

            # Create dump of existing database

            configPath = '%s/wp-config.php' % (masterPath)

            if not os.path.exists(configPath):
                logging.statusWriter(tempStatusPath, 'WordPress is not detected. [404]')
                return 0

            data = open(configPath, 'r').readlines()

            for items in data:
                if items.find('DB_NAME') > -1:
                    try:
                        dbName = items.split("'")[3]
                        if mysqlUtilities.createDatabaseBackup(dbName, '/home/cyberpanel'):
                            break
                        else:
                            raise BaseException('Failed to create database backup.')
                    except:
                        dbName = items.split('"')[1]
                        if mysqlUtilities.createDatabaseBackup(dbName, '/home/cyberpanel'):
                            break
                        else:
                            raise BaseException('Failed to create database backup.')

            databasePath = '%s/%s.sql' % ('/home/cyberpanel', dbName)

            command = "sed -i 's/%s/%s/g' %s" % (masterDomain, domain, databasePath)
            ProcessUtilities.executioner(command, 'cyberpanel')
            command = "sed -i 's/%s/%s/g' %s" % ('https', 'http', databasePath)
            ProcessUtilities.executioner(command, 'cyberpanel')

            if not mysqlUtilities.restoreDatabaseBackup(dbNameRestore, '/home/cyberpanel', None, 1, dbName):
                try:
                    os.remove(databasePath)
                except:
                    pass
                raise BaseException('Failed to restore database backup.')

            try:
                os.remove(databasePath)
            except:
                pass

            ## Update final config file

            pathFinalConfig = '%s/wp-config.php' % (path)
            data = open(pathFinalConfig, 'r').readlines()

            tmp = "/tmp/" + str(randint(1000, 9999))
            writeToFile = open(tmp, 'w')

            for items in data:
                if items.find('DB_NAME') > -1:
                    writeToFile.write("define( 'DB_NAME', '%s' );\n" % (dbNameRestore))
                elif items.find('DB_USER') > -1:
                    writeToFile.write("define( 'DB_USER', '%s' );\n" % (dbUser))
                elif items.find('DB_PASSWORD') > -1:
                    writeToFile.write("define( 'DB_PASSWORD', '%s' );\n" % (dbPassword))
                elif items.find('WP_SITEURL') > -1:
                    continue
                else:
                    writeToFile.write(items)

            writeToFile.close()

            command = 'mv %s %s' % (tmp, pathFinalConfig)
            ProcessUtilities.executioner(command)

            command = 'chown %s:%s %s' % (website.externalApp, website.externalApp, pathFinalConfig)
            ProcessUtilities.executioner(command)

            logging.statusWriter(tempStatusPath, 'Database synced..,100')

            try:
                os.remove(databasePath)
            except:
                pass

            logging.statusWriter(tempStatusPath, 'Data copied..,[200]')

            return 0
        except BaseException as msg:
            mesg = '%s. [168][404]' % (str(msg))
            logging.statusWriter(self.tempStatusPath, mesg)

    def startSyncing(self):
        try:
            tempStatusPath = self.extraArgs['tempStatusPath']
            childDomain = self.extraArgs['childDomain']
            eraseCheck = self.extraArgs['eraseCheck']
            dbCheck = self.extraArgs['dbCheck']
            copyChanged = self.extraArgs['copyChanged']

            child = ChildDomains.objects.get(domain=childDomain)

            configPath = '%s/wp-config.php' % (child.path)
            if not os.path.exists(configPath):
                logging.statusWriter(tempStatusPath, 'WordPress is not detected. [404]')
                return 0

            if dbCheck:
                logging.statusWriter(tempStatusPath, 'Syncing databases..,10')

                ## Create backup of child-domain database

                configPath = '%s/wp-config.php' % (child.path)

                data = open(configPath, 'r').readlines()

                for items in data:
                    if items.find('DB_NAME') > -1:
                        dbName = items.split("'")[3]
                        if mysqlUtilities.createDatabaseBackup(dbName, '/home/cyberpanel'):
                            break
                        else:
                            raise BaseException('Failed to create database backup.')

                databasePath = '%s/%s.sql' % ('/home/cyberpanel', dbName)
                command = "sed -i 's/%s/%s/g' %s" % (child.domain, child.master.domain, databasePath)
                ProcessUtilities.executioner(command, 'cyberpanel')

                ## Restore to master domain

                masterPath = '/home/%s/public_html' % (child.master.domain)

                configPath = '%s/wp-config.php' % (masterPath)

                data = open(configPath, 'r').readlines()

                for items in data:
                    if items.find('DB_NAME') > -1:
                        dbNameRestore = items.split("'")[3]
                        if not mysqlUtilities.restoreDatabaseBackup(dbNameRestore, '/home/cyberpanel', None, 1, dbName):
                            try:
                                os.remove(databasePath)
                            except:
                                pass
                            raise BaseException('Failed to restore database backup.')

                try:
                    os.remove(databasePath)
                except:
                    pass

            if eraseCheck:
                sourcePath = child.path
                destinationPath = '/home/%s/public_html' % (child.master.domain)

                command = 'rsync -avzh --exclude "wp-config.php" %s/ %s' % (sourcePath, destinationPath)
                ProcessUtilities.executioner(command, child.master.externalApp)
            elif copyChanged:
                sourcePath = child.path
                destinationPath = '/home/%s/public_html' % (child.master.domain)

                command = 'rsync -avzh --exclude "wp-config.php" %s/ %s' % (sourcePath, destinationPath)
                ProcessUtilities.executioner(command, child.master.externalApp)

            logging.statusWriter(tempStatusPath, 'Data copied..,[200]')

            return 0
        except BaseException as msg:
            mesg = '%s. [404]' % (str(msg))
            logging.statusWriter(tempStatusPath, mesg)
