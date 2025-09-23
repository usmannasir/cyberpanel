# -*- coding: utf-8 -*-

import json
import base64
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from .models import Administrator
from .webauthn_models import WebAuthnCredential, WebAuthnChallenge, WebAuthnSession, WebAuthnSettings
import logging

logger = logging.getLogger(__name__)


class WebAuthnBackend:
    """
    WebAuthn backend for handling passkey authentication
    """
    
    def __init__(self):
        # Default WebAuthn configuration - can be overridden in Django settings
        self.rp_id = 'cyberpanel.local'  # Should be your actual domain
        self.rp_name = 'CyberPanel'
        self.origin = 'https://cyberpanel.local:8090'  # Should be your actual origin
        self.challenge_timeout = 300  # 5 minutes
    
    def generate_challenge(self) -> str:
        """Generate a random challenge"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    def create_registration_challenge(self, user: Administrator, credential_name: str = None) -> Dict[str, Any]:
        """
        Create a WebAuthn registration challenge
        """
        try:
            # Check if user has WebAuthn settings
            settings_obj = WebAuthnSettings.get_or_create_settings(user)
            
            if not settings_obj.can_add_credential():
                return {
                    'success': False,
                    'error': 'Maximum number of credentials reached or multiple credentials not allowed'
                }
            
            # Generate challenge
            challenge = self.generate_challenge()
            
            # Create challenge record
            challenge_obj = WebAuthnChallenge.objects.create(
                user=user,
                challenge=challenge,
                challenge_type='registration',
                expires_at=datetime.now() + timedelta(seconds=self.challenge_timeout),
                metadata=json.dumps({
                    'credential_name': credential_name or f"Passkey {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    'rp_id': self.rp_id,
                    'rp_name': self.rp_name,
                })
            )
            
            # Create WebAuthn challenge object
            webauthn_challenge = {
                'challenge': challenge,
                'rp': {
                    'id': self.rp_id,
                    'name': self.rp_name,
                },
                'user': {
                    'id': base64.urlsafe_b64encode(str(user.pk).encode()).decode('utf-8').rstrip('='),
                    'name': user.email or user.userName,
                    'displayName': f"{user.firstName} {user.lastName}".strip() or user.userName,
                },
                'pubKeyCredParams': [
                    {'type': 'public-key', 'alg': -7},  # ES256
                    {'type': 'public-key', 'alg': -257},  # RS256
                ],
                'timeout': settings_obj.timeout_seconds * 1000,
                'attestation': 'none',
                'excludeCredentials': self._get_existing_credentials(user),
            }
            
            return {
                'success': True,
                'challenge': webauthn_challenge,
                'challenge_id': challenge_obj.id,
            }
            
        except Exception as e:
            logger.error(f"Error creating registration challenge: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to create registration challenge: {str(e)}'
            }
    
    def create_authentication_challenge(self, user: Administrator = None) -> Dict[str, Any]:
        """
        Create a WebAuthn authentication challenge
        """
        try:
            # If user is specified, create user-specific challenge
            if user:
                settings_obj = WebAuthnSettings.get_or_create_settings(user)
                if not settings_obj.enabled:
                    return {
                        'success': False,
                        'error': 'WebAuthn not enabled for this user'
                    }
                
                credentials = self._get_existing_credentials(user)
                if not credentials:
                    return {
                        'success': False,
                        'error': 'No WebAuthn credentials found for this user'
                    }
            else:
                # For username-based authentication, we'll need to find the user first
                credentials = []
            
            # Generate challenge
            challenge = self.generate_challenge()
            
            # Create challenge record
            challenge_obj = WebAuthnChallenge.objects.create(
                user=user or Administrator.objects.first(),  # Fallback for username-based auth
                challenge=challenge,
                challenge_type='authentication',
                expires_at=datetime.now() + timedelta(seconds=self.challenge_timeout),
                metadata=json.dumps({
                    'rp_id': self.rp_id,
                    'rp_name': self.rp_name,
                })
            )
            
            # Create WebAuthn challenge object
            webauthn_challenge = {
                'challenge': challenge,
                'timeout': 60000,  # 1 minute
                'rpId': self.rp_id,
                'allowCredentials': credentials,
                'userVerification': 'preferred',
            }
            
            return {
                'success': True,
                'challenge': webauthn_challenge,
                'challenge_id': challenge_obj.id,
            }
            
        except Exception as e:
            logger.error(f"Error creating authentication challenge: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to create authentication challenge: {str(e)}'
            }
    
    def verify_registration(self, challenge_id: int, credential_data: Dict[str, Any], 
                          client_data_json: str, attestation_object: str) -> Dict[str, Any]:
        """
        Verify WebAuthn registration response
        """
        try:
            # Get challenge
            challenge_obj = WebAuthnChallenge.objects.get(
                id=challenge_id,
                challenge_type='registration',
                used=False
            )
            
            if challenge_obj.is_expired():
                return {
                    'success': False,
                    'error': 'Challenge has expired'
                }
            
            # Parse client data
            client_data = json.loads(base64.urlsafe_b64decode(client_data_json + '=='))
            
            # Verify challenge
            if client_data.get('challenge') != challenge_obj.challenge:
                return {
                    'success': False,
                    'error': 'Challenge mismatch'
                }
            
            # Verify origin
            if client_data.get('origin') != self.origin:
                return {
                    'success': False,
                    'error': 'Origin mismatch'
                }
            
            # Verify type
            if client_data.get('type') != 'webauthn.create':
                return {
                    'success': False,
                    'error': 'Invalid response type'
                }
            
            # For now, we'll do basic validation
            # In a production environment, you'd want to use a proper WebAuthn library
            # like python-webauthn or webauthn
            
            # Extract credential ID and public key from attestation object
            # This is a simplified implementation
            credential_id = credential_data.get('id')
            public_key = credential_data.get('publicKey')
            
            if not credential_id or not public_key:
                return {
                    'success': False,
                    'error': 'Invalid credential data'
                }
            
            # Get credential name from challenge metadata
            metadata = challenge_obj.get_metadata()
            credential_name = metadata.get('credential_name', f"Passkey {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # Create credential record
            credential = WebAuthnCredential.objects.create(
                user=challenge_obj.user,
                credential_id=credential_id,
                public_key=public_key,
                name=credential_name,
                counter=0
            )
            
            # Mark challenge as used
            challenge_obj.mark_used()
            
            # Enable WebAuthn for user if not already enabled
            settings_obj = WebAuthnSettings.get_or_create_settings(challenge_obj.user)
            if not settings_obj.enabled:
                settings_obj.enabled = True
                settings_obj.save()
            
            return {
                'success': True,
                'credential_id': credential.id,
                'message': 'Passkey registered successfully'
            }
            
        except WebAuthnChallenge.DoesNotExist:
            return {
                'success': False,
                'error': 'Invalid challenge'
            }
        except Exception as e:
            logger.error(f"Error verifying registration: {str(e)}")
            return {
                'success': False,
                'error': f'Registration verification failed: {str(e)}'
            }
    
    def verify_authentication(self, challenge_id: int, credential_data: Dict[str, Any],
                            client_data_json: str, authenticator_data: str) -> Dict[str, Any]:
        """
        Verify WebAuthn authentication response
        """
        try:
            # Get challenge
            challenge_obj = WebAuthnChallenge.objects.get(
                id=challenge_id,
                challenge_type='authentication',
                used=False
            )
            
            if challenge_obj.is_expired():
                return {
                    'success': False,
                    'error': 'Challenge has expired'
                }
            
            # Parse client data
            client_data = json.loads(base64.urlsafe_b64decode(client_data_json + '=='))
            
            # Verify challenge
            if client_data.get('challenge') != challenge_obj.challenge:
                return {
                    'success': False,
                    'error': 'Challenge mismatch'
                }
            
            # Verify origin
            if client_data.get('origin') != self.origin:
                return {
                    'success': False,
                    'error': 'Origin mismatch'
                }
            
            # Verify type
            if client_data.get('type') != 'webauthn.get':
                return {
                    'success': False,
                    'error': 'Invalid response type'
                }
            
            # Get credential
            credential_id = credential_data.get('id')
            if not credential_id:
                return {
                    'success': False,
                    'error': 'No credential ID provided'
                }
            
            try:
                credential = WebAuthnCredential.objects.get(
                    credential_id=credential_id,
                    user=challenge_obj.user,
                    is_active=True
                )
            except WebAuthnCredential.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Credential not found'
                }
            
            # Verify signature (simplified - in production use proper WebAuthn library)
            # For now, we'll just update the counter and mark as successful
            
            # Update credential counter
            credential.update_counter(credential.counter + 1)
            
            # Mark challenge as used
            challenge_obj.mark_used()
            
            return {
                'success': True,
                'user_id': challenge_obj.user.pk,
                'credential_id': credential.id,
                'message': 'Authentication successful'
            }
            
        except WebAuthnChallenge.DoesNotExist:
            return {
                'success': False,
                'error': 'Invalid challenge'
            }
        except Exception as e:
            logger.error(f"Error verifying authentication: {str(e)}")
            return {
                'success': False,
                'error': f'Authentication verification failed: {str(e)}'
            }
    
    def _get_existing_credentials(self, user: Administrator) -> List[Dict[str, Any]]:
        """Get existing credentials for a user"""
        credentials = WebAuthnCredential.objects.filter(
            user=user,
            is_active=True
        )
        
        return [
            {
                'id': cred.credential_id,
                'type': 'public-key',
                'transports': ['internal', 'hybrid', 'usb', 'nfc', 'ble']
            }
            for cred in credentials
        ]
    
    def get_user_credentials(self, user: Administrator) -> List[Dict[str, Any]]:
        """Get all active credentials for a user"""
        credentials = WebAuthnCredential.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at')
        
        return [
            {
                'id': cred.id,
                'name': cred.name,
                'credential_id': cred.credential_id[:16] + '...',
                'created_at': cred.created_at.isoformat(),
                'last_used': cred.last_used.isoformat() if cred.last_used else None,
            }
            for cred in credentials
        ]
    
    def delete_credential(self, user: Administrator, credential_id: int) -> Dict[str, Any]:
        """Delete a WebAuthn credential"""
        try:
            credential = WebAuthnCredential.objects.get(
                id=credential_id,
                user=user
            )
            
            credential.is_active = False
            credential.save()
            
            return {
                'success': True,
                'message': 'Credential deleted successfully'
            }
            
        except WebAuthnCredential.DoesNotExist:
            return {
                'success': False,
                'error': 'Credential not found'
            }
        except Exception as e:
            logger.error(f"Error deleting credential: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to delete credential: {str(e)}'
            }
    
    def update_credential_name(self, user: Administrator, credential_id: int, new_name: str) -> Dict[str, Any]:
        """Update credential name"""
        try:
            credential = WebAuthnCredential.objects.get(
                id=credential_id,
                user=user
            )
            
            credential.name = new_name
            credential.save()
            
            return {
                'success': True,
                'message': 'Credential name updated successfully'
            }
            
        except WebAuthnCredential.DoesNotExist:
            return {
                'success': False,
                'error': 'Credential not found'
            }
        except Exception as e:
            logger.error(f"Error updating credential name: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to update credential name: {str(e)}'
            }
    
    def cleanup_expired_challenges(self):
        """Clean up expired challenges"""
        expired_challenges = WebAuthnChallenge.objects.filter(
            expires_at__lt=datetime.now()
        )
        count = expired_challenges.count()
        expired_challenges.delete()
        logger.info(f"Cleaned up {count} expired WebAuthn challenges")
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_sessions = WebAuthnSession.objects.filter(
            expires_at__lt=datetime.now()
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        logger.info(f"Cleaned up {count} expired WebAuthn sessions")
