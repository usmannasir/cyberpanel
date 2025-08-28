""" Network for Cloudflare API"""

from urllib.parse import urlparse

from requests import Session, RequestException, ConnectionError as requests_ConnectionError
from requests.exceptions import Timeout
from requests.adapters import HTTPAdapter

class CFnetworkError(Exception):
    """ errors for network calls """

class CFnetwork():
    """ CFnetwork """

    def __init__(self, use_sessions=True, global_request_timeout=5, max_request_retries=5):
        """ CFnetwork """

        self.use_sessions = use_sessions
        self.global_request_timeout = global_request_timeout
        self.max_request_retries = max_request_retries
        self.session = None

    def __call__(self, method, url, headers=None, params=None, data_str=None, data_json=None, files=None):
        """ __call__ """

        if self.use_sessions:
            if self.session is None:
                s = Session()
                if self.max_request_retries is not None:
                    prefix = 'https://%s' % (urlparse(url).netloc)
                    s.mount(prefix, HTTPAdapter(max_retries=self.max_request_retries))
                self.session = s
        else:
            # only now do we import all of requests ... it's a rare case
            import requests
            self.session = requests

        try:
             r = self._do_network(method, url, headers, params, data_str, data_json, files)
        except Timeout as e:
            raise CFnetworkError('network request timeout error: %s' % (e)) from None
        except requests_ConnectionError as e:
            raise CFnetworkError('network request connection error: %s' % (e)) from None
        except RequestException as e:
            raise CFnetworkError('network request exception error: %s' % (e)) from None

        return r

    def _do_network(self, method, url, headers, params, data_str, data_json, files):
        """ _do_network """
        method = method.upper()

        # https://docs.python-requests.org/en/latest/user/quickstart/#post-a-multipart-encoded-file
        # Note, the json parameter is ignored if either data or files is passed.
        # This should have been handled well before here (it is!)

        if method == 'GET':
            # no data or files
            r = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=self.global_request_timeout,
            )
        elif method == 'POST':
            r = self.session.post(
                url,
                headers=headers,
                params=params,
                data=data_str,
                json=data_json,
                files=files,
                timeout=self.global_request_timeout,
            )
        elif method == 'PUT':
            r = self.session.put(
                url,
                headers=headers,
                params=params,
                data=data_str,
                json=data_json,
                files=files,
                timeout=self.global_request_timeout,
            )
        elif method == 'DELETE':
            r = self.session.delete(
                url,
                headers=headers,
                params=params,
                data=data_str,
                json=data_json,
                timeout=self.global_request_timeout,
            )
        elif method == 'PATCH':
            r = self.session.request(
                'PATCH',
                url,
                headers=headers,
                params=params,
                data=data_str,
                json=data_json,
                timeout=self.global_request_timeout,
            )
        else:
            # should never happen
            raise CFnetworkError('internal error - http method invalid: %s' % (method))
        # success!
        return r

    def __del__(self):
        """ __del__ """

        if self.use_sessions and self.session:
            self.session.close()
            self.session = None
