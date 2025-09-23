# -*- coding: utf-8 -*-

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
import json
import base64
from .models import Administrator
from .webauthn_models import WebAuthnCredential, WebAuthnChallenge, WebAuthnSettings
from .webauthn_backend import WebAuthnBackend


class WebAuthnTestCase(TestCase):
    """Test cases for WebAuthn functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = Administrator.objects.create(
            userName='testuser',
            password='hashedpassword',
            email='test@example.com',
            firstName='Test',
            lastName='User',
            type=1,
            acl_id=1
        )
        
        # Create WebAuthn settings
        self.webauthn_settings = WebAuthnSettings.objects.create(
            user=self.user,
            enabled=True,
            require_passkey=False,
            allow_multiple_credentials=True,
            max_credentials=10,
            timeout_seconds=60
        )
        
        self.webauthn_backend = WebAuthnBackend()
    
    def test_webauthn_models(self):
        """Test WebAuthn models"""
        # Test WebAuthnCredential
        credential = WebAuthnCredential.objects.create(
            user=self.user,
            credential_id='test_credential_id',
            public_key='test_public_key',
            name='Test Passkey',
            counter=0
        )
        
        self.assertEqual(credential.user, self.user)
        self.assertEqual(credential.name, 'Test Passkey')
        self.assertTrue(credential.is_active)
        
        # Test WebAuthnChallenge
        challenge = WebAuthnChallenge.objects.create(
            user=self.user,
            challenge='test_challenge',
            challenge_type='registration',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        self.assertEqual(challenge.user, self.user)
        self.assertEqual(challenge.challenge_type, 'registration')
        self.assertFalse(challenge.is_expired())
        
        # Test WebAuthnSettings
        self.assertTrue(self.webauthn_settings.enabled)
        self.assertTrue(self.webauthn_settings.can_add_credential())
    
    def test_registration_challenge_creation(self):
        """Test WebAuthn registration challenge creation"""
        result = self.webauthn_backend.create_registration_challenge(
            self.user, 'Test Passkey'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('challenge', result)
        self.assertIn('challenge_id', result)
        
        # Verify challenge was stored in database
        challenge_id = result['challenge_id']
        challenge = WebAuthnChallenge.objects.get(id=challenge_id)
        self.assertEqual(challenge.user, self.user)
        self.assertEqual(challenge.challenge_type, 'registration')
    
    def test_authentication_challenge_creation(self):
        """Test WebAuthn authentication challenge creation"""
        result = self.webauthn_backend.create_authentication_challenge(self.user)
        
        self.assertTrue(result['success'])
        self.assertIn('challenge', result)
        self.assertIn('challenge_id', result)
        
        # Verify challenge was stored in database
        challenge_id = result['challenge_id']
        challenge = WebAuthnChallenge.objects.get(id=challenge_id)
        self.assertEqual(challenge.user, self.user)
        self.assertEqual(challenge.challenge_type, 'authentication')
    
    def test_credential_management(self):
        """Test credential management functions"""
        # Create test credential
        credential = WebAuthnCredential.objects.create(
            user=self.user,
            credential_id='test_credential_id',
            public_key='test_public_key',
            name='Test Passkey',
            counter=0
        )
        
        # Test get_user_credentials
        credentials = self.webauthn_backend.get_user_credentials(self.user)
        self.assertEqual(len(credentials), 1)
        self.assertEqual(credentials[0]['name'], 'Test Passkey')
        
        # Test delete_credential
        result = self.webauthn_backend.delete_credential(self.user, credential.id)
        self.assertTrue(result['success'])
        
        # Verify credential is deactivated
        credential.refresh_from_db()
        self.assertFalse(credential.is_active)
        
        # Test update_credential_name
        credential.is_active = True
        credential.save()
        
        result = self.webauthn_backend.update_credential_name(
            self.user, credential.id, 'Updated Name'
        )
        self.assertTrue(result['success'])
        
        credential.refresh_from_db()
        self.assertEqual(credential.name, 'Updated Name')
    
    def test_webauthn_api_endpoints(self):
        """Test WebAuthn API endpoints"""
        # Test registration start endpoint
        response = self.client.post('/webauthn/registration/start/', 
                                  json.dumps({'username': 'testuser', 'credential_name': 'Test Passkey'}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Test credentials list endpoint
        response = self.client.get('/webauthn/credentials/testuser/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('credentials', data)
        self.assertIn('settings', data)
        
        # Test settings update endpoint
        response = self.client.post('/webauthn/settings/update/',
                                  json.dumps({
                                      'username': 'testuser',
                                      'enabled': True,
                                      'require_passkey': False
                                  }),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_webauthn_settings_validation(self):
        """Test WebAuthn settings validation"""
        # Test max credentials limit
        settings = WebAuthnSettings.objects.get(user=self.user)
        settings.max_credentials = 1
        settings.save()
        
        # Create first credential
        WebAuthnCredential.objects.create(
            user=self.user,
            credential_id='cred1',
            public_key='key1',
            name='First Passkey'
        )
        
        # Should not be able to add more credentials
        self.assertFalse(settings.can_add_credential())
        
        # Test multiple credentials disabled
        settings.allow_multiple_credentials = False
        settings.max_credentials = 10
        settings.save()
        
        # Should not be able to add more credentials
        self.assertFalse(settings.can_add_credential())
    
    def test_challenge_expiration(self):
        """Test challenge expiration handling"""
        # Create expired challenge
        expired_challenge = WebAuthnChallenge.objects.create(
            user=self.user,
            challenge='expired_challenge',
            challenge_type='registration',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        
        self.assertTrue(expired_challenge.is_expired())
        
        # Test cleanup
        self.webauthn_backend.cleanup_expired_challenges()
        
        # Expired challenge should be deleted
        with self.assertRaises(WebAuthnChallenge.DoesNotExist):
            WebAuthnChallenge.objects.get(id=expired_challenge.id)
    
    def test_webauthn_integration_with_existing_2fa(self):
        """Test WebAuthn integration with existing 2FA system"""
        # Enable 2FA for user
        self.user.twoFA = 1
        self.user.secretKey = 'test_secret_key'
        self.user.save()
        
        # Enable WebAuthn
        settings = WebAuthnSettings.objects.get(user=self.user)
        settings.enabled = True
        settings.save()
        
        # Both should be enabled
        self.assertTrue(self.user.twoFA)
        self.assertTrue(settings.enabled)
        
        # User should be able to use either authentication method
        # (This would be tested in the actual authentication flow)
    
    def test_webauthn_security_features(self):
        """Test WebAuthn security features"""
        # Test credential counter update
        credential = WebAuthnCredential.objects.create(
            user=self.user,
            credential_id='test_credential_id',
            public_key='test_public_key',
            name='Test Passkey',
            counter=0
        )
        
        # Update counter
        result = credential.update_counter(5)
        self.assertTrue(result)
        
        # Should not allow decreasing counter
        result = credential.update_counter(3)
        self.assertFalse(result)
        
        # Test challenge uniqueness
        challenge1 = self.webauthn_backend.generate_challenge()
        challenge2 = self.webauthn_backend.generate_challenge()
        
        self.assertNotEqual(challenge1, challenge2)
        self.assertEqual(len(challenge1), 44)  # Base64 encoded 32 bytes
    
    def test_webauthn_error_handling(self):
        """Test WebAuthn error handling"""
        # Test with non-existent user
        result = self.webauthn_backend.create_registration_challenge(
            None, 'Test Passkey'
        )
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
        # Test with disabled WebAuthn
        settings = WebAuthnSettings.objects.get(user=self.user)
        settings.enabled = False
        settings.save()
        
        result = self.webauthn_backend.create_authentication_challenge(self.user)
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_webauthn_data_serialization(self):
        """Test WebAuthn data serialization"""
        # Test challenge metadata
        challenge = WebAuthnChallenge.objects.create(
            user=self.user,
            challenge='test_challenge',
            challenge_type='registration',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        # Set metadata
        metadata = {'test_key': 'test_value', 'number': 123}
        challenge.set_metadata(metadata)
        challenge.save()
        
        # Retrieve metadata
        retrieved_metadata = challenge.get_metadata()
        self.assertEqual(retrieved_metadata, metadata)
        
        # Test session data
        from .webauthn_models import WebAuthnSession
        
        session = WebAuthnSession.create_session(
            self.user, 'registration', {'test': 'data'}
        )
        
        session_data = session.get_data()
        self.assertEqual(session_data, {'test': 'data'})
        
        # Update session data
        session.set_data({'updated': 'data'})
        session.save()
        
        updated_data = session.get_data()
        self.assertEqual(updated_data, {'updated': 'data'})


class WebAuthnIntegrationTestCase(TestCase):
    """Integration tests for WebAuthn with CyberPanel"""
    
    def setUp(self):
        """Set up integration test data"""
        self.client = Client()
        
        # Create admin user
        self.admin = Administrator.objects.create(
            userName='admin',
            password='hashedpassword',
            email='admin@example.com',
            firstName='Admin',
            lastName='User',
            type=1,
            acl_id=1
        )
        
        # Create regular user
        self.user = Administrator.objects.create(
            userName='testuser',
            password='hashedpassword',
            email='test@example.com',
            firstName='Test',
            lastName='User',
            type=0,
            acl_id=2,
            owner=self.admin.pk
        )
    
    def test_webauthn_user_management_integration(self):
        """Test WebAuthn integration with user management"""
        # Login as admin
        self.client.force_login(self.admin)
        
        # Test WebAuthn settings update through user management
        response = self.client.post('/webauthn/settings/update/',
                                  json.dumps({
                                      'username': 'testuser',
                                      'enabled': True,
                                      'require_passkey': False,
                                      'allow_multiple_credentials': True,
                                      'max_credentials': 5
                                  }),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify settings were updated
        settings = WebAuthnSettings.get_or_create_settings(self.user)
        self.assertTrue(settings.enabled)
        self.assertEqual(settings.max_credentials, 5)
    
    def test_webauthn_permissions(self):
        """Test WebAuthn permission system"""
        # Test admin can manage any user's WebAuthn settings
        self.client.force_login(self.admin)
        
        response = self.client.get('/webauthn/credentials/testuser/')
        self.assertEqual(response.status_code, 200)
        
        # Test user can manage their own WebAuthn settings
        self.client.force_login(self.user)
        
        response = self.client.get('/webauthn/credentials/testuser/')
        self.assertEqual(response.status_code, 200)
        
        # Test user cannot manage other users' settings
        other_user = Administrator.objects.create(
            userName='otheruser',
            password='hashedpassword',
            email='other@example.com',
            firstName='Other',
            lastName='User',
            type=0,
            acl_id=2,
            owner=self.admin.pk
        )
        
        response = self.client.get('/webauthn/credentials/otheruser/')
        self.assertEqual(response.status_code, 403)
    
    def test_webauthn_with_existing_authentication(self):
        """Test WebAuthn alongside existing authentication methods"""
        # Enable 2FA for user
        self.user.twoFA = 1
        self.user.secretKey = 'test_secret_key'
        self.user.save()
        
        # Enable WebAuthn
        settings = WebAuthnSettings.objects.create(
            user=self.user,
            enabled=True,
            require_passkey=False
        )
        
        # Both authentication methods should be available
        self.assertTrue(self.user.twoFA)
        self.assertTrue(settings.enabled)
        
        # User should be able to use either method
        # (In practice, this would be handled in the login flow)
    
    def test_webauthn_cleanup_maintenance(self):
        """Test WebAuthn cleanup and maintenance functions"""
        # Create expired challenges and sessions
        expired_challenge = WebAuthnChallenge.objects.create(
            user=self.user,
            challenge='expired_challenge',
            challenge_type='registration',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        from .webauthn_models import WebAuthnSession
        expired_session = WebAuthnSession.objects.create(
            user=self.user,
            session_id='expired_session',
            session_type='registration',
            data='{}',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # Run cleanup
        backend = WebAuthnBackend()
        backend.cleanup_expired_challenges()
        backend.cleanup_expired_sessions()
        
        # Expired items should be deleted
        with self.assertRaises(WebAuthnChallenge.DoesNotExist):
            WebAuthnChallenge.objects.get(id=expired_challenge.id)
        
        with self.assertRaises(WebAuthnSession.DoesNotExist):
            WebAuthnSession.objects.get(id=expired_session.id)
