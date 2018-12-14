import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import CyberCPLogFileWriter as logging
import subprocess
import shlex
from websiteFunctions.models import Websites
from databases.models import Databases
import MySQLdb as mysql


class mysqlUtilities:

    @staticmethod
    def setupConnection():
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            conn = mysql.connect(user='root', passwd=password)
            cursor = conn.cursor()

            return conn, cursor

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0, 0

    @staticmethod
    def createDatabase(dbname,dbuser,dbpassword):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("CREATE DATABASE " + dbname)
            cursor.execute("CREATE USER '" +dbuser+ "'@'localhost' IDENTIFIED BY '"+dbpassword+"'")
            cursor.execute("GRANT ALL PRIVILEGES ON " +dbname+ ".* TO '" +dbuser+ "'@'localhost'")
            connection.close()

            return 1

        except BaseException, msg:
            mysqlUtilities.deleteDatabase(dbname, dbuser)
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
            return 0

    @staticmethod
    def deleteDatabase(dbname, dbuser):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("DROP DATABASE " + dbname)
            cursor.execute("DROP USER '"+dbuser+"'@'localhost'")
            connection.close()

            return 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[deleteDatabase]")
            return str(msg)

    @staticmethod
    def createDatabaseBackup(databaseName,tempStoragePath):
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            command = 'sudo mysqldump -u root -p'+password+' '+databaseName

            cmd = shlex.split(command)

            with open(tempStoragePath+"/"+databaseName+'.sql', 'w') as f:
                res = subprocess.call(cmd,stdout=f)

            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("Database: "+databaseName + "could not be backed! [createDatabaseBackup]")
                return 0

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabaseBackup]")
            return 0

    @staticmethod
    def restoreDatabaseBackup(databaseName, tempStoragePath,dbPassword):
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]


            command = 'sudo mysql -u root -p' + password + ' ' + databaseName

            cmd = shlex.split(command)


            with open(tempStoragePath + "/" + databaseName + '.sql', 'r') as f:
                res = subprocess.call(cmd, stdin=f)

            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("Could not restore MYSQL database: " +databaseName +"! [restoreDatabaseBackup]")
                return 0

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            passwordCMD = "use mysql;SET PASSWORD FOR '" + databaseName + "'@'localhost' = '" + dbPassword + "';FLUSH PRIVILEGES;"

            cursor.execute(passwordCMD)
            connection.close()

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[restoreDatabaseBackup]")

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

        except BaseException, msg:
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

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0, str(msg)

    @staticmethod
    def getDatabases(virtualHostName):
        try:
            website = Websites.objects.get(domain=virtualHostName)
            return website.databases_set.all()
        except:
            0
