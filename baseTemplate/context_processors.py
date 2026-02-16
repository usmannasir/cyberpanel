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