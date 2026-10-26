# HTTP listeners, ModSecurity activation, and OLS upgrade preflight

Reviewed against v3.0.8 `3132f765` for issues #1486, #1611, #1609, and #1711.

## Changes

New website HTTP mappings use each existing non-TLS listener, including multiword names and IPv6 addresses, just as HTTPS mappings already cover secure listeners. Existing mappings/aliases are retained; repeated calls are idempotent. No HTTP listener is an explicit failure. The mapping file is prepared beside the existing configuration and atomically replaced, preserving mode/ownership; a preparation/replacement failure retains the original file.

The GUI custom-OLS ModSecurity installer uses the same release-pinned, checksum/ABI/dependency-checked module downloader as other release consumers. Package-manager exit codes other than zero fail, and compatibility failures cannot leave a success marker. After module configuration is written, the native parser validates it and `lswsctrl restart` activates it. Validation or restart errors are returned to the installer status path. OLS parser status 1 is warnings; status 2 or an `[ERROR]` diagnostic is rejected.

Upgrade validation runs before changes, after replacement of the candidate bundle inside the existing rollback transaction, and after module/Auto-SSL configuration edits before the later stop/start. A failed bundle transaction aborts the upgrade rather than continuing into further service changes. The helper stays in `upgrade.py` because the downloaded bootstrap runs before source activation. This prevents detected configuration errors from being knowingly activated; it does not establish the cause of the old 2.4.4 corruption report or guarantee every runtime fault can be found by `-t`.

## Native acceptance

Owned, network-disabled Ubuntu 22.04.5 x86_64 Docker fixture. Published core SHA256 `736eeb47bd3dc7b2a7206b95106dd735a80b3386118d0b4b17f39f9fa5324f8c`; published external ModSecurity module SHA256 `d196438c0a113ca339706a1e7e37c51026489e4893d06436d6f76252b6e0d6ec`.

* Previous HTTP mapping logic: IPv4 200, second named IPv6 listener 404. Candidate: both 200 with the expected fixture body; native configuration parser passed.
* Actual current `installCompatibleModSecurity` and candidate `installModSecConfigs` methods: module ABI/hash/ldd/atomic installation checks, generated configuration validation, and actual `lswsctrl restart` executed. Only download transport was replaced by a previously checksum-verified local artifact because the container had no network. Benign request 200, dedicated rule 987654 request 403, and that rule appeared in `/usr/local/lsws/logs/auditmodsec.log`.
* Invalid on-disk virtual-host configuration rejected by the actual upgrade validator while the existing master PID and HTTP 200 response remained intact. No full CyberPanel upgrade was performed.
* Official MaxMind `GeoLite2-ASN-Test.mmdb`: lookup of fixture IP 1.0.0.1 succeeded, but ModSecurity GEO.ASN and ENV.ASN were empty. The fixture contains ASN 15169. libModSecurity 3.0.17's geographic extraction has no ASN field and its ENV collection reads process environment, not PHP's per-request `$_SERVER`. ASN integration remains an unsupported capability, not a resolved issue. Do not populate a trusted ASN rule from an untrusted request header.

No production listeners, websites, services, firewall rules, or customer systems were changed. AlmaLinux 9.6 customer behavior and older customer versions were not directly tested. The diagnostic ModSecurity rule proves module activation/blocking/auditing, not a full OWASP CRS acceptance suite.

## Regression command

```
PYTHONWARNINGS=ignore PYTHONPATH=.:install python3 -m unittest \
 plogical.test_http_listener_mapping plogical.test_modsec_installation \
 plogical.test_ols_upgrade_preflight plogical.test_domain_alias_utilities \
 plogical.test_alias_http_mapping plogical.test_alias_https_mapping \
 plogical.test_vhost_deletion_config install.test_custom_ols_platforms \
 install.test_ols_release_consumers plogical.test_upgrade_binaries
```

The isolated native runners and sanitized receipts accompany the support handoff under `outputs/support-remaining16-20261027/`.
