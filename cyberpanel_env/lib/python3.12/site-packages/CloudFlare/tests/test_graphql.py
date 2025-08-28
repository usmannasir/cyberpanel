""" graphql tests """

import os
import sys
import random
import datetime
import pytz
import json

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test /graphql

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

zone_name = None
zone_id = None

def test_find_zone(domain_name=None):
    """ test_find_zone """
    global zone_name, zone_id
    # grab a random zone identifier from the first 10 zones
    if domain_name:
        params = {'per_page':1, 'name':domain_name}
    else:
        params = {'per_page':10}
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('%s: Error %d=%s' % (domain_name, int(e), str(e)), file=sys.stderr)
        assert False
    assert len(zones) > 0 and len(zones) <= 10
    n = random.randrange(len(zones))
    zone_name = zones[n]['name']
    zone_id = zones[n]['id']
    assert len(zone_id) == 32
    print('zone: %s %s' % (zone_id, zone_name), file=sys.stderr)

def rfc3339_iso8601_time(hour_delta=0, with_hms=False):
    # format time (with an hour offset in RFC3339 or ISO8601 format (and do it UTC time)
    if sys.version_info[:3][0] <= 3 and sys.version_info[:3][1] <= 10:
        dt = datetime.datetime.utcnow().replace(microsecond=0, tzinfo=pytz.UTC)
    else:
        dt = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    dt += datetime.timedelta(hours=hour_delta)
    if with_hms:
        return dt.isoformat().replace('+00:00', 'Z')
    return dt.strftime('%Y-%m-%d')

def test_graphql_get():
    """ /graphql_get test """
    try:
        # graphql is alwatys a post - this should fail (but presently doesn't)
        r = cf.graphql.get()
        if r is not None and 'data' in r and 'errors' in r:
            # still an invalid API!
            print('Error in API (but proceeding) r=', r, file=sys.stderr)
            assert True
        else:
            assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)
        assert True

def test_graphql_patch():
    """ /graphql_patch test """
    try:
        # graphql is alwatys a post - this should fail (but presently doesn't)
        r = cf.graphql.patch()
        if r is not None and 'data' in r and 'errors' in r:
            # still an invalid API!
            print('Error in API (but proceeding) r=', r, file=sys.stderr)
            assert True
        else:
            assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)
        assert True

def test_graphql_put():
    """ /graphql_put test """
    try:
        # graphql is alwatys a post - this should fail (but presently doesn't)
        r = cf.graphql.put()
        if r is not None and 'data' in r and 'errors' in r:
            # still an invalid API!
            print('Error in API (but proceeding) r=', r, file=sys.stderr)
            assert True
        else:
            assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)
        assert True

def test_graphql_delete():
    """ /graphql_delete test """
    try:
        # graphql is alwatys a post - this should fail (but presently doesn't)
        r = cf.graphql.delete()
        if r is not None and 'data' in r and 'errors' in r:
            # still an invalid API!
            print('Error in API (but proceeding) r=', r, file=sys.stderr)
            assert True
        else:
            assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)
        assert True

def test_graphql_post_empty():
    """ /graphql_post_empty test """
    try:
        # graphql requires data - this should fail (but presently doesn't)
        r = cf.graphql.post(data={})
        if r is not None and 'data' in r and 'errors' in r:
            # still an invalid API!
            print('Error in API (but proceeding) r=', r, file=sys.stderr)
            assert True
        else:
            assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)
        assert True

def test_graphql_post():
    """ /graphql_post test """
    date_before = rfc3339_iso8601_time(0) # now
    date_after = rfc3339_iso8601_time(-3 * 24) # 3 days worth

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

    # remove whitespace from query - this isn't needed; but helps debug
    query = '\n'.join([s.strip() for s in query.splitlines()]).strip()

    # graphql query is always a post
    try:
        r = cf.graphql.post(data={'query':query})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('%s: Error %d=%s' % ('/graphql.post', int(e), str(e)), file=sys.stderr)
        assert False

    # success - lets confirm it's graphql results as-per query above

    # basic graphql results
    assert 'data' in r
    assert 'errors' in r
    assert r['errors'] is None

    # viewer and zones from above
    assert 'viewer' in r['data']
    assert 'zones' in r['data']['viewer']

    # only one zone
    zones = r['data']['viewer']['zones']
    assert len(zones) == 1
    zone_info = zones[0]

    # the data
    assert 'httpRequests1dGroups' in zone_info
    httpRequests1dGroups = zone_info['httpRequests1dGroups']
    assert isinstance(httpRequests1dGroups, list)
    for h in httpRequests1dGroups:
        assert 'dimensions' in h
        assert 'date' in h['dimensions']
        result_date = h['dimensions']['date']
        assert 'sum' in h
        result_sum = h['sum']
        assert 'countryMap' in result_sum
        countryMap = h['sum']['countryMap']
        for element in countryMap:
            assert 'bytes' in element
            assert 'requests' in element
            assert 'clientCountryName' in element

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_zone(sys.argv[1])
    else:
        test_find_zone()
    test_graphql_get()
    test_graphql_put()
    test_graphql_patch()
    test_graphql_delete()
    test_graphql_post_empty()
    test_graphql_post()
