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

    @staticmethod
    def incrementSOASerial(zone):
        """Increment the serial on every SOA record for a primary zone."""
        if not zone or zone.type != 'MASTER':
            return False

        updated = False
        for soa_record in Records.objects.filter(domainOwner=zone, type='SOA'):
            try:
                soa_content = soa_record.content.split()
                soa_content[2] = str(int(soa_content[2]) + 1)
                soa_record.content = ' '.join(soa_content)
                soa_record.save(update_fields=['content'])
                updated = True
            except (AttributeError, IndexError, TypeError, ValueError) as error:
                logging.CyberCPLogFileWriter.writeToFile(
                    'Unable to increment SOA serial for zone %s: %s' % (zone.name, str(error))
                )
        return updated

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
    def _powerdns_models():
        """
        Return (Domains, Records) from CyberPanel's dns app.
        dnspython also ships a top-level `dns` package; ensure /usr/local/CyberCP
        is preferred so CLI RepairSpfRecords works when run as a script.
        """
        import importlib
        import sys

        root = '/usr/local/CyberCP'
        if root in sys.path:
            try:
                sys.path.remove(root)
            except ValueError:
                pass
        sys.path.insert(0, root)

        dns_mod = sys.modules.get('dns')
        dns_file = getattr(dns_mod, '__file__', '') or ''
        if dns_mod is not None and 'site-packages' in dns_file.replace('\\', '/'):
            for key in list(sys.modules):
                if key == 'dns' or key.startswith('dns.'):
                    del sys.modules[key]

        existing = globals().get('Domains')
        existing_rec = globals().get('Records')
        if existing is not None and existing_rec is not None:
            mod_name = getattr(existing, '__module__', '') or ''
            if mod_name == 'dns.models':
                return existing, existing_rec

        models = importlib.import_module('dns.models')
        return models.Domains, models.Records

    @staticmethod
    def RepairSpfRecords(domainName=None):
        """
        Replace apex TXT SPF that does not match the current deployment type.
        domainName: optional single zone; otherwise all Websites apex zones.
        Returns (ok_count, error_message_or_None).
        """
        try:
            from websiteFunctions.models import Websites
            Domains, Records = DNS._powerdns_models()

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

    @staticmethod
    def UpsertSpfForName(hostName):
        """
        Ensure a single SPF TXT for hostName matches buildSpfRecord().
        Creates missing SPF, updates wrong SPF, removes duplicate SPF TXT rows.
        Returns (changed_count, error_or_None).
        """
        try:
            Domains, Records = DNS._powerdns_models()
            import tldextract

            host = (hostName or '').strip().lower().rstrip('.')
            if not host:
                return 0, 'Empty hostname'

            extract = tldextract.TLDExtract(cache_dir=None)
            ex = extract(host)
            if not ex.domain or not ex.suffix:
                return 0, 'Invalid hostname'
            apex = (ex.domain + '.' + ex.suffix).lower()
            zone = Domains.objects.filter(name=apex).first()
            if not zone:
                return 0, 'No DNS zone for %s' % apex

            target = DNS.buildSpfRecord()
            txts = list(Records.objects.filter(domainOwner=zone, type='TXT', name=host))
            spf_recs = []
            for rec in txts:
                content = (rec.content or '').strip().strip('"')
                if content.lower().startswith('v=spf1'):
                    spf_recs.append(rec)

            changed = 0
            if not spf_recs:
                DNS.createDNSRecord(zone, host, 'TXT', target, 0, 3600)
                changed = 1
            else:
                first = spf_recs[0]
                content = (first.content or '').strip().strip('"')
                if content != target:
                    first.content = target
                    first.save()
                    changed = 1
                    try:
                        DNS.bumpSOASerial(zone)
                    except Exception:
                        pass
                for extra in spf_recs[1:]:
                    try:
                        extra.delete()
                        changed += 1
                    except Exception:
                        pass
            return changed, None
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [UpsertSpfForName]')
            return 0, str(msg)

    @staticmethod
    def RecreateDNSForDomain(domainName, admin, includeChildren=True):
        """
        Full recreate for existing sites: repair PowerDNS template records (including
        wrong A -> machine IP), upsert SPF, force Cloudflare sync, and report CF
        zone status / required nameservers when the zone is not active yet.

        Returns (status_1_or_0, message). For structured Cloudflare details use
        plogical.dns_recreate.recreate_dns_for_domain().
        """
        try:
            from plogical.dns_recreate import recreate_dns_for_domain
            result = recreate_dns_for_domain(
                domainName, admin, includeChildren=includeChildren)
            return int(result.get('status') or 0), result.get('message') or ''
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [RecreateDNSForDomain]')
            return 0, str(msg)

    def loadCFKeys(self):
        cfFile = '%s%s' % (DNS.CFPath, self.admin.userName)

        if os.path.exists(cfFile):
            data = open(cfFile, 'r').readlines()
            self.email = data[0].rstrip('\n')
            self.key = data[1].rstrip('\n')
            self.status = data[2].rstrip('\n')
            return 1
        else:
            #logging.CyberCPLogFileWriter.writeToFile('User %s does not have CloudFlare configured.' % (self.admin.userName))
            return 0

    def cfTemplate(self, zoneDomain, admin, enableCheck=None):
        try:
            self.admin = admin
            ## Get zone

            if self.loadCFKeys():

                if enableCheck == None:
                    pass
                else:
                    if self.status == 'Enable':
                        pass
                    else:
                        return 0, 'Sync not enabled.'

                cf = get_cloudflare_client(self.email, self.key)

                try:
                    params = {'name': zoneDomain, 'per_page': 50}
                    zones = cf.zones.get(params=params)

                    for zone in sorted(zones, key=lambda v: v['name']):
                        zone = zone['id']

                        domain = Domains.objects.get(name=zoneDomain)
                        records = Records.objects.filter(domain_id=domain.id)

                        for record in records:
                            DNS.createDNSRecordCloudFlare(cf, zone, record.name, record.type, record.content, record.prio,
                                                          record.ttl)

                        return 1, None


                except CloudFlare.exceptions.CloudFlareAPIError as e:
                    logging.CyberCPLogFileWriter.writeToFile(str(e))
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(str(e))

                try:
                    zone_info = cf.zones.post(data={'jump_start': False, 'name': zoneDomain})

                    zone = zone_info['id']

                    domain = Domains.objects.get(name=zoneDomain)
                    records = Records.objects.filter(domain_id=domain.id)

                    for record in records:
                        DNS.createDNSRecordCloudFlare(cf, zone, record.name, record.type, record.content, record.prio,
                                                      record.ttl)

                    return 1, None

                except CloudFlare.exceptions.CloudFlareAPIError as e:
                    return 0, str(e)
                except Exception as e:
                    return 0, str(e)

        except BaseException as msg:
            return 0, str(e)

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

                    DNS.createDNSRecord(zone, topLevelDomain, "TXT", "v=spf1 a mx ip4:" + ipAddress + " ~all", 0, 3600)

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

                    DNS.createDNSRecord(zone, "_dmarc." + topLevelDomain, "TXT", "v=DMARC1; p=none;", 0, 3600)

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

                    DNS.createDNSRecord(zone, topLevelDomain, "TXT", "v=spf1 a mx ip4:" + ipAddress + " ~all", 0, 3600)

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

                    DNS.createDNSRecord(zone, "_dmarc." + topLevelDomain, "TXT", "v=DMARC1; p=none;", 0, 3600)

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

                ## Mail Record

                if ('mail.%s' % (actualSubDomain)).find('mail.mail') == -1:
                    DNS.createDNSRecord(zone, 'mail.' + actualSubDomain, "A", ipAddress, 0, 3600)

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

                DNS.createDNSRecord(zone, actualSubDomain, "TXT", "v=spf1 a mx ip4:" + ipAddress + " ~all", 0, 3600)

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

                DNS.createDNSRecord(zone, "_dmarc." + actualSubDomain, "TXT", "v=DMARC1; p=none;", 0, 3600)

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
            logging.CyberCPLogFileWriter.writeToFile(
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
                        params = {'name': domain, 'per_page': 50}
                        zones = cf.zones.get(params=params)

                        for zone in sorted(zones, key=lambda v: v['name']):
                            zone = zone['id']

                            DNS.createDNSRecordCloudFlare(cf, zone, "default._domainkey." + topLevelDomain, 'TXT',
                                                          output[leftIndex:rightIndex], 0,
                                                          3600)


                    except CloudFlare.exceptions.CloudFlareAPIError as e:
                        logging.CyberCPLogFileWriter.writeToFile(str(e))
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(str(e))

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                "We had errors while creating DKIM record for: " + domain + ". Error message: " + str(msg))

    @staticmethod
    def getZoneObject(virtualHostName):
        try:
            return Domains.objects.get(name=virtualHostName)
        except:
            return 0

    @staticmethod
    def createDNSRecordCloudFlare(cf, zone, name, type, value, priority, ttl):
        try:

            if value.find('DKIM') > -1:
                value = value.replace('\n\t', '')
                value = value.replace('"', '')

            if ttl > 0:
                dns_record = {'name': name, 'type': type, 'content': value, 'ttl': ttl, 'priority': priority}
            else:
                dns_record = {'name': name, 'type': type, 'content': value, 'priority': priority}

            cf.zones.dns_records.post(zone, data=dns_record)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + '. [createDNSRecordCloudFlare]')

    @staticmethod
    def createDNSRecord(zone, name, type, value, priority, ttl):
        try:

            if Records.objects.filter(name=name, type=type, content=value).count() > 0:
                return

            DNS.incrementSOASerial(zone)


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
                        params = {'name': zone.name, 'per_page': 50}
                        zones = cf.zones.get(params=params)

                        for zone in sorted(zones, key=lambda v: v['name']):
                            zone = zone['id']

                            DNS.createDNSRecordCloudFlare(cf, zone, name, type, value, ttl, priority)

                    except CloudFlare.exceptions.CloudFlareAPIError as e:
                        logging.CyberCPLogFileWriter.writeToFile(str(e))
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(str(e))
            except:
                pass

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDNSRecord]")

    @staticmethod
    def deleteDNSZone(virtualHostName):
        try:
            delZone = Domains.objects.get(name=virtualHostName)
            delZone.delete()
        except:
            ## There does not exist a zone for this domain.
            pass

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
            zone = delRecord.domainOwner
            recordType = delRecord.type
            delRecord.delete()
            if recordType != 'SOA':
                DNS.incrementSOASerial(zone)
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
            logging.CyberCPLogFileWriter.writeToFile(f'ConfigurePowerDNSInAcme, Error: {str(msg)}')
            return 0, str(msg)

    @staticmethod
    def ConfigureCloudflareInAcme(SAVED_CF_Key, SAVED_CF_Email):
        try:

            ## remove existing keys first

            path = '/root/.acme.sh/account.conf'

            command = f"sed -i '/SAVED_CF_Key/d;/SAVED_CF_Email/d' {path}"
            ProcessUtilities.executioner(command)


            CFContent = f"""
SAVED_CF_Key='{SAVED_CF_Key}'
SAVED_CF_Email='{SAVED_CF_Email}'
"""

            command = f'echo {shlex.quote(CFContent)} >> {path}'
            ProcessUtilities.executioner(command, None, True)

            return 1, None

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(f'ConfigureCloudflareInAcme, Error: {str(msg)}')
            return 0, str(msg)
