"""Whether this controller holds the Multi-Server Manager licence.

The platform is asked the way the panel asks about every add-on (same address,
same request), with two differences: the feature asked about is always
'multi-server', and a LiteSpeed Enterprise server is not given a free yes.

    yes         reused for YES_SECONDS
    no          reused for NO_SECONDS
    no answer   (platform unreachable, any status but 200, a reply that is not
                exactly a yes or a no): the last yes still counts until
                GRACE_SECONDS after the platform gave it, then the answer is
                no. The platform is not asked again for RETRY_SECONDS.

One worker asks at a time. Before anybody asks, the time of the attempt is
written to the stored row, in a statement that only one of several workers
arriving together can win (_claim). The others, and every request of the next
RETRY_SECONDS, are answered at once from what is stored. The one that asks
waits DEADLINE seconds at most, whatever the platform or the network does. So a
platform that stalls delays one request in RETRY_SECONDS by DEADLINE seconds;
it never holds up every page of the controller.

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
import threading
import time
from urllib.parse import urlencode

URL = 'https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission'
ORDER_PAGE = 'https://platform.cyberpersons.com/order/multi-server/'
FEATURE = 'multi-server'
ADDRESS_FILE = '/etc/cyberpanel/machineIP'
YES_SECONDS = 60
NO_SECONDS = 10
RETRY_SECONDS = 10
GRACE_SECONDS = 24 * 60 * 60
DEADLINE = 4  # seconds the one request that asks may wait for the platform, in all
CONNECT_SECONDS = 2
READ_SECONDS = 2
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
    state = _stored(address)
    known = _known(state, now)
    if known is not None:
        return known
    if not _claim(address, now):
        # Another worker is asking at this moment, or has just asked.
        state = _stored(address)
        known = _known(state, now)
        return known if known is not None else _in_grace(state, now)
    answer = ask(address)
    if answer is None:
        return _in_grace(state, now)
    _save_answer(address, answer, now)
    return answer


def _stored(address):
    state = _load()
    return state if state is not None and state.server_ip == address else None


def _known(state, now):
    """The answer that needs no asking, or None when it is time to ask the platform."""
    if state is None:
        return None
    if state.answered_at > 0 and 0 <= now - state.answered_at < (
            YES_SECONDS if state.granted is True else NO_SECONDS):
        return state.granted is True
    if 0 <= now - state.checked_at < RETRY_SECONDS:
        return _in_grace(state, now)
    return None


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


def purchase_url():
    """Where the licence for this controller is bought.

    The order form opens with the address this server asks about, so the licence
    is bought for the address the platform will be asked for. Never raises.
    """
    address = server_address()
    return ORDER_PAGE + ('?' + urlencode({'ip': address}) if address else '')


def ask(address):
    """The platform's answer: True, False, or None when it gave no usable one in DEADLINE seconds. Never raises.

    The request runs beside the caller, who waits for it no longer than that. The time limits
    of the request itself count for each step and for each address tried, and resolving the
    name has none, so they cannot promise a total. A request that is left behind ends by
    those limits, and its late answer is not used.
    """
    try:
        answers = []
        asking = threading.Thread(target=lambda: answers.append(_ask(address)))
        asking.daemon = True
        asking.start()
        asking.join(DEADLINE)
        return answers[0] if answers else None
    except Exception:
        return None


def _ask(address):
    try:
        import requests
        response = requests.post(URL, data=json.dumps({'name': FEATURE, 'IP': address}),
                                 headers={'Accept-Encoding': 'identity'}, timeout=(CONNECT_SECONDS, READ_SECONDS),
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


# One statement, so workers writing at the same moment cannot interleave.
_ANSWER = ('INSERT INTO ms_entitlement (id, server_ip, granted, answered_at, checked_at) '
           'VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE '
           'server_ip = VALUES(server_ip), granted = VALUES(granted), '
           'answered_at = VALUES(answered_at), checked_at = VALUES(checked_at)')
# The row is changed only while no attempt of the last RETRY_SECONDS stands in it for this
# address, so of the workers that run this at the same moment exactly one changes it. The last
# answer is kept unless it was for another address; server_ip is assigned last because the
# conditions before it must still see the old value.
_CLAIM = ('UPDATE ms_entitlement SET granted = IF(server_ip = %s, granted, 0), '
          'answered_at = IF(server_ip = %s, answered_at, 0), checked_at = %s, server_ip = %s '
          'WHERE id = %s AND NOT (server_ip = %s AND checked_at > %s AND checked_at <= %s)')
_FIRST = 'INSERT INTO ms_entitlement (id, server_ip, granted, answered_at, checked_at) VALUES (%s, %s, 0, 0, %s)'


def _save_answer(address, granted, now):
    _execute(_ANSWER, [ROW, address, 1 if granted is True else 0, now, now])


def _claim(address, now):
    """Note that the platform is being asked now; True for the one worker that is to ask it.

    False when another worker noted an attempt within the last RETRY_SECONDS. The last answer is
    not touched, so it still counts for the grace period if this attempt gets no answer.
    """
    from django.db import IntegrityError, connection, transaction
    try:
        # Its own savepoint: a failed write must not spoil the caller's transaction.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(_CLAIM, [address, address, now, address, ROW, address, now - RETRY_SECONDS, now])
                if cursor.rowcount == 1:
                    return True
                cursor.execute('SELECT 1 FROM ms_entitlement WHERE id = %s', [ROW])
                if cursor.fetchone() is not None:
                    return False
                cursor.execute(_FIRST, [ROW, address, now])
                return True
    except IntegrityError:
        return False  # another worker stored the very first row at the same moment, and it asks


def _execute(statement, values):
    from django.db import connection, transaction
    # Its own savepoint: a failed write must not spoil the caller's transaction.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(statement, values)
