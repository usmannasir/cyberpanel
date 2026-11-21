"""The gateway on a managed server for requests from its controller.

It is the first middleware of the panel and does nothing at all unless this
server's role is `node` and the request carries a header whose name begins with
X-CPMS-. Such a request is the gateway's alone: it is never passed on to the
panel's sessions, cookies or views, whatever else it carries. It is verified
and answered here, or it is refused here.

One such request does not come over a link, because it is the one that asks
for a link: POST /multiserver/pair. It is handed to pairing.node_receive as it
arrived, before any of the checks below, and that module's answer is sent as
it is (pairing.py describes the request, its own checks and its one refusal).

Before anything is checked, every header a client can set is taken off the
request except Host, so that what remains is exactly what the controller signed
(transport.py lists how each signed field travels). The checks then run in this
order, and the first that fails ends the request:

    format      the seven X-CPMS-* headers and nothing else under that prefix,
                each in its exact form; GET or POST; a Host; no transfer coding
    size        the declared length within transport.MAX_REQUEST_BODY, none for GET
    link        the request names this server; the link exists and is active,
                unexpired and of the current generation
    source_ip   the address the connection came from is one the link allows
                (addresses.py is the one rule for both)
    time        signed within WINDOW seconds of now and at most WINDOW seconds
                behind the newest signed time accepted on the link
    size        the body is as long as declared (it is kept only now: nobody who
                failed a check above makes this server hold one in memory)
    signature   the controller's signature over the request as it arrived
    replay      the nonce is new on the link; stored only now, in one
                transaction with the link's newest accepted time
    admin       the administrator the link acts as is still an active full one
    not_allowed the mode and path have a handler in ROUTES

Until the signature has verified, a refusal is unsigned and is the answer this
panel gives a visitor who is not signed in at an address that does not exist,
so it says nothing about which check failed. From then on every reply, a
refusal included, is signed with this server's identity key and bound to the
request (crypto.response_message). Refusals before verification share a bounded audit budget with pairing. Of a request, only its link, actor, address, method, path and
length are ever written down: no reply, audit row or log line repeats a key, a
request's signature, its body or its nonce. Nothing raised in here reaches the
panel's error pages.

Whatever the answer, the request body is read to its declared end first. The
panel's web server passes a body to the application as a stream and takes its
next request from the same stream, so nothing may be left on it unread.
"""
import collections
import hmac
import json
import re
import time

from multiServer import addresses, crypto, keys, pairing, switch, transport

WINDOW = 90  # seconds a signed time may differ from this server's clock, either way
PRUNE_EVERY = 60  # a link's dead nonces are removed when its newest accepted time enters a new minute
MAX_REPLY_BODY = transport.MAX_RESPONSE - transport.MAX_RESPONSE_HEAD
JSON = 'application/json'
HELLO = '/multiserver/gateway/hello'
NEEDS_SESSION = 'This request need session.'  # the words of CyberCP/secMiddleware.py

_PREFIX = 'HTTP_X_CPMS_'
_FIELDS = dict(('HTTP_' + name.upper().replace('-', '_'), field) for field, name in transport.HEADERS.items())
_TIME = re.compile(r'0|[1-9][0-9]{0,10}')
_LENGTH = re.compile(r'0|[1-9][0-9]{0,17}')
_SIGNATURE = re.compile(r'[0-9a-f]{128}')
_KEY = re.compile(r'[0-9a-f]{64}')
_DUPLICATE = 1062  # MariaDB: the unique key already has this value

# What a handler is given: the request as it was signed and verified, and nothing else of it.
Verified = collections.namedtuple(
    'Verified', 'link_id admin_id actor mode method host path query content_type body source')
Route = collections.namedtuple('Route', 'capability method query handler')


def _hello(verified):
    import cyberpanel_version
    return 200, JSON, _json({'version': cyberpanel_version.VERSION, 'build': cyberpanel_version.BUILD,
                             'role': keys.NODE, 'capabilities': capabilities()})


# Everything a controller can ask of this server, by (mode, path). A handler is called only for a
# request that passed every check above, with its exact method, and without a query unless the route
# takes one. It returns (status, media type, body). Nothing here leads to the panel's URL table.
ROUTES = {
    ('json', HELLO): Route('hello', 'GET', False, _hello),
}

# Extension point, empty on purpose. A later mode that cannot be answered from ROUTES registers one
# callable here under its name: handler(verified, request, get_response) -> (status, media type, body).
# Meant for 'page' and 'static' (passing a request on to the panel with a session that is never
# stored), 'confirm' (pairing) and 'rotate' (a new link key). Such a handler is where the rule belongs
# that the Multi-Server pages, login, /api, /cloudAPI, the firewall and the mapped administrator's own
# user and two-factor settings are never reachable through a link. While a mode is not listed, every
# request in it that has no route is refused as not_allowed.
MODE_HANDLERS = {}


def capabilities():
    """The names a controller may rely on, taken from the routes themselves."""
    return sorted(set(route.capability for route in ROUTES.values()))


class NodeGateway(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _addressed(request.META) or switch.active_role() != keys.NODE:
            return self.get_response(request)
        if request.META.get('REQUEST_METHOD') == 'POST' and request.path_info == pairing.PATH:
            return _pair(request)
        exchange = _Exchange()
        try:
            try:
                response = _serve(request, exchange, self.get_response)
            except _Refused as refusal:
                response = _refuse(exchange, refusal.reason)
            except Exception as error:
                _note(error)
                response = _refuse(exchange, 'internal')
        except Exception:
            response = _absent(exchange.has_body, exchange.language)
        if not exchange.read:
            _drain(request)
        return response


def _pair(request):
    """Hand a pairing request to pairing.node_receive and send its answer as it is."""
    try:
        response = pairing.node_receive(request)
    except Exception as error:  # it says it never raises; nothing raised here may reach the panel's error pages
        _note(error)
        response = pairing.refused()
    _drain(request)
    return response


class _Refused(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


class _Exchange(object):
    """What is known of one request so far: it decides how a refusal is answered and what is audited."""
    __slots__ = ('source', 'link_id', 'actor', 'method', 'path', 'size', 'has_body', 'language', 'read',
                 'node', 'identity', 'nonce', 'signed')

    def __init__(self):
        for name in self.__slots__:
            setattr(self, name, None)


def _addressed(meta):
    return any(type(name) is str and name.startswith(_PREFIX) for name in meta)


def _serve(request, exchange, get_response):
    meta = request.META
    now = int(time.time())
    exchange.source = addresses.peer(meta.get('REMOTE_ADDR'))
    exchange.has_body = _declares_body(meta)
    coded = 'HTTP_TRANSFER_ENCODING' in meta or meta.get('HTTP_CONTENT_ENCODING', 'identity') != 'identity'
    named = _strip(request, exchange)

    # format
    method, host = meta.get('REQUEST_METHOD'), meta.get('HTTP_HOST')
    path, query = request.path_info, meta.get('QUERY_STRING', '')
    content_type, length = meta.get('CONTENT_TYPE'), meta.get('CONTENT_LENGTH')
    if method in crypto.METHODS:
        exchange.method = method
    exchange.path = path
    if coded or set(named) != set(_FIELDS.values()) or content_type == '-':
        raise _Refused('format')
    content_type = content_type or '-'
    length = length or '0'
    if (not _matches(_TIME, named['timestamp']) or not _matches(_SIGNATURE, named['signature'])
            or not _matches(_LENGTH, length)):
        raise _Refused('format')
    timestamp, declared = int(named['timestamp']), int(length)

    def signed_bytes(body):
        return crypto.request_message(named['link'], named['node'], method, host, path, query, content_type,
                                      body, timestamp, named['nonce'], named['actor'], named['mode'])
    try:
        signed_bytes(b'')  # the signer's own grammar for every field, before any of them is used
    except ValueError:
        raise _Refused('format') from None
    exchange.size = declared

    # size
    if declared > transport.MAX_REQUEST_BODY or (method == 'GET' and declared):
        raise _Refused('size')

    # link
    identity = keys.identity_key()
    if identity is None:
        raise _Refused('internal')
    node = crypto.node_id(crypto.public_key(identity))
    if not hmac.compare_digest(node, named['node']):
        raise _Refused('link')
    from multiServer import models
    generation = keys.generation()
    link = models.Link.objects.filter(pk=named['link']).first()
    if link is not None:
        exchange.link_id = link.link_id  # the audit trail names a link only when there is one of that name
    unusable = _unusable(link, generation, now)
    if unusable:
        raise _Refused(unusable)

    # source_ip
    if not addresses.allows(link.allowed_ips, exchange.source):
        raise _Refused('source_ip')

    # time
    if abs(timestamp - now) > WINDOW or timestamp < link.last_request_at - WINDOW:
        raise _Refused('time')

    # size, of the body itself
    try:
        body = request.body
    except Exception:  # not only OSError: lswsgi's stream fails without naming an error
        raise _Refused('size') from None
    exchange.read = True
    if len(body) != declared:
        raise _Refused('size')

    # signature
    message = signed_bytes(body)
    if not crypto.verify(bytes.fromhex(link.controller_key), bytes.fromhex(named['signature']), message):
        raise _Refused('signature')
    exchange.node, exchange.identity, exchange.nonce = node, identity, named['nonce']
    exchange.actor = named['actor']
    exchange.signed = message  # from here on every reply is signed

    # replay
    _accept(link, generation, timestamp, named['nonce'], now)

    # admin
    from multiServer import views
    if views.active_full_administrator(link.admin_id) is None:
        raise _Refused('admin')

    # not_allowed
    verified = Verified(link.link_id, link.admin_id, named['actor'], named['mode'], method, host, path, query,
                        content_type, body, exchange.source)
    status, media_type, reply = _dispatch(verified, request, get_response)
    response = _signed(exchange, status, media_type, reply)
    _audit(exchange, 'ok', None, status)
    return response


def _dispatch(verified, request, get_response):
    route = ROUTES.get((verified.mode, verified.path))
    if route is not None:
        if route.method != verified.method or (verified.query and not route.query):
            raise _Refused('not_allowed')
        return route.handler(verified)
    handler = MODE_HANDLERS.get(verified.mode)
    if handler is None:
        raise _Refused('not_allowed')
    return handler(verified, request, get_response)


def _strip(request, exchange):
    """Take the link headers out of the request and drop every other header but Host; return the link headers.

    Cookies, credentials and forwarding headers are gone before anything else looks at the request, so
    nothing can take the caller for a signed-in user or for another address. The link headers leave the
    request too: nothing that later handles it, or reports on it, can come across a signature or a nonce.
    """
    meta = request.META
    request.COOKIES = {}
    # The one thing read from an unsigned header, and only to word an unsigned refusal.
    exchange.language = _language(request)
    named = {}
    for name in [name for name in meta if type(name) is str and name.startswith('HTTP_') and name != 'HTTP_HOST']:
        value = meta.pop(name)
        if name.startswith(_PREFIX):
            # An unknown name is kept under itself, so the set of names found is not the set required.
            named[_FIELDS.get(name, name)] = value
    request.__dict__.pop('headers', None)  # Django's view of the headers, should anything have built it
    return named


def _drain(request):
    """Read what is left of the request body, as far as it was declared, and throw it away. Never raises."""
    try:
        while request.read(65536):
            pass
    except Exception:
        pass


def _matches(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def _declares_body(meta):
    """Whether the panel itself would find a body on this request: it reads as many bytes as are declared."""
    try:
        return int(meta.get('CONTENT_LENGTH')) > 0
    except (TypeError, ValueError):
        return False


def _language(request):
    try:
        from django.utils import translation
        return translation.get_language_from_request(request)
    except Exception:
        return None


def _unusable(link, generation, now):
    """Why a link row cannot carry a request now, or None."""
    from multiServer import models
    if link is None or link.status != models.ACTIVE or not _matches(_KEY, link.controller_key):
        return 'link'
    if link.expires_at <= now:
        return 'expired'
    # The counter starts at 1; 0 means it could not be read, and then no link counts.
    if generation < 1 or link.generation != generation:
        return 'generation'
    return None


def _checked(link):
    return link.controller_key, link.allowed_ips, link.admin_id


def _accept(link, generation, timestamp, nonce, now):
    """Accept a fresh nonce without moving the link's newest timestamp backwards.

    The link row is updated first. That serialises the requests of one link, and it confirms at the
    moment of acceptance what was read from the row earlier: still active, unexpired, of this
    generation, with the same controller key, addresses and administrator, and still inside the ordering window. The nonce is then inserted, and the unique index on (link, nonce) is what
    refuses a second use; a refusal undoes the update.

    seen_at holds the signed time. A nonce more than WINDOW below the link's newest accepted time can
    be removed whatever this server's clock does, because that signed timestamp can never again be accepted.
    """
    from django.db import IntegrityError, transaction
    from django.db.models import Value
    from django.db.models.functions import Greatest
    from multiServer import models
    try:
        with transaction.atomic():
            advanced = models.Link.objects.filter(
                pk=link.link_id, status=models.ACTIVE, generation=generation, expires_at__gt=now,
                controller_key=link.controller_key, allowed_ips=link.allowed_ips, admin_id=link.admin_id,
                last_request_at__lte=timestamp + WINDOW
            ).update(last_request_at=Greatest('last_request_at', Value(timestamp)))
            if advanced != 1:
                current = models.Link.objects.filter(pk=link.link_id).first()
                reason = _unusable(current, generation, now)
                if reason is None and _checked(current) != _checked(link):
                    reason = 'link'
                raise _Refused(reason or 'time')
            models.Nonce.objects.create(link_id=link.link_id, nonce=nonce, seen_at=timestamp)
    except IntegrityError as error:
        if getattr(error.__cause__, 'args', (None,))[0] != _DUPLICATE:
            raise
        raise _Refused('replay') from None
    if timestamp // PRUNE_EVERY > link.last_request_at // PRUNE_EVERY:
        try:
            models.Nonce.objects.filter(link_id=link.link_id, seen_at__lt=timestamp - WINDOW).delete()
        except Exception as error:
            _note(error)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')


def _signed(exchange, status, media_type, body):
    """A reply the controller will accept: whole, of stated length, signed for this very request."""
    if (type(status) is not int or not 200 <= status <= 599 or 300 <= status <= 399 or status in (204, 205)
            or type(body) is not bytes or len(body) > MAX_REPLY_BODY or media_type == '-'):
        raise ValueError('Not a reply a link can carry.')
    message = crypto.response_message(exchange.link_id, exchange.node, exchange.nonce, exchange.signed, status,
                                      media_type, body)
    from django.http import HttpResponse
    response = HttpResponse(body, status=status, content_type=media_type)
    response['Content-Length'] = str(len(body))
    response['Cache-Control'] = 'no-store'
    response[transport.HEADERS['signature']] = crypto.sign(exchange.identity, message).hex()
    # Django would otherwise log a 4xx or 5xx reply and, for a 5xx, compose a report on the request.
    response._has_been_logged = True
    return response


def _absent(has_body, language):
    """This panel's answer to a visitor who is not signed in, at an address that does not exist.

    Built by hand, header for header in the order the panel's own middleware adds them, because the
    request must not be passed to that middleware. multiServer/test_gateway.py compares the two.

    It is the same for every address, and that is where it can be told from a panel without a link:
    a few addresses are answered there without a session (the sign-in page, /verifyLogin, /api and
    the like), a malformed Host is answered with 400, and a language cookie changes Content-Language.
    None of that tells a caller which check a request failed.
    """
    from django.conf import settings
    from django.http import HttpResponse, HttpResponseRedirect
    if has_body:
        response = HttpResponse(json.dumps({'error_message': NEEDS_SESSION, 'errorMessage': NEEDS_SESSION}))
    else:
        response = HttpResponseRedirect('/')
    response['X-Frame-Options'] = getattr(settings, 'X_FRAME_OPTIONS', 'DENY').upper()
    response['Content-Length'] = str(len(response.content))
    response['Vary'] = 'Accept-Language, Cookie'
    response['Content-Language'] = language or settings.LANGUAGE_CODE
    if getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False):
        response['X-Content-Type-Options'] = 'nosniff'
    for header, setting in (('Referrer-Policy', 'SECURE_REFERRER_POLICY'),
                            ('Cross-Origin-Opener-Policy', 'SECURE_CROSS_ORIGIN_OPENER_POLICY')):
        policy = getattr(settings, setting, None)  # the second exists from Django 4.0
        if policy:
            response[header] = ','.join(part.strip() for part in (
                policy.split(',') if isinstance(policy, str) else policy))
    return response


def _refuse(exchange, reason):
    response = None
    if exchange.signed is not None:
        try:
            response = _signed(exchange, 500 if reason == 'internal' else 403, JSON, _json({'error': reason}))
        except Exception as error:
            _note(error)
    if response is None:
        response = _absent(exchange.has_body, exchange.language)
    _audit(exchange, 'refused', reason, response.status_code)
    return response


def _audit(exchange, outcome, reason, status):
    from multiServer import audit
    fields = {'outcome': outcome, 'status': status}
    for name, value in (('reason', reason), ('link_id', exchange.link_id), ('actor', exchange.actor),
                        ('source_ip', exchange.source),
                        ('method', exchange.method), ('path', exchange.path), ('size', exchange.size)):
        if value is not None:
            fields[name] = value
    record = audit.record if exchange.signed is not None else audit.record_unverified
    record('request', **fields)


_NOTED = {}  # kind of failure -> when this process last wrote it down


def _note(error):
    """Leave the kind of an unexpected failure in the panel's log, once a minute for each kind.

    Never its text, which may quote a request; and not once for every request, because while something
    is broken anybody can send the request that fails.
    """
    try:
        kind, now = type(error).__name__, time.time()
        if now - _NOTED.get(kind, 0) < 60:
            return
        _NOTED[kind] = now
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        CyberCPLogFileWriter.writeToFile('Multi-Server Manager gateway failed: %s' % kind)
    except Exception:
        pass
