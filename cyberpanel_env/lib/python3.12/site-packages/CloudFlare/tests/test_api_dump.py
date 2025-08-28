""" test dump calls """

import os
import sys
import re

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test API list fetches from Cloudflare website

cf = None

OPENAPI_URL = "https://github.com/cloudflare/api-schemas/raw/main/openapi.json"

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

verb_only = re.compile('^[a-zA-Z0-9][-a-zA-Z0-9_]*[a-zA-Z0-9]$')

def check_cmd_syntax(cmd):
    """ check_cmd_syntax """
    assert '/' == cmd[0]
    for verb in cmd[1:].split('/'):
        if verb[0] == '@':
            # don't want to check the rest of the api - it's an AI one
            break
        if verb[0] == ':':
            # :id or equiv
            assert bool(verb_only.match(verb[1:]))
        else:
            # just a verb
            assert bool(verb_only.match(verb))

def check_method_syntax(method):
    """ check_method_syntax """
    assert method in ['GET', 'POST', 'PATCH', 'PUT', 'DELETE']

def test_api_list():
    """dump a tree of all the known API commands"""
    api_list = cf.api_list()
    assert len(api_list) > 0
    for api in api_list:
        check_cmd_syntax(api)

def test_api_from_openapi():
    """dump a tree of all the known API commands - from web"""
    api_list = cf.api_from_openapi()
    assert len(api_list) > 0
    for api in api_list:
        # {'action': 'GET', 'cmd': '/accounts', 'deprecated': ...
        assert 'action' in api
        assert 'cmd' in api
        check_method_syntax(api['action'])
        check_cmd_syntax(api['cmd'])

def test_api_from_openapi_with_url():
    """dump a tree of all the known API commands - from web"""
    api_list = cf.api_from_openapi(OPENAPI_URL)
    assert len(api_list) > 0

if __name__ == '__main__':
    test_cloudflare(debug=True)
    test_api_list()
    test_api_from_openapi()
    test_api_from_openapi_with_url()
