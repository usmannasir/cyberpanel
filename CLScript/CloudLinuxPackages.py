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
from packages.models import Package
import argparse
import json
from CLScript.CLMain import CLMain
from loginSystem.models import Administrator


class CloudLinuxPackages(CLMain):
    def __init__(self):
        CLMain.__init__(self)

    def listAll(self, owner=None):
        packages = []

        if owner == None:
            for items in Package.objects.all():
                try:
                    packages.append({'name': items.packageName, 'owner': items.admin.userName})
                except:
                    pass
        else:
            admin = Administrator.objects.get(userName=owner)
            for items in Package.objects.filter(admin=admin):
                try:
                    packages.append({'name': items.packageName, 'owner': items.admin.userName})
                except:
                    pass

        final = {'data': packages, 'metadata': self.initialMeta}
        print(json.dumps(final))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('-o', '--owner', help='Owner')

    args = parser.parse_args()

    pi = CloudLinuxPackages()
    try:
        pi.listAll(args.owner)
    except:
        pi.listAll()
