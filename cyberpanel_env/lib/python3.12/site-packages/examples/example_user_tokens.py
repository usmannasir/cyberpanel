#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    #
    # Usage: examples/example_user_tokens.py [config file profile name]
    #
    # Store your access token in the config file as-per the README ("Cloudflare" is the default).
    #
    # $ cat ~/.cloudflare/cloudflare.cfg
    # [Work]
    # token = 00000000000000000000000000000000
    # [Home]
    # email = home@example.com
    # token = 00000000000000000000000000000000
    # $
    #

    try:
        profile_id = sys.argv[1]
    except IndexError:
        profile_id = None

    cf = CloudFlare.CloudFlare(profile=profile_id)

    # display all the users tokens
    try:
        v = cf.user.tokens()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('/user.tokens.get %d %s - api call failed' % (e, e))
        v = None
    except Exception as e:
        exit('/user.tokens.get - %s - api call failed' % (e))

    if v:
        print('TOKENS:')
        for t in v:
            print('  %s %s [%-20s %-20s %-20s] %d %s' % (
                t['id'],
                t['status'],
                t['issued_on'],
                t['modified_on'],
                t['last_used_on'],
                len(t['policies']),
                t['name']
            ))
        print('')

    # verify the user token being used (vs. email/key - this will throw an exception if it's not valid
    try:
        v = cf.user.tokens.verify()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # exit('/user.tokens.verify.get %d %s - api call failed' % (e, e))
        v = None
    except Exception as e:
        exit('/user.tokens.verify.get - %s - api call failed' % (e))

    if v:
        print('VERIFYED TOKENS')
        print(' %s %-10s [%-20s %-20s]' % (
            v['id'],
            v['status'],
            v['not_before'] if 'not_before' in v else '',
            v['expires_on'] if 'expires_on' in v else ''
        ))
    else:
        print('User token not verified - i.e invalid (or not used)')

    exit(0)

if __name__ == '__main__':
    main()
