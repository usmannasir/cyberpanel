"""Multi-Server Manager pages and calls.

Every view is wrapped by serves(), so with the feature off each address under
/multiserver/ answers exactly like an address that does not exist. Nothing but
Django and the role switch is imported when this module loads: it is part of the
panel's URL table and must never be the reason the panel cannot start.
"""
import functools

from django.http import Http404, JsonResponse

from multiServer import keys, switch


def serves(*roles):
    """Let a view answer only on a server whose role is one of `roles`.

    The view receives that role as its second argument; it is read once per
    request. For any other server the address does not exist.
    """
    if not roles or any(role not in (keys.CONTROLLER, keys.NODE) for role in roles):
        raise ValueError('A view serves the controller, a managed server, or both.')

    def wrap(view):
        @functools.wraps(view)
        def guarded(request, *args, **kwargs):
            role = switch.active_role()
            if role not in roles:
                raise Http404()
            return view(request, role, *args, **kwargs)
        guarded.serves = roles
        return guarded
    return wrap


def active_full_administrator(user_id):
    """The administrator with this id if it is an active full administrator, else None. Never raises."""
    try:
        if type(user_id) is not int:
            return None
        from loginSystem.models import Administrator
        from plogical.acl import ACLManager
        administrator = Administrator.objects.get(pk=user_id)
        full = ACLManager.loadedACL(user_id).get('admin')
        if administrator.state != 'ACTIVE' or type(full) is not int or full != 1:
            return None
        return administrator
    except Exception:
        return None


def full_administrator(request):
    """The signed-in administrator if it is an active full administrator, else None. Never raises."""
    try:
        return active_full_administrator(request.session.get('userID'))
    except Exception:
        return None


@serves(keys.CONTROLLER, keys.NODE)
def status(request, role):
    """This server's role and, on a controller, whether its licence is in order."""
    if request.method != 'GET' or full_administrator(request) is None:
        raise Http404()
    licensed = None
    if role == keys.CONTROLLER:
        from multiServer import entitlement
        licensed = entitlement.allowed()
    response = JsonResponse({'role': role, 'licensed': licensed})
    response['Cache-Control'] = 'no-store'
    return response
