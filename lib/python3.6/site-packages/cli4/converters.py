"""Cloudflare API via command line"""
from __future__ import absolute_import

import CloudFlare

class ConverterError(Exception):
    """ errors for converters"""

def convert_zones_to_identifier(cf, zone_name):
    """zone names to numbers"""
    params = {'name':zone_name, 'per_page':1}
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (zone_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (zone_name, e))

    if len(zones) == 1:
        return zones[0]['id']

    raise ConverterError('%s: not found' % (zone_name))

def convert_accounts_to_identifier(cf, account_name):
    """account names to numbers"""
    params = {'name':account_name, 'per_page':1}
    try:
        accounts = cf.accounts.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (account_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (account_name, e))

    if len(accounts) == 1:
        return accounts[0]['id']

    raise ConverterError('%s: not found' % (account_name))

def convert_dns_record_to_identifier(cf, zone_id, dns_name):
    """dns record names to numbers"""
    # this can return an array of results as there can be more than one DNS entry for a name.
    params = {'name':dns_name}
    try:
        dns_records = cf.zones.dns_records.get(zone_id, params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (dns_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (dns_name, e))

    r = []
    for dns_record in dns_records:
        if dns_name == dns_record['name']:
            r.append(dns_record['id'])
    if len(r) > 0:
        return r

    raise ConverterError('%s: not found' % (dns_name))

def convert_certificates_to_identifier(cf, certificate_name):
    """certificate names to numbers"""
    try:
        certificates = cf.certificates.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (certificate_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (certificate_name, e))

    for certificate in certificates:
        if certificate_name in certificate['hostnames']:
            return certificate['id']

    raise ConverterError('%s: not found' % (certificate_name))

def convert_organizations_to_identifier(cf, organization_name):
    """organizations names to numbers"""
    try:
        organizations = cf.user.organizations.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (organization_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (organization_name, e))

    for organization in organizations:
        if organization_name == organization['name']:
            return organization['id']

    raise ConverterError('%s not found' % (organization_name))

def convert_invites_to_identifier(cf, invite_name):
    """invite names to numbers"""
    try:
        invites = cf.user.invites.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (invite_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (invite_name, e))

    for invite in invites:
        if invite_name == invite['organization_name']:
            return invite['id']

    raise ConverterError('%s: not found' % (invite_name))

def convert_virtual_dns_to_identifier(cf, virtual_dns_name):
    """virtual dns names to numbers"""
    try:
        virtual_dnss = cf.user.virtual_dns.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (virtual_dns_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (virtual_dns_name, e))

    for virtual_dns in virtual_dnss:
        if virtual_dns_name == virtual_dns['name']:
            return virtual_dns['id']

    raise ConverterError('%s: not found' % (virtual_dns_name))

def convert_load_balancers_pool_to_identifier(cf, pool_name):
    """load balancer pool names to numbers"""
    try:
        pools = cf.user.load_balancers.pools.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (pool_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (pool_name, e))

    for p in pools:
        if pool_name == p['description']:
            return p['id']

    raise ConverterError('%s: not found' % (pool_name))

def convert_custom_hostnames_to_identifier(cf, zone_id, custom_hostname):
    """custom_hostnames to numbers"""
    # this can return an array of results
    params = {'name':custom_hostname}
    try:
        custom_hostnames_records = cf.zones.custom_hostnames.get(zone_id, params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        raise ConverterError(int(e), '%s - %d %s' % (dns_name, e, e))
    except Exception as e:
        raise ConverterError(0, '%s - %s' % (dns_name, e))

    r = []
    for custom_hostnames_record in custom_hostnames_records:
        if custom_hostname == custom_hostnames_record['hostname']:
            r.append(custom_hostnames_record['id'])
    if len(r) > 0:
        return r

    raise ConverterError('%s: not found' % (custom_hostname))
