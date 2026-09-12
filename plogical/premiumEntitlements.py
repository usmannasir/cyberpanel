"""Check paid access before an interactive operation starts work."""
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect

from plogical.acl import ACLManager


def premium_entitlement_required(feature, *, label='Premium feature', flags=(), page_redirect=None):
    def decorate(operation):
        @wraps(operation)
        def checked(*args, **kwargs):
            try:
                status = ACLManager.CheckForPremFeature(feature)
                available = type(status) is int and status == 1
            except Exception:
                available = False
            if not available:
                if page_redirect:
                    return redirect(page_redirect)
                data = {flag: 0 for flag in flags}
                data.update(status=0, error_message=f'An active {label} entitlement is required.')
                return JsonResponse(data)
            return operation(*args, **kwargs)
        return checked
    return decorate
