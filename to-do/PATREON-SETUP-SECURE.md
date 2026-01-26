# Secure Patreon Configuration Setup

## ⚠️ SECURITY WARNING

**NEVER commit Patreon secrets to the repository!**

All secrets must be configured via environment variables on the production server.

## Setup Instructions

### 1. Get Your Patreon Credentials

From your Patreon Developer Dashboard:
- Client ID
- Client Secret
- Membership Tier ID (e.g., `27789984`)
- Creator Access Token (optional, for server-side verification)
- Creator Refresh Token (optional)

### 2. Configure Environment Variables

#### Option A: Systemd Service (Recommended)

Edit `/etc/systemd/system/lscpd.service`:

```ini
[Service]
Environment="PATREON_CLIENT_ID=your_client_id"
Environment="PATREON_CLIENT_SECRET=your_client_secret"
Environment="PATREON_MEMBERSHIP_TIER_ID=your_tier_id"
Environment="PATREON_CREATOR_ACCESS_TOKEN=your_access_token"
Environment="PATREON_CREATOR_REFRESH_TOKEN=your_refresh_token"
```

Then reload and restart:
```bash
systemctl daemon-reload
systemctl restart lscpd
```

#### Option B: /etc/environment

Add to `/etc/environment`:
```bash
PATREON_CLIENT_ID=your_client_id
PATREON_CLIENT_SECRET=your_client_secret
PATREON_MEMBERSHIP_TIER_ID=your_tier_id
PATREON_CREATOR_ACCESS_TOKEN=your_access_token
PATREON_CREATOR_REFRESH_TOKEN=your_refresh_token
```

#### Option C: Secure Config File (Not in Repo)

Create `/usr/local/CyberCP/patreon_config.py` (add to .gitignore):

```python
# Patreon Configuration - DO NOT COMMIT TO REPOSITORY
PATREON_CLIENT_ID = 'your_client_id'
PATREON_CLIENT_SECRET = 'your_client_secret'
PATREON_MEMBERSHIP_TIER_ID = 'your_tier_id'
PATREON_CREATOR_ACCESS_TOKEN = 'your_access_token'
PATREON_CREATOR_REFRESH_TOKEN = 'your_refresh_token'
```

Then import in settings.py:
```python
try:
    from .patreon_config import *
except ImportError:
    pass  # Use environment variables instead
```

### 3. Verify Configuration

Test that secrets are loaded:
```bash
python3 -c "
import os
print('Client ID:', 'SET' if os.environ.get('PATREON_CLIENT_ID') else 'NOT SET')
print('Client Secret:', 'SET' if os.environ.get('PATREON_CLIENT_SECRET') else 'NOT SET')
print('Tier ID:', os.environ.get('PATREON_MEMBERSHIP_TIER_ID', 'NOT SET'))
"
```

### 4. Security Checklist

- [ ] Secrets removed from repository
- [ ] Environment variables set on production server
- [ ] `/usr/local/CyberCP/patreon_config.py` added to .gitignore (if used)
- [ ] CyberPanel service restarted
- [ ] Configuration verified working

## For Plugin Developers

When creating paid plugins:

1. **Never hardcode secrets** in plugin code
2. **Use environment variables** or Django settings
3. **Document required variables** in README
4. **Provide example** with placeholder values only

Example meta.xml:
```xml
<paid>true</paid>
<patreon_tier>Your Tier Name</patreon_tier>
<patreon_url>https://www.patreon.com/c/yourname/membership</patreon_url>
```

## Troubleshooting

If membership checks fail:
1. Verify environment variables are set: `env | grep PATREON`
2. Check CyberPanel logs: `/home/lscp/logs/error.log`
3. Verify tier ID matches your Patreon tier
4. Ensure user has authorized OAuth access
