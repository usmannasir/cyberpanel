#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    # Grab the first argument, if there is one
    try:
        zone_name = sys.argv[1]
        params = {'name':zone_name, 'per_page':1}
    except IndexError:
        params = {'per_page':50}

    #
    # Show how 'with' statement works
    #
    with CloudFlare.CloudFlare() as cf:
        zones = cf.zones(params=params)
        for zone in sorted(zones, key=lambda v: v['name']):
            print(zone['id'], zone['name'])

    exit(0)

if __name__ == '__main__':
    main()

