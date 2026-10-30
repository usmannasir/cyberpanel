# Standard backup staging and failure diagnostics

## Current storage and user boundaries

The manual backup API and the standard scheduler both call the same creation
pipeline. `BackupManager.submitBackupCreation` sets the staging directory to
`/home/<domain>/backup/<backup-name>` and starts
`backupUtilities.submitBackupCreation`. The scheduler calls this API through
`backupSchedule.createLocalBackup`; `IncScheduler` moves the completed archive
to the configured destination with `move_local_backup_archive` only afterward.
A destination on a separate disk therefore does not relocate staging or the
initial compressed archive out of the website home filesystem.

`startBackup` copies the website home into staging with rsync as its current
website user. `BackupRoot` prepares privileged metadata separately, transfers
its ownership, and invokes the final tar command as the website user. Filesystem
capacity, inode limits, user quotas, permissions, and concurrent changes may
therefore affect the run before the final destination is used. A later quota
measurement cannot establish which error happened during a previous run.

The scheduler already checks for matching backup workers and bounds waiting
when a worker disappears. Claims that current releases have no worker-liveness
check are incorrect. Do not remove status files or staging from an active run.

## Correctness and diagnostic changes

Previously, rsync's exit status and output were discarded, so an incomplete
copy could advance to database/archive creation. A nonzero rsync exit now aborts
staging. The direct subprocess preserves the existing operating-system user;
it does not use a privileged bridge or bypass quotas. Verbose per-file listing
is disabled while errors are captured.

Previously, archive preparation and tar failures discarded captured output and
reported generic messages. Errors now retain up to the final 4096 characters of
command output in the backup status and server log. These are filesystem-command
diagnostics, not database dump commands or credentials. Error statuses are
shell-quoted when written through the privileged command bridge. Completion
readers require the exact `Completed` status, so that word inside an error's
filename cannot turn failure into success.

This patch does not move staging, change retention, increase quotas, or prove
that any particular customer's historical failure was caused by quota. It also
does not change the standard schedule's generic per-site summary log: detailed
errors are available in the backup status and CyberPanel server log. Status
markers may be removed by polling/cleanup, so preserve the server log and the
failed job's timestamp before retrying.

## Validation

On the previous v3.0.8 source `fec62830256a4822c4fb764a5a9c7f0ff131c386`, five
regression probes failed as expected: ignored simulated quota failure, ignored
real rsync missing-source failure, discarded tar diagnostic, and two false
completion cases (manual status and scheduler).

The patched source passes:

- 76 tests from `python3 -m unittest discover -s plogical -p 'test_*backup*.py'`.
- 21 tests from `python3 -m unittest backup.test_destination_identity
  backup.test_internal_request_security backup.test_schedule_retention
  backup.test_backup_status_outcomes`.
- Python compilation of the four changed production modules and `git diff --check`.

Fixtures run real rsync/tar/move operations only inside owned temporary
directories, with database and privileged-operation boundaries replaced by
fixtures. They verify archive members, partial-archive cleanup, error status,
and no database-success update on failure. No customer server or quota-enabled
filesystem was used; quota exhaustion itself is simulated. A broad backup test
discovery additionally encountered an unrelated GDrive fixture import requiring
configured Django settings; that import is outside this patch's validation.
