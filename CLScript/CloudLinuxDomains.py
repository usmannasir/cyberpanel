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

    def __init__(self, name, owner, with_php):
        CLMain.__init__(self)
        self.owner = owner
        self.name = name
        self.with_php = with_php

    def listAll(self):
        data = {}

        if self.owner != None:
            websites = Websites.objects.filter(externalApp=self.owner)
        else:
            websites = Websites.objects.all()

        for webs in websites:
            if self.name != None:
                if self.name != webs.domain:
                    continue

            if self.with_php:
                completePathToConfigFile = f'/usr/local/lsws/conf/vhosts/{webs.domain}/vhost.conf'
                from plogical.phpUtilities import phpUtilities
                from managePHP.phpManager import PHPManager
                phpVersion = phpUtilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(completePathToConfigFile)
                php = PHPManager.getPHPString(phpVersion)

                data[webs.domain] = {
                    "owner": webs.externalApp,
                    "document_root": "/home/%s/public_html/" % (webs.domain),
                    "is_main": True,
                    "php": {
                        "version": php[:2],
                        "ini_path": f"/usr/local/lsws/lsphp{php[:2]}/etc/php.d",
                        "is_native": False
                    }

                }

                for webs in webs.childdomains_set.all():
                    completePathToConfigFile = f'/usr/local/lsws/conf/vhosts/{webs.domain}/vhost.conf'
                    from plogical.phpUtilities import phpUtilities
                    from managePHP.phpManager import PHPManager
                    phpVersion = phpUtilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(completePathToConfigFile)
                    php = PHPManager.getPHPString(phpVersion)

                    data[webs.domain] = {"owner": webs.master.externalApp,
                                         "document_root": webs.path,
                                         "is_main": False,
                                         "php": {
                                             "version": php[:2],
                                             "ini_path": f"/usr/local/lsws/lsphp{php[:2]}/etc/php.d",
                                             "is_native": False
                                         }

                                         }

            else:
                data[webs.domain] = {"owner": webs.externalApp,
                                     "document_root": "/home/%s/public_html/" % (webs.domain),
                                     "is_main": True}
                for webs in webs.childdomains_set.all():
                    data[webs.domain] = {"owner": webs.master.externalApp,
                                         "document_root": webs.path,
                                         "is_main": False}

        final = {'data': data, 'metadata': self.initialMeta}
        print(json.dumps(final))


import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CyberPanel CloudLinux Manager')
    parser.add_argument('-o', '--owner', help='Owner')
    parser.add_argument('-n', '--name', help='Owner')
    parser.add_argument('-p', '--with-php', action='store_true', help='False (X-Ray support only)')

    args = parser.parse_args()

    # Assuming CloudLinuxDomains class exists
    pi = CloudLinuxDomains(args.name, args.owner, args.with_php)
    try:
        pi.listAll()
    except:
        pi.listAll()
