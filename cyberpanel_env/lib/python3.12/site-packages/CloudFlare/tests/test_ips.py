""" ips tests """

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips():
    """ test_ips """
    # no auth required
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert isinstance(ips['ipv4_cidrs'], list)
    assert isinstance(ips['ipv6_cidrs'], list)
    assert len(ips['ipv4_cidrs']) > 0
    assert len(ips['ipv6_cidrs']) > 0

def test_ips_plus_jdcloud():
    """ test_ips_plus_jdcloud """
    # no auth required
    params = {'networks':'jdcloud'}
    ips = cf.ips(params=params)
    assert isinstance(ips, dict)
    assert isinstance(ips['ipv4_cidrs'], list)
    assert isinstance(ips['ipv6_cidrs'], list)
    assert isinstance(ips['jdcloud_cidrs'], list)
    assert len(ips['ipv4_cidrs']) > 0
    assert len(ips['ipv6_cidrs']) > 0
    assert len(ips['jdcloud_cidrs']) > 0

def test_ips_patch():
    """ test_ips_patch """
    # should fail!
    try:
        cf.ips.patch()
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

def test_ips_post():
    """ test_ips_post """
    # should fail!
    try:
        cf.ips.post()
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

def test_ips_put():
    """ test_ips_put """
    # should fail!
    try:
        cf.ips.put()
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

def test_ips_delete():
    """ test_ips_delete """
    # should fail!
    try:
        cf.ips.delete()
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

if __name__ == '__main__':
    test_cloudflare(debug=True)
    test_ips()
    test_ips_plus_jdcloud()
    test_ips_patch()
    test_ips_post()
    test_ips_put()
    test_ips_delete()
