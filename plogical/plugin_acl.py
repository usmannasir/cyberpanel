# -*- coding: utf-8 -*-
"""Shared ACL checks for CyberPanel plugin management (core + store plugins).

Plugin access is split into three independent permissions:
    - view    : see the installed plugins list / plugin UI
    - use     : open and use an installed plugin's settings/features
    - install : install, upgrade, enable/disable and remove plugins

The legacy ``managePlugins`` flag implies all three (handled in
``ACLManager.loadedACL`` via the derived ``canViewPlugins`` / ``canUsePlugins``
/ ``canInstallPlugins`` keys). Use/install both imply view.
"""
from functools import wraps
from django.http import JsonResponse


def _loaded_acl(request):
    """Return loadedACL dict for the session user, or None if not logged in."""
    try:
        user_id = request.session['userID']
    except KeyError:
        return None
    try:
        from plogical.acl import ACLManager
        return ACLManager.loadedACL(user_id)
    except BaseException:
        return None


def _acl_allows(request, derived_key):
    """True if session user is full admin or has the given derived can* flag."""
    acl = _loaded_acl(request)
    if not acl:
        return False
    try:
        if acl.get('admin') == 1:
            return True
        return int(acl.get(derived_key, 0) or 0) == 1
    except (TypeError, ValueError):
        return False


def user_can_view_plugins(request):
    """True if user may view the plugins list / plugin UI."""
    return _acl_allows(request, 'canViewPlugins')


def user_can_use_plugins(request):
    """True if user may open and use a plugin's settings/features."""
    return _acl_allows(request, 'canUsePlugins')


def user_can_install_plugins(request):
    """True if user may install/upgrade/enable/disable/remove plugins."""
    return _acl_allows(request, 'canInstallPlugins')


# Backward-compatible alias. External/store plugins import this name; keep it
# pointing at the "install/manage" capability (the strongest plugin right).
def user_can_manage_plugins(request):
    """Legacy alias: True if user may install/manage plugins."""
    return user_can_install_plugins(request)


def deny_plugin_json_response(request, action='manage'):
    """401 if no session, else 403 JSON for a plugin action ('view'/'use'/'install'/'manage')."""
    try:
        request.session['userID']
    except KeyError:
        return JsonResponse({
            'success': False,
            'error_message': 'Authentication required.',
            'error': 'Authentication required.',
        }, status=401)

    messages = {
        'view': 'You are not authorized to view plugins.',
        'use': 'You are not authorized to use plugins.',
        'install': 'You are not authorized to install or manage plugins.',
        'manage': 'You are not authorized to manage plugins.',
    }
    msg = messages.get(action, messages['manage'])
    return JsonResponse({
        'success': False,
        'error_message': msg,
        'error': msg,
    }, status=403)


# Backward-compatible alias for the previous single-permission deny helper.
def deny_plugin_manage_json_response(request):
    """Legacy alias for deny_plugin_json_response(request, 'install')."""
    return deny_plugin_json_response(request, 'install')


def require_view_plugins_api(view_func):
    """Decorator: JSON 401/403 if user cannot view plugins."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_can_view_plugins(request):
            return deny_plugin_json_response(request, 'view')
        return view_func(request, *args, **kwargs)
    return _wrapped


def require_use_plugins_api(view_func):
    """Decorator: JSON 401/403 if user cannot use plugins."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_can_use_plugins(request):
            return deny_plugin_json_response(request, 'use')
        return view_func(request, *args, **kwargs)
    return _wrapped


def require_install_plugins_api(view_func):
    """Decorator: JSON 401/403 if user cannot install/manage plugins."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_can_install_plugins(request):
            return deny_plugin_json_response(request, 'install')
        return view_func(request, *args, **kwargs)
    return _wrapped


# Legacy decorator alias.
def require_manage_plugins_api(view_func):
    """Legacy alias of require_install_plugins_api."""
    return require_install_plugins_api(view_func)
