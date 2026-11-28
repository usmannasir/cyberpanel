"""Fetch a remote image for an e-mail shown in webmail.

The response is served from the panel's own address, so it must never be
something a browser can run (SVG, HTML) and the request must never reach the
server's own network.  Every hop of the fetch is checked:

* only http and https on their standard ports;
* every address the name resolves to must be public, and the connection is
  made to the address that was checked, so a second DNS answer cannot move it;
* redirects are followed by hand, a few at most, each one checked again;
* the body must be a raster image recognised from its own bytes, and the type
  sent to the browser is the recognised one, not the remote header.
"""

import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import quote, urljoin, urlsplit

MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
TIMEOUT = 10
DEADLINE = 30
READ_CHUNK = 64 * 1024
STANDARD_PORTS = {'http': 80, 'https': 443}
REDIRECT_STATUSES = (301, 302, 303, 307, 308)
USER_AGENT = 'CyberPanel-Webmail-Proxy/1.1'

# Ranges that reach another network through a translator or tunnel
# (NAT64, 6to4).  The address itself can look public.
TRANSLATED_NETWORKS = tuple(ipaddress.ip_network(net) for net in (
    '64:ff9b::/96', '64:ff9b:1::/48', '2002::/16',
))

# Headers browsers send for images served by this proxy.
RESPONSE_POLICY = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"


class ImageProxyError(Exception):
    """The image cannot be fetched safely."""


def is_public_address(text):
    try:
        address = ipaddress.ip_address(str(text).split('%', 1)[0])
    except ValueError:
        return False
    if address.version == 6:
        if address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        elif any(address in network for network in TRANSLATED_NETWORKS):
            return False
    return bool(
        address.is_global
        and not address.is_multicast
        and not address.is_private
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_reserved
        and not address.is_unspecified
    )


def resolve_public_addresses(host, port, resolver=socket.getaddrinfo):
    """Return the addresses of host; refuse if any answer is not public."""
    try:
        answers = resolver(host, port, 0, socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, ValueError):
        raise ImageProxyError('The image address does not resolve.')
    addresses = []
    for family, _type, _proto, _name, sockaddr in answers:
        if family in (socket.AF_INET, socket.AF_INET6) and sockaddr[0] not in addresses:
            addresses.append(sockaddr[0])
    if not addresses:
        raise ImageProxyError('The image address does not resolve.')
    if not all(is_public_address(address) for address in addresses):
        raise ImageProxyError('The image address is not public.')
    return addresses


def sniff_image_type(data):
    """Media type of a raster image recognised from its first bytes."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    if data[4:8] == b'ftyp' and data[8:12] in (b'avif', b'avis'):
        return 'image/avif'
    if data[:2] == b'BM':
        return 'image/bmp'
    if data[:4] == b'\x00\x00\x01\x00':
        return 'image/x-icon'
    return None


def check_url(url):
    """Split an image URL into (scheme, host, port, request target)."""
    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise ImageProxyError('Invalid image address.')
    if scheme not in STANDARD_PORTS or not host:
        raise ImageProxyError('Invalid image address.')
    if parts.username is not None or parts.password is not None:
        raise ImageProxyError('Invalid image address.')
    if port is None:
        port = STANDARD_PORTS[scheme]
    if port != STANDARD_PORTS[scheme]:
        raise ImageProxyError('Images are fetched from standard web ports only.')
    target = quote(parts.path or '/', safe="/%:@!$&'()*+,;=-._~")
    if parts.query:
        target += '?' + quote(parts.query, safe="/%:@!$&'()*+,;=-._~?")
    return scheme, host, port, target


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, timeout):
        super().__init__(host, port, timeout=timeout)
        self.pinned_address = address

    def connect(self):
        self.sock = socket.create_connection((self.pinned_address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, address, timeout):
        context = ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=context)
        self.pinned_address = address
        self.pinned_context = context

    def connect(self):
        sock = socket.create_connection((self.pinned_address, self.port), self.timeout)
        try:
            # The certificate is checked against the name, not the address.
            self.sock = self.pinned_context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


CONNECTIONS = {'http': _PinnedHTTPConnection, 'https': _PinnedHTTPSConnection}


def _read_body(response, deadline):
    length = response.getheader('Content-Length')
    if length and length.strip().isdigit() and int(length) > MAX_BYTES:
        raise ImageProxyError('The image is too large.')
    data = b''
    while len(data) <= MAX_BYTES:
        if time.monotonic() > deadline:
            raise ImageProxyError('The image took too long to arrive.')
        chunk = response.read(min(READ_CHUNK, MAX_BYTES + 1 - len(data)))
        if not chunk:
            return data
        data += chunk
    raise ImageProxyError('The image is too large.')


def _get(scheme, host, port, target, addresses, connections, deadline):
    """Ask each checked address in turn; return (status, Location, body)."""
    failure = None
    for address in addresses:
        if time.monotonic() > deadline:
            break
        connection = connections[scheme](host, port, address, TIMEOUT)
        try:
            try:
                connection.request('GET', target, headers={
                    'User-Agent': USER_AGENT,
                    'Accept': 'image/avif,image/webp,image/png,image/jpeg,image/gif,image/*;q=0.8',
                })
            except (OSError, http.client.HTTPException) as error:
                failure = error  # this address cannot be reached: try the next
                continue
            response = connection.getresponse()
            if response.status in REDIRECT_STATUSES:
                return response.status, response.getheader('Location'), b''
            if response.status != 200:
                raise ImageProxyError('The image server answered %d.' % response.status)
            return response.status, None, _read_body(response, deadline)
        except ImageProxyError:
            raise
        except (OSError, http.client.HTTPException, ValueError) as error:
            raise ImageProxyError('The image could not be fetched (%s).' % type(error).__name__)
        finally:
            connection.close()
    raise ImageProxyError('The image server cannot be reached (%s).' % type(failure).__name__)


def fetch_image(url, resolver=socket.getaddrinfo, connections=None):
    """Return (bytes, media type) of the raster image at url."""
    connections = connections or CONNECTIONS
    deadline = time.monotonic() + DEADLINE
    for _hop in range(MAX_REDIRECTS + 1):
        scheme, host, port, target = check_url(url)
        addresses = resolve_public_addresses(host, port, resolver)
        status, location, data = _get(scheme, host, port, target, addresses,
                                      connections, deadline)
        if status in REDIRECT_STATUSES:
            if not location:
                raise ImageProxyError('The image address redirects nowhere.')
            url = urljoin(url, location.strip())
            continue
        media_type = sniff_image_type(data)
        if media_type is None:
            raise ImageProxyError('The address does not hold a supported image.')
        return data, media_type
    raise ImageProxyError('The image address redirects too often.')
