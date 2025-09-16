# -*- coding: utf-8 -*-
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