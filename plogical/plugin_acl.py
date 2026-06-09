# -*- coding: utf-8 -*-
"""Shared ACL checks for CyberPanel plugin management (core + store plugins)."""
from functools import wraps
from django.http import JsonResponse


def user_can_manage_plugins(request):
    """True if session user is full admin or has managePlugins ACL."""
    try:
        user_id = request.session['userID']
    except KeyError:
        return False
    try:
        from plogical.acl import ACLManager
        acl = ACLManager.loadedACL(user_id)
        if acl.get('admin') == 1:
            return True
        try:
            return int(acl.get('managePlugins', 0) or 0) == 1
        except (TypeError, ValueError):
            return False
    except BaseException:
        return False


def deny_plugin_manage_json_response(request):
    """401 if no session, else 403 JSON for plugin management APIs."""
    try:
        request.session['userID']
    except KeyError:
        return JsonResponse({
            'success': False,
            'error_message': 'Authentication required.',
            'error': 'Authentication required.',
        }, status=401)
    return JsonResponse({
        'success': False,
        'error_message': 'You are not authorized to manage plugins.',
        'error': 'You are not authorized to manage plugins.',
    }, status=403)


def require_manage_plugins_api(view_func):
    """Decorator: JSON 401/403 if user cannot manage plugins (use after login/session check)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        return view_func(request, *args, **kwargs)
    return _wrapped
