import hashlib
import ipaddress
import os
import socket
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen


PLUGIN_VERSION = '0.4.8'
PLUGIN_URL = 'https://github.com/usmannasir/cyberedge-cache/releases/download/v0.4.8/cyberedge-cache-0.4.8-e14ab90.zip'
PLUGIN_SHA256 = '2d72c63cf9ba1d51bf0774ed50b9ac16c92ec24987b7341507946ec281b46986'
PLATFORM_START_URL = 'https://platform.cyberpersons.com/edge/get-started/'
MAX_PLUGIN_BYTES = 10 * 1024 * 1024


def download_verified_plugin(opener=urlopen):
    """Download the pinned release and return a readable temporary ZIP."""
    path = None
    try:
        response = opener(PLUGIN_URL, timeout=20)
        try:
            declared = response.headers.get('Content-Length')
            if declared and int(declared) > MAX_PLUGIN_BYTES:
                raise ValueError('CyberEdge plugin download is unexpectedly large.')
            digest = hashlib.sha256()
            total = 0
            handle, path = tempfile.mkstemp(prefix='cyberedge-cache-', suffix='.zip')
            with os.fdopen(handle, 'wb') as output:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_PLUGIN_BYTES:
                        raise ValueError('CyberEdge plugin download exceeded its size limit.')
                    digest.update(chunk)
                    output.write(chunk)
        finally:
            response.close()
        if digest.hexdigest() != PLUGIN_SHA256:
            raise ValueError('CyberEdge plugin checksum verification failed.')
        os.chmod(path, 0o644)
        return path
    except Exception:
        if path and os.path.exists(path):
            os.unlink(path)
        raise


def wordpress_admin_redirect(destination):
    """Return an allow-listed WordPress admin destination for panel auto-login."""
    if destination == 'cyberedge':
        return '/wp-admin/tools.php?page=cyberedge-cache'
    return '/wp-admin'


def public_edge_status(site_url, resolver=socket.getaddrinfo, runner=subprocess.run):
    """Read customer-facing Edge headers without following redirects or private DNS."""
    parts = urlsplit(site_url if '://' in site_url else 'https://' + site_url)
    if parts.scheme != 'https' or not parts.hostname:
        return {'state': 'unavailable'}
    try:
        host = parts.hostname.encode('idna').decode('ascii')
        addresses = sorted({row[4][0] for row in resolver(host, 443, type=socket.SOCK_STREAM)})
        public = [address for address in addresses if ipaddress.ip_address(address).is_global]
    except Exception:
        return {'state': 'unavailable'}
    if not public:
        return {'state': 'unavailable'}
    try:
        result = runner([
            '/usr/bin/curl', '--silent', '--show-error', '--head', '--max-time', '5',
            '--max-redirs', '0', '--resolve', '%s:443:%s' % (host, public[0]),
            'https://%s%s' % (host, parts.path or '/'),
        ], capture_output=True, text=True, timeout=7, check=False)
    except Exception:
        return {'state': 'unavailable'}
    headers = {}
    for line in result.stdout.splitlines():
        if ':' in line:
            name, value = line.split(':', 1)
            headers[name.strip().lower()] = value.strip()
    cache = headers.get('x-cyberedge-cache', '').lower()
    node = headers.get('x-cyberedge-node', '')
    return {
        'state': 'active' if result.returncode == 0 and cache in ('hit', 'miss', 'bypass') and node else 'inactive',
        'cache': cache,
        'node': node,
        'reason': headers.get('x-cyberedge-cache-reason', ''),
    }
