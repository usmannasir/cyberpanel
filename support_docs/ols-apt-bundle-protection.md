# Ubuntu custom OpenLiteSpeed package protection

The CyberPanel custom OpenLiteSpeed core and its CyberPanel/ModSecurity modules
are a paired release. APT still owns the original package paths after the
custom overlay replaces their contents. Upgrading either package can replace
one member of the validated bundle with stock bytes.

The upgrade bootstrap validates an existing custom bundle before package work
and persistently holds `openlitespeed`. It also holds `ols-modsecurity` when
that separate package is installed, because it owns
`/usr/local/lsws/modules/mod_security.so`. An absent optional package is neither
installed nor held. Existing holds are preserved. An indeterminate or partially
installed ModSecurity package state, failed hold, or ineffective hold stops the
upgrade before APT installations/upgrades. A failed second hold may leave the
first protective hold in place; it is not removed on error.

These holds remain after the upgrade and affect unattended package updates.
Updates to the custom core and WAF must come from a verified, ABI-matched
CyberPanel release. Do not simply remove the holds to apply a stock OLS/WAF
update; that can split the bundle again. This guard is scoped to the upgrade
bootstrap and existing custom installations, not every possible external
package-management or fresh-install path.

A stock core alongside a marker-bearing CyberPanel module is now validated
before package work too. A timeout, configuration error, or incompatible-core
ABI diagnostic stops the upgrade with a recovery message. A stock installation
with a harmless unused module file and a valid configuration is not held.

## Existing damage is a separate recovery operation

GitHub #1989 includes a stock OpenLiteSpeed 1.9.4 core, the CyberPanel 2.7.7
module reporting an incompatible ABI, and CRS/configuration errors after APT
replaced package contents. The early guard prevents a repeat upgrade from doing
more package work in that failed state. It does not restore overwritten bytes,
reconstruct missing CRS files, repair site configuration, or establish that the
reporter's production websites are healthy.

Preserve the failed-upgrade logs before retrying (the normal bootstrap clears
old upgrade logs). Capture OS/architecture, installed source ref, package status,
holds, core/module hashes, and bounded native validation output. Useful read-only
checks are:

```bash
cat /etc/os-release
uname -m
git -C /usr/local/CyberCP rev-parse HEAD
/usr/local/lsws/bin/openlitespeed -v
timeout 30 /usr/local/lsws/bin/openlitespeed -t
apt-mark showhold
dpkg-query -W -f='${Package} ${Status} ${Version}\n' openlitespeed ols-modsecurity
sha256sum /usr/local/lsws/bin/openlitespeed /usr/local/lsws/modules/cyberpanel_ols.so /usr/local/lsws/modules/mod_security.so
systemctl is-active lsws lshttpd lscpd
```

An active service can still be running an older mapped executable and have an
invalid on-disk configuration. Do not restart it merely because it is active or
because the upgrader stopped. Confirm the actual service and process identity.
Service aliases vary, so a missing alias alone is not proof of failure.

Recovery requires a snapshot/backup and review of the actual installed files:
restore a verified complete core/module/WAF release for the native OS and
architecture, retain website settings and paid-module state, and restore the
correct CRS release/configuration from a known source when missing. Validate
the complete candidate configuration and a rollback path before service stops.
The ordinary upgrader intentionally rejects invalid starting configuration; do
not remove this check or delete security directives/modules to force it through.
Missing CRS includes and malformed rules can remain after replacing the core.
Do not treat a blanket binary-copy command as recovery for thirty production
websites.

After an authorized recovery, verify native configuration with no errors or ABI
mismatch, required services, real panel login, representative hosted PHP/SQL/TLS
traffic, and WAF normal/attack behavior. Only then treat recovery as successful
and retry the normal upgrade as appropriate.

## Verification on 30 October 2026

- 19 guard regression tests passed. Running the same tests against the prior
  public shell produced 11 failed assertions, including WAF replacement despite
  the core hold and late handling of the already split bundle.
- 51 combined guard, staged-helper, release-consumer and security-bootstrap
  tests passed; shell syntax and whitespace checks passed.
- Read-only inspection of the official Ubuntu noble
  `ols-modsecurity_1.9.4-2+noble_amd64.deb` confirmed its payload is the
  `mod_security.so` path above. Archive SHA256:
  `38dea9723d7456d41d1cdc330582533af1aebec29005f7b1177475552b0ed4c0`.
- A real APT solver simulation with isolated status/lists/cache and official
  noble metadata selected the WAF update from 1.9.3 to 1.9.4 despite a held
  1.9.4 core; holding both packages selected zero updates. No package install,
  service change, or customer-server mutation occurred.
- This is source/fixture/solver acceptance. No new native Ubuntu 24 full upgrade
  or customer recovery is claimed. Earlier Ubuntu 22/26 acceptance belongs to
  the prior release and does not establish this customer's recovery.
