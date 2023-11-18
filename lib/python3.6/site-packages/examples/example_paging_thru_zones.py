#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    cf = CloudFlare.CloudFlare(raw=True)

    page_number = 0
    while True: 
        page_number += 1
        try:
            raw_results = cf.zones.get(params={'per_page':5,'page':page_number})
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.get %d %s - api call failed' % (e, e))

        zones = raw_results['result']
        domains = []
        for zone in zones:
            zone_id = zone['id']
            zone_name = zone['name']
            domains.append(zone_name)

        count = raw_results['result_info']['count']
        page = raw_results['result_info']['page']
        per_page = raw_results['result_info']['per_page']
        total_count = raw_results['result_info']['total_count']
        total_pages = raw_results['result_info']['total_pages']

        print("COUNT=%d PAGE=%d PER_PAGE=%d TOTAL_COUNT=%d TOTAL_PAGES=%d -- %s" % (count, page, per_page, total_count, total_pages, domains))

        if page_number == total_pages:
            break

if __name__ == '__main__':
    main()

