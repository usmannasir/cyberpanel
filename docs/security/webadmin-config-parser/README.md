# Tested WebAdmin configuration parser repair candidate

Status: **source repair candidate only**. This directory does not publish a replacement OLS binary, change installer pins, or make an already-blocked upgrade recover automatically.

The published 2.5.6 WebAdmin UI writes six login-throttling/history/audit settings that the same release's native configuration parser does not recognize. Saving those settings makes `openlitespeed -t` return 2; the upgrade preflight correctly refuses that configuration. The seventh setting, `configAutoBackupRetention`, is also emitted by the bundled UI and omitted from the parser table.

`webadmin-parser.patch` adds only these seven existing names to `src/main/plainconf.cpp`, registers a native regression file in the full unit-test target, and adds five regression cases. It does not delete settings, change values/defaults, bypass validation, alter PHP enforcement, or change module entitlements. The parser already registers configuration keywords globally; this follows its existing architecture.

## Exact provenance

Downloads were checked against the immutable release:

| Input | SHA-256 |
| --- | --- |
| [Core source](https://cyberpanel.net/openlitespeed-2.5.6-source.tar.gz) | `86a4d7dfc14f7bc72be6fbd7749ef6a13fe81e7549bc00acd62868372618b3b0` |
| [Security assets](https://cyberpanel.net/ols-security-assets-2.5.6-php8.3.36-x86_64.tar.gz) | `b812c9bfa839cbd20087fce1526f1fac77ea5360bf2b411d5827dd6d025c5a13` |
| [Published Ubuntu core](https://cyberpanel.net/openlitespeed-2.5.6-x86_64-ubuntu) | `404c148b3dbdc7341d9a8166b034ddb93f4aac9eee1168ba331f9b0e9fb79b6c` |

Published PHP ownership is explicit:

- `Product/Base/DTblDefBase.php`, `add_ADM_THROTTLE`: defines the six controls and numeric bounds; `getSharedAdminPhpAttrs`: defines configuration-backup retention (3â€“3650 days).
- `Product/Base/DPageDefBase.php`: maps `ADM_PHP` and `ADM_THROTTLE` into `adminConfig`.
- `Controller/ControllerBase.php`, `initializeAdminTimeout`: reads all seven values and passes them to the throttle/history/audit/backup implementation.
- `Config/Validation/ThrottlePostTableValidationRule.php`: refuses a block window greater than maximum backoff.
- `Config/Service/ConfigActionService.php`: validates before `SavePost`; the six throttle/history/audit changes use the existing no-restart save handling.

Those PHP files are unchanged. The separate PHP regression executes the actual bundled cross-field validation and no-restart field mapping. It checks valid/equal/invalid limits and input-value preservation. It is not a browser login/save acceptance test or a full per-field bounds test.

## Observed validation

The native parser tests compile actual source, not a reimplementation. Five tests cover all seven settings, exact values, existing settings, mixed case, omitted controls, and continued rejection of unknown security directives. Against the original parser, three tests fail with eleven assertions; after the patch all five pass. These focused executables link preserved native utility libraries; no full historical 388-test-suite rerun is claimed.

A separate **whole server binary** was compiled from the checksum-verified source plus the seven keyword additions on Ubuntu 24.04 x86_64 (GCC 13.3). Existing build dependencies and locally extracted distro development headers were used; no host package installation was necessary. Its hash is recorded in `validation.json`. This experimental binary is not a reproducible release build and must not be distributed or installed as a replacement for the supported platform artifacts.

Using the same synthetic root and unchanged configuration:

- Published binary: exit 2, seven unsupported-key errors.
- Experimental complete binary: exit 0, no diagnostics.
- Experimental binary with an unknown typo appended: exit 2, unknown-key error.
- The original synthetic `admin_config.conf` SHA-256 was unchanged after both normal validations.

Logs and fixtures are adjacent. Public logs replace only the private fixture-directory prefix with `<QA_WORKDIR>`; raw logs are retained outside the repository. The fixture has no licensed module, websites, WAF, customer authentication, or private data. No server listener was started. This validates real configuration loading, not request handling, paid functionality, login throttling under load, or a complete hosting upgrade.

## Reproduce in isolated build infrastructure

1. Download the three immutable inputs above, verify all hashes, and extract source/security assets into a disposable directory with safe archive extraction. Keep the original source separately.
2. Apply `patch -p1 < webadmin-parser.patch` inside the extracted `core` directory. With the project's supported native dependencies, configure CMake with `-DOLS_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo`, then build. Run the five `WebAdmin*` tests on baseline and candidate; the patch adds their file to `OLS_UNITTEST_FULL_SRCS`. A full unit run is required for release acceptance.
3. To reproduce configuration validation, make a disposable root containing `conf`, `logs`, `tmp`, `admin/conf`, `admin/logs`, `admin/fcgi-bin`, and `admin/cyberpanel-php/etc`. Copy the two adjacent fixtures to `conf/httpd_config.conf` and `admin/conf/admin_config.conf`. Copy `dist/conf/mime.properties` from source to `conf/`.
4. Copy `payload/admin/fcgi-bin/admin_php` and `payload/admin/cyberpanel-php/etc/php.ini` from the verified assets into the corresponding root locations. Set runtime mode 0755 and preserve the root-owned INI policy. Create an empty mode-0600 `admin/conf/htpasswd` (no valid user) and empty `admin/conf/enable_webadmin` marker in this disposable root only.
5. Record the admin-config hash, then run each binary using **only** `LSWS_HOME=/absolute/disposable/root timeout 30 /absolute/binary -t`. Capture each exit status immediately. Never execute a candidate without `-t` or point it at an installed server. Expect baseline 2 and candidate 0. Verify the configuration hash afterward.
6. Append `throttleMaxFailurez 3` to the disposable admin config and repeat candidate `-t`: expect 2 and a corresponding unsupported-key error. Restore the fixture afterward.
7. Run `php php-security-regression.php /absolute/extracted-assets/payload`. No production PHP files or configuration are modified.

## Release and recovery gates

A complete release still requires:

1. Review/apply this source change in the owning custom OLS core repository; rebuild the four native core variants with the established release toolchain and provenance. Keep existing security fixes and ABI.
2. Retest the paired licensed module, all five platform-specific WAF adapters, security assets, WebAdmin behavior, and native OS matrix. An unchanged ABI does not waive these tests. Run actual UI save/login throttling/history/audit/backup acceptance, plus normal/blocked WAF traffic and rollback.
3. Publish a new immutable release version with source, manifest, validation evidence, artifact hashes, sidecars, and updated consumer pins. Never overwrite the existing 2.5.6 artifacts. Update standalone WAF core-hash allowlists even if adapter bytes remain unchanged.
4. Provide a reviewed recovery bootstrap for installations where the old core rejects these valid UI-generated settings **before** an ordinary upgrade can install the repaired core. It must verify exact source/artifact provenance and OS, stage the complete matched bundle, validate the unchanged configuration with the candidate, reject unrelated errors, preserve authentication/entitlements/security values, and support paired rollback. Do not broadly ignore the old preflight, remove the settings, or advise stock-package replacement.
5. Validate that bootstrap end-to-end on a disposable instance reproducing the block, including service lifecycle and website behavior, before offering it to affected users.

Until these gates pass, the source patch and test receipts are reviewable engineering evidence, not a customer installation procedure or a released fix.
