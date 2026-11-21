"""Controller node management from a local administrator session."""
import datetime
import re

from django.contrib import messages
from django.db import DatabaseError
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from multiServer import audit, entitlement, links, models, stepup, views


def administrator(request):
    admin = views.full_administrator(request)
    if not admin or not views.two_factor_enrolled(admin):
        return None
    session_key = getattr(request.session, 'session_key', None)
    if not session_key or request.session.get('ms_managed') or any(key.startswith('HTTP_X_CPMS_') for key in request.META):
        return None
    try:
        return None if models.LinkSession.objects.filter(pk=session_key).exists() else admin
    except DatabaseError:
        # The navigation processor also runs on unrelated panel pages.
        return None


def switch_choices():
    choices = []
    rows = models.Node.objects.filter(status=models.ACTIVE).values_list('pk', 'label', 'advertised').order_by('label', 'pk')
    for link_id, label, advertised in rows:
        if links._is_link_id(link_id) and 'ticket' in advertised.split(','):
            try:
                label = links.check_label(label)
            except links.InvalidLabel:
                label = 'Unnamed node'
            choices.append({'id': link_id, 'label': label})
    return choices


def _date(timestamp):
    try:
        return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc) if timestamp else None
    except (OverflowError, OSError, ValueError, TypeError):
        return None


def _number(row):
    """The number to read out for a server that waits for approval, as two groups of four digits; '' if none."""
    from multiServer import pairing
    number = pairing.shown_number(row) if row.status == models.PENDING else None
    return '%s %s' % (number[:4], number[4:]) if number else ''


def summary(row):
    try:
        label = links.check_label(row.label)
    except links.InvalidLabel:
        label = 'Unnamed node'
    caps = row.advertised.split(',') if row.advertised else []
    valid = len(caps) <= links.MAX_CAPABILITIES and all(links._CAPABILITY.fullmatch(cap) for cap in caps)
    return {
        'number': _number(row),
        'id': row.link_id if links._is_link_id(row.link_id) else '',
        'label': label,
        'status': row.status if row.status in models.STATUSES else 'unknown',
        'version': row.panel_version if re.fullmatch(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,4}', row.panel_version or '') else '',
        'capabilities': ', '.join(caps) if valid else '',
        'can_login': valid and row.status == models.ACTIVE and 'ticket' in caps,
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
    # The sealed text is read only for a server that waits for approval, to show its number.
    rows = models.Node.objects.defer('sealed').order_by('label', 'link_id')
    return httpProc(request, 'multiServer/nodes.html',
                    {'nodes': [summary(row) for row in rows], 'licensed': entitlement.allowed()}).render()


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
    if not links._is_link_id(link_id) or action not in ('refresh', 'confirm', 'pause', 'resume', 'revoke',
                                                         'forget'):
        raise Http404()
    if action == 'confirm':
        # Asks the server; it answers only when its administrator has approved the link there.
        result = links.confirm(link_id, admin.userName)
        if result.ok:
            messages.success(request, 'That server approved the link. It is connected.')
        else:
            messages.error(request, 'Not connected yet. Approve the link on that server with the number shown '
                           'here, then check again. ' + result.error)
        return redirect('multiServerNodes')
    if action == 'refresh':
        result = links.hello(link_id, admin.userName)
        if result.ok:
            messages.success(request, 'Node capabilities refreshed.')
        else:
            messages.error(request, result.error)
        return redirect('multiServerNodes')
    event = 'node_remove' if action == 'forget' else 'link_' + action
    if action in ('revoke', 'forget'):
        if request.POST.get('confirm') != action:
            audit.record(event, outcome='refused', link_id=link_id, actor=admin.userName, reason='not_allowed')
            messages.error(request, 'Confirm the action and enter your current password and verification code.')
            return redirect('multiServerNodes')
        reason = stepup.confirm(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''))
        if reason:
            audit.record(event, outcome='refused', link_id=link_id, actor=admin.userName, reason=reason)
            messages.error(request, stepup.message(reason))
            return redirect('multiServerNodes')
    actions = {'pause': links.pause, 'resume': links.resume, 'revoke': links.revoke, 'forget': links.remove}
    try:
        changed = actions[action](link_id, admin.userName)
    except Exception:
        audit.record(event, outcome='error', reason='internal', actor=admin.userName, link_id=link_id)
        changed = False
    if action == 'pause' and (changed or models.Node.objects.filter(pk=link_id, status=models.PAUSED).exists()):
        from multiServer.sso import end_paused
        if end_paused(link_id, admin.userName):
            messages.success(request, 'Paused on this controller. The node confirmed that its managed sessions ended.')
        else:
            messages.warning(request, 'Paused on this controller. The node has not confirmed session invalidation. '
                             'Retry while paused. Existing managed sessions expire within 30 minutes of login.')
        return redirect('multiServerNodes')
    if changed:
        messages.success(request, {'pause': 'Paused on this controller.', 'resume': 'Node resumed.',
                                   'revoke': 'The node confirmed revocation. Its controller record was removed.',
                                   'forget': 'Local record removed. Remote revocation is unconfirmed.'}[action])
    elif action == 'revoke':
        messages.error(request, 'Revocation was not confirmed. Check the node and retry if it is still listed.')
    else:
        messages.error(request, 'Action unavailable. Check the current node status and licence.')
    return redirect('multiServerNodes')


PAIRED = ('Paired. Now, on that server, open Multi-Server > Controllers and approve this controller with the '
          'number shown below. Then press "Check approval" here.')


@never_cache
@csrf_protect
@sensitive_post_parameters('password', 'code', 'pairing_code')
def add(request):
    """Add a server from its pairing code, in two steps.

    The first shows what the code says and connects to nothing. The second,
    with the password and a fresh verification code, pairs. The pairing code
    goes from the first form to the second in the page itself and is kept
    nowhere on this server.
    """
    from multiServer import pairing, stepup
    admin = administrator(request)
    if not admin:
        raise Http404()
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    step = request.POST.get('step', '')
    if step not in ('read', 'connect'):
        raise Http404()
    code = ''.join(request.POST.get('pairing_code', '').split())
    label = request.POST.get('label', '').strip()
    try:
        links.check_label(label)
        target = pairing.read_code(code)
    except (links.InvalidLabel, pairing.PairingError) as error:
        messages.error(request, str(error))  # a fixed text of links.py, pairing.py or transport.py
        return redirect('multiServerNodes')
    if step == 'read':
        from plogical.httpProc import httpProc
        return httpProc(request, 'multiServer/add.html', {
            'pairing_code': code, 'label': label, 'host': target.host, 'port': target.port,
            'identity': _groups(target.node_id), 'certificate': _groups(target.tls_pin)}).render()
    reason = stepup.confirm(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''))
    if reason:
        audit.record('pairing', outcome='refused', reason=reason, actor=admin.userName)
        messages.error(request, stepup.message(reason))
        return redirect('multiServerNodes')
    try:
        pairing.start(code, label, admin.userName)
    except pairing.PairingError as error:
        messages.error(request, str(error))
        return redirect('multiServerNodes')
    messages.success(request, PAIRED)
    return redirect('multiServerNodes')


def _groups(fingerprint):
    """A fingerprint in groups of four, as it is easier to compare by eye."""
    return ' '.join(fingerprint[start:start + 4] for start in range(0, len(fingerprint), 4))
