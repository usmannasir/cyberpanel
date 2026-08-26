#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from loginSystem.models import Administrator, ACL
from plogical.securityUtils import ensure_api_token

def main():
    admin = Administrator.objects.get(userName='admin')
    ensure_api_token(admin)
    admin.api = 1
    admin.save()

    print("API Access Enabled")
    print("API Token: %s" % admin.token)

if __name__ == "__main__":
    main()
