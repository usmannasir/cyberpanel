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


class CloudLinuxAdmins(CLMain):

    def __init__(self, name, isMain):
        CLMain.__init__(self)
        self.name = name
        if isMain == 'true':
            self.isMain = 1
        else:
            self.isMain = 0

    def listAll(self):
        users = []
        acl = ACL.objects.get(name='admin')
        for items in Administrator.objects.filter(acl=acl):

            if items.userName == 'admin':
                isMain = True
            else:
                isMain = False

            if self.isMain:
                if isMain == False:
                    continue

            if self.name != None:
                if self.name != items.userName:
                    continue

            user = {'name': items.userName,
                    "locale_code": "EN_us",
                    "unix_user": None,
                     "email": items.email,
                     "is_main": isMain
                    }

            users.append(user)

        final = {'data': users, 'metadata': self.initialMeta}
        print(json.dumps(final))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('-n','--name', help='Owner')
    parser.add_argument('-m', '--is-main', help='Owner')

    args = vars(parser.parse_args())

    pi = CloudLinuxAdmins(args['name'], args['is_main'])
    try:
        pi.listAll()
    except:
        pi.listAll()
