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

An administrator without two-factor login sets it up here: the page shows the
key of a new set-up as a QR code, and one form takes a code from the app, the
password and the role. Nobody has to sign out. Wherever the password and a
fresh code were checked here, this session counts as a sign-in made with them,
as the sign-in page records it (sso.remember_login); the controller pages ask
for that (and offer the same check, action 'confirm', instead of a new sign-in).
"""
from django.contrib import messages
from django.db import DatabaseError
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from multiServer import audit, entitlement, keys, msctl, qr, stepup, switch, views

NAMES = {keys.OFF: 'Off', keys.CONTROLLER: 'Controller', keys.NODE: 'Managed server'}
CARD_ORDER = (keys.CONTROLLER, keys.NODE, keys.OFF)
CHANGED = 'This server is now: %s.'
TWO_FACTOR_ON = ('Two-factor login is on for your account. From now on you sign in to this panel with your '
                 'password and a code from your authenticator app.')
NOT_SET_UP = 'Two-factor login could not be set up for your account. Open this page again and start again.'
SIGNED_IN = 'Confirmed. You can open your servers from here now.'
# The session of the administrator who started a set-up here; only it may finish that set-up.
SETUP = 'ms_twofa_setup'
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
        action = request.POST.get('action', 'role')
        if action not in ACTIONS:
            raise Http404()
        return ACTIONS[action](request, admin)
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET', 'POST'])
    from plogical.httpProc import httpProc
    role = keys.role()
    enrolled = views.two_factor_enrolled(admin)
    context = {
        'role': role, 'role_name': NAMES[role], 'running': switch.active_role() == role,
        'enrolled': enrolled, 'licensed': entitlement.allowed(),
        # Shown as cards, the role most people come for first.
        'choices': [(value, NAMES[value]) for value in sorted(msctl.ROLES, key=CARD_ORDER.index)],
        # What the form starts with: a server that is off is most likely being made a controller.
        'suggested': keys.CONTROLLER if role == keys.OFF else role,
        'buy_url': entitlement.purchase_url(),
    }
    shown = None if enrolled or request.session.get(SETUP) != admin.pk else stepup.setup(admin, _label(admin))
    if shown is not None:
        key, address = shown
        size, runs = qr.runs(address)
        context.update(setup_key=' '.join(key[start:start + 4] for start in range(0, len(key), 4)),
                       qr_runs=runs, qr_view=size + 8)
    return httpProc(request, 'multiServer/role.html', context).render()


def _label(admin):
    """How the account is named in the authenticator app: the user and this server, which has several of these."""
    return '%s (%s)' % (admin.userName, entitlement.server_address() or 'CyberPanel')


def _change(request, admin):
    wanted = request.POST.get('role', '')
    if wanted not in msctl.ROLE_COMMANDS or not views.two_factor_enrolled(admin):
        raise Http404()
    reason = stepup.confirm(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''))
    if reason is not None:
        audit.record('role', outcome='refused', reason=reason, actor=admin.userName)
        messages.error(request, stepup.message(reason))
        return redirect('multiServerRole')
    _apply(request, admin, wanted)
    _signed_in(request, admin.pk)
    return redirect('multiServerRole')


def _apply(request, admin, wanted):
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


def _start_setup(request, admin):
    if views.two_factor_enrolled(admin):
        raise Http404()
    if stepup.start(admin.pk):
        request.session[SETUP] = admin.pk
    else:
        request.session.pop(SETUP, None)
        messages.error(request, NOT_SET_UP)
    return redirect('multiServerRole')


def _enrol(request, admin):
    wanted = request.POST.get('role', '')
    if (wanted not in msctl.ROLE_COMMANDS or views.two_factor_enrolled(admin)
            or request.session.get(SETUP) != admin.pk):
        raise Http404()
    reason = stepup.enrol(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''))
    if reason is not None:
        audit.record('two_factor', outcome='refused', reason=reason, actor=admin.userName)
        messages.error(request, stepup.message(reason))
        return redirect('multiServerRole')
    request.session.pop(SETUP, None)
    audit.record('two_factor', actor=admin.userName)
    messages.success(request, TWO_FACTOR_ON)
    if wanted != keys.role():
        _apply(request, admin, wanted)
    _signed_in(request, admin.pk)
    return redirect('multiServerRole')


def _confirm_sign_in(request, admin):
    """The controller pages' replacement for signing out and in again: the same two checks, here."""
    if not views.two_factor_enrolled(admin):
        raise Http404()
    reason = stepup.confirm(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''))
    if reason is not None:
        audit.record('sign_in', outcome='refused', reason=reason, actor=admin.userName)
        messages.error(request, stepup.message(reason))
    else:
        _signed_in(request, admin.pk)
        audit.record('sign_in', actor=admin.userName)
        messages.success(request, SIGNED_IN)
    return redirect('multiServerNodes' if keys.role() == keys.CONTROLLER else 'multiServerRole')


def _signed_in(request, admin_id):
    """Record a sign-in made with the password and a fresh code, as the sign-in page does after checking them."""
    from loginSystem.models import Administrator
    from multiServer import sso
    request.session.cycle_key()
    request.session.pop('ms_local_login', None)
    if keys.role() == keys.CONTROLLER and request.is_secure():
        sso.remember_login(request, Administrator.objects.get(pk=admin_id))


ACTIONS = {'role': _change, 'setup': _start_setup, 'enrol': _enrol, 'confirm': _confirm_sign_in}
