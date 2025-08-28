#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import json
sys.path.insert(0, os.path.abspath('..'))

import CloudFlare

def main():
    """Cloudflare API code - example"""

    try:
        zone_name = sys.argv[1]
    except IndexError:
        exit('usage: example_page_rules.py zone')

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

    routing = cf.zones.email.routing(zone_id)
    print('%s: %s enabled=%s synced=%s status=%s' % (
        routing['tag'],
        routing['name'],
        routing['enabled'],
        routing['synced'],
        routing['status']
    ))

    rules = cf.zones.email.routing.rules(zone_id)
    for r in rules:
        print('%s: matches=%s actions=%s enabled=%s' % (
            r['tag'],
            r['matchers'],
            r['actions'],
            r['enabled']
        ))

    exit(0)

if __name__ == '__main__':
    main()
