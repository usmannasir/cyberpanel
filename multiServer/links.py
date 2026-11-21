"""How a controller keeps each managed server, and the first thing it asks one.

A row of ms_nodes has a label and a status for listing and one sealed text.
Everything needed to reach the server is inside that text and nowhere else: its
address, its identity key, the certificate it serves, and the private key this
controller signs with on that one link. The text is encrypted and authenticated
with the controller's master key (Fernet), and the row's own link id is part of
what is authenticated. A text that was altered, sealed with another key, or
copied into another row therefore opens for nobody, and whoever can only write
to the database cannot point a link at another server.

What comes out of a sealed text is never used as it is. It is checked again by
the transport's own rules (transport.Link), the same ones a new link has to
pass, so a record is valid here exactly when the transport would connect with
it. A record has no field for the transport's loopback allowance: no stored
link can lead to this machine.

A node is trusted for nothing it says. hello() accepts one small reply of one
exact shape and keeps only values that passed a pattern; when anything else
comes back, or nothing, the row gets one of the fixed texts below and never a
word that the node, or an exception, supplied.

No error raised here, and no repr, holds a key, a certificate pin, a sealed
text or the master key. This module writes no log.
"""
import base64
import collections
import contextlib
import json
import re
import time

from multiServer import audit, crypto, entitlement, keys, switch, transport

# The first line of what is sealed; the lines after it are, in this order, the
# link id of the row, the node id, host, port, node key, private key and
# certificate pin, keys in hexadecimal. No field can hold a line break.
RECORD = 'CPMS1-NODE'
# The longest sealed text there can be: 563 characters of record for a host of
# 253, padded to 576, in a Fernet token of 57 + 576 bytes, in base64. The
# column ms_nodes.sealed takes 2048.
MAX_SEALED = 844
LOCK_SECONDS = 10  # how long store() waits for another worker that is storing

HELLO_PATH = '/multiserver/gateway/hello'
MAX_HELLO = 1024  # bytes of a node's whole answer to hello
MAX_BUILD = 9999
MAX_CAPABILITIES = 16

# Every text that can be put in ms_nodes.last_error or handed to a page as the
# reason a server was not asked. None of them has a part that varies.
NOT_CONTROLLER = 'This server is not a Multi-Server Manager controller.'
NO_LICENCE = 'This controller has no Multi-Server Manager licence.'
NO_SUCH_SERVER = 'There is no such server.'
NOT_ACTIVE = 'This server is not active.'
UNREADABLE = 'The stored connection details of this server cannot be read.'
REFUSED = 'The server refused the request.'
TOO_LARGE = 'The server sent a reply that is too large.'
NOT_A_NODE = 'The server did not answer as a managed server does.'
FAILED = 'The request failed.'
# What the transport refused, first match first, so a kind comes before the
# kind it is a special case of: (error, audit reason, text).
_FAILURES = (
    (transport.TimedOut, 'timeout', 'The server did not answer in time.'),
    (transport.ConnectionFailed, 'unreachable', 'The server could not be reached.'),
    (transport.CertificateMismatch, 'certificate',
     'The server presented a different certificate from the one it was connected with.'),
    (transport.RefusedAddress, 'not_allowed',
     'The name of the server now leads to an address that a link may not connect to.'),
    (transport.RedirectRefused, 'format', 'The server answered with a redirect instead of a signed reply.'),
    (transport.ResponseTooLarge, 'size', TOO_LARGE),
    (transport.MalformedResponse, 'format', 'The server sent a reply that is not valid.'),
    (transport.BadSignature, 'signature',
     'The reply was not signed by the server. It may no longer accept this controller.'),
    (transport.InvalidRequest, 'format', 'The request could not be signed.'),
    (transport.InvalidLink, 'internal', UNREADABLE),
)
STORED_ERRORS = tuple(sorted(set((UNREADABLE, REFUSED, TOO_LARGE, NOT_A_NODE, FAILED)
                                 + tuple(text for _, _, text in _FAILURES))))

_LINK_ID = re.compile(r'[0-9a-f]{32}')
_MASTER_KEY = re.compile(rb'[A-Za-z0-9_-]{43}=')  # the form keys.master_key() returns
_SEALED = re.compile(r'[A-Za-z0-9_-]+={0,2}')
_PLAIN = re.compile(re.escape(RECORD) + r'\n([0-9a-f]{32})\n([0-9a-f]{64})\n([0-9a-z.:-]{1,253})\n([1-9][0-9]{0,4})'
                    r'\n([0-9a-f]{64})\n([0-9a-f]{64})\n([0-9a-f]{64})')
# A label is shown in the controller's pages: nothing in it can be markup.
_LABEL = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9 ._-]{0,62}[A-Za-z0-9])?')
_VERSION = re.compile(r'(?:0|[1-9][0-9]{0,2})\.(?:0|[1-9][0-9]{0,2})')
_CAPABILITY = re.compile(r'[a-z][a-z0-9_]{0,23}')

# What hello() returns: `error` is '' or one of the fixed texts above; the
# version and the capabilities are set only when `ok` is True.
Hello = collections.namedtuple('Hello', 'ok error panel_version capabilities')


class LinkError(Exception):
    """Any refusal by this module. No message holds a key, the pin, a sealed text or the master key."""


class NotController(LinkError):
    """This server is not switched on as a controller."""


class NoMasterKey(LinkError):
    """The controller's master key is missing or is not a Fernet key."""


class NotSealed(LinkError):
    """The text is not a record sealed with this master key: cut short, altered, or sealed elsewhere."""


class MovedRecord(LinkError):
    """The record was sealed for another row."""


class InvalidRecord(LinkError):
    """A field of the record is not what the transport accepts for a link."""


class InvalidLabel(LinkError):
    """The label is not short plain text."""


class DuplicateNode(LinkError):
    """This node, or this link id, already has a row."""


class UnreadableRow(LinkError):
    """A row stored earlier cannot be read, so it cannot be told whether it is the same node."""


class Busy(LinkError):
    """Another worker was storing a server for longer than LOCK_SECONDS."""


class Record(object):
    """What a controller keeps about one managed server.

    Checked when built, by the transport's own rules, and never changed. Only
    transport.RefusedAddress is passed on as it is, because it names the kind
    of address; every other failure is an InvalidRecord.
    """
    __slots__ = ('node_id', 'host', 'port', 'node_key', 'private_key', 'tls_pin')

    def __init__(self, node_id, host, port, node_key, private_key, tls_pin):
        # Any link id: the row is named only when the record is sealed.
        _described('0' * 32, node_id, host, port, node_key, private_key, tls_pin)
        for name, value in zip(Record.__slots__, (node_id, host, port, node_key, private_key, tls_pin)):
            object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        raise AttributeError('A link record cannot be changed.')

    def __delattr__(self, name):
        raise AttributeError('A link record cannot be changed.')

    def __repr__(self):
        # Never the keys or the pin: this text can end up in a log.
        return 'Record(%s port %d)' % (self.host, self.port)

    def __reduce__(self):
        # The private key is stored sealed and in no other form.
        raise TypeError('A link record is not serialised.')


def seal(link_id, record, master_key):
    """The text for ms_nodes.sealed: the record, readable only with the master key and only in row link_id."""
    if type(record) is not Record:
        raise InvalidRecord('Only a link record is sealed.')
    _link(link_id, record)  # the link id is checked here, and with it the record once more
    plain = '\n'.join((RECORD, link_id, record.node_id, record.host, str(record.port), record.node_key.hex(),
                       record.private_key.hex(), record.tls_pin))
    return _fernet(master_key).encrypt(plain.encode('ascii')).decode('ascii')


def unseal(link_id, text, master_key):
    """The record sealed into `text` for row link_id.

    NoMasterKey, NotSealed, MovedRecord or InvalidRecord otherwise; nothing of
    a text that fails is returned or repeated.
    """
    fernet = _fernet(master_key)
    try:
        if type(text) is not str or len(text) > MAX_SEALED or _SEALED.fullmatch(text) is None:
            raise ValueError
        token = text.encode('ascii')
        # One spelling per token: the library would also take base64 that decodes to the same bytes.
        if base64.urlsafe_b64encode(base64.urlsafe_b64decode(token)) != token:
            raise ValueError
        plain = fernet.decrypt(token)
    except Exception:
        # Whatever the library raises for a token that is not one of its own under this key.
        raise NotSealed('This is not a record sealed with the master key of this controller.') from None
    try:
        fields = _PLAIN.fullmatch(plain.decode('ascii'))
    except ValueError:
        fields = None
    if fields is None:
        raise InvalidRecord('The sealed record does not have the form of a link record.')
    if fields.group(1) != link_id:
        raise MovedRecord('The record was sealed for another row.')
    try:
        return Record(fields.group(2), fields.group(3), int(fields.group(4)), bytes.fromhex(fields.group(5)),
                      bytes.fromhex(fields.group(6)), fields.group(7))
    except transport.RefusedAddress:
        raise InvalidRecord('The sealed record names an address a link may not connect to.') from None


def link_of(row, master_key=None):
    """The transport's description of the link that a row of ms_nodes holds.

    The master key is read from the key directory unless one is given. The row
    is not asked for its status: whoever sends decides whom it may send to.
    """
    if master_key is None:
        master_key = keys.master_key()
    return _link(row.link_id, unseal(row.link_id, row.sealed, master_key))


def check_label(label):
    """The label when it is 1 to 64 plain characters; InvalidLabel otherwise."""
    if type(label) is not str or _LABEL.fullmatch(label) is None:
        raise InvalidLabel('A label is 1 to 64 letters, digits, spaces, dots, dashes and underscores, '
                           'and begins and ends with a letter or a digit.')
    return label


def store(label, link_id, host, port, node_key, private_key, tls_pin, actor=None):
    """Keep a newly paired server as one row of ms_nodes, PENDING until activate().

    Refused with NotController, InvalidLabel, InvalidRecord,
    transport.RefusedAddress (an address a link may not connect to),
    NoMasterKey, DuplicateNode (this node or this link id is stored already),
    UnreadableRow (an earlier row cannot be read: remove it first) or Busy.
    Nothing is stored when it raises.
    """
    try:
        _store(label, link_id, host, port, node_key, private_key, tls_pin)
    except Exception as error:
        _audit('pairing', link_id, actor, *_STORE_REFUSALS.get(type(error), ('error', 'internal')))
        raise
    _audit('pairing', link_id, actor)


def activate(link_id, actor=None):
    """PENDING to ACTIVE, once pairing has seen the node accept the link. True when the row was pending."""
    from multiServer import models
    return _move(link_id, models.PENDING, models.ACTIVE, 'link_approve', actor)


def pause(link_id, actor=None):
    """ACTIVE to PAUSED: nothing is sent to the server until resume(). True when the row was active.

    Like remove(), it asks neither the licence nor the master key.
    """
    from multiServer import models
    return _move(link_id, models.ACTIVE, models.PAUSED, 'link_pause', actor)


def resume(link_id, actor=None):
    """PAUSED to ACTIVE. True when the row was paused."""
    from multiServer import models
    return _move(link_id, models.PAUSED, models.ACTIVE, 'link_resume', actor)


def remove(link_id, actor=None):
    """Forget a server: its row and, with the row, the only copy of the key for its link.

    True when there was such a row. It asks neither the licence nor the master
    key, so a row that cannot be read can still be removed.
    """
    removed = False
    if _is_link_id(link_id):
        from multiServer import models
        removed = models.Node.objects.filter(pk=link_id).delete()[1].get(models.Node._meta.label, 0) == 1
    _audit('node_remove', link_id, actor, *(() if removed else ('refused', 'link')))
    return removed


def hello(link_id, actor):
    """Ask one active server who it is and note the outcome on its row. Never raises.

    Nothing is sent unless this server is a licensed controller and the row is
    ACTIVE; such a refusal changes no row. An answer of exactly the expected
    shape sets panel_version and last_seen_at and clears the error. Anything
    else sets last_error to one of STORED_ERRORS and keeps the rest.
    """
    try:
        return _hello(link_id, actor)
    except Exception:
        pass  # not even its message is kept: it may quote what the node sent
    try:
        return _failed(link_id, actor, 'error', 'internal', FAILED)
    except Exception:
        return Hello(False, FAILED, '', ())


def _described(link_id, node_id, host, port, node_key, private_key, tls_pin):
    """The transport's own description of a link: its checks are the one definition of a valid record."""
    try:
        return transport.Link(link_id, node_id, host, port, node_key, private_key, tls_pin)
    except transport.RefusedAddress:
        raise
    except Exception:
        raise InvalidRecord('A link record holds exactly what pairing produces.') from None


def _link(link_id, record):
    return _described(link_id, record.node_id, record.host, record.port, record.node_key, record.private_key,
                      record.tls_pin)


def _fernet(master_key):
    # Imported on use, as in crypto.py: without a usable library the feature is off, the panel is not.
    try:
        from cryptography.fernet import Fernet
        # The library would also take a key with other characters around or after it.
        if type(master_key) is not bytes or _MASTER_KEY.fullmatch(master_key) is None:
            raise ValueError
        return Fernet(master_key)
    except Exception:
        raise NoMasterKey('The master key of this controller is missing or cannot be used.') from None


def _is_link_id(value):
    return type(value) is str and _LINK_ID.fullmatch(value) is not None


def _audit(event, link_id, actor, outcome='ok', reason=None, **fields):
    # audit.record never raises; whether the row was written does not decide the operation.
    if actor is not None:
        fields['actor'] = actor
    if reason is not None:
        fields['reason'] = reason
    audit.record(event, outcome=outcome, link_id=link_id, **fields)


@contextlib.contextmanager
def _one_at_a_time():
    """One worker at a time looks for a node among the rows and then adds it.

    A named lock of the database server, because the node's identity is inside
    the sealed texts and no unique index can refuse a second row for it.
    """
    from django.db import connection
    name = "CONCAT(DATABASE(), '.ms_nodes')"
    with connection.cursor() as cursor:
        cursor.execute('SELECT GET_LOCK(%s, %%s)' % name, [LOCK_SECONDS])
        held = cursor.fetchone()[0]
    if held != 1:
        raise Busy('Another server is being stored at this moment.')
    try:
        yield
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT RELEASE_LOCK(%s)' % name)
        except Exception:
            pass  # a connection that broke has let go of the lock already


def _store(label, link_id, host, port, node_key, private_key, tls_pin):
    if switch.active_role() != keys.CONTROLLER:
        raise NotController(NOT_CONTROLLER)
    check_label(label)
    try:
        node_id = crypto.node_id(node_key)
    except ValueError:
        raise InvalidRecord('A link record holds exactly what pairing produces.') from None
    master_key = keys.master_key()
    sealed = seal(link_id, Record(node_id, host, port, node_key, private_key, tls_pin), master_key)
    from django.db import transaction
    from multiServer import models
    with _one_at_a_time(), transaction.atomic():
        # A locking read: it sees every committed row and waits for a row that a worker who had its turn has
        # not committed yet (a caller that stores inside a transaction of its own).
        for other_id, other_sealed in models.Node.objects.select_for_update().order_by('link_id').values_list(
                'link_id', 'sealed'):
            try:
                other = unseal(other_id, other_sealed, master_key)
            except LinkError:
                raise UnreadableRow('A server stored earlier has connection details that cannot be read. '
                                    'Remove that server before connecting another.') from None
            if other_id == link_id or other.node_id == node_id:
                raise DuplicateNode('This server is already connected.')
        now = int(time.time())
        models.Node.objects.create(link_id=link_id, label=label, status=models.PENDING, sealed=sealed,
                                   created_at=now, updated_at=now)


_STORE_REFUSALS = {
    NotController: ('refused', 'role'),
    InvalidLabel: ('refused', 'format'),
    InvalidRecord: ('refused', 'format'),
    transport.RefusedAddress: ('refused', 'not_allowed'),
    DuplicateNode: ('refused', 'link'),
}


def _move(link_id, before, after, event, actor):
    moved = False
    if _is_link_id(link_id):
        from multiServer import models
        # One statement: of two workers, exactly one finds the row in the state it starts from.
        moved = models.Node.objects.filter(pk=link_id, status=before).update(
            status=after, updated_at=int(time.time())) == 1
    _audit(event, link_id, actor, *(() if moved else ('refused', 'link')))
    return moved


def _hello(link_id, actor):
    if switch.active_role() != keys.CONTROLLER:
        return _refused(link_id, actor, 'role', NOT_CONTROLLER)
    if entitlement.allowed() is not True:
        return _refused(link_id, actor, 'licence', NO_LICENCE)
    from multiServer import models
    row = models.Node.objects.filter(pk=link_id).first() if _is_link_id(link_id) else None
    if row is None or row.status != models.ACTIVE:
        return _refused(link_id, actor, 'link', NO_SUCH_SERVER if row is None else NOT_ACTIVE)
    try:
        link = link_of(row)
    except LinkError:
        return _failed(link_id, actor, 'error', 'internal', UNREADABLE)
    try:
        status, content_type, body = transport.send(link, 'GET', HELLO_PATH, '', '-', b'', actor, 'json')
    except transport.TransportError as error:
        reason, text = _failure(error)
        return _failed(link_id, actor, 'error', reason, text)
    seen = dict(status=status, size=len(body))
    if status != 200:
        return _failed(link_id, actor, 'refused', 'not_allowed', REFUSED, **seen)
    if len(body) > MAX_HELLO:
        return _failed(link_id, actor, 'error', 'size', TOO_LARGE, **seen)
    answer = _answer(content_type, body)
    if answer is None:
        return _failed(link_id, actor, 'error', 'format', NOT_A_NODE, **seen)
    _note(link_id, panel_version=answer[0], last_seen_at=int(time.time()), last_error='', last_error_at=None)
    _audit('request', link_id, actor, method='GET', path=HELLO_PATH, **seen)
    return Hello(True, '', answer[0], answer[1])


def _failure(error):
    for kind, reason, text in _FAILURES:
        if isinstance(error, kind):
            return reason, text
    return 'internal', FAILED


def _answer(content_type, body):
    """(panel version, capabilities) when the reply is exactly what a node says to hello; None otherwise.

    The four names and nothing else: "version" as 3.0, "build" as a small whole
    number, "role" as node, "capabilities" as a short list of short lower-case
    names. What is kept is made of digits, dots, lower-case letters and
    underscores only.
    """
    try:
        if content_type != 'application/json':
            return None
        answer = json.loads(body.decode('ascii'), object_pairs_hook=entitlement._object)
        if type(answer) is not dict or sorted(answer) != ['build', 'capabilities', 'role', 'version']:
            return None
        version, build, capabilities = answer['version'], answer['build'], answer['capabilities']
        if type(answer['role']) is not str or answer['role'] != keys.NODE:
            return None
        if type(version) is not str or _VERSION.fullmatch(version) is None:
            return None
        if type(build) is not int or not 0 <= build <= MAX_BUILD:
            return None
        if type(capabilities) is not list or len(capabilities) > MAX_CAPABILITIES:
            return None
        if any(type(name) is not str or _CAPABILITY.fullmatch(name) is None for name in capabilities):
            return None
        if len(set(capabilities)) != len(capabilities):
            return None
        return '%s.%d' % (version, build), tuple(capabilities)
    except Exception:
        return None


def _refused(link_id, actor, reason, text):
    """Nothing was sent and no row is touched: the reason lies with this controller, not with the server."""
    _audit('request', link_id, actor, 'refused', reason, method='GET', path=HELLO_PATH)
    return Hello(False, text, '', ())


def _failed(link_id, actor, outcome, reason, text, **seen):
    _note(link_id, last_error=text, last_error_at=int(time.time()))
    _audit('request', link_id, actor, outcome, reason, method='GET', path=HELLO_PATH, **seen)
    return Hello(False, text, '', ())


def _note(link_id, **changes):
    """Write the outcome on the row, unless the server was paused or removed in the meantime."""
    if not _is_link_id(link_id):
        return
    from django.db import transaction
    from multiServer import models
    # Its own savepoint: a failed write must not spoil the caller's transaction.
    with transaction.atomic():
        models.Node.objects.filter(pk=link_id, status=models.ACTIVE).update(**changes)
