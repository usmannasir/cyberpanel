#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    cf = CloudFlare.CloudFlare()
    try:
        r = cf.api_from_web()
    except Exception as e:
        exit('api_from_web: - %s - api call connection failed' % (e))

    print(json.dumps(r))
    exit(0)

if __name__ == '__main__':
    main()

