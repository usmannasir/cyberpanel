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
        params = {'per_page':50}

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones - %s - api call failed' % (e))

    # there should only be one zone
    for zone in sorted(zones, key=lambda v: v['name']):
        zone_name = zone['name']
        zone_id = zone['id']
        try:
            certificates = cf.zones.ssl.certificate_packs.get(zone_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.ssl.certificate_packs %d %s - api call failed' % (e, e))

        for certificate in certificates:
            certificate_type = certificate['type']
            primary_certificate = certificate['primary_certificate']
            certificate_hosts = certificate['hosts']
            certificate_sig = certificate['certificates'][0]['signature']
            certificate_sig_count = len(certificate['certificates'])
            if certificate_sig_count > 1:
                c = certificate['certificates'][0]
                print('%-40s %-10s %-32s    %-15s [ %s ]' % (
                    zone_name,
                    certificate_type,
                    primary_certificate,
                    c['signature'],
                    ','.join(certificate_hosts)
                ))
                nn = 0
                for c in certificate['certificates']:
                    nn += 1
                    if nn == 1:
                        next
                    print('%-40s %-10s %-32s %2d:%-15s [ %s ]' % (
                        '',
                        '',
                        '',
                        nn,
                        c['signature'],
                        ''
                    ))
            else:
                for c in certificate['certificates']:
                    print('%-40s %-10s %-32s    %-15s [ %s ]' % (
                        zone_name,
                        certificate_type,
                        primary_certificate,
                        c['signature'],
                        ','.join(certificate_hosts)
                    ))

    exit(0)

if __name__ == '__main__':
    main()

