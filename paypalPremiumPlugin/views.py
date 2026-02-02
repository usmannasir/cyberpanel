# -*- coding: utf-8 -*-
"""
PayPal Premium Plugin Views - Unified Verification (same as contaboAutoSnapshot)
Supports: Plugin Grants, Activation Key, Patreon, PayPal, AES encryption
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from plogical.mailUtilities import mailUtilities
from plogical.httpProc import httpProc
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from functools import wraps
import urllib.request
import urllib.error
import json
import time

from .models import PaypalPremiumPluginConfig
from . import api_encryption

PLUGIN_NAME = 'paypalPremiumPlugin'
PLUGIN_VERSION = '1.0.2'

REMOTE_VERIFICATION_PATREON_URL = 'https://api.newstargeted.com/api/verify-patreon-membership.php'
REMOTE_VERIFICATION_PAYPAL_URL = 'https://api.newstargeted.com/api/verify-paypal-payment.php'
REMOTE_VERIFICATION_PLUGIN_GRANT_URL = 'https://api.newstargeted.com/api/verify-plugin-grant.php'
REMOTE_ACTIVATION_KEY_URL = 'https://api.newstargeted.com/api/activate-plugin-key.php'

PATREON_TIER = 'CyberPanel Paid Plugin'
PATREON_URL = 'https://www.patreon.com/membership/27789984'
PAYPAL_ME_URL = 'https://paypal.me/KimBS?locale.x=en_US&country.x=NO'
PAYPAL_PAYMENT_LINK = ''


def cyberpanel_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            if not request.session.get('userID'):
                from loginSystem.views import loadLoginPage
                return redirect(loadLoginPage)
            return view_func(request, *args, **kwargs)
        except KeyError:
            from loginSystem.views import loadLoginPage
            return redirect(loadLoginPage)
    return _wrapped_view


def _api_request(url, data, timeout=10):
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
        logging.writeToFile(f"PayPal Premium Plugin: API request error to {url}: {str(e)}")
        return {}


def check_plugin_grant(user_email, user_ip='', domain=''):
    try:
        request_data = {
            'user_email': user_email or '',
            'plugin_name': PLUGIN_NAME,
            'user_ip': user_ip,
            'domain': domain,
        }
        data = _api_request(REMOTE_VERIFICATION_PLUGIN_GRANT_URL, request_data)
        if data.get('success') and data.get('has_access'):
            return {'has_access': True, 'message': data.get('message', 'Access granted via Plugin Grants')}
        return {'has_access': False, 'message': data.get('message', '')}
    except Exception as e:
        logging.writeToFile(f"PayPal Premium Plugin: Plugin grant check error: {str(e)}")
        return {'has_access': False, 'message': ''}


def check_patreon_membership(user_email, user_ip='', domain=''):
    try:
        request_data = {
            'user_email': user_email,
            'plugin_name': PLUGIN_NAME,
            'plugin_version': PLUGIN_VERSION,
            'user_ip': user_ip,
            'domain': domain,
            'tier_id': '27789984'
        }
        response_data = _api_request(REMOTE_VERIFICATION_PATREON_URL, request_data)
        if response_data.get('success', False):
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
        logging.writeToFile(f"PayPal Premium Plugin: Patreon check error: {str(e)}")
        return {'has_access': False, 'patreon_tier': PATREON_TIER, 'patreon_url': PATREON_URL, 'message': 'Unable to verify Patreon.', 'error': str(e)}


def check_paypal_payment(user_email, user_ip='', domain=''):
    try:
        request_data = {
            'user_email': user_email,
            'plugin_name': PLUGIN_NAME,
            'plugin_version': PLUGIN_VERSION,
            'user_ip': user_ip,
            'domain': domain,
            'timestamp': int(time.time()),
        }
        response_data = _api_request(REMOTE_VERIFICATION_PAYPAL_URL, request_data)
        if response_data.get('success', False):
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
        logging.writeToFile(f"PayPal Premium Plugin: PayPal check error: {str(e)}")
        return {'has_access': False, 'paypal_me_url': PAYPAL_ME_URL, 'paypal_payment_link': PAYPAL_PAYMENT_LINK, 'message': 'Unable to verify PayPal.', 'error': str(e)}


def unified_verification_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            if not request.session.get('userID'):
                from loginSystem.views import loadLoginPage
                return redirect(loadLoginPage)

            user_email = request.session.get('email', '') or (getattr(request.user, 'email', '') if hasattr(request, 'user') and request.user else '') or getattr(request.user, 'username', '')

            try:
                config = PaypalPremiumPluginConfig.get_config()
                payment_method = config.payment_method
            except Exception:
                payment_method = 'both'

            has_access = False
            verification_result = {}

            activation_key = request.GET.get('activation_key') or request.POST.get('activation_key')
            if not activation_key:
                try:
                    config = PaypalPremiumPluginConfig.get_config()
                    activation_key = getattr(config, 'activation_key', '') or ''
                except Exception:
                    activation_key = ''

            if activation_key:
                try:
                    request_data = {'activation_key': activation_key.strip(), 'plugin_name': PLUGIN_NAME, 'user_email': user_email}
                    response_data = _api_request(REMOTE_ACTIVATION_KEY_URL, request_data)
                    if response_data.get('success', False) and response_data.get('has_access', False):
                        has_access = True
                        verification_result = {'method': 'activation_key', 'has_access': True, 'message': response_data.get('message', 'Access activated via key')}
                        try:
                            config = PaypalPremiumPluginConfig.get_config()
                            config.activation_key = activation_key.strip()
                            config.save(update_fields=['activation_key', 'updated_at'])
                        except Exception as e:
                            logging.writeToFile(f"PayPal Premium Plugin: Could not persist activation key: {str(e)}")
                    elif not response_data.get('success') and activation_key:
                        try:
                            config = PaypalPremiumPluginConfig.get_config()
                            if getattr(config, 'activation_key', '') == activation_key.strip():
                                config.activation_key = ''
                                config.save(update_fields=['activation_key', 'updated_at'])
                        except Exception:
                            pass
                except Exception as e:
                    logging.writeToFile(f"PayPal Premium Plugin: Activation key check error: {str(e)}")

            if not has_access:
                grant_result = check_plugin_grant(user_email, request.META.get('REMOTE_ADDR', ''), request.get_host())
                if grant_result.get('has_access'):
                    has_access = True
                    verification_result = {'method': 'plugin_grant', 'has_access': True, 'message': grant_result.get('message', 'Access granted via Plugin Grants')}

            if not has_access:
                try:
                    if payment_method == 'patreon':
                        result = check_patreon_membership(user_email, request.META.get('REMOTE_ADDR', ''), request.get_host())
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
                        result = check_paypal_payment(user_email, request.META.get('REMOTE_ADDR', ''), request.get_host())
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
                        patreon_result = check_patreon_membership(user_email, request.META.get('REMOTE_ADDR', ''), request.get_host())
                        paypal_result = check_paypal_payment(user_email, request.META.get('REMOTE_ADDR', ''), request.get_host())
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
                    logging.writeToFile(f"PayPal Premium Plugin: Verification error: {str(e)}")
                    has_access = False
                    verification_result = {
                        'method': payment_method, 'has_access': False,
                        'patreon_tier': PATREON_TIER, 'patreon_url': PATREON_URL,
                        'paypal_me_url': PAYPAL_ME_URL, 'paypal_payment_link': PAYPAL_PAYMENT_LINK,
                        'message': 'Unable to verify access.', 'error': str(e)
                    }

            if not has_access:
                context = {
                    'plugin_name': 'PayPal Premium Plugin Example',
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
                proc = httpProc(request, 'paypalPremiumPlugin/subscription_required.html', context, 'admin')
                return proc.render()

            if has_access and verification_result:
                request.session['paypal_premium_access_via'] = verification_result.get('method', '')

            return view_func(request, *args, **kwargs)
        except Exception as e:
            logging.writeToFile(f"PayPal Premium Plugin: Decorator error: {str(e)}")
            return HttpResponse(f"<div style='padding: 20px;'><h2>Plugin Error</h2><p>{str(e)}</p></div>")
    return _wrapped_view


@cyberpanel_login_required
def main_view(request):
    mailUtilities.checkHome()
    return redirect('paypalPremiumPlugin:settings')


@cyberpanel_login_required
@unified_verification_required
def settings_view(request):
    mailUtilities.checkHome()
    try:
        config = PaypalPremiumPluginConfig.get_config()
    except Exception:
        from django.core.management import call_command
        try:
            call_command('migrate', 'paypalPremiumPlugin', verbosity=0, interactive=False)
            config = PaypalPremiumPluginConfig.get_config()
        except Exception as e:
            return HttpResponse(f"<div style='padding: 20px;'><h2>Database Error</h2><p>{str(e)}</p></div>")

    access_via = request.session.get('paypal_premium_access_via', '')
    show_payment_ui = access_via not in ('plugin_grant', 'activation_key')

    context = {
        'plugin_name': 'PayPal Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'status': 'Active',
        'config': config,
        'has_access': True,
        'show_payment_ui': show_payment_ui,
        'access_via_grant_or_key': not show_payment_ui,
        'patreon_tier': PATREON_TIER,
        'patreon_url': PATREON_URL,
        'paypal_me_url': PAYPAL_ME_URL,
        'paypal_payment_link': PAYPAL_PAYMENT_LINK,
        'description': 'Configure your PayPal premium plugin settings.',
    }
    proc = httpProc(request, 'paypalPremiumPlugin/settings.html', context, 'admin')
    return proc.render()


@cyberpanel_login_required
@require_http_methods(["POST"])
def activate_key(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        activation_key = data.get('activation_key', '').strip()
        user_email = data.get('user_email', '').strip()
        if not user_email:
            user_email = request.session.get('email', '') or (getattr(request.user, 'email', '') if hasattr(request, 'user') and request.user else '')

        if not activation_key:
            return JsonResponse({'success': False, 'message': 'Activation key is required'}, status=400)

        request_data = {'activation_key': activation_key, 'plugin_name': PLUGIN_NAME, 'user_email': user_email}
        response_data = _api_request(REMOTE_ACTIVATION_KEY_URL, request_data)

        if response_data.get('success', False) and response_data.get('has_access', False):
            try:
                config = PaypalPremiumPluginConfig.get_config()
                config.activation_key = activation_key
                config.save(update_fields=['activation_key', 'updated_at'])
            except Exception as e:
                logging.writeToFile(f"PayPal Premium Plugin: Could not persist activation key: {str(e)}")

            return JsonResponse({
                'success': True,
                'has_access': True,
                'message': response_data.get('message', 'Access activated successfully')
            })

        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': response_data.get('message', 'Invalid activation key')
        })

    except Exception as e:
        logging.writeToFile(f"PayPal Premium Plugin: activate_key error: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@cyberpanel_login_required
@require_http_methods(["POST"])
def save_payment_method(request):
    try:
        payment_method = request.POST.get('payment_method', 'both')
        if payment_method not in ('patreon', 'paypal', 'both'):
            payment_method = 'both'
        config = PaypalPremiumPluginConfig.get_config()
        config.payment_method = payment_method
        config.save(update_fields=['payment_method', 'updated_at'])
        return JsonResponse({'success': True, 'message': 'Payment method saved'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@cyberpanel_login_required
@unified_verification_required
def api_status_view(request):
    return JsonResponse({
        'plugin_name': 'PayPal Premium Plugin Example',
        'version': PLUGIN_VERSION,
        'status': 'active',
        'payment': 'verified',
        'verification_method': 'unified'
    })
