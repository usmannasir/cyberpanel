# Sync to Master safety and recovery

The child-domain Sync to Master page loads its own controller and requires explicit confirmation. Database-only, replacement of WordPress content, and merge of changed content now control the actual work. Source and production ownership are both checked. Production wp-config.php, rewrite rules and home/siteurl values are preserved. Incompatible database prefixes or URL layouts require a manual deployment.

Before any production mutation, the worker creates and verifies a files archive and a nonempty database export under `/var/lib/cyberpanel/sync-backups/<unique-id>/`. Directories are root-only (0700), archives and SQL are 0600, and no SQL dump is placed in a webroot. Database exports use `--single-transaction`. Both success and failure status show the recovery location. Backups are retained until an administrator removes them after checking the deployment; monitor available disk space.

Every command is checked. Failed backup, validation, import or file copy stops the job and reports failure. A per-production-path lock prevents overlapping jobs. Lost browser polling does not resubmit a potentially running deployment. Root-side canonical path checks reject symlinked or overlapping content layouts, and copied files use production content ownership.

This is not an atomic deployment or an automatic rollback. Schedule a suitable window for a busy site: writes after the recovery snapshot may be overwritten. A failed import/copy can leave partial changes, with the verified recovery snapshot retained. Files outside the selected WordPress directory and external databases/storage are outside this recovery snapshot.

## Recovery

1. Record the recovery path shown in job status. Confirm the worker has stopped before another sync or recovery. Put the site into a maintenance window and protect any new production writes.
2. As an administrator, inspect `production.tar.gz` with `tar -tzf` and verify `production.sql` is nonempty. Preserve the current partial state separately if needed.
3. Extract the archive into a new private directory first and verify its wp-config.php belongs to the intended production site. Restore the intended production tree, preserving ownership; account for new files introduced by the failed deployment so they do not remain unintentionally.
4. Import `production.sql` using that production site's WP-CLI configuration. Verify home/siteurl, HTTPS, representative content and file permissions before reopening the site.
5. If the process was killed, a `lock-<path-hash>` directory may remain in the backup root. Remove only the exact stale lock after confirming there is no active sync for that path. Never clear all locks as a retry shortcut.

## Verification

Run `python3 -m unittest websiteFunctions.test_staging_sync websiteFunctions.test_sync_master_authorization` and `node --test websiteFunctions/test_sync_master.js`. Authorization tests execute the actual manager methods with isolated database/worker boundaries. The nonroot ProcessUtilities test verifies sudo, quoting and exit-status handling with a simulated socket response.

Opt-in real WordPress/MariaDB integration is `CYBERPANEL_SYNC_INTEGRATION=1 PHP_BIN=/path/to/php WP_CLI=/path/to/wp-cli.phar python3 -m unittest websiteFunctions.test_staging_sync_integration`. It creates only disposable directories, database names and a database user, then cleans them up. It tests successful sync and actual recovery, HTTPS and serialized URLs, database-only, content merge, and a forced backup failure. Its runner is the production ProcessUtilities implementation. It requires local MariaDB administrator socket access and a PHP build with mysqli.

`node websiteFunctions/test_sync_master_browser.cjs` requires Playwright and Chromium. It mounts the actual template and controller with fixture HTTP responses, checking confirmation, completion, recovery-path display and lost-poll behavior. This is UI component acceptance, not an authenticated live-panel/customer deployment.
