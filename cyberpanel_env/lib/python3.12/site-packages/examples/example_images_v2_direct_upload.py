#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import json
import datetime
import requests

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

#
# Warning: You need to enable image storage on your account for this code to work.
# You'll get 403 errors if you don't have it enabled (go pay for it)
#
# If you need to delete images after running this code you can do this:
#
# cli4 --delete /accounts/:"${ACCOUNT}"/images/v1/::${image_id}
#
# Or if you want to live dangerously - do this and delete every image you have
# You should not run this unless you really really really know what you're doing! (like rm -rf /)
#
# cli4 /accounts/:"${ACCOUNT}"/images/v1 | jq -r '.images[]|.id' | while read image_id ; do cli4 --delete /accounts/:"${ACCOUNT}"/images/v1/::$image_id ; done
#

#
# A note about version numbers.
# this code works with 2.14.2 in a simple way
# this code works with 2.18.0 is a simple way
# released between then require at-least one paramater send via files= in order to not trigger a backend API bug
#

def rfc3339_iso8601_time(hour_delta=0, with_hms=False):
    """ rfc3339_iso8601_time """
    # format time (with an hour offset in RFC3339 ISO8601 format (and do it UTC time)
    dt = (datetime.datetime.now(datetime.UTC).replace(microsecond=0) + datetime.timedelta(hours=hour_delta))
    if with_hms:
        return dt.isoformat().replace('+00:00', 'Z')
    return dt.strftime('%Y-%m-%d')

def method_from_library_version():
    """ method_from_library_version """
    if CloudFlare.__version__ <= '2.14.2':
        print('Using %s version of Cloudflare python library - hence do not need data= or files=; but use files= if passing anything' % (CloudFlare.__version__))
        return ''
    if CloudFlare.__version__ <= '2.17.0':
        print('Using %s version of Cloudflare python library - hence must use files=' % (CloudFlare.__version__))
        return 'USE-FILES'
    # with newer library than 2.17.0 (i.e 2.18.0 and above) you should be able to pass just the data version
    print('Using %s version of Cloudflare python library - hence use data= as it is simpler' % (CloudFlare.__version__))
    return 'USE-DATA'

def doit(account_name, image_filename):
    """ doit """

    # https://developers.cloudflare.com/stream/uploading-videos/direct-creator-uploads/
    # https://developers.cloudflare.com/api/operations/cloudflare-images-create-authenticated-direct-upload-url-v-2

    with CloudFlare.CloudFlare(debug=False) as cf:
        try:
            params = {'name': account_name, 'per_page': 1}
            accounts = cf.accounts.get(params=params)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.exit('%s: %d %s - api call failed' % ('/accounts', int(e), str(e)))
        try:
            account_id = accounts[0]['id']
        except IndexError:
            sys.exit('%s: account name not found' % (account_name))

        try:
           image_fp = open(image_filename, 'rb')
        except Exception as e:
            sys.exit('%s: %s - file read failed' % (image_filename, e))

        image_filesize = os.fstat(image_fp.fileno()).st_size
        if image_filesize > 1024*1024*1024:
                print('%s: filesize = %0.1f GBytes' % (image_filename, float(image_filesize)/1024*1024*1024))
        elif image_filesize > 1024*1024:
                print('%s: filesize = %0.1f MBytes' % (image_filename, float(image_filesize)/1024*1024))
        elif image_filesize > 1024:
                print('%s: filesize = %0.1f KBytes' % (image_filename, float(image_filesize)/1024))
        else:
                print('%s: filesize = %d Bytes' % (image_filename, image_filesize))

        # format future time in RFC3339 format (and do it UTC time)
        time_plus_one_hour_in_iso = rfc3339_iso8601_time(1, True)

        # direct_upload uses multipart/form-data and hence this info is passed as files (but None for filename)
        # these are the four form values
        # presently you need to upload at-least one of these until the library version is greater than 2.17.0
        # --form expiry= \
        # --form id= \
        # --form metadata= \
        # --form requireSignedURLs=

        # here's examples using metadata and expiry.

        # this is just simple metadata created to show it working - your code will be different
        metadata_values = {
            'source': image_filename,
            'size': image_filesize,
        }

        data = None
        files = None

        lib_method = method_from_library_version()

        if lib_method == 'USE-FILES':
            files = {
                ('metadata', (None, json.dumps(metadata_values))),
                ('expiry', (None, time_plus_one_hour_in_iso))
            }
        elif lib_method == 'USE-DATA':
            data = {
                'metadata': json.dumps(metadata_values),
                'expiry': time_plus_one_hour_in_iso,
            }
        elif lib_method == '':
            # optionally do nothing or send via files=
            pass

        try:
            r = cf.accounts.images.v2.direct_upload.post(account_id, data=data, files=files)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.exit('%s: %d %s - api call failed' % ('/accounts/images/v2/direct_upload', int(e), str(e)))
        print('v2 new image post results')
        print(json.dumps(r, indent=4))

        image_id = r['id']
        image_url = r['uploadURL']

        # https://developers.cloudflare.com/stream/uploading-videos/direct-creator-uploads/
        # curl -X POST \
        #      -F file=@/Users/mickie/Downloads/example_video.mp4 \
        #      https://upload.videodelivery.net/f65014bc6ff5419ea86e7972a047ba22

        try:
            r = requests.post(image_url, files={('file', image_fp)}, timeout=5)
        except Exception as e:
            sys.exit('%s: %s - api call failed' % (image_url, e))

        image_fp.close()

        if r.status_code != 200:
           if r.status_code == 403:
               print('403 means you need to enable images in your account')
           if r.status_code == 403:
               print('415 means the file is a bad image format')
           sys.exit('%s: HTTP Error %s' % (image_url, r.status_code))

        j = r.json()
        if j['success'] is True:
            print('Image upload results')
            print(json.dumps(j['result'], indent=4))
        else:
            sys.exit('Error:\n    errors: %s\n    messages: %s' % (j['errors'], j['messages']))

        # list all images
        try:
            r = cf.accounts.images.v2(account_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.exit('%s: %d %s - api call failed' % ('/accounts/images/v1', int(e), str(e)))

        print('All account images:')
        for img in r['images']:
            print('%s   %s: %s %s %s' % ('>' if img['id'] == image_id else ' ', img['id'], img['uploaded'], img['filename'], img['variants'][0]))
            if 'meta' in img:
                for k,v in img['meta'].items():
                    print('        %s = %s' % (k, v))
            else:
                print('        - no meta data')

        # delete the image - this was just a test (comment this out if you end up using this code for uploads)
        try:
            r = cf.accounts.images.v1.delete(account_id, image_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.exit('%s: %d %s - api call failed' % ('/accounts/images/v1', int(e), str(e)))
        print('Image delete')
        print(json.dumps(r, indent=4))

def main():
    """ main """
    try:
        account_name = sys.argv[1]
    except IndexError:
        sys.exit('usage: example_images_v2_direct_upload.py account_name image_filename')
    try:
        image_filename = sys.argv[2]
    except IndexError:
        sys.exit('usage: example_images_v2_direct_upload.py account_name image_filename')
    doit(account_name, image_filename)
    sys.exit(0)

if __name__ == '__main__':
    main()
