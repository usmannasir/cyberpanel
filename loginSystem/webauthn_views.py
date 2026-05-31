# -*- coding: utf-8 -*-

import json
import base64
from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import Administrator
from .webauthn_backend import WebAuthnBackend
from .webauthn_models import WebAuthnSettings, WebAuthnCredential
from plogical.acl import ACLManager
from django.http import JsonResponse
from plogical.usernameUtils import resolve_administrator_by_login_name, GENERIC_AUTH_FAIL

import logging

logger = logging.getLogger(__name__)


class WebAuthnAPIView(View):
    """Base class for WebAuthn API views"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.webauthn = WebAuthnBackend()
    
    def json_response(self, data, status=200):
        """Return JSON response"""
        return HttpResponse(
            json.dumps(data, ensure_ascii=False),
            content_type='application/json',
            status=status
        )
    
    def error_response(self, message, status=400):
        """Return error response"""
        return self.json_response({
            'success': False,
            'error': message
        }, status)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnRegistrationStart(WebAuthnAPIView):
    """Start WebAuthn registration process"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get('username')
            credential_name = data.get('credential_name', '')
            
            if not username:
                return self.error_response('Username is required')
            
            try:
                user, exact = resolve_administrator_by_login_name(username)
                if not user or not exact:
                    return self.error_response(GENERIC_AUTH_FAIL, 403)
            except Administrator.DoesNotExist:
                return self.error_response('User not found', 404)
            
            # Check if user has permission to register WebAuthn
            if hasattr(request, 'session') and 'userID' in request.session:
                current_user_id = request.session['userID']
                current_user = Administrator.objects.get(pk=current_user_id)
                current_acl = ACLManager.loadedACL(current_user_id)
                
                # Allow if admin, user is modifying themselves, or user is owned by current user
                if not (current_acl['admin'] == 1 or 
                       user.pk == current_user.pk or 
                       user.owner == current_user.pk):
                    return self.error_response('Unauthorized access', 403)
            
            result = self.webauthn.create_registration_challenge(user, credential_name, request=request)
            return self.json_response(result)
            
        except json.JSONDecodeError:
            return self.error_response('Invalid JSON')
        except Exception as e:
            logger.error(f"Error in registration start: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnRegistrationComplete(WebAuthnAPIView):
    """Complete WebAuthn registration process"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            challenge_id = data.get('challenge_id')
            credential_data = data.get('credential')
            client_data_json = data.get('client_data_json')
            attestation_object = data.get('attestation_object')
            
            if not all([challenge_id, credential_data, client_data_json, attestation_object]):
                return self.error_response('Missing required fields')
            
            result = self.webauthn.verify_registration(
                challenge_id=challenge_id,
                credential_data=credential_data,
                client_data_json=client_data_json,
                attestation_object=attestation_object,
                request=request,
            )
            
            return self.json_response(result)
            
        except json.JSONDecodeError:
            return self.error_response('Invalid JSON')
        except Exception as e:
            logger.error(f"Error in registration complete: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnAuthenticationStart(WebAuthnAPIView):
    """Start WebAuthn authentication process"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get('username')
            
            if not username:
                return self.error_response('Username is required')
            
            try:
                user, exact = resolve_administrator_by_login_name(username)
                if not user or not exact:
                    return self.error_response(GENERIC_AUTH_FAIL, 403)
            except Administrator.DoesNotExist:
                return self.error_response('User not found', 404)
            
            result = self.webauthn.create_authentication_challenge(user, request=request)
            return self.json_response(result)
            
        except json.JSONDecodeError:
            return self.error_response('Invalid JSON')
        except Exception as e:
            logger.error(f"Error in authentication start: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnAuthenticationComplete(WebAuthnAPIView):
    """Complete WebAuthn authentication (username-first or passkey-first)."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            credential_data = data.get('credential')
            if not credential_data:
                return self.error_response('Missing credential')

            # Passkey-first: credential only, challenge in session
            challenge_id = data.get('challenge_id')
            if not challenge_id:
                result = self.webauthn.verify_passkey_first_authentication(credential_data, request)
                if result.get('success'):
                    request.session['userID'] = result['user_id']
                    request.session['webauthn_auth'] = True
                    request.session.set_expiry(43200)
                    ip_addr = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR', '')
                    if ip_addr.find(':') > -1:
                        ip_addr = ':'.join(ip_addr.split(':')[:3])
                    request.session['ipAddr'] = ip_addr
                    redirect_url = data.get('redirect') or request.session.pop('webauthn_redirect', '/') or '/'
                    if '//' in redirect_url or not redirect_url.startswith('/'):
                        redirect_url = '/'
                    result['redirect'] = redirect_url
                    logger.info(f"WebAuthn passkey-first authentication successful for user ID: {result['user_id']}")
                return self.json_response(result)

            # Username-first: challenge_id + credential parts
            client_data_json = data.get('client_data_json')
            authenticator_data = data.get('authenticator_data')
            if not all([client_data_json, authenticator_data]):
                return self.error_response('Missing required fields for username-first auth')
            result = self.webauthn.verify_authentication(
                challenge_id=challenge_id,
                credential_data=credential_data,
                client_data_json=client_data_json,
                authenticator_data=authenticator_data,
                request=request,
            )
            if result.get('success'):
                request.session['userID'] = result['user_id']
                request.session['webauthn_auth'] = True
                request.session.set_expiry(43200)
                ip_addr = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR', '')
                if ip_addr.find(':') > -1:
                    ip_addr = ':'.join(ip_addr.split(':')[:3])
                request.session['ipAddr'] = ip_addr
                logger.info(f"WebAuthn authentication successful for user ID: {result['user_id']}")
            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response('Invalid JSON')
        except Exception as e:
            logger.error(f"Error in authentication complete: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnCredentialsList(WebAuthnAPIView):
    """List WebAuthn credentials for a user"""
    
    def get(self, request, username=None):
        try:
            if not username:
                return self.error_response('Username is required')
            
            try:
                user, exact = resolve_administrator_by_login_name(username)
                if not user or not exact:
                    return self.error_response(GENERIC_AUTH_FAIL, 403)
            except Administrator.DoesNotExist:
                return self.error_response('User not found', 404)
            
            # Check permissions
            if hasattr(request, 'session') and 'userID' in request.session:
                current_user_id = request.session['userID']
                current_user = Administrator.objects.get(pk=current_user_id)
                current_acl = ACLManager.loadedACL(current_user_id)
                
                if not (current_acl['admin'] == 1 or 
                       user.pk == current_user.pk or 
                       user.owner == current_user.pk):
                    return self.error_response('Unauthorized access', 403)
            
            from django.db.utils import OperationalError, ProgrammingError
            try:
                credentials = self.webauthn.get_user_credentials(user)
                settings = WebAuthnSettings.get_or_create_settings(user)
            except (OperationalError, ProgrammingError) as db_err:
                if 'webauthn' not in str(db_err).lower():
                    raise
                credentials = []
                settings = WebAuthnSettings(
                    user=user,
                    enabled=False,
                    require_passkey=False,
                    allow_multiple_credentials=True,
                    max_credentials=10,
                )
            
            return self.json_response({
                'success': True,
                'credentials': credentials,
                'settings': {
                    'enabled': settings.enabled,
                    'require_passkey': settings.require_passkey,
                    'allow_multiple_credentials': settings.allow_multiple_credentials,
                    'max_credentials': settings.max_credentials,
                    'can_add_credential': settings.can_add_credential(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error listing credentials: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnCredentialDelete(WebAuthnAPIView):
    """Delete a WebAuthn credential"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get('username')
            credential_id = data.get('credential_id')
            
            if not username or not credential_id:
                return self.error_response('Username and credential ID are required')
            
            try:
                user, exact = resolve_administrator_by_login_name(username)
                if not user or not exact:
                    return self.error_response(GENERIC_AUTH_FAIL, 403)
            except Administrator.DoesNotExist:
                return self.error_response('User not found', 404)
            
            # Check permissions
            if hasattr(request, 'session') and 'userID' in request.session:
                current_user_id = request.session['userID']
                current_user = Administrator.objects.get(pk=current_user_id)
                current_acl = ACLManager.loadedACL(current_user_id)
                
                if not (current_acl['admin'] == 1 or 
                       user.pk == current_user.pk or 
                       user.owner == current_user.pk):
                    return self.error_response('Unauthorized access', 403)
            
            result = self.webauthn.delete_credential(user, credential_id)
            return self.json_response(result)
            
        except json.JSONDecodeError:
            return self.error_response('Invalid JSON')
        except Exception as e:
            logger.error(f"Error deleting credential: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnCredentialUpdate(WebAuthnAPIView):
    """Update WebAuthn credential name"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get('username')
            credential_id = data.get('credential_id')
            new_name = data.get('new_name')
            
            if not all([username, credential_id, new_name]):
                return self.error_response('Username, credential ID, and new name are required')
            
            try:
                user, exact = resolve_administrator_by_login_name(username)
                if not user or not exact:
                    return self.error_response(GENERIC_AUTH_FAIL, 403)
            except Administrator.DoesNotExist:
                return self.error_response('User not found', 404)
            
            # Check permissions
            if hasattr(request, 'session') and 'userID' in request.session:
                current_user_id = request.session['userID']
                current_user = Administrator.objects.get(pk=current_user_id)
                current_acl = ACLManager.loadedACL(current_user_id)
                
                if not (current_acl['admin'] == 1 or 
                       user.pk == current_user.pk or 
                       user.owner == current_user.pk):
                    return self.error_response('Unauthorized access', 403)
            
            result = self.webauthn.update_credential_name(user, credential_id, new_name)
            return self.json_response(result)
            
        except json.JSONDecodeError:
            return self.error_response('Invalid JSON')
        except Exception as e:
            logger.error(f"Error updating credential: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnSettingsUpdate(WebAuthnAPIView):
    """Update WebAuthn settings for a user"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get('username')
            enabled = data.get('enabled')
            require_passkey = data.get('require_passkey')
            allow_multiple_credentials = data.get('allow_multiple_credentials')
            max_credentials = data.get('max_credentials')
            timeout_seconds = data.get('timeout_seconds')
            
            if not username:
                return self.error_response('Username is required')
            
            try:
                user, exact = resolve_administrator_by_login_name(username)
                if not user or not exact:
                    return self.error_response(GENERIC_AUTH_FAIL, 403)
            except Administrator.DoesNotExist:
                return self.error_response('User not found', 404)
            
            # Check permissions
            if hasattr(request, 'session') and 'userID' in request.session:
                current_user_id = request.session['userID']
                current_user = Administrator.objects.get(pk=current_user_id)
                current_acl = ACLManager.loadedACL(current_user_id)
                
                if not (current_acl['admin'] == 1 or 
                       user.pk == current_user.pk or 
                       user.owner == current_user.pk):
                    return self.error_response('Unauthorized access', 403)
            
            settings = WebAuthnSettings.get_or_create_settings(user)
            
            if enabled is not None:
                settings.enabled = bool(enabled)
            if require_passkey is not None:
                settings.require_passkey = bool(require_passkey)
            if allow_multiple_credentials is not None:
                settings.allow_multiple_credentials = bool(allow_multiple_credentials)
            if max_credentials is not None:
                settings.max_credentials = int(max_credentials)
            if timeout_seconds is not None:
                settings.timeout_seconds = int(timeout_seconds)
            
            settings.save()
            
            return self.json_response({
                'success': True,
                'message': 'Settings updated successfully',
                'settings': {
                    'enabled': settings.enabled,
                    'require_passkey': settings.require_passkey,
                    'allow_multiple_credentials': settings.allow_multiple_credentials,
                    'max_credentials': settings.max_credentials,
                    'timeout_seconds': settings.timeout_seconds,
                }
            })
            
        except json.JSONDecodeError:
            return self.error_response('Invalid JSON')
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnCleanup(WebAuthnAPIView):
    """Cleanup expired WebAuthn data"""
    
    def post(self, request):
        try:
            # Check if user is admin
            if not (hasattr(request, 'session') and 'userID' in request.session):
                return self.error_response('Authentication required', 401)
            
            current_user_id = request.session['userID']
            current_acl = ACLManager.loadedACL(current_user_id)
            
            if current_acl['admin'] != 1:
                return self.error_response('Admin access required', 403)
            
            # Cleanup expired data
            self.webauthn.cleanup_expired_challenges()
            self.webauthn.cleanup_expired_sessions()
            
            return self.json_response({
                'success': True,
                'message': 'Cleanup completed successfully'
            })
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return self.error_response(f'Internal server error: {str(e)}', 500)


# Passkey-first authentication (no username): GET options
@csrf_exempt
@require_http_methods(["GET"])
def webauthn_authentication_options(request):
    """GET authentication options for all credentials (passkey-first login)."""
    try:
        backend = WebAuthnBackend(request=request)
        result = backend.create_passkey_first_options(request)
        if not result.get('success'):
            return HttpResponse(
                json.dumps(result, ensure_ascii=False),
                content_type='application/json',
                status=400,
            )
        redirect_url = request.GET.get('return', '/')
        if '//' in redirect_url or not redirect_url.startswith('/'):
            redirect_url = '/'
        request.session['webauthn_redirect'] = redirect_url
        return HttpResponse(
            json.dumps(result, ensure_ascii=False),
            content_type='application/json',
        )
    except Exception as e:
        logger.error(f"Error in authentication options: {str(e)}")
        return HttpResponse(
            json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False),
            content_type='application/json',
            status=500,
        )


# Traditional function-based views for easier integration (pass request into backend)
@csrf_exempt
def webauthn_registration_start(request):
    """Start WebAuthn registration - function view"""
    view = WebAuthnRegistrationStart()
    view.webauthn = WebAuthnBackend(request=request)
    return view.post(request)


@csrf_exempt
def webauthn_registration_complete(request):
    """Complete WebAuthn registration - function view"""
    view = WebAuthnRegistrationComplete()
    view.webauthn = WebAuthnBackend(request=request)
    return view.post(request)


@csrf_exempt
def webauthn_authentication_start(request):
    """Start WebAuthn authentication - function view"""
    view = WebAuthnAuthenticationStart()
    view.webauthn = WebAuthnBackend(request=request)
    return view.post(request)


@csrf_exempt
@csrf_exempt
def webauthn_authentication_complete(request):
    """Complete WebAuthn authentication - function view (username-first or passkey-first)"""
    view = WebAuthnAuthenticationComplete()
    view.webauthn = WebAuthnBackend(request=request)
    return view.post(request)


@csrf_exempt
def webauthn_credentials_list(request, username):
    """List WebAuthn credentials - function view"""
    view = WebAuthnCredentialsList()
    return view.get(request, username)


@csrf_exempt
def webauthn_credential_delete(request):
    """Delete WebAuthn credential - function view"""
    view = WebAuthnCredentialDelete()
    return view.post(request)


@csrf_exempt
def webauthn_credential_update(request):
    """Update WebAuthn credential - function view"""
    view = WebAuthnCredentialUpdate()
    return view.post(request)


@csrf_exempt
def webauthn_settings_update(request):
    """Update WebAuthn settings - function view"""
    view = WebAuthnSettingsUpdate()
    return view.post(request)


@csrf_exempt
def webauthn_cleanup(request):
    """Cleanup WebAuthn data - function view"""
    view = WebAuthnCleanup()
    return view.post(request)
