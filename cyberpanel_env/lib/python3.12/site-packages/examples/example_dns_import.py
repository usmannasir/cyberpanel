#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import json

import CloudFlare

def main():
    """Cloudflare API code - example"""

    try:
        zone_name = sys.argv[1]
        file_name = sys.argv[2]
    except IndexError:
        exit('usage: example_dns_import.py zone zone-file')

    try:
        fd = open(file_name, 'rb')
    except IOError as e:
        exit('file open - %s' % (e))

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        params = {'name': zone_name}
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones.get - %s - api call failed' % (e))

    if len(zones) == 0:
        exit('/zones.get - %s - zone not found' % (zone_name))

    if len(zones) != 1:
        exit('/zones.get - %s - api call returned %d items' % (zone_name, len(zones)))

    zone_id = zones[0]['id']

    try:
        #
        # "import" is a reserved word and hence we add '_' to the end of verb.
        #
        r = cf.zones.dns_records.import_.post(zone_id, files={'file':fd})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/dns_records/import %s - %d %s - api call failed' % (dns_name, e, e))

    print(json.dumps(r))

    exit(0)

if __name__ == '__main__':
    main()
