#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from loginSystem.models import Administrator, ACL
from django.shortcuts import HttpResponse
from packages.models import Package
from websiteFunctions.models import Websites
from dns.models import Domains
import json

class AliasManager:

    def __init__(self, domain):
        self.domain = domain

    def fetchAlisForDomains(self):
        website = Websites.objects.get(domain=self.domain)

        finalAlisList = []
        noAlias = 0

        aliases = website.aliasdomains_set.all()

        for items in aliases:
            finalAlisList.append(items.aliasDomain)
            noAlias = 1

        return noAlias, finalAlisList