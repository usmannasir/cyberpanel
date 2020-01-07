import subprocess, shlex

class mysqlUtilities:

    @staticmethod
    def createDatabase(dbname, dbuser, dbpassword):

        try:

            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]

            createDB = "CREATE DATABASE " + dbname

            command = 'mysql -u root -p' + password + ' -e "' + createDB + '"'
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                return 0

            createUser = "CREATE USER '" + dbuser + "'@'localhost' IDENTIFIED BY '" + dbpassword + "'"

            command = 'mysql -u root -p' + password + ' -e "' + createUser + '"'

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                return 0
            else:
                dropDB = "GRANT ALL PRIVILEGES ON " + dbname + ".* TO '" + dbuser + "'@'localhost'"
                command = 'mysql -u root -p' + password + ' -e "' + dropDB + '"'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    return 0

            return 1
        except BaseException as msg:
            return 0