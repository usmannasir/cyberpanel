# -*- coding: utf-8 -*-
"""
Auto Ban Security Alerts Plugin Views
Automatically bans IPs from Security Alerts Detected in Recent SSH Logs
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from plogical.mailUtilities import mailUtilities
from plogical.httpProc import httpProc
from plogical.plugin_acl import require_manage_plugins_api
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from functools import wraps
import urllib.request
import urllib.error
import json
import os
import hashlib
import uuid
import threading
import time

from .models import AutoBanConfig, WhitelistedIP, AutoBanLog
from . import api_encryption

PLUGIN_NAME = 'autoBanSecurityAlerts'
PLUGIN_VERSION = '1.0.3'

AUTO_BAN_PER_PAGE_CHOICES = (5, 10, 15, 30, 50)
AUTO_BAN_DEFAULT_PER_PAGE = 5

REMOTE_VERIFICATION_PATREON_URL = 'https://api.newstargeted.com/api/verify-patreon-membership.php'
REMOTE_VERIFICATION_PAYPAL_URL = 'https://api.newstargeted.com/api/verify-paypal-payment.php'
REMOTE_VERIFICATION_PLUGIN_GRANT_URL = 'https://api.newstargeted.com/api/verify-plugin-grant.php'
REMOTE_ACTIVATION_KEY_URL = 'https://api.newstargeted.com/api/activate-plugin-key.php'
REMOTE_ENTITLEMENT_VERIFY_URL = 'https://api.newstargeted.com/api/verify-entitlement.php'

PATREON_TIER = 'CyberPanel Paid Plugin'
PATREON_URL = 'https://www.patreon.com/membership/27789984'
PAYPAL_ME_URL = 'https://paypal.me/KimBS?locale.x=en_US&country.x=NO'
PAYPAL_PAYMENT_LINK = ''

# Global monitoring thread
_monitoring_thread = None
_monitoring_lock = threading.Lock()


def _parse_firewall_http_response(result):
    """Parse JsonResponse/HttpResponse/dict from FirewallManager methods."""
    if result is None:
        return {}
    if isinstance(result, dict):
        return result
    try:
        raw = getattr(result, 'content', None)
        if raw is None:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', errors='replace')
        return json.loads(raw)
    except Exception:
        return {}


def _resolve_user_identity(request, override_email=''):
    """
    Resolve a stable user identity for premium verification/persistence.
    """
    candidates = [
        (override_email or '').strip(),
        (request.session.get('email', '') if hasattr(request, 'session') else '').strip(),
        (getattr(getattr(request, 'user', None), 'email', '') or '').strip(),
        (getattr(getattr(request, 'user', None), 'username', '') or '').strip(),
    ]
    for item in candidates:
        if item:
            return item.lower()
    # CyberPanel commonly stores only userID in session (not email). Fall back to Administrator.
    try:
        from loginSystem.models import Administrator
        uid = request.session.get('userID') if hasattr(request, 'session') else None
        if uid:
            admin = Administrator.objects.filter(pk=uid).only('email', 'userName').first()
            if admin:
                if getattr(admin, 'email', '') and str(admin.email).lower() != 'none':
                    return str(admin.email).strip().lower()
                if getattr(admin, 'userName', ''):
                    return str(admin.userName).strip().lower()
    except Exception:
        pass
    return ''


def _persist_activation_in_cyberpanel_db(request, activation_key):
    """
    Save activation key in CyberPanel pluginHolder DB storage for upgrade resilience.
    """
    key_value = (activation_key or '').strip()
    if not key_value:
        return False
    try:
        from pluginHolder.plugin_access import save_activation_key
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: pluginHolder save_activation_key import failed: {str(e)}")
        return False

    identities = set()
    for identity in [
        (request.session.get('email', '') if hasattr(request, 'session') else '').strip().lower(),
        (getattr(getattr(request, 'user', None), 'email', '') or '').strip().lower(),
        (getattr(getattr(request, 'user', None), 'username', '') or '').strip().lower(),
    ]:
        if identity:
            identities.add(identity)
    try:
        from loginSystem.models import Administrator
        uid = request.session.get('userID') if hasattr(request, 'session') else None
        if uid:
            admin = Administrator.objects.filter(pk=uid).only('email', 'userName').first()
            if admin:
                if getattr(admin, 'email', '') and str(admin.email).lower() != 'none':
                    identities.add(str(admin.email).strip().lower())
                if getattr(admin, 'userName', ''):
                    identities.add(str(admin.userName).strip().lower())
    except Exception:
        pass

    saved_any = False
    for identity in identities:
        try:
            if save_activation_key(PLUGIN_NAME, identity, key_value, source='autoban_plugin'):
                saved_any = True
        except Exception as e:
            logging.writeToFile(f"Auto Ban Plugin: save_activation_key failed for {identity}: {str(e)}")
    return saved_any


def cyberpanel_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            if not request.session.get('userID'):
                from loginSystem.login_return import redirect_to_login
                return redirect_to_login(request)
            return view_func(request, *args, **kwargs)
        except KeyError:
            from loginSystem.login_return import redirect_to_login
            return redirect_to_login(request)
    return _wrapped_view


def _api_request(url, data, timeout=10):
    """Send encrypted API request and return decoded response dict."""
    try:
        body, extra_headers = api_encryption.encrypt_payload(data)
        headers = {
            'User-Agent': f'CyberPanel-Plugin/{PLUGIN_VERSION}',
            'X-Plugin-Name': PLUGIN_NAME
        }
        headers.update(extra_headers)
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            ct = response.headers.get('Content-Type', '')
            expect_enc = extra_headers.get('X-Encrypted') == '1'
            return api_encryption.decrypt_response(raw, ct, expect_encrypted=expect_enc)
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: API request error to {url}: {str(e)}")
        return {}


def get_server_fingerprint():
    """Stable server id for API binding (machine-id + MAC-derived node)."""
    try:
        parts = []
        try:
            with open('/etc/machine-id', 'r') as _mf:
                mid = _mf.read().strip()
                if mid:
                    parts.append(mid)
        except Exception:
            pass
        parts.append(str(uuid.getnode()))
        return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()
    except Exception:
        return ''


def _persist_entitlement_from_response(config, response_data):
    if not config or not response_data:
        return
    try:
        tok = response_data.get('entitlement_token')
        if not tok:
            return
        exp = response_data.get('entitlement_expires_at')
        config.entitlement_token = tok
        fields = ['entitlement_token', 'updated_at']
        if exp is not None:
            try:
                config.entitlement_expires_at = int(exp)
            except (TypeError, ValueError):
                config.entitlement_expires_at = None
            fields.append('entitlement_expires_at')
        config.save(update_fields=fields)
    except Exception as ex:
        logging.writeToFile(f"Auto Ban Plugin: Could not persist entitlement: {str(ex)}")


def _clear_entitlement(config):
    if not config:
        return
    try:
        if getattr(config, 'entitlement_token', ''):
            config.entitlement_token = ''
            config.entitlement_expires_at = None
            config.save(update_fields=['entitlement_token', 'entitlement_expires_at', 'updated_at'])
    except Exception as ex:
        logging.writeToFile(f"Auto Ban Plugin: Could not clear entitlement: {str(ex)}")


def check_plugin_grant(user_email, user_ip='', domain='', server_fp=''):
    try:
        # Normalize email to lowercase for matching
        user_email_normalized = (user_email or '').strip().lower()
        request_data = {
            'user_email': user_email_normalized,
            'plugin_name': PLUGIN_NAME,
            'user_ip': user_ip,
            'domain': domain,
            'server_fingerprint': server_fp,
        }
        data = _api_request(REMOTE_VERIFICATION_PLUGIN_GRANT_URL, request_data)
        if data.get('success') and data.get('has_access'):
            logging.writeToFile(f"Auto Ban Plugin: Plugin grant access granted for {user_email_normalized}")
            _persist_entitlement_from_response(AutoBanConfig.get_config(), data)
            return {'has_access': True, 'message': data.get('message', 'Access granted via Plugin Grants')}
        logging.writeToFile(f"Auto Ban Plugin: Plugin grant check - no access for {user_email_normalized}: {data.get('message', 'No grant found')}")
        return {'has_access': False, 'message': data.get('message', '')}
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Plugin grant check error: {str(e)}")
        return {'has_access': False, 'message': ''}


def check_patreon_membership(user_email, user_ip='', domain='', server_fp=''):
    try:
        request_data = {
            'user_email': user_email,
            'plugin_name': PLUGIN_NAME,
            'plugin_version': PLUGIN_VERSION,
            'user_ip': user_ip,
            'domain': domain,
            'server_fingerprint': server_fp,
            'tier_id': '27789984'
        }
        response_data = _api_request(REMOTE_VERIFICATION_PATREON_URL, request_data)
        if response_data.get('success', False):
            if response_data.get('has_access'):
                _persist_entitlement_from_response(AutoBanConfig.get_config(), response_data)
            return {
                'has_access': response_data.get('has_access', False),
                'patreon_tier': response_data.get('patreon_tier', PATREON_TIER),
                'patreon_url': response_data.get('patreon_url', PATREON_URL),
                'message': response_data.get('message', 'Access granted'),
                'error': None
            }
        return {
            'has_access': False,
            'patreon_tier': PATREON_TIER,
            'patreon_url': PATREON_URL,
            'message': response_data.get('message', 'Patreon subscription required'),
            'error': response_data.get('error')
        }
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Patreon check error: {str(e)}")
        return {
            'has_access': False,
            'patreon_tier': PATREON_TIER,
            'patreon_url': PATREON_URL,
            'message': 'Unable to verify Patreon membership.',
            'error': str(e)
        }


def check_paypal_payment(user_email, user_ip='', domain='', server_fp=''):
    try:
        request_data = {
            'user_email': user_email,
            'plugin_name': PLUGIN_NAME,
            'plugin_version': PLUGIN_VERSION,
            'user_ip': user_ip,
            'domain': domain,
            'server_fingerprint': server_fp,
            'timestamp': 0,
        }
        import time
        request_data['timestamp'] = int(time.time())
        response_data = _api_request(REMOTE_VERIFICATION_PAYPAL_URL, request_data)
        if response_data.get('success', False):
            if response_data.get('has_access'):
                _persist_entitlement_from_response(AutoBanConfig.get_config(), response_data)
            return {
                'has_access': response_data.get('has_access', False),
                'paypal_me_url': response_data.get('paypal_me_url', PAYPAL_ME_URL),
                'paypal_payment_link': response_data.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                'message': response_data.get('message', 'Access granted'),
                'error': None
            }
        return {
            'has_access': False,
            'paypal_me_url': PAYPAL_ME_URL,
            'paypal_payment_link': PAYPAL_PAYMENT_LINK,
            'message': response_data.get('message', 'PayPal payment required'),
            'error': response_data.get('error')
        }
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: PayPal check error: {str(e)}")
        return {
            'has_access': False,
            'paypal_me_url': PAYPAL_ME_URL,
            'paypal_payment_link': PAYPAL_PAYMENT_LINK,
            'message': 'Unable to verify PayPal payment.',
            'error': str(e)
        }


def unified_verification_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            if not request.session.get('userID'):
                from loginSystem.login_return import redirect_to_login
                return redirect_to_login(request)

            # Get user email from session or user object, normalize to lowercase
            user_email = _resolve_user_identity(request)
            logging.writeToFile(f"Auto Ban Plugin: Checking access for email: {user_email}")

            try:
                config = AutoBanConfig.get_config()
                payment_method = config.payment_method
            except Exception:
                payment_method = 'both'

            has_access = False
            verification_result = {}

            user_ip = request.META.get('REMOTE_ADDR', '') or ''
            domain = request.get_host() or ''
            server_fp = get_server_fingerprint()

            try:
                cfg_ent = AutoBanConfig.get_config()
                ent_tok = (getattr(cfg_ent, 'entitlement_token', '') or '').strip()
                if ent_tok:
                    ent_resp = _api_request(REMOTE_ENTITLEMENT_VERIFY_URL, {
                        'entitlement_token': ent_tok,
                        'plugin_name': PLUGIN_NAME,
                        'user_email': user_email,
                        'server_fingerprint': server_fp,
                        'domain': domain,
                    })
                    if ent_resp.get('success') and ent_resp.get('has_access'):
                        logging.writeToFile(
                            f"Auto Ban Plugin: entitlement verification granted method=entitlement user={user_email[:3] + '***' if user_email else ''}"
                        )
                        _persist_entitlement_from_response(cfg_ent, ent_resp)
                        request.session['auto_ban_plugin_access_via'] = 'entitlement'
                        return view_func(request, *args, **kwargs)
                    _clear_entitlement(AutoBanConfig.get_config())
            except Exception as _ent_e:
                logging.writeToFile(f"Auto Ban Plugin: Entitlement verify error: {str(_ent_e)}")

            activation_key = request.GET.get('activation_key') or request.POST.get('activation_key')
            if (
                not activation_key
                and request.method == 'POST'
                and request.content_type
                and 'application/json' in request.content_type
                and request.body
            ):
                try:
                    _payload = json.loads(request.body)
                    if isinstance(_payload, dict):
                        activation_key = _payload.get('activation_key') or activation_key
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            if not activation_key:
                try:
                    config = AutoBanConfig.get_config()
                    activation_key = getattr(config, 'activation_key', '') or ''
                except Exception:
                    activation_key = ''

            if activation_key:
                try:
                    activation_key_str = activation_key.strip()

                    # 1) Local verification using CyberPanel DB-backed activation keys.
                    # This prevents re-locking when upgrades/remote activation state becomes inconsistent.
                    activation_ok = False
                    try:
                        from pluginHolder.plugin_access import verify_saved_activation_key
                        activation_ok = verify_saved_activation_key(PLUGIN_NAME, user_email, activation_key_str)
                        logging.writeToFile(
                            f"Auto Ban Plugin: local activation DB verify result: ok={activation_ok} "
                            f"plugin={PLUGIN_NAME} user={user_email[:3] + '***' if user_email else ''} "
                            f"key_last4={activation_key_str[-4:] if len(activation_key_str) >= 4 else ''}"
                        )
                    except Exception as _db_e:
                        activation_ok = False
                        logging.writeToFile(f"Auto Ban Plugin: local activation DB verify error: {str(_db_e)}")

                    if activation_ok:
                        has_access = True
                        verification_result = {
                            'method': 'activation_key',
                            'has_access': True,
                            'message': 'Access granted via saved activation key'
                        }
                    else:
                        request_data = {
                            'activation_key': activation_key_str,
                            'plugin_name': PLUGIN_NAME,
                            'user_email': user_email,
                            'server_fingerprint': server_fp,
                            'domain': domain,
                        }
                        response_data = _api_request(REMOTE_ACTIVATION_KEY_URL, request_data)
                        if response_data.get('success', False) and response_data.get('has_access', False):
                            has_access = True
                            verification_result = {
                                'method': 'activation_key',
                                'has_access': True,
                                'message': response_data.get('message', 'Access activated via key'),
                            }
                            try:
                                config = AutoBanConfig.get_config()
                                config.activation_key = activation_key_str
                                config.save(update_fields=['activation_key', 'updated_at'])
                                _persist_entitlement_from_response(config, response_data)
                                _persist_activation_in_cyberpanel_db(request, activation_key_str)
                            except Exception as e:
                                logging.writeToFile(f"Auto Ban Plugin: Could not persist activation key: {str(e)}")
                        else:
                            try:
                                config = AutoBanConfig.get_config()
                                persisted = (getattr(config, 'activation_key', '') or '').strip()
                                if persisted == activation_key_str:
                                    has_access = True
                                    verification_result = {
                                        'method': 'activation_key',
                                        'has_access': True,
                                        'message': 'Access granted via saved activation key',
                                    }
                            except Exception:
                                pass
                except Exception as e:
                    logging.writeToFile(f"Auto Ban Plugin: Activation key check error: {str(e)}")

            # Prefer local DB activation keys over remote "plugin grant" checks when both could match.
            if not has_access and user_email and activation_key:
                try:
                    from pluginHolder.plugin_access import has_saved_activation
                    if has_saved_activation(PLUGIN_NAME, user_email):
                        has_access = True
                        verification_result = {
                            'method': 'activation_key',
                            'has_access': True,
                            'message': 'Access granted via saved activation key'
                        }
                except Exception as _hs_e:
                    logging.writeToFile(f"Auto Ban Plugin: has_saved_activation check error: {str(_hs_e)}")

            if not has_access:
                grant_result = check_plugin_grant(user_email, user_ip, domain, server_fp)
                if grant_result.get('has_access'):
                    has_access = True
                    verification_result = {'method': 'plugin_grant', 'has_access': True, 'message': grant_result.get('message', 'Access granted via Plugin Grants')}

            if not has_access:
                try:
                    if payment_method == 'patreon':
                        result = check_patreon_membership(user_email, user_ip, domain, server_fp)
                        has_access = result.get('has_access', False)
                        verification_result = {
                            'method': 'patreon', 'has_access': has_access,
                            'patreon_tier': result.get('patreon_tier', PATREON_TIER),
                            'patreon_url': result.get('patreon_url', PATREON_URL),
                            'paypal_me_url': PAYPAL_ME_URL, 'paypal_payment_link': PAYPAL_PAYMENT_LINK,
                            'message': result.get('message', 'Patreon subscription required'),
                            'error': result.get('error')
                        }
                    elif payment_method == 'paypal':
                        result = check_paypal_payment(user_email, user_ip, domain, server_fp)
                        has_access = result.get('has_access', False)
                        verification_result = {
                            'method': 'paypal', 'has_access': has_access,
                            'patreon_tier': PATREON_TIER, 'patreon_url': PATREON_URL,
                            'paypal_me_url': result.get('paypal_me_url', PAYPAL_ME_URL),
                            'paypal_payment_link': result.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                            'message': result.get('message', 'PayPal payment required'),
                            'error': result.get('error')
                        }
                    else:
                        patreon_result = check_patreon_membership(user_email, user_ip, domain, server_fp)
                        paypal_result = check_paypal_payment(user_email, user_ip, domain, server_fp)
                        has_access = patreon_result.get('has_access', False) or paypal_result.get('has_access', False)
                        verification_result = {
                            'method': 'both', 'has_access': has_access,
                            'patreon_tier': patreon_result.get('patreon_tier', PATREON_TIER),
                            'patreon_url': patreon_result.get('patreon_url', PATREON_URL),
                            'paypal_me_url': paypal_result.get('paypal_me_url', PAYPAL_ME_URL),
                            'paypal_payment_link': paypal_result.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                            'message': 'Payment or subscription required' if not has_access else 'Access granted'
                        }
                except Exception as e:
                    logging.writeToFile(f"Auto Ban Plugin: Verification error: {str(e)}")
                    has_access = False
                    verification_result = {
                        'method': payment_method, 'has_access': False,
                        'patreon_tier': PATREON_TIER, 'patreon_url': PATREON_URL,
                        'paypal_me_url': PAYPAL_ME_URL, 'paypal_payment_link': PAYPAL_PAYMENT_LINK,
                        'message': 'Unable to verify access.',
                        'error': str(e)
                    }

            if not has_access:
                context = {
                    'plugin_name': 'Auto Ban Security Alerts',
                    'is_paid': True,
                    'payment_method': payment_method,
                    'verification_result': verification_result,
                    'patreon_tier': verification_result.get('patreon_tier', PATREON_TIER),
                    'patreon_url': verification_result.get('patreon_url', PATREON_URL),
                    'paypal_me_url': verification_result.get('paypal_me_url', PAYPAL_ME_URL),
                    'paypal_payment_link': verification_result.get('paypal_payment_link', PAYPAL_PAYMENT_LINK),
                    'message': verification_result.get('message', 'Payment or subscription required'),
                    'error': verification_result.get('error')
                }
                proc = httpProc(request, 'autoBanSecurityAlerts/subscription_required.html', context, 'managePlugins')
                return proc.render()

            if has_access and verification_result:
                method = verification_result.get('method', '') or ''
                request.session['auto_ban_plugin_access_via'] = method
                logging.writeToFile(
                    f"Auto Ban Plugin: granted has_access=True method={method} user={user_email[:3] + '***' if user_email else ''}"
                )
            else:
                # If has_access is true but verification_result is empty, UI may remain on payment page.
                logging.writeToFile(
                    f"Auto Ban Plugin: granted has_access={has_access} verification_result_empty={not bool(verification_result)}"
                )

            return view_func(request, *args, **kwargs)
        except Exception as e:
            logging.writeToFile(f"Auto Ban Plugin: Decorator error: {str(e)}")
            return HttpResponse(f"<div style='padding: 20px;'><h2>Plugin Error</h2><p>{str(e)}</p></div>")
    return _wrapped_view


def get_machine_ip():
    """Get CyberPanel machine IP from /etc/cyberpanel/machineIP"""
    try:
        ip_file = '/etc/cyberpanel/machineIP'
        if os.path.exists(ip_file):
            with open(ip_file, 'r') as f:
                ip = f.read().strip()
                if ip:
                    return ip
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error reading machine IP: {str(e)}")
    return None


def ensure_machine_ip_whitelisted():
    """Ensure the current CyberPanel machine IP is whitelisted"""
    try:
        machine_ip = get_machine_ip()
        if not machine_ip:
            return

        # Check if already whitelisted
        existing = WhitelistedIP.objects.filter(ip_address=machine_ip, is_system_ip=True).first()
        if existing:
            return

        # Remove old system IP entries (in case IP changed)
        WhitelistedIP.objects.filter(is_system_ip=True).exclude(ip_address=machine_ip).delete()

        # Add new system IP
        WhitelistedIP.objects.get_or_create(
            ip_address=machine_ip,
            defaults={
                'description': 'CyberPanel Machine IP (Auto-managed)',
                'is_system_ip': True
            }
        )
        logging.writeToFile(f"Auto Ban Plugin: Auto-whitelisted machine IP: {machine_ip}")
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error ensuring machine IP whitelisted: {str(e)}")


def _recent_bans_pagination_context(request):
    """Build context for Recent Auto-Bans table (settings page + AJAX fragment)."""
    machine_ip = get_machine_ip()
    try:
        per_page = int(request.GET.get('per_page', str(AUTO_BAN_DEFAULT_PER_PAGE)))
    except (TypeError, ValueError):
        per_page = AUTO_BAN_DEFAULT_PER_PAGE
    if per_page not in AUTO_BAN_PER_PAGE_CHOICES:
        per_page = AUTO_BAN_DEFAULT_PER_PAGE

    try:
        page_num = int(request.GET.get('page', '1'))
    except (TypeError, ValueError):
        page_num = 1
    if page_num < 1:
        page_num = 1

    bans_qs = AutoBanLog.objects.all().order_by('-banned_at')
    paginator = Paginator(bans_qs, per_page)
    recent_bans_page = paginator.get_page(page_num)

    return {
        'recent_bans_page': recent_bans_page,
        'per_page': per_page,
        'per_page_choices': AUTO_BAN_PER_PAGE_CHOICES,
        'machine_ip': machine_ip,
    }


@cyberpanel_login_required
def main_view(request):
    mailUtilities.checkHome()
    return redirect('autoBanSecurityAlerts:settings')


@cyberpanel_login_required
@unified_verification_required
def settings_view(request):
    mailUtilities.checkHome()
    try:
        config = AutoBanConfig.get_config()
    except Exception:
        from django.core.management import call_command
        try:
            call_command('migrate', 'autoBanSecurityAlerts', verbosity=0, interactive=False)
            config = AutoBanConfig.get_config()
            ensure_machine_ip_whitelisted()
        except Exception as e:
            return HttpResponse(f"<div style='padding: 20px;'><h2>Database Error</h2><p>{str(e)}</p></div>")

    # Ensure machine IP is whitelisted
    ensure_machine_ip_whitelisted()

    access_via = request.session.get('auto_ban_plugin_access_via', '')
    show_payment_ui = access_via not in ('plugin_grant', 'activation_key', 'entitlement')

    whitelisted_ips = WhitelistedIP.objects.all()
    ban_ctx = _recent_bans_pagination_context(request)

    context = {
        'plugin_name': 'Auto Ban Security Alerts',
        'version': PLUGIN_VERSION,
        'status': 'Active' if config.enabled else 'Disabled',
        'config': config,
        'has_access': True,
        'show_payment_ui': show_payment_ui,
        'access_via_grant_or_key': not show_payment_ui,
        'patreon_tier': PATREON_TIER,
        'patreon_url': PATREON_URL,
        'paypal_me_url': PAYPAL_ME_URL,
        'paypal_payment_link': PAYPAL_PAYMENT_LINK,
        'description': 'Automatically ban IP addresses from Security Alerts Detected in Recent SSH Logs.',
        'whitelisted_ips': whitelisted_ips,
        **ban_ctx,
    }
    proc = httpProc(request, 'autoBanSecurityAlerts/settings.html', context, 'managePlugins')
    return proc.render()


def _expires_display_for_autoban_log(log):
    """Human-readable expiry for export (aligned with Firewall banned IP export)."""
    from datetime import timedelta
    dur = (log.ban_duration or 'permanent').strip() or 'permanent'
    if dur == 'permanent' or not log.banned_at:
        return 'Never'
    duration_map = {'1h': 3600, '24h': 86400, '7d': 604800, '30d': 2592000}
    secs = duration_map.get(dur, 86400)
    try:
        exp_dt = log.banned_at + timedelta(seconds=secs)
        return exp_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return 'Never'


@cyberpanel_login_required
@unified_verification_required
@require_http_methods(["GET"])
def export_auto_bans_firewall_json(request):
    """
    Export all AutoBanLog rows as JSON compatible with CyberPanel
    Firewall → Import Banned IPs (expects banned_ips array, version 1.0).
    """
    mailUtilities.checkHome()
    try:
        banned_records = []
        for log in AutoBanLog.objects.all().order_by('-banned_at'):
            ip = str(log.ip_address or '').strip()
            reason = (log.ban_reason or '').strip() or 'Auto-ban (Security Alerts)'
            duration = (log.ban_duration or 'permanent').strip() or 'permanent'
            banned_on = log.banned_at.strftime('%Y-%m-%d %H:%M:%S') if log.banned_at else 'N/A'
            banned_records.append({
                'id': int(log.pk),
                'ip': ip,
                'reason': reason,
                'duration': duration,
                'banned_on': banned_on,
                'expires': _expires_display_for_autoban_log(log),
                'active': True,
                'security_alert_type': str(log.security_alert_type or ''),
            })
        export_data = {
            'version': '1.0',
            'exported_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'autoBanSecurityAlerts',
            'total_banned_ips': len(banned_records),
            'banned_ips': banned_records,
        }
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        logging.writeToFile(
            'Auto Ban Plugin: Exported %s auto-ban rows for firewall import' % len(banned_records)
        )
        response = HttpResponse(json_content, content_type='application/json; charset=utf-8')
        ts = int(time.time())
        response['Content-Disposition'] = 'attachment; filename="auto_ban_export_%s.json"' % ts
        return response
    except Exception as e:
        logging.writeToFile('Auto Ban Plugin: export_auto_bans_firewall_json failed: %s' % str(e))
        return JsonResponse({'exportStatus': 0, 'error_message': 'Export failed'}, status=500)


@cyberpanel_login_required
@unified_verification_required
def recent_bans_fragment(request):
    """Return HTML fragment for Recent Auto-Bans (AJAX pagination without full page reload)."""
    if request.method != 'GET':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        from django.template.loader import render_to_string
        ctx = _recent_bans_pagination_context(request)
        html = render_to_string(
            'autoBanSecurityAlerts/_recent_bans_fragment.html',
            ctx,
            request=request,
        )
        rp = ctx['recent_bans_page']
        return JsonResponse(
            {
                'ok': True,
                'html': html,
                'page': rp.number,
                'per_page': ctx['per_page'],
                'num_pages': rp.paginator.num_pages,
            },
            json_dumps_params={'ensure_ascii': False},
        )
    except Exception as e:
        logging.writeToFile('Auto Ban Plugin: recent_bans_fragment failed: %s' % str(e))
        return JsonResponse({'ok': False, 'error': 'Failed to load'}, status=500)


@cyberpanel_login_required
@require_manage_plugins_api
@unified_verification_required
@require_http_methods(["POST"])
@csrf_exempt
def update_config(request):
    """Update plugin configuration"""
    try:
        config = AutoBanConfig.get_config()
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        if 'enabled' in data:
            config.enabled = data.get('enabled') in [True, 'true', '1', 1]
        if 'ban_duration' in data:
            config.ban_duration = data.get('ban_duration', 'permanent')
        if 'ban_reason' in data:
            config.ban_reason = data.get('ban_reason', 'Auto-banned from Security Alerts Detected')
        if 'check_interval' in data:
            try:
                interval = int(data.get('check_interval', 60))
                if interval < 30:
                    interval = 30
                config.check_interval = interval
            except ValueError:
                pass

        config.save()

        # External systemd monitor (never in-process inside LSCPD workers)
        if config.enabled:
            start_monitoring_thread()
        else:
            stop_monitoring_service()

        return JsonResponse({'status': 1, 'message': 'Configuration updated successfully'})
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error updating config: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})


@cyberpanel_login_required
@require_manage_plugins_api
@unified_verification_required
@require_http_methods(["POST"])
@csrf_exempt
def add_whitelist_ip(request):
    """Add IP to whitelist"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        ip_address = data.get('ip_address', '').strip()
        description = data.get('description', '').strip()

        if not ip_address:
            return JsonResponse({'status': 0, 'error_message': 'IP address is required'})

        # Validate IP
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            return JsonResponse({'status': 0, 'error_message': 'Invalid IP address format'})

        # Check if already whitelisted
        if WhitelistedIP.objects.filter(ip_address=ip_address).exists():
            return JsonResponse({'status': 0, 'error_message': 'IP address is already whitelisted'})

        WhitelistedIP.objects.create(
            ip_address=ip_address,
            description=description,
            is_system_ip=False
        )

        return JsonResponse({'status': 1, 'message': 'IP address added to whitelist'})
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error adding whitelist IP: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})


@cyberpanel_login_required
@require_manage_plugins_api
@unified_verification_required
@require_http_methods(["POST"])
@csrf_exempt
def remove_whitelist_ip(request):
    """Remove IP from whitelist (cannot remove system IP)"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        ip_id = data.get('ip_id')

        if not ip_id:
            return JsonResponse({'status': 0, 'error_message': 'IP ID is required'})

        whitelist_ip = WhitelistedIP.objects.filter(pk=ip_id).first()
        if not whitelist_ip:
            return JsonResponse({'status': 0, 'error_message': 'Whitelisted IP not found'})

        if whitelist_ip.is_system_ip:
            return JsonResponse({'status': 0, 'error_message': 'Cannot delete system IP (CyberPanel machine IP)'})

        whitelist_ip.delete()
        return JsonResponse({'status': 1, 'message': 'IP address removed from whitelist'})
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error removing whitelist IP: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})


@cyberpanel_login_required
@require_manage_plugins_api
@unified_verification_required
@require_http_methods(["POST"])
@csrf_exempt
def remove_auto_ban(request):
    """Unban IP in firewall and remove the AutoBanLog row."""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        log_id = data.get('log_id')
        if log_id in (None, ''):
            return JsonResponse({'status': 0, 'error_message': 'log_id is required'})
        try:
            log_id = int(log_id)
        except (TypeError, ValueError):
            return JsonResponse({'status': 0, 'error_message': 'Invalid log_id'})

        log_entry = AutoBanLog.objects.filter(pk=log_id).first()
        if not log_entry:
            return JsonResponse({'status': 0, 'error_message': 'Log entry not found'})

        ip = str(log_entry.ip_address).strip()
        machine_ip = get_machine_ip()
        if machine_ip and ip == str(machine_ip).strip():
            return JsonResponse({'status': 0, 'error_message': 'Cannot remove ban for the CyberPanel machine IP'})

        from firewall.firewallManager import FirewallManager
        from loginSystem.models import Administrator

        admin = Administrator.objects.filter(acl__adminStatus=1).first()
        if not admin:
            return JsonResponse({'status': 0, 'error_message': 'No admin user found'})

        fm = FirewallManager()
        result = fm.removeBannedIP(admin.pk, {'ip': ip})
        parsed = _parse_firewall_http_response(result)
        err_raw = (parsed.get('error_message') or parsed.get('error') or '')
        err_msg = err_raw.strip().lower()

        if parsed.get('status') == 1:
            log_entry.delete()
            return JsonResponse({'status': 1, 'message': parsed.get('message', 'IP unbanned successfully')})

        if 'not found' in err_msg:
            log_entry.delete()
            return JsonResponse({
                'status': 1,
                'message': 'Log cleared (ban was already removed or not found in firewall)',
            })

        return JsonResponse({
            'status': 0,
            'error_message': err_raw or 'Failed to remove ban',
        })
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error removing auto-ban: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': 'Could not remove ban'})


@cyberpanel_login_required
@require_http_methods(["POST"])
def activate_key(request):
    """Activate plugin with activation key.

    Must NOT use unified_verification_required: the subscription UI POSTs JSON
    (activation_key in body). Django leaves request.POST empty for JSON, so the
    decorator would think there is no key and return HTML (subscription page),
    which breaks fetch().json() in the browser.
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        activation_key = data.get('activation_key', '').strip()
        user_email = _resolve_user_identity(request, data.get('user_email', ''))

        if not activation_key:
            return JsonResponse({'status': 0, 'error_message': 'Activation key is required'})

        request_data = {
            'activation_key': activation_key,
            'plugin_name': PLUGIN_NAME,
            'user_email': user_email,
            'server_fingerprint': get_server_fingerprint(),
            'domain': request.get_host() or '',
        }
        response_data = _api_request(REMOTE_ACTIVATION_KEY_URL, request_data)

        if response_data.get('success', False) and response_data.get('has_access', False):
            try:
                config = AutoBanConfig.get_config()
                config.activation_key = activation_key
                config.save(update_fields=['activation_key', 'updated_at'])
                _persist_entitlement_from_response(config, response_data)
                _persist_activation_in_cyberpanel_db(request, activation_key)
            except Exception as e:
                logging.writeToFile(f"Auto Ban Plugin: Could not persist activation key: {str(e)}")

            return JsonResponse({
                'status': 1,
                'message': response_data.get('message', 'Plugin activated successfully'),
                'has_access': True
            })
        else:
            return JsonResponse({
                'status': 0,
                'error_message': response_data.get('message', 'Invalid activation key'),
                'has_access': False
            })
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Activation key error: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})


def auto_ban_ip(ip_address, alert_type='', reason=''):
    """Ban an IP address using the firewall manager"""
    try:
        from firewall.firewallManager import FirewallManager
        from loginSystem.models import Administrator

        # Get first admin user for the ban operation
        admin = Administrator.objects.filter(acl__adminStatus=1).first()
        if not admin:
            logging.writeToFile("Auto Ban Plugin: No admin user found for banning IP")
            return False

        config = AutoBanConfig.get_config()
        ban_reason = reason or config.ban_reason
        if alert_type:
            ban_reason = f"{ban_reason} - {alert_type}"

        fm = FirewallManager()
        data = {
            'ip': ip_address,
            'reason': ban_reason,
            'duration': config.ban_duration
        }

        result = fm.addBannedIP(admin.pk, data)

        # Check if ban was successful
        if hasattr(result, 'status_code'):
            # HttpResponse object
            if result.status_code == 200:
                try:
                    result_data = json.loads(result.content)
                    if result_data.get('status') == 1:
                        # Log the ban
                        AutoBanLog.objects.create(
                            ip_address=ip_address,
                            ban_reason=ban_reason,
                            ban_duration=config.ban_duration,
                            security_alert_type=alert_type
                        )
                        logging.writeToFile(f"Auto Ban Plugin: Successfully banned IP {ip_address} - {ban_reason}")
                        return True
                except Exception:
                    pass
        elif isinstance(result, dict) and result.get('status') == 1:
            # Already a dict with status
            AutoBanLog.objects.create(
                ip_address=ip_address,
                ban_reason=ban_reason,
                ban_duration=config.ban_duration,
                security_alert_type=alert_type
            )
            logging.writeToFile(f"Auto Ban Plugin: Successfully banned IP {ip_address} - {ban_reason}")
            return True

        logging.writeToFile(f"Auto Ban Plugin: Failed to ban IP {ip_address}")
        return False
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error banning IP {ip_address}: {str(e)}")
        return False


def get_security_alerts():
    """Get current security alerts by calling analyzeSSHSecurity logic directly"""
    try:
        from plogical.processUtilities import ProcessUtilities
        import re
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        alerts = []
        
        # Determine log path
        distro = ProcessUtilities.decideDistro()
        if distro in [ProcessUtilities.ubuntu, ProcessUtilities.ubuntu20]:
            log_path = '/var/log/auth.log'
        else:
            log_path = '/var/log/secure'
        
        try:
            # Get last 500 lines for better analysis
            output = ProcessUtilities.outputExecutioner(f'tail -n 500 {log_path}')
        except Exception as e:
            logging.writeToFile(f"Auto Ban Plugin: Failed to read log: {str(e)}")
            return []
        
        lines = output.split('\n')
        
        # Analysis patterns
        failed_passwords = defaultdict(int)
        invalid_users = defaultdict(int)
        root_login_attempts = []
        
        for line in lines:
            if not line.strip():
                continue
            
            # Failed password attempts
            if 'Failed password' in line:
                match = re.search(r'Failed password for (?:invalid user )?(\S+) from (\S+)', line)
                if match:
                    user, ip = match.groups()
                    failed_passwords[ip] += 1
                    
                    # Check for root login attempts
                    if user == 'root':
                        root_login_attempts.append({
                            'ip': ip,
                            'line': line
                        })
            
            # Invalid user attempts
            elif 'Invalid user' in line or 'invalid user' in line:
                match = re.search(r'[Ii]nvalid user (\S+) from (\S+)', line)
                if match:
                    user, ip = match.groups()
                    invalid_users[ip] += 1
        
        # Generate alerts based on analysis
        # High severity: Brute force attacks
        for ip, count in failed_passwords.items():
            if count >= 10:
                alerts.append({
                    'title': 'Brute Force Attack Detected',
                    'description': f'IP address {ip} has made {count} failed password attempts.',
                    'severity': 'high',
                    'details': {
                        'IP Address': ip,
                        'Failed Attempts': count,
                        'Attack Type': 'Brute Force'
                    },
                    'ips': [ip],
                })
        
        # High severity: Root login attempts
        if root_login_attempts:
            from collections import Counter
            counts = Counter(r["ip"] for r in root_login_attempts)
            unique_ips = [ip for ip, _c in counts.most_common()]
            top_ip = unique_ips[0]
            alerts.append({
                'title': 'Root Login Attempts Detected',
                'description': f'Direct root login attempts detected from {len(unique_ips)} IP addresses.',
                'severity': 'high',
                'details': {
                    'Unique IPs': len(unique_ips),
                    'Total Attempts': len(root_login_attempts),
                    'Top IP': top_ip,
                    'IP Address': top_ip,
                    'All IPs': ', '.join(unique_ips[:30]),
                },
                'ips': unique_ips,
            })
        
        # Medium severity: Dictionary attacks
        for ip, count in invalid_users.items():
            if count >= 5:
                alerts.append({
                    'title': 'Dictionary Attack Detected',
                    'description': f'IP address {ip} attempted to login with {count} non-existent usernames.',
                    'severity': 'medium',
                    'details': {
                        'IP Address': ip,
                        'Invalid User Attempts': count,
                        'Attack Type': 'Dictionary Attack'
                    },
                    'ips': [ip],
                })
        
        return alerts
    except Exception as e:
        logging.writeToFile(f"Auto Ban Plugin: Error getting security alerts: {str(e)}")
        return []


def extract_ips_from_alerts(alerts):
    """Extract IP addresses from security alerts (all attackers, not only Top IP)."""
    import re
    seen = set()
    ips = []
    for alert in alerts:
        for ip in alert.get('ips') or []:
            ip = str(ip).strip()
            if ip and ip not in seen:
                seen.add(ip)
                ips.append({
                    'ip': ip,
                    'type': alert.get('title', ''),
                    'severity': alert.get('severity', 'medium')
                })
        details = alert.get('details', {}) or {}
        candidates = []
        for key in ('IP Address', 'Top IP'):
            if details.get(key):
                candidates.append(details.get(key))
        all_ips = details.get('All IPs') or ''
        if all_ips:
            candidates.extend([p.strip() for p in str(all_ips).split(',') if p.strip()])
        for ip in candidates:
            ip = str(ip).strip()
            if not ip or ip in seen:
                continue
            # Skip non-IP detail values like Unique IPs counts
            if not re.match(r'^[0-9a-fA-F:.]+$', ip):
                continue
            seen.add(ip)
            ips.append({
                'ip': ip,
                'type': alert.get('title', ''),
                'severity': alert.get('severity', 'medium')
            })
    return ips


def monitoring_worker():
    """Deprecated in-process loop. Prefer systemd cyberpanel-autoban.service."""
    from autoBanSecurityAlerts.monitor_service import run_loop
    run_loop()


def stop_monitoring_service():
    """Stop the external Auto Ban systemd unit."""
    try:
        from plogical.processUtilities import ProcessUtilities
        ProcessUtilities.executioner('systemctl stop cyberpanel-autoban.service')
        logging.writeToFile('Auto Ban Plugin: Stopped cyberpanel-autoban.service')
    except Exception as e:
        logging.writeToFile('Auto Ban Plugin: Could not stop monitor service: %s' % e)


def start_monitoring_thread():
    """
    Start Auto Ban via systemd (outside LSCPD).

    In-process threads inside lswsgi deadlock the panel: workers call
    ProcessUtilities over UDS while OLS holds all worker slots.
    """
    try:
        from plogical.processUtilities import ProcessUtilities
        ProcessUtilities.executioner('systemctl enable cyberpanel-autoban.service')
        ProcessUtilities.executioner('systemctl restart cyberpanel-autoban.service')
        logging.writeToFile('Auto Ban Plugin: Started cyberpanel-autoban.service')
    except Exception as e:
        logging.writeToFile('Auto Ban Plugin: Could not start monitor service: %s' % e)


# Do not auto-start monitors on import (would run inside every LSCPD worker).
