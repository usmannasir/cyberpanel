# Preserve installed PHP branches during upgrades

The upgrade PHP-package step now upgrades only exact installed `lsphpNN`
packages and their installed extensions. It uses `apt-get --only-upgrade
--no-remove install` or the RPM manager's `update` operation, without package
wildcards. A removed base runtime excludes leftover packages from that branch,
so updating an orphaned extension cannot pull the removed runtime back in.
Empty inventory never becomes a general distribution upgrade. Query and package
transaction failures propagate instead of falling back to a blanket install.

The existing required PHP 8.3 setup and panel LSAPI binary selection remain in
their dedicated upgrade steps. This change does not alter site PHP selections,
remove old installed runtimes, or claim any particular vendor package is patched.
Administrators remain responsible for checking package patch provenance and the
runtime used by live workers. A site configured for an intentionally removed
PHP branch is not automatically switched or repaired by reinstalling that branch.

The legacy PHP 7.4 development-package repair now runs only when its runtime
executable is present, on both the Ubuntu and CentOS 7 paths.

Validation includes package inventory/transaction regression checks, adjacent
installer/upgrade checks, and real package-manager transactions with synthetic
PHP packages in disposable containers. Local test repositories deliberately offer
a removed branch alongside an installed branch. These prove package-selection
and dependency behavior, not a full CyberPanel upgrade or LiteSpeed vendor build
compatibility. The owned installed CyberPanel host's package inventory was
inspected without executing an upgrade transaction there.
