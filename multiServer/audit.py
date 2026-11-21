"""The Multi-Server Manager audit trail.

One row per event: what happened, how it ended, on which link, for whom, from
where, and for a request its method, path, status and size. A row never holds
what was sent or received, and this module is where that is enforced:

  * the event, the outcome and the reason come from the fixed lists below;
  * only the named fields are accepted, each with one type and one exact form;
  * a query string is cut from a path, and anything else that does not fit is
    left out whole, never shortened, and counted in the row's `dropped`.

So a body, a password, a pairing code, a ticket or a signature has no field to
travel in, and a value shaped like one (a long run of hexadecimal digits, a
numeric code, an oversized word) is refused even in a field that takes text.
Every secret this feature issues is hexadecimal or longer than MAX_SEGMENT.

For a pre-link overflow summary, event=request, outcome=refused, reason=internal
and status is NULL. The size column holds the exact number of excess refusals in
one worker's completed minute. All request metadata is absent.

record() never raises: the action being audited decides what a False means.
"""
import collections
import ipaddress
import re
import threading
import time

EVENTS = (
    'pairing_code',     # a managed server issued a pairing code
    'pairing',          # a controller presented a pairing code
    'link_approve', 'link_pause', 'link_resume', 'link_revoke', 'link_rotate', 'link_expire',
    'allowed_ips',      # the addresses a controller may call from were changed
    'request',          # a signed request was sent (controller) or received (managed server)
    'ticket_issue', 'ticket_use',
    'view_open',        # a framed view of a managed server was opened
    'inventory',
    'node_remove',
    'licence',
    'role',
)
OUTCOMES = ('ok', 'refused', 'error')
REASONS = (
    'role', 'format', 'size', 'link', 'generation', 'expired', 'source_ip', 'time', 'signature',
    'body_hash', 'replay', 'admin', 'not_allowed', 'burned', 'consumed', 'certificate', 'unreachable',
    'timeout', 'licence', 'password', 'two_factor', 'internal',
    'number',           # the number typed to approve a link is not the one its controller shows
)
METHODS = ('GET', 'POST')
MAX_PATH = 255
MAX_SEGMENT = 40
MAX_SIZE = 2 ** 40

_LINK = re.compile(r'[0-9a-f]{32}')
_ACTOR = re.compile(r'[A-Za-z0-9_.@-]{1,50}')
_PATH = re.compile(r'/(?:[A-Za-z0-9._~@+-]+/)*(?:[A-Za-z0-9._~@+-]+)?')
_SECRET = re.compile(r'[0-9A-Fa-f]{16}|[0-9]{6}')


# Both public endpoints share one refusal allowance until a real link is found.
UNVERIFIED_PER_MINUTE = 30
RETENTION_SECONDS = 180 * 86400
PRUNE_INTERVAL = 3600
PRUNE_BATCH = 1000


class _MinuteBudget:
    def __init__(self, limit):
        self.limit = limit
        self.ends_at = 0
        self.count = 0
        self.pending = collections.deque()  # one count per completed window with excess refusals
        self.lock = threading.Lock()
        self.writer = threading.Lock()

    def observe(self, pre_link):
        with self.lock:
            now = time.monotonic()
            if now >= self.ends_at:
                if self.count > self.limit:
                    self.pending.append(self.count - self.limit)
                self.ends_at = now + 60
                self.count = 0
            if pre_link:
                self.count += 1
                return self.count <= self.limit
            return True

    def report(self):
        # Called after commit. A rollback or a failed summary insert leaves the count for
        # the next committed event. Only one writer claims a count; DB I/O never holds lock.
        with self.lock:
            if not self.pending or not self.writer.acquire(False):
                return
            count = self.pending[0]
        try:
            # A request/refused/internal row with NULL status: size is the exact number
            # suppressed in that minute. No part of a caller's request enters this row.
            row = entry('request', dict(outcome='refused', reason='internal', size=count))
            row['at'] = int(time.time())
            _insert(row)
            with self.lock:
                self.pending.popleft()
        except Exception:
            pass
        finally:
            self.writer.release()


_unverified = _MinuteBudget(UNVERIFIED_PER_MINUTE)
_prune_lock = threading.Lock()
_next_prune = 0


def record_unverified(event, **fields):
    return _record((event,), fields, pre_link=True)


def record(*event, **fields):
    """record(event, **fields): write one audit row; True when it was written. Never raises.

    The event is taken by position only, so that no field name a caller passes,
    not even "event", can make the call itself fail.
    """
    return _record(event, fields, pre_link=False)


def _record(event, fields, pre_link):
    try:
        if not _unverified.observe(pre_link):
            return False
        row = entry(event[0], fields) if len(event) == 1 else None
        if row is None:
            return False
        row['at'] = int(time.time())
        _write(row)
        return True
    except Exception:
        return False


def entry(event, fields):
    """The columns for one event, or None when its event or outcome is not a known one."""
    if type(event) is not str or event not in EVENTS:
        return None
    row = {'event': event, 'outcome': 'ok', 'dropped': 0}
    for name, value in fields.items():
        check = _FIELDS.get(name)
        kept = check(value) if check is not None else None
        if kept is not None:
            row[name] = kept
        elif name == 'outcome':
            # Leaving it out would record a refusal or a failure as a success.
            return None
        else:
            row['dropped'] += 1
    return row


def _insert(row):
    from multiServer.models import AuditEntry
    AuditEntry.objects.create(**row)


def _write(row):
    from django.db import transaction
    # Its own savepoint: a failed insert must not spoil the caller's transaction.
    with transaction.atomic():
        _insert(row)
        transaction.on_commit(_unverified.report)
        transaction.on_commit(_prune_if_due)


def _prune_if_due():
    # Keep the retention query outside the audited operation's transaction.
    # Bounded indexed deletes also let an old installation catch up gradually.
    global _next_prune
    try:
        with _prune_lock:
            now = time.monotonic()
            if now < _next_prune:
                return
            _next_prune = now + PRUNE_INTERVAL
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM ms_audit WHERE at < %s ORDER BY at, id LIMIT %s',
                           [int(time.time()) - RETENTION_SECONDS, PRUNE_BATCH])
    except Exception:
        pass  # retention is retried on later activity, the event already committed


def _one_of(allowed):
    return lambda value: value if type(value) is str and value in allowed else None


def _matching(pattern):
    return lambda value: value if type(value) is str and pattern.fullmatch(value) else None


def _number(low, high):
    return lambda value: value if type(value) is int and low <= value <= high else None


def _actor(value):
    if type(value) is not str or not _ACTOR.fullmatch(value) or _SECRET.search(value):
        return None
    return value


def _source_ip(value):
    # A zone ("fe80::1%eth0") is free text and has no place in a source address.
    if type(value) is not str or len(value) > 45 or '%' in value:
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def _path(value):
    if type(value) is not str:
        return None
    value = re.split(r'[?#]', value, maxsplit=1)[0]
    if len(value) > MAX_PATH or not _PATH.fullmatch(value) or _SECRET.search(value):
        return None
    if any(len(segment) > MAX_SEGMENT or segment in ('.', '..') for segment in value.split('/')):
        return None
    return value


_FIELDS = {
    'outcome': _one_of(OUTCOMES),
    'reason': _one_of(REASONS),
    'link_id': _matching(_LINK),
    'actor': _actor,
    'source_ip': _source_ip,
    'method': _one_of(METHODS),
    'path': _path,
    'status': _number(100, 599),
    'size': _number(0, MAX_SIZE),
}
