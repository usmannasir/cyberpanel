# Mindset AI Engine - Database Models
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

from django.db import models
from django.conf import settings


class AIProvider(models.Model):
    """AI provider configuration"""

    PROVIDER_TYPES = [
        ('ollama', 'Ollama (Local)'),
        ('deepinfra', 'DeepInfra'),
        ('openai', 'OpenAI'),
        ('huggingface', 'HuggingFace'),
        ('lmstudio', 'LM Studio'),
    ]

    name = models.CharField(max_length=50, unique=True)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)

    # Configuration
    api_key = models.TextField(null=True, blank=True)  # Encrypted
    api_key_encrypted = models.BooleanField(default=True)
    base_url = models.CharField(max_length=255, null=True, blank=True)
    default_model = models.CharField(max_length=100)

    # Settings
    enabled = models.BooleanField(default=True)
    is_local = models.BooleanField(default=False)
    priority = models.IntegerField(default=100)  # Lower = higher priority

    # Rate limiting
    requests_per_minute = models.IntegerField(default=60)
    tokens_per_day = models.IntegerField(default=1000000)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_providers'
        ordering = ['priority', 'name']
        verbose_name = 'AI Provider'
        verbose_name_plural = 'AI Providers'

    def __str__(self):
        return f"{self.name} ({self.provider_type})"


class AITaskRouting(models.Model):
    """Route specific AI tasks to specific providers"""

    TASK_TYPES = [
        ('log_analysis', 'Log Analysis'),
        ('error_explanation', 'Error Explanation'),
        ('security_scan', 'Security Scanning'),
        ('performance_tuning', 'Performance Tuning'),
        ('code_review', 'Code Review'),
        ('deployment_assist', 'Deployment Assistant'),
    ]

    task_type = models.CharField(max_length=50, choices=TASK_TYPES, unique=True)
    provider = models.ForeignKey(
        AIProvider,
        on_delete=models.CASCADE,
        related_name='task_routes'
    )
    model_override = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'ai_task_routing'
        verbose_name = 'AI Task Routing'
        verbose_name_plural = 'AI Task Routings'

    def __str__(self):
        return f"{self.task_type} -> {self.provider.name}"


class UserAIConfig(models.Model):
    """Per-user AI configuration (BYOK support)"""

    user_id = models.IntegerField(unique=True)

    # User's own API keys (encrypted)
    openai_key = models.TextField(null=True, blank=True)
    deepinfra_key = models.TextField(null=True, blank=True)
    huggingface_key = models.TextField(null=True, blank=True)

    # User preferences
    preferred_provider = models.CharField(max_length=50, null=True, blank=True)
    local_only_mode = models.BooleanField(default=False)

    # Privacy settings
    redact_secrets = models.BooleanField(default=True)
    anonymize_paths = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_user_configs'
        verbose_name = 'User AI Config'
        verbose_name_plural = 'User AI Configs'

    def __str__(self):
        return f"AI Config for User {self.user_id}"


class AIQueryLog(models.Model):
    """Log of AI queries for auditing and debugging"""

    user_id = models.IntegerField()
    task_type = models.CharField(max_length=50)
    provider = models.CharField(max_length=50)
    model = models.CharField(max_length=100)

    # Request/Response (sanitized)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    # Timing
    latency_ms = models.IntegerField(default=0)

    # Status
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_query_logs'
        ordering = ['-created_at']
        verbose_name = 'AI Query Log'
        verbose_name_plural = 'AI Query Logs'

    def __str__(self):
        return f"{self.task_type} by User {self.user_id} at {self.created_at}"
