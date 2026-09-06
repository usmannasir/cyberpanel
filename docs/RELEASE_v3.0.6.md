# CyberPanel v3.0.6 (build 6) — Standalone Webmail Maintenance Release

_Release candidate prepared 2026-09-07._

CyberPanel 3.0.6 restores the standalone webmail authentication flow for
ordinary mailbox users. The global panel middleware previously intercepted the
dedicated webmail login routes before the webmail controller could authenticate
the mailbox against IMAP.

## Changes

- Allows anonymous access only to the exact standalone webmail login page,
  login API, and logout API.
- Allows other `/webmail/` routes only for a complete standalone mailbox
  session or an existing CyberPanel administrator session.
- Keeps mailbox authentication separate from CyberPanel administrator
  authentication; no mailbox-to-administrator fallback is introduced.
- Rotates and persists the session identifier after login and logout and sets a
  12-hour standalone-session lifetime.
- Adds per-account and source-address throttling for failed mailbox logins and
  avoids exposing backend IMAP error details.
- Makes the login/logout APIs POST-only and CSRF-protected and ensures the login
  page issues a CSRF cookie.
- Restricts standalone account switching and account listing to the currently
  authenticated mailbox and adds an explicit standalone sign-out action.

## Account model clarification

CyberPanel's panel login authenticates only `Administrator` records. Website
Owner accounts (`type=3`) are created from website-owner credentials, while
mailboxes use separate email-account credentials. CyberPanel does not
automatically provision the same credentials for both account types. A matching
username and password can occur only when an administrator chooses overlapping
credentials, and such a user receives only the panel privileges allowed by its
assigned ACL.

## Validation completed

- 11 standalone webmail unit tests passed.
- 2 live-endpoint integration tests passed.
- 30 related middleware, webmail, and website-owner security tests passed.
- Django system checks and changed-file Python/JavaScript syntax checks passed.
- On the retained Ubuntu 26 QA panel, anonymous login loaded over HTTPS with a
  CSRF cookie, invalid mailbox credentials reached the webmail controller and
  returned the generic error, POST logout succeeded, and GET logout returned
  HTTP 405.
- A fresh headless Chromium session completed the same flow with zero page,
  console, or server errors.

## Publish checklist

1. Publish this exact tested source tree to `v3.0.6` and `stable`.
2. Set `https://cyberpanel.net/version.txt` to exactly
   `{"version":"3.0","build":6}`.
3. Upgrade the retained Ubuntu 26 validation server through the public updater.
4. Repeat the standalone login/logout browser and endpoint checks and verify
   required services.
5. Add the build 6 entry to the public CyberPanel change log.

If public installation or upgrade fails, restore the public pointer to build 5
while preserving the release branch for diagnosis.
