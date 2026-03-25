# CyberMail Email Delivery — Technical Reference

**Module**: `emailDelivery`
**Platform API Base**: `https://platform.cyberpersons.com/email/cp/`
**Last Updated**: 2026-03-06

---

## Architecture

```
CyberPanel UI (AngularJS)
    |
    v
Django Views (emailDelivery/views.py)
    |
    v
EmailDeliveryManager (emailDelivery/emailDeliveryManager.py)
    |
    ├──> CyberMail Platform API (HTTPS POST, Bearer auth)
    ├──> PowerDNS (via dnsUtilities.DNS.createDNSRecord)
    └──> Postfix (via mailUtilities.py subprocess as root)
```

### Design Patterns

- **Manager Class Pattern**: All business logic in `EmailDeliveryManager`, views are thin wrappers
- **Per-User API Keys**: Each CyberPanel admin gets their own platform API key (no server-level key)
- **AngularJS SPA**: Single template with conditional rendering based on `isConnected` state
- **Subprocess for Root Operations**: Postfix relay config runs via `ProcessUtilities.outputExecutioner()` which executes as root

---

## Database Models

### CyberMailAccount (`cybermail_accounts`)

```python
class CyberMailAccount(models.Model):
    admin              = OneToOneField(Administrator, CASCADE)  # 1:1 with admin
    platform_account_id = IntegerField(null=True)               # Platform's account ID
    api_key            = CharField(max_length=255)               # Per-user Bearer token
    email              = CharField(max_length=255)               # Platform email
    plan_name          = CharField(default='Free')               # Display name
    plan_slug          = CharField(default='free')               # free/starter/professional/enterprise
    emails_per_month   = IntegerField(default=15000)             # Plan limit
    is_connected       = BooleanField(default=False)             # Active connection
    relay_enabled      = BooleanField(default=False)             # Postfix relay active
    smtp_credential_id = IntegerField(null=True)                 # Active relay credential
    smtp_username      = CharField(max_length=255)               # Relay SMTP username
    smtp_host          = CharField(default='mail.cyberpersons.com')
    smtp_port          = IntegerField(default=587)
    created_at         = DateTimeField(auto_now_add=True)
    updated_at         = DateTimeField(auto_now=True)
```

### CyberMailDomain (`cybermail_domains`)

```python
class CyberMailDomain(models.Model):
    account            = ForeignKey(CyberMailAccount, CASCADE)
    domain             = CharField(max_length=255)
    platform_domain_id = IntegerField(null=True)
    status             = CharField(default='pending')  # pending/verified
    spf_verified       = BooleanField(default=False)
    dkim_verified      = BooleanField(default=False)
    dmarc_verified     = BooleanField(default=False)
    dns_configured     = BooleanField(default=False)   # Auto-configured in PowerDNS
    created_at         = DateTimeField(auto_now_add=True)
```

---

## API Endpoints (CyberPanel Internal)

All endpoints are POST, require authenticated CyberPanel session, and return JSON.

### Account Management

| Endpoint | Method | Purpose | Request Body |
|----------|--------|---------|-------------|
| `/emailDelivery/` | GET | Render page | — |
| `/emailDelivery/connect/` | POST | Register/connect account | `{email, password}` |
| `/emailDelivery/status/` | POST | Get account status + sync domains | — |
| `/emailDelivery/disconnect/` | POST | Disconnect account, cleanup | — |

### Domain Management

| Endpoint | Method | Purpose | Request Body |
|----------|--------|---------|-------------|
| `/emailDelivery/domains/add/` | POST | Add sending domain | `{domain}` |
| `/emailDelivery/domains/list/` | POST | List domains with status | — |
| `/emailDelivery/domains/verify/` | POST | Verify DNS records | `{domain}` |
| `/emailDelivery/domains/dns-records/` | POST | Get required DNS records | `{domain}` |
| `/emailDelivery/domains/auto-configure-dns/` | POST | Auto-add DNS to PowerDNS | `{domain}` |
| `/emailDelivery/domains/remove/` | POST | Remove sending domain | `{domain}` |

### SMTP Credentials

| Endpoint | Method | Purpose | Request Body |
|----------|--------|---------|-------------|
| `/emailDelivery/smtp/create/` | POST | Create SMTP credential | `{description}` |
| `/emailDelivery/smtp/list/` | POST | List all credentials | — |
| `/emailDelivery/smtp/rotate/` | POST | Rotate credential password | `{credential_id}` |
| `/emailDelivery/smtp/delete/` | POST | Delete credential | `{credential_id}` |

### Relay

| Endpoint | Method | Purpose | Request Body |
|----------|--------|---------|-------------|
| `/emailDelivery/relay/enable/` | POST | Enable Postfix SMTP relay | — |
| `/emailDelivery/relay/disable/` | POST | Disable Postfix SMTP relay | — |

### Analytics

| Endpoint | Method | Purpose | Request Body |
|----------|--------|---------|-------------|
| `/emailDelivery/stats/` | POST | Aggregate sending stats | — |
| `/emailDelivery/stats/domains/` | POST | Per-domain stats | — |
| `/emailDelivery/logs/` | POST | Paginated delivery logs | `{page, per_page, status, from_domain, days}` |

### Health

| Endpoint | Method | Purpose | Request Body |
|----------|--------|---------|-------------|
| `/emailDelivery/health/` | POST | Platform health check | — |

---

## Platform API Mapping

Each CyberPanel endpoint maps to a platform API call:

| CyberPanel Method | Platform Endpoint | Auth | Notes |
|-------------------|-------------------|------|-------|
| `connect()` | `api/register/` | None (public) | Returns `api_key` for future calls |
| `getStatus()` | `api/account/` + `api/domains/list/` | Bearer | Syncs plan + domains |
| `addDomain()` | `api/domains/add/` + `api/domains/dns-records/` | Bearer | Auto-configures DNS |
| `listDomains()` | `api/domains/list/` | Bearer | Syncs verification status |
| `verifyDomain()` | `api/domains/verify/` | Bearer | Returns spf/dkim/dmarc booleans |
| `getDnsRecords()` | `api/domains/dns-records/` | Bearer | Returns required records |
| `removeDomain()` | `api/domains/remove/` | Bearer | — |
| `createSmtpCredential()` | `api/smtp/create/` | Bearer | Returns one-time password |
| `listSmtpCredentials()` | `api/smtp/list/` | Bearer | Normalizes `id` → `credential_id` |
| `rotateSmtpPassword()` | `api/smtp/rotate/` | Bearer | Normalizes `new_password` → `password` |
| `deleteSmtpCredential()` | `api/smtp/delete/` | Bearer | Clears relay if active credential |
| `enableRelay()` | `api/smtp/create/` or `api/smtp/rotate/` | Bearer | Then configures Postfix |
| `getStats()` | `api/stats/` | Bearer | — |
| `getDomainStats()` | `api/stats/domains/` | Bearer | Converts dict → array |
| `getLogs()` | `api/logs/` | Bearer | Maps field names for JS |
| `checkStatus()` | `api/health/` | None | — |

### API Response Normalization

The manager normalizes platform responses for frontend compatibility:

| Platform Field | CyberPanel Field | Method |
|---------------|-----------------|--------|
| `id` (credential) | `credential_id` | `listSmtpCredentials()` |
| `new_password` | `password` | `rotateSmtpPassword()` |
| `queued_at` | `date` | `getLogs()` |
| `from_email` | `from` | `getLogs()` |
| `to_email` | `to` | `getLogs()` |
| `domains` (dict) | `domains` (array) | `getDomainStats()` |

---

## Connection Flow

```
1. User clicks "Get Started Free"
2. JS sends POST /emailDelivery/connect/ {email, password}
3. Manager calls platform POST api/register/ (no auth)
4. Platform returns {success, data: {api_key, account_id, plan_name, ...}}
5. Manager creates/updates CyberMailAccount with api_key
6. All subsequent calls use Authorization: Bearer <api_key>
```

### Reconnection Behavior

When connecting with an existing `CyberMailAccount` record:
- Updates email, api_key, platform_account_id, plan info
- Resets: `smtp_credential_id=None`, `smtp_username=''`, `relay_enabled=False`
- Deletes all local `CyberMailDomain` records (stale data)

### Disconnection Behavior

- Disables Postfix relay if active
- Clears: `is_connected`, `relay_enabled`, `api_key`, `smtp_credential_id`, `smtp_username`, `platform_account_id`
- Deletes all local domain records
- Does NOT delete the platform account

---

## DNS Auto-Configuration

### Flow

```
1. User adds domain via addDomain()
2. Manager calls platform api/domains/add/
3. Manager calls _autoConfigureDnsForDomain()
4.   → Finds domain zone in PowerDNS (dns.models.Domains)
5.   → Calls platform api/domains/dns-records/ to get required records
6.   → For each record: DNS.createDNSRecord(zone, host, type, value, priority, ttl)
7.   → Marks CyberMailDomain.dns_configured = True
8. User clicks "Verify" → calls platform api/domains/verify/
9. Platform checks DNS → returns spf/dkim/dmarc booleans
```

### DNS Record Types Created

| Record | Type | Example Value |
|--------|------|---------------|
| SPF | TXT | `v=spf1 include:spf.cyberpersons.com ~all` |
| DKIM | TXT | `v=DKIM1; k=rsa; p=MIIBIjANBg...` |
| DMARC | TXT | `v=DMARC1; p=quarantine; rua=mailto:dmarc@...` |

### When Auto-Configuration Fails

- Domain not in PowerDNS → returns message to add records manually
- Platform API unreachable → returns connection error
- Individual record creation fails → logged, continues with remaining records

---

## SMTP Relay Configuration

### Enable Relay Flow

```
1. Manager checks account.smtp_credential_id
2. If no credential:
   → POST api/smtp/create/ {email, description: "CyberPanel Relay"}
   → Stores credential_id, username, gets one-time password
3. If credential exists:
   → POST api/smtp/rotate/ {email, credential_id}
   → Gets new_password
4. Calls subprocess: python mailUtilities.py configureRelayHost
   --smtpHost mail.cyberpersons.com --smtpPort 587
   --smtpUser <username> --smtpPassword <password>
5. mailUtilities.py (runs as root):
   → Writes /etc/postfix/main.cf relay lines
   → Writes /etc/postfix/sasl_passwd
   → chmod 600, postmap, systemctl reload postfix
6. Sets account.relay_enabled = True
```

### Postfix Configuration Applied

```ini
# Added to /etc/postfix/main.cf
relayhost = [mail.cyberpersons.com]:587
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_tls_security_level = encrypt
```

```
# /etc/postfix/sasl_passwd
[mail.cyberpersons.com]:587 username:password
```

### Disable Relay

```
1. Calls subprocess: python mailUtilities.py removeRelayHost
2. mailUtilities.py removes relay lines from main.cf
3. Restores smtp_tls_security_level = may
4. Deletes sasl_passwd and .db files
5. Reloads Postfix
6. Sets account.relay_enabled = False
```

### Output Parsing

The subprocess prints `1,None` on success. The manager checks for `'1,None' in output` (not `startswith`) because Python SyntaxWarnings may appear before the success output.

---

## Frontend Architecture

### Template: `emailDelivery/templates/emailDelivery/index.html`

- Extends `baseTemplate/index.html`
- Uses AngularJS 1.6.5 with `{$ $}` interpolation (not `{{ }}`)
- CSS classes use `ed-` prefix
- Two views controlled by Django `{% if isConnected %}`:
  - Marketing landing page (not connected)
  - Dashboard with tabs (connected)

### Controller: `emailDeliveryCtrl`

Located in `emailDelivery/static/emailDelivery/emailDelivery.js`

Key state variables:
```javascript
$scope.isConnected      // Boolean — dashboard vs marketing view
$scope.activeTab        // 'domains' | 'smtp' | 'relay' | 'logs' | 'stats'
$scope.account          // Account object from getStatus
$scope.domains          // Array of domain objects
$scope.smtpCredentials  // Array of SMTP credential objects
$scope.stats            // Aggregate stats object
$scope.domainStats      // Array of per-domain stats
$scope.logs             // Array of log entries
$scope.logFilters       // {status, from_domain, days}
$scope.logsPage         // Current log page number
$scope.logsTotalPages   // Total log pages
```

### Modal Handling

Bootstrap 3 modals are placed OUTSIDE the `ng-controller` div (AngularJS scope limitation). Modal forms use jQuery + `onclick` handlers that call standalone functions (`cmConnect()`, `cmAddDomain()`, etc.) which make AJAX calls with `$.ajax()` and CSRF tokens.

### CSRF Token

All AJAX calls include the CSRF token from cookies:
```javascript
function getCookie(name) {
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length == 2) return parts.pop().split(";").shift();
}
```

---

## Error Handling

### API Errors
- Connection timeout: 30-second timeout on all platform API calls
- Connection errors: caught and returned as `{success: false, error: "Could not connect..."}`
- Missing API key: `{success: false, error: "No API key found. Please reconnect your account."}`

### Logging
All errors logged via `CyberCPLogFileWriter.writeToFile()` with format:
```
[EmailDeliveryManager.<method>] Error: <message>
```

Log file: `/home/cyberpanel/error-logs.txt`

---

## Banner System

Promotional banners appear on 6 email-related pages:

| Page | Template Path |
|------|--------------|
| Mail Functions | `mailServer/templates/mailServer/index.html` |
| Create Email | `mailServer/templates/mailServer/createEmailAccount.html` |
| DKIM Manager | `mailServer/templates/mailServer/dkimManager.html` |
| Webmail | `webmail/templates/webmail/index.html` |
| Email Premium | `emailPremium/templates/emailPremium/emailPage.html` |
| Email Marketing | `emailMarketing/templates/emailMarketing/emailMarketing.html` |

### Banner Behavior
- Hidden by default (`display:none`)
- Shown via JS if `cybermail_dismiss=1` cookie is NOT present
- Dismiss button sets cookie with 7-day expiry (`max-age=604800`)
- Links to `/emailDelivery/`

---

## File Structure

```
emailDelivery/
├── __init__.py
├── apps.py                          # Django app config
├── models.py                        # CyberMailAccount, CyberMailDomain
├── views.py                         # Thin view wrappers (18 endpoints)
├── urls.py                          # URL patterns
├── emailDeliveryManager.py          # Core business logic (~743 lines)
├── migrations/
│   └── __init__.py
├── static/
│   └── emailDelivery/
│       └── emailDelivery.js         # AngularJS controller
└── templates/
    └── emailDelivery/
        └── index.html               # SPA template (marketing + dashboard)
```

### Related Files

| File | Modifications |
|------|--------------|
| `CyberCP/settings.py` | Added `'emailDelivery'` to `INSTALLED_APPS` |
| `CyberCP/urls.py` | Added `path('emailDelivery/', include('emailDelivery.urls'))` |
| `plogical/mailUtilities.py` | Added `configureRelayHost()` and `removeRelayHost()` static methods + argparse args |
