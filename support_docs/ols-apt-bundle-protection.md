# Custom OpenLiteSpeed package protection

The CyberPanel custom OpenLiteSpeed core and its CyberPanel/ModSecurity modules
are a paired release. The package manager still owns the original package paths
after the custom overlay replaces their contents, so a package update can
replace one member of the validated bundle with stock bytes. The CyberPanel
module then disables itself (`incompatible OpenLiteSpeed core ABI`).

## What is protected, and when

`plogical/olsPackageProtection.py` applies a lasting protection after a fresh
installation and at every upgrade. It acts only when the installed core and the
CyberPanel module both carry the CyberPanel ABI marker; stock installations,
platforms without a custom bundle and LiteSpeed Enterprise are left alone.

| Family | Protection | Packages |
|---|---|---|
| Ubuntu | `apt-mark hold` | `openlitespeed`, and `ols-modsecurity` when installed |
| AlmaLinux, RHEL, Rocky, CloudLinux, CentOS, openEuler | names merged into the `exclude` key of `[main]` in `/etc/dnf/dnf.conf` (`/etc/yum.conf` where dnf.conf is absent), below the line `# cyberpanel-ols-package-protection` when the key is new | the RPM owners of the core and of `mod_security.so` |

It records what it added in `/etc/cyberpanel/ols-package-protection.json` and
`python3 /usr/local/CyberCP/plogical/olsPackageProtection.py --status` reports
the current state. A step that cannot complete is reported as a warning and
retried at the next upgrade; it never fails an installation or upgrade.

The upgrade bootstrap additionally validates an existing bundle before package
work and holds the Ubuntu packages itself, because it runs before the new
source is in place. On RPM systems it excludes the owners from its own
`yum update`. An indeterminate or partially installed ModSecurity package
state, failed hold, or ineffective hold stops the upgrade before package work.

These protections remain after the upgrade and affect unattended package
updates. Updates to the custom core and WAF come from a verified, ABI-matched
CyberPanel release. Do not remove the protection to apply a stock OLS/WAF
update; that splits the bundle again.

What the protection does not stop: an administrator who names the package
explicitly (`apt-get install --reinstall openlitespeed`, `dpkg -i`,
`dnf --disableexcludes=main reinstall openlitespeed`). On RPM systems
`dnf remove openlitespeed` reports "No packages marked for removal" while the
package is excluded; use `--disableexcludes=main`, or release the protection
first with `olsPackageProtection.py --release`. Switching to LiteSpeed
Enterprise from the panel does this itself.

## A vendor core beside the CyberPanel module is repaired by the upgrade

When a package update has already replaced the core, the ordinary upgrade
(terminal or panel) restores the bundle with its existing transaction: the
complete core/module/WAF set is staged and checksum-verified, the exact
previous files are kept, the configuration is validated with the CyberPanel
core, and the previous files are restored and restarted when that fails. The
vendor core, WAF and operating-system minor version are not fingerprinted: any
of them is accepted on a platform with a bundle. The control script,
environment file and systemd unit must be the ones the vendor packages ship,
as for every bundle upgrade.

The upgrade stops before any package work when

- OpenLiteSpeed reports configuration errors the vendor core did not cause
  (the complete lines are printed; correct them and run the upgrade again);
- no bundle exists for the platform (Ubuntu before 22.04, non-x86_64);
- a stock-recovery policy file exists on anything but Ubuntu 22.04.

It stops later, before any OpenLiteSpeed file is changed and after the
upgrade's ordinary operating-system package step, when the service cannot be
identified: an edited control script or systemd unit, a control script left by
an earlier recovery attempt, drop-ins, a master started outside its unit, or a
stopped service with an active watchdog. Package holds set by that run are
released again, and the reason is printed.

Ubuntu 22.04 keeps native AutoSSL inactive after such a repair through
`/usr/local/lsws/.cyberpanel-stock-recovery-policy`, as the published Jammy
recovery does. A policy file that already exists beside a vendor core is kept
and the policy-aware core is restored. Elsewhere AutoSSL follows the existing
configuration.

A stock installation with a harmless unused module file and a valid
configuration is neither held nor converted.

## Damage beyond the replaced core

GitHub #1989 includes a stock OpenLiteSpeed 1.9.4 core, the CyberPanel 2.7.7
module reporting an incompatible ABI, and CRS/configuration errors after APT
replaced package contents. The upgrade restores the bundle; it does not
reconstruct missing CRS files or repair site configuration, and it stops before
any change while such errors are reported.

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
