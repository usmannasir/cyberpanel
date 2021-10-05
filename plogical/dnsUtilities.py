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

                cf = CloudFlare.CloudFlare(email=self.email, token=self.key)

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

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.6/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            import tldextract

            extractDomain = tldextract.extract(domain)
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

                    content = "ns1." + topLevelDomain + " hostmaster." + topLevelDomain + " 1 10800 3600 604800 3600"

                    soaRecord = Records(domainOwner=zone,
                                        domain_id=zone.id,
                                        name=topLevelDomain,
                                        type="SOA",
                                        content=content,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1)
                    soaRecord.save()

                    ## Main A record.

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=topLevelDomain,
                                     type="A",
                                     content=ipAddress,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    # CNAME Records.

                    cNameValue = "www." + topLevelDomain

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=cNameValue,
                                     type="CNAME",
                                     content=topLevelDomain,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    cNameValue = "ftp." + topLevelDomain

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=cNameValue,
                                     type="CNAME",
                                     content=topLevelDomain,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    ## MX Record.

                    mxValue = "mail." + topLevelDomain

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=topLevelDomain,
                                     type="MX",
                                     content=mxValue,
                                     ttl=3600,
                                     prio="10",
                                     disabled=0,
                                     auth=1)
                    record.save()

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=mxValue,
                                     type="A",
                                     content=ipAddress,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    ## TXT Records for mail

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=topLevelDomain,
                                     type="TXT",
                                     content="v=spf1 a mx ip4:" + ipAddress + " ~all",
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name="_dmarc." + topLevelDomain,
                                     type="TXT",
                                     content="v=DMARC1; p=none",
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name="_domainkey." + topLevelDomain,
                                     type="TXT",
                                     content="t=y; o=~;",
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()
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

                    content = "ns1." + topLevelDomain + " hostmaster." + topLevelDomain + " 1 10800 3600 604800 3600"

                    soaRecord = Records(domainOwner=zone,
                                        domain_id=zone.id,
                                        name=topLevelDomain,
                                        type="SOA",
                                        content=content,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1)
                    soaRecord.save()

                    ## Main A record.

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=topLevelDomain,
                                     type="A",
                                     content=ipAddress,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    # CNAME Records.

                    cNameValue = "www." + topLevelDomain

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=cNameValue,
                                     type="CNAME",
                                     content=topLevelDomain,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    cNameValue = "ftp." + topLevelDomain

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=cNameValue,
                                     type="CNAME",
                                     content=topLevelDomain,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    ## MX Record.

                    mxValue = "mail." + topLevelDomain

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=topLevelDomain,
                                     type="MX",
                                     content=mxValue,
                                     ttl=3600,
                                     prio="10",
                                     disabled=0,
                                     auth=1)
                    record.save()

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=mxValue,
                                     type="A",
                                     content=ipAddress,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    ## TXT Records for mail

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=topLevelDomain,
                                     type="TXT",
                                     content="v=spf1 a mx ip4:" + ipAddress + " ~all",
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name="_dmarc." + topLevelDomain,
                                     type="TXT",
                                     content="v=DMARC1; p=none",
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name="_domainkey." + topLevelDomain,
                                     type="TXT",
                                     content="t=y; o=~;",
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

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

                mxValue = "mail." + actualSubDomain

                record = Records(domainOwner=zone,
                                 domain_id=zone.id,
                                 name=actualSubDomain,
                                 type="MX",
                                 content=mxValue,
                                 ttl=3600,
                                 prio="10",
                                 disabled=0,
                                 auth=1)
                record.save()

                ## TXT Records

                record = Records(domainOwner=zone,
                                 domain_id=zone.id,
                                 name=actualSubDomain,
                                 type="TXT",
                                 content="v=spf1 a mx ip4:" + ipAddress + " ~all",
                                 ttl=3600,
                                 prio=0,
                                 disabled=0,
                                 auth=1)
                record.save()

                record = Records(domainOwner=zone,
                                 domain_id=zone.id,
                                 name="_dmarc." + actualSubDomain,
                                 type="TXT",
                                 content="v=DMARC1; p=none",
                                 ttl=3600,
                                 prio=0,
                                 disabled=0,
                                 auth=1)
                record.save()

                record = Records(domainOwner=zone,
                                 domain_id=zone.id,
                                 name="_domainkey." + actualSubDomain,
                                 type="TXT",
                                 content="t=y; o=~;",
                                 ttl=3600,
                                 prio=0,
                                 disabled=0,
                                 auth=1)
                record.save()

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

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.6/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            import tldextract

            extractDomain = tldextract.extract(domain)
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

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                command = ' systemctl restart pdns'
                ProcessUtilities.executioner(command)

            ## Add record to CF If sync enabled

            dns = DNS()
            dns.admin = zone.admin
            if dns.loadCFKeys():
                cf = CloudFlare.CloudFlare(email=dns.email, token=dns.key)

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

            if zone.type == 'MASTER':
                getSOA = Records.objects.get(domainOwner=zone, type='SOA')
                soaContent = getSOA.content.split(' ')
                soaContent[2] = str(int(soaContent[2]) + 1)
                getSOA.content = " ".join(soaContent)
                getSOA.save()

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

                cf = CloudFlare.CloudFlare(email=dns.email, token=dns.key)

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
            delRecord.delete()
        except:
            ## There does not exist a zone for this domain.
            pass
