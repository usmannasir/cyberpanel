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


def get_cloudflare_client(email, secret):
    """Build a client from panel-stored email and key/token lines."""
    email = (email or "").strip()
    secret = (secret or "").strip()
    if not secret:
        raise ValueError("Cloudflare API key or token is empty")

    # Application Tokens (cfat_...) and normal API tokens: Bearer only.
    # UI may still store account email; Cloudflare ignores it for Bearer auth.
    if secret.startswith("cfat_"):
        return CloudFlare.CloudFlare(token=secret)

    if email and _is_global_api_key(secret):
        return CloudFlare.CloudFlare(email=email, key=secret)

    if email:
        return CloudFlare.CloudFlare(token=secret)

    return CloudFlare.CloudFlare(token=secret)
