"""The controller's side of the signed channel to a node.

One request goes out over one TLS connection and one reply comes back. The node
is trusted for two things only, both fixed when the two servers were paired: the
exact certificate it serves and its identity key. The certificate is compared
before a single byte of the request is written, and nothing of a reply reaches
the caller until the node's signature over that reply, bound to this very
request, has been verified. No certificate authority, proxy setting, redirect,
cookie or stored session takes part.

How the signed fields of crypto.request_message travel:

    method, path, query      the request line (no '?' when the query is empty)
    host:port                Host
    content type             Content-Type (the header is absent when it is '-')
    length, body hash        the body itself
    link id, node id, time,
    nonce, actor, mode       the X-CPMS-* headers of HEADERS

A field that HTTP already carries is not repeated in a header: the node has to
rebuild the signed bytes from what its own application is about to act on.
"""
import hashlib
import hmac
import ipaddress
import os
import re
import socket
import ssl
import threading
import time

from multiServer import crypto

# The one table of header names; the node's gateway reads the same one. The
# signature is 128 lower-case hex digits and uses the same header in a reply,
# which carries no other X-CPMS-* header.
HEADERS = {
    'link': 'X-CPMS-Link',
    'node': 'X-CPMS-Node',
    'timestamp': 'X-CPMS-Timestamp',
    'nonce': 'X-CPMS-Nonce',
    'actor': 'X-CPMS-Actor',
    'mode': 'X-CPMS-Mode',
    'signature': 'X-CPMS-Signature',
}

CONNECT_TIMEOUT = 5  # seconds for each of: name lookup, TCP connect, TLS handshake
DEADLINE = 30  # seconds for the whole exchange, whatever the node does
MAX_REQUEST_BODY = 8 * 1024 * 1024
MAX_RESPONSE = 8 * 1024 * 1024  # status line, headers and body together
MAX_RESPONSE_HEAD = 32 * 1024
MAX_RESPONSE_HEADERS = 100

LOOPBACK = 'loopback'

# Where a link may never lead, first match first. The table is spelled out here,
# not taken from the ipaddress module's own flags, because those differ between
# Python versions.
_REFUSED = tuple((ipaddress.ip_network(network), kind) for network, kind in (
    # Metadata services are named first; Azure's has an otherwise public address.
    ('169.254.169.254/32', 'cloud metadata'), ('169.254.170.2/32', 'cloud metadata'),
    ('100.100.100.200/32', 'cloud metadata'), ('168.63.129.16/32', 'cloud metadata'),
    ('fd00:ec2::254/128', 'cloud metadata'), ('fd20:ce::254/128', 'cloud metadata'),
    ('0.0.0.0/8', 'unspecified'), ('127.0.0.0/8', LOOPBACK),
    ('10.0.0.0/8', 'private'), ('172.16.0.0/12', 'private'), ('192.168.0.0/16', 'private'),
    ('100.64.0.0/10', 'carrier-grade NAT'), ('169.254.0.0/16', 'link-local'),
    ('224.0.0.0/4', 'multicast'),
    ('192.0.0.0/24', 'reserved'), ('192.0.2.0/24', 'reserved'), ('192.88.99.0/24', 'reserved'),
    ('198.18.0.0/15', 'reserved'), ('198.51.100.0/24', 'reserved'), ('203.0.113.0/24', 'reserved'),
    ('240.0.0.0/4', 'reserved'),
    ('::/128', 'unspecified'), ('::1/128', LOOPBACK),
    # An IPv4 address written as IPv6 is refused whatever it holds: write it as IPv4.
    ('::ffff:0:0/96', 'IPv4-mapped'),
    ('fc00::/7', 'private'), ('fe80::/10', 'link-local'), ('ff00::/8', 'multicast'),
    # Public IPv6 is 2000::/3 and nothing else; within it these ranges carry an
    # IPv4 address (6to4, Teredo) or are set aside.
    ('::/3', 'reserved'), ('4000::/2', 'reserved'), ('8000::/1', 'reserved'),
    ('2001::/23', 'reserved'), ('2001:db8::/32', 'reserved'), ('2002::/16', 'reserved'),
    ('3fff::/20', 'reserved'),
))

_HEX64 = re.compile(r'[0-9a-f]{64}')
_SIGNATURE = re.compile(r'[0-9a-f]{128}')
_IPV4 = re.compile(r'(?:(?:0|[1-9][0-9]{0,2})\.){3}(?:0|[1-9][0-9]{0,2})')
_IPV6 = re.compile(r'[0-9a-f:.]{2,45}')
_NAME = re.compile(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?')
_STATUS_LINE = re.compile(rb'HTTP/1\.[01] ([0-9]{3})(?: [\t\x20-\x7e\x80-\xff]*)?')
_HEADER_LINE = re.compile(rb"([!#$%&'*+.^_`|~0-9A-Za-z-]+):([\t\x20-\x7e\x80-\xff]*)")
_LENGTH = re.compile(r'0|[1-9][0-9]{0,17}')


class TransportError(Exception):
    """Any refusal by this module. No message holds a key, a signature, a body or the pin."""


class InvalidLink(TransportError):
    """The link description is not exactly what pairing produces."""


class InvalidRequest(TransportError):
    """A request field cannot be signed; nothing was sent."""


class RefusedAddress(TransportError):
    """The node's address is one a link may never connect to."""


class ConnectionFailed(TransportError):
    """The node could not be reached or the connection broke."""


class TimedOut(ConnectionFailed):
    """The node did not finish within the time allowed."""


class CertificateMismatch(TransportError):
    """The server did not present the pinned certificate; nothing was sent to it."""


class MalformedResponse(TransportError):
    """The reply is not the one plain, whole reply a node sends."""


class ResponseTooLarge(MalformedResponse):
    """The reply is, or says it is, larger than a reply may be."""


class RedirectRefused(MalformedResponse):
    """The reply points somewhere else; a link is never followed anywhere."""


class BadSignature(TransportError):
    """The reply is unsigned or not signed by the node for this request."""


def check_address(address, allow_loopback_for_tests=False):
    """The address, parsed, when a link may connect to it; RefusedAddress otherwise.

    allow_loopback_for_tests exists for the test suite alone, which has to talk
    to a server on this machine. It opens the loopback range and nothing else.
    """
    try:
        if not isinstance(address, str) or '%' in address:
            raise ValueError
        parsed = ipaddress.ip_address(address)
    except ValueError:
        raise RefusedAddress('This is not an address a link can connect to.') from None
    for network, kind in _REFUSED:
        if parsed in network:
            if kind == LOOPBACK and allow_loopback_for_tests is True:
                break
            raise RefusedAddress('A link may not connect to this address (%s).' % kind)
    return parsed


class Link(object):
    """One paired node as the controller knows it; checked when built, never changed.

    host is a public IPv4 or IPv6 address in its one plain spelling, or a full
    lower-case host name. Anything that a resolver could read as an address in
    another notation (127.1, 0x7f000001, 2130706433) is not a host name here.
    """
    __slots__ = ('link_id', 'node_id', 'host', 'port', 'authority', 'node_key', 'private_key',
                 'tls_pin', 'allow_loopback_for_tests')

    def __init__(self, link_id, node_id, host, port, node_key, private_key, tls_pin,
                 allow_loopback_for_tests=False):
        if not isinstance(allow_loopback_for_tests, bool):
            raise InvalidLink('Invalid loopback allowance.')
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise InvalidLink('Invalid port.')
        _check_host(host, allow_loopback_for_tests)
        authority = ('[%s]:%d' if ':' in host else '%s:%d') % (host, port)
        if not isinstance(tls_pin, str) or _HEX64.fullmatch(tls_pin) is None:
            raise InvalidLink('Invalid certificate pin.')
        try:
            # The same checks that every later request has to pass.
            crypto.request_message(link_id, node_id, 'GET', authority, '/', '', '-', b'', 0, '0' * 32,
                                   'check', 'json')
            crypto.public_key(private_key)
            named = crypto.node_id(node_key)
        except ValueError as error:
            raise InvalidLink(str(error)) from None
        if named != node_id:
            raise InvalidLink('The node id is not the fingerprint of the node key.')
        for name, value in zip(Link.__slots__, (link_id, node_id, host, port, authority, node_key,
                                                private_key, tls_pin, allow_loopback_for_tests)):
            object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        raise AttributeError('A link description cannot be changed.')

    def __delattr__(self, name):
        raise AttributeError('A link description cannot be changed.')

    def __repr__(self):
        # Never the keys or the pin: this text can end up in a log.
        return 'Link(%s at %s)' % (self.link_id, self.authority)

    def __reduce__(self):
        # The private key is stored in the sealed link record and nowhere else.
        raise TypeError('A link description is not serialised.')


def send(link, method, path, query, content_type, body, actor, mode, now=None, nonce=None):
    """Send one signed request to the node; return (status, content type, body) of its verified reply.

    now and nonce are for tests. Left out, the time is read and the nonce is
    drawn here, so that no reply to an earlier request can ever verify.
    """
    if type(link) is not Link:
        raise InvalidLink('A link description is required.')
    deadline = time.monotonic() + DEADLINE
    timestamp = int(time.time()) if now is None else now
    nonce = os.urandom(16).hex() if nonce is None else nonce
    try:
        signed = crypto.request_message(link.link_id, link.node_id, method, link.authority, path, query,
                                        content_type, body, timestamp, nonce, actor, mode)
    except ValueError as error:
        raise InvalidRequest(str(error)) from None
    if len(body) > MAX_REQUEST_BODY:
        raise InvalidRequest('The request body is too large.')
    head = _request_head(link, method, path, query, content_type, len(body), timestamp, nonce, actor,
                         mode, crypto.sign(link.private_key, signed).hex())
    connection = _connect(link, deadline)
    try:
        _write(connection, head + body, deadline)
        status, reply_type, reply_body, signature = _read_reply(connection, deadline)
    finally:
        connection.close()
    try:
        expected = crypto.response_message(link.link_id, link.node_id, nonce, signed, status, reply_type,
                                           reply_body)
    except ValueError:
        raise MalformedResponse('The node named an invalid content type.') from None
    if not crypto.verify(link.node_key, signature, expected):
        raise BadSignature('The reply is not signed by the node for this request.')
    return status, reply_type, reply_body


def _check_host(host, allow_loopback_for_tests):
    if not isinstance(host, str):
        raise InvalidLink('Invalid host.')
    try:
        if ':' in host:
            if _IPV6.fullmatch(host) is None:
                raise ValueError
            address = ipaddress.IPv6Address(host)
            check_address(host, allow_loopback_for_tests)
            # One spelling per address, the one that is signed and sent as Host.
            if str(address) != host:
                raise ValueError
        elif _IPV4.fullmatch(host):
            ipaddress.IPv4Address(host)
            check_address(host, allow_loopback_for_tests)
        elif len(host) > 253 or _NAME.fullmatch(host) is None:
            raise ValueError
    except ValueError:
        raise InvalidLink('Invalid host.') from None


def _request_head(link, method, path, query, content_type, length, timestamp, nonce, actor, mode,
                  signature):
    # Every value has passed a pattern that admits no line break, so the lines
    # below are exactly the lines sent.
    lines = ['%s %s HTTP/1.1' % (method, path + '?' + query if query else path),
             'Host: ' + link.authority, 'Connection: close', 'Accept-Encoding: identity']
    if content_type != '-':
        lines.append('Content-Type: ' + content_type)
    if method == 'POST':
        lines.append('Content-Length: %d' % length)
    for field, value in (('link', link.link_id), ('node', link.node_id), ('timestamp', timestamp),
                         ('nonce', nonce), ('actor', actor), ('mode', mode), ('signature', signature)):
        lines.append('%s: %s' % (HEADERS[field], value))
    return ('\r\n'.join(lines) + '\r\n\r\n').encode('ascii')


def _left(deadline):
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimedOut('The node did not answer in time.')
    return left


def _lookup(host, port, deadline):
    """The addresses of a name, asked once. The resolver has no time limit of its own."""
    answer = []

    def ask():
        try:
            answer.append(socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM))
        except Exception:
            answer.append(None)

    worker = threading.Thread(target=ask)
    worker.daemon = True
    worker.start()
    worker.join(min(CONNECT_TIMEOUT, _left(deadline)))
    if not answer:
        raise TimedOut('The name of the node was not resolved in time.')
    found = []
    for entry in answer[0] or ():
        if entry[0] in (socket.AF_INET, socket.AF_INET6) and entry[4][0] not in found:
            found.append(entry[4][0])
    if not found:
        raise ConnectionFailed('The name of the node could not be resolved.')
    return found


def _node_addresses(link, deadline):
    """Every address of the node, each one checked; none is looked up again later."""
    try:
        ipaddress.ip_address(link.host)
        found = [link.host]
    except ValueError:
        found = _lookup(link.host, link.port, deadline)
    # One refused address refuses the name: a public answer beside an internal
    # one is how a name is made to lead inside.
    return [check_address(address, link.allow_loopback_for_tests) for address in found]


def _tls_context():
    """TLS that trusts no authority and no name: the pinned certificate alone names the node."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    except (AttributeError, ValueError):  # Python 3.6
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    return context


def _open(address, port, deadline):
    """A TCP connection to exactly this checked address; no name is involved."""
    family, target = socket.AF_INET, (str(address), port)
    if address.version == 6:
        family, target = socket.AF_INET6, (str(address), port, 0, 0)
    connection = socket.socket(family, socket.SOCK_STREAM)
    try:
        connection.settimeout(min(CONNECT_TIMEOUT, _left(deadline)))
        connection.connect(target)
    except socket.timeout:
        connection.close()
        raise TimedOut('The node did not accept a connection in time.') from None
    except OSError:
        connection.close()
        raise ConnectionFailed('Could not connect to the node.') from None
    except BaseException:
        connection.close()
        raise
    return connection


def _secure(connection, link, deadline):
    """TLS on the connection, handed back only if the server holds the pinned certificate."""
    name = link.host if _NAME.fullmatch(link.host) else None
    try:
        connection.settimeout(min(CONNECT_TIMEOUT, _left(deadline)))
        secured = _tls_context().wrap_socket(connection, server_hostname=name)
    except socket.timeout:
        connection.close()
        raise TimedOut('The node did not complete TLS in time.') from None
    except (OSError, ValueError):
        connection.close()
        raise ConnectionFailed('TLS with the node failed.') from None
    except BaseException:
        connection.close()
        raise
    certificate = secured.getpeercert(binary_form=True)
    if not certificate or not hmac.compare_digest(hashlib.sha256(certificate).hexdigest(), link.tls_pin):
        secured.close()
        raise CertificateMismatch('The server did not present the certificate this link was paired with.')
    return secured


def _connect(link, deadline):
    failure = ConnectionFailed('Could not connect to the node.')
    for address in _node_addresses(link, deadline):
        try:
            return _secure(_open(address, link.port, deadline), link, deadline)
        except ConnectionFailed as error:
            failure = error
    raise failure


def _within(deadline, connection, call, argument):
    """One socket call, allowed only what is left of the whole exchange."""
    try:
        connection.settimeout(_left(deadline))
        return call(argument)
    except socket.timeout:
        raise TimedOut('The node did not answer in time.') from None
    except OSError:
        raise ConnectionFailed('The connection to the node broke.') from None


def _write(connection, data, deadline):
    view = memoryview(data)
    while view:
        view = view[_within(deadline, connection, connection.send, view[:65536]):]


def _read_reply(connection, deadline):
    """One whole reply and then the end of the connection: (status, content type, body, signature)."""
    received = bytearray()
    while True:
        end = received.find(b'\r\n\r\n')
        if end + 4 > MAX_RESPONSE_HEAD or (end == -1 and len(received) >= MAX_RESPONSE_HEAD):
            raise ResponseTooLarge('The node sent too many reply headers.')
        if end != -1:
            break
        chunk = _within(deadline, connection, connection.recv, 65536)
        if not chunk and not received:
            raise ConnectionFailed('The node closed the connection without replying.')
        if not chunk:
            raise MalformedResponse('The node closed the connection in the middle of its reply headers.')
        received += chunk
    status, length, content_type, signature = _parse_head(bytes(received[:end]))
    if end + 4 + length > MAX_RESPONSE:
        raise ResponseTooLarge('The reply is larger than a reply may be.')
    body = received[end + 4:]
    # Read to the end of the connection, not just the declared length: whatever
    # follows one reply, a second reply included, makes the whole exchange void.
    while len(body) <= length:
        try:
            chunk = _within(deadline, connection, connection.recv, 65536)
        except TimedOut:
            raise
        except ConnectionFailed:
            # A node that drops the connection without the TLS goodbye has still
            # ended it; the declared length decides whether the reply is whole.
            chunk = b''
        if not chunk:
            break
        body += chunk
    if len(body) != length:
        raise MalformedResponse('The reply does not have the length it declares.')
    return status, content_type, bytes(body), signature


def _parse_head(head):
    lines = head.split(b'\r\n')
    first = _STATUS_LINE.fullmatch(lines[0])
    if first is None or not 200 <= int(first.group(1)) <= 599:
        raise MalformedResponse('The node did not send a final HTTP reply.')
    if len(lines) - 1 > MAX_RESPONSE_HEADERS:
        raise MalformedResponse('The node sent too many reply headers.')
    status = int(first.group(1))
    headers = {}
    for line in lines[1:]:
        matched = _HEADER_LINE.fullmatch(line)
        if matched is None:
            raise MalformedResponse('The node sent a malformed reply header.')
        headers.setdefault(matched.group(1).lower(), []).append(matched.group(2).strip(b' \t'))

    def one(name):
        values = headers.get(name.lower().encode('ascii'), [])
        if len(values) > 1:
            raise MalformedResponse('The node repeated a reply header.')
        return values[0].decode('latin-1') if values else None

    if 300 <= status <= 399:
        raise RedirectRefused('The node answered with a redirect.')
    if one('Transfer-Encoding') is not None or one('Content-Encoding') not in (None, 'identity'):
        raise MalformedResponse('The node did not send its reply whole and unencoded.')
    length = one('Content-Length')
    if length is None or _LENGTH.fullmatch(length) is None:
        raise MalformedResponse('The node did not say how long its reply is.')
    signature = one(HEADERS['signature'])
    if signature is None or _SIGNATURE.fullmatch(signature) is None:
        raise BadSignature('The reply is not signed.')
    content_type = one('Content-Type')
    # Parameters such as the character set are not signed and are not passed on.
    content_type = '-' if content_type is None else content_type.split(';', 1)[0].strip(' \t')
    return status, int(length), content_type, bytes.fromhex(signature)
