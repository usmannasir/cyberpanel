# Refactoring Plan & Migration Guide

## Overview

This document provides a comprehensive plan for refactoring CyberPanel into Mindset and guides existing CyberPanel users through migration.

---

## Part 1: Refactoring Plan

### 1.1 Phased Approach

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REFACTORING ROADMAP                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1          PHASE 2          PHASE 3          PHASE 4          PHASE 5│
│  Branding         Laravel          AI               Enterprise       Polish │
│  (Week 1-2)       (Week 3-6)       (Week 7-10)      (Week 11-14)    (15-16) │
│                                                                              │
│  ┌─────────┐     ┌─────────┐      ┌─────────┐      ┌─────────┐     ┌─────┐ │
│  │Rename   │     │Laravel  │      │Provider │      │Backup   │     │UI   │ │
│  │Files    │     │Installer│      │Layer    │      │Overhaul │     │Theme│ │
│  │         │     │         │      │         │      │         │     │     │ │
│  │Config   │     │Deploy   │      │Ollama   │      │Vault    │     │Docs │ │
│  │Updates  │     │System   │      │DeepInfra│      │System   │     │     │ │
│  │         │     │         │      │         │      │         │     │Tests│ │
│  │Logo/UI  │     │Artisan  │      │Log      │      │Prometheus│    │     │ │
│  │         │     │Runner   │      │Analysis │      │Grafana  │     │     │ │
│  └─────────┘     └─────────┘      └─────────┘      └─────────┘     └─────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.2 Phase 1: Rebranding (Weeks 1-2)

#### Files to Rename/Update

| Current | New | Type |
|---------|-----|------|
| `CyberCP/` | `mindset/` | Directory |
| `cyberpanel.sh` | `mindset.sh` | Installer |
| `CyberCP/settings.py` | `mindset/settings.py` | Config |
| `CyberCP/wsgi.py` | `mindset/wsgi.py` | WSGI |
| `cli/cyberPanel.py` | `cli/mindset.py` | CLI |
| `version.txt` | `version.txt` | Version (update content) |

#### String Replacements

```python
# Branding strings to replace
REPLACEMENTS = {
    'CyberPanel': 'Mindset',
    'cyberpanel': 'mindset',
    'CYBERPANEL': 'MINDSET',
    'Cyber Panel': 'Mindset',
    'cyber panel': 'mindset',
    'cyber-panel': 'mindset',
    'cyberPanel': 'mindset',
}

# Files to update (glob patterns)
FILES_TO_UPDATE = [
    '**/*.py',
    '**/*.html',
    '**/*.js',
    '**/*.css',
    '**/*.json',
    '**/*.yaml',
    '**/*.yml',
    '**/*.md',
    '**/*.txt',
    '**/*.sh',
    '**/*.conf',
    '**/*.service',
]

# Files to exclude
EXCLUDE_PATTERNS = [
    'venv/**',
    '.git/**',
    'node_modules/**',
    '*.pyc',
    '__pycache__/**',
]
```

#### Branding Script

```python
#!/usr/bin/env python3
# scripts/rebrand.py - Automated rebranding script

import os
import re
from pathlib import Path
from typing import List, Tuple

class Rebrander:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.replacements = {
            'CyberPanel': 'Mindset',
            'cyberpanel': 'mindset',
            'CYBERPANEL': 'MINDSET',
            'Cyber Panel': 'Mindset',
            'CyberCP': 'Mindset',
            'cybercp': 'mindset',
        }

    def rebrand_file(self, file_path: Path) -> Tuple[int, List[str]]:
        """Rebrand a single file"""
        try:
            content = file_path.read_text()
            changes = []

            for old, new in self.replacements.items():
                if old in content:
                    count = content.count(old)
                    content = content.replace(old, new)
                    changes.append(f"{old} -> {new} ({count}x)")

            if changes:
                file_path.write_text(content)
                return len(changes), changes

            return 0, []
        except Exception as e:
            return -1, [str(e)]

    def rebrand_directory(self) -> dict:
        """Rebrand entire directory"""
        results = {'files_modified': 0, 'total_changes': 0, 'errors': []}

        extensions = {'.py', '.html', '.js', '.css', '.json', '.yaml', '.yml',
                     '.md', '.txt', '.sh', '.conf', '.service', '.xml'}

        for file_path in self.base_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                # Skip excluded paths
                if any(part in str(file_path) for part in ['venv', '.git', 'node_modules']):
                    continue

                count, changes = self.rebrand_file(file_path)
                if count > 0:
                    results['files_modified'] += 1
                    results['total_changes'] += count
                    print(f"Modified: {file_path}")
                    for change in changes:
                        print(f"  - {change}")
                elif count < 0:
                    results['errors'].append((str(file_path), changes[0]))

        return results

if __name__ == '__main__':
    rebrander = Rebrander('/home/user/cyberpanel')
    results = rebrander.rebrand_directory()
    print(f"\nSummary: Modified {results['files_modified']} files, "
          f"{results['total_changes']} total changes")
```

---

### 1.3 Phase 2: Laravel Features (Weeks 3-6)

#### New Modules to Create

```
mindset/
├── laravelManager/          # NEW - Laravel management module
│   ├── __init__.py
│   ├── models.py           # LaravelSite, Deployment, Worker models
│   ├── views.py            # Django views
│   ├── api.py              # FastAPI endpoints
│   ├── installer.py        # Laravel installer
│   ├── deployer.py         # Zero-downtime deployer
│   ├── artisan.py          # Artisan command runner
│   ├── horizon.py          # Horizon management
│   ├── scheduler.py        # Scheduler management
│   ├── env_manager.py      # .env management
│   ├── logs.py             # Log viewer
│   └── templates/
│       ├── dashboard.html
│       ├── deploy.html
│       ├── artisan.html
│       ├── logs.html
│       └── env.html
```

#### Database Migrations

```python
# laravelManager/migrations/0001_initial.py

from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('websiteFunctions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LaravelSite',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('website', models.OneToOneField(on_delete=models.CASCADE, to='websiteFunctions.Websites')),
                ('laravel_version', models.CharField(max_length=20, default='12.x')),
                ('php_version', models.CharField(max_length=10, default='8.3')),
                ('deployment_strategy', models.CharField(max_length=20, default='zero-downtime')),
                ('horizon_enabled', models.BooleanField(default=False)),
                ('octane_enabled', models.BooleanField(default=False)),
                ('scheduler_enabled', models.BooleanField(default=False)),
                ('env_encrypted', models.BooleanField(default=False)),
                ('last_deployed', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Deployment',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('laravel_site', models.ForeignKey(on_delete=models.CASCADE, to='laravelManager.LaravelSite')),
                ('release_id', models.CharField(max_length=50)),
                ('git_commit', models.CharField(max_length=40, null=True)),
                ('git_branch', models.CharField(max_length=100, null=True)),
                ('status', models.CharField(max_length=20)),  # pending, running, success, failed
                ('log', models.TextField(null=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='QueueWorker',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('laravel_site', models.ForeignKey(on_delete=models.CASCADE, to='laravelManager.LaravelSite')),
                ('name', models.CharField(max_length=100)),
                ('queue', models.CharField(max_length=100, default='default')),
                ('processes', models.IntegerField(default=1)),
                ('timeout', models.IntegerField(default=60)),
                ('tries', models.IntegerField(default=3)),
                ('enabled', models.BooleanField(default=True)),
            ],
        ),
    ]
```

---

### 1.4 Phase 3: AI Integration (Weeks 7-10)

#### New AI Module Structure

```
mindset/
├── aiEngine/                # NEW - AI integration module
│   ├── __init__.py
│   ├── models.py           # AIProvider, AIConfig models
│   ├── views.py            # Django views
│   ├── api.py              # FastAPI endpoints
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py         # Abstract provider
│   │   ├── ollama.py       # Local LLM
│   │   ├── deepinfra.py    # DeepInfra API
│   │   ├── openai.py       # OpenAI API
│   │   └── huggingface.py  # HuggingFace API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── log_analyzer.py
│   │   ├── error_explainer.py
│   │   ├── security_scanner.py
│   │   ├── performance_tuner.py
│   │   └── deployment_assistant.py
│   ├── router.py           # AI routing logic
│   └── templates/
│       ├── dashboard.html
│       └── settings.html
```

---

### 1.5 Phase 4: Enterprise Features (Weeks 11-14)

#### Modules to Enhance/Create

1. **Backup System Overhaul**
   - Migrate `backup/` and `IncBackups/` to unified system
   - Add encryption layer
   - Add Backblaze B2, MinIO support
   - Implement retention policies

2. **Secrets Vault**
   - New `secrets/` module
   - Encrypted storage
   - Key rotation
   - Audit logging

3. **Monitoring Enhancement**
   - Prometheus metrics export
   - Grafana dashboard templates
   - Alert manager integration

---

### 1.6 Phase 5: Polish (Weeks 15-16)

1. **UI Modernization**
   - Dark mode support
   - Mobile responsiveness
   - App-centric dashboard

2. **Documentation**
   - API documentation (OpenAPI)
   - User guides
   - Developer documentation

3. **Testing**
   - Unit tests
   - Integration tests
   - End-to-end tests

---

## Part 2: Migration Guide

### 2.1 Migration Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MIGRATION PROCESS                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1           STEP 2           STEP 3           STEP 4           STEP 5 │
│  Backup           Update           Migrate          Verify           Cleanup│
│                                                                              │
│  ┌─────────┐     ┌─────────┐      ┌─────────┐      ┌─────────┐     ┌─────┐ │
│  │Full     │     │Stop     │      │Run      │      │Test All │     │Remove│ │
│  │System   │────▶│Services │─────▶│Migration│─────▶│Services │────▶│Old   │ │
│  │Backup   │     │         │      │Script   │      │         │     │Files │ │
│  └─────────┘     └─────────┘      └─────────┘      └─────────┘     └─────┘ │
│                                                                              │
│  ~30 min          ~5 min           ~15 min          ~10 min          ~5 min │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Pre-Migration Checklist

```bash
#!/bin/bash
# Pre-migration checklist script

echo "=== Mindset Migration Pre-Check ==="

# Check CyberPanel version
CP_VERSION=$(cat /usr/local/CyberCP/version.txt 2>/dev/null || echo "unknown")
echo "Current CyberPanel Version: $CP_VERSION"

# Check if minimum version
if [[ "$CP_VERSION" < "2.3" ]]; then
    echo "WARNING: CyberPanel version should be 2.3+ for smooth migration"
fi

# Check disk space
FREE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | tr -dc '0-9')
echo "Free Disk Space: ${FREE_SPACE}GB"
if [[ $FREE_SPACE -lt 10 ]]; then
    echo "WARNING: Less than 10GB free space. Migration requires ~5GB"
fi

# Count websites
SITE_COUNT=$(mysql -u root cyberpanel -se "SELECT COUNT(*) FROM websiteFunctions_websites" 2>/dev/null || echo "0")
echo "Number of Websites: $SITE_COUNT"

# Count databases
DB_COUNT=$(mysql -u root cyberpanel -se "SELECT COUNT(*) FROM databases_databases" 2>/dev/null || echo "0")
echo "Number of Databases: $DB_COUNT"

# Check backup destinations
echo ""
echo "=== Backup Destinations ==="
mysql -u root cyberpanel -se "SELECT * FROM backup_normalbackupdests" 2>/dev/null || echo "No backup destinations configured"

# Check running services
echo ""
echo "=== Running Services ==="
systemctl is-active --quiet lsws && echo "OpenLiteSpeed: Running" || echo "OpenLiteSpeed: Not Running"
systemctl is-active --quiet mysql && echo "MySQL: Running" || echo "MySQL: Not Running"
systemctl is-active --quiet gunicorn && echo "Gunicorn: Running" || echo "Gunicorn: Not Running"

echo ""
echo "=== Pre-Check Complete ==="
echo "Review the above information before proceeding with migration."
```

---

### 2.3 Migration Script

```bash
#!/bin/bash
# migrate-to-mindset.sh - CyberPanel to Mindset migration script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CYBERPANEL_PATH="/usr/local/CyberCP"
MINDSET_PATH="/opt/mindset"
BACKUP_PATH="/root/cyberpanel-migration-backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

#####################################################################
# Step 1: Full System Backup
#####################################################################

backup_system() {
    log "Step 1: Creating full system backup..."

    mkdir -p "$BACKUP_PATH"

    # Backup CyberPanel directory
    log "Backing up CyberPanel installation..."
    tar -czf "$BACKUP_PATH/cyberpanel_$TIMESTAMP.tar.gz" -C /usr/local CyberCP

    # Backup database
    log "Backing up database..."
    mysqldump -u root --all-databases > "$BACKUP_PATH/all_databases_$TIMESTAMP.sql"

    # Backup nginx/OLS configs
    log "Backing up web server configs..."
    tar -czf "$BACKUP_PATH/lsws_configs_$TIMESTAMP.tar.gz" /usr/local/lsws/conf 2>/dev/null || true

    # Backup SSL certificates
    log "Backing up SSL certificates..."
    tar -czf "$BACKUP_PATH/ssl_certs_$TIMESTAMP.tar.gz" /etc/letsencrypt 2>/dev/null || true

    # Backup home directories (user data)
    log "Backing up user data..."
    tar -czf "$BACKUP_PATH/home_dirs_$TIMESTAMP.tar.gz" /home --exclude='*/node_modules' --exclude='*/vendor' 2>/dev/null || true

    log "Backup completed: $BACKUP_PATH"
}

#####################################################################
# Step 2: Stop Services
#####################################################################

stop_services() {
    log "Step 2: Stopping services..."

    systemctl stop gunicorn 2>/dev/null || true
    systemctl stop lscpd 2>/dev/null || true

    # Don't stop lsws or mysql - they're needed for hosted sites

    log "Services stopped"
}

#####################################################################
# Step 3: Run Migration
#####################################################################

run_migration() {
    log "Step 3: Running migration..."

    # Clone Mindset
    log "Downloading Mindset..."
    if [[ -d "$MINDSET_PATH" ]]; then
        cd "$MINDSET_PATH"
        git fetch origin
        git checkout main
        git pull origin main
    else
        git clone https://github.com/mindset-hosting/mindset.git "$MINDSET_PATH"
    fi

    cd "$MINDSET_PATH"

    # Create virtual environment
    log "Setting up Python environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    # Migrate database schema
    log "Migrating database schema..."

    # Update database name (optional - can keep using 'cyberpanel')
    # mysql -u root -e "RENAME DATABASE cyberpanel TO mindset"

    # Run Django migrations
    python manage.py migrate

    # Copy user data and configurations
    log "Migrating user data..."
    python scripts/migrate_from_cyberpanel.py \
        --source="$CYBERPANEL_PATH" \
        --target="$MINDSET_PATH"

    # Update service files
    log "Updating service files..."
    cp "$MINDSET_PATH/install/systemd/mindset.service" /etc/systemd/system/
    cp "$MINDSET_PATH/install/systemd/mindset-api.service" /etc/systemd/system/

    systemctl daemon-reload

    log "Migration completed"
}

#####################################################################
# Step 4: Verify Services
#####################################################################

verify_services() {
    log "Step 4: Verifying services..."

    # Start Mindset services
    systemctl start mindset
    systemctl start mindset-api

    sleep 5

    # Check services
    if systemctl is-active --quiet mindset; then
        log "Mindset service: Running"
    else
        error "Mindset service failed to start"
    fi

    if systemctl is-active --quiet mindset-api; then
        log "Mindset API: Running"
    else
        warn "Mindset API may have issues"
    fi

    # Test API endpoint
    if curl -s http://localhost:8091/api/health | grep -q "ok"; then
        log "API health check: Passed"
    else
        warn "API health check: May have issues"
    fi

    # Verify websites are accessible
    log "Verifying hosted websites..."
    mysql -u root cyberpanel -se "SELECT domain FROM websiteFunctions_websites LIMIT 5" | while read domain; do
        if curl -s -o /dev/null -w "%{http_code}" "http://$domain" | grep -q "200\|301\|302"; then
            log "  $domain: OK"
        else
            warn "  $domain: May have issues"
        fi
    done

    log "Verification completed"
}

#####################################################################
# Step 5: Cleanup
#####################################################################

cleanup() {
    log "Step 5: Cleanup..."

    # Enable Mindset services
    systemctl enable mindset
    systemctl enable mindset-api

    # Disable old CyberPanel services
    systemctl disable gunicorn 2>/dev/null || true
    systemctl disable lscpd 2>/dev/null || true

    # Optional: Remove old CyberPanel (keep backup)
    read -p "Remove old CyberPanel installation? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -rf "$CYBERPANEL_PATH"
        log "Old CyberPanel removed"
    else
        log "Old CyberPanel kept at $CYBERPANEL_PATH"
    fi

    log "Cleanup completed"
}

#####################################################################
# Main
#####################################################################

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     CYBERPANEL TO MINDSET MIGRATION                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    # Check root
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi

    # Confirm
    echo "This will migrate your CyberPanel installation to Mindset."
    echo "A full backup will be created before migration."
    echo ""
    read -p "Continue? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        exit 0
    fi

    backup_system
    stop_services
    run_migration
    verify_services
    cleanup

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     MIGRATION COMPLETED SUCCESSFULLY                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Access Mindset at: https://$(hostname):8090"
    echo "Backup location: $BACKUP_PATH"
    echo ""
}

main "$@"
```

---

### 2.4 Data Migration Script

```python
#!/usr/bin/env python3
# scripts/migrate_from_cyberpanel.py

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

class CyberPanelMigrator:
    """Migrate data from CyberPanel to Mindset"""

    def __init__(self, source_path: str, target_path: str):
        self.source = Path(source_path)
        self.target = Path(target_path)
        self.log_file = self.target / 'migration.log'

    def log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')

    def migrate_settings(self):
        """Migrate settings from CyberPanel .env to Mindset"""
        self.log("Migrating settings...")

        source_env = self.source / '.env'
        target_env = self.target / '.env'

        if source_env.exists():
            # Read source env
            env_vars = {}
            with open(source_env, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value

            # Map old keys to new keys
            key_mapping = {
                'SECRET_KEY': 'SECRET_KEY',
                'DB_NAME': 'DB_NAME',
                'DB_USER': 'DB_USER',
                'DB_PASSWORD': 'DB_PASSWORD',
                'DB_HOST': 'DB_HOST',
                'DB_PORT': 'DB_PORT',
            }

            # Create new env file
            with open(target_env, 'w') as f:
                f.write("# Mindset Configuration (migrated from CyberPanel)\n")
                f.write(f"# Migration date: {datetime.now().isoformat()}\n\n")

                for old_key, new_key in key_mapping.items():
                    if old_key in env_vars:
                        f.write(f"{new_key}={env_vars[old_key]}\n")

            self.log("Settings migrated successfully")
        else:
            self.log("No .env file found in source")

    def migrate_users(self):
        """Migrate user accounts"""
        self.log("Migrating user accounts...")

        # Users are in the database, so this is handled by Django migrations
        # Just log the action
        self.log("User accounts will be migrated via database migration")

    def migrate_websites(self):
        """Migrate website configurations"""
        self.log("Migrating website configurations...")

        # Website data is in database
        # OLS vhost configs may need updating
        vhosts_path = Path('/usr/local/lsws/conf/vhosts')

        if vhosts_path.exists():
            for vhost_dir in vhosts_path.iterdir():
                if vhost_dir.is_dir():
                    conf_file = vhost_dir / 'vhconf.conf'
                    if conf_file.exists():
                        # Update any CyberPanel references
                        content = conf_file.read_text()
                        content = content.replace('CyberCP', 'Mindset')
                        content = content.replace('cyberpanel', 'mindset')
                        conf_file.write_text(content)
                        self.log(f"Updated vhost config: {vhost_dir.name}")

        self.log("Website configurations migrated")

    def migrate_ssl_certs(self):
        """Verify SSL certificates are intact"""
        self.log("Verifying SSL certificates...")

        ssl_path = Path('/etc/letsencrypt/live')
        if ssl_path.exists():
            cert_count = len(list(ssl_path.iterdir()))
            self.log(f"Found {cert_count} SSL certificates")
        else:
            self.log("No Let's Encrypt certificates found")

    def migrate_custom_configs(self):
        """Migrate custom configurations"""
        self.log("Migrating custom configurations...")

        # Copy any custom scripts
        custom_scripts = self.source / 'custom_scripts'
        if custom_scripts.exists():
            target_custom = self.target / 'custom_scripts'
            shutil.copytree(custom_scripts, target_custom, dirs_exist_ok=True)
            self.log("Custom scripts migrated")

        # Copy any plugins
        plugins_source = self.source / 'pluginHolder'
        if plugins_source.exists():
            plugins_target = self.target / 'pluginHolder'
            shutil.copytree(plugins_source, plugins_target, dirs_exist_ok=True)
            self.log("Plugins migrated")

    def generate_report(self) -> dict:
        """Generate migration report"""
        report = {
            'migration_date': datetime.now().isoformat(),
            'source_path': str(self.source),
            'target_path': str(self.target),
            'status': 'completed',
            'actions': []
        }

        # Read log file
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                report['actions'] = f.readlines()

        # Save report
        report_path = self.target / 'migration_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def run(self):
        """Run full migration"""
        self.log("Starting CyberPanel to Mindset migration...")
        self.log(f"Source: {self.source}")
        self.log(f"Target: {self.target}")

        self.migrate_settings()
        self.migrate_users()
        self.migrate_websites()
        self.migrate_ssl_certs()
        self.migrate_custom_configs()

        report = self.generate_report()
        self.log("Migration completed successfully")

        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate CyberPanel to Mindset')
    parser.add_argument('--source', required=True, help='CyberPanel installation path')
    parser.add_argument('--target', required=True, help='Mindset installation path')

    args = parser.parse_args()

    migrator = CyberPanelMigrator(args.source, args.target)
    migrator.run()
```

---

### 2.5 Rollback Procedure

```bash
#!/bin/bash
# rollback-to-cyberpanel.sh - Rollback from Mindset to CyberPanel

set -e

BACKUP_PATH="/root/cyberpanel-migration-backup"
MINDSET_PATH="/opt/mindset"
CYBERPANEL_PATH="/usr/local/CyberCP"

echo "=== Mindset to CyberPanel Rollback ==="

# Find most recent backup
LATEST_BACKUP=$(ls -t "$BACKUP_PATH"/cyberpanel_*.tar.gz 2>/dev/null | head -1)

if [[ -z "$LATEST_BACKUP" ]]; then
    echo "ERROR: No backup found in $BACKUP_PATH"
    exit 1
fi

echo "Found backup: $LATEST_BACKUP"
read -p "Rollback to this backup? [y/N]: " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    exit 0
fi

# Stop Mindset services
echo "Stopping Mindset services..."
systemctl stop mindset 2>/dev/null || true
systemctl stop mindset-api 2>/dev/null || true

# Restore database
echo "Restoring database..."
DB_BACKUP=$(ls -t "$BACKUP_PATH"/all_databases_*.sql 2>/dev/null | head -1)
if [[ -n "$DB_BACKUP" ]]; then
    mysql -u root < "$DB_BACKUP"
fi

# Restore CyberPanel
echo "Restoring CyberPanel..."
rm -rf "$CYBERPANEL_PATH"
tar -xzf "$LATEST_BACKUP" -C /usr/local

# Restore OLS configs
echo "Restoring web server configs..."
OLS_BACKUP=$(ls -t "$BACKUP_PATH"/lsws_configs_*.tar.gz 2>/dev/null | head -1)
if [[ -n "$OLS_BACKUP" ]]; then
    tar -xzf "$OLS_BACKUP" -C /
fi

# Restore services
echo "Restoring services..."
systemctl enable gunicorn
systemctl start gunicorn
systemctl restart lsws

# Disable Mindset services
systemctl disable mindset 2>/dev/null || true
systemctl disable mindset-api 2>/dev/null || true

echo ""
echo "=== Rollback Completed ==="
echo "CyberPanel has been restored from backup."
echo "Access at: https://$(hostname):8090"
```

---

### 2.6 Post-Migration Checklist

```markdown
# Post-Migration Checklist

## Immediate Verification (Within 1 hour)

- [ ] Admin panel accessible at https://server:8090
- [ ] Admin login works with existing credentials
- [ ] All websites listed in dashboard
- [ ] At least one website loads correctly
- [ ] SSL certificates are valid
- [ ] Email services working (if configured)

## Within 24 hours

- [ ] All websites accessible and functioning
- [ ] Database connections working for all sites
- [ ] Backup jobs running (if scheduled)
- [ ] DNS resolving correctly (if using PowerDNS)
- [ ] FTP access working (if configured)
- [ ] File manager accessible

## Within 1 week

- [ ] Review all Laravel-specific features
- [ ] Test deployment for at least one Laravel site
- [ ] Verify cron jobs executing
- [ ] Check resource usage is normal
- [ ] Review logs for any errors
- [ ] Update DNS records if server hostname changed

## Documentation

- [ ] Update internal documentation
- [ ] Note any custom configurations
- [ ] Document any issues encountered
- [ ] Share feedback with Mindset team
```

---

## Part 3: Open Source Licensing

### 3.1 Recommended License

Mindset should continue under the **GPLv3 license** (same as CyberPanel) to:
- Maintain compatibility with existing CyberPanel code
- Ensure all derivative works remain open source
- Allow commercial use while protecting the community

### 3.2 License Header

```
# Mindset - Laravel-Native Hosting Platform
# Copyright (C) 2024 Mindset Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
```

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
