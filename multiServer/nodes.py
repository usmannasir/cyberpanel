"""Controller node management from a local administrator session."""
import datetime
import re

from django.contrib import messages
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from multiServer import audit, entitlement, links, models, views


def administrator(request):
    admin = views.full_administrator(request)
    if not admin or admin.twoFA != 1 or admin.secretKey in ('', 'None', None):
        return None
    try:
        import pyotp
        if not pyotp.TOTP(admin.secretKey).byte_secret():
            return None
    except (ValueError, TypeError):
        return None
    session_key = request.session.session_key
    if (not session_key or any(key.startswith('HTTP_X_CPMS_') for key in request.META)
            or models.LinkSession.objects.filter(pk=session_key).exists()):
        return None
    return admin


def _date(timestamp):
    try:
        return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc) if timestamp else None
    except (OverflowError, OSError, ValueError, TypeError):
        return None


def summary(row):
    try:
        label = links.check_label(row.label)
    except links.InvalidLabel:
        label = 'Unnamed node'
    caps = row.advertised.split(',') if row.advertised else []
    valid = len(caps) <= links.MAX_CAPABILITIES and all(links._CAPABILITY.fullmatch(cap) for cap in caps)
    return {
        'id': row.link_id if links._is_link_id(row.link_id) else '',
        'label': label,
        'status': row.status if row.status in models.STATUSES else 'unknown',
        'version': row.panel_version if re.fullmatch(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,4}', row.panel_version or '') else '',
        'capabilities': ', '.join(caps) if valid else '',
        'seen': _date(row.last_seen_at),
        'error': row.last_error if row.last_error in links.STORED_ERRORS else ('Unknown error' if row.last_error else ''),
        'error_at': _date(row.last_error_at),
    }


@never_cache
def index(request):
    if not administrator(request):
        raise Http404()
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    from plogical.httpProc import httpProc
    rows = models.Node.objects.defer('sealed').order_by('label', 'link_id')
    return httpProc(request, 'multiServer/nodes.html',
                    {'nodes': [summary(row) for row in rows], 'licensed': entitlement.allowed()}).render()


def _step_up(admin, data):
    import pyotp
    from plogical import hashPassword
    password, code = data.get('password', ''), data.get('code', '')
    if not password or len(password) > 4096 or not hashPassword.check_password(admin.password, password):
        return 'password'
    try:
        if re.fullmatch('[0-9]{6}', code) and pyotp.TOTP(admin.secretKey).verify(code, valid_window=1):
            return None
    except (ValueError, TypeError):
        pass
    return 'two_factor'


@never_cache
@csrf_protect
@sensitive_post_parameters('password', 'code')
def control(request):
    admin = administrator(request)
    if not admin:
        raise Http404()
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    action = request.POST.get('action', '')
    link_id = request.POST.get('link_id', '')
    if not links._is_link_id(link_id) or action not in ('pause', 'resume', 'revoke', 'forget'):
        raise Http404()
    event = 'node_remove' if action == 'forget' else 'link_' + action
    if action in ('revoke', 'forget'):
        reason = (_step_up(admin, request.POST) if request.POST.get('confirm') == action else 'not_allowed')
        if reason:
            audit.record(event, outcome='refused', link_id=link_id, actor=admin.userName, reason=reason)
            messages.error(request, 'Confirm the action and enter your current password and verification code.')
            return redirect('multiServerNodes')
    actions = {'pause': links.pause, 'resume': links.resume, 'revoke': links.revoke, 'forget': links.remove}
    try:
        changed = actions[action](link_id, admin.userName)
    except Exception:
        audit.record(event, outcome='error', reason='internal', actor=admin.userName, link_id=link_id)
        changed = False
    if changed:
        messages.success(request, {'pause': 'Paused on this controller.', 'resume': 'Node resumed.',
                                   'revoke': 'The node confirmed revocation. Its controller record was removed.',
                                   'forget': 'Local record removed. Remote revocation is unconfirmed.'}[action])
    elif action == 'revoke':
        messages.error(request, 'Revocation was not confirmed. Check the node and retry if it is still listed.')
    else:
        messages.error(request, 'Action unavailable. Check the current node status and licence.')
    return redirect('multiServerNodes')
