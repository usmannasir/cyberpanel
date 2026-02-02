# Remote Verification Setup

## Overview

This version of the plugin uses **remote verification** - all Patreon API calls happen on YOUR server, not the user's server.

## Benefits

✅ **No secrets in plugin** - Users can see all plugin code, but no credentials  
✅ **Secure** - All Patreon API credentials stay on your server  
✅ **Centralized** - You control access, can revoke, update logic, etc.  
✅ **Public code** - Plugin code can be open source  

## Architecture

```
User's Server                    Your Server              Patreon API
     |                                |                        |
     |-- Verify Request ------------> |                        |
     |                                |-- Check Membership --> |
     |                                |<-- Membership Status - |
     |<-- Access Granted/Denied ----- |                        |
```

## Setup

### 1. Deploy Verification API

Deploy the verification endpoint to your server:
- File: `/home/newstargeted.com/api.newstargeted.com/modules/patreon/verify-membership.php`
- URL: `https://api.newstargeted.com/api/verify-patreon-membership`

### 2. Configure Your Server

Add Patreon credentials to your server's `config.php`:

```php
define('PATREON_CLIENT_ID', 'your_client_id');
define('PATREON_CLIENT_SECRET', 'your_client_secret');
define('PATREON_CREATOR_ACCESS_TOKEN', 'your_access_token');
```

### 3. Update Plugin

Replace `views.py` with `views_remote.py`:

```bash
mv views.py views_local.py  # Backup local version
mv views_remote.py views.py  # Use remote version
```

### 4. Configure Plugin URL

Update `REMOTE_VERIFICATION_URL` in `views.py` to point to your server:

```python
REMOTE_VERIFICATION_URL = 'https://api.newstargeted.com/api/verify-patreon-membership'
```

## Security Features

- **Rate limiting** - Prevents abuse (60 requests/hour per IP)
- **HTTPS only** - All communication encrypted
- **No secrets** - Plugin only makes API calls
- **Caching** - Reduces Patreon API calls (5 min cache)

## Testing

1. Install plugin on user's server
2. Try accessing plugin (should show subscription required)
3. Subscribe to Patreon tier
4. Access plugin again (should work)

## Migration from Local Verification

If you were using local verification:

1. Keep `views_local.py` as backup
2. Use `views_remote.py` as `views.py`
3. Deploy verification API to your server
4. Update plugin URL in code
