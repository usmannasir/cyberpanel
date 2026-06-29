# -*- coding: utf-8 -*-
import os
import time

from .views import VERSION, BUILD

def version_context(request):
    """Add version information to all templates"""
    return {
        'CYBERPANEL_VERSION': VERSION,
        'CYBERPANEL_BUILD': BUILD,
        'CYBERPANEL_FULL_VERSION': f"{VERSION}.{BUILD}"
    }

def cosmetic_context(request):
    """Add cosmetic data (custom CSS) to all templates"""
    try:
        from .models import CyberPanelCosmetic
        cosmetic = CyberPanelCosmetic.objects.get(pk=1)
        return {
            'cosmetic': cosmetic
        }
    except:
        from .models import CyberPanelCosmetic
        cosmetic = CyberPanelCosmetic()
        cosmetic.save()
        return {
            'cosmetic': cosmetic
        }

def notification_preferences_context(request):
    """Add user notification preferences to all templates"""
    try:
        if 'userID' in request.session:
            from .models import UserNotificationPreferences
            from loginSystem.models import Administrator
            user = Administrator.objects.get(pk=request.session['userID'])
            try:
                preferences = UserNotificationPreferences.objects.get(user=user)
                return {
                    'backup_notification_dismissed': preferences.backup_notification_dismissed,
                    'ai_scanner_notification_dismissed': preferences.ai_scanner_notification_dismissed
                }
            except UserNotificationPreferences.DoesNotExist:
                return {
                    'backup_notification_dismissed': False,
                    'ai_scanner_notification_dismissed': False
                }
    except:
        pass
    
    return {
        'backup_notification_dismissed': False,
        'ai_scanner_notification_dismissed': False
    }

def firewall_static_context(request):
    """Expose a cache-busting token for firewall static assets (bumps when firewall.js changes)."""
    try:
        from django.conf import settings
        base = settings.BASE_DIR
        # Check both app static and repo static so version updates when either is updated
        paths = [
            os.path.join(base, 'firewall', 'static', 'firewall', 'firewall.js'),
            os.path.join(base, 'static', 'firewall', 'firewall.js'),
            os.path.join(base, 'public', 'static', 'firewall', 'firewall.js'),
        ]
        version = 0
        for p in paths:
            try:
                version = max(version, int(os.path.getmtime(p)))
            except (OSError, TypeError):
                pass
        if version <= 0:
            version = int(time.time())
    except (OSError, AttributeError):
        version = int(time.time())
    return {
        'FIREWALL_STATIC_VERSION': version
    }


def dns_static_context(request):
    """Cache-busting for DNS static assets (bumps when dns.js changes). Avoids stale JS/layout."""
    try:
        from django.conf import settings
        base = settings.BASE_DIR
        paths = [
            os.path.join(base, 'dns', 'static', 'dns', 'dns.js'),
            os.path.join(base, 'static', 'dns', 'dns.js'),
            os.path.join(base, 'public', 'static', 'dns', 'dns.js'),
        ]
        version = 0
        for p in paths:
            try:
                version = max(version, int(os.path.getmtime(p)))
            except (OSError, TypeError):
                pass
        if version <= 0:
            version = int(time.time())
    except (OSError, AttributeError):
        version = int(time.time())
    return {
        'DNS_STATIC_VERSION': version
    }


def plugin_sidebar_context(request):
    """
    Sidebar Plugins menu: Installed / Plugin Store (ACL), Limited phpMyAdmin link
    for admins, plugin managers, or cpuser grantees; grant-only users see LPMA only.
    """
    defaults = {
        'lpma_plugin_installed': False,
        'lpma_has_cpuser_grant': False,
        'show_plugin_management_links': False,
        'show_lpma_sidebar_link': False,
        'show_plugins_menu': False,
        'grant_only_lpma_sidebar': False,
        'plugin_sidebar_extra_links': [],
        'lpma_sidebar_url': '/plugins/limitedPhpmyAdmin/',
    }
    try:
        if 'userID' not in request.session:
            return defaults
        uid = request.session['userID']
        from plogical.acl import ACLManager

        acl = ACLManager.loadedACL(uid)
        admin = bool(acl.get('admin'))
        # Granular plugin permissions (legacy managePlugins implies all three;
        # use/install imply view). These derived flags come from loadedACL.
        can_view_plugins = admin or bool(acl.get('canViewPlugins'))
        can_use_plugins = admin or bool(acl.get('canUsePlugins'))
        can_install_plugins = admin or bool(acl.get('canInstallPlugins'))
        manage_plugins = can_view_plugins
        # Menu visibility follows the view permission (the baseline to reach plugins).
        show_plugin_management_links = can_view_plugins

        lpma_plugin_installed = os.path.isdir('/usr/local/CyberCP/limitedPhpmyAdmin')

        lpma_has_cpuser_grant = False
        if lpma_plugin_installed:
            try:
                from django.apps import apps

                if apps.is_installed('limitedPhpmyAdmin'):
                    from limitedPhpmyAdmin.models import LimitedPhpmyAdminGrant

                    lpma_has_cpuser_grant = LimitedPhpmyAdminGrant.objects.filter(
                        enabled=True,
                        subject_type='cpuser',
                        administrator_id=uid,
                    ).exists()
            except Exception:
                lpma_has_cpuser_grant = False

        show_lpma_sidebar_link = lpma_plugin_installed and (
            show_plugin_management_links or lpma_has_cpuser_grant
        )
        show_plugins_menu = show_plugin_management_links or (
            lpma_has_cpuser_grant and lpma_plugin_installed
        )
        grant_only_lpma_sidebar = (
            lpma_has_cpuser_grant and lpma_plugin_installed and not show_plugin_management_links
        )

        extra = []
        if show_lpma_sidebar_link:
            extra.append(
                {
                    'url': '/plugins/limitedPhpmyAdmin/',
                    'label_key': 'limited_phpmyadmin_sidebar',
                }
            )

        defaults.update(
            {
                'lpma_plugin_installed': lpma_plugin_installed,
                'lpma_has_cpuser_grant': lpma_has_cpuser_grant,
                'show_plugin_management_links': show_plugin_management_links,
                'show_lpma_sidebar_link': show_lpma_sidebar_link,
                'show_plugins_menu': show_plugins_menu,
                'grant_only_lpma_sidebar': grant_only_lpma_sidebar,
                'plugin_sidebar_extra_links': extra,
                'lpma_sidebar_url': '/plugins/limitedPhpmyAdmin/',
                'canViewPlugins': 1 if can_view_plugins else 0,
                'canUsePlugins': 1 if can_use_plugins else 0,
                'canInstallPlugins': 1 if can_install_plugins else 0,
            }
        )
        return defaults
    except Exception:
        return defaults
