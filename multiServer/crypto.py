"""Signing for Multi-Server Manager links.

A controller signs every request to a node, and a node signs every reply, with
Ed25519 keys exchanged when the two servers were paired. Each signed message
begins with a line naming its type, has a fixed number of lines, and holds no
field that could contain a line break, so one kind of message can never be read
as another and no field can be read two ways.
"""
import hashlib
import hmac
import re

REQUEST = 'CPMS1-REQ'
RESPONSE = 'CPMS1-RSP'
HELLO = 'CPMS1-HELLO'
PAIR_REQUEST = 'CPMS1-PAIR-REQ'
PAIR_RESPONSE = 'CPMS1-PAIR-RSP'
PAIR_CONFIRMATION = 'CPMS1-PAIR-SAS'
PAIR_VALUE = 'CPMS1-PAIR-VALUE'
PAIR_COMMITMENT = 'CPMS1-PAIR-COMMIT'

METHODS = ('GET', 'POST')
MODES = ('json', 'page', 'static', 'inventory', 'ticket', 'confirm', 'rotate')
MAX_PATH = 2048
MAX_QUERY = 4096

_HEX32 = re.compile(r'[0-9a-f]{32}')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_PATH = re.compile(r'/(?:[A-Za-z0-9._~@+-]+/)*(?:[A-Za-z0-9._~@+-]+)?')
_QUERY = re.compile(r'[A-Za-z0-9._~%=&+-]*')
_HOST = re.compile(r'(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:.]{2,45}\]):([0-9]{1,5})')
_MEDIA_TYPE = re.compile(r'[a-z0-9][a-z0-9!#$&^_.+-]{0,62}/[a-z0-9][a-z0-9!#$&^_.+-]{0,62}')
_ACTOR = re.compile(r'[A-Za-z0-9_.@-]{1,50}')
_ADDRESS = re.compile(r'[0-9a-f:.]{2,45}')  # one IPv4 or IPv6 address as multiServer/addresses.py spells it


def _ed25519():
    # Imported on use: a panel without a usable library keeps working with the
    # feature switched off instead of failing to start.
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    return ed25519, serialization, InvalidSignature


def generate_private_key():
    ed25519, serialization, _ = _ed25519()
    return ed25519.Ed25519PrivateKey.generate().private_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption())


def public_key(private):
    ed25519, serialization, _ = _ed25519()
    return ed25519.Ed25519PrivateKey.from_private_bytes(_raw_key(private)).public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


def sign(private, message):
    if not isinstance(message, bytes):
        raise ValueError('Only bytes are signed.')
    ed25519 = _ed25519()[0]
    return ed25519.Ed25519PrivateKey.from_private_bytes(_raw_key(private)).sign(message)


def verify(public, signature, message):
    """True only for a valid signature; never raises."""
    try:
        if not (isinstance(signature, bytes) and len(signature) == 64 and isinstance(message, bytes)):
            return False
        ed25519 = _ed25519()[0]
        ed25519.Ed25519PublicKey.from_public_bytes(_raw_key(public)).verify(signature, message)
        return True
    except Exception:
        return False


def node_id(public):
    """A node is named by the fingerprint of its identity key."""
    return hashlib.sha256(_raw_key(public)).hexdigest()


# The curve of Ed25519: -x^2 + y^2 = 1 + d x^2 y^2 over the integers modulo p.
_P = 2 ** 255 - 19
_D = -121665 * pow(121666, _P - 2, _P) % _P
_ROOT_OF_MINUS_ONE = pow(2, (_P - 1) // 4, _P)


def usable_public_key(public):
    """Whether 32 bytes are a public key that only the holder of its private key can sign for. Never raises.

    Eight points of the curve have small order. Under such a key a signature
    can be made up by anybody, for any message, without a private key, and the
    signing library does not refuse them. A key another server sends is
    therefore kept only when it names a point of the curve and eight times
    that point is not the neutral point. The bytes are read as leniently as
    any library reads them (a number above p is taken modulo p, and so is the
    sign of zero), so that no second spelling of a small point gets through.
    """
    try:
        number = int.from_bytes(_raw_key(public), 'little')
        y, odd = (number & (2 ** 255 - 1)) % _P, number >> 255
        # x^2 = (y^2 - 1) / (d y^2 + 1); the divisor is never zero because d is not a square.
        square = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
        x = pow(square, (_P + 3) // 8, _P)
        if (x * x - square) % _P:
            x = x * _ROOT_OF_MINUS_ONE % _P
        if (x * x - square) % _P:
            return False  # not a point of the curve
        if x & 1 != odd:
            x = (_P - x) % _P
        for _ in range(3):
            # Doubling; the addition law of this curve is complete, so no divisor is zero.
            product = _D * x * x * y * y % _P
            x, y = (2 * x * y * pow(1 + product, _P - 2, _P) % _P,
                    (y * y + x * x) * pow(1 - product, _P - 2, _P) % _P)
        return (x, y) != (0, 1)
    except Exception:
        return False


def self_test():
    """Whether Ed25519 works here (it is disabled, for example, in FIPS mode)."""
    try:
        private = bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60')
        expected = bytes.fromhex('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')
        if public_key(private) != expected:
            return False
        fresh = generate_private_key()
        signature = sign(fresh, b'self-test')
        return verify(public_key(fresh), signature, b'self-test') \
            and not verify(public_key(fresh), signature, b'self-tesT')
    except Exception:
        return False


def request_message(link_id, node_id, method, host, path, query, content_type, body, timestamp,
                    nonce, actor, mode):
    """The bytes a controller signs for one request to a node."""
    body = _body(body)
    if method not in METHODS or (method == 'GET' and body):
        raise ValueError('Unsupported request method.')
    if mode not in MODES:
        raise ValueError('Unsupported request mode.')
    return _lines(REQUEST, _match(_HEX32, link_id, 'link'), _match(_HEX64, node_id, 'node'), method,
                  _host(host), _path(path), _query(query), _content_type(content_type), len(body),
                  hashlib.sha256(body).hexdigest(), _timestamp(timestamp), _match(_HEX32, nonce, 'nonce'),
                  _match(_ACTOR, actor, 'actor'), mode)


def response_message(link_id, node_id, nonce, request, status, content_type, body):
    """The bytes a node signs for its reply to one signed request."""
    if not isinstance(request, bytes) or not request.startswith(REQUEST.encode() + b'\n'):
        raise ValueError('A reply is bound to the signed request.')
    if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
        raise ValueError('Invalid status.')
    return _lines(RESPONSE, _match(_HEX32, link_id, 'link'), _match(_HEX64, node_id, 'node'),
                  _match(_HEX32, nonce, 'nonce'), hashlib.sha256(request).hexdigest(), status,
                  _content_type(content_type), hashlib.sha256(_body(body)).hexdigest())


def hello_message(node_id, nonce, tls_fingerprint, timestamp):
    """The bytes a node signs to name the certificate it currently serves."""
    return _lines(HELLO, _match(_HEX64, node_id, 'node'), _match(_HEX32, nonce, 'nonce'),
                  _match(_HEX64, tls_fingerprint, 'certificate fingerprint'), _timestamp(timestamp))


# Pairing, before the two servers share a key. Every key in these messages is a
# public key, written as 64 hexadecimal digits.

def pair_request_message(link_id, pairing_key, controller_key, node_id, tls_fingerprint, host, timestamp,
                         nonce):
    """The bytes a controller signs, with the one-time key of a pairing code, to ask a node for a link.

    pairing_key is the public half of that one-time key. The node fills in its
    own id and its own certificate, so a request made for another node, or for
    a connection that ends somewhere else, does not verify.
    """
    return _lines(PAIR_REQUEST, _match(_HEX32, link_id, 'link'), _match(_HEX64, pairing_key, 'pairing key'),
                  _match(_HEX64, controller_key, 'controller key'), _match(_HEX64, node_id, 'node'),
                  _match(_HEX64, tls_fingerprint, 'certificate fingerprint'), _host(host),
                  _timestamp(timestamp), _match(_HEX32, nonce, 'nonce'))


def pair_value(identity, pairing_key):
    """The value a node adds to one pairing, as 64 hexadecimal digits.

    Only the node can work it out (it is keyed with the node's identity key),
    it is different for every pairing code, and the node tells it to nobody
    before it has accepted the one request that uses the code up. So whoever
    asks for a link cannot know the confirmation number while it can still
    choose what the number is made from.
    """
    message = _lines(PAIR_VALUE, _match(_HEX64, pairing_key, 'pairing key'))
    return hmac.new(_raw_key(identity), message, hashlib.sha256).hexdigest()


def pair_commitment(value, host, tls_fingerprint, controller_ip):
    """What a pairing code says about the value before anybody has seen it, and about where the code was made.

    A code carries this and not the value. The node is thereby held to the
    value it had when it made the code, so a server that answers a pairing
    request cannot pick a value afterwards to arrive at a number of its
    choosing. It also fixes the address and certificate the code names and the
    one controller address the code was made for: with any of them changed,
    the value in the answer no longer matches the code.
    """
    return hashlib.sha256(_lines(PAIR_COMMITMENT, _match(_HEX64, value, 'pairing value'), _host(host),
                                 _match(_HEX64, tls_fingerprint, 'certificate fingerprint'),
                                 _match(_ADDRESS, controller_ip, 'controller address'))).hexdigest()


def pair_response_message(request, node_key, value, controller_ip):
    """The bytes a node signs, with its identity key, to accept exactly one pairing request.

    value is the node's pair_value for the code, controller_ip the address the
    node will take this controller's requests from.
    """
    if not isinstance(request, bytes) or not request.startswith(PAIR_REQUEST.encode() + b'\n'):
        raise ValueError('A pairing reply is bound to the pairing request.')
    return _lines(PAIR_RESPONSE, hashlib.sha256(request).hexdigest(), _match(_HEX64, node_key, 'node key'),
                  _match(_HEX64, value, 'pairing value'), _match(_ADDRESS, controller_ip, 'controller address'))


def pair_confirmation_message(link_id, pairing_key, controller_key, node_key, value):
    """What both servers keep of a pairing; the number their administrators compare is taken from it."""
    return _lines(PAIR_CONFIRMATION, _match(_HEX32, link_id, 'link'), _match(_HEX64, pairing_key, 'pairing key'),
                  _match(_HEX64, controller_key, 'controller key'), _match(_HEX64, node_key, 'node key'),
                  _match(_HEX64, value, 'pairing value'))


def _lines(*fields):
    return '\n'.join(str(field) for field in fields).encode('ascii')


def _raw_key(value):
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError('An Ed25519 key is 32 bytes.')
    return value


def _body(value):
    if not isinstance(value, bytes):
        raise ValueError('A body is bytes.')
    return value


def _match(pattern, value, name):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError('Invalid %s.' % name)
    return value


def _timestamp(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 10 ** 11:
        raise ValueError('Invalid time.')
    return value


def _host(value):
    matched = _HOST.fullmatch(value) if isinstance(value, str) else None
    if matched is None or not 1 <= int(matched.group(1)) <= 65535:
        raise ValueError('Invalid host.')
    return value


def _path(value):
    _match(_PATH, value, 'path')
    if len(value) > MAX_PATH or any(part in ('.', '..') for part in value.split('/')):
        raise ValueError('Invalid path.')
    return value


def _query(value):
    _match(_QUERY, value, 'query')
    names = [pair.partition('=')[0] for pair in value.split('&')] if value else []
    if len(value) > MAX_QUERY or len(names) != len(set(names)):
        raise ValueError('Invalid query.')
    return value


def _content_type(value):
    if value == '-':
        return value
    return _match(_MEDIA_TYPE, value, 'content type')
