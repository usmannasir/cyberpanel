""" Network for Cloudflare API"""
from __future__ import absolute_import

import requests

from .exceptions import CloudFlareAPIError

class CFnetwork(object):
    """ Network for Cloudflare API"""

    def __init__(self, use_sessions=True):
        """ Network for Cloudflare API"""

        self.use_sessions = use_sessions
        self.session = None

    def __call__(self, method, url, headers=None, params=None, data=None, files=None):
        """ Network for Cloudflare API"""

        if self.use_sessions:
            if self.session is None:
                self.session = requests.Session()
        else:
            self.session = requests

        method = method.upper()

        if method == 'GET':
            return self.session.get(url,
                                    headers=headers, params=params, data=data)
        if method == 'POST':
            if isinstance(data, str):
                return self.session.post(url,
                                         headers=headers, params=params, data=data, files=files)
            else:
                return self.session.post(url,
                                         headers=headers, params=params, json=data, files=files)
        if method == 'PUT':
            if isinstance(data, str):
                return self.session.put(url,
                                        headers=headers, params=params, data=data)
            else:
                return self.session.put(url,
                                        headers=headers, params=params, json=data)
        if method == 'DELETE':
            if isinstance(data, str):
                return self.session.delete(url,
                                           headers=headers, params=params, data=data)
            else:
                return self.session.delete(url,
                                           headers=headers, params=params, json=data)
        if method == 'PATCH':
            if isinstance(data, str):
                return self.session.request('PATCH', url,
                                            headers=headers, params=params, data=data)
            else:
                return self.session.request('PATCH', url,
                                            headers=headers, params=params, json=data)

        # should never happen
        raise CloudFlareAPIError(0, 'method not supported')

    def __del__(self):
        """ Network for Cloudflare API"""

        if self.use_sessions and self.session:
            self.session.close()
            self.session = None
