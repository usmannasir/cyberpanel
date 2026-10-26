# Checked DNS cleanup during website deletion

PowerDNS Records, Comments, Cryptokeys and Domainmetadata use integer domain_id columns, so deleting a Django Domains row does not cascade through those models. Previously the website deletion helper also suppressed every DNS deletion exception. A website could disappear and report success while a zone and DNS child rows remained.

Zone deletion now locks the zone and deletes its current PowerDNS child rows and the zone in one transaction. A missing zone succeeds for retry purposes. A real deletion error is logged and reported. Both OpenLiteSpeed and Enterprise website deletion check that result before deleting hosted databases or the Website row. Existing pending/error handling remains in place.

The whole website deletion is not transactional: vhost configuration, WordPress metadata or other earlier cleanup may already have changed when a later operation fails. An explicit failure means inspect the log and repair the reported condition before retrying. This change does not disable foreign-key checks or automatically repair incompatible legacy schemas or unrelated mail/Unix-account artifacts.

Validation:

- Seven focused DNS/deletion-order tests plus existing website/database/Unix-account/vhost regression suites.
- Twelve native checks use real CyberPanel MariaDB models, SQL schemas and a disposable restrictive foreign key. Baseline reports success while leaving the zone and all four child-row types. Candidate failure rolls back all DNS child deletions and retains Website/database metadata and actual SQL data. Removing the fixture's external restriction permits retry; zone/children/schema/website are removed and the same domain can be recreated.
- Vhost files, service restarts and Unix-account operations are isolated in this native fixture. No full host installation/deletion or customer environment was tested.
- Sixteen isolated SQLite mail-deletion ORM regressions pass. The combined application regression suite has eighty-nine tests, eighty-eight passing and one existing environment-specific skip.

Generated website/zone rows, DNS children, SQL schemas and the restrictive fixture table are removed after acceptance. Existing host services and websites are preserved.
