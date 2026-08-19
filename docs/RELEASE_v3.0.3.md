# CyberPanel v3.0.3 (build 3) — Release Notes

_Released 2026-08-20._

CyberPanel v3.0.3 is a security hotfix for API authentication and account
authorization. Administrators should upgrade promptly.

## Changes

- Rejects placeholder and empty API credentials across token-authenticated
  endpoints.
- Generates random credentials for API-created accounts and rotates invalid
  credentials on enabled accounts during upgrade.
- Makes cloud session-access failures uniform and rate-limited, rejects
  suspended accounts, and rotates authenticated sessions.
- Prevents non-administrators from assigning administrator-level custom ACLs
  through API and user-management flows.
- Removes credential-bearing website-creation payloads from debug logs.

Existing valid API credentials continue to work. An enabled account that still
had an invalid placeholder credential receives a new credential during upgrade.
Administrators can reset an account credential by changing its password.

## Publish checklist

Complete these steps in order:

1. Push the `v3.0.3` branch.
2. Update `https://cyberpanel.net/version.txt` to exactly
   `{"version":"3.0","build":3}` with no trailing newline.
3. Publish the `v3.0.3` changelog entry on the CyberPanel changelog page.
4. Merge the tested release into `stable` and push `stable`.
5. Upgrade the existing Ubuntu 26 test server from the public pointer and run
   the authenticated browser smoke test.

Rollback the public pointer to `{"version":"3.0","build":2}` if the public
upgrade check fails.
