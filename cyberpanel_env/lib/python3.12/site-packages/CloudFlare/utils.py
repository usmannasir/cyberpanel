""" misc utilities  for Cloudflare API"""
import sys
import json
from requests import __version__ as requests__version__

from . import __version__

def user_agent():
    """ misc utilities  for Cloudflare API"""
    # the default User-Agent is something like 'python-requests/2.11.1'
    # this additional data helps support @ Cloudflare help customers
    return ('python-cloudflare/' + __version__ + '/' +
            'python-requests/' + str(requests__version__) + '/' +
            'python/' + '.'.join([str(v) for v in sys.version_info[:3]]))

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

def build_curl(method, url, headers, params, data_str, data_json, files):
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
    msg.append('       curl \\')
    msg.append('            --url "%s" \\' % (str(url_full)))
    msg.append('            --request %s \\' % (str(method)))
    # headers
    h = sanitize_secrets(headers)
    for k in h:
        if k is None:
            continue
        msg.append('            --header "%s: %s" \\' % (k, h[k]))
    # data_str
    if data_str is not None:
        if isinstance(data_str, (bytes,bytearray)):
            if len(data_str) > 180:
                msg.append('            --data-binary \'%s ...\' \\' % (str(data_str[0:180]).replace('\n', '\n')))
            else:
                msg.append('            --data-binary \'%s\' \\' % (str(data_str).replace('\n', '\n')))
        else:
            if len(data_str) > 180:
                msg.append('            --data \'%s ...\' \\' % (str(data_str[0:180]).replace('\n', ' ')))
            else:
                msg.append('            --data \'%s\' \\' % (str(data_str).replace('\n', ' ')))
    # data_json
    if data_json is not None:
        try:
            s = json.dumps(data_json)
        except (TypeError, ValueError, RecursionError):
            s = str(data_json)
        if len(s) > 180:
            msg.append('            --data \'%s ...\' \\' % (s[0:180].replace('\n', ' ')))
        else:
            msg.append('            --data \'%s\' \\' % (s.replace('\n', ' ')))
    # files
    if files is not None:
        if isinstance(files, (dict)):
            for k, v in files.items():
                if isinstance(v, (list, tuple)):
                    if v[0] is None:
                        msg.append('            --form %s="%s" \\' % (k, v[1]))
                    else:
                        msg.append('            --form %s="%s" \\' % (k, v[0]))
                else:
                    msg.append('            --form %s="%s" \\' % (k,v))
        elif isinstance(files, (set, list, tuple)):
            for f in files:
                if isinstance(f, (list, tuple)):
                    if f[1][0] is None:
                        # not a file
                        msg.append('            --form %s="%s" \\' % (f[0], f[1][1]))
                    else:
                        # a file
                        msg.append('            --form %s="@%s" \\' % (f[0], f[1][0]))
                else:
                    msg.append('            --form "%s" \\' % (f,))
        else:
            msg.append('            --form file="@%s" \\' % (files))

    # remove the last \ from the last line.
    msg[-1] = msg[-1][:-1]

    return '\n'.join(msg)
