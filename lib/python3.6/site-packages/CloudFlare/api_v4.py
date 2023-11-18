""" API core commands for Cloudflare API"""

def api_v4(self):
    """ API core commands for Cloudflare API"""

    # The API commands for /user/
    user(self)
    user_audit_logs(self)
    user_load_balancers(self)
    user_load_balancing_analytics(self)
    user_tokens_verify(self)
    user_workers(self)

    # The API commands for /zones/
    zones(self)
    zones_access(self)
    zones_amp(self)
    zones_analytics(self)
    zones_argo(self)
    zones_dns_analytics(self)
    zones_dnssec(self)
    zones_firewall(self)
    zones_load_balancers(self)
    zones_logpush(self)
    zones_logs(self)
    zones_media(self)
    zones_origin_tls_client_auth(self)
    zones_rate_limits(self)
    zones_secondary_dns(self)
    zones_settings(self)
    zones_spectrum(self)
    zones_ssl(self)
    zones_workers(self)

    # The API commands for /railguns/
    railguns(self)

    # The API commands for /certificates/
    certificates(self)

    # The API commands for /ips/
    ips(self)

    # The API commands for /accounts/
    accounts(self)
    accounts_access(self)
    accounts_addressing(self)
    accounts_audit_logs(self)
    accounts_firewall(self)
    accounts_load_balancers(self)
    accounts_secondary_dns(self)
    accounts_stream(self)

    # The API commands for /memberships/
    memberships(self)

    # The API commands for /graphql
    graphql(self)

def user(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "user")
    self.add('VOID', "user/billing")
    self.add('AUTH', "user/billing/history")
    self.add('AUTH', "user/billing/profile")
    self.add('VOID', "user/billing/subscriptions")
    self.add('AUTH', "user/billing/subscriptions/apps")
    self.add('AUTH', "user/billing/subscriptions/zones")
    self.add('VOID', "user/firewall")
    self.add('VOID', "user/firewall/access_rules")
    self.add('AUTH', "user/firewall/access_rules/rules")
    self.add('AUTH', "user/invites")
    self.add('AUTH', "user/organizations")
    self.add('AUTH', "user/subscriptions")

def zones(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "zones")
    self.add('AUTH', "zones", "activation_check")
    self.add('AUTH', "zones", "available_plans")
    self.add('AUTH', "zones", "available_rate_plans")
    self.add('AUTH', "zones", "custom_certificates")
    self.add('AUTH', "zones", "custom_certificates/prioritize")
    self.add('AUTH', "zones", "custom_hostnames")
    self.add('AUTH', "zones", "custom_hostnames/fallback_origin")
    self.add('AUTH', "zones", "custom_pages")
    self.add('AUTH', "zones", "dns_records")
    self.add('AUTH', "zones", "dns_records/export")
    self.add('AUTH', "zones", "dns_records/import")
    self.add('AUTH', "zones", "filters")
    self.add('AUTH', "zones", "healthchecks")
    self.add('AUTH', "zones", "healthchecks/preview")
    self.add('AUTH', "zones", "keyless_certificates")
    self.add('AUTH', "zones", "pagerules")
    self.add('AUTH', "zones", "pagerules/settings")
    self.add('AUTH', "zones", "purge_cache")
    self.add('AUTH', "zones", "railguns")
    self.add('AUTH', "zones", "railguns", "diagnose")
    self.add('VOID', "zones", "security")
    self.add('AUTH', "zones", "security/events")
    self.add('AUTH', "zones", "subscription")

def zones_settings(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "zones", "settings")
    self.add('AUTH', "zones", "settings/0rtt")
    self.add('AUTH', "zones", "settings/advanced_ddos")
    self.add('AUTH', "zones", "settings/always_online")
    self.add('AUTH', "zones", "settings/always_use_https")
    self.add('AUTH', "zones", "settings/automatic_https_rewrites")
    self.add('AUTH', "zones", "settings/brotli")
    self.add('AUTH', "zones", "settings/browser_cache_ttl")
    self.add('AUTH', "zones", "settings/browser_check")
    self.add('AUTH', "zones", "settings/cache_level")
    self.add('AUTH', "zones", "settings/challenge_ttl")
    self.add('AUTH', "zones", "settings/ciphers")
    self.add('AUTH', "zones", "settings/development_mode")
    self.add('AUTH', "zones", "settings/email_obfuscation")
    self.add('AUTH', "zones", "settings/h2_prioritization")
    self.add('AUTH', "zones", "settings/hotlink_protection")
    self.add('AUTH', "zones", "settings/http2")
    self.add('AUTH', "zones", "settings/http3")
    self.add('AUTH', "zones", "settings/image_resizing")
    self.add('AUTH', "zones", "settings/ip_geolocation")
    self.add('AUTH', "zones", "settings/ipv6")
    self.add('AUTH', "zones", "settings/min_tls_version")
    self.add('AUTH', "zones", "settings/minify")
    self.add('AUTH', "zones", "settings/mirage")
    self.add('AUTH', "zones", "settings/mobile_redirect")
    self.add('AUTH', "zones", "settings/opportunistic_encryption")
    self.add('AUTH', "zones", "settings/opportunistic_onion")
    self.add('AUTH', "zones", "settings/origin_error_page_pass_thru")
    self.add('AUTH', "zones", "settings/polish")
    self.add('AUTH', "zones", "settings/prefetch_preload")
    self.add('AUTH', "zones", "settings/privacy_pass")
    self.add('AUTH', "zones", "settings/pseudo_ipv4")
    self.add('AUTH', "zones", "settings/response_buffering")
    self.add('AUTH', "zones", "settings/rocket_loader")
    self.add('AUTH', "zones", "settings/security_header")
    self.add('AUTH', "zones", "settings/security_level")
    self.add('AUTH', "zones", "settings/server_side_exclude")
    self.add('AUTH', "zones", "settings/sort_query_string_for_cache")
    self.add('AUTH', "zones", "settings/ssl")
    self.add('AUTH', "zones", "settings/tls_1_3")
    self.add('AUTH', "zones", "settings/tls_client_auth")
    self.add('AUTH', "zones", "settings/true_client_ip_header")
    self.add('AUTH', "zones", "settings/waf")
    self.add('AUTH', "zones", "settings/webp")
    self.add('AUTH', "zones", "settings/websockets")

def zones_analytics(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "analytics")
    self.add('AUTH', "zones", "analytics/colos")
    self.add('AUTH', "zones", "analytics/dashboard")
    self.add('AUTH', "zones", "analytics/latency")
    self.add('AUTH', "zones", "analytics/latency/colos")

def zones_firewall(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "firewall")
    self.add('VOID', "zones", "firewall/access_rules")
    self.add('AUTH', "zones", "firewall/access_rules/rules")
    self.add('AUTH', "zones", "firewall/lockdowns")
    self.add('AUTH', "zones", "firewall/rules")
    self.add('AUTH', "zones", "firewall/ua_rules")
    self.add('VOID', "zones", "firewall/waf")
    self.add('AUTH', "zones", "firewall/waf/overrides")
    self.add('AUTH', "zones", "firewall/waf/packages")
    self.add('AUTH', "zones", "firewall/waf/packages", "groups")
    self.add('AUTH', "zones", "firewall/waf/packages", "rules")

def zones_rate_limits(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "zones", "rate_limits")

def zones_dns_analytics(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "dns_analytics")
    self.add('AUTH', "zones", "dns_analytics/report")
    self.add('AUTH', "zones", "dns_analytics/report/bytime")

def zones_amp(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "amp")
    self.add('AUTH', "zones", "amp/sxg")

def zones_logpush(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "logpush")
    self.add('VOID', "zones", "logpush/datasets")
    self.add('AUTH', "zones", "logpush/datasets", "fields")
    self.add('AUTH', "zones", "logpush/datasets", "jobs")
    self.add('AUTH', "zones", "logpush/jobs")
    self.add('AUTH', "zones", "logpush/ownership")
    self.add('AUTH', "zones", "logpush/ownership/validate")
    self.add('VOID', "zones", "logpush/validate")
    self.add('VOID', "zones", "logpush/validate/destination")
    self.add('AUTH', "zones", "logpush/validate/destination/exists")
    self.add('AUTH', "zones", "logpush/validate/origin")

def zones_logs(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "logs")
    self.add('AUTH', "zones", "logs/control")
    self.add('VOID', "zones", "logs/control/retention")
    self.add('AUTH', "zones", "logs/control/retention/flag")
    self.add('AUTH_UNWRAPPED', "zones", "logs/received")
    self.add('AUTH_UNWRAPPED', "zones", "logs/received/fields")
    self.add('AUTH_UNWRAPPED', "zones", "logs/rayids")

def railguns(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "railguns")
    self.add('AUTH', "railguns", "zones")

def certificates(self):
    """ API core commands for Cloudflare API"""

    self.add('CERT', "certificates")

def ips(self):
    """ API core commands for Cloudflare API"""

    self.add('OPEN', "ips")

def zones_argo(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "argo")
    self.add('AUTH', "zones", "argo/tiered_caching")
    self.add('AUTH', "zones", "argo/smart_routing")

def zones_dnssec(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "zones", "dnssec")

def zones_spectrum(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "spectrum")
    self.add('VOID', "zones", "spectrum/analytics")
    self.add('VOID', "zones", "spectrum/analytics/aggregate")
    self.add('AUTH', "zones", "spectrum/analytics/aggregate/current")
    self.add('VOID', "zones", "spectrum/analytics/events")
    self.add('AUTH', "zones", "spectrum/analytics/events/bytime")
    self.add('AUTH', "zones", "spectrum/analytics/events/summary")
    self.add('AUTH', "zones", "spectrum/apps")

def zones_ssl(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "ssl")
    self.add('AUTH', "zones", "ssl/analyze")
    self.add('AUTH', "zones", "ssl/certificate_packs")
    self.add('AUTH', 'zones', 'ssl/certificate_packs/order')
    self.add('AUTH', 'zones', 'ssl/certificate_packs/quota')
    self.add('AUTH', "zones", "ssl/verification")
    self.add('VOID', "zones", "ssl/universal")
    self.add('AUTH', "zones", "ssl/universal/settings")

def zones_origin_tls_client_auth(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', 'zones', 'origin_tls_client_auth')
    self.add('AUTH', 'zones', 'origin_tls_client_auth/hostnames')
    self.add('AUTH', 'zones', 'origin_tls_client_auth/hostnames/certificates')
    self.add('AUTH', 'zones', 'origin_tls_client_auth/settings')

def zones_workers(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "workers")
    self.add('AUTH', "zones", "workers/filters")
    self.add('AUTH', "zones", "workers/routes")
    self.add('AUTH', "zones", "workers/script")
    self.add('AUTH', "zones", "workers/script/bindings")

def zones_load_balancers(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "zones", "load_balancers")

def zones_secondary_dns(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "zones", "secondary_dns")
    self.add('AUTH', "zones", "secondary_dns/force_axfr")

def user_load_balancers(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "user/load_balancers")
    self.add('AUTH', "user/load_balancers/monitors")
    self.add('AUTH', "user/load_balancers/monitors", "preview")
    self.add('AUTH', "user/load_balancers/preview")
    self.add('AUTH', "user/load_balancers/pools")
    self.add('AUTH', "user/load_balancers/pools", "health")
    self.add('AUTH', "user/load_balancers/pools", "preview")

def user_workers(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "user/workers")
    self.add('AUTH', "user/workers/scripts")

def user_audit_logs(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "user/audit_logs")

def user_load_balancing_analytics(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "user/load_balancing_analytics")
    self.add('AUTH', "user/load_balancing_analytics/events")

def user_tokens_verify(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "user/tokens")
    self.add('AUTH', "user/tokens/permission_groups")
    self.add('AUTH', "user/tokens/verify")
    self.add('AUTH', "user/tokens", "value")

def accounts(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "accounts")
    self.add('VOID', "accounts", "billing")
    self.add('AUTH', "accounts", "billing/profile")
    self.add('AUTH', "accounts", "custom_pages")
    self.add('AUTH', "accounts", "members")
    self.add('AUTH', "accounts", "railguns")
    self.add('AUTH', "accounts", "railguns", "connections")
    self.add('VOID', "accounts", "registrar")
    self.add('AUTH', "accounts", "registrar/domains")
    self.add('AUTH', "accounts", "roles")
    self.add('VOID', 'accounts', 'rules')
    self.add('AUTH', 'accounts', 'rules/lists')
    self.add('AUTH', 'accounts', 'rules/lists', 'items')
    self.add('AUTH', 'accounts', 'rules/lists/bulk_operations')
    self.add('VOID', "accounts", "storage")
    self.add('AUTH', "accounts", "storage/analytics")
    self.add('AUTH', "accounts", "storage/analytics/stored")
    self.add('VOID', "accounts", "storage/kv")
    self.add('AUTH', "accounts", "storage/kv/namespaces")
    self.add('AUTH', "accounts", "storage/kv/namespaces", "bulk")
    self.add('AUTH', "accounts", "storage/kv/namespaces", "keys")
    self.add('AUTH', "accounts", "storage/kv/namespaces", "values")
    self.add('AUTH', "accounts", "subscriptions")
    self.add('AUTH', "accounts", "virtual_dns")
    self.add('VOID', "accounts", "virtual_dns", "dns_analytics")
    self.add('AUTH', "accounts", "virtual_dns", "dns_analytics/report")
    self.add('AUTH', "accounts", "virtual_dns", "dns_analytics/report/bytime")
    self.add('VOID', "accounts", "workers")
    self.add('AUTH', "accounts", "workers/scripts")

def accounts_addressing(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "accounts", "addressing")
    self.add('AUTH', "accounts", "addressing/prefixes")
    self.add('VOID', "accounts", "addressing/prefixes", "bgp")
    self.add('AUTH', "accounts", "addressing/prefixes", "bgp/status")
    self.add('AUTH', 'accounts', 'addressing/prefixes', 'delegations')

def accounts_audit_logs(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "accounts", "audit_logs")

def accounts_load_balancers(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "accounts", "load_balancers")
    self.add('AUTH', 'accounts', 'load_balancers/preview')
    self.add('AUTH', "accounts", "load_balancers/monitors")
    self.add('AUTH', 'accounts', 'load_balancers/monitors', 'preview')
    self.add('AUTH', "accounts", "load_balancers/pools")
    self.add('AUTH', "accounts", "load_balancers/pools", "health")
    self.add('AUTH', 'accounts', 'load_balancers/pools', 'preview')
    self.add('AUTH', 'accounts', 'load_balancers/search')

def accounts_firewall(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "accounts", "firewall")
    self.add('VOID', "accounts", "firewall/access_rules")
    self.add('AUTH', "accounts", "firewall/access_rules/rules")

def accounts_secondary_dns(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "accounts", "secondary_dns")
    self.add('AUTH', "accounts", "secondary_dns/masters")
    self.add('AUTH', "accounts", "secondary_dns/tsigs")

def accounts_stream(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "accounts", "stream")
    self.add('AUTH', "accounts", "stream", "captions")
    self.add('AUTH', "accounts", "stream/copy")
    self.add('AUTH', "accounts", "stream/direct_upload")
    self.add('AUTH', "accounts", "stream", "embed")
    self.add('AUTH', "accounts", "stream/keys")
    self.add('AUTH', "accounts", "stream/preview")
    self.add('AUTH', "accounts", "stream/watermarks")
    self.add('AUTH', "accounts", "stream/webhook")

def zones_media(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "zones", "media")
    self.add('AUTH', "zones", "media", "embed")
    self.add('AUTH', "zones", "media", "preview")

def memberships(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "memberships")

def graphql(self):
    """ API core commands for Cloudflare API"""

    self.add('AUTH', "graphql")

def zones_access(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "zones", "access")
    self.add('AUTH', "zones", "access/apps")
    self.add('AUTH', "zones", "access/apps", "policies")
    self.add('AUTH', "zones", "access/apps", "revoke_tokens")
    self.add('AUTH', "zones", "access/certificates")
    #self.add('AUTH', "zones", "access/apps/ca")
    self.add('AUTH', "zones", "access/apps", "ca")
    self.add('AUTH', "zones", "access/groups")
    self.add('AUTH', "zones", "access/identity_providers")
    self.add('AUTH', "zones", "access/organizations")
    self.add('AUTH', "zones", "access/organizations/revoke_user")
    self.add('AUTH', "zones", "access/service_tokens")

def accounts_access(self):
    """ API core commands for Cloudflare API"""

    self.add('VOID', "accounts", "access")
    self.add('AUTH', 'accounts', 'access/certificates')
    self.add('AUTH', "accounts", "access/groups")
    self.add('AUTH', "accounts", "access/identity_providers")
    self.add('AUTH', "accounts", "access/organizations")
    self.add('AUTH', "accounts", "access/organizations/revoke_user")
    self.add('AUTH', "accounts", "access/service_tokens")
    self.add('VOID', "accounts", "access/logs")
    self.add('AUTH', 'accounts', 'access/logs/access_requests')
    self.add('AUTH', 'accounts', 'access/apps')
    #self.add('AUTH', 'accounts', 'access/apps/ca')
    self.add('AUTH', 'accounts', 'access/apps', 'ca')
    self.add('AUTH', 'accounts', 'access/apps', 'policies')
    self.add('AUTH', 'accounts', 'access/apps', 'revoke_tokens')

