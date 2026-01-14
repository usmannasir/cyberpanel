# Laravel 12 Golden Path - Mindset Platform

## Overview

The Laravel Golden Path provides a zero-friction, opinionated workflow for deploying and managing Laravel 12 applications on Mindset. This document outlines the complete lifecycle from creation to production operation.

---

## 1. Laravel Application Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LARAVEL APPLICATION LIFECYCLE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   CREATE    CONFIGURE    CONNECT    DEPLOY    MONITOR    SCALE    BACKUP   │
│      │          │           │          │          │         │         │     │
│      ▼          ▼           ▼          ▼          ▼         ▼         ▼     │
│   ┌────┐    ┌──────┐    ┌──────┐   ┌──────┐   ┌──────┐  ┌──────┐  ┌─────┐  │
│   │New │    │ .env │    │ Git  │   │ Zero │   │Logs  │  │Queue │  │Auto │  │
│   │App │    │ PHP  │    │ Repo │   │ Down │   │Metrics│ │Workers│ │Daily│  │
│   │    │    │ Cron │    │      │   │ time │   │Alerts│  │Scale │  │     │  │
│   └────┘    └──────┘    └──────┘   └──────┘   └──────┘  └──────┘  └─────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Quick Start: Create Laravel App

### 2.1 One-Click Creation

```python
# mindset/laravel/installer.py

from pathlib import Path
import subprocess
from typing import Optional

class LaravelInstaller:
    """Laravel application installer"""

    LARAVEL_VERSION = "12.*"
    DEFAULT_PHP_VERSION = "8.3"

    def __init__(self, site_manager, database_manager):
        self.site_manager = site_manager
        self.db_manager = database_manager

    async def create_laravel_app(
        self,
        domain: str,
        owner_id: int,
        php_version: str = None,
        database_type: str = "mysql",
        install_breeze: bool = False,
        install_horizon: bool = False,
        install_octane: bool = False
    ) -> dict:
        """Create a new Laravel application"""

        php_version = php_version or self.DEFAULT_PHP_VERSION

        # 1. Create site with proper structure
        site = await self.site_manager.create_site(
            domain=domain,
            owner_id=owner_id,
            php_version=php_version,
            site_type="laravel"
        )

        site_path = Path(f"/home/{site.user}/{domain}")

        # 2. Create Laravel directory structure
        await self._create_laravel_structure(site_path)

        # 3. Install Laravel
        await self._install_laravel(site_path, php_version)

        # 4. Create database
        db_name = self._generate_db_name(domain)
        db_user = db_name
        db_password = self._generate_password()

        await self.db_manager.create_database(
            name=db_name,
            user=db_user,
            password=db_password,
            owner_id=owner_id
        )

        # 5. Configure .env
        await self._configure_env(
            site_path=site_path,
            domain=domain,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password
        )

        # 6. Optional packages
        if install_breeze:
            await self._install_breeze(site_path)

        if install_horizon:
            await self._install_horizon(site_path, site)

        if install_octane:
            await self._install_octane(site_path, site)

        # 7. Set permissions
        await self._set_permissions(site_path, site.user)

        # 8. Configure web server
        await self._configure_webserver(site, site_path)

        # 9. Run initial migrations
        await self._run_migrations(site_path)

        # 10. Generate application key
        await self._generate_app_key(site_path)

        return {
            "site_id": site.id,
            "domain": domain,
            "database": db_name,
            "path": str(site_path),
            "url": f"https://{domain}"
        }

    async def _create_laravel_structure(self, site_path: Path):
        """Create Laravel-optimized directory structure"""
        directories = [
            site_path / "current",
            site_path / "releases",
            site_path / "shared" / "storage" / "app" / "public",
            site_path / "shared" / "storage" / "framework" / "cache",
            site_path / "shared" / "storage" / "framework" / "sessions",
            site_path / "shared" / "storage" / "framework" / "views",
            site_path / "shared" / "storage" / "logs",
            site_path / ".mindset" / "hooks",
            site_path / ".mindset" / "logs",
            site_path / "logs",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    async def _install_laravel(self, site_path: Path, php_version: str):
        """Install Laravel via Composer"""
        release_path = site_path / "releases" / "initial"
        release_path.mkdir(parents=True, exist_ok=True)

        cmd = [
            f"/usr/local/lsws/lsphp{php_version.replace('.', '')}/bin/php",
            "/usr/bin/composer",
            "create-project",
            "--prefer-dist",
            f"laravel/laravel:{self.LARAVEL_VERSION}",
            str(release_path)
        ]

        subprocess.run(cmd, check=True)

        # Create symlink to current release
        current = site_path / "current"
        if current.is_symlink():
            current.unlink()
        current.symlink_to(release_path)

    async def _configure_env(
        self,
        site_path: Path,
        domain: str,
        db_name: str,
        db_user: str,
        db_password: str
    ):
        """Configure Laravel .env file"""
        env_content = f"""APP_NAME="{domain}"
APP_ENV=production
APP_KEY=
APP_DEBUG=false
APP_TIMEZONE=UTC
APP_URL=https://{domain}

APP_LOCALE=en
APP_FALLBACK_LOCALE=en
APP_FAKER_LOCALE=en_US

APP_MAINTENANCE_DRIVER=file

BCRYPT_ROUNDS=12

LOG_CHANNEL=stack
LOG_STACK=single
LOG_DEPRECATIONS_CHANNEL=null
LOG_LEVEL=error

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE={db_name}
DB_USERNAME={db_user}
DB_PASSWORD={db_password}

SESSION_DRIVER=redis
SESSION_LIFETIME=120
SESSION_ENCRYPT=true

BROADCAST_CONNECTION=log
FILESYSTEM_DISK=local
QUEUE_CONNECTION=redis

CACHE_STORE=redis
CACHE_PREFIX=

REDIS_CLIENT=phpredis
REDIS_HOST=127.0.0.1
REDIS_PASSWORD=null
REDIS_PORT=6379

MAIL_MAILER=smtp
MAIL_HOST=127.0.0.1
MAIL_PORT=25
MAIL_USERNAME=null
MAIL_PASSWORD=null
MAIL_ENCRYPTION=null
MAIL_FROM_ADDRESS="noreply@{domain}"
MAIL_FROM_NAME="${{APP_NAME}}"
"""

        env_path = site_path / "shared" / ".env"
        env_path.write_text(env_content)

        # Symlink to current release
        current_env = site_path / "current" / ".env"
        if not current_env.exists():
            current_env.symlink_to(env_path)

    async def _install_horizon(self, site_path: Path, site):
        """Install Laravel Horizon for queue management"""
        release_path = site_path / "current"

        # Install Horizon
        subprocess.run([
            "composer", "require", "laravel/horizon"
        ], cwd=release_path, check=True)

        # Publish assets
        subprocess.run([
            "php", "artisan", "horizon:install"
        ], cwd=release_path, check=True)

        # Create supervisor config for Horizon
        await self._create_horizon_supervisor(site, release_path)

    async def _install_octane(self, site_path: Path, site):
        """Install Laravel Octane for high-performance serving"""
        release_path = site_path / "current"

        # Install Octane with RoadRunner
        subprocess.run([
            "composer", "require", "laravel/octane"
        ], cwd=release_path, check=True)

        subprocess.run([
            "php", "artisan", "octane:install", "--server=roadrunner"
        ], cwd=release_path, check=True)

        # Configure OLS to proxy to Octane
        await self._configure_octane_proxy(site, release_path)

    async def _set_permissions(self, site_path: Path, user: str):
        """Set correct permissions for Laravel"""
        import os
        import pwd
        import grp

        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(user).gr_gid

        # Recursive chown
        for root, dirs, files in os.walk(site_path):
            os.chown(root, uid, gid)
            for d in dirs:
                os.chown(os.path.join(root, d), uid, gid)
            for f in files:
                os.chown(os.path.join(root, f), uid, gid)

        # Writable directories
        writable = [
            site_path / "shared" / "storage",
            site_path / "current" / "bootstrap" / "cache",
        ]

        for directory in writable:
            os.chmod(directory, 0o775)

    async def _configure_webserver(self, site, site_path: Path):
        """Configure OpenLiteSpeed for Laravel"""
        vhost_config = f"""
docRoot                   {site_path}/current/public
enableGzip                1

index  {{
  useServer               0
  indexFiles              index.php
}}

rewrite  {{
  enable                  1
  autoLoadHtaccess        1
  rules                   <<<END_rules
RewriteEngine On
RewriteCond %{{REQUEST_FILENAME}} !-d
RewriteCond %{{REQUEST_FILENAME}} !-f
RewriteRule ^ index.php [L]
END_rules
}}

context / {{
  location                {site_path}/current/public
  allowBrowse             1
  rewrite  {{
    enable                1
    inherit               1
  }}
}}

context /storage {{
  location                {site_path}/shared/storage/app/public
  allowBrowse             1
  enableExpires           1
  expiresDefault          "access plus 1 year"
}}
"""
        # Write vhost configuration
        vhost_path = Path(f"/usr/local/lsws/conf/vhosts/{site.domain}")
        vhost_path.mkdir(parents=True, exist_ok=True)
        (vhost_path / "vhconf.conf").write_text(vhost_config)
```

### 2.2 CLI Usage

```bash
# Create new Laravel app
mindset laravel:create example.com

# Create with options
mindset laravel:create example.com \
    --php=8.3 \
    --with-horizon \
    --with-octane \
    --with-breeze

# Deploy from Git
mindset laravel:deploy example.com \
    --repo=git@github.com:user/repo.git \
    --branch=main
```

---

## 3. Environment Management

### 3.1 Secure .env Editor

```python
# mindset/laravel/env_manager.py

from pathlib import Path
from typing import Dict, Optional
import re
from cryptography.fernet import Fernet

class EnvManager:
    """Secure Laravel environment management"""

    SENSITIVE_KEYS = [
        'APP_KEY', 'DB_PASSWORD', 'REDIS_PASSWORD',
        'MAIL_PASSWORD', 'AWS_SECRET', 'PUSHER_SECRET',
        'STRIPE_SECRET', 'API_KEY', 'SECRET'
    ]

    VALIDATION_RULES = {
        'APP_ENV': ['local', 'staging', 'production'],
        'APP_DEBUG': ['true', 'false'],
        'LOG_LEVEL': ['debug', 'info', 'notice', 'warning', 'error', 'critical'],
        'DB_CONNECTION': ['mysql', 'pgsql', 'sqlite', 'sqlsrv'],
        'CACHE_STORE': ['file', 'redis', 'memcached', 'database', 'array'],
        'SESSION_DRIVER': ['file', 'cookie', 'database', 'redis', 'memcached', 'array'],
        'QUEUE_CONNECTION': ['sync', 'database', 'redis', 'beanstalkd', 'sqs'],
    }

    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)

    def read_env(self, env_path: Path) -> Dict[str, str]:
        """Read and parse .env file"""
        if not env_path.exists():
            return {}

        env_vars = {}
        content = env_path.read_text()

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip('"\'')
                env_vars[key] = value

        return env_vars

    def write_env(self, env_path: Path, env_vars: Dict[str, str]):
        """Write .env file with proper formatting"""
        lines = []

        # Group by category
        categories = {
            'APP': [],
            'DB': [],
            'CACHE': [],
            'SESSION': [],
            'QUEUE': [],
            'REDIS': [],
            'MAIL': [],
            'AWS': [],
            'OTHER': []
        }

        for key, value in env_vars.items():
            # Determine category
            category = 'OTHER'
            for cat in categories.keys():
                if key.startswith(cat):
                    category = cat
                    break

            # Quote value if needed
            if ' ' in str(value) or '"' in str(value):
                value = f'"{value}"'

            categories[category].append(f"{key}={value}")

        # Build output
        for category, vars in categories.items():
            if vars:
                lines.append(f"# {category} Configuration")
                lines.extend(sorted(vars))
                lines.append("")

        env_path.write_text('\n'.join(lines))

    def validate_env(self, env_vars: Dict[str, str]) -> Dict[str, list]:
        """Validate environment variables"""
        errors = {}
        warnings = {}

        # Check required variables
        required = ['APP_KEY', 'APP_URL', 'DB_DATABASE']
        for key in required:
            if key not in env_vars or not env_vars[key]:
                errors.setdefault(key, []).append(f"{key} is required")

        # Validate allowed values
        for key, allowed in self.VALIDATION_RULES.items():
            if key in env_vars and env_vars[key] not in allowed:
                errors.setdefault(key, []).append(
                    f"Invalid value '{env_vars[key]}'. Allowed: {allowed}"
                )

        # Production warnings
        if env_vars.get('APP_ENV') == 'production':
            if env_vars.get('APP_DEBUG') == 'true':
                warnings.setdefault('APP_DEBUG', []).append(
                    "APP_DEBUG should be false in production"
                )
            if env_vars.get('LOG_LEVEL') == 'debug':
                warnings.setdefault('LOG_LEVEL', []).append(
                    "LOG_LEVEL=debug may impact performance in production"
                )

        return {'errors': errors, 'warnings': warnings}

    def encrypt_env(self, env_path: Path, output_path: Path):
        """Encrypt .env file at rest"""
        content = env_path.read_bytes()
        encrypted = self.cipher.encrypt(content)
        output_path.write_bytes(encrypted)

    def decrypt_env(self, encrypted_path: Path, output_path: Path):
        """Decrypt .env file"""
        encrypted = encrypted_path.read_bytes()
        decrypted = self.cipher.decrypt(encrypted)
        output_path.write_bytes(decrypted)

    def mask_sensitive(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive values for display"""
        masked = {}
        for key, value in env_vars.items():
            is_sensitive = any(
                s in key.upper() for s in self.SENSITIVE_KEYS
            )
            if is_sensitive and value:
                masked[key] = '*' * len(value)
            else:
                masked[key] = value
        return masked
```

### 3.2 Environment API

```python
# mindset/laravel/api/env.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

router = APIRouter(prefix="/api/v1/sites/{site_id}/env", tags=["Environment"])

class EnvUpdateRequest(BaseModel):
    variables: Dict[str, str]
    validate: bool = True

@router.get("/")
async def get_env(site_id: int, show_sensitive: bool = False):
    """Get environment variables (masked by default)"""
    site = await get_site(site_id)
    env_manager = EnvManager(get_encryption_key())

    env_path = Path(site.path) / "shared" / ".env"
    env_vars = env_manager.read_env(env_path)

    if not show_sensitive:
        env_vars = env_manager.mask_sensitive(env_vars)

    return {"variables": env_vars}

@router.put("/")
async def update_env(site_id: int, request: EnvUpdateRequest):
    """Update environment variables"""
    site = await get_site(site_id)
    env_manager = EnvManager(get_encryption_key())

    env_path = Path(site.path) / "shared" / ".env"

    # Read existing
    env_vars = env_manager.read_env(env_path)

    # Update with new values
    env_vars.update(request.variables)

    # Validate if requested
    if request.validate:
        validation = env_manager.validate_env(env_vars)
        if validation['errors']:
            raise HTTPException(400, detail=validation)

    # Write updated env
    env_manager.write_env(env_path, env_vars)

    # Clear config cache
    await run_artisan(site, "config:clear")

    return {"success": True, "validation": validation if request.validate else None}

@router.post("/validate")
async def validate_env(site_id: int):
    """Validate current environment configuration"""
    site = await get_site(site_id)
    env_manager = EnvManager(get_encryption_key())

    env_path = Path(site.path) / "shared" / ".env"
    env_vars = env_manager.read_env(env_path)

    return env_manager.validate_env(env_vars)
```

---

## 4. Zero-Downtime Deployments

### 4.1 Deployment Engine

```python
# mindset/laravel/deployer.py

from pathlib import Path
from datetime import datetime
from typing import Optional, List
import subprocess
import asyncio

class LaravelDeployer:
    """Zero-downtime deployment engine for Laravel"""

    def __init__(self, site, config: dict):
        self.site = site
        self.config = config
        self.site_path = Path(site.path)
        self.releases_path = self.site_path / "releases"
        self.shared_path = self.site_path / "shared"
        self.current_path = self.site_path / "current"

    async def deploy(
        self,
        source: str,  # Git URL or path
        branch: str = "main",
        run_migrations: bool = True,
        run_npm_build: bool = True
    ) -> dict:
        """Execute zero-downtime deployment"""

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        release_path = self.releases_path / timestamp

        deployment_log = []

        try:
            # 1. Clone/Copy to new release
            deployment_log.append(await self._clone_release(source, branch, release_path))

            # 2. Link shared resources
            deployment_log.append(await self._link_shared(release_path))

            # 3. Install Composer dependencies
            deployment_log.append(await self._composer_install(release_path))

            # 4. Install NPM dependencies and build
            if run_npm_build:
                deployment_log.append(await self._npm_build(release_path))

            # 5. Run database migrations
            if run_migrations:
                deployment_log.append(await self._run_migrations(release_path))

            # 6. Optimize Laravel
            deployment_log.append(await self._optimize_laravel(release_path))

            # 7. Health check
            deployment_log.append(await self._health_check(release_path))

            # 8. Activate release (atomic symlink swap)
            deployment_log.append(await self._activate_release(release_path))

            # 9. Reload PHP-FPM
            deployment_log.append(await self._reload_php_fpm())

            # 10. Cleanup old releases
            deployment_log.append(await self._cleanup_releases())

            # 11. Restart queue workers
            deployment_log.append(await self._restart_workers())

            return {
                "success": True,
                "release": timestamp,
                "log": deployment_log
            }

        except Exception as e:
            # Rollback on failure
            await self._rollback_release(release_path)
            return {
                "success": False,
                "error": str(e),
                "log": deployment_log
            }

    async def _clone_release(self, source: str, branch: str, release_path: Path) -> dict:
        """Clone repository to release directory"""
        release_path.mkdir(parents=True, exist_ok=True)

        cmd = [
            "git", "clone",
            "--depth=1",
            f"--branch={branch}",
            source,
            str(release_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        return {
            "step": "clone",
            "success": result.returncode == 0,
            "output": result.stdout or result.stderr
        }

    async def _link_shared(self, release_path: Path) -> dict:
        """Link shared directories and files"""
        shared_links = {
            # Directories
            "storage/app": self.shared_path / "storage" / "app",
            "storage/framework/cache": self.shared_path / "storage" / "framework" / "cache",
            "storage/framework/sessions": self.shared_path / "storage" / "framework" / "sessions",
            "storage/framework/views": self.shared_path / "storage" / "framework" / "views",
            "storage/logs": self.shared_path / "storage" / "logs",
            # Files
            ".env": self.shared_path / ".env",
        }

        for target, source in shared_links.items():
            target_path = release_path / target

            # Remove existing
            if target_path.exists() or target_path.is_symlink():
                if target_path.is_dir():
                    import shutil
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()

            # Create parent directory
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Create symlink
            target_path.symlink_to(source)

        return {"step": "link_shared", "success": True}

    async def _composer_install(self, release_path: Path) -> dict:
        """Install Composer dependencies"""
        cmd = [
            "composer", "install",
            "--no-dev",
            "--optimize-autoloader",
            "--no-interaction"
        ]

        result = subprocess.run(
            cmd, cwd=release_path,
            capture_output=True, text=True
        )

        return {
            "step": "composer_install",
            "success": result.returncode == 0,
            "output": result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
        }

    async def _npm_build(self, release_path: Path) -> dict:
        """Install NPM dependencies and build assets"""
        # Check if package.json exists
        if not (release_path / "package.json").exists():
            return {"step": "npm_build", "success": True, "output": "Skipped (no package.json)"}

        # Install dependencies
        install_result = subprocess.run(
            ["npm", "ci"],
            cwd=release_path,
            capture_output=True, text=True
        )

        if install_result.returncode != 0:
            return {
                "step": "npm_build",
                "success": False,
                "output": install_result.stderr
            }

        # Build assets
        build_result = subprocess.run(
            ["npm", "run", "build"],
            cwd=release_path,
            capture_output=True, text=True
        )

        return {
            "step": "npm_build",
            "success": build_result.returncode == 0,
            "output": build_result.stdout[-2000:] if build_result.stdout else build_result.stderr[-2000:]
        }

    async def _run_migrations(self, release_path: Path) -> dict:
        """Run database migrations"""
        result = subprocess.run(
            ["php", "artisan", "migrate", "--force"],
            cwd=release_path,
            capture_output=True, text=True
        )

        return {
            "step": "migrations",
            "success": result.returncode == 0,
            "output": result.stdout or result.stderr
        }

    async def _optimize_laravel(self, release_path: Path) -> dict:
        """Run Laravel optimization commands"""
        commands = [
            ["php", "artisan", "config:cache"],
            ["php", "artisan", "route:cache"],
            ["php", "artisan", "view:cache"],
            ["php", "artisan", "event:cache"],
        ]

        outputs = []
        for cmd in commands:
            result = subprocess.run(
                cmd, cwd=release_path,
                capture_output=True, text=True
            )
            outputs.append(f"{' '.join(cmd)}: {'OK' if result.returncode == 0 else 'FAILED'}")

        return {
            "step": "optimize",
            "success": True,
            "output": '\n'.join(outputs)
        }

    async def _health_check(self, release_path: Path) -> dict:
        """Run health check before activating release"""
        # Check 1: PHP syntax check on critical files
        critical_files = [
            "bootstrap/app.php",
            "config/app.php",
            "routes/web.php",
        ]

        for file in critical_files:
            file_path = release_path / file
            if file_path.exists():
                result = subprocess.run(
                    ["php", "-l", str(file_path)],
                    capture_output=True
                )
                if result.returncode != 0:
                    raise Exception(f"Syntax error in {file}")

        # Check 2: Test artisan command works
        result = subprocess.run(
            ["php", "artisan", "about"],
            cwd=release_path,
            capture_output=True
        )

        if result.returncode != 0:
            raise Exception("Artisan health check failed")

        # Check 3: Custom health check script if exists
        health_script = self.site_path / ".mindset" / "hooks" / "health-check.sh"
        if health_script.exists():
            result = subprocess.run(
                ["bash", str(health_script)],
                cwd=release_path,
                capture_output=True
            )
            if result.returncode != 0:
                raise Exception("Custom health check failed")

        return {"step": "health_check", "success": True}

    async def _activate_release(self, release_path: Path) -> dict:
        """Atomically switch to new release"""
        import os

        # Create temporary symlink
        temp_link = self.site_path / f"current_tmp_{datetime.utcnow().timestamp()}"
        temp_link.symlink_to(release_path)

        # Atomic rename (this is the zero-downtime moment)
        os.rename(str(temp_link), str(self.current_path))

        return {
            "step": "activate",
            "success": True,
            "output": f"Activated release: {release_path.name}"
        }

    async def _reload_php_fpm(self) -> dict:
        """Reload PHP-FPM to clear opcode cache"""
        result = subprocess.run(
            ["systemctl", "reload", f"lsphp{self.config['php_version'].replace('.', '')}"],
            capture_output=True
        )

        return {
            "step": "reload_php",
            "success": result.returncode == 0
        }

    async def _cleanup_releases(self, keep: int = 5) -> dict:
        """Remove old releases"""
        releases = sorted(self.releases_path.iterdir(), reverse=True)

        removed = []
        for release in releases[keep:]:
            if release.is_dir():
                import shutil
                shutil.rmtree(release)
                removed.append(release.name)

        return {
            "step": "cleanup",
            "success": True,
            "output": f"Removed {len(removed)} old releases"
        }

    async def _restart_workers(self) -> dict:
        """Restart queue workers gracefully"""
        result = subprocess.run(
            ["php", "artisan", "queue:restart"],
            cwd=self.current_path,
            capture_output=True
        )

        return {
            "step": "restart_workers",
            "success": result.returncode == 0
        }

    async def _rollback_release(self, failed_release: Path):
        """Rollback on deployment failure"""
        import shutil

        # Remove failed release
        if failed_release.exists():
            shutil.rmtree(failed_release)

        # current symlink should still point to previous release

    async def rollback(self, releases_back: int = 1) -> dict:
        """Rollback to previous release"""
        releases = sorted(self.releases_path.iterdir(), reverse=True)

        if len(releases) <= releases_back:
            raise Exception("Not enough releases to rollback")

        target_release = releases[releases_back]

        await self._activate_release(target_release)
        await self._reload_php_fpm()
        await self._restart_workers()

        return {
            "success": True,
            "rolled_back_to": target_release.name
        }
```

---

## 5. Queue Worker Management

### 5.1 Horizon Integration

```python
# mindset/laravel/horizon.py

from pathlib import Path
import subprocess
from typing import Optional

class HorizonManager:
    """Laravel Horizon queue management"""

    def __init__(self, site):
        self.site = site
        self.site_path = Path(site.path) / "current"
        self.supervisor_conf = f"/etc/supervisor/conf.d/horizon-{site.domain.replace('.', '-')}.conf"

    async def install(self):
        """Install and configure Horizon"""
        # Install Horizon package
        subprocess.run(
            ["composer", "require", "laravel/horizon"],
            cwd=self.site_path,
            check=True
        )

        # Publish configuration
        subprocess.run(
            ["php", "artisan", "horizon:install"],
            cwd=self.site_path,
            check=True
        )

        # Create supervisor configuration
        await self._create_supervisor_config()

        # Reload supervisor
        subprocess.run(["supervisorctl", "reread"])
        subprocess.run(["supervisorctl", "update"])

    async def _create_supervisor_config(self):
        """Create supervisor configuration for Horizon"""
        config = f"""[program:horizon-{self.site.domain.replace('.', '-')}]
process_name=%(program_name)s
command=php {self.site_path}/artisan horizon
autostart=true
autorestart=true
user={self.site.user}
redirect_stderr=true
stdout_logfile={self.site_path.parent}/logs/horizon.log
stopwaitsecs=3600
"""
        Path(self.supervisor_conf).write_text(config)

    async def status(self) -> dict:
        """Get Horizon status"""
        result = subprocess.run(
            ["php", "artisan", "horizon:status"],
            cwd=self.site_path,
            capture_output=True,
            text=True
        )

        return {
            "running": "running" in result.stdout.lower(),
            "output": result.stdout
        }

    async def pause(self):
        """Pause Horizon processing"""
        subprocess.run(
            ["php", "artisan", "horizon:pause"],
            cwd=self.site_path,
            check=True
        )

    async def resume(self):
        """Resume Horizon processing"""
        subprocess.run(
            ["php", "artisan", "horizon:continue"],
            cwd=self.site_path,
            check=True
        )

    async def terminate(self):
        """Terminate Horizon gracefully"""
        subprocess.run(
            ["php", "artisan", "horizon:terminate"],
            cwd=self.site_path,
            check=True
        )

    async def get_metrics(self) -> dict:
        """Get Horizon metrics"""
        result = subprocess.run(
            ["php", "artisan", "horizon:snapshot"],
            cwd=self.site_path,
            capture_output=True,
            text=True
        )

        # Parse metrics from database
        # This is simplified - actual implementation would query the database
        return {
            "jobs_per_minute": 0,
            "failed_jobs": 0,
            "pending_jobs": 0,
            "processes": 0
        }
```

### 5.2 Scheduler Management

```python
# mindset/laravel/scheduler.py

from pathlib import Path
import subprocess
from typing import List, Dict
import re

class SchedulerManager:
    """Laravel scheduler management"""

    def __init__(self, site):
        self.site = site
        self.site_path = Path(site.path) / "current"
        self.cron_file = f"/etc/cron.d/laravel-{site.domain.replace('.', '-')}"

    async def enable(self):
        """Enable Laravel scheduler via cron"""
        cron_entry = f"* * * * * {self.site.user} cd {self.site_path} && php artisan schedule:run >> /dev/null 2>&1\n"
        Path(self.cron_file).write_text(cron_entry)

    async def disable(self):
        """Disable Laravel scheduler"""
        cron_path = Path(self.cron_file)
        if cron_path.exists():
            cron_path.unlink()

    async def list_tasks(self) -> List[Dict]:
        """List scheduled tasks"""
        result = subprocess.run(
            ["php", "artisan", "schedule:list"],
            cwd=self.site_path,
            capture_output=True,
            text=True
        )

        tasks = []
        for line in result.stdout.splitlines():
            # Parse schedule:list output
            match = re.match(r'\s*(\S+)\s+(.+)', line)
            if match:
                tasks.append({
                    "expression": match.group(1),
                    "command": match.group(2)
                })

        return tasks

    async def run_task(self, task_name: str) -> dict:
        """Run a specific scheduled task"""
        result = subprocess.run(
            ["php", "artisan", task_name],
            cwd=self.site_path,
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout or result.stderr
        }

    async def test(self) -> dict:
        """Test scheduler configuration"""
        result = subprocess.run(
            ["php", "artisan", "schedule:test"],
            cwd=self.site_path,
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout
        }
```

---

## 6. Artisan Command Interface

### 6.1 Artisan Runner

```python
# mindset/laravel/artisan.py

from pathlib import Path
import subprocess
from typing import List, Optional
import asyncio

class ArtisanRunner:
    """Laravel Artisan command interface"""

    # Whitelisted commands that can be run from UI
    ALLOWED_COMMANDS = [
        # Cache
        "cache:clear", "cache:forget", "config:cache", "config:clear",
        "route:cache", "route:clear", "view:cache", "view:clear",
        "event:cache", "event:clear", "optimize", "optimize:clear",

        # Database
        "migrate", "migrate:status", "migrate:rollback",
        "db:seed", "db:wipe",

        # Queue
        "queue:clear", "queue:failed", "queue:flush",
        "queue:restart", "queue:retry", "queue:work",
        "horizon:status", "horizon:pause", "horizon:continue",

        # Maintenance
        "down", "up", "about", "env",

        # Storage
        "storage:link",

        # Keys
        "key:generate",

        # Scheduler
        "schedule:list", "schedule:run", "schedule:test",

        # Tinker (with restrictions)
        "tinker",
    ]

    # Commands that require confirmation
    DANGEROUS_COMMANDS = [
        "migrate", "migrate:rollback", "db:wipe",
        "down", "key:generate"
    ]

    def __init__(self, site):
        self.site = site
        self.site_path = Path(site.path) / "current"

    async def run(
        self,
        command: str,
        arguments: List[str] = None,
        force: bool = False,
        timeout: int = 60
    ) -> dict:
        """Run artisan command"""
        arguments = arguments or []

        # Validate command
        base_command = command.split(':')[0] if ':' in command else command
        full_command = f"{command}"

        if not self._is_allowed(full_command):
            raise PermissionError(f"Command not allowed: {command}")

        # Build command
        cmd = ["php", "artisan", command] + arguments

        if force and command in self.DANGEROUS_COMMANDS:
            cmd.append("--force")

        # Run command
        try:
            result = subprocess.run(
                cmd,
                cwd=self.site_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                user=self.site.user
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "exit_code": -1
            }

    def _is_allowed(self, command: str) -> bool:
        """Check if command is in whitelist"""
        for allowed in self.ALLOWED_COMMANDS:
            if command == allowed or command.startswith(f"{allowed}:"):
                return True
        return False

    async def list_commands(self) -> List[dict]:
        """List available artisan commands"""
        result = await self.run("list", ["--format=json"])

        if result["success"]:
            import json
            data = json.loads(result["output"])
            return [
                {
                    "name": cmd["name"],
                    "description": cmd.get("description", ""),
                    "allowed": self._is_allowed(cmd["name"]),
                    "dangerous": cmd["name"] in self.DANGEROUS_COMMANDS
                }
                for cmd in data.get("commands", [])
            ]
        return []

    async def tinker(self, code: str) -> dict:
        """Run code in Tinker (sandboxed)"""
        # Security: sanitize and limit code execution
        forbidden_patterns = [
            "exec(", "system(", "shell_exec(", "passthru(",
            "file_put_contents(", "unlink(", "rmdir(",
            "eval(", "`"
        ]

        for pattern in forbidden_patterns:
            if pattern in code:
                raise PermissionError(f"Forbidden operation: {pattern}")

        # Run with timeout
        result = subprocess.run(
            ["php", "artisan", "tinker", f"--execute={code}"],
            cwd=self.site_path,
            capture_output=True,
            text=True,
            timeout=30,
            user=self.site.user
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
```

---

## 7. Laravel Logs Viewer

```python
# mindset/laravel/logs.py

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re

class LaravelLogViewer:
    """Laravel log file viewer and analyzer"""

    LOG_PATTERN = re.compile(
        r'\[(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*[+\-\d:]*)\]\s*'
        r'(?P<env>\w+)\.(?P<level>\w+):\s*'
        r'(?P<message>.*?)(?=\[\d{4}-\d{2}-\d{2}|\Z)',
        re.DOTALL
    )

    def __init__(self, site):
        self.site = site
        self.log_path = Path(site.path) / "shared" / "storage" / "logs"

    async def list_log_files(self) -> List[dict]:
        """List available log files"""
        files = []
        for log_file in self.log_path.glob("*.log"):
            stat = log_file.stat()
            files.append({
                "name": log_file.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(log_file)
            })
        return sorted(files, key=lambda x: x["modified"], reverse=True)

    async def read_log(
        self,
        filename: str = "laravel.log",
        lines: int = 100,
        level: Optional[str] = None
    ) -> List[dict]:
        """Read and parse log entries"""
        log_file = self.log_path / filename

        if not log_file.exists():
            return []

        content = log_file.read_text()
        entries = []

        for match in self.LOG_PATTERN.finditer(content):
            entry = {
                "timestamp": match.group("timestamp"),
                "environment": match.group("env"),
                "level": match.group("level"),
                "message": match.group("message").strip()
            }

            # Filter by level if specified
            if level and entry["level"].lower() != level.lower():
                continue

            entries.append(entry)

        # Return most recent entries
        return entries[-lines:]

    async def search_logs(
        self,
        query: str,
        filename: str = "laravel.log"
    ) -> List[dict]:
        """Search logs for specific text"""
        entries = await self.read_log(filename, lines=10000)

        return [
            entry for entry in entries
            if query.lower() in entry["message"].lower()
        ]

    async def get_error_summary(
        self,
        filename: str = "laravel.log",
        hours: int = 24
    ) -> dict:
        """Get summary of errors in the last N hours"""
        entries = await self.read_log(filename, lines=10000)

        cutoff = datetime.utcnow().timestamp() - (hours * 3600)

        error_counts = {}
        recent_errors = []

        for entry in entries:
            try:
                entry_time = datetime.fromisoformat(
                    entry["timestamp"].replace(' ', 'T')
                ).timestamp()
            except:
                continue

            if entry_time < cutoff:
                continue

            level = entry["level"].upper()
            if level in ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]:
                error_counts[level] = error_counts.get(level, 0) + 1

                if len(recent_errors) < 10:
                    recent_errors.append(entry)

        return {
            "period_hours": hours,
            "counts": error_counts,
            "total_errors": sum(error_counts.values()),
            "recent_errors": recent_errors
        }

    async def clear_logs(self, filename: str = "laravel.log"):
        """Clear log file"""
        log_file = self.log_path / filename
        if log_file.exists():
            log_file.write_text("")

    async def download_logs(
        self,
        filename: str = "laravel.log"
    ) -> bytes:
        """Get log file contents for download"""
        log_file = self.log_path / filename
        return log_file.read_bytes() if log_file.exists() else b""
```

---

## 8. API Endpoints

```python
# mindset/laravel/api/__init__.py

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/sites/{site_id}/laravel", tags=["Laravel"])

# Include sub-routers
from .env import router as env_router
from .deploy import router as deploy_router
from .artisan import router as artisan_router
from .logs import router as logs_router
from .workers import router as workers_router

router.include_router(env_router)
router.include_router(deploy_router)
router.include_router(artisan_router)
router.include_router(logs_router)
router.include_router(workers_router)
```

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
