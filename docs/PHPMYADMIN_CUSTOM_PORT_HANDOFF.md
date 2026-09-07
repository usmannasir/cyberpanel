# phpMyAdmin signon with a custom panel port

The phpMyAdmin signon bridge validates each one-time handoff with the local
CyberPanel service. It reads the panel listener port from
`/usr/local/lscp/conf/bind.conf`, the same file written by the panel port settings
page and installer. A port change therefore takes effect without reinstalling
phpMyAdmin.

The supported configuration is `*:<port>`, with a decimal port from 1 to 65535.
An absent or empty file retains the default port 8090. An existing file that
cannot be read, or nonempty malformed content, prevents signon. The validation
destination always uses HTTPS, `127.0.0.1`, and the fixed
`/dataBases/consumePHPMYAdminHandoff` endpoint. Browser host and forwarding
headers do not select the destination. A failed custom-port validation is not
retried against the default port.

Install and upgrade already copy `plogical/phpmyadminsignin.php` into
`public/phpmyadmin/phpmyadminsignin.php`. A targeted deployment must refresh both
copies and preserve the served copy's database host and port customization;
`install.database_consumers.configure_phpmyadmin_signon` supports remote MySQL
configuration. The database connection port and panel listener port are
independent.

Run the signon regression tests with PHP and the cURL extension available:

```sh
php tests/test_phpmyadmin_signin_handoff.php
php tests/test_phpmyadmin_signin_rejects_invalid.php
php tests/test_phpmyadmin_signin_logout.php
php tests/test_phpmyadmin_signin_port.php
php tests/test_phpmyadmin_signin_port_transport.php
python3 -m unittest databases.test_phpmyadmin_handoff install.test_database_consumers
```

For live acceptance, use a backed-up disposable panel with a valid hostname
certificate. Create a disposable database through the panel, verify automatic
phpMyAdmin signon and database visibility, refresh, and sign out. Repeat at the
default port, port 2083, and port 2096, restarting LSCPD after each port change.
Confirm invalid and replayed handoffs create no signon session. Restore the
original listener configuration and remove the disposable database after the
checks. Record browser errors, service health, and source/served file hashes.
