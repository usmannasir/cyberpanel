# CyberPanel Cloud Platform - VPS API Documentation

**Version:** 1.0.0
**Base URL:** `https://platform.cyberpersons.com/api/v1`
**Last Updated:** January 2026

---

## Table of Contents

1. [Introduction](#introduction)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Response Format](#response-format)
5. [Error Codes](#error-codes)
6. [Endpoints](#endpoints)
   - [General](#general-endpoints)
   - [Account & Billing](#account--billing-endpoints)
   - [VPS Management](#vps-management-endpoints)
   - [VPS Actions](#vps-action-endpoints)
   - [VPS Creation](#vps-creation-endpoints)

---

## Introduction

The CyberPanel Cloud Platform API allows you to programmatically manage your VPS instances, view account information, and automate your infrastructure. This RESTful API uses JSON for request and response bodies.

### Quick Start

1. Create an API key at https://platform.cyberpersons.com/api-keys/
2. Copy your key (shown only once)
3. Include it in the `Authorization` header:
   ```
   Authorization: Bearer cyp_live_your_api_key_here
   ```

---

## Authentication

All API requests (except `/health` and `/scopes`) require authentication using an API key.

### API Key Format

API keys have the format: `cyp_live_<64_character_hex_string>`

Example: `cyp_live_3ac1ca2feaADSRTSAFDbcdd86f2dc01c4a574e4a34EWRWEb9d995a28723caERERE`

### Authorization Header

Include your API key in the `Authorization` header using the Bearer scheme:

```
Authorization: Bearer cyp_live_your_api_key_here
```

### Permission Scopes

API keys have granular permission scopes. When creating an API key, select only the scopes you need:

| Scope | Description |
|-------|-------------|
| `vps:read` | List and view VPS instances, plans, locations, templates |
| `vps:write` | Create, start, stop, restart, and modify VPS instances |
| `vps:delete` | Delete VPS instances (destructive action) |
| `account:read` | View account information and API key metadata |
| `account:write` | Update account settings |
| `billing:read` | View balance, invoices, and billing information |
| `billing:write` | Add funds to account |
| `support:read` | View support tickets |
| `support:write` | Create and reply to support tickets |
| `email:read` | View email service information |
| `email:write` | Send emails via Email Delivery Service |
| `all` | Full access to all permissions |

### Security Features

- **Key Hashing:** Keys are SHA-256 hashed before storage - we never store plain keys
- **IP Whitelisting:** Optionally restrict key usage to specific IP addresses
- **Expiration Dates:** Set optional expiration dates for keys
- **Usage Tracking:** All requests are logged for security auditing

---

## Rate Limiting

API keys have configurable rate limits to prevent abuse:

| Limit Type | Default | Description |
|------------|---------|-------------|
| Per Minute | 60 requests | Requests allowed per minute |
| Per Hour | 1000 requests | Requests allowed per hour |

### Rate Limit Headers

Responses include rate limit information in headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1704067200
```

### Rate Limit Exceeded (HTTP 429)

When you exceed the rate limit:

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "You have exceeded the per minute rate limit. Please retry after 45 seconds."
}
```

The response includes a `Retry-After` header indicating seconds to wait.

---

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "message": "Optional success message"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_CODE",
  "message": "Human-readable explanation"
}
```

---

## Error Codes

### Authentication Errors (4xx)

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `NO_API_KEY` | 401 | No API key provided |
| `INVALID_API_KEY` | 401 | API key is invalid or malformed |
| `EXPIRED_API_KEY` | 401 | API key has expired |
| `INACTIVE_API_KEY` | 401 | API key has been deactivated |
| `IP_NOT_ALLOWED` | 403 | Request IP not in key's whitelist |
| `INSUFFICIENT_SCOPE` | 403 | API key lacks required permissions |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

### Resource Errors (4xx)

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `VPS_NOT_FOUND` | 404 | VPS instance doesn't exist or isn't owned by you |
| `VPS_DELETED` | 400 | VPS has already been deleted |
| `VPS_SUSPENDED` | 403 | VPS is suspended (check suspension reason) |
| `VPS_ALREADY_DELETED` | 400 | Attempted to delete already-deleted VPS |
| `PLAN_NOT_FOUND` | 400 | Invalid plan_id |
| `LOCATION_NOT_FOUND` | 400 | Invalid location_code |
| `INVALID_TEMPLATE` | 400 | Invalid template_id |
| `KEY_NOT_FOUND` | 404 | API key doesn't exist |

### Validation Errors (4xx)

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `MISSING_FIELDS` | 400 | Required fields not provided |
| `INVALID_HOSTNAME` | 400 | Hostname format invalid |
| `PASSWORD_TOO_SHORT` | 400 | Password must be at least 8 characters |
| `PASSWORD_TOO_LONG` | 400 | Password must not exceed 72 characters |
| `PASSWORD_WEAK` | 400 | Password must contain letters AND numbers |
| `INSUFFICIENT_BALANCE` | 400 | Account balance too low |

### Server Errors (5xx)

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `START_FAILED` | 500 | Failed to start VPS |
| `STOP_FAILED` | 500 | Failed to stop VPS |
| `RESTART_FAILED` | 500 | Failed to restart VPS |
| `DELETE_FAILED` | 500 | Failed to delete VPS |
| `STATUS_FAILED` | 500 | Failed to get VPS status |
| `CONSOLE_FAILED` | 500 | Failed to get console access |
| `DEPLOYMENT_FAILED` | 500 | VPS deployment failed |
| `NODE_NOT_FOUND` | 500 | Proxmox node not found |

---

## Endpoints

### General Endpoints

#### Health Check

Check if the API is operational. No authentication required.

```
GET /api/v1/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "CyberPanel Cloud API",
    "version": "1.0.0"
  }
}
```

---

#### Test Authentication

Verify your API key is working.

```
GET /api/v1/test
```

**Required Scope:** Any valid API key

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "API authentication successful!",
    "key_name": "My Production Key",
    "key_prefix": "cyp_live_3ac",
    "user_email": "user@example.com",
    "scopes": ["vps:read", "vps:write"],
    "ip_address": "203.0.113.50",
    "request_count": 142
  },
  "message": "Your API key is working correctly"
}
```

---

#### List Available Scopes

List all available permission scopes. No authentication required.

```
GET /api/v1/scopes
```

**Response:**
```json
{
  "success": true,
  "data": {
    "scopes": [
      {"scope": "vps:read", "description": "VPS - Read"},
      {"scope": "vps:write", "description": "VPS - Create/Modify"},
      {"scope": "vps:delete", "description": "VPS - Delete"},
      {"scope": "billing:read", "description": "Billing - Read"},
      {"scope": "billing:write", "description": "Billing - Add Funds"},
      {"scope": "account:read", "description": "Account - Read Info"},
      {"scope": "all", "description": "Full Access - All Permissions"}
    ]
  }
}
```

---

### Account & Billing Endpoints

#### Get Account Info

```
GET /api/v1/account
```

**Required Scope:** `account:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "email": "user@example.com",
    "full_name": "John Doe",
    "balance": "150.00",
    "status": "active",
    "two_factor_enabled": true,
    "vps_ordering_enabled": true,
    "registration_date": "2024-01-15T10:30:00Z"
  }
}
```

---

#### Get Billing Info

```
GET /api/v1/billing
```

**Required Scope:** `billing:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "balance": "150.00",
    "auto_funding": {
      "enabled": true,
      "threshold": "10.00",
      "amount": "50.00"
    },
    "recent_invoices": [
      {
        "id": 456,
        "description": "VPS Hourly Charge - my-server.example.com",
        "amount": "-0.0082",
        "type": "debit",
        "date": "2026-01-05T12:00:00Z"
      }
    ]
  }
}
```

---

#### List API Keys

List all your API keys (metadata only, not the actual keys).

```
GET /api/v1/account/api-keys
```

**Required Scope:** `account:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "api_keys": [
      {
        "id": 1,
        "name": "Production Key",
        "key_prefix": "cyp_live_3ac",
        "scopes": ["vps:read", "vps:write"],
        "is_active": true,
        "ip_whitelist": [],
        "expires_at": null,
        "last_used_at": "2026-01-05T14:30:00Z",
        "last_used_ip": "203.0.113.50",
        "request_count": 142,
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000,
        "created_at": "2025-12-01T09:00:00Z"
      }
    ],
    "total": 1
  }
}
```

---

#### Get API Key Usage Logs

```
GET /api/v1/account/api-keys/{key_id}/usage
```

**Required Scope:** `account:read`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Number of records (max 100) |
| `offset` | integer | 0 | Pagination offset |

**Response:**
```json
{
  "success": true,
  "data": {
    "key_id": 1,
    "key_name": "Production Key",
    "usage_logs": [
      {
        "endpoint": "/api/v1/vps",
        "method": "GET",
        "ip_address": "203.0.113.50",
        "response_status": 200,
        "response_time_ms": 45,
        "created_at": "2026-01-05T14:30:00Z"
      }
    ],
    "pagination": {
      "limit": 50,
      "offset": 0,
      "total": 142,
      "has_more": true
    }
  }
}
```

---

### VPS Management Endpoints

#### List VPS Instances

```
GET /api/v1/vps
```

**Required Scope:** `vps:read`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | - | Filter by status: `running`, `stopped`, `suspended` |
| `location` | string | - | Filter by location code: `la`, `de`, `eu` |
| `limit` | integer | 50 | Number of results (max 100) |
| `offset` | integer | 0 | Pagination offset |

**Response:**
```json
{
  "success": true,
  "data": {
    "instances": [
      {
        "id": 45,
        "vmid": 281,
        "name": "my-server.example.com",
        "status": "running",
        "ip_address": "74.81.40.145",
        "is_suspended": false,
        "created_at": "2026-01-05T10:00:00Z"
      }
    ],
    "pagination": {
      "total": 3,
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

---

#### Get VPS Details

```
GET /api/v1/vps/{id}
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 45,
    "vmid": 281,
    "name": "my-server.example.com",
    "status": "running",
    "ip_address": "74.81.40.145",
    "is_suspended": false,
    "created_at": "2026-01-05T10:00:00Z",
    "updated_at": "2026-01-05T14:30:00Z",
    "plan": {
      "id": 1,
      "name": "Starter",
      "cpu_cores": 1,
      "ram_mb": 1024,
      "disk_gb": 25,
      "bandwidth_gb": 1000,
      "price": "6.00"
    },
    "location": {
      "code": "la",
      "name": "Los Angeles, USA"
    },
    "server": {
      "hostname": "lax-power.cyberpersons.com"
    },
    "billing": {
      "hourly_rate": "0.0082",
      "billing_start": "2026-01-05T10:00:00Z",
      "last_billed": "2026-01-05T14:00:00Z"
    }
  }
}
```

---

#### Get VPS Dashboard Summary

```
GET /api/v1/vps/summary
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "total_instances": 3,
    "running": 2,
    "stopped": 1,
    "suspended": 0,
    "total_monthly_cost": "18.00",
    "locations": {
      "la": 2,
      "de": 1
    }
  }
}
```

---

#### Get VPS Live Status

Get real-time metrics from Proxmox.

```
GET /api/v1/vps/{id}/status
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "vps_id": 45,
    "vmid": 281,
    "name": "my-server.example.com",
    "status": "running",
    "qmpstatus": "running",
    "cpu": {
      "usage_percent": 2.5,
      "cores": 1
    },
    "memory": {
      "used_bytes": 536870912,
      "total_bytes": 1073741824,
      "usage_percent": 50.0
    },
    "disk": {
      "read_bytes": 1234567890,
      "write_bytes": 987654321
    },
    "network": {
      "in_bytes": 5678901234,
      "out_bytes": 1234567890
    },
    "uptime_seconds": 86400,
    "pid": 12345
  }
}
```

---

#### List VPS Plans

```
GET /api/v1/vps/plans
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "plans": [
      {
        "id": 1,
        "name": "Starter",
        "cpu_cores": 1,
        "ram_mb": 1024,
        "disk_gb": 25,
        "bandwidth_gb": 1000,
        "monthly_price": "6.00",
        "price_hourly": "0.0082"
      },
      {
        "id": 2,
        "name": "Basic",
        "cpu_cores": 2,
        "ram_mb": 2048,
        "disk_gb": 50,
        "bandwidth_gb": 2000,
        "monthly_price": "12.00",
        "price_hourly": "0.0164"
      }
    ]
  }
}
```

---

#### List Locations

```
GET /api/v1/vps/locations
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "locations": [
      {
        "code": "la",
        "name": "Los Angeles, USA",
        "country": "US",
        "available_ips": 15,
        "is_available": true
      },
      {
        "code": "de",
        "name": "Falkenstein, Germany",
        "country": "DE",
        "available_ips": 8,
        "is_available": true
      }
    ]
  }
}
```

---

#### List OS Templates

```
GET /api/v1/vps/templates
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "templates": [
      {"id": "101", "name": "CyberPanel", "os": "AlmaLinux 8", "description": "CyberPanel pre-installed with OpenLiteSpeed"},
      {"id": "9000", "name": "Ubuntu 22.04", "os": "Ubuntu 22.04 LTS", "description": "Clean Ubuntu 22.04 LTS installation"},
      {"id": "9022", "name": "Ubuntu 24.04", "os": "Ubuntu 24.04 LTS", "description": "Clean Ubuntu 24.04 LTS installation"},
      {"id": "9010", "name": "Debian 12", "os": "Debian 12", "description": "Clean Debian 12 installation"},
      {"id": "9001", "name": "AlmaLinux 8", "os": "AlmaLinux 8", "description": "Clean AlmaLinux 8 installation"},
      {"id": "9008", "name": "AlmaLinux 9", "os": "AlmaLinux 9", "description": "Clean AlmaLinux 9 installation"},
      {"id": "9125", "name": "Windows Server 2022", "os": "Windows Server 2022", "description": "Windows Server 2022 (requires $20 min balance)"}
    ]
  }
}
```

---

### VPS Action Endpoints

#### Start VPS

```
POST /api/v1/vps/{id}/start
```

**Required Scope:** `vps:write`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 45,
    "vmid": 281,
    "name": "my-server.example.com",
    "status": "running",
    "ip_address": "74.81.40.145"
  },
  "message": "VPS started successfully"
}
```

---

#### Stop VPS

```
POST /api/v1/vps/{id}/stop
```

**Required Scope:** `vps:write`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 45,
    "vmid": 281,
    "name": "my-server.example.com",
    "status": "stopped",
    "ip_address": "74.81.40.145"
  },
  "message": "VPS stopped successfully"
}
```

---

#### Restart VPS

```
POST /api/v1/vps/{id}/restart
```

**Required Scope:** `vps:write`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 45,
    "vmid": 281,
    "name": "my-server.example.com",
    "status": "running",
    "ip_address": "74.81.40.145"
  },
  "message": "VPS restarted successfully"
}
```

---

#### Delete VPS

**WARNING:** This permanently deletes the VPS and all data. This action cannot be undone.

```
POST /api/v1/vps/{id}/delete
```

**Required Scope:** `vps:write`

**Response:**
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "vps_id": 45,
    "name": "my-server.example.com",
    "vmid": 281
  },
  "message": "VPS \"my-server.example.com\" deleted successfully"
}
```

---

#### Get Console Access

Get noVNC console URL for browser-based access.

```
GET /api/v1/vps/{id}/console
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "vps_id": 45,
    "console_url": "https://lax-power.cyberpersons.com:8006/?console=kvm&novnc=1&vmid=281&node=lax-power",
    "type": "novnc",
    "expires_in_seconds": 300
  },
  "message": "Console URL generated. Valid for 5 minutes."
}
```

---

### VPS Creation Endpoints

#### Create VPS

```
POST /api/v1/vps/create
```

**Required Scope:** `vps:write`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hostname` | string | Yes | FQDN hostname (e.g., `my-server.example.com`) |
| `plan_id` | integer | Yes | Plan ID from `/vps/plans` |
| `location_code` | string | Yes | Location code from `/vps/locations` |
| `template_id` | string | Yes | Template ID from `/vps/templates` |
| `root_password` | string | Yes | Root password (8-72 chars, must have letters AND numbers) |
| `ssh_key` | string | No | SSH public key for root access |
| `webhook_url` | string | No | URL to notify when deployment completes/fails |
| `webhook_secret` | string | No | Secret for webhook signature verification |

**Example Request:**
```json
{
  "hostname": "my-server.example.com",
  "plan_id": 1,
  "location_code": "la",
  "template_id": "9000",
  "root_password": "SecurePass123",
  "ssh_key": "ssh-rsa AAAAB3NzaC1yc2E...",
  "webhook_url": "https://your-server.com/webhook"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "vps_id": 46,
    "name": "my-server.example.com",
    "status": "deploying",
    "ip_address": "74.81.40.146",
    "plan": {
      "id": 1,
      "name": "Starter",
      "price": "6.00"
    },
    "location": "la",
    "template": "9000",
    "deployment_url": "/api/v1/vps/46/deployment",
    "estimated_time_seconds": 180,
    "webhook_configured": true
  },
  "message": "VPS deployment started. Use the deployment endpoint to check progress."
}
```

---

#### Get Deployment Status

Poll this endpoint to track VPS deployment progress.

```
GET /api/v1/vps/{id}/deployment
```

**Required Scope:** `vps:read`

**Response (In Progress):**
```json
{
  "success": true,
  "data": {
    "vps_id": 46,
    "deployment_status": "in_progress",
    "vps_status": "deploying",
    "current_task": "configure_network",
    "progress_percent": 70,
    "tasks": [
      {"name": "validate_resources", "status": "completed", "order": 1},
      {"name": "allocate_ip", "status": "completed", "order": 2},
      {"name": "create_vm", "status": "completed", "order": 3},
      {"name": "configure_hardware", "status": "completed", "order": 4},
      {"name": "apply_cloud_init", "status": "completed", "order": 5},
      {"name": "start_vm", "status": "completed", "order": 6},
      {"name": "configure_network", "status": "in_progress", "order": 7},
      {"name": "wait_for_guest_agent", "status": "pending", "order": 8},
      {"name": "verify_connectivity", "status": "pending", "order": 9},
      {"name": "finalize", "status": "pending", "order": 10}
    ],
    "tasks_completed": 6,
    "tasks_total": 10,
    "started_at": "2026-01-05T15:00:00Z",
    "is_ready": false
  }
}
```

**Response (Completed):**
```json
{
  "success": true,
  "data": {
    "vps_id": 46,
    "deployment_status": "completed",
    "vps_status": "running",
    "current_task": null,
    "progress_percent": 100,
    "tasks_completed": 10,
    "tasks_total": 10,
    "started_at": "2026-01-05T15:00:00Z",
    "completed_at": "2026-01-05T15:03:00Z",
    "is_ready": true,
    "access_info": {
      "ip_address": "74.81.40.146",
      "ssh_port": 22,
      "ssh_user": "root"
    }
  },
  "message": "VPS deployment completed successfully"
}
```

---

### VPS Snapshots

#### List Snapshots

```
GET /api/v1/vps/{id}/snapshots
```

**Required Scope:** `vps:read`

**Response:**
```json
{
  "success": true,
  "data": {
    "vps_id": 45,
    "snapshots": [
      {
        "name": "pre-upgrade-snapshot",
        "description": "Before system upgrade",
        "created_at": "2026-01-04T10:00:00Z",
        "vmstate": false
      }
    ]
  }
}
```

---

#### Create Snapshot

```
POST /api/v1/vps/{id}/snapshots/create
```

**Required Scope:** `vps:write`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Snapshot name (alphanumeric, underscores) |
| `description` | string | No | Description of the snapshot |
| `include_ram` | boolean | No | Include RAM state (default: false) |

**Example Request:**
```json
{
  "name": "pre_upgrade_snapshot",
  "description": "Before upgrading to Ubuntu 24.04",
  "include_ram": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "vps_id": 45,
    "snapshot": {
      "name": "pre_upgrade_snapshot",
      "description": "Before upgrading to Ubuntu 24.04",
      "created_at": "2026-01-05T16:00:00Z"
    }
  },
  "message": "Snapshot created successfully"
}
```

---

## Code Examples

### Python

```python
import requests

API_KEY = "cyp_live_your_api_key_here"
BASE_URL = "https://platform.cyberpersons.com/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# List all VPS instances
response = requests.get(f"{BASE_URL}/vps", headers=headers)
instances = response.json()["data"]["instances"]
for vps in instances:
    print(f"{vps['name']}: {vps['status']} ({vps['ip_address']})")

# Create a new VPS
new_vps = requests.post(f"{BASE_URL}/vps/create", headers=headers, json={
    "hostname": "my-server.example.com",
    "plan_id": 1,
    "location_code": "la",
    "template_id": "9000",
    "root_password": "SecurePass123"
})
vps_id = new_vps.json()["data"]["vps_id"]

# Poll deployment status
import time
while True:
    status = requests.get(f"{BASE_URL}/vps/{vps_id}/deployment", headers=headers)
    data = status.json()["data"]
    print(f"Progress: {data['progress_percent']}% - {data['current_task']}")
    if data["is_ready"]:
        print(f"VPS ready at {data['access_info']['ip_address']}")
        break
    time.sleep(10)
```

### JavaScript (Node.js)

```javascript
const API_KEY = "cyp_live_your_api_key_here";
const BASE_URL = "https://platform.cyberpersons.com/api/v1";

const headers = {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json"
};

// List all VPS instances
const response = await fetch(`${BASE_URL}/vps`, { headers });
const { data } = await response.json();
data.instances.forEach(vps => {
    console.log(`${vps.name}: ${vps.status} (${vps.ip_address})`);
});

// Create a new VPS
const createResponse = await fetch(`${BASE_URL}/vps/create`, {
    method: "POST",
    headers,
    body: JSON.stringify({
        hostname: "my-server.example.com",
        plan_id: 1,
        location_code: "la",
        template_id: "9000",
        root_password: "SecurePass123"
    })
});
const { data: vpsData } = await createResponse.json();
console.log(`VPS ${vpsData.vps_id} deployment started`);
```

### cURL

```bash
# Test authentication
curl -X GET "https://platform.cyberpersons.com/api/v1/test" \
  -H "Authorization: Bearer cyp_live_your_api_key_here"

# List VPS instances
curl -X GET "https://platform.cyberpersons.com/api/v1/vps" \
  -H "Authorization: Bearer cyp_live_your_api_key_here"

# Create VPS
curl -X POST "https://platform.cyberpersons.com/api/v1/vps/create" \
  -H "Authorization: Bearer cyp_live_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "my-server.example.com",
    "plan_id": 1,
    "location_code": "la",
    "template_id": "9000",
    "root_password": "SecurePass123"
  }'

# Stop VPS
curl -X POST "https://platform.cyberpersons.com/api/v1/vps/45/stop" \
  -H "Authorization: Bearer cyp_live_your_api_key_here"

# Delete VPS (WARNING: Permanent!)
curl -X POST "https://platform.cyberpersons.com/api/v1/vps/45/delete" \
  -H "Authorization: Bearer cyp_live_your_api_key_here"
```

### PHP

```php
<?php
$api_key = "cyp_live_your_api_key_here";
$base_url = "https://platform.cyberpersons.com/api/v1";

function api_request($method, $endpoint, $data = null) {
    global $api_key, $base_url;

    $ch = curl_init("$base_url$endpoint");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: Bearer $api_key",
        "Content-Type: application/json"
    ]);

    if ($method === "POST") {
        curl_setopt($ch, CURLOPT_POST, true);
        if ($data) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        }
    }

    $response = curl_exec($ch);
    curl_close($ch);
    return json_decode($response, true);
}

// List VPS instances
$instances = api_request("GET", "/vps");
foreach ($instances["data"]["instances"] as $vps) {
    echo "{$vps['name']}: {$vps['status']} ({$vps['ip_address']})\n";
}

// Create VPS
$new_vps = api_request("POST", "/vps/create", [
    "hostname" => "my-server.example.com",
    "plan_id" => 1,
    "location_code" => "la",
    "template_id" => "9000",
    "root_password" => "SecurePass123"
]);
echo "Created VPS ID: " . $new_vps["data"]["vps_id"];
?>
```

---

## Webhook Notifications

When creating a VPS, you can specify a `webhook_url` to receive notifications when deployment completes or fails.

### Webhook Payload

```json
{
  "event": "vps.deployment.completed",
  "timestamp": "2026-01-05T15:03:00Z",
  "data": {
    "vps_id": 46,
    "name": "my-server.example.com",
    "status": "running",
    "ip_address": "74.81.40.146",
    "deployment_time_seconds": 180
  }
}
```

### Event Types

| Event | Description |
|-------|-------------|
| `vps.deployment.completed` | VPS deployment finished successfully |
| `vps.deployment.failed` | VPS deployment failed |

### Webhook Security

If you provide a `webhook_secret`, the webhook request will include a signature header:

```
X-Webhook-Signature: sha256=<hmac_signature>
```

Verify the signature by computing HMAC-SHA256 of the request body using your secret.

---

## Support

- **Documentation:** https://platform.cyberpersons.com/api-keys/
- **Support Tickets:** https://platform.cyberpersons.com/support/
- **Email:** help@cyberpanel.net

---

## Changelog

### v1.0.0 (January 2026)
- Initial API release
- VPS management endpoints (list, create, start, stop, restart, delete)
- Account and billing endpoints
- Snapshot management
- Webhook notifications for deployments