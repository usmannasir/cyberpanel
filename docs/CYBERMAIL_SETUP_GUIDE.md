# CyberMail Email Delivery — Setup & Administration Guide

**Feature**: CyberMail Email Delivery Integration
**CyberPanel Version**: 2.4.5+
**Platform**: https://platform.cyberpersons.com
**Last Updated**: 2026-03-06

---

## Overview

CyberMail Email Delivery is a built-in CyberPanel feature that routes outgoing emails through CyberMail's optimized delivery infrastructure. It solves common email deliverability problems — emails landing in spam, IP blacklisting, missing DNS records — by providing dedicated sending servers, automatic DNS configuration, and real-time delivery analytics.

### Key Benefits

- **15,000 emails/month free** on the Free plan
- **Automatic DNS setup** — SPF, DKIM, and DMARC records configured in one click
- **SMTP relay** — route all server email through CyberMail with one toggle
- **Real-time analytics** — delivery logs, bounce tracking, reputation monitoring
- **Multi-region delivery** — 4 delivery nodes with 99.9% uptime SLA
- **98%+ inbox rate** across major providers (Gmail, Outlook, Yahoo)

---

## Prerequisites

1. CyberPanel 2.4.5 or later installed
2. Active internet connection from the server
3. PowerDNS running (for automatic DNS configuration)
4. Postfix installed (for SMTP relay feature)

---

## Installation

The CyberMail module is included in CyberPanel 2.4.5+. No separate installation needed.

### Verify the Module

```bash
# Check the app exists
ls /usr/local/CyberCP/emailDelivery/

# Check it's in INSTALLED_APPS
grep -n "emailDelivery" /usr/local/CyberCP/CyberCP/settings.py

# Run migrations if needed
cd /usr/local/CyberCP
python manage.py migrate emailDelivery
```

### Database Tables

The module creates two tables:

| Table | Purpose |
|-------|---------|
| `cybermail_accounts` | Stores per-admin CyberMail account connections |
| `cybermail_domains` | Tracks sending domains and their verification status |

---

## Getting Started

### Step 1: Access CyberMail

Navigate to: **https://your-server:8090/emailDelivery/**

You'll see the CyberMail marketing page with plan information and a "Get Started Free" button.

### Step 2: Connect Your Account

1. Click **"Get Started Free"**
2. Enter your email address (defaults to your CyberPanel admin email)
3. Create a password for your CyberMail account
4. Click **Connect**

This registers your account on the CyberMail platform and obtains an API key that's stored locally for future API calls.

> **Note**: If you already have a CyberMail account on the platform, use the same email and password. The system will link your existing account.

### Step 3: Add Sending Domains

1. After connecting, you'll see the dashboard
2. Go to the **Domains** tab
3. Click **"Add Domain"**
4. Enter your domain name (e.g., `example.com`)
5. Click **Add**

The system will:
- Register the domain on the CyberMail platform
- Automatically create SPF, DKIM, and DMARC DNS records in PowerDNS
- Report how many DNS records were configured

### Step 4: Verify Domain

1. Click **"Verify"** next to your domain
2. The system checks SPF, DKIM, and DMARC records
3. Green checkmarks appear for each verified record
4. Status changes to "Verified" when all records pass

> **DNS Propagation**: If verification fails immediately after adding, wait 5-10 minutes for DNS propagation and try again.

### Step 5: Enable SMTP Relay (Optional)

The SMTP relay routes ALL outgoing email from your server through CyberMail:

1. Go to the **Relay** tab
2. Click **"Enable Relay"**
3. The system will:
   - Create (or rotate) SMTP credentials on the platform
   - Configure Postfix with the relay host (`mail.cyberpersons.com:587`)
   - Set up SASL authentication
   - Enable TLS encryption

**What gets configured in Postfix** (`/etc/postfix/main.cf`):
```
relayhost = [mail.cyberpersons.com]:587
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_tls_security_level = encrypt
```

---

## Dashboard Overview

After connecting, the dashboard provides five tabs:

### Domains Tab
- Lists all sending domains with verification status
- SPF, DKIM, DMARC status badges (green = verified)
- Actions: Verify, Auto-Configure DNS, Remove
- DNS auto-configuration works when the domain exists in PowerDNS

### SMTP Tab
- Manage SMTP credentials for sending
- Create new credentials with descriptions
- Rotate passwords (one-time display)
- Delete unused credentials

### Relay Tab
- Shows current relay status (Enabled/Disabled)
- Displays relay host and port
- Enable/Disable toggle
- Relay info: `mail.cyberpersons.com:587` with STARTTLS

### Logs Tab
- Paginated delivery logs
- Filter by: Status (delivered/bounced/failed), Days (1-30)
- Shows: Date, From, To, Subject, Status
- Color-coded status badges

### Stats Tab
- Aggregate stats: Total Sent, Delivered, Bounced, Failed, Delivery Rate
- Per-domain breakdown table
- Useful for identifying domains with deliverability issues

---

## Plans & Pricing

| Plan | Price | Emails/Month | Features |
|------|-------|-------------|----------|
| **Free** | $0 | 15,000 | Shared infrastructure, basic analytics |
| **Starter** | $15/mo | 100,000 | Priority support, advanced analytics |
| **Professional** | $90/mo | 500,000 | Dedicated IPs, custom DKIM, webhooks |
| **Enterprise** | $299/mo | 2,000,000 | SLA guarantee, account manager, custom limits |

Upgrade at: https://platform.cyberpersons.com

---

## Promotional Banners

CyberMail banners appear on email-related pages to inform users about the delivery service:

- Mail Functions (`/mailServer/`)
- Create Email Account
- DKIM Manager
- Webmail
- Email Premium
- Email Marketing

Banners are dismissible with a 7-day cookie-based suppression. They show:
- "Stop Landing in Spam" headline
- Brief feature description
- "Get Started Free" CTA linking to `/emailDelivery/`

---

## Disconnecting

1. Go to **https://your-server:8090/emailDelivery/**
2. Click the **"Disconnect"** button
3. Confirm the action

Disconnecting will:
- Disable SMTP relay if active (remove Postfix relay config)
- Clear the stored API key
- Remove local domain records
- Reset SMTP credential references

> **Note**: Your CyberMail platform account is NOT deleted. You can reconnect later with the same credentials.

---

## Troubleshooting

### "Account not connected" error
The admin session doesn't have an active CyberMail connection. Click "Get Started Free" to connect.

### DNS records not auto-configured
- The domain must exist in PowerDNS on this server
- Check if the domain was created via CyberPanel's DNS management
- If using external DNS, add records manually using the DNS records shown on the platform

### Domain verification failing
- Wait 5-10 minutes after DNS changes for propagation
- Verify records exist: `dig TXT example.com +short`
- Check for conflicting SPF records (only one SPF record allowed per domain)

### SMTP relay not working
- Check Postfix status: `systemctl status postfix`
- Verify relay config: `grep relayhost /etc/postfix/main.cf`
- Check SASL credentials: `cat /etc/postfix/sasl_passwd`
- Test connectivity: `telnet mail.cyberpersons.com 587`
- Check mail queue: `mailq`
- View Postfix logs: `tail -f /var/log/mail.log`

### Relay shows "Failed to configure"
- Ensure `/usr/local/CyberCP/plogical/mailUtilities.py` has the `configureRelayHost` method
- Check file permissions on `/etc/postfix/sasl_passwd`
- Verify Postfix is installed and running

### Emails still going to spam
1. Verify all DNS records (SPF, DKIM, DMARC) are green
2. Check your domain's reputation at https://www.mail-tester.com
3. Ensure you're not sending to purchased/scraped lists
4. Consider upgrading to a plan with dedicated IPs

---

## File Reference

| File | Purpose |
|------|---------|
| `emailDelivery/emailDeliveryManager.py` | Core business logic, platform API calls |
| `emailDelivery/models.py` | Database models (CyberMailAccount, CyberMailDomain) |
| `emailDelivery/views.py` | Django view functions (thin wrappers) |
| `emailDelivery/urls.py` | URL routing (18 endpoints) |
| `emailDelivery/static/emailDelivery/emailDelivery.js` | AngularJS controller |
| `emailDelivery/templates/emailDelivery/index.html` | Single-page template (marketing + dashboard) |
| `plogical/mailUtilities.py` | Postfix relay configuration (configureRelayHost/removeRelayHost) |

---

## Security

- API keys are stored per-admin in the local database, never in config files
- All platform API calls use HTTPS with Bearer token authentication
- SMTP credentials use SASL over TLS (STARTTLS on port 587)
- SASL password file is chmod 600 (root-only readable)
- Session-based authentication with CSRF protection on all endpoints
- Passwords are never stored locally — only on the platform
