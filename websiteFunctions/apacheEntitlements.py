"""Entitlement checks for Apache tools and optional backend creation."""
from functools import wraps
import re

from django.http import JsonResponse
from django.shortcuts import redirect

from plogical.acl import ACLManager


def apache_manager_available():
    try:
        status = ACLManager.CheckForPremFeature('all')
        return type(status) is int and status == 1
    except Exception:
        return False


def apache_entitlement_error(message='An active entitlement is required for Apache Manager.'):
    return JsonResponse({
        'status': 0, 'saveStatus': 0, 'configstatus': 0,
        'createWebSiteStatus': 0, 'installStatus': 0,
        'error_message': message,
    })


def normalize_apache_backend(value):
    if value is None or value == '':
        return 0
    if type(value) in (int, bool):
        return int(value)
    if isinstance(value, str) and re.fullmatch(r'[+-]?\d+', value.strip()):
        return int(value.strip())
    raise ValueError('Invalid Apache backend selection.')


def apache_backend_entitlement_error(data):
    try:
        requested = normalize_apache_backend((data or {}).get('apacheBackend', 0))
    except (AttributeError, TypeError, ValueError) as error:
        return apache_entitlement_error(str(error))
    if requested and not apache_manager_available():
        return apache_entitlement_error()
    return None


def apache_entitlement_required(page=False):
    def decorate(method):
        @wraps(method)
        def checked(*args, **kwargs):
            if not apache_manager_available():
                return redirect('pricing') if page else apache_entitlement_error()
            return method(*args, **kwargs)
        return checked
    return decorate
