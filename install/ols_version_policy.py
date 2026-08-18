"""
Single source of truth for OpenLiteSpeed minimum official version (upstream semver).

Used by install/install.py and plogical/upgrade.py when deciding whether to overlay
CyberPanel-published binaries from ols_binaries_config (fallback for older OLS or
when the LiteSpeed repo package is unavailable).

Upstream version comes from /usr/local/lsws/bin/openlitespeed -v or lshttpd -v,
for example OpenLiteSpeed/1.9.0. That is not the same as CyberPanel bundle filenames
(openlitespeed-2.4.x-* in ols_binaries_config.py).
"""

# Minimum upstream OpenLiteSpeed from LiteSpeed repo before skipping custom binary overlay.
MIN_OFFICIAL_OLS = (1, 9, 0)
