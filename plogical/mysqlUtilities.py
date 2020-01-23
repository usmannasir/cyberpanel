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

class mysqlUtilities:

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
    def createDatabase(dbname,dbuser,dbpassword):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("CREATE DATABASE " + dbname)
            cursor.execute("CREATE USER '" + dbuser + "'@'localhost' IDENTIFIED BY '"+dbpassword+"'")
            cursor.execute("GRANT ALL PRIVILEGES ON " + dbname + ".* TO '" + dbuser + "'@'localhost'")
            connection.close()

            return 1

        except BaseException as msg:
            mysqlUtilities.deleteDatabase(dbname, dbuser)
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
            return 0

    @staticmethod
    def createDBUser(dbuser, dbpassword):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("CREATE DATABASE " + dbuser)
            cursor.execute("CREATE USER '" + dbuser + "'@'localhost' IDENTIFIED BY '" + dbpassword + "'")

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

            cursor.execute("GRANT ALL PRIVILEGES ON " + dbName + ".* TO '" + globalUser + "'@'localhost'")
            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
            return 0

    @staticmethod
    def deleteDatabase(dbname, dbuser):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("DROP DATABASE `%s`" % (dbname))
            cursor.execute("DROP USER '"+dbuser+"'@'localhost'")
            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[deleteDatabase]")
            return str(msg)

    @staticmethod
    def createDatabaseBackup(databaseName, tempStoragePath):
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"
            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            cnfPath = '/home/cyberpanel/.my.cnf'

            if not os.path.exists(cnfPath):
                cnfContent = """[mysqldump]
user=root
password=%s
[mysql]
user=root
password=%s
""" % (password, password)
                writeToFile = open(cnfPath, 'w')
                writeToFile.write(cnfContent)
                writeToFile.close()

                os.chmod(cnfPath, 0o600)

            command = 'mysqldump --defaults-extra-file=/home/cyberpanel/.my.cnf --host=localhost ' + databaseName
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

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            cnfPath = '/home/cyberpanel/.my.cnf'

            if not os.path.exists(cnfPath):
                cnfContent = """[mysqldump]
user=root
password=%s
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

            command = 'mysql --defaults-extra-file=/home/cyberpanel/.my.cnf --host=localhost ' + databaseName
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

                passwordCMD = "use mysql;SET PASSWORD FOR '" + databaseName + "'@'localhost' = '" + dbPassword + "';FLUSH PRIVILEGES;"

                cursor.execute(passwordCMD)
                connection.close()

            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[restoreDatabaseBackup]")
            return 0

    @staticmethod
    def submitDBCreation(dbName, dbUsername, dbPassword, databaseWebsite):
        try:

            if len(dbName) > 16 or len(dbUsername) > 16:
                raise BaseException("Length of Database name or Database user should be 16 at max.")

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
                return 0,result

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
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
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'sudo mv ' + tempPath + ' /etc/my.cnf'
            else:
                command = 'sudo mv ' + tempPath + ' /etc/mysql/my.cnf'

            ProcessUtilities.executioner(command)

            return 1, None

        except BaseException as msg:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
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
            command = 'sudo systemctl restart mysql'
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
                if items[0] == 'information_schema' or items[0] == 'mysql' or items[0] == 'performance_schema' or items[
                    0] == 'performance_schema':
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
    def changePassword(userName, dbPassword, encrypt = None):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0
            cursor.execute("use mysql")

            if encrypt == None:
                try:
                    dbuser = DBUsers.objects.get(user=userName)
                    cursor.execute("SET PASSWORD FOR '" + userName + "'@'localhost' = PASSWORD('" + dbPassword + "')")
                except:
                    userName = mysqlUtilities.fetchuser(userName)
                    cursor.execute("SET PASSWORD FOR '" + userName + "'@'localhost' = PASSWORD('" + dbPassword + "')")
            else:
                cursor.execute("SET PASSWORD FOR '" + userName + "'@'localhost' = '" + dbPassword + "'")

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