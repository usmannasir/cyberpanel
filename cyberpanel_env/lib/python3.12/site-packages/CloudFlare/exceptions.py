""" errors for Cloudflare API"""

class CloudFlareError(Exception):
    """ errors for Cloudflare API"""

    class _CodeMessage():
        """ a small class to save away an interger and string (the code and the message)"""

        def __init__(self, code, message):
            self._code = code
            self._message = message

        def __int__(self):
            return self._code

        def __str__(self):
            return self._message

        def __repr__(self):
            return '[%d:"%s"]' % (int(self._code), str(self._message))

    def __init__(self, code=0, message=None, error_chain=None, e=None):
        """ errors for Cloudflare API"""

        if e and isinstance(e, CloudFlareAPIError):
            # create fresh values (i.e copies)
            self._evalue = CloudFlareError._CodeMessage(int(e), str(e))
            if getattr(e, '_error_chain', False):
                self._error_chain = [CloudFlareError._CodeMessage(int(v), str(v)) for v in e._error_chain]
            return

        self._evalue = CloudFlareError._CodeMessage(int(code), str(message))
        if error_chain is not None:
            self._error_chain = []
            for evalue in error_chain:
                if isinstance(evalue, CloudFlareError._CodeMessage):
                    v = evalue
                else:
                    v = CloudFlareError._CodeMessage(int(evalue['code']), str(evalue['message']))
                self._error_chain.append(v)
        # As we are built off Exception, we need to get our superclass all squared away
        # super().__init__(message)

    def __bool__(self):
        """ bool value for Cloudflare API errors"""

        # required because there's a len() function below that can return 0
        # see https://docs.python.org/3/library/stdtypes.html#truth-value-testing
        return True

    def __int__(self):
        """ integer value for Cloudflare API errors"""

        return int(self._evalue)

    def __str__(self):
        """ string value for Cloudflare API errors"""

        return str(self._evalue)

    def __repr__(self):
        """ string value for Cloudflare API errors"""

        s = '[%d:"%s"]' % (int(self._evalue), str(self._evalue))
        if getattr(self, '_error_chain', False):
            for evalue in self._error_chain:
                s += ' [%d:"%s"]' % (int(evalue), str(evalue))
        return s

    def __len__(self):
        """ Cloudflare API errors can contain a chain of errors"""

        try:
            return len(getattr(self, '_error_chain'))
        except AttributeError:
            return 0

    def __getitem__(self, ii):
        """ Cloudflare API errors can contain a chain of errors"""

        return self._error_chain[ii]

    def __iter__(self):
        """ Cloudflare API errors can contain a chain of errors"""

        if getattr(self, '_error_chain', False):
            for evalue in self._error_chain:
                yield evalue
        return

    def next(self):
        """ Cloudflare API errors can contain a chain of errors"""

        if getattr(self, '_error_chain', False) is False:
            raise StopIteration

class CloudFlareAPIError(CloudFlareError):
    """ errors for Cloudflare API"""

class CloudFlareInternalError(CloudFlareError):
    """ errors for Cloudflare API"""
