#!/usr/local/CyberCP/bin/python
import sys
sys.path.append('/usr/local/CyberCP')
import json
from CLScript.CLMain import CLMain


class PanelInfo(CLMain):
    def __init__(self):
        CLMain.__init__(self)

    def emit(self):

        initial = {
            "name": "CyberPanel",
            "version": "%s.%s" % (self.version, self.build),
            "user_login_url": "https://%s:8090/" % (self.ipAddress),
            # "supported_cl_features": {
            #     "php_selector": True,
            #     "ruby_selector": True,
            #     "python_selector": True,
            #     "nodejs_selector": True,
            #     "mod_lsapi": True,
            #     "mysql_governor": True,
            #     "cagefs": True,
            #     "reseller_limits": True,
            #     "xray": True,
            #     "accelerate_wp": True,
            #     "autotracing": True
            # }
        }

        final = {'data': initial, 'metadata': self.initialMeta}

        print(json.dumps(final))


if __name__ == '__main__':
    pi = PanelInfo()
    pi.emit()
