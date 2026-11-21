"""Support for the Multi-Server Manager tests that need Django or MariaDB.

These tests start the panel's Django and, as root, create and drop MariaDB
databases. They therefore run only on a server an engineer has marked as a
disposable test server, by creating the file named in MARKER there:

    touch /root/multiserver-test-server
    /usr/local/CyberCP/bin/python -m unittest multiServer.test_wiring multiServer.test_database

Everywhere else, including any server that merely has a panel installed, they
report themselves as skipped, and the helpers below refuse to start Django or
to open a connection.

On a test server the installed panel and its database are still left alone.
Django is started with a throwaway secret key, so the settings module does not
write a key file into the installation, and no test uses the panel's database:
each database test class creates a database of its own with a user of its own,
points Django at it, and drops both afterwards.
"""
import os
import secrets

MARKER = '/root/multiserver-test-server'
PASSWORD_FILE = '/etc/cyberpanel/mysqlPassword'


def unavailable():
    """Why the Django and MariaDB tests may not run on this server, or None when they may."""
    if not os.path.isfile(MARKER):
        return ('not marked as a disposable test server (%s is missing): tests that start Django or create '
                'MariaDB databases do not run here' % MARKER)
    try:
        import django  # noqa: F401
        import MySQLdb  # noqa: F401
    except ImportError as error:
        return 'Django or its MariaDB driver is not installed: %s' % error
    if not os.path.isfile(PASSWORD_FILE):
        return 'no panel is installed here (%s is missing)' % PASSWORD_FILE
    return None


def require_test_server():
    reason = unavailable()
    if reason is not None:
        raise RuntimeError('Refusing to run: ' + reason)


def start_django():
    require_test_server()
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
    os.environ.setdefault('SECRET_KEY', 'multiserver-tests-' + secrets.token_hex(16))
    django.setup()


class ScratchDatabase:
    """An empty MariaDB database that exists only for one test class.

    Root creates and drops it. Everything in between is done as a user made for
    it, who holds what the panel's own database user holds (all privileges on
    one database) and can reach no other database.
    """

    def __init__(self):
        require_test_server()
        import MySQLdb
        with open(PASSWORD_FILE) as source:
            self._root_password = source.readline().rstrip('\n')
        self.driver = MySQLdb
        self.name = 'ms_test_%d_%s' % (os.getpid(), secrets.token_hex(4))
        self.password = secrets.token_hex(16)
        self._restore = None
        self._as_root('CREATE DATABASE `%s`' % self.name,
                      "CREATE USER '%s'@'localhost' IDENTIFIED BY '%s'" % (self.name, self.password),
                      "GRANT ALL PRIVILEGES ON `%s`.* TO '%s'@'localhost'"
                      % (self.name.replace('_', '\\_'), self.name))

    def _as_root(self, *statements):
        connection = self.driver.connect(host='localhost', user='root', passwd=self._root_password)
        try:
            cursor = connection.cursor()
            for statement in statements:
                cursor.execute(statement)
            connection.commit()
        finally:
            connection.close()

    def connect(self):
        return self.driver.connect(host='localhost', user=self.name, passwd=self.password, db=self.name,
                                   charset='utf8mb4')

    def run(self, statement):
        """Run one statement on a connection of its own and return all rows."""
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute(statement)
            rows = cursor.fetchall()
            connection.commit()
            return rows
        finally:
            connection.close()

    def give_to_django(self):
        """Make this database the one Django's default connection opens, in every thread."""
        from django.db import connections
        connection = connections['default']
        connection.close()
        saved = dict(connection.settings_dict)
        connection.settings_dict.update(NAME=self.name, USER=self.name, PASSWORD=self.password)

        def restore():
            connection.close()
            connection.settings_dict.clear()
            connection.settings_dict.update(saved)
        self._restore = restore

    def drop(self):
        if self._restore is not None:
            self._restore()
        self._as_root('DROP DATABASE IF EXISTS `%s`' % self.name,
                      "DROP USER IF EXISTS '%s'@'localhost'" % self.name)
