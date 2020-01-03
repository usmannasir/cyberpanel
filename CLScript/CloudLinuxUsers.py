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
import argparse
import pwd
import json
from CLScript.CLMain import CLMain


class CloudLinuxUsers(CLMain):

    def __init__(self, owner, username, packageName, packageOwner, fields, uid):

        CLMain.__init__(self)
        self.owner = owner
        self.username = username
        self.packageName = packageName
        self.packageOwner = packageOwner
        self.fields = fields
        if uid!=None:
            self.uid = int(uid)
        else:
            self.uid = uid

        if self.fields == None:
            self.id = 1
            self.un = 1
            self.ow = 1
            self.domain = 1
            self.package = 1
            self.email = 1
            self.localecode = 1
        else:
            if self.fields.find('id') > -1:
                self.id = 1
            else:
                self.id = 0
            if self.fields.find('username') > -1:
                self.un = 1
            else:
                self.un = 0

            if self.fields.find('owner') > -1:
                self.ow = 1
            else:
                self.ow = 0

            if self.fields.find('domain') > -1:
                self.domain = 1
            else:
                self.domain = 0

            if self.fields.find('package') > -1:
                self.package = 1
            else:
                self.package = 0

            if self.fields.find('email') > -1:
                self.email = 1
            else:
                self.email = 0

            if self.fields.find('locale_code') > -1:
                self.localecode = 1
            else:
                self.localecode = 0



    def fetchJson(self, websites):
        users = []
        for webs in websites:
            itemPackage = webs.package
            package = {'name': itemPackage.packageName, 'owner': webs.externalApp}

            user = {}

            if self.id:
                user['id'] = pwd.getpwnam(webs.externalApp).pw_uid

            if self.un:
                user['username'] = webs.externalApp

            if self.ow:
                user['owner'] = webs.externalApp

            if self.domain:
                user['domain'] = webs.domain

            if self.package:
                user['package'] = package

            if self.email:
                user['email'] = webs.adminEmail

            if self.localecode:
                user['locale_code'] = "EN_us"


            if self.packageName != None:
                if self.package:
                    if self.packageName == user['package']['name'] and self.packageOwner == user['package']['owner']:
                        pass
                    else:
                        continue

            if self.uid !=None:
                if self.id:
                    if self.uid == user['id']:
                        users.append(user)
                else:
                    users.append(user)
            else:
                users.append(user)

        final = {'data': users, 'metadata': self.initialMeta}
        print(json.dumps(final))

    def listAll(self):

        if self.owner == None:
            websites = Websites.objects.all()
        else:
            websites = Websites.objects.filter(externalApp=self.owner)

        if self.username != None:
            websites = websites.filter(externalApp=self.username)

        self.fetchJson(websites)


def main():
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('-o', '--owner', help='Owner')
    parser.add_argument('--fields', help='Fields to output!')
    parser.add_argument('--username', help='Fields to output!')
    parser.add_argument('--package-name', help='Fields to output!')
    parser.add_argument('--package-owner', help='Fields to output!')
    parser.add_argument('--unix-id', help='Fields to output!')

    args = vars(parser.parse_args())

    pi = CloudLinuxUsers(args['owner'], args['username'], args['package_name'], args['package_owner'], args['fields'], args['unix_id'])
    pi.listAll()



if __name__ == '__main__':
    main()
