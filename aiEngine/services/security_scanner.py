# Mindset AI Engine - Security Scanner Service
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

import re
from typing import Optional, Dict, List, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from ..providers.base import AIMessage


class Severity(Enum):
    """Security finding severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityFinding:
    """Represents a security finding"""
    title: str
    description: str
    severity: Severity
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "cwe_id": self.cwe_id,
        }


class SecurityScanner:
    """
    AI-powered security scanning service

    Analyzes code and configurations for security vulnerabilities including:
    - SQL injection
    - XSS (Cross-Site Scripting)
    - CSRF vulnerabilities
    - Authentication/Authorization flaws
    - Insecure file operations
    - Sensitive data exposure
    - Security misconfigurations

    Provides OWASP-aligned analysis with CWE IDs where applicable.
    """

    SYSTEM_PROMPT = """You are an expert application security engineer specializing in Laravel and PHP security.
Analyze code and configurations for security vulnerabilities.

Focus on:
- SQL injection (CWE-89)
- XSS - Cross-Site Scripting (CWE-79)
- CSRF vulnerabilities (CWE-352)
- Authentication/Authorization flaws (CWE-287, CWE-862)
- Insecure file operations (CWE-73)
- Sensitive data exposure (CWE-200)
- Security misconfigurations (CWE-16)
- Insecure deserialization (CWE-502)
- Command injection (CWE-78)

For each finding, provide:
1. Title and severity (critical/high/medium/low)
2. Description of the vulnerability
3. Specific line numbers if possible
4. Code example showing the fix
5. CWE ID if applicable

Rate severity using:
- Critical: Direct exploitation possible, high impact
- High: Exploitation possible with some conditions
- Medium: Limited impact or requires specific conditions
- Low: Minor impact or defense in depth issue"""

    # Pattern-based detection for quick scanning
    VULNERABILITY_PATTERNS = {
        'sql_injection': [
            (r'->whereRaw\s*\([^)]*\$', 'Potential SQL injection in whereRaw'),
            (r'DB::raw\s*\([^)]*\$', 'Potential SQL injection in DB::raw'),
            (r'->selectRaw\s*\([^)]*\$', 'Potential SQL injection in selectRaw'),
            (r'query\s*\([^)]*\$_', 'Direct use of user input in query'),
        ],
        'xss': [
            (r'\{\!\!\s*\$', 'Unescaped output - potential XSS'),
            (r'echo\s+\$_(?:GET|POST|REQUEST)', 'Direct output of user input'),
            (r'->with\([^)]*\$_', 'User input passed directly to view'),
        ],
        'command_injection': [
            (r'exec\s*\([^)]*\$', 'Potential command injection in exec'),
            (r'shell_exec\s*\([^)]*\$', 'Potential command injection in shell_exec'),
            (r'system\s*\([^)]*\$', 'Potential command injection in system'),
            (r'passthru\s*\([^)]*\$', 'Potential command injection in passthru'),
        ],
        'file_inclusion': [
            (r'include\s*\([^)]*\$', 'Potential file inclusion vulnerability'),
            (r'require\s*\([^)]*\$', 'Potential file inclusion vulnerability'),
            (r'file_get_contents\s*\([^)]*\$', 'Potential arbitrary file read'),
        ],
        'insecure_config': [
            (r"APP_DEBUG\s*=\s*true", 'Debug mode enabled (check if production)'),
            (r"APP_ENV\s*=\s*local", 'Local environment setting'),
            (r'MAIL_PASSWORD\s*=\s*[^\s]+', 'Mail password in config'),
        ],
        'hardcoded_secrets': [
            (r"password\s*=\s*['\"][^'\"]+['\"]", 'Hardcoded password'),
            (r"api_key\s*=\s*['\"][^'\"]+['\"]", 'Hardcoded API key'),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", 'Hardcoded secret'),
        ],
    }

    def __init__(self, ai_router):
        """
        Initialize security scanner

        Args:
            ai_router: AI router instance for provider selection
        """
        self.router = ai_router

    async def scan_code(
        self,
        code: str,
        filename: str,
        language: str = "php"
    ) -> Dict[str, Any]:
        """
        Scan code for security vulnerabilities

        Args:
            code: Source code to analyze
            filename: Name of the file
            language: Programming language

        Returns:
            Dict containing findings and analysis
        """
        # First, run quick pattern-based detection
        quick_findings = self._quick_scan(code, filename)

        # Then, use AI for deeper analysis
        provider = await self.router.get_provider_for_task("security_scan")

        # Truncate code if too long
        truncated_code = code[:8000] if len(code) > 8000 else code

        user_message = f"""Scan this {language} code for security vulnerabilities:

Filename: {filename}

```{language}
{truncated_code}
```

Initial pattern scan found {len(quick_findings)} potential issues:
{self._format_quick_findings(quick_findings)}

Provide a thorough security analysis with:
1. List of vulnerabilities found with line numbers
2. Severity rating for each (critical/high/medium/low)
3. Specific fix recommendations with code examples
4. CWE IDs where applicable
5. Overall security assessment"""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "analysis": response.content,
            "quick_findings": [f.to_dict() for f in quick_findings],
            "file": filename,
            "provider": response.provider,
            "model": response.model,
            "tokens_used": response.tokens_used,
        }

    async def scan_config(
        self,
        config: str,
        config_type: str = "env"
    ) -> Dict[str, Any]:
        """
        Analyze configuration for security issues

        Args:
            config: Configuration content
            config_type: Type of config (env, php, yaml, etc.)

        Returns:
            Dict containing analysis
        """
        provider = await self.router.get_provider_for_task("security_scan")

        # Redact potential secrets before sending to AI
        redacted_config = self._redact_secrets(config)

        user_message = f"""Analyze this {config_type} configuration for security issues:

```
{redacted_config}
```

Check for:
1. Debug mode or development settings in production
2. Exposed secrets or credentials (some have been redacted)
3. Insecure default settings
4. Missing security configurations
5. Weak encryption or session settings
6. Missing security headers configuration
7. Overly permissive CORS settings

Provide specific recommendations for each issue found."""

        response = await provider.complete([
            AIMessage(role="system", content=self.SYSTEM_PROMPT),
            AIMessage(role="user", content=user_message)
        ])

        return {
            "analysis": response.content,
            "config_type": config_type,
            "provider": response.provider,
        }

    async def scan_directory(
        self,
        directory: Path,
        extensions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Scan an entire directory for security issues

        Args:
            directory: Directory path to scan
            extensions: File extensions to scan (default: php, blade.php, env)

        Returns:
            Dict containing all findings
        """
        extensions = extensions or ['.php', '.blade.php', '.env']

        all_findings = []
        files_scanned = 0
        errors = []

        for ext in extensions:
            pattern = f"**/*{ext}" if ext.startswith('.') else f"**/*.{ext}"
            for file_path in directory.glob(pattern):
                try:
                    content = file_path.read_text()
                    findings = self._quick_scan(content, str(file_path))
                    all_findings.extend(findings)
                    files_scanned += 1
                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

        # Summarize by severity
        severity_counts = {s.value: 0 for s in Severity}
        for finding in all_findings:
            severity_counts[finding.severity.value] += 1

        return {
            "files_scanned": files_scanned,
            "total_findings": len(all_findings),
            "severity_counts": severity_counts,
            "findings": [f.to_dict() for f in all_findings[:100]],  # Limit to top 100
            "errors": errors,
        }

    async def analyze_laravel_app(
        self,
        app_path: Path
    ) -> Dict[str, Any]:
        """
        Perform Laravel-specific security analysis

        Args:
            app_path: Path to Laravel application

        Returns:
            Comprehensive security analysis
        """
        findings = []
        checks = []

        # Check 1: .env file exposure
        env_file = app_path / ".env"
        public_env = app_path / "public" / ".env"
        if public_env.exists():
            findings.append(SecurityFinding(
                title=".env file in public directory",
                description="The .env file is accessible from the public directory",
                severity=Severity.CRITICAL,
                file_path=str(public_env),
                recommendation="Remove .env from public directory immediately",
                cwe_id="CWE-200"
            ))
        checks.append({"name": ".env exposure", "passed": not public_env.exists()})

        # Check 2: Debug mode
        if env_file.exists():
            env_content = env_file.read_text()
            if "APP_DEBUG=true" in env_content and "APP_ENV=production" in env_content:
                findings.append(SecurityFinding(
                    title="Debug mode enabled in production",
                    description="APP_DEBUG is true while APP_ENV is production",
                    severity=Severity.HIGH,
                    file_path=str(env_file),
                    recommendation="Set APP_DEBUG=false in production",
                    cwe_id="CWE-489"
                ))
        checks.append({"name": "Debug mode check", "passed": True})

        # Check 3: Storage symlink
        storage_link = app_path / "public" / "storage"
        checks.append({"name": "Storage symlink", "passed": storage_link.is_symlink()})

        # Check 4: Key generation
        if env_file.exists():
            env_content = env_file.read_text()
            if "APP_KEY=" in env_content and "APP_KEY=\n" not in env_content:
                checks.append({"name": "APP_KEY set", "passed": True})
            else:
                findings.append(SecurityFinding(
                    title="Missing APP_KEY",
                    description="APP_KEY is not set in .env file",
                    severity=Severity.CRITICAL,
                    file_path=str(env_file),
                    recommendation="Run: php artisan key:generate",
                    cwe_id="CWE-310"
                ))
                checks.append({"name": "APP_KEY set", "passed": False})

        # Check 5: Common vulnerable files
        vulnerable_files = [
            "phpinfo.php",
            "info.php",
            "test.php",
            ".git/config",
            ".gitignore",
            "composer.json",
        ]

        for vf in vulnerable_files:
            public_file = app_path / "public" / vf
            if public_file.exists():
                findings.append(SecurityFinding(
                    title=f"Sensitive file in public directory: {vf}",
                    description=f"File {vf} should not be publicly accessible",
                    severity=Severity.MEDIUM,
                    file_path=str(public_file),
                    recommendation=f"Remove or restrict access to {vf}",
                    cwe_id="CWE-200"
                ))

        # Check 6: Scan key PHP files for vulnerabilities
        key_files = [
            app_path / "routes" / "web.php",
            app_path / "routes" / "api.php",
            app_path / "app" / "Http" / "Controllers",
        ]

        for key_path in key_files:
            if key_path.is_file():
                content = key_path.read_text()
                file_findings = self._quick_scan(content, str(key_path))
                findings.extend(file_findings)
            elif key_path.is_dir():
                for php_file in key_path.glob("**/*.php"):
                    content = php_file.read_text()
                    file_findings = self._quick_scan(content, str(php_file))
                    findings.extend(file_findings)

        # Summary
        severity_counts = {s.value: 0 for s in Severity}
        for finding in findings:
            severity_counts[finding.severity.value] += 1

        return {
            "checks": checks,
            "findings": [f.to_dict() for f in findings],
            "severity_counts": severity_counts,
            "total_findings": len(findings),
            "overall_score": self._calculate_security_score(findings, checks),
        }

    def _quick_scan(
        self,
        code: str,
        filename: str
    ) -> List[SecurityFinding]:
        """Pattern-based quick scan for common vulnerabilities"""
        findings = []

        lines = code.split('\n')

        for category, patterns in self.VULNERABILITY_PATTERNS.items():
            for pattern, description in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        severity = self._get_severity_for_category(category)
                        findings.append(SecurityFinding(
                            title=f"{category.replace('_', ' ').title()} Detected",
                            description=description,
                            severity=severity,
                            file_path=filename,
                            line_number=line_num,
                            code_snippet=line.strip()[:200],
                            cwe_id=self._get_cwe_for_category(category),
                        ))

        return findings

    def _get_severity_for_category(self, category: str) -> Severity:
        """Get severity level for vulnerability category"""
        severity_map = {
            'sql_injection': Severity.CRITICAL,
            'command_injection': Severity.CRITICAL,
            'xss': Severity.HIGH,
            'file_inclusion': Severity.HIGH,
            'hardcoded_secrets': Severity.HIGH,
            'insecure_config': Severity.MEDIUM,
        }
        return severity_map.get(category, Severity.MEDIUM)

    def _get_cwe_for_category(self, category: str) -> Optional[str]:
        """Get CWE ID for vulnerability category"""
        cwe_map = {
            'sql_injection': 'CWE-89',
            'xss': 'CWE-79',
            'command_injection': 'CWE-78',
            'file_inclusion': 'CWE-98',
            'hardcoded_secrets': 'CWE-798',
            'insecure_config': 'CWE-16',
        }
        return cwe_map.get(category)

    def _redact_secrets(self, content: str) -> str:
        """Redact potential secrets from content"""
        patterns = [
            (r'(password|secret|key|token|api_key)\s*=\s*[^\s]+', r'\1=[REDACTED]'),
            (r'(PASSWORD|SECRET|KEY|TOKEN|API_KEY)\s*=\s*[^\s]+', r'\1=[REDACTED]'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        return content

    def _format_quick_findings(self, findings: List[SecurityFinding]) -> str:
        """Format quick findings for AI prompt"""
        if not findings:
            return "None detected"

        lines = []
        for f in findings[:10]:  # Limit to 10
            lines.append(f"- {f.severity.value.upper()}: {f.title} (line {f.line_number})")

        if len(findings) > 10:
            lines.append(f"  ... and {len(findings) - 10} more")

        return "\n".join(lines)

    def _calculate_security_score(
        self,
        findings: List[SecurityFinding],
        checks: List[dict]
    ) -> int:
        """Calculate overall security score (0-100)"""
        score = 100

        # Deduct for findings
        severity_deductions = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0,
        }

        for finding in findings:
            score -= severity_deductions.get(finding.severity, 0)

        # Deduct for failed checks
        failed_checks = sum(1 for c in checks if not c.get('passed', True))
        score -= failed_checks * 5

        return max(0, score)
