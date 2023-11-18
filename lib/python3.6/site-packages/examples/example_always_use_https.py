#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    update_flag = False

    try:
        if sys.argv[1] == '--off':
            update_flag = True
            new_value = 'off'
            sys.argv.pop(1)
    except IndexError:
        pass

    try:
        if sys.argv[1] == '--on':
            update_flag = True
            new_value = 'on'
            sys.argv.pop(1)
    except IndexError:
        pass

    # Grab the zone name
    try:
        zone_name = sys.argv[1]
        params = {'name':zone_name, 'per_page':1}
    except IndexError:
        exit('usage: example_always_use_https.py [--on|--off] zone')

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones - %s - api call failed' % (e))

    zone_id = zones[0]['id']

    # retrieve present value
    try:
        r = cf.zones.settings.always_use_https.get(zone_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.settings.always_use_https.get %d %s - api call failed' % (e, e))

    present_value = r['value']

    print(zone_id, zone_name, present_value)

    if update_flag and present_value != new_value:
        print('\t', '(now updating... %s -> %s)' % (present_value, new_value))
        try:
            r = cf.zones.settings.always_use_https.patch(zone_id, data={'value':new_value})
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.settings.always_use_https.patch %d %s - api call failed' % (e, e))
        updated_value = r['value']
        if new_value == updated_value:
            print('\t', '... updated!')

if __name__ == '__main__':
    main()
    exit(0)

