"""Single-use native logins. Link locks serialize issuance, redemption and invalidation."""
import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils.crypto import salted_hmac

from multiServer import addresses, audit, keys, landings, links, models, switch, transport, views

ISSUE = '/multiserver/gateway/ticket'
CLEAR = '/multiserver/gateway/end-sessions'
TTL = 30
SESSION_TTL = 300
HEX = re.compile('[0-9a-f]{64}')
PROOF = re.compile('[0-9a-f]{128}')


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def stamp(*parts):
    return salted_hmac('multiserver.native.v1', json.dumps(parts, separators=(',', ':'))).hexdigest()


def account_stamp(admin):
    return stamp(admin.pk, admin.userName, admin.password, admin.twoFA, admin.secretKey, admin.acl_id)


def panel_origin(value):
    """Require a bare HTTPS origin, including a validated DNS/IP host and optional port."""
    from django.http.request import split_domain_port
    if not isinstance(value, str) or len(value) > 265 or not value.startswith('https://'):
        raise ValueError
    authority = value[8:]
    domain, port = split_domain_port(authority)
    if not domain or domain.endswith('.') or authority != domain + (':' + port if port else ''):
        raise ValueError
    if port and (not 1 <= int(port) <= 65535 or port != str(int(port))):
        raise ValueError
    # Browsers omit the default port from Host and Origin, including when the
    # paired transport explicitly names port 443 in its signed authority.
    return 'https://' + domain if port == '443' else value


def local_origin(request):
    if not request.is_secure():
        raise ValueError
    return panel_origin('https://' + request.get_host().lower())


def login_stamp(request, admin):
    return stamp(account_stamp(admin), local_origin(request), request.session.session_key, keys.role_revision(keys.CONTROLLER))


def remember_login(request, admin):
    try:
        if not settings.SESSION_COOKIE_DOMAIN:
            request.session['ms_local_login'] = login_stamp(request, admin)
    except ValueError:
        pass  # An unsupported panel origin cannot prevent a normal local login.


def verified_login(request, admin):
    saved = request.session.get('ms_local_login')
    return bool(admin and isinstance(saved, str) and not settings.SESSION_COOKIE_DOMAIN
                and hmac.compare_digest(saved, login_stamp(request, admin)))


def controller_admin(request):
    from multiServer import nodes
    admin = nodes.administrator(request)
    return admin if verified_login(request, admin) else None


def peer_row(link_id):
    if not links._is_link_id(link_id):
        raise ValueError
    row = models.Node.objects.select_for_update().get(pk=link_id, status=models.ACTIVE)
    if 'ticket' not in row.advertised.split(','):
        raise ValueError
    return links.link_of(row)


def live_link(link, admin_id):
    from multiServer.nodeGateway import _unusable
    if (switch.active_role() != keys.NODE or _unusable(link, keys.generation(), int(time.time()))
            or link.admin_id != admin_id):
        raise ValueError
    admin = views.active_full_administrator(admin_id)
    if not admin:
        raise ValueError
    return admin


def identity(link, admin, origin, target):
    return stamp(link.link_id, link.controller_key, link.allowed_ips, link.generation, link.activated_at,
                 account_stamp(admin), origin, target, keys.role_revision(keys.NODE))


def proof_message(flow, challenge):
    return ('CPMS1-BROWSER\n' + flow + '\n' + challenge).encode('ascii')


def gateway_issue(request):
    from multiServer.nodeGateway import _Refused
    try:
        if request.content_type != 'application/json' or len(request.body) > 500:
            raise ValueError
        page, origin = json.loads(request.body.decode('ascii'))
        origin = panel_origin(origin)
        target = panel_origin('https://' + request.host)
        if page not in landings.PAGES or urlsplit(target).hostname == urlsplit(origin).hostname:
            raise ValueError
        with transaction.atomic():
            link = models.Link.objects.select_for_update().get(pk=request.link_id)
            admin = live_link(link, request.admin_id)
            if request.source not in addresses.listed(link.allowed_ips):
                raise ValueError
            token = secrets.token_hex(32)
            now = int(time.time())
            models.SsoTicket.objects.filter(link=link, expires_at__lte=now).delete()
            models.LinkSession.objects.filter(link=link, created_at__lte=now-SESSION_TTL).delete()
            models.SsoTicket.objects.create(ticket_hash=digest(token), link=link, admin_id=admin.pk,
                actor=request.actor, landing=page + '|' + identity(link, admin, origin, target),
                created_at=now, expires_at=min(now + TTL, link.expires_at))
        audit.record('ticket_issue', outcome='ok', link_id=link.pk, actor=request.actor, source_ip=request.source)
        return 200, 'application/json', json.dumps(token).encode('ascii')
    except (TypeError, ValueError, models.Link.DoesNotExist):
        raise _Refused('not_allowed') from None


def clear(link):
    """Caller owns the Link row lock. Invalidate pending tickets and persistent native sessions."""
    sessions = models.LinkSession.objects.filter(link=link)
    if sessions.exists():
        Session.objects.filter(session_key__in=sessions.values('session_key')).delete()
    sessions.delete()
    models.SsoTicket.objects.filter(link=link).delete()


def gateway_clear(request):
    from multiServer.nodeGateway import _Refused
    if request.body or request.content_type != '-':
        raise _Refused('format')
    with transaction.atomic():
        link = models.Link.objects.select_for_update().get(pk=request.link_id)
        clear(link)
    return 200, 'application/json', b'{"ended":true}'


def end_paused(link_id, actor):
    """Local pause is already committed. A paused row retains the key for retry."""
    try:
        with transaction.atomic():
            row = models.Node.objects.select_for_update().get(pk=link_id, status=models.PAUSED)
            result = transport.send(links.link_of(row), 'POST', CLEAR, '', '-', b'', actor, 'ticket')
            return result == (200, 'application/json', b'{"ended":true}')
    except Exception:
        return False


def ticket_state(flow, origin, target):
    # Always lock the link before the ticket, just like clear(). A second worker sees a
    # committed consumption or deletion before it can create another native session.
    link_id = models.SsoTicket.objects.values_list('link_id', flat=True).get(pk=flow)
    link = models.Link.objects.select_for_update().get(pk=link_id)
    ticket = models.SsoTicket.objects.select_for_update().get(pk=flow, link=link, used=False)
    admin = live_link(link, ticket.admin_id)
    page, saved = ticket.landing.split('|')
    if (ticket.expires_at <= int(time.time()) or page not in landings.PAGES
            or not hmac.compare_digest(saved, identity(link, admin, origin, target))):
        raise ValueError
    return link, ticket, admin, page, saved


def managed_context(request):
    state = request.session['ms_managed']
    link = models.Link.objects.get(pk=state['link'])
    admin = live_link(link, request.session['userID'])
    now = int(time.time())
    if (now >= state['until'] or not models.LinkSession.objects.filter(pk=request.session.session_key, link=link,
            created_at__gt=now-SESSION_TTL).exists() or not hmac.compare_digest(
                state['stamp'], identity(link, admin, state['origin'], local_origin(request)))):
        raise ValueError
    return state
