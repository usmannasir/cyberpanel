# Mindset AI Engine - Log Analyzer Service
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

from typing import Optional, Dict, List, Any
import re

from ..providers.base import AIMessage


class LogAnalyzer:
    """
    AI-powered log analysis service

    Analyzes Laravel logs and provides:
    - Error identification and categorization
    - Root cause analysis
    - Fix recommendations
    - Severity assessment
    """

    SYSTEM_PROMPT = """You are an expert system administrator and Laravel developer.
Analyze the provided logs and:
1. Identify errors, warnings, and anomalies
2. Explain the root cause of issues in plain language
3. Suggest specific fixes with code examples when applicable
4. Prioritize issues by severity (critical/high/medium/low)

Be concise but thorough. Focus on actionable insights.
Format your response in clear sections."""

    ERROR_PATTERNS = {
        'fatal': [
            r'fatal error',
            r'SQLSTATE',
            r'exception.*thrown',
            r'Out of memory',
        ],
        'error': [
            r'\.ERROR:',
            r'\[error\]',
            r'PHP Error',
            r'Uncaught',
        ],
        'warning': [
            r'\.WARNING:',
            r'\[warning\]',
            r'deprecated',
        ],
        'security': [
            r'unauthorized',
            r'permission denied',
            r'access denied',
            r'invalid token',
            r'csrf',
        ],
    }

    def __init__(self, ai_router):
        """
        Initialize log analyzer

        Args:
            ai_router: AI router instance for provider selection
        """
        self.router = ai_router

    async def analyze(
        self,
        logs: str,
        context: Optional[str] = None,
        app_type: str = "laravel"
    ) -> Dict[str, Any]:
        """
        Analyze logs and return AI-powered insights

        Args:
            logs: Log content to analyze
            context: Optional context about the application
            app_type: Type of application (laravel, php, etc.)

        Returns:
            Dict containing analysis results
        """
        # Get appropriate provider
        provider = await self.router.get_provider_for_task("log_analysis")

        # Pre-analyze for quick stats
        stats = self._pre_analyze(logs)

        # Truncate logs if too long
        truncated_logs = logs[:10000] if len(logs) > 10000 else logs

        # Build prompt
        user_message = f"""Analyze these {app_type} application logs:

```
{truncated_logs}
```

{f'Additional context: {context}' if context else ''}

Quick stats:
- Fatal errors: {stats['fatal_count']}
- Errors: {stats['error_count']}
- Warnings: {stats['warning_count']}
- Security issues: {stats['security_count']}

Provide:
1. Summary of issues found
2. Root cause analysis for critical issues
3. Recommended fixes with specific code/commands
4. Severity assessment (critical/high/medium/low)"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "analysis": response.content,
            "provider": response.provider,
            "model": response.model,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
            "stats": stats,
        }

    async def explain_error(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        code_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get AI explanation for a specific error

        Args:
            error_message: The error message
            stack_trace: Optional stack trace
            code_context: Optional relevant code snippet

        Returns:
            Dict containing explanation
        """
        provider = await self.router.get_provider_for_task("error_explanation")

        user_message = f"""Explain this error and how to fix it:

Error: {error_message}

{f'Stack trace:\n```\n{stack_trace}\n```' if stack_trace else ''}

{f'Relevant code:\n```php\n{code_context}\n```' if code_context else ''}

Provide:
1. What the error means in plain language
2. Common causes of this error
3. Step-by-step fix instructions
4. How to prevent it in the future"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "explanation": response.content,
            "provider": response.provider,
            "model": response.model,
            "tokens_used": response.tokens_used,
        }

    async def categorize_errors(
        self,
        logs: str
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Categorize errors found in logs

        Args:
            logs: Log content

        Returns:
            Dict with categorized errors
        """
        categories = {
            "fatal": [],
            "database": [],
            "authentication": [],
            "validation": [],
            "performance": [],
            "other": [],
        }

        # Pattern matching for categorization
        patterns = {
            "fatal": [r"fatal", r"SQLSTATE.*\[HY000\]"],
            "database": [r"SQLSTATE", r"MySQL", r"PDO", r"database"],
            "authentication": [r"auth", r"login", r"token", r"session"],
            "validation": [r"validation", r"required", r"invalid"],
            "performance": [r"timeout", r"memory", r"slow"],
        }

        lines = logs.split('\n')
        for line in lines:
            line_lower = line.lower()
            categorized = False

            for category, category_patterns in patterns.items():
                for pattern in category_patterns:
                    if re.search(pattern, line_lower):
                        categories[category].append({
                            "line": line[:200],
                            "pattern": pattern
                        })
                        categorized = True
                        break
                if categorized:
                    break

            # If error but not categorized
            if not categorized and any(p in line_lower for p in ['error', 'exception']):
                categories["other"].append({"line": line[:200]})

        return categories

    def _pre_analyze(self, logs: str) -> Dict[str, int]:
        """Quick pattern-based analysis for stats"""
        logs_lower = logs.lower()

        stats = {
            "fatal_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "security_count": 0,
            "total_lines": logs.count('\n') + 1,
        }

        for category, patterns in self.ERROR_PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, logs_lower))
            stats[f"{category}_count"] = count

        return stats
