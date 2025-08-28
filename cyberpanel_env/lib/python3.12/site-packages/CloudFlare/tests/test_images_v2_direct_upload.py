""" radar returning CSV test """

import os
import sys
import json
import random
import datetime
import pytz

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test /accounts/:id/images/v2/direct_upload - this uses forms in port

cf = None

def rfc3339_iso8601_time(hour_delta=0, with_hms=False):
    # format time (with an hour offset in RFC3339 or ISO8601 format (and do it UTC time)
    if sys.version_info[:3][0] <= 3 and sys.version_info[:3][1] <= 10:
        dt = datetime.datetime.utcnow().replace(microsecond=0, tzinfo=pytz.UTC)
    else:
        dt = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    dt += datetime.timedelta(hours=hour_delta)
    if with_hms:
        return dt.isoformat().replace('+00:00', 'Z')
    return dt.strftime('%Y-%m-%d')

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

account_name = None
account_id = None

def test_find_account(find_name=None):
    """ test_find_account """
    global account_name, account_id
    # grab a random account identifier from the first 10 accounts
    if find_name:
        params = {'per_page':1, 'name':find_name}
    else:
        params = {'per_page':10}
    try:
        accounts = cf.accounts.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('%s: Error %d=%s' % (find_name, int(e), str(e)), file=sys.stderr)
        assert False
    assert len(accounts) > 0 and len(accounts) <= 10
    # n = random.randrange(len(accounts))
    # stop using a random account - use the primary account (i.e. the zero'th one)
    n = 0
    account_name = accounts[n]['name']
    account_id = accounts[n]['id']
    assert len(account_id) == 32
    print('account: %s %s' % (account_id, account_name), file=sys.stderr)

# simple metadata in json string form
metadata_values = json.dumps({
    'item1': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, ...',
    'item2': 'Ignore item number one',
})

# format future time in RFC3339 format (and do it UTC time)
time_plus_one_hour_in_iso = rfc3339_iso8601_time(1, True)

def test_images_v2_direct_upload():
    """ test_images_v2_direct_upload """

    try:
        r = cf.accounts.images.v2.direct_upload.post(account_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error unexpected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert False

    assert isinstance(r, dict)
    assert len(r['id']) > 0
    assert len(r['uploadURL']) > 0

    image_id = r['id']
    image_url = r['uploadURL']
    print('%s %s' % (image_id, image_url), file=sys.stderr)

def test_images_v2_direct_upload_data():
    """ test_images_v2_direct_upload """

    data = {
        'metadata': metadata_values,
        'expiry': time_plus_one_hour_in_iso,
    }
    try:
        r = cf.accounts.images.v2.direct_upload.post(account_id, data=data)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error unexpected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert False

    assert isinstance(r, dict)
    assert len(r['id']) > 0
    assert len(r['uploadURL']) > 0

    image_id = r['id']
    image_url = r['uploadURL']
    print('%s %s' % (image_id, image_url), file=sys.stderr)

def test_images_v2_direct_upload_files():
    """ test_images_v2_direct_upload """

    files = {
        ('metadata', (None, metadata_values)),
        ('expiry', (None, time_plus_one_hour_in_iso))
    }
    try:
        r = cf.accounts.images.v2.direct_upload.post(account_id, files=files)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error unexpected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert False

    assert isinstance(r, dict)
    assert len(r['id']) > 0
    assert len(r['uploadURL']) > 0

    image_id = r['id']
    image_url = r['uploadURL']
    print('%s %s' % (image_id, image_url), file=sys.stderr)

def test_images_v2_direct_upload_data_and_files():
    """ test_images_v2_direct_upload """

    data = {
        'metadata': metadata_values,
        'expiry': time_plus_one_hour_in_iso,
    }
    files = {
        ('metadata', (None, metadata_values)),
        ('expiry', (None, time_plus_one_hour_in_iso))
    }
    try:
        r = cf.accounts.images.v2.direct_upload.post(account_id, data=data, files=files)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error unexpected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert False

    assert isinstance(r, dict)
    assert len(r['id']) > 0
    assert len(r['uploadURL']) > 0

    image_id = r['id']
    image_url = r['uploadURL']
    print('%s %s' % (image_id, image_url), file=sys.stderr)

def test_images_v2_direct_upload_files_len_zero():
    """ test_images_v2_direct_upload """

    files = set() # zero length set
    try:
        r = cf.accounts.images.v2.direct_upload.post(account_id, files=files)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        # this can trigger an error from the Cloudflare API backend - which is wrong; however, should be coded around.
        print('Error unexpected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert False

    assert isinstance(r, dict)
    assert len(r['id']) > 0
    assert len(r['uploadURL']) > 0

    image_id = r['id']
    image_url = r['uploadURL']
    print('%s %s' % (image_id, image_url), file=sys.stderr)

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_account(sys.argv[1])
    else:
        test_find_account()
    test_images_v2_direct_upload()
    test_images_v2_direct_upload_data()
    test_images_v2_direct_upload_files()
    test_images_v2_direct_upload_data_and_files()
    test_images_v2_direct_upload_files_len_zero()
