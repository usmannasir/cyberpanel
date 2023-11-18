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
        dns_name = sys.argv[2]
    except IndexError:
        exit('usage: example_delete_zone_entry.py zone dns_record')

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        params = {'name':zone_name}
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones.get - %s - api call failed' % (e))

    if len(zones) == 0:
        exit('/zones.get - %s - zone not found' % (zone_name))

    if len(zones) != 1:
        exit('/zones.get - %s - api call returned %d items' % (zone_name, len(zones)))

    zone = zones[0]

    zone_id = zone['id']
    zone_name = zone['name']

    print('ZONE:', zone_id, zone_name)

    try:
        params = {'name':dns_name + '.' + zone_name}
        dns_records = cf.zones.dns_records.get(zone_id, params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/dns_records %s - %d %s - api call failed' % (dns_name, e, e))

    found = False
    for dns_record in dns_records:
        dns_record_id = dns_record['id']
        dns_record_name = dns_record['name']
        dns_record_type = dns_record['type']
        dns_record_value = dns_record['content']
        print('DNS RECORD:', dns_record_id, dns_record_name, dns_record_type, dns_record_value)

        try:
            dns_record = cf.zones.dns_records.delete(zone_id, dns_record_id)
            print('DELETED')
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.dns_records.delete %s - %d %s - api call failed' % (dns_name, e, e))
        found = True

    if not found:
        print('RECORD NOT FOUND')

    exit(0)

if __name__ == '__main__':
    main()

