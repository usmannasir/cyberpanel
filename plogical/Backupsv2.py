import argparse
import json
import os
import sys
import time

sys.path.append('/usr/local/CyberCP')
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass

from plogical.processUtilities import ProcessUtilities


class CPBackupsV2:
    PENDING_START = 0
    RUNNING = 1
    COMPLETED = 2
    FAILED = 3

    def __init__(self, data):
        self.data = data
        pass

    @staticmethod
    def FetchCurrentTimeStamp():
        import time
        return str(time.time())

    def UpdateStatus(self, message, status):

        from websiteFunctions.models import Backupsv2, BackupsLogsv2
        self.buv2 = Backupsv2.objects.get(fileName=self.buv2.fileName)
        self.buv2.status = status
        self.buv2.save()

        BackupsLogsv2(message=message, owner=self.buv2).save()

        if status == CPBackupsV2.FAILED:
            self.buv2.website.BackupLock = 0
            self.buv2.website.save()
        elif status == CPBackupsV2.COMPLETED:
            self.buv2.website.BackupLock = 0
            self.buv2.website.save()

    def InitiateBackup(self):

        from websiteFunctions.models import Websites, Backupsv2
        from django.forms.models import model_to_dict
        from plogical.mysqlUtilities import mysqlUtilities
        self.website = Websites.objects.get(domain=self.data['domain'])

        if not os.path.exists(self.data['BasePath']):
            command = f"mkdir -p {self.data['BasePath']}"
            ProcessUtilities.executioner(command)

            command = f"chmod 711 {self.data['BasePath']}"
            ProcessUtilities.executioner(command)

        self.StartingTimeStamp = CPBackupsV2.FetchCurrentTimeStamp()

        while(1):

            if self.website.BackupLock == 0:

                self.website.BackupLock = 1
                self.website.save()

                self.buv2 = Backupsv2(website=self.website, fileName='backup-' + self.data['domain'] + "-" + time.strftime("%m.%d.%Y_%H-%M-%S"), status=CPBackupsV2.RUNNING, BasePath=self.data['BasePath'])
                self.buv2.save()

                self.FinalPath = f"{self.data['BasePath']}/{self.buv2.fileName}"

                command = f"mkdir -p {self.FinalPath}"
                ProcessUtilities.executioner(command)

                #command = f"chown {website.externalApp}:{website.externalApp} {self.FinalPath}"
                #ProcessUtilities.executioner(command)

                command = f'chown cyberpanel:cyberpanel {self.FinalPath}'
                ProcessUtilities.executioner(command)

                command = f"chmod 711 {self.FinalPath}"
                ProcessUtilities.executioner(command, self.website.externalApp)

                try:

                    self.UpdateStatus('Creating backup config,0', CPBackupsV2.RUNNING)

                    Config = {'MainWebsite': model_to_dict(self.website, fields=['domain', 'adminEmail', 'phpSelection', 'state', 'config'])}
                    Config['admin'] = model_to_dict(self.website.admin, fields=['userName', 'password', 'firstName', 'lastName',
                                                                           'email', 'type', 'owner', 'token', 'api', 'securityLevel',
                                                                           'state', 'initself.websitesLimit', 'twoFA', 'secretKey', 'config'])
                    Config['acl'] = model_to_dict(self.website.admin.acl)

                    ### Child domains to config

                    ChildsList = []

                    for childDomains in self.website.childdomains_set.all():
                        print(childDomains.domain)
                        ChildsList.append(model_to_dict(childDomains))

                    Config['ChildDomains'] = ChildsList

                    #print(str(Config))

                    ### Databases

                    connection, cursor = mysqlUtilities.setupConnection()

                    if connection == 0:
                        return 0

                    dataBases = self.website.databases_set.all()
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

                    for wpsite in self.website.wpsites_set.all():
                        WPSitesList.append(model_to_dict(wpsite,fields=['title', 'path', 'FinalURL', 'AutoUpdates', 'PluginUpdates', 'ThemeUpdates', 'WPLockState']))

                    Config['WPSites'] = WPSitesList
                    self.config = Config

                    #command = f"echo '{json.dumps(Config)}' > {self.FinalPath}/config.json"
                    #ProcessUtilities.executioner(command, self.website.externalApp, True)

                    WriteToFile = open(f'{self.FinalPath}/config.json', 'w')
                    WriteToFile.write(json.dumps(Config))
                    WriteToFile.close()

                    command = f"chmod 600 {self.FinalPath}/config.json"
                    ProcessUtilities.executioner(command)

                    self.UpdateStatus('Backup config created,5', CPBackupsV2.RUNNING)
                except BaseException as msg:
                    self.UpdateStatus(f'Failed during config generation, Error: {str(msg)}', CPBackupsV2.FAILED)
                    return 0

                try:

                    if self.data['BackupDatabase']:
                        self.UpdateStatus('Backing up databases..,10', CPBackupsV2.RUNNING)
                        if self.BackupDataBases() == 0:
                            self.UpdateStatus(f'Failed to create backup for databases.', CPBackupsV2.FAILED)
                            return 0

                        self.UpdateStatus('Database backups completed successfully..,25', CPBackupsV2.RUNNING)

                    if self.data['BackupData']:
                        self.UpdateStatus('Backing up website data..,30', CPBackupsV2.RUNNING)
                        if self.BackupData() == 0:
                            return 0
                        self.UpdateStatus('Website data backup completed successfully..,70', CPBackupsV2.RUNNING)

                        ##command = f'/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/Backupsv2.py BackupDataBases --path {self.FinalPath}'
                        ##ProcessUtilities.executioner(command)


                    self.UpdateStatus('Completed', CPBackupsV2.COMPLETED)

                    print(self.FinalPath)

                    break
                except BaseException as msg:
                    self.UpdateStatus(f'Failed after config generation, Error: {str(msg)}', CPBackupsV2.FAILED)
                    return 0

            else:
                time.sleep(5)

    def BackupDataBases(self):

        ### This function will backup databases of the website, also need to take care of database that we need to exclude
        ### excluded databases are in a list self.data['ExcludedDatabases'] only backup databases if backupdatabase check is on
        ## For example if self.data['BackupDatabase'] is one then only run this function otherwise not

        from plogical.mysqlUtilities import mysqlUtilities

        for dbs in self.config['databases']:

            ### Pending: Need to only backup database present in the list of databases that need backing up

            for key, value in dbs.items():
                print(f'DB {key}')

                if mysqlUtilities.createDatabaseBackup(key, self.FinalPath) == 0:
                    self.UpdateStatus(f'Failed to create backup for database {key}.', CPBackupsV2.RUNNING)
                    return 0

                for dbUsers in value:
                    print(f'User: {dbUsers["user"]}, Host: {dbUsers["host"]}, Pass: {dbUsers["password"]}')



        return 1

    def BackupData(self):

        ### This function will backup data of the website, also need to take care of directories that we need to exclude
        ### excluded directories are in a list self.data['ExcludedDirectories'] only backup data if backupdata check is on
        ## For example if self.data['BackupData'] is one then only run this function otherwise not

        destination = f'{self.FinalPath}/data'
        source = f'/home/{self.website.domain}'

        ## Pending add user provided folders in the exclude list

        exclude = f'--exclude=.cache --exclude=.cache --exclude=.cache --exclude=.wp-cli ' \
                  f'--exclude=backup --exclude=incbackup --exclude=incbackup --exclude=logs --exclude=lscache'

        command = f'mkdir -p {destination}'
        ProcessUtilities.executioner(command, 'cyberpanel')

        command = f'chown {self.website.externalApp}:{self.website.externalApp} {destination}'
        ProcessUtilities.executioner(command)

        command = f'rsync -av {exclude}  {source}/ {destination}/'
        ProcessUtilities.executioner(command, self.website.externalApp)

        return 1

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='CyberPanel Backup Generator')
        parser.add_argument('function', help='Specify a function to call!')
        parser.add_argument('--path', help='')

        args = parser.parse_args()

        if args.function == "BackupDataBases":
            cpbuv2 = CPBackupsV2({'finalPath': args.path})
            cpbuv2.BackupDataBases()

    except:
        cpbuv2 = CPBackupsV2({'domain': 'cyberpanel.net', 'BasePath': '/home/backup', 'BackupDatabase': 1, 'BackupData': 1} )
        cpbuv2.InitiateBackup()