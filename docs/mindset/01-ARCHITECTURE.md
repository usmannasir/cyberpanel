# Mindset Platform Architecture Document

## Executive Summary

Mindset is a next-generation, AI-powered hosting control panel forked from CyberPanel, purpose-built for Laravel 12 and modern PHP application hosting. This document outlines the complete system architecture, design decisions, and implementation strategy.

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture](#core-architecture)
3. [Technology Stack](#technology-stack)
4. [Module Architecture](#module-architecture)
5. [Laravel 12 Hosting Architecture](#laravel-12-hosting-architecture)
6. [AI Integration Architecture](#ai-integration-architecture)
7. [Security Architecture](#security-architecture)
8. [Backup & DR Architecture](#backup--dr-architecture)
9. [API Architecture](#api-architecture)
10. [Deployment Architecture](#deployment-architecture)

---

## 1. System Overview

### 1.1 Vision

Mindset transforms traditional web hosting into an intelligent, developer-centric platform that treats Laravel applications as first-class citizens while maintaining full compatibility with existing CyberPanel features.

### 1.2 Design Principles

1. **Laravel-First**: Every feature is designed with Laravel developers in mind
2. **AI-Native**: Intelligence is embedded, not bolted on
3. **Security-by-Default**: Zero-trust architecture throughout
4. **Automation-Obsessed**: Every action must be automatable
5. **Free & Open**: Prefer powerful FOSS tools over paid alternatives
6. **Developer Experience**: CLI-first, API-complete, UI-beautiful

### 1.3 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MINDSET PLATFORM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Web UI    │  │  REST API   │  │  CLI Tool   │  │  Webhooks   │        │
│  │  (Django)   │  │  (FastAPI)  │  │  (mindset)  │  │   Server    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                   │                                          │
│  ┌────────────────────────────────┴────────────────────────────────────┐    │
│  │                     CORE SERVICE LAYER                               │    │
│  ├──────────────────────────────────────────────────────────────────────┤    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │   Laravel   │  │    Site     │  │   Backup    │  │     AI      │ │    │
│  │  │   Manager   │  │   Manager   │  │   Manager   │  │   Engine    │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │     SSL     │  │     DNS     │  │   Database  │  │   Security  │ │    │
│  │  │   Manager   │  │   Manager   │  │   Manager   │  │   Manager   │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│  ┌────────────────────────────────┴────────────────────────────────────┐    │
│  │                    INFRASTRUCTURE LAYER                              │    │
│  ├──────────────────────────────────────────────────────────────────────┤    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │    │
│  │  │OpenLite  │  │  MySQL/  │  │  Redis   │  │PowerDNS  │  │Postfix │ │    │
│  │  │Speed     │  │PostgreSQL│  │          │  │          │  │Dovecot │ │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │    │
│  │  │PHP-FPM   │  │Meilisearch│ │ MinIO    │  │ Fail2Ban │  │  UFW   │ │    │
│  │  │8.3+JIT   │  │          │  │          │  │ CrowdSec │  │        │ │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architecture

### 2.1 Application Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web UI | Django 4.2+ | Administrative dashboard |
| REST API | FastAPI | High-performance async API |
| CLI | Python Click | Command-line interface |
| WebSocket | FastAPI + Uvicorn | Real-time updates |

### 2.2 Service Layer

```
mindset/
├── core/                    # Core platform services
│   ├── laravel/            # Laravel-specific management
│   │   ├── deployer.py     # Zero-downtime deployments
│   │   ├── artisan.py      # Artisan command runner
│   │   ├── horizon.py      # Queue management
│   │   ├── octane.py       # Octane server management
│   │   ├── scheduler.py    # Cron/scheduler UI
│   │   └── env_manager.py  # .env encryption & validation
│   ├── ai/                 # AI integration services
│   │   ├── providers/      # AI provider adapters
│   │   ├── analyzers/      # Log/error analyzers
│   │   └── assistants/     # AI assistants
│   ├── backup/             # Backup services
│   ├── security/           # Security services
│   └── monitoring/         # Metrics & monitoring
├── infrastructure/          # Infrastructure management
│   ├── webserver/          # OLS configuration
│   ├── database/           # MySQL/PostgreSQL
│   ├── cache/              # Redis management
│   └── search/             # Meilisearch integration
└── integrations/           # External integrations
    ├── git/                # GitHub/GitLab/Bitbucket
    ├── cloud/              # S3/GCS/Azure Blob
    └── notifications/      # Slack/Discord/Email
```

### 2.3 Data Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Primary    │    │    Cache     │    │    Search    │       │
│  │   Database   │    │    Layer     │    │    Index     │       │
│  │              │    │              │    │              │       │
│  │  MySQL 8.0   │◄──►│    Redis     │    │ Meilisearch  │       │
│  │  PostgreSQL  │    │   Cluster    │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                    │               │
│         └───────────────────┴────────────────────┘               │
│                            │                                     │
│  ┌──────────────────────────┴───────────────────────────────┐   │
│  │                    BACKUP TARGETS                         │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │   │
│  │  │ Local  │ │  S3    │ │  B2    │ │ GDrive │ │  SFTP  │  │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### 3.1 Core Platform

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Backend | Python | 3.11+ | Core application |
| Web Framework | Django | 4.2+ | Admin UI |
| API Framework | FastAPI | 0.115+ | REST/WebSocket API |
| Task Queue | Celery | 5.3+ | Background jobs |
| Message Broker | Redis | 7.0+ | Queue backend |
| Primary DB | MySQL | 8.0+ | Application data |
| Alternative DB | PostgreSQL | 15+ | Optional |
| Cache | Redis | 7.0+ | Session/cache |

### 3.2 Web Hosting Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Server | OpenLiteSpeed | High-performance HTTP |
| PHP Runtime | PHP 8.3 | Laravel execution |
| PHP Accelerator | OPcache + JIT | Performance |
| Process Manager | PHP-FPM | Request handling |
| Reverse Proxy | OLS | Load balancing |

### 3.3 Laravel-Specific Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Queue Server | Redis | Laravel queues |
| Search | Meilisearch | Laravel Scout |
| Cache | Redis | Laravel cache |
| Broadcasting | Soketi | Laravel Echo |
| Octane | RoadRunner/Swoole | High-performance |

### 3.4 DevOps & Monitoring

| Component | Technology | Purpose |
|-----------|------------|---------|
| Metrics | Prometheus | Time-series metrics |
| Dashboards | Grafana | Visualization |
| Log Aggregation | Loki | Log management |
| Security | Fail2Ban + CrowdSec | Intrusion prevention |
| Firewall | UFW | Network security |
| WAF | ModSecurity | Application firewall |

---

## 4. Module Architecture

### 4.1 Module Structure

Each Mindset module follows this structure:

```
module_name/
├── __init__.py
├── models.py           # Django models
├── views.py            # Django views (UI)
├── api.py              # FastAPI endpoints
├── services.py         # Business logic
├── tasks.py            # Celery tasks
├── schemas.py          # Pydantic schemas
├── urls.py             # URL routing
├── templates/          # Django templates
├── tests/              # Unit & integration tests
└── migrations/         # Database migrations
```

### 4.2 Core Modules

1. **laravelManager** - Laravel application lifecycle
2. **siteManager** - Website/domain management
3. **databaseManager** - MySQL/PostgreSQL management
4. **backupManager** - Backup orchestration
5. **securityManager** - Security & compliance
6. **aiEngine** - AI integration layer
7. **deploymentManager** - CI/CD pipelines
8. **monitoringManager** - Metrics & alerting

---

## 5. Laravel 12 Hosting Architecture

### 5.1 Laravel Application Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LARAVEL APPLICATION LIFECYCLE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CREATE          CONFIGURE         DEPLOY          OPERATE         SCALE    │
│    │                 │               │                │              │       │
│    ▼                 ▼               ▼                ▼              ▼       │
│ ┌──────┐        ┌──────────┐    ┌─────────┐     ┌─────────┐    ┌────────┐  │
│ │Fresh │        │.env Setup│    │Git Push │     │Monitor  │    │Add     │  │
│ │Install│       │PHP Config│    │Webhook  │     │Logs     │    │Workers │  │
│ │       │        │Cron Jobs │    │CI/CD    │     │Metrics  │    │Scale   │  │
│ └──────┘        └──────────┘    └─────────┘     └─────────┘    └────────┘  │
│    │                 │               │                │              │       │
│    └─────────────────┴───────────────┴────────────────┴──────────────┘       │
│                                    │                                         │
│                            ZERO-DOWNTIME                                     │
│                            DEPLOYMENT FLOW                                   │
│                                    │                                         │
│    ┌───────────────────────────────┴────────────────────────────────────┐   │
│    │                                                                     │   │
│    │  1. Clone to releases/timestamp                                     │   │
│    │  2. Copy shared/ (.env, storage)                                   │   │
│    │  3. composer install --no-dev                                       │   │
│    │  4. npm ci && npm run build                                         │   │
│    │  5. php artisan migrate --force                                     │   │
│    │  6. php artisan config:cache                                        │   │
│    │  7. php artisan route:cache                                         │   │
│    │  8. php artisan view:cache                                          │   │
│    │  9. Health check                                                    │   │
│    │  10. Symlink current -> releases/timestamp                          │   │
│    │  11. Reload PHP-FPM                                                 │   │
│    │  12. Cleanup old releases                                           │   │
│    │                                                                     │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Laravel Site Directory Structure

```
/home/{user}/{domain}/
├── current -> releases/20240115120000       # Active release symlink
├── releases/                                 # Deployment releases
│   ├── 20240115120000/                      # Current release
│   ├── 20240115100000/                      # Previous release
│   └── 20240114150000/                      # Rollback target
├── shared/                                   # Persistent data
│   ├── .env                                 # Environment (encrypted)
│   ├── storage/                             # Laravel storage
│   │   ├── app/
│   │   ├── framework/
│   │   └── logs/
│   └── node_modules/                        # Cached dependencies
├── .mindset/                                # Mindset metadata
│   ├── config.yaml                          # App configuration
│   ├── hooks/                               # Deployment hooks
│   │   ├── pre-deploy.sh
│   │   ├── post-deploy.sh
│   │   └── health-check.sh
│   └── logs/                                # Deployment logs
└── logs/                                    # Web server logs
    ├── access.log
    └── error.log
```

### 5.3 Laravel-Specific Features

#### Environment Management

```yaml
# .mindset/config.yaml
laravel:
  version: "12.x"
  php_version: "8.3"

  environment:
    encryption: true
    encryption_key_source: "vault"  # vault, env, file

  deployment:
    strategy: "zero-downtime"  # zero-downtime, standard, maintenance
    keep_releases: 5

  optimization:
    opcache: true
    jit: true
    preloading: true

  workers:
    horizon:
      enabled: true
      supervisor: "default"
    scheduler:
      enabled: true
      timezone: "UTC"
    octane:
      enabled: false
      server: "roadrunner"  # roadrunner, swoole
      workers: 4

  health_checks:
    - type: "http"
      path: "/health"
      expected_status: 200
    - type: "artisan"
      command: "about"
```

#### Queue Worker Management

```
┌─────────────────────────────────────────────────────────────────┐
│                 LARAVEL QUEUE ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    SUPERVISOR                            │    │
│  │                   (mindset-worker)                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │   Queue:    │   │   Queue:    │   │   Queue:    │           │
│  │   default   │   │    high     │   │    low      │           │
│  │   (3 proc)  │   │   (2 proc)  │   │   (1 proc)  │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                     │
│                     ┌──────▼──────┐                             │
│                     │    Redis    │                             │
│                     │   Queue     │                             │
│                     │   Backend   │                             │
│                     └─────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. AI Integration Architecture

### 6.1 AI Provider Abstraction

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI INTEGRATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                 AI PROVIDER INTERFACE                    │    │
│  │               (Abstract Base Class)                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│     ┌──────────┬───────────┼───────────┬───────────┐            │
│     │          │           │           │           │            │
│     ▼          ▼           ▼           ▼           ▼            │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │
│ │DeepInfra│ │ OpenAI │ │ Ollama │ │LMStudio│ │Hugging │         │
│ │Provider│ │Provider│ │Provider│ │Provider│ │ Face   │         │
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘         │
│     │          │           │           │           │            │
│     └──────────┴───────────┴───────────┴───────────┘            │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │  AI ROUTER      │                           │
│                   │  (Cost/Speed    │                           │
│                   │   Optimization) │                           │
│                   └────────┬────────┘                           │
│                            │                                     │
│  ┌─────────────────────────┴─────────────────────────────┐      │
│  │                    AI SERVICES                         │      │
│  ├────────────────────────────────────────────────────────┤      │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐          │      │
│  │ │    Log     │ │   Error    │ │  Security  │          │      │
│  │ │  Analyzer  │ │ Explainer  │ │  Scanner   │          │      │
│  │ └────────────┘ └────────────┘ └────────────┘          │      │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐          │      │
│  │ │Performance │ │   Code     │ │ Deployment │          │      │
│  │ │   Tuner    │ │  Reviewer  │ │ Assistant  │          │      │
│  │ └────────────┘ └────────────┘ └────────────┘          │      │
│  └────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 AI Configuration

```yaml
# /etc/mindset/ai.yaml
ai:
  enabled: true
  mode: "hybrid"  # local, cloud, hybrid

  providers:
    deepinfra:
      enabled: true
      api_key: "${DEEPINFRA_API_KEY}"
      default_model: "meta-llama/Meta-Llama-3.1-70B-Instruct"

    ollama:
      enabled: true
      host: "localhost"
      port: 11434
      models:
        - "llama3.1:8b"
        - "codellama:13b"

    openai:
      enabled: false
      api_key: "${OPENAI_API_KEY}"

  routing:
    # Use local for simple tasks, cloud for complex
    log_analysis: "local"
    error_explanation: "cloud"
    security_scan: "local"
    code_review: "cloud"

  privacy:
    redact_secrets: true
    anonymize_paths: true
    local_only_mode: false
```

---

## 7. Security Architecture

### 7.1 Security Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SECURITY ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 1: NETWORK                                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  UFW Firewall │ CrowdSec │ Fail2Ban │ Rate Limiting │ GeoIP Blocking  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  LAYER 2: APPLICATION                                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ModSecurity WAF │ OWASP Rules │ Input Validation │ CSRF Protection   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  LAYER 3: AUTHENTICATION                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  2FA/MFA │ API Keys │ SSH Keys │ Session Management │ Password Policy │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  LAYER 4: AUTHORIZATION                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  RBAC │ ACLs │ Resource Isolation │ User Quotas │ Permission Checks   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  LAYER 5: DATA                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Encryption at Rest │ TLS in Transit │ Secret Vault │ Backup Encrypt  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  LAYER 6: MONITORING                                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Audit Logs │ Intrusion Detection │ Anomaly Detection │ AI Security   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Laravel App Isolation

```
┌─────────────────────────────────────────────────────────────────┐
│              LARAVEL APPLICATION ISOLATION                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    SYSTEM USER                            │   │
│  │                  (per application)                        │   │
│  │                                                           │   │
│  │  User: app_domain_com                                     │   │
│  │  Group: app_domain_com                                    │   │
│  │  Home: /home/app_domain_com                              │   │
│  │  Shell: /usr/sbin/nologin (or /bin/bash if SSH enabled)  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    PHP-FPM POOL                           │   │
│  │                  (per application)                        │   │
│  │                                                           │   │
│  │  Pool: app_domain_com                                     │   │
│  │  User: app_domain_com                                     │   │
│  │  Listen: /run/php/app_domain_com.sock                     │   │
│  │  open_basedir: /home/app_domain_com:/tmp                  │   │
│  │  disable_functions: exec,shell_exec,system,passthru...    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    DATABASE                               │   │
│  │                  (per application)                        │   │
│  │                                                           │   │
│  │  Database: app_domain_com                                 │   │
│  │  User: app_domain_com                                     │   │
│  │  Host: localhost (127.0.0.1 only)                        │   │
│  │  Privileges: SELECT,INSERT,UPDATE,DELETE,CREATE,INDEX... │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Backup & DR Architecture

### 8.1 Backup Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BACKUP ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         BACKUP TYPES                                   │  │
│  │                                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │   Database   │  │    Files     │  │   Full App   │                 │  │
│  │  │   Backup     │  │   Backup     │  │   Snapshot   │                 │  │
│  │  │              │  │              │  │              │                 │  │
│  │  │ mysqldump    │  │ rsync/tar    │  │ Combined     │                 │  │
│  │  │ Incremental  │  │ Incremental  │  │ Atomic       │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                            ┌───────▼───────┐                                │
│                            │  ENCRYPTION   │                                │
│                            │   (AES-256)   │                                │
│                            └───────┬───────┘                                │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                       BACKUP DESTINATIONS                              │  │
│  │                                                                        │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │  │
│  │  │ Local  │ │ S3/    │ │ Back-  │ │ Google │ │ SFTP   │ │ MinIO  │   │  │
│  │  │ Disk   │ │ Wasabi │ │ blaze  │ │ Drive  │ │        │ │        │   │  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                       RETENTION POLICIES                               │  │
│  │                                                                        │  │
│  │  Daily:   Keep 7 days                                                 │  │
│  │  Weekly:  Keep 4 weeks                                                │  │
│  │  Monthly: Keep 12 months                                              │  │
│  │  Yearly:  Keep forever (optional)                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Disaster Recovery

```yaml
# DR Configuration
disaster_recovery:
  rpo: "1 hour"          # Recovery Point Objective
  rto: "15 minutes"      # Recovery Time Objective

  strategies:
    database:
      - type: "point-in-time"
        retention: "7 days"
      - type: "daily-full"
        retention: "30 days"

    files:
      - type: "incremental"
        frequency: "hourly"
      - type: "full"
        frequency: "daily"

  failover:
    automatic: false
    notification:
      - email
      - slack
```

---

## 9. API Architecture

### 9.1 API Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Base URL: https://panel.domain.com/api/v1                                   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        AUTHENTICATION                                  │  │
│  │                                                                        │  │
│  │  Bearer Token: Authorization: Bearer <api_key>                        │  │
│  │  API Key: X-API-Key: <api_key>                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         ENDPOINTS                                      │  │
│  │                                                                        │  │
│  │  /sites                    - Site management                          │  │
│  │  /sites/{id}/laravel       - Laravel-specific operations              │  │
│  │  /sites/{id}/deployments   - Deployment management                    │  │
│  │  /sites/{id}/backups       - Backup operations                        │  │
│  │  /sites/{id}/ssl           - SSL certificate management               │  │
│  │  /sites/{id}/databases     - Database management                      │  │
│  │  /sites/{id}/cron          - Cron job management                      │  │
│  │  /sites/{id}/workers       - Queue worker management                  │  │
│  │                                                                        │  │
│  │  /servers                  - Server management                        │  │
│  │  /servers/{id}/services    - Service control                          │  │
│  │  /servers/{id}/firewall    - Firewall rules                           │  │
│  │                                                                        │  │
│  │  /ai/analyze               - AI analysis endpoints                    │  │
│  │  /ai/explain               - Error explanation                        │  │
│  │  /ai/suggest               - Performance suggestions                  │  │
│  │                                                                        │  │
│  │  /webhooks                 - Webhook management                       │  │
│  │  /users                    - User management                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 API Response Format

```json
{
  "success": true,
  "data": {
    "id": "site_abc123",
    "domain": "example.com",
    "laravel": {
      "version": "12.0",
      "php_version": "8.3"
    }
  },
  "meta": {
    "request_id": "req_xyz789",
    "timestamp": "2024-01-15T12:00:00Z"
  }
}
```

---

## 10. Deployment Architecture

### 10.1 Installation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MINDSET INSTALLATION FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  curl -fsSL https://mindset.sh/install.sh | bash                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Phase 1: Pre-flight Checks                                        │     │
│  │  ├── Verify Ubuntu 20.04/22.04/24.04                              │     │
│  │  ├── Check minimum resources (2GB RAM, 20GB disk)                 │     │
│  │  ├── Verify network connectivity                                   │     │
│  │  └── Check for conflicting software                               │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                               │                                              │
│                               ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Phase 2: System Hardening                                         │     │
│  │  ├── Configure UFW firewall                                        │     │
│  │  ├── SSH hardening (key-only, no root)                            │     │
│  │  ├── Install Fail2Ban                                              │     │
│  │  ├── Configure automatic security updates                          │     │
│  │  └── Set up CrowdSec                                              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                               │                                              │
│                               ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Phase 3: Core Services                                            │     │
│  │  ├── Install OpenLiteSpeed                                         │     │
│  │  ├── Install PHP 8.3 with extensions                              │     │
│  │  ├── Install MySQL 8.0                                             │     │
│  │  ├── Install Redis                                                 │     │
│  │  ├── Install Node.js (LTS)                                        │     │
│  │  └── Install Composer                                              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                               │                                              │
│                               ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Phase 4: Mindset Platform                                         │     │
│  │  ├── Clone Mindset repository                                      │     │
│  │  ├── Create Python virtual environment                            │     │
│  │  ├── Install Python dependencies                                   │     │
│  │  ├── Initialize database                                           │     │
│  │  ├── Configure services                                            │     │
│  │  └── Generate SSL certificate                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                               │                                              │
│                               ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Phase 5: Post-Installation                                        │     │
│  │  ├── Create admin user                                             │     │
│  │  ├── Start all services                                            │     │
│  │  ├── Run health checks                                             │     │
│  │  ├── Display access credentials                                    │     │
│  │  └── Send notification (if configured)                            │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Directory Structure

```
/opt/mindset/                    # Mindset installation
├── app/                         # Django application
├── api/                         # FastAPI application
├── cli/                         # CLI tools
├── services/                    # Background services
├── static/                      # Static assets
├── templates/                   # UI templates
└── migrations/                  # Database migrations

/etc/mindset/                    # Configuration
├── mindset.yaml                 # Main configuration
├── ai.yaml                      # AI configuration
├── backup.yaml                  # Backup configuration
└── ssl/                         # SSL certificates

/var/lib/mindset/                # Data
├── backups/                     # Local backups
├── secrets/                     # Encrypted secrets
└── cache/                       # Application cache

/var/log/mindset/                # Logs
├── app.log                      # Application log
├── api.log                      # API log
├── deployment.log               # Deployment log
└── security.log                 # Security audit log
```

---

## Appendix B: Service Ports

| Service | Port | Protocol |
|---------|------|----------|
| Mindset UI | 8090 | HTTPS |
| Mindset API | 8091 | HTTPS |
| OpenLiteSpeed | 80/443 | HTTP/HTTPS |
| OLS Admin | 7080 | HTTPS |
| MySQL | 3306 | TCP |
| Redis | 6379 | TCP |
| PowerDNS | 53 | UDP/TCP |
| SMTP | 25/587 | TCP |
| SSH | 22 | TCP |

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
*Author: Mindset Architecture Team*
