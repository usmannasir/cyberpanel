# Combined website and mail storage

CyberPanel's storage statistics include the website home and the mail domain directories owned by that website, including mail for its child domains. The mail directories remain under `/home/vmail` with their existing ownership. Updating statistics does not enable a hard limit.

For ordinary web and mail writes, an administrator can explicitly enroll those directories into one filesystem project quota. The package's disk and inode limits then apply to their combined allocation. Existing website user quotas remain separate protection.

## Requirements

- Web and mail storage must be on the **same writable ext4 or XFS filesystem**, with a stable UUID and project quota accounting and enforcement already enabled.
- Enrollment accepts real directories and regular files. It refuses symlinks, special files, nested mounts, external hard links, foreign project IDs and child website paths outside the website home.
- Existing storage roots must be present and match their recorded identities. Enrollment does not reconstruct missing mail data or silently adopt replacement directories.
- The affected website and mail writers must be quiesced for enrollment. Include mail delivery, IMAP writes, website processes, scheduled jobs and file transfers for the selected scope. The command does not stop them for you.

The helper does not enable filesystem features, remount filesystems, edit fstab, change existing UID/GID ownership or rewrite Dovecot configuration. A server lacking project-quota support continues to receive corrected statistics and its existing user-quota behavior. Configure any missing filesystem prerequisites through a separately reviewed maintenance procedure.

## Review and enroll

Run these commands as root. Replace `example.test` with the website's domain.

```sh
/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/storageQuota.py status --website example.test
```

After quiescing the affected writers, create a plan:

```sh
/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/storageQuota.py plan --website example.test
```

The result names a private, root-owned `plan_file` under `/var/lib/cyberpanel`. Review that JSON file. It identifies the website, web/mail roots, filesystem, package policy, inode count and inventory fingerprint. It contains metadata, not message contents. Keep writers quiesced while reviewing and applying it.

Pass the exact returned path to enrollment:

```sh
/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/storageQuota.py enroll --website example.test --plan /var/lib/cyberpanel/storage-plan-7-EXAMPLE.json --quiesced
```

`--quiesced` confirms that you have stopped the affected writers; it is not an automatic stop action. The command checks the plan against current ownership, policy, mounts and inode inventory. A stale plan fails before assignment. Prepare a new plan while writers remain quiesced if legitimate storage changes invalidated it.

Enrollment retains existing file attributes, assigns the project's identity, enables inheritance on its directories and applies both limits. It reports success only after verifying the enrolled scope and kernel limit readback. Run `status` again before resuming writers.

## Status and package changes

| State | Meaning |
| --- | --- |
| `unconfigured` | No combined enrollment, limits disabled/unlimited, or manually disabled enrollment. Check `enrolled` and `reason`. |
| `active` | Scope, package policy and kernel limits were verified at that check. `enforced` is true. |
| `pending` | Enrollment or a policy operation did not finish verification. |
| `unsupported` | Ownership, roots, filesystem capability or another verification requirement failed. |

The panel caches the last statistics/status refresh; it is not a live filesystem monitor. A cached successful status does not prove that a later administrator change preserved the configuration.

For an enrolled website, supported package edits/reassignment update its project limits through the checked helper in addition to existing user-quota handling. A disabled package enforcement setting clears the owned project's hard limits through the same checked transition. A zero disk or inode allowance means unlimited for that resource, not zero permitted storage.

New mail domain directories for enrolled websites are tagged while empty, before mailbox activation. Existing unregistered mail data requires maintenance review. Registered mail roots cannot be reused by another website without ownership review. The panel retains an enrolled mail domain when its last mailbox is deleted so its storage ownership remains explicit; ordinary unregistered domain cleanup keeps its previous behavior.

## Mail delivery at the limit

When combined storage is full, new website writes and mail storage operations can fail even if an individual mailbox still has room. Existing messages remain stored. Free space or increase the website package allowance before retrying a failed write.

This feature preserves Dovecot's existing delivery policy. In Dovecot 2.4, `quota_full_tempfail` defaults to `no`: a delivery failure recognized as a quota error is permanently rejected. With LDA's `-e` option, this quota rejection returns exit 77 and a quota-specific error. An administrator who wants delivery deferred for retry can select `quota_full_tempfail=yes`; the LDA then returns temporary failure (exit 75). Review the server's delivery configuration and queue policy when choosing this setting. CyberPanel enrollment does not change it automatically.

The filesystem also affects the delivery outcome. Ext4 project exhaustion reports `EDQUOT`, which Dovecot recognizes as a quota error. XFS project exhaustion can report `ENOSPC` while the underlying filesystem still has free capacity. In the tested Dovecot 2.4.2 Maildir setup, this XFS error produces temporary delivery failure (exit 75) under either setting. Check the delivery result and the affected project's limits when diagnosing a "No space left on device" mail error; do not assume that the entire disk is full.

See Dovecot's [quota_full_tempfail setting](https://doc.dovecot.org/2.4.0/core/summaries/settings.html#quota_full_tempfail) and [LDA manual](https://doc.dovecot.org/2.4.0/core/man/dovecot-lda.1.html). Delivery outcomes must be checked separately from quota enforcement: a denied write does not by itself prove that a message was queued for retry.

## Failed operations and recovery

The root-owned registry is `/var/lib/cyberpanel/storage-quotas.json`. It records project IDs, root identities and operation states. Project IDs are not reused. Preserve this registry with server configuration backups; do not copy another server's project mapping onto existing storage.

An interrupted enrollment or failed limit readback leaves a `pending` record instead of claiming success. If the website, roots and filesystem identities are unchanged, keep writers quiesced, create a fresh plan and rerun enrollment. It resumes the same project ID. Existing quota limits and assigned attributes may already have changed; inspect the reported error and current status rather than assuming rollback.

If roots were replaced, moved or reassigned, or domain membership was removed outside the supported flow, automatic enrollment refuses to guess ownership. Preserve the recorded state and review the database ownership, directory device/inode identities and filesystem mapping. Restore the intended original scope through a reviewed recovery procedure before retrying. Do not delete the registry or clear an unknown project's attributes to bypass this check.

The existing restore routines replace storage roots and are blocked for enrolled websites, including pending or manually disabled enrollments. Restore to an **unenrolled destination**, verify its data, and enroll that destination during maintenance.

To deliberately remove this feature's limits from a still-verifiable owned scope:

```sh
/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/storageQuota.py disable --website example.test --quiesced
```

This clears only the registered project's limits after scope verification. It retains its identity, directory attributes and registry record; user quotas and the package model are unchanged. Existing mail remains accessible, but new domain enrollment/package integration requires a fresh maintenance enrollment before it can claim combined protection again.

## Accounting and protection boundaries

Usage represents allocated filesystem bytes, not Dovecot's virtual uncompressed message size. It includes mail indexes, Sieve files and other data under the owned mail domain roots. Combined bytes are summed before rounding to displayed MiB. Mail forwarding aliases are charged where a local copy is actually stored, without a separate charge for an alias name. Unattributed orphan mail directories are not assigned to a website by name alone.

This feature limits ordinary web/mail capacity. **It is not an isolation boundary against a tenant running arbitrary code as a Unix file owner.** Linux can let an inode owner change its project ID or inheritance attributes. Keep existing user quotas; additional isolation controls require their own design. No user-namespace, syscall-filtering or server security changes are made by this feature.
