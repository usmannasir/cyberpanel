""" get/post/delete/etc zone ruleset based tests """

import os
import sys
import uuid
import random

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test GET POST PUT PATCH & DELETE - but not in that order

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

zone_name = None
zone_id = None

def test_find_zone(domain_name=None):
    """ test_find_zone """
    global zone_name, zone_id
    # grab a random zone identifier from the first 10 zones
    if domain_name:
        params = {'per_page':1, 'name':domain_name}
    else:
        params = {'per_page':10}
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('%s: Error %d=%s' % (domain_name, int(e), str(e)), file=sys.stderr)
        assert False
    assert len(zones) > 0 and len(zones) <= 10
    n = random.randrange(len(zones))
    zone_name = zones[n]['name']
    zone_id = zones[n]['id']
    assert len(zone_id) == 32
    print('zone: %s %s' % (zone_id, zone_name), file=sys.stderr)

ruleset_name = None
ruleset_ref = None
ruleset_content = None

def test_ruleset_create_values():
    """ test_accounts_ruleset_create_values """
    global ruleset_name, ruleset_ref, ruleset_content
    ruleset_name = str(uuid.uuid1())
    ruleset_ref = str(uuid.uuid1())
    ruleset_content = """
        {
          "description": "Testing 1 2 3 ...",
          "kind": "zone",
          "name": "%s",
          "phase": "http_request_firewall_custom",
          "rules": [
            {
              "action": "block",
              "description": "Block when the IP address is not 1.1.1.1",
              "enabled": false,
              "expression": "ip.src ne 1.1.1.1",
              "ref": "%s"
            }
          ]
        }
    """ % (ruleset_name, ruleset_ref)
    ruleset_content = ''.join([s.strip() for s in ruleset_content.splitlines()]).strip()

    print('ruleset: name=%s content=%s' % (ruleset_name, ruleset_content), file=sys.stderr)
    assert True

ruleset_id = None

def test_zones_rulesets_get():
    """ test_zones_rulesets_get """
    # GET
    ruleset_results = cf.zones.rulesets.get(zone_id)
    assert isinstance(ruleset_results, list)
    for ruleset in ruleset_results:
        assert isinstance(ruleset, dict)
        assert 'id' in ruleset
        assert 'kind' in ruleset
        assert 'phase' in ruleset
        assert 'name' in ruleset
        print('ruleset: %s: name=%s kind=%s phase=%s' % (ruleset['id'], ruleset['name'], ruleset['kind'], ruleset['phase']), file=sys.stderr)
    assert True

def test_zones_ruleset_post():
    """ test_zones_rulesets_post """
    global ruleset_id
    # POST
    ruleset = cf.zones.rulesets.post(zone_id, data=ruleset_content)
    assert isinstance(ruleset, dict)
    assert 'id' in ruleset
    assert 'kind' in ruleset
    assert 'phase' in ruleset
    assert 'name' in ruleset
    assert 'rules' in ruleset
    assert 'ref' in ruleset['rules'][0]
    assert ruleset['name'] == ruleset_name
    assert ruleset['rules'][0]['ref'] == ruleset_ref
    ruleset_id = ruleset['id']
    print('ruleset: %s: name=%s kind=%s phase=%s' % (ruleset['id'], ruleset['name'], ruleset['kind'], ruleset['phase']), file=sys.stderr)

def test_zones_rulesets_get_specific():
    """ test_zones_rulesets_get_specific """
    # GET
    ruleset = cf.zones.rulesets.get(zone_id, ruleset_id)
    assert isinstance(ruleset, dict)
    assert 'id' in ruleset
    assert 'kind' in ruleset
    assert 'phase' in ruleset
    assert 'name' in ruleset
    assert 'rules' in ruleset
    assert ruleset['id'] == ruleset_id
    print('ruleset: %s: name=%s kind=%s phase=%s' % (ruleset['id'], ruleset['name'], ruleset['kind'], ruleset['phase']), file=sys.stderr)

def test_zones_ruleset_delete():
    """ test_zones_rulesets_delete """
    # DELETE
    ruleset_response = cf.zones.rulesets.delete(zone_id, ruleset_id)
    # None is returned - not quite the same response as other delete's in the API
    assert ruleset_response is None

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

ruleset_id = None
ruleset_version = None

def test_accounts_ruleset():
    """ test_accounts_ruleset """
    global ruleset_id, ruleset_version
    ruleset_results = results = cf.accounts.rulesets(account_id)
    assert isinstance(ruleset_results, list)
    for ruleset in ruleset_results:
        assert isinstance(ruleset, dict)
        assert 'id' in ruleset
        assert 'version' in ruleset
        ruleset_id = ruleset['id']
        ruleset_version = ruleset['version']
        # we only need one!
        break
    print('account ruleset: %s %s' % (ruleset_id, ruleset_name), file=sys.stderr)

def test_accounts_rulesets_versions():
    """ test_accounts_ruleset_versions """
    ruleset = cf.accounts.rulesets.versions(account_id, ruleset_id, ruleset_version)
    assert isinstance(ruleset, dict)
    assert 'id' in ruleset
    assert 'version' in ruleset
    assert ruleset['id'] == ruleset_id
    assert ruleset['version'] == ruleset_version

def test_accounts_rulesets_versions_by_tag():
    """ test_accounts_rulesets_versions_by_tag """
    # List an account ruleset version's rules by tag
    # /accounts/{account_id}/rulesets/{ruleset_id}/versions/{ruleset_version}/by_tag/{rule_tag}
    # four id's passed on call!
    rule_tag = 'QWERTYUIOP'
    try:
        results = cf.accounts.rulesets.versions.by_tag(account_id, ruleset_id, ruleset_version, rule_tag)
        print('results=', results, file=sys.stderr)
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert True

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_zone(sys.argv[1])
    else:
        test_find_zone()
    test_ruleset_create_values()
    test_zones_rulesets_get()
    test_zones_ruleset_post()
    test_zones_rulesets_get_specific()
    test_zones_ruleset_delete()
    if len(sys.argv) > 2:
        test_find_account(sys.argv[2])
    else:
        test_find_account()
    test_accounts_ruleset()
    test_accounts_rulesets_versions()
    test_accounts_rulesets_versions_by_tag()
