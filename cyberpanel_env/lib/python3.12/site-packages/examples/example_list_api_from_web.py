#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    cf = CloudFlare.CloudFlare()
    try:
        found_comands = cf.api_from_openapi()
    except Exception as e:
        exit('api_from_web: - %s - api call connection failed' % (e))

    # {
    #   "action": "GET",
    #   "cmd": "/accounts",
    #   "deprecated": false,
    #   "deprecated_date": "",
    #   "deprecated_already": false
    # }

    # {
    #  "action": "DELETE",
    #  "cmd": "/accounts/:id/addressing/prefixes/:id/delegations",
    #  "deprecated": false,
    #  "deprecated_date": "",
    #  "deprecated_already": false,
    #  "content_type": "application/json"
    # }

    print('# cloudflare-python')
    print('')
    print('## Table of commands')
    print('')
    print('|`GET`   |`PUT`   |`POST`  |`PATCH` |`DELETE`|API call|')
    print('|--------|--------|--------|--------|--------|:-------|')

    cmds = {}
    for r in found_comands:
        if r['deprecated'] or r['deprecated_already']:
            continue
        cmd = r['cmd']
        action = r['action']
        if cmd not in cmds:
            cmds[cmd] = {}
        cmds[cmd][action] = action

    # This produces something like this ...
    # GET    -      -      PATCH  -       /zones/:zone_identifier/settings/always_online
    # GET    -      PUT    PATCH  DELETE  /zones/:zone_identifier/waiting_rooms/:waiting_room_id

    for cmd in cmds.keys():
        p = '|'
        for method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            if method in cmds[cmd]:
                p += '%-8s|' % ('`' + method + '`')
            else:
                p += '%-8s|' % ('-')
        print("%s %s |" % (p, cmd))

    print('')

if __name__ == '__main__':
    main()
