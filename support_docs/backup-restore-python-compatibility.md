# Backup restore compatibility with older Python tarfile

A backup restore running as root on older Python versions can fail with
`getgrnam() argument 'name' must be str, not None` during archive extraction.
The portable extraction path previously set archive owner names and numeric IDs
to `None`. Older tarfile implementations pass the name directly to `getgrnam`;
newer implementations accept `None` as an instruction to ignore ownership.

The fallback now uses numeric UID/GID `-1` with `numeric_owner=True` and empty
owner names. POSIX ownership calls leave the existing owner unchanged for `-1`,
so archive-provided users/groups are never resolved or applied. The later
website ownership remapping remains responsible for the destination site UID/GID.
Archive metadata is copied before sanitization. Existing path/link validation and
special-mode-bit removal remain in place, and the Python 3.12+ data-filter path
is unchanged.

Python documents `None` ownership metadata support as a Python 3.12 addition:
https://docs.python.org/3/library/tarfile.html#tarfile.TarInfo.uid

## Verification

The released pre-fix code reproduced the exact exception in the official
Python 3.8.10 slim image (digest
`sha256:6c0b171f6e4cbd880a972a36b77f18ccb03c3f32a6385e3306e289e9ddbfbcfe`).
Three existing integrity tests failed before the fix. The added regression also
failed because it prohibits archive owner-name lookups. Tests verify private
file modes, numeric ownership, unchanged original archive metadata, traversal
and link rejection, and whole-home ownership restoration.

After the correction, all 38 focused tests passed on actual Python 3.8.10 and
3.12.3. The 18 integrity tests also passed on Python 3.10.12. No customer server,
private archive, pCloud account or credentials were used.

Run the focused suite with:

```
python3 -m unittest plogical.test_backup_integrity \
  plogical.test_restore_home_ownership plogical.test_backup_restore_ssl \
  plogical.test_backup_command_outcomes
```

This verifies a Python extraction compatibility defect. It does not establish a
particular customer's traceback, package build, archive or third-party storage
integration. Request the failing traceback and exact runtime/build to confirm
that customer's cause.

## External archive upload jobs

An rclone `--min-age 5m` filter selects files by age; it does not establish that
an archive writer finished. The normal backup producer currently writes directly
to the final `.tar.gz` pathname and marks completion after tar succeeds. A
paused writer can therefore leave an incomplete archive old enough for the filter.
Use producer-confirmed completion and an immutable upload handoff, with archive
validation and restoration tests, when designing external jobs. A custom script
must be reviewed and tested before recommending a specific change. No native
pCloud integration or customer's rclone workflow is validated by these tests.
Rclone's age-filter reference: https://rclone.org/filtering/#min-age-dont-transfer-any-file-younger-than-this
