#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import re
import json
import uuid

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    cf = CloudFlare.CloudFlare()

    try:
        zone_name = sys.argv[1]
    except IndexError:
        exit('usage: example_firewall_rules.py zone_name')

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

    # SHOW EXISTING FIREWALL RULES
    r = cf.zones.firewall.rules.get(zone_id)
    print('existing filewall rules =\n' + json.dumps(r, indent=4, sort_keys=False) + '\n')

    # SHOW EXISTING FILTERS
    r = cf.zones.filters.get(zone_id)
    print('existing filters =\n' + json.dumps(r, indent=4, sort_keys=False) + '\n')

    # CREATE A FILTER & FIREWALL RULES

    reference_name = 'FILTER-' + str(uuid.uuid1())

    my_filter = {
        'expression': 'http.request.uri.path == "/private.html$"',
        'paused': True,
        'description': 'stop access to /private.html',
        'ref': reference_name,
    }

    my_rule = [
        {
            'action': 'block',
            'filter': my_filter,
            'paused': True,
        }
    ]

    try:
        r = cf.zones.firewall.rules.post(zone_id, data=my_rule)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('create zones.filewall.rules: %d %s' % (int(e), str(e)))
        exit(1)

    print('firewall rule created =\n' + json.dumps(r, indent=4, sort_keys=False) + '\n')

    firewall_id = r[0]['id']
    filter_id = r[0]['filter']['id']

    print('filewall_id = %s filter_id = %s' % (firewall_id, filter_id))

    # SHOW PRESENT FIREWALL RULES
    r = cf.zones.firewall.rules.get(zone_id)
    print('present filewall rules =\n' + json.dumps(r, indent=4, sort_keys=False) + '\n')

    # DELETE NEW FIREWALL RULES
    for f in r:
        print('id = ' + f['id'])
        try:
            r2 = cf.zones.firewall.rules.delete(zone_id, f['id'])
            print('deleted id = ' + r2['id'])
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            print('zones.filewall.rules.delete: %d %s' % (int(e), str(e)))

    # SHOW PRESENT FILTERS
    r = cf.zones.filters.get(zone_id)
    print('present filters =\n' + json.dumps(r, indent=4, sort_keys=False) + '\n')

    # DELETE NEW FILTERS
    for f in r:
        print('id = ' + f['id'])
        try:
            r2 = cf.zones.filters.delete(zone_id, f['id'])
            print('deleted id = ' + r2['id'])
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            print('zones.filters.delete: %d %s' % (int(e), str(e)))

    # SHOW FINAL FIREWALL RULES
    r = cf.zones.firewall.rules.get(zone_id)
    print('final filewall rules =\n' + json.dumps(r, indent=4, sort_keys=False) + '\n')

    # SHOW FINAL FILTERS
    r = cf.zones.filters.get(zone_id)
    print('final filters =\n' + json.dumps(r, indent=4, sort_keys=False) + '\n')

if __name__ == '__main__':
    main()
