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
import json
from CLScript.CLMain import CLMain


class CloudLinuxDomains(CLMain):

    def __init__(self, name, owner):
        CLMain.__init__(self)
        self.owner = owner
        self.name = name

    def listAll(self):
        data = {}

        if self.owner !=None:
            websites = Websites.objects.filter(externalApp=self.owner)
        else:
            websites = Websites.objects.all()


        for webs in websites:
            if self.name != None:
                if self.name != webs.domain:
                    continue
            data[webs.domain] = {"owner": webs.externalApp,
                                 "document_root": "/home/%s/public_html/" % (webs.domain),
                                 "is_main": True}
            for webs in webs.childdomains_set.all():
                data[webs.domain] = {"owner": webs.master.externalApp,
                                     "document_root": webs.path,
                                     "is_main": False}

        final = {'data': data, 'metadata': self.initialMeta}
        print(json.dumps(final))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('-o', '--owner', help='Owner')
    parser.add_argument('-n', '--name', help='Owner')

    args = parser.parse_args()

    pi = CloudLinuxDomains(args.owner, args.name)
    try:
        pi.listAll()
    except:
        pi.listAll()
