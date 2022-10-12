import os,sys
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
    def createDatabaseBackup(databaseName, tempStoragePath):
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

            command = 'mysqldump --defaults-extra-file=/home/cyberpanel/.my.cnf -u %s --host=%s --port %s %s' % (mysqluser, mysqlhost, mysqlport, databaseName)
            cmd = shlex.split(command)

            try:
                errorPath = '/home/cyberpanel/error-logs.txt'
                errorLog = open(errorPath, 'a')
                with open(tempStoragePath+"/"+databaseName+'.sql', 'w') as f:
                    res = subprocess.call(cmd,stdout=f, stderr=errorLog)
                    if res != 0:
                        logging.CyberCPLogFileWriter.writeToFile(
                            "Database: " + databaseName + "could not be backed! [createDatabaseBackup]")
                        return 0

            except subprocess.CalledProcessError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    "Database: " + databaseName + "could not be backed! Error: %s. [createDatabaseBackup]" % (str(msg)))
                return 0
            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabaseBackup]")
            return 0

    @staticmethod
    def restoreDatabaseBackup(databaseName, tempStoragePath, dbPassword, passwordCheck = None, additionalName = None):
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

            command = 'mysql --defaults-extra-file=/home/cyberpanel/.my.cnf -u %s --host=%s --port %s %s' % (mysqluser, mysqlhost, mysqlport, databaseName)
            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'{command} {tempStoragePath}/{databaseName} ' )
            cmd = shlex.split(command)

            if additionalName == None:
                with open(tempStoragePath + "/" + databaseName + '.sql', 'r') as f:
                    res = subprocess.call(cmd, stdin=f)
                if res != 0:
                    logging.CyberCPLogFileWriter.writeToFile("Could not restore MYSQL database: " + databaseName +"! [restoreDatabaseBackup]")
                    return 0
            else:
                with open(tempStoragePath + "/" + additionalName + '.sql', 'r') as f:
                    res = subprocess.call(cmd, stdin=f)

                if res != 0:
                    logging.CyberCPLogFileWriter.writeToFile("Could not restore MYSQL database: " + additionalName + "! [restoreDatabaseBackup]")
                    return 0

            if passwordCheck == None:

                connection, cursor = mysqlUtilities.setupConnection()

                if connection == 0:
                    return 0

                passwordCMD = "use mysql;SET PASSWORD FOR '" + databaseName + "'@'%s' = '" % (mysqlUtilities.LOCALHOST) + dbPassword + "';FLUSH PRIVILEGES;"

                cursor.execute(passwordCMD)
                connection.close()

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
            else:
                command = 'sudo mv /etc/mysql/my.cnf /etc/mysql/my.cnf.bak'
                data['suggestedContent'] = data['suggestedContent'].replace('/var/lib/mysql/mysql.sock', '/var/run/mysqld/mysqld.sock')


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

            cursor.execute("use " + name['databaseName'])
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

            cursor.execute("use " + name['databaseName'])
            cursor.execute("DROP TABLE " + name['tableName'])

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

            cursor.execute("use " + name['databaseName'])
            cursor.execute("select count(*) from " + name['tableName'])
            rows = cursor.fetchall()[0][0]


            ##

            cursor.execute("desc " + name['tableName'])
            result = cursor.fetchall()

            data['completeData'] = '<thead><tr>'

            for items in result:
                data['completeData'] = data['completeData'] + '<th>' + items[0] + '</th>'

            data['completeData'] = data['completeData'] + '</tr></thead>'

            data['completeData'] = data['completeData'] + '<tbody>'

            ##

            data['pagination'] = mysqlUtilities.getPagination(rows, recordsToShow)
            endPageNumber, finalPageNumber = mysqlUtilities.recordsPointer(page, recordsToShow)

            cursor.execute("select * from " + name['tableName'])
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

            cursor.execute("use " + name['databaseName'])
            cursor.execute("desc " + name['tableName'])
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

def main():
    parser = argparse.ArgumentParser(description='CyberPanel')
    parser.add_argument('function', help='Specific a function to call!')

    args = parser.parse_args()

    if args.function == "enableRemoteMYSQL":
        mysqlUtilities.enableRemoteMYSQL()


if __name__ == "__main__":
    main()
