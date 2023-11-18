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
        params = {'per_page':1}

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones.get - %s - api call failed' % (e))

    # there should only be one zone
    for zone in sorted(zones, key=lambda v: v['name']):
        zone_name = zone['name']
        zone_id = zone['id']
        try:
            settings = cf.zones.settings.get(zone_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.settings.get %d %s - api call failed' % (e, e))

        print(zone_id, zone_name)
        for setting in sorted(settings, key=lambda v: v['id']):
            r_name = setting['id']
            r_value = setting['value']
            r_editable = setting['editable']
            try:
                k = sorted(r_value.keys())
                print('\t%-30s %10s = %s' % (r_name, '(editable)' if r_editable else '', '{'))
                for k in sorted(r_value.keys()):
                    print('\t%-30s %10s    %s = %s' % ('', '', r_name+'/'+k, r_value[k]))
                print('\t%-30s %10s = %s' % ('', '', '}'))
            except:
                print('\t%-30s %10s = %s' % (r_name, '(editable)' if r_editable else '', r_value))

        print('')

    exit(0)

if __name__ == '__main__':
    main()

