"""Who may use the AI Scanner, and which scans a signed-in user may see."""
import functools

from django.http import JsonResponse

from plogical.acl import ACLManager


def scanner_allowed(currentACL):
    """An administrator may always use the scanner; anyone else unless their ACL switches it off.

    ACLs made before the switch existed do not carry it, so its absence means allowed.
    """
    if currentACL.get('admin') == 1:
        return True
    return currentACL.get('aiScannerAccess', 1) != 0


def scanner_view(page=False):
    """Let a view run only for a signed-in user who may use the scanner.

    A page view sends anyone else to the login or the error page; every other
    view answers in JSON.
    """
    def decorate(view):
        @functools.wraps(view)
        def checked(request, *arguments, **options):
            try:
                userID = request.session['userID']
            except KeyError:
                if page:
                    from django.shortcuts import redirect
                    from loginSystem.views import loadLoginPage
                    return redirect(loadLoginPage)
                return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
            if not scanner_allowed(ACLManager.loadedACL(userID)):
                if page:
                    return ACLManager.loadError()
                return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
            return view(request, *arguments, **options)
        return checked
    return decorate


def may_see_scan(userID, scan):
    """A scan is shown to an administrator, to its owner and to the owner's reseller."""
    currentACL = ACLManager.loadedACL(userID)
    if currentACL['admin'] == 1:
        return True
    return scan.admin in ACLManager.loadUserObjects(userID)
