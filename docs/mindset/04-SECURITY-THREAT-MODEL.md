# Security Threat Model - Mindset Platform

## Executive Summary

This document outlines the security threat model for the Mindset hosting platform. It identifies potential threats, vulnerabilities, attack vectors, and the corresponding mitigations implemented in the system.

---

## 1. System Overview

### 1.1 Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TRUST BOUNDARIES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  UNTRUSTED ZONE (Internet)                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  - Anonymous users                                                     │  │
│  │  - Potential attackers                                                 │  │
│  │  - Automated bots/scanners                                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                            ═══════╪═══════  Firewall/WAF                    │
│                                    │                                         │
│  SEMI-TRUSTED ZONE (DMZ)                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  - OpenLiteSpeed (public web)                                         │  │
│  │  - Hosted Laravel applications                                         │  │
│  │  - SSH access (key-only)                                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                            ═══════╪═══════  Internal Firewall               │
│                                    │                                         │
│  TRUSTED ZONE (Internal)                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  - Mindset Control Panel                                               │  │
│  │  - Database servers                                                    │  │
│  │  - Backup systems                                                      │  │
│  │  - AI services (local)                                                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Assets

| Asset | Classification | Impact if Compromised |
|-------|---------------|----------------------|
| User credentials | Critical | Full system access |
| API keys | Critical | Service impersonation |
| Database content | High | Data breach, privacy violation |
| SSL private keys | Critical | MITM attacks, impersonation |
| Backup data | High | Historical data exposure |
| Application code | Medium | IP theft, vulnerability exposure |
| System configuration | High | System compromise |
| AI API keys | Medium | Financial loss, service abuse |

---

## 2. Threat Categories (STRIDE)

### 2.1 Spoofing Identity

| Threat | Attack Vector | Likelihood | Impact | Mitigation |
|--------|--------------|------------|--------|------------|
| Session hijacking | Stolen session cookies | Medium | Critical | Secure cookies, session binding |
| API key theft | Exposed keys in logs/code | Medium | High | Key rotation, secure storage |
| SSH key compromise | Stolen private keys | Low | Critical | Key passphrase, 2FA |
| Admin impersonation | Credential stuffing | Medium | Critical | Rate limiting, 2FA, strong passwords |

#### Mitigations Implemented

```python
# Session Security (mindset/security/session.py)
class SessionSecurity:
    def bind_session_to_ip(self, session, ip_address):
        """Bind session to originating IP"""
        session['bound_ip'] = ip_address
        session['created_at'] = datetime.utcnow().isoformat()

    def validate_session(self, session, request_ip):
        """Validate session binding"""
        if session.get('bound_ip') != request_ip:
            raise SessionHijackingDetected()

        # Check session age
        created = datetime.fromisoformat(session['created_at'])
        if (datetime.utcnow() - created).hours > 24:
            raise SessionExpired()
```

### 2.2 Tampering

| Threat | Attack Vector | Likelihood | Impact | Mitigation |
|--------|--------------|------------|--------|------------|
| SQL injection | Malicious input | Medium | Critical | Parameterized queries, ORM |
| Command injection | Unsanitized shell commands | Medium | Critical | Input validation, sandboxing |
| File tampering | Unauthorized file modification | Low | High | File integrity monitoring |
| Config tampering | Direct config file editing | Low | High | File permissions, immutable configs |

#### Mitigations Implemented

```python
# Input Validation (mindset/security/validation.py)
import re
from typing import Optional

class InputValidator:
    DANGEROUS_PATTERNS = [
        r'[;&|`$]',           # Shell metacharacters
        r'\.\.',              # Directory traversal
        r'<script',           # XSS
        r'union\s+select',    # SQL injection
        r'--',                # SQL comment
    ]

    def sanitize_input(self, value: str, allow_special: bool = False) -> str:
        """Sanitize user input"""
        if not allow_special:
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    raise DangerousInputDetected(f"Pattern detected: {pattern}")

        # HTML encode
        return html.escape(value)

    def validate_domain(self, domain: str) -> bool:
        """Validate domain name format"""
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))

    def validate_path(self, path: str, base_dir: str) -> bool:
        """Validate file path is within allowed directory"""
        real_path = os.path.realpath(path)
        real_base = os.path.realpath(base_dir)
        return real_path.startswith(real_base)
```

### 2.3 Repudiation

| Threat | Attack Vector | Likelihood | Impact | Mitigation |
|--------|--------------|------------|--------|------------|
| Action denial | No audit trail | Medium | Medium | Comprehensive logging |
| Log tampering | Direct log file access | Low | High | Log integrity, remote logging |
| Timestamp manipulation | System time changes | Low | Medium | NTP sync, signed timestamps |

#### Mitigations Implemented

```python
# Audit Logging (mindset/security/audit.py)
import hashlib
import json
from datetime import datetime

class AuditLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.previous_hash = None

    def log_action(
        self,
        user_id: int,
        action: str,
        resource: str,
        details: dict,
        ip_address: str
    ):
        """Log an auditable action with integrity chain"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': details,
            'ip_address': ip_address,
            'previous_hash': self.previous_hash
        }

        # Create integrity hash
        entry_json = json.dumps(entry, sort_keys=True)
        entry['hash'] = hashlib.sha256(entry_json.encode()).hexdigest()
        self.previous_hash = entry['hash']

        # Write to log
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        # Also send to remote syslog for redundancy
        self._send_to_syslog(entry)

    def verify_log_integrity(self) -> bool:
        """Verify the integrity chain of audit logs"""
        previous_hash = None
        with open(self.log_file, 'r') as f:
            for line in f:
                entry = json.loads(line)
                if entry.get('previous_hash') != previous_hash:
                    return False

                stored_hash = entry.pop('hash')
                entry_json = json.dumps(entry, sort_keys=True)
                calculated_hash = hashlib.sha256(entry_json.encode()).hexdigest()

                if stored_hash != calculated_hash:
                    return False

                previous_hash = stored_hash

        return True
```

### 2.4 Information Disclosure

| Threat | Attack Vector | Likelihood | Impact | Mitigation |
|--------|--------------|------------|--------|------------|
| Data exposure | Misconfigured permissions | Medium | High | Strict permissions, encryption |
| Error message leakage | Verbose error pages | High | Medium | Custom error pages |
| Backup exposure | Unencrypted backups | Medium | Critical | Backup encryption |
| .env exposure | Public access to .env | Medium | Critical | Web server config, .htaccess |

#### Mitigations Implemented

```python
# Secret Management (mindset/security/secrets.py)
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class SecretVault:
    def __init__(self, master_password: str, salt: bytes = None):
        self.salt = salt or os.urandom(16)
        self.cipher = self._create_cipher(master_password)

    def _create_cipher(self, password: str) -> Fernet:
        """Create encryption cipher from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret"""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a secret"""
        return self.cipher.decrypt(ciphertext.encode()).decode()

    def encrypt_env_file(self, env_path: str, output_path: str):
        """Encrypt entire .env file"""
        with open(env_path, 'r') as f:
            content = f.read()

        encrypted = self.encrypt(content)

        with open(output_path, 'w') as f:
            f.write(encrypted)

        # Secure permissions
        os.chmod(output_path, 0o600)
```

### 2.5 Denial of Service

| Threat | Attack Vector | Likelihood | Impact | Mitigation |
|--------|--------------|------------|--------|------------|
| Resource exhaustion | Large file uploads | High | Medium | Upload limits |
| Application DoS | Slow loris attacks | Medium | High | Timeout configs |
| Database DoS | Expensive queries | Medium | High | Query limits, caching |
| Brute force | Login attempts | High | Medium | Rate limiting, lockout |

#### Mitigations Implemented

```python
# Rate Limiting (mindset/security/rate_limit.py)
import redis
import time
from functools import wraps

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """Check if key is rate limited"""
        current_time = int(time.time())
        window_start = current_time - window_seconds

        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Add current request
        pipe.zadd(key, {str(current_time): current_time})

        # Count requests in window
        pipe.zcard(key)

        # Set expiry
        pipe.expire(key, window_seconds)

        results = pipe.execute()
        request_count = results[2]

        remaining = max(0, max_requests - request_count)

        return request_count > max_requests, remaining

    def rate_limit(self, max_requests: int, window_seconds: int):
        """Decorator for rate limiting"""
        def decorator(func):
            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                # Use IP + endpoint as key
                key = f"rate_limit:{request.client.host}:{request.url.path}"

                is_limited, remaining = self.is_rate_limited(
                    key, max_requests, window_seconds
                )

                if is_limited:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded",
                        headers={"Retry-After": str(window_seconds)}
                    )

                response = await func(request, *args, **kwargs)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                return response

            return wrapper
        return decorator
```

### 2.6 Elevation of Privilege

| Threat | Attack Vector | Likelihood | Impact | Mitigation |
|--------|--------------|------------|--------|------------|
| Privilege escalation | Exploiting sudo/permissions | Low | Critical | Least privilege |
| Container escape | Docker vulnerabilities | Low | Critical | Security contexts |
| PHP process escape | open_basedir bypass | Low | High | Strict PHP config |
| ACL bypass | Logic flaws | Medium | High | Thorough ACL checks |

#### Mitigations Implemented

```python
# Access Control (mindset/security/acl.py)
from enum import Enum
from typing import Set

class Permission(Enum):
    # Site permissions
    SITE_CREATE = "site.create"
    SITE_DELETE = "site.delete"
    SITE_MODIFY = "site.modify"
    SITE_VIEW = "site.view"

    # Database permissions
    DB_CREATE = "db.create"
    DB_DELETE = "db.delete"
    DB_ACCESS = "db.access"

    # Admin permissions
    ADMIN_USERS = "admin.users"
    ADMIN_SETTINGS = "admin.settings"
    ADMIN_SECURITY = "admin.security"

    # Laravel-specific
    LARAVEL_DEPLOY = "laravel.deploy"
    LARAVEL_ARTISAN = "laravel.artisan"
    LARAVEL_ENV = "laravel.env"
    LARAVEL_WORKERS = "laravel.workers"

class Role(Enum):
    ADMIN = "admin"
    RESELLER = "reseller"
    USER = "user"

ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # All permissions
    Role.RESELLER: {
        Permission.SITE_CREATE,
        Permission.SITE_DELETE,
        Permission.SITE_MODIFY,
        Permission.SITE_VIEW,
        Permission.DB_CREATE,
        Permission.DB_DELETE,
        Permission.DB_ACCESS,
        Permission.LARAVEL_DEPLOY,
        Permission.LARAVEL_ARTISAN,
        Permission.LARAVEL_ENV,
        Permission.LARAVEL_WORKERS,
    },
    Role.USER: {
        Permission.SITE_VIEW,
        Permission.SITE_MODIFY,
        Permission.DB_ACCESS,
        Permission.LARAVEL_DEPLOY,
        Permission.LARAVEL_ARTISAN,
        Permission.LARAVEL_ENV,
    },
}

class ACLChecker:
    def __init__(self, user):
        self.user = user
        self.role = Role(user.role)

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        # Admin always has access
        if self.role == Role.ADMIN:
            return True

        # Check role permissions
        return permission in ROLE_PERMISSIONS.get(self.role, set())

    def can_access_site(self, site) -> bool:
        """Check if user can access a specific site"""
        if self.role == Role.ADMIN:
            return True

        # Check ownership
        if site.owner_id == self.user.id:
            return True

        # Check if user is under reseller
        if self.user.reseller_id and site.owner.reseller_id == self.user.reseller_id:
            return self.has_permission(Permission.SITE_VIEW)

        return False

    def require_permission(self, permission: Permission):
        """Decorator to require permission"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.has_permission(permission):
                    raise PermissionDenied(
                        f"Permission required: {permission.value}"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
```

---

## 3. Attack Scenarios

### 3.1 Web Application Attacks

#### Scenario: SQL Injection via API

```
Attack Path:
1. Attacker identifies API endpoint accepting user input
2. Crafts malicious SQL payload
3. Attempts injection via API parameters

Mitigations:
- Django ORM prevents direct SQL injection
- Input validation layer
- Parameterized queries for raw SQL
- Web Application Firewall (ModSecurity)
```

#### Scenario: Cross-Site Scripting (XSS)

```
Attack Path:
1. Attacker submits malicious JavaScript in form field
2. Script stored in database
3. Script executes when other users view page

Mitigations:
- Django template auto-escaping
- Content Security Policy headers
- Input sanitization
- HTTPOnly cookies
```

### 3.2 Infrastructure Attacks

#### Scenario: SSH Brute Force

```
Attack Path:
1. Attacker scans for SSH port
2. Attempts password combinations
3. Gains shell access on success

Mitigations:
- Fail2Ban blocks after 5 attempts
- SSH key-only authentication
- Non-standard SSH port (optional)
- CrowdSec community blocklists
```

#### Scenario: Supply Chain Attack

```
Attack Path:
1. Attacker compromises package repository
2. Malicious package installed via pip/npm
3. Code executes during installation or runtime

Mitigations:
- Pinned dependency versions
- Hash verification for packages
- Security scanning of dependencies
- Sandboxed installation environment
```

### 3.3 Laravel-Specific Attacks

#### Scenario: .env File Exposure

```
Attack Path:
1. Attacker requests /.env directly
2. Web server returns file contents
3. Database credentials exposed

Mitigations:
- OpenLiteSpeed config blocks .env access
- .env encrypted at rest
- Environment variables from vault
- File permissions 600
```

#### Scenario: Artisan Command Injection

```
Attack Path:
1. Attacker gains limited access to artisan interface
2. Crafts command with shell injection
3. Executes arbitrary system commands

Mitigations:
- Whitelist of allowed artisan commands
- Parameter sanitization
- PHP-FPM user isolation
- open_basedir restrictions
```

---

## 4. Security Controls Matrix

### 4.1 Preventive Controls

| Control | Implementation | Coverage |
|---------|---------------|----------|
| Firewall (UFW) | System-level | Network |
| WAF (ModSecurity) | OpenLiteSpeed | Application |
| Input Validation | Django middleware | Application |
| Rate Limiting | Redis-based | Application |
| 2FA/MFA | TOTP | Authentication |
| Encryption at Rest | AES-256 | Data |
| TLS 1.3 | Let's Encrypt | Transport |

### 4.2 Detective Controls

| Control | Implementation | Coverage |
|---------|---------------|----------|
| Audit Logging | File + Syslog | All actions |
| Intrusion Detection | Fail2Ban + CrowdSec | Network |
| File Integrity | AIDE/Tripwire | System |
| Log Analysis | AI-powered | Application |
| Security Scanning | AI Scanner | Code |

### 4.3 Corrective Controls

| Control | Implementation | Coverage |
|---------|---------------|----------|
| Auto-ban | Fail2Ban | Attackers |
| Session Invalidation | On breach detection | Sessions |
| Key Rotation | Automated | Credentials |
| Rollback | Deployment system | Application |
| Backup Restore | One-click | Data |

---

## 5. Hardening Checklist

### 5.1 System Hardening

```bash
#!/bin/bash
# System hardening script

# Disable root SSH login
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable password authentication
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Configure UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow 8090/tcp # Mindset UI
ufw enable

# Install and configure Fail2Ban
apt install -y fail2ban
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[mindset]
enabled = true
port = 8090
filter = mindset
logpath = /var/log/mindset/access.log
maxretry = 5
EOF

systemctl restart fail2ban

# Install CrowdSec
curl -s https://packagecloud.io/install/repositories/crowdsec/crowdsec/script.deb.sh | bash
apt install -y crowdsec crowdsec-firewall-bouncer-iptables

# Configure automatic security updates
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

### 5.2 PHP Hardening

```ini
; /etc/php/8.3/fpm/conf.d/99-security.ini

; Disable dangerous functions
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,curl_exec,curl_multi_exec,parse_ini_file,show_source

; Hide PHP version
expose_php = Off

; Limit resources
max_execution_time = 30
max_input_time = 60
memory_limit = 256M
post_max_size = 64M
upload_max_filesize = 32M

; Session security
session.cookie_httponly = 1
session.cookie_secure = 1
session.use_strict_mode = 1
session.cookie_samesite = Strict

; Error handling (production)
display_errors = Off
log_errors = On
error_log = /var/log/php/error.log
```

### 5.3 Database Hardening

```sql
-- MySQL hardening

-- Remove anonymous users
DELETE FROM mysql.user WHERE User='';

-- Remove test database
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';

-- Require secure connections
ALTER USER 'root'@'localhost' REQUIRE SSL;

-- Create application user with limited privileges
CREATE USER 'mindset'@'localhost' IDENTIFIED BY 'secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON mindset.* TO 'mindset'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;
```

---

## 6. Incident Response

### 6.1 Response Procedures

```python
# mindset/security/incident.py

from enum import Enum
from datetime import datetime
from typing import Optional

class IncidentSeverity(Enum):
    CRITICAL = 1  # Active breach, data loss
    HIGH = 2      # Attempted breach, service impact
    MEDIUM = 3    # Suspicious activity
    LOW = 4       # Policy violation, anomaly

class IncidentResponse:
    def __init__(self, notification_service):
        self.notifications = notification_service

    async def handle_incident(
        self,
        severity: IncidentSeverity,
        incident_type: str,
        details: dict,
        source_ip: Optional[str] = None
    ):
        """Handle security incident"""
        incident = {
            'id': generate_incident_id(),
            'timestamp': datetime.utcnow().isoformat(),
            'severity': severity.name,
            'type': incident_type,
            'details': details,
            'source_ip': source_ip
        }

        # Log incident
        await self.log_incident(incident)

        # Take automatic action based on severity
        if severity == IncidentSeverity.CRITICAL:
            await self.critical_response(incident)
        elif severity == IncidentSeverity.HIGH:
            await self.high_response(incident)
        elif severity == IncidentSeverity.MEDIUM:
            await self.medium_response(incident)

        # Notify administrators
        await self.notifications.send_alert(
            level=severity.name.lower(),
            title=f"Security Incident: {incident_type}",
            details=incident
        )

    async def critical_response(self, incident: dict):
        """Automatic response to critical incidents"""
        # Block source IP immediately
        if incident.get('source_ip'):
            await self.block_ip(incident['source_ip'])

        # Invalidate all sessions
        await self.invalidate_all_sessions()

        # Enable lockdown mode
        await self.enable_lockdown()

        # Create forensic snapshot
        await self.create_forensic_backup()

    async def high_response(self, incident: dict):
        """Automatic response to high severity incidents"""
        # Block source IP
        if incident.get('source_ip'):
            await self.block_ip(incident['source_ip'])

        # Increase logging verbosity
        await self.increase_logging()

    async def medium_response(self, incident: dict):
        """Automatic response to medium severity incidents"""
        # Add to watchlist
        if incident.get('source_ip'):
            await self.add_to_watchlist(incident['source_ip'])
```

---

## 7. Compliance Considerations

### 7.1 Security Standards Alignment

| Standard | Relevant Controls |
|----------|------------------|
| OWASP Top 10 | Input validation, XSS protection, injection prevention |
| CIS Benchmarks | System hardening, access control |
| SOC 2 | Audit logging, access management |
| GDPR | Data encryption, access controls |
| PCI DSS | Network segmentation, encryption |

### 7.2 Security Documentation

- Security policy document
- Incident response plan
- Access control matrix
- Data classification guide
- Security training materials

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
*Review Frequency: Quarterly*
