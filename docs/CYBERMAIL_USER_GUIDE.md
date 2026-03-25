# CyberMail Email Delivery — User Guide

**For**: CyberPanel users and resellers
**Last Updated**: 2026-03-06

---

## What is CyberMail?

CyberMail is CyberPanel's built-in email delivery service. It routes your outgoing emails through optimized servers so they land in the inbox instead of spam. Every CyberPanel installation includes CyberMail with a free tier of 15,000 emails per month.

---

## Quick Start

### 1. Open CyberMail

Log into CyberPanel and navigate to: **Email > Email Delivery** or go directly to `https://your-server:8090/emailDelivery/`

### 2. Create Your Account

- Click **"Get Started Free"**
- Enter your email address
- Choose a password
- Click **Connect**

You'll immediately get access to the dashboard with the Free plan (15,000 emails/month).

### 3. Add Your Domain

- Go to the **Domains** tab
- Click **"Add Domain"**
- Type your domain name (e.g., `mydomain.com`)
- Click **Add**

CyberMail will automatically set up the DNS records needed for email delivery (SPF, DKIM, DMARC). If your domain's DNS is managed by CyberPanel's PowerDNS, this happens instantly.

### 4. Verify Your Domain

- Click **"Verify"** next to your domain
- Check that SPF, DKIM, and DMARC all show green checkmarks
- If any are red, wait a few minutes for DNS propagation and verify again

### 5. Start Sending

Once your domain is verified, emails sent from that domain will benefit from CyberMail's delivery optimization. For maximum deliverability, enable the SMTP relay.

---

## Features

### Domain Management

Add multiple sending domains to your CyberMail account. Each domain gets:

- **SPF record** — tells receivers your emails are authorized
- **DKIM signing** — cryptographically signs your emails to prevent tampering
- **DMARC policy** — instructs receivers how to handle unauthenticated emails

**Status indicators:**
- Gray badge = Not verified
- Green badge = Verified and active

**Actions:**
- **Verify** — recheck DNS records
- **Auto DNS** — reconfigure DNS records in PowerDNS (if records were deleted)
- **Remove** — remove the domain from CyberMail

### SMTP Credentials

Create credentials for sending emails through CyberMail's SMTP servers:

- **Create** — generates a username and one-time password
- **Rotate** — generates a new password (old one stops working)
- **Delete** — permanently removes the credential

> **Important**: The password is shown only once when created or rotated. Copy it immediately.

**SMTP Settings for manual configuration:**
| Setting | Value |
|---------|-------|
| Host | `mail.cyberpersons.com` |
| Port | `587` |
| Security | STARTTLS |
| Authentication | Login (SASL) |
| Username | Shown after creation |
| Password | Shown once after creation |

### SMTP Relay

The easiest way to use CyberMail — route ALL outgoing email from your server automatically:

- **Enable** — one click to configure everything
- **Disable** — one click to revert to direct sending

When enabled, every email your server sends (from all websites, all email accounts) goes through CyberMail. No application-level changes needed.

### Delivery Logs

Monitor every email sent through CyberMail:

- **Filter by status**: All, Delivered, Bounced, Failed, Deferred
- **Filter by time**: Last 1, 3, 7, 14, or 30 days
- **View details**: Date, sender, recipient, subject, delivery status

### Statistics

Track your email performance:

- **Total Sent** — emails sent this billing period
- **Delivered** — successfully delivered to recipient
- **Bounced** — rejected by recipient server
- **Failed** — permanent delivery failures
- **Delivery Rate** — percentage of successful deliveries
- **Per-Domain Breakdown** — stats for each sending domain

### Usage Tracking

The dashboard shows a progress bar of your monthly email usage:
- Green = under 80% usage
- Yellow/warning = approaching limit
- An upgrade banner appears when you're near your plan limit

---

## Plans

| | Free | Starter | Professional | Enterprise |
|---|---|---|---|---|
| **Price** | $0/mo | $15/mo | $90/mo | $299/mo |
| **Emails** | 15,000 | 100,000 | 500,000 | 2,000,000 |
| **Infrastructure** | Shared | Shared | Dedicated IPs | Dedicated IPs |
| **Analytics** | Basic | Advanced | Advanced | Advanced |
| **Support** | Community | Priority | Priority | Dedicated Manager |
| **Custom DKIM** | No | No | Yes | Yes |
| **Webhooks** | No | No | Yes | Yes |
| **SLA** | — | — | — | 99.9% |

To upgrade, visit the CyberMail platform at https://platform.cyberpersons.com

---

## Disconnecting Your Account

If you need to disconnect CyberMail:

1. Go to the CyberMail dashboard
2. Click the **"Disconnect"** button
3. Confirm the action

**What happens:**
- SMTP relay is disabled (if it was enabled)
- Postfix returns to direct sending
- Local data (domains, credentials) is cleared
- Your platform account is preserved — you can reconnect anytime

---

## FAQ

**Q: Will enabling relay affect my existing email accounts?**
A: Yes, ALL outgoing email from the server will route through CyberMail. This includes emails from websites (contact forms, notifications) and email accounts (Postfix). Incoming email is not affected.

**Q: Can I use CyberMail without the relay?**
A: Yes. You can use SMTP credentials directly in your applications (WordPress SMTP plugins, custom scripts, etc.) without enabling the server-wide relay.

**Q: What happens if I exceed my plan limit?**
A: Check with the platform for current overage policies. The dashboard shows your usage so you can monitor and upgrade before hitting limits.

**Q: Can I use CyberMail for bulk marketing emails?**
A: CyberMail is designed for transactional and legitimate business email. Bulk marketing to purchased lists is not permitted. Use it for newsletters to opted-in subscribers, transactional emails, and business communications.

**Q: My domain DNS is not managed by CyberPanel. Can I still use CyberMail?**
A: Yes. After adding the domain, click "DNS Records" to see the required records. Add them manually at your DNS provider (Cloudflare, Route53, etc.).

**Q: I disconnected and reconnected. Why are my old domains gone?**
A: Reconnecting clears stale local data. Simply add your domains again — if they're still registered on the platform, they'll link back.

**Q: Is there a banner on other pages?**
A: Yes, a promotional banner appears on email-related pages (Webmail, Mail Functions, etc.). It can be dismissed by clicking the X button and won't reappear for 7 days.

---

## Support

- **CyberPanel Issues**: https://github.com/usmannasir/cyberpanel/issues
- **CyberMail Platform**: https://platform.cyberpersons.com
- **Email Deliverability Help**: Check your domain at https://www.mail-tester.com
