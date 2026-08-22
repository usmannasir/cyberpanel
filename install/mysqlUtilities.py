import subprocess, shlex
import install
import re
import time


# MySQL identifiers we create ourselves. Anything outside this shape is
# refused rather than interpolated into a statement.
_IDENTIFIER = re.compile(r'^[A-Za-z0-9_]{1,64}$')


class MySQLSetupError(Exception):
    """Raised when the installation database cannot be prepared."""


class mysqlUtilities:

    @staticmethod
    def _load_admin_connection():
        """Return (params, remote) for the administrative connection.

        Remote installations store a JSON document written by
        installCyberPanel.Main(); local ones store the root password on the
        first line of the same file.
        """
        pass_file = "/etc/cyberpanel/mysqlPassword"
        try:
            with open(pass_file, 'r') as handle:
                raw = handle.read()
        except (IOError, OSError) as e:
            raise MySQLSetupError(
                "Cannot read %s: %s" % (pass_file, e))

        from json import loads
        try:
            data = loads(raw)
        except ValueError as e:
            # A JSON-looking file was written for a remote install. Treating a
            # damaged document as a local root password silently redirects the
            # administrative connection to localhost.
            if raw.lstrip().startswith(('{', '[')):
                raise MySQLSetupError(
                    "Invalid remote MySQL configuration in %s: %s"
                    % (pass_file, e))
            # Not JSON: the local-install format, root password on line one.
            password = raw.split('\n', 1)[0]
            return {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'passwd': password,
            }, 0

        if not isinstance(data, dict):
            # A local password can itself be valid JSON (for example, "123").
            # Only a JSON object represents the remote-install format.
            return {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'passwd': raw.split('\n', 1)[0],
            }, 0

        try:
            params = {
                'host': data['mysqlhost'],
                'port': int(data['mysqlport']),
                'user': data['mysqluser'],
                'passwd': data['mysqlpassword'],
            }
        except (KeyError, TypeError, ValueError) as e:
            raise MySQLSetupError(
                "Invalid remote MySQL configuration in %s: %s"
                % (pass_file, e))
        return params, 1

    @staticmethod
    def _connect(params):
        """Open the administrative connection, or say precisely why not.

        Credentials are passed as connection arguments, never on a command
        line where `ps` and the debug output would expose them.
        """
        try:
            import MySQLdb
        except ImportError as e:
            raise MySQLSetupError(
                "The MySQL client library is unavailable (%s). It is listed "
                "in requirments.txt and must be installed into the CyberPanel "
                "virtual environment before the database can be prepared." % e)
        try:
            return MySQLdb.connect(connect_timeout=15, **params)
        except Exception as e:
            raise MySQLSetupError(
                "Cannot connect to MySQL at %s:%s as '%s': %s"
                % (params['host'], params['port'], params['user'], e))

    @staticmethod
    def createDatabase(dbname, dbuser, dbpassword, publicip):
        """Create the CyberPanel database and its application account.

        Returns 1 on success and 0 on failure, as before, but a failure is
        now logged with the reason. Previously every exception was swallowed
        and the caller ignored the result, so an unusable administrative
        connection produced no database, no account and no message — the
        installation carried on and failed several steps later at
        `manage.py migrate` against an account that had never been created.
        """
        try:
            if not _IDENTIFIER.match(dbname):
                raise MySQLSetupError("Refusing unsafe database name: %r" % dbname)
            if not _IDENTIFIER.match(dbuser):
                raise MySQLSetupError("Refusing unsafe database user: %r" % dbuser)

            params, remote = mysqlUtilities._load_admin_connection()
            host = params['host']
            connection = mysqlUtilities._connect(params)

            # A remote installation must reach this server from the panel's
            # public address; a local one only ever connects over the socket.
            account_host = publicip if remote else 'localhost'

            cursor = connection.cursor()
            try:
                cursor.execute("CREATE DATABASE IF NOT EXISTS `%s`" % dbname)

                cursor.execute(
                    "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                    (dbuser, account_host, dbpassword))

                if remote:
                    # A retry generates a new application password. CREATE USER
                    # IF NOT EXISTS leaves an existing account unchanged, so
                    # explicitly synchronize it with the value written to .env.
                    # DigitalOcean also needs the legacy authentication plugin
                    # for the client version shipped with CyberPanel.
                    if host.find('ondigitalocean') > -1:
                        cursor.execute(
                            "ALTER USER %s@%s IDENTIFIED WITH "
                            "mysql_native_password BY %s",
                            (dbuser, account_host, dbpassword))
                    else:
                        cursor.execute(
                            "ALTER USER %s@%s IDENTIFIED BY %s",
                            (dbuser, account_host, dbpassword))

                # RDS does not permit granting privileges the master account
                # does not itself hold, so ask for the explicit subset there.
                if remote and host.find('rds.amazon') > -1:
                    grant = ("GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, "
                             "INSERT, DELETE ON `%s`.* TO %%s@%%s" % dbname)
                else:
                    grant = "GRANT ALL PRIVILEGES ON `%s`.* TO %%s@%%s" % dbname
                cursor.execute(grant, (dbuser, account_host))

                cursor.execute("FLUSH PRIVILEGES")
                connection.commit()
            finally:
                cursor.close()
                connection.close()

            return 1
        except MySQLSetupError as e:
            mysqlUtilities._report(str(e))
            return 0
        except Exception as e:
            mysqlUtilities._report(
                "Unexpected failure preparing the CyberPanel database: %s" % e)
            return 0

    @staticmethod
    def _report(message):
        """Send a failure reason somewhere a human will actually see it."""
        text = "[ERROR] %s" % message
        try:
            import installLog
            installLog.InstallLog.writeToFile(text)
        except Exception:
            try:
                install.logging.InstallLog.writeToFile(text)
            except Exception:
                pass
        print(text)
