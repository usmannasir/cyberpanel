# -*- coding: utf-8 -*-
"""
PayPal Premium Plugin Views - Enhanced Security Version
This version uses remote server verification with multiple security layers
SECURITY: All PayPal verification happens on YOUR server, not user's server
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from plogical.mailUtilities import mailUtilities
from plogical.httpProc import httpProc
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from functools import wraps
import sys
import os
import urllib.request
import urllib.error
import json
import hashlib
import socket
import platform
import subprocess
import time
import uuid

# Remote verification server (YOUR server, not user's server)
REMOTE_VERIFICATION_URL = 'https://api.newstargeted.com/api/verify-paypal-payment'
PLUGIN_NAME = 'paypalPremiumPlugin'  # PayPal Premium Plugin Example
PLUGIN_VERSION = '1.0.0'

# PayPal configuration
PAYPAL_ME_URL = 'https://paypal.me/KimBS?locale.x=en_US&country.x=NO'
PAYPAL_PAYMENT_LINK = ''  # Can be set to a PayPal Payment Link URL

# Security configuration
CACHE_FILE = '/tmp/.paypalPremiumPlugin_license_cache'
CACHE_DURATION = 3600  # 1 hour

# File integrity hashes (generated after plugin finalization)
# To regenerate: python3 -c "import hashlib; print(hashlib.sha256(open('views.py', 'rb').read()).hexdigest())"
PLUGIN_FILE_HASHES = {
    'views.py': '4899d70dde220b38d691a5cefdc4fd77b6d3e250ac1c7e12fa280d6f4ad31eb1',  # Updated with security features
    'urls.py': '92433d401c358cd33ffd1926881920fd1867bb6d7dad1c3c2ed1e7d3b0abc2c6',
}

def get_server_fingerprint():
    """
    Generate unique server fingerprint
    Ties license to specific server hardware/configuration
    """
    fingerprint_data = []
    
    try:
        # Server hostname
        fingerprint_data.append(socket.gethostname())
        
        # Primary IP
        fingerprint_data.append(socket.gethostbyname(socket.gethostname()))
        
        # System information
        fingerprint_data.append(platform.node())
        fingerprint_data.append(platform.machine())
        fingerprint_data.append(platform.processor())
        
        # MAC address
        fingerprint_data.append(str(uuid.getnode()))
        
        # Disk information (if available)
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=2)
            fingerprint_data.append(result.stdout[:100])
        except:
            pass
        
        # Create hash
        fingerprint_string = '|'.join(str(x) for x in fingerprint_data)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    except Exception as e:
        # Fallback fingerprint
        return hashlib.sha256(f"{socket.gethostname()}|{platform.node()}".encode()).hexdigest()

def verify_code_integrity():
    """
    Verify plugin files haven't been tampered with
    Returns: (is_valid, error_message)
    """
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename, expected_hash in PLUGIN_FILE_HASHES.items():
        if not expected_hash:
            continue  # Skip if hash not set
            
        filepath = os.path.join(plugin_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.sha256(file_content).hexdigest()
                    
                    if file_hash != expected_hash:
                        return False, f"File {filename} has been modified (integrity check failed)"
            except Exception as e:
                return False, f"Error checking {filename}: {str(e)}"
    
    return True, None

def get_cached_verification():
    """Get cached verification result"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                cache_time = cache_data.get('timestamp', 0)
                server_fp = cache_data.get('server_fingerprint')
                
                # Verify server fingerprint matches
                current_fp = get_server_fingerprint()
                if server_fp != current_fp:
                    return None  # Server changed, invalidate cache
                
                # Check if cache is still valid
                if time.time() - cache_time < CACHE_DURATION:
                    return cache_data.get('has_access', False)
        except:
            pass
    return None

def cache_verification_result(has_access, server_fp):
    """Cache verification result"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({
                'has_access': has_access,
                'server_fingerprint': server_fp,
                'timestamp': time.time()
            }, f)
        os.chmod(CACHE_FILE, 0o600)  # Secure permissions (owner read/write only)
    except Exception as e:
        pass  # Silently fail caching

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

def secure_verification_required(view_func):
    """
    Enhanced decorator with multiple security checks
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check 1: Login required
        try:
            userID = request.session['userID']
        except KeyError:
            from loginSystem.views import loadLoginPage
            return redirect(loadLoginPage)
        
        # Check 2: Code integrity
        is_valid, integrity_error = verify_code_integrity()
        if not is_valid:
            # Log security violation
            logging.writeToFile(f"SECURITY VIOLATION: {integrity_error} - User: {request.session.get('userID')}")
            
            # Show error (don't reveal details)
            context = {
                'error': 'Plugin integrity check failed. Please reinstall the plugin.',
                'security_violation': True
            }
            proc = httpProc(request, 'paypalPremiumPlugin/subscription_required.html', context, 'admin')
            return proc.render()
        
        # Check 3: Remote verification
        user_email = getattr(request.user, 'email', None) if hasattr(request, 'user') and request.user else None
        if not user_email:
            user_email = request.session.get('email', '') or getattr(request.user, 'username', '')
        
        domain = request.get_host()
        user_ip = request.META.get('REMOTE_ADDR', '')
        
        verification_result = check_remote_payment_secure(
            user_email,
            user_ip,
            domain
        )
        
        if not verification_result.get('has_access', False):
            # Show payment required page
            context = {
                'plugin_name': 'PayPal Premium Plugin Example',
                'is_paid': True,
                'paypal_me_url': verification_result.get('paypal_me_url', PAYPAL_ME_URL),
                'paypal_payment_link': verification_result.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                'message': verification_result.get('message', 'PayPal payment required'),
                'error': verification_result.get('error')
            }
            proc = httpProc(request, 'paypalPremiumPlugin/subscription_required.html', context, 'admin')
            return proc.render()
        
        # All checks passed - proceed
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

def remote_verification_required(view_func):
    """
    Decorator that checks PayPal payment via remote server
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
        
        # Check payment via remote server
        verification_result = check_remote_payment_secure(
            user_email,
            request.META.get('REMOTE_ADDR', ''),
            request.get_host()
        )
        
        if not verification_result.get('has_access', False):
            # User doesn't have payment - show payment required page
            context = {
                'plugin_name': 'PayPal Premium Plugin Example',
                'is_paid': True,
                'paypal_me_url': verification_result.get('paypal_me_url', PAYPAL_ME_URL),
                'paypal_payment_link': verification_result.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                'message': verification_result.get('message', 'PayPal payment required'),
                'error': verification_result.get('error')
            }
            proc = httpProc(request, 'paypalPremiumPlugin/subscription_required.html', context, 'admin')
            return proc.render()
        
        # User has access - proceed with view
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

def check_remote_payment_secure(user_email, user_ip='', domain=''):
    """
    Enhanced remote payment verification with multiple security layers
    
    Args:
        user_email: User's email address
        user_ip: User's IP address (for logging/security)
        domain: Current domain (for domain binding)
        
    Returns:
        dict: {
            'has_access': bool,
            'paypal_me_url': str,
            'paypal_payment_link': str,
            'message': str,
            'error': str or None
        }
    """
    # Layer 1: Code integrity check
    is_valid, integrity_error = verify_code_integrity()
    if not is_valid:
        return {
            'has_access': False,
            'paypal_me_url': PAYPAL_ME_URL,
            'paypal_payment_link': PAYPAL_PAYMENT_LINK,
            'message': 'Plugin integrity check failed',
            'error': integrity_error,
            'security_violation': True
        }
    
    # Layer 2: Check cache
    cached_result = get_cached_verification()
    if cached_result is not None:
        return {
            'has_access': cached_result,
            'paypal_me_url': PAYPAL_ME_URL,
            'paypal_payment_link': PAYPAL_PAYMENT_LINK,
            'message': 'Access granted' if cached_result else 'PayPal payment required'
        }
    
    # Layer 3: Server fingerprinting
    server_fp = get_server_fingerprint()
    
    # Layer 4: Prepare secure request
    request_data = {
        'user_email': user_email,
        'plugin_name': PLUGIN_NAME,
        'plugin_version': PLUGIN_VERSION,
        'server_fingerprint': server_fp,
        'domain': domain,
        'user_ip': user_ip,
        'timestamp': int(time.time())
    }
    
    try:
        # Make request to remote verification server
        req = urllib.request.Request(
            REMOTE_VERIFICATION_URL,
            data=json.dumps(request_data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': f'CyberPanel-Plugin/{PLUGIN_VERSION}',
                'X-Plugin-Name': PLUGIN_NAME,
                'X-Timestamp': str(request_data['timestamp'])
            }
        )
        
        # Send request with timeout
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                
                if response_data.get('success', False):
                    has_access = response_data.get('has_access', False)
                    
                    # Cache result
                    cache_verification_result(has_access, server_fp)
                    
                    return {
                        'has_access': has_access,
                        'paypal_me_url': response_data.get('paypal_me_url', PAYPAL_ME_URL),
                        'paypal_payment_link': response_data.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                        'message': response_data.get('message', 'Access granted' if has_access else 'PayPal payment required'),
                        'error': None
                    }
                else:
                    return {
                        'has_access': False,
                        'paypal_me_url': response_data.get('paypal_me_url', PAYPAL_ME_URL),
                        'paypal_payment_link': response_data.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                        'message': response_data.get('message', 'PayPal payment required'),
                        'error': response_data.get('error')
                    }
        except urllib.error.HTTPError as e:
            # Server returned error
            error_body = e.read().decode('utf-8') if e.fp else 'Unknown error'
            return {
                'has_access': False,
                'paypal_me_url': PAYPAL_ME_URL,
                'paypal_payment_link': PAYPAL_PAYMENT_LINK,
                'message': 'Unable to verify payment. Please try again later.',
                'error': f'HTTP {e.code}: {error_body}'
            }
        except urllib.error.URLError as e:
            # Network error
            return {
                'has_access': False,
                'paypal_me_url': PAYPAL_ME_URL,
                'paypal_payment_link': PAYPAL_PAYMENT_LINK,
                'message': 'Unable to connect to verification server. Please check your internet connection.',
                'error': str(e.reason) if hasattr(e, 'reason') else str(e)
            }
        except Exception as e:
            # Other errors
            return {
                'has_access': False,
                'paypal_me_url': PAYPAL_ME_URL,
                'paypal_payment_link': PAYPAL_PAYMENT_LINK,
                'message': 'Verification error occurred. Please try again later.',
                'error': str(e)
            }
            
    except Exception as e:
        logging.writeToFile(f"Error in remote payment check: {str(e)}")
        return {
            'has_access': False,
            'paypal_me_url': PAYPAL_ME_URL,
            'paypal_payment_link': PAYPAL_PAYMENT_LINK,
            'message': 'Verification error occurred. Please try again later.',
            'error': str(e)
        }

def check_remote_payment(user_email, user_ip=''):
    """
    Legacy function for backward compatibility
    """
    return check_remote_payment_secure(user_email, user_ip, '')

@cyberpanel_login_required
def main_view(request):
    """
    Main view for PayPal premium plugin
    Shows plugin information and features if paid, or payment required message if not
    """
    mailUtilities.checkHome()
    
    # Get user email for verification
    user_email = getattr(request.user, 'email', None) if hasattr(request, 'user') and request.user else None
    if not user_email:
        user_email = request.session.get('email', '') or getattr(request.user, 'username', '')
    
    # Check payment status (but don't block access)
    verification_result = check_remote_payment_secure(
        user_email,
        request.META.get('REMOTE_ADDR', ''),
        request.get_host()
    )
    has_access = verification_result.get('has_access', False)
    
    # Determine plugin status
    plugin_status = 'Active' if has_access else 'Payment Required'
    
    context = {
        'plugin_name': 'PayPal Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'status': plugin_status,
        'has_access': has_access,
        'description': 'This is an example paid plugin that requires PayPal payment.' if not has_access else 'This is an example paid plugin. You have access because payment has been verified!',
        'paypal_me_url': verification_result.get('paypal_me_url', PAYPAL_ME_URL),
        'paypal_payment_link': verification_result.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
        'features': [
            'Premium Feature 1',
            'Premium Feature 2',
            'Premium Feature 3',
            'Advanced Configuration',
            'Priority Support'
        ] if has_access else []
    }
    
    proc = httpProc(request, 'paypalPremiumPlugin/index.html', context, 'admin')
    return proc.render()

@cyberpanel_login_required
def settings_view(request):
    """
    Settings page for PayPal premium plugin
    Shows settings but disables them if user doesn't have PayPal payment
    """
    mailUtilities.checkHome()
    
    # Get user email for verification
    user_email = getattr(request.user, 'email', None) if hasattr(request, 'user') and request.user else None
    if not user_email:
        user_email = request.session.get('email', '') or getattr(request.user, 'username', '')
    
    # Check payment status (but don't block access)
    verification_result = check_remote_payment_secure(
        user_email,
        request.META.get('REMOTE_ADDR', ''),
        request.get_host()
    )
    has_access = verification_result.get('has_access', False)
    
    # Determine plugin status
    plugin_status = 'Active' if has_access else 'Payment Required'
    
    context = {
        'plugin_name': 'PayPal Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'plugin_status': plugin_status,
        'status': plugin_status,  # Keep both for compatibility
        'description': 'Configure your premium plugin settings',
        'has_access': has_access,
        'paypal_me_url': verification_result.get('paypal_me_url', PAYPAL_ME_URL),
        'paypal_payment_link': verification_result.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
        'verification_message': verification_result.get('message', '')
    }
    
    proc = httpProc(request, 'paypalPremiumPlugin/settings.html', context, 'admin')
    return proc.render()

@cyberpanel_login_required
@secure_verification_required
def api_status_view(request):
    """
    API endpoint for plugin status
    Only accessible with PayPal payment (verified remotely with enhanced security)
    """
    return JsonResponse({
        'plugin_name': 'PayPal Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'status': 'active',
        'payment': 'verified',
        'description': 'Premium plugin is active and accessible',
        'verification_method': 'remote_secure'
    })
