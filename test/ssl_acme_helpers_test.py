#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke tests for SSL renewal helpers (CyberPanel issue #1676 / PR #1732 alignment)."""
import os
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

import django  # noqa: E402

django.setup()

from plogical.sslUtilities import (  # noqa: E402
    _ssl_resolve_acme_webroot,
    _ssl_privkey_is_ecdsa,
)


def test_webroot_default():
    assert _ssl_resolve_acme_webroot(None) == '/usr/local/lsws/Example/html'
    assert _ssl_resolve_acme_webroot('') == '/usr/local/lsws/Example/html'


def test_webroot_custom():
    with tempfile.TemporaryDirectory() as tmp:
        assert _ssl_resolve_acme_webroot(tmp) == tmp


def test_webroot_invalid_fallback():
    assert _ssl_resolve_acme_webroot('/nonexistent/path/12345') == '/usr/local/lsws/Example/html'


def test_privkey_missing_defaults_ecdsa():
    assert _ssl_privkey_is_ecdsa('/nonexistent/privkey.pem') is True


if __name__ == '__main__':
    test_webroot_default()
    test_webroot_custom()
    test_webroot_invalid_fallback()
    test_privkey_missing_defaults_ecdsa()
    print('ok: ssl_acme_helpers_test')
