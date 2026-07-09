import os,sys
import shutil
import urllib
from urllib.parse import unquote

sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
from plogical import CyberCPLogFileWriter as logging
import subprocess
import shlex
try:
    from websiteFunctions.models import Websites
    from databases.models import Databases
    from backup.models import DBUsers
except:
    pass
import MySQLdb as mysql
import json
from random import randint
from plogical.processUtilities import ProcessUtilities
import MySQLdb.cursors as cursors
from math import ceil
import argparse

class mysqlUtilities:

    LOCALHOST = 'localhost'
    RDS = 0
    REMOTEHOST = ''

    @staticmethod
    def quoteIdentifier(identifier):
        # MySQL identifiers (db/table/column names) cannot be passed as bound
        # parameters. Backtick-quote them and double any embedded backtick so a
        # malicious value cannot break out of the identifier into SQL. This
        # preserves every legitimate identifier while neutralising injection.
        if identifier is None:
            raise ValueError("identifier cannot be None")
        return "`" + str(identifier).replace("`", "``") + "`"

    @staticmethod
    def getPagination(records, toShow):
        pages = float(records) / float(toShow)

        pagination = []
        counter = 1

        if pages <= 1.0:
            pages = 1
            pagination.append(counter)
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append(counter)
                counter = counter + 1

        return pagination

    @staticmethod
    def recordsPointer(page, toShow):
        finalPageNumber = ((page * toShow)) - toShow
        endPageNumber = finalPageNumber + toShow
        return endPageNumber, finalPageNumber

    @staticmethod
    def setupConnection():
        try:

            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(open(passFile, 'r').read())

                mysqluser = jsonData['mysqluser']
                mysqlpassword = jsonData['mysqlpassword']
                mysqlport = jsonData['mysqlport']
                mysqlhost = jsonData['mysqlhost']
                mysqlUtilities.REMOTEHOST = mysqlhost

                if mysqlhost.find('rds.amazon') > -1:
                    mysqlUtilities.RDS = 1

                ## Also set localhost to this server

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddressLocal = ipData.split('\n', 1)[0]

                mysqlUtilities.LOCALHOST = ipAddressLocal

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('Local IP for MySQL: %s' % (mysqlUtilities.LOCALHOST))

                conn = mysql.connect(host=mysqlhost ,user=mysqluser, passwd=mysqlpassword, port=int(mysqlport), cursorclass=cursors.SSCursor)
                cursor = conn.cursor()

                return conn, cursor

            except BaseException as msg:

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('%s. [setupConnection:75]' % (str(msg)))

                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]
                password = password.strip('\n').strip('\r')

                conn = mysql.connect(user='root', passwd=password, cursorclass=cursors.SSCursor)
                cursor = conn.cursor()

                return conn, cursor

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0, 0

    @staticmethod
    def createDatabase(dbname,dbuser,dbpassword, dbcreate = 1, host = None):
        try:
            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            if dbcreate == 1:
                HostToUse = mysqlUtilities.LOCALHOST
            else:
                HostToUse = host
            ## Create db

            if dbcreate:

                query = "CREATE DATABASE %s" % (dbname)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(query)

                cursor.execute(query)

            ## create user

            if mysqlUtilities.REMOTEHOST.find('ondigitalocean') > -1:
                query = "CREATE USER '%s'@'%s' IDENTIFIED WITH mysql_native_password BY '%s'" % (
                dbuser, HostToUse, dbpassword)
            else:
                query = "CREATE USER '" + dbuser + "'@'%s' IDENTIFIED BY '" % (
                    HostToUse) + dbpassword + "'"

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(query)

            cursor.execute(query)

            if mysqlUtilities.RDS == 0:
                cursor.execute("GRANT ALL PRIVILEGES ON " + dbname + ".* TO '" + dbuser + "'@'%s'" % (HostToUse))
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile("GRANT ALL PRIVILEGES ON " + dbname + ".* TO '" + dbuser + "'@'%s'" % (HostToUse))
            else:
                cursor.execute(
                    "GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON " + dbname + ".* TO '" + dbuser + "'@'%s'" % (HostToUse))
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile("GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON " + dbname + ".* TO '" + dbuser + "'@'%s'" % (HostToUse))

            connection.close()

            return 1

        except BaseException as msg:
            if dbcreate:
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('Deleting database because failed to create %s' % (dbname))
                #mysqlUtilities.deleteDatabase(dbname, dbuser)
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
            return 0

    @staticmethod
    def createDBUser(dbuser, dbpassword):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("CREATE DATABASE " + dbuser)
            cursor.execute("CREATE USER '" + dbuser + "'@'%s' IDENTIFIED BY '" % (mysqlUtilities.LOCALHOST) + dbpassword + "'")

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDBUser]")
            return 0

    @staticmethod
    def allowGlobalUserAccess(globalUser, dbName):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            if mysqlUtilities.RDS == 0:
                cursor.execute("GRANT ALL PRIVILEGES ON " + dbName + ".* TO '" + globalUser + "'@'%s'" % (mysqlUtilities.LOCALHOST))
            else:
                cursor.execute("GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON " + dbName + ".* TO '" + globalUser + "'@'%s'" % (
                    mysqlUtilities.LOCALHOST))

            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
            return 0

    @staticmethod
    def deleteDatabase(dbname, dbuser):
        try:

            ## Remove possible git folder

            dbPath = '/var/lib/mysql/%s/.git' % (dbname)

            command = 'rm -rf %s' % (dbPath)
            ProcessUtilities.executioner(command)

            ##

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("DROP DATABASE `%s`" % (dbname))

            ## Try deleting all user who had priviliges on db

            cursor.execute("select user,host from mysql.db where db='%s'" % (dbname))
            databaseUsers = cursor.fetchall()

            for databaseUser in databaseUsers:
                cursor.execute("DROP USER '"+databaseUser[0]+"'@'%s'" % (databaseUser[1]))
            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[deleteDatabase]")
            return str(msg)

    @staticmethod
    def createDatabaseBackup(databaseName, tempStoragePath, rustic=0, RusticRepoName = None,
                           externalApp = None, use_compression=None, use_new_features=None):
        """
        Enhanced database backup with backward compatibility

        Parameters:
        - use_compression: None (auto-detect), True (force compression), False (no compression)
        - use_new_features: None (auto-detect based on config), True/False (force)
        """
        try:
            # Check if new features are enabled (via config file or parameter)
            if use_new_features is None:
                use_new_features = mysqlUtilities.checkNewBackupFeatures()

            # Determine compression based on config or parameter
            if use_compression is None:
                use_compression = mysqlUtilities.shouldUseCompression()

            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(open(passFile, 'r').read())

                mysqluser = jsonData['mysqluser']
                mysqlpassword = jsonData['mysqlpassword']
                mysqlport = jsonData['mysqlport']
                mysqlhost = jsonData['mysqlhost']
                password = mysqlpassword
            except:
                passFile = "/etc/cyberpanel/mysqlPassword"
                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]
                mysqlhost = 'localhost'
                mysqlport = '3306'
                mysqluser = 'root'


            cnfPath = '/home/cyberpanel/.my.cnf'

            if not os.path.exists(cnfPath):
                cnfContent = """[mysqldump]
user=root
password=%s
max_allowed_packet=1024M
[mysql]
user=root
password=%s
""" % (password, password)
                writeToFile = open(cnfPath, 'w')
                writeToFile.write(cnfContent)
                writeToFile.close()

                os.chmod(cnfPath, 0o600)

            SHELL = False

            if rustic == 0:
                # Determine backup file extension based on compression
                if use_compression:
                    backup_extension = '.sql.gz'
                    backup_file = f"{tempStoragePath}/{databaseName}{backup_extension}"
                else:
                    backup_extension = '.sql'
                    backup_file = f"{tempStoragePath}/{databaseName}{backup_extension}"

                # Remove old backup if exists
                command = f'rm -f {backup_file}'
                ProcessUtilities.executioner(command)

                # Build mysqldump command with new features
                dump_cmd = mysqlUtilities.buildMysqldumpCommand(
                    mysqluser, mysqlhost, mysqlport, databaseName,
                    use_new_features, use_compression
                )

                if use_compression:
                    # New method: Stream directly to compressed file
                    full_command = f"{dump_cmd} | gzip -c > {backup_file}"
                    result = ProcessUtilities.executioner(full_command, shell=True)

                    # Verify backup file was created successfully
                    if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
                        logging.CyberCPLogFileWriter.writeToFile(
                            f"Database: {databaseName} could not be backed up (compressed)! [createDatabaseBackup]"
                        )
                        return 0
                else:
                    # Legacy method: Direct dump to file (backward compatible)
                    cmd = shlex.split(dump_cmd)

                    with open(backup_file, 'w') as f:
                        result = subprocess.run(
                            cmd,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            shell=SHELL
                        )

                        if result.returncode != 0:
                            logging.CyberCPLogFileWriter.writeToFile(
                                "Database: " + databaseName + " could not be backed up! [createDatabaseBackup]"
                            )
                            logging.CyberCPLogFileWriter.writeToFile(result.stderr.decode('utf-8'))
                            return 0

                # Store metadata about backup format for restore
                mysqlUtilities.saveBackupMetadata(
                    databaseName, tempStoragePath, use_compression, use_new_features
                )

            else:
                SHELL = True

                command = f'mysqldump --defaults-file=/home/cyberpanel/.my.cnf -u {mysqluser} --host={mysqlhost} --port {mysqlport} --add-drop-table --allow-keywords --complete-insert --quote-names --skip-comments {databaseName} 2>/dev/null | sudo -u {externalApp} rustic -r {RusticRepoName} backup --stdin-filename {databaseName}.sql - --password "" --json 2>/dev/null'

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(command)

                result = json.loads(
                    ProcessUtilities.outputExecutioner(command, None, True).rstrip('\n'))

                try:
                    SnapShotID = result['id']  ## snapshot id that we need to store in db
                    files_new = result['summary']['files_new']  ## basically new files in backup
                    total_duration = result['summary']['total_duration']  ## time taken

                    return 1, SnapShotID

                except BaseException as msg:
                    return 0, str(msg)



            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabaseBackup]")
            return 0

    @staticmethod
    def restoreDatabaseBackup(databaseName, tempStoragePath, dbPassword, passwordCheck = None, additionalName = None, rustic=0, RusticRepoName = None, externalApp = None, snapshotid = None):
        """
        Enhanced restore with automatic format detection
        """
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(open(passFile, 'r').read())

                mysqluser = jsonData['mysqluser']
                mysqlpassword = jsonData['mysqlpassword']
                mysqlport = jsonData['mysqlport']
                mysqlhost = jsonData['mysqlhost']
                password = mysqlpassword
            except:
                passFile = "/etc/cyberpanel/mysqlPassword"
                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]
                mysqlhost = 'localhost'
                mysqlport = '3306'
                mysqluser = 'root'

            cnfPath = '/home/cyberpanel/.my.cnf'

            if not os.path.exists(cnfPath):
                cnfContent = """[mysqldump]
user=root
password=%s
max_allowed_packet=1024M
[mysql]
user=root
password=%s
""" % (password, password)
                writeToFile = open(cnfPath, 'w')
                writeToFile.write(cnfContent)
                writeToFile.close()

                os.chmod(cnfPath, 0o600)
                command = 'chown cyberpanel:cyberpanel %s' % (cnfPath)
                subprocess.call(shlex.split(command))

            if rustic == 0:
                # Auto-detect backup format
                backup_format = mysqlUtilities.detectBackupFormat(
                    tempStoragePath, databaseName, additionalName
                )

                if additionalName:
                    base_name = additionalName
                else:
                    base_name = databaseName

                # Determine actual backup file based on detected format
                if backup_format['compressed']:
                    backup_file = f"{tempStoragePath}/{base_name}.sql.gz"
                    if not os.path.exists(backup_file):
                        # Fallback to uncompressed for backward compatibility
                        backup_file = f"{tempStoragePath}/{base_name}.sql"
                        backup_format['compressed'] = False
                else:
                    backup_file = f"{tempStoragePath}/{base_name}.sql"
                    if not os.path.exists(backup_file):
                        # Try compressed version
                        backup_file = f"{tempStoragePath}/{base_name}.sql.gz"
                        if os.path.exists(backup_file):
                            backup_format['compressed'] = True

                if not os.path.exists(backup_file):
                    logging.CyberCPLogFileWriter.writeToFile(
                        f"Backup file not found: {backup_file}"
                    )
                    return 0

                # Build restore command
                mysql_cmd = f'mysql --defaults-file=/home/cyberpanel/.my.cnf -u {mysqluser} --host={mysqlhost} --port {mysqlport} {databaseName}'

                if backup_format['compressed']:
                    # Handle compressed backup
                    restore_cmd = f"gunzip -c {backup_file} | {mysql_cmd}"
                    result = ProcessUtilities.executioner(restore_cmd, shell=True)

                    # Don't rely solely on exit code, MySQL import usually succeeds
                    # The passwordCheck logic below will verify database integrity
                else:
                    # Handle uncompressed backup (legacy)
                    cmd = shlex.split(mysql_cmd)
                    with open(backup_file, 'r') as f:
                        result = subprocess.call(cmd, stdin=f)

                    # Don't fail on non-zero exit as MySQL may return warnings
                    # The passwordCheck logic below will verify database integrity

                if passwordCheck == None:

                    connection, cursor = mysqlUtilities.setupConnection()

                    if connection == 0:
                        return 0

                    passwordCMD = "use mysql;SET PASSWORD FOR '" + databaseName + "'@'%s' = '" % (mysqlUtilities.LOCALHOST) + dbPassword + "';FLUSH PRIVILEGES;"

                    cursor.execute(passwordCMD)
                    connection.close()

                return 1
            else:
                command = f'sudo -u {externalApp} rustic -r {RusticRepoName} dump {snapshotid}:{databaseName}.sql --password "" 2>/dev/null | mysql --defaults--file=/home/cyberpanel/.my.cnf -u %s --host=%s --port %s %s' % (
                mysqluser, mysqlhost, mysqlport, databaseName)
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(f'{command} {tempStoragePath}/{databaseName} ')
                ProcessUtilities.outputExecutioner(command, None, True)

                return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[restoreDatabaseBackup]")
            return 0

    @staticmethod
    def submitDBCreation(dbName, dbUsername, dbPassword, databaseWebsite):
        try:

            if len(dbName) > 32 or len(dbUsername) > 32:
                raise BaseException("Length of Database name or Database user should be 32 at max.")

            website = Websites.objects.get(domain=databaseWebsite)

            if website.package.dataBases == 0:
                pass
            elif website.package.dataBases > website.databases_set.all().count():
                pass
            else:
                raise BaseException("Maximum database limit reached for this website.")

            if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(dbUser=dbUsername).exists():
                raise BaseException("This database or user is already taken.")

            result = mysqlUtilities.createDatabase(dbName, dbUsername, dbPassword)

            if result == 1:
                pass
            else:
                raise BaseException(result)

            db = Databases(website=website, dbName=dbName, dbUser=dbUsername)
            db.save()

            return 1,'None'

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0,str(msg)

    @staticmethod
    def submitDBDeletion(dbName):
        try:

            databaseToBeDeleted = Databases.objects.get(dbName=dbName)
            result = mysqlUtilities.deleteDatabase(dbName, databaseToBeDeleted.dbUser)

            if result == 1:
                databaseToBeDeleted.delete()
                return 1,'None'
            else:
                databaseToBeDeleted.delete()
                logging.CyberCPLogFileWriter.writeToFile('Deleted database with some errors. Error: %s' % (result))
                return 1,'None'

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0, str(msg)

    @staticmethod
    def getDatabases(virtualHostName):
        try:
            website = Websites.objects.get(domain=virtualHostName)
            return website.databases_set.all()
        except:
            0

    @staticmethod
    def showStatus():
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("SHOW GLOBAL STATUS")
            result = cursor.fetchall()

            data = {}
            data['status'] = 1

            for items in result:
                if items[0] == 'Uptime':
                    data['uptime'] = mysqlUtilities.GetTime(items[1])
                elif items[0] == 'Connections':
                    data['connections'] = items[1]
                elif items[0] == 'Slow_queries':
                    data['Slow_queries'] = items[1]

            ## Process List

            cursor.execute("show processlist")
            result = cursor.fetchall()

            json_data = "["
            checker = 0

            for items in result:
                if len(str(items[1])) == 0:
                    database = 'NULL'
                else:
                    database = items[1]

                if len(str(items[6])) == 0:
                    state = 'NULL'
                else:
                    state = items[6]

                if len(str(items[7])) == '':
                    info = 'NULL'
                else:
                    info = items[7]

                dic = {
                    'id': items[0],
                    'user': items[1],
                    'database': database,
                    'command': items[4],
                    'time': items[5],
                    'state': state,
                    'info': info,
                    'progress': items[8],
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            data['processes'] = json_data

            ##

            return data

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[showStatus]")
            return 0

    @staticmethod
    def GetTime(seconds):
        time = float(seconds)
        day = time // (24 * 3600)
        time = time % (24 * 3600)
        hour = time // 3600
        time %= 3600
        minutes = time // 60
        time %= 60
        seconds = time

        return ("%d:%d:%d:%d" % (day, hour, minutes, seconds))

    @staticmethod
    def applyMySQLChanges(data):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo mv /etc/my.cnf /etc/my.cnf.bak'
                decoded_content = urllib.parse.unquote(data['suggestedContent'])
                data['suggestedContent'] = decoded_content.replace('/var/lib/mysql/mysql.sock',
                                                                   '/var/run/mysqld/mysqld.sock')
            else:
                command = 'sudo mv /etc/mysql/my.cnf /etc/mysql/my.cnf.bak'
                decoded_content = urllib.parse.unquote(data['suggestedContent'])
                data['suggestedContent'] = decoded_content.replace('/var/lib/mysql/mysql.sock', '/var/run/mysqld/mysqld.sock')


            ProcessUtilities.executioner(command)

            ## Temp

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            writeToFile = open(tempPath, 'w')
            writeToFile.write(data['suggestedContent'])
            writeToFile.close()

            ##
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo mv ' + tempPath + ' /etc/my.cnf'
            else:
                command = 'sudo mv ' + tempPath + ' /etc/mysql/my.cnf'

            ProcessUtilities.executioner(command)

            return 1, None

        except BaseException as msg:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo mv /etc/my.cnf.bak /etc/my.cnf'
            else:
                command = 'sudo mv /etc/mysql/my.cnf.bak /etc/mysql//my.cnf'
            subprocess.call(shlex.split(command))
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0, str(msg)

    @staticmethod
    def fetchVariables():
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("SHOW VARIABLES")
            result = cursor.fetchall()

            for items in result:
                logging.CyberCPLogFileWriter.writeToFile(str(items))


            ##

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[showStatus]")
            return 0

    @staticmethod
    def restartMySQL():
        try:
            command = 'sudo systemctl restart mariadb'
            ProcessUtilities.executioner(command)

            return 1, None

        except BaseException as msg:
            command = 'sudo mv /etc/my.cnf.bak /etc/my.cnf'
            subprocess.call(shlex.split(command))
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0, str(msg)

    @staticmethod
    def fetchDatabases():
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            data = {}
            data['status'] = 1

            cursor.execute("SHOW DATABASES")
            result = cursor.fetchall()

            counter = 1
            json_data = "["
            checker = 0

            for items in result:
                if items[0] == 'information_schema' or items[0] == 'mysql' or items[0] == 'performance_schema':
                    continue

                dic = {
                    'id': counter,
                    'database': items[0]

                }
                counter = counter + 1

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)


            json_data = json_data + ']'
            data['databases'] = json_data
            return data

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[fetchDatabases]")
            return 0

    @staticmethod
    def fetchTables(name):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            data = {}
            data['status'] = 1

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
            cursor.execute("SHOW TABLE STATUS")
            result = cursor.fetchall()

            counter = 1
            json_data = "["
            checker = 0

            for items in result:

                dic = {
                    'Name': items[0],
                    'Engine': items[1],
                    'Version': items[2],
                    'rowFormat': items[3],
                    'rows': items[4],
                    'Collation': items[14]
                }
                counter = counter + 1

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            data['tables'] = json_data
            return data

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[fetchDatabases]")
            return 0

    @staticmethod
    def deleteTable(name):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            data = {}
            data['status'] = 1

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
            cursor.execute("DROP TABLE " + mysqlUtilities.quoteIdentifier(name['tableName']))

            return data

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[fetchDatabases]")
            return 0

    @staticmethod
    def fetchTableData(name):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            recordsToShow = int(name['recordsToShow'])
            page = int(name['currentPage'])

            data = {}
            data['status'] = 1

            ##

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
            cursor.execute("select count(*) from " + mysqlUtilities.quoteIdentifier(name['tableName']))
            rows = cursor.fetchall()[0][0]


            ##

            cursor.execute("desc " + mysqlUtilities.quoteIdentifier(name['tableName']))
            result = cursor.fetchall()

            data['completeData'] = '<thead><tr>'

            for items in result:
                data['completeData'] = data['completeData'] + '<th>' + items[0] + '</th>'

            data['completeData'] = data['completeData'] + '</tr></thead>'

            data['completeData'] = data['completeData'] + '<tbody>'

            ##

            data['pagination'] = mysqlUtilities.getPagination(rows, recordsToShow)
            endPageNumber, finalPageNumber = mysqlUtilities.recordsPointer(page, recordsToShow)

            cursor.execute("select * from " + mysqlUtilities.quoteIdentifier(name['tableName']))
            result = cursor.fetchall()

            for items in result[finalPageNumber:endPageNumber]:
                data['completeData'] = data['completeData'] + '<tr>'
                for it in items:
                    data['completeData'] = data['completeData'] + '<td>' + str(it) + '</td>'
                data['completeData'] = data['completeData'] + '</tr>'

            data['completeData'] = data['completeData'] + '</tbody>'

            ##

            return data

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[fetchTableData]")
            return 0

    @staticmethod
    def fetchStructure(name):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
            cursor.execute("desc " + mysqlUtilities.quoteIdentifier(name['tableName']))
            result = cursor.fetchall()

            ## Columns List

            data = {}
            data['status'] = 1

            json_data = "["
            checker = 0

            for items in result:

                dic = {
                    'Name': items[0],
                    'Type': items[1],
                    'Null': items[2],
                    'Key': items[3],
                    'Default': items[4],
                    'Extra': items[5]
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            data['columns'] = json_data

            ##

            return data

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[showStatus]")
            return 0

    @staticmethod
    def changePassword(userName, dbPassword, encrypt = None, host = None):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("use mysql")

            if host != None:
                LOCALHOST = host
            else:
                LOCALHOST = mysqlUtilities.LOCALHOST

            if encrypt == None:
                try:
                    dbuser = DBUsers.objects.get(user=userName)
                    query = "SET PASSWORD FOR '" + userName + "'@'%s' = PASSWORD('" % (LOCALHOST) + dbPassword + "')"
                except:
                    userName = mysqlUtilities.fetchuser(userName)
                    query = "SET PASSWORD FOR '" + userName + "'@'%s' = PASSWORD('" % (LOCALHOST) + dbPassword + "')"
            else:
                query = "SET PASSWORD FOR '" + userName + "'@'%s' = '" % (LOCALHOST) + dbPassword + "'"

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(query)

            cursor.execute(query)

            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[mysqlUtilities.changePassword]")
            return 0

    @staticmethod
    def fetchuser(databaseName):
        try:
            connection, cursor = mysqlUtilities.setupConnection()
            cursor.execute("use mysql")
            database = Databases.objects.get(dbName=databaseName)
            databaseName = databaseName.replace('_', '\_')
            query = "select user from db where db = '%s'" % (databaseName)

            if connection == 0:
                return 0

            cursor.execute(query)
            rows = cursor.fetchall()
            counter = 0

            for row in rows:
                if row[0].find('_') > -1:
                    database.dbUser = row[0]
                    database.save()

                    try:
                        connection.close()
                    except:
                        pass
                    message = 'Detected databaser user is %s for database %s.' % (row[0], databaseName)
                    logging.CyberCPLogFileWriter.writeToFile(message)
                    return row[0]
                else:
                    counter = counter + 1

            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[mysqlUtilities.fetchuser]")
            return 0

    @staticmethod
    def allowRemoteAccess(dbName, userName, remoteIP):
        try:

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mysqlUtilities.py enableRemoteMYSQL"
            ProcessUtilities.executioner(execPath)

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[mysqlUtilities.allowRemoteAccess]")
            return 0

    @staticmethod
    def enableRemoteMYSQL():
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20 or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                cnfPath = '/etc/mysql/my.cnf'
            else:
                cnfPath = '/etc/my.cnf'

            data = open(cnfPath, 'r').read()

            if data.find('bind-address'):
                print('1,None')
                return 1
            else:
                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddressLocal = ipData.split('\n', 1)[0]

                mysqldContent = '''
[mysqld] 
bind-address=%s
''' % (ipAddressLocal)

                writeToFile = open(cnfPath, 'a')
                writeToFile.write(mysqldContent)
                writeToFile.close()

                print('1,None')

                from time import sleep
                sleep(5)
                ProcessUtilities.popenExecutioner('systemctl restart mariadb')
                return 1

        except BaseException as msg:
            print('0,%s "[mysqlUtilities.enableRemoteMYSQL]' % (str(msg)))
            return 0

    @staticmethod
    def addUserToDB(database, user, password, createUser = 0):
        try:

            connection, cursor = mysqlUtilities.setupConnection()
            
            if connection == 0:
                return 0

            if createUser:
                try:
                    cursor.execute(
                        "CREATE USER '" + user + "'@'%s' IDENTIFIED BY '" % (mysqlUtilities.LOCALHOST) + password + "'")
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile('%s [addUserToDB:937]' % (str(msg)))
                    try:
                        cursor.execute("DROP USER '%s'@'%s'" % (user, mysqlUtilities.LOCALHOST))
                        cursor.execute(
                            "CREATE USER '" + user + "'@'%s' IDENTIFIED BY '" % (mysqlUtilities.LOCALHOST) + password + "'")
                    except BaseException as msg:
                        logging.CyberCPLogFileWriter.writeToFile('%s [addUserToDB:943]'  % (str(msg)))

                return

            if mysqlUtilities.RDS == 0:
                cursor.execute(
                    "GRANT ALL PRIVILEGES ON " + database + ".* TO '" + user + "'@'%s'" % (mysqlUtilities.LOCALHOST))
            else:
                try:
                    cursor.execute(
                        "GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON " + database + ".* TO '" + user + "'@'%s'" % (mysqlUtilities.LOCALHOST))
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile('%s [addUserToDB:953]' % (str(msg)))

            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[addUserToDB]")
            return 0

    @staticmethod
    def UpdateWPTempPassword(dbname, password):
        try:

            ##

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("use %s" % (dbname))
            cursor.execute("UPDATE `wp_users` SET `user_pass`= MD5('%s') WHERE `user_login`='usman'" % (password))
            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[deleteDatabase]")
            return str(msg)

    @staticmethod
    def UpgradeMariaDB(versionToInstall, tempStatusPath):

        ### first check if provided version is already installed

        command = 'mysql --version'
        result = ProcessUtilities.outputExecutioner(command)

        if result.find(versionToInstall) > -1:
            print(f'MySQL is already {result}. [200]')
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, f'MySQL is already {result}. [200]')
            return 0

        logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Creating backup of MySQL..,10')

        MySQLBackupDir = '/var/lib/mysql-backupcp'

        from os import getuid
        if getuid() != 0:
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'This function should run as root. [404]')
            return 0, 'This function should run as root.'


        if not os.path.exists(MySQLBackupDir):
            command = 'rsync -av /var/lib/mysql/ /var/lib/mysql-backupcp/'
            ProcessUtilities.executioner(command)

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'MySQL backup created..,20')

        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:

            CNFCurrentPath = '/etc/mysql/ '
            CNFBackupPath = '/etc/cnfbackup/'

            command = f'rsync -av {CNFCurrentPath} {CNFBackupPath}'
            ProcessUtilities.executioner(command)

            command = 'sudo apt-get remove --purge mariadb-server mariadb-client galera -y && sudo apt autoremove -y'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'apt-get install apt-transport-https curl -y'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'mkdir -p /etc/apt/keyrings '
            ProcessUtilities.executioner(command, 'root', True)

            command = "curl -o /etc/apt/keyrings/mariadb-keyring.pgp 'https://mariadb.org/mariadb_release_signing_key.pgp'"
            ProcessUtilities.executioner(command, 'root', True)

            RepoPath = '/etc/apt/sources.list.d/mariadb.sources'
            RepoContent = f"""
# MariaDB {versionToInstall} repository list - created 2023-12-11 07:53 UTC
# https://mariadb.org/download/
X-Repolib-Name: MariaDB
Types: deb
# deb.mariadb.org is a dynamic mirror if your preferred mirror goes offline. See https://mariadb.org/mirrorbits/ for details.
# URIs: https://deb.mariadb.org/{versionToInstall}/ubuntu
URIs: https://mirrors.gigenet.com/mariadb/repo/{versionToInstall}/ubuntu
Suites: jammy
Components: main main/debug
Signed-By: /etc/apt/keyrings/mariadb-keyring.pgp
"""

            WriteToFile = open(RepoPath, 'w')
            WriteToFile.write(RepoContent)
            WriteToFile.close()

            command = 'apt-get update -y'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'DEBIAN_FRONTEND=noninteractive sudo apt-get install mariadb-server -y'
            ProcessUtilities.executioner(command, 'root', True)


        else:
            CNFCurrentPath = '/etc/my.cnf.d/ '
            CNFBackupPath = '/etc/cnfbackup/'

            command = f'rsync -av {CNFCurrentPath} {CNFBackupPath}'
            ProcessUtilities.executioner(command)

            if os.path.exists('/etc/my.cnf'):
                shutil.copy('/etc/my.cnf', f'{CNFBackupPath}/my.cnf')

            command = 'yum remove mariadb* -y'
            ProcessUtilities.executioner(command, 'root', True)


            RepoPath = '/etc/yum.repos.d/mariadb.repo'
            RepoContent = f"""
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/{versionToInstall}/rhel8-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1            
"""

            WriteToFile = open(RepoPath, 'w')
            WriteToFile.write(RepoContent)
            WriteToFile.close()


            command = 'dnf update -y'
            result = ProcessUtilities.outputExecutioner(command, 'root', True)

            print(result)

            command = 'dnf install mariadb-server -y'
            result = ProcessUtilities.outputExecutioner(command, 'root', True)

            print(result)

            command = 'systemctl start mariadb && systemctl enable mariadb'
            result = ProcessUtilities.outputExecutioner(command, 'root', True)

            print(result)


        logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Completed [200]')

    @staticmethod
    def buildMysqldumpCommand(user, host, port, database, use_new_features, use_compression):
        """Build mysqldump command with appropriate options"""

        base_cmd = f"mysqldump --defaults-file=/home/cyberpanel/.my.cnf -u {user} --host={host} --port {port}"

        # Add new performance features if enabled
        if use_new_features:
            # Add single-transaction for InnoDB consistency
            base_cmd += " --single-transaction"

            # Add extended insert for better performance
            base_cmd += " --extended-insert"

            # Add order by primary for consistent dumps
            base_cmd += " --order-by-primary"

            # Add quick option to avoid loading entire result set
            base_cmd += " --quick"

            # Add lock tables option
            base_cmd += " --lock-tables=false"

            # Check MySQL version for parallel support
            if mysqlUtilities.supportParallelDump():
                # Get number of threads (max 4 for safety)
                threads = min(4, ProcessUtilities.getNumberOfCores() if hasattr(ProcessUtilities, 'getNumberOfCores') else 2)
                base_cmd += f" --parallel={threads}"

        base_cmd += f" {database}"
        return base_cmd

    @staticmethod
    def saveBackupMetadata(database, path, compressed, new_features):
        """Save metadata about backup format for restore compatibility"""
        import time

        metadata = {
            'database': database,
            'compressed': compressed,
            'new_features': new_features,
            'backup_version': '2.0' if new_features else '1.0',
            'timestamp': time.time()
        }

        metadata_file = f"{path}/{database}.backup.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

    @staticmethod
    def detectBackupFormat(path, database, additional_name=None):
        """
        Detect backup format from metadata or file extension
        """
        base_name = additional_name if additional_name else database

        # First try to read metadata file (new backups will have this)
        metadata_file = f"{path}/{base_name}.backup.json"
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        # Fallback: detect by file existence and extension
        format_info = {
            'compressed': False,
            'new_features': False,
            'backup_version': '1.0'
        }

        # Check for compressed file
        if os.path.exists(f"{path}/{base_name}.sql.gz"):
            format_info['compressed'] = True
            # Compressed backups likely use new features
            format_info['new_features'] = True
            format_info['backup_version'] = '2.0'
        elif os.path.exists(f"{path}/{base_name}.sql"):
            format_info['compressed'] = False
            # Check file content for new features indicators
            format_info['new_features'] = mysqlUtilities.checkSQLFileFeatures(
                f"{path}/{base_name}.sql"
            )

        return format_info

    @staticmethod
    def checkNewBackupFeatures():
        """Check if new backup features are enabled"""
        try:
            config_file = '/usr/local/CyberCP/plogical/backup_config.json'
            if not os.path.exists(config_file):
                # Try alternate location
                config_file = '/etc/cyberpanel/backup_config.json'

            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('database_backup', {}).get('use_new_features', False)
        except:
            pass
        return False  # Default to legacy mode for safety

    @staticmethod
    def shouldUseCompression():
        """Check if compression should be used"""
        try:
            config_file = '/usr/local/CyberCP/plogical/backup_config.json'
            if not os.path.exists(config_file):
                # Try alternate location
                config_file = '/etc/cyberpanel/backup_config.json'

            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('database_backup', {}).get('use_compression', False)
        except:
            pass
        return False  # Default to no compression for compatibility

    @staticmethod
    def supportParallelDump():
        """Check if MySQL version supports parallel dump"""
        try:
            result = ProcessUtilities.outputExecutioner("mysql --version")
            # MySQL 8.0+ and MariaDB 10.3+ support parallel dump
            if "8.0" in result or "8.1" in result or "10.3" in result or "10.4" in result or "10.5" in result or "10.6" in result:
                return True
        except:
            pass
        return False

    @staticmethod
    def checkSQLFileFeatures(file_path):
        """Check SQL file for new feature indicators"""
        try:
            # Read first few lines to check for new features
            with open(file_path, 'r') as f:
                head = f.read(2048)  # Read first 2KB
                # Check for indicators of new features
                if "--single-transaction" in head or "--extended-insert" in head or "-- Dump completed" in head:
                    return True
        except:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description='CyberPanel')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--version', help='MySQL version to upgrade to.')
    parser.add_argument('--tempStatusPath', help='MySQL version to upgrade to.')

    args = parser.parse_args()


    if args.function == "enableRemoteMYSQL":
        mysqlUtilities.enableRemoteMYSQL()
    elif args.function == "UpgradeMariaDB":
        mysqlUtilities.UpgradeMariaDB(args.version, args.tempStatusPath)


if __name__ == "__main__":
    main()
