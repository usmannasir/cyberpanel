import subprocess, shlex
import install
import time

class mysqlUtilities:

    @staticmethod
    def createDatabase(dbname, dbuser, dbpassword, publicip):
        """
        Create database and user with improved error handling and validation
        """
        import installLog as logging

        # Validate input parameters
        if not dbname or not dbuser or not dbpassword:
            logging.InstallLog.writeToFile(f"ERROR: Missing required parameters - dbname: {dbname}, dbuser: {dbuser}, password: {'SET' if dbpassword else 'EMPTY'}")
            return 0

        logging.InstallLog.writeToFile(f"Creating database '{dbname}' and user '{dbuser}' with password length: {len(dbpassword)}")

        try:
            # Step 1: Create database
            createDB = "CREATE DATABASE IF NOT EXISTS " + dbname

            try:
                from json import loads
                mysqlData = loads(open("/etc/cyberpanel/mysqlPassword", 'r').read())

                initCommand = 'mariadb -h %s --port %s -u %s -p%s -e "' % (mysqlData['mysqlhost'], mysqlData['mysqlport'], mysqlData['mysqluser'], mysqlData['mysqlpassword'])
                remote = 1
                logging.InstallLog.writeToFile("Using remote MySQL configuration")
            except:
                passFile = "/etc/cyberpanel/mysqlPassword"

                try:
                    f = open(passFile)
                    data = f.read()
                    password = data.split('\n', 1)[0]
                    f.close()

                    # Try password-based authentication first
                    initCommand = 'mariadb -u root -p' + password + ' -e "'
                    remote = 0
                    logging.InstallLog.writeToFile("Using local MySQL configuration with password")
                except:
                    # Fallback to socket authentication for fresh MariaDB installs
                    initCommand = 'sudo mariadb -e "'
                    remote = 0
                    logging.InstallLog.writeToFile("Using local MySQL configuration with socket authentication")

            command = initCommand + createDB + '"'

            logging.InstallLog.writeToFile(f"Executing database creation: CREATE DATABASE IF NOT EXISTS {dbname}")

            if hasattr(install, 'preFlightsChecks') and hasattr(install.preFlightsChecks, 'debug') and install.preFlightsChecks.debug:
                print(command)
                time.sleep(10)

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            # If command failed and we're using password auth, try socket auth as fallback
            if res != 0 and not remote and 'sudo' not in initCommand:
                logging.InstallLog.writeToFile(f"Password-based auth failed (code {res}), trying socket authentication...")
                initCommand = 'sudo mariadb -e "'
                command = initCommand + createDB + '"'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

            if res != 0:
                logging.InstallLog.writeToFile(f"ERROR: Database creation failed with return code: {res}")
                return 0
            else:
                logging.InstallLog.writeToFile(f"✓ Database '{dbname}' created successfully")

            # Step 2: Create user (drop first if exists to avoid conflicts)
            if remote:
                dropUser = f"DROP USER IF EXISTS '{dbuser}'@'{publicip}'"
                createUser = f"CREATE USER '{dbuser}'@'{publicip}' IDENTIFIED BY '{dbpassword}'"
                host = publicip
            else:
                dropUser = f"DROP USER IF EXISTS '{dbuser}'@'localhost'"
                createUser = f"CREATE USER '{dbuser}'@'localhost' IDENTIFIED BY '{dbpassword}'"
                host = 'localhost'

            # Drop user if exists
            command = initCommand + dropUser + '"'
            logging.InstallLog.writeToFile(f"Dropping existing user '{dbuser}'@'{host}' if exists")

            if hasattr(install, 'preFlightsChecks') and hasattr(install.preFlightsChecks, 'debug') and install.preFlightsChecks.debug:
                print(command)
                time.sleep(10)

            cmd = shlex.split(command)
            subprocess.call(cmd)  # Ignore return code for DROP USER IF EXISTS

            # Create user
            command = initCommand + createUser + '"'
            logging.InstallLog.writeToFile(f"Creating user '{dbuser}'@'{host}' with password")

            if hasattr(install, 'preFlightsChecks') and hasattr(install.preFlightsChecks, 'debug') and install.preFlightsChecks.debug:
                print(command)
                time.sleep(10)

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            # If user creation failed and we're using password auth, try socket auth as fallback
            if res != 0 and not remote and 'sudo' not in initCommand:
                logging.InstallLog.writeToFile(f"User creation with password failed (code {res}), trying socket authentication...")
                initCommand = 'sudo mariadb -e "'
                command = initCommand + createUser + '"'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

            if res != 0:
                logging.InstallLog.writeToFile(f"ERROR: User creation failed with return code: {res}")
                return 0
            else:
                logging.InstallLog.writeToFile(f"✓ User '{dbuser}'@'{host}' created successfully")

                # Step 3: Handle special cases and grant privileges
                if remote:
                    ### DigitalOcean MySQL compatibility
                    if mysqlData['mysqlhost'].find('ondigitalocean') > -1:
                        alterUserPassword = f"ALTER USER '{dbuser}'@'{publicip}' IDENTIFIED WITH mysql_native_password BY '{dbpassword}'"
                        command = initCommand + alterUserPassword + '"'

                        logging.InstallLog.writeToFile(f"Applying DigitalOcean MySQL compatibility for '{dbuser}'@'{publicip}'")

                        if hasattr(install, 'preFlightsChecks') and hasattr(install.preFlightsChecks, 'debug') and install.preFlightsChecks.debug:
                            print(command)
                            time.sleep(10)

                        cmd = shlex.split(command)
                        res = subprocess.call(cmd)

                        if res != 0:
                            logging.InstallLog.writeToFile(f"WARNING: DigitalOcean ALTER USER failed with return code: {res}")

                    ## RDS vs Standard MySQL permissions
                    if mysqlData['mysqlhost'].find('rds.amazon') == -1:
                        grantPrivileges = f"GRANT ALL PRIVILEGES ON {dbname}.* TO '{dbuser}'@'{publicip}'"
                    else:
                        grantPrivileges = f"GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON {dbname}.* TO '{dbuser}'@'{publicip}'"
                    host = publicip
                else:
                    grantPrivileges = f"GRANT ALL PRIVILEGES ON {dbname}.* TO '{dbuser}'@'localhost'"
                    host = 'localhost'

                # Grant privileges
                command = initCommand + grantPrivileges + '"'
                logging.InstallLog.writeToFile(f"Granting privileges on database '{dbname}' to user '{dbuser}'@'{host}'")

                if hasattr(install, 'preFlightsChecks') and hasattr(install.preFlightsChecks, 'debug') and install.preFlightsChecks.debug:
                    print(command)
                    time.sleep(10)

                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                # If privilege granting failed and we're using password auth, try socket auth as fallback
                if res != 0 and not remote and 'sudo' not in initCommand:
                    logging.InstallLog.writeToFile(f"Grant privileges with password failed (code {res}), trying socket authentication...")
                    initCommand = 'sudo mariadb -e "'
                    command = initCommand + grantPrivileges + '"'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                if res != 0:
                    logging.InstallLog.writeToFile(f"ERROR: Grant privileges failed with return code: {res}")
                    return 0
                else:
                    logging.InstallLog.writeToFile(f"✓ Privileges granted successfully")

                # Step 4: Flush privileges
                flushCommand = initCommand + "FLUSH PRIVILEGES" + '"'
                logging.InstallLog.writeToFile("Flushing MySQL privileges")

                cmd = shlex.split(flushCommand)
                res = subprocess.call(cmd)

                # If flush failed and we're using password auth, try socket auth as fallback
                if res != 0 and not remote and 'sudo' not in initCommand:
                    logging.InstallLog.writeToFile(f"FLUSH PRIVILEGES with password failed (code {res}), trying socket authentication...")
                    flushCommand = 'sudo mariadb -e "FLUSH PRIVILEGES"'
                    cmd = shlex.split(flushCommand)
                    res = subprocess.call(cmd)

                if res != 0:
                    logging.InstallLog.writeToFile(f"WARNING: FLUSH PRIVILEGES failed with return code: {res}")
                else:
                    logging.InstallLog.writeToFile("✓ Privileges flushed successfully")

            logging.InstallLog.writeToFile(f"✅ Database '{dbname}' and user '{dbuser}' created successfully!")
            return 1

        except BaseException as msg:
            logging.InstallLog.writeToFile(f"❌ CRITICAL ERROR in createDatabase: {str(msg)}")
            import traceback
            logging.InstallLog.writeToFile(f"Full traceback: {traceback.format_exc()}")
            return 0