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
from websiteFunctions.models import Websites, ChildDomains
import argparse
import json
from CLScript.CLMain import CLMain


class CloudLinuxDomains(CLMain):

    def __init__(self):
        CLMain.__init__(self)

    def listAll(self, owner=None):
        data = {}

        for webs in Websites.objects.all():
            data[webs.domain] = {"owner": webs.externalApp,
                                 "document_root": "/home/%s/public_html/" % (webs.domain),
                                 "is_main": True}

        for webs in ChildDomains.objects.all():
            data[webs.domain] = {"owner": webs.master.externalApp,
                                 "document_root": webs.path,
                                 "is_main": False}

        final = {'data': data, 'metadata': self.initialMeta}
        print(json.dumps(final))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('--owner', help='Owner')

    args = parser.parse_args()

    pi = CloudLinuxDomains()
    try:
        pi.listAll(args.owner)
    except:
        pi.listAll()
