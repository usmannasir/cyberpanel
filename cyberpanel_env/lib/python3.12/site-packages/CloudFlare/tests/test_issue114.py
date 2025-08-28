""" issue-114 tests """

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# CloudFlare(email=None, key=None, token=None, certtoken=None, debug=False, ...)

cf = None

debug = False

class TestCloudflare:
    """ TestCloudflare """

    def test_email_key_token000(self):
        """ test_email_key_token### """
        self._run(0, 0, 0)

    def test_email_key_token001(self):
        """ test_email_key_token### """
        self._run(0, 0, 1)

    def test_email_key_token002(self):
        """ test_email_key_token### """
        self._run(0, 0, 2)

    def test_email_key_token010(self):
        """ test_email_key_token### """
        self._run(0, 1, 0)

    def test_email_key_token011(self):
        """ test_email_key_token### """
        self._run(0, 1, 1)

    def test_email_key_token012(self):
        """ test_email_key_token### """
        self._run(0, 1, 2)

    def test_email_key_token020(self):
        """ test_email_key_token### """
        self._run(0, 2, 0)

    def test_email_key_token021(self):
        """ test_email_key_token### """
        self._run(0, 2, 1)

    def test_email_key_token022(self):
        """ test_email_key_token### """
        self._run(0, 2, 2)

    def test_email_key_token100(self):
        """ test_email_key_token### """
        self._run(1, 1, 0)

    def test_email_key_token101(self):
        """ test_email_key_token### """
        self._run(1, 1, 1)

    def test_email_key_token102(self):
        """ test_email_key_token### """
        self._run(1, 1, 2)

    def test_email_key_token110(self):
        """ test_email_key_token### """
        self._run(1, 1, 1)

    def test_email_key_token111(self):
        """ test_email_key_token### """
        self._run(1, 1, 1)

    def test_email_key_token112(self):
        """ test_email_key_token### """
        self._run(1, 1, 2)

    def test_email_key_token120(self):
        """ test_email_key_token### """
        self._run(1, 2, 1)

    def test_email_key_token121(self):
        """ test_email_key_token### """
        self._run(1, 2, 1)

    def test_email_key_token122(self):
        """ test_email_key_token### """
        self._run(1, 2, 2)

    def test_email_key_token200(self):
        """ test_email_key_token### """
        self._run(2, 0, 0)

    def test_email_key_token201(self):
        """ test_email_key_token### """
        self._run(2, 0, 1)

    def test_email_key_token202(self):
        """ test_email_key_token### """
        self._run(2, 0, 2)

    def test_email_key_token210(self):
        """ test_email_key_token### """
        self._run(2, 1, 2)

    def test_email_key_token211(self):
        """ test_email_key_token### """
        self._run(2, 1, 1)

    def test_email_key_token212(self):
        """ test_email_key_token### """
        self._run(2, 1, 2)

    def test_email_key_token220(self):
        """ test_email_key_token### """
        self._run(2, 2, 2)

    def test_email_key_token221(self):
        """ test_email_key_token### """
        self._run(2, 2, 1)

    def test_email_key_token222(self):
        """ test_email_key_token### """
        self._run(2, 2, 2)

    def _run(self, token_index, key_index, email_index):
        """ _run """
        global cf
        try:
            profile = self._profile
        except AttributeError:
            # Always clear environment
            self._setup()
            assert self._email or self._key or self._token
            # if not self._email and not self._key and not self._token:
            #     assert 'EMAIL/KEY/TOKEN all needed in order to run this test' == ''
            profile = self._profile

        # select combination
        email = [None, self._email, 'example@example.com'][email_index]
        key = [None, self._key, self._token][key_index]
        token = [None, self._token, self._key][token_index]

        try:
            cf = CloudFlare.CloudFlare(email=email, key=key, token=token, debug=debug, profile=profile)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            print('%s: Error %d=%s' % ('CloudFlare', int(e), str(e)), file=sys.stderr)
            # don't know what to do; but, lets continue anyway
            return
        assert isinstance(cf, CloudFlare.CloudFlare)

        try:
            r = cf.zones.get(params={'per_page':1})
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            print('%s: Error %d=%s' % ('/zones', int(e), str(e)), file=sys.stderr)
            r = None

        if email is None and key is None and token == self._token:
            print('SUCCESS (as expeced): email = ', self._obfuscate(email), 'key = ', self._obfuscate(key), 'token = ', self._obfuscate(token), file=sys.stderr)
            assert isinstance(r, list)
            assert len(r) == 1
            assert isinstance(r[0], dict)
            return

        if email is None and key == self._token and token is None:
            print('SUCCESS (as expeced): email = ', self._obfuscate(email), 'key = ', self._obfuscate(key), 'token = ', self._obfuscate(token), file=sys.stderr)
            assert isinstance(r, list)
            assert isinstance(r, list)
            assert len(r) == 1
            assert isinstance(r[0], dict)
            return

        if email == self._email and key == self._key and token is None:
            print('SUCCESS (as expeced): email = ', self._obfuscate(email), 'key = ', self._obfuscate(key), 'token = ', self._obfuscate(token), file=sys.stderr)
            assert isinstance(r, list)
            assert len(r) == 1
            assert isinstance(r[0], dict)
            return

        if email == self._email and key is None and token == self._key:
            print('SUCCESS (as expeced): email = ', self._obfuscate(email), 'key = ', self._obfuscate(key), 'token = ', self._obfuscate(token), file=sys.stderr)
            assert isinstance(r, list)
            assert len(r) == 1
            assert isinstance(r[0], dict)
            return

        # Nothing else should work!
        print('FAILED  (as expeced): email = ', self._obfuscate(email), 'key = ', self._obfuscate(key), 'token = ', self._obfuscate(token), file=sys.stderr)
        assert r is None

    def _setup(self):
        """ setup """
        # Force no profile to be picked
        self._profile = ''
        # read in email/key/token from config file(s)
        _config_files = [
            '.cloudflare.cfg',
            os.path.expanduser('~/.cloudflare.cfg'),
            os.path.expanduser('~/.cloudflare/cloudflare.cfg')
        ]
        email = None
        key = None
        token = None
        for filename in _config_files:
            try:
                with open(filename, 'r') as fd:
                    for line in fd:
                        if email and key and token:
                            break
                        if line[0] == '#':
                            continue
                        a = line.split()
                        if len(a) < 3:
                            continue
                        if a[1] != '=':
                            continue
                        if not email and a[0] == 'email':
                            email = a[2]
                            continue
                        if not key and a[0] == 'key':
                            key = a[2]
                            continue
                        if not token and a[0] == 'token':
                            token = a[2]
                            continue
                break
            except FileNotFoundError:
                pass
        self._email = email
        self._key = key
        self._token = token

        # now remove all env variables!
        for env in ['CLOUDFLARE_EMAIL', 'CLOUDFLARE_API_KEY', 'CLOUDFLARE_API_TOKEN']:
            try:
                del os.environ[env]
            except KeyError:
                pass
        for env in ['CF_API_EMAIL', 'CF_API_KEY', 'CF_API_TOKEN']:
            try:
                del os.environ[env]
            except KeyError:
                pass

    def _obfuscate(self, s):
        """ _obfuscate """
        return '█' if s is None else '█' * len(s)

if __name__ == '__main__':
    debug = True
    t = TestCloudflare()
    t.test_email_key_token000()
    t.test_email_key_token001()
    t.test_email_key_token002()
    t.test_email_key_token010()
    t.test_email_key_token011()
    t.test_email_key_token012()
    t.test_email_key_token020()
    t.test_email_key_token021()
    t.test_email_key_token022()
    t.test_email_key_token100()
    t.test_email_key_token101()
    t.test_email_key_token102()
    t.test_email_key_token110()
    t.test_email_key_token111()
    t.test_email_key_token112()
    t.test_email_key_token120()
    t.test_email_key_token121()
    t.test_email_key_token122()
    t.test_email_key_token200()
    t.test_email_key_token201()
    t.test_email_key_token202()
    t.test_email_key_token210()
    t.test_email_key_token211()
    t.test_email_key_token212()
    t.test_email_key_token220()
    t.test_email_key_token221()
    t.test_email_key_token222()
