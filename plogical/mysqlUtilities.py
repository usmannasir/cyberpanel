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


class mysqlUtilities:


    @staticmethod
    def createDatabase(dbname,dbuser,dbpassword):

        try:

            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            createDB = "CREATE DATABASE "+dbname

            command = 'sudo mysql -u root -p' + password + ' -e "' + createDB + '"'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("Can not create Database: " +dbname)
                return 0

            createUser = "CREATE USER '" +dbuser+ "'@'localhost' IDENTIFIED BY '"+dbpassword+"'"

            command = 'sudo mysql -u root -p' + password + ' -e "' + createUser + '"'

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("Can not create Database User: " + dbuser)
                ## reverting the db creation which was created earlier
                mysqlUtilities.deleteDatabase(dbname,dbuser)
                return 0
            else:
                dropDB = "GRANT ALL PRIVILEGES ON " +dbname+ ".* TO '" +dbuser+ "'@'localhost'"
                command = 'sudo mysql -u root -p' + password + ' -e "' + dropDB + '"'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    mysqlUtilities.deleteDatabase(dbname, dbuser)
                    logging.CyberCPLogFileWriter.writeToFile("Can not grant privileges to user: " + dbuser)
                    return 0

            return 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
            return 0

    @staticmethod
    def deleteDatabase(dbname, dbuser):

        try:

            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            dropDB = "DROP DATABASE " + dbname
            command = 'sudo mysql -u root -p' + password + ' -e "' + dropDB + '"'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)


            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("Can not delete Database: " + dbname)
                return 0
            else:
                dropUser = "DROP USER '"+dbuser+"'@'localhost'"
                command = 'sudo mysql -u root -p' + password + ' -e "' + dropUser + '"'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    logging.CyberCPLogFileWriter.writeToFile("Can not delete Database User: " + dbuser)
                    return 0

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
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
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

            passwordCMD = "use mysql;SET PASSWORD FOR '"+databaseName+"'@'localhost' = '"+dbPassword+"';FLUSH PRIVILEGES;"

            command = 'sudo mysql -u root -p'+password+' -e "'+passwordCMD+'"'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("Could not change password for MYSQL user: " + databaseName + "! [restoreDatabaseBackup]")
                return 0

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
