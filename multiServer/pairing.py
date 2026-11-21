"""Pairing: how a controller and a managed server that share no secret come to trust each other.

1. On the managed server a full administrator names the controller's address
   and is given a pairing code (issue_code). The code holds where this server
   is, the fingerprints of its identity key and of its certificate, a random
   seed, which is a one-time Ed25519 private key, and a commitment (below).
   The server keeps the public half of the seed only, with the controller's
   address and the time the code ends.
2. On the controller an administrator pastes the code and is shown what it
   says (read_code). start() first makes sure that it will be able to keep the
   link (links.prepare), because the next step uses the code up. It then
   connects to that address, pinned to that certificate, and sends a request
   signed with the one-time key: a new link id and the controller's new public
   key for the link.
3. The managed server (node_receive) checks the request, uses the code up and
   records the link as pending, in one step, and answers with its identity
   key, its value for this pairing and the address it will take the
   controller's requests from, all three under its signature over the request.
4. The controller checks that key against the fingerprint in the code, and the
   value against the commitment in the code, and keeps the link. It now shows
   eight digits (confirmation_number), which both servers can work out from
   what they keep of the pairing. The managed server never shows them: its
   administrator reads them on the controller and types them into approve(),
   which makes the link active only for the right number. Until then the link
   can do nothing, and MAX_WRONG_NUMBERS wrong numbers close it. So nobody
   approves a link without having seen the controller it belongs to.
5. The controller learns of the approval by asking: links.confirm() sends the
   first signed request on the link, and the answer the managed server now
   gives makes the controller's record active too. There is no other message.

The number is taken from the link id, the one-time public key, the controller's
key, the identity key and the managed server's value for the pairing
(crypto.pair_value). Nobody can look for a second pairing that shows the same
number, because each side has to fix its part before it learns the other's:

  * whoever asks for a link chooses the link id and the controller's key, and
    learns the value only from the answer to the one request that uses the
    code up;
  * whoever answers is held to the value by the commitment in the code
    (crypto.pair_commitment), which was made before the request existed. The
    commitment also covers the address and port the code names, the
    certificate, and the controller address the code was made for, so the
    value opens it only for a controller that used exactly those.

The managed server does not store its value. It works it out again, from its
identity key and the link's one-time public key, when the number is typed. The
controller keeps the one-time public key and the value inside the sealed
record of the link (links.py) for as long as it has to show the number.

The code is 'CPMS1-PAIR-' followed by base32 (A-Z and 2-7, no padding) in
groups of eight joined by dashes, so it is letters, digits and dashes only:

    1 byte    version (1)
    2 bytes   panel port
    32 bytes  fingerprint of the identity key (the node id)
    32 bytes  fingerprint of the certificate the panel serves
    32 bytes  the seed
    32 bytes  the commitment
    1 byte    kind of host: 4, 6, or 0 for a name
    4, 16 or more bytes  the host
    4 bytes   check: the start of SHA-256 over 'CPMS1-PAIR-CODE', a line feed and all of the above

The request is POST /multiserver/pair with Content-Type text/plain. Its body is
five lines: link id, one-time public key, controller public key, time, nonce.
X-CPMS-Signature is the signature by the one-time key over
crypto.pair_request_message, which the managed server rebuilds from those five
lines, the Host header, its own node id and its own certificate.

The answer is 200 text/plain. Its body is three lines: the identity public key,
the value, and the controller address the link allows. X-CPMS-Signature is the
signature by the identity key over crypto.pair_response_message. Every refusal is 403 with no body and no
signature, whatever the reason; the reason is in the audit trail.

Nothing here writes a code, a seed, a private key or a signature to a log, an
audit row or an error.

A link row is only ever changed by one conditional UPDATE that names the
columns it sets. Nothing here loads a row and saves it back: that would write
the row's whole earlier state over what the gateway has recorded since, the
newest accepted time of the link included.
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

from multiServer import addresses, audit, crypto, keys, links, switch, transport

PATH = '/multiserver/pair'
CODE_LIFETIME = 10 * 60  # seconds a pairing code can be used
MAX_FAILURES = 5  # refused attempts after which a code is burned
TIME_WINDOW = 90  # seconds the controller's clock may differ from this server's
PENDING_LIFETIME = 10 * 60  # seconds a link waits for approval
MAX_WRONG_NUMBERS = 5  # wrong numbers typed after which a waiting link is closed
LINK_LIFETIME = 90 * 24 * 60 * 60  # seconds an approved link lasts
MAX_BODY = 256
MAX_CODE = 1024
MAX_CERTIFICATE = 64 * 1024

PREFIX = 'CPMS1-PAIR-'
VERSION = 1
_CHECKED = b'CPMS1-PAIR-CODE\n'
_FIXED = 132  # bytes of a code before its host

_CODE = re.compile(r'CPMS1-PAIR(?:-[A-Z2-7]{1,8})+')
_BODY = re.compile(rb'([0-9a-f]{32})\n([0-9a-f]{64})\n([0-9a-f]{64})\n(0|[1-9][0-9]{0,10})\n([0-9a-f]{32})')
_REPLY = re.compile(rb'([0-9a-f]{64})\n([0-9a-f]{64})\n([0-9a-f:.]{2,45})')
_LINK = re.compile(r'[0-9a-f]{32}')
_NUMBER = re.compile(r'[0-9]{8}')
_ACTOR = re.compile(r'[A-Za-z0-9_.@-]{1,50}')
_PEM = re.compile(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', re.S)
_SIGNATURE_HEADER = 'HTTP_' + transport.HEADERS['signature'].upper().replace('-', '_')

_FAULTS = ('internal', 'unreachable', 'timeout')  # recorded as errors, everything else as refusals
_DECISIONS = {
    'link': 'There is no such link.',
    'not_allowed': 'This link is not waiting for a decision.',
    'expired': 'This link was not approved in time. Pair the two servers again.',
    'generation': 'A link was revoked on this server after this one was made. Pair the two servers again.',
    'burned': 'A wrong number was typed %d times. This link is closed; pair the two servers again.'
              % MAX_WRONG_NUMBERS,
}

NOT_AN_ADDRESS = "The controller's address must be one IPv4 or IPv6 address."

Target = collections.namedtuple('Target', 'host port node_id tls_pin')
Paired = collections.namedtuple('Paired', 'link_id node_id host port confirmation')
Pending = collections.namedtuple('Pending', 'link_id controller_ip admin_id created_at expires_at')


class PairingError(Exception):
    """A refusal. `reason` is its audit reason; the text may be shown and holds nothing secret."""
    recorded = False  # True when the audit trail already has this refusal

    def __init__(self, reason, message, link_id=None):
        Exception.__init__(self, message)
        self.reason = reason
        self.link_id = link_id


def confirmation_number(transcript):
    """The eight digits a controller shows and a managed server asks for, from crypto.pair_confirmation_message."""
    if not isinstance(transcript, bytes) or not transcript.startswith(crypto.PAIR_CONFIRMATION.encode() + b'\n'):
        raise ValueError('The number is taken from what both servers keep of a pairing.')
    return '%08d' % (int.from_bytes(hashlib.sha256(transcript).digest()[:8], 'big') % 10 ** 8)


# The controller.

def read_code(text):
    """What a pairing code says, to be shown before anything is connected. The seed is not part of it."""
    endpoint, node_id, _, _ = _decode(text)
    return Target(endpoint.host, endpoint.port, node_id, endpoint.tls_pin)


def start(code_text, label, actor):
    """Pair this controller with the managed server a code names; PairingError when that is refused.

    Whatever would stop the link from being kept here (the label, the address,
    the master key, a server that is connected already) is refused before
    anything is sent, while the code is still unused. Once the server's answer
    has been verified, the link is kept as a PENDING record (links.store).
    Returns Paired, whose confirmation is the number to show: the link works
    when the other server's administrator has typed it there and
    links.confirm() has then asked that server.
    """
    refusal = None
    try:
        paired = _start(code_text, label, actor)
    except PairingError as error:
        refusal = error
    except Exception:
        refusal = PairingError('internal', 'Pairing failed on this server.')
    if refusal is not None:
        if not refusal.recorded:
            _record('pairing', refusal.reason, link_id=refusal.link_id, actor=actor)
        # Raised here, outside the handler, so that nothing of a failed store() travels with it.
        raise refusal
    return paired


def _start(code_text, label, actor):
    if switch.active_role() != keys.CONTROLLER:
        raise PairingError('role', 'This server is not a Multi-Server Manager controller.')
    from multiServer import entitlement
    if entitlement.allowed() is not True:
        raise PairingError('licence', 'This server has no Multi-Server Manager licence.')
    try:
        links.check_label(label)
    except links.InvalidLabel as error:
        raise PairingError('format', str(error)) from None
    if not isinstance(actor, str) or _ACTOR.fullmatch(actor) is None:
        raise PairingError('format', 'The administrator cannot be named on a link.')
    endpoint, node_id, seed, commitment = _decode(code_text)
    try:
        with links.pairing_slot():
            return _pair_one(endpoint, node_id, seed, commitment, label, actor)
    except links.Busy:
        raise PairingError('internal', 'Another pairing is in progress. Try again.') from None
    except links.NoMasterKey as error:
        raise _unkept(error) from None


def _pair_one(endpoint, node_id, seed, commitment, label, actor):
    private_key = crypto.generate_private_key()
    link_id, nonce, timestamp = os.urandom(16).hex(), os.urandom(16).hex(), _now()
    refusal = None
    try:
        # Everything about keeping the link that can be known now. What follows uses the code up.
        links.prepare(label, link_id, node_id, endpoint.host, endpoint.port, private_key, endpoint.tls_pin)
    except Exception as error:
        refusal = _unkept(error)
    if refusal is not None:
        raise refusal
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
    answer = _REPLY.fullmatch(reply) if status == 200 and content_type == 'text/plain' else None
    if answer is None:
        raise PairingError('format', 'The server did not answer as a managed server does.')
    node_key, value, allowed = (field.decode('ascii') for field in answer.groups())
    if addresses.entry(allowed) != allowed:
        raise PairingError('format', 'The server did not answer as a managed server does.')
    node_key = bytes.fromhex(node_key)
    if not hmac.compare_digest(crypto.node_id(node_key), node_id):
        raise PairingError('signature', 'The server that answered is not the one this pairing code names.')
    if not crypto.usable_public_key(node_key):
        # A key anybody can sign for: its signature would prove nothing, now or on any later reply.
        raise PairingError('format', 'The server did not answer as a managed server does.')
    if not crypto.verify(node_key, signature,
                         crypto.pair_response_message(request, node_key.hex(), value, allowed)):
        raise PairingError('signature', 'The answer is not signed by the server this pairing code names.')
    if not hmac.compare_digest(crypto.pair_commitment(value, endpoint.authority, endpoint.tls_pin, allowed),
                               commitment):
        # The server is not held to this value by the code: a number made from it would prove nothing.
        raise PairingError('signature', 'The answer of the server does not match the pairing code. Reject the '
                           'waiting link on that server and pair again with a new code.', link_id)
    stored = False
    try:
        links.store(label, link_id, endpoint.host, endpoint.port, node_key, private_key, endpoint.tls_pin, actor,
                    (pairing_key, value))
        stored = True
    except Exception:
        pass
    if not stored:
        unkept = PairingError('internal', 'The link could not be kept on this server. Reject it on the other '
                              'server and pair again.', link_id)
        unkept.recorded = True  # by links.store
        raise unkept
    number = confirmation_number(crypto.pair_confirmation_message(link_id, pairing_key, controller_key,
                                                                  node_key.hex(), value))
    return Paired(link_id, node_id, endpoint.host, endpoint.port, number)


def shown_number(row):
    """The number to show for a row of ms_nodes that waits for approval, or None. Never raises.

    Worked out again from the sealed record each time it is shown; it is not
    kept anywhere as a number.
    """
    try:
        record = links.unseal(row.link_id, row.sealed, keys.master_key())
        pairing_key, value = record.pairing
        return confirmation_number(crypto.pair_confirmation_message(
            row.link_id, pairing_key, crypto.public_key(record.private_key).hex(), record.node_key.hex(), value))
    except Exception:
        return None


def _unkept(error):
    """The refusal for a link this controller could not keep; said before the code is used. Never raises."""
    # Each of these messages is a fixed text of links.py or transport.py and names no key.
    for kind, reason in ((links.NotController, 'role'), (links.InvalidLabel, 'format'),
                         (links.DuplicateNode, 'link'), (transport.RefusedAddress, 'not_allowed'),
                         (links.NoMasterKey, 'internal'), (links.UnreadableRow, 'internal'),
                         (links.Busy, 'internal')):
        if type(error) is kind:
            return PairingError(reason, str(error))
    return PairingError('internal', 'Pairing failed on this server.')


def _transport_reason(error):
    for kind, reason in ((transport.RefusedAddress, 'not_allowed'), (transport.TimedOut, 'timeout'),
                         (transport.ConnectionFailed, 'unreachable'), (transport.MalformedResponse, 'format')):
        if isinstance(error, kind):
            return reason
    return 'internal'


# The code.

def _check(payload):
    return hashlib.sha256(_CHECKED + payload).digest()[:4]


def _encode(host, port, node_id, tls_pin, seed, commitment):
    """The one pairing code for these values."""
    try:
        address = ipaddress.ip_address(host)
        where = bytes([address.version]) + address.packed
    except ValueError:
        where = b'\x00' + host.encode('ascii')
    payload = (bytes([VERSION]) + port.to_bytes(2, 'big') + bytes.fromhex(node_id) + bytes.fromhex(tls_pin)
               + seed + bytes.fromhex(commitment) + where)
    text = base64.b32encode(payload + _check(payload)).decode('ascii').rstrip('=')
    return PREFIX + '-'.join(text[start:start + 8] for start in range(0, len(text), 8))


def _decode(text):
    """(endpoint, node id, seed, commitment) of a pairing code; PairingError for anything but one whole code."""
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
        commitment, kind, where = payload[99:131].hex(), payload[131], payload[_FIXED:]
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
        if not hmac.compare_digest(_encode(host, port, node_id, tls_pin, seed, commitment), text):
            raise ValueError
        return transport.Endpoint(host, port, tls_pin), node_id, seed, commitment
    except transport.RefusedAddress as error:
        raise PairingError('not_allowed', str(error)) from None
    except (ValueError, transport.InvalidLink):
        raise refusal from None


# The managed server.

def issue_code(admin_id, controller_ip, host=None, port=None):
    """A new pairing code for the controller at controller_ip; PairingError when it cannot be given.

    The caller has already demanded the administrator's password and a fresh
    code of the second factor; here the account only has to have a second
    factor. host and port are where the controller reaches this panel; left
    out, they are the address the panel reports as its own and the port it
    listens on. The code is returned once and is not kept here.
    """
    administrator = _administrator('pairing_code', admin_id)
    actor = administrator.userName
    source = addresses.entry(controller_ip)
    if source is None:
        _refuse('pairing_code', 'format', NOT_AN_ADDRESS, actor=actor)
    try:
        identity = keys.identity_key()
        node_id = crypto.node_id(crypto.public_key(identity))
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
    pairing_key = crypto.public_key(seed).hex()
    commitment = crypto.pair_commitment(crypto.pair_value(identity, pairing_key), endpoint.authority,
                                        endpoint.tls_pin, source)
    with transaction.atomic():
        PairingCode.objects.create(public_key=pairing_key, controller_ip=source,
                                   admin_id=admin_id, created_at=now, expires_at=now + CODE_LIFETIME)
        if audit.record('pairing_code', actor=actor, source_ip=source) is not True:
            raise PairingError('internal', 'The pairing code could not be recorded.')
    return _encode(endpoint.host, endpoint.port, node_id, endpoint.tls_pin, seed, commitment)


def node_receive(request):
    """Answer one POST /multiserver/pair on a managed server.

    The gateway (nodeGateway.py) hands the request over as it arrived, before
    any session exists, and sends the answer as it is. Nothing here reads a
    cookie, a session or a forwarding header. Whatever is wrong, the caller gets
    the same unsigned answer; only the audit trail has the reason.
    """
    # The address in its one spelling (addresses.py), as it is compared and as it is written down.
    source = addresses.peer(request.META.get('REMOTE_ADDR'))
    try:
        answer, signature = _accept(request, source)
    except Exception as error:
        refusal = error if isinstance(error, PairingError) else PairingError('internal', '')
        fields = dict(source_ip=source) if source is not None else {}
        if refusal.link_id is not None:
            fields['link_id'] = refusal.link_id
        audit.record_unverified('pairing', outcome='error' if refusal.reason in _FAULTS else 'refused',
                                reason=refusal.reason, status=403, **fields)
        return refused()
    return _answer(200, answer, signature.hex())


def refused():
    """The one answer to a pairing request that is not accepted, whatever the reason."""
    return _answer(403, '', None)


def _answer(status, body, signature):
    from django.http import HttpResponse
    response = HttpResponse(body, status=status, content_type='text/plain')
    if signature is not None:
        response[transport.HEADERS['signature']] = signature
    response['Content-Length'] = str(len(response.content))
    response['Cache-Control'] = 'no-store'
    return response


def _accept(request, source):
    """Check one pairing request, in this order, and make its link; (the body of the answer, signature)."""
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
    # A code is made for one address: the connection came from it, or the request is refused and counted.
    if source is None or addresses.listed(code.controller_ip) != (source,):
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
    value = crypto.pair_value(identity, pairing_key)
    reply = crypto.sign(identity, crypto.pair_response_message(message, node_key.hex(), value, source))
    try:
        # The code is used up and the link is made together or not at all. The update finds the
        # code only while it is unused and not burned, so of any number of requests one gets past
        # it; the unique index on the link's pairing key would stop a second link even then.
        with transaction.atomic():
            consumed = codes.filter(consumed=False, failures__lt=MAX_FAILURES).update(consumed=True)
            if consumed == 1:
                # The row as the gateway reads it (nodeGateway.py): the id and the key in lower-case
                # hexadecimal, the address in the form of addresses.py, this server's current
                # generation, and no request accepted yet.
                Link.objects.create(link_id=link_id, controller_key=controller_key, pairing_key=pairing_key,
                                    allowed_ips=addresses.joined((source,)), admin_id=code.admin_id, status=PENDING,
                                    generation=generation, created_at=now, updated_at=now,
                                    expires_at=now + PENDING_LIFETIME, last_request_at=0)
                if audit.record('pairing', link_id=link_id, source_ip=source, status=200) is not True:
                    raise _no('internal', link_id)
    except IntegrityError:
        raise _no('replay', link_id) from None
    if consumed != 1:
        raise _no(_unusable(codes.first(), now) or 'internal', link_id)
    return '\n'.join((node_key.hex(), value, source)), reply


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
    if not crypto.usable_public_key(bytes.fromhex(controller_key)):
        # Under such a key anybody could sign the link's requests; no link is ever made for one.
        raise _no('format')
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


def pending(close=True):
    """The links waiting for a decision on this managed server. Their numbers are not part of it.

    The requests that nobody approved in time are closed on the way, unless
    `close` is False: then nothing is written and they are only left out, as
    for a page that is merely looked at.
    """
    if switch.active_role() != keys.NODE:
        raise PairingError('role', 'This server is not a managed server.')
    from multiServer.models import PENDING, REVOKED, Link
    now = _now()
    waiting = Link.objects.filter(status=PENDING)
    for link_id in list(waiting.filter(expires_at__lte=now).values_list('link_id', flat=True)) if close else ():
        # Nobody approved it in time. One statement, so a link approved at this very moment is left alone.
        if waiting.filter(link_id=link_id, expires_at__lte=now).update(status=REVOKED, updated_at=now) == 1:
            audit.record('link_expire', link_id=link_id)
    return [Pending(link.link_id, link.allowed_ips, link.admin_id, link.created_at, link.expires_at)
            for link in waiting.filter(generation=keys.generation(), expires_at__gt=now)
            .order_by('created_at', 'link_id')]


def approve(link_id, admin_id, number):
    """Make a pending link active: from now on its controller manages this server.

    `number` is the eight digits the controller shows for this link, typed by
    the administrator of this server. A wrong number is counted on the link,
    and the one that makes MAX_WRONG_NUMBERS closes the link for good.
    """
    _decide('link_approve', link_id, admin_id, number)


def reject(link_id, admin_id):
    """Close a pending link; its controller never gets in."""
    _decide('link_revoke', link_id, admin_id)


def _decide(event, link_id, admin_id, number=None):
    from django.db import transaction
    from multiServer.models import ACTIVE, PENDING, REVOKED, Link
    actor = _administrator(event, admin_id).userName
    if not isinstance(link_id, str) or _LINK.fullmatch(link_id) is None:
        _refuse(event, 'format', 'This is not a link.', actor=actor)
    approving = event == 'link_approve'
    if approving and (not isinstance(number, str) or _NUMBER.fullmatch(number) is None):
        # Not counted against the link: nothing of this form is ever the number.
        _refuse(event, 'format', 'The number is the eight digits the controller shows for this link.',
                link_id=link_id, actor=actor)
    now = _now()
    waiting = Link.objects.filter(link_id=link_id, status=PENDING)
    # What a link must be to be approved; asked again by the statement that approves it.
    approvable = waiting.filter(expires_at__gt=now, generation=keys.generation(), failures__lt=MAX_WRONG_NUMBERS)
    if approving:
        link = approvable.first()
        if link is None:
            _undecided(event, link_id, actor, now)
        identity = keys.identity_key()
        if identity is None:
            _refuse(event, 'internal', 'The identity key of this server could not be read.', link_id=link_id,
                    actor=actor)
        if not _is_its_number(link, identity, number):
            _wrong_number(waiting, link_id, actor, now)
        approvable = approvable.filter(pairing_key=link.pairing_key, controller_key=link.controller_key)
    with transaction.atomic():
        # One statement each: of two decisions made at the same moment only one finds the link pending.
        if approving:
            decided = approvable.update(status=ACTIVE, activated_at=now, updated_at=now,
                                        expires_at=now + LINK_LIFETIME)
        else:
            decided = waiting.update(status=REVOKED, updated_at=now)
        if decided == 1 and audit.record(event, link_id=link_id, actor=actor) is not True:
            raise PairingError('internal', 'The decision could not be recorded.')
    if decided != 1:
        _undecided(event, link_id, actor, now)


def _undecided(event, link_id, actor, now):
    """Refuse a decision that found no link to decide, for the reason the link now shows; always raises."""
    from multiServer.models import PENDING, Link
    link = Link.objects.filter(link_id=link_id).first()
    if link is None:
        reason = 'link'
    elif link.status != PENDING:
        reason = 'not_allowed'
    elif link.expires_at <= now:
        reason = 'expired'
    else:
        reason = 'burned' if link.failures >= MAX_WRONG_NUMBERS else 'generation'
    _refuse(event, reason, _DECISIONS[reason], link_id=link_id, actor=actor)


def _is_its_number(link, identity, number):
    """Whether `number` is the one the controller of this pending link shows; the time taken says nothing."""
    expected = confirmation_number(crypto.pair_confirmation_message(
        link.link_id, link.pairing_key, link.controller_key, crypto.public_key(identity).hex(),
        crypto.pair_value(identity, link.pairing_key)))
    return hmac.compare_digest(expected.encode('ascii'), number.encode('ascii'))


def _wrong_number(waiting, link_id, actor, now):
    """Count one wrong number on a waiting link and close the link at the last one allowed; always raises.

    The count is one statement, so numbers typed at the same moment are each
    counted, and it does not wait for the audit trail: a server that cannot
    write its audit row still gives nobody a sixth try.
    """
    from django.db import transaction
    from django.db.models import F
    from multiServer.models import REVOKED
    with transaction.atomic():
        counted = waiting.filter(failures__lt=MAX_WRONG_NUMBERS).update(failures=F('failures') + 1) == 1
        closed = waiting.filter(failures__gte=MAX_WRONG_NUMBERS).update(status=REVOKED, updated_at=now) == 1
    if closed:
        audit.record('link_revoke', link_id=link_id, actor=actor, reason='burned')
        _refuse('link_approve', 'burned', _DECISIONS['burned'], link_id=link_id, actor=actor)
    if not counted:
        # Decided by somebody else in the meantime. A wrong number never goes on to the approval below.
        _undecided('link_approve', link_id, actor, now)
    _refuse('link_approve', 'number', 'This is not the number the controller shows for this link.',
            link_id=link_id, actor=actor)


def _administrator(event, admin_id):
    """The acting administrator of a managed server; anyone else, or any other server, is refused.

    A full administrator who signs in without a second factor is refused too:
    whoever takes over such an account could otherwise hand this server to a
    controller of their own.
    """
    if switch.active_role() != keys.NODE:
        _refuse(event, 'role', 'This server is not a managed server.')
    from multiServer import views
    # The panel's one rule for who is a full administrator, asked about an id instead of a session.
    administrator = views.full_administrator(types.SimpleNamespace(session={'userID': admin_id}))
    if administrator is None:
        _refuse(event, 'admin', 'Only a full administrator of this server may do this.')
    if not views.two_factor_enrolled(administrator):
        _refuse(event, 'two_factor', 'Turn on two-factor authentication for your account first.',
                actor=administrator.userName)
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
