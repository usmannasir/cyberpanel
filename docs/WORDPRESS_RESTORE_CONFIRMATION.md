# WordPress restore confirmation

The backup list's Restore link opens the configuration page; that GET request does not itself restore a backup. The destructive action already used an AJAX POST. It now asks for confirmation before changing progress state or submitting the request. Cancelling leaves the form and destination selection intact. The restore action accepts POST only; normal Django CSRF validation remains enabled.

The WordPress Manager paid entitlement decorator remains the first manager boundary. Backup ownership and existing destination ownership are validated before a worker starts. New-site restore requires createWebsite permission and a valid unused website domain. New-site restore paths are restricted to safe relative segments and canonical containment within the new document root; traversal, absolute paths and symlink escape are rejected before dispatch. The home flag is derived from the normalized path. Existing-site restore ignores supplied path/home and uses its authorized WordPress target. These checks do not grant paid access or change prices, licenses, entitlements, or other paid features.

Validation:

- All nine bundled RestoreWPBackup controller copies: eighteen JavaScript tests (cancel and confirm), failing before the confirmation change and passing afterwards.
- Eleven manager boundary tests cover unpaid access, rightful paid owner, foreign backup/target refusal, ambiguous destination, new-site permission, existing domain refusal, and allowed new-site dispatch.
- Two view tests cover GET/HEAD refusal and POST dispatch. Existing WordPress entitlement tests remain passing.
- Actual Django-rendered template with Angular1.6.5/jQuery2.2.4 in Chromium: baseline submitted immediately, cancellation sends nothing, confirmation sends exactly one CSRF POST. The local browser fixture captures the request; it does not restore real data.
- Seventeen native Django HTTP checks use actual session/CSRF middleware, CyberPanel account/website/backup ORM and ACL. Both paid and denied upstream entitlement responses are simulated in-process while executing the current strict lookup/decorator. Valid owner dispatch works; unpaid/foreign-owner/missing-CSRF paths never start a worker. Real filesystem fixtures also verify symlink-escape denial and a valid nested destination. No real entitlement is changed. Worker dispatch is intercepted; this is not an end-to-end restore acceptance test.

All fixture accounts, sites, backup rows and sessions are removed. No customer account or hosted data is modified.

Six dedicated path tests cover valid nested/root paths, malformed/traversal/shell-form inputs, escaping symlinks and a symbolic document root. The broader legacy WordPress installer is not claimed to have been audited by this restore-entrypoint change.
