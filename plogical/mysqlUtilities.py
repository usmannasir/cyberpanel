import pexpect
import CyberCPLogFileWriter as logging
import subprocess
import shlex


class mysqlUtilities:

    @staticmethod
    def SendQuery(user, password, dbname, query):
        try:
            expectation = "Enter password:"
            securemysql = pexpect.spawn("mysql -u "+user+" -p")
            securemysql.expect(expectation)
            securemysql.sendline(password)

            expectation = ["Access denied for user", "Welcome to the MariaDB monitor"]
            index = securemysql.expect(expectation)
            if index == 0:
                return "Wrong Password"
            else:

                securemysql.sendline("USE "+dbname+";")
                expectation = "Database changed"
                securemysql.expect(expectation)

                expectation = "Query OK"
                securemysql.sendline(query);
                securemysql.expect(expectation)

                securemysql.sendline("exit");

                securemysql.wait()
                return 1
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Exception EOF [SendQuery]")
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[SendQuery]")


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

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")

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
