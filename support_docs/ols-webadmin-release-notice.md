# OpenLiteSpeed WebAdmin release notices

CyberPanel custom OLS and upstream OLS use different version channels. An
upstream release such as 1.9.4 must not be presented as the compatible update to
a CyberPanel custom 2.5.5 core. A higher custom version number also does not
establish that later upstream security changes are included.

The maintained fix is `plogical/olsWebAdmin.py`, called after WebAdmin installation
and after the new CyberPanel source is activated during an upgrade. WebAdmin PHP
comes from the OLS distribution assets, independently of the custom core overlay.
The known source layout is `admin/html/lib/LSWebAdmin/Product` and
`admin/html/view/dashboard.php` (the published custom source archive uses
`dist/admin/html.open` before installation).

The helper changes only three PHP assets and an informational JSON marker. It
identifies the custom channel from the executable's explicit
`cyberpanel_lsi_api_abi_v1` marker, not from a numerically higher version. The JSON
record is bound to the executable's device, inode, size and modification time;
replacing the executable invalidates the record until it is refreshed. The
dashboard explains that compatible custom updates come through CyberPanel.
Stock OLS notices continue to report genuinely newer upstream versions using
`version_compare`. Equal or older release files do not create update notices.
This metadata is not a security attestation and never suppresses package updates.

All three original source shapes are validated before any installed file is
changed. Unknown or partially missing layouts are reported without altering
files. Existing file modes/owners are retained, replacements are staged, and
backups are kept under `admin/.cyberpanel-webadmin-backup-*`. A write failure
restores already replaced files. Reapplying the helper is a no-op when current.
No OLS executable, module, listener, credentials or service policy is changed.

## Verification, 26 October 2026

Ten regression tests cover custom/stock detection, binary replacement,
idempotency, unknown layouts, symbolic links, copy boundaries and rollback.
The actual WebAdmin distribution was copied to an isolated loopback PHP server
with disposable htpasswd credentials and an isolated HTTPS server environment.
A real login and full authenticated dashboard HTTP response reproduced the
incorrect baseline 1.9.4 notice for custom 2.5.5. The candidate displayed the
custom-channel explanation and omitted that misleading update link. Stock
1.9.3 to 1.9.4 still displayed an update; equal 1.9.4 and newer 1.9.5 did not.
Replacing the fixture binary immediately invalidated the custom marker. The
copied real custom binary hash was unchanged; the listener and temporary tree
were removed. This is authenticated WebAdmin component acceptance, not a full
CyberPanel or OS upgrade and not a claim about upstream security patch coverage.
