#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import datetime

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def rfc3339_iso8601_time(hour_delta=0, with_hms=False):
    """ rfc3339_iso8601_time """
    # format time (with an hour offset in RFC3339 ISO8601 format (and do it UTC time)
    dt = (datetime.datetime.now(datetime.UTC).replace(microsecond=0) + datetime.timedelta(hours=hour_delta))
    if with_hms:
        return dt.isoformat().replace('+00:00', 'Z')
    return dt.strftime('%Y-%m-%d')

def main():
    """Cloudflare API code - example"""

    # Grab the zone name
    try:
        zone_name = sys.argv[1]
        params = {'name':zone_name, 'per_page':1}
    except IndexError:
        sys.exit('usage: example_graphql zone')

    cf = CloudFlare.CloudFlare()

    # grab the zone identifier
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        sys.exit('/zones.get %d %s - api call failed' % (int(e), str(e)))

    date_before = rfc3339_iso8601_time(0) # now
    date_after = rfc3339_iso8601_time(-7 * 24) # 7 previous days worth

    zone_id = zones[0]['id']
    query = """
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
    """ % (zone_id, date_before, date_after)

    # query - always a post
    try:
        r = cf.graphql.post(data={'query':query})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        sys.exit('/graphql.post %d %s - api call failed' % (int(e), str(e)))

    # only one zone, so use zero'th element!
    zone_info = r['data']['viewer']['zones'][0]

    http_requests1d_groups = zone_info['httpRequests1dGroups']

    for h in sorted(http_requests1d_groups, key=lambda v: v['dimensions']['date']):
        result_date = h['dimensions']['date']
        result_info = h['sum']['countryMap']
        print(result_date)
        for element in sorted(result_info, key=lambda v: -v['bytes']):
            print("    %7d %7d %2s" % (element['bytes'], element['requests'], element['clientCountryName']))

if __name__ == '__main__':
    main()
    sys.exit(0)
