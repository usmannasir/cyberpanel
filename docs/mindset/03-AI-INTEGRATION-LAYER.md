# AI Integration Layer Design

## Overview

The Mindset AI Integration Layer provides a unified, provider-agnostic interface for AI-powered features. It supports both cloud-based and local AI models, prioritizing privacy with BYOK (Bring Your Own Key) and local-only modes.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MINDSET AI LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        AI SERVICE REGISTRY                          │    │
│  │                                                                      │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │    │
│  │  │LogAnalyzer  │  │ErrorExplainer│ │SecurityScan │                 │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │    │
│  │  │PerfTuner    │  │CodeReviewer │  │DeployAssist │                 │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                            ┌───────▼───────┐                                │
│                            │   AI ROUTER   │                                │
│                            │   (Strategy)  │                                │
│                            └───────┬───────┘                                │
│                                    │                                         │
│  ┌─────────────────────────────────┴─────────────────────────────────┐      │
│  │                     PROVIDER ABSTRACTION                          │      │
│  │                                                                   │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │      │
│  │  │DeepInfra │ │ OpenAI   │ │ Ollama   │ │LM Studio │ │Hugging │ │      │
│  │  │ Provider │ │ Provider │ │ Provider │ │ Provider │ │ Face   │ │      │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### 2.1 Provider Interface

```python
# mindset/ai/providers/base.py

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from pydantic import BaseModel

class AIMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class AIResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: int
    finish_reason: str

class AIProviderConfig(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30

class AIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, config: AIProviderConfig):
        self.config = config

    @abstractmethod
    async def complete(
        self,
        messages: list[AIMessage],
        **kwargs
    ) -> AIResponse:
        """Generate a completion from messages"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[AIMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from messages"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming"""
        pass
```

### 2.2 Provider Implementations

#### DeepInfra Provider

```python
# mindset/ai/providers/deepinfra.py

import httpx
from .base import AIProvider, AIResponse, AIMessage, AIProviderConfig

class DeepInfraProvider(AIProvider):
    """DeepInfra AI Provider - High-performance inference"""

    BASE_URL = "https://api.deepinfra.com/v1/openai"

    MODELS = {
        "llama-3.1-70b": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "llama-3.1-8b": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "mixtral-8x7b": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "codellama-34b": "codellama/CodeLlama-34b-Instruct-hf",
    }

    @property
    def name(self) -> str:
        return "deepinfra"

    @property
    def supports_streaming(self) -> bool:
        return True

    async def complete(
        self,
        messages: list[AIMessage],
        **kwargs
    ) -> AIResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.model,
                    "messages": [m.dict() for m in messages],
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                },
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()

            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                provider=self.name,
                tokens_used=data["usage"]["total_tokens"],
                finish_reason=data["choices"][0]["finish_reason"]
            )

    async def stream(
        self,
        messages: list[AIMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.model,
                    "messages": [m.dict() for m in messages],
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "stream": True
                },
                timeout=self.config.timeout
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        chunk = json.loads(line[6:])
                        if chunk["choices"][0]["delta"].get("content"):
                            yield chunk["choices"][0]["delta"]["content"]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False
```

#### Ollama Provider (Local LLM)

```python
# mindset/ai/providers/ollama.py

import httpx
from .base import AIProvider, AIResponse, AIMessage, AIProviderConfig

class OllamaProvider(AIProvider):
    """Ollama Provider - Local LLM inference"""

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def supports_streaming(self) -> bool:
        return True

    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"

    async def complete(
        self,
        messages: list[AIMessage],
        **kwargs
    ) -> AIResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": [m.dict() for m in messages],
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    }
                },
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()

            return AIResponse(
                content=data["message"]["content"],
                model=data["model"],
                provider=self.name,
                tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                finish_reason="stop"
            )

    async def stream(
        self,
        messages: list[AIMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": [m.dict() for m in messages],
                    "stream": True
                },
                timeout=self.config.timeout
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if data.get("message", {}).get("content"):
                            yield data["message"]["content"]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available Ollama models"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]

    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=600  # Models can be large
            )
            return response.status_code == 200
```

### 2.3 AI Router

```python
# mindset/ai/router.py

from enum import Enum
from typing import Optional
from .providers.base import AIProvider, AIProviderConfig, AIResponse, AIMessage

class RoutingStrategy(Enum):
    COST_OPTIMIZED = "cost"      # Prefer cheaper providers
    SPEED_OPTIMIZED = "speed"    # Prefer faster providers
    QUALITY_OPTIMIZED = "quality" # Prefer best quality
    LOCAL_FIRST = "local"        # Prefer local providers
    CLOUD_FIRST = "cloud"        # Prefer cloud providers

class AIRouter:
    """Routes AI requests to appropriate providers"""

    def __init__(self):
        self.providers: dict[str, AIProvider] = {}
        self.task_routing: dict[str, str] = {}
        self.default_strategy = RoutingStrategy.LOCAL_FIRST

    def register_provider(self, provider: AIProvider):
        """Register an AI provider"""
        self.providers[provider.name] = provider

    def set_task_routing(self, task: str, provider: str):
        """Set preferred provider for a specific task"""
        self.task_routing[task] = provider

    async def get_provider_for_task(
        self,
        task: str,
        strategy: Optional[RoutingStrategy] = None
    ) -> AIProvider:
        """Get the best provider for a task"""
        strategy = strategy or self.default_strategy

        # Check explicit task routing first
        if task in self.task_routing:
            provider_name = self.task_routing[task]
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if await provider.health_check():
                    return provider

        # Apply routing strategy
        if strategy == RoutingStrategy.LOCAL_FIRST:
            return await self._get_local_first()
        elif strategy == RoutingStrategy.CLOUD_FIRST:
            return await self._get_cloud_first()
        elif strategy == RoutingStrategy.COST_OPTIMIZED:
            return await self._get_cost_optimized()
        elif strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            return await self._get_quality_optimized()
        else:
            return await self._get_any_available()

    async def _get_local_first(self) -> AIProvider:
        """Prefer local providers (Ollama, LM Studio)"""
        local_providers = ["ollama", "lmstudio"]
        for name in local_providers:
            if name in self.providers:
                if await self.providers[name].health_check():
                    return self.providers[name]
        return await self._get_any_available()

    async def _get_cloud_first(self) -> AIProvider:
        """Prefer cloud providers"""
        cloud_providers = ["deepinfra", "openai", "huggingface"]
        for name in cloud_providers:
            if name in self.providers:
                if await self.providers[name].health_check():
                    return self.providers[name]
        return await self._get_any_available()

    async def _get_cost_optimized(self) -> AIProvider:
        """Prefer cheaper providers"""
        cost_order = ["ollama", "lmstudio", "deepinfra", "huggingface", "openai"]
        for name in cost_order:
            if name in self.providers:
                if await self.providers[name].health_check():
                    return self.providers[name]
        raise RuntimeError("No AI providers available")

    async def _get_quality_optimized(self) -> AIProvider:
        """Prefer higher quality providers"""
        quality_order = ["openai", "deepinfra", "ollama", "huggingface", "lmstudio"]
        for name in quality_order:
            if name in self.providers:
                if await self.providers[name].health_check():
                    return self.providers[name]
        raise RuntimeError("No AI providers available")

    async def _get_any_available(self) -> AIProvider:
        """Get any available provider"""
        for provider in self.providers.values():
            if await provider.health_check():
                return provider
        raise RuntimeError("No AI providers available")
```

---

## 3. AI Services

### 3.1 Log Analyzer

```python
# mindset/ai/services/log_analyzer.py

from typing import Optional
from ..router import AIRouter
from ..providers.base import AIMessage

class LogAnalyzer:
    """AI-powered log analysis service"""

    SYSTEM_PROMPT = """You are an expert system administrator and Laravel developer.
    Analyze the provided logs and:
    1. Identify errors, warnings, and anomalies
    2. Explain the root cause of issues
    3. Suggest specific fixes with code examples when applicable
    4. Prioritize issues by severity

    Be concise but thorough. Focus on actionable insights."""

    def __init__(self, router: AIRouter):
        self.router = router

    async def analyze(
        self,
        logs: str,
        context: Optional[str] = None,
        app_type: str = "laravel"
    ) -> dict:
        """Analyze logs and return insights"""
        provider = await self.router.get_provider_for_task("log_analysis")

        user_message = f"""Analyze these {app_type} application logs:

```
{logs[:10000]}  # Truncate for token limits
```

{f'Additional context: {context}' if context else ''}

Provide:
1. Summary of issues found
2. Root cause analysis
3. Recommended fixes
4. Severity assessment (critical/high/medium/low)"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "analysis": response.content,
            "provider": response.provider,
            "model": response.model,
            "tokens_used": response.tokens_used
        }

    async def explain_error(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        code_context: Optional[str] = None
    ) -> dict:
        """Explain a specific error"""
        provider = await self.router.get_provider_for_task("error_explanation")

        user_message = f"""Explain this error and how to fix it:

Error: {error_message}

{f'Stack trace:\n```\n{stack_trace}\n```' if stack_trace else ''}

{f'Relevant code:\n```php\n{code_context}\n```' if code_context else ''}

Provide:
1. What the error means
2. Common causes
3. Step-by-step fix
4. How to prevent it in the future"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "explanation": response.content,
            "provider": response.provider,
            "model": response.model
        }
```

### 3.2 Security Scanner

```python
# mindset/ai/services/security_scanner.py

from typing import Optional
from ..router import AIRouter
from ..providers.base import AIMessage

class SecurityScanner:
    """AI-powered security scanning service"""

    SYSTEM_PROMPT = """You are an expert application security engineer specializing in Laravel and PHP.
    Analyze code and configurations for security vulnerabilities including:
    - SQL injection
    - XSS (Cross-Site Scripting)
    - CSRF vulnerabilities
    - Authentication/Authorization flaws
    - Insecure file operations
    - Sensitive data exposure
    - Security misconfigurations

    Provide specific line numbers and code examples for fixes.
    Rate severity using CVSS-like scoring (Critical/High/Medium/Low)."""

    def __init__(self, router: AIRouter):
        self.router = router

    async def scan_code(
        self,
        code: str,
        filename: str,
        language: str = "php"
    ) -> dict:
        """Scan code for security vulnerabilities"""
        provider = await self.router.get_provider_for_task("security_scan")

        user_message = f"""Scan this {language} code for security vulnerabilities:

Filename: {filename}

```{language}
{code[:8000]}
```

Provide:
1. List of vulnerabilities found with line numbers
2. Severity rating for each
3. Specific fix recommendations with code
4. Overall security assessment"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "findings": response.content,
            "file": filename,
            "provider": response.provider
        }

    async def analyze_config(
        self,
        config: str,
        config_type: str = "env"
    ) -> dict:
        """Analyze configuration for security issues"""
        provider = await self.router.get_provider_for_task("security_scan")

        # Redact potential secrets
        redacted_config = self._redact_secrets(config)

        user_message = f"""Analyze this {config_type} configuration for security issues:

```
{redacted_config}
```

Check for:
1. Exposed secrets or credentials
2. Debug mode in production
3. Insecure settings
4. Missing security headers
5. Weak encryption settings"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "analysis": response.content,
            "config_type": config_type,
            "provider": response.provider
        }

    def _redact_secrets(self, content: str) -> str:
        """Redact potential secrets from content"""
        import re
        patterns = [
            (r'(password|secret|key|token|api_key)=.+', r'\1=[REDACTED]'),
            (r'(PASSWORD|SECRET|KEY|TOKEN|API_KEY)=.+', r'\1=[REDACTED]'),
        ]
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        return content
```

### 3.3 Performance Tuner

```python
# mindset/ai/services/performance_tuner.py

from typing import Optional
from ..router import AIRouter
from ..providers.base import AIMessage

class PerformanceTuner:
    """AI-powered performance optimization service"""

    SYSTEM_PROMPT = """You are an expert in Laravel performance optimization and server tuning.
    Analyze metrics, configurations, and code to identify performance bottlenecks and provide
    specific, actionable recommendations.

    Consider:
    - PHP-FPM pool settings
    - OPcache configuration
    - Database query optimization
    - Caching strategies (Redis, application cache)
    - Queue worker optimization
    - Asset optimization
    - Server resource allocation"""

    def __init__(self, router: AIRouter):
        self.router = router

    async def analyze_metrics(
        self,
        metrics: dict,
        app_config: Optional[dict] = None
    ) -> dict:
        """Analyze performance metrics and suggest optimizations"""
        provider = await self.router.get_provider_for_task("performance_tuning")

        user_message = f"""Analyze these performance metrics and suggest optimizations:

System Metrics:
- CPU Usage: {metrics.get('cpu_percent', 'N/A')}%
- Memory Usage: {metrics.get('memory_percent', 'N/A')}%
- Disk I/O: {metrics.get('disk_io', 'N/A')}
- Network: {metrics.get('network', 'N/A')}

PHP-FPM Metrics:
- Active Processes: {metrics.get('php_fpm_active', 'N/A')}
- Idle Processes: {metrics.get('php_fpm_idle', 'N/A')}
- Max Children Reached: {metrics.get('php_fpm_max_reached', 'N/A')}

Application Metrics:
- Average Response Time: {metrics.get('avg_response_time', 'N/A')}ms
- Requests per Second: {metrics.get('requests_per_sec', 'N/A')}
- Error Rate: {metrics.get('error_rate', 'N/A')}%

{f'Current Config: {app_config}' if app_config else ''}

Provide specific configuration changes with before/after values."""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "recommendations": response.content,
            "provider": response.provider
        }

    async def optimize_query(self, query: str, explain_output: Optional[str] = None) -> dict:
        """Analyze and optimize a database query"""
        provider = await self.router.get_provider_for_task("performance_tuning")

        user_message = f"""Optimize this database query:

```sql
{query}
```

{f'EXPLAIN output:\n```\n{explain_output}\n```' if explain_output else ''}

Provide:
1. Optimized query
2. Suggested indexes
3. Explanation of changes"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "optimization": response.content,
            "provider": response.provider
        }
```

---

## 4. Configuration

### 4.1 AI Configuration File

```yaml
# /etc/mindset/ai.yaml

ai:
  enabled: true

  # Privacy settings
  privacy:
    redact_secrets: true
    anonymize_paths: true
    local_only_mode: false  # Set to true to disable cloud providers

  # Default routing strategy
  routing:
    default_strategy: "local_first"  # local_first, cloud_first, cost, quality

    # Task-specific routing
    tasks:
      log_analysis: "ollama"
      error_explanation: "deepinfra"
      security_scan: "ollama"
      performance_tuning: "deepinfra"
      code_review: "deepinfra"
      deployment_assist: "ollama"

  # Provider configurations
  providers:
    ollama:
      enabled: true
      host: "localhost"
      port: 11434
      default_model: "llama3.1:8b"
      models:
        - "llama3.1:8b"
        - "codellama:13b"
        - "mistral:7b"

    deepinfra:
      enabled: true
      api_key: "${DEEPINFRA_API_KEY}"  # Environment variable
      default_model: "meta-llama/Meta-Llama-3.1-70B-Instruct"
      models:
        - "meta-llama/Meta-Llama-3.1-70B-Instruct"
        - "meta-llama/Meta-Llama-3.1-8B-Instruct"
        - "codellama/CodeLlama-34b-Instruct-hf"

    openai:
      enabled: false  # Disabled by default (paid)
      api_key: "${OPENAI_API_KEY}"
      default_model: "gpt-4-turbo-preview"

    lmstudio:
      enabled: false
      host: "localhost"
      port: 1234
      default_model: "local-model"

    huggingface:
      enabled: false
      api_key: "${HUGGINGFACE_API_KEY}"
      default_model: "meta-llama/Llama-2-70b-chat-hf"

  # Rate limiting
  rate_limits:
    requests_per_minute: 60
    tokens_per_day: 1000000

  # Caching
  cache:
    enabled: true
    ttl_seconds: 3600
    max_entries: 1000
```

### 4.2 User BYOK Configuration

```python
# mindset/ai/byok.py

from typing import Optional
from pydantic import BaseModel
from cryptography.fernet import Fernet

class UserAIConfig(BaseModel):
    """Per-user AI configuration with BYOK support"""
    user_id: int

    # User's own API keys (encrypted)
    openai_key: Optional[str] = None
    deepinfra_key: Optional[str] = None
    huggingface_key: Optional[str] = None

    # User preferences
    preferred_provider: Optional[str] = None
    local_only: bool = False

class BYOKManager:
    """Manage Bring Your Own Key configurations"""

    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)

    def encrypt_key(self, api_key: str) -> str:
        """Encrypt an API key for storage"""
        return self.cipher.encrypt(api_key.encode()).decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key for use"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()

    def save_user_config(self, config: UserAIConfig):
        """Save user AI configuration to database"""
        # Encrypt any API keys before saving
        if config.openai_key:
            config.openai_key = self.encrypt_key(config.openai_key)
        if config.deepinfra_key:
            config.deepinfra_key = self.encrypt_key(config.deepinfra_key)
        if config.huggingface_key:
            config.huggingface_key = self.encrypt_key(config.huggingface_key)

        # Save to database...

    def get_user_provider(self, user_id: int, provider_name: str) -> Optional[str]:
        """Get user's API key for a provider"""
        # Load from database...
        # Decrypt and return
        pass
```

---

## 5. API Endpoints

### 5.1 AI API Routes

```python
# mindset/ai/api.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])

class LogAnalysisRequest(BaseModel):
    logs: str
    context: Optional[str] = None
    app_type: str = "laravel"

class ErrorExplainRequest(BaseModel):
    error_message: str
    stack_trace: Optional[str] = None
    code_context: Optional[str] = None

class SecurityScanRequest(BaseModel):
    code: str
    filename: str
    language: str = "php"

@router.post("/analyze/logs")
async def analyze_logs(request: LogAnalysisRequest):
    """Analyze application logs using AI"""
    analyzer = get_log_analyzer()
    result = await analyzer.analyze(
        logs=request.logs,
        context=request.context,
        app_type=request.app_type
    )
    return result

@router.post("/explain/error")
async def explain_error(request: ErrorExplainRequest):
    """Get AI explanation for an error"""
    analyzer = get_log_analyzer()
    result = await analyzer.explain_error(
        error_message=request.error_message,
        stack_trace=request.stack_trace,
        code_context=request.code_context
    )
    return result

@router.post("/scan/security")
async def scan_security(request: SecurityScanRequest):
    """Scan code for security vulnerabilities"""
    scanner = get_security_scanner()
    result = await scanner.scan_code(
        code=request.code,
        filename=request.filename,
        language=request.language
    )
    return result

@router.get("/providers")
async def list_providers():
    """List available AI providers and their status"""
    router = get_ai_router()
    providers = []
    for name, provider in router.providers.items():
        providers.append({
            "name": name,
            "available": await provider.health_check(),
            "supports_streaming": provider.supports_streaming
        })
    return {"providers": providers}

@router.post("/providers/{provider}/test")
async def test_provider(provider: str):
    """Test a specific AI provider"""
    router = get_ai_router()
    if provider not in router.providers:
        raise HTTPException(status_code=404, detail="Provider not found")

    is_available = await router.providers[provider].health_check()
    return {"provider": provider, "available": is_available}
```

---

## 6. Installation & Setup

### 6.1 Ollama Installation

```bash
#!/bin/bash
# Install Ollama for local LLM support

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
systemctl enable ollama
systemctl start ollama

# Pull recommended models
ollama pull llama3.1:8b
ollama pull codellama:13b

# Verify installation
ollama list
```

### 6.2 AI Service Setup

```python
# mindset/ai/setup.py

import yaml
from pathlib import Path
from .router import AIRouter
from .providers.ollama import OllamaProvider
from .providers.deepinfra import DeepInfraProvider
from .providers.base import AIProviderConfig

def setup_ai_services(config_path: str = "/etc/mindset/ai.yaml") -> AIRouter:
    """Initialize AI services from configuration"""

    # Load configuration
    config = yaml.safe_load(Path(config_path).read_text())
    ai_config = config.get("ai", {})

    # Create router
    router = AIRouter()

    # Setup Ollama if enabled
    if ai_config.get("providers", {}).get("ollama", {}).get("enabled"):
        ollama_config = ai_config["providers"]["ollama"]
        provider = OllamaProvider(AIProviderConfig(
            base_url=f"http://{ollama_config['host']}:{ollama_config['port']}",
            model=ollama_config["default_model"]
        ))
        router.register_provider(provider)

    # Setup DeepInfra if enabled
    if ai_config.get("providers", {}).get("deepinfra", {}).get("enabled"):
        deepinfra_config = ai_config["providers"]["deepinfra"]
        import os
        api_key = os.environ.get("DEEPINFRA_API_KEY") or deepinfra_config.get("api_key", "")
        if api_key and not api_key.startswith("$"):
            provider = DeepInfraProvider(AIProviderConfig(
                api_key=api_key,
                model=deepinfra_config["default_model"]
            ))
            router.register_provider(provider)

    # Setup task routing
    task_routing = ai_config.get("routing", {}).get("tasks", {})
    for task, provider in task_routing.items():
        router.set_task_routing(task, provider)

    return router
```

---

## 7. UI Integration

### 7.1 AI Dashboard Component

```html
<!-- mindset/templates/ai/dashboard.html -->
{% extends "baseTemplate/index.html" %}

{% block content %}
<div class="ai-dashboard">
    <div class="card">
        <div class="card-header">
            <h3>AI Services</h3>
        </div>
        <div class="card-body">
            <div class="provider-status">
                <h4>Provider Status</h4>
                <div id="provider-list">
                    <!-- Populated via JavaScript -->
                </div>
            </div>

            <div class="quick-actions mt-4">
                <h4>Quick Actions</h4>
                <button class="btn btn-primary" onclick="openLogAnalyzer()">
                    Analyze Logs
                </button>
                <button class="btn btn-secondary" onclick="openSecurityScan()">
                    Security Scan
                </button>
                <button class="btn btn-info" onclick="openPerfTuner()">
                    Performance Tips
                </button>
            </div>
        </div>
    </div>

    <!-- Log Analysis Modal -->
    <div class="modal" id="logAnalyzerModal">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5>AI Log Analysis</h5>
                </div>
                <div class="modal-body">
                    <textarea id="logInput" rows="10"
                        placeholder="Paste your logs here..."></textarea>
                    <button class="btn btn-primary mt-2" onclick="analyzeLogs()">
                        Analyze
                    </button>
                    <div id="analysisResult" class="mt-3"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
async function loadProviderStatus() {
    const response = await fetch('/api/v1/ai/providers');
    const data = await response.json();

    const list = document.getElementById('provider-list');
    list.innerHTML = data.providers.map(p => `
        <div class="provider-item">
            <span class="name">${p.name}</span>
            <span class="status ${p.available ? 'online' : 'offline'}">
                ${p.available ? 'Online' : 'Offline'}
            </span>
        </div>
    `).join('');
}

async function analyzeLogs() {
    const logs = document.getElementById('logInput').value;
    const resultDiv = document.getElementById('analysisResult');

    resultDiv.innerHTML = '<div class="loading">Analyzing...</div>';

    const response = await fetch('/api/v1/ai/analyze/logs', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({logs: logs, app_type: 'laravel'})
    });

    const data = await response.json();
    resultDiv.innerHTML = `<pre>${data.analysis}</pre>`;
}

// Load on page load
loadProviderStatus();
</script>
{% endblock %}
```

---

## 8. Privacy & Security

### 8.1 Data Handling Policies

1. **Secret Redaction**: All logs and code are scanned for secrets before sending to cloud providers
2. **Path Anonymization**: File paths are anonymized to protect server structure
3. **Local-Only Mode**: Users can opt to use only local AI providers
4. **BYOK**: Users can provide their own API keys, stored encrypted
5. **Data Retention**: No AI queries are stored beyond session cache
6. **Audit Logging**: All AI interactions are logged for security audit

### 8.2 Security Implementation

```python
# mindset/ai/security.py

import re
from typing import List

class AISecurityFilter:
    """Filter sensitive data before AI processing"""

    SECRET_PATTERNS = [
        r'(?i)(password|passwd|pwd)\s*[=:]\s*[^\s]+',
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*[^\s]+',
        r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*[^\s]+',
        r'(?i)(access[_-]?token|accesstoken)\s*[=:]\s*[^\s]+',
        r'(?i)(auth[_-]?token|authtoken)\s*[=:]\s*[^\s]+',
        r'(?i)bearer\s+[a-zA-Z0-9\-_]+',
        r'(?i)(aws[_-]?secret|awssecret)\s*[=:]\s*[^\s]+',
        r'[a-f0-9]{32,}',  # Hash-like strings
    ]

    PATH_PATTERNS = [
        (r'/home/[^/]+/', '/home/[USER]/'),
        (r'/var/www/[^/]+/', '/var/www/[SITE]/'),
    ]

    def redact_secrets(self, content: str) -> str:
        """Remove secrets from content"""
        for pattern in self.SECRET_PATTERNS:
            content = re.sub(pattern, '[REDACTED]', content)
        return content

    def anonymize_paths(self, content: str) -> str:
        """Anonymize file paths"""
        for pattern, replacement in self.PATH_PATTERNS:
            content = re.sub(pattern, replacement, content)
        return content

    def filter_content(self, content: str, redact: bool = True, anonymize: bool = True) -> str:
        """Apply all security filters"""
        if redact:
            content = self.redact_secrets(content)
        if anonymize:
            content = self.anonymize_paths(content)
        return content
```

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
