#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import argparse
import fcntl
import secrets
import string
import tempfile
from loginSystem.models import Administrator
from loginSystem.first_administrator import (GENERATED_PASSWORD_MARKER, create_first_administrator,
                                             forget_generated_password_notice)
from plogical import hashPassword
from plogical.securityUtils import ensure_api_token, is_current_api_token, normalize_api_token

if not os.geteuid() == 0:
    sys.exit("\nOnly root can run this script\n")

PASSWORD_FILE = '/etc/cyberpanel/adminPass'
PASSWORD_LOCK = '/etc/cyberpanel/adminPass.lock'
GENERATED_LENGTH = 20
GENERATED_ALPHABET = string.ascii_letters + string.digits

def password_from_file(path):
    """The first line of a file, without its line ending."""
    with open(path, encoding='utf-8') as source:
        return source.readline().rstrip('\r\n')

def generated_password():
    """A password that nobody chose: letters and digits only, so that it is
    one word on any command line and never begins with "-"."""
    return ''.join(secrets.choice(GENERATED_ALPHABET) for _ in range(GENERATED_LENGTH))

def note_generated_password():
    """Leave the mark that makes the sign-in page say where the generated
    password is. The directory belongs to the panel's own account: a link put
    there is not followed, and nothing is written into the file."""
    try:
        descriptor = os.open(GENERATED_PASSWORD_MARKER, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    except OSError:
        return
    os.close(descriptor)

def make_first_administrator():
    """Make the panel's first administrator, unless it has one, with a
    generated password that only root can read in PASSWORD_FILE.

    The panel runs this through its root helper when its sign-in page is asked
    for and there is no administrator. Two such requests at the same time make
    one administrator: the count is taken under a lock. The password is in
    PASSWORD_FILE once the administrator exists, never before, and is not
    printed. Returns the exit status.
    """
    directory = os.path.dirname(PASSWORD_FILE)
    lock = os.open(PASSWORD_LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if Administrator.objects.exists():
            print("The panel has an administrator; nothing was changed.")
            return 0
        password = generated_password()
        # Made for root only (mode 600) and put in place only once the
        # administrator is saved: until then the old file stays as it was.
        descriptor, temporary = tempfile.mkstemp(prefix='.adminPass.', dir=directory)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stored:
                stored.write(password + '\n')
                stored.flush()
                os.fsync(stored.fileno())
            create_first_administrator(password)
            os.replace(temporary, PASSWORD_FILE)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        note_generated_password()
        print("An administrator 'admin' was created. Its password is stored in %s, readable by root." % PASSWORD_FILE)
        return 0
    finally:
        os.close(lock)

def main():

    parser = argparse.ArgumentParser(description='Reset admin user password!')
    parser.add_argument('--password', help='New Password')
    parser.add_argument('--password-file', help='Read the new password from the first line of this file, '
                                                'so that it is not part of the command line')
    parser.add_argument('--first-administrator', action='store_true',
                        help='Make the first administrator, with a generated password stored in '
                             '/etc/cyberpanel/adminPass, unless the panel has one')
    parser.add_argument('--api', help='Enable/Disable API')
    parser.add_argument('--api-token', help='Set a pre-generated versioned API token while enabling API access')
    args = parser.parse_args()

    if args.first_administrator:
        if args.password is not None or args.password_file is not None or args.api is not None:
            parser.error('--first-administrator takes no other option')
        try:
            status = make_first_administrator()
        except Exception as error:
            print("The first administrator could not be made: %s" % type(error).__name__)
            status = 1
        sys.exit(status)

    if args.api != None:
        if args.api == '1':
            admin = Administrator.objects.get(userName="admin")
            if args.api_token:
                if not is_current_api_token(args.api_token):
                    parser.error('--api-token must use the cp_api_v1_ format')
                admin.token = 'Basic %s' % normalize_api_token(args.api_token)
            else:
                ensure_api_token(admin)
            admin.api = 1
            admin.save()
            print("API Enabled.")
            print("API Token: %s" % admin.token)
        else:
            admin = Administrator.objects.get(userName="admin")
            admin.api = 0
            admin.token = ''
            admin.save()
            print("API Disabled.")
    else:

        adminPass = args.password
        if args.password_file is not None:
            adminPass = password_from_file(args.password_file)
            if not adminPass:
                parser.error('--password-file names a file without a password')

        numberOfAdministrator = Administrator.objects.count()
        if numberOfAdministrator == 0:
            create_first_administrator(adminPass)
            forget_generated_password_notice()
            print("Admin password successfully changed!")
            return 1

        token = hashPassword.generateToken('admin', adminPass)
        admin = Administrator.objects.get(userName="admin")
        admin.password = hashPassword.hash_password(adminPass)
        admin.token = token
        admin.save()
        forget_generated_password_notice()

        print("Admin password successfully changed!")

if __name__ == "__main__":
    main()
