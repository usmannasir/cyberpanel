# SnappyMail AUTHENTICATIONFAILED after v2.5.5-dev upgrade

Date: 20/07/2026

## Symptom

SnappyMail at `:2087/snappymail/` shows:

`AUTHENTICATIONFAILED Authentication failed`

## Root cause

This message comes from Dovecot (IMAP), not from a broken SnappyMail install. When the mailbox password does not match `e_users.password`, Dovecot rejects PLAIN auth and SnappyMail surfaces that exact string.

Typical healthy signals:

- Account exists in `cyberpanel.e_users` with `{CRYPT}$2b$12$...` (bcrypt)
- `dovecot` and `postfix` are active; ports 143/993 listen
- `include.php` points at `/usr/local/lscp/cyberpanel/snappymail/data/` (not rainloop)
- Successful IMAP logins from `::1` prove SnappyMail can reach Dovecot

## Operator fix

Reset the mailbox password (panel UI or CLI), then retest:

```bash
cyberpanel changeEmailPassword --email user@example.com --password 'NEW_PASS'
doveadm auth test user@example.com 'NEW_PASS'
```

## Secondary cleanup (upgrade hardening)

RainLoop to SnappyMail migration can leave both `domains/<name>.ini` and `domains/<name>.json`. SnappyMail prefers `.json` (localhost:143 STARTTLS). Conflicting `.ini` (often 993/TLS) is removed on upgrade/fix when a sibling `.json` exists (backed up under `domains.bak/`).

Implemented in:

- `scripts/utils/fix-snappymail.sh`
- `upgrade_modules/10_post_tweak.sh`
