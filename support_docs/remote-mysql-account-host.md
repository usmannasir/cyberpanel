# Remote MySQL application-account host

The remote installer uses the supplied `--mysqlhost`, `--mysqlport` and
`--mysqluser` for its administrative connection. The host part of the application
account must match the source seen by that MySQL server, which can differ from
the panel's public IP on private networks or behind address translation.

Before creating a database or user, the installer now queries `USER()` on that
administrative connection and takes its host component. It refuses empty or
wildcard-containing values rather than silently granting access from another
host. Local installations retain `localhost`. Passwords and SQL values remain
bound parameters. Re-running installation refreshes the application password on
the same observed account.

This does not select a network interface or alter routing. The supplied database
host determines the destination, and the operating system/network determines
the route. It also does not rename the application database/account: these are
still `cyberpanel`, separate from the supplied administrative identity. Deploying
multiple panels on one shared application database is not made safe by this
change; separately configurable application database identities remain outside
this fix. Existing installations' grants are not changed by upgrading code.

## Verification

- `python -m unittest install.test_mysql_utilities install.test_env_generator`
- Opt-in real-server regression in `install.test_remote_mysql_integration`, using
  the documented `CP_TEST_MYSQL_*` environment variables. It creates and removes
  uniquely named fixture databases/accounts and executes real application SQL.
- Disposable MySQL 8.0 test: old installer created the account for a deliberately
  different public address and application authentication failed; updated code
  used the server-observed private Docker bridge address and application
  authentication/read/write succeeded. A supplied custom administrative user and
  password refresh on retry were verified. The container was removed afterward.

No public/customer database or installed service was modified during testing.
