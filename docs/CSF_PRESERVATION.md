# Upgrading an installation that already uses CSF

The default upgrader stops when `/etc/csf` exists. The explicit `--preserve-csf`
option keeps the installed CSF firewall instead of migrating it to another
firewall. It does not install, update, repair, or uninstall CSF.

Use the current official upgrader and a release that supports preservation:

```sh
bash <(curl -fsSL https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) --preserve-csf --branch 3.0.8
```

Keep an independent console available and confirm existing SSH and panel access
before upgrading. Use this mode when CSF is the sole active firewall manager.
Active firewalld, UFW, or Imunify360 causes the preflight to stop.

Before package, service, or source changes, the upgrader writes a root-only
recovery directory under `/root/cyberpanel-csf-preserve.*`. It contains the CSF
configuration and executable files, systemd unit files, registered panel plugin,
firewall rules, and a manifest of contents, permissions, ownership, activation,
and service state. The directory is retained after success or failure.

The mode skips blanket operating-system package upgrades, automatic Imunify
firewall repair, and automatic Sieve firewall-rule additions. Existing firewall
ports and access policy remain the administrator's responsibility. Normal
CyberPanel dependency and source updates still run. Registered CSF plugin source,
activation, and permissions are carried into the new source tree.

Verification runs before the Python upgrade and after the wrapper finishes.
Packet counters and expiring-rule countdowns are ignored; actual policy changes
are not. If LFD, an administrator, or another process changes deny lists or rules
during the upgrade, verification reports a difference and the command fails.
Do not assume that a reported difference is an upgrade defect or overwrite new
security blocks automatically. Review the retained snapshots from the console.

The updater never automatically restores a firewall snapshot: doing so could
remove a new security block or replace a concurrent administrator change. The
source swap retains the previous installation and automatically rolls it back
if activation fails. Retained file archives and rule snapshots support reviewed
manual recovery; they are not a transaction covering package or database changes.

The panel and cloud upgrade buttons continue to refuse CSF installations because
they cannot provide this explicit preflight and recovery workflow. Do not bypass
their guards or remove `/etc/csf` to make an upgrade proceed.
