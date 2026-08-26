# CyberPanel v3.0.5 (build 5) — Security Release

_Release candidate prepared 2026-08-26._

CyberPanel 3.0.5 closes an API authentication gap for accounts protected by
two-factor authentication. Every maintained password- or token-authenticated
API entry point now applies the account's TOTP policy before allowing an
operation or creating a browser session.

## Security changes

- Enforces TOTP on the standard API, cloud API router, connection verification,
  API login, and `/cloudAPI/access` session handoff.
- Replaces password-derived API tokens with random, versioned credentials.
- Rotates enabled legacy tokens during upgrade and rejects them after the
  security update.
- Adds API-key regeneration and complete revocation to **Users > API Access**.
- Rate-limits repeated failed API TOTP checks per account and source address.
- Allows root provisioning tools to install an explicit versioned token.
- Returns the current token from password-based connection verification only
  after password and TOTP checks succeed, with `Cache-Control: no-store`.

## Integration migration

Accounts without two-factor authentication continue to authenticate with their
current random API key. Accounts with two-factor authentication must include a
current six-digit code in either:

```text
X-CyberPanel-OTP: 123456
```

or the JSON `otp` field. Query-string TOTP values are intentionally rejected.

Upgrades rotate legacy password-derived tokens for enabled API accounts. Copy
the replacement key from **Users > API Access**, or regenerate it there, and
update the external integration. Disabling API access clears the stored key.

For automated image provisioning, generate a 64-character URL-safe secret with
the `cp_api_v1_` prefix and run:

```bash
/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/adminPass.py \
  --api 1 --api-token 'Basic cp_api_v1_<64-character-secret>'
```

## Validation completed on the candidate

- Focused source suite: 59 tests passed.
- Installed Ubuntu 26 suite: 59 tests passed.
- Live API regression: missing TOTP rejected; current TOTP accepted on the
  standard API, cloud API, and session handoff.
- Legacy password-derived token replay rejected even with a valid TOTP.
- Live failed-TOTP regression: ten invalid codes triggered the per-account,
  per-source limit; a valid code remained blocked until the limiter reset and
  then authenticated normally.
- Authenticated strict-HTTPS browser regression: key regeneration, display,
  disable, and database revocation passed without console or page errors.
- Root CLI regression: explicit token install and disable/revocation passed,
  with the original administrator state restored after the test.

## Publish checklist

1. Push the tested candidate to `v3.0.5` and merge that exact candidate into
   `stable`.
2. Set `https://cyberpanel.net/version.txt` to exactly
   `{"version":"3.0","build":5}`.
3. Upgrade the retained Ubuntu 26 validation server through the public path.
4. Repeat API, authenticated browser, service, website, WordPress, and backup
   smoke tests.
5. Update the public change log and publish the coordinated security advisory.

If public installation or upgrade fails, restore the public pointer to build 4
while leaving the private advisory unpublished.
