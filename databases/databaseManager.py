#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
from django.shortcuts import redirect

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.http import HttpResponse
import json
from plogical.acl import ACLManager
from plogical.premiumEntitlements import premium_entitlement_required
import plogical.CyberCPLogFileWriter as logging
from plogical.mysqlUtilities import mysqlUtilities
from websiteFunctions.models import Websites
from databases.models import Databases, DBMeta
import argparse
from loginSystem.models import Administrator
import plogical.randomPassword as randomPassword
from plogical.httpProc import httpProc
from backup.models import DBUsers
from plogical.securityUtils import is_safe_sql_identifier
from plogical import databaseAccounts
import re

# MySQL host literal: IPs, hostnames, CIDR and the '%' wildcard are valid, but
# never quotes/spaces/semicolons that could break out of the '...'@'host' literal.
_MYSQL_HOST_RE = re.compile(r"[A-Za-z0-9_.:%/-]{1,255}")


def website_database_prefix(domain):
    """The start of the names of a website's databases and database users.

    The same rule as getTruncatedWebName on the create-database page
    (databases.js), which shows the prefix before the request is sent.
    """
    name = str(domain).replace('-', '').split('.')[0]
    if len(name) > 5:
        name = name[:4]
    return name

class DatabaseManager:

    REMOTE_ACCESS = 'remote_access'

    def loadDatabaseHome(self, request = None, userID = None):
        template = 'databases/index.html'
        proc = httpProc(request, template, None, 'createDatabase')
        return proc.render()

    def phpMyAdmin(self, request = None, userID = None):
        template = 'databases/phpMyAdmin.html'
        proc = httpProc(request, template, None, 'createDatabase')
        return proc.render()

    def createDatabase(self, request = None, userID = None):
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        template = 'databases/createDatabase.html'
        proc = httpProc(request, template, {'websitesList': websitesName}, 'createDatabase')
        return proc.render()

    def submitDBCreation(self, userID = None, data = None, rAPI = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            if ACLManager.currentContextPermission(currentACL, 'createDatabase') == 0:
                return ACLManager.loadErrorJson('createDBStatus', 0)

            databaseWebsite = data['databaseWebsite']
            dbName = data['dbName']
            dbUsername = data['dbUsername']
            dbPassword = data['dbPassword']

            if ACLManager.checkOwnership(databaseWebsite, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if rAPI == None:
                # The prefix comes from the website. A prefix sent by the browser is not used.
                prefix = website_database_prefix(databaseWebsite)
                if not is_safe_sql_identifier(prefix) or not prefix[0].isalnum():
                    data_ret = {'status': 0, 'createDBStatus': 0,
                                'error_message': 'A database name cannot be derived from this website name.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                dbName = prefix + "_" + dbName
                dbUsername = prefix + "_" + dbUsername

            if not is_safe_sql_identifier(dbName) or not is_safe_sql_identifier(dbUsername):
                data_ret = {'status': 0, 'createDBStatus': 0,
                            'error_message': 'Database name and username may only contain letters, numbers, and underscores.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if not isinstance(dbPassword, str) or not dbPassword:
                data_ret = {'status': 0, 'createDBStatus': 0,
                            'error_message': 'A database password is required.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            result = mysqlUtilities.submitDBCreation(dbName, dbUsername, dbPassword, databaseWebsite)

            if result[0] == 1:
                data_ret = {'status': 1, 'createDBStatus': 1, 'error_message': "None", 
                           'dbName': dbName, 'dbUsername': dbUsername}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'createDBStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'createDBStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteDatabase(self, request = None, userID = None):
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        template = 'databases/deleteDatabase.html'
        proc = httpProc(request, template, {'websitesList': websitesName}, 'deleteDatabase')
        return proc.render()

    @premium_entitlement_required('Filemanager', label='MySQL Manager',
                                  page_redirect='https://cyberpanel.net/cyberpanel-addons')
    def MySQLManager(self, request=None, userID=None):
        proc = httpProc(request, 'databases/mysqlmanager.html', None, 'admin')
        return proc.render()
    @premium_entitlement_required('Filemanager', label='MySQL Manager',
                                  page_redirect='https://cyberpanel.net/cyberpanel-addons')
    def OptimizeMySQL(self, request = None, userID = None):
        from cloudAPI.cloudManager import CloudManager
        cm = CloudManager()
        result = cm.fetchRam(request)

        data1 = json.loads(result.content)

        data = {}
        data['ramInGB'] = data1.get('ramInGB')
        data['conf'] = data1.get('conf')

        template = 'databases/OptimizeMySQL.html'
        proc = httpProc(request, template, data, 'admin')
        return proc.render()

    @premium_entitlement_required('Filemanager', label='MySQL Manager',
                                  page_redirect='https://cyberpanel.net/cyberpanel-addons')
    def Upgardemysql(self, request = None, userID = None):
        data={}
        data['mysqlversions']=['10.6','10.11']
        template = 'databases/Updatemysql.html'
        proc = httpProc(request, template, data, 'admin')
        return proc.render()


    def fetchDatabases(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteDatabase') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            databaseWebsite = data['databaseWebsite']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(databaseWebsite, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            website = Websites.objects.get(domain=databaseWebsite)
            databases = Databases.objects.filter(website=website)

            json_data = "["
            checker = 0

            for items in databases:
                dic = {'id': items.pk,
                       'dbName': items.dbName,
                       'dbUser': items.dbUser, }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})

            return HttpResponse(final_json)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(msg)})
            return HttpResponse(final_json)

    def submitDatabaseDeletion(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteDatabase') == 0:
                return ACLManager.loadErrorJson('deleteStatus', 0)

            dbName = data['dbName']
            if not is_safe_sql_identifier(dbName):
                data_ret = {'status': 0, 'deleteStatus': 0,
                            'error_message': 'Invalid database name.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            db = Databases.objects.get(dbName=dbName)

            if ACLManager.checkOwnership(db.website.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            # The database server tells names apart by case; the registration is the name to act on.
            if db.dbName != dbName:
                data_ret = {'status': 0, 'deleteStatus': 0,
                            'error_message': 'Invalid database name.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            result = mysqlUtilities.submitDBDeletion(db.dbName)

            if result[0] == 1:
                data_ret = {'status': 1, 'deleteStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def listDBs(self, request = None, userID = None):
        currentACL = ACLManager.loadedACL(userID)
        AllWebsites = ACLManager.findAllSites(currentACL, userID)
        template = 'databases/listDataBases.html'
        proc = httpProc(request, template, {'AllWebsites': AllWebsites}, 'listDatabases')
        return proc.render()

    @staticmethod
    def ownedDatabaseUser(userName, admin, currentACL):
        """The databases registered with exactly this user, when the caller manages every one of them.

        Returns (databases, None), or (None, reason) where reason is 'unauthorized'
        or a sentence for the customer.
        """
        databases = databaseAccounts.registered_databases(userName)
        if not databases:
            return None, 'unauthorized'
        for database in databases:
            if ACLManager.checkOwnership(database.website.domain, admin, currentACL) != 1:
                return None, 'unauthorized'
        refusal = databaseAccounts.account_refusal(databases[0].dbUser)
        if refusal is not None:
            logging.CyberCPLogFileWriter.writeToFile(
                'Database %s is registered with a user the panel does not act on (%s). '
                'Give the database a user of its own. [databases]' % (databases[0].dbName, refusal))
            return None, ('This database is registered with a user name the panel does not change. '
                          'Ask the administrator to give the database a user of its own.')
        return databases, None

    def changePassword(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listDatabases') == 0:
                return ACLManager.loadErrorJson('changePasswordStatus', 0)

            userName = data['dbUserName']
            dbPassword = data['dbPassword']

            if not is_safe_sql_identifier(userName):
                data_ret = {'status': 0, 'changePasswordStatus': 0,
                            'error_message': 'Invalid database username.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if not isinstance(dbPassword, str) or not dbPassword:
                data_ret = {'status': 0, 'changePasswordStatus': 0,
                            'error_message': 'A database password is required.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            admin = Administrator.objects.get(pk=userID)

            databases, refusal = DatabaseManager.ownedDatabaseUser(userName, admin, currentACL)
            if databases is None:
                if refusal == 'unauthorized':
                    return ACLManager.loadErrorJson()
                data_ret = {'status': 0, 'changePasswordStatus': 0, 'error_message': refusal}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # The registered name, on every host the user has an account at.
            res = mysqlUtilities.changePassword(databases[0].dbUser, dbPassword)

            if res == 0:
                data_ret = {'status': 0, 'changePasswordStatus': 0,'error_message': "Please see CyberPanel main log file."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'status': 1, 'changePasswordStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'changePasswordStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def remoteAccess(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listDatabases') == 0:
                return ACLManager.loadErrorJson('changePasswordStatus', 0)

            userName = data['dbUserName']

            admin = Administrator.objects.get(pk=userID)

            databases = databaseAccounts.registered_databases(userName)
            if not databases:
                return ACLManager.loadErrorJson()
            for database in databases:
                if ACLManager.checkOwnership(database.website.domain, admin, currentACL) != 1:
                    return ACLManager.loadErrorJson()

            try:
                meta = DBMeta.objects.get(database=databases[0], key=DatabaseManager.REMOTE_ACCESS)
                data_ret = {'status': 1, 'dbHost': json.loads(meta.value)['remoteIP']}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            except BaseException as msg:
                data_ret = {'status': 1, 'dbHost': 'localhost'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0,'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def allowRemoteIP(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listDatabases') == 0:
                return ACLManager.loadErrorJson('changePasswordStatus', 0)

            userName = data['dbUserName']
            remoteIP = data['remoteIP']

            if (not is_safe_sql_identifier(userName) or not isinstance(remoteIP, str)
                    or not _MYSQL_HOST_RE.fullmatch(remoteIP)):
                return ACLManager.loadErrorJson('changePasswordStatus', 0)

            admin = Administrator.objects.get(pk=userID)

            databases, refusal = DatabaseManager.ownedDatabaseUser(userName, admin, currentACL)
            if databases is None:
                if refusal == 'unauthorized':
                    return ACLManager.loadErrorJson()
                data_ret = {'status': 0, 'error_message': refusal}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            db = databases[0]
            # The server keeps host names in lower case.
            remoteIP = remoteIP.lower()

            try:
                meta = DBMeta.objects.get(database=db, key=DatabaseManager.REMOTE_ACCESS)
                previousIP = json.loads(meta.value)['remoteIP']
            except:
                meta = None
                previousIP = None

            # The user's accounts as the server has them, with the stored password of each.
            passwords = {}
            for account in DBUsers.objects.filter(user=db.dbUser):
                if account.user == db.dbUser:
                    passwords[account.host] = account.password

            mysqlUtilities.allowRemoteAccess(db.dbName, db.dbUser, remoteIP)
            opened, reason = databaseAccounts.open_remote_access(
                mysqlUtilities, passwords, db.dbName, db.dbUser, remoteIP, previousIP)
            if opened != 1:
                data_ret = {'status': 0, 'error_message': reason}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            metaData = {'remoteIP': remoteIP}

            if meta is not None:
                meta.value = json.dumps(metaData)
                meta.save()
            else:
                DBMeta(database=db, value = json.dumps(metaData), key=DatabaseManager.REMOTE_ACCESS).save()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0,'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    @staticmethod
    def generatePHPMYAdminData(userID):
        try:

            admin = Administrator.objects.get(id=userID)
            path = '/etc/cyberpanel/' + admin.userName


            currentACL = ACLManager.loadedACL(userID)
            websiteOBJs = ACLManager.findWebsiteObjects(currentACL, userID)
            finalUserPassword = randomPassword.generate_pass()

            writeToFile = open(path, 'w')
            writeToFile.write(finalUserPassword)
            writeToFile.close()

            mysqlUtilities.createDBUser(admin.userName, finalUserPassword)
            mysqlUtilities.changePassword(admin.userName, finalUserPassword)

            for webs in websiteOBJs:
                for db in webs.databases_set.all():
                    mysqlUtilities.allowGlobalUserAccess(admin.userName, db.dbName)

            print("1," + finalUserPassword)

        except BaseException as msg:
            print("0," + str(msg))



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument('--userID', help='Logged in user ID')


    args = parser.parse_args()

    if args.function == "generatePHPMYAdminData":
        DatabaseManager.generatePHPMYAdminData(int(args.userID))


if __name__ == "__main__":
    main()
