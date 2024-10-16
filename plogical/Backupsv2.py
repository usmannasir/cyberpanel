import argparse
import json
import os
import sys
import time

import paramiko
import requests
import json
import configparser
from django.http import HttpResponse

sys.path.append('/usr/local/CyberCP')
import django
import plogical.CyberCPLogFileWriter as logging

import plogical.mysqlUtilities as mysqlUtilities

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass

from plogical.processUtilities import ProcessUtilities
from plogical.processUtilities import ProcessUtilities as pu

import threading as multi


class CPBackupsV2(multi.Thread):
    PENDING_START = 0
    RUNNING = 1
    COMPLETED = 2
    FAILED = 3

    ### RCLONE BACKEND TYPES
    SFTP = 1
    LOCAL = 2
    GDrive = 3

    RUSTIC_PATH = '/usr/bin/rustic'
    RCLONE_CONFIG = '/root/.config/rclone/rclone.conf'
    command = 'rclone obscure hosting'

    def __init__(self, data):
        multi.Thread.__init__(self)
        self.data = data
        try:
            self.function = data['function']
        except:
            pass

        statusRes, message = self.InstallRustic()

        ### set self.website as it is needed in many functions
        from websiteFunctions.models import Websites
        self.website = Websites.objects.get(domain=self.data['domain'])

        # Resresh gdive access_token code
        try:
            self.LocalRclonePath = f'/home/{self.website.domain}/.config/rclone'
            self.ConfigFilePath = f'{self.LocalRclonePath}/rclone.conf'

            reponame =  self.data['BackendName']

            try:
                ### refresh token if gdrie
                command = f"rclone config dump"
                token = json.loads(ProcessUtilities.outputExecutioner(command, self.website.externalApp, True).rstrip('\n'))

                refreshToken = json.loads(token[reponame]['token'])['refresh_token']

                logging.CyberCPLogFileWriter.writeToFile(f"Refresh Token: {refreshToken}")

                new_Acess_token = self.refresh_V2Gdive_token(refreshToken)

                command = f"""rclone config update '{reponame}' token '{{"access_token":"{new_Acess_token}","token_type":"Bearer","refresh_token":"{refreshToken}","expiry":"2024-04-08T21:53:00.123456789Z"}}' --non-interactive"""
                result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(result)


            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(f"Token Not upadate inside. Error: {str(msg)}")
                pass

            # command = 'cat %s' % (path)
            # CurrentContent = pu.outputExecutioner(command)


            # if CurrentContent.find(reponame) > -1:
            #     config = configparser.ConfigParser()
            #     config.read_string(CurrentContent)
            #
            #     token_str = config.get(reponame, 'token')
            #     token_dict = json.loads(token_str)
            #     refresh_token = token_dict['refresh_token']
            #
            #     new_Acess_token = self.refresh_V2Gdive_token(refresh_token)
            #
            #     old_access_token = token_dict['access_token']
            #
            #     new_content = CurrentContent.replace(str(old_access_token), new_Acess_token)
            #
            #     command = f"cat /dev/null > {self.ConfigFilePath}"
            #     pu.executioner(command, self.website.externalApp, True)
            #
            #     command = f"echo '{new_content}' >> {self.ConfigFilePath}"
            #     ProcessUtilities.executioner(command, self.website.externalApp, True)
            #
            #     command = f"chmod 600 {self.ConfigFilePath}"
            #     ProcessUtilities.executioner(command, self.website.externalApp)
            # else:
            #     logging.CyberCPLogFileWriter.writeToFile("Token Not upadate..........")
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Error update token............%s"%msg)



        ## Set up the repo name to be used

        if self.data['BackendName'] != 'local':
            self.repo = f"rclone:'{self.data['BackendName']}':{self.data['domain']}"
        else:
            self.repo = f"rclone:'{self.data['BackendName']}':/home/{self.data['domain']}/incrementalbackups"

        ### This will contain list of all snapshots id generated and it will be merged

        self.snapshots = []

        ##

        self.StatusFile = f'/home/cyberpanel/{self.website.domain}_rustic_backup_log'
        self.StatusFile_Restore = f'/home/cyberpanel/{self.website.domain}_rustic_backup_log_Restore'

        ## restore or backup?

        self.restore = 0

        if os.path.exists(self.StatusFile):
            os.remove(self.StatusFile)


        #### i want to keep a merge flag, if not delete all snapshots in case of backup fail

        self.MergeSnapshotFlag = 1

        # ### delete repo function
        # try:
        #     self.repo = data['BackendName']
        # except:
        #     pass

    def run(self):
        try:
            if self.function == 'InitiateBackup':
                self.InitiateBackup()
            elif self.function == 'InitiateRestore':
                self.InitiateRestore()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [CPBackupsV2.run]')

    def FetchSnapShots(self):
        try:
            command = f'rustic -r {self.repo} snapshots --password "" --json 2>/dev/null'
            # SLSkjoSCczb6wxTMCBPmBMGq/UDSpp28-u cyber5986 rustic -r rclone:None:cyberpanel.net snapshots --password "" --json 2>/dev/null
            result = json.loads(
                ProcessUtilities.outputExecutioner(command, self.website.externalApp, True).rstrip('\n'))
            return 1, result
        except BaseException as msg:
            return 0, str(msg)

    def SetupRcloneBackend(self, type, config):
        try:
            self.LocalRclonePath = f'/home/{self.website.domain}/.config/rclone'
            self.ConfigFilePath = f'{self.LocalRclonePath}/rclone.conf'

            command = f'mkdir -p {self.LocalRclonePath}'
            ProcessUtilities.executioner(command, self.website.externalApp)


            if type == CPBackupsV2.SFTP:
                ## config = {"name":, "host":, "user":, "port":, "path":, "password":,}


                ### first check sftp credentails details

                # Connect to the remote server using the private key
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    # Connect to the server using the private key
                    ssh.connect(config["host"], username=config["user"], password=config["password"], port=config["sshPort"])
                    ssh.close()
                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.CyberCPLogFileWriter.writeToFile(f'Successfully connected to {config["host"]} through user {config["user"]}')
                except BaseException as msg:
                    return 0, str(msg)



                command = f'rclone obscure {config["password"]}'
                ObsecurePassword = ProcessUtilities.outputExecutioner(command).rstrip('\n')

                content = f'''
                
[{config["Repo_Name"]}]
type = sftp
host = {config["host"]}
user = {config["user"]}
pass = {ObsecurePassword}
port = {config["sshPort"]}
'''

                command = f"echo '{content}' >> {self.ConfigFilePath}"
                ProcessUtilities.executioner(command, self.website.externalApp, True)

                command = f"chmod 600 {self.ConfigFilePath}"
                ProcessUtilities.executioner(command, self.website.externalApp)
                return 1, None
            elif type == CPBackupsV2.GDrive:
                token = """{"access_token":"%s","token_type":"Bearer","refresh_token":"%s", "expiry":"2024-04-08T21:53:00.123456789Z"}""" % (
                config["token"], config["refresh_token"])

                if config["client_id"] == 'undefined':
                    config["client_id"] = ''
                    config["client_secret"] = ''

                content = f'''
[{config["accountname"]}]
type = drive
scope = drive
client_id={config["client_id"]}
client_secret={config["client_secret"]}
token = {token}
team_drive =
'''
                command = f"echo '{content}' >> {self.ConfigFilePath}"
                ProcessUtilities.executioner(command, self.website.externalApp, True)

                command = f"chmod 600 {self.ConfigFilePath}"
                ProcessUtilities.executioner(command, self.website.externalApp)
                return 1, None
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [Configure.run]')
            return 0, str(msg)

    @staticmethod
    def FetchCurrentTimeStamp():
        import time
        return str(time.time())

    def UpdateStatus(self, message, status):

        if status == CPBackupsV2.FAILED:
            self.website.BackupLock = 0
            self.website.save()
            ### delete leftover dbs if backup fails

            command = f'rm -f {self.FinalPathRuctic}/*.sql'
            ProcessUtilities.executioner(command, None, True)

            file = open(self.StatusFile, 'a')
            file.writelines("[" + time.strftime(
                "%m.%d.%Y_%H-%M-%S") + ":FAILED] " + message + "[404]" + "\n")
            file.close()

            ### if backup failed, we need to prune snapshots as they are not needed.

            snapshots = ''
            for snapshot in self.snapshots:
                snapshots = f'{snapshots} {snapshot}'

            command = f'rustic -r {self.repo} forget {snapshots}  --password ""'
            result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(result)

        elif status == CPBackupsV2.COMPLETED:
            self.website.BackupLock = 0
            self.website.save()
            file = open(self.StatusFile, 'a')
            file.writelines("[" + time.strftime(
                "%m.%d.%Y_%H-%M-%S") + ":COMPLETED] " + message + "[200]" + "\n")
            file.close()
        else:
            file = open(self.StatusFile, 'a')
            file.writelines("[" + time.strftime(
                "%m.%d.%Y_%H-%M-%S") + ":INFO] " + message + "\n")
            file.close()

    ## parent is used to link this snapshot with master snapshot
    def BackupConfig(self):
        ### Backup config file to rustic

        command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}'
        ProcessUtilities.executioner(command)

        command = f'rustic init -r {self.repo} --password ""'
        ProcessUtilities.executioner(command, self.website.externalApp)

        # command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}'
        # ProcessUtilities.executioner(command)

        command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}/config.json'
        ProcessUtilities.executioner(command)

        command = f'rustic -r {self.repo} backup {self.FinalPathRuctic}/config.json --json --password "" 2>/dev/null'
        status, result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True, None, True)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.CyberCPLogFileWriter.writeToFile(f'Status {str(status)}')

        if status:

            result = json.loads(result.rstrip('\n'))

            try:
                SnapShotID = result['id']  ## snapshot id that we need to store in db
                files_new = result['summary']['files_new']  ## basically new files in backup
                total_duration = result['summary']['total_duration']  ## time taken

                self.snapshots.append(SnapShotID)

            except BaseException as msg:
                self.UpdateStatus(f'Backup failed as no snapshot id found, error: {str(msg)}', CPBackupsV2.FAILED)
                return 0

            command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}/config.json'
            ProcessUtilities.executioner(command)

            return 1
        else:
            self.UpdateStatus(f'Backup failed , error: {str(result)}', CPBackupsV2.FAILED)
            return 0

    def MergeSnapshots(self):
        snapshots = ''
        for snapshot in self.snapshots:
            snapshots = f'{snapshots} {snapshot}'

        if self.MergeSnapshotFlag:
            command = f'rustic -r {self.repo} merge {snapshots}  --password "" --json'
            result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(result)

        command = f'rustic -r {self.repo} forget {snapshots}  --password ""'
        result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.CyberCPLogFileWriter.writeToFile(result)

    def InitiateBackup(self):
        logging.CyberCPLogFileWriter.writeToFile("[Create Backup start]")
        from websiteFunctions.models import Websites, Backupsv2
        from django.forms.models import model_to_dict
        from plogical.mysqlUtilities import mysqlUtilities
        self.website = Websites.objects.get(domain=self.data['domain'])

        ## Base path is basically the path set by user where all the backups will be housed

        if not os.path.exists(self.data['BasePath']):
            command = f"mkdir -p {self.data['BasePath']}"
            ProcessUtilities.executioner(command)

            #command = f"chmod 711 {self.data['BasePath']}"
            #ProcessUtilities.executioner(command)

        self.StartingTimeStamp = CPBackupsV2.FetchCurrentTimeStamp()

        ### Init rustic repo in main func so dont need to do again and again

        while (1):

            self.website = Websites.objects.get(domain=self.data['domain'])

            if self.website.BackupLock == 0:

                Disk1 = f"du -sm /home/{self.website.domain}/"
                Disk2 = "2>/dev/null | awk '{print $1}'"

                self.WebsiteDiskUsage = int(
                    ProcessUtilities.outputExecutioner(f"{Disk1} {Disk2}", 'root', True).rstrip('\n'))

                self.CurrentFreeSpaceOnDisk = int(
                    ProcessUtilities.outputExecutioner("df -m / | awk 'NR==2 {print $4}'", 'root', True).rstrip('\n'))

                if self.WebsiteDiskUsage > self.CurrentFreeSpaceOnDisk:
                    self.UpdateStatus(f'Not enough disk space on the server to backup this website.',
                                      CPBackupsV2.FAILED)
                    return 0

                self.UpdateStatus('Checking if backup modules installed,0', CPBackupsV2.RUNNING)

                ### Before doing anything install rustic

                statusRes, message = self.InstallRustic()

                if statusRes == 0:
                    self.UpdateStatus(f'Failed to install Rustic, error: {message}', CPBackupsV2.FAILED)
                    return 0

                # = Backupsv2(website=self.website, fileName='backup-' + self.data['domain'] + "-" + time.strftime("%m.%d.%Y_%H-%M-%S"), status=CPBackupsV2.RUNNING, BasePath=self.data['BasePath'])
                # self.buv2.save()

                # self.FinalPath = f"{self.data['BasePath']}/{self.buv2.fileName}"

                ### Rustic backup final path

                self.FinalPathRuctic = f"{self.data['BasePath']}/{self.website.domain}"

                # command = f"mkdir -p {self.FinalPath}"
                # ProcessUtilities.executioner(command)

                # command = f"chown {website.externalApp}:{website.externalApp} {self.FinalPath}"
                # ProcessUtilities.executioner(command)

                # command = f'chown cyberpanel:cyberpanel {self.FinalPath}'
                # ProcessUtilities.executioner(command)

                # command = f"chmod 711 {self.FinalPath}"
                # ProcessUtilities.executioner(command)

                command = f"mkdir -p {self.FinalPathRuctic}"
                ProcessUtilities.executioner(command)

                command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}'
                ProcessUtilities.executioner(command)

                command = f"chmod 711 {self.FinalPathRuctic}"
                ProcessUtilities.executioner(command)

                try:

                    self.UpdateStatus('Creating backup config,0', CPBackupsV2.RUNNING)

                    Config = {'MainWebsite': model_to_dict(self.website,
                                                           fields=['domain', 'adminEmail', 'phpSelection', 'state',
                                                                   'config'])}
                    Config['admin'] = model_to_dict(self.website.admin,
                                                    fields=['userName', 'password', 'firstName', 'lastName',
                                                            'email', 'type', 'owner', 'token', 'api', 'securityLevel',
                                                            'state', 'initself.websitesLimit', 'twoFA', 'secretKey',
                                                            'config'])
                    Config['acl'] = model_to_dict(self.website.admin.acl)

                    ### Child domains to config

                    ChildsList = []

                    for childDomains in self.website.childdomains_set.all():
                        print(childDomains.domain)
                        ChildsList.append(model_to_dict(childDomains))

                    Config['ChildDomains'] = ChildsList

                    # print(str(Config))

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
                        WPSitesList.append(model_to_dict(wpsite, fields=['title', 'path', 'FinalURL', 'AutoUpdates',
                                                                         'PluginUpdates', 'ThemeUpdates',
                                                                         'WPLockState']))

                    Config['WPSites'] = WPSitesList
                    self.config = Config

                    ### DNS Records

                    try:
                        from dns.models import Domains

                        self.dnsDomain = Domains.objects.get(name=self.website.domain)

                        DNSRecords = []

                        for record in self.dnsDomain.records_set.all():
                            DNSRecords.append(model_to_dict(record))

                        Config['MainDNSDomain'] = model_to_dict(self.dnsDomain)
                        Config['DNSRecords'] = DNSRecords
                    except:
                        pass

                    ### Email accounts

                    try:
                        from mailServer.models import Domains

                        self.emailDomain = Domains.objects.get(domain=self.website.domain)

                        EmailAddrList = []

                        for record in self.emailDomain.eusers_set.all():
                            EmailAddrList.append(model_to_dict(record))

                        Config['MainEmailDomain'] = model_to_dict(self.emailDomain)
                        Config['EmailAddresses'] = EmailAddrList
                    except:
                        pass

                    # command = f"echo '{json.dumps(Config)}' > {self.FinalPath}/config.json"
                    # ProcessUtilities.executioner(command, self.website.externalApp, True)

                    command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}/config.json'
                    ProcessUtilities.executioner(command)

                    WriteToFile = open(f'{self.FinalPathRuctic}/config.json', 'w')
                    WriteToFile.write(json.dumps(Config))
                    WriteToFile.close()

                    command = f"chmod 600 {self.FinalPathRuctic}/config.json"
                    ProcessUtilities.executioner(command)

                    if self.BackupConfig() == 0:
                        return 0

                    self.UpdateStatus('Backup config created,5', CPBackupsV2.RUNNING)
                except BaseException as msg:
                    self.UpdateStatus(f'Failed during config generation, Error: {str(msg)}', CPBackupsV2.FAILED)
                    return 0

                try:
                    if self.data['BackupDatabase']:
                        self.UpdateStatus('Backing up databases..,10', CPBackupsV2.RUNNING)
                        if self.BackupDataBasesRustic() == 0:
                            self.UpdateStatus(f'Failed to create backup for databases.', CPBackupsV2.FAILED)
                            self.MergeSnapshotFlag = 0
                            #return 0
                        else:
                            self.UpdateStatus('Database backups completed successfully..,25', CPBackupsV2.RUNNING)

                    if self.data['BackupData'] and self.MergeSnapshotFlag:
                        self.UpdateStatus('Backing up website data..,30', CPBackupsV2.RUNNING)
                        if self.BackupRustic() == 0:
                            self.UpdateStatus(f'Failed to create backup for data..', CPBackupsV2.FAILED)
                            self.MergeSnapshotFlag = 0
                            # return 0
                        else:
                            self.UpdateStatus('Website data backup completed successfully..,70', CPBackupsV2.RUNNING)

                    if self.data['BackupEmails'] and self.MergeSnapshotFlag:
                        self.UpdateStatus('Backing up emails..,75', CPBackupsV2.RUNNING)
                        if self.BackupEmailsRustic() == 0:
                            self.UpdateStatus(f'Failed to create backup for emails..', CPBackupsV2.FAILED)
                            self.MergeSnapshotFlag = 0
                        else:
                            self.UpdateStatus('Emails backup completed successfully..,85', CPBackupsV2.RUNNING)

                    ### Finally change the backup rustic folder to the website user owner

                    command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}'
                    ProcessUtilities.executioner(command)

                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.CyberCPLogFileWriter.writeToFile(f'Snapshots to be merged {str(self.snapshots)}')

                    self.MergeSnapshots()

                    self.UpdateStatus('Completed', CPBackupsV2.COMPLETED)
                    return 1

                    break
                except BaseException as msg:
                    self.UpdateStatus(f'Failed, Error: {str(msg)}', CPBackupsV2.FAILED)
                    return 0
            else:
                time.sleep(5)

                ### If website lock is there for more then 20 minutes it means old backup is stucked or backup job failed, thus continue backup

                if float(CPBackupsV2.FetchCurrentTimeStamp()) > (float(self.StartingTimeStamp) + 1200):
                    self.website = Websites.objects.get(domain=self.data['domain'])
                    self.website.BackupLock = 0
                    self.website.save()

    def BackupDataBasesRustic(self):

        ### This function will backup databases of the website, also need to take care of database that we need to exclude
        ### excluded databases are in a list self.data['ExcludedDatabases'] only backup databases if backupdatabase check is on
        ## For example if self.data['BackupDatabase'] is one then only run this function otherwise not

        # command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}'
        # ProcessUtilities.executioner(command)

        command = f'rustic init -r {self.repo} --password ""'
        ProcessUtilities.executioner(command, self.website.externalApp)

        command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}'
        ProcessUtilities.executioner(command)

        from plogical.mysqlUtilities import mysqlUtilities

        for dbs in self.config['databases']:

            ### Pending: Need to only backup database present in the list of databases that need backing up

            for key, value in dbs.items():
                print(f'DB {key}')

                CurrentDBPath = f"{self.FinalPathRuctic}/{key}.sql"

                DBResult, SnapID = mysqlUtilities.createDatabaseBackup(key, self.FinalPathRuctic, 1, self.repo,
                                                                       self.website.externalApp)

                if DBResult == 1:
                    self.snapshots.append(SnapID)

                    # command = f'chown {self.website.externalApp}:{self.website.externalApp} {CurrentDBPath}'
                    # ProcessUtilities.executioner(command)

                    ## Now pack config into same thing

                    # command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}/config.json'
                    # ProcessUtilities.executioner(command)

                    # command = f'rustic -r {self.repo} backup {CurrentDBPath} --password "" --json 2>/dev/null'
                    # print(f'db command rustic: {command}')
                    # result = json.loads(
                    #     ProcessUtilities.outputExecutioner(command, self.website.externalApp, True).rstrip('\n'))
                    #
                    # try:
                    #     SnapShotID = result['id']  ## snapshot id that we need to store in db
                    #     files_new = result['summary']['files_new']  ## basically new files in backup
                    #     total_duration = result['summary']['total_duration']  ## time taken
                    #
                    #     self.snapshots.append(SnapShotID)
                    #
                    #     ### Config is saved with each database, snapshot of config is attached to db snapshot with parent
                    #
                    #     #self.BackupConfig(SnapShotID)
                    #
                    #     command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}'
                    #     ProcessUtilities.executioner(command)
                    #
                    # except BaseException as msg:
                    #     self.UpdateStatus(f'Backup failed as no snapshot id found, error: {str(msg)}',
                    #                       CPBackupsV2.FAILED)
                    #     return 0
                    #
                    #
                    # for dbUsers in value:
                    #     print(f'User: {dbUsers["user"]}, Host: {dbUsers["host"]}, Pass: {dbUsers["password"]}')
                    #
                    # command = f'rm -f {CurrentDBPath}'
                    # ProcessUtilities.executioner(command)

                else:
                    command = f'rm -f {CurrentDBPath}'
                    ProcessUtilities.executioner(command)
                    self.UpdateStatus(f'Failed to create backup for database {key}.', CPBackupsV2.FAILED)
                    return 0

        return 1

    def BackupRustic(self):

        ### This function will backup data of the website, also need to take care of directories that we need to exclude
        ### excluded directories are in a list self.data['ExcludedDirectories'] only backup data if backupdata check is on
        ## For example if self.data['BackupData'] is one then only run this function otherwise not

        # command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}'
        # ProcessUtilities.executioner(command)

        command = f'rustic init -r {self.repo} --password ""'
        ProcessUtilities.executioner(command, self.website.externalApp)

        source = f'/home/{self.website.domain}'

        # command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}/config.json'
        # ProcessUtilities.executioner(command)

        ## Pending add user provided folders in the exclude list

        exclude = f' --glob !{source}/logs '

        command = f'rustic -r {self.repo} backup {source} --password "" {exclude} --json 2>/dev/null'
        status, result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True, None, True)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.CyberCPLogFileWriter.writeToFile(f'Status code {status}')

        if status:
            result = json.loads(result.rstrip('\n'))

            try:
                SnapShotID = result['id']  ## snapshot id that we need to store in db
                files_new = result['summary']['files_new']  ## basically new files in backup
                total_duration = result['summary']['total_duration']  ## time taken

                self.snapshots.append(SnapShotID)

                ### Config is saved with each backup, snapshot of config is attached to data snapshot with parent

                # self.BackupConfig(SnapShotID)
            except BaseException as msg:
                self.UpdateStatus(f'Backup failed as no snapshot id found, error: {str(msg)}', CPBackupsV2.FAILED)
                return 0

            # self.UpdateStatus(f'Rustic command result id: {SnapShotID}, files new {files_new}, total_duration {total_duration}', CPBackupsV2.RUNNING)

            return 1
        else:
            self.UpdateStatus(f'Backup failed, error: {str(result)}', CPBackupsV2.FAILED)
            return 0

    def BackupEmailsRustic(self):

        ### This function will backup emails of the website, also need to take care of emails that we need to exclude
        ### excluded emails are in a list self.data['ExcludedEmails'] only backup data if backupemail check is on
        ## For example if self.data['BackupEmails'] is one then only run this function otherwise not

        # command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}'
        # ProcessUtilities.executioner(command)

        command = f'rustic init -r {self.repo} --password ""'
        ProcessUtilities.executioner(command, self.website.externalApp)

        # command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}/config.json'
        # ProcessUtilities.executioner(command)

        source = f'/home/vmail/{self.website.domain}'

        if os.path.exists(source):
            ## Pending add user provided folders in the exclude list

            exclude = f' --exclude-if-present rusticbackup  --exclude-if-present logs '

            command = f'export RCLONE_CONFIG=/home/{self.website.domain}/.config/rclone/rclone.conf && rustic -r {self.repo} backup {source} --password "" {exclude} --json 2>/dev/null'

            result = json.loads(ProcessUtilities.outputExecutioner(command, None, True).rstrip('\n'))

            try:
                SnapShotID = result['id']  ## snapshot id that we need to store in db
                files_new = result['summary']['files_new']  ## basically new files in backup
                total_duration = result['summary']['total_duration']  ## time taken

                self.snapshots.append(SnapShotID)

                ### Config is saved with each email backup, snapshot of config is attached to email snapshot with parent

                # self.BackupConfig(SnapShotID)

            except BaseException as msg:
                self.UpdateStatus(f'Backup failed as no snapshot id found, error: {str(msg)}', CPBackupsV2.FAILED)
                return 0

        return 1

    #### Resote Functions

    def RestoreConfig(self):
        try:

            self.UpdateStatus(f'Restoring config..,10',
                              CPBackupsV2.RUNNING)
            ConfigPath = f'/home/backup/{self.website.domain}/config.json'
            RestoreConfigPath = f'/home/{self.website.domain}/'

            command = f'rustic -r {self.repo} restore {self.data["snapshotid"]}:{ConfigPath} {RestoreConfigPath} --password ""  2>/dev/null'
            result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True)

            ConfigContent = json.loads(ProcessUtilities.outputExecutioner(f'cat {RestoreConfigPath}/config.json').rstrip('\n'))

            ### ACL Creation code

            # ### First check if the acl exists
            # from loginSystem.models import ACL, Administrator
            # from django.http import HttpRequest
            # requestNew = HttpRequest()
            # try:
            #     if os.path.exists(ProcessUtilities.debugPath):
            #         logging.CyberCPLogFileWriter.writeToFile(f'ACL in config: {ConfigContent["acl"]}')
            #     acl = ACL.objects.get(name=ConfigContent['acl']['name'])
            # except:
            #     if os.path.exists(ProcessUtilities.debugPath):
            #         logging.CyberCPLogFileWriter.writeToFile('ACL Already existed.')
            #     requestNew.session['userID'] = Administrator.objects.get(userName='admin').id
            #     from userManagment.views import createACLFunc
            #     dataToPass = ConfigContent['acl']
            #     dataToPass['makeAdmin'] = ConfigContent['acl']['adminStatus']
            #     requestNew._body = json.dumps(dataToPass)
            #
            #     if os.path.exists(ProcessUtilities.debugPath):
            #         logging.CyberCPLogFileWriter.writeToFile(f'Passed content to Create ACL Func: {json.dumps(dataToPass)}')
            #
            #     resp = createACLFunc(requestNew)
            #     if os.path.exists(ProcessUtilities.debugPath):
            #         logging.CyberCPLogFileWriter.writeToFile(f'CreateACLFunc stats: {str(resp.content)}')

            ### Create DNS Records

            try:
                from dns.models import Domains
                zone = Domains.objects.get(name=self.website.domain)
                from plogical.dnsUtilities import DNS

                for record in ConfigContent['DNSRecords']:
                    DNS.createDNSRecord(zone, record['name'], record['type'], record['content'], 0, record['ttl'])
            except BaseException as msg:
                self.UpdateStatus(f'Error in RestoreConfig while restoring dns config. Error: {str(msg)}',
                                      CPBackupsV2.RUNNING)


            ### Create Emails Accounts


            #logging.statusWriter(statusPath, "Restoring email accounts!", 1)

            try:

                from plogical.mailUtilities import mailUtilities
                for emailAccount in ConfigContent['EmailAddresses']:

                    email = emailAccount['email']
                    username = email.split("@")[0]
                    password = emailAccount['password']

                    result = mailUtilities.createEmailAccount(self.website.domain, username, password)
                    if result[0] == 0:
                        # #logging.statusWriter(statusPath,
                        #                      'Email existed, updating password according to last snapshot. %s' % (
                        #                          email))
                        if mailUtilities.changeEmailPassword(email, password, 1)[0] == 0:
                            # logging.statusWriter(statusPath,
                            #                      'Failed changing password for: %s' % (
                            #                          email))
                            pass
                        else:
                            pass
                            # logging.statusWriter(statusPath,
                            #                      'Password changed for: %s' % (
                            #                          email))

                    else:
                        pass
                        # logging.statusWriter(statusPath,
                        #                      'Email created: %s' % (
                        #                          email))
            except BaseException as msg:
                self.UpdateStatus(f'Error in RestoreConfig while restoring email config. Error: {str(msg)}',
                                          CPBackupsV2.RUNNING)


            ### Restoring DBs

            try:

                from databases.models import Databases, DatabasesUsers

                for database in ConfigContent['databases']:

                    dbName = list(database.keys())[0]

                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.CyberCPLogFileWriter.writeToFile(f'Databasename: {dbName}')

                    first = 1

                    databaseUsers = database[dbName]

                    for databaseUser in databaseUsers:

                        dbUser = databaseUser['user']
                        dbHost = databaseUser['host']
                        password = databaseUser['password']

                        if os.path.exists(ProcessUtilities.debugPath):
                            logging.CyberCPLogFileWriter.writeToFile('Database user: %s' % (dbUser))
                            logging.CyberCPLogFileWriter.writeToFile('Database host: %s' % (dbHost))
                            logging.CyberCPLogFileWriter.writeToFile('Database password: %s' % (password))

                        if first:

                            first = 0

                            try:
                                dbExist = Databases.objects.get(dbName=dbName)
                                logging.CyberCPLogFileWriter.writeToFile('Database exists, changing Database password.. %s' % (dbName))

                                if mysqlUtilities.mysqlUtilities.changePassword(dbUser, password, 1, dbHost) == 0:
                                    logging.CyberCPLogFileWriter.writeToFile('Failed changing password for database: %s' % (dbName))
                                else:
                                    logging.CyberCPLogFileWriter.writeToFile('Password successfully changed for database: %s.' % (dbName))

                            except:

                                logging.CyberCPLogFileWriter.writeToFile('Database did not exist, creating new.. %s' % (dbName))

                                if mysqlUtilities.mysqlUtilities.createDatabase(dbName, dbUser, "cyberpanel") == 0:
                                    logging.CyberCPLogFileWriter.writeToFile('Failed the creation of database: %s' % (dbName))
                                else:
                                    logging.CyberCPLogFileWriter.writeToFile('Database: %s successfully created.' % (dbName))

                                mysqlUtilities.mysqlUtilities.changePassword(dbUser, password, 1)

                                if mysqlUtilities.mysqlUtilities.changePassword(dbUser, password, 1) == 0:
                                    logging.CyberCPLogFileWriter.writeToFile('Failed changing password for database: %s' % (dbName))
                                else:
                                    logging.CyberCPLogFileWriter.writeToFile(
                                                         'Password successfully changed for database: %s.' % (dbName))

                                try:
                                    newDB = Databases(website=self.website, dbName=dbName, dbUser=dbUser)
                                    newDB.save()
                                except:
                                    pass

                        ## This function will not create database, only database user is created as third value is 0 for createDB

                        mysqlUtilities.mysqlUtilities.createDatabase(dbName, dbUser, password, 0, dbHost)
                        mysqlUtilities.mysqlUtilities.changePassword(dbUser, password, 1, dbHost)
            except BaseException as msg:
                self.UpdateStatus(f'Error in RestoreConfig while restoring database config. Error: {str(msg)}', CPBackupsV2.RUNNING)

            return 1, None

        except BaseException as msg:
            return 0, str(msg)

    def InitiateRestore(self):

        ### if restore then status file should be restore status file

        self.restore = 1
        # self.StatusFile = self.StatusFile_Restore

        from websiteFunctions.models import Websites
        from plogical.mysqlUtilities import mysqlUtilities
        self.website = Websites.objects.get(domain=self.data['domain'])

        self.UpdateStatus('Started restoring,20', CPBackupsV2.RUNNING)

        ## Base path is basically the path set by user where all the backups will be housed

        if not os.path.exists(self.data['BasePath']):
            command = f"mkdir -p {self.data['BasePath']}"
            ProcessUtilities.executioner(command)

            #command = f"chmod 711 {self.data['BasePath']}"
            #ProcessUtilities.executioner(command)

        self.StartingTimeStamp = CPBackupsV2.FetchCurrentTimeStamp()

        ### Init rustic repo in main func so dont need to do again and again

        while (1):

            self.website = Websites.objects.get(domain=self.data['domain'])

            if self.website.BackupLock == 0:

                Disk1 = f"du -sm /home/{self.website.domain}/"
                Disk2 = "2>/dev/null | awk '{print $1}'"

                self.WebsiteDiskUsage = int(
                    ProcessUtilities.outputExecutioner(f"{Disk1} {Disk2}", 'root', True).rstrip('\n'))

                self.CurrentFreeSpaceOnDisk = int(
                    ProcessUtilities.outputExecutioner("df -m / | awk 'NR==2 {print $4}'", 'root', True).rstrip('\n'))

                if self.WebsiteDiskUsage > self.CurrentFreeSpaceOnDisk:
                    self.UpdateStatus(f'Not enough disk space on the server to restore this website.',
                                      CPBackupsV2.FAILED)
                    return 0

                ### Rustic backup final path

                self.FinalPathRuctic = f"{self.data['BasePath']}/{self.website.domain}"

                command = f"mkdir -p {self.FinalPathRuctic}"
                ProcessUtilities.executioner(command)

                command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}'
                ProcessUtilities.executioner(command)

                command = f"chmod 711 {self.FinalPathRuctic}"
                ProcessUtilities.executioner(command)

                ### Find Restore path first, if path is db, only then restore it to cp

                status, message = self.RestoreConfig()
                if status == 0:
                    self.UpdateStatus(f'Failed to restore config, Error {message}',
                                      CPBackupsV2.FAILED)
                    return 0

                if self.data["path"].find('.sql') > -1:
                    mysqlUtilities.restoreDatabaseBackup(self.data["path"].rstrip('.sql'), None, None, None, None, 1,
                                                         self.repo, self.website.externalApp, self.data["snapshotid"])

                else:

                    if self.data["path"].find('/home/vmail') > -1:
                        externalApp = None
                        InitialCommand = f'export RCLONE_CONFIG=/home/{self.website.domain}/.config/rclone/rclone.conf && '
                    else:
                        externalApp = self.website.externalApp
                        InitialCommand = ''

                    command = f'{InitialCommand}rustic -r {self.repo} restore {self.data["snapshotid"]}:{self.data["path"]} {self.data["path"]} --password ""  2>/dev/null'
                    result = ProcessUtilities.outputExecutioner(command, externalApp, True)

                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.CyberCPLogFileWriter.writeToFile(result)

                self.UpdateStatus('Completed', CPBackupsV2.COMPLETED)

                return 1


            else:
                time.sleep(5)

                ### If website lock is there for more then 20 minutes it means old backup is stucked or backup job failed, thus continue backup

                if float(CPBackupsV2.FetchCurrentTimeStamp()) > (float(self.StartingTimeStamp) + 1200):
                    self.website = Websites.objects.get(domain=self.data['domain'])
                    self.website.BackupLock = 0
                    self.website.save()

    ### Delete Snapshots

    def DeleteSnapshots(self, deleteString):

        ### if restore then status file should be restore status file

        from websiteFunctions.models import Websites
        self.website = Websites.objects.get(domain=self.data['domain'])

        command = f'rustic -r {self.repo} forget {deleteString} --prune --password ""  2>/dev/null'
        result = ProcessUtilities.outputExecutioner(command, self.website.externalApp, True)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.CyberCPLogFileWriter.writeToFile(result)

    @staticmethod
    def FetchCurrentSchedules(website):
        try:
            finalConfigPath = f'/home/cyberpanel/v2backups/{website}'

            if os.path.exists(finalConfigPath):
                command = f'cat {finalConfigPath}'
                RetResult = ProcessUtilities.outputExecutioner(command)
                print(repr(RetResult))
                BackupConfig = json.loads(ProcessUtilities.outputExecutioner(command).rstrip('\n'))

                schedules = []
                for value in BackupConfig['schedules']:

                    schedules.append({
                                      'repo': value['repo'],
                                      'frequency': value['frequency'],
                                      'websiteData': value['websiteData'],
                                      'websiteEmails': value['websiteEmails'],
                                      'websiteDatabases': value['websiteDatabases'],
                                      'lastRun': value['lastRun'],
                                      'retention': value['retention'],
                                      'domain': website
                                      })

                return 1, schedules
            else:
                return 1, []

        except BaseException as msg:
            return 0, str(msg)

    @staticmethod
    def refresh_V2Gdive_token(refresh_token):
        try:
            # refresh_token = "1//09pPJHjUgyp09CgYIARAAGAkSNgF-L9IrZ0FLMhuKVfPEwmv_6neFto3JJ-B9uXBYu1kPPdsPhSk1OJXDBA3ZvC3v_AH9S1rTIQ"

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile('Current Token: ' + refresh_token )

            finalData = json.dumps({'refresh_token': refresh_token})
            r = requests.post("https://platform.cyberpersons.com/refreshToken", data=finalData
                              )
            newtoken = json.loads(r.text)['access_token']

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile('newtoken: ' + newtoken )
                logging.CyberCPLogFileWriter.writeToFile(r.text)

            return newtoken
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(f'Error in tkupdate: {str(msg)}')
            print("Error Update token:%s" % msg)
            return None

    @staticmethod
    def DeleteSchedule(website, repo, frequency, websiteData, websiteDatabases, websiteEmails):
        try:
            finalConfigPath = f'/home/cyberpanel/v2backups/{website}'

            if os.path.exists(finalConfigPath):
                command = f'cat {finalConfigPath}'
                RetResult = ProcessUtilities.outputExecutioner(command)
                print(repr(RetResult))
                BackupConfig = json.loads(ProcessUtilities.outputExecutioner(command).rstrip('\n'))
                counter = 0

                for value in BackupConfig['schedules']:

                    if value['repo'] == repo and value['frequency'] == frequency and value['websiteData'] == websiteData and \
                            value['websiteEmails'] == websiteEmails and value['websiteDatabases'] == websiteDatabases:
                        del BackupConfig['schedules'][counter]
                        break
                    else:
                        counter = counter  + 1

                FinalContent = json.dumps(BackupConfig)
                WriteToFile = open(finalConfigPath, 'w')
                WriteToFile.write(FinalContent)
                WriteToFile.close()

                return 1, BackupConfig
            else:
                return 1, []

        except BaseException as msg:
            return 0, str(msg)

    @staticmethod
    def CreateScheduleV2(website, repo, frequency, websiteData, websiteDatabases, websiteEmails, retention):
        try:

            finalConfigPath = f'/home/cyberpanel/v2backups/{website}'

            if not os.path.exists('/home/cyberpanel/v2backups/'):

                command = 'mkdir -p /home/cyberpanel/v2backups/'
                ProcessUtilities.executioner(command, 'cyberpanel')


            if os.path.exists(finalConfigPath):

                command = f'cat {finalConfigPath}'
                RetResult = ProcessUtilities.outputExecutioner(command)
                print(repr(RetResult))
                BackupConfig = json.loads(ProcessUtilities.outputExecutioner(command).rstrip('\n'))

                try:
                    BackupConfig['schedules'].append({"repo": repo, "retention": retention, "frequency": frequency, "websiteData": websiteData,
                                      "websiteEmails": websiteEmails, "websiteDatabases": websiteDatabases,
                                      "lastRun": ""})
                except:
                    BackupConfig['schedules'] = [{"repo": repo, "retention": retention, "frequency": frequency, "websiteData": websiteData,
                                      "websiteEmails": websiteEmails, "websiteDatabases": websiteDatabases,
                                      "lastRun": ""}]

                # BackupConfig['schedules'] = {"retention": "7", "frequency": frequency, "websiteData": websiteData,
                #                       "websiteEmails": websiteEmails, "websiteDatabases": websiteDatabases,
                #                       "lastRun": ""}

                FinalContent = json.dumps(BackupConfig)
                WriteToFile = open(finalConfigPath, 'w')
                WriteToFile.write(FinalContent)
                WriteToFile.close()
                return 1, BackupConfig
            else:
                BackupConfig = {'site': website,
                                'schedules':
                                    [{"repo": repo, "retention": retention, "frequency": frequency,
                                      "websiteData": websiteData,
                                      "websiteEmails": websiteEmails, "websiteDatabases": websiteDatabases,
                                      "lastRun": ""}]}

                FinalContent = json.dumps(BackupConfig)
                WriteToFile = open(finalConfigPath, 'w')
                WriteToFile.write(FinalContent)
                WriteToFile.close()

                return 1, BackupConfig

        except BaseException as msg:
            return 0, str(msg)



    @staticmethod
    def DeleteRepoScheduleV2(website, repo, eu):
        try:
            finalConfigPath = f'/home/{website}/.config/rclone/rclone.conf'

            if os.path.exists(finalConfigPath):
                command = f"sed -i '/\[{repo}\]/,/^$/d' {finalConfigPath}"
                ProcessUtilities.outputExecutioner(command, eu, True)


                return 1, 'Done'
            else:
                return 0, "Repo not found!"
        except BaseException as msg:
            return 0, str(msg)
    # def BackupEmails(self):
    #
    #     ### This function will backup emails of the website, also need to take care of emails that we need to exclude
    #     ### excluded emails are in a list self.data['ExcludedEmails'] only backup data if backupemail check is on
    #     ## For example if self.data['BackupEmails'] is one then only run this function otherwise not
    #
    #     destination = f'{self.FinalPath}/emails'
    #     source = f'/home/vmail/{self.website.domain}'
    #
    #     ## Pending add user provided folders in the exclude list
    #
    #     exclude = f'--exclude=.cache --exclude=.cache --exclude=.cache --exclude=.wp-cli ' \
    #               f'--exclude=backup --exclude=incbackup --exclude=incbackup --exclude=logs --exclude=lscache'
    #
    #     command = f'mkdir -p {destination}'
    #     ProcessUtilities.executioner(command, 'cyberpanel')
    #
    #     command = f'chown vmail:vmail {destination}'
    #     ProcessUtilities.executioner(command)
    #
    #     command = f'rsync -av  {source}/ {destination}/'
    #     ProcessUtilities.executioner(command, 'vmail')
    #
    #     return 1

    # def BackupDataBases(self):
    #
    #     ### This function will backup databases of the website, also need to take care of database that we need to exclude
    #     ### excluded databases are in a list self.data['ExcludedDatabases'] only backup databases if backupdatabase check is on
    #     ## For example if self.data['BackupDatabase'] is one then only run this function otherwise not
    #
    #     command = f'chown {self.website.externalApp}:{self.website.externalApp} {self.FinalPathRuctic}'
    #     ProcessUtilities.executioner(command)
    #
    #     command = f'rustic init -r {self.FinalPathRuctic} --password ""'
    #     ProcessUtilities.executioner(command, self.website.externalApp)
    #
    #     command = f'chown cyberpanel:cyberpanel {self.FinalPathRuctic}'
    #     ProcessUtilities.executioner(command)
    #
    #     from plogical.mysqlUtilities import mysqlUtilities
    #
    #     for dbs in self.config['databases']:
    #
    #         ### Pending: Need to only backup database present in the list of databases that need backing up
    #
    #         for key, value in dbs.items():
    #             print(f'DB {key}')
    #
    #             if mysqlUtilities.createDatabaseBackup(key, self.FinalPath) == 0:
    #                 self.UpdateStatus(f'Failed to create backup for database {key}.', CPBackupsV2.RUNNING)
    #                 return 0
    #
    #             for dbUsers in value:
    #                 print(f'User: {dbUsers["user"]}, Host: {dbUsers["host"]}, Pass: {dbUsers["password"]}')
    #
    #
    #
    #     return 1

    # def BackupData(self):
    #
    #     ### This function will backup data of the website, also need to take care of directories that we need to exclude
    #     ### excluded directories are in a list self.data['ExcludedDirectories'] only backup data if backupdata check is on
    #     ## For example if self.data['BackupData'] is one then only run this function otherwise not
    #
    #     destination = f'{self.FinalPath}/data'
    #     source = f'/home/{self.website.domain}'
    #
    #     ## Pending add user provided folders in the exclude list
    #
    #     exclude = f'--exclude=.cache --exclude=.cache --exclude=.cache --exclude=.wp-cli ' \
    #               f'--exclude=backup --exclude=incbackup --exclude=incbackup --exclude=logs --exclude=lscache'
    #
    #     command = f'mkdir -p {destination}'
    #     ProcessUtilities.executioner(command, 'cyberpanel')
    #
    #     command = f'chown {self.website.externalApp}:{self.website.externalApp} {destination}'
    #     ProcessUtilities.executioner(command)
    #
    #     command = f'rsync -av {exclude}  {source}/ {destination}/'
    #     ProcessUtilities.executioner(command, self.website.externalApp)
    #
    #     return 1

    def InstallRustic(self):
        try:

            if not os.path.exists(CPBackupsV2.RUSTIC_PATH):

                ### also install rclone

                command = 'curl https://rclone.org/install.sh | sudo bash'
                ProcessUtilities.executioner(command, None, True)



                url = "https://api.github.com/repos/rustic-rs/rustic/releases/latest"
                response = requests.get(url)

                if response.status_code == 200:
                    data = response.json()
                    version = data['tag_name']
                    name = data['name']
                else:
                    return 0, str(response.content)

                # sudo mv filename /usr/bin/
                from plogical.acl import ACLManager

                if ACLManager.ISARM():
                    command = 'wget -P /home/rustic https://github.com/rustic-rs/rustic/releases/download/%s/rustic-%s-aarch64-unknown-linux-gnu.tar.gz' % (
                        version, version)
                    ProcessUtilities.executioner(command)

                    command = 'tar xzf /home/rustic/rustic-%s-aarch64-unknown-linux-gnu.tar.gz -C /home/rustic//' % (
                        version)
                    ProcessUtilities.executioner(command)

                else:
                    command = 'wget -P /home/rustic https://github.com/rustic-rs/rustic/releases/download/%s/rustic-%s-x86_64-unknown-linux-musl.tar.gz' % (
                version, version)
                    ProcessUtilities.executioner(command)

                    command = 'tar xzf /home/rustic/rustic-%s-x86_64-unknown-linux-musl.tar.gz -C /home/rustic//' % (
                        version)
                    ProcessUtilities.executioner(command)

                command = 'sudo mv /home/rustic/rustic /usr/bin/'
                ProcessUtilities.executioner(command)

                command = 'rm -rf /home/rustic'
                ProcessUtilities.executioner(command)

            return 1, None

        except BaseException as msg:
            print('Error: %s' % msg)
            return 0, str(msg)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='CyberPanel Backup Generator')
        parser.add_argument('function', help='Specify a function to call!')
        parser.add_argument('--path', help='')

        args = parser.parse_args()

        if args.function == "BackupDataBases":
            cpbuv2 = CPBackupsV2({'finalPath': args.path})
            # cpbuv2.BackupDataBases()

    except:
        cpbuv2 = CPBackupsV2(
            {'function': 'InitiateRestore', 'domain': 'cyberpanel.net', 'BasePath': '/home/backup', 'SnapShotID': 1,
             'BackendName': 'usman'})
        cpbuv2.InitiateRestore()
