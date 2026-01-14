# Mindset AI Engine - Base Provider Interface
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


@dataclass
class AIMessage:
    """Represents a message in a conversation"""
    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class AIResponse:
    """Represents an AI completion response"""
    content: str
    model: str
    provider: str
    tokens_used: int
    finish_reason: str
    latency_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "tokens_used": self.tokens_used,
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
        }


@dataclass
class AIProviderConfig:
    """Configuration for an AI provider"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict) -> 'AIProviderConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, config: AIProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name"""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether this provider runs locally"""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming responses"""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[AIMessage],
        **kwargs
    ) -> AIResponse:
        """Generate a completion from messages"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[AIMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from messages"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available and healthy"""
        pass

    async def list_models(self) -> List[str]:
        """List available models (if supported)"""
        return []

    def validate_config(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = []
        if not self.config.model:
            errors.append("Model is required")
        return errors


class AIProviderError(Exception):
    """Base exception for AI provider errors"""

    def __init__(self, message: str, provider: str, recoverable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.recoverable = recoverable


class RateLimitError(AIProviderError):
    """Rate limit exceeded"""

    def __init__(self, provider: str, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded for {provider}",
            provider,
            recoverable=True
        )
        self.retry_after = retry_after


class ModelNotFoundError(AIProviderError):
    """Requested model not available"""

    def __init__(self, provider: str, model: str):
        super().__init__(
            f"Model '{model}' not found on {provider}",
            provider,
            recoverable=False
        )
        self.model = model


class ProviderUnavailableError(AIProviderError):
    """Provider is not available"""

    def __init__(self, provider: str, reason: str = ""):
        super().__init__(
            f"Provider {provider} is unavailable: {reason}",
            provider,
            recoverable=True
        )
