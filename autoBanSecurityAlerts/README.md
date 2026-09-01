# Auto Ban Security Alerts Plugin

A premium CyberPanel plugin that automatically bans IP addresses from Security Alerts Detected in Recent SSH Logs, eliminating the need for manual "Ban IP Permanently" clicks.

## Features

- **Automatic IP Banning**: Automatically bans IPs that appear in Security Alerts Detected
- **IP Whitelist Management**: Whitelist IPs that should never be auto-banned
- **System IP Protection**: CyberPanel machine IP is automatically whitelisted and cannot be deleted
- **Auto-whitelist on IP Change**: If the machine IP changes in `/etc/cyberpanel/machineIP`, it's automatically whitelisted
- **Configurable Ban Duration**: Choose from 1 hour, 24 hours, 7 days, 30 days, or permanent
- **Customizable Check Interval**: Set how often to check for Security Alerts (minimum 30 seconds)
- **Ban History**: View recent auto-bans with details
- **Premium Plugin**: Requires Patreon subscription or PayPal payment

## Installation

1. Copy the plugin directory to `/home/cyberpanel-plugins/autoBanSecurityAlerts/`
2. Install via CyberPanel Plugin Manager or manually:
   ```bash
   cd /usr/local/CyberCP
   python3 manage.py migrate autoBanSecurityAlerts
   ```
3. Access the plugin at: `https://your-domain:8090/plugins/autoBanSecurityAlerts/settings/`

## Configuration

### Payment Methods

The plugin supports:
- **Patreon Subscription**: Subscribe to "CyberPanel Paid Plugin" tier
- **PayPal Payment**: One-time payment via PayPal.me
- **Activation Key**: Enter a valid activation key if you have one

### Settings

- **Enable Auto-Banning**: Toggle to enable/disable automatic banning
- **Ban Duration**: Choose how long IPs should be banned (default: Permanent)
- **Ban Reason**: Custom reason for auto-banned IPs
- **Check Interval**: How often to check for Security Alerts (default: 60 seconds, minimum: 30 seconds)

### IP Whitelist

- **System IP**: The CyberPanel machine IP (from `/etc/cyberpanel/machineIP`) is automatically whitelisted
- **User IPs**: Add custom IPs to the whitelist that should never be banned
- **System IP Protection**: The system IP cannot be deleted from the whitelist

## How It Works

1. The plugin runs a background monitoring thread that periodically checks for Security Alerts
2. When Security Alerts are detected, IPs are extracted from the alerts
3. IPs are checked against the whitelist (system IP and user-added IPs)
4. IPs that are not whitelisted and haven't been recently banned are automatically banned
5. Ban attempts are logged in the Recent Auto-Bans section

## Security Alerts Monitored

The plugin monitors for:
- **Brute Force Attacks**: IPs with 10+ failed password attempts
- **Root Login Attempts**: Direct root login attempts
- **Dictionary Attacks**: IPs attempting to login with 5+ non-existent usernames
- **Port Scanning**: Suspicious connection patterns

## Requirements

- CyberPanel 2.5.5+
- Python 3.6+
- Django 2.2+
- Premium subscription (Patreon or PayPal)

## Author

master3395

## License

MIT

## Support

For support, please contact via:
- Patreon: https://www.patreon.com/membership/27789984
- PayPal: https://paypal.me/KimBS
