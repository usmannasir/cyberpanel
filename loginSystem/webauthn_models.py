# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth import get_user_model
from .models import Administrator
import json
import base64
from datetime import datetime, timedelta


class WebAuthnCredential(models.Model):
    """
    Model to store WebAuthn passkey credentials for users
    """
    user = models.ForeignKey(Administrator, on_delete=models.CASCADE, related_name='webauthn_credentials')
    credential_id = models.CharField(max_length=255, unique=True, help_text="Base64 encoded credential ID")
    public_key = models.TextField(help_text="Base64 encoded public key")
    counter = models.BigIntegerField(default=0, help_text="Signature counter for replay protection")
    name = models.CharField(max_length=100, help_text="User-friendly name for the passkey")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="Whether this credential is active")
    
    class Meta:
        db_table = 'webauthn_credentials'
        verbose_name = 'WebAuthn Credential'
        verbose_name_plural = 'WebAuthn Credentials'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['credential_id']),
        ]
    
    def __str__(self):
        return f"{self.user.userName} - {self.name} ({self.credential_id[:16]}...)"
    
    def get_credential_id_bytes(self):
        """Get credential ID as bytes"""
        return base64.urlsafe_b64decode(self.credential_id + '==')
    
    def get_public_key_bytes(self):
        """Get public key as bytes"""
        return base64.urlsafe_b64decode(self.public_key + '==')
    
    def update_counter(self, new_counter):
        """Update signature counter"""
        if new_counter > self.counter:
            self.counter = new_counter
            self.last_used = datetime.now()
            self.save(update_fields=['counter', 'last_used'])
            return True
        return False


class WebAuthnChallenge(models.Model):
    """
    Model to store WebAuthn challenges for registration and authentication
    """
    user = models.ForeignKey(Administrator, on_delete=models.CASCADE, related_name='webauthn_challenges')
    challenge = models.CharField(max_length=255, help_text="Base64 encoded challenge")
    challenge_type = models.CharField(max_length=20, choices=[
        ('registration', 'Registration'),
        ('authentication', 'Authentication'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    metadata = models.TextField(default='{}', help_text="Additional challenge metadata as JSON")
    
    class Meta:
        db_table = 'webauthn_challenges'
        verbose_name = 'WebAuthn Challenge'
        verbose_name_plural = 'WebAuthn Challenges'
        indexes = [
            models.Index(fields=['user', 'challenge_type', 'used']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.userName} - {self.challenge_type} ({self.challenge[:16]}...)"
    
    def is_expired(self):
        """Check if challenge has expired"""
        return datetime.now() > self.expires_at
    
    def get_challenge_bytes(self):
        """Get challenge as bytes"""
        return base64.urlsafe_b64decode(self.challenge + '==')
    
    def get_metadata(self):
        """Get metadata as dict"""
        try:
            return json.loads(self.metadata)
        except:
            return {}
    
    def set_metadata(self, data):
        """Set metadata from dict"""
        self.metadata = json.dumps(data)
    
    def mark_used(self):
        """Mark challenge as used"""
        self.used = True
        self.save(update_fields=['used'])


class WebAuthnSession(models.Model):
    """
    Model to store WebAuthn session data for ongoing operations
    """
    user = models.ForeignKey(Administrator, on_delete=models.CASCADE, related_name='webauthn_sessions')
    session_id = models.CharField(max_length=255, unique=True, help_text="Unique session identifier")
    session_type = models.CharField(max_length=20, choices=[
        ('registration', 'Registration'),
        ('authentication', 'Authentication'),
    ])
    data = models.TextField(help_text="Session data as JSON")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'webauthn_sessions'
        verbose_name = 'WebAuthn Session'
        verbose_name_plural = 'WebAuthn Sessions'
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.userName} - {self.session_type} ({self.session_id[:16]}...)"
    
    def is_expired(self):
        """Check if session has expired"""
        return datetime.now() > self.expires_at
    
    def get_data(self):
        """Get session data as dict"""
        try:
            return json.loads(self.data)
        except:
            return {}
    
    def set_data(self, data):
        """Set session data from dict"""
        self.data = json.dumps(data)
    
    @classmethod
    def create_session(cls, user, session_type, data, duration_minutes=10):
        """Create a new WebAuthn session"""
        import uuid
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        session = cls.objects.create(
            user=user,
            session_id=session_id,
            session_type=session_type,
            data=json.dumps(data),
            expires_at=expires_at
        )
        return session


class WebAuthnSettings(models.Model):
    """
    Model to store WebAuthn configuration settings
    """
    user = models.OneToOneField(Administrator, on_delete=models.CASCADE, related_name='webauthn_settings')
    enabled = models.BooleanField(default=False, help_text="Whether WebAuthn is enabled for this user")
    require_passkey = models.BooleanField(default=False, help_text="Require passkey for login (passwordless)")
    allow_multiple_credentials = models.BooleanField(default=True, help_text="Allow multiple passkeys per user")
    max_credentials = models.IntegerField(default=10, help_text="Maximum number of passkeys allowed")
    timeout_seconds = models.IntegerField(default=60, help_text="WebAuthn operation timeout in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webauthn_settings'
        verbose_name = 'WebAuthn Settings'
        verbose_name_plural = 'WebAuthn Settings'
    
    def __str__(self):
        return f"WebAuthn Settings for {self.user.userName}"
    
    @classmethod
    def get_or_create_settings(cls, user):
        """Get or create WebAuthn settings for a user"""
        settings, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'enabled': False,
                'require_passkey': False,
                'allow_multiple_credentials': True,
                'max_credentials': 10,
                'timeout_seconds': 60,
            }
        )
        return settings
    
    def can_add_credential(self):
        """Check if user can add another credential. No limit (like diabetes.newstargeted.com)."""
        return True
