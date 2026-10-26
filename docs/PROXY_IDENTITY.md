# Panel proxy identity and phpMyAdmin callbacks

The panel previously accepted `CF-Connecting-IP` from any socket peer. That let a direct origin request choose its session IP binding; it did not supply a password, API token, MFA response, or phpMyAdmin grant.

`plogical/clientIP.py` now accepts that header only from Cloudflare's published IPv4/IPv6 networks, verified against https://www.cloudflare.com/ips-v4 and https://www.cloudflare.com/ips-v6 on 2026-10-26. The list is shipped with reviewed source; requests never fetch proxy configuration. A trusted edge must provide one valid address. Direct clients, generic local reverse proxies, and arbitrary `X-Forwarded-For`/`X-CyberPanel-Peer` headers do not gain forwarded-address trust. Installations needing another reverse proxy must terminate their address trust at a separately reviewed boundary; localhost alone is not such a boundary. Sessions established using an untrusted forwarded address may require a fresh login.

Panel password login, API login, cloud access, middleware and phpMyAdmin use the same resolver and canonical IPv4/mapped-IPv4 or IPv6 /48 binding. LOW security continues to permit changes to a valid address; it does not skip authentication, MFA, grant validation or current ACL checks.

## Internal phpMyAdmin transport

PHP's two loopback POST callbacks authenticate their actual socket peer and optional Cloudflare header with HMAC-SHA256. The signature includes the version, timestamp, exact method/path, panel cookie, peer, forwarded address and SHA256 of the encoded POST body. Python accepts it only on the two fixed phpMyAdmin callback paths, from 127.0.0.1/::1, within 30 seconds. A generic loopback proxy cannot manufacture that signature.

This is bounded attestation, not a general nonce/replay cache. The handoff still consumes its one-use token. Grant validation is read-only and repeats current principal, ACL, session and database-authorization checks; replaying the same valid validation request during its short window grants no new session or authority. Cross-session, cross-path, changed-body and expired signatures fail. The private key never appears in an HTTP request or response.

Two matching private key files allow existing separate service accounts to read only their own copy:

- `/etc/cyberpanel/pmaPeerKey`: root:cyberpanel 0640, Python verifier.
- `/etc/cyberpanel/pmaPeerKeyPHP`: root:lscpd 0640, PHP signer.

Both are outside the source and LSCPD trees targeted by legacy recursive permission repairs. No service group membership changes. Missing, invalid, symlinked, hardlinked, group-writable or world-accessible keys fail closed. Repeat upgrades preserve the key; mismatched copies stop activation instead of silently rotating it. Do not delete one copy as a routine repair. Restore matching private copies from a trusted backup if needed.

The upgrade invokes the new staged helper before `activate_source`. It preserves the complete existing phpMyAdmin application and replaces its two authentication helpers with the new release copies, retaining the database host/port. Failures leave the old source active. The existing previous-installation rollback remains available and the external key survives rollback. Fresh install/PMA setup provisions keys before copying the signer.

## Validation scope

The isolated native acceptance ran on the owned Ubuntu QA server with installed CyberPanel Python/Django and native LiteSpeed PHP cURL under `lscpd`. It created only disposable real ACL/admin/GlobalUserDB records and private file sessions. Actual HTTP login/API/cloud handlers and security middleware accepted valid credentials and ignored forged address headers. Actual signed PHP callbacks passed direct and IPv4/IPv6 Cloudflare-address scenarios, consumed a handoff only once, rejected wrong grants/unsigned peers, and rejected a suspended principal. Cloudflare peer addresses were supplied through isolated PHP server variables; this was not a request through a live Cloudflare edge. The test did not upgrade or reboot the installed host, change a firewall, or touch customer servers. Fixture records, keys and the loopback listener were removed.

Additional regression coverage checks CIDR boundaries, malformed/multiple addresses, mapped IPv4, safe legacy session prefixes, all session creators, private-key preservation and unsafe filesystem refusal, source-staging rollback boundaries, native PHP/Python signature agreement, vendor phpMyAdmin authentication, configurable panel ports and authenticated sign-on. Sanitized support receipts record exact counts and source revisions.
