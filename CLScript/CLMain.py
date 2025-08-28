import json

class CLMain():
    def __init__(self):
        self.path = '/usr/local/CyberCP/version.txt'
        #versionInfo = json.loads(open(self.path, 'r').read())
        self.version = '2.4'
        self.build = '3'

        from plogical.machineIP import get_machine_ip
        self.ipAddress = get_machine_ip()

        self.initialMeta = {
            "result": "ok"
        }