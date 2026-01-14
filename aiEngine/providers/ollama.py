# Mindset AI Engine - Ollama Provider (Local LLMs)
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
    ModelNotFoundError,
)


class OllamaProvider(AIProvider):
    """
    Ollama Provider - Local LLM inference

    Ollama allows running large language models locally, providing:
    - Privacy (data never leaves the server)
    - No API costs
    - Offline capability
    - Support for many open-source models

    Recommended models:
    - llama3.1:8b - General purpose, good balance
    - codellama:13b - Code-focused tasks
    - mistral:7b - Fast and capable
    """

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 11434

    def __init__(self, config: AIProviderConfig):
        super().__init__(config)

        # Parse host and port from base_url or use defaults
        if config.base_url:
            self.base_url = config.base_url.rstrip('/')
        else:
            self.base_url = f"http://{self.DEFAULT_HOST}:{self.DEFAULT_PORT}"

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return "Ollama (Local)"

    @property
    def is_local(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        return True

    async def complete(
        self,
        messages: List[AIMessage],
        **kwargs
    ) -> AIResponse:
        """Generate a completion using Ollama"""
        start_time = time.time()

        model = kwargs.get('model', self.config.model)
        temperature = kwargs.get('temperature', self.config.temperature)
        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [m.to_dict() for m in messages],
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        }
                    },
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                data = response.json()

                latency_ms = int((time.time() - start_time) * 1000)

                # Calculate token usage
                eval_count = data.get('eval_count', 0)
                prompt_eval_count = data.get('prompt_eval_count', 0)

                return AIResponse(
                    content=data["message"]["content"],
                    model=data["model"],
                    provider=self.name,
                    tokens_used=eval_count + prompt_eval_count,
                    finish_reason="stop",
                    latency_ms=latency_ms
                )

            except httpx.ConnectError:
                raise ProviderUnavailableError(
                    self.name,
                    "Cannot connect to Ollama. Is it running?"
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ModelNotFoundError(self.name, model)
                raise AIProviderError(
                    f"Ollama API error: {e.response.text}",
                    self.name
                )

    async def stream(
        self,
        messages: List[AIMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from Ollama"""
        model = kwargs.get('model', self.config.model)
        temperature = kwargs.get('temperature', self.config.temperature)

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [m.to_dict() for m in messages],
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                        }
                    },
                    timeout=self.config.timeout
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if data.get("message", {}).get("content"):
                                    yield data["message"]["content"]
                            except json.JSONDecodeError:
                                continue

            except httpx.ConnectError:
                raise ProviderUnavailableError(
                    self.name,
                    "Cannot connect to Ollama"
                )

    async def health_check(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception:
            return []

    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model},
                    timeout=600  # Models can be large
                )
                return response.status_code == 200
        except Exception:
            return False

    async def model_info(self, model: str) -> Optional[dict]:
        """Get information about a specific model"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/show",
                    json={"name": model},
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    def validate_config(self) -> List[str]:
        """Validate Ollama configuration"""
        errors = []
        if not self.config.model:
            errors.append("Model is required (e.g., 'llama3.1:8b')")
        return errors
