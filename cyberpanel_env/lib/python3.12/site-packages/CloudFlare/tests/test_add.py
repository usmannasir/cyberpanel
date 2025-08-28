""" add to api tests """

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

def test_add_invalid():
    """ test_add_invalid """
    """add API commands"""
    cf.add('OPEN', 'invalid')
    try:
        results = cf.invalid()
        print('error - should not reach here', file=sys.stderr)
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # error 7000 No route for that URI
        print('Error expected: %d=%s' % (int(e), str(e)), file=sys.stderr)
        assert int(e) == 7000
        assert str(e) == 'No route for that URI'

def test_add_invalid_with_underscore():
    """add API commands"""
    cf.add('OPEN', 'in_valid')
    try:
        results = cf.in_valid()
        print('error - should not reach here', file=sys.stderr)
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # error 7000 No route for that URI
        print('Error expected: %d=%s' % (int(e), str(e)), file=sys.stderr)
        assert int(e) == 7000
        assert str(e) == 'No route for that URI'

def test_add_invalid_with_dash():
    """add API commands"""
    cf.add('OPEN', 'in-val-id')
    try:
        results = cf.in_val_id()
        print('error - should not reach here', file=sys.stderr)
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # error 7000 No route for that URI
        print('Error expected: %d=%s' % (int(e), str(e)), file=sys.stderr)
        assert int(e) == 7000
        assert str(e) == 'No route for that URI'

if __name__ == '__main__':
    test_cloudflare(debug=True)
    test_add_invalid()
    test_add_invalid_with_underscore()
    test_add_invalid_with_dash()
