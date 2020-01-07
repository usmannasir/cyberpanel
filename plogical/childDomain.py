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
    def __init__(self, masterDomain = None, childDomain = None):
        self.masterDomain = masterDomain
        self.childDomain = childDomain

    def findChildDomainsJson(self):
        master = Websites.objects.get(domain=self.masterDomain)
        childDomains = master.childdomains_set.all()

        json_data = "["
        checker = 0

        for items in childDomains:
            dic = {
                'childDomain': items.domain,
                'path': items.path,
                'childLunch': '/websites/' + self.masterDomain + '/' + items.domain
            }

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data