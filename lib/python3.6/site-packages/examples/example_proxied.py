#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Change the proxied value on a FQDN"""

    try:
        zone_name = sys.argv[1]
        dns_name = sys.argv[2]
        if sys.argv[3] == 'false':
            new_r_proxied_flag = False
        elif sys.argv[3] == 'true':
            new_r_proxied_flag = True
        else:
            raise ValueError('bad arg')
    except IndexError:
        exit('usage: ./example-make-zone-proxied.py zone dns_record [true|false]')
    except ValueError:
        exit('usage: ./example-make-zone-proxied.py zone dns_record [true|false]')

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        params = {'name':zone_name, 'per_page':1}
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones.get - %s - api call failed' % (e))

    if len(zones) != 1:
        exit('/zones.get - %s - api call returned %d items' % (zone_name, len(zones)))

    # there should only be one zone
    zone = zones[0]

    zone_name = zone['name']
    zone_id = zone['id']

    print("Zone:\t%s %s" % (zone_id, zone_name))

    try:
        params = {'name': dns_name}
        dns_records = cf.zones.dns_records.get(zone_id, params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/dns_records.get %d %s - api call failed' % (e, e))

    if len(dns_records) == 0:
        exit('/zones.dns_records.get - %s - no records found' % (dns_name))

    for dns_record in dns_records:
        r_zone_id = dns_record['zone_id']
        r_id = dns_record['id']
        r_name = dns_record['name']
        r_type = dns_record['type']
        r_content = dns_record['content']
        r_ttl = dns_record['ttl']
        r_proxied = dns_record['proxied']
        r_proxiable = dns_record['proxiable']
        print('Record:\t%s %s %s %6d %-5s %s ; proxied=%s proxiable=%s' % (
            r_zone_id, r_id, r_name, r_ttl, r_type, r_content, r_proxied, r_proxiable
        ))

        if r_proxied == new_r_proxied_flag:
            # Nothing to do
            continue

        dns_record_id = dns_record['id']

        new_dns_record = {
            'zone_id': r_zone_id,
            'id': r_id,
            'type': r_type,
            'name': r_name,
            'content': r_content,
            'ttl': r_ttl,
            'proxied': new_r_proxied_flag
        }

        try:
            dns_record = cf.zones.dns_records.put(zone_id, dns_record_id, data=new_dns_record)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones/dns_records.put %d %s - api call failed' % (e, e))

        r_zone_id = dns_record['zone_id']
        r_id = dns_record['id']
        r_name = dns_record['name']
        r_type = dns_record['type']
        r_content = dns_record['content']
        r_ttl = dns_record['ttl']
        r_proxied = dns_record['proxied']
        r_proxiable = dns_record['proxiable']
        print('Record:\t%s %s %s %6d %-5s %s ; proxied=%s proxiable=%s <<-- after' % (
            r_zone_id, r_id, r_name, r_ttl, r_type, r_content, r_proxied, r_proxiable
        ))

    exit(0)

if __name__ == '__main__':
    main()

