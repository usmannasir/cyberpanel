#!/usr/bin/env python3
"""OLS HTTP-01 webroot must be the shared Example path, not site public_html."""
from __future__ import print_function

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class _FakePU(object):
    OLS = 0
    ent = 1

    @staticmethod
    def decideServer():
        return _FakePU.OLS


def main():
    import types
    # Stub ProcessUtilities before importing helper via exec of function source.
    pu = types.ModuleType('plogical.processUtilities')
    class ProcessUtilities(_FakePU):
        pass
    pu.ProcessUtilities = ProcessUtilities
    sys.modules['plogical.processUtilities'] = pu

    # Minimal plogical package stubs if needed
    if 'plogical' not in sys.modules:
        pkg = types.ModuleType('plogical')
        pkg.__path__ = [os.path.join(ROOT, 'plogical')]
        sys.modules['plogical'] = pkg

    # Import after stubbing decideServer used inside helper
    from plogical.processUtilities import ProcessUtilities as PU
    assert PU.decideServer() == PU.OLS

    # Load helper from sslUtilities without full Django
    path = os.path.join(ROOT, 'plogical', 'sslUtilities.py')
    src = open(path, 'r', encoding='utf-8', errors='replace').read()
    # Extract _ssl_resolve_acme_webroot by compiling a tiny namespace
    ns = {
        'os': os,
        'ProcessUtilities': PU,
        'BaseException': BaseException,
    }
    start = src.index('def _ssl_resolve_acme_webroot')
    end = src.index('\ndef _ssl_align_site_acme_challenge_dir', start)
    exec(src[start:end], ns)
    resolve = ns['_ssl_resolve_acme_webroot']

    with tempfile.TemporaryDirectory() as td:
        site = os.path.join(td, 'public_html')
        os.makedirs(site)
        got = resolve(site)
        expected = '/usr/local/lsws/Example/html'
        if got != expected:
            print('FAIL: expected %s got %s' % (expected, got))
            return 1
        got2 = resolve(None)
        if got2 != expected:
            print('FAIL: None path expected %s got %s' % (expected, got2))
            return 1
    print('OK: OLS ACME webroot resolves to shared Example path')
    return 0


if __name__ == '__main__':
    sys.exit(main())
