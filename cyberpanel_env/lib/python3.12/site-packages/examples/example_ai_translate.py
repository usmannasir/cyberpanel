#!/usr/bin/env python

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
import CloudFlare

use_find = False

def doit(account_name, english_text):

    # We set the timeout because these AI calls take longer than normal API calls
    cf = CloudFlare.CloudFlare(global_request_timeout=120)

    try:
        if account_name is None or account_name == '':
            params = {'per_page': 1}
        else:
            params = {'name': account_name, 'per_page': 1}
        accounts = cf.accounts.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/accounts %d %s - api call failed' % (e, e))

    try:
        account_id = accounts[0]['id']
    except IndexError:
        exit('%s: account name not found' % (account_name))

    translate_data = {
        'text': english_text,
        'source_lang': 'english',
        'target_lang': 'french',
    }

    try:
        if use_find:
            # you can use this format:
            r = cf.find('/accounts/:id/ai/run/@cf/meta/m2m100-1.2b').post(account_id, data=translate_data)
        else:
            # or you can use this format:
            # @'s are replaced by at_ so .../@cf/... becomes .../at_cf/... etc
            r = cf.accounts.ai.run.at_cf.meta.m2m100_1_2b.post(account_id, data=translate_data)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/ai.run %d %s - api call failed' % (e, e))

    print(r['translated_text'])

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '-a':
        del sys.argv[1]
        account_name = sys.argv[1]
        del sys.argv[1]
    else:
        account_name = None
    if len(sys.argv) > 1:
        english_text = ' '.join(sys.argv[1:])
    else:
        english_text = "I'll have an order of the moule frites"
    doit(account_name, english_text)

if __name__ == '__main__':
    main()
