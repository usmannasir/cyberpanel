# OLS + Apache Backend Auto-Setup

## What this does

When creating a website or child domain via `website-functions.sh`, users can now select:

- `Enable Additional Feature: OpenLiteSpeed + Apache backend (YES/NO)`

If set to `YES`, the script automatically runs:

- `ols-apache-backend-setup.sh --domain <domain>`

## Automated actions

1. Detects docroot from LiteSpeed vhost config.
2. Writes Apache backend vhost config at:
   - `/etc/httpd/conf.d/<domain>.ols-apache-backend.conf`
   - Includes both `:8083` (HTTP backend) and `:8082` (HTTPS backend).
3. Rewrites LiteSpeed vhost config to proxy through:
   - `apachebackend` (`127.0.0.1:8083`)
   - `proxyApacheBackendSSL` (`127.0.0.1:8082`)
4. Runs validation and service gates:
   - `httpd -t`
   - ensures `httpd` is running/enabled
   - restarts `lsws`
   - verifies ports `8082/8083` are listening
   - verifies site health is not 503
5. Rolls back to backups if setup fails after retries.

## Logs

- Main setup log: `/var/log/cyberpanel_ols_apache_backend.log`
- Existing user CLI logs are still used for create/delete actions.

## Failure handling

- Retries up to 3 times.
- Every error line includes timestamp, module, domain, and retry count.
- On hard failure, prior config snapshots are restored.

## Test

Run:

```bash
/home/cyberpanel-mods/user-management/Test/test-ols-apache-backend-setup.sh
```

This validates wiring and safety gates for the new feature.
