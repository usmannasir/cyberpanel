""" graphql tests """

import os
import sys
import random

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test /zones/:id/logs/received

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

def test_logs_received():
    """ /zones/:id/logs/received test """

    # python -m cli4 -v zones/:$zone/logs/received
    try:
        r = cf.zones.logs.received.get(zone_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('%s: Error %d=%s' % ('/zones.logs.received.get', int(e), str(e)), file=sys.stderr)
        assert False
    # XXX/TODO - sadly this call returns all manner of weird stuff - we punt for now
    assert r is not None

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_zone(sys.argv[1])
    else:
        test_find_zone()
    test_logs_received()
