#!/usr/bin/env python

import os
import sys
import random
import tempfile
import requests

sys.path.insert(0, os.path.abspath('.'))
import CloudFlare

use_find = False

def user_agent():
    s = random.choice([
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36 Edg/91.0.864.48',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36',
    ])
    return s

def doit(account_name, audio_data):

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

    try:
        if use_find:
            # you can use this format:
            r = cf.find('/accounts/:id/ai/run/@cf/openai/whisper').post(account_id, data=audio_data)
        else:
            # or you can use this format:
            # @'s are replaced by at_ so .../@cf/... becomes .../at_cf/...
            r = cf.accounts.ai.run.at_cf.openai.whisper.post(account_id, data=audio_data)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/ai.run %d %s - api call failed' % (e, e))

    print('%s' % (r['text']))
    # words = [word['word'] for word in r['words']]
    # print('%s' % ('|'.join(words)))

# based on ... thank you to the author
# https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
def download_audio_file(url, referer, n_requested):
    headers = {}
    headers['Referer'] = referer
    headers['User-Agent'] = user_agent()

    # will be deleted once program exits
    fp = tempfile.TemporaryFile(mode='w+b')

    n_received = 0
    # NOTE the stream=True parameter below
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=16*1024):
            fp.write(chunk)
            n_received += len(chunk)
            if n_received > n_requested:
                break

    # rewind the file so it's ready to read
    fp.seek(0)
    return fp

def default_audio_clip():

    s = random.choice([
        (
            'https://www.americanrhetoric.com/mp3clipsXE/barackobama/barackobamapresidentialfarewellARXE.mp3',
            'https://www.americanrhetoric.com/barackobamaspeeches.htm'
        ),
        (
            'https://archive.org/download/DoNotGoGentleIntoThatGoodNight/gentle.ogg',
	    'https://archive.org/details/DoNotGoGentleIntoThatGoodNight'
	),
        (
            'https://www.nasa.gov/wp-content/uploads/2015/01/590333main_ringtone_eagleHasLanded_extended.mp3',
	    'https://www.nasa.gov/audio-and-ringtones/'
	),
        (
            'https://www.nasa.gov/wp-content/uploads/2015/01/590331main_ringtone_smallStep.mp3',
	    'https://www.nasa.gov/audio-and-ringtones/'
	),
        (
            'https://upload.wikimedia.org/wikipedia/en/7/7f/George_Bush_1988_No_New_Taxes.ogg',
	    'https://en.wikipedia.org/wiki/File:George_Bush_1988_No_New_Taxes.ogg'
	),
        (
            'https://archive.org/download/grand_meaulnes_2004_librivox/grandmeaulnes_01_alainfournier.mp3',
	    'https://archive.org/details/grand_meaulnes_2004_librivox/grandmeaulnes_01_alainfournier_128kb.mp3'
	),
    ])

    return s

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '-a':
        del sys.argv[1]
        account_name = sys.argv[1]
        del sys.argv[1]
    else:
        account_name = None

    if len(sys.argv) > 1:
        url = sys.argv[1]
        referer = url
    else:
        url, referer = default_audio_clip()

    # we only grab the first 680KB of the file - that's enough to show working code
    audio_fp = download_audio_file(url, referer, 680 * 1024)
    audio_data = audio_fp.read()
    print('%s: length=%d' % (url.split('/')[-1:][0], len(audio_data)))

    doit(account_name, audio_data)

if __name__ == '__main__':
    main()
