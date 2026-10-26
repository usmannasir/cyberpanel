# Registered plugin preservation during upgrades

The source-swap upgrader now copies plugin directories registered under
`/home/cyberpanel/plugins` into the staged release and preserves their existing
`INSTALLED_APPS` entries and the standard routes written by `pluginInstaller`.
New release settings and core applications remain authoritative. Plugin install
hooks and migrations are not rerun, and no plugin is downloaded automatically.

Invalid registry entries, missing or linked plugin directories, release-source
name collisions, and custom plugin routes stop before source activation. This
avoids silently discarding a plugin or overwriting new core code. A registry
marker does not recreate files lost in an earlier upgrade: recover the plugin
from a trusted backup (the retained `.cyberpanel-previous-*/CyberCP` tree may
contain it), review compatibility, and preserve existing plugin database tables.
Do not replace the new core settings or URL configuration with the old files.

Validation on 26 October 2026 used the actual preservation and atomic activation
helpers against disposable directories on a CyberPanel host. The installed
CyberPanel Python runtime served a real Django plugin HTTP request after the
swap, collected its static asset, preserved the plugin source hash and SQLite
data, and retained the old plugin in the rollback tree. This is targeted upgrade
acceptance; it is not an entire OS upgrade or proof of third-party plugin API
compatibility. Regression tests cover repeated upgrades, disabled plugins,
legacy routes, tuple settings, missing files, collisions, linked directories,
and malformed registry names.
