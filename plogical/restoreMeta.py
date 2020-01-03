#!/usr/local/CyberCP/bin/python
import os.path
import sys
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
import django
django.setup()

from websiteFunctions.models import Websites
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from xml.etree import ElementTree
import plogical.mysqlUtilities as mysqlUtilities
from databases.models import Databases
import argparse
try:
    from plogical.virtualHostUtilities import virtualHostUtilities
    from plogical.mailUtilities import mailUtilities
except:
    pass

class restoreMeta():

    @staticmethod
    def startRestore(metaPath, statusPath):
        try:

            ## extracting master domain for later use
            backupMetaData = ElementTree.parse(metaPath)
            masterDomain = backupMetaData.find('masterDomain').text

            ########### Creating child/sub/addon/parked domains

            logging.statusWriter(statusPath, "Creating Child Domains!", 1)

            ### Restoring Child Domains if any.

            childDomains = backupMetaData.findall('ChildDomains/domain')

            try:
                for childDomain in childDomains:

                    domain = childDomain.find('domain').text
                    phpSelection = childDomain.find('phpSelection').text
                    path = childDomain.find('path').text

                    virtualHostUtilities.createDomain(masterDomain, domain, phpSelection, path, 0, 0, 0,
                                                                  'admin', 0)
            except BaseException as msg:
                logging.writeToFile(str(msg) + " [startRestore]")
                return 0

            ## Restore Aliases

            logging.statusWriter(statusPath, "Restoring Domain Aliases!", 1)

            aliases = backupMetaData.findall('Aliases/alias')

            for items in aliases:
                virtualHostUtilities.createAlias(masterDomain, items.text, 0, "", "", "admin")

            ## Restoring email accounts

            logging.statusWriter(statusPath, "Restoring email accounts!", 1)

            emailAccounts = backupMetaData.findall('emails/emailAccount')

            try:
                for emailAccount in emailAccounts:

                    email = emailAccount.find('email').text
                    username = email.split("@")[0]
                    password = emailAccount.find('password').text

                    result = mailUtilities.createEmailAccount(masterDomain, username, password)
                    if result[0] == 0:
                        logging.statusWriter(statusPath, 'Email existed, updating password according to last snapshot. %s' % (email))
                        if mailUtilities.changeEmailPassword(email, password, 1)[0] == 0:
                            logging.statusWriter(statusPath,
                                                 'Failed changing password for: %s' % (
                                                     email))
                        else:
                            logging.statusWriter(statusPath,
                                                 'Password changed for: %s' % (
                                                     email))

                    else:
                        logging.statusWriter(statusPath,
                                             'Email created: %s' % (
                                                 email))

            except BaseException as msg:
                logging.writeToFile(str(msg) + " [startRestore]")
                return 0

            ## Emails restored

            ## restoring databases

            logging.statusWriter(statusPath, "Restoring Databases!", 1)

            ## Create databases

            databases = backupMetaData.findall('Databases/database')
            website = Websites.objects.get(domain=masterDomain)

            for database in databases:
                dbName = database.find('dbName').text
                dbUser = database.find('dbUser').text
                dbPassword = database.find('password').text

                try:
                    dbExist = Databases.objects.get(dbName=dbName)
                    logging.statusWriter(statusPath, 'Database exists, changing Database password.. %s' % (dbName))
                    mysqlUtilities.mysqlUtilities.changePassword(dbUser, dbPassword, 1)
                    if mysqlUtilities.mysqlUtilities.changePassword(dbUser, dbPassword, 1) == 0:
                        logging.statusWriter(statusPath, 'Failed changing password for database: %s' % (dbName))
                    else:
                        logging.statusWriter(statusPath, 'Password successfully changed for database: %s.' % (dbName))
                except:
                    logging.statusWriter(statusPath, 'Database did not exist, creating new.. %s' % (dbName))
                    if mysqlUtilities.mysqlUtilities.createDatabase(dbName, dbUser, "cyberpanel") == 0:
                        logging.statusWriter(statusPath, 'Failed the creation of database: %s' % (dbName))
                    else:
                        logging.statusWriter(statusPath, 'Database: %s successfully created.' % (dbName))

                    mysqlUtilities.mysqlUtilities.changePassword(dbUser, dbPassword, 1)
                    if mysqlUtilities.mysqlUtilities.changePassword(dbUser, dbPassword, 1) == 0:
                        logging.statusWriter(statusPath, 'Failed changing password for database: %s' % (dbName))
                    else:
                        logging.statusWriter(statusPath, 'Password successfully changed for database: %s.' % (dbName))


                    try:
                        newDB = Databases(website=website, dbName=dbName, dbUser=dbUser)
                        newDB.save()
                    except:
                        pass


            ## Databases restored

            try:
                os.remove(metaPath)
            except:
                pass

        except BaseException as msg:
            logging.writeToFile(str(msg) + " [startRestore]")

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--metaPath', help='')
    parser.add_argument('--statusFile', help='!')

    ## backup restore arguments

    parser.add_argument('--backupFile', help='')
    parser.add_argument('--dir', help='')


    args = parser.parse_args()

    if args.function == "submitRestore":
        restoreMeta.startRestore(args.metaPath,args.statusFile)

if __name__ == "__main__":
    main()