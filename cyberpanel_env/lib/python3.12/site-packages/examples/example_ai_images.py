#!/usr/bin/env python

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
import CloudFlare

use_find = False

def doit(account_name, prompt_text):

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

    image_create_data = {
        'prompt': prompt_text,
    }

    try:
        if use_find:
            # you can use this format:
            r = cf.find('/accounts/:id/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0').post(account_id, data=image_create_data)
        else:
            # or you can use this format:
            # @'s are replaced by at_ so .../@cf/... becomes .../at_cf/... etc
            r = cf.accounts.ai.run.at_cf.stabilityai.stable_diffusion_xl_base_1_0.post(account_id, data=image_create_data)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/ai.run %d %s - api call failed' % (e, e))

    sys.stdout.buffer.write(r)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '-a':
        del sys.argv[1]
        account_name = sys.argv[1]
        del sys.argv[1]
    else:
        account_name = None
    if len(sys.argv) > 1:
        prompt_text = ' '.join(sys.argv[1:])
    else:
        prompt_text = "A happy llama running through an orange cloud"
    doit(account_name, prompt_text)

if __name__ == '__main__':
    main()
