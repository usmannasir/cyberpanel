""" API from OpenAPI for Cloudflare API"""

import sys
import re
import datetime
import json

API_TYPES = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE']

match_identifier = re.compile(r'\{[A-Za-z0-9_\-]*\}')

def do_path(cmd, values):
    """ do_path() """

    cmds = []

    if cmd[0] != '/':
        cmd = '/' + cmd  # make sure there's a leading /

    cmd = match_identifier.sub(':id', cmd)
    if cmd[-4:] == '/:id':
        cmd = cmd[:-4]
    if cmd[-4:] == '/:id':
        cmd = cmd[:-4]

    for action in values:
        if action == '' or action.upper() not in API_TYPES:
            continue
        if 'deprecated' in values[action] and values[action]['deprecated']:
            deprecated = True
            deprecated_date = datetime.datetime.now().strftime('%Y-%m-%d')
            deprecated_already = True
        else:
            deprecated = False
            deprecated_date = ''
            deprecated_already = False

        # The requestBody/content could be one of the following:
        # "requestBody": {
        #   "content": {
        #     "application/javascript" {
        #     "application/json" {
        #     "application/octet-stream" {
        #     "application/x-ndjson" {
        #     "multipart/form-data" {

        content_type = None
        if 'requestBody' in values[action] and values[action]['requestBody']:
            request_body = values[action]['requestBody']
            if 'content' in request_body and request_body['content']:
                content_type = ','.join(list(request_body['content'].keys()))
                if content_type == 'application/json':
                    # this is the default; so we simply ignore it
                    content_type = None

        if content_type:
            v = {
                    'action': action.upper(),
                    'cmd': cmd,
                    'deprecated': deprecated,
                    'deprecated_date': deprecated_date,
                    'deprecated_already': deprecated_already,
                    'content_type': content_type
                }
        else:
            v = {
                    'action': action.upper(),
                    'cmd': cmd,
                    'deprecated': deprecated,
                    'deprecated_date': deprecated_date,
                    'deprecated_already': deprecated_already
                }
        cmds.append(v)
    return cmds

def api_decode_from_openapi(content):
    """ API decode from OpenAPI for Cloudflare API"""

    try:
        j = json.loads(content)
    except json.decoder.JSONDecodeError as e:
        raise SyntaxError('OpenAPI json decode failed: %s' % (e)) from None

    try:
        components = j['components']
        info = j['info']
        cloudflare_version = info['version']
        openapi_version = j['openapi']
        paths = j['paths']
        servers = j['servers']
    except KeyError as e:
        raise SyntaxError('OpenAPI json missing standard OpenAPI values: %s' % (e)) from None

    if len(components) == 0:
        raise SyntaxError('OpenAPI json components missing values')

    cloudflare_url = None
    for server in servers:
        try:
            cloudflare_url = server['url']
        except KeyError as e:
            pass
    if not cloudflare_url:
        raise SyntaxError('OpenAPI json servers/server missing url value')

    all_cmds = []
    for path in paths:
        if path[0] != '/':
            sys.stderr.write("OpenAPI invalid path: %s\n" % (path))
            continue
        all_cmds += do_path(path, paths[path])

    return sorted(all_cmds, key=lambda v: v['cmd']), openapi_version, cloudflare_version, cloudflare_url
