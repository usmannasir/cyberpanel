# OLS 2.5.7 historical QA and released installer revision 2

The original candidate receipts below are retained as historical staging evidence. The tested runtime and installer revision 2 are now published and their ordinary public HTTPS downloads have been hash-verified. Use the [current release notes](../openlitespeed-2.5.7.md), installer-r2-manifest.json and installer-r2-validation.json for current downloads; revision 1 installers are superseded.

The candidate repairs seven WebAdmin parser registrations and applies configured login throttle/history policy before authentication. It retains the custom ABI, existing module and WAF bytes, and PHP 8.3.36 runtime. The PHP application has changed; it is not byte-identical to the prior release.

The explicit parser recovery entrypoint validates the unchanged installed configuration against the paired candidate before stopping the service and preserves complete rollback. Ordinary upgrades continue to validate configuration. Recovery requires the documented Linux namespace/overlay prerequisites and refuses unsupported hosts. No license or entitlement is created by recovery.

Licensed-feature acceptance now passes across six userspaces: 456 feature checks, 54 fresh unlicensed checks, and 48 packaged-PHP autoStart checks, with no failures or skips. See LICENSED_ACCEPTANCE.md and licensed-acceptance.json for fixture corrections, exact artifact hashes and coverage limits. This is not a full production installation/reboot or customer-server test. Immutable runtime and revision-2 installer publication/download verification have passed.
