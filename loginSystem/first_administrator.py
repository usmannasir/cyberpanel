"""The panel's first administrator.

While it had no administrator, the panel created "admin" with the password
1234567 on the first request it got, from whoever sent that request. The panel
creates no account itself now: plogical/adminPass.py --first-administrator
makes the first one, as root, with a password that nobody chose and that only
root on the server can read (/etc/cyberpanel/adminPass). While the marker below
exists, the sign-in page says where that password is.
"""
import os

from django.db import transaction

from baseTemplate.models import version
from cyberpanel_version import BUILD, VERSION
from loginSystem.models import ACL, Administrator
from packages.models import Package
from plogical import hashPassword
from plogical.acl import ACLManager

# Run by the panel's root helper. Nothing of a request is part of it.
FIRST_ADMINISTRATOR_COMMAND = ('/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/adminPass.py '
                               '--first-administrator')
# Made by adminPass.py --first-administrator; removed when "admin" signs in or
# a password is set with adminPass.py. In the panel's own directory, so that
# the panel can remove it.
GENERATED_PASSWORD_MARKER = '/home/cyberpanel/adminPassGenerated'


def create_first_administrator(password):
    """Make "admin" with this password, and what a panel's first administrator
    comes with: the default ACLs, the version row and the Default package.

    The administrator, its version row and its package are saved together or
    not at all: an administrator whose password was never stored would lock
    the panel's owner out. The ACLs come first and on their own, because
    createDefaultACLs leaves those that exist as they are.
    """
    ACLManager.createDefaultACLs()
    acl = ACL.objects.get(name='admin')
    with transaction.atomic():
        admin = Administrator(userName="admin", password=hashPassword.hash_password(password), type=1,
                              email='admin@cyberpanel.net', firstName="Cyber", lastName="Panel", acl=acl,
                              token=hashPassword.generateToken('admin', password))
        admin.save()
        version(currentVersion=VERSION, build=BUILD).save()
        Package(admin=admin, packageName="Default", diskSpace=1000, bandwidth=1000, ftpAccounts=1000,
                dataBases=1000, emailAccounts=1000, allowedDomains=20).save()
    return admin


def ensure_first_administrator():
    """Have the first administrator made on the server and say whether the
    panel has an administrator now. Nothing is created here."""
    try:
        from plogical.processUtilities import ProcessUtilities
        ProcessUtilities.executioner(FIRST_ADMINISTRATOR_COMMAND)
    except Exception:
        pass
    try:
        return Administrator.objects.exists()
    except Exception:
        return False


def generated_password_notice():
    """Whether the sign-in page says where the generated password is."""
    try:
        return os.path.lexists(GENERATED_PASSWORD_MARKER)
    except Exception:
        return False


def forget_generated_password_notice():
    """The generated password was used or replaced: the page stops saying where it is."""
    try:
        os.unlink(GENERATED_PASSWORD_MARKER)
    except OSError:
        pass
