# phpMyAdmin follows the current panel session

The one-time, 120-second login handoff now issues a separate grant bound to the
originating CyberPanel session, account, database username and current database
access token. The signon callback checks that grant before phpMyAdmin uses its
stored credentials on each authenticated request. Validation does not renew the
panel session or return database passwords.

Panel logout, session expiry, session-key rotation, suspended/deleted accounts,
revoked database access, changed database access tokens and rejected IP changes
require another login through the panel. The panel's LOW security setting still
allows network changes; HIGH retains its existing exact IPv4 and three-group
IPv6 comparison. Existing unbound phpMyAdmin sessions require reauthentication.
A new handoff replaces that panel session's previous grant.

phpMyAdmin uses its supported `SignonScript` hook:

```php
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonScript'] = __DIR__ . '/phpmyadminsession.php';
```

Install and upgrade copy both `plogical/phpmyadminsignin.php` and
`plogical/phpmyadminsession.php` into `public/phpmyadmin`. The callback includes
only the bridge's pure helper functions and preserves phpMyAdmin's PHP session,
CSRF/HMAC state and customized database host/port. A missing or failed validator
does not fall back to independent session authentication.

The validator is the fixed HTTPS loopback endpoint
`/dataBases/validatePHPMYAdminSession`. Its panel port comes from the same
validated `bind.conf` configuration as the original handoff. Browser host and
forwarding headers never select the destination. No MySQL connection or schema
change is needed for validation; current authorization comes from the panel
account, ACL and GlobalUserDB record. MySQL's own database grants continue to
govern queries.

For targeted deployment, back up the served PHP files and `config.inc.php`,
preserve ownership/modes and any database endpoint customization, install the
callback and bridge, and add SignonScript to the existing signon server entry.
Deploy the Django endpoint/helper together and verify the served configuration
actually selects the callback. Copying PHP alone or adding Django middleware
does not enable this protection. Do not replace a customized configuration with
the sample. Rollback restores the exact saved files/configuration together.

Run the existing checks from `PHPMYADMIN_CUSTOM_PORT_HANDOFF.md`, plus:

```sh
python3 -m unittest databases.test_phpmyadmin_session databases.test_phpmyadmin_session_views install.test_phpmyadmin_session_setup
python3 tests/run_phpmyadmin_session_tests.py /path/to/php
```

The latter loads the actual authentication classes from the bundled 5.2.1 ZIP
with private fixture sessions, captured HTTP transport and no database access.
Its baseline intentionally demonstrates that the old independent session mode
continues accepting credentials; the candidate must reject those cases. A
hash-checked vendor directory can be supplied using `PMA_TEST_VENDOR_DIR` on
isolated staging systems where the complete ZIP has not been copied.

Owned disposable browser acceptance must additionally verify ordinary signon,
fresh navigation and AJAX requests, panel logout/reauthentication, HIGH/LOW IP
policy, custom panel and database ports, service health and cleanup. A previously
rendered browser tab alone does not establish whether a new request was accepted.
