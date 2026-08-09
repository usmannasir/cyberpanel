# -*- coding: utf-8 -*-
from cyberpanel_version import BUILD, FULL_VERSION, VERSION

def version_context(request):
    """Add version information to all templates"""
    return {
        'CYBERPANEL_VERSION': VERSION,
        'CYBERPANEL_BUILD': BUILD,
        'CYBERPANEL_FULL_VERSION': FULL_VERSION
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
