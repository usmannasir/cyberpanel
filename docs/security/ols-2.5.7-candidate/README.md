# Unreleased OLS 2.5.7 candidate

These receipts describe staged artifacts, not published downloads. Do not activate the new consumer pins until the release gates in the manifest pass and every immutable artifact can be downloaded and verified.

The candidate repairs seven WebAdmin parser registrations and applies configured login throttle/history policy before authentication. It retains the custom ABI, existing module and WAF bytes, and PHP 8.3.36 runtime. The PHP application has changed; it is not byte-identical to the prior release.

The explicit parser recovery entrypoint validates the unchanged installed configuration against the paired candidate before stopping the service and preserves complete rollback. Ordinary upgrades continue to validate configuration. Recovery requires the documented Linux namespace/overlay prerequisites and refuses unsupported hosts. No license or entitlement is created by recovery.

Licensed-feature acceptance now passes across six userspaces: 456 feature checks, 54 fresh unlicensed checks, and 48 packaged-PHP autoStart checks, with no failures or skips. See LICENSED_ACCEPTANCE.md and licensed-acceptance.json for fixture corrections, exact artifact hashes and coverage limits. This is not a full production installation/reboot or customer-server test. Immutable publication and download verification remain open before consumer activation.
