"""Give the distribution's Dovecot on an RPM system its MySQL driver.

CyberPanel keeps mailboxes in MySQL. On AlmaLinux, Rocky and CloudLinux 8 the
mail filter step installs the distribution's Dovecot (through
dovecot-pigeonhole) before the mail server step asks for the dovecot23
packages, which cannot be installed beside it. Such a server has Dovecot
without dovecot-mysql: Dovecot's sign-in service stops with "Unknown database
driver 'mysql'", and Postfix, which asks it to check passwords, then drops
every SMTP connection.
"""
import os
import subprocess

SQL_SETTINGS = '/etc/dovecot/dovecot-sql.conf.ext'


def _succeeds(*command):
    return subprocess.call(list(command), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0


def distribution_dovecot_installed(succeeds=_succeeds):
    """True where the package named plainly "dovecot" is installed (not dovecot23 and not a .deb system)."""
    return os.path.exists('/usr/bin/rpm') and succeeds('rpm', '-q', 'dovecot')


def driver_missing(succeeds=_succeeds, settings=SQL_SETTINGS):
    """True when this server's Dovecot is told to use MySQL and cannot."""
    return (distribution_dovecot_installed(succeeds) and os.path.exists(settings)
            and not succeeds('rpm', '-q', 'dovecot-mysql'))


def repair(log=lambda message: None, succeeds=_succeeds, settings=SQL_SETTINGS):
    """Install the driver where it is missing and restart the mail services. Returns what was done."""
    if not driver_missing(succeeds, settings):
        return 'not needed'
    if not succeeds('dnf', 'install', '-y', 'dovecot-mysql'):
        log('WARNING: The Dovecot MySQL driver could not be installed; mailboxes cannot sign in until '
            '"dnf install -y dovecot-mysql" succeeds.')
        return 'failed'
    for service in ('dovecot', 'postfix'):
        succeeds('systemctl', 'restart', service)
    log('Installed the Dovecot MySQL driver that this server was missing; mail sign-in works again.')
    return 'installed'
