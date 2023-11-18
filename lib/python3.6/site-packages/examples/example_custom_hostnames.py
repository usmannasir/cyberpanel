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
        params = {'per_page':500}

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones.get - %s - api call failed' % (e))

    # there should only be one zone - but handle more if needed
    for zone in sorted(zones, key=lambda v: v['name']):
        zone_name = zone['name']
        zone_id = zone['id']
        zone_plan = zone['plan']['name']
        if zone_plan != 'Enterprise Website':
            print('%s %s %s - not Enterprise' % (zone_id, zone_name, zone_plan))
            continue

        print('%s %-40s %s' % (zone_id, zone_name, zone_plan))
        try:
            custom_info = cf.zones.custom_hostnames.get(zone_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.stderr.write('/zones.custom_hostnames.get %d %s - api call failed\n' % (e, e))
            continue

        for hostname_info in custom_info:
            print('\t%s %-30s %s' % (hostname_info['id'], hostname_info['hostname'], hostname_info['created_at']))

            for s in sorted(hostname_info.keys()):
                if s in ['id', 'hostname', 'created_at'] or hostname_info[s] == None:
                    continue
                print('\t%-15s = %s' % (s, hostname_info[s]))

        try:
            fallback_origin = cf.zones.custom_hostnames.fallback_origin.get(zone_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.stderr.write('/zones.custom_hostnames.fallback_origin.get %d %s - api call failed\n' % (e, e))
            continue

        print('\t%s %-30s %s %s' % ('', fallback_origin['origin'], fallback_origin['created_at'], fallback_origin['status']))
        print('')

    exit(0)

if __name__ == '__main__':
    main()

