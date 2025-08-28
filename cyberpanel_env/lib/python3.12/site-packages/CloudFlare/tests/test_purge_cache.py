""" get/post/delete/etc zone ruleset based tests """

import os
import sys
import uuid
import random

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test purge_cache

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

zone_name = None
zone_id = None
zone_type = None

def test_find_zone(domain_name=None):
    """ test_find_zone """
    global zone_name, zone_id, zone_type
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
    zone_type = zones[0]['plan']['name']
    assert len(zone_id) == 32
    print('zone: %s %s' % (zone_id, zone_name), file=sys.stderr)

def create_purge_zone_data():
    """ create_purge_zone_data """
    if 'Enterprise' in zone_type:
        # Enterprise accounts can do all things ...
        fake_tag = 'tag-' + str(uuid.uuid1())
        data = {
            # 'purge_everything': True,
            'hosts': [zone_name],
            'tags': [fake_tag],
            'prefixes': [zone_name + '/' + 'index.html'],
        }
    else:
        # Free, Pro, Business accounts can only do this ...
        data = {
            'purge_everything': True
        }
    return data

def test_purge_cache_post():
    """ test_purge_cache_post """
    r = cf.zones.purge_cache.post(zone_id, data=create_purge_zone_data())
    assert isinstance(r, dict)
    assert 'id' in r
    assert r['id'] == zone_id

def test_purge_cache_delete():
    """ test_purge_cache_delete """
    # delete method is not in documents; however, it works
    r = cf.zones.purge_cache.delete(zone_id, data=create_purge_zone_data())
    assert isinstance(r, dict)
    assert 'id' in r
    assert r['id'] == zone_id

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_zone(sys.argv[1])
    else:
        test_find_zone()
    test_purge_cache_post()
    test_purge_cache_delete()
