#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import CloudFlare

def main():
    """Cloudflare API code - example"""

    method = 'POST'

    try:
        if sys.argv[1] == '--delete':
            del sys.argv[1]
            method = 'DELETE'
    except IndexError:
        pass

    try:
        zone_name = sys.argv[1]
    except IndexError:
        exit('usage: example_zone_purge_cache.py zone')

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
    zone_type = zones[0]['plan']['name']

    if 'Enterprise' in zone_type:
        # Enterprise accounts can do all things ...
        data = {
            # 'purge_everything': True,
            'hosts': [zone_name],
            'tags': ['random-tag'],
            'prefixes': [zone_name + '/' + 'index.html'],
        }
    else:
        # Free, Pro, Business accounts can only do this ...
        data = {'purge_everything': True}

    print('%s: zone type="%s" and hence using data="%s" method="%s"' % (zone_name, zone_type, data, method))

    try:
        if method == 'DELETE':
            # delete method is not in documents; however, it works
            r = cf.zones.purge_cache.delete(zone_id, data=data)
        else:
            r = cf.zones.purge_cache.post(zone_id, data=data)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/purge_cache %s - %d %s - api call failed' % (zone_name, e, e))

    if 'id' not in r or r['id'] != zone_id:
        print('%s: weird response: result="%s"' % (zone_name, r))

    exit(0)

if __name__ == '__main__':
    main()
