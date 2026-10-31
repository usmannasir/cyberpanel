# Unreleased OLS 2.5.7 candidate

These receipts describe staged artifacts, not published downloads. Do not activate the new consumer pins until the release gates in the manifest pass and every immutable artifact can be downloaded and verified.

The candidate repairs seven WebAdmin parser registrations and applies configured login throttle/history policy before authentication. It retains the custom ABI, existing module and WAF bytes, and PHP 8.3.36 runtime. The PHP application has changed; it is not byte-identical to the prior release.

The explicit parser recovery entrypoint validates the unchanged installed configuration against the paired candidate before stopping the service and preserves complete rollback. Ordinary upgrades continue to validate configuration. Recovery requires the documented Linux namespace/overlay prerequisites and refuses unsupported hosts. No license or entitlement is created by recovery.

Paid-feature acceptance remains open pending a legitimate test entitlement. The core/WAF and verified-TLS HTTP/2 and HTTP/3 checks do not substitute for that gate.
