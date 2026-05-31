# CyberPanel v2.5.5-dev Security Audit Report

**Audit date:** 31/05/2026  
**Scope:** Live host 207.180.193.210, install path /usr/local/CyberCP, fork master3395/cyberpanel branch v2.5.5-dev  
**Mode:** Read-only audit (no remediations applied in this pass)  

---

## 1. Executive summary

**Overall posture: Elevated risk** (production on a dev fork branch with several critical and high findings).

| Priority | Count | Top items |
|----------|-------|-----------|
| Critical | 2 | Hardcoded Django SECRET_KEY with world-readable settings.py; unauthenticated git webhooks executing shell commands |
| High | 4 | Exposed panel port 2087/tcp, API/cloudAPI without session layer, GET session bootstrap, weak password hashing |
| Medium | 8 | Case-insensitive usernames, fail2ban disabled, WebAdmin proxy, .git in install tree, etc. |
| Low | 2 | Debug file toggle, version string drift |

**Positive findings:** /etc/cyberpanel/ secret files are mostly 600/640; DEBUG = False; default 1234567 password is **no longer valid** for live admin; HTTP probes returned 302 on .git/HEAD (not direct 200); api.tests_security passed (5 tests).

**Recommended next step:** Approve remediation items in Section 5 before code or firewall changes.

---

## 2. Findings (SEC-01 through SEC-14)

### Critical

#### SEC-01: Hardcoded SECRET_KEY and world-readable settings.py

| Field | Detail |
|-------|--------|
| Severity | Critical |
| Component | CyberCP/settings.py |
| Evidence | mode 644 root:root. SECRET_KEY assigned inline (line 34), not from /etc/cyberpanel/ |
| Exploit scenario | Local users or backup readers forge Django sessions if other controls fail |
| Recommended fix | Move secret to /etc/cyberpanel/django_secret (600); rotate key; chmod 600 on settings or remove inline secret. Effort: M |

#### SEC-02: Unauthenticated git webhooks execute shell commands

| Field | Detail |
|-------|--------|
| Severity | Critical |
| Component | websiteFunctions/website.py, CyberCP/secMiddleware.py |
| Evidence | Session/input bypass for /websites/<domain>/webhook and gitNotify. outputExecutioner on gitConf commands without shared-secret check in reviewed path |
| Exploit scenario | Anyone who can hit the webhook URL may run commands as the site user |
| Recommended fix | HMAC or per-site token in URL/header; rate limit; audit logs. Effort: L |

### High

#### SEC-03: Panel port 2087/tcp exposed on firewall

Evidence: firewalld public zone includes 2087/tcp; lscpd on 0.0.0.0:2087. Fix: restrict to trusted IPs or proxy-only on 443. Effort: S

#### SEC-04: /api and /cloudAPI bypass session; weak password hashing

Evidence: secMiddleware skips /api and /cloudAPI; 32 csrf_exempt handlers in api/views.py; SHA-256 passwords in hashPassword.py. Effort: L

#### SEC-05: cloudAPI/access session bootstrap via GET

Evidence: CSRF-exempt tree; session from token in GET (prior code review). Effort: M

#### SEC-06: Default install password 1234567

Evidence: install.py still hardcodes 1234567 when env unset. **Live:** default_password_still_valid=False for admin. Effort: M (installer Phase 7)

### Medium

#### SEC-07: key.pem 644; .git under /usr/local/CyberCP

Evidence: key.pem mode 644; full .git present. Effort: S

#### SEC-08: ALLOWED_HOSTS = ['*']; missing secure cookie flags

Evidence: live settings.py. Effort: S

#### SEC-09: CyberPanel fail2ban jail disabled

Evidence: [cyberpanel] enabled=false; logpath /usr/local/CyberCP/logs/error.log missing; real logs under /usr/local/lscp/logs/. Effort: S

#### SEC-10: LiteSpeed WebAdmin via ols.newstargeted.com

Evidence: 7080 not in firewall but HTTPS proxy exists. webadmin_passwd is 600. Effort: S

#### SEC-11: SQL string concat in mysqlUtilities.py

Evidence: CREATE USER/GRANT concat; api.tests_security OK (5 tests). Effort: M

#### SEC-13: Usernames case-insensitive at login

Evidence: userName collation latin1_swedish_ci. Live: Admin and ADMIN lookup return admin pk=1 with exact_case=False. Effort: M

#### SEC-14: No username rename on Modify Users

Evidence: modifyUser.html has no newUserName field; saveModifications does not rename. URL: /users/modifyUsers. Effort: L (Phase 9)

### Low

#### SEC-12: Debug toggle and version drift

Evidence: /usr/local/CyberCP/debug absent; live commit 99c51094 vs origin 8b2f5fcf1. Effort: S

---

## 3. Live administrator posture (no secrets)

| userName | api | twoFA | state | type |
|----------|-----|-------|-------|------|
| admin | 1 | 0 | ACTIVE | 0 |
| test123 | 0 | 0 | ACTIVE | 1 |

Primary admin: API enabled, 2FA off, default password not valid on live.

---

## 4. Live vs repository drift

| Reference | Commit |
|-----------|--------|
| Live /usr/local/CyberCP | 99c510948b3a4c0ccaa55fa0a4faf481344831e2 |
| origin/v2.5.5-dev | 8b2f5fcf1a1a7a5d6c76d17d837a0bc5811229e6 |

~300 files differ. Live has uncommitted changes (templates, cyberpanel-ui.css, deploy scripts). Production is not a clean deploy of latest origin.

---

## 5. Remediation backlog

| Order | ID | Effort | Type |
|-------|-----|--------|------|
| 1 | SEC-02 | L | Code |
| 2 | SEC-01 | M | Code+ops |
| 3 | SEC-03 | S | Ops |
| 4 | SEC-09 | S | Ops |
| 5 | SEC-04 | L | Code |
| 6 | SEC-05 | M | Code |
| 7 | SEC-06 | M | Code |
| 8 | SEC-13 | M | Code+DB |
| 9 | SEC-14 | L | Code |
| 10 | SEC-07,08,10,11 | S-M | Mixed |

---

## 6. Username case tests (live)

| Submitted | Same pk as admin | Exact case |
|-----------|------------------|------------|
| admin | Yes | Yes |
| Admin | Yes | No |
| ADMIN | Yes | No |

---

## 7. Modify Users baseline

No rename field. Planned: current username read-only, optional newUserName, ACL per operator policy.

---

## 8. Network and middleware

Ports open (public): 2087, 21, 5672, 15672, others. HTTP .git/HEAD: 302 on tested URLs.

MIDDLEWARE (live): Security, Session, Locale, Common, CSRF, Auth, Messages, XFrame, secMiddleware. phpmyadminMiddleware not registered.

API routes: see api/urls.py (createWebsite, loginAPI, verifyConn, fetchSSHkey, ai-scanner/*, scanner/*, etc.). cloudAPI: single dispatcher.

SSH: PermitRootLogin yes (review hardening separately).

---

## 9. Patch approval checklist

- [ ] SEC-01 through SEC-14 per Section 5

---

End of report.

## 10. Appendix: detailed evidence

### /etc/cyberpanel/ file permissions (31/05/2026)

```
600 cyberpanel:cyberpanel webmail.conf
600 root:root adminPass
600 root:root fastapi_ssh_server.conf
600 root:root limited_phpmyadmin_policy.json
600 root:root webadmin_passwd
640 root:cyberpanel mysqlPassword
644 root:root banned_ips.json
644 root:root csrf_trusted_origins
644 root:root health.json
```

### CSRF trusted origins (file)

Includes https://mail.newstargeted.com:2087, https://207.180.193.210:2087 (and http variants).

### fail2ban [cyberpanel] jail

```
enabled = false
logpath = /usr/local/CyberCP/logs/error.log  (missing)
port = 8090
```

Suggest logpath: /usr/local/lscp/logs/error.log

### Code review notes

- LEGACY_TERMINAL_JWT_SECRET present in plogical/securityUtils.py (fallback if no secret file)
- cert.pem in repository root (install copy on server)
- api/views.py: 1265 lines (maintainability risk)
- Webhook routes: websiteFunctions/urls.py paths <domain>/webhook and <domain>/gitNotify
- phpMyAdmin: limited_phpmyadmin_policy.json mode 600 (strict tabs blocked)

### SEC-14 planned rename ACL (operator policy)

| Actor | May rename |
|-------|------------|
| Full panel admin | Anyone including primary admin |
| Reseller | Only users they created |
| Normal user | Self only |
| Uniqueness | Case-sensitive: admin and Admin may coexist after DB migration |

### Tests run

```
manage.py test api.tests_security
Ran 5 tests in 0.002s
OK
```

---

*Report generated per CyberPanel v2.5.5-dev Security Audit Plan. No plan file was modified.*
