
import pexpect
import installLog as logging

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
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [SendQuery]")
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[SendQuery]")


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
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [createDatabase]")
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[createDatabase]")

    @staticmethod
    def createDatabaseCyberPanel(dbname,dbuser,dbpassword):

        try:

            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            expectation = "Enter password:"
            securemysql = pexpect.spawn("mysql --host=127.0.0.1 --port=3307 -u root -p")
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
            logging.InstallLog.writeToFile(str(msg) + " Exception EOF [createDatabase]")
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[createDatabase]")