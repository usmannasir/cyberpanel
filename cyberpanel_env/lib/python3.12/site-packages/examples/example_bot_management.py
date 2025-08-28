#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import json
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

import CloudFlare

def main():
    """Cloudflare API code - example"""

    try:
        zone_name = sys.argv[1]
    except IndexError:
        exit('usage: example_bot_management.py zone_name True/False')

    try:
        enable_value = sys.argv[2]
    except IndexError:
        exit('usage: example_bot_management.py zone_name True/False')

    enable_value = True if enable_value in ['true','True','1'] else False

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        params = {'name': zone_name}
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zone %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zone.get - %s - api call failed' % (e))

    if len(zones) == 0:
        exit('/zones.get - %s - zones not found' % (zone_name))

    if len(zones) != 1:
        exit('/zones.get - %s - api call returned %d items' % (zone_name, len(zones)))

    zone_id = zones[0]['id']

    settings_bot = cf.zones.bot_management.get(zone_id)
    print(json.dumps(settings_bot, indent=4))

    try:
        settings_bot = cf.zones.bot_management.put(zone_id, data={'enable_js': enable_value})
    except Exception as e:
        if int(e) == 99998:
            print('Exception: 99998 ignored!', file=sys.stderr)
            pass
        else:
            exit('Exception: %d %s' % (int(e), str(e)))

    settings_bot = cf.zones.bot_management.get(zone_id)
    print(json.dumps(settings_bot, indent=4))

if __name__ == '__main__':
    main()
