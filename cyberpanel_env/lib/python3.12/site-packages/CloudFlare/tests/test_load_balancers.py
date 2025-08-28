""" workers tests """

import os
import sys
import uuid
import random

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test /accounts/:id/workers/scripts

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

account_name = None
account_id = None

def test_find_account(find_name=None):
    """ test_find_account """
    global account_name, account_id
    # grab a random account identifier from the first 10 accounts
    if find_name:
        params = {'per_page':1, 'name':find_name}
    else:
        params = {'per_page':10}
    try:
        accounts = cf.accounts.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('%s: Error %d=%s' % (find_name, int(e), str(e)), file=sys.stderr)
        assert False
    assert len(accounts) > 0 and len(accounts) <= 10
    # n = random.randrange(len(accounts))
    # stop using a random account - use the primary account (i.e. the zero'th one)
    n = 0
    account_name = accounts[n]['name']
    account_id = accounts[n]['id']
    assert len(account_id) == 32
    print('account: %s %s' % (account_id, account_name), file=sys.stderr)

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

def test_load_balancers_list_regions():
    """ test_load_balancers_list_regions """
    regions = cf.accounts.load_balancers.regions(account_id)
    assert isinstance(regions, dict)
    assert 'regions' in regions
    assert 'iso_standard' in regions
    assert isinstance(regions['regions'], list)
    assert isinstance(regions['iso_standard'], str)
    for region in regions['regions']:
        assert 'countries' in region
        assert 'region_code' in region
        assert isinstance(region['countries'], list)
        assert isinstance(region['region_code'], str)
        countries = ','.join([v['country_code_a2'] for v in region['countries']])
        print('/accounts/load_balancers/regions: %s: %s' % (region['region_code'], countries), file=sys.stderr)

def test_load_balancers_get_regions():
    """ test_load_balancers_get_regions """
    regions = cf.accounts.load_balancers.regions(account_id, 'WNAM')
    assert isinstance(regions, dict)
    assert 'regions' in regions
    assert 'iso_standard' in regions
    assert isinstance(regions['regions'], list)
    assert isinstance(regions['iso_standard'], str)
    for region in regions['regions']:
        assert 'countries' in region
        assert 'region_code' in region
        assert isinstance(region['countries'], list)
        assert isinstance(region['region_code'], str)
        countries = ','.join([v['country_code_a2'] for v in region['countries']])
        print('/accounts/load_balancers/regions: %s: %s' % (region['region_code'], countries), file=sys.stderr)

def test_load_balancers_search():
    """ test_load_balancers_search """
    r = cf.accounts.load_balancers.search(account_id)
    assert isinstance(r, dict)
    assert 'resources' in r
    assert isinstance(r['resources'], list)
    if len(r['resources']) == 0:
        print('/account/load_balancers/search: returns zero results', file=sys.stderr)
        return
    for resource in r['resources']:
        assert 'reference_type' in r
        assert isinstance(r['reference_type'], str)
        assert 'resource_id' in r
        assert isinstance(r['resource_id'], str)
        assert 'resource_name' in r
        assert isinstance(r['resource_name'], str)
        assert 'resource_type' in r
        assert isinstance(r['resource_type'], str)
        print('/account/load_balancers/search: %s: %s' % (r['resource_id'], r['resource_name']), file=sys.stderr)

def test_load_balancers_pools():
    """ test_load_balancers_pools """
    pools = cf.accounts.load_balancers.pools(account_id)
    assert isinstance(pools, list)
    for pool in pools:
        assert isinstance(pool, dict)
        assert 'id' in pool
        print('/accounts/load_balancers/pools: %s: %s length=%d' % (pool['id'], pool['name'], len(pool['origins'])), file=sys.stderr)

pool_id = None

def test_load_balancers_pool_create():
    """ test_load_balancers_pool_create """
    global pool_id
    origin_name = str(uuid.uuid1())
    pool_name = str(uuid.uuid1())
    origins_data = [
        # Yes yes yes - we know these are Google's addresses - but that's ok
        {'address':'8.8.8.101', 'name':origin_name + '_1'},
        {'address':'8.8.8.102', 'name':origin_name + '_2'},
        {'address':'8.8.8.103', 'name':origin_name + '_3'},
    ]
    pool_data = {'description':'testing123', 'name':pool_name, 'origins':origins_data}
    try:
        pool = cf.accounts.load_balancers.pools.post(account_id, data=pool_data)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # this happens when the account isn't setup for load balancers
        pool_id = None
        return
    assert isinstance(pool, dict)
    assert 'id' in pool
    print('/accounts/load_balancers/pools: POST: %s: %s length=%d' % (pool['id'], pool['name'], len(pool['origins'])), file=sys.stderr)
    pool_id = pool['id']
    print('pool_id =', pool_id)

def test_load_balancers_pool_details():
    """ test_load_balancers_pool_details """
    if pool_id is None:
        print('/accounts/load_balancers/pools: skip', file=sys.stderr)
        return
    pool = cf.accounts.load_balancers.pools(account_id, pool_id)
    assert isinstance(pool, dict)
    assert 'id' in pool
    print('/accounts/load_balancers/pools: %s: %s length=%d' % (pool['id'], pool['name'], len(pool['origins'])), file=sys.stderr)
    assert pool_id == pool['id']

load_balancer_id = None

def test_load_balancers_create():
    """ test_load_balancers_create """
    global load_balancer_id
    if pool_id is None:
        print('/zones/load_balancers: POST: skip', file=sys.stderr)
        load_balancer_id = None
        return
    dns_name = str(uuid.uuid1())
    balancer_data = {
        'default_pools': [pool_id],
        'fallback_pool': pool_id,
        'name': dns_name + '.' + zone_name,
        'description': dns_name,
    }
    try:
        load_balancer = cf.zones.load_balancers.post(zone_id, data=balancer_data)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # this happens when the zone isn't setup for load balancers
        print('/zones/load_balancers: POST: skip', file=sys.stderr)
        load_balancer_id = None
        return
    assert isinstance(load_balancer, dict)
    assert 'default_pools' in load_balancer
    assert 'fallback_pool' in load_balancer
    assert 'id' in load_balancer
    load_balancer_id = load_balancer['id']
    print('/zones/load_balancers: POST: %s %s' % (load_balancer['id'], load_balancer['name']), file=sys.stderr)

def test_load_balancers_pool_health():
    """ test_load_balancers_pool_health """
    if pool_id is None:
        print('/accounts/load_balancers/pools/health: skip', file=sys.stderr)
        return
    try:
        health = cf.accounts.load_balancers.pools.health(account_id, pool_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # the new loadbalancer will not be ready - which is ok
        print('/accounts/load_balancers/pools/health: Error expected: %d %s' % (int(e), str(e)), file=sys.stderr)
        return
    assert isinstance(health, dict)
    assert 'pool_id' in health
    assert isinstance(health['pool_id'], str)
    assert isinstance(health['pop_health'], dict)
    print('/accounts/load_balancers/pools/health: %s: length=%d' % (health['pool_id'], len(health['pop_health'])), file=sys.stderr)
    assert pool_id == health['pool_id']

def test_load_balancers_pool_delete_should_fail():
    """ test_load_balancers_pool_delete_should_fail """
    if pool_id is None or load_balancer_id is None:
        print('/accounts/load_balancers/pools: DELETE: skip', file=sys.stderr)
        return
    try:
        pool = cf.accounts.load_balancers.pools.delete(account_id, pool_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # the new loadbalancer can not be deleted as it's in use with a zone
        print('/accounts/load_balancers/pools: DELETE: Error expected: %d %s' % (int(e), str(e)), file=sys.stderr)
        return
    assert 'id' in pool
    print('/accounts/load_balancers/pools: DELETE: %s: deleted' % (pool['id']), file=sys.stderr)
    assert pool_id == pool['id']
    assert False

def test_load_balancers_delete():
    """ test_load_balancers_delete """
    if load_balancer_id is None:
        print('/zones/load_balancers: DELETE: skip', file=sys.stderr)
        return
    r = cf.zones.load_balancers.delete(zone_id, load_balancer_id)
    assert isinstance(r, dict)
    assert 'id' in r
    print('/zones/load_balancers: DELETE: %s: deleted' % (r['id']), file=sys.stderr)
    assert load_balancer_id == r['id']

def test_load_balancers_pool_delete():
    """ test_load_balancers_pool_delete """
    if pool_id is None:
        print('/accounts/load_balancers/pools: DELETE: skip', file=sys.stderr)
        return
    pool = cf.accounts.load_balancers.pools.delete(account_id, pool_id)
    assert isinstance(pool, dict)
    assert 'id' in pool
    print('/accounts/load_balancers/pools: DELETE: %s: deleted' % (pool['id']), file=sys.stderr)
    assert pool_id == pool['id']

if __name__ == '__main__':
    test_cloudflare(debug=False)
    if len(sys.argv) > 1:
        test_find_account(sys.argv[1])
    else:
        test_find_account()
    if len(sys.argv) > 2:
        test_find_zone(sys.argv[2])
    else:
        test_find_zone()
    test_load_balancers_list_regions()
    test_load_balancers_get_regions()
    test_load_balancers_search()
    test_load_balancers_pools()
    test_load_balancers_pool_create()
    test_load_balancers_pool_details()
    test_load_balancers_create()
    test_load_balancers_pool_health()
    test_load_balancers_pool_delete_should_fail()
    test_load_balancers_delete()
    test_load_balancers_pool_delete()
