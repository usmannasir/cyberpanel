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
from loginSystem.models import Administrator, ACL
import argparse
import json
from CLScript.CLMain import CLMain


class CloudLinuxResellers(CLMain):

    def __init__(self, id, name):
        CLMain.__init__(self)
        self.id = id
        self.name = name

    def listAll(self, owner=None):
        users = []
        acl = ACL.objects.get(name='reseller')
        for items in Administrator.objects.filter(acl=acl):
            if self.name != None:
                if self.name != items.userName:
                    continue

            user = {'name': items.userName,
                    "locale_code": "EN_us",
                     "email": items.email,
                    "id": None
                    }

            users.append(user)

        final = {'data': users, 'metadata': self.initialMeta}
        print(json.dumps(final))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('--id', help='Owner')
    parser.add_argument('-n', '--name', help='Owner')

    args = parser.parse_args()

    pi = CloudLinuxResellers(args.id, args.name)
    try:
        pi.listAll()
    except:
        pi.listAll()
