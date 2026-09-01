# -*- coding: utf-8 -*-
"""CyberPanel session + admin ACL and safe error responses for Fail2ban plugin."""
import uuid
import logging as pylogging
from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from loginSystem.models import Administrator
from plogical.acl import ACLManager

logger = pylogging.getLogger('fail2ban_plugin')


def _fail2ban_log_exception(request, exc, error_id):
    logger.error(
        'fail2ban_plugin error_id=%s path=%s: %s',
        error_id,
        getattr(request, 'path', ''),
        str(exc),
        exc_info=True,
    )


def json_server_error(request, exc=None, status=500):
    """Generic JSON error; log details server-side only."""
    error_id = str(uuid.uuid4())[:12]
    if exc is not None:
        _fail2ban_log_exception(request, exc, error_id)
    return JsonResponse(
        {'success': False, 'error': 'Internal server error', 'error_id': error_id},
        status=status,
    )


def cyberpanel_login_and_admin(view_func):
    """Require CyberPanel session userID and ACL admin flag (matches other plugins)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        path = request.path or ''
        is_api = '/api/' in path
        try:
            uid = request.session['userID']
        except KeyError:
            if is_api:
                return JsonResponse(
                    {
                        'success': False,
                        'error': 'Authentication required',
                        'error_message': 'This request need session.',
                        'errorMessage': 'This request need session.',
                        'login_required': True,
                    },
                    status=401,
                )
            from loginSystem.login_return import redirect_to_login
            return redirect_to_login(request)
        try:
            acl = ACLManager.loadedACL(uid)
        except Exception:
            acl = {}
        if acl.get('admin') != 1:
            if is_api:
                return JsonResponse(
                    {'success': False, 'error': 'Admin access required'},
                    status=403,
                )
            return HttpResponse(
                '<div style="padding:20px;font-family:sans-serif">403 Forbidden: admin access required for the Fail2ban plugin.</div>',
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


def fail2ban_api(view_func):
    """
    JSON API decorator: CSRF-exempt (CyberPanel plugin pattern) + admin session.
    Session auth remains required; CSRF is redundant for same-origin panel XHR.
    """
    return csrf_exempt(cyberpanel_login_and_admin(view_func))


def _django_user_for_fail2ban_settings(request):
    """Map CyberPanel Administrator to a Django User for Fail2banSettings OneToOne."""
    admin = Administrator.objects.get(pk=int(request.session['userID']))
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username=admin.userName,
        defaults={'email': (getattr(admin, 'email', None) or '')[:254]},
    )
    return user


def _html_plugin_error(request, exc, label='Plugin'):
    error_id = str(uuid.uuid4())[:12]
    _fail2ban_log_exception(request, exc, error_id)
    return HttpResponse(
        '<div>%s error (reference: %s)</div>' % (label, error_id),
        status=500,
    )
