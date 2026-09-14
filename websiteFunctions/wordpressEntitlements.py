"""Enforce the WordPress entitlement before page or manager work begins."""
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect

from plogical.acl import ACLManager


def wordpress_manager_available():
    try:
        status = ACLManager.CheckForPremFeature('wp-manager')
        return type(status) is int and status == 1
    except Exception:
        return False


def wordpress_entitlement_required(page=False):
    def decorate(method):
        @wraps(method)
        def checked(*args, **kwargs):
            if not wordpress_manager_available():
                if page:
                    return redirect('pricing')
                # Existing AJAX and direct API callers use these numeric fields.
                # Denial must never look like a started installer or worker.
                return JsonResponse({
                    'status': 0,
                    'installStatus': 0,
                    'createWebSiteStatus': 0,
                    'fetchStatus': 0,
                    'error_message': 'An active WordPress Manager entitlement is required.',
                })
            return method(*args, **kwargs)
        return checked
    return decorate
