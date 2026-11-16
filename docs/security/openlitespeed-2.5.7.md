# CyberPanel OpenLiteSpeed 2.5.7 â€” installer revision 2

The matched 2.5.7 release repairs seven WebAdmin security-setting registrations in the native configuration parser. It also makes fresh WebAdmin login requests use the validated current throttle/history policy before authentication. Unknown directives remain errors. Existing security values, authentication, CSRF protection and configuration are preserved.

This release retains the existing CyberPanel module 2.7.7 and ModSecurity 2.5.6 adapter bytes and the custom LSI ABI. Version numbers identify separate components. Do not replace just the custom core with the distribution OpenLiteSpeed package.

## Release evidence

- Four native builds: 393 unit cases, 102 CGI assertions and 28 Brotli fixtures per build.
- Ubuntu 22/24/26 and EL8/9/10 x86_64 userspaces: core/WAF plus certificate-verified HTTP/2 and HTTP/3 checks.
- Licensed acceptance: 456 feature checks, 54 fresh unlicensed checks and 48 packaged-PHP autoStart checks, with zero failures or skips. See [licensed acceptance](ols-2.5.7-candidate/LICENSED_ACCEPTANCE.md) for fixture corrections and coverage limits.
- WebAdmin: 21 verified-HTTPS behavior checks and 11 policy tests. These are protocol-level checks; they do not claim a successful browser login/save acceptance run.
- Recovery: isolated old-parser reproduction, unchanged-configuration validation, native service transaction, HTTP 200/WAF 403 and injected-start-failure rollback across all 265 affected paths.

These userspace tests do not establish a full installation/reboot or customer-server recovery on every supported host.

## Recovery for the affected 2.5.6 parser

The ordinary upgrade preflight still refuses invalid configuration. If it reports the exact affected 2.5.6 WebAdmin parser failure, use the explicit versioned recovery installer, after retaining a current backup/snapshot and arranging a maintenance window:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://cyberpanel.net/install-module-2.5.7-r2.sh -o /root/install-module-2.5.7-r2.sh
printf '%s  %s\n' \
  c1541115b4de82e4bfb15c436288367fa1395c4f3c66d0813afe4ae29c6df5ec \
  /root/install-module-2.5.7-r2.sh | sha256sum -c -
bash /root/install-module-2.5.7-r2.sh --repair-webadmin-parser
```

Run the final command only after checksum verification succeeds. Recovery validates the installed and candidate bundles in private namespaces before stopping the service, then uses the complete paired rollback transaction. It refuses unrelated errors, ABI mismatches, unknown/new warnings, changed configuration or artifact hashes, external configuration includes/symlinks, and unavailable isolation. It does not grant a module license or remove security settings.

Recovery requires Linux recursive mount isolation (`mount_setattr`, kernel 5.12+), overlayfs and the documented mount/unshare tools. Older EL8 kernels can run the EL8 runtime but cannot use this recovery path; the installer refuses them before service changes. Do not bypass that refusal.

The isolated preflight has no network. If an existing paid module requires a license-cache refresh, first run the ordinary native configuration diagnostic with normal network access so the normal validator can refresh its own cache. Do not edit or fabricate license/cache files or ignore a license-network error. An absent license is separately tested with the module enabled and retains the expected disabled-feature warning.

After successful repair, verify the native configuration check, service status and normal/WAF traffic before retrying the ordinary CyberPanel upgrade. Customer-server completion still requires that host's retest.

## Installer revision 2

Use filenames ending `2.5.7-r2` for the shared installer and cPanel/Plesk/standalone packages. Revision 1's driver retained the older numeric downgrade ceiling and could refuse a same-version reinstall. Revision 2 accepts 2.5.7 while still rejecting newer releases before commands or bundle mutation. Core, module, WAF and security-assets bytes are unchanged by this installer correction. Previously published versioned files remain immutable.

[Installer revision 2 manifest](https://cyberpanel.net/openlitespeed-2.5.7-r2-manifest.json) Â· [Revision 2 validation](https://cyberpanel.net/openlitespeed-2.5.7-r2-validation.json) Â· [Core/source manifest](https://cyberpanel.net/openlitespeed-2.5.7-manifest.json) Â· [Source archive](https://cyberpanel.net/openlitespeed-2.5.7-source.tar.gz)

The source archive SHA-256 is `99b5b9886d52281f5cc90d5925ba29b896c463ab2ea8b9f76368a7ae479d36ee`; it contains the exact parser, WebAdmin application, tests and build provenance and excludes licensed module source. Security assets SHA-256: `1a7720d214a6030a13efee45c6f46afd5fe3b373f4b78e5a824d23278d18cad0`.

## CyberPanel OWASP CRS recovery

On Ubuntu 22.04, 24.04, and 26.04 and on AlmaLinux 9.8, the stock OpenLiteSpeed recovery path accepts CyberPanel's bundled OWASP CRS 3.3.2 when the rules are stored in their original include files. It checks the rule and data files before installing the paired core and WAF and preserves the existing configuration. The installer and normal upgrade use the same updated binaries for those native artifact families.

The updated core handles valid multiline module configuration without a fixed-size parameter buffer. It rejects an invalid module configuration safely. ModSecurity applies the first successfully loaded engine setting at the site's own scope and preserves an explicit monitor-only or disabled mode.

[GitHub issue #1989](https://github.com/usmannasir/cyberpanel/issues/1989) · [Corresponding source and build recipes](https://cyberpanel.net/openlitespeed-2.5.7-crs-scopes-source.tar.gz)

## Quoted inline method policy in stock recovery

CRS stock recovery R8 preserves quoted inline modsecurity_rules blocks,
including a vhost's phase-one SecAction setting tx.allowed_methods.
The recovery inspector accepts the static method assignment together with
id, phase:1, nolog, pass, and t:none. It does not rewrite the rule,
change the allowed methods, remove CRS includes, or disable ModSecurity.

Matching quote delimiters, literal method names and complete parameter names
are required. Dynamic assignments, additional actions, ambiguous quoting and
external dependencies remain unsupported. The native isolated configuration
check still validates the complete rule graph before the service transaction.
Keep a snapshot and use the exact checksum-pinned wrapper supplied by the
upgrade preflight. Do not substitute an older recovery revision or bypass its
checks when recovery refuses a configuration.

The versioned recovery helper is maintained in
install/olsRecoveryPreflight.py; its focused regression tests are
install/test_ols_recovery_inline.py. Release and customer verification are
recorded separately.
