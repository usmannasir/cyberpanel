# Isolated native ASN acceptance

These files test the documented OLS rewrite alternative. They contain no proprietary source or production data. `main.go` generates a synthetic database using MaxMind's official writer; its addresses/ASNs are test fixtures, not real attribution. The extra 88.252.206.167 entry satisfies this published OLS build's database sanity lookup.

Use a disposable Ubuntu 22.04 x86_64 container runtime with OLS dependencies, Python, curl, and the published matching OLS executable. Never point this test at a production installation. No host ports are published; networking stays disabled. Only the test container's network namespace receives source addresses.

Prepare a new fixture directory with this layout:

```
fixture/
  .asn-qa-fixture              # text: isolated ASN QA only
  native-root/
    bin/openlitespeed          # published executable, SHA256 in docs
    bin/litespeed              # relative symlink to openlitespeed
    bin/lswsctrl               # standard OLS control script
    conf/httpd_config.conf     # copy server.conf
    conf/mime.properties       # standard OLS MIME definitions
    conf/vhosts/test.conf      # copy vhost.conf
    Example/html/index.html   # harmless test text
    logs/
    modules/
    share/autoindex/
```

Build the database before starting the worker:

```
cd tests/native/asn_filter
go run . /absolute/fixture/native-root/conf/ASN-QA.mmdb
```

Start the disposable container with `--network none`, mount only this fixture's `native-root` at `/usr/local/lsws`, and keep it alive for the test. Inside it, create the standard `lsadm` user if absent, and assign the fixture document root to `nobody:nogroup`. Configure the following source addresses on **the container's loopback device only**, using its verified PID/network namespace or an in-container network tool:

* 1.0.0.1/32, 1.128.0.1/32, 192.0.2.1/32
* 2001:1700::1/128, 2001:1c00::1/128, 2001:db8::1/128 (IPv6 addresses with `nodad`)

Run the native parser and start OLS inside the container. Then:

```
python3 acceptance.py --fixture-root /absolute/fixture --container OWNED_QA_CONTAINER
```

The runner verifies the network mode, fixture mount, marker, and direct-peer setting before changing fixture files. It checks denied/allowed/unknown IPv4+IPv6, spoofed headers, and missing/corrupt database behavior under basic and strict policies. Database failure tests deliberately reload bad data inside this disposable runtime. The original fixture database and policy are restored in `finally`; a successful run saves `native-acceptance.json` under the fixture directory.

Remove the owned container after review. Do not reuse the synthetic MMDB for production. This is not an end-to-end customer upgrade or a ModSecurity ASN integration test.
