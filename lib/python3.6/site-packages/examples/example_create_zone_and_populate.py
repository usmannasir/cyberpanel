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
        exit('usage: provide a zone name as an argument on the command line')

    cf = CloudFlare.CloudFlare()

    # Create zone - which will only work if ...
    # 1) The zone is not on Cloudflare.
    # 2) The zone passes a whois test
    print('Create zone %s ...' % (zone_name))
    try:
        zone_info = cf.zones.post(data={'jump_start':False, 'name': zone_name})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.post %s - %d %s' % (zone_name, e, e))
    except Exception as e:
        exit('/zones.post %s - %s' % (zone_name, e))

    zone_id = zone_info['id']
    if 'email' in zone_info['owner']:
        zone_owner = zone_info['owner']['email']
    else:
        zone_owner = '"' + zone_info['owner']['name'] + '"'
    zone_plan = zone_info['plan']['name']
    zone_status = zone_info['status']
    print('\t%s name=%s owner=%s plan=%s status=%s\n' % (
        zone_id,
        zone_name,
        zone_owner,
        zone_plan,
        zone_status
    ))

    # DNS records to create
    dns_records = [
        {'name':'ding', 'type':'A', 'content':'216.58.194.206'},
        {'name':'foo', 'type':'AAAA', 'content':'2001:d8b::1'},
        {'name':'foo', 'type':'A', 'content':'192.168.0.1'},
        {'name':'duh', 'type':'A', 'content':'10.0.0.1', 'ttl':120},
        {'name':'bar', 'type':'CNAME', 'content':'foo.%s' % (zone_name)}, # CNAME requires FQDN at content
        {'name':'shakespeare', 'type':'TXT', 'content':"What's in a name? That which we call a rose by any other name would smell as sweet."}
    ]

    print('Create DNS records ...')
    for dns_record in dns_records:
        # Create DNS record
        try:
            r = cf.zones.dns_records.post(zone_id, data=dns_record)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.dns_records.post %s %s - %d %s' % (zone_name, dns_record['name'], e, e))
        # Print respose info - they should be the same
        dns_record = r
        print('\t%s %30s %6d %-5s %s ; proxied=%s proxiable=%s' % (
            dns_record['id'],
            dns_record['name'],
            dns_record['ttl'],
            dns_record['type'],
            dns_record['content'],
            dns_record['proxied'],
            dns_record['proxiable']
        ))

        # set proxied flag to false - for example
        dns_record_id = dns_record['id']

        new_dns_record = {
            # Must have type/name/content (even if they don't change)
            'type':dns_record['type'],
            'name':dns_record['name'],
            'content':dns_record['content'],
            # now add new values you want to change
            'proxied':False
        }

        try:
            dns_record = cf.zones.dns_records.put(zone_id, dns_record_id, data=new_dns_record)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones/dns_records.put %d %s - api call failed' % (e, e))

    print('')

    # Now read back all the DNS records
    print('Read back DNS records ...')
    try:
        dns_records = cf.zones.dns_records.get(zone_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.dns_records.get %s - %d %s' % (zone_name, e, e))

    for dns_record in sorted(dns_records, key=lambda v: v['name']):
        print('\t%s %30s %6d %-5s %s ; proxied=%s proxiable=%s' % (
            dns_record['id'],
            dns_record['name'],
            dns_record['ttl'],
            dns_record['type'],
            dns_record['content'],
            dns_record['proxied'],
            dns_record['proxiable']
        ))

    print('')

    exit(0)

if __name__ == '__main__':
    main()

