import subprocess, shlex
import install
import time

class mysqlUtilities:

    @staticmethod
    def createDatabase(dbname, dbuser, dbpassword):

        try:
            createDB = "CREATE DATABASE " + dbname

            try:
                from json import loads
                mysqlData = loads(open("/etc/cyberpanel/mysqlPassword", 'r').read())


                initCommand = 'mysql -h %s --port %s -u %s -p%s -e "' % (mysqlData['mysqlhost'], mysqlData['mysqlport'], mysqlData['mysqluser'], mysqlData['mysqlpassword'])


            except:
                passFile = "/etc/cyberpanel/mysqlPassword"

                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]

                initCommand = 'mysql -u root -p' + password + ' -e "'

            command = initCommand + createDB + '"'

            if install.preFlightsChecks.debug:
                print(command)
                time.sleep(10)

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                return 0

            createUser = "CREATE USER '" + dbuser + "'@'localhost' IDENTIFIED BY '" + dbpassword + "'"

            command = initCommand + createUser + '"'

            if install.preFlightsChecks.debug:
                print(command)
                time.sleep(10)

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                return 0
            else:
                dropDB = "GRANT ALL PRIVILEGES ON " + dbname + ".* TO '" + dbuser + "'@'localhost'"
                command = initCommand + dropDB + '"'

                if install.preFlightsChecks.debug:
                    print(command)
                    time.sleep(10)

                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    return 0

            return 1
        except BaseException as msg:
            return 0