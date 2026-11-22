import os,sys
import shutil
import urllib
from urllib.parse import unquote

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
import getpass
import re
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
from plogical import databaseGrants
from plogical import randomPassword
import MySQLdb.cursors as cursors
from plogical import databaseImport
from math import ceil
import argparse
import pwd

class mysqlUtilities:

    LOCALHOST = 'localhost'
    RDS = 0
    REMOTEHOST = ''

    # The host of a database account as the panel writes it: an address, a
    # name or a pattern with `%`.
    ACCOUNT_HOST = re.compile(r'[A-Za-z0-9_.:%/-]{1,255}')

    @staticmethod
    def quoteIdentifier(identifier):
        # MySQL identifiers (db/table/column names) cannot be passed as bound
        # parameters. Backtick-quote them and double any embedded backtick so a
        # malicious value cannot break out of the identifier into SQL. This
        # preserves every legitimate identifier while neutralising injection.
        if identifier is None:
            raise ValueError("identifier cannot be None")
        return "`" + str(identifier).replace("`", "``") + "`"


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

            try:
                jsonData = json.loads(open(passFile, 'r').read())

                mysqluser = jsonData['mysqluser']
                mysqlpassword = jsonData['mysqlpassword']
                mysqlport = jsonData['mysqlport']
                mysqlhost = jsonData['mysqlhost']
                mysqlUtilities.REMOTEHOST = mysqlhost

                if mysqlhost.find('rds.amazon') > -1:
                    mysqlUtilities.RDS = 1

                ## Also set localhost to this server

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddressLocal = ipData.split('\n', 1)[0]

                mysqlUtilities.LOCALHOST = ipAddressLocal

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('Local IP for MySQL: %s' % (mysqlUtilities.LOCALHOST))

                conn = mysql.connect(host=mysqlhost ,user=mysqluser, passwd=mysqlpassword, port=int(mysqlport), cursorclass=cursors.SSCursor)
                cursor = conn.cursor()

                return conn, cursor

            except BaseException as msg:

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('%s. [setupConnection:75]' % (str(msg)))

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
    def createDatabase(dbname,dbuser,dbpassword, dbcreate = 1, host = None, progress=None):
        connection = None
        record = progress or (lambda stage: None)
        try:
            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            if dbcreate == 1:
                HostToUse = mysqlUtilities.LOCALHOST
            else:
                HostToUse = host

            # In a grant `_` and `%` are wildcards: name this database only.
            grantOn = mysqlUtilities.quoteIdentifier(databaseGrants.grant_name(cursor, dbname))

            ## Create db

            if dbcreate:

                query = "CREATE DATABASE %s" % (
                    mysqlUtilities.quoteIdentifier(dbname))

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(query)

                record('creating_database')
                cursor.execute(query)
                record('database_created')

            ## create user

            def createUserForHost(hostToUse):
                if mysqlUtilities.REMOTEHOST.find('ondigitalocean') > -1:
                    query = "CREATE USER %s@%s IDENTIFIED WITH mysql_native_password BY %s"
                else:
                    query = "CREATE USER %s@%s IDENTIFIED BY %s"

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(query)

                record('creating_user_' + hostToUse)
                cursor.execute(query, (dbuser, hostToUse, dbpassword))
                record('user_created_' + hostToUse)

                if mysqlUtilities.RDS == 0:
                    grant = "GRANT ALL PRIVILEGES ON %s.* TO %%s@%%s" % grantOn
                else:
                    grant = "GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON %s.* TO %%s@%%s" % grantOn
                record('granting_user_' + hostToUse)
                cursor.execute(grant, (dbuser, hostToUse))
                record('user_granted_' + hostToUse)
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(grant)

            createUserForHost(HostToUse)

            if dbcreate == 1 and HostToUse != '127.0.0.1' and mysqlUtilities.REMOTEHOST in ('', 'localhost', '127.0.0.1'):
                try:
                    createUserForHost('127.0.0.1')
                except BaseException as msg:
                    if progress is not None:
                        raise
                    logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDatabase:127.0.0.1]")

            record('sql_ready')
            return 1

        except BaseException as msg:
            if dbcreate:
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('Deleting database because failed to create %s' % (dbname))
                #mysqlUtilities.deleteDatabase(dbname, dbuser)
            logging.CyberCPLogFileWriter.writeToFile('SQL creation failed for %s [createDatabase]' % dbname)
            return 0
        finally:
            if connection:
                connection.close()

    @staticmethod
    def createDBUser(dbuser, dbpassword):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("CREATE DATABASE " + mysqlUtilities.quoteIdentifier(dbuser))
            cursor.execute("CREATE USER %s@%s IDENTIFIED BY %s", (dbuser, mysqlUtilities.LOCALHOST, dbpassword))

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

            grantOn = mysqlUtilities.quoteIdentifier(databaseGrants.grant_name(cursor, dbName))
            if mysqlUtilities.RDS == 0:
                cursor.execute("GRANT ALL PRIVILEGES ON %s.* TO %%s@%%s" % grantOn,
                               (globalUser, mysqlUtilities.LOCALHOST))
            else:
                cursor.execute("GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON %s.* TO %%s@%%s" % grantOn,
                               (globalUser, mysqlUtilities.LOCALHOST))

            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabase]")
            return 0

    @staticmethod
    def deleteDatabase(dbname, dbuser):
        connection = None
        try:

            # Let MySQL manage its data directory. A database name is an SQL
            # identifier, never a filesystem path or part of a shell command.
            # Unexpected files must make DROP fail safely for administrator review.

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("DROP DATABASE IF EXISTS " + mysqlUtilities.quoteIdentifier(dbname))

            ## The accounts that exist for this database alone go with it. Any
            ## other account that was granted this database (the phpMyAdmin
            ## account of a panel user, a user shared with another database)
            ## stays and only loses its grant on the name, so that it has no
            ## access when a database of this name is made again.

            # A grant is stored under the plain name or under its escaped form.
            databaseUsers = databaseGrants.accounts_granted(cursor, dbname)
            ownAccounts = mysqlUtilities.accountsOfDatabaseAlone(dbname, dbuser)

            for databaseUser in databaseUsers:
                if databaseUser[0] in ownAccounts:
                    cursor.execute("DROP USER IF EXISTS %s@%s", (databaseUser[0], databaseUser[1]))
                else:
                    databaseGrants.revoke_database(cursor, mysqlUtilities.quoteIdentifier, dbname,
                                                   databaseUser[0], databaseUser[1])

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[deleteDatabase]")
            return str(msg)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def accountsOfDatabaseAlone(dbname, dbuser):
        """Names of the database accounts that belong to this database and to nothing else.

        They are the user the panel registered for the database (`dbuser`,
        as the caller read it) and its additional registered users, without
        any name that another database is registered with or that a panel
        user signs in to phpMyAdmin with.
        """
        names = set()
        if isinstance(dbuser, str) and dbuser:
            names.add(dbuser)
        try:
            from databases.models import DatabasesUsers, GlobalUserDB
        except BaseException:
            return names
        row = Databases.objects.filter(dbName=dbname).first()
        if row is not None:
            names.add(row.dbUser)
            names.update(DatabasesUsers.objects.filter(owner=row).values_list('username', flat=True))
        others = set(Databases.objects.filter(dbUser__in=names).exclude(dbName=dbname).values_list('dbUser', flat=True))
        additional = DatabasesUsers.objects.filter(username__in=names)
        if row is not None:
            additional = additional.exclude(owner=row)
        others.update(additional.values_list('username', flat=True))
        others.update(GlobalUserDB.objects.filter(username__in=names).values_list('username', flat=True))
        return names - others

    @staticmethod
    def createDatabaseBackup(databaseName, tempStoragePath, rustic=0, RusticRepoName = None,
                           externalApp = None, use_compression=None, use_new_features=None):
        """
        Enhanced database backup with backward compatibility

        Parameters:
        - use_compression: None (auto-detect), True (force compression), False (no compression)
        - use_new_features: None (auto-detect based on config), True/False (force)
        """
        try:
            # The name becomes part of file names and of command lines.
            if not mysqlUtilities.usableInCommands(databaseName):
                logging.CyberCPLogFileWriter.writeToFile(
                    'A database with this name cannot be backed up. [createDatabaseBackup]')
                return 0

            # Check if new features are enabled (via config file or parameter)
            if use_new_features is None:
                use_new_features = mysqlUtilities.checkNewBackupFeatures()

            # Determine compression based on config or parameter
            if use_compression is None:
                use_compression = mysqlUtilities.shouldUseCompression()

            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(open(passFile, 'r').read())

                mysqluser = jsonData['mysqluser']
                mysqlpassword = jsonData['mysqlpassword']
                mysqlport = jsonData['mysqlport']
                mysqlhost = jsonData['mysqlhost']
                password = mysqlpassword
            except:
                passFile = "/etc/cyberpanel/mysqlPassword"
                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]
                mysqlhost = 'localhost'
                mysqlport = '3306'
                mysqluser = 'root'


            cnfPath = '/home/cyberpanel/.my.cnf'

            if not os.path.exists(cnfPath):
                mysqlUtilities.writeClientDefaults(cnfPath, password)

            SHELL = False

            if rustic == 0:
                # Determine backup file extension based on compression
                if use_compression:
                    backup_extension = '.sql.gz'
                    backup_file = f"{tempStoragePath}/{databaseName}{backup_extension}"
                else:
                    backup_extension = '.sql'
                    backup_file = f"{tempStoragePath}/{databaseName}{backup_extension}"

                # Remove old backup if exists
                command = f'rm -f {shlex.quote(backup_file)}'
                ProcessUtilities.executioner(command)

                # Build mysqldump command with new features
                dump_cmd = mysqlUtilities.buildMysqldumpCommand(
                    mysqluser, mysqlhost, mysqlport, databaseName,
                    use_new_features, use_compression
                )

                if use_compression:
                    # New method: Stream directly to compressed file
                    # The dump holds the customer's data: nobody else may read it.
                    full_command = f"umask 077; {dump_cmd} | gzip -c > {shlex.quote(backup_file)}"
                    result = ProcessUtilities.executioner(full_command, shell=True)
                    # The panel's own account reads it back on a restore.
                    ProcessUtilities.executioner(f'chown cyberpanel:cyberpanel {shlex.quote(backup_file)}')

                    # Verify backup file was created successfully
                    if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
                        logging.CyberCPLogFileWriter.writeToFile(
                            f"Database: {databaseName} could not be backed up (compressed)! [createDatabaseBackup]"
                        )
                        return 0
                else:
                    # Legacy method: Direct dump to file (backward compatible)
                    cmd = shlex.split(dump_cmd)

                    # The dump holds the customer's data: it is private from
                    # the moment it exists and never written into a file that
                    # was already there.
                    descriptor = os.open(backup_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    with os.fdopen(descriptor, 'w') as f:
                        mysqlUtilities.keepForPanelAccount(descriptor)
                        result = subprocess.run(
                            cmd,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            shell=SHELL
                        )

                        if result.returncode != 0:
                            logging.CyberCPLogFileWriter.writeToFile(
                                "Database: " + databaseName + " could not be backed up! [createDatabaseBackup]"
                            )
                            logging.CyberCPLogFileWriter.writeToFile(result.stderr.decode('utf-8'))
                            return 0

                # Store metadata about backup format for restore
                mysqlUtilities.saveBackupMetadata(
                    databaseName, tempStoragePath, use_compression, use_new_features
                )

            else:
                SHELL = True

                command = f'mysqldump --defaults-file=/home/cyberpanel/.my.cnf -u {mysqluser} --host={mysqlhost} --port {mysqlport} --add-drop-table --allow-keywords --complete-insert --quote-names --skip-comments {shlex.quote(databaseName)} 2>/dev/null | sudo -u {externalApp} rustic -r {RusticRepoName} backup --stdin-filename {shlex.quote(databaseName + ".sql")} - --password "" --json 2>/dev/null'

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(command)

                result = json.loads(
                    ProcessUtilities.outputExecutioner(command, None, True).rstrip('\n'))

                try:
                    SnapShotID = result['id']  ## snapshot id that we need to store in db
                    files_new = result['summary']['files_new']  ## basically new files in backup
                    total_duration = result['summary']['total_duration']  ## time taken

                    return 1, SnapShotID

                except BaseException as msg:
                    return 0, str(msg)



            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[createDatabaseBackup]")
            return 0

    @staticmethod
    def usableInCommands(databaseName):
        """True for a database name that may become a file name and an argument of the dump programs."""
        return (isinstance(databaseName, str) and 0 < len(databaseName) <= 64
                and not databaseName.startswith('-') and databaseName not in ('.', '..')
                and '/' not in databaseName and '\x00' not in databaseName and '\n' not in databaseName)

    @staticmethod
    def writeClientDefaults(cnfPath, password):
        """Write the option file of the panel's dump program; nobody else can read it at any moment."""
        cnfContent = """[mysqldump]
user=root
password=%s
max_allowed_packet=1024M
[mysql]
user=root
password=%s
""" % (password, password)
        descriptor = os.open(cnfPath, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'w') as writeToFile:
            mysqlUtilities.keepForPanelAccount(descriptor)
            writeToFile.write(cnfContent)

    @staticmethod
    def keepForPanelAccount(descriptor):
        """Make an open file readable by its owner alone; one that root made goes to the panel's account.

        The panel's own account makes and reads these files as well as root,
        and no other account has any business with them.
        """
        os.fchmod(descriptor, 0o600)
        if os.geteuid() == 0:
            try:
                owner = pwd.getpwnam('cyberpanel')
                os.fchown(descriptor, owner.pw_uid, owner.pw_gid)
            except KeyError:
                pass

    @staticmethod
    def restoreRusticDatabase(databaseName, rusticRepoName, externalApp,
                              snapshotid, mysqluser, mysqlhost, mysqlport):
        try:
            repository = shlex.split(rusticRepoName or '')
            if len(repository) != 1:
                return 0

            dumpCommand = [
                'sudo', '-u', externalApp, 'rustic', '-r', repository[0],
                'dump', '%s:%s.sql' % (snapshotid, databaseName),
                '--password', '',
            ]

            def feed(sink):
                if getpass.getuser() != 'root':
                    # The panel's own account may not switch to the website's
                    # account. The helper runs the dump as that account and its
                    # output goes to the import as it arrives.
                    return ProcessUtilities.streamCommand(
                        'rustic -r %s dump %s --password "" 2>/dev/null' % (
                            shlex.quote(repository[0]),
                            shlex.quote('%s:%s.sql' % (snapshotid, databaseName))),
                        externalApp, sink)
                dumpProcess = subprocess.Popen(
                    dumpCommand, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                try:
                    databaseImport.copy(dumpProcess.stdout, sink)
                finally:
                    dumpProcess.stdout.close()
                    dumpProcess.wait()
                return dumpProcess.returncode == 0

            # The dump comes from a repository the website's account can write
            # to: it is loaded by an account that may use this database only.
            if databaseImport.import_dump(databaseName, feed, mysqlhost, mysqlport,
                                          mysqlUtilities.registeredUser(databaseName)) == 1:
                return 1
            logging.CyberCPLogFileWriter.writeToFile(
                'Rustic database restore failed for %s.' % databaseName)
            return 0
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + '[restoreRusticDatabase]')
            return 0

    @staticmethod
    def restoreDatabaseBackup(databaseName, tempStoragePath, dbPassword, passwordCheck = None, additionalName = None, rustic=0, RusticRepoName = None, externalApp = None, snapshotid = None):
        """
        Enhanced restore with automatic format detection
        """
        try:
            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(open(passFile, 'r').read())

                mysqluser = jsonData['mysqluser']
                mysqlpassword = jsonData['mysqlpassword']
                mysqlport = jsonData['mysqlport']
                mysqlhost = jsonData['mysqlhost']
                password = mysqlpassword
            except:
                passFile = "/etc/cyberpanel/mysqlPassword"
                f = open(passFile)
                data = f.read()
                password = data.split('\n', 1)[0]
                mysqlhost = 'localhost'
                mysqlport = '3306'
                mysqluser = 'root'

            if rustic == 0:
                # Auto-detect backup format
                backup_format = mysqlUtilities.detectBackupFormat(
                    tempStoragePath, databaseName, additionalName
                )

                if additionalName:
                    base_name = additionalName
                else:
                    base_name = databaseName

                # Determine actual backup file based on detected format
                if backup_format['compressed']:
                    backup_file = f"{tempStoragePath}/{base_name}.sql.gz"
                    if not os.path.exists(backup_file):
                        # Fallback to uncompressed for backward compatibility
                        backup_file = f"{tempStoragePath}/{base_name}.sql"
                        backup_format['compressed'] = False
                else:
                    backup_file = f"{tempStoragePath}/{base_name}.sql"
                    if not os.path.exists(backup_file):
                        # Try compressed version
                        backup_file = f"{tempStoragePath}/{base_name}.sql.gz"
                        if os.path.exists(backup_file):
                            backup_format['compressed'] = True

                if not os.path.exists(backup_file):
                    logging.CyberCPLogFileWriter.writeToFile(
                        f"Backup file not found: {backup_file}"
                    )
                    return 0

                def feed(sink):
                    if backup_format['compressed']:
                        decompress = subprocess.Popen(['gunzip', '-c', backup_file], stdout=subprocess.PIPE,
                                                      stderr=subprocess.DEVNULL)
                        try:
                            databaseImport.copy(decompress.stdout, sink)
                        finally:
                            decompress.stdout.close()
                            decompress.wait()
                        return decompress.returncode == 0
                    with open(backup_file, 'rb') as stream:
                        return databaseImport.copy(stream, sink)

                # The dump comes out of an archive somebody else made: it is
                # loaded by an account that may use this database only.
                registered = mysqlUtilities.registeredUser(databaseName)
                if databaseImport.import_dump(databaseName, feed, mysqlhost, mysqlport, registered) != 1:
                    logging.CyberCPLogFileWriter.writeToFile('Database import failed for %s.' % databaseName)
                    return 0

                if passwordCheck == None:
                    # An archive of the old format holds the password hash of
                    # the database's one user, which is the registered user.
                    if registered is None or mysqlUtilities.changePassword(registered, dbPassword, 1) != 1:
                        logging.CyberCPLogFileWriter.writeToFile(
                            'The password of the user of %s was not restored.' % databaseName)
                        return 0

                return 1
            else:
                return mysqlUtilities.restoreRusticDatabase(
                    databaseName, RusticRepoName, externalApp, snapshotid,
                    mysqluser, mysqlhost, mysqlport,
                )

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[restoreDatabaseBackup]")
            return 0

    @staticmethod
    def registeredUser(databaseName):
        """The user the panel registered for this database, or None."""
        try:
            return Databases.objects.get(dbName=databaseName).dbUser
        except BaseException:
            return None

    @staticmethod
    def databaseNamesExist(dbName, dbUsername):
        connection, cursor = mysqlUtilities.setupConnection()
        if connection == 0:
            raise RuntimeError('Cannot check the SQL namespace.')
        try:
            cursor.execute('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s', (dbName,))
            database_exists = bool(cursor.fetchall())
            cursor.execute('SELECT User, Host FROM mysql.user WHERE User = %s', (dbUsername,))
            return database_exists or bool(cursor.fetchall())
        finally:
            connection.close()

    @staticmethod
    def prepareDatabaseForRestore(dbName, dbUsername, website):
        existing = Databases.objects.filter(dbName=dbName).first()
        if existing is None:
            # The password of the restored user is set from the backup right
            # after; until then nobody knows the one the account starts with.
            return mysqlUtilities.createDatabaseAndRegister(dbName, dbUsername, randomPassword.generate_pass(32),
                                                            website)
        if existing.website_id != website.pk or existing.dbUser != dbUsername:
            return 0, 'Database registration belongs to another website or user; existing data was preserved.'
        connection, cursor = mysqlUtilities.setupConnection()
        if connection == 0:
            return 0, 'Cannot verify the registered SQL database.'
        try:
            cursor.execute('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s', (dbName,))
            if not cursor.fetchall():
                return 0, 'Panel registration exists but the SQL database is missing; administrator review is required.'
            return 1, 'None'
        finally:
            connection.close()

    @staticmethod
    def isRegisteredAccount(dbName, dbUser):
        """True when the panel registered this account name for this database and for nothing else.

        The account a panel user signs in to phpMyAdmin with is granted many
        databases and is never one database's own account.
        """
        try:
            from databases.models import DatabasesUsers, GlobalUserDB
            database = Databases.objects.get(dbName=dbName)
            names = set([database.dbUser])
            names.update(DatabasesUsers.objects.filter(owner=database).values_list('username', flat=True))
            if dbUser not in names:
                return False
            return not GlobalUserDB.objects.filter(username__iexact=dbUser).exists()
        except BaseException:
            return False

    @staticmethod
    def restoreDatabaseUser(dbName, dbUser, password, dbHost):
        # A backup lists every account that had a grant on the database when it
        # was made. Only the accounts registered for this database are restored;
        # any other account is left exactly as it is on this server.
        if not isinstance(dbUser, str) or not isinstance(dbHost, str) \
                or not mysqlUtilities.ACCOUNT_HOST.fullmatch(dbHost):
            logging.CyberCPLogFileWriter.writeToFile(
                'A database account of %s was not restored: its host is not valid.' % dbName)
            return 0
        if not mysqlUtilities.isRegisteredAccount(dbName, dbUser):
            logging.CyberCPLogFileWriter.writeToFile(
                'The account %s listed in the backup of %s is not a registered user of that database and was '
                'left as it is.' % (dbUser, dbName))
            return 1
        # Reuse an existing account only when it already has this database grant.
        connection, cursor = mysqlUtilities.setupConnection()
        if connection == 0:
            return 0
        try:
            cursor.execute('SELECT User FROM mysql.user WHERE User = %s AND Host = %s', (dbUser, dbHost))
            exists = bool(cursor.fetchall())
            if exists and not databaseGrants.account_is_granted(cursor, dbName, dbUser, dbHost):
                return 0
        finally:
            connection.close()
        # A new account starts with a password nobody knows; the one from the
        # backup is set in the next step.
        if not exists and mysqlUtilities.createDatabase(dbName, dbUser, randomPassword.generate_pass(32), 0,
                                                        dbHost) != 1:
            return 0
        return mysqlUtilities.changePassword(dbUser, password, 1, dbHost)

    @staticmethod
    def createDatabaseAndRegister(dbName, dbUsername, dbPassword, website):
        from plogical.databaseProvisioning import create_and_register
        return create_and_register(dbName, dbUsername, dbPassword, website, mysqlUtilities, Databases)

    @staticmethod
    def submitDBCreation(dbName, dbUsername, dbPassword, databaseWebsite):
        try:

            if len(dbName) > 32 or len(dbUsername) > 32:
                raise BaseException("Length of Database name or Database user should be 32 at max.")

            website = Websites.objects.get(domain=databaseWebsite)

            if website.package.dataBases == 0:
                pass
            elif website.package.dataBases > website.databases_set.all().count():
                pass
            else:
                raise BaseException("Maximum database limit reached for this website.")

            if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(dbUser=dbUsername).exists():
                raise BaseException("This database or user is already taken.")

            return mysqlUtilities.createDatabaseAndRegister(dbName, dbUsername, dbPassword, website)

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
                logging.CyberCPLogFileWriter.writeToFile('Database deletion failed. Error: %s' % (result))
                return 0, str(result)

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo mv /etc/my.cnf /etc/my.cnf.bak'
                decoded_content = urllib.parse.unquote(data['suggestedContent'])
                data['suggestedContent'] = decoded_content.replace('/var/lib/mysql/mysql.sock',
                                                                   '/var/run/mysqld/mysqld.sock')
            else:
                command = 'sudo mv /etc/mysql/my.cnf /etc/mysql/my.cnf.bak'
                decoded_content = urllib.parse.unquote(data['suggestedContent'])
                data['suggestedContent'] = decoded_content.replace('/var/lib/mysql/mysql.sock', '/var/run/mysqld/mysqld.sock')


            ProcessUtilities.executioner(command)

            ## Temp

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            writeToFile = open(tempPath, 'w')
            writeToFile.write(data['suggestedContent'])
            writeToFile.close()

            ##
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo mv ' + tempPath + ' /etc/my.cnf'
            else:
                command = 'sudo mv ' + tempPath + ' /etc/mysql/my.cnf'

            ProcessUtilities.executioner(command)

            return 1, None

        except BaseException as msg:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
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
            command = 'sudo systemctl restart mariadb'
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
                if items[0] == 'information_schema' or items[0] == 'mysql' or items[0] == 'performance_schema':
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

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
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

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
            cursor.execute("DROP TABLE " + mysqlUtilities.quoteIdentifier(name['tableName']))

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

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
            cursor.execute("select count(*) from " + mysqlUtilities.quoteIdentifier(name['tableName']))
            rows = cursor.fetchall()[0][0]


            ##

            cursor.execute("desc " + mysqlUtilities.quoteIdentifier(name['tableName']))
            result = cursor.fetchall()

            data['completeData'] = '<thead><tr>'

            for items in result:
                data['completeData'] = data['completeData'] + '<th>' + items[0] + '</th>'

            data['completeData'] = data['completeData'] + '</tr></thead>'

            data['completeData'] = data['completeData'] + '<tbody>'

            ##

            data['pagination'] = mysqlUtilities.getPagination(rows, recordsToShow)
            endPageNumber, finalPageNumber = mysqlUtilities.recordsPointer(page, recordsToShow)

            cursor.execute("select * from " + mysqlUtilities.quoteIdentifier(name['tableName']))
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

            cursor.execute("use " + mysqlUtilities.quoteIdentifier(name['databaseName']))
            cursor.execute("desc " + mysqlUtilities.quoteIdentifier(name['tableName']))
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
    def changePassword(userName, dbPassword, encrypt = None, host = None):
        try:

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            cursor.execute("use mysql")

            if host != None:
                LOCALHOST = host
            else:
                LOCALHOST = mysqlUtilities.LOCALHOST

            if encrypt == None:
                query = "ALTER USER %s@%s IDENTIFIED BY %s"
                queryArgs = (userName, LOCALHOST, dbPassword)
            else:
                query = "SET PASSWORD FOR %s@%s = %s"
                queryArgs = (userName, LOCALHOST, dbPassword)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(query)

            cursor.execute(query, queryArgs)

            if LOCALHOST != '127.0.0.1' and mysqlUtilities.REMOTEHOST in ('', 'localhost', '127.0.0.1'):
                try:
                    if encrypt == None:
                        query = "ALTER USER %s@%s IDENTIFIED BY %s"
                    else:
                        query = "SET PASSWORD FOR %s@%s = %s"

                    queryArgs = (userName, '127.0.0.1', dbPassword)

                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.CyberCPLogFileWriter.writeToFile(query)

                    cursor.execute(query, queryArgs)
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        str(msg) + " [mysqlUtilities.changePassword:127.0.0.1]")

            connection.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[mysqlUtilities.changePassword]")
            return 0

    @staticmethod
    def fetchuser(databaseName):
        try:
            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            try:
                database = Databases.objects.get(dbName=databaseName)
                users = [user for user, host in databaseGrants.accounts_granted(cursor, databaseName)]
            finally:
                connection.close()

            # The registered user stays the database's user while it has its grant.
            if database.dbUser in users:
                return database.dbUser

            for user in users:
                if user.find('_') > -1:
                    database.dbUser = user
                    database.save()
                    message = 'Detected databaser user is %s for database %s.' % (user, databaseName)
                    logging.CyberCPLogFileWriter.writeToFile(message)
                    return user

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[mysqlUtilities.fetchuser]")
            return 0

    @staticmethod
    def allowRemoteAccess(dbName, userName, remoteIP):
        try:

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mysqlUtilities.py enableRemoteMYSQL"
            ProcessUtilities.executioner(execPath)

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[mysqlUtilities.allowRemoteAccess]")
            return 0

    @staticmethod
    def enableRemoteMYSQL():
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20 or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                cnfPath = '/etc/mysql/my.cnf'
            else:
                cnfPath = '/etc/my.cnf'

            data = open(cnfPath, 'r').read()

            if data.find('bind-address'):
                print('1,None')
                return 1
            else:
                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddressLocal = ipData.split('\n', 1)[0]

                mysqldContent = '''
[mysqld] 
bind-address=%s
''' % (ipAddressLocal)

                writeToFile = open(cnfPath, 'a')
                writeToFile.write(mysqldContent)
                writeToFile.close()

                print('1,None')

                from time import sleep
                sleep(5)
                ProcessUtilities.popenExecutioner('systemctl restart mariadb')
                return 1

        except BaseException as msg:
            print('0,%s "[mysqlUtilities.enableRemoteMYSQL]' % (str(msg)))
            return 0

    @staticmethod
    def addUserToDB(database, user, password, createUser = 0):
        connection = None
        try:
            from plogical import databaseAccounts

            # Only the account phpMyAdmin uses for a panel user is created or granted here.
            if not databaseAccounts.is_phpmyadmin_account(user):
                logging.CyberCPLogFileWriter.writeToFile('Not a phpMyAdmin account. [addUserToDB]')
                return 0

            connection, cursor = mysqlUtilities.setupConnection()

            if connection == 0:
                return 0

            if createUser:
                databaseAccounts.prepare_phpmyadmin_account(cursor, user, mysqlUtilities.LOCALHOST, password)
                return 1

            grantOn = mysqlUtilities.quoteIdentifier(databaseGrants.grant_name(cursor, database))
            if mysqlUtilities.RDS == 0:
                cursor.execute(
                    "GRANT ALL PRIVILEGES ON %s.* TO %%s@%%s" % grantOn, (user, mysqlUtilities.LOCALHOST))
            else:
                cursor.execute(
                    "GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON %s.* TO %%s@%%s" % grantOn,
                    (user, mysqlUtilities.LOCALHOST))

            return 1

        except BaseException as msg:
            # The message of the driver can repeat the statement, which holds the password.
            if isinstance(msg, ValueError):
                detail = str(msg)
            else:
                detail = msg.args[0] if msg.args and isinstance(msg.args[0], int) else ''
            logging.CyberCPLogFileWriter.writeToFile('%s %s [addUserToDB]' % (type(msg).__name__, detail))
            return 0
        finally:
            if connection:
                connection.close()

    @staticmethod
    def UpgradeMariaDB(versionToInstall, tempStatusPath):

        ### first check if provided version is already installed

        command = 'mysql --version'
        result = ProcessUtilities.outputExecutioner(command)

        if result.find(versionToInstall) > -1:
            print(f'MySQL is already {result}. [200]')
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, f'MySQL is already {result}. [200]')
            return 0

        logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Creating backup of MySQL..,10')

        MySQLBackupDir = '/var/lib/mysql-backupcp'

        from os import getuid
        if getuid() != 0:
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'This function should run as root. [404]')
            return 0, 'This function should run as root.'


        if not os.path.exists(MySQLBackupDir):
            command = 'rsync -av /var/lib/mysql/ /var/lib/mysql-backupcp/'
            ProcessUtilities.executioner(command)

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'MySQL backup created..,20')

        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:

            CNFCurrentPath = '/etc/mysql/ '
            CNFBackupPath = '/etc/cnfbackup/'

            command = f'rsync -av {CNFCurrentPath} {CNFBackupPath}'
            ProcessUtilities.executioner(command)

            command = 'sudo apt-get remove --purge mariadb-server mariadb-client galera -y && sudo apt autoremove -y'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'apt-get install apt-transport-https curl -y'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'mkdir -p /etc/apt/keyrings '
            ProcessUtilities.executioner(command, 'root', True)

            command = "curl -o /etc/apt/keyrings/mariadb-keyring.pgp 'https://mariadb.org/mariadb_release_signing_key.pgp'"
            ProcessUtilities.executioner(command, 'root', True)

            RepoPath = '/etc/apt/sources.list.d/mariadb.sources'
            RepoContent = f"""
# MariaDB {versionToInstall} repository list - created 2023-12-11 07:53 UTC
# https://mariadb.org/download/
X-Repolib-Name: MariaDB
Types: deb
# deb.mariadb.org is a dynamic mirror if your preferred mirror goes offline. See https://mariadb.org/mirrorbits/ for details.
# URIs: https://deb.mariadb.org/{versionToInstall}/ubuntu
URIs: https://mirrors.gigenet.com/mariadb/repo/{versionToInstall}/ubuntu
Suites: jammy
Components: main main/debug
Signed-By: /etc/apt/keyrings/mariadb-keyring.pgp
"""

            WriteToFile = open(RepoPath, 'w')
            WriteToFile.write(RepoContent)
            WriteToFile.close()

            command = 'apt-get update -y'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'DEBIAN_FRONTEND=noninteractive sudo apt-get install mariadb-server -y'
            ProcessUtilities.executioner(command, 'root', True)


        else:
            CNFCurrentPath = '/etc/my.cnf.d/ '
            CNFBackupPath = '/etc/cnfbackup/'

            command = f'rsync -av {CNFCurrentPath} {CNFBackupPath}'
            ProcessUtilities.executioner(command)

            if os.path.exists('/etc/my.cnf'):
                shutil.copy('/etc/my.cnf', f'{CNFBackupPath}/my.cnf')

            command = 'yum remove mariadb* -y'
            ProcessUtilities.executioner(command, 'root', True)


            RepoPath = '/etc/yum.repos.d/mariadb.repo'
            RepoContent = f"""
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/{versionToInstall}/rhel8-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1            
"""

            WriteToFile = open(RepoPath, 'w')
            WriteToFile.write(RepoContent)
            WriteToFile.close()


            command = 'dnf update -y'
            result = ProcessUtilities.outputExecutioner(command, 'root', True)

            print(result)

            command = 'dnf install mariadb-server -y'
            result = ProcessUtilities.outputExecutioner(command, 'root', True)

            print(result)

            command = 'systemctl start mariadb && systemctl enable mariadb'
            result = ProcessUtilities.outputExecutioner(command, 'root', True)

            print(result)


        logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Completed [200]')

    @staticmethod
    def buildMysqldumpCommand(user, host, port, database, use_new_features, use_compression):
        """Build mysqldump command with appropriate options"""

        base_cmd = f"mysqldump --defaults-file=/home/cyberpanel/.my.cnf -u {user} --host={host} --port {port}"

        # Add new performance features if enabled
        if use_new_features:
            # Add single-transaction for InnoDB consistency
            base_cmd += " --single-transaction"

            # Add extended insert for better performance
            base_cmd += " --extended-insert"

            # Add order by primary for consistent dumps
            base_cmd += " --order-by-primary"

            # Add quick option to avoid loading entire result set
            base_cmd += " --quick"

            # Add lock tables option
            base_cmd += " --lock-tables=false"

            # Check MySQL version for parallel support
            if mysqlUtilities.supportParallelDump():
                # Get number of threads (max 4 for safety)
                threads = min(4, ProcessUtilities.getNumberOfCores() if hasattr(ProcessUtilities, 'getNumberOfCores') else 2)
                base_cmd += f" --parallel={threads}"

        base_cmd += f" {shlex.quote(database)}"
        return base_cmd

    @staticmethod
    def saveBackupMetadata(database, path, compressed, new_features):
        """Save metadata about backup format for restore compatibility"""
        import time

        metadata = {
            'database': database,
            'compressed': compressed,
            'new_features': new_features,
            'backup_version': '2.0' if new_features else '1.0',
            'timestamp': time.time()
        }

        metadata_file = f"{path}/{database}.backup.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

    @staticmethod
    def detectBackupFormat(path, database, additional_name=None):
        """
        Detect backup format from metadata or file extension
        """
        base_name = additional_name if additional_name else database

        # First try to read metadata file (new backups will have this)
        metadata_file = f"{path}/{base_name}.backup.json"
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        # Fallback: detect by file existence and extension
        format_info = {
            'compressed': False,
            'new_features': False,
            'backup_version': '1.0'
        }

        # Check for compressed file
        if os.path.exists(f"{path}/{base_name}.sql.gz"):
            format_info['compressed'] = True
            # Compressed backups likely use new features
            format_info['new_features'] = True
            format_info['backup_version'] = '2.0'
        elif os.path.exists(f"{path}/{base_name}.sql"):
            format_info['compressed'] = False
            # Check file content for new features indicators
            format_info['new_features'] = mysqlUtilities.checkSQLFileFeatures(
                f"{path}/{base_name}.sql"
            )

        return format_info

    @staticmethod
    def checkNewBackupFeatures():
        """Check if new backup features are enabled"""
        try:
            config_file = '/usr/local/CyberCP/plogical/backup_config.json'
            if not os.path.exists(config_file):
                # Try alternate location
                config_file = '/etc/cyberpanel/backup_config.json'

            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('database_backup', {}).get('use_new_features', False)
        except:
            pass
        return False  # Default to legacy mode for safety

    @staticmethod
    def shouldUseCompression():
        """Check if compression should be used"""
        try:
            config_file = '/usr/local/CyberCP/plogical/backup_config.json'
            if not os.path.exists(config_file):
                # Try alternate location
                config_file = '/etc/cyberpanel/backup_config.json'

            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('database_backup', {}).get('use_compression', False)
        except:
            pass
        return False  # Default to no compression for compatibility

    @staticmethod
    def supportParallelDump():
        """Check if MySQL version supports parallel dump"""
        try:
            result = ProcessUtilities.outputExecutioner("mysql --version")
            # MySQL 8.0+ and MariaDB 10.3+ support parallel dump
            if "8.0" in result or "8.1" in result or "10.3" in result or "10.4" in result or "10.5" in result or "10.6" in result:
                return True
        except:
            pass
        return False

    @staticmethod
    def checkSQLFileFeatures(file_path):
        """Check SQL file for new feature indicators"""
        try:
            # Read first few lines to check for new features
            with open(file_path, 'r') as f:
                head = f.read(2048)  # Read first 2KB
                # Check for indicators of new features
                if "--single-transaction" in head or "--extended-insert" in head or "-- Dump completed" in head:
                    return True
        except:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description='CyberPanel')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--version', help='MySQL version to upgrade to.')
    parser.add_argument('--tempStatusPath', help='MySQL version to upgrade to.')

    args = parser.parse_args()


    if args.function == "enableRemoteMYSQL":
        mysqlUtilities.enableRemoteMYSQL()
    elif args.function == "UpgradeMariaDB":
        mysqlUtilities.UpgradeMariaDB(args.version, args.tempStatusPath)


if __name__ == "__main__":
    main()
