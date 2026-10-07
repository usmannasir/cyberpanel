import ipaddress

# Cloudflare edge ranges, published at https://www.cloudflare.com/ips/.
# CF-Connecting-IP is only trusted when the request comes from one of these,
# otherwise any client could choose the IP address CyberPanel binds its
# session to.
CLOUDFLARE_NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in (
    '173.245.48.0/20',
    '103.21.244.0/22',
    '103.22.200.0/22',
    '103.31.4.0/22',
    '141.101.64.0/18',
    '108.162.192.0/18',
    '190.93.240.0/20',
    '188.114.96.0/20',
    '197.234.240.0/22',
    '198.41.128.0/17',
    '162.158.0.0/15',
    '104.16.0.0/13',
    '104.24.0.0/14',
    '172.64.0.0/13',
    '131.0.72.0/22',
    '2400:cb00::/32',
    '2606:4700::/32',
    '2803:f800::/32',
    '2405:b500::/32',
    '2405:8100::/32',
    '2a06:98c0::/29',
    '2c0f:f248::/32',
))


def _ip_address(value):
    try:
        return ipaddress.ip_address((value or '').strip())
    except ValueError:
        return None


def is_cloudflare_ip(ip):
    address = _ip_address(ip)
    return address is not None and any(address in network for network in CLOUDFLARE_NETWORKS)


def get_client_ip(request):
    peer = request.META.get('REMOTE_ADDR') or ''

    # plogical/phpmyadminsignin.php validates panel sessions over loopback and
    # passes on the address its own request came from, so the same rule below
    # applies to it.  Only local callers can set this.
    loopback = _ip_address(peer)
    if loopback is not None and loopback.is_loopback:
        local_peer = _ip_address(request.META.get('HTTP_X_CYBERPANEL_PEER'))
        if local_peer is not None:
            peer = str(local_peer)

    forwarded = _ip_address(request.META.get('HTTP_CF_CONNECTING_IP'))
    if forwarded is not None and is_cloudflare_ip(peer):
        return str(forwarded)

    return peer
