import os
import sys

sys.path.append('/usr/local/CyberCP')
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass


class CPBackupsV2:
    def __init__(self, data):
        self.data = data
        pass

    def InitiateBackup(self):
        Config = {'domain': self.data['domain']}
        from websiteFunctions.models import Websites, ChildDomains, WPSites, WPStaging
        from django.forms.models import model_to_dict
        from plogical.mysqlUtilities import mysqlUtilities
        website = Websites.objects.get(domain=self.data['domain'])


        Config = {'MainWebsite': model_to_dict(website, fields=['domain', 'adminEmail', 'phpSelection', 'state', 'config'])}
        Config['admin'] = model_to_dict(website.admin, fields=['userName', 'password', 'firstName', 'lastName',
                                                               'email', 'type', 'owner', 'token', 'api', 'securityLevel',
                                                               'state', 'initWebsitesLimit', 'twoFA', 'secretKey', 'config'])
        Config['acl'] = model_to_dict(website.admin.acl)

        ### Child domains to config

        ChildsList = []

        for childDomains in website.childdomains_set.all():
            ChildsList.append(model_to_dict(childDomains))

        Config['ChildDomains'] = ChildsList

        ### Databases

        dataBases = website.databases_set.all()

        connection, cursor = mysqlUtilities.setupConnection()

        if connection == 0:
            return 0




        pass

if __name__ == "__main__":
    cpbuv2 = CPBackupsV2({'domain': 'cyberpanel.net'} )
    cpbuv2.InitiateBackup()