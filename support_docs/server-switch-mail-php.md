# Server switching and mail child PHP selection

Fixes GitHub #1985 and #1986.

- Switching a master or child website saves the selected PHP version in its model.
- Returning a child to OpenLiteSpeed reinstalls its existing certificate, as the master-domain path already did. A certificate-installation failure is reported instead of a successful conversion.
- A new mail child uses its parent's PHP version if the corresponding executable is installed. Otherwise it selects the newest installed executable reported by the PHP inventory. Missing and non-executable runtimes, including the inventory's fallback list, are rejected. If none is available, creation stops with an actionable error instead of generating a missing PHP handler.

## Validation

Eleven new regression tests cover parent preference, version ordering, absent/non-executable binaries, autodiscover argument wiring, parent/child PHP persistence, child SSL, and SSL error reporting. Thirty-six existing conversion/mail/TLS tests, six optional-service/alias tests, and sixteen isolated SQLite mail-deletion tests passed.

Live SSH acceptance on an owned Ubuntu 24.04 CyberPanel 3.0.7 lab loaded the current 3.0.8 baseline and candidate methods only into a test process. No installed source replacement or full upgrade was performed. Disposable master/child records and vhosts were created through CyberPanel. The baseline reproduced the stale PHP model value and missing child `vhssl` block. The candidate wrote PHP 8.3 to both models and configurations, and a TLS-validated HTTPS request executed PHP 8.3.33. With PHP 7.3 absent, installed-runtime selection and native mail-child creation produced PHP 8.3 in the model, configuration and actual HTTP response.

The Apache backend was not installed on the lab: the pure-OpenLiteSpeed conversion path was invoked directly. The mail-services orchestration was covered by regression tests; the lab lacks configured mail services, so live acceptance exercised runtime selection and native child provisioning rather than mail SSL/Dovecot/Postfix configuration. These checks do not establish a full customer-host upgrade or end-to-end Apache-to-OLS migration.
