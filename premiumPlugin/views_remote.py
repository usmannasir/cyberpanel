# -*- coding: utf-8 -*-
"""
Premium Plugin Views - Remote Verification Version
This version uses remote server verification (no secrets in plugin)
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from plogical.mailUtilities import mailUtilities
from plogical.httpProc import httpProc
from functools import wraps
import sys
import os
import urllib.request
import urllib.error
import json

# Remote verification server (YOUR server, not user's server)
REMOTE_VERIFICATION_URL = 'https://api.newstargeted.com/api/verify-patreon-membership'
PLUGIN_NAME = 'premiumPlugin'
PLUGIN_VERSION = '1.0.0'

def cyberpanel_login_required(view_func):
    """
    Custom decorator that checks for CyberPanel session userID
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            userID = request.session['userID']
            # User is authenticated via CyberPanel session
            return view_func(request, *args, **kwargs)
        except KeyError:
            # Not logged in, redirect to login
            from loginSystem.views import loadLoginPage
            return redirect(loadLoginPage)
    return _wrapped_view

def remote_verification_required(view_func):
    """
    Decorator that checks Patreon membership via remote server
    No secrets stored in plugin - all verification happens on your server
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # First check login
        try:
            userID = request.session['userID']
        except KeyError:
            from loginSystem.views import loadLoginPage
            return redirect(loadLoginPage)
        
        # Get user email
        user_email = getattr(request.user, 'email', None) if hasattr(request, 'user') and request.user else None
        if not user_email:
            # Try to get from session or username
            user_email = request.session.get('email', '') or getattr(request.user, 'username', '')
        
        # Check membership via remote server
        verification_result = check_remote_membership(user_email, request.META.get('REMOTE_ADDR', ''))
        
        if not verification_result.get('has_access', False):
            # User doesn't have subscription - show subscription required page
            context = {
                'plugin_name': 'Premium Plugin Example',
                'is_paid': True,
                'patreon_tier': verification_result.get('patreon_tier', 'CyberPanel Paid Plugin'),
                'patreon_url': verification_result.get('patreon_url', 'https://www.patreon.com/c/newstargeted/membership'),
                'message': verification_result.get('message', 'Patreon subscription required'),
                'error': verification_result.get('error')
            }
            proc = httpProc(request, 'premiumPlugin/subscription_required.html', context, 'admin')
            return proc.render()
        
        # User has access - proceed with view
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

def check_remote_membership(user_email, user_ip=''):
    """
    Check Patreon membership via remote verification server
    
    Args:
        user_email: User's email address
        user_ip: User's IP address (for logging/security)
        
    Returns:
        dict: {
            'has_access': bool,
            'patreon_tier': str,
            'patreon_url': str,
            'message': str,
            'error': str or None
        }
    """
    try:
        # Prepare request data
        request_data = {
            'user_email': user_email,
            'plugin_name': PLUGIN_NAME,
            'plugin_version': PLUGIN_VERSION,
            'user_ip': user_ip,
            'tier_id': '27789984'  # CyberPanel Paid Plugin tier ID
        }
        
        # Make request to remote verification server
        req = urllib.request.Request(
            REMOTE_VERIFICATION_URL,
            data=json.dumps(request_data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': f'CyberPanel-Plugin/{PLUGIN_VERSION}',
                'X-Plugin-Name': PLUGIN_NAME
            }
        )
        
        # Send request with timeout
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                
                if response_data.get('success', False):
                    return {
                        'has_access': response_data.get('has_access', False),
                        'patreon_tier': response_data.get('patreon_tier', 'CyberPanel Paid Plugin'),
                        'patreon_url': response_data.get('patreon_url', 'https://www.patreon.com/c/newstargeted/membership'),
                        'message': response_data.get('message', 'Access granted'),
                        'error': None
                    }
                else:
                    return {
                        'has_access': False,
                        'patreon_tier': response_data.get('patreon_tier', 'CyberPanel Paid Plugin'),
                        'patreon_url': response_data.get('patreon_url', 'https://www.patreon.com/c/newstargeted/membership'),
                        'message': response_data.get('message', 'Patreon subscription required'),
                        'error': response_data.get('error')
                    }
        except urllib.error.HTTPError as e:
            # Server returned error
            error_body = e.read().decode('utf-8') if e.fp else 'Unknown error'
            return {
                'has_access': False,
                'patreon_tier': 'CyberPanel Paid Plugin',
                'patreon_url': 'https://www.patreon.com/c/newstargeted/membership',
                'message': 'Unable to verify subscription. Please try again later.',
                'error': f'HTTP {e.code}: {error_body}'
            }
        except urllib.error.URLError as e:
            # Network error
            return {
                'has_access': False,
                'patreon_tier': 'CyberPanel Paid Plugin',
                'patreon_url': 'https://www.patreon.com/c/newstargeted/membership',
                'message': 'Unable to connect to verification server. Please check your internet connection.',
                'error': str(e.reason) if hasattr(e, 'reason') else str(e)
            }
        except Exception as e:
            # Other errors
            return {
                'has_access': False,
                'patreon_tier': 'CyberPanel Paid Plugin',
                'patreon_url': 'https://www.patreon.com/c/newstargeted/membership',
                'message': 'Verification error occurred. Please try again later.',
                'error': str(e)
            }
            
    except Exception as e:
        import logging
        logging.writeToFile(f"Error in remote membership check: {str(e)}")
        return {
            'has_access': False,
            'patreon_tier': 'CyberPanel Paid Plugin',
            'patreon_url': 'https://www.patreon.com/c/newstargeted/membership',
            'message': 'Verification error occurred. Please try again later.',
            'error': str(e)
        }

@cyberpanel_login_required
@remote_verification_required
def main_view(request):
    """
    Main view for premium plugin
    Only accessible with Patreon subscription (verified remotely)
    """
    mailUtilities.checkHome()
    
    context = {
        'plugin_name': 'Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'description': 'This is an example paid plugin. You have access because you are subscribed to Patreon!',
        'features': [
            'Premium Feature 1',
            'Premium Feature 2',
            'Premium Feature 3',
            'Advanced Configuration',
            'Priority Support'
        ]
    }
    
    proc = httpProc(request, 'premiumPlugin/index.html', context, 'admin')
    return proc.render()

@cyberpanel_login_required
@remote_verification_required
def settings_view(request):
    """
    Settings page for premium plugin
    Only accessible with Patreon subscription (verified remotely)
    """
    mailUtilities.checkHome()
    
    context = {
        'plugin_name': 'Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'description': 'Configure your premium plugin settings'
    }
    
    proc = httpProc(request, 'premiumPlugin/settings.html', context, 'admin')
    return proc.render()

@cyberpanel_login_required
@remote_verification_required
def api_status_view(request):
    """
    API endpoint for plugin status
    Only accessible with Patreon subscription (verified remotely)
    """
    return JsonResponse({
        'plugin_name': 'Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'status': 'active',
        'subscription': 'active',
        'description': 'Premium plugin is active and accessible',
        'verification_method': 'remote'
    })
