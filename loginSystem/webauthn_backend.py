# -*- coding: utf-8 -*-
"""
WebAuthn backend using webauthn library. rp_id and origin are never hardcoded;
they are derived from the current request only.
"""

import json
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from .models import Administrator
from .webauthn_models import WebAuthnCredential, WebAuthnChallenge, WebAuthnSession, WebAuthnSettings
import logging

logger = logging.getLogger(__name__)

# Optional webauthn library (pip install webauthn)
try:
    from webauthn.registration.generate_registration_options import generate_registration_options
    from webauthn.registration.verify_registration_response import verify_registration_response
    from webauthn.authentication.generate_authentication_options import generate_authentication_options
    from webauthn.authentication.verify_authentication_response import verify_authentication_response
    from webauthn.helpers import (
        options_to_json,
        base64url_to_bytes,
        bytes_to_base64url,
    )
    from webauthn.helpers.structs import (
        PublicKeyCredentialDescriptor,
        PublicKeyCredentialType,
        UserVerificationRequirement,
    )
    from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse
    WEBAUTHN_LIB_AVAILABLE = True
except ImportError:
    WEBAUTHN_LIB_AVAILABLE = False


def _rp_id_and_origin_from_request(request) -> tuple:
    """Derive rp_id and origin from the current request. Never hardcode."""
    if request is None:
        raise ValueError("Request is required to derive rp_id and origin")
    host = request.get_host().split(':')[0]
    # Origin: scheme + host + port if non-default
    base_uri = request.build_absolute_uri('/')
    parsed = urlparse(base_uri)
    if (parsed.scheme == 'https' and parsed.port in (443, None)) or (parsed.scheme == 'http' and parsed.port in (80, None)):
        origin = f"{parsed.scheme}://{parsed.hostname}"
    else:
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        origin = f"{parsed.scheme}://{parsed.hostname}:{port}"
    rp_id = host
    return rp_id, origin


class WebAuthnBackend:
    """
    WebAuthn backend. rp_id and origin are derived from request only (never hardcoded).
    """

    def __init__(self, request=None):
        self._request = request
        self.challenge_timeout = 300

    def _get_rp(self, request=None):
        req = request or self._request
        rp_id, _ = _rp_id_and_origin_from_request(req)
        return rp_id, 'CyberPanel'

    def _get_origin(self, request=None):
        _, origin = _rp_id_and_origin_from_request(request or self._request)
        return origin

    def generate_challenge(self) -> str:
        """Generate a random challenge (base64url)."""
        if WEBAUTHN_LIB_AVAILABLE:
            return bytes_to_base64url(secrets.token_bytes(32))
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').replace('+', '-').replace('/', '_').rstrip('=')

    def create_registration_challenge(self, user: Administrator, credential_name: str = None, request=None) -> Dict[str, Any]:
        """Create a WebAuthn registration challenge. Uses request for rp_id/origin."""
        if not WEBAUTHN_LIB_AVAILABLE:
            return {'success': False, 'error': 'WebAuthn library not installed'}
        try:
            req = request or self._request
            if req is None:
                return {'success': False, 'error': 'Request required for registration'}
            rp_id, rp_name = self._get_rp(req)
            settings_obj = WebAuthnSettings.get_or_create_settings(user)
            if not settings_obj.can_add_credential():
                return {'success': False, 'error': 'Maximum number of credentials reached or multiple credentials not allowed'}
            exclude_creds = []
            for cred in WebAuthnCredential.objects.filter(user=user, is_active=True):
                try:
                    cid = base64url_to_bytes(cred.credential_id) if cred.credential_id else None
                    if cid is not None:
                        exclude_creds.append(PublicKeyCredentialDescriptor(type=PublicKeyCredentialType.PUBLIC_KEY, id=cid))
                except Exception:
                    pass
            options = generate_registration_options(
                rp_id=rp_id,
                rp_name=rp_name,
                user_name=user.email or user.userName,
                user_id=str(user.pk).encode(),
                user_display_name=f"{user.firstName} {user.lastName}".strip() or user.userName or None,
                timeout=settings_obj.timeout_seconds * 1000,
                exclude_credentials=exclude_creds or None,
            )
            challenge_b64 = bytes_to_base64url(options.challenge)
            challenge_obj = WebAuthnChallenge.objects.create(
                user=user,
                challenge=challenge_b64,
                challenge_type='registration',
                expires_at=datetime.now() + timedelta(seconds=self.challenge_timeout),
                metadata=json.dumps({'credential_name': credential_name or f"Passkey {datetime.now().strftime('%Y-%m-%d %H:%M')}"}),
            )
            options_dict = json.loads(options_to_json(options))
            return {'success': True, 'challenge': options_dict, 'challenge_id': challenge_obj.id}
        except Exception as e:
            logger.error(f"Error creating registration challenge: {str(e)}")
            return {'success': False, 'error': str(e)}

    def verify_registration(self, challenge_id: int, credential_data: Dict[str, Any],
                           client_data_json: str, attestation_object: str, request=None) -> Dict[str, Any]:
        """Verify WebAuthn registration using webauthn library."""
        if not WEBAUTHN_LIB_AVAILABLE:
            return {'success': False, 'error': 'WebAuthn library not installed'}
        try:
            req = request or self._request
            if req is None:
                return {'success': False, 'error': 'Request required'}
            challenge_obj = WebAuthnChallenge.objects.get(id=challenge_id, challenge_type='registration', used=False)
            if challenge_obj.is_expired():
                return {'success': False, 'error': 'Challenge has expired'}
            expected_origin = self._get_origin(req)
            expected_rp_id, _ = self._get_rp(req)
            expected_challenge = base64url_to_bytes(challenge_obj.challenge)
            credential_payload = {
                'id': credential_data.get('id'),
                'rawId': credential_data.get('rawId') or credential_data.get('id'),
                'response': {
                    'clientDataJSON': client_data_json,
                    'attestationObject': attestation_object,
                },
                'type': credential_data.get('type', 'public-key'),
            }
            verified = verify_registration_response(
                credential=credential_payload,
                expected_challenge=expected_challenge,
                expected_rp_id=expected_rp_id,
                expected_origin=expected_origin,
            )
            credential_id_b64 = bytes_to_base64url(verified.credential_id)
            public_key_b64 = base64.urlsafe_b64encode(verified.credential_public_key).decode('utf-8').rstrip('=')
            metadata = challenge_obj.get_metadata()
            credential_name = metadata.get('credential_name', f"Passkey {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            WebAuthnCredential.objects.create(
                user=challenge_obj.user,
                credential_id=credential_id_b64,
                public_key=public_key_b64,
                name=credential_name,
                counter=verified.sign_count,
            )
            challenge_obj.mark_used()
            settings_obj = WebAuthnSettings.get_or_create_settings(challenge_obj.user)
            if not settings_obj.enabled:
                settings_obj.enabled = True
                settings_obj.save()
            return {'success': True, 'message': 'Passkey registered successfully'}
        except InvalidRegistrationResponse as e:
            return {'success': False, 'error': str(e)}
        except WebAuthnChallenge.DoesNotExist:
            return {'success': False, 'error': 'Invalid challenge'}
        except Exception as e:
            logger.error(f"Error verifying registration: {str(e)}")
            return {'success': False, 'error': str(e)}

    def create_authentication_challenge(self, user: Administrator = None, request=None) -> Dict[str, Any]:
        """Create WebAuthn authentication challenge for a specific user (username-first flow)."""
        if not WEBAUTHN_LIB_AVAILABLE:
            return {'success': False, 'error': 'WebAuthn library not installed'}
        try:
            req = request or self._request
            if req is None or user is None:
                return {'success': False, 'error': 'Request and user required'}
            settings_obj = WebAuthnSettings.get_or_create_settings(user)
            if not settings_obj.enabled:
                return {'success': False, 'error': 'WebAuthn not enabled for this user'}
            allow_creds = []
            for cred in WebAuthnCredential.objects.filter(user=user, is_active=True):
                try:
                    cid = base64url_to_bytes(cred.credential_id)
                    allow_creds.append(PublicKeyCredentialDescriptor(type=PublicKeyCredentialType.PUBLIC_KEY, id=cid))
                except Exception:
                    pass
            if not allow_creds:
                return {'success': False, 'error': 'No WebAuthn credentials found for this user'}
            rp_id, _ = self._get_rp(req)
            options = generate_authentication_options(
                rp_id=rp_id,
                timeout=60000,
                allow_credentials=allow_creds,
                user_verification=UserVerificationRequirement.PREFERRED,
            )
            challenge_b64 = bytes_to_base64url(options.challenge)
            challenge_obj = WebAuthnChallenge.objects.create(
                user=user,
                challenge=challenge_b64,
                challenge_type='authentication',
                expires_at=datetime.now() + timedelta(seconds=self.challenge_timeout),
                metadata=json.dumps({}),
            )
            options_dict = json.loads(options_to_json(options))
            return {'success': True, 'challenge': options_dict, 'challenge_id': challenge_obj.id}
        except Exception as e:
            logger.error(f"Error creating authentication challenge: {str(e)}")
            return {'success': False, 'error': str(e)}

    def create_passkey_first_options(self, request) -> Dict[str, Any]:
        """Create authentication options for all credentials (passkey-first login). Stores challenge in session."""
        if not WEBAUTHN_LIB_AVAILABLE:
            return {'success': False, 'error': 'WebAuthn library not installed'}
        try:
            rp_id, _ = self._get_rp(request)
            allow_creds = []
            for cred in WebAuthnCredential.objects.filter(is_active=True):
                try:
                    cid = base64url_to_bytes(cred.credential_id)
                    allow_creds.append(PublicKeyCredentialDescriptor(type=PublicKeyCredentialType.PUBLIC_KEY, id=cid))
                except Exception:
                    pass
            if not allow_creds:
                return {'success': False, 'error': 'No passkeys registered'}
            options = generate_authentication_options(
                rp_id=rp_id,
                timeout=60000,
                allow_credentials=allow_creds,
                user_verification=UserVerificationRequirement.PREFERRED,
            )
            challenge_b64 = bytes_to_base64url(options.challenge)
            request.session['webauthn_auth_challenge'] = challenge_b64
            options_dict = json.loads(options_to_json(options))
            return {'success': True, 'publicKey': options_dict}
        except Exception as e:
            logger.error(f"Error creating passkey-first options: {str(e)}")
            return {'success': False, 'error': str(e)}

    def verify_passkey_first_authentication(self, credential_payload: Dict[str, Any], request) -> Dict[str, Any]:
        """Verify passkey-first assertion; look up user by credential id. Returns user_id on success."""
        if not WEBAUTHN_LIB_AVAILABLE:
            return {'success': False, 'error': 'WebAuthn library not installed'}
        try:
            challenge_b64 = request.session.get('webauthn_auth_challenge')
            if not challenge_b64:
                return {'success': False, 'error': 'No challenge in session'}
            raw_id = credential_payload.get('rawId') or credential_payload.get('id')
            if not raw_id:
                return {'success': False, 'error': 'No credential id'}
            cred_id_str = raw_id if isinstance(raw_id, str) else (bytes_to_base64url(bytes(raw_id)) if WEBAUTHN_LIB_AVAILABLE else str(raw_id))
            cred_id_str = cred_id_str.replace('+', '-').replace('/', '_').rstrip('=')
            try:
                cred = WebAuthnCredential.objects.get(credential_id=cred_id_str, is_active=True)
            except WebAuthnCredential.DoesNotExist:
                return {'success': False, 'error': 'Credential not found'}
            expected_origin = self._get_origin(request)
            expected_rp_id, _ = self._get_rp(request)
            expected_challenge = base64url_to_bytes(challenge_b64)
            public_key_bytes = base64.urlsafe_b64decode(cred.public_key + '==')
            auth_cred = {
                'id': credential_payload.get('id'),
                'rawId': raw_id,
                'response': credential_payload.get('response', {}),
                'type': credential_payload.get('type', 'public-key'),
            }
            verified = verify_authentication_response(
                credential=auth_cred,
                expected_challenge=expected_challenge,
                expected_rp_id=expected_rp_id,
                expected_origin=expected_origin,
                credential_public_key=public_key_bytes,
                credential_current_sign_count=cred.counter,
            )
            cred.update_counter(verified.new_sign_count)
            if 'webauthn_auth_challenge' in request.session:
                del request.session['webauthn_auth_challenge']
            return {'success': True, 'user_id': cred.user_id, 'message': 'Authentication successful'}
        except InvalidAuthenticationResponse as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Error verifying passkey-first auth: {str(e)}")
            return {'success': False, 'error': str(e)}

    def verify_authentication(self, challenge_id: int, credential_data: Dict[str, Any],
                             client_data_json: str, authenticator_data: str, request=None) -> Dict[str, Any]:
        """Verify username-first WebAuthn authentication."""
        if not WEBAUTHN_LIB_AVAILABLE:
            return {'success': False, 'error': 'WebAuthn library not installed'}
        try:
            req = request or self._request
            if req is None:
                return {'success': False, 'error': 'Request required'}
            challenge_obj = WebAuthnChallenge.objects.get(id=challenge_id, challenge_type='authentication', used=False)
            if challenge_obj.is_expired():
                return {'success': False, 'error': 'Challenge has expired'}
            raw_id = credential_data.get('id') or credential_data.get('rawId')
            if not raw_id:
                return {'success': False, 'error': 'No credential ID provided'}
            try:
                credential = WebAuthnCredential.objects.get(
                    credential_id=raw_id if isinstance(raw_id, str) else bytes_to_base64url(raw_id) if hasattr(raw_id, '__iter__') else str(raw_id),
                    user=challenge_obj.user,
                    is_active=True,
                )
            except WebAuthnCredential.DoesNotExist:
                return {'success': False, 'error': 'Credential not found'}
            expected_origin = self._get_origin(req)
            expected_rp_id, _ = self._get_rp(req)
            expected_challenge = base64url_to_bytes(challenge_obj.challenge)
            public_key_bytes = base64.urlsafe_b64decode(credential.public_key + '==')
            auth_cred = {
                'id': credential_data.get('id'),
                'rawId': raw_id,
                'response': {
                    'clientDataJSON': client_data_json,
                    'authenticatorData': authenticator_data,
                    'signature': credential_data.get('signature', ''),
                },
                'type': credential_data.get('type', 'public-key'),
            }
            verified = verify_authentication_response(
                credential=auth_cred,
                expected_challenge=expected_challenge,
                expected_rp_id=expected_rp_id,
                expected_origin=expected_origin,
                credential_public_key=public_key_bytes,
                credential_current_sign_count=credential.counter,
            )
            credential.update_counter(verified.new_sign_count)
            challenge_obj.mark_used()
            return {'success': True, 'user_id': challenge_obj.user.pk, 'message': 'Authentication successful'}
        except InvalidAuthenticationResponse as e:
            return {'success': False, 'error': str(e)}
        except WebAuthnChallenge.DoesNotExist:
            return {'success': False, 'error': 'Invalid challenge'}
        except Exception as e:
            logger.error(f"Error verifying authentication: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_existing_credentials(self, user: Administrator, request=None) -> List[Dict[str, Any]]:
        credentials = WebAuthnCredential.objects.filter(user=user, is_active=True)
        return [
            {'id': cred.credential_id, 'type': 'public-key', 'transports': ['internal', 'hybrid', 'usb', 'nfc', 'ble']}
            for cred in credentials
        ]

    def get_user_credentials(self, user: Administrator) -> List[Dict[str, Any]]:
        credentials = WebAuthnCredential.objects.filter(user=user, is_active=True).order_by('-created_at')
        return [
            {
                'id': cred.id,
                'name': cred.name,
                'credential_id': (cred.credential_id[:16] + '...') if len(cred.credential_id) > 16 else cred.credential_id,
                'created_at': cred.created_at.isoformat(),
                'last_used': cred.last_used.isoformat() if cred.last_used else None,
            }
            for cred in credentials
        ]

    def delete_credential(self, user: Administrator, credential_id: int) -> Dict[str, Any]:
        try:
            credential = WebAuthnCredential.objects.get(id=credential_id, user=user)
            credential.is_active = False
            credential.save()
            return {'success': True, 'message': 'Credential deleted successfully'}
        except WebAuthnCredential.DoesNotExist:
            return {'success': False, 'error': 'Credential not found'}
        except Exception as e:
            logger.error(f"Error deleting credential: {str(e)}")
            return {'success': False, 'error': str(e)}

    def update_credential_name(self, user: Administrator, credential_id: int, new_name: str) -> Dict[str, Any]:
        try:
            credential = WebAuthnCredential.objects.get(id=credential_id, user=user)
            credential.name = new_name
            credential.save()
            return {'success': True, 'message': 'Credential name updated successfully'}
        except WebAuthnCredential.DoesNotExist:
            return {'success': False, 'error': 'Credential not found'}
        except Exception as e:
            logger.error(f"Error updating credential name: {str(e)}")
            return {'success': False, 'error': str(e)}

    def cleanup_expired_challenges(self):
        expired = WebAuthnChallenge.objects.filter(expires_at__lt=datetime.now())
        count = expired.count()
        expired.delete()
        logger.info(f"Cleaned up {count} expired WebAuthn challenges")

    def cleanup_expired_sessions(self):
        expired = WebAuthnSession.objects.filter(expires_at__lt=datetime.now())
        count = expired.count()
        expired.delete()
        logger.info(f"Cleaned up {count} expired WebAuthn sessions")
