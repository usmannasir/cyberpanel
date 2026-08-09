#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from websiteFunctions.models import Websites
import json


class ChildDomainManager:
    def __init__(self, masterDomain=None, childDomain=None):
        self.masterDomain = masterDomain
        self.childDomain = childDomain

    @staticmethod
    def openBasedirLabel(domainName):
        """Return Enable/Disable from live vhost.conf for List Domains selects."""
        candidates = (
            '/usr/local/lsws/conf/vhosts/%s/vhost.conf' % domainName,
            '/usr/local/lsws/conf/vhosts/%s/vhconf.conf' % domainName,
        )
        for confPath in candidates:
            try:
                if not os.path.exists(confPath):
                    continue
                with open(confPath, 'r', encoding='utf-8', errors='replace') as confFile:
                    content = confFile.read()
                if 'open_basedir' in content:
                    return 'Enable'
                return 'Disable'
            except OSError:
                continue
        return 'Disable'

    def findChildDomainsJson(self, alias=0):
        master = Websites.objects.get(domain=self.masterDomain)
        childDomains = master.childdomains_set.filter(alais=alias)

        json_data = "["
        checker = 0

        for items in childDomains:
            if items.domain == f'mail.{master.domain}':
                pass
            else:
                phpSelection = items.phpSelection or master.phpSelection or 'PHP 8.1'
                dic = {
                    'childDomain': items.domain,
                    'path': items.path,
                    'childLunch': '/websites/' + self.masterDomain + '/' + items.domain,
                    'phpSelection': phpSelection,
                    'childBaseDir': ChildDomainManager.openBasedirLabel(items.domain),
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data
