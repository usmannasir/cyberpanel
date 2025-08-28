""" class calling tests """

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test Cloudflare init param (ie. debug, raw, etc)

cf = None

def test_cloudflare():
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare()
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_percent_s():
    """ test_percent_s """
    s = '%s' % cf
    assert len(s) > 0 and isinstance(s, str)

def test_percent_r():
    """ test_percent_r """
    s = '%r' % cf
    assert len(s) > 0 and isinstance(s, str)

def test_percent_ips_s():
    """ test_percent_ips_s """
    s = '%s' % cf.ips
    assert len(s) > 0 and isinstance(s, str)

def test_percent_ips_r():
    """ test_percent_ips_r """
    s = '%r' % cf.ips
    assert len(s) > 0 and isinstance(s, str)

def test_percent_cf_accounts_billing_s():
    """ test_percent_cf_accounts_billing_s """
    s = '%s' % cf.accounts.billing
    assert len(s) > 0 and isinstance(s, str)

def test_percent_cf_accounts_billing_r():
    """ test_percent_cf_accounts_billing_r """
    s = '%r' % cf.accounts.billing
    assert len(s) > 0 and isinstance(s, str)

def test_percent_cf_zones_waiting_rooms_events_details_s():
    """ test_percent_cf_accounts_billing_s """
    s = '%s' % cf.zones.waiting_rooms.events.details
    assert len(s) > 0 and isinstance(s, str)

def test_percent_cf_zones_waiting_rooms_events_details_r():
    """ test_percent_cf_accounts_billing_r """
    s = '%r' % cf.zones.waiting_rooms.events.details
    assert len(s) > 0 and isinstance(s, str)

def test_ips1():
    """ test_ips1 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_debug():
    """ test_cloudflare_debug """
    global cf
    cf = CloudFlare.CloudFlare(debug=True)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips2():
    """ test_ips2 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_raw():
    """ test_cloudflare_raw """
    global cf
    cf = CloudFlare.CloudFlare(raw=False)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips3():
    """ test_ips3 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_no_sessions():
    """ test_cloudflare_no_sessions """
    global cf
    cf = CloudFlare.CloudFlare(use_sessions=False)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_ips4():
    """ test_ips4 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_ips5():
    """ test_ips5 """
    ips = cf.ips()
    assert isinstance(ips, dict)
    assert len(ips) > 0

def test_cloudflare_url_invalid():
    """ test_cloudflare_url_invalid """
    global cf
    cf = CloudFlare.CloudFlare(base_url='blah blah blah blah ...')
    # this does not fail yet - so we wait

def test_ips6_should_fail():
    """ test_ips6_should_fail """
    try:
        ips = cf.ips()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s %d %s' % (type(e).__name__, int(e), str(e)), file=sys.stderr)
        pass
    except Exception as e:
        print('Error expected: %s %s' % (type(e).__name__, e), file=sys.stderr)
        pass

def test_cloudflare_url_wrong():
    """ test_cloudflare_url_wrong """
    global cf
    cf = CloudFlare.CloudFlare(base_url='http://example.com/')
    # this does not fail yet - so we wait

def test_ips7_should_fail():
    """ test_ips7_should_fail """
    try:
        ips = cf.ips()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %s %d %s' % (type(e).__name__, int(e), str(e)), file=sys.stderr)
        pass
    except Exception as e:
        print('Error expected: %s %s' % (type(e).__name__, e), file=sys.stderr)
        pass

def test_cloudflare_email_invalid():
    """ test_cloudflare_email_invalid """
    global cf
    try:
        cf = CloudFlare.CloudFlare(email=int(0))
        assert False
    except TypeError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

def test_cloudflare_key_invalid():
    """ test_cloudflare_key_invalid """
    global cf
    try:
        cf = CloudFlare.CloudFlare(key=int(0))
        assert False
    except TypeError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

def test_cloudflare_token_invalid():
    """ test_cloudflare_token_invalid """
    global cf
    try:
        cf = CloudFlare.CloudFlare(token=int(0))
        assert False
    except TypeError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

def test_cloudflare_certtoken_invalid():
    """ test_cloudflare_certtoken_invalid """
    global cf
    try:
        cf = CloudFlare.CloudFlare(certtoken=int(0))
        assert False
    except TypeError as e:
        print('Error expected: %s' % (e), file=sys.stderr)

def test_cloudflare_context():
    """ test_cloudflare_context """
    global cf
    cf = None
    with CloudFlare.CloudFlare() as cf:
        assert isinstance(cf, CloudFlare.CloudFlare)
        ips = cf.ips()
        assert isinstance(ips, dict)
        assert len(ips) > 0

if __name__ == '__main__':
    test_cloudflare()
    test_percent_s()
    test_percent_r()
    test_percent_ips_s()
    test_percent_ips_r()
    test_percent_cf_accounts_billing_s()
    test_percent_cf_accounts_billing_r()
    test_percent_cf_zones_waiting_rooms_events_details_s()
    test_percent_cf_zones_waiting_rooms_events_details_r()
    test_ips1()
    test_cloudflare_debug()
    test_ips2()
    test_cloudflare_raw()
    test_ips3()
    test_cloudflare_no_sessions()
    test_ips4()
    test_ips5()

    test_cloudflare_url_wrong()
    test_ips6_should_fail()

    test_cloudflare_url_invalid()
    test_ips7_should_fail()

    test_cloudflare_email_invalid()
    test_cloudflare_key_invalid()
    test_cloudflare_token_invalid()
    test_cloudflare_certtoken_invalid()

    test_cloudflare_context()
