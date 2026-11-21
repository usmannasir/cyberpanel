"""Private native-panel handoff, with a browser binding across the two HTTPS origins.

A navigation POST under no-referrer may carry Origin: null. The first POST therefore
cannot log anyone in. The node sets a host-only random cookie and posts its digest to
the controller. Only the original local session can sign that digest. The last POST
needs both the signature and the same browser's node cookie, within the ticket's 30s.
The cookie is set during a top-level visit, with no iframe or opener.
"""
import hmac
import json
import secrets
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.csrf import rotate_token
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect

from multiServer import audit, crypto, entitlement, landings, models, sso, transport

BIND = '__Host-cpms-node'
RETURN = '__Host-cpms-return'
PREFIX = '/multiserver/login/'
PATHS = frozenset(PREFIX + suffix for suffix in ('select', 'arrive', 'return', 'finish', 'redeem'))


def private(response, policy="default-src 'none'; form-action 'none'"):
    response['Cache-Control'] = 'no-store, private'
    response['Referrer-Policy'] = 'no-referrer'
    response['Content-Security-Policy'] = policy + "; frame-ancestors 'none'; base-uri 'none'"
    response['Cross-Origin-Opener-Policy'] = 'same-origin'
    response['X-Frame-Options'] = 'DENY'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def failed(status=403):
    return private(HttpResponse('Server login unavailable. Return to the controller and select the server again.',
                                status=status, content_type='text/plain'))


def post_bridge(origin, step, fields):
    nonce = secrets.token_hex(16)
    action = origin + PREFIX + step
    html = render_to_string('multiServer/post.html', dict(action=action, fields=fields.items(), nonce=nonce))
    return private(HttpResponse(html), "default-src 'none'; script-src 'nonce-%s'; form-action %s" % (nonce, origin))


def form(request, fields, csrf=False):
    if (request.method != 'POST' or request.META.get('QUERY_STRING') or
            request.content_type != 'application/x-www-form-urlencoded' or
            not 0 < int(request.META.get('CONTENT_LENGTH') or 0) <= 2048):
        raise ValueError
    data = request.POST
    if set(data) - set(fields) - ({'csrfmiddlewaretoken'} if csrf else set()):
        raise ValueError
    if any(len(data.getlist(field)) != 1 for field in fields):
        raise ValueError
    return [data[field] for field in fields]


def check_cross_origin(request, origin):
    if request.META.get('HTTP_ORIGIN') not in ('null', origin):
        raise ValueError


def allowed_controller(request):
    admin = sso.controller_admin(request)
    if not admin or not entitlement.allowed():
        raise ValueError
    return admin


@csrf_protect
def select(request):
    admin = allowed_controller(request)
    origin = sso.local_origin(request)
    if request.META.get('HTTP_ORIGIN') != origin:
        raise ValueError
    link_id, page = form(request, ('server', 'page'), csrf=True)
    if page not in landings.PAGES:
        raise ValueError
    if link_id == 'local':
        return private(HttpResponseRedirect(landings.path(page)))
    with transaction.atomic():
        link = sso.peer_row(link_id)
        target = sso.panel_origin('https://' + link.authority)
        if urlsplit(origin).hostname == link.host:
            raise ValueError
        sent = int(time.time())
        status, media, body = transport.send(link, 'POST', sso.ISSUE, '', 'application/json',
            json.dumps([page, origin]).encode('ascii'), admin.userName, 'ticket')
        if status != 200 or media != 'application/json' or len(body) != 66:
            raise ValueError
        token = json.loads(body.decode('ascii'))
        if not sso.HEX.fullmatch(token):
            raise ValueError
        request.session['ms_open'] = [sso.digest(token), link_id, sent + sso.TTL]
    audit.record('ticket_issue', outcome='ok', link_id=link_id, actor=admin.userName,
                 source_ip=request.META.get('REMOTE_ADDR'))
    return post_bridge(target, 'arrive', {'ticket': token, 'controller': origin})


def transient(response, name, value):
    response.set_cookie(name, value, max_age=sso.TTL, secure=True, httponly=True, samesite='None', path='/')


def arrive(request):
    token, origin = form(request, ('ticket', 'controller'))
    origin = sso.panel_origin(origin)
    check_cross_origin(request, origin)
    if not sso.HEX.fullmatch(token):
        raise ValueError
    flow = sso.digest(token)
    with transaction.atomic():
        sso.ticket_state(flow, origin, sso.local_origin(request))
    cookie = secrets.token_hex(32)
    response = post_bridge(origin, 'return', {'flow': flow, 'challenge': sso.digest(cookie)})
    transient(response, BIND, cookie)
    return response


def returned(request):
    # The native controller cookie can be SameSite=Lax or Strict and absent on this
    # cross-site POST. Re-enter the controller in a first-party document before finish.
    flow, challenge = form(request, ('flow', 'challenge'))
    if not all(sso.HEX.fullmatch(x) for x in (flow, challenge)):
        raise ValueError
    sso.local_origin(request)
    nonce = secrets.token_hex(16)
    html = render_to_string('multiServer/return.html', {'nonce': nonce})
    response = private(HttpResponse(html), "default-src 'none'; script-src 'nonce-%s'" % nonce)
    transient(response, RETURN, flow + '.' + challenge)
    return response


def finish(request):
    if request.method != 'GET' or request.META.get('QUERY_STRING'):
        raise ValueError
    allowed_controller(request)
    flow, challenge = request.COOKIES.get(RETURN, '').split('.')
    pending, link_id, expires = request.session.get('ms_open', ())
    if (not all(sso.HEX.fullmatch(x) for x in (flow, challenge)) or not hmac.compare_digest(flow, pending)
            or expires <= int(time.time())):
        raise ValueError
    with transaction.atomic():
        link = sso.peer_row(link_id)
        proof = crypto.sign(link.private_key, sso.proof_message(flow, challenge)).hex()
    del request.session['ms_open']
    response = post_bridge('https://' + link.authority, 'redeem',
                           {'flow': flow, 'controller': sso.local_origin(request), 'proof': proof})
    transient(response, RETURN, '')
    return response


def redeem(request):
    from CyberCP.sessionSecurity import get_client_ip, session_ip_key
    flow, origin, proof = form(request, ('flow', 'controller', 'proof'))
    origin = sso.panel_origin(origin)
    check_cross_origin(request, origin)
    target = sso.local_origin(request)
    cookie = request.COOKIES.get(BIND, '')
    ip = session_ip_key(get_client_ip(request))
    if not (ip and sso.HEX.fullmatch(flow) and sso.HEX.fullmatch(cookie) and sso.PROOF.fullmatch(proof)):
        raise ValueError
    if settings.SESSION_ENGINE != 'django.contrib.sessions.backends.db' or settings.SESSION_COOKIE_DOMAIN:
        raise ValueError
    with transaction.atomic():
        link, ticket, admin, page, stamp = sso.ticket_state(flow, origin, target)
        if not crypto.verify(bytes.fromhex(link.controller_key), bytes.fromhex(proof),
                             sso.proof_message(flow, sso.digest(cookie))):
            raise ValueError
        location = landings.path(page)
        now = int(time.time())
        if models.SsoTicket.objects.filter(pk=flow, used=False, expires_at__gt=now).update(used=True) != 1:
            raise ValueError
        until = min(link.expires_at, now + sso.SESSION_TTL)
        fresh = SessionStore()
        fresh.update({'userID': admin.pk, 'ipAddr': ip, 'ms_managed': {
            'link': link.pk, 'origin': origin, 'stamp': stamp, 'actor': ticket.actor, 'until': until}})
        # Django 3.1's JSON session serializer supports integer expiry. The
        # absolute deadline above is independently enforced on every managed request.
        fresh.set_expiry(until - now)
        fresh.create()
        models.LinkSession.objects.create(link=link, session_key=fresh.session_key, created_at=now)
    # An unrelated prior local login remains a distinct database session. Only the new,
    # link-scoped identifier is delivered. No inherited session keys or user preferences.
    request.session = fresh
    rotate_token(request)
    response = private(HttpResponseRedirect(location))
    response.status_code = 303
    transient(response, BIND, '')
    audit.record('ticket_use', outcome='ok', link_id=link.pk, actor=ticket.actor,
                 source_ip=request.META.get('REMOTE_ADDR'), path=location)
    return response


def dispatch(request, operation):
    try:
        if any(k.startswith('HTTP_X_CPMS_') for k in request.META):
            return failed()
        return operation(request)
    except Exception:
        # Transport, expiration, stale session, schema and role changes all fail closed.
        # No exception, form, request body, token or cookie is rendered or logged.
        return failed()


def guard(request):
    """Run before ordinary panel routes, including routes that normally allow anonymous access."""
    from django.urls import resolve, Resolver404
    try:
        state = sso.managed_context(request)
    except Exception:
        request.session.flush()
        return failed()
    try:
        match = resolve(request.path_info)
    except Resolver404:
        return failed(404)
    if match.url_name == 'logout':
        models.LinkSession.objects.filter(pk=request.session.session_key).delete()
        request.session.flush()
        return private(HttpResponseRedirect('/'))
    if not landings.native_allowed(match):
        return failed()
    request.ms_managed = state
    return None
