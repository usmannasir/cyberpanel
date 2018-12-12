#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import CyberCPLogFileWriter as logging
import subprocess
import shlex
from dns.models import Domains,Records
from processUtilities import ProcessUtilities

class DNS:

    nsd_base = "/etc/nsd/nsd.conf"
    zones_base_dir = "/usr/local/lsws/conf/zones/"
    create_zone_dir = "/usr/local/lsws/conf/zones"

    ## DNS Functions

    @staticmethod
    def dnsTemplate(domain, admin):
        try:

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            import tldextract

            extractDomain = tldextract.extract(domain)
            topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix
            subDomain = extractDomain.subdomain

            if len(subDomain) == 0:

                if Domains.objects.filter(name=topLevelDomain).count() == 0:
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
            else:
                if Domains.objects.filter(name=topLevelDomain).count() == 0:
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

                # CNAME Records.

                cNameValue = "www." + actualSubDomain

                DNS.createDNSRecord(zone, cNameValue, "CNAME", actualSubDomain, 0, 3600)

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                command = 'sudo systemctl restart pdns'
                ProcessUtilities.executioner(command)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                "We had errors while creating DNS records for: " + domain + ". Error message: " + str(msg))

    @staticmethod
    def createDKIMRecords(domain):
        try:

            import tldextract

            extractDomain = tldextract.extract(domain)
            topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix

            zone = Domains.objects.get(name=topLevelDomain)

            path = "/etc/opendkim/keys/" + topLevelDomain + "/default.txt"
            command = "sudo cat " + path
            output = subprocess.check_output(shlex.split(command))
            leftIndex = output.index('(') + 2
            rightIndex = output.rindex(')') - 1

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                command = 'sudo systemctl restart pdns'
                ProcessUtilities.executioner(command)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                "We had errors while creating DKIM record for: " + domain + ". Error message: " + str(msg))

    @staticmethod
    def getZoneObject(virtualHostName):
        try:
            return Domains.objects.get(name=virtualHostName)
        except:
            return 0

    @staticmethod
    def createDNSRecord(zone, name, type, value, priority, ttl):
        try:
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

                    if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
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

                    if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
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

                if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
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
                if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                    command = 'sudo systemctl restart pdns'
                    ProcessUtilities.executioner(command)
        except BaseException, msg:
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
