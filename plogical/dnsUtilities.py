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

    ## DNS Functions

    def loadCFKeys(self):
        cfFile = '%s%s' % (DNS.CFPath, self.admin.userName)

        if os.path.exists(cfFile):
            data = open(cfFile, 'r').readlines()
            self.email = data[0].strip() if len(data) > 0 else ''
            self.key = data[1].strip() if len(data) > 1 else ''
            self.status = data[2].strip() if len(data) > 2 else ''
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

                    for zone_obj in sorted(zones, key=lambda v: v['name']):
                        zone_id = zone_obj['id']
                        zone_name = zone_obj['name']

                        domain = Domains.objects.get(name=zoneDomain)
                        records = Records.objects.filter(domain_id=domain.id)

                        for record in records:
                            DNS.createDNSRecordCloudFlare(
                                cf, zone_id, zone_name, record.name, record.type, record.content,
                                record.prio, record.ttl)

                        return 1, None


                except CloudFlare.exceptions.CloudFlareAPIError as e:
                    logging.CyberCPLogFileWriter.writeToFile(str(e))
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(str(e))

                try:
                    zone_info = cf.zones.post(data={'jump_start': False, 'name': zoneDomain})

                    zone_id = zone_info['id']
                    zone_name = zone_info['name']

                    domain = Domains.objects.get(name=zoneDomain)
                    records = Records.objects.filter(domain_id=domain.id)

                    for record in records:
                        DNS.createDNSRecordCloudFlare(
                            cf, zone_id, zone_name, record.name, record.type, record.content,
                            record.prio, record.ttl)

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

                    # AAAA Record (IPv6) - Required for mail delivery to Google, Outlook, etc.
                    try:
                        from plogical.acl import ACLManager
                        ipv6Address = ACLManager.GetServerIPv6()
                        if ipv6Address:
                            DNS.createDNSRecord(zone, topLevelDomain, "AAAA", ipv6Address, 0, 3600)
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f'Error creating AAAA record for {topLevelDomain}: {str(e)}')

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
                        logging.CyberCPLogFileWriter.writeToFile(f'Error creating AAAA record for mail {mxValue}: {str(e)}')

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
                        logging.CyberCPLogFileWriter.writeToFile(f'Error creating AAAA record for {topLevelDomain}: {str(e)}')

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
                        logging.CyberCPLogFileWriter.writeToFile(f'Error creating AAAA record for mail {mxValue}: {str(e)}')

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
                    logging.CyberCPLogFileWriter.writeToFile(f'Error creating AAAA record for subdomain {actualSubDomain}: {str(e)}')

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
                        logging.CyberCPLogFileWriter.writeToFile(f'Error creating AAAA record for mail subdomain {actualSubDomain}: {str(e)}')

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

                        for zone_obj in sorted(zones, key=lambda v: v['name']):
                            zone_id = zone_obj['id']
                            zone_name = zone_obj['name']

                            DNS.createDNSRecordCloudFlare(
                                cf, zone_id, zone_name, "default._domainkey." + topLevelDomain, 'TXT',
                                output[leftIndex:rightIndex], 0, 3600)


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
    def createDNSRecordCloudFlare(cf, zone, zone_name, name, type, value, priority, ttl, proxied=None):
        try:
            import tldextract
            from plogical.cloudflare_dns_sync import CloudflareDnsSync
            if not zone_name:
                parsed = tldextract.TLDExtract(cache_dir=None)(name)
                zone_name = parsed.domain + '.' + parsed.suffix
            CloudflareDnsSync.upsert_dns_record(
                cf, zone, zone_name, name, type, value, priority, ttl, proxied)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + '. [createDNSRecordCloudFlare]')

    @staticmethod
    def bumpSOASerial(zone):
        """Increment SOA serial for a MASTER zone (PowerDNS zone transfer signaling)."""
        try:
            if zone is None or getattr(zone, 'type', None) != 'MASTER':
                return False
            updated = False
            for getSOA in Records.objects.filter(domainOwner=zone, type='SOA'):
                parts = (getSOA.content or '').split()
                if len(parts) < 3:
                    continue
                try:
                    parts[2] = str(int(parts[2]) + 1)
                except (TypeError, ValueError):
                    logging.CyberCPLogFileWriter.writeToFile(
                        'SOA serial bump skipped: invalid serial in record id %s' % (getSOA.id,)
                    )
                    continue
                getSOA.content = ' '.join(parts)
                getSOA.save()
                updated = True
            return updated
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [bumpSOASerial]')
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
                        params = {'name': zone.name, 'per_page': 50}
                        zones = cf.zones.get(params=params)

                        for zone_obj in sorted(zones, key=lambda v: v['name']):
                            zone_id = zone_obj['id']
                            zone_name = zone_obj['name']

                            DNS.createDNSRecordCloudFlare(cf, zone_id, zone_name, name, type, value, priority, ttl)

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

            command = f'echo "{CFContent}" >> {path}'
            ProcessUtilities.executioner(command, None, True)

            return 1, None

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(f'ConfigureCloudflareInAcme, Error: {str(msg)}')
            return 0, str(msg)
