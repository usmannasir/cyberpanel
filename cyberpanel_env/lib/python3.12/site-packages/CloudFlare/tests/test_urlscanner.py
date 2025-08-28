""" urlscanner tests - PNG data retured """

import os
import sys
import random
import tempfile

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

cf = None

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

scan_uuid = None
scan_url = None

def test_urlscanner():
    """ test_urlscanner """
    global scan_uuid, scan_url
    scans = cf.accounts.urlscanner.scan.get(account_id, params={'limit':10})
    assert isinstance(scans, dict)
    assert 'tasks' in scans
    assert isinstance(scans['tasks'], list)
    tasks = scans['tasks']
    for task in tasks:
        assert isinstance(task, dict)
        assert 'success' in task
        assert 'time' in task
        assert 'uuid' in task
        assert 'url' in task
        print('%s: %s %s %s' % (task['uuid'], task['success'], task['time'], task['url']), file=sys.stderr)
    n = random.randrange(len(tasks))
    scan_uuid = tasks[n]['uuid']
    scan_url = tasks[n]['url']

def test_urlscanner_scan():
    """ test_urlscanner_scan """
    scan = cf.accounts.urlscanner.scan.get(account_id, scan_uuid)
    assert isinstance(scan, dict)
    assert 'scan' in scan
    assert isinstance(scan['scan'], dict)
    assert 'task' in scan['scan']
    task = scan['scan']['task']
    assert 'success' in task
    assert 'time' in task
    assert 'url' in task
    assert 'uuid' in task
    assert 'visibility' in task
    print('%s: %s %s %s' % (task['uuid'], task['success'], task['time'], task['url']), file=sys.stderr)

# https://www.w3.org/TR/png/#5PNG-file-signature
# PNG signature 89 50 4E 47 0D 0A 1A 0A
def ispng(s):
    """ ispng """
    if b'\x89PNG\x0d\x0a\x1a\x0a' == s[0:8]:
        return True
    return False

# we don't write out the image - we have no interest in doing this
def write_png_file(s):
    """ write_png_file """
    hostname = scan_url.split('/')[2].replace('.', '_')
    with tempfile.NamedTemporaryFile(mode='wb', prefix='screenshot-' + hostname + '-', suffix='.png', delete=False) as fp:
        fp.write(s)
        print('%s' % (fp.name), file=sys.stderr)

def test_urlscanner_scan_screenshot():
    """ test_urlscanner_scan_screenshot """
    # the real test - returning bytes as this is an image
    png_content = cf.accounts.urlscanner.scan.screenshot.get(account_id, scan_uuid)
    assert isinstance(png_content, bytes)
    print('%s: %s png_content: len=%d sig="%s"' % (scan_uuid, scan_url, len(png_content), png_content[0:8]), file=sys.stderr)
    assert ispng(png_content)
    # write_png_file(png_content)

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_account(sys.argv[1])
    else:
        test_find_account()
    test_urlscanner()
    test_urlscanner_scan()
    test_urlscanner_scan_screenshot()
