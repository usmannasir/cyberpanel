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

            expectation = "Enter password:"
            securemysql = pexpect.spawn("mysql -u root -p")
            securemysql.expect(expectation)
            securemysql.sendline(password)

            expectation = ["Access denied for user", "Welcome to the MariaDB monitor"]

            index = securemysql.expect(expectation)

            if index == 0:
                return "Wrong root Password"
            else:
                securemysql.sendline("CREATE DATABASE "+dbname+";")

                expectation = ["database exists","Query OK"]
                index = securemysql.expect(expectation)


                if index == 0:
                    return "This database already exists, please choose another name."
                elif index == 1:
                    securemysql.sendline("CREATE USER '" +dbuser+ "'@'localhost' IDENTIFIED BY '"+dbpassword+"';")
                    expectation = ["CREATE USER failed","Query OK"]

                    index = securemysql.expect(expectation)

                    if index == 0:
                        securemysql.sendline("DROP DATABASE IF EXISTS "+dbname+";")
                        return "This user already exists, please choose another user."
                    else:
                        securemysql.sendline("GRANT ALL PRIVILEGES ON " +dbname+ ".* TO '" +dbuser+ "'@'localhost';")
                        expectation = "Query OK"
                        securemysql.expect(expectation)
                        securemysql.sendline("exit")
                        securemysql.wait()
            return 1
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Exception EOF [createDatabase]")
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")

    @staticmethod
    def deleteDatabase(dbname, dbuser):

        try:

            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]


            expectation = "Enter password:"
            securemysql = pexpect.spawn("mysql -u root -p")
            securemysql.expect(expectation)
            securemysql.sendline(password)

            expectation = ["Access denied for user", "Welcome to the MariaDB monitor"]

            index = securemysql.expect(expectation)

            if index == 0:
                return "Wrong root Password"
            else:
                securemysql.sendline("DROP DATABASE IF EXISTS " + dbname + ";")

                expectation = ["Query OK",pexpect.EOF]
                index = securemysql.expect(expectation)

                if index == 0:

                    securemysql.sendline("DROP USER '"+dbuser+"'@'localhost';")

                    securemysql.close()
                    return 1
                else:
                    securemysql.sendline("DROP USER '" + dbuser + "'@'localhost';")
                    securemysql.close()
                    return 1

        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Exception EOF [deleteDatabase]")
            return str(msg)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
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
                logging.CyberCPLogFileWriter.writeToFile("[could not backup]")

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
                logging.CyberCPLogFileWriter.writeToFile("[Could not restore MYSQL Database]")
                return 0

            passwordCMD = "use mysql;SET PASSWORD FOR '"+databaseName+"'@'localhost' = '"+dbPassword+"';FLUSH PRIVILEGES;"

            command = 'sudo mysql -u root -p'+password+' -e "'+passwordCMD+'"'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("[Could not change Password]")
                return 0



            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[restoreDatabaseBackup]")
