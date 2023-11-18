#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import time
import datetime
import pytz

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def now_iso8601_time(h_delta):
    """Cloudflare API code - example"""

    t = time.time() - (h_delta * 3600)
    r = datetime.datetime.fromtimestamp(int(t), tz=pytz.timezone("UTC")).strftime('%Y-%m-%dT%H:%M:%SZ')
    return r

def main():
    """Cloudflare API code - example"""

    # Grab the zone name
    try:
        zone_name = sys.argv[1]
        params = {'name':zone_name, 'per_page':1}
    except IndexError:
        exit('usage: example_graphql zone')

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones - %s - api call failed' % (e))

    date_before = now_iso8601_time(0) # now
    date_after = now_iso8601_time(7 * 24) # 7 days worth

    zone_id = zones[0]['id']
    query="""
      query {
        viewer {
            zones(filter: {zoneTag: "%s"} ) {
            httpRequests1dGroups(limit:40, filter:{date_lt: "%s", date_gt: "%s"}) {
              sum { countryMap { bytes, requests, clientCountryName } }
              dimensions { date }
            }
          }
        }
      }
    """ % (zone_id, date_before[0:10], date_after[0:10]) # only use yyyy-mm-dd part for httpRequests1dGroups

    # query - always a post
    try:
        r = cf.graphql.post(data={'query':query})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/graphql.post %d %s - api call failed' % (e, e))

    ## only one zone, so use zero'th element!
    zone_info = r['data']['viewer']['zones'][0]

    httpRequests1dGroups = zone_info['httpRequests1dGroups']

    for h in sorted(httpRequests1dGroups, key=lambda v: v['dimensions']['date']):
        result_date = h['dimensions']['date']
        result_info = h['sum']['countryMap']
        print(result_date)
        for element in sorted(result_info, key=lambda v: -v['bytes']):
            print("    %7d %7d %2s" % (element['bytes'], element['requests'], element['clientCountryName']))

if __name__ == '__main__':
    main()
    exit(0)

