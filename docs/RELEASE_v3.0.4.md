# CyberPanel v3.0.4 (build 4) — Release Notes

_Released 2026-08-23._

_Updated 2026-08-24 with native AlmaLinux 10 support._

CyberPanel v3.0.4 improves installation and upgrade reliability, completes
remote MySQL support, standardizes new installations on the integrated webmail
client, and fixes reported problems in SSL renewal, WordPress Manager, mail
delivery, plugins, and File Manager.

## Highlights

- Configures Django, Postfix, Dovecot, PowerDNS, PureFTPd, phpMyAdmin, and
  runtime database operations for an explicitly selected remote MySQL host and
  port.
- Preserves private configuration across upgrades and stops failed database
  preparation with a clear, redacted error.
- Uses CyberPanel's integrated webmail exclusively on fresh installations while
  retaining protected legacy data during upgrades.
- Restores Postfix lookups on MariaDB 11.8 and Dovecot 2.4 local mail delivery
  without broadening credential-file permissions.
- Installs WordPress reliably on existing websites and records the result in
  WordPress Manager.
- Deploys renewed SSL certificates before reporting success and protects ACME
  account and certificate keys.
- Downloads files whose names contain spaces or special characters while
  preserving traversal protection (#1902).
- Restores phpMyAdmin auto-login with a short-lived, one-time handoff from the
  authenticated CyberPanel session (#1904).
- Makes interrupted upgrades, firewall-asset repair, plugin route updates,
  Sieve redirect generation, and OpenSSH-key deletion fail safely.
- Adds native AlmaLinux 10 installation and upgrade support using the matched
  OpenLiteSpeed 2.5.2, `cyberpanel_ols.so` 2.7.6, and ModSecurity 2.5.2 EL10
  release set.

## Compatibility

Ubuntu 22.04, Ubuntu 24.04, Ubuntu 26.04, and AlmaLinux 10 installation paths
have been exercised during the 3.0 release series. The AlmaLinux 10 candidate
received a clean public install, a custom-OLS upgrade pass, service and ABI
verification, and an authenticated browser website-creation test. The final
Ubuntu candidate received a clean Ubuntu 26.04 install, remote-database
upgrade, reboot, service, WordPress, SSL, native-webmail, and authenticated
browser pass. Existing local-database installations retain their established
configuration.

## Publish checklist

Complete these steps in order:

1. Push the exact tested candidate to the `v3.0.4` branch.
2. Confirm `https://cyberpanel.net/version.txt` is exactly
   `{"version":"3.0","build":4}` with no trailing newline.
3. Publish the `v3.0.4` changelog entry on the CyberPanel changelog page.
4. Merge the exact tested release into `stable` and push `stable`.
5. Reinstall the existing Ubuntu 26 test server from the public branch and run
   the authenticated browser smoke test.

Rollback the public pointer to `{"version":"3.0","build":3}` if the public
installation or upgrade check fails.
