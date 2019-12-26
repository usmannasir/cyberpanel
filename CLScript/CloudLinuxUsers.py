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


class CloudLinuxUsers(CLMain):

    def __init__(self):
        CLMain.__init__(self)

    def listAll(self, owner=None):
        users = []

        for webs in Websites.objects.all():
            itemPackage = webs.package
            clPackage = CLPackages.objects.get(owner=itemPackage)
            package = {'name': clPackage.name, 'owner': webs.externalApp}

            user = {'id': pwd.getpwnam(webs.externalApp).pw_uid,
                    'username': webs.externalApp,
                    'owner': webs.externalApp,
                    'domain': webs.domain,
                    'package': package,
                    'email': webs.adminEmail,
                    "locale_code": "EN_us"
                    }

            users.append(user)

        final = {'data': users, 'metadata': self.initialMeta}
        print(json.dumps(final))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('--owner', help='Owner')

    args = parser.parse_args()

    pi = CloudLinuxUsers()
    try:
        pi.listAll(args.owner)
    except:
        pi.listAll()
