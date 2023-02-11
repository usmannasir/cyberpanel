import json
import os
import sys

sys.path.append('/usr/local/CyberCP')
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass


class CPBackupsV2:
    def __init__(self, data):
        self.data = data
        pass

    def InitiateBackup(self):

        from websiteFunctions.models import Websites, ChildDomains, WPSites, WPStaging
        from django.forms.models import model_to_dict
        from plogical.mysqlUtilities import mysqlUtilities
        website = Websites.objects.get(domain=self.data['domain'])


        Config = {'MainWebsite': model_to_dict(website, fields=['domain', 'adminEmail', 'phpSelection', 'state', 'config'])}
        Config['admin'] = model_to_dict(website.admin, fields=['userName', 'password', 'firstName', 'lastName',
                                                               'email', 'type', 'owner', 'token', 'api', 'securityLevel',
                                                               'state', 'initWebsitesLimit', 'twoFA', 'secretKey', 'config'])
        Config['acl'] = model_to_dict(website.admin.acl)

        ### Child domains to config

        ChildsList = []

        for childDomains in website.childdomains_set.all():
            print(childDomains.domain)
            ChildsList.append(model_to_dict(childDomains))

        Config['ChildDomains'] = ChildsList

        #print(str(Config))

        ### Databases

        connection, cursor = mysqlUtilities.setupConnection()

        if connection == 0:
            return 0

        dataBases = website.databases_set.all()
        DBSList = []

        for db in dataBases:

            query = f"SELECT host,user FROM mysql.db WHERE db='{db.dbName}';"
            cursor.execute(query)
            DBUsers = cursor.fetchall()

            UserList = []

            for databaseUser in DBUsers:
                query = f"SELECT password FROM `mysql`.`user` WHERE `Host`='{databaseUser[0]}' AND `User`='{databaseUser[1]}';"
                cursor.execute(query)
                resp = cursor.fetchall()
                print(resp)
                UserList.append({'user': databaseUser[1], 'host': databaseUser[0], 'password': resp[0][0]})

            DBSList.append({db.dbName: UserList})

        Config['databases'] = DBSList

        WPSitesList = []

        for wpsite in website.wpsites_set.all():
            WPSitesList.append(model_to_dict(wpsite,fields=['title', 'path', 'FinalURL', 'AutoUpdates', 'PluginUpdates', 'ThemeUpdates', 'WPLockState']))

        Config['WPSites'] = WPSitesList

        print(json.dumps(Config))

        pass

    def BackupData(self):

        ### This function will backup databases of the website, also need to take care of database that we need to exclude
        ### excluded databases are in a list self.data['ExcludedDatabases'] only backup databases if backupdatabase check is on
        ## For example if self.data['BackupDatabase'] is one then only run this function otherwise not

        pass

    def BackupDataBases(self):
        ### This function will backup data of the website, also need to take care of directories that we need to exclude
        ### excluded directories are in a list self.data['ExcludedDirectories'] only backup data if backupdata check is on
        ## For example if self.data['BackupData'] is one then only run this function otherwise not

        pass

if __name__ == "__main__":
    cpbuv2 = CPBackupsV2({'domain': 'cyberpanel.net'} )
    cpbuv2.InitiateBackup()