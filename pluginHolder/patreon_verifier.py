# -*- coding: utf-8 -*-
"""
Patreon Verifier for CyberPanel Plugins
Verifies Patreon membership status for paid plugins
"""

import urllib.request
import urllib.error
import json
import os
import sys

# Patreon API configuration
PATREON_API_BASE = 'https://www.patreon.com/api/oauth2/v2'
PATREON_MEMBERSHIP_TIER = 'CyberPanel Paid Plugin'  # The membership tier name to check

class PatreonVerifier:
    """
    Verifies Patreon membership status for CyberPanel users
    """
    
    def __init__(self):
        """Initialize Patreon verifier"""
        # Try to import from Django settings first, then fallback to environment
        try:
            from django.conf import settings
            self.client_id = getattr(settings, 'PATREON_CLIENT_ID', os.environ.get('PATREON_CLIENT_ID', ''))
            self.client_secret = getattr(settings, 'PATREON_CLIENT_SECRET', os.environ.get('PATREON_CLIENT_SECRET', ''))
            self.creator_id = getattr(settings, 'PATREON_CREATOR_ID', os.environ.get('PATREON_CREATOR_ID', ''))
            self.membership_tier_id = getattr(settings, 'PATREON_MEMBERSHIP_TIER_ID', os.environ.get('PATREON_MEMBERSHIP_TIER_ID', ''))
            self.creator_access_token = getattr(settings, 'PATREON_CREATOR_ACCESS_TOKEN', os.environ.get('PATREON_CREATOR_ACCESS_TOKEN', ''))
        except:
            # Fallback to environment variables only
            self.client_id = os.environ.get('PATREON_CLIENT_ID', '')
            self.client_secret = os.environ.get('PATREON_CLIENT_SECRET', '')
            self.creator_id = os.environ.get('PATREON_CREATOR_ID', '')
            self.membership_tier_id = os.environ.get('PATREON_MEMBERSHIP_TIER_ID', '')
            self.creator_access_token = os.environ.get('PATREON_CREATOR_ACCESS_TOKEN', '')
        
        # Cache for membership checks (to avoid excessive API calls)
        self.cache_file = '/home/cyberpanel/patreon_cache.json'
        self.cache_duration = 300  # Cache for 5 minutes
    
    def get_user_patreon_token(self, user_email):
        """
        Get stored Patreon access token for a user
        This should be stored when user authorizes via Patreon OAuth
        """
        # In a real implementation, you'd store this in a database
        # For now, we'll check if there's a stored token file
        token_file = f'/home/cyberpanel/patreon_tokens/{user_email}.token'
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    token_data = json.load(f)
                    return token_data.get('access_token')
            except:
                return None
        return None
    
    def check_membership_cached(self, user_email):
        """
        Check membership with caching
        """
        import time
        cache_data = self._load_cache()
        cache_key = f"membership_{user_email}"
        
        if cache_key in cache_data:
            cached_result = cache_data[cache_key]
            if time.time() - cached_result.get('timestamp', 0) < self.cache_duration:
                return cached_result.get('has_membership', False)
        
        # Check membership via API
        has_membership = self.check_membership(user_email)
        
        # Update cache
        cache_data[cache_key] = {
            'has_membership': has_membership,
            'timestamp': time.time()
        }
        self._save_cache(cache_data)
        
        return has_membership
    
    def check_membership(self, user_email):
        """
        Check if user has active Patreon membership for 'CyberPanel Paid Plugin'
        
        Args:
            user_email: User's email address
            
        Returns:
            bool: True if user has active membership, False otherwise
        """
        access_token = self.get_user_patreon_token(user_email)
        
        if not access_token:
            return False
        
        try:
            # Get user's identity
            user_info = self._get_user_identity(access_token)
            if not user_info:
                return False
            
            member_id = user_info.get('id')
            if not member_id:
                return False
            
            # Get user's memberships
            memberships = self._get_memberships(access_token, member_id)
            if not memberships:
                return False
            
            # Check if user has the required membership tier
            # First try to match by tier ID (more accurate)
            for membership in memberships:
                tier_id = membership.get('id', '')
                tier_name = membership.get('attributes', {}).get('title', '')
                
                # Check by tier ID first (most accurate)
                if tier_id == self.membership_tier_id:
                    # Check if membership is active
                    status = membership.get('attributes', {}).get('patron_status', '')
                    if status in ['active_patron', 'former_patron']:
                        # Check if currently entitled
                        entitled = membership.get('attributes', {}).get('currently_entitled_amount_cents', 0)
                        if entitled > 0:
                            return True
                
                # Fallback: Check by tier name (for compatibility)
                if PATREON_MEMBERSHIP_TIER.lower() in tier_name.lower():
                    # Check if membership is active
                    status = membership.get('attributes', {}).get('patron_status', '')
                    if status in ['active_patron', 'former_patron']:
                        # Check if currently entitled
                        entitled = membership.get('attributes', {}).get('currently_entitled_amount_cents', 0)
                        if entitled > 0:
                            return True
            
            return False
            
        except Exception as e:
            import logging
            logging.writeToFile(f"Error checking Patreon membership for {user_email}: {str(e)}")
            return False
    
    def _get_user_identity(self, access_token):
        """
        Get user identity from Patreon API
        """
        url = f"{PATREON_API_BASE}/identity"
        
        try:
            req = urllib.request.Request(url)
            req.add_header('Authorization', f'Bearer {access_token}')
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                return data.get('data', {})
        except Exception as e:
            import logging
            logging.writeToFile(f"Error getting Patreon identity: {str(e)}")
            return None
    
    def _get_memberships(self, access_token, member_id):
        """
        Get user's memberships from Patreon API
        """
        url = f"{PATREON_API_BASE}/members/{member_id}?include=currently_entitled_tiers"
        
        try:
            req = urllib.request.Request(url)
            req.add_header('Authorization', f'Bearer {access_token}')
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
                # Parse included tiers
                memberships = []
                included = data.get('included', [])
                
                for item in included:
                    if item.get('type') == 'tier':
                        # Include tier ID in the membership data
                        tier_data = {
                            'id': item.get('id', ''),
                            'type': item.get('type', ''),
                            'attributes': item.get('attributes', {})
                        }
                        memberships.append(tier_data)
                
                return memberships
        except Exception as e:
            import logging
            logging.writeToFile(f"Error getting Patreon memberships: {str(e)}")
            return []
    
    def _load_cache(self):
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self, cache_data):
        """Save cache to file"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            import logging
            logging.writeToFile(f"Error saving Patreon cache: {str(e)}")
    
    def verify_plugin_access(self, user_email, plugin_name):
        """
        Verify if user can access a paid plugin
        
        Args:
            user_email: User's email address
            plugin_name: Name of the plugin to check
            
        Returns:
            dict: {
                'has_access': bool,
                'is_paid': bool,
                'message': str
            }
        """
        # Check if plugin is paid (this will be checked from meta.xml)
        # For now, we'll assume the plugin system will pass this info
        
        # Check membership
        has_membership = self.check_membership_cached(user_email)
        
        return {
            'has_access': has_membership,
            'is_paid': True,  # This will be determined by plugin metadata
            'message': 'Access granted' if has_membership else 'Patreon subscription required'
        }
