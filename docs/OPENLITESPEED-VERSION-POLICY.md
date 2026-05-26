# OpenLiteSpeed version policy (CyberPanel v255-dev)

## Two version numbers

| Source | Example | Meaning |
|--------|---------|---------|
| Upstream OpenLiteSpeed | `LiteSpeed/1.9.0 Open` from `openlitespeed -v` | Semver used for policy checks |
| CyberPanel bundle filenames | `openlitespeed-2.4.4-x86_64-rhel9` in [`install/ols_binaries_config.py`](../install/ols_binaries_config.py) | CyberPanel-hosted tarball/module IDs (not upstream semver) |

## Policy constant

[`install/ols_version_policy.py`](../install/ols_version_policy.py) defines **`MIN_OFFICIAL_OLS`**.

- **Fresh install** ([`install/install.py`](../install/install.py)): adds LiteSpeed repo (`repo.litespeed.sh`), installs/upgrades the `openlitespeed` package, reads the installed upstream version, and **skips** overlaying [`ols_binaries_config.py`](../install/ols_binaries_config.py) binaries when `installed >= MIN_OFFICIAL_OLS`.
- **Upgrade** ([`plogical/upgrade.py`](../plogical/upgrade.py)): **`upgrade_openlitespeed_repo_first_then_optional_overlay()`** runs the same order (repo and package upgrade first, then optional CyberPanel overlay only if below minimum).

## Supported platforms for custom fallback binaries

[`plogical/upgrade.py`](../plogical/upgrade.py) `detectPlatform()` maps:

- **rhel8**, **rhel9**, **ubuntu** keys in `BINARY_CONFIGS`
- **EL10** (AlmaLinux/RHEL/Rocky 10): mapped to **`rhel9`** bundles until a dedicated EL10 artifact exists

## Repo verification (audit)

Example AlmaLinux 9 host with LiteSpeed repo: RPM **`openlitespeed-1.9.0-1.el9`** and binary reports **`OpenLiteSpeed/1.9.0`**. Actual packages vary by distro and repo state; if an OS cannot reach `MIN_OFFICIAL_OLS`, the installer/upgrader falls back to CyberPanel-published binaries when downloads and GLIBC checks succeed.

## Changing the default minimum

1. Edit **`MIN_OFFICIAL_OLS`** in [`install/ols_version_policy.py`](../install/ols_version_policy.py).
2. Confirm **`dnf`/`apt`** packages from `repo.litespeed.sh` meet that version on every OS you support **before** raising the tuple.
3. If the repo lags on one OS, either keep a lower minimum or publish updated **`ols_binaries_config`** builds for that OS only.

## Related

LiteSpeed **Enterprise** UI strings (for example in [`upgrade_modules/10_post_tweak.sh`](../upgrade_modules/10_post_tweak.sh)) use separate versioning and are unrelated to OpenLiteSpeed upstream semver.
