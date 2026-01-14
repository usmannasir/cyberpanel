# Mindset AI Engine - DeepInfra Provider
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

import json
import time
from typing import AsyncGenerator, List, Optional

import httpx

from .base import (
    AIProvider,
    AIProviderConfig,
    AIMessage,
    AIResponse,
    AIProviderError,
    ProviderUnavailableError,
    RateLimitError,
    ModelNotFoundError,
)


class DeepInfraProvider(AIProvider):
    """
    DeepInfra Provider - High-performance cloud inference

    DeepInfra provides fast, cost-effective inference for open-source models:
    - Meta Llama 3.1 (8B, 70B)
    - Mistral/Mixtral
    - CodeLlama
    - And many more

    Features:
    - OpenAI-compatible API
    - Streaming support
    - Competitive pricing
    - Low latency
    """

    BASE_URL = "https://api.deepinfra.com/v1/openai"

    # Popular models available on DeepInfra
    MODELS = {
        "llama-3.1-70b": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "llama-3.1-8b": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
        "mixtral-8x7b": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "mixtral-8x22b": "mistralai/Mixtral-8x22B-Instruct-v0.1",
        "codellama-34b": "codellama/CodeLlama-34b-Instruct-hf",
        "codellama-70b": "codellama/CodeLlama-70b-Instruct-hf",
        "qwen-72b": "Qwen/Qwen2-72B-Instruct",
        "gemma-2-27b": "google/gemma-2-27b-it",
    }

    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.BASE_URL

    @property
    def name(self) -> str:
        return "deepinfra"

    @property
    def display_name(self) -> str:
        return "DeepInfra"

    @property
    def is_local(self) -> bool:
        return False

    @property
    def supports_streaming(self) -> bool:
        return True

    async def complete(
        self,
        messages: List[AIMessage],
        **kwargs
    ) -> AIResponse:
        """Generate a completion using DeepInfra"""
        start_time = time.time()

        model = kwargs.get('model', self.config.model)
        temperature = kwargs.get('temperature', self.config.temperature)
        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)

        # Resolve model alias if needed
        if model in self.MODELS:
            model = self.MODELS[model]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [m.to_dict() for m in messages],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    timeout=self.config.timeout
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise RateLimitError(self.name, retry_after)

                # Handle not found
                if response.status_code == 404:
                    raise ModelNotFoundError(self.name, model)

                response.raise_for_status()
                data = response.json()

                latency_ms = int((time.time() - start_time) * 1000)

                return AIResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data["model"],
                    provider=self.name,
                    tokens_used=data["usage"]["total_tokens"],
                    finish_reason=data["choices"][0]["finish_reason"],
                    latency_ms=latency_ms
                )

            except httpx.ConnectError:
                raise ProviderUnavailableError(
                    self.name,
                    "Cannot connect to DeepInfra API"
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AIProviderError(
                        "Invalid API key",
                        self.name,
                        recoverable=False
                    )
                raise AIProviderError(
                    f"DeepInfra API error: {e.response.text}",
                    self.name
                )

    async def stream(
        self,
        messages: List[AIMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from DeepInfra"""
        model = kwargs.get('model', self.config.model)
        temperature = kwargs.get('temperature', self.config.temperature)
        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)

        # Resolve model alias
        if model in self.MODELS:
            model = self.MODELS[model]

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [m.to_dict() for m in messages],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True
                    },
                    timeout=self.config.timeout
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                if chunk["choices"][0]["delta"].get("content"):
                                    yield chunk["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                continue

            except httpx.ConnectError:
                raise ProviderUnavailableError(
                    self.name,
                    "Cannot connect to DeepInfra API"
                )

    async def health_check(self) -> bool:
        """Check if DeepInfra API is accessible"""
        if not self.config.api_key:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """List available models on DeepInfra"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                return [model["id"] for model in data.get("data", [])]
        except Exception:
            # Return known models if API call fails
            return list(self.MODELS.values())

    def validate_config(self) -> List[str]:
        """Validate DeepInfra configuration"""
        errors = []
        if not self.config.api_key:
            errors.append("API key is required for DeepInfra")
        if not self.config.model:
            errors.append("Model is required (e.g., 'llama-3.1-70b')")
        return errors

    @classmethod
    def get_recommended_models(cls) -> dict:
        """Get recommended models for different tasks"""
        return {
            "general": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "fast": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "code": "codellama/CodeLlama-70b-Instruct-hf",
            "reasoning": "Qwen/Qwen2-72B-Instruct",
        }
