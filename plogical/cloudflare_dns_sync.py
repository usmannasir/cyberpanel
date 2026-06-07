#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""
Cloudflare DNS sync helpers for CyberPanel website / child domain lifecycle.
"""
import os
import shlex

import tldextract

from plogical import CyberCPLogFileWriter as logging
from plogical.cloudflareClient import get_cloudflare_client
from plogical.processUtilities import ProcessUtilities

try:
    from dns.models import Domains, Records
    from websiteFunctions.models import Websites, ChildDomains
except Exception:
    pass


class CloudflareDnsSync:
    CFPath = '/home/cyberpanel/CloudFlare'

    @staticmethod
    def load_admin_cf_config(admin_user_name):
        cf_file = '%s%s' % (CloudflareDnsSync.CFPath, admin_user_name)
        if not os.path.exists(cf_file):
            return None
        data = open(cf_file, 'r').readlines()
        email = data[0].strip() if len(data) > 0 else ''
        token = data[1].strip() if len(data) > 1 else ''
        status = data[2].strip() if len(data) > 2 else ''
        if status != 'Enable':
            return None
        if not token:
            return None
        return {'email': email, 'token': token, 'cf': get_cloudflare_client(email, token)}

    @staticmethod
    def resolve_zone(cf, domain_name):
        domain_name = (domain_name or '').rstrip('.').lower()
        params = {'name': domain_name, 'per_page': 50}
        zones = cf.zones.get(params=params)
        for z in sorted(zones, key=lambda v: v['name']):
            if z['name'].rstrip('.').lower() == domain_name:
                return z['id'], z['name']
        if '.' in domain_name:
            parent = domain_name.split('.', 1)[1]
            params = {'name': parent, 'per_page': 50}
            zones = cf.zones.get(params=params)
            for z in sorted(zones, key=lambda v: v['name']):
                if z['name'].rstrip('.').lower() == parent:
                    return z['id'], z['name']
        return None, None

    @staticmethod
    def record_to_fqdn(record_name, zone_name):
        n = (record_name or '').rstrip('.').lower()
        z = (zone_name or '').rstrip('.').lower()
        if not z:
            return n
        if n == z or n.endswith('.' + z):
            return n
        return ('%s.%s' % (n, z)).rstrip('.')

    @staticmethod
    def list_zone_records(cf, zone_id):
        records = []
        page = 1
        per_page = 100
        while True:
            batch = cf.zones.dns_records.get(
                zone_id, params={'per_page': per_page, 'page': page})
            if not batch:
                break
            records.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return records

    @staticmethod
    def upsert_dns_record(cf, zone_id, zone_name, name, record_type, value, priority, ttl, proxied=None):
        if value and str(value).find('DKIM') > -1:
            value = str(value).replace('\n\t', '').replace('"', '')

        if proxied is None and record_type in ['A', 'AAAA', 'CNAME']:
            name_lower = name.lower()
            mail_prefixes = ('mail.', 'smtp.', 'imap.', 'pop3.', 'pop.', 'autodiscover.', 'webmail.')
            is_mail = (
                any(name_lower.startswith(p) for p in mail_prefixes) or
                any('.%s' % p.rstrip('.') in name_lower for p in mail_prefixes)
            )
            proxied = not is_mail
        elif record_type not in ['A', 'AAAA', 'CNAME']:
            proxied = False

        if ttl and int(ttl) > 0:
            dns_record = {
                'name': name, 'type': record_type, 'content': value,
                'ttl': int(ttl), 'priority': priority,
            }
        else:
            dns_record = {
                'name': name, 'type': record_type, 'content': value, 'priority': priority,
            }
        if record_type in ['A', 'AAAA', 'CNAME']:
            dns_record['proxied'] = proxied

        target_fqdn = CloudflareDnsSync.record_to_fqdn(name, zone_name).rstrip('.').lower()
        existing = CloudflareDnsSync.list_zone_records(cf, zone_id)
        matches = []
        for rec in existing:
            if (rec.get('type') or '').upper() != record_type.upper():
                continue
            fqdn = CloudflareDnsSync.record_to_fqdn(rec.get('name'), zone_name).rstrip('.').lower()
            if fqdn == target_fqdn:
                matches.append(rec)

        for rec in matches:
            same_content = (rec.get('content') or '') == value
            same_proxy = rec.get('proxied', False) == dns_record.get('proxied', False)
            if same_content and same_proxy:
                return
            cf.zones.dns_records.put(zone_id, rec['id'], data=dns_record)
            logging.CyberCPLogFileWriter.writeToFile(
                'Updated Cloudflare %s record for %s' % (record_type, name), 0)
            return

        cf.zones.dns_records.post(zone_id, data=dns_record)

    @staticmethod
    def delete_local_dns_records_for_host(domain_name):
        try:
            extract = tldextract.TLDExtract(cache_dir=None)
            parsed = extract(domain_name)
            apex = parsed.domain + '.' + parsed.suffix
            if not parsed.subdomain:
                return 1, 'Skipped apex zone records'
            zone = Domains.objects.get(name=apex)
        except Exception:
            return 1, 'No local zone to clean'

        host = domain_name.rstrip('.').lower()
        deleted = 0
        for record in Records.objects.filter(domain_id=zone.id):
            name = (record.name or '').rstrip('.').lower()
            if name == host or name.endswith('.' + host):
                record.delete()
                deleted += 1

        if deleted:
            from plogical.dnsUtilities import DNS
            DNS.bumpSOASerial(zone)
            logging.CyberCPLogFileWriter.writeToFile(
                'Deleted %s local DNS records for %s' % (deleted, domain_name), 0)
        return 1, 'Deleted %s local records' % deleted

    @staticmethod
    def delete_cloudflare_records_for_host(domain_name, admin_user_name=None):
        try:
            if not admin_user_name:
                try:
                    website = Websites.objects.get(domain=domain_name)
                    admin_user_name = website.admin.userName
                except Exception:
                    child = ChildDomains.objects.get(domain=domain_name)
                    admin_user_name = child.master.admin.userName

            cfg = CloudflareDnsSync.load_admin_cf_config(admin_user_name)
            if not cfg:
                return 1, 'Cloudflare sync not enabled'

            cf = cfg['cf']
            zone_id, zone_name = CloudflareDnsSync.resolve_zone(cf, domain_name)
            if not zone_id:
                return 1, 'Domain not found in Cloudflare'

            base_fqdn = domain_name.rstrip('.').lower()
            zone_fqdn = zone_name.rstrip('.').lower()
            is_subdomain = base_fqdn != zone_fqdn

            dns_records = CloudflareDnsSync.list_zone_records(cf, zone_id)
            if is_subdomain:
                to_delete = []
                for record in dns_records:
                    fqdn = CloudflareDnsSync.record_to_fqdn(record.get('name'), zone_name)
                    if fqdn == base_fqdn or fqdn.endswith('.' + base_fqdn):
                        to_delete.append(record)
            else:
                to_delete = list(dns_records)

            deleted_count = 0
            for record in to_delete:
                try:
                    cf.zones.dns_records.delete(zone_id, record['id'])
                    deleted_count += 1
                except Exception as exc:
                    logging.CyberCPLogFileWriter.writeToFile(
                        'Error deleting Cloudflare record %s for %s: %s' % (
                            record.get('id'), domain_name, str(exc)))

            if deleted_count:
                logging.CyberCPLogFileWriter.writeToFile(
                    'Deleted %s CloudFlare DNS records for %s' % (deleted_count, domain_name))
            return 1, 'Deleted %s DNS records' % deleted_count
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                'Error in delete_cloudflare_records_for_host for %s: %s' % (domain_name, str(msg)))
            return 0, str(msg)

    @staticmethod
    def cleanup_host_dns_records(domain_name, admin_user_name=None):
        CloudflareDnsSync.delete_local_dns_records_for_host(domain_name)
        return CloudflareDnsSync.delete_cloudflare_records_for_host(domain_name, admin_user_name)

    @staticmethod
    def collect_valid_hosts_for_apex(apex_domain):
        apex = apex_domain.rstrip('.').lower()
        valid = {apex}
        for site in Websites.objects.filter(domain=apex):
            valid.add(site.domain.rstrip('.').lower())
        for site in Websites.objects.filter(domain__iendswith='.' + apex):
            valid.add(site.domain.rstrip('.').lower())
        for child in ChildDomains.objects.filter(domain__iendswith='.' + apex):
            valid.add(child.domain.rstrip('.').lower())
        for child in ChildDomains.objects.filter(domain=apex):
            valid.add(child.domain.rstrip('.').lower())
        return valid

    @staticmethod
    def host_is_managed_in_panel(fqdn, valid_hosts, apex):
        fqdn = (fqdn or '').rstrip('.').lower()
        apex = (apex or '').rstrip('.').lower()
        if fqdn in valid_hosts:
            return True
        for host in valid_hosts:
            if host == apex:
                continue
            if fqdn == host:
                return True
            if fqdn == ('www.%s' % host) or fqdn == ('mail.%s' % host):
                return True
            if fqdn.endswith('.' + host):
                return True
        return False

    @staticmethod
    def prune_orphan_cloudflare_hosts(apex_domain, admin_user_name):
        """Remove Cloudflare host records under apex that are not in CyberPanel."""
        try:
            from plogical.acl import ACLManager

            cfg = CloudflareDnsSync.load_admin_cf_config(admin_user_name)
            if not cfg:
                return 0, 'Cloudflare sync not enabled'

            apex = apex_domain.rstrip('.').lower()
            cf = cfg['cf']
            zone_id, zone_name = CloudflareDnsSync.resolve_zone(cf, apex)
            if not zone_id:
                return 0, 'Zone not found in Cloudflare'

            valid_hosts = CloudflareDnsSync.collect_valid_hosts_for_apex(apex)
            server_ip = ACLManager.GetServerIP()
            server_ipv6 = ACLManager.GetServerIPv6() or ''

            dns_records = CloudflareDnsSync.list_zone_records(cf, zone_id)
            orphan_hosts = set()

            for record in dns_records:
                rtype = (record.get('type') or '').upper()
                if rtype not in ('A', 'AAAA', 'CNAME'):
                    continue
                fqdn = CloudflareDnsSync.record_to_fqdn(record.get('name'), zone_name)
                if CloudflareDnsSync.host_is_managed_in_panel(fqdn, valid_hosts, apex):
                    continue
                if not fqdn.endswith('.' + apex) and fqdn != apex:
                    continue
                content = record.get('content') or ''
                if rtype == 'A' and content != server_ip:
                    continue
                if rtype == 'AAAA' and server_ipv6 and content != server_ipv6:
                    continue
                if rtype == 'CNAME' and not content.rstrip('.').lower().endswith('.' + apex):
                    continue
                orphan_hosts.add(fqdn)

            deleted_count = 0
            for fqdn in sorted(orphan_hosts):
                ok, _msg = CloudflareDnsSync.delete_cloudflare_records_for_host(fqdn, admin_user_name)
                if ok:
                    deleted_count += 1
                    CloudflareDnsSync.delete_local_dns_records_for_host(fqdn)

            logging.CyberCPLogFileWriter.writeToFile(
                'Pruned orphan Cloudflare hosts for %s: %s removed' % (apex, deleted_count), 0)
            return 1, 'Pruned %s orphan hosts' % deleted_count
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                'prune_orphan_cloudflare_hosts failed for %s: %s' % (apex_domain, str(msg)))
            return 0, str(msg)
