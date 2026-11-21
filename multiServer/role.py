"""The page where a full administrator gives this server its Multi-Server role.

It is the one Multi-Server page that is there while the feature is off. The
role itself is a root-owned file, and the panel does not write it: the page
asks the panel's root helper to run msctl.py with one of three fixed command
lines (msctl.ROLE_COMMANDS). Which of the three is the only thing a request
decides, and it decides it by naming one of the three roles: nothing a visitor
types becomes part of a command.

Seeing the page takes a full administrator in a session of their own on this
server. Changing the role also takes two-factor login on that account, and the
password with a fresh code again (stepup.py).
"""
from django.contrib import messages
from django.db import DatabaseError
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from multiServer import audit, keys, msctl, stepup, switch, views

NAMES = {keys.OFF: 'Off', keys.CONTROLLER: 'Controller', keys.NODE: 'Managed server'}
CHANGED = 'This server is now: %s.'
NOT_CHANGED = ('The role was not changed. Run "msctl.py status" as root on this server to see why '
               '(multiServer/msctl.py).')
# What msctl.py says when it refuses; shown as it is, anything else it says is not shown.
REFUSALS = (msctl.HAS_SERVERS, msctl.HAS_CONTROLLERS, msctl.CANNOT_CHECK, msctl.BUSY)


def administrator(request):
    """The signed-in full administrator in a session of their own on this server, else None.

    A session that a controller opened through a link is not one, and neither
    is a request that carries a link's headers.
    """
    admin = views.full_administrator(request)
    if admin is None or request.session.get('ms_managed') \
            or any(name.startswith('HTTP_X_CPMS_') for name in request.META):
        return None
    from multiServer import models
    try:
        if models.LinkSession.objects.filter(pk=request.session.session_key).exists():
            return None
    except DatabaseError:
        # Without its tables the feature is off and no session came through a link, except on a managed
        # server, the one place where such sessions are: there, what cannot be told is refused.
        if keys.role() == keys.NODE:
            return None
    return admin


@never_cache
@csrf_protect
@sensitive_post_parameters('password', 'code')
def page(request):
    admin = administrator(request)
    if admin is None:
        raise Http404()
    if request.method == 'POST':
        return _change(request, admin)
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET', 'POST'])
    from plogical.httpProc import httpProc
    role = keys.role()
    return httpProc(request, 'multiServer/role.html', {
        'role': role, 'role_name': NAMES[role], 'running': switch.active_role() == role,
        'enrolled': views.two_factor_enrolled(admin),
        'choices': [(value, NAMES[value]) for value in msctl.ROLES],
    }).render()


def _change(request, admin):
    wanted = request.POST.get('role', '')
    if wanted not in msctl.ROLE_COMMANDS or not views.two_factor_enrolled(admin):
        raise Http404()
    reason = stepup.confirm(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''))
    if reason is not None:
        audit.record('role', outcome='refused', reason=reason, actor=admin.userName)
        messages.error(request, stepup.message(reason))
        return redirect('multiServerRole')
    from plogical.processUtilities import ProcessUtilities
    answer = ProcessUtilities.outputExecutioner(msctl.ROLE_COMMANDS[wanted], retRequired=True)
    if keys.role() == wanted:
        audit.record('role', actor=admin.userName)
        messages.success(request, CHANGED % NAMES[wanted])
    else:
        said = answer[1].strip() if type(answer) is tuple and type(answer[1]) is str else ''
        refused = said in REFUSALS
        audit.record('role', outcome='refused' if refused else 'error',
                     reason='not_allowed' if refused else 'internal', actor=admin.userName)
        messages.error(request, said if refused else NOT_CHANGED)
    return redirect('multiServerRole')
