# WordPress child conversion database ownership

Converting a cloned/staged WordPress child to an independent website previously left its managed database registered to the original parent. Deleting the parent then deleted the clone database as well.

New conversions inspect the local WordPress DB_NAME and DB_USER with existing WP-CLI as the website Unix user, before deleting the child configuration. After the files move and their permissions are repaired, the managed database owner and matching normalized WPSites owner/path are transferred together in a database transaction. Incoming staging links from the former production site are removed; unrelated staging links are retained. Additional database-user records remain attached to the transferred database.

Conversion refuses ambiguous cases before deletion: shared database names, shared registered accounts or SQL grants on other databases, outgoing staging children, child-specific WPDeployments configuration, unreadable/missing managed WordPress configuration, or a symbolic-link document root (including a trailing slash). Missing deployment path means the established parent-root fallback; malformed paths refuse conversion. These checks do not migrate arbitrary custom application databases or managed deployment configuration.

This change applies to future conversions. It does not repair already-converted database ownership or restore deleted databases. An existing converted site must have its managed database ownership checked before deleting its original parent.

If the post-move ownership/metadata validation fails, conversion reports failure with a warning not to delete the parent. The ownership transaction rolls back, but the existing conversion workflow may already have created the independent website and moved its files. Whole website provisioning is not an atomic transaction; the operator must repair that reported partial state before retrying or deleting either website.

## Validation

- 50 focused tests: `PYTHONWARNINGS=ignore /usr/local/CyberCP/bin/python -m unittest plogical.test_child_database_ownership plogical.test_child_domain_conversion plogical.test_status_file_reservation`.
- Three worker regressions failed on the prior implementation before the fix: transfer before success, preflight refusal before child deletion, and failure instead of false success when ownership transfer fails.
- A real installed CyberPanel QA host tested native Django models, MariaDB schemas/accounts/grants/table data, WP-CLI configuration reading as actual Unix site users, filesystem moves, and the current vhost parent-deletion database/model block. Provisioning was isolated from vhost/DNS/HTTP services. WordPress configuration fixtures included bootstrap discovery files; this was not a full browser-driven clone/provisioning test.
- Baseline parent deletion dropped the clone database. After the fix, parent deletion removed only the original database; the independent site's files, WordPress metadata, SQL login and table marker survived. Shared account/name and unsupported metadata cases refused safely. Injecting failure at staging-link deletion rolled back database and WordPress owner changes.
- Fixture database rows/schemas/accounts, Unix accounts and home directories were removed. No customer server, shared QA service, existing website or host firewall was changed.
