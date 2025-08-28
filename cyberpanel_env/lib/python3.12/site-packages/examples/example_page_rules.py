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

    url_match = "*.%s/url1*" % (zone_name)
    url_forwarded = "http://%s/url2" % (zone_name)

    targets = [{"target":"url","constraint":{"operator":"matches","value":url_match}}]
    actions = [{"id":"forwarding_url","value":{"status_code":302,"url":url_forwarded}}]
    pagerule_for_redirection = {"status": "active","priority": 1,"actions": actions,"targets": targets}

    try:
        r = cf.zones.pagerules.get(zone_id, data=pagerule_for_redirection)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.pagerules.get %d %s - api call failed' % (e, e))

    create = True

    for rule in r:
        if (rule['actions'] == pagerule_for_redirection["actions"] and rule["targets"] == pagerule_for_redirection["targets"]):
            print('\t', '... rule already present!')
            create = False
            break

    if (create):
        try:
            r = cf.zones.pagerules.post(zone_id, data=pagerule_for_redirection)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.pagerules.post %d %s - api call failed' % (e, e))
        if (r['actions'] == pagerule_for_redirection["actions"] and r["targets"] == pagerule_for_redirection["targets"]):
            print('\t', '... created!')
    exit(0)

if __name__ == '__main__':
    main()
