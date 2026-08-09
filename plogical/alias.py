#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from websiteFunctions.models import Websites
from plogical.domainAliasUtilities import merge_alias_names

class AliasManager:

    def __init__(self, domain):
        self.domain = domain

    def fetchAlisForDomains(self):
        website = Websites.objects.get(domain=self.domain)

        current_aliases = website.aliasdomains_set.values_list('aliasDomain', flat=True)
        legacy_aliases = website.childdomains_set.filter(alais=1).values_list('domain', flat=True)
        finalAlisList = merge_alias_names(current_aliases, legacy_aliases)

        return int(bool(finalAlisList)), finalAlisList
