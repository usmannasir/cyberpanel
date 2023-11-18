#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import CloudFlare

def main():
    """Cloudflare API code - example"""

    try:
        zone_name = sys.argv[1]
    except IndexError:
        exit('usage: example_dns_export.py zone')

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
        dns_records = cf.zones.dns_records.export.get(zone_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/dns_records/export %s - %d %s - api call failed' % (dns_name, e, e))

    for l in dns_records.splitlines():
        if len(l) == 0 or l[0] == ';':
            # blank line or comment line are skipped - to make example easy to see
            continue
        print(l)

    exit(0)

if __name__ == '__main__':
    main()

