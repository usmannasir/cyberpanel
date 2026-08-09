#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""
CloudFlare API client for CyberPanel.

python-cloudflare uses:
- email + key: Global API Key (X-Auth-Email + X-Auth-Key)
- token: API Token or Application Token (Authorization: Bearer only)

CyberPanel UI stores email + "API Token" together. Application Tokens use the
cfat_ prefix and MUST use Bearer auth. Sending cfat_... as X-Auth-Key with email
causes Cloudflare: Invalid request headers.

Global API Keys from Cloudflare are 37 hexadecimal characters.
"""
import re
import socket
import warnings

import CloudFlare

_CF_API_HOST = 'api.cloudflare.com'
_orig_getaddrinfo = socket.getaddrinfo


def _cloudflare_ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Prefer IPv4 for Cloudflare API when tokens allow IPv4 but block IPv6."""
    if isinstance(host, str) and host == _CF_API_HOST:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _cloudflare_ipv4_getaddrinfo


def _is_global_api_key(secret):
    """True if secret matches Cloudflare Global API Key shape (37 hex chars)."""
    return bool(re.fullmatch(r"[a-f0-9]{37}", (secret or "").strip(), flags=re.I))


def _make_cloudflare_client(**kwargs):
    """
    Instantiate CloudFlare client without letting python-cloudflare 2.20.*
    PendingDeprecationWarning leak into CLI stdout/stderr (CyberPanel merges
    stderr into Issue SSL output and shows it as Operation Failed).
    """
    # 2.20.* forces simplefilter('always') then warns. Neutralize both the
    # warning module and the name imported into CloudFlare.cloudflare.
    try:
        import CloudFlare.warning_2_20 as _cf_warn_mod
        import CloudFlare.cloudflare as _cf_mod

        def _noop_warn(warning=None):
            return None

        _cf_warn_mod.warn_warning_2_20 = _noop_warn
        if getattr(_cf_mod, 'warn_warning_2_20', None):
            _cf_mod.warn_warning_2_20 = _noop_warn
    except Exception:
        pass
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', PendingDeprecationWarning)
        return CloudFlare.CloudFlare(**kwargs)


def get_cloudflare_client(email, secret):
    """Build a client from panel-stored email and key/token lines."""
    email = (email or "").strip()
    secret = (secret or "").strip()
    if not secret:
        raise ValueError("Cloudflare API key or token is empty")

    # Application Tokens (cfat_...) and normal API tokens: Bearer only.
    # UI may still store account email; Cloudflare ignores it for Bearer auth.
    if secret.startswith("cfat_"):
        return _make_cloudflare_client(token=secret)

    if email and _is_global_api_key(secret):
        return _make_cloudflare_client(email=email, key=secret)

    if email:
        return _make_cloudflare_client(token=secret)

    return _make_cloudflare_client(token=secret)
