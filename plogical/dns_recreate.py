#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""
Full Recreate DNS: repair existing PowerDNS zones and force Cloudflare sync + NS status.
"""
from __future__ import print_function

import os

from plogical import CyberCPLogFileWriter as logging


def _machine_ip():
    try:
        with open('/etc/cyberpanel/machineIP', 'r') as fh:
            return fh.read().split('\n', 1)[0].strip()
    except Exception:
        return ''


def _server_ipv6():
    try:
        from plogical.acl import ACLManager
        return ACLManager.GetServerIPv6()
    except Exception:
        return None


def _bind_powerdns(DNS):
    Domains, Records = DNS._powerdns_models()
    import sys as _sys
    _mod = _sys.modules[DNS.__module__]
    _mod.Domains = Domains
    _mod.Records = Records
    return Domains, Records


def _upsert_simple(Records, DNS, zone, name, rtype, value, priority=0, ttl=3600):
    """Create or update a single non-TXT address/CNAME-style record; drop duplicates."""
    name = (name or '').rstrip('.').lower()
    value = (value or '').strip()
    if not name or not value:
        return 0
    rows = list(Records.objects.filter(domainOwner=zone, name=name, type=rtype))
    changed = 0
    if not rows:
        DNS.createDNSRecord(zone, name, rtype, value, priority, ttl)
        return 1
    first = rows[0]
    need = (first.content or '') != value
    if rtype.upper() == 'MX':
        try:
            need = need or int(first.prio or 0) != int(priority)
        except (TypeError, ValueError):
            need = True
    if need:
        first.content = value
        first.ttl = ttl
        if rtype.upper() == 'MX':
            first.prio = str(priority)
        first.save()
        try:
            DNS.bumpSOASerial(zone)
        except Exception:
            pass
        changed = 1
    for extra in rows[1:]:
        try:
            extra.delete()
            changed += 1
        except Exception:
            pass
    return changed


def _ensure_cname(Records, DNS, zone, name, target):
    name = (name or '').rstrip('.').lower()
    target = (target or '').rstrip('.').lower()
    if not name or not target:
        return 0
    # Prefer CNAME; do not overwrite an existing A/AAAA for the same name
    if Records.objects.filter(domainOwner=zone, name=name, type__in=['A', 'AAAA']).exists():
        return 0
    return _upsert_simple(Records, DNS, zone, name, 'CNAME', target)


def _ensure_mx(Records, DNS, zone, name, exchange, priority=10):
    name = (name or '').rstrip('.').lower()
    exchange = (exchange or '').rstrip('.').lower()
    if not name or not exchange:
        return 0
    existing = list(Records.objects.filter(domainOwner=zone, name=name, type='MX'))
    if existing:
        # Keep custom MX sets; only fix empty exchange on the first row
        return 0
    DNS.createDNSRecord(zone, name, 'MX', exchange, priority, 3600)
    return 1


def ensure_host_template_records(host, admin, DNS=None):
    """
    Ensure standard template records exist for an existing (or new) host zone.
    Updates wrong A records to the current machine IP. Does not delete custom records.
    Returns (changed_count, error_or_None).
    """
    try:
        from plogical.dnsUtilities import DNS as DNSClass
        DNS = DNS or DNSClass
        Domains, Records = _bind_powerdns(DNS)

        import tldextract
        host = (host or '').strip().lower().rstrip('.')
        if not host:
            return 0, 'Empty hostname'

        extract = tldextract.TLDExtract(cache_dir=None)
        ex = extract(host)
        if not ex.domain or not ex.suffix:
            return 0, 'Invalid hostname'
        apex = (ex.domain + '.' + ex.suffix).lower()

        # Create zone from scratch when missing
        if Domains.objects.filter(name=apex).count() == 0:
            DNS.dnsTemplate(host, admin)
            Domains, Records = _bind_powerdns(DNS)

        zone = Domains.objects.filter(name=apex).first()
        if not zone:
            return 0, 'No DNS zone for %s' % apex

        ip_address = _machine_ip()
        ipv6 = _server_ipv6()
        changed = 0

        if ip_address:
            changed += _upsert_simple(Records, DNS, zone, host, 'A', ip_address)
            mail_host = 'mail.%s' % host
            if mail_host.find('mail.mail') == -1:
                changed += _upsert_simple(Records, DNS, zone, mail_host, 'A', ip_address)

        if ipv6:
            changed += _upsert_simple(Records, DNS, zone, host, 'AAAA', ipv6)
            mail_host = 'mail.%s' % host
            if mail_host.find('mail.mail') == -1:
                changed += _upsert_simple(Records, DNS, zone, mail_host, 'AAAA', ipv6)

        changed += _ensure_cname(Records, DNS, zone, 'www.%s' % host, host)
        changed += _ensure_cname(Records, DNS, zone, 'ftp.%s' % host, host)
        changed += _ensure_mx(Records, DNS, zone, host, host, 10)

        spf_changed, spf_err = DNS.UpsertSpfForName(host)
        if spf_err:
            logging.writeToFile('ensure_host SPF %s: %s' % (host, spf_err))
        else:
            changed += int(spf_changed or 0)

        if apex != host:
            spf_changed, spf_err = DNS.UpsertSpfForName(apex)
            if not spf_err:
                changed += int(spf_changed or 0)

        # Lightweight DKIM selector stub (createDNSRecord skips if content exists)
        DNS.createDNSRecord(zone, '_domainkey.%s' % host, 'TXT', 't=y; o=~;', 0, 3600)

        return changed, None
    except BaseException as msg:
        logging.writeToFile(str(msg) + ' [ensure_host_template_records]')
        return 0, str(msg)


def cloudflare_sync_and_status(domain, admin, DNS=None):
    """
    Force-sync local PowerDNS records into Cloudflare and report zone status / NS.
    Triggers Cloudflare activation_check when the zone is not active.
    """
    info = {
        'enabled': False,
        'synced': False,
        'zone_id': None,
        'zone_name': None,
        'zone_status': None,
        'name_servers': [],
        'activation_check': False,
        'message': '',
    }
    try:
        from plogical.dnsUtilities import DNS as DNSClass
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        from plogical.cloudflareClient import get_cloudflare_client

        DNS = DNS or DNSClass
        dns = DNS()
        dns.admin = admin
        if not dns.loadCFKeys():
            info['message'] = 'Cloudflare keys not configured for this user.'
            return info
        if dns.status != 'Enable':
            info['message'] = 'Cloudflare sync is disabled for this user.'
            return info

        info['enabled'] = True
        ok, err = dns.cfTemplate(domain, admin, enableCheck=True)
        info['synced'] = bool(ok)
        if not ok:
            info['message'] = err or 'Cloudflare sync failed.'
            # Still try to resolve zone for NS guidance
        cf = get_cloudflare_client(dns.email, dns.key)
        zone_id, zone_name = CloudflareDnsSync.resolve_zone(cf, domain)
        if not zone_id:
            if not info['message']:
                info['message'] = 'Cloudflare zone not found for %s' % domain
            return info

        info['zone_id'] = zone_id
        info['zone_name'] = zone_name
        try:
            zone = cf.zones.get(zone_id)
        except Exception:
            zone = None
        if isinstance(zone, dict):
            info['zone_status'] = zone.get('status')
            info['name_servers'] = list(zone.get('name_servers') or [])
        elif isinstance(zone, list) and zone:
            # Some client versions return a list for filtered gets
            z0 = zone[0]
            info['zone_status'] = z0.get('status')
            info['name_servers'] = list(z0.get('name_servers') or [])

        if info['zone_status'] and info['zone_status'] != 'active':
            try:
                cf.zones.activation_check.post(zone_id)
                info['activation_check'] = True
            except Exception as act_err:
                logging.writeToFile(
                    'Cloudflare activation_check %s: %s' % (domain, str(act_err)))

            ns = ', '.join(info['name_servers']) if info['name_servers'] else '(see Cloudflare dashboard)'
            info['message'] = (
                'Cloudflare zone status is "%s" (not active). '
                'At your domain registrar set nameservers to ONLY: %s. '
                'Disable DNSSEC at the registrar. '
                'Then wait for Cloudflare to activate (activation check %s). '
                'Public DNS will stay NXDOMAIN until the registrar uses those NS.'
            ) % (
                info['zone_status'],
                ns,
                'requested' if info['activation_check'] else 'not requested',
            )
        elif info['synced']:
            info['message'] = 'Cloudflare zone is active; records synced.'
        elif not info['message']:
            info['message'] = 'Cloudflare zone is active but sync reported an issue.'

        return info
    except BaseException as msg:
        logging.writeToFile(str(msg) + ' [cloudflare_sync_and_status]')
        info['message'] = str(msg)
        return info


def recreate_dns_for_domain(domainName, admin, includeChildren=True):
    """
    Full recreate: ensure template records on existing zones, upsert SPF,
    force Cloudflare sync, and return NS/status guidance when CF is pending.
    """
    result = {
        'status': 0,
        'message': '',
        'applied': [],
        'errors': [],
        'cloudflare': None,
    }
    try:
        from plogical.dnsUtilities import DNS
        from websiteFunctions.models import Websites, ChildDomains

        domain = (domainName or '').strip().lower().rstrip('.')
        if not domain:
            result['message'] = 'Missing domain name'
            return result

        _bind_powerdns(DNS)

        hosts = [domain]
        website = Websites.objects.filter(domain=domain).first()
        if includeChildren and website is not None:
            for child in ChildDomains.objects.filter(master=website):
                child_name = (child.domain or '').strip().lower().rstrip('.')
                if child_name and child_name not in hosts:
                    hosts.append(child_name)

        for host in hosts:
            try:
                # Seed from classic template (new zones + CF hook), then force-repair existing
                DNS.dnsTemplate(host, admin)
                changed, err = ensure_host_template_records(host, admin, DNS=DNS)
                if err:
                    result['errors'].append('%s: %s' % (host, err))
                else:
                    result['applied'].append(host)
                    if changed:
                        logging.writeToFile(
                            'RecreateDNS ensured %s record change(s) for %s' % (changed, host))
            except BaseException as host_err:
                result['errors'].append('%s: %s' % (host, str(host_err)))
                logging.writeToFile('recreate_dns_for_domain %s: %s' % (host, str(host_err)))

        # One Cloudflare pass on the primary domain (covers apex zone + children records)
        result['cloudflare'] = cloudflare_sync_and_status(domain, admin, DNS=DNS)

        if not result['applied'] and result['errors']:
            result['status'] = 0
            result['message'] = '; '.join(result['errors'])
            return result

        parts = ['DNS recreated for: %s' % ', '.join(result['applied'])]
        cf = result['cloudflare'] or {}
        if cf.get('enabled'):
            if cf.get('synced'):
                parts.append('Cloudflare records synced.')
            if cf.get('zone_status') and cf.get('zone_status') != 'active':
                parts.append(cf.get('message') or 'Cloudflare zone is not active yet.')
            elif cf.get('message') and not cf.get('synced'):
                parts.append(cf.get('message'))
        else:
            if cf.get('message'):
                parts.append(cf.get('message'))
        if result['errors']:
            parts.append('Issues: %s' % '; '.join(result['errors']))

        result['status'] = 1
        result['message'] = ' '.join(parts)
        return result
    except BaseException as msg:
        logging.writeToFile(str(msg) + ' [recreate_dns_for_domain]')
        result['status'] = 0
        result['message'] = str(msg)
        return result
