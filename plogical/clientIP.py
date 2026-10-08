#!/usr/local/CyberCP/bin/python
import ipaddress
import os
import sys
import tempfile

# CF-Connecting-IP is only trusted when the request comes from Cloudflare,
# otherwise any client could choose the IP address CyberPanel binds its
# session to.  Cloudflare publishes its edge ranges at these URLs; running
# this file (monthly from root's crontab, and once after install/upgrade)
# saves them to CLOUDFLARE_IPS_FILE.  The built-in copy is used until that
# succeeds.
CLOUDFLARE_IPS_URLS = ('https://www.cloudflare.com/ips-v4', 'https://www.cloudflare.com/ips-v6')
CLOUDFLARE_IPS_FILE = '/etc/cyberpanel/cloudflare-ips.txt'

BUILTIN_CLOUDFLARE_NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in (
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

# A truncated or error-page download must never replace the list.
MINIMUM_NETWORKS = 10

_saved = {'mtime': None, 'networks': BUILTIN_CLOUDFLARE_NETWORKS}


def _parse_networks(text):
    networks = tuple(ipaddress.ip_network(line.strip()) for line in text.splitlines() if line.strip())
    if len(networks) < MINIMUM_NETWORKS:
        raise ValueError('only %d Cloudflare networks' % len(networks))
    return networks


def cloudflare_networks():
    try:
        mtime = os.path.getmtime(CLOUDFLARE_IPS_FILE)
    except OSError:
        return BUILTIN_CLOUDFLARE_NETWORKS

    if mtime != _saved['mtime']:
        try:
            with open(CLOUDFLARE_IPS_FILE) as handle:
                networks = _parse_networks(handle.read())
        except (OSError, ValueError):
            networks = BUILTIN_CLOUDFLARE_NETWORKS
        _saved.update(mtime=mtime, networks=networks)
    return _saved['networks']


def _ip_address(value):
    try:
        return ipaddress.ip_address((value or '').strip())
    except ValueError:
        return None


def is_cloudflare_ip(ip):
    address = _ip_address(ip)
    return address is not None and any(address in network for network in cloudflare_networks())


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


def refresh_cloudflare_ips():
    import requests

    text = ''
    for url in CLOUDFLARE_IPS_URLS:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        text += response.text + '\n'
    networks = _parse_networks(text)

    # Written beside the target and renamed, so the panel never reads a
    # partial file.  World-readable because the panel does not run as root.
    directory = os.path.dirname(CLOUDFLARE_IPS_FILE)
    descriptor, temporary_path = tempfile.mkstemp(dir=directory, prefix='.cloudflare-ips.')
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write('\n'.join(str(network) for network in networks) + '\n')
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, CLOUDFLARE_IPS_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return len(networks)


if __name__ == '__main__':
    try:
        print('Saved %d Cloudflare networks to %s' % (refresh_cloudflare_ips(), CLOUDFLARE_IPS_FILE))
    except Exception as error:
        print('Could not refresh Cloudflare IP ranges: %s' % error)
        sys.exit(1)
