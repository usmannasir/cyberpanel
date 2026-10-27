# Cloudflare credentials in SSL V2

SSL V2 remains a paid feature. Only a licensed panel administrator can configure the server-wide DNS credentials. A licensed website owner can still issue certificates for websites allowed by the existing ACL and ownership checks; that permission does not reveal or change server-wide credentials.

In SSL V2 → API Settings, select **Scoped API Token** for a Cloudflare token. Give it Zone:Read and DNS:Edit permissions restricted to the zones this server should manage. The email field is not required for token authentication. **Global API Key (legacy)** remains available and requires the account email. Existing saved legacy keys continue to work; the server does not guess whether a key is a token.

The form never displays the saved secret. Enter a replacement to update it. Saving a token removes conflicting legacy account-level authentication fields, and switching to a legacy key removes account-level token fields. Other providers and ACME account settings are retained. Existing acme.sh per-domain credential overrides are retained; this change does not rotate them or migrate historical renewal state.

The configuration helper writes the root-owned `account.conf` atomically with mode 0600. Credentials travel to its fixed privileged action through stdin, not command arguments. Install and upgrade provision only the helper's `metadata` and `save` actions for the CyberPanel service users, with isolated Python and restricted environment handling. No general Python or shell sudo access is granted. An unmanaged conflicting policy is not overwritten.

Opening the SSL settings page reads only configuration metadata. It no longer configures or restarts PowerDNS. Local PowerDNS initialization occurs only when that provider is selected by an explicit certificate issuance request.

Cloudflare zone detection uses the appropriate Bearer-token or legacy-key headers and checks enclosing zones without requiring the origin to have A/AAAA records. API requests have timeouts and do not follow redirects. Provider errors do not return credentials.

## Tested scope

- Focused parser, validation, file protection, atomic failure, authentication headers, metadata and access-control tests.
- Native CyberPanel ORM/ACL and Django session/CSRF tests: unpaid and non-admin configuration denied; permitted administrator save reaches the actual writer on an owned fixture.
- Chromium tests of the actual rendered form: token/legacy selection, email requirements, password field, POST and access-specific rendering.
- Real root helper plus upstream acme.sh Cloudflare plugin against an isolated HTTP provider fixture: persisted credentials, token/legacy authentication, TXT add/remove, preservation of unrelated TXT data and provider denial.
- Native non-root execution through the fixed sudo rule passed for both service accounts, including rejection of unrelated commands, extra arguments, unsafe environment settings and malformed inputs. Provisioning is idempotent and refuses unsafe or unmanaged paths.

These tests do not establish live Cloudflare or certificate-authority issuance and renewal, a complete Cloudflare Tunnel deployment, or all acceptance criteria in issue #1922. Unified Auto/DNS-01/HTTP-01 selection, broader solver persistence and migration, and full certificate deployment/renewal acceptance remain separate work. This change does not make the paid DNS-01 feature free.

References: [Cloudflare API token creation](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/) and [acme.sh Cloudflare DNS plugin](https://github.com/acmesh-official/acme.sh/blob/master/dnsapi/dns_cf.sh).
