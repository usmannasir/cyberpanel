# Patreon Configuration for CyberPanel Paid Plugins

## Configuration Complete

Patreon credentials have been configured in CyberPanel settings.

### Credentials Configuration

**SECURITY WARNING**: Never commit secrets to the repository!

Set these via environment variables:

```bash
export PATREON_CLIENT_ID="your_client_id_here"
export PATREON_CLIENT_SECRET="your_client_secret_here"
export PATREON_MEMBERSHIP_TIER_ID="your_tier_id_here"
export PATREON_CREATOR_ACCESS_TOKEN="your_access_token_here"
export PATREON_CREATOR_REFRESH_TOKEN="your_refresh_token_here"
```

Or add to `/etc/environment` or systemd service file.

### Location

Credentials are stored in:
- `/usr/local/CyberCP/CyberCP/settings.py` (or `/home/cyberpanel-repo/CyberCP/settings.py`)

### How It Works

1. Users install paid plugins (no subscription required)
2. When accessing the plugin, system checks for Patreon membership
3. If user has active subscription to tier `27789984`, access is granted
4. If not, subscription required page is shown

### Testing

To test the configuration:

1. Install the `premiumPlugin` example plugin
2. Try accessing it without subscription (should show subscription page)
3. Subscribe to Patreon tier "CyberPanel Paid Plugin" (ID: 27789984)
4. Authorize CyberPanel to check membership
5. Access plugin again (should work)

### Membership Verification

The system checks for:
- Tier ID: `27789984`
- Tier Name: "CyberPanel Paid Plugin" (fallback)
- Active patron status
- Currently entitled amount > 0

### Notes

- Membership checks are cached for 5 minutes
- Users must authorize CyberPanel via OAuth to check membership
- Creator access token can be used for server-side verification

