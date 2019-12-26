#!/usr/local/CyberCP/bin/python
import sys
import os.path
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
from websiteFunctions.models import Websites
from CLManager.CLPackages import CLPackages
import argparse
import pwd
import json
from CLScript.CLMain import CLMain


class CloudLinuxPackages(CLMain):
    def __init__(self):
        CLMain.__init__(self)

    def listAll(self, owner=None):
        packages = []

        if owner == None:
            for items in Websites.objects.all():
                itemPackage = items.package
                try:
                    clPackage = CLPackages.objects.get(owner=itemPackage)
                    packages.append({'name': clPackage.name, 'owner': items.externalApp})
                except:
                    pass
        else:
            for items in Websites.objects.filter(externalApp=owner):
                itemPackage = items.package
                try:
                    clPackage = CLPackages.objects.get(owner=itemPackage)
                    packages.append({'name': clPackage.name, 'owner': items.externalApp})
                except:
                    pass

        final = {'data': packages, 'metadata': self.initialMeta}
        print(json.dumps(final))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('--owner', help='Owner')

    args = parser.parse_args()

    pi = CloudLinuxPackages()
    try:
        pi.listAll(args.owner)
    except:
        pi.listAll()
