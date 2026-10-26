"""Resolve panel client addresses only across authenticated proxy boundaries."""
import hashlib
import hmac
import ipaddress
import os
import re
import stat
import time

# https://www.cloudflare.com/ips-v4 and /ips-v6, verified 2026-10-26.
# Keep updates code-reviewed: a downloaded list must never silently widen trust.
CLOUDFLARE_NETWORKS = tuple(ipaddress.ip_network(value) for value in '''
173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22
141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20
197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13
104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
2400:cb00::/32 2606:4700::/32 2803:f800::/32 2405:b500::/32
2405:8100::/32 2a06:98c0::/29 2c0f:f248::/32
'''.split())
PMA_PEER_KEY = '/etc/cyberpanel/pmaPeerKey'
PMA_PATHS = frozenset(('/dataBases/consumePHPMYAdminHandoff',
                       '/dataBases/validatePHPMYAdminSession'))


def _address(value):
    if not isinstance(value, str) or len(value) > 45 or '%' in value:
        return None
    try:
        parsed = ipaddress.ip_address(value)
        return parsed.ipv4_mapped if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped else parsed
    except ValueError:
        return None


def _peer_key():
    """Never follow a substituted key or accept a world-accessible secret."""
    try:
        fd = os.open(PMA_PEER_KEY, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            value = source.read(65)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o027:
            return None
        return value if re.fullmatch(b'[a-f0-9]{64}', value) else None
    except (OSError, ValueError):
        return None


def _pma_peer(request, remote):
    """PHP attests its socket peer; localhost alone does not confer this trust.

    Signatures bind a session and exact POST for at most 30 seconds. The consume
    endpoint separately consumes a one-use handoff; validation is read-only and
    always rechecks the current grant/ACL. No nonce cache with per-worker gaps.
    """
    if str(remote) not in ('127.0.0.1', '::1') or request.method != 'POST' or request.path not in PMA_PATHS:
        return None
    meta = request.META
    timestamp = meta.get('HTTP_X_CYBERPANEL_PEER_TIME', '')
    signature = meta.get('HTTP_X_CYBERPANEL_PEER_SIGNATURE', '')
    peer = meta.get('HTTP_X_CYBERPANEL_PEER', '')
    forwarded = meta.get('HTTP_CF_CONNECTING_IP', '')
    session = request.COOKIES.get('cyberpanel_sessionid', '')
    if (not re.fullmatch(r'[0-9]{10}', timestamp)
            or not re.fullmatch(r'[a-f0-9]{64}', signature)
            or not re.fullmatch(r'[A-Za-z0-9]{16,128}', session)
            or not _address(peer) or (forwarded and not _address(forwarded))
            or abs(time.time() - int(timestamp)) > 30):
        return None
    key = _peer_key()
    if key is None:
        return None
    message = '\n'.join(('pma-peer-v1', timestamp, request.method, request.path,
                         session, peer, forwarded, hashlib.sha256(request.body).hexdigest()))
    expected = hmac.new(key, message.encode('ascii'), hashlib.sha256).hexdigest()
    return _address(peer) if hmac.compare_digest(signature, expected) else None


def get_client_ip(request):
    remote = _address(request.META.get('REMOTE_ADDR'))
    if remote is None:
        return None
    if str(remote) in ('127.0.0.1', '::1'):
        remote = _pma_peer(request, remote) or remote
    if any(remote in network for network in CLOUDFLARE_NETWORKS):
        forwarded = _address(request.META.get('HTTP_CF_CONNECTING_IP'))
        # A trusted proxy without a valid client address cannot establish an IP
        # binding shared by every client on that edge.
        return str(forwarded) if forwarded is not None else None
    return str(remote)
