# -*- coding: utf-8 -*-
"""
Plugin Access Control
Checks if user has access to paid plugins
"""

from .patreon_verifier import PatreonVerifier
import hashlib
from django.db import connection
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


def _normalize_identity(value):
    if not value:
        return ''
    return str(value).strip().lower()


def _hash_activation_key(raw_key):
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def _ensure_activation_table():
    """
    Create table on-demand so upgrade paths without Django migrations are safe.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS plugin_activation_keys (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        plugin_name VARCHAR(191) NOT NULL,
        user_identity VARCHAR(191) NOT NULL,
        activation_key_hash CHAR(64) NOT NULL,
        key_last4 VARCHAR(4) NOT NULL DEFAULT '',
        source VARCHAR(50) NOT NULL DEFAULT 'manual',
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uniq_plugin_identity (plugin_name, user_identity),
        KEY idx_identity (user_identity),
        KEY idx_plugin (plugin_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)


def save_activation_key(plugin_name, user_identity, activation_key, source='manual'):
    """
    Persist activation key hash in MariaDB (upsert by plugin_name + user_identity).
    """
    plugin_name = _normalize_identity(plugin_name)
    user_identity = _normalize_identity(user_identity)
    activation_key = str(activation_key or '').strip()
    if not plugin_name or not user_identity or not activation_key:
        return False

    try:
        _ensure_activation_table()
        key_hash = _hash_activation_key(activation_key)
        key_last4 = activation_key[-4:] if len(activation_key) >= 4 else activation_key
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO plugin_activation_keys
                    (plugin_name, user_identity, activation_key_hash, key_last4, source, is_active)
                VALUES (%s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    activation_key_hash = VALUES(activation_key_hash),
                    key_last4 = VALUES(key_last4),
                    source = VALUES(source),
                    is_active = 1
                """,
                [plugin_name, user_identity, key_hash, key_last4, source]
            )
        return True
    except Exception as e:
        logging.writeToFile('plugin_access.save_activation_key failed: %s' % str(e))
        return False


def has_saved_activation(plugin_name, user_identity):
    plugin_name = _normalize_identity(plugin_name)
    user_identity = _normalize_identity(user_identity)
    if not plugin_name or not user_identity:
        return False

    try:
        _ensure_activation_table()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM plugin_activation_keys
                WHERE plugin_name = %s
                  AND user_identity = %s
                  AND is_active = 1
                LIMIT 1
                """,
                [plugin_name, user_identity]
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logging.writeToFile('plugin_access.has_saved_activation failed: %s' % str(e))
        return False


def verify_saved_activation_key(plugin_name, user_identity, activation_key):
    plugin_name = _normalize_identity(plugin_name)
    user_identity = _normalize_identity(user_identity)
    activation_key = str(activation_key or '').strip()
    if not plugin_name or not user_identity or not activation_key:
        return False

    try:
        _ensure_activation_table()
        key_hash = _hash_activation_key(activation_key)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM plugin_activation_keys
                WHERE plugin_name = %s
                  AND user_identity = %s
                  AND activation_key_hash = %s
                  AND is_active = 1
                LIMIT 1
                """,
                [plugin_name, user_identity, key_hash]
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logging.writeToFile('plugin_access.verify_saved_activation_key failed: %s' % str(e))
        return False


def _resolve_identity_for_request(request):
    """
    CyberPanel often authenticates via session userID (not Django auth user).
    Prefer Administrator email when available, otherwise username.
    """
    candidates = []
    try:
        if getattr(request, 'user', None) and request.user.is_authenticated:
            u = request.user
            email = getattr(u, 'email', None) or ''
            if email:
                candidates.append(email)
            uname = getattr(u, 'username', None) or ''
            if uname:
                candidates.append(uname)
    except Exception:
        pass
    try:
        uid = request.session.get('userID') if hasattr(request, 'session') else None
        if uid:
            from loginSystem.models import Administrator
            admin = Administrator.objects.filter(pk=uid).only('email', 'userName').first()
            if admin:
                if getattr(admin, 'email', '') and str(admin.email).lower() != 'none':
                    candidates.append(str(admin.email))
                if getattr(admin, 'userName', ''):
                    candidates.append(str(admin.userName))
    except Exception:
        pass
    for item in candidates:
        item = (item or '').strip()
        if item:
            return item.lower()
    return ''


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
    
    user_email = _resolve_identity_for_request(request)
    if not user_email:
        return {
            'has_access': False,
            'is_paid': True,
            'message': 'Unable to verify user identity',
            'patreon_url': plugin_meta.get('patreon_url')
        }
    
    # First allow DB-backed activation keys (survives upgrades)
    if has_saved_activation(plugin_name, user_email):
        return {
            'has_access': True,
            'is_paid': True,
            'message': 'Access granted',
            'patreon_url': None
        }

    # Fallback to Patreon membership
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
