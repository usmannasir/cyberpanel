import json
import os
import os.path
import sys
import argparse
import requests

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

class UpgradeCyberPanel:

    def __init__(self, branch, mail, dns, ftp):
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        self.ipAddress = ipData.split('\n', 1)[0]

    def PostStatus(self, message):
        finalData = json.dumps({'ipAddress': self.ipAddress, "UpgradeCyberPanelStatus": message})
        url = "http://de-a.cyberhosting.org:8000/settings/RecvData"
        resp = requests.post(url, data=finalData, verify=False)
        print (resp.text)

    def UpgardeNow(self):
        self.PostStatus('Upgrade in route..,35')
        import time
        time.sleep(10)
        self.PostStatus('Upgrade completed. [200]')


def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('--branch', help='Branch to install.')
    parser.add_argument('--mail', help='Upgrade mail services.')
    parser.add_argument('--dns', help='Upgrade dns services.')
    parser.add_argument('--ftp', help='Upgrade ftp services.')

    args = parser.parse_args()

    uc = UpgradeCyberPanel(1,1,1,1)
    uc.UpgardeNow()


if __name__ == "__main__":
    main()