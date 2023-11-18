#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    # Check for update flag
    update_ipv6 = False
    try:
        if sys.argv[1] == '--update':
            update_ipv6 = True
            sys.argv.pop(1)
    except IndexError:
        pass

    # Grab the first argument, if there is one
    try:
        zone_name = sys.argv[1]
        params = {'name':zone_name, 'per_page':1}
    except IndexError:
        params = {'per_page':50}

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones - %s - api call failed' % (e))

    for zone in sorted(zones, key=lambda v: v['name']):
        zone_name = zone['name']
        zone_id = zone['id']
        try:
            ipv6 = cf.zones.settings.ipv6.get(zone_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.settings.ipv6.get %d %s - api call failed' % (e, e))

        ipv6_value = ipv6['value']
        if update_ipv6 and ipv6_value == 'off':
            print(zone_id, ipv6_value, zone_name, '(now updating... off -> on)')
            try:
                ipv6 = cf.zones.settings.ipv6.patch(zone_id, data={'value':'on'})
            except CloudFlare.exceptions.CloudFlareAPIError as e:
                exit('/zones.settings.ipv6.patch %d %s - api call failed' % (e, e))
            ipv6_value = ipv6['value']
            if ipv6_value == 'on':
                print('\t', '... updated!')
        else:
            print(zone_id, ipv6_value, zone_name)

    exit(0)

if __name__ == '__main__':
    main()

