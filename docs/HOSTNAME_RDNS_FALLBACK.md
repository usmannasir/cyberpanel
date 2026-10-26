# Hostname rDNS service failure

Hostname setup retains its rDNS requirement. The existing DNS-service lookup now
has bounded requests and a bounded system-resolver fallback when services return
errors, malformed/empty responses, or no usable hostnames. IPv4/IPv6 input is
validated, returned hostnames are normalized, and unavailable local DNS still
returns no match. The former error handler referenced an undefined variable.

The resolver runs in a short-lived Python subprocess with a five-second timeout,
because the standard gethostbyaddr call has no per-call timeout. This uses the
host's configured NSS resolver, which may include local hosts entries; it is not
an independent authoritative-DNS consensus check. No skip-rDNS setting is changed.

Verification: `python -m unittest plogical.test_reverse_dns` (eight focused
tests); real HTTP503 responses from an isolated local server still produced the
expected PTR names for two public resolver addresses through the real system
resolver. This tests lookup recovery, not a complete customer hostname/certificate
issuance. No installed hostname, certificate, DNS configuration or service was
changed for acceptance.
