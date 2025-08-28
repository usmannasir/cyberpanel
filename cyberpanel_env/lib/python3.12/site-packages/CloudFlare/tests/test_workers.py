""" workers tests """

import os
import sys
import uuid
import random

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test /accounts/:id/workers/scripts

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

sample_script_content = """
addEventListener("fetch", event => {
        event.respondWith(fetchAndModify(event.request));
    }
);

async function fetchAndModify(request) {
    console.log("got a request:", request);

    // Send the request on to the origin server.
    const response = await fetch(request);

    // Read response body.
    const text = await response.text();

    // Modify it.
    const modified = text.replace(
          "<body>",
          "<body style=\\"background: #ff0;\\">"
    );

    // Return modified response.
    return new Response(modified, {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers
        }
    );
}
"""

sample_script_content = '\n'.join([s.strip() for s in sample_script_content.splitlines() if s != '']).strip()

script_id = None
script_tag = None

def test_workers_script_put():
    """ test_workers_script_put """
    global script_id, script_tag

    script_id = str(uuid.uuid1())

    r = cf.accounts.workers.scripts.put(account_id, script_id, data=sample_script_content)
    assert isinstance(r, dict)
    assert 'id' in r
    assert 'tag' in r
    assert script_id == r['id']
    script_tag = r['tag']

def test_workers_find():
    """ test_workers_find """
    workers = cf.accounts.workers.scripts(account_id)
    assert len(workers) > 0
    assert isinstance(workers, list)
    found = False
    for w in workers:
        assert 'id' in w
        if script_id == w['id']:
            found = True
            break
    assert found is True

def test_workers_find_all():
    """ test_workers_find_all """
    workers = cf.accounts.workers.scripts(account_id)
    assert len(workers) >= 0
    assert isinstance(workers, list)
    if len(workers) == 0:
        return
    for w in workers:
        assert 'id' in w
        assert 'tag' in w
        this_script_name = w['id']
        this_script_tag = w['tag']
        assert isinstance(this_script_name, str)
        assert len(this_script_tag) == 32
        this_script_content = cf.accounts.workers.scripts(account_id, this_script_name)
        assert isinstance(this_script_content, str)
        assert len(this_script_content) > 0
        # print('%s: %s -> %s' % (this_script_tag, this_script_name, this_script_content.replace('\n','')[0:50]), file=sys.stderr)
        # just do one ... that's all that's needed for testing
        break

def test_workers_script_delete():
    """ test_workers_script_delete """
    r = cf.accounts.workers.scripts.delete(account_id, script_id)
    assert isinstance(r, dict)
    assert 'id' in r
    # note that 'id' and 'tag' are inconsistently used in DELETE vs PUT. Sigh.
    assert script_tag == r['id']

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_account(sys.argv[1])
    else:
        test_find_account()
    test_workers_script_put()
    test_workers_find()
    test_workers_find_all()
    test_workers_script_delete()
