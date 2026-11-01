# PHP session cleanup safety

CyberPanel's existing setup script changes session paths and lifetimes,
recursively changes session-file permissions and restarts services. It also
installed a cron helper with hard-coded `find -cmin 120` change-age deletion
(the exact 120-minute bucket, not all files older than 120 minutes), independent
of application lifetime. Its calculated
global PHP lifetime was not used. Even using that global lifetime would be unsafe:
applications can set a longer `session.gc_maxlifetime` for the same directory.

The installer now generates a no-op rather than a global file purge. All other
existing setup behavior is unchanged in this narrowly scoped correction; the
legacy path/lifetime overrides, recursive permission changes, and service
restart still require separate design and validation. They are not claimed safe
or fixed by this patch. The upgrader retires only the byte-exact shipped 120-minute
helper, retaining its original bytes in a SHA256-named sibling backup. Existing
cron entries reach a harmless no-op; crontabs and unknown/custom helpers are not
rewritten. Links, hard links, non-root ownership and writable installation paths
are refused before replacement. Retirement is atomic and a second run is a no-op.
Expected filesystem or validation failures produce an explicit "retirement not
verified; manual review required" warning and do not abort the overall upgrade.
The warning does not claim the cleaner was unchanged: durability verification
can fail after replacement. The low-level retirement function remains strict.

The migration prints an explicit warning: operators must configure appropriate
application-specific garbage collection and monitor disk usage. Retiring the
unsafe generic purge can increase retained session storage. No universal expiry
can be inferred safely, and this change does not guarantee bounded disk usage.
PHP's own GC may also use the shortest application's lifetime when applications
share a path; use separately owned application directories and an explicit
application-compatible cleanup policy when different lifetimes are required.

This is a safety correction, not full resolution of GitHub #1091. The new upgrade
retirement helper does not initialize paths, migrate/purge sessions, or override
custom paths/lifetimes. The existing fresh setup entrypoint still does its prior
initialization; no new Python dependency was introduced into that shell path.
It does not clean a fixed prefix, so there is
no partial-scan starvation claim. An unknown historical cleaner is left intact
with a warning and must be reviewed separately.

Validation must include executing the retired helper against real PHP-created
short- and long-lifetime session fixtures and proving all bytes, modes and
timestamps survive. Tests use private temporary installation trees and session
directories, not production paths. No live installer/upgrade or user-server
acceptance is implied by these helper tests.
Fixture ages are modification times set with `utime`; they do not reproduce the
legacy cleaner's change-time deletion. These tests establish no-op preservation,
not a before/after reproduction of the original deletion.

Publication: apply this patch to the current release and stable trees; run the
targeted safety tests and adjacent upgrade/installer tests. The new helper, setup
entrypoint, and post-source-copy upgrade call must be published together. Never
run the legacy setup script as a migration. For rollback, restore only the exact
backed-up helper after reviewing its destructive policy; do not automate rearming
the purge, and do not promise that deleted sessions can be recovered.
