import hashlib
from django.db import models

class PortManagerApiKey(models.Model):
    SCOPE_READ = 'read'
    SCOPE_MUTATE = 'mutate'
    SCOPE_CHOICES = ((SCOPE_READ, 'read'), (SCOPE_MUTATE, 'mutate'))
    label = models.CharField(max_length=64, default='default')
    key_hash = models.CharField(max_length=64, unique=True)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES, default=SCOPE_READ)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)

    @staticmethod
    def hash_key(raw):
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

class PortManagerAudit(models.Model):
    actor = models.CharField(max_length=128, blank=True, default='')
    action = models.CharField(max_length=64)
    detail = models.TextField(blank=True, default='')
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
