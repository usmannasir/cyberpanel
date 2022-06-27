#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import argparse
from loginSystem.models import Administrator, ACL
from plogical import hashPassword
from plogical.acl import ACLManager
from packages.models import Package
from baseTemplate.models import version

VERSION = '2.3'
BUILD = 2

if not os.geteuid() == 0:
    sys.exit("\nOnly root can run this script\n")

def main():

    parser = argparse.ArgumentParser(description='Reset admin user password!')
    parser.add_argument('--password', help='New Password')
    parser.add_argument('--api', help='Enable/Disable API')
    args = parser.parse_args()

    if args.api != None:
        if args.api == '1':
            admin = Administrator.objects.get(userName="admin")
            admin.api = 1
            admin.save()
            print("API Enabled.")
        else:
            admin = Administrator.objects.get(userName="admin")
            admin.api = 0
            admin.save()
            print("API Disabled.")
    else:

        adminPass = args.password

        numberOfAdministrator = Administrator.objects.count()
        if numberOfAdministrator == 0:

            ACLManager.createDefaultACLs()
            acl = ACL.objects.get(name='admin')
            token = hashPassword.generateToken('admin', adminPass)

            email = 'example@example.org'
            admin = Administrator(userName="admin", password=hashPassword.hash_password(adminPass), type=1, email=email,
                                  firstName="Cyber", lastName="Panel", acl=acl, token=token)
            admin.save()

            vers = version(currentVersion=VERSION, build=BUILD)
            vers.save()

            package = Package(admin=admin, packageName="Default", diskSpace=1000,
                              bandwidth=1000, ftpAccounts=1000, dataBases=1000,
                              emailAccounts=1000, allowedDomains=20)
            package.save()


            print("Admin password successfully changed!")
            return 1

        token = hashPassword.generateToken('admin', adminPass)
        admin = Administrator.objects.get(userName="admin")
        admin.password = hashPassword.hash_password(adminPass)
        admin.token = token
        admin.save()

        print("Admin password successfully changed!")

if __name__ == "__main__":
    main()
