# -*- coding: utf-8 -*-
"""
Plugin Access Control
Checks if user has access to paid plugins
"""

from .patreon_verifier import PatreonVerifier
import logging

def check_plugin_access(request, plugin_name, plugin_meta=None):
    """
    Check if user has access to a plugin
    
    Args:
        request: Django request object
        plugin_name: Name of the plugin
        plugin_meta: Plugin metadata dict (optional, will be loaded if not provided)
        
    Returns:
        dict: {
            'has_access': bool,
            'is_paid': bool,
            'message': str,
            'patreon_url': str or None
        }
    """
    # Default response for free plugins
    default_response = {
        'has_access': True,
        'is_paid': False,
        'message': 'Access granted',
        'patreon_url': None
    }
    
    # If plugin_meta not provided, try to load it
    if plugin_meta is None:
        plugin_meta = _load_plugin_meta(plugin_name)
    
    # Check if plugin is paid
    if not plugin_meta or not plugin_meta.get('is_paid', False):
        return default_response
    
    # Plugin is paid - check Patreon membership
    if not request.user or not request.user.is_authenticated:
        return {
            'has_access': False,
            'is_paid': True,
            'message': 'Please log in to access this plugin',
            'patreon_url': plugin_meta.get('patreon_url')
        }
    
    # Get user email
    user_email = getattr(request.user, 'email', None)
    if not user_email:
        # Try to get from username or other fields
        user_email = getattr(request.user, 'username', '')
    
    if not user_email:
        return {
            'has_access': False,
            'is_paid': True,
            'message': 'Unable to verify user identity',
            'patreon_url': plugin_meta.get('patreon_url')
        }
    
    # Check Patreon membership
    verifier = PatreonVerifier()
    has_membership = verifier.check_membership_cached(user_email)
    
    if has_membership:
        return {
            'has_access': True,
            'is_paid': True,
            'message': 'Access granted',
            'patreon_url': None
        }
    else:
        return {
            'has_access': False,
            'is_paid': True,
            'message': f'This plugin requires a Patreon subscription to "{plugin_meta.get("patreon_tier", "CyberPanel Paid Plugin")}"',
            'patreon_url': plugin_meta.get('patreon_url', 'https://www.patreon.com/c/newstargeted/membership')
        }

def _load_plugin_meta(plugin_name):
    """
    Load plugin metadata from meta.xml
    
    Args:
        plugin_name: Name of the plugin
        
    Returns:
        dict: Plugin metadata or None
    """
    import os
    from xml.etree import ElementTree
    
    installed_path = f'/usr/local/CyberCP/{plugin_name}/meta.xml'
    source_path = f'/home/cyberpanel/plugins/{plugin_name}/meta.xml'
    
    meta_path = None
    if os.path.exists(installed_path):
        meta_path = installed_path
    elif os.path.exists(source_path):
        meta_path = source_path
    
    if not meta_path:
        return None
    
    try:
        tree = ElementTree.parse(meta_path)
        root = tree.getroot()
        
        # Extract paid plugin information
        paid_elem = root.find('paid')
        patreon_tier_elem = root.find('patreon_tier')
        patreon_url_elem = root.find('patreon_url')
        
        is_paid = False
        if paid_elem is not None and paid_elem.text and paid_elem.text.lower() == 'true':
            is_paid = True
        
        return {
            'is_paid': is_paid,
            'patreon_tier': patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin',
            'patreon_url': patreon_url_elem.text if patreon_url_elem is not None else 'https://www.patreon.com/c/newstargeted/membership'
        }
    except Exception as e:
        logging.writeToFile(f"Error loading plugin meta for {plugin_name}: {str(e)}")
        return None
