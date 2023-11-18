import subprocess, shlex
import install
import time

class mysqlUtilities:

    @staticmethod
    def createDatabase(dbname, dbuser, dbpassword, publicip):

        try:
            createDB = "CREATE DATABASE " + dbname

            try:
                from json import loads
                mysqlData = loads(open("/etc/cyberpanel/mysqlPassword", 'r').read())

                initCommand = 'mysql -h %s --port %s -u %s -p%s -e "' % (mysqlData['mysqlhost'], mysqlData['mysqlport'], mysqlData['mysqluser'], mysqlData['mysqlpassword'])
                remote = 1
            except:
                passFile = "/etc/cyberpanel/mysqlPassword"

                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]

                initCommand = 'mysql -u root -p' + password + ' -e "'
                remote = 0

            command = initCommand + createDB + '"'

            if install.preFlightsChecks.debug:
                print(command)
                time.sleep(10)

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                return 0

            if remote:
                createUser = "CREATE USER '" + dbuser + "'@'%s' IDENTIFIED BY '" % (publicip) + dbpassword + "'"
            else:
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

                if remote:

                    ### DO Check

                    if mysqlData['mysqlhost'].find('ondigitalocean') > -1:

                        alterUserPassword = "ALTER USER 'cyberpanel'@'%s' IDENTIFIED WITH mysql_native_password BY '%s'" % (
                        publicip, dbpassword)
                        command = initCommand + alterUserPassword + '"'

                        if install.preFlightsChecks.debug:
                            print(command)
                            time.sleep(10)

                        cmd = shlex.split(command)
                        subprocess.call(cmd)

                    ## RDS Check

                    if mysqlData['mysqlhost'].find('rds.amazon') == -1:
                        dropDB = "GRANT ALL PRIVILEGES ON " + dbname + ".* TO '" + dbuser + "'@'%s'" % (publicip)
                    else:
                        dropDB = "GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON " + dbname + ".* TO '" + dbuser + "'@'%s'" % (publicip)
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