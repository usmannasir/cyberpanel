""" API core commands for Cloudflare API"""

def api_v4(self):
    """ :meta private: """


    # The API commands for /user/
    user(self)
    user_audit_logs(self)
    user_load_balancers(self)
    user_load_balancing_analytics(self)
    user_tokens_verify(self)

    # The API commands for /radar/
    radar(self)
    radar_as112(self)
    radar_attacks(self)
    radar_bgp(self)
    radar_email(self)
    radar_http(self)

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
    zones_waiting_rooms(self)
    zones_workers(self)
    zones_extras(self)
    zones_web3(self)
    zones_email(self)
    zones_api_gateway(self)

    # The API commands for /railguns/
    railguns(self)

    # The API commands for /certificates/
    certificates(self)

    # The API commands for /ips/
    ips(self)

    # The API commands for /live/
    live(self)

    # The API commands for /accounts/
    accounts(self)
    accounts_access(self)
    accounts_addressing(self)
    accounts_audit_logs(self)
    accounts_diagnostics(self)
    accounts_firewall(self)
    accounts_load_balancers(self)
    accounts_secondary_dns(self)
    accounts_stream(self)
    accounts_ai(self)
    accounts_extras(self)
    accounts_cloudforce_one(self)
    accounts_email(self)
    accounts_r2(self)

    # The API commands for /memberships/
    memberships(self)

    # The API commands for /graphql
    graphql(self)

    # Issue 151
    from_developers(self)

def user(self):
    """ :meta private: """

    self.add('AUTH', 'user')
    self.add('AUTH', 'user/billing/history')
    self.add('AUTH', 'user/billing/profile')
#   self.add('AUTH', 'user/billing/subscriptions/apps')
#   self.add('AUTH', 'user/billing/subscriptions/zones')
    self.add('AUTH', 'user/firewall/access_rules/rules')
    self.add('AUTH', 'user/invites')
    self.add('AUTH', 'user/organizations')
    self.add('AUTH', 'user/subscriptions')

def zones(self):
    """ :meta private: """

    self.add('AUTH', 'zones')
    self.add('AUTH', 'zones', 'activation_check')
    self.add('AUTH', 'zones', 'available_plans')
    self.add('AUTH', 'zones', 'available_rate_plans')
    self.add('AUTH', 'zones', 'bot_management')
    self.add('AUTH', 'zones', 'bot_management/feedback')
    self.add('AUTH', 'zones', 'client_certificates')
    self.add('AUTH', 'zones', 'custom_certificates')
    self.add('AUTH', 'zones', 'custom_certificates/prioritize')
    self.add('AUTH', 'zones', 'custom_csrs')
    self.add('AUTH', 'zones', 'custom_hostnames')
    self.add('AUTH', 'zones', 'custom_hostnames/fallback_origin')
    self.add('AUTH', 'zones', 'custom_ns')
    self.add('AUTH', 'zones', 'custom_pages')
    self.add('AUTH', 'zones', 'dns_records')
    self.add('AUTH', 'zones', 'dns_records/export')
    self.add('AUTH', 'zones', 'dns_records/import', content_type={'POST':'multipart/form-data'})
    self.add('AUTH', 'zones', 'dns_records/scan')
    self.add('AUTH', 'zones', 'dns_settings')
    self.add('AUTH', 'zones', 'dns_settings/use_apex_ns')
    self.add('AUTH', 'zones', 'filters')
    self.add('AUTH', 'zones', 'filters/validate-expr')
    self.add('AUTH', 'zones', 'healthchecks')
    self.add('AUTH', 'zones', 'healthchecks/preview')
    self.add('AUTH', 'zones', 'keyless_certificates')
    self.add('AUTH', 'zones', 'origin_max_http_version')
    self.add('AUTH', 'zones', 'pagerules')
    self.add('AUTH', 'zones', 'pagerules/settings')
    self.add('AUTH', 'zones', 'purge_cache')
    self.add('AUTH', 'zones', 'railguns')
    self.add('AUTH', 'zones', 'railguns', 'diagnose')
    self.add('AUTH', 'zones', 'security/events')
    self.add('AUTH', 'zones', 'subscription')

def zones_settings(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'settings')
    self.add('AUTH', 'zones', 'settings/0rtt')
    self.add('AUTH', 'zones', 'settings/advanced_ddos')
    self.add('AUTH', 'zones', 'settings/always_online')
    self.add('AUTH', 'zones', 'settings/always_use_https')
    self.add('AUTH', 'zones', 'settings/automatic_https_rewrites')
    self.add('AUTH', 'zones', 'settings/automatic_platform_optimization')
    self.add('AUTH', 'zones', 'settings/brotli')
    self.add('AUTH', 'zones', 'settings/browser_cache_ttl')
    self.add('AUTH', 'zones', 'settings/browser_check')
    self.add('AUTH', 'zones', 'settings/cache_level')
    self.add('AUTH', 'zones', 'settings/challenge_ttl')
    self.add('AUTH', 'zones', 'settings/ciphers')
    self.add('AUTH', 'zones', 'settings/development_mode')
    self.add('AUTH', 'zones', 'settings/early_hints')
    self.add('AUTH', 'zones', 'settings/email_obfuscation')
    self.add('AUTH', 'zones', 'settings/fonts')
    self.add('AUTH', 'zones', 'settings/h2_prioritization')
    self.add('AUTH', 'zones', 'settings/hotlink_protection')
    self.add('AUTH', 'zones', 'settings/http2')
    self.add('AUTH', 'zones', 'settings/http3')
    self.add('AUTH', 'zones', 'settings/image_resizing')
    self.add('AUTH', 'zones', 'settings/ip_geolocation')
    self.add('AUTH', 'zones', 'settings/ipv6')
    self.add('AUTH', 'zones', 'settings/min_tls_version')
    self.add('AUTH', 'zones', 'settings/minify')
    self.add('AUTH', 'zones', 'settings/mirage')
    self.add('AUTH', 'zones', 'settings/mobile_redirect')
    self.add('AUTH', 'zones', 'settings/nel')
    self.add('AUTH', 'zones', 'settings/opportunistic_encryption')
    self.add('AUTH', 'zones', 'settings/opportunistic_onion')
    self.add('AUTH', 'zones', 'settings/orange_to_orange')
    self.add('AUTH', 'zones', 'settings/origin_error_page_pass_thru')
    self.add('AUTH', 'zones', 'settings/origin_max_http_version')
    self.add('AUTH', 'zones', 'settings/polish')
    self.add('AUTH', 'zones', 'settings/prefetch_preload')
    self.add('AUTH', 'zones', 'settings/privacy_pass')
    self.add('AUTH', 'zones', 'settings/proxy_read_timeout')
    self.add('AUTH', 'zones', 'settings/pseudo_ipv4')
    self.add('AUTH', 'zones', 'settings/response_buffering')
    self.add('AUTH', 'zones', 'settings/rocket_loader')
    self.add('AUTH', 'zones', 'settings/security_header')
    self.add('AUTH', 'zones', 'settings/security_level')
    self.add('AUTH', 'zones', 'settings/server_side_exclude')
    self.add('AUTH', 'zones', 'settings/sort_query_string_for_cache')
    self.add('AUTH', 'zones', 'settings/ssl')
    self.add('AUTH', 'zones', 'settings/ssl_recommender')
    self.add('AUTH', 'zones', 'settings/tls_1_3')
    self.add('AUTH', 'zones', 'settings/tls_client_auth')
    self.add('AUTH', 'zones', 'settings/true_client_ip_header')
    self.add('AUTH', 'zones', 'settings/waf')
    self.add('AUTH', 'zones', 'settings/webp')
    self.add('AUTH', 'zones', 'settings/websockets')

    self.add('AUTH', 'zones', 'settings/zaraz/config')
    self.add('AUTH', 'zones', 'settings/zaraz/default')
    self.add('AUTH', 'zones', 'settings/zaraz/export')
    self.add('AUTH', 'zones', 'settings/zaraz/history')
    self.add('AUTH', 'zones', 'settings/zaraz/history/configs')
    self.add('AUTH', 'zones', 'settings/zaraz/publish')
    self.add('AUTH', 'zones', 'settings/zaraz/workflow')

    self.add('AUTH', 'zones', 'settings/zaraz/v2/config')
    self.add('AUTH', 'zones', 'settings/zaraz/v2/default')
    self.add('AUTH', 'zones', 'settings/zaraz/v2/export')
    self.add('AUTH', 'zones', 'settings/zaraz/v2/history')
    self.add('AUTH', 'zones', 'settings/zaraz/v2/history/configs')
    self.add('AUTH', 'zones', 'settings/zaraz/v2/publish')
    self.add('AUTH', 'zones', 'settings/zaraz/v2/workflow')

def zones_analytics(self):
    """ :meta private: """

#   self.add('AUTH', 'zones', 'analytics/colos') # deprecated 2021-03-01 - expired!
#   self.add('AUTH', 'zones', 'analytics/dashboard') # deprecated 2021-03-01 - expired!
    self.add('AUTH', 'zones', 'analytics/latency')
    self.add('AUTH', 'zones', 'analytics/latency/colos')

def zones_firewall(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'firewall/access_rules/rules')
    self.add('AUTH', 'zones', 'firewall/lockdowns')
    self.add('AUTH', 'zones', 'firewall/rules')
    self.add('AUTH', 'zones', 'firewall/ua_rules')
    self.add('AUTH', 'zones', 'firewall/waf/overrides')
    self.add('AUTH', 'zones', 'firewall/waf/packages')
    self.add('AUTH', 'zones', 'firewall/waf/packages', 'groups')
    self.add('AUTH', 'zones', 'firewall/waf/packages', 'rules')

def zones_rate_limits(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'rate_limits')

def zones_dns_analytics(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'dns_analytics/report')
    self.add('AUTH', 'zones', 'dns_analytics/report/bytime')

def zones_amp(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'amp/sxg')

def zones_logpush(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'logpush/datasets', 'fields')
    self.add('AUTH', 'zones', 'logpush/datasets', 'jobs')
    self.add('AUTH', 'zones', 'logpush/edge')
    self.add('AUTH', 'zones', 'logpush/edge/jobs')
    self.add('AUTH', 'zones', 'logpush/jobs')
    self.add('AUTH', 'zones', 'logpush/ownership')
    self.add('AUTH', 'zones', 'logpush/ownership/validate')
    self.add('AUTH', 'zones', 'logpush/validate/destination/exists')
    self.add('AUTH', 'zones', 'logpush/validate/origin')

def zones_logs(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'logs/control/retention/flag')
    self.add('AUTH_UNWRAPPED', 'zones', 'logs/received')
    self.add('AUTH', 'zones', 'logs/received/fields')
    self.add('AUTH_UNWRAPPED', 'zones', 'logs/rayids')

def railguns(self):
    """ :meta private: """

    self.add('AUTH', 'railguns')
    self.add('AUTH', 'railguns', 'zones')

def certificates(self):
    """ :meta private: """

    self.add('CERT', 'certificates')

def ips(self):
    """ :meta private: """

    self.add('OPEN', 'ips')

def live(self):
    """ :meta private: """

    self.add('AUTH', 'live')

def zones_argo(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'argo/tiered_caching')
    self.add('AUTH', 'zones', 'argo/smart_routing')

def zones_dnssec(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'dnssec')

def zones_spectrum(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'spectrum/analytics/aggregate/current')
    self.add('AUTH', 'zones', 'spectrum/analytics/events/bytime')
    self.add('AUTH', 'zones', 'spectrum/analytics/events/summary')
    self.add('AUTH', 'zones', 'spectrum/apps')

def zones_ssl(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'ssl/analyze')
    self.add('AUTH', 'zones', 'ssl/certificate_packs')
    self.add('AUTH', 'zones', 'ssl/certificate_packs/order')
    self.add('AUTH', 'zones', 'ssl/certificate_packs/quota')
    self.add('AUTH', 'zones', 'ssl/recommendation')
    self.add('AUTH', 'zones', 'ssl/verification')
    self.add('AUTH', 'zones', 'ssl/universal/settings')

def zones_origin_tls_client_auth(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'origin_tls_client_auth')
    self.add('AUTH', 'zones', 'origin_tls_client_auth/hostnames')
    self.add('AUTH', 'zones', 'origin_tls_client_auth/hostnames/certificates')
    self.add('AUTH', 'zones', 'origin_tls_client_auth/settings')

def zones_workers(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'workers/filters')
    self.add('AUTH', 'zones', 'workers/routes')
    self.add('AUTH', 'zones', 'workers/script')
    self.add('AUTH', 'zones', 'workers/script/bindings')

def zones_load_balancers(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'load_balancers')

def zones_secondary_dns(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'secondary_dns')
    self.add('AUTH', 'zones', 'secondary_dns/force_axfr')
    self.add('AUTH', 'zones', 'secondary_dns/incoming')
    self.add('AUTH', 'zones', 'secondary_dns/outgoing')
    self.add('AUTH', 'zones', 'secondary_dns/outgoing/disable')
    self.add('AUTH', 'zones', 'secondary_dns/outgoing/enable')
    self.add('AUTH', 'zones', 'secondary_dns/outgoing/force_notify')
    self.add('AUTH', 'zones', 'secondary_dns/outgoing/status')

def user_load_balancers(self):
    """ :meta private: """

    self.add('AUTH', 'user/load_balancers/monitors')
    self.add('AUTH', 'user/load_balancers/monitors', 'preview')
    self.add('AUTH', 'user/load_balancers/monitors', 'references')
    self.add('AUTH', 'user/load_balancers/preview')
    self.add('AUTH', 'user/load_balancers/pools')
    self.add('AUTH', 'user/load_balancers/pools', 'health')
    self.add('AUTH', 'user/load_balancers/pools', 'preview')
    self.add('AUTH', 'user/load_balancers/pools', 'references')

def user_audit_logs(self):
    """ :meta private: """

    self.add('AUTH', 'user/audit_logs')

def user_load_balancing_analytics(self):
    """ :meta private: """

    self.add('AUTH', 'user/load_balancing_analytics/events')

def user_tokens_verify(self):
    """ :meta private: """

    self.add('AUTH', 'user/tokens')
    self.add('AUTH', 'user/tokens/permission_groups')
    self.add('AUTH', 'user/tokens/verify')
    self.add('AUTH', 'user/tokens', 'value')

def accounts(self):
    """ :meta private: """

    self.add('AUTH', 'accounts')
    self.add('AUTH', 'accounts', 'billing/profile')
    self.add('AUTH', 'accounts', 'brand-protection/submit')
    self.add('AUTH', 'accounts', 'brand-protection/url-info')
    self.add('AUTH', 'accounts', 'cfd_tunnel')
    self.add('AUTH', 'accounts', 'cfd_tunnel', 'configurations')
    self.add('AUTH', 'accounts', 'cfd_tunnel', 'connectors')
    self.add('AUTH', 'accounts', 'cfd_tunnel', 'connections')
    self.add('AUTH', 'accounts', 'cfd_tunnel', 'management')
    self.add('AUTH', 'accounts', 'cfd_tunnel', 'token')
    self.add('AUTH', 'accounts', 'custom_pages')

    self.add('AUTH', 'accounts', 'dlp/datasets')
    self.add('AUTH', 'accounts', 'dlp/datasets', 'upload', content_type={'POST':'application/octet-stream'})
    self.add('AUTH', 'accounts', 'dlp/patterns/validate')
    self.add('AUTH', 'accounts', 'dlp/payload_log')
    self.add('AUTH', 'accounts', 'dlp/profiles')
    self.add('AUTH', 'accounts', 'dlp/profiles/custom')
    self.add('AUTH', 'accounts', 'dlp/profiles/predefined')

    self.add('AUTH', 'accounts', 'members')
    self.add('AUTH', 'accounts', 'mnm/config')
    self.add('AUTH', 'accounts', 'mnm/config/full')
    self.add('AUTH', 'accounts', 'mnm/rules')
    self.add('AUTH', 'accounts', 'mnm/rules', 'advertisement')
    self.add('AUTH', 'accounts', 'railguns')
    self.add('AUTH', 'accounts', 'railguns', 'connections')
    self.add('AUTH', 'accounts', 'registrar/domains')
    self.add('AUTH', 'accounts', 'registrar/contacts')
    self.add('AUTH', 'accounts', 'roles')
    self.add('AUTH', 'accounts', 'rules/lists')
    self.add('AUTH', 'accounts', 'rules/lists', 'items')
    self.add('AUTH', 'accounts', 'rules/lists/bulk_operations')
    self.add('AUTH', 'accounts', 'rulesets')
    self.add('AUTH', 'accounts', 'rulesets', 'versions')
    self.add('AUTH', 'accounts', 'rulesets', 'versions', 'by_tag')
    self.add('AUTH', 'accounts', 'rulesets', 'versions', 'by_tag/wordpress')
    self.add('AUTH', 'accounts', 'rulesets', 'rules')
#   self.add('AUTH', 'accounts', 'rulesets/import')
    self.add('AUTH', 'accounts', 'rulesets/phases', 'entrypoint')
    self.add('AUTH', 'accounts', 'rulesets/phases', 'entrypoint/versions')
    self.add('AUTH', 'accounts', 'rulesets/phases', 'versions')

    self.add('AUTH', 'accounts', 'rum/site_info')
    self.add('AUTH', 'accounts', 'rum/site_info/list')
    self.add('AUTH', 'accounts', 'rum/v2', 'rule')
    self.add('AUTH', 'accounts', 'rum/v2', 'rules')

    self.add('AUTH', 'accounts', 'storage/analytics')
    self.add('AUTH', 'accounts', 'storage/analytics/stored')
    self.add('AUTH', 'accounts', 'storage/kv/namespaces')
    self.add('AUTH', 'accounts', 'storage/kv/namespaces', 'bulk')
    self.add('AUTH', 'accounts', 'storage/kv/namespaces', 'keys')
    self.add('AUTH', 'accounts', 'storage/kv/namespaces', 'values', content_type={'PUT':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'storage/kv/namespaces', 'metadata')

    self.add('AUTH', 'accounts', 'subscriptions')
    self.add('AUTH', 'accounts', 'tunnels')
    self.add('AUTH', 'accounts', 'tunnels', 'connections')

    self.add('AUTH', 'accounts', 'vectorize/index')
    self.add('AUTH', 'accounts', 'vectorize/indexes')
    self.add('AUTH', 'accounts', 'vectorize/indexes', 'delete-by-ids')
    self.add('AUTH', 'accounts', 'vectorize/indexes', 'get-by-ids')
    self.add('AUTH', 'accounts', 'vectorize/indexes', 'insert', content_type={'POST':'application/x-ndjson'})
    self.add('AUTH', 'accounts', 'vectorize/indexes', 'query')
    self.add('AUTH', 'accounts', 'vectorize/indexes', 'upsert', content_type={'POST':'application/x-ndjson'})

    self.add('AUTH', 'accounts', 'virtual_dns')
    self.add('AUTH', 'accounts', 'virtual_dns', 'dns_analytics/report')
    self.add('AUTH', 'accounts', 'virtual_dns', 'dns_analytics/report/bytime')

    self.add('AUTH', 'accounts', 'workers/account-settings')
    self.add('AUTH', 'accounts', 'workers/deployments/by-script')
    self.add('AUTH', 'accounts', 'workers/deployments/by-script', 'detail')
    self.add('AUTH', 'accounts', 'workers/dispatch/namespaces')
    self.add('AUTH', 'accounts', 'workers/dispatch/namespaces', 'scripts')
    self.add('AUTH', 'accounts', 'workers/dispatch/namespaces', 'scripts', 'bindings')
    self.add('AUTH', 'accounts', 'workers/dispatch/namespaces', 'scripts', 'content', content_type={'PUT':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'workers/dispatch/namespaces', 'scripts', 'secrets')
    self.add('AUTH', 'accounts', 'workers/dispatch/namespaces', 'scripts', 'settings')
    self.add('AUTH', 'accounts', 'workers/dispatch/namespaces', 'scripts', 'tags')
    self.add('AUTH', 'accounts', 'workers/domains')
    self.add('AUTH', 'accounts', 'workers/durable_objects/namespaces')
    self.add('AUTH', 'accounts', 'workers/durable_objects/namespaces', 'objects')
    self.add('AUTH', 'accounts', 'workers/queues')
    self.add('AUTH', 'accounts', 'workers/queues', 'consumers')
    self.add('AUTH', 'accounts', 'workers/scripts')
    self.add('AUTH', 'accounts', 'workers/scripts', 'content', content_type={'PUT':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'workers/scripts', 'content/v2')
    self.add('AUTH', 'accounts', 'workers/scripts', 'deployments')
    self.add('AUTH', 'accounts', 'workers/scripts', 'schedules')
    self.add('AUTH', 'accounts', 'workers/scripts', 'script-settings')
    self.add('AUTH', 'accounts', 'workers/scripts', 'settings', content_type={'PATCH':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'workers/scripts', 'tails')
    self.add('AUTH', 'accounts', 'workers/scripts', 'usage-model')
    self.add('AUTH', 'accounts', 'workers/scripts', 'versions')
    self.add('AUTH', 'accounts', 'workers/services', 'environments', 'content', content_type={'PUT':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'workers/services', 'environments', 'settings')

    self.add('AUTH', 'accounts', 'workers/subdomain')

def accounts_addressing(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'addressing/address_maps')
    self.add('AUTH', 'accounts', 'addressing/address_maps', 'accounts')
    self.add('AUTH', 'accounts', 'addressing/address_maps', 'ips')
    self.add('AUTH', 'accounts', 'addressing/address_maps', 'zones')
    self.add('AUTH', 'accounts', 'addressing/loa_documents', content_type={'POST':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'addressing/loa_documents', 'download')
    self.add('AUTH', 'accounts', 'addressing/prefixes')
    self.add('AUTH', 'accounts', 'addressing/prefixes', 'bgp/prefixes')
    self.add('AUTH', 'accounts', 'addressing/prefixes', 'bgp/status')
    self.add('AUTH', 'accounts', 'addressing/prefixes', 'bindings')
    self.add('AUTH', 'accounts', 'addressing/prefixes', 'delegations')
    self.add('AUTH', 'accounts', 'addressing/services')

def accounts_audit_logs(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'audit_logs')

def accounts_load_balancers(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'load_balancers/preview')
    self.add('AUTH', 'accounts', 'load_balancers/monitors')
    self.add('AUTH', 'accounts', 'load_balancers/monitors', 'preview')
    self.add('AUTH', 'accounts', 'load_balancers/monitors', 'references')
    self.add('AUTH', 'accounts', 'load_balancers/pools')
    self.add('AUTH', 'accounts', 'load_balancers/pools', 'health')
    self.add('AUTH', 'accounts', 'load_balancers/pools', 'preview')
    self.add('AUTH', 'accounts', 'load_balancers/pools', 'references')
    self.add('AUTH', 'accounts', 'load_balancers/regions')
    self.add('AUTH', 'accounts', 'load_balancers/search')


def accounts_firewall(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'firewall/access_rules/rules')

def accounts_secondary_dns(self):
    """ :meta private: """

#   self.add('AUTH', 'accounts', 'secondary_dns/masters')
    self.add('AUTH', 'accounts', 'secondary_dns/primaries')
    self.add('AUTH', 'accounts', 'secondary_dns/tsigs')
    self.add('AUTH', 'accounts', 'secondary_dns/acls')
    self.add('AUTH', 'accounts', 'secondary_dns/peers')

def accounts_stream(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'stream')
    self.add('AUTH', 'accounts', 'stream', 'audio')
    self.add('AUTH', 'accounts', 'stream', 'audio/copy')
    self.add('AUTH', 'accounts', 'stream', 'captions', content_type={'PUT':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'stream', 'embed')
    self.add('AUTH', 'accounts', 'stream', 'downloads')
    self.add('AUTH', 'accounts', 'stream', 'token')
    self.add('AUTH', 'accounts', 'stream/clip')
    self.add('AUTH', 'accounts', 'stream/copy')
    self.add('AUTH', 'accounts', 'stream/direct_upload')
    self.add('AUTH', 'accounts', 'stream/keys')
#   self.add('AUTH', 'accounts', 'stream/preview')
    self.add('AUTH', 'accounts', 'stream/watermarks', content_type={'POST':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'stream/webhook')
    self.add('AUTH', 'accounts', 'stream/live_inputs')
    self.add('AUTH', 'accounts', 'stream/live_inputs', 'outputs')
    self.add('AUTH', 'accounts', 'stream/live_inputs', 'outputs', 'enabled')

def zones_media(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'media')
    self.add('AUTH', 'zones', 'media', 'embed')
    self.add('AUTH', 'zones', 'media', 'preview')

def memberships(self):
    """ :meta private: """

    self.add('AUTH', 'memberships')

def graphql(self):
    """ :meta private: """

    self.add('AUTH', 'graphql')

def zones_access(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'access/apps')
    self.add('AUTH', 'zones', 'access/apps', 'policies')
    self.add('AUTH', 'zones', 'access/apps', 'revoke_tokens')
    self.add('AUTH', 'zones', 'access/bookmarks')
    self.add('AUTH', 'zones', 'access/certificates')
    self.add('AUTH', 'zones', 'access/certificates/settings')
#   self.add('AUTH', 'zones', 'access/apps/ca')
    self.add('AUTH', 'zones', 'access/apps', 'ca')
    self.add('AUTH', 'zones', 'access/apps', 'user_policy_checks')
    self.add('AUTH', 'zones', 'access/groups')
    self.add('AUTH', 'zones', 'access/identity_providers')
    self.add('AUTH', 'zones', 'access/organizations')
    self.add('AUTH', 'zones', 'access/organizations/revoke_user')
    self.add('AUTH', 'zones', 'access/service_tokens')

def accounts_access(self):
    """ :meta private: """

#   self.add('AUTH', 'accounts', 'access/bookmarks') # deprecated 2023-03-19
    self.add('AUTH', 'accounts', 'access/custom_pages')
    self.add('AUTH', 'accounts', 'access/gateway_ca')
    self.add('AUTH', 'accounts', 'access/groups')
    self.add('AUTH', 'accounts', 'access/identity_providers')
    self.add('AUTH', 'accounts', 'access/organizations')
#   self.add('AUTH', 'accounts', 'access/organizations/doh') # deprecated 2020-02-04 - expired!
    self.add('AUTH', 'accounts', 'access/organizations/revoke_user')
    self.add('AUTH', 'accounts', 'access/service_tokens')
    self.add('AUTH', 'accounts', 'access/service_tokens', 'refresh')
    self.add('AUTH', 'accounts', 'access/service_tokens', 'rotate')
    self.add('AUTH', 'accounts', 'access/apps')
#   self.add('AUTH', 'accounts', 'access/apps/ca')
    self.add('AUTH', 'accounts', 'access/apps', 'ca')
    self.add('AUTH', 'accounts', 'access/apps', 'policies')
    self.add('AUTH', 'accounts', 'access/apps', 'revoke_tokens')
    self.add('AUTH', 'accounts', 'access/apps', 'user_policy_checks')
    self.add('AUTH', 'accounts', 'access/certificates')
    self.add('AUTH', 'accounts', 'access/certificates/settings')
    self.add('AUTH', 'accounts', 'access/keys')
    self.add('AUTH', 'accounts', 'access/keys/rotate')
    self.add('AUTH', 'accounts', 'access/logs/access_requests')
    self.add('AUTH', 'accounts', 'access/policies')
    self.add('AUTH', 'accounts', 'access/seats')
    self.add('AUTH', 'accounts', 'access/tags')
    self.add('AUTH', 'accounts', 'access/users')
    self.add('AUTH', 'accounts', 'access/users', 'failed_logins')
    self.add('AUTH', 'accounts', 'access/users', 'active_sessions')
    self.add('AUTH', 'accounts', 'access/users', 'last_seen_identity')


def accounts_diagnostics(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'diagnostics/traceroute')

def zones_waiting_rooms(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'waiting_rooms')
    self.add('AUTH', 'zones', 'waiting_rooms', 'events')
    self.add('AUTH', 'zones', 'waiting_rooms', 'events', 'details')
    self.add('AUTH', 'zones', 'waiting_rooms', 'rules')
    self.add('AUTH', 'zones', 'waiting_rooms', 'status')
    self.add('AUTH', 'zones', 'waiting_rooms/preview')
    self.add('AUTH', 'zones', 'waiting_rooms/settings')

def accounts_ai(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'ai-gateway/gateways')
    self.add('AUTH', 'accounts', 'ai-gateway/gateways', 'logs')

    self.add('AUTH', 'accounts', 'ai/authors/search')
    self.add('AUTH', 'accounts', 'ai/finetunes')
    self.add('AUTH', 'accounts', 'ai/finetunes', 'finetune-assets', content_type={'POST':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'ai/finetunes/public')
    self.add('AUTH', 'accounts', 'ai/models/search')

    self.add('AUTH', 'accounts', 'ai/run', content_type={'POST':['application/json','application/octet-stream']})

    self.add('AUTH', 'accounts', 'ai/run/@cf/baai/bge-base-en-v1.5')
    self.add('AUTH', 'accounts', 'ai/run/@cf/baai/bge-large-en-v1.5')
    self.add('AUTH', 'accounts', 'ai/run/@cf/baai/bge-small-en-v1.5')
    self.add('AUTH', 'accounts', 'ai/run/@cf/bytedance/stable-diffusion-xl-lightning')
    self.add('AUTH', 'accounts', 'ai/run/@cf/deepseek-ai/deepseek-coder-7b-instruct-v1.5')
    self.add('AUTH', 'accounts', 'ai/run/@cf/deepseek-ai/deepseek-math-7b-base')
    self.add('AUTH', 'accounts', 'ai/run/@cf/deepseek-ai/deepseek-math-7b-instruct')
    self.add('AUTH', 'accounts', 'ai/run/@cf/defog/sqlcoder-7b-2')
    self.add('AUTH', 'accounts', 'ai/run/@cf/facebook/bart-large-cnn')
    self.add('AUTH', 'accounts', 'ai/run/@cf/facebook/detr-resnet-50', content_type={'POST':'application/octet-stream'})
    self.add('AUTH', 'accounts', 'ai/run/@cf/fblgit/una-cybertron-7b-v2-bf16')
    self.add('AUTH', 'accounts', 'ai/run/@cf/google/gemma-2b-it-lora')
    self.add('AUTH', 'accounts', 'ai/run/@cf/google/gemma-7b-it-lora')
    self.add('AUTH', 'accounts', 'ai/run/@cf/huggingface/distilbert-sst-2-int8')
    self.add('AUTH', 'accounts', 'ai/run/@cf/inml/inml-roberta-dga')
    self.add('AUTH', 'accounts', 'ai/run/@cf/jpmorganchase/roberta-spam')
    self.add('AUTH', 'accounts', 'ai/run/@cf/llava-hf/llava-1.5-7b-hf')
    self.add('AUTH', 'accounts', 'ai/run/@cf/lykon/dreamshaper-8-lcm')
    self.add('AUTH', 'accounts', 'ai/run/@cf/m-a-p/opencodeinterpreter-ds-6.7b')
    self.add('AUTH', 'accounts', 'ai/run/@cf/meta-llama/llama-2-7b-chat-hf-lora')
    self.add('AUTH', 'accounts', 'ai/run/@cf/meta/detr-resnet-50')
    self.add('AUTH', 'accounts', 'ai/run/@cf/meta/llama-2-7b-chat-fp16')
    self.add('AUTH', 'accounts', 'ai/run/@cf/meta/llama-2-7b-chat-int8')
    self.add('AUTH', 'accounts', 'ai/run/@cf/meta/llama-3-8b-instruct')
    self.add('AUTH', 'accounts', 'ai/run/@cf/meta/m2m100-1.2b')
    self.add('AUTH', 'accounts', 'ai/run/@cf/microsoft/phi-2')
    self.add('AUTH', 'accounts', 'ai/run/@cf/microsoft/phi-3-mini-4k-instruct')
    self.add('AUTH', 'accounts', 'ai/run/@cf/microsoft/resnet-50', content_type={'POST':'application/octet-stream'})
    self.add('AUTH', 'accounts', 'ai/run/@cf/mistral/mistral-7b-instruct-v0.1')
    self.add('AUTH', 'accounts', 'ai/run/@cf/mistral/mistral-7b-instruct-v0.1-vllm')
    self.add('AUTH', 'accounts', 'ai/run/@cf/mistral/mistral-7b-instruct-v0.2-lora')
    self.add('AUTH', 'accounts', 'ai/run/@cf/mistral/mixtral-8x7b-instruct-v0.1-awq')
    self.add('AUTH', 'accounts', 'ai/run/@cf/nexaaidev/octopus-v2')
    self.add('AUTH', 'accounts', 'ai/run/@cf/openai/whisper', content_type={'POST':'application/octet-stream'})
    self.add('AUTH', 'accounts', 'ai/run/@cf/openai/whisper-sherpa', content_type={'POST':'application/octet-stream'})
    self.add('AUTH', 'accounts', 'ai/run/@cf/openai/whisper-tiny-en', content_type={'POST':'application/octet-stream'})
    self.add('AUTH', 'accounts', 'ai/run/@cf/openchat/openchat-3.5-0106')
    self.add('AUTH', 'accounts', 'ai/run/@cf/qwen/qwen1.5-0.5b-chat')
    self.add('AUTH', 'accounts', 'ai/run/@cf/qwen/qwen1.5-1.8b-chat')
    self.add('AUTH', 'accounts', 'ai/run/@cf/qwen/qwen1.5-14b-chat-awq')
    self.add('AUTH', 'accounts', 'ai/run/@cf/qwen/qwen1.5-7b-chat-awq')
    self.add('AUTH', 'accounts', 'ai/run/@cf/runwayml/stable-diffusion-v1-5-img2img')
    self.add('AUTH', 'accounts', 'ai/run/@cf/runwayml/stable-diffusion-v1-5-inpainting')
    self.add('AUTH', 'accounts', 'ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0')
    self.add('AUTH', 'accounts', 'ai/run/@cf/stabilityai/stable-diffusion-xl-turbo')
    self.add('AUTH', 'accounts', 'ai/run/@cf/sven/test')
    self.add('AUTH', 'accounts', 'ai/run/@cf/thebloke/discolm-german-7b-v1-awq')
    self.add('AUTH', 'accounts', 'ai/run/@cf/thebloke/yarn-mistral-7b-64k-awq')
    self.add('AUTH', 'accounts', 'ai/run/@cf/tiiuae/falcon-7b-instruct')
    self.add('AUTH', 'accounts', 'ai/run/@cf/tinyllama/tinyllama-1.1b-chat-v1.0')
    self.add('AUTH', 'accounts', 'ai/run/@cf/unum/uform-gen2-qwen-500m')

    self.add('AUTH', 'accounts', 'ai/run/@hf/baai/bge-base-en-v1.5')
    self.add('AUTH', 'accounts', 'ai/run/@hf/baai/bge-m3')
    self.add('AUTH', 'accounts', 'ai/run/@hf/google/gemma-7b-it')
    self.add('AUTH', 'accounts', 'ai/run/@hf/meta-llama/meta-llama-3-8b-instruct')
    self.add('AUTH', 'accounts', 'ai/run/@hf/mistral/mistral-7b-instruct-v0.2')
    self.add('AUTH', 'accounts', 'ai/run/@hf/nexusflow/starling-lm-7b-beta')
    self.add('AUTH', 'accounts', 'ai/run/@hf/nousresearch/hermes-2-pro-mistral-7b')
    self.add('AUTH', 'accounts', 'ai/run/@hf/sentence-transformers/all-minilm-l6-v2')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/codellama-7b-instruct-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/deepseek-coder-6.7b-base-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/deepseek-coder-6.7b-instruct-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/llama-2-13b-chat-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/llamaguard-7b-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/mistral-7b-instruct-v0.1-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/neural-chat-7b-v3-1-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/openchat_3.5-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/openhermes-2.5-mistral-7b-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/orca-2-13b-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/starling-lm-7b-alpha-awq')
    self.add('AUTH', 'accounts', 'ai/run/@hf/thebloke/zephyr-7b-beta-awq')

    self.add('AUTH', 'accounts', 'ai/run/proxy')
    self.add('AUTH', 'accounts', 'ai/tasks/search')

def accounts_extras(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'alerting/v3/available_alerts')
    self.add('AUTH', 'accounts', 'alerting/v3/destinations/eligible')
    self.add('AUTH', 'accounts', 'alerting/v3/destinations/pagerduty')
    self.add('AUTH', 'accounts', 'alerting/v3/destinations/pagerduty/connect')
    self.add('AUTH', 'accounts', 'alerting/v3/destinations/webhooks')
    self.add('AUTH', 'accounts', 'alerting/v3/history')
    self.add('AUTH', 'accounts', 'alerting/v3/policies')

    self.add('AUTH', 'accounts', 'calls/apps')
    self.add('AUTH', 'accounts', 'calls/turn_keys')

    self.add('AUTH', 'accounts', 'custom_ns')
    self.add('AUTH', 'accounts', 'custom_ns/availability')
    self.add('AUTH', 'accounts', 'custom_ns/verify')

    self.add('AUTH', 'accounts', 'devices')
    self.add('AUTH', 'accounts', 'devices', 'override_codes')
    self.add('AUTH', 'accounts', 'devices/dex_tests')
    self.add('AUTH', 'accounts', 'devices/networks')
    self.add('AUTH', 'accounts', 'devices/policies')
    self.add('AUTH', 'accounts', 'devices/policy')
    self.add('AUTH', 'accounts', 'devices/policy', 'exclude')
#   self.add('AUTH', 'accounts', 'devices/policy/exclude')
    self.add('AUTH', 'accounts', 'devices/policy', 'fallback_domains')
#   self.add('AUTH', 'accounts', 'devices/policy/fallback_domains')
    self.add('AUTH', 'accounts', 'devices/policy', 'include')
#   self.add('AUTH', 'accounts', 'devices/policy/include')
    self.add('AUTH', 'accounts', 'devices/posture')
    self.add('AUTH', 'accounts', 'devices/posture/integration')
    self.add('AUTH', 'accounts', 'devices/revoke')
    self.add('AUTH', 'accounts', 'devices/settings')
    self.add('AUTH', 'accounts', 'devices/unrevoke')

    self.add('AUTH', 'accounts', 'dex/colos')
    self.add('AUTH', 'accounts', 'dex/fleet-status/devices')
    self.add('AUTH', 'accounts', 'dex/fleet-status/live')
    self.add('AUTH', 'accounts', 'dex/fleet-status/over-time')
    self.add('AUTH', 'accounts', 'dex/http-tests')
    self.add('AUTH', 'accounts', 'dex/http-tests', 'percentiles')
    self.add('AUTH', 'accounts', 'dex/tests')
    self.add('AUTH', 'accounts', 'dex/tests/unique-devices')
    self.add('AUTH', 'accounts', 'dex/traceroute-test-results', 'network-path')
    self.add('AUTH', 'accounts', 'dex/traceroute-tests')
    self.add('AUTH', 'accounts', 'dex/traceroute-tests', 'network-path')
    self.add('AUTH', 'accounts', 'dex/traceroute-tests', 'percentiles')

    self.add('AUTH', 'accounts', 'dns_firewall')
    self.add('AUTH', 'accounts', 'dns_firewall', 'dns_analytics/report')
    self.add('AUTH', 'accounts', 'dns_firewall', 'dns_analytics/report/bytime')

    self.add('AUTH', 'accounts', 'gateway')
    self.add('AUTH', 'accounts', 'gateway/app_types')
    self.add('AUTH', 'accounts', 'gateway/audit_ssh_settings')
    self.add('AUTH', 'accounts', 'gateway/categories')
    self.add('AUTH', 'accounts', 'gateway/configuration')
    self.add('AUTH', 'accounts', 'gateway/lists')
    self.add('AUTH', 'accounts', 'gateway/lists', 'items')
    self.add('AUTH', 'accounts', 'gateway/locations')
    self.add('AUTH', 'accounts', 'gateway/logging')
    self.add('AUTH', 'accounts', 'gateway/proxy_endpoints')
    self.add('AUTH', 'accounts', 'gateway/rules')

    self.add('AUTH', 'accounts', 'images/v1', content_type={'POST':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'images/v1', 'blob')
    self.add('AUTH', 'accounts', 'images/v1/config')
    self.add('AUTH', 'accounts', 'images/v1/keys')
    self.add('AUTH', 'accounts', 'images/v1/stats')
    self.add('AUTH', 'accounts', 'images/v1/variants')
    self.add('AUTH', 'accounts', 'images/v2')
    self.add('AUTH', 'accounts', 'images/v2/direct_upload', content_type={'POST':'multipart/form-data'})

    self.add('AUTH', 'accounts', 'intel-phishing/predict')
    self.add('AUTH', 'accounts', 'intel/asn')
    self.add('AUTH', 'accounts', 'intel/asn', 'subnets')
    self.add('AUTH', 'accounts', 'intel/attack-surface-report', 'dismiss')
    self.add('AUTH', 'accounts', 'intel/attack-surface-report/issue-types')
    self.add('AUTH', 'accounts', 'intel/attack-surface-report/issues')
    self.add('AUTH', 'accounts', 'intel/attack-surface-report/issues/class')
    self.add('AUTH', 'accounts', 'intel/attack-surface-report/issues/severity')
    self.add('AUTH', 'accounts', 'intel/attack-surface-report/issues/type')
    self.add('AUTH', 'accounts', 'intel/dns')
    self.add('AUTH', 'accounts', 'intel/domain')
    self.add('AUTH', 'accounts', 'intel/domain-history')
    self.add('AUTH', 'accounts', 'intel/domain/bulk')
    self.add('AUTH', 'accounts', 'intel/indicator-feeds')
    self.add('AUTH', 'accounts', 'intel/indicator-feeds', 'data')
    self.add('AUTH', 'accounts', 'intel/indicator-feeds', 'snapshot', content_type={'PUT':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'intel/indicator-feeds/permissions/add')
    self.add('AUTH', 'accounts', 'intel/indicator-feeds/permissions/remove')
    self.add('AUTH', 'accounts', 'intel/indicator-feeds/permissions/view')
    self.add('AUTH', 'accounts', 'intel/ip')
    self.add('AUTH', 'accounts', 'intel/ip-list')
    self.add('AUTH', 'accounts', 'intel/miscategorization')
    self.add('AUTH', 'accounts', 'intel/sinkholes')
    self.add('AUTH', 'accounts', 'intel/whois')

    self.add('AUTH', 'accounts', 'magic/cf_interconnects')
    self.add('AUTH', 'accounts', 'magic/gre_tunnels')
    self.add('AUTH', 'accounts', 'magic/ipsec_tunnels')
    self.add('AUTH', 'accounts', 'magic/ipsec_tunnels', 'psk_generate')
    self.add('AUTH', 'accounts', 'magic/routes')
    self.add('AUTH', 'accounts', 'magic/sites')
    self.add('AUTH', 'accounts', 'magic/sites', 'acls')
    self.add('AUTH', 'accounts', 'magic/sites', 'lans')
    self.add('AUTH', 'accounts', 'magic/sites', 'wans')

    self.add('AUTH', 'accounts', 'pages/projects')
    self.add('AUTH', 'accounts', 'pages/projects', 'deployments', content_type={'POST':'multipart/form-data'})
    self.add('AUTH', 'accounts', 'pages/projects', 'deployments', 'history/logs')
    self.add('AUTH', 'accounts', 'pages/projects', 'deployments', 'retry')
    self.add('AUTH', 'accounts', 'pages/projects', 'deployments', 'rollback')
    self.add('AUTH', 'accounts', 'pages/projects', 'domains')
    self.add('AUTH', 'accounts', 'pages/projects', 'purge_build_cache')

    self.add('AUTH', 'accounts', 'pcaps')
    self.add('AUTH', 'accounts', 'pcaps', 'download')
    self.add('AUTH', 'accounts', 'pcaps/ownership')
    self.add('AUTH', 'accounts', 'pcaps/ownership/validate')

    self.add('AUTH', 'accounts', 'queues')
    self.add('AUTH', 'accounts', 'queues', 'consumers')
    self.add('AUTH', 'accounts', 'queues', 'messages/ack')
    self.add('AUTH', 'accounts', 'queues', 'messages/pull')

    self.add('AUTH', 'accounts', 'teamnet/routes')
    self.add('AUTH', 'accounts', 'teamnet/routes/ip')
    self.add('AUTH', 'accounts', 'teamnet/routes/network')
    self.add('AUTH', 'accounts', 'teamnet/virtual_networks')

    self.add('AUTH', 'accounts', 'urlscanner/scan')
    self.add('AUTH', 'accounts', 'urlscanner/scan', 'har')
    self.add('AUTH', 'accounts', 'urlscanner/scan', 'screenshot')

    self.add('AUTH', 'accounts', 'hyperdrive/configs')

    self.add('AUTH', 'accounts', 'warp_connector')
    self.add('AUTH', 'accounts', 'warp_connector', 'token')

    self.add('AUTH', 'accounts', 'zerotrust/connectivity_settings')

    self.add('AUTH', 'accounts', 'd1/database')
    self.add('AUTH', 'accounts', 'd1/database', 'query')

    self.add('AUTH', 'accounts', 'zt_risk_scoring')
    self.add('AUTH', 'accounts', 'zt_risk_scoring', 'reset')
    self.add('AUTH', 'accounts', 'zt_risk_scoring/behaviors')
    self.add('AUTH', 'accounts', 'zt_risk_scoring/summary')

def zones_extras(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'acm/total_tls')

    self.add('AUTH', 'zones', 'cache/cache_reserve')
    self.add('AUTH', 'zones', 'cache/cache_reserve_clear')
    self.add('AUTH', 'zones', 'cache/origin_post_quantum_encryption')
    self.add('AUTH', 'zones', 'cache/regional_tiered_cache')
    self.add('AUTH', 'zones', 'cache/tiered_cache_smart_topology_enable')
    self.add('AUTH', 'zones', 'cache/variants')

    self.add('AUTH', 'zones', 'managed_headers')
    self.add('AUTH', 'zones', 'page_shield')
    self.add('AUTH', 'zones', 'page_shield/policies')
    self.add('AUTH', 'zones', 'page_shield/scripts')
    self.add('AUTH', 'zones', 'page_shield/connections')
    self.add('AUTH', 'zones', 'rulesets')
    self.add('AUTH', 'zones', 'rulesets', 'rules')
    self.add('AUTH', 'zones', 'rulesets', 'versions')
    self.add('AUTH', 'zones', 'rulesets/phases', 'entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases', 'entrypoint/versions')
    self.add('AUTH', 'zones', 'rulesets/phases', 'versions')
    self.add('AUTH', 'zones', 'rulesets/phases/http_custom_errors/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_config_settings/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_request_dynamic_redirect/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_request_origin/entrypoint')

    self.add('AUTH', 'zones', 'url_normalization')

    self.add('AUTH', 'zones', 'hostnames/settings')
    self.add('AUTH', 'zones', 'snippets', content_type={'PUT':'multipart/form-data'})
    self.add('AUTH', 'zones', 'snippets', 'content')
    self.add('AUTH', 'zones', 'snippets/snippet_rules')

    self.add('AUTH', 'zones', 'speed_api/availabilities')
    self.add('AUTH', 'zones', 'speed_api/pages')
    self.add('AUTH', 'zones', 'speed_api/pages', 'tests')
    self.add('AUTH', 'zones', 'speed_api/pages', 'trend')
    self.add('AUTH', 'zones', 'speed_api/schedule')

    self.add('AUTH', 'zones', 'dcv_delegation/uuid')

def zones_web3(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'web3/hostnames')
    self.add('AUTH', 'zones', 'web3/hostnames', 'ipfs_universal_path/content_list')
    self.add('AUTH', 'zones', 'web3/hostnames', 'ipfs_universal_path/content_list/entries')

def accounts_email(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'email/routing/addresses')

def accounts_r2(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'r2/buckets')
    self.add('AUTH', 'accounts', 'r2/buckets', 'usage')
    self.add('AUTH', 'accounts', 'r2/buckets', 'objects')
    self.add('AUTH', 'accounts', 'r2/buckets', 'sippy')

    self.add('AUTH', 'accounts', 'event_notifications/r2', 'configuration')
    self.add('AUTH', 'accounts', 'event_notifications/r2', 'configuration/queues')


def zones_email(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'email/routing')
    self.add('AUTH', 'zones', 'email/routing/disable')
    self.add('AUTH', 'zones', 'email/routing/dns')
    self.add('AUTH', 'zones', 'email/routing/enable')
    self.add('AUTH', 'zones', 'email/routing/rules')
    self.add('AUTH', 'zones', 'email/routing/rules/catch_all')

def zones_api_gateway(self):
    """ :meta private: """

    self.add('AUTH', 'zones', 'api_gateway/configuration')
    self.add('AUTH', 'zones', 'api_gateway/discovery')
    self.add('AUTH', 'zones', 'api_gateway/discovery/operations')
    self.add('AUTH', 'zones', 'api_gateway/operations')
    self.add('AUTH', 'zones', 'api_gateway/operations', 'schema_validation')
#   self.add('AUTH', 'zones', 'api_gateway/operations/schema_validation')
    self.add('AUTH', 'zones', 'api_gateway/schemas')
    self.add('AUTH', 'zones', 'api_gateway/settings/schema_validation')
    self.add('AUTH', 'zones', 'api_gateway/user_schemas', content_type={'POST':'multipart/form-data'})
    self.add('AUTH', 'zones', 'api_gateway/user_schemas', 'operations')

def radar(self):
    """ :meta private: """

    self.add('AUTH', 'radar/alerts')
    self.add('AUTH', 'radar/alerts/locations')
    self.add('AUTH', 'radar/annotations/outages')
    self.add('AUTH', 'radar/annotations/outages/locations')

    self.add('AUTH', 'radar/datasets')
    self.add('AUTH', 'radar/datasets/download')

    self.add('AUTH', 'radar/dns/top/ases')
    self.add('AUTH', 'radar/dns/top/locations')

    self.add('AUTH', 'radar/entities/asns')
    self.add('AUTH', 'radar/entities/asns', 'rel')
    self.add('AUTH', 'radar/entities/asns/ip')
    self.add('AUTH', 'radar/entities/ip')
    self.add('AUTH', 'radar/entities/locations')

    self.add('AUTH', 'radar/netflows/timeseries')
    self.add('AUTH', 'radar/netflows/top/ases')
    self.add('AUTH', 'radar/netflows/top/locations')

    self.add('AUTH', 'radar/performance/iqi/summary')
    self.add('AUTH', 'radar/performance/iqi/timeseries_groups')

    self.add('AUTH', 'radar/quality/iqi/summary')
    self.add('AUTH', 'radar/quality/iqi/timeseries_groups')
    self.add('AUTH', 'radar/quality/speed/histogram')
    self.add('AUTH', 'radar/quality/speed/summary')
    self.add('AUTH', 'radar/quality/speed/top/ases')
    self.add('AUTH', 'radar/quality/speed/top/locations')

    self.add('AUTH', 'radar/ranking/domain')
    self.add('AUTH', 'radar/ranking/timeseries')
    self.add('AUTH', 'radar/ranking/timeseries_groups')
    self.add('AUTH', 'radar/ranking/top')

    self.add('AUTH', 'radar/search/global')

    self.add('AUTH', 'radar/specialevents')

    self.add('AUTH', 'radar/verified_bots/top/bots')
    self.add('AUTH', 'radar/verified_bots/top/categories')

    self.add('AUTH', 'radar/connection_tampering/summary')
    self.add('AUTH', 'radar/connection_tampering/timeseries_groups')
    self.add('AUTH', 'radar/traffic_anomalies')
    self.add('AUTH', 'radar/traffic_anomalies/locations')

def radar_as112(self):
    """ :meta private: """

    self.add('AUTH', 'radar/as112/summary/dnssec')
    self.add('AUTH', 'radar/as112/summary/edns')
    self.add('AUTH', 'radar/as112/summary/ip_version')
    self.add('AUTH', 'radar/as112/summary/protocol')
    self.add('AUTH', 'radar/as112/summary/query_type')
    self.add('AUTH', 'radar/as112/summary/response_codes')

    self.add('AUTH', 'radar/as112/timeseries')
    self.add('AUTH', 'radar/as112/timeseries/dnssec')
    self.add('AUTH', 'radar/as112/timeseries/edns')
    self.add('AUTH', 'radar/as112/timeseries/ip_version')
    self.add('AUTH', 'radar/as112/timeseries/protocol')
    self.add('AUTH', 'radar/as112/timeseries/query_type')
    self.add('AUTH', 'radar/as112/timeseries/response_codes')

    self.add('AUTH', 'radar/as112/timeseries_groups/dnssec')
    self.add('AUTH', 'radar/as112/timeseries_groups/edns')
    self.add('AUTH', 'radar/as112/timeseries_groups/ip_version')
    self.add('AUTH', 'radar/as112/timeseries_groups/protocol')
    self.add('AUTH', 'radar/as112/timeseries_groups/query_type')
    self.add('AUTH', 'radar/as112/timeseries_groups/response_codes')

    self.add('AUTH', 'radar/as112/top/locations')
    self.add('AUTH', 'radar/as112/top/locations/dnssec')
    self.add('AUTH', 'radar/as112/top/locations/edns')
    self.add('AUTH', 'radar/as112/top/locations/ip_version')

def radar_attacks(self):
    """ :meta private: """

    self.add('AUTH', 'radar/attacks/layer3/summary')
    self.add('AUTH', 'radar/attacks/layer3/timeseries')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups')
    self.add('AUTH', 'radar/attacks/layer3/summary/bitrate')
    self.add('AUTH', 'radar/attacks/layer3/summary/duration')
    self.add('AUTH', 'radar/attacks/layer3/summary/ip_version')
    self.add('AUTH', 'radar/attacks/layer3/summary/protocol')
    self.add('AUTH', 'radar/attacks/layer3/summary/vector')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups/bitrate')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups/duration')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups/industry')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups/ip_version')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups/protocol')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups/vector')
    self.add('AUTH', 'radar/attacks/layer3/timeseries_groups/vertical')
    self.add('AUTH', 'radar/attacks/layer3/top/attacks')
    self.add('AUTH', 'radar/attacks/layer3/top/industry')
    self.add('AUTH', 'radar/attacks/layer3/top/locations/origin')
    self.add('AUTH', 'radar/attacks/layer3/top/locations/target')
    self.add('AUTH', 'radar/attacks/layer3/top/vertical')

    self.add('AUTH', 'radar/attacks/layer7/summary')
    self.add('AUTH', 'radar/attacks/layer7/summary/http_method')
    self.add('AUTH', 'radar/attacks/layer7/summary/http_version')
    self.add('AUTH', 'radar/attacks/layer7/summary/ip_version')
    self.add('AUTH', 'radar/attacks/layer7/summary/managed_rules')
    self.add('AUTH', 'radar/attacks/layer7/summary/mitigation_product')
    self.add('AUTH', 'radar/attacks/layer7/timeseries')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups/http_method')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups/http_version')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups/industry')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups/ip_version')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups/managed_rules')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups/mitigation_product')
    self.add('AUTH', 'radar/attacks/layer7/timeseries_groups/vertical')
    self.add('AUTH', 'radar/attacks/layer7/top/ases/origin')
    self.add('AUTH', 'radar/attacks/layer7/top/attacks')
    self.add('AUTH', 'radar/attacks/layer7/top/industry')
    self.add('AUTH', 'radar/attacks/layer7/top/locations/origin')
    self.add('AUTH', 'radar/attacks/layer7/top/locations/target')
    self.add('AUTH', 'radar/attacks/layer7/top/vertical')

def radar_bgp(self):
    """ :meta private: """

    self.add('AUTH', 'radar/bgp/leaks/events')
    self.add('AUTH', 'radar/bgp/timeseries')
    self.add('AUTH', 'radar/bgp/top/ases')
    self.add('AUTH', 'radar/bgp/top/ases/prefixes')
    self.add('AUTH', 'radar/bgp/top/prefixes')
    self.add('AUTH', 'radar/bgp/hijacks/events')
    self.add('AUTH', 'radar/bgp/routes/moas')
    self.add('AUTH', 'radar/bgp/routes/pfx2as')
    self.add('AUTH', 'radar/bgp/routes/stats')
    self.add('AUTH', 'radar/bgp/routes/timeseries')

def radar_email(self):
    """ :meta private: """

    self.add('AUTH', 'radar/email/routing/summary/arc')
    self.add('AUTH', 'radar/email/routing/summary/dkim')
    self.add('AUTH', 'radar/email/routing/summary/dmarc')
    self.add('AUTH', 'radar/email/routing/summary/encrypted')
    self.add('AUTH', 'radar/email/routing/summary/ip_version')
    self.add('AUTH', 'radar/email/routing/summary/spf')
    self.add('AUTH', 'radar/email/routing/timeseries_groups/arc')
    self.add('AUTH', 'radar/email/routing/timeseries_groups/dkim')
    self.add('AUTH', 'radar/email/routing/timeseries_groups/dmarc')
    self.add('AUTH', 'radar/email/routing/timeseries_groups/encrypted')
    self.add('AUTH', 'radar/email/routing/timeseries_groups/ip_version')
    self.add('AUTH', 'radar/email/routing/timeseries_groups/spf')

    self.add('AUTH', 'radar/email/security/summary/arc')
    self.add('AUTH', 'radar/email/security/summary/dkim')
    self.add('AUTH', 'radar/email/security/summary/dmarc')
    self.add('AUTH', 'radar/email/security/summary/malicious')
    self.add('AUTH', 'radar/email/security/summary/spam')
    self.add('AUTH', 'radar/email/security/summary/spf')
    self.add('AUTH', 'radar/email/security/summary/spoof')
    self.add('AUTH', 'radar/email/security/summary/threat_category')
    self.add('AUTH', 'radar/email/security/summary/tls_version')

    self.add('AUTH', 'radar/email/security/timeseries/arc')
    self.add('AUTH', 'radar/email/security/timeseries/dkim')
    self.add('AUTH', 'radar/email/security/timeseries/dmarc')
    self.add('AUTH', 'radar/email/security/timeseries/malicious')
    self.add('AUTH', 'radar/email/security/timeseries/spam')
    self.add('AUTH', 'radar/email/security/timeseries/spf')
    self.add('AUTH', 'radar/email/security/timeseries/threat_category')
    self.add('AUTH', 'radar/email/security/timeseries_groups/arc')
    self.add('AUTH', 'radar/email/security/timeseries_groups/dkim')
    self.add('AUTH', 'radar/email/security/timeseries_groups/dmarc')
    self.add('AUTH', 'radar/email/security/timeseries_groups/malicious')
    self.add('AUTH', 'radar/email/security/timeseries_groups/spam')
    self.add('AUTH', 'radar/email/security/timeseries_groups/spf')
    self.add('AUTH', 'radar/email/security/timeseries_groups/spoof')
    self.add('AUTH', 'radar/email/security/timeseries_groups/threat_category')
    self.add('AUTH', 'radar/email/security/timeseries_groups/tls_version')

    self.add('AUTH', 'radar/email/security/top/ases')
    self.add('AUTH', 'radar/email/security/top/ases/arc')
    self.add('AUTH', 'radar/email/security/top/ases/dkim')
    self.add('AUTH', 'radar/email/security/top/ases/dmarc')
    self.add('AUTH', 'radar/email/security/top/ases/malicious')
    self.add('AUTH', 'radar/email/security/top/ases/spam')
    self.add('AUTH', 'radar/email/security/top/ases/spf')
    self.add('AUTH', 'radar/email/security/top/locations')
    self.add('AUTH', 'radar/email/security/top/locations/arc')
    self.add('AUTH', 'radar/email/security/top/locations/dkim')
    self.add('AUTH', 'radar/email/security/top/locations/dmarc')
    self.add('AUTH', 'radar/email/security/top/locations/malicious')
    self.add('AUTH', 'radar/email/security/top/locations/spam')
    self.add('AUTH', 'radar/email/security/top/locations/spf')
    self.add('AUTH', 'radar/email/security/top/tlds')
    self.add('AUTH', 'radar/email/security/top/tlds/malicious')
    self.add('AUTH', 'radar/email/security/top/tlds/spam')
    self.add('AUTH', 'radar/email/security/top/tlds/spoof')

def radar_http(self):
    """ :meta private: """


    self.add('AUTH', 'radar/http/summary/bot_class')
    self.add('AUTH', 'radar/http/summary/device_type')
    self.add('AUTH', 'radar/http/summary/http_protocol')
    self.add('AUTH', 'radar/http/summary/http_version')
    self.add('AUTH', 'radar/http/summary/ip_version')
    self.add('AUTH', 'radar/http/summary/os')
    self.add('AUTH', 'radar/http/summary/post_quantum')
    self.add('AUTH', 'radar/http/summary/tls_version')

    self.add('AUTH', 'radar/http/timeseries/bot_class')
    self.add('AUTH', 'radar/http/timeseries/browser')
    self.add('AUTH', 'radar/http/timeseries/browser_family')
    self.add('AUTH', 'radar/http/timeseries/device_type')
    self.add('AUTH', 'radar/http/timeseries/http_protocol')
    self.add('AUTH', 'radar/http/timeseries/http_version')
    self.add('AUTH', 'radar/http/timeseries/ip_version')
    self.add('AUTH', 'radar/http/timeseries/os')
    self.add('AUTH', 'radar/http/timeseries/tls_version')

    self.add('AUTH', 'radar/http/timeseries_groups/bot_class')
    self.add('AUTH', 'radar/http/timeseries_groups/browser')
    self.add('AUTH', 'radar/http/timeseries_groups/browser_family')
    self.add('AUTH', 'radar/http/timeseries_groups/device_type')
    self.add('AUTH', 'radar/http/timeseries_groups/http_protocol')
    self.add('AUTH', 'radar/http/timeseries_groups/http_version')
    self.add('AUTH', 'radar/http/timeseries_groups/ip_version')
    self.add('AUTH', 'radar/http/timeseries_groups/os')
    self.add('AUTH', 'radar/http/timeseries_groups/post_quantum')
    self.add('AUTH', 'radar/http/timeseries_groups/tls_version')

    self.add('AUTH', 'radar/http/top/ases')
    self.add('AUTH', 'radar/http/top/ases/bot_class')
    self.add('AUTH', 'radar/http/top/ases/browser_family')
    self.add('AUTH', 'radar/http/top/ases/device_type')
    self.add('AUTH', 'radar/http/top/ases/http_protocol')
    self.add('AUTH', 'radar/http/top/ases/http_version')
    self.add('AUTH', 'radar/http/top/ases/ip_version')
    self.add('AUTH', 'radar/http/top/ases/os')
    self.add('AUTH', 'radar/http/top/ases/tls_version')
    self.add('AUTH', 'radar/http/top/browsers')
    self.add('AUTH', 'radar/http/top/browser_families')
    self.add('AUTH', 'radar/http/top/locations')
    self.add('AUTH', 'radar/http/top/locations/bot_class')
    self.add('AUTH', 'radar/http/top/locations/browser_family')
    self.add('AUTH', 'radar/http/top/locations/device_type')
    self.add('AUTH', 'radar/http/top/locations/http_protocol')
    self.add('AUTH', 'radar/http/top/locations/http_version')
    self.add('AUTH', 'radar/http/top/locations/ip_version')
    self.add('AUTH', 'radar/http/top/locations/os')
    self.add('AUTH', 'radar/http/top/locations/tls_version')

def from_developers(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'analytics_engine/sql')

    self.add('AUTH', 'accounts', 'logpush/jobs')
    self.add('AUTH', 'accounts', 'logpush/datasets', 'fields')
    self.add('AUTH', 'accounts', 'logpush/datasets', 'jobs')
    self.add('AUTH', 'accounts', 'logpush/ownership')
    self.add('AUTH', 'accounts', 'logpush/ownership/validate')
    self.add('AUTH', 'accounts', 'logpush/validate/destination/exists')
    self.add('AUTH', 'accounts', 'logpush/validate/origin')

    self.add('AUTH', 'accounts', 'logs/retrieve')
    self.add('AUTH', 'accounts', 'logs/control/cmb/config')

    self.add('AUTH', 'accounts', 'magic/advanced_tcp_protection/configs/allowlist')
    self.add('AUTH', 'accounts', 'magic/advanced_tcp_protection/configs/prefixes')
    self.add('AUTH', 'accounts', 'magic/advanced_tcp_protection/configs/prefixes/bulk')
    self.add('AUTH', 'accounts', 'magic/advanced_tcp_protection/configs/syn_protection/rules')
    self.add('AUTH', 'accounts', 'magic/advanced_tcp_protection/configs/tcp_flow_protection/rules')
    self.add('AUTH', 'accounts', 'magic/advanced_tcp_protection/configs/tcp_protection_status')

    self.add('AUTH', 'accounts', 'pubsub/namespaces')
    self.add('AUTH', 'accounts', 'pubsub/namespaces', 'brokers')
    self.add('AUTH', 'accounts', 'pubsub/namespaces', 'brokers', 'credentials')

    self.add('AUTH', 'accounts', 'rulesets/phases/ddos_l4/entrypoint')
    self.add('AUTH', 'accounts', 'rulesets/phases/ddos_l7/entrypoint')
    self.add('AUTH', 'accounts', 'rulesets/phases/http_request_firewall_custom/entrypoint')
    self.add('AUTH', 'accounts', 'rulesets/phases/http_request_firewall_managed/entrypoint')

    self.add('AUTH', 'accounts', 'stream', 'captions', 'vtt')
    self.add('AUTH', 'accounts', 'stream/analytics/views')
    self.add('AUTH', 'accounts', 'stream/live_inputs', 'videos')
    self.add('AUTH', 'accounts', 'stream/storage-usage')

#   self.add('AUTH', 'organizations', 'load_balancers/monitors')

    self.add('AUTH', 'users')

    self.add('AUTH', 'zones', 'content-upload-scan/disable')
    self.add('AUTH', 'zones', 'content-upload-scan/enable')
    self.add('AUTH', 'zones', 'content-upload-scan/payloads')
    self.add('AUTH', 'zones', 'content-upload-scan/settings')

    self.add('AUTH', 'zones', 'phases/http_request_firewall_managed/entrypoint')

    self.add('AUTH', 'zones', 'rulesets/phases/ddos_l7/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_ratelimit/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_request_cache_settings/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_request_firewall_custom/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_request_firewall_managed/entrypoint')
    self.add('AUTH', 'zones', 'rulesets/phases/http_request_firewall_managed/entrypoint/versions')

    self.add('AUTH', 'zones', 'certificate_authorities/hostname_associations')
    self.add('AUTH', 'zones', 'hold')

    self.add('AUTH', 'accounts', 'challenges/widgets')
    self.add('AUTH', 'accounts', 'challenges/widgets', 'rotate_secret')
    self.add('AUTH', 'accounts', 'mtls_certificates')
    self.add('AUTH', 'accounts', 'mtls_certificates', 'associations')
    self.add('AUTH', 'accounts', 'request-tracer/trace')

def accounts_cloudforce_one(self):
    """ :meta private: """

    self.add('AUTH', 'accounts', 'cloudforce-one/requests')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests', 'message')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests', 'message/new')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests/constants')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests/new')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests/priority')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests/priority/new')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests/priority/quota')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests/quota')
    self.add('AUTH', 'accounts', 'cloudforce-one/requests/types')
