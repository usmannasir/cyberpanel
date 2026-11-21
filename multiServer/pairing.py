"""Pairing: how a controller and a managed server that share no secret come to trust each other.

1. On the managed server a full administrator names the controller's address
   and is given a pairing code (issue_code). The code holds where this server
   is, the fingerprints of its identity key and of its certificate, and a
   random seed, which is a one-time Ed25519 private key. The server keeps the
   public half only, with the controller's address and the time the code ends.
2. On the controller an administrator pastes the code and is shown what it
   says (read_code). start() then connects to that address, pinned to that
   certificate, and sends a request signed with the one-time key: a new link
   id and the controller's new public key for the link.
3. The managed server (node_receive) checks the request, uses the code up and
   records the link as pending, in one step, and answers with its identity key
   and its signature over the request.
4. The controller checks that key against the fingerprint in the code and
   keeps the link. Both servers now show the same eight digits
   (confirmation_number); when the administrator of the managed server has
   compared them, approve() makes the link active. Until then it can do nothing.

The code is 'CPMS1-PAIR-' followed by base32 (A-Z and 2-7, no padding) in
groups of eight joined by dashes, so it is letters, digits and dashes only:

    1 byte    version (1)
    2 bytes   panel port
    32 bytes  fingerprint of the identity key (the node id)
    32 bytes  fingerprint of the certificate the panel serves
    32 bytes  the seed
    1 byte    kind of host: 4, 6, or 0 for a name
    4, 16 or more bytes  the host
    4 bytes   check: the start of SHA-256 over 'CPMS1-PAIR-CODE', a line feed and all of the above

The request is POST /multiserver/pair with Content-Type text/plain. Its body is
five lines: link id, one-time public key, controller public key, time, nonce.
X-CPMS-Signature is the signature by the one-time key over
crypto.pair_request_message, which the managed server rebuilds from those five
lines, the Host header, its own node id and its own certificate.

The answer is 200 text/plain with the identity public key as its body and, in
X-CPMS-Signature, the signature by the identity key over
crypto.pair_response_message. Every refusal is 403 with no body and no
signature, whatever the reason; the reason is in the audit trail.

Nothing here writes a code, a seed, a private key or a signature to a log, an
audit row or an error.
"""
import base64
import collections
import hashlib
import hmac
import ipaddress
import os
import re
import ssl
import time
import types

from multiServer import audit, crypto, keys, switch, transport

PATH = '/multiserver/pair'
CODE_LIFETIME = 10 * 60  # seconds a pairing code can be used
MAX_FAILURES = 5  # refused attempts after which a code is burned
TIME_WINDOW = 90  # seconds the controller's clock may differ from this server's
PENDING_LIFETIME = 10 * 60  # seconds a link waits for approval
LINK_LIFETIME = 90 * 24 * 60 * 60  # seconds an approved link lasts
MAX_BODY = 256
MAX_CODE = 1024
MAX_LABEL = 64
MAX_CERTIFICATE = 64 * 1024

PREFIX = 'CPMS1-PAIR-'
VERSION = 1
_CHECKED = b'CPMS1-PAIR-CODE\n'
_FIXED = 100  # bytes of a code before its host

_CODE = re.compile(r'CPMS1-PAIR(?:-[A-Z2-7]{1,8})+')
_BODY = re.compile(rb'([0-9a-f]{32})\n([0-9a-f]{64})\n([0-9a-f]{64})\n(0|[1-9][0-9]{0,10})\n([0-9a-f]{32})')
_KEY = re.compile(rb'[0-9a-f]{64}')
_LINK = re.compile(r'[0-9a-f]{32}')
_ACTOR = re.compile(r'[A-Za-z0-9_.@-]{1,50}')
_PEM = re.compile(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', re.S)
_SIGNATURE_HEADER = 'HTTP_' + transport.HEADERS['signature'].upper().replace('-', '_')

_FAULTS = ('internal', 'unreachable', 'timeout')  # recorded as errors, everything else as refusals
_DECISIONS = {
    'link': 'There is no such link.',
    'not_allowed': 'This link is not waiting for a decision.',
    'expired': 'This link was not approved in time. Pair the two servers again.',
    'generation': 'A link was revoked on this server after this one was made. Pair the two servers again.',
}

Target = collections.namedtuple('Target', 'host port node_id tls_pin')
Paired = collections.namedtuple('Paired', 'link_id node_id host port confirmation')
Pending = collections.namedtuple('Pending', 'link_id controller_ip admin_id created_at expires_at confirmation')


class PairingError(Exception):
    """A refusal. `reason` is its audit reason; the text may be shown and holds nothing secret."""

    def __init__(self, reason, message, link_id=None):
        Exception.__init__(self, message)
        self.reason = reason
        self.link_id = link_id


def confirmation_number(transcript):
    """The eight digits both administrators compare, from crypto.pair_confirmation_message."""
    if not isinstance(transcript, bytes) or not transcript.startswith(crypto.PAIR_CONFIRMATION.encode() + b'\n'):
        raise ValueError('The number is taken from what both servers keep of a pairing.')
    return '%08d' % (int.from_bytes(hashlib.sha256(transcript).digest()[:8], 'big') % 10 ** 8)


# The controller.

def read_code(text):
    """What a pairing code says, to be shown before anything is connected. The seed is not part of it."""
    endpoint, node_id, _ = _decode(text)
    return Target(endpoint.host, endpoint.port, node_id, endpoint.tls_pin)


def start(code_text, label, actor, store):
    """Pair this controller with the managed server a code names; PairingError when that is refused.

    Once that server's answer has been verified, the new link is handed over as
    store(label, link_id, host, port, node_key, private_key, tls_pin), with both
    keys as 32 bytes. Returns Paired, whose confirmation is the number to show.
    The link works only after the other server's administrator has approved it.
    """
    refusal = None
    try:
        paired = _start(code_text, label, actor, store)
    except PairingError as error:
        refusal = error
    except Exception:
        refusal = PairingError('internal', 'Pairing failed on this server.')
    if refusal is not None:
        _record('pairing', refusal.reason, link_id=refusal.link_id, actor=actor)
        # Raised here, outside the handler, so that nothing of a failed store() travels with it.
        raise refusal
    audit.record('pairing', link_id=paired.link_id, actor=actor)
    return paired


def _start(code_text, label, actor, store):
    if switch.active_role() != keys.CONTROLLER:
        raise PairingError('role', 'This server is not a Multi-Server Manager controller.')
    from multiServer import entitlement
    if entitlement.allowed() is not True:
        raise PairingError('licence', 'This server has no Multi-Server Manager licence.')
    if (not isinstance(label, str) or not 1 <= len(label) <= MAX_LABEL or not label.isprintable()
            or not isinstance(actor, str) or _ACTOR.fullmatch(actor) is None or not callable(store)):
        raise PairingError('format', 'A name for the server is required.')
    endpoint, node_id, seed = _decode(code_text)
    private_key = crypto.generate_private_key()
    link_id, nonce, timestamp = os.urandom(16).hex(), os.urandom(16).hex(), _now()
    pairing_key, controller_key = crypto.public_key(seed).hex(), crypto.public_key(private_key).hex()
    request = crypto.pair_request_message(link_id, pairing_key, controller_key, node_id, endpoint.tls_pin,
                                          endpoint.authority, timestamp, nonce)
    body = '\n'.join((link_id, pairing_key, controller_key, str(timestamp), nonce)).encode('ascii')
    try:
        status, content_type, reply, signature = transport.exchange(endpoint, PATH, body,
                                                                    crypto.sign(seed, request))
    except transport.BadSignature:
        # A managed server answers a request it does not accept without a signature, and never says why.
        raise PairingError('signature', 'The server did not accept the pairing code. A code can be used once, '
                           'for ten minutes, from the controller address it was made for.') from None
    except transport.CertificateMismatch:
        raise PairingError('certificate', 'The server at that address did not present the certificate the '
                           'pairing code names. Nothing was sent to it.') from None
    except transport.TransportError as error:
        raise PairingError(_transport_reason(error), str(error)) from None
    if status != 200 or content_type != 'text/plain' or _KEY.fullmatch(reply) is None:
        raise PairingError('format', 'The server did not answer as a managed server does.')
    node_key = bytes.fromhex(reply.decode('ascii'))
    if not hmac.compare_digest(crypto.node_id(node_key), node_id):
        raise PairingError('signature', 'The server that answered is not the one this pairing code names.')
    if not crypto.verify(node_key, signature, crypto.pair_response_message(request, node_key.hex())):
        raise PairingError('signature', 'The answer is not signed by the server this pairing code names.')
    stored = False
    try:
        store(label, link_id, endpoint.host, endpoint.port, node_key, private_key, endpoint.tls_pin)
        stored = True
    except Exception:
        pass
    if not stored:
        raise PairingError('internal', 'The link could not be kept on this server. Reject it on the other '
                           'server and pair again.', link_id)
    number = confirmation_number(crypto.pair_confirmation_message(link_id, pairing_key, controller_key,
                                                                  node_key.hex()))
    return Paired(link_id, node_id, endpoint.host, endpoint.port, number)


def _transport_reason(error):
    for kind, reason in ((transport.RefusedAddress, 'not_allowed'), (transport.TimedOut, 'timeout'),
                         (transport.ConnectionFailed, 'unreachable'), (transport.MalformedResponse, 'format')):
        if isinstance(error, kind):
            return reason
    return 'internal'


# The code.

def _check(payload):
    return hashlib.sha256(_CHECKED + payload).digest()[:4]


def _encode(host, port, node_id, tls_pin, seed):
    """The one pairing code for these values."""
    try:
        address = ipaddress.ip_address(host)
        where = bytes([address.version]) + address.packed
    except ValueError:
        where = b'\x00' + host.encode('ascii')
    payload = (bytes([VERSION]) + port.to_bytes(2, 'big') + bytes.fromhex(node_id) + bytes.fromhex(tls_pin)
               + seed + where)
    text = base64.b32encode(payload + _check(payload)).decode('ascii').rstrip('=')
    return PREFIX + '-'.join(text[start:start + 8] for start in range(0, len(text), 8))


def _decode(text):
    """(endpoint, node id, seed) of a pairing code; PairingError for anything but one whole code."""
    refusal = PairingError('format', 'This is not a pairing code, or not all of one.')
    if not isinstance(text, str) or len(text) > MAX_CODE or _CODE.fullmatch(text) is None:
        raise refusal
    packed = text[len(PREFIX):].replace('-', '')
    try:
        raw = base64.b32decode(packed + '=' * (-len(packed) % 8))
        payload = raw[:-4]
        if len(payload) <= _FIXED:
            raise ValueError
        port = int.from_bytes(payload[1:3], 'big')
        node_id, tls_pin, seed = payload[3:35].hex(), payload[35:67].hex(), payload[67:99]
        kind, where = payload[99], payload[_FIXED:]
        if kind == 4:
            host = str(ipaddress.IPv4Address(where))
        elif kind == 6:
            host = str(ipaddress.IPv6Address(where))
        elif kind == 0:
            host = where.decode('ascii')
        else:
            raise ValueError
        # One text per code, the one written for these values. It begins with the version and ends in
        # the check, so another version and any changed character are refused here, and so are other
        # groupings, spare bits and second spellings of a host.
        if not hmac.compare_digest(_encode(host, port, node_id, tls_pin, seed), text):
            raise ValueError
        return transport.Endpoint(host, port, tls_pin), node_id, seed
    except transport.RefusedAddress as error:
        raise PairingError('not_allowed', str(error)) from None
    except (ValueError, transport.InvalidLink):
        raise refusal from None


# The managed server.

def issue_code(admin_id, controller_ip, host=None, port=None):
    """A new pairing code for the controller at controller_ip; PairingError when it cannot be given.

    The caller has already demanded the administrator's password and second
    factor. host and port are where the controller reaches this panel; left
    out, they are the address the panel reports as its own and the port it
    listens on. The code is returned once and is not kept here.
    """
    administrator = _administrator('pairing_code', admin_id)
    actor = administrator.userName
    source = _address(controller_ip)
    if source is None:
        _refuse('pairing_code', 'format', "The controller's address must be one IPv4 or IPv6 address.", actor=actor)
    try:
        node_id = crypto.node_id(crypto.public_key(keys.identity_key()))
        fingerprint = _certificate_fingerprint()
        if host is None:
            from multiServer import entitlement
            host = entitlement.server_address()
        if port is None:
            from plogical import softUpgrade
            port = softUpgrade.panel_endpoint(softUpgrade.PANEL_CONF)[1]
    except Exception:
        _refuse('pairing_code', 'internal', 'The identity key, the certificate or the port of this server could '
                'not be read.', actor=actor)
    try:
        endpoint = transport.Endpoint(host, port, fingerprint)
    except transport.RefusedAddress as error:
        _refuse('pairing_code', 'not_allowed', str(error), actor=actor)
    except transport.InvalidLink:
        _refuse('pairing_code', 'format', 'The address or the port of this server is not one a controller can '
                'connect to.', actor=actor)
    from django.db import transaction
    from multiServer.models import PairingCode
    seed, now = crypto.generate_private_key(), _now()
    with transaction.atomic():
        PairingCode.objects.create(public_key=crypto.public_key(seed).hex(), controller_ip=source,
                                   admin_id=admin_id, created_at=now, expires_at=now + CODE_LIFETIME)
        if audit.record('pairing_code', actor=actor, source_ip=source) is not True:
            raise PairingError('internal', 'The pairing code could not be recorded.')
    return _encode(endpoint.host, endpoint.port, node_id, endpoint.tls_pin, seed)


def node_receive(request):
    """Answer one POST /multiserver/pair on a managed server.

    The gateway calls this before any session exists, and nothing here reads a
    cookie, a session or a forwarding header. Whatever is wrong, the caller gets
    the same unsigned answer; only the audit trail has the reason.
    """
    from django.http import HttpResponse
    source = request.META.get('REMOTE_ADDR')
    try:
        node_key, signature = _accept(request, source)
        response = HttpResponse(node_key, content_type='text/plain')
        response[transport.HEADERS['signature']] = signature.hex()
    except Exception as error:
        refusal = error if isinstance(error, PairingError) else PairingError('internal', '')
        _record('pairing', refusal.reason, link_id=refusal.link_id, source_ip=source, status=403)
        response = HttpResponse(status=403, content_type='text/plain')
    response['Content-Length'] = str(len(response.content))
    response['Cache-Control'] = 'no-store'
    return response


def _accept(request, source):
    """Check one pairing request, in this order, and make its link; (identity public key, signature)."""
    if switch.active_role() != keys.NODE:
        raise _no('role')
    (link_id, pairing_key, controller_key, timestamp, nonce), signature, host = _parse(request)
    from django.db import IntegrityError, transaction
    from django.db.models import F
    from multiServer.models import PENDING, Link, PairingCode
    now = _now()
    codes = PairingCode.objects.filter(pk=pairing_key)
    code = codes.first()
    reason = _unusable(code, now)
    if reason is not None:
        raise _no(reason)
    # One statement: attempts made at the same moment are each counted, and the fifth burns the code.
    count_failure = codes.filter(consumed=False, failures__lt=MAX_FAILURES)
    given = _address(source)
    if given is None or given != code.controller_ip:
        count_failure.update(failures=F('failures') + 1)
        raise _no('source_ip')
    identity, generation = keys.identity_key(), keys.generation()
    if identity is None or generation < 1:
        raise _no('internal')
    node_key = crypto.public_key(identity)
    message = crypto.pair_request_message(link_id, pairing_key, controller_key, crypto.node_id(node_key),
                                          _certificate_fingerprint(), host, timestamp, nonce)
    if not crypto.verify(bytes.fromhex(pairing_key), signature, message):
        count_failure.update(failures=F('failures') + 1)
        raise _no('signature')
    if abs(now - timestamp) > TIME_WINDOW:
        raise _no('time', link_id)
    reply = crypto.sign(identity, crypto.pair_response_message(message, node_key.hex()))
    try:
        # The code is used up and the link is made together or not at all. The update finds the
        # code only while it is unused and not burned, so of any number of requests one gets past
        # it; the unique index on the link's pairing key would stop a second link even then.
        with transaction.atomic():
            consumed = codes.filter(consumed=False, failures__lt=MAX_FAILURES).update(consumed=True)
            if consumed == 1:
                Link.objects.create(link_id=link_id, controller_key=controller_key, pairing_key=pairing_key,
                                    allowed_ips=code.controller_ip, admin_id=code.admin_id, status=PENDING,
                                    generation=generation, created_at=now, updated_at=now,
                                    expires_at=now + PENDING_LIFETIME)
                if audit.record('pairing', link_id=link_id, source_ip=source, status=200) is not True:
                    raise _no('internal', link_id)
    except IntegrityError:
        raise _no('replay', link_id) from None
    if consumed != 1:
        raise _no(_unusable(codes.first(), now) or 'internal', link_id)
    return node_key.hex(), reply


def _parse(request):
    """((link id, pairing key, controller key, time, nonce), signature, host) of a well-formed request."""
    meta = request.META
    length = meta.get('CONTENT_LENGTH')
    if (request.method != 'POST' or request.path != PATH or meta.get('QUERY_STRING')
            or not isinstance(length, str) or transport._LENGTH.fullmatch(length) is None):
        raise _no('format')
    if int(length) > MAX_BODY:
        raise _no('size')
    body, signature, host = request.body, meta.get(_SIGNATURE_HEADER), meta.get('HTTP_HOST')
    fields = _BODY.fullmatch(body)
    if (fields is None or len(body) != int(length) or meta.get('CONTENT_TYPE') != 'text/plain'
            or not isinstance(signature, str) or transport._SIGNATURE.fullmatch(signature) is None):
        raise _no('format')
    link_id, pairing_key, controller_key, timestamp, nonce = (field.decode('ascii') for field in fields.groups())
    try:
        # Checks the host too. The node id and the certificate are this server's own, filled in later.
        crypto.pair_request_message(link_id, pairing_key, controller_key, '0' * 64, '0' * 64, host,
                                    int(timestamp), nonce)
    except ValueError:
        raise _no('format') from None
    return (link_id, pairing_key, controller_key, int(timestamp), nonce), bytes.fromhex(signature), host


def _unusable(code, now):
    """Why a pairing code cannot be used, or None while it can."""
    if code is None:
        return 'link'
    if code.expires_at <= now:
        return 'expired'
    if code.consumed:
        return 'consumed'
    if code.failures >= MAX_FAILURES:
        return 'burned'
    return None


def pending():
    """The links waiting for a decision on this managed server, each with its number to compare."""
    if switch.active_role() != keys.NODE:
        raise PairingError('role', 'This server is not a managed server.')
    identity = keys.identity_key()
    if identity is None:
        raise PairingError('internal', 'The identity key of this server could not be read.')
    from multiServer.models import PENDING, REVOKED, Link
    now, node_key = _now(), crypto.public_key(identity).hex()
    waiting = Link.objects.filter(status=PENDING)
    for link_id in list(waiting.filter(expires_at__lte=now).values_list('link_id', flat=True)):
        # Nobody approved it in time. One statement, so a link approved at this very moment is left alone.
        if waiting.filter(link_id=link_id, expires_at__lte=now).update(status=REVOKED, updated_at=now) == 1:
            audit.record('link_expire', link_id=link_id)
    return [Pending(link.link_id, link.allowed_ips, link.admin_id, link.created_at, link.expires_at,
                    confirmation_number(crypto.pair_confirmation_message(
                        link.link_id, link.pairing_key, link.controller_key, node_key)))
            for link in waiting.filter(generation=keys.generation()).order_by('created_at', 'link_id')]


def approve(link_id, admin_id):
    """Make a pending link active: from now on its controller manages this server."""
    _decide('link_approve', link_id, admin_id)


def reject(link_id, admin_id):
    """Close a pending link; its controller never gets in."""
    _decide('link_revoke', link_id, admin_id)


def _decide(event, link_id, admin_id):
    from django.db import transaction
    from multiServer.models import ACTIVE, PENDING, REVOKED, Link
    actor = _administrator(event, admin_id).userName
    if not isinstance(link_id, str) or _LINK.fullmatch(link_id) is None:
        _refuse(event, 'format', 'This is not a link.', actor=actor)
    now = _now()
    waiting = Link.objects.filter(link_id=link_id, status=PENDING)
    with transaction.atomic():
        # One statement each: of two decisions made at the same moment only one finds the link pending.
        if event == 'link_approve':
            decided = waiting.filter(expires_at__gt=now, generation=keys.generation()).update(
                status=ACTIVE, activated_at=now, updated_at=now, expires_at=now + LINK_LIFETIME)
        else:
            decided = waiting.update(status=REVOKED, updated_at=now)
        if decided == 1 and audit.record(event, link_id=link_id, actor=actor) is not True:
            raise PairingError('internal', 'The decision could not be recorded.')
    if decided != 1:
        link = Link.objects.filter(link_id=link_id).first()
        if link is None:
            reason = 'link'
        elif link.status != PENDING:
            reason = 'not_allowed'
        else:
            reason = 'expired' if link.expires_at <= now else 'generation'
        _refuse(event, reason, _DECISIONS[reason], link_id=link_id, actor=actor)


def _administrator(event, admin_id):
    """The acting administrator of a managed server; anyone else, or any other server, is refused."""
    if switch.active_role() != keys.NODE:
        _refuse(event, 'role', 'This server is not a managed server.')
    from multiServer import views
    # The panel's one rule for who is a full administrator, asked about an id instead of a session.
    administrator = views.full_administrator(types.SimpleNamespace(session={'userID': admin_id}))
    if administrator is None:
        _refuse(event, 'admin', 'Only a full administrator of this server may do this.')
    return administrator


def _certificate_fingerprint():
    """The SHA-256 of the certificate this panel serves, which is how a controller pins it."""
    from plogical import softUpgrade
    with open(str(softUpgrade.PANEL_CONF / 'cert.pem'), 'rb') as source:
        pem = source.read(MAX_CERTIFICATE + 1)
    first = _PEM.search(pem)
    if len(pem) > MAX_CERTIFICATE or first is None:
        raise ValueError('The panel certificate cannot be read.')
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(first.group(0).decode('ascii'))).hexdigest()


def _address(text):
    """The one spelling of an IP address; None for anything else, IPv4 written as IPv6 included."""
    try:
        if not isinstance(text, str) or '%' in text:
            return None
        address = ipaddress.ip_address(text)
        if address.version == 4:
            return text if str(address) == text else None
        return None if address.ipv4_mapped is not None else str(address)
    except ValueError:
        return None


def _now():
    return int(time.time())


def _no(reason, link_id=None):
    return PairingError(reason, 'Refused.', link_id)


def _record(event, reason, **fields):
    audit.record(event, outcome='error' if reason in _FAULTS else 'refused', reason=reason,
                 **dict((name, value) for name, value in fields.items() if value is not None))


def _refuse(event, reason, message, **fields):
    _record(event, reason, **fields)
    raise PairingError(reason, message, fields.get('link_id'))
