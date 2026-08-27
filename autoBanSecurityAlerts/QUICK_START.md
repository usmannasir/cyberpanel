# Auto Ban Security Alerts Plugin - Quick Start Guide

## ✅ Installation Complete!

The plugin has been successfully installed and configured.

## Access the Plugin

**URL:** https://cyberpanel.newstargeted.com:8090/plugins/autoBanSecurityAlerts/settings/

Or navigate via CyberPanel:
1. Login to CyberPanel
2. Go to **Plugins** → **Installed Plugins**
3. Find **"Auto Ban Security Alerts"**
4. Click **"Settings"**

## First-Time Setup

### Step 1: Activate Premium Access

Choose one of these methods:

1. **Activation Key** (if you have one)
   - Enter key in the activation form
   - Click "Activate"

2. **Patreon Subscription**
   - Subscribe to: https://www.patreon.com/membership/27789984
   - Plugin will auto-verify your subscription

3. **PayPal Payment**
   - Pay via: https://paypal.me/KimBS
   - Plugin will auto-verify your payment

### Step 2: Configure Settings

Once activated, configure:

- **Enable Auto-Banning**: Toggle ON/OFF
- **Ban Duration**: Choose from 1h, 24h, 7d, 30d, or Permanent
- **Ban Reason**: Custom reason for auto-banned IPs
- **Check Interval**: How often to check (minimum 30 seconds)

### Step 3: Manage Whitelist

- **System IP**: Automatically whitelisted (207.180.193.210) - cannot be deleted
- **Add IPs**: Add any IPs that should never be auto-banned
- **Remove IPs**: Remove user-added IPs (system IP is protected)

## How It Works

1. **Background Monitoring**: Plugin runs a thread that checks Security Alerts every N seconds
2. **Alert Detection**: Monitors for:
   - Brute force attacks (10+ failed passwords)
   - Root login attempts
   - Dictionary attacks (5+ invalid users)
   - Port scanning
3. **Auto-Banning**: IPs from alerts are automatically banned (unless whitelisted)
4. **Logging**: All bans are logged in "Recent Auto-Bans" section

## Features

✅ **Automatic IP Banning** - No more manual clicking!
✅ **IP Whitelist** - Protect trusted IPs
✅ **System IP Protection** - CyberPanel IP auto-whitelisted
✅ **Auto-Update** - System IP whitelist updates automatically
✅ **Ban History** - Track all auto-bans
✅ **Configurable** - Customize ban duration and check interval

## Troubleshooting

### Plugin Not Showing
- Restart CyberPanel: `systemctl restart lscpd`
- Check INSTALLED_APPS in settings.py

### Migrations Needed
```bash
cd /usr/local/CyberCP
python3 manage.py migrate autoBanSecurityAlerts
```

### Check Logs
```bash
tail -f /usr/local/lscp/logs/error.log
```

## Support

- **Patreon**: https://www.patreon.com/membership/27789984
- **PayPal**: https://paypal.me/KimBS

---

**Plugin Version:** 1.0.0  
**Author:** master3395  
**Status:** ✅ Installed and Ready
