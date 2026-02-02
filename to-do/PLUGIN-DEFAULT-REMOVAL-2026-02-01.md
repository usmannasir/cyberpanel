# Plugin Default Removal - 2026-02-01

## Summary
CyberPanel repository no longer requires any plugins by default. Plugins are installed by users from the [Plugin Store](https://github.com/master3395/cyberpanel-plugins) via the CyberPanel Plugin Manager.

## Changes
- **settings.py**: Removed `emailMarketing` from `INSTALLED_APPS`
- **urls.py**: Commented out `emailMarketing` route (plugin installer adds it when plugin is installed)

## Plugin Installation
Users install plugins from: https://github.com/master3395/cyberpanel-plugins

The plugin installer adds apps to `INSTALLED_APPS` and URL routes when plugins are installed via the Plugin Store UI.
