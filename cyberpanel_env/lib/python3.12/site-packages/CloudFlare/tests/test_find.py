""" find api tests """

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test API list fetches from Cloudflare website

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_find():
    """ test_find """
    ips_call = cf.find('/ips')
    assert True

def test_find_call():
    """ test_find """
    ips_call = cf.find('/ips')
    ips = ips_call()
    assert isinstance(ips, dict)
    assert isinstance(ips['ipv4_cidrs'], list)
    assert isinstance(ips['ipv6_cidrs'], list)
    assert len(ips['ipv4_cidrs']) > 0
    assert len(ips['ipv6_cidrs']) > 0

def test_find_invalid():
    """ test_find """
    try:
        invalid_endpoint_call = cf.find('/invalid-endpoint')
        print('error - should not reach here', file=sys.stderr)
        assert False
    except AttributeError as e:
        assert True

if __name__ == '__main__':
    test_cloudflare(debug=True)
    test_find()
    test_find_call()
    test_find_invalid()
