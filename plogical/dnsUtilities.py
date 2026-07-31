#!/usr/local/CyberCP/bin/python
import os, sys

sys.path.append('/usr/local/CyberCP')
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
from plogical import CyberCPLogFileWriter as logging
import subprocess
import shlex

try:
    from dns.models import Domains, Records
    from manageServices.models import PDNSStatus, SlaveServers
except:
    pass

import CloudFlare
from plogical.cloudflareClient import get_cloudflare_client
from plogical.processUtilities import ProcessUtilities


class DNS:
    nsd_base = "/etc/nsd/nsd.conf"
    zones_base_dir = "/usr/local/lsws/conf/zones/"
    create_zone_dir = "/usr/local/lsws/conf/zones"
    defaultNameServersPath = '/home/cyberpanel/defaultNameservers'
    CFPath = '/home/cyberpanel/CloudFlare'
    DEPLOYMENT_TYPE_FILE = '/etc/cyberpanel/deployment_type'
    SPF_CYBERPERSONS = 'v=spf1 include:spf.cyberpersons.com ~all'

    ## DNS Functions

    @staticmethod
    def getDeploymentType():
        """
        Resolve mail SPF mode: cyberpersons (platform rental) or selfhosted (own VPS).
        Order: /etc/cyberpanel/deployment_type, admin config deploymentType, default selfhosted.
        """
        try:
            if os.path.exists(DNS.DEPLOYMENT_TYPE_FILE):
                with open(DNS.DEPLOYMENT_TYPE_FILE, 'r') as _df:
                    raw = _df.read().strip().lower()
                if raw in ('cyberpersons', 'selfhosted'):
                    return raw
        except Exception:
            pass
        try:
            from loginSystem.models import Administrator
            import json as _json
            admin = Administrator.objects.get(pk=1)
            config = _json.loads(admin.config) if admin.config else {}
            val = str(config.get('deploymentType', '') or '').strip().lower()
            if val in ('cyberpersons', 'selfhosted'):
                return val
        except Exception:
            pass
        return 'selfhosted'

    @staticmethod
    def buildSpfRecord(ipAddress=None):
        """
        SPF TXT content for new zones.
        CyberPersons rental: include:spf.cyberpersons.com
        Self-hosted (default): a mx ip4:<machineIP>
        """
        if DNS.getDeploymentType() == 'cyberpersons':
            return DNS.SPF_CYBERPERSONS
        if not ipAddress:
            try:
                with open('/etc/cyberpanel/machineIP', 'r') as _ipf:
                    ipAddress = _ipf.read().split('\n', 1)[0].strip()
            except Exception:
                ipAddress = ''
        if ipAddress:
            return 'v=spf1 a mx ip4:%s ~all' % ipAddress
        return 'v=spf1 a mx ~all'

    @staticmethod
    def RepairSpfRecords(domainName=None):
        """
        Replace apex TXT SPF that does not match the current deployment type.
        domainName: optional single zone; otherwise all Websites apex zones.
        Returns (ok_count, error_message_or_None).
        """
        try:
            from websiteFunctions.models import Websites
            from django.apps import apps as django_apps
            Domains = django_apps.get_model('dns', 'Domains')
            Records = django_apps.get_model('dns', 'Records')

            target = DNS.buildSpfRecord()
            wrong_cp = 'include:spf.cyberpersons.com'
            wrong_self_prefix = 'v=spf1 a mx ip4:'

            names = []
            if domainName:
                names = [domainName.strip().lower().rstrip('.')]
            else:
                for site in Websites.objects.all():
                    names.append(site.domain.lower().rstrip('.'))

            ok = 0
            for name in names:
                try:
                    import tldextract
                    extract = tldextract.TLDExtract(cache_dir=None)
                    ex = extract(name)
                    apex = (ex.domain + '.' + ex.suffix).lower()
                    if not ex.domain or not ex.suffix:
                        continue
                    zone = Domains.objects.filter(name=apex).first()
                    if not zone:
                        continue
                    txts = Records.objects.filter(domainOwner=zone, type='TXT', name=apex)
                    for rec in txts:
                        content = (rec.content or '').strip().strip('"')
                        if not content.lower().startswith('v=spf1'):
                            continue
                        dtype = DNS.getDeploymentType()
                        needs = False
                        if dtype == 'selfhosted' and wrong_cp in content and 'ip4:' not in content:
                            needs = True
                        elif dtype == 'cyberpersons' and content.startswith(wrong_self_prefix):
                            needs = True
                        elif content != target and (
                            (dtype == 'selfhosted' and wrong_cp in content)
                            or (dtype == 'cyberpersons' and 'ip4:' in content)
                        ):
                            needs = True
                        if needs and content != target:
                            rec.content = target
                            rec.save()
                            ok += 1
                            try:
                                DNS.bumpSOASerial(zone)
                            except Exception:
                                pass
                except Exception as e:
                    logging.writeToFile('RepairSpfRecords %s: %s' % (name, str(e)))
            return ok, None
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [RepairSpfRecords]')
            return 0, str(msg)

    def loadCFKeys(self):
        cfFile = '%s%s' % (DNS.CFPath, self.admin.userName)

        if os.path.exists(cfFile):
            data = open(cfFile, 'r').readlines()
            self.email = data[0].strip() if len(data) > 0 else ''
            self.key = data[1].strip() if len(data) > 1 else ''
            self.status = data[2].strip() if len(data) > 2 else ''
            return 1
        else:
            #logging.writeToFile('User %s does not have CloudFlare configured.' % (self.admin.userName))
            return 0

    def cfTemplate(self, zoneDomain, admin, enableCheck=True):
        """
        Sync local PowerDNS zone records to Cloudflare.

        enableCheck defaults to True so cfSync=Disable is honored (same as delete path).
        Resolves the Cloudflare zone by walking parents (blog.example.com -> example.com).
        PowerDNS records are always loaded from the apex Domains row.
        """
        try:
            import tldextract
            from plogical.cloudflare_dns_sync import CloudflareDnsSync
            self.admin = admin

            if not self.loadCFKeys():
                return 0, 'Cloudflare keys not configured.'

            if enableCheck and self.status != 'Enable':
                return 0, 'Sync not enabled.'

            no_cache_extract = tldextract.TLDExtract(cache_dir=None)
            extracted = no_cache_extract(zoneDomain)
            apex = extracted.domain + '.' + extracted.suffix
            if not extracted.domain or not extracted.suffix:
                return 0, 'Could not resolve apex for %s' % zoneDomain

            try:
                domain = Domains.objects.get(name=apex)
            except Domains.DoesNotExist:
                return 0, 'No local PowerDNS zone for %s' % apex

            cf = get_cloudflare_client(self.email, self.key)
            zone_id, zone_name = CloudflareDnsSync.resolve_zone(cf, zoneDomain)

            # Only create a Cloudflare zone for a true apex hostname. Never create
            # zones named like blog.example.com when the parent zone is missing.
            if not zone_id:
                if zoneDomain.rstrip('.').lower() != apex.lower():
                    return 0, 'Cloudflare zone not found for apex %s' % apex
                try:
                    zone_info = cf.zones.post(data={'jump_start': False, 'name': apex})
                    zone_id = zone_info['id']
                    zone_name = zone_info['name']
                except CloudFlare.exceptions.CloudFlareAPIError as e:
                    return 0, str(e)
                except Exception as e:
                    return 0, str(e)

            records = Records.objects.filter(domain_id=domain.id)
            existing_cf = CloudflareDnsSync.list_zone_records(cf, zone_id)

            for record in records:
                # Skip SOA/NS for Cloudflare (managed at registrar / CF defaults)
                if (record.type or '').upper() in ('SOA', 'NS'):
                    continue
                DNS.createDNSRecordCloudFlare(
                    cf, zone_id, zone_name, record.name, record.type, record.content,
                    record.prio, record.ttl, existing_records=existing_cf)

            return 1, None

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [cfTemplate]')
            return 0, str(msg)
    @staticmethod
    def dnsTemplate(domain, admin):
        try:

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]


            import tldextract

            no_cache_extract = tldextract.TLDExtract(cache_dir=None)

            extractDomain = no_cache_extract(domain)
            topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix
            subDomain = extractDomain.subdomain

            if len(subDomain) == 0:
                if Domains.objects.filter(name=topLevelDomain).count() == 0:
                    try:
                        pdns = PDNSStatus.objects.get(pk=1)
                        if pdns.type == 'MASTER':
                            zone = Domains(admin=admin, name=topLevelDomain, type="MASTER")
                            zone.save()

                            for items in SlaveServers.objects.all():
                                record = Records(domainOwner=zone,
                                                 domain_id=zone.id,
                                                 name=topLevelDomain,
                                                 type="NS",
                                                 content=items.slaveServer,
                                                 ttl=3600,
                                                 prio=0,
                                                 disabled=0,
                                                 auth=1)
                                record.save()
                        else:
                            zone = Domains(admin=admin, name=topLevelDomain, type="NATIVE")
                    except:
                        zone = Domains(admin=admin, name=topLevelDomain, type="NATIVE")

                    zone.save()

                    if zone.type == 'NATIVE':

                        if os.path.exists(DNS.defaultNameServersPath):
                            defaultNS = open(DNS.defaultNameServersPath, 'r').readlines()

                            for items in defaultNS:
                                if len(items) > 5:
                                    record = Records(domainOwner=zone,
                                                     domain_id=zone.id,
                                                     name=topLevelDomain,
                                                     type="NS",
                                                     content=items.rstrip('\n'),
                                                     ttl=3600,
                                                     prio=0,
                                                     disabled=0,
                                                     auth=1)
                                    record.save()
                        else:
                            record = Records(domainOwner=zone,
                                             domain_id=zone.id,
                                             name=topLevelDomain,
                                             type="NS",
                                             content='ns1.%s' % (topLevelDomain),
                                             ttl=3600,
                                             prio=0,
                                             disabled=0,
                                             auth=1)
                            record.save()

                            record = Records(domainOwner=zone,
                                             domain_id=zone.id,
                                             name=topLevelDomain,
                                             type="NS",
                                             content='ns2.%s' % (topLevelDomain),
                                             ttl=3600,
                                             prio=0,
                                             disabled=0,
                                             auth=1)
                            record.save()

                    content = "ns1." + topLevelDomain + " hostmaster." + topLevelDomain + " 1 10800 3600 1209600 3600"

                    # soaRecord = Records(domainOwner=zone,
                    #                     domain_id=zone.id,
                    #                     name=topLevelDomain,
                    #                     type="SOA",
                    #                     content=content,
                    #                     ttl=3600,
                    #                     prio=0,
                    #                     disabled=0,
                    #                     auth=1)
                    # soaRecord.save()

                    DNS.createDNSRecord(zone, topLevelDomain, "SOA", content, 0, 3600)

                    ## Main A record.

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=topLevelDomain,
                    #                  type="A",
                    #                  content=ipAddress,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, topLevelDomain, "A", ipAddress, 0, 3600)

                    # AAAA Record (IPv6) - Required for mail delivery to Google, Outlook, etc.
                    try:
                        from plogical.acl import ACLManager
                        ipv6Address = ACLManager.GetServerIPv6()
                        if ipv6Address:
                            DNS.createDNSRecord(zone, topLevelDomain, "AAAA", ipv6Address, 0, 3600)
                    except Exception as e:
                        logging.writeToFile(f'Error creating AAAA record for {topLevelDomain}: {str(e)}')

                    # CNAME Records.

                    cNameValue = "www." + topLevelDomain

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=cNameValue,
                    #                  type="CNAME",
                    #                  content=topLevelDomain,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, cNameValue, "CNAME", topLevelDomain, 0, 3600)

                    cNameValue = "ftp." + topLevelDomain

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=cNameValue,
                    #                  type="CNAME",
                    #                  content=topLevelDomain,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, cNameValue, "CNAME", topLevelDomain, 0, 3600)

                    ## MX Record.

                    mxValue = topLevelDomain

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=topLevelDomain,
                    #                  type="MX",
                    #                  content=mxValue,
                    #                  ttl=3600,
                    #                  prio="10",
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, topLevelDomain, "MX", mxValue, 10, 3600)

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=mxValue,
                    #                  type="A",
                    #                  content=ipAddress,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, mxValue, "A", ipAddress, 0, 3600)

                    # AAAA Record for mail (IPv6) - Required for mail delivery
                    try:
                        from plogical.acl import ACLManager
                        ipv6Address = ACLManager.GetServerIPv6()
                        if ipv6Address:
                            DNS.createDNSRecord(zone, mxValue, "AAAA", ipv6Address, 0, 3600)
                    except Exception as e:
                        logging.writeToFile(f'Error creating AAAA record for mail {mxValue}: {str(e)}')

                    ## TXT Records for mail

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=topLevelDomain,
                    #                  type="TXT",
                    #                  content="v=spf1 a mx ip4:" + ipAddress + " ~all",
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, topLevelDomain, "TXT", DNS.buildSpfRecord(ipAddress), 0, 3600)

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name="_dmarc." + topLevelDomain,
                    #                  type="TXT",
                    #                  content="v=DMARC1; p=none",
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    # Apex DMARC: do not auto-add p=none here — use one TXT at _dmarc.<apex> in Cloudflare/DNS
                    # to avoid conflicting duplicate DMARC records (invalid per RFC 7489).
                    # DNS.createDNSRecord(zone, "_dmarc." + topLevelDomain, "TXT", "v=DMARC1; p=none;", 0, 3600)

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name="_domainkey." + topLevelDomain,
                    #                  type="TXT",
                    #                  content="t=y; o=~;",
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, "_domainkey." + topLevelDomain, "TXT", "t=y; o=~;", 0, 3600)
            else:
                if Domains.objects.filter(name=topLevelDomain).count() == 0:
                    try:
                        pdns = PDNSStatus.objects.get(pk=1)
                        if pdns.type == 'MASTER':
                            zone = Domains(admin=admin, name=topLevelDomain, type="MASTER")
                        else:
                            zone = Domains(admin=admin, name=topLevelDomain, type="NATIVE")
                    except:
                        zone = Domains(admin=admin, name=topLevelDomain, type="NATIVE")

                    zone.save()

                    content = "ns1." + topLevelDomain + " hostmaster." + topLevelDomain + " 1 10800 3600 1209600 3600"

                    # soaRecord = Records(domainOwner=zone,
                    #                     domain_id=zone.id,
                    #                     name=topLevelDomain,
                    #                     type="SOA",
                    #                     content=content,
                    #                     ttl=3600,
                    #                     prio=0,
                    #                     disabled=0,
                    #                     auth=1)
                    # soaRecord.save()

                    DNS.createDNSRecord(zone, topLevelDomain, "SOA", content, 0, 3600)

                    ## Main A record.

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=topLevelDomain,
                    #                  type="A",
                    #                  content=ipAddress,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, topLevelDomain, "A", ipAddress, 0, 3600)

                    # AAAA Record (IPv6) - Required for mail delivery to Google, Outlook, etc.
                    try:
                        from plogical.acl import ACLManager
                        ipv6Address = ACLManager.GetServerIPv6()
                        if ipv6Address:
                            DNS.createDNSRecord(zone, topLevelDomain, "AAAA", ipv6Address, 0, 3600)
                    except Exception as e:
                        logging.writeToFile(f'Error creating AAAA record for {topLevelDomain}: {str(e)}')

                    # CNAME Records.

                    cNameValue = "www." + topLevelDomain

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=cNameValue,
                    #                  type="CNAME",
                    #                  content=topLevelDomain,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, cNameValue, "CNAME", topLevelDomain, 0, 3600)

                    cNameValue = "ftp." + topLevelDomain

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=cNameValue,
                    #                  type="CNAME",
                    #                  content=topLevelDomain,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, cNameValue, "CNAME", topLevelDomain, 0, 3600)

                    ## MX Record.

                    mxValue = topLevelDomain

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=topLevelDomain,
                    #                  type="MX",
                    #                  content=mxValue,
                    #                  ttl=3600,
                    #                  prio="10",
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, mxValue, "MX", mxValue, 10, 3600)

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=mxValue,
                    #                  type="A",
                    #                  content=ipAddress,
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, mxValue, "A", ipAddress, 0, 3600)

                    # AAAA Record for mail (IPv6) - Required for mail delivery
                    try:
                        from plogical.acl import ACLManager
                        ipv6Address = ACLManager.GetServerIPv6()
                        if ipv6Address:
                            DNS.createDNSRecord(zone, mxValue, "AAAA", ipv6Address, 0, 3600)
                    except Exception as e:
                        logging.writeToFile(f'Error creating AAAA record for mail {mxValue}: {str(e)}')

                    ## TXT Records for mail

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name=topLevelDomain,
                    #                  type="TXT",
                    #                  content="v=spf1 a mx ip4:" + ipAddress + " ~all",
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, topLevelDomain, "TXT", DNS.buildSpfRecord(ipAddress), 0, 3600)

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name="_dmarc." + topLevelDomain,
                    #                  type="TXT",
                    #                  content="v=DMARC1; p=none",
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    # Apex DMARC: do not auto-add p=none here — use one TXT at _dmarc.<apex> in Cloudflare/DNS
                    # to avoid conflicting duplicate DMARC records (invalid per RFC 7489).
                    # DNS.createDNSRecord(zone, "_dmarc." + topLevelDomain, "TXT", "v=DMARC1; p=none;", 0, 3600)

                    # record = Records(domainOwner=zone,
                    #                  domain_id=zone.id,
                    #                  name="_domainkey." + topLevelDomain,
                    #                  type="TXT",
                    #                  content="t=y; o=~;",
                    #                  ttl=3600,
                    #                  prio=0,
                    #                  disabled=0,
                    #                  auth=1)
                    # record.save()

                    DNS.createDNSRecord(zone, "_domainkey." + topLevelDomain, "TXT", "t=y; o=~;", 0, 3600)

                ## Creating sub-domain level record.

                zone = Domains.objects.get(name=topLevelDomain)

                actualSubDomain = subDomain + "." + topLevelDomain

                ## Main A record.

                DNS.createDNSRecord(zone, actualSubDomain, "A", ipAddress, 0, 3600)

                # AAAA Record for subdomain (IPv6)
                try:
                    from plogical.acl import ACLManager
                    ipv6Address = ACLManager.GetServerIPv6()
                    if ipv6Address:
                        DNS.createDNSRecord(zone, actualSubDomain, "AAAA", ipv6Address, 0, 3600)
                except Exception as e:
                    logging.writeToFile(
                        'Error creating AAAA record for subdomain %s: %s' % (actualSubDomain, str(e)))

                ## Mail Record

                if ('mail.%s' % (actualSubDomain)).find('mail.mail') == -1:
                    DNS.createDNSRecord(zone, 'mail.' + actualSubDomain, "A", ipAddress, 0, 3600)
                    # AAAA Record for mail subdomain (IPv6) - Required for mail delivery
                    try:
                        from plogical.acl import ACLManager
                        ipv6Address = ACLManager.GetServerIPv6()
                        if ipv6Address:
                            DNS.createDNSRecord(zone, 'mail.' + actualSubDomain, "AAAA", ipv6Address, 0, 3600)
                    except Exception as e:
                        logging.writeToFile(f'Error creating AAAA record for mail subdomain {actualSubDomain}: {str(e)}')

                # CNAME Records.

                cNameValue = "www." + actualSubDomain

                DNS.createDNSRecord(zone, cNameValue, "CNAME", actualSubDomain, 0, 3600)

                ## MX Records

                mxValue = actualSubDomain

                # record = Records(domainOwner=zone,
                #                  domain_id=zone.id,
                #                  name=actualSubDomain,
                #                  type="MX",
                #                  content=mxValue,
                #                  ttl=3600,
                #                  prio="10",
                #                  disabled=0,
                #                  auth=1)
                # record.save()

                DNS.createDNSRecord(zone, actualSubDomain, "MX", mxValue, 10, 3600)

                ## TXT Records

                # record = Records(domainOwner=zone,
                #                  domain_id=zone.id,
                #                  name=actualSubDomain,
                #                  type="TXT",
                #                  content="v=spf1 a mx ip4:" + ipAddress + " ~all",
                #                  ttl=3600,
                #                  prio=0,
                #                  disabled=0,
                #                  auth=1)
                # record.save()

                DNS.createDNSRecord(zone, actualSubDomain, "TXT", DNS.buildSpfRecord(ipAddress), 0, 3600)

                # record = Records(domainOwner=zone,
                #                  domain_id=zone.id,
                #                  name="_dmarc." + actualSubDomain,
                #                  type="TXT",
                #                  content="v=DMARC1; p=none",
                #                  ttl=3600,
                #                  prio=0,
                #                  disabled=0,
                #                  auth=1)
                # record.save()

                # Do not auto-create subdomain _dmarc: one organizational policy at _dmarc.<apex> is enough for
                # typical setups; avoids dozens of p=none records and Cloudflare clutter.
                # DNS.createDNSRecord(zone, "_dmarc." + actualSubDomain, "TXT", "v=DMARC1; p=none;", 0, 3600)

                # record = Records(domainOwner=zone,
                #                  domain_id=zone.id,
                #                  name="_domainkey." + actualSubDomain,
                #                  type="TXT",
                #                  content="t=y; o=~;",
                #                  ttl=3600,
                #                  prio=0,
                #                  disabled=0,
                #                  auth=1)
                # record.save()

                DNS.createDNSRecord(zone, "_domainkey." + actualSubDomain, "TXT", "t=y; o=~;", 0, 3600)

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                command = 'sudo systemctl restart pdns'
                ProcessUtilities.executioner(command)

            dns = DNS()
            dns.cfTemplate(domain, admin)

        except BaseException as msg:
            logging.writeToFile(
                "We had errors while creating DNS records for: " + domain + ". Error message: " + str(msg))

    @staticmethod
    def createDKIMRecords(domain):
        try:

            import tldextract

            no_cache_extract = tldextract.TLDExtract(cache_dir=None)

            extractDomain = no_cache_extract(domain)
            topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix
            subDomain = extractDomain.subdomain

            zone = Domains.objects.get(name=topLevelDomain)

            path = "/etc/opendkim/keys/" + topLevelDomain + "/default.txt"
            command = "cat " + path
            output = subprocess.check_output(shlex.split(command)).decode("utf-8")
            leftIndex = output.index('(') + 2
            rightIndex = output.rindex(')') - 1

            if Records.objects.filter(domainOwner=zone, name="default._domainkey." + topLevelDomain).count() == 0:

                record = Records(domainOwner=zone,
                                 domain_id=zone.id,
                                 name="default._domainkey." + topLevelDomain,
                                 type="TXT",
                                 content=output[leftIndex:rightIndex],
                                 ttl=3600,
                                 prio=0,
                                 disabled=0,
                                 auth=1)
                record.save()
            #### in else we need to update record if new key found
            else:
                rcrd = Records.objects.get(domainOwner=zone, name="default._domainkey." + topLevelDomain)
                rcrd.content =  output[leftIndex:rightIndex]
                rcrd.save()


            if len(subDomain) > 0:
                if Records.objects.filter(domainOwner=zone, name="default._domainkey." + domain).count() == 0:
                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name="default._domainkey." + domain,
                                     type="TXT",
                                     content=output[leftIndex:rightIndex],
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()
                #### in else we need to update record of new key found
                else:
                    rcrd = Records.objects.get(domainOwner=zone, name="default._domainkey." + domain)
                    rcrd.content = output[leftIndex:rightIndex]
                    rcrd.save()

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                command = ' systemctl restart pdns'
                ProcessUtilities.executioner(command)

            ## Add record to CF If sync enabled

            dns = DNS()
            dns.admin = zone.admin
            if dns.loadCFKeys():
                cf = get_cloudflare_client(dns.email, dns.key)

                if dns.status == 'Enable':
                    try:
                        from plogical.cloudflare_dns_sync import CloudflareDnsSync
                        zone_id, zone_name = CloudflareDnsSync.resolve_zone(cf, domain)
                        if not zone_id:
                            logging.writeToFile(
                                'Cloudflare zone not found for DKIM on %s (apex %s)' % (domain, topLevelDomain))
                        else:
                            DNS.createDNSRecordCloudFlare(
                                cf, zone_id, zone_name, "default._domainkey." + topLevelDomain, 'TXT',
                                output[leftIndex:rightIndex], 0, 3600)
                            if len(subDomain) > 0:
                                DNS.createDNSRecordCloudFlare(
                                    cf, zone_id, zone_name, "default._domainkey." + domain, 'TXT',
                                    output[leftIndex:rightIndex], 0, 3600)

                    except CloudFlare.exceptions.CloudFlareAPIError as e:
                        logging.writeToFile(str(e))
                    except Exception as e:
                        logging.writeToFile(str(e))

        except BaseException as msg:
            logging.writeToFile(
                "We had errors while creating DKIM record for: " + domain + ". Error message: " + str(msg))

    @staticmethod
    def getZoneObject(virtualHostName):
        try:
            return Domains.objects.get(name=virtualHostName)
        except:
            return 0

    @staticmethod
    def createDNSRecordCloudFlare(cf, zone, zone_name, name, type, value, priority, ttl, proxied=None,
                                  existing_records=None):
        try:
            import tldextract
            from plogical.cloudflare_dns_sync import CloudflareDnsSync
            if not zone_name:
                parsed = tldextract.TLDExtract(cache_dir=None)(name)
                zone_name = parsed.domain + '.' + parsed.suffix
            CloudflareDnsSync.upsert_dns_record(
                cf, zone, zone_name, name, type, value, priority, ttl, proxied, existing_records)
        except BaseException as msg:
            logging.writeToFile(str(msg) + '. [createDNSRecordCloudFlare]')

    @staticmethod
    def bumpSOASerial(zone):
        """Increment SOA serial for MASTER and NATIVE zones (PowerDNS notify / local serial)."""
        try:
            if zone is None:
                return False
            updated = False
            for getSOA in Records.objects.filter(domainOwner=zone, type='SOA'):
                parts = (getSOA.content or '').split()
                if len(parts) < 3:
                    continue
                try:
                    parts[2] = str(int(parts[2]) + 1)
                except (TypeError, ValueError):
                    logging.writeToFile(
                        'SOA serial bump skipped: invalid serial in record id %s' % (getSOA.id,)
                    )
                    continue
                getSOA.content = ' '.join(parts)
                getSOA.save()
                updated = True
            return updated
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [bumpSOASerial]')
            return False

    @staticmethod
    def createDNSRecord(zone, name, type, value, priority, ttl):
        try:

            if Records.objects.filter(name=name, type=type, content=value).count() > 0:
                return

            DNS.bumpSOASerial(zone)


            if type == 'NS':
                if Records.objects.filter(name=name, type=type, content=value).count() == 0:
                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=name,
                                     type=type,
                                     content=value,
                                     ttl=ttl,
                                     prio=priority,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                        command = 'ls -la /etc/systemd/system/multi-user.target.wants/pdns.service'
                        result = ProcessUtilities.outputExecutioner(command)

                        if result.find('No such file') == -1:
                            command = 'sudo systemctl restart pdns'
                            ProcessUtilities.executioner(command)

                return

            if type == 'SOA':
                if Records.objects.filter(name=name, type=type, content=value).count() == 0:
                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=name,
                                     type=type,
                                     content=value,
                                     ttl=ttl,
                                     prio=priority,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                        command = 'ls -la /etc/systemd/system/multi-user.target.wants/pdns.service'
                        result = ProcessUtilities.outputExecutioner(command)

                        if result.find('No such file') == -1:
                            command = 'sudo systemctl restart pdns'
                            ProcessUtilities.executioner(command)

                return

            if type == 'TXT':
                if Records.objects.filter(name=name, type=type, content=value).count() == 0:
                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=name,
                                     type=type,
                                     content=value,
                                     ttl=ttl,
                                     prio=priority,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                        command = 'ls -la /etc/systemd/system/multi-user.target.wants/pdns.service'
                        result = ProcessUtilities.outputExecutioner(command)

                        if result.find('No such file') == -1:
                            command = 'sudo systemctl restart pdns'
                            ProcessUtilities.executioner(command)
                return

            if type == 'MX':
                record = Records(domainOwner=zone,
                                 domain_id=zone.id,
                                 name=name,
                                 type=type,
                                 content=value,
                                 ttl=ttl,
                                 prio=str(priority),
                                 disabled=0,
                                 auth=1)
                record.save()

                if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                    command = 'ls -la /etc/systemd/system/multi-user.target.wants/pdns.service'
                    result = ProcessUtilities.outputExecutioner(command)

                    if result.find('No such file') == -1:
                        command = 'sudo systemctl restart pdns'
                        ProcessUtilities.executioner(command)
                return

            if Records.objects.filter(name=name, type=type).count() == 0:
                record = Records(domainOwner=zone,
                                 domain_id=zone.id,
                                 name=name,
                                 type=type,
                                 content=value,
                                 ttl=ttl,
                                 prio=priority,
                                 disabled=0,
                                 auth=1)
                record.save()
                if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:

                    command = 'ls -la /etc/systemd/system/multi-user.target.wants/pdns.service'
                    result = ProcessUtilities.outputExecutioner(command)

                    if result.find('No such file') == -1:
                        command = 'sudo systemctl restart pdns'
                        ProcessUtilities.executioner(command)

            ## Add Record to CF if SYNC Enabled

            try:

                dns = DNS()
                dns.admin = zone.admin
                dns.loadCFKeys()

                cf = get_cloudflare_client(dns.email, dns.key)

                if dns.status == 'Enable':
                    try:
                        from plogical.cloudflare_dns_sync import CloudflareDnsSync
                        zone_id, zone_name = CloudflareDnsSync.resolve_zone(cf, name or zone.name)
                        if zone_id:
                            DNS.createDNSRecordCloudFlare(cf, zone_id, zone_name, name, type, value, priority, ttl)

                    except CloudFlare.exceptions.CloudFlareAPIError as e:
                        logging.writeToFile(str(e))
                    except Exception as e:
                        logging.writeToFile(str(e))
            except:
                pass

        except BaseException as msg:
            logging.writeToFile(str(msg) + " [createDNSRecord]")

    @staticmethod
    def deleteDNSZone(virtualHostName):
        try:
            delZone = Domains.objects.get(name=virtualHostName)
            delZone.delete()
        except:
            ## There does not exist a zone for this domain.
            pass

    @staticmethod
    def maybeDeleteOrphanDNSZone(domainName):
        """
        Delete a PowerDNS Domains row for domainName when nothing in the panel still uses it.

        Used after alias/child delete when dnsTemplate created a dedicated apex zone
        (for example an alias that is its own registrable domain).
        """
        try:
            import tldextract
            from websiteFunctions.models import Websites, ChildDomains, aliasDomains

            fqdn = (domainName or '').rstrip('.').lower()
            if not fqdn:
                return 0, 'Empty domain'

            if Domains.objects.filter(name=fqdn).count() == 0:
                return 1, 'No dedicated zone'

            if Websites.objects.filter(domain=fqdn).exists():
                return 1, 'Website still uses zone'
            if ChildDomains.objects.filter(domain=fqdn).exists():
                return 1, 'Child domain still uses zone'
            if aliasDomains.objects.filter(aliasDomain=fqdn).exists():
                return 1, 'Alias still uses zone'

            extract = tldextract.TLDExtract(cache_dir=None)
            parsed = extract(fqdn)
            apex = ('%s.%s' % (parsed.domain, parsed.suffix)).lower() if parsed.domain and parsed.suffix else fqdn

            # If this Domains row is an apex that still backs other hosts, keep it.
            if fqdn == apex:
                if Websites.objects.filter(domain__iendswith='.' + apex).exists():
                    return 1, 'Apex still used by websites'
                if ChildDomains.objects.filter(domain__iendswith='.' + apex).exists():
                    return 1, 'Apex still used by child domains'
                if aliasDomains.objects.filter(aliasDomain__iendswith='.' + apex).exists():
                    return 1, 'Apex still used by aliases'

            DNS.deleteDNSZone(fqdn)
            logging.writeToFile('Deleted orphan PowerDNS zone for %s' % fqdn, 0)
            return 1, 'Deleted orphan zone'
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [maybeDeleteOrphanDNSZone]')
            return 0, str(msg)

    @staticmethod
    def cleanupHostDNSRecords(domainName, adminUserName=None):
        """Remove local PowerDNS and Cloudflare records for one website or child domain."""
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        return CloudflareDnsSync.cleanup_host_dns_records(domainName, adminUserName)

    @staticmethod
    def pruneOrphanCloudflareHosts(apexDomain, adminUserName):
        """Remove Cloudflare host records under apex that are not managed in CyberPanel."""
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        return CloudflareDnsSync.prune_orphan_cloudflare_hosts(apexDomain, adminUserName)

    @staticmethod
    def deleteCloudFlareDNSRecords(domainName, adminUserName=None):
        """
        Delete all CloudFlare DNS records for a domain when domain is removed from CyberPanel.
        This function is called automatically when domains/sub-domains are deleted.
        """
        from plogical.cloudflare_dns_sync import CloudflareDnsSync
        return CloudflareDnsSync.delete_cloudflare_records_for_host(domainName, adminUserName)

    @staticmethod
    def createDNSZone(virtualHostName, admin):
        try:
            zone = Domains(admin=admin, name=virtualHostName, type="NATIVE")
            zone.save()
        except:
            ## There does not exist a zone for this domain.
            pass

    @staticmethod
    def getDNSRecords(virtualHostName):
        try:
            zone = Domains.objects.get(name=virtualHostName)
            zone.save()
            return zone.records_set.all()
        except:
            ## There does not exist a zone for this domain.
            pass

    @staticmethod
    def getDNSZones():
        try:
            return Domains.objects.all()
        except:
            pass

    @staticmethod
    def deleteDNSRecord(recordID):
        try:
            delRecord = Records.objects.get(id=recordID)
            delRecord.delete()
        except:
            ## There does not exist a zone for this domain.
            pass

    @staticmethod
    def ConfigurePowerDNSInAcme():
        try:
            from plogical.randomPassword import generate_pass
            path = '/root/.acme.sh/account.conf'

            APIKey = generate_pass(16)

            CurrentContent = ProcessUtilities.outputExecutioner(f'cat {path}')

            if CurrentContent.find('PDNS_Url') == -1:
                PDNSContent = f"""
PDNS_Url='http://localhost:8081'
PDNS_ServerId='localhost'
PDNS_Token='{APIKey}'
"""

                command = f'echo "{PDNSContent}" >> {path}'
                ProcessUtilities.executioner(command,None, True)

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                    PDNSPath = '/etc/pdns/pdns.conf'
                else:
                    PDNSPath = '/etc/powerdns/pdns.conf'


                PDNSConf = f"""
# Turn on the webserver API
webserver=yes
webserver-address=0.0.0.0
webserver-port=8081

# Set the API key for accessing the API
api=yes
api-key={APIKey}

webserver-allow-from=0.0.0.0/0
"""
                command = f'echo "{PDNSConf}" >> {PDNSPath}'
                ProcessUtilities.executioner(command,None, True)

                command = 'systemctl restart pdns'
                ProcessUtilities.executioner(command)


            return 1, None

        except BaseException as msg:
            logging.writeToFile(f'ConfigurePowerDNSInAcme, Error: {str(msg)}')
            return 0, str(msg)

    @staticmethod
    def ConfigureCloudflareInAcme(SAVED_CF_Key, SAVED_CF_Email):
        try:
            from plogical.cloudflareClient import _is_global_api_key

            path = '/root/.acme.sh/account.conf'
            secret = (SAVED_CF_Key or '').strip()
            email = (SAVED_CF_Email or '').strip()

            command = (
                "sed -i '/SAVED_CF_Key/d;/SAVED_CF_Email/d;"
                "/^CF_Key=/d;/^CF_Email=/d;/^CF_Token=/d' %s" % shlex.quote(path)
            )
            ProcessUtilities.executioner(command)

            lines = [
                "SAVED_CF_Key='%s'" % secret.replace("'", "'\\''"),
                "SAVED_CF_Email='%s'" % email.replace("'", "'\\''"),
            ]
            # acme.sh dns_cf: API tokens need CF_Token (Bearer). Global API keys use CF_Key + CF_Email.
            if secret and not _is_global_api_key(secret):
                lines.append("CF_Token='%s'" % secret.replace("'", "'\\''"))
            elif secret:
                lines.append("CF_Key='%s'" % secret.replace("'", "'\\''"))
                if email:
                    lines.append("CF_Email='%s'" % email.replace("'", "'\\''"))

            CFContent = '\n'.join(lines) + '\n'
            command = 'echo %s >> %s' % (shlex.quote(CFContent), shlex.quote(path))
            ProcessUtilities.executioner(command, None, True)

            return 1, None

        except BaseException as msg:
            logging.writeToFile(f'ConfigureCloudflareInAcme, Error: {str(msg)}')
            return 0, str(msg)
