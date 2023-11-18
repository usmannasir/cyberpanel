#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    cf = CloudFlare.CloudFlare()
    try:
        ips = cf.ips.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/ips - %d %s' % (e, e))
    except Exception as e:
        exit('/ips - %s - api call connection failed' % (e))

    print('ipv4_cidrs count = ', len(ips['ipv4_cidrs']))
    for cidr in sorted(set(ips['ipv4_cidrs'])):
        print('\t', cidr)
    print('ipv6_cidrs count = ', len(ips['ipv6_cidrs']))
    for cidr in sorted(set(ips['ipv6_cidrs'])):
        print('\t', cidr)
    exit(0)

if __name__ == '__main__':
    main()

