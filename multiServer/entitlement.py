"""Whether this controller holds the Multi-Server Manager licence.

The platform is asked the way the panel asks about every add-on (same address,
same request), with two differences: the feature asked about is always
'multi-server', and a LiteSpeed Enterprise server is not given a free yes.

    yes         reused for YES_SECONDS
    no          reused for NO_SECONDS
    no answer   (platform unreachable, any status but 200, a reply that is not
                exactly a yes or a no): the last yes still counts until
                GRACE_SECONDS after the platform gave it, then the answer is
                no. The platform is not asked again for RETRY_SECONDS, so an
                outage slows one request in that time, not every request.

Only the integer 1 as "status" in a JSON object is a yes and only the integer 0
is a no. An answer belongs to the address it was asked for: if the server's
address changes, the old answer is not used.

The last answer is one row of the panel's database (ms_entitlement), so every
worker process shares it. The database was chosen over a file because a website
user cannot write to it, it needs no directory that the unprivileged panel user
may write to, and a one-row update is atomic without a lock.

allowed() never raises and answers False whenever something is in doubt,
including a last answer that cannot be read or recorded. Pausing and revoking
links and reading the audit trail must never ask this module.
"""
import collections
import ipaddress
import json
import time

URL = 'https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission'
FEATURE = 'multi-server'
ADDRESS_FILE = '/etc/cyberpanel/machineIP'
YES_SECONDS = 60
NO_SECONDS = 10
RETRY_SECONDS = 10
GRACE_SECONDS = 24 * 60 * 60
MAX_REPLY = 4096
ROW = 1

State = collections.namedtuple('State', 'server_ip granted answered_at checked_at')


def allowed():
    """True only while the platform's answer for this server is yes."""
    try:
        return _decide(int(time.time())) is True
    except Exception:
        return False


def _decide(now):
    address = server_address()
    if address is None:
        return False
    state = _load()
    if state is not None and state.server_ip != address:
        state = None
    if state is not None:
        if state.answered_at > 0 and 0 <= now - state.answered_at < (
                YES_SECONDS if state.granted is True else NO_SECONDS):
            return state.granted is True
        if 0 <= now - state.checked_at < RETRY_SECONDS:
            return _in_grace(state, now)
    answer = ask(address)
    if answer is None:
        _save_attempt(address, now)
        return _in_grace(state, now)
    _save_answer(address, answer, now)
    return answer


def _in_grace(state, now):
    return (state is not None and state.granted is True and state.answered_at > 0
            and 0 <= now - state.answered_at <= GRACE_SECONDS)


def server_address():
    """The address the licence is sold for: the one the panel reports as its own."""
    try:
        with open(ADDRESS_FILE) as source:
            text = source.read(128).split('\n', 1)[0].strip()
        ipaddress.ip_address(text)
        return text if len(text) <= 45 and '%' not in text else None
    except Exception:
        return None


def ask(address):
    """The platform's answer: True, False, or None when it gave no usable one. Never raises."""
    try:
        import requests
        response = requests.post(URL, data=json.dumps({'name': FEATURE, 'IP': address}),
                                 headers={'Accept-Encoding': 'identity'}, timeout=(3.05, 10),
                                 allow_redirects=False, stream=True)
        try:
            if type(response.status_code) is not int or response.status_code != 200:
                return None
            reply = response.raw.read(MAX_REPLY + 1, decode_content=True)
        finally:
            response.close()
        if type(reply) is not bytes or len(reply) > MAX_REPLY:
            return None
        payload = json.loads(reply.decode('utf-8'), object_pairs_hook=_object)
        status = payload.get('status') if type(payload) is dict else None
        if type(status) is int and status in (0, 1):
            return status == 1
        return None
    except Exception:
        return None


def _object(pairs):
    """A JSON object, refused when a name appears twice (one reading must be the only one)."""
    names = [name for name, _ in pairs]
    if len(names) != len(set(names)):
        raise ValueError('A name is repeated.')
    return dict(pairs)


def _load():
    from multiServer.models import Entitlement
    row = Entitlement.objects.filter(pk=ROW).values_list(
        'server_ip', 'granted', 'answered_at', 'checked_at').first()
    return State(*row) if row is not None else None


_PUT = ('INSERT INTO ms_entitlement (id, server_ip, granted, answered_at, checked_at) '
        'VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE ')
# One statement each, so workers writing at the same moment cannot interleave.
_ANSWER = _PUT + ('server_ip = VALUES(server_ip), granted = VALUES(granted), '
                  'answered_at = VALUES(answered_at), checked_at = VALUES(checked_at)')
# The last answer is kept unless it was for another address; server_ip is
# assigned last because the conditions before it must still see the old value.
_ATTEMPT = _PUT + ('granted = IF(server_ip = VALUES(server_ip), granted, 0), '
                   'answered_at = IF(server_ip = VALUES(server_ip), answered_at, 0), '
                   'checked_at = VALUES(checked_at), server_ip = VALUES(server_ip)')


def _save_answer(address, granted, now):
    _execute(_ANSWER, [ROW, address, 1 if granted is True else 0, now, now])


def _save_attempt(address, now):
    """Note that the platform was asked in vain, without touching its last answer."""
    _execute(_ATTEMPT, [ROW, address, 0, 0, now])


def _execute(statement, values):
    from django.db import connection, transaction
    # Its own savepoint: a failed write must not spoil the caller's transaction.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(statement, values)
