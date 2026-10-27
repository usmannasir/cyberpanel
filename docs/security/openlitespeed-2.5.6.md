# CyberPanel custom OpenLiteSpeed 2.5.6

This release updates the custom OpenLiteSpeed core, its matching ModSecurity adapter, and the isolated WebAdmin PHP runtime as one tested bundle. The licensed CyberPanel module remains version 2.7.7 with unchanged binary hashes and entitlement checks.

## Security changes

- Merge the OpenLiteSpeed 1.9.4 security and protocol changes into the custom core while preserving the CyberPanel module ABI.
- Update Brotli to 1.2.1 and LSQUIC to 4.10.2. Fix compressed-cache negotiation so a client accepting only Brotli is not sent a cached gzip response.
- Update the WAF engine to ModSecurity 3.0.17 and rebuild its adapter against the same custom ABI header. Run request-body inspection before request handlers. Remove the internal cache path that could disable WAF inspection.
- Install PHP 8.3.36 for WebAdmin only, built with OpenSSL 3.5.9 and libxml2 2.15.3. Disable session upload progress and omit OPcache in this isolated runtime. Keep DOM support for WebAdmin log export.
- Select a dedicated, root-owned WebAdmin PHP configuration. Refuse an unsafe existing configuration instead of silently using it.
- Default WebAdmin to disabled on fresh installation. Preserve an existing explicit enablement setting during upgrades, including the marker required by the new core.
- Guard the bundled stock-upgrade helper against replacing the CyberPanel custom core with a stock build.

Website PHP and CyberPanel's own PHP runtime are outside this bundle. This release does not change their versions or configuration.

## Paid functionality and cache behavior

The CyberPanel module, paid entitlements, and WordPress Manager access policy are unchanged. Tests use a legitimate existing license and separately verify fresh unlicensed behavior. No license grant is fabricated by the release installers.

Normal request-inspection profiles retain LSCache. If `SecResponseBodyAccess On` is explicitly configured while the rule engine is enabled, cache reads and writes are bypassed so response-body inspection runs, including for previously warmed cache entries. With the rule engine off, enabling the response-body flag alone does not disable caching. This is a deliberate security behavior, not inspection of a cached sendfile response.

## Installation and rollback

Installers verify the platform-specific core, licensed module, WAF adapter, and support archive checksums before replacing files. They validate the staged PHP runtime and WebAdmin PHP sources, stop the service, replace the complete bundle, test the configuration, and verify service startup. Failure restores the paired binaries and support assets. The saved rollback receipt also supports explicit paired rollback.

The isolated runtime does not replace website PHP or modify customer authentication files, license files, listener configuration, or virtual-host configuration. Fresh installs intentionally add the WebAdmin-disabled setting. Existing explicit WebAdmin enablement may require the new marker file described above.

The standalone WAF installer requires the matching custom core hash. It directs older installations to upgrade the complete bundle instead of mixing an older core with the new adapter.

## Validation

The native test matrix covers Ubuntu 22.04, 24.04, and 26.04, plus AlmaLinux 8, 9, and 10 on x86_64. These are isolated native-userspace containers, not six full hosting-panel installations or customer-server tests.

- Four native core builds each pass 388 unit cases, 102 CGI assertions, and 28 official Brotli fixtures. The unavailable external GeoIP database tests retain their explicit skips.
- All six platforms pass the 73-check paid-feature suite and six fresh-unlicensed checks, covering PHP configuration, headers, environment, access control, authentication, redirects, TLS restrictions, inheritance, brute-force handling, and cache behavior.
- HTTP/1.1, HTTP/2, TLS/SNI, and HTTP/3 are tested. The final release hashes pass the 16-check HTTP/3 suite on all six platforms, including paid behavior, WAF query/body handling, compression, concurrent streams, and malformed-header rejection.
- Security tests cover request bodies, cached requests, response-body inspection, compression negotiation, mixed traffic, graceful reloads, and rollback to the published baseline followed by restoration of the candidate.
- WebAdmin tests cover anonymous and rejected-login behavior, a valid login and session, configuration view, XML parsing, multiline log export, verified outbound TLS, GET and multipart PHP runtime settings, and the fresh-install disabled default. PHP's changed security tests report 108 passes, 14 documented skips, and no failures.
- The final core build differs from the full functional candidate only in version-reporting strings. Its exact hashes are retested across the six platforms for paid behavior and HTTP/1.1, HTTP/2, HTTP/3, and TLS/SNI. Both manifests and the exact two-file diff are retained in the QA evidence.

Graceful reloads can close an in-flight TCP/TLS connection. A bounded comparison reproduces this behavior on the published baseline as well as the candidate. Raw closures and safe GET reconnects are recorded; POST requests are never retried. Steady-load security tests pass. This release does not promise zero disconnects during reloads.

One initial EL8 HTTP/3 run was interrupted by a stale detached-PHP PID file in the container fixture after a cold restart. The fixture was corrected without changing production code, and the settled run and exact final-hash run passed. The original failed receipt remains in the evidence.

## Upstream references

- [OpenLiteSpeed 1.9 release log](https://openlitespeed.org/release-log/version-1-9-x/)
- [Brotli 1.2.1](https://github.com/google/brotli/releases/tag/v1.2.1)
- [PHP 2026 security announcements](https://www.php.net/archive/2026.php)
- [ModSecurity 3.0.17](https://github.com/owasp-modsecurity/ModSecurity/releases/tag/v3.0.17)

Artifact checksums, build provenance, and the core source archive accompany the versioned release. Keep the core, adapter, and support assets paired when installing or rolling back.
