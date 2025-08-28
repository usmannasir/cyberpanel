""" test global_request_timeout and max_request_retries """

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

def test_ips1():
    """ test_ips1 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_with_global_request_timeout(debug=False):
    """ test_cloudflare_with_global_request_timeout """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug, global_request_timeout=10)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips2():
    """ test_ips2 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_with_max_request_retries(debug=False):
    """ test_cloudflare_with_max_request_retries """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug, max_request_retries=2)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips3():
    """ test_ips3 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_with_global_request_timeout_and_max_request_retries(debug=False):
    """ test_cloudflare_with_global_request_timeout_and_max_request_retries """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug, global_request_timeout=10, max_request_retries=2)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips4():
    """ test_ips4 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_with_global_request_timeout_invalid(debug=False):
    """ test_cloudflare_with_global_request_timeout_invalid """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug, global_request_timeout='STRING')
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips5():
    """ test_ips5 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_with_max_request_retries_invalid(debug=False):
    """ test_cloudflare_with_max_request_retries_invalid """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug, max_request_retries='STRING')
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips6():
    """ test_ips6 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_with_global_request_timeout_and_max_request_retries_invalid(debug=False):
    """ test_cloudflare_with_global_request_timeout_and_max_request_retries_invalid """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug, global_request_timeout='STRING', max_request_retries='STRING')
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips7():
    """ test_ips7 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

if __name__ == '__main__':
    test_cloudflare(debug=True)
    test_ips1()
    test_cloudflare_with_global_request_timeout(debug=True)
    test_ips2()
    test_cloudflare_with_max_request_retries(debug=True)
    test_ips3()
    test_cloudflare_with_global_request_timeout_and_max_request_retries(debug=True)
    test_ips4()
    test_cloudflare_with_global_request_timeout_invalid(debug=True)
    test_ips5()
    test_cloudflare_with_max_request_retries_invalid(debug=True)
    test_ips6()
    test_cloudflare_with_global_request_timeout_and_max_request_retries_invalid(debug=True)
    test_ips7()
