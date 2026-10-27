# OpenLiteSpeed 2.5.6 support assets

The custom core/module update also requires the pinned security asset archive.
A core-only overlay does not update WebAdmin PHP or source-managed support files.

The archive has 261 explicit regular files, including 220 PHP source files,
WebAdmin PHP 8.3.36, static OpenSSL 3.5.9 and libxml2 2.15.3, licenses and build
provenance. It contains no customer authentication database, listener/vhost
configuration, website PHP, panel PHP, licensing state or entitlement changes.
Optional LSNS and cache-manager assets update only when already installed.

The isolated WebAdmin runtime deliberately has no OPcache. Its dedicated INI
sets `session.upload_progress.enabled=0` before request parsing, the PHP project's
interim mitigation for CVE-2026-115560. PHP 8.3.36 includes the fixes for
CVE-2026-109618 and CVE-2026-109619. This does not patch a website's PHP runtime.
A system CA bundle is selected from the normal Ubuntu/EL paths; TLS peer
verification remains enabled.

## Transaction contract

1. Download `SECURITY_ASSETS_URL` to private staging and construct
   `SecurityAssetsTransaction(archive, SECURITY_ASSETS_SHA256, server_root,
   fresh_install=...)`. Construction validates every path/hash, backs up
   regular files and symlinks, probes the candidate PHP and lints all PHP assets.
2. Persist `tx.backup_dir` in the paired core/module backup before stopping OLS.
3. Stop OLS completely, replace the paired core/modules, then call `tx.apply()`.
   Validate OLS configuration and start the service. A graceful restart is not
   sufficient to reevaluate the upstream WebAdmin enable marker.
4. If any stage fails, stop the service, call `tx.rollback()` and restore the
   paired core/modules before restarting the previous version.
5. A later manual rollback must call
   `restore_security_assets(saved_backup_dir, server_root)` together with the
   core/module rollback. Report failure if the restored service cannot start.

The helper never starts or stops a service. It rejects archive traversal, links,
unknown assets, duplicate files, unexpected WebAdmin document-root links and
checksum failures before replacing installed bytes. It preserves an existing
`admin_php` symlink in rollback instead of copying over its website-PHP target.

Fresh installs set `disableWebAdmin 1` and do not create an enable marker.
Upgrades preserve an explicit `disableWebAdmin 0` by creating the new upstream
`admin/conf/enable_webadmin` marker transactionally if absent. Existing listener,
authentication and legacy `admin/conf/php.ini` bytes are preserved. The matching
2.5.6 core selects the dedicated INI only after checking its ownership and mode.

## Verification scope

The isolated build's runtime/XML/AES/HTTPS trust-store probes passed on Ubuntu
22, 24 and 26 and AlmaLinux 8, 9 and 10. Actual Ubuntu 22 WebAdmin HTTP requests
verified PHP 8.3.36, no OPcache, the dedicated INI, no additional INI scan and
upload-progress disabled for GET and multipart uploads. Anonymous access and an
incorrect password were denied; correct login, session reuse and the
configuration view succeeded. Temporary probes were removed after testing.

The 121 changed upstream PHP PHPT tests applicable to the selected extensions
were run with a CLI test driver built from the same source/configuration. There
were 107 passes, 14 skips and no failures. Skips include unbuilt extensions,
CGI-only cases and Windows-only behavior; they are not successful exploit
regressions. Real LSAPI multipart requests independently checked startup policy.

The helper unit suite verifies normal/fresh application, symlink restoration,
persisted rollback, failed runtime checks, authentication/website preservation,
optional-component absence, bad hashes and malicious archive paths. This is
isolated QA, not proof for every customer server or permission/customization.

The public artifact URL must not be enabled until the complete paired release,
including the matching core's dedicated-INI behavior and paid-feature regression
checks, has passed the release tests. This document does not assert publication.
