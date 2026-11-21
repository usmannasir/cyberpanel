"""A managed server and the controllers that may manage it: the Controllers page, and ending a link.

Whoever uses the page is a full administrator of this server, signed in here
with a second factor (nodes.administrator). A session that was opened through
a link never reaches it: such a session belongs to a controller, and this page
decides which controllers there are.
"""
import datetime
import re
import time

from django.contrib import messages
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from multiServer import addresses, audit, keys, links, models, msctl, nodes, pairing, stepup

MAX_LISTED = 100  # links shown, newest first

ALLOWED = ('Approved. That controller now manages this server. On the controller, press "Check approval" to '
           'finish.')
REJECTED = 'Rejected. That controller was not let in.'
ENDED = 'The link is ended. That controller can no longer manage this server.'
NOT_ENDED = ('The link could not be ended. Try again, or run "msctl.py revoke" as root on this server '
             '(see multiServer/msctl.py).')
UNCONFIRMED = 'Tick the box to confirm, and enter your current password and a verification code.'
OWN_ADDRESS = "A controller cannot reach this server at the address the panel has for it. "

_LINK = re.compile(r'[0-9a-f]{32}')
_STATES = {models.ACTIVE: 'Active', models.PAUSED: 'Paused', models.REVOKED: 'Ended', 'expired': 'Expired'}


def end(link_id, actor, raise_counter):
    """End the link of one controller on this managed server, for good.

    True when it was ended now, None when it had been ended before, False when
    there is no such link. Run as root (msctl.py), because one step is root's
    alone: `raise_counter` raises the revocation counter in the key directory
    and returns its new value.

    What is done, in this order: the revocation marker of the link is written
    (it alone stops the link from then on, and it outlasts a restored
    database); the panel sessions and login tickets that came through the link
    are removed; the row becomes REVOKED; the counter is raised; every other
    link that counted until now is moved on to the new value. The ended link
    keeps the old value, so nothing brings it back. One audit row is written.

    The rows of all links are locked while this runs. A request of another
    controller that arrives in that moment is refused once and passes when it
    is sent again, and a panel session that another controller had opened
    here ends and has to be opened again.
    """
    if type(link_id) is not str or _LINK.fullmatch(link_id) is None:
        raise ValueError('This is not a link.')
    from django.db import transaction
    from multiServer import sso
    live = (models.PENDING, models.ACTIVE, models.PAUSED)
    with transaction.atomic():
        found = dict((row.link_id, row) for row in models.Link.objects.select_for_update().order_by('link_id'))
        link = found.get(link_id)
        if link is None:
            return False
        if link.status not in live:
            # Closed before: rejected, never approved in time, or ended. The marker is there or is made up for.
            keys.mark_revoked(link_id)
            return None
        counter = keys.generation()
        if counter < 1:
            raise RuntimeError('The revocation counter cannot be read.')
        _catch_up(found.values(), counter, live)
        keys.mark_revoked(link_id)
        sso.clear(link)
        models.Link.objects.filter(pk=link_id).update(status=models.REVOKED, updated_at=int(time.time()))
        raised = raise_counter()
        if type(raised) is not int or raised != counter + 1:
            raise RuntimeError('The revocation counter was not raised by one.')
        models.Link.objects.exclude(pk=link_id).filter(generation=counter, status__in=live).update(generation=raised)
    audit.record('link_revoke', link_id=link_id, **(dict(actor=actor) if actor else {}))
    return True


def _catch_up(rows, counter, live):
    """Move on the links that an interrupted end() left one behind the counter.

    end() raises the counter in the key directory and then moves every other
    link on to it. If it stopped between the two (the database went away, the
    process was killed), the rows went back to the old value while the file
    kept the new one, and every link of this server is refused from then on.
    That state is recognised here, at the start of the next end(): no link
    counts at the counter, and links that are not ended sit exactly one behind
    it. Those are moved on. A link whose revocation marker is written stays
    behind, so nothing that was ended comes back.
    """
    if any(row.generation == counter for row in rows):
        return
    behind = [row.link_id for row in rows
              if row.status in live and row.generation == counter - 1 and not keys.revoked(row.link_id)]
    if behind:
        models.Link.objects.filter(pk__in=behind, generation=counter - 1, status__in=live).update(generation=counter)
        for row in rows:
            if row.link_id in behind:
                row.generation = counter


def _date(timestamp):
    try:
        return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc) if timestamp else None
    except (OverflowError, OSError, ValueError, TypeError):
        return None


def _names(admin_ids):
    """The user names of these administrators, for showing who allowed a controller."""
    from loginSystem.models import Administrator
    return dict(Administrator.objects.filter(pk__in=set(admin_ids)).values_list('pk', 'userName'))


def summary(link, now, counter, names):
    """One link as the page shows it. Nothing of a row is shown that does not have the form it was written in."""
    known = _LINK.fullmatch(link.link_id or '') is not None
    state = link.status if link.status in (models.ACTIVE, models.PAUSED, models.REVOKED) else 'unknown'
    if state in (models.ACTIVE, models.PAUSED):
        if not known or link.generation != counter or keys.revoked(link.link_id):
            state = models.REVOKED
        elif link.expires_at <= now:
            state = 'expired'
    return {
        'id': link.link_id if known else '',
        'short': link.link_id[:8] if known else '',
        'addresses': ', '.join(addresses.listed(link.allowed_ips)),
        'state': _STATES.get(state, 'Unknown'),
        # Also for a link whose ending did not finish: its marker is written, its row is not yet closed.
        'can_end': known and link.status in (models.ACTIVE, models.PAUSED),
        'since': _date(link.activated_at),
        'until': _date(link.expires_at) if state in (models.ACTIVE, models.PAUSED) else None,
        'by': names.get(link.admin_id, ''),
    }


def _page(request):
    from plogical.httpProc import httpProc
    now, counter = int(time.time()), keys.generation()
    waiting = pairing.pending(close=False)  # looking at the page writes nothing
    rows = list(models.Link.objects.exclude(status=models.PENDING).order_by('-created_at', 'link_id')[:MAX_LISTED])
    names = _names([row.admin_id for row in rows] + [asking.admin_id for asking in waiting])
    asked = [{'id': asking.link_id, 'short': asking.link_id[:8],
              'addresses': ', '.join(addresses.listed(asking.controller_ip)),
              'by': names.get(asking.admin_id, ''), 'at': _date(asking.created_at),
              'until': _date(asking.expires_at)} for asking in waiting]
    return httpProc(request, 'multiServer/controllers.html',
                    {'waiting': asked, 'links': [summary(row, now, counter, names) for row in rows],
                     'wrong_numbers': pairing.MAX_WRONG_NUMBERS}).render()


@never_cache
def index(request):
    if not nodes.administrator(request):
        raise Http404()
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    return _page(request)


@never_cache
@csrf_protect
@sensitive_post_parameters('password', 'code', 'number')
def control(request):
    admin = nodes.administrator(request)
    if not admin:
        raise Http404()
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    action = request.POST.get('action', '')
    pairing.pending()  # closes the requests that nobody approved in time
    if action == 'allow':
        return _allow(request, admin)
    link_id = request.POST.get('link_id', '')
    if action not in ('approve', 'reject', 'end') or not links._is_link_id(link_id):
        raise Http404()
    try:
        if action == 'approve':
            pairing.approve(link_id, admin.pk, re.sub('[ -]', '', request.POST.get('number', '')))
            messages.success(request, ALLOWED)
        elif action == 'reject':
            pairing.reject(link_id, admin.pk)
            messages.success(request, REJECTED)
        else:
            _end(request, admin, link_id)
    except pairing.PairingError as error:
        messages.error(request, str(error))  # one of the fixed texts of pairing.py
    return redirect('multiServerControllers')


def _confirmed(request, admin, event, **named):
    """Whether the password and a new code were given; a refusal is put on record and said."""
    reason = stepup.confirm(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''))
    if reason is None:
        return True
    audit.record(event, outcome='refused', reason=reason, actor=admin.userName, **named)
    messages.error(request, stepup.message(reason))
    return False


def _allow(request, admin):
    controller_ip = request.POST.get('controller_ip', '').strip()
    if addresses.entry(controller_ip) is None:
        # Said before the password and the code are looked at: a slip of the keyboard does not use a code up.
        messages.error(request, pairing.NOT_AN_ADDRESS)
        return redirect('multiServerControllers')
    if not _confirmed(request, admin, 'pairing_code'):
        return redirect('multiServerControllers')
    try:
        code = pairing.issue_code(admin.pk, controller_ip)
    except pairing.PairingError as error:
        messages.error(request, (OWN_ADDRESS if error.reason == 'not_allowed' else '') + str(error))
        return redirect('multiServerControllers')
    from plogical.httpProc import httpProc
    # Shown once, in the answer to this request, and kept nowhere on this server.
    return httpProc(request, 'multiServer/code.html',
                    {'pairing_code': code, 'minutes': pairing.CODE_LIFETIME // 60}).render()


def _end(request, admin, link_id):
    if request.POST.get('confirm') != 'end':
        audit.record('link_revoke', outcome='refused', reason='not_allowed', link_id=link_id, actor=admin.userName)
        messages.error(request, UNCONFIRMED)
        return
    link = models.Link.objects.filter(pk=link_id).first()
    if link is None or not links._is_link_id(link.link_id):
        audit.record('link_revoke', outcome='refused', reason='link', link_id=link_id, actor=admin.userName)
        messages.error(request, 'There is no such link.')
        return
    if not _confirmed(request, admin, 'link_revoke', link_id=link_id):
        return
    from plogical.processUtilities import ProcessUtilities
    # Root ends it (msctl.py): the id is the row's own, and the number is the signed-in administrator's.
    ProcessUtilities.executioner(msctl.revoke_command(link.link_id, admin.pk))
    if models.Link.objects.filter(pk=link.link_id, status=models.REVOKED).exists() and keys.revoked(link.link_id):
        messages.success(request, ENDED)
    else:
        audit.record('link_revoke', outcome='error', reason='internal', link_id=link.link_id, actor=admin.userName)
        messages.error(request, NOT_ENDED)
