#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import argparse
from websiteFunctions.models import Websites
from CLManager.models import CLPackages
import pwd

class CLinuxPackages:

    @staticmethod
    def listAll():
        for items in Websites.objects.all():
            itemPackage = items.package
            try:
                clPackage = CLPackages.objects.get(owner=itemPackage)
                statement = '%s %s' % (pwd.getpwnam(items.externalApp).pw_uid, clPackage.name)
                print(statement)
            except:
                pass


    @staticmethod
    def listPackages():
        for items in CLPackages.objects.all():
            print(items.name)

    @staticmethod
    def userIDPackage(user):
        website = Websites.objects.get(externalApp=user)
        itemPackage = website.package
        try:
            clPackage = CLPackages.objects.get(owner=itemPackage)
            print(clPackage)
        except:
            pass


    @staticmethod
    def packageForUser(package):
        for items in Websites.objects.all():
            itemPackage = items.package
            try:
                clPackage = CLPackages.objects.get(owner=itemPackage)
                if clPackage.name == package:
                    print(pwd.getpwnam(items.externalApp).pw_uid)
            except:
                pass

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Container Manager')
    parser.add_argument('--userid', help='User ID')
    parser.add_argument('--package', help='Package')
    parser.add_argument('--function', help='Function')
    parser.add_argument('--list-all', help='List all users/packages.', action='store_true')
    parser.add_argument('--list-packages', help='List all packages.', action='store_true')


    args = vars(parser.parse_args())

    if args['userid']:
        CLinuxPackages.userIDPackage(args['userid'])
    elif args['package']:
        CLinuxPackages.packageForUser(args['package'])
    elif args['list_all']:
        CLinuxPackages.listAll()
    elif args['list_packages']:
        CLinuxPackages.listPackages()





if __name__ == "__main__":
    main()

