""" misc utilities  for Cloudflare API"""
from __future__ import absolute_import

import sys
import requests

from . import __version__

def user_agent():
    """ misc utilities  for Cloudflare API"""
    # the default User-Agent is something like 'python-requests/2.11.1'
    # this additional data helps support @ Cloudflare help customers
    return ('python-cloudflare/' + __version__ + '/' +
            'python-requests/' + str(requests.__version__) + '/' +
            'python/' + '.'.join(map(str, sys.version_info[:3]))
           )

def sanitize_secrets(secrets):
    """ misc utilities  for Cloudflare API"""
    redacted_phrase = 'REDACTED'

    if secrets is None:
        return None

    secrets_copy = secrets.copy()
    if 'password' in secrets_copy:
        secrets_copy['password'] = redacted_phrase
    elif 'X-Auth-Key' in secrets_copy:
        secrets_copy['X-Auth-Key'] = redacted_phrase
    elif 'X-Auth-User-Service-Key' in secrets_copy:
        secrets_copy['X-Auth-User-Service-Key'] = redacted_phrase
    elif 'Authorization' in secrets_copy:
        secrets_copy['Authorization'] = redacted_phrase

    return secrets_copy

def build_curl(method, url, headers, params, data, files):
    """ misc utilities  for Cloudflare API"""

    msg = []
    # url
    url_full = url
    if params is not None:
        for k in params:
            if k is None:
                continue
            url_full += '&%s=%s' % (k, params[k])
        url_full = url_full.replace('&', '?', 1)
    msg.append('       curl -X %s "%s" \\' % (str(method), str(url_full)))
    # headers
    h = sanitize_secrets(headers)
    for k in h:
        if k is None:
            continue
        msg.append('            -H "%s: %s" \\' % (k, h[k]))
    # data
    if data is not None:
        try:
            str_data = json.dumps(data)
        except:
            str_data = str(data)
        msg.append('            --data \'%s\' \\' % (str_data.replace('\n', ' ')))
    # files
    if files is not None:
        msg.append('            --form "file=@%s" \\' % (files))

    # remove the last \ from the last line.
    msg[-1] = msg[-1][:-1]

    return '\n'.join(msg)
