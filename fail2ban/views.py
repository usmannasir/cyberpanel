# -*- coding: utf-8 -*-
"""HTML page views for Fail2ban plugin."""
from django.shortcuts import render
from django.http import HttpResponse

from .utils import Fail2banManager
from .panel_auth import cyberpanel_login_and_admin, _html_plugin_error


@cyberpanel_login_and_admin
def fail2ban_plugin(request):
    """Main plugin page: single inline-tab UI (no separate panels)."""
    return unified_settings(request)


@cyberpanel_login_and_admin
def settings(request):
    """Alias for pluginHolder settings proxy + clean /settings/ URL."""
    return unified_settings(request)


@cyberpanel_login_and_admin
def plugin_card(request):
    """Plugin card view with buttons"""
    try:
        context = {
            'title': 'Settings Plugin Card'
        }
        return render(request, 'fail2ban_plugin/plugin_card.html', context)
    except Exception as e:
        return _html_plugin_error(request, e, 'Plugin card')


@cyberpanel_login_and_admin
def jails_standalone(request):
    """Legacy URL: open the unified page on the jails tab."""
    from django.shortcuts import redirect
    return redirect('/plugins/fail2ban/#jails')


@cyberpanel_login_and_admin
def banned_ips_standalone(request):
    """Legacy URL: open the unified page on the banned tab."""
    from django.shortcuts import redirect
    return redirect('/plugins/fail2ban/#banned')


@cyberpanel_login_and_admin
def whitelist_standalone(request):
    """Legacy URL: open the unified page on the whitelist tab."""
    from django.shortcuts import redirect
    return redirect('/plugins/fail2ban/#whitelist')


@cyberpanel_login_and_admin
def blacklist_standalone(request):
    """Legacy URL: open the unified page on the blacklist tab."""
    from django.shortcuts import redirect
    return redirect('/plugins/fail2ban/#blacklist')


@cyberpanel_login_and_admin
def logs_standalone(request):
    """Legacy URL: open the unified page on the logs tab."""
    from django.shortcuts import redirect
    return redirect('/plugins/fail2ban/#logs')


@cyberpanel_login_and_admin
def statistics_standalone(request):
    """Legacy URL: open the unified page on the statistics tab."""
    from django.shortcuts import redirect
    return redirect('/plugins/fail2ban/#statistics')


@cyberpanel_login_and_admin
def settings_standalone(request):
    """Legacy /settings/ path: same single-page UI."""
    return unified_settings(request)


@cyberpanel_login_and_admin
def unified_settings(request):
    """Unified settings view with tabs"""
    try:
        active_tab = (request.GET.get('tab') or 'overview').strip().lower()
        if active_tab in ('banned-ips', 'banned_ips'):
            active_tab = 'banned'
        if active_tab == 'alerts':
            active_tab = 'overview'

        if active_tab == 'overview':
            path = request.path_info
            if 'jails' in path:
                active_tab = 'jails'
            elif 'banned-ips' in path:
                active_tab = 'banned'
            elif 'whitelist' in path:
                active_tab = 'whitelist'
            elif 'blacklist' in path:
                active_tab = 'blacklist'
            elif 'logs' in path:
                active_tab = 'logs'
            elif 'statistics' in path:
                active_tab = 'statistics'
            elif 'settings' in path:
                active_tab = 'settings'

        manager = Fail2banManager()
        status = manager.get_status()

        try:
            from .models import Fail2banAutoBanConfig
            autoban = Fail2banAutoBanConfig.get_config()
            autoban_enabled = bool(autoban.enabled)
        except Exception:
            autoban_enabled = False

        context = {
            'title': 'Settings',
            'active_tab': active_tab,
            'status': status,
            'plugin_name': 'Fail2ban Security Manager',
            'version': '1.2.0',
            'plugin_status': 'Active',
            'autoban_enabled': autoban_enabled,
            'tabs': [
                {'id': 'overview', 'name': 'Dashboard', 'icon': 'overview'},
                {'id': 'jails', 'name': 'Manage Jails', 'icon': 'jails'},
                {'id': 'banned', 'name': 'Banned IPs', 'icon': 'banned'},
                {'id': 'whitelist', 'name': 'Whitelist', 'icon': 'whitelist'},
                {'id': 'blacklist', 'name': 'Blacklist', 'icon': 'blacklist'},
                {'id': 'logs', 'name': 'Security Logs', 'icon': 'logs'},
                {'id': 'statistics', 'name': 'Statistics', 'icon': 'stats'},
                {'id': 'settings', 'name': 'Settings', 'icon': 'settings'},
            ]
        }
        return render(request, 'fail2ban_plugin/settings_modern.html', context)
    except Exception as e:
        return _html_plugin_error(request, e, 'Unified settings')


@cyberpanel_login_and_admin
def dashboard(request):
    """Legacy dashboard view - redirects to unified settings"""
    return unified_settings(request)


@cyberpanel_login_and_admin
def jails_management(request):
    """Jails management page"""
    context = {
        'title': 'Jails Management',
        'active_tab': 'jails'
    }
    return render(request, 'fail2ban_plugin/jails.html', context)


@cyberpanel_login_and_admin
def banned_ips_management(request):
    """Banned IPs management page"""
    context = {
        'title': 'Banned IPs Management',
        'active_tab': 'banned_ips'
    }
    return render(request, 'fail2ban_plugin/banned_ips.html', context)


@cyberpanel_login_and_admin
def whitelist_management(request):
    """Whitelist management page"""
    context = {
        'title': 'Whitelist Management',
        'active_tab': 'whitelist'
    }
    return render(request, 'fail2ban_plugin/whitelist.html', context)


@cyberpanel_login_and_admin
def blacklist_management(request):
    """Blacklist management page"""
    context = {
        'title': 'Blacklist Management',
        'active_tab': 'blacklist'
    }
    return render(request, 'fail2ban_plugin/blacklist.html', context)


@cyberpanel_login_and_admin
def settings_management(request):
    """Settings management page"""
    context = {
        'title': 'Settings Management',
        'active_tab': 'settings'
    }
    return render(request, 'fail2ban_plugin/settings.html', context)


@cyberpanel_login_and_admin
def logs_view(request):
    """Logs view page"""
    context = {
        'title': 'Security Logs',
        'active_tab': 'logs'
    }
    return render(request, 'fail2ban_plugin/logs.html', context)


@cyberpanel_login_and_admin
def statistics_view(request):
    """Statistics view page"""
    context = {
        'title': 'Security Statistics',
        'active_tab': 'statistics'
    }
    return render(request, 'fail2ban_plugin/statistics.html', context)

# Alias for CyberPanel plugin_settings_proxy (/plugins/<name>/settings/)
settings = unified_settings
