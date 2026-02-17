#!/usr/local/CyberCP/bin/python
import argparse
import errno
import os.path
import sys
import django

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.http import HttpResponse
import json
try:
    from plogical.dnsUtilities import DNS
    from loginSystem.models import Administrator
    from .models import Domains, Records
    from plogical.mailUtilities import mailUtilities
    from websiteFunctions.models import Websites, ChildDomains
except Exception:
    Websites = None
    ChildDomains = None
import os
from re import match,I,M
from plogical.acl import ACLManager
import CloudFlare
import re
import plogical.CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from plogical.httpProc import httpProc

class DNSManager:
    defaultNameServersPath = '/home/cyberpanel/defaultNameservers'

    def __init__(self, extraArgs=None):
        self.extraArgs = extraArgs

    def loadCFKeys(self):
        cfFile = '%s%s' % (DNS.CFPath, self.admin.userName)
        data = open(cfFile, 'r').readlines()
        self.email = data[0].rstrip('\n')
        self.key = data[1].rstrip('\n')

    def loadDNSHome(self, request = None, userID = None):
        admin = Administrator.objects.get(pk=userID)
        template = 'dns/index.html'
        proc = httpProc(request, template, {"type": admin.type}, 'createDNSZone')
        return proc.render()

    def createNameserver(self, request = None, userID = None):
        mailUtilities.checkHome()

        if os.path.exists('/home/cyberpanel/powerdns'):
            finalData = {"status": 1}
        else:
            finalData = {"status": 0}

        template = 'dns/createNameServer.html'
        proc = httpProc(request, template, finalData, 'createNameServer')
        return proc.render()

    def NSCreation(self, userID = None, data = None):
        try:
            admin = Administrator.objects.get(pk=userID)
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createNameServer') == 0:
                return ACLManager.loadErrorJson('NSCreation', 0)


            domainForNS = data['domainForNS']
            ns1 = data['ns1']
            ns2 = data['ns2']
            firstNSIP = data['firstNSIP']
            secondNSIP = data['secondNSIP']

            DNS.dnsTemplate(domainForNS, admin)

            newZone = Domains.objects.get(name=domainForNS)

            ## NS1


            record = Records(domainOwner=newZone,
                             domain_id=newZone.id,
                             name=ns1,
                             type="A",
                             content=firstNSIP,
                             ttl=3600,
                             prio=0,
                             disabled=0,
                             auth=1)
            record.save()

            ## NS2

            record = Records(domainOwner=newZone,
                             domain_id=newZone.id,
                             name=ns2,
                             type="A",
                             content=secondNSIP,
                             ttl=3600,
                             prio=0,
                             disabled=0,
                             auth=1)
            record.save()

            final_dic = {'NSCreation': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'NSCreation': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def createDNSZone(self, request = None, userID = None):

        if os.path.exists('/home/cyberpanel/powerdns'):
            finalData = {'status': 1}
        else:
            finalData = {'status': 0}

        template = 'dns/createDNSZone.html'
        proc = httpProc(request, template, finalData, 'createDNSZone')
        return proc.render()

    def zoneCreation(self, userID = None, data = None):
        try:
            admin = Administrator.objects.get(pk=userID)

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createDNSZone') == 0:
                return ACLManager.loadErrorJson('zoneCreation', 0)

            zoneDomain = data['zoneDomain']

            newZone = Domains(admin=admin, name=zoneDomain, type="MASTER")
            newZone.save()

            content = "ns1." + zoneDomain + " hostmaster." + zoneDomain + " 1 10800 3600 1209600 3600"

            soaRecord = Records(domainOwner=newZone,
                                domain_id=newZone.id,
                                name=zoneDomain,
                                type="SOA",
                                content=content,
                                ttl=3600,
                                prio=0,
                                disabled=0,
                                auth=1)
            soaRecord.save()

            final_dic = {'zoneCreation': 1}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'zoneCreation': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addDeleteDNSRecords(self, request = None, userID = None):
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/powerdns'):
            finalData = {"status": 0}
        else:
            finalData = {"status": 1}

        # Get DNS zones directly from the Domains table instead of just websites
        finalData['domainsList'] = ACLManager.findAllDNSZones(currentACL, userID)


        template = 'dns/addDeleteDNSRecords.html'
        proc = httpProc(request, template, finalData, 'addDeleteRecords')
        return proc.render()

    def getCurrentRecordsForDomain(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)


            zoneDomain = data['selectedZone']
            currentSelection = data['currentSelection']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            domain = Domains.objects.get(name=zoneDomain)
            records = Records.objects.filter(domain_id=domain.id)

            fetchType = ""

            if currentSelection == 'aRecord':
                fetchType = 'A'
            elif currentSelection == 'aaaaRecord':
                fetchType = 'AAAA'
            elif currentSelection == 'cNameRecord':
                fetchType = 'CNAME'
            elif currentSelection == 'mxRecord':
                fetchType = 'MX'
            elif currentSelection == 'txtRecord':
                fetchType = 'TXT'
            elif currentSelection == 'spfRecord':
                fetchType = 'SPF'
            elif currentSelection == 'nsRecord':
                fetchType = 'NS'
            elif currentSelection == 'soaRecord':
                fetchType = 'SOA'
            elif currentSelection == 'srvRecord':
                fetchType = 'SRV'
            elif currentSelection == 'caaRecord':
                fetchType = 'CAA'

            json_data = "["
            checker = 0

            for items in records:
                if items.type == fetchType:
                    dic = {'id': items.id,
                           'type': items.type,
                           'name': items.name,
                           'content': items.content,
                           'priority': items.prio,
                           'ttl': items.ttl
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)
                else:
                    continue

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addDNSRecord(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('add_status', 0)

            zoneDomain = data['selectedZone']
            recordType = data['recordType']
            recordName = data['recordName']

            ttl = int(data['ttl'])
            if ttl < 0:
                raise ValueError("TTL: The item must be greater than 0")
            elif ttl > 86400:
                raise ValueError("TTL: The item must be lesser than 86401")

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            zone = Domains.objects.get(name=zoneDomain)
            value = ""

            if recordType == "A":

                recordContentA = data['recordContentA']  ## IP or pointing value

                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain

                DNS.createDNSRecord(zone, value, recordType, recordContentA, 0, ttl)

            elif recordType == "MX":

                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain

                recordContentMX = data['recordContentMX']
                priority = data['priority']

                DNS.createDNSRecord(zone, value, recordType, recordContentMX, priority, ttl)

            elif recordType == "AAAA":

                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain

                recordContentAAAA = data['recordContentAAAA']  ## IP or pointing value

                DNS.createDNSRecord(zone, value, recordType, recordContentAAAA, 0, ttl)

            elif recordType == "CNAME":

                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain

                recordContentCNAME = data['recordContentCNAME']  ## IP or pointing value

                DNS.createDNSRecord(zone, value, recordType, recordContentCNAME, 0, ttl)

            elif recordType == "SPF":

                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain

                recordContentSPF = data['recordContentSPF']  ## IP or pointing value

                DNS.createDNSRecord(zone, value, recordType, recordContentSPF, 0, ttl)

            elif recordType == "TXT":

                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain

                recordContentTXT = data['recordContentTXT']  ## IP or pointing value

                DNS.createDNSRecord(zone, value, recordType, recordContentTXT, 0, ttl)

            elif recordType == "SOA":

                recordContentSOA = data['recordContentSOA']

                DNS.createDNSRecord(zone, recordName, recordType, recordContentSOA, 0, ttl)

            elif recordType == "NS":

                recordContentNS = data['recordContentNS']

                if recordContentNS == "@":
                    recordContentNS = "ns1." + zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?',
                           recordContentNS, M | I):
                    recordContentNS = recordContentNS
                else:
                    recordContentNS = recordContentNS + "." + zoneDomain

                DNS.createDNSRecord(zone, recordName, recordType, recordContentNS, 0, ttl)

            elif recordType == "SRV":

                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain

                recordContentSRV = data['recordContentSRV']
                priority = data['priority']

                DNS.createDNSRecord(zone, value, recordType, recordContentSRV, priority, ttl)

            elif recordType == "CAA":
                if recordName == "@":
                    value = zoneDomain
                ## re.match
                elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                           M | I):
                    value = recordName
                else:
                    value = recordName + "." + zoneDomain
                recordContentCAA = data['recordContentCAA']  ## IP or pointing value
                DNS.createDNSRecord(zone, value, recordType, recordContentCAA, 0, ttl)

            final_dic = {'status': 1, 'add_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def updateRecord(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('add_status', 0)

            zoneDomain = data['selectedZone']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            record = Records.objects.get(pk=data['id'])

            if ACLManager.VerifyRecordOwner(currentACL, record, zoneDomain) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if data['nameNow'] != None:
                record.name = data['nameNow']

            if data['ttlNow'] != None:
                record.ttl = int(data['ttlNow'])
                if record.ttl < 0:
                    raise ValueError("TTL: The item must be greater than 0")
                elif record.ttl > 86400:
                    raise ValueError("TTL: The item must be lesser than 86401")

            if data['priorityNow'] != None:
                record.prio = int(data['priorityNow'])

            if data['contentNow'] != None:
                record.content = data['contentNow']

            record.save()

            final_dic = {'status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteDNSRecord(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('delete_status', 0)

            id = data['id']

            delRecord = Records.objects.get(id=id)

            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnershipZone(delRecord.domainOwner.name, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()


            delRecord.delete()

            final_dic = {'status': 1, 'delete_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteDNSZone(self, request = None, userID = None):
        currentACL = ACLManager.loadedACL(userID)
        if not os.path.exists('/home/cyberpanel/powerdns'):
            finalData = {"status": 0}
        else:
            finalData = {"status": 1}

        # Get DNS zones directly from the Domains table instead of just websites
        finalData['domainsList'] = ACLManager.findAllDNSZones(currentACL, userID)
        template = 'dns/deleteDNSZone.html'
        proc = httpProc(request, template, finalData, 'deleteZone')
        return proc.render()

    def submitZoneDeletion(self, userID = None, data = None):
        try:
            zoneDomain = data['zoneDomain']

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteZone') == 0:
                return ACLManager.loadErrorJson('delete_status', 0)


            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            delZone = Domains.objects.get(name=zoneDomain)
            admin = Administrator.objects.get(pk=userID)
            if currentACL['admin'] == 1:
                if delZone.admin != admin:
                    return ACLManager.loadErrorJson()

            delZone.delete()

            final_dic = {'delete_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def configureDefaultNameServers(self, request=None, userID=None):
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/powerdns'):
            data = {"status": 0}
        else:
            data = {"status": 1}

        data['domainsList'] = ACLManager.findAllDomains(currentACL, userID)
        if os.path.exists(DNSManager.defaultNameServersPath):
            nsData = open(DNSManager.defaultNameServersPath, 'r').readlines()
            try:
                data['firstNS'] = nsData[0].rstrip('\n')
            except:
                pass
            try:
                data['secondNS'] = nsData[1].rstrip('\n')
            except:
                pass
            try:
                data['thirdNS'] = nsData[2].rstrip('\n')
            except:
                pass
            try:
                data['forthNS'] = nsData[3].rstrip('\n')
            except:
                pass

        template = 'dns/configureDefaultNameServers.html'
        proc = httpProc(request, template, data, 'admin')
        return proc.render()

    def saveNSConfigurations(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            nsContent = ''

            try:
                nsContent = '%s\n%s\n%s\n%s\n' % (data['firstNS'].rstrip('\n'), data['secondNS'].rstrip('\n'), data['thirdNS'].rstrip('\n'), data['forthNS'].rstrip('\n'))
            except:
                try:
                    nsContent = '%s\n%s\n%s\n' % (data['firstNS'].rstrip('\n'), data['secondNS'].rstrip('\n'), data['thirdNS'].rstrip('\n'))
                except:
                    try:
                        nsContent = '%s\n%s\n' % (data['firstNS'].rstrip('\n'), data['secondNS'].rstrip('\n'))
                    except:
                        try:
                            nsContent = '%s\n' % (data['firstNS'].rstrip('\n'))
                        except:
                            pass

            writeToFile = open(DNSManager.defaultNameServersPath, 'w')
            writeToFile.write(nsContent.rstrip('\n'))
            writeToFile.close()

            ###

            import tldextract

            no_cache_extract = tldextract.TLDExtract(cache_dir=None)

            nsData = open(DNSManager.defaultNameServersPath, 'r').readlines()

            for ns in nsData:
                extractDomain = no_cache_extract(ns.rstrip('\n'))
                topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix

                zone = Domains.objects.get(name=topLevelDomain)

                DNS.createDNSRecord(zone, ns, 'A', ACLManager.fetchIP(), 0, 1400)

            final_dic = {'status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addDeleteDNSRecordsCloudFlare(self, request = None, userID = None):
        currentACL = ACLManager.loadedACL(userID)
        if not os.path.exists('/home/cyberpanel/powerdns'):
            status = 0
        else:
            status = 1
        admin = Administrator.objects.get(pk=userID)

        CloudFlare = 0

        cfPath = '%s%s' % (DNS.CFPath, admin.userName)

        if os.path.exists(cfPath):
            CloudFlare = 1
            allDomains = ACLManager.findAllDomains(currentACL, userID)
            # Filter to only show main domains (domains with exactly one dot, e.g., "example.com")
            # Sub-domains have two or more dots (e.g., "subdomain.example.com")
            domainsList = [domain for domain in allDomains if domain.count('.') == 1]
            self.admin = admin
            self.loadCFKeys()
            data = {"domainsList": domainsList, "status": status, 'CloudFlare': CloudFlare, 'cfEmail': self.email,
                    'cfToken': self.key}
        else:
            data = {"status": status, 'CloudFlare': CloudFlare}

        template = 'dns/addDeleteDNSRecordsCloudFlare.html'
        proc = httpProc(request, template, data, 'addDeleteRecords')
        return proc.render()

    def saveCFConfigs(self, userID = None, data = None):
        try:
            cfEmail = data['cfEmail']
            cfToken = data['cfToken']
            cfSync = data['cfSync']

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('status', 0)

            admin = Administrator.objects.get(pk=userID)
            cfPath = '%s%s' % (DNS.CFPath, admin.userName)

            writeToFile = open(cfPath, 'w')
            writeToFile.write('%s\n%s\n%s' % (cfEmail, cfToken, cfSync))
            writeToFile.close()

            os.chmod(cfPath, 0o600)

            final_dic = {'status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def getCurrentRecordsForDomainCloudFlare(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)


            zoneDomain = data['selectedZone']
            currentSelection = data['currentSelection']

            admin = Administrator.objects.get(pk=userID)
            self.admin = admin

            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            self.loadCFKeys()

            params = {'name': zoneDomain, 'per_page':50}
            cf = CloudFlare.CloudFlare(email=self.email,token=self.key)

            try:
                zones = cf.zones.get(params=params)
            except BaseException as e:
                final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(e), "data": '[]'})
                return HttpResponse(final_json)

            # there should only be one zone

            if len(zones) == 0:
                final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': '', "data": '[]'})
                return HttpResponse(final_json)

            for zone in sorted(zones, key=lambda v: v['name']):
                zone_name = zone['name']
                zone_id = zone['id']

                fetchType = ""

                if currentSelection == 'aRecord':
                    fetchType = 'A'
                elif currentSelection == 'aaaaRecord':
                    fetchType = 'AAAA'
                elif currentSelection == 'cNameRecord':
                    fetchType = 'CNAME'
                elif currentSelection == 'mxRecord':
                    fetchType = 'MX'
                elif currentSelection == 'txtRecord':
                    fetchType = 'TXT'
                elif currentSelection == 'spfRecord':
                    fetchType = 'SPF'
                elif currentSelection == 'nsRecord':
                    fetchType = 'NS'
                elif currentSelection == 'soaRecord':
                    fetchType = 'SOA'
                elif currentSelection == 'srvRecord':
                    fetchType = 'SRV'
                elif currentSelection == 'caaRecord':
                    fetchType = 'CAA'

                try:
                    dns_records = cf.zones.dns_records.get(zone_id, params={'per_page':50, 'type':fetchType})
                except BaseException as e:
                    final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(e), "data": '[]'})
                    return HttpResponse(final_json)

                prog = re.compile('\.*' + zone_name + '$')
                dns_records = sorted(dns_records, key=lambda v: prog.sub('', v['name']) + '_' + v['type'])

                json_data = "["
                checker = 0

                for dns_record in dns_records:
                    if dns_record['ttl'] == 1:
                        ttl = 'AUTO'
                    else:
                        ttl = dns_record['ttl']

                    prio = dns_record.get('priority', 0)
                    if prio is None:
                        prio = 0
                    dic = {'id': dns_record['id'],
                           'type': dns_record['type'],
                           'name': dns_record['name'],
                           'content': dns_record['content'],
                           'priority': str(prio),
                           'ttl': ttl,
                           'proxy': dns_record['proxied'],
                           'proxiable': dns_record['proxiable']
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)


                json_data = json_data + ']'
                final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteDNSRecordCloudFlare(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            zoneDomain = data['selectedZone']
            id = data['id']

            admin = Administrator.objects.get(pk=userID)
            self.admin = admin

            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            self.loadCFKeys()

            params = {'name': zoneDomain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)

            try:
                zones = cf.zones.get(params=params)
            except BaseException as e:
                final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': str(e), "data": '[]'})
                return HttpResponse(final_json)

            for zone in sorted(zones, key=lambda v: v['name']):
                zone_id = zone['id']

                cf.zones.dns_records.delete(zone_id, id)

                final_dic = {'status': 1, 'delete_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def getExportRecordsCloudFlare(self, userID=None, data=None):
        """Fetch all DNS records for a zone (all types) for export. Returns JSON list."""
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)
            zone_domain = data.get('selectedZone', '').strip()
            if not zone_domain:
                final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': 'Zone is required.', 'data': '[]'})
                return HttpResponse(final_json)
            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zone_domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson()
            self.loadCFKeys()
            params = {'name': zone_domain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)
            zones = cf.zones.get(params=params)
            if not zones:
                final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': 'Zone not found.', 'data': '[]'})
                return HttpResponse(final_json)
            zone_id = sorted(zones, key=lambda v: v['name'])[0]['id']
            all_records = []
            page = 1
            per_page = 100
            while True:
                try:
                    dns_records = cf.zones.dns_records.get(zone_id, params={'per_page': per_page, 'page': page})
                except BaseException as e:
                    final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(e), 'data': '[]'})
                    return HttpResponse(final_json)
                if not dns_records:
                    break
                for dns_record in dns_records:
                    ttl = 'AUTO' if dns_record.get('ttl') == 1 else dns_record.get('ttl', 3600)
                    prio = dns_record.get('priority') or 0
                    all_records.append({
                        'id': dns_record.get('id'),
                        'type': dns_record.get('type'),
                        'name': dns_record.get('name'),
                        'content': dns_record.get('content'),
                        'priority': prio,
                        'ttl': ttl,
                        'proxy': dns_record.get('proxied', False),
                        'proxiable': dns_record.get('proxiable', False),
                    })
                if len(dns_records) < per_page:
                    break
                page += 1
            final_json = json.dumps({
                'status': 1,
                'fetchStatus': 1,
                'error_message': '',
                'data': json.dumps(all_records),
            }, default=str)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(msg), 'data': '[]'})
            return HttpResponse(final_json)

    def clearAllDNSRecordsCloudFlare(self, userID=None, data=None):
        """Delete all DNS records for a zone. Returns list of deleted records for local backup/restore."""
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('delete_status', 0)
            zone_domain = data.get('selectedZone', '').strip()
            if not zone_domain:
                final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': 'Zone is required.', 'deleted_records': []})
                return HttpResponse(final_json)
            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zone_domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson()
            self.loadCFKeys()
            params = {'name': zone_domain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)
            zones = cf.zones.get(params=params)
            if not zones:
                final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': 'Zone not found.', 'deleted_records': []})
                return HttpResponse(final_json)
            zone_id = sorted(zones, key=lambda v: v['name'])[0]['id']
            deleted = []
            page = 1
            per_page = 100
            while True:
                try:
                    dns_records = cf.zones.dns_records.get(zone_id, params={'per_page': per_page, 'page': page})
                except BaseException as e:
                    final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': str(e), 'deleted_records': deleted})
                    return HttpResponse(final_json)
                if not dns_records:
                    break
                for dns_record in dns_records:
                    rec_type = dns_record.get('type', '')
                    if rec_type in ('SOA', 'NS'):
                        continue
                    rec_id = dns_record.get('id')
                    ttl = 'AUTO' if dns_record.get('ttl') == 1 else dns_record.get('ttl', 3600)
                    prio = dns_record.get('priority') or 0
                    deleted.append({
                        'id': rec_id,
                        'type': rec_type,
                        'name': dns_record.get('name'),
                        'content': dns_record.get('content'),
                        'priority': prio,
                        'ttl': ttl,
                        'proxy': dns_record.get('proxied', False),
                        'proxiable': dns_record.get('proxiable', False),
                    })
                    try:
                        cf.zones.dns_records.delete(zone_id, rec_id)
                    except BaseException as e:
                        final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': str(e), 'deleted_records': deleted})
                        return HttpResponse(final_json)
                if len(dns_records) < per_page:
                    break
                page += 1
            final_json = json.dumps({'status': 1, 'delete_status': 1, 'error_message': '', 'deleted_records': deleted}, default=str)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': str(msg), 'deleted_records': []})
            return HttpResponse(final_json)

    def importDNSRecordsCloudFlare(self, userID=None, data=None):
        """Import DNS records from a list. Creates each record via CloudFlare API."""
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('import_status', 0)
            zone_domain = data.get('selectedZone', '').strip()
            records = data.get('records', [])
            if not zone_domain:
                final_json = json.dumps({'status': 0, 'import_status': 0, 'error_message': 'Zone is required.', 'imported': 0, 'failed': []})
                return HttpResponse(final_json)
            if not isinstance(records, list):
                final_json = json.dumps({'status': 0, 'import_status': 0, 'error_message': 'records must be a list.', 'imported': 0, 'failed': []})
                return HttpResponse(final_json)
            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zone_domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson()
            self.loadCFKeys()
            params = {'name': zone_domain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)
            zones = cf.zones.get(params=params)
            if not zones:
                final_json = json.dumps({'status': 0, 'import_status': 0, 'error_message': 'Zone not found.', 'imported': 0, 'failed': []})
                return HttpResponse(final_json)
            zone_id = sorted(zones, key=lambda v: v['name'])[0]['id']
            imported = 0
            failed = []
            for rec in records:
                name = (rec.get('name') or '').strip()
                rec_type = (rec.get('type') or '').strip().upper()
                content = (rec.get('content') or '').strip()
                if not name or not rec_type or not content:
                    failed.append({'name': name or '(empty)', 'error': 'Name, type and content required.'})
                    continue
                ttl_val = rec.get('ttl', 3600)
                if ttl_val == 'AUTO' or ttl_val == 1:
                    ttl_int = 1
                else:
                    try:
                        ttl_int = int(ttl_val)
                        if ttl_int < 0:
                            ttl_int = 1
                        elif ttl_int > 86400 and ttl_int != 1:
                            ttl_int = 86400
                    except (ValueError, TypeError):
                        ttl_int = 3600
                priority = 0
                try:
                    priority = int(rec.get('priority', 0) or 0)
                except (ValueError, TypeError):
                    pass
                proxied = bool(rec.get('proxy', False) and rec.get('proxiable', True))
                try:
                    DNS.createDNSRecordCloudFlare(cf, zone_id, name, rec_type, content, priority, ttl_int, proxied=proxied)
                    imported += 1
                except BaseException as e:
                    failed.append({'name': name, 'error': str(e)})
            final_json = json.dumps({
                'status': 1,
                'import_status': 1,
                'error_message': '',
                'imported': imported,
                'failed': failed,
            }, default=str)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'import_status': 0, 'error_message': str(msg), 'imported': 0, 'failed': []})
            return HttpResponse(final_json)

    def _get_valid_hostnames_for_zone(self, zone_domain):
        """Return set of valid hostnames for this zone (main domain + child domains in panel)."""
        valid = set()
        valid.add(zone_domain.lower().strip())
        if Websites is None or ChildDomains is None:
            return valid
        try:
            website = Websites.objects.get(domain=zone_domain)
            valid.add(website.domain.lower())
            for child in website.childdomains_set.all():
                valid.add(child.domain.lower())
        except (Websites.DoesNotExist, Exception):
            pass
        return valid

    def getStaleDNSRecordsCloudFlare(self, userID=None, data=None):
        """List DNS records that point to subdomains/hostnames no longer in the panel (orphan/stale)."""
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)
            zone_domain = data.get('selectedZone', '').strip()
            if not zone_domain:
                final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': 'Zone is required.', 'stale_records': []})
                return HttpResponse(final_json)
            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zone_domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson()
            valid_hostnames = self._get_valid_hostnames_for_zone(zone_domain)
            self.loadCFKeys()
            params = {'name': zone_domain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)
            zones = cf.zones.get(params=params)
            if not zones:
                final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': 'Zone not found.', 'stale_records': []})
                return HttpResponse(final_json)
            zone_id = sorted(zones, key=lambda v: v['name'])[0]['id']
            stale = []
            page = 1
            per_page = 100
            zone_lower = zone_domain.lower()
            # Only consider A, AAAA, CNAME as "subdomain" records that can be stale
            host_record_types = ('A', 'AAAA', 'CNAME')
            while True:
                try:
                    dns_records = cf.zones.dns_records.get(zone_id, params={'per_page': per_page, 'page': page})
                except BaseException as e:
                    final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(e), 'stale_records': []})
                    return HttpResponse(final_json)
                if not dns_records:
                    break
                for dns_record in dns_records:
                    rec_type = (dns_record.get('type') or '').strip().upper()
                    if rec_type not in host_record_types:
                        continue
                    name = (dns_record.get('name') or '').strip()
                    if not name:
                        continue
                    fqdn = name.lower().rstrip('.')
                    if fqdn in valid_hostnames:
                        continue
                    ttl = 'AUTO' if dns_record.get('ttl') == 1 else dns_record.get('ttl', 3600)
                    stale.append({
                        'id': dns_record.get('id'),
                        'type': rec_type,
                        'name': name,
                        'content': dns_record.get('content', ''),
                        'priority': dns_record.get('priority') or 0,
                        'ttl': ttl,
                        'proxy': dns_record.get('proxied', False),
                    })
                if len(dns_records) < per_page:
                    break
                page += 1
            final_json = json.dumps({
                'status': 1,
                'fetchStatus': 1,
                'error_message': '',
                'stale_records': stale,
            }, default=str)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'fetchStatus': 0, 'error_message': str(msg), 'stale_records': []})
            return HttpResponse(final_json)

    def removeStaleDNSRecordsCloudFlare(self, userID=None, data=None):
        """Remove DNS records that are stale (optionally by id list). Returns deleted list for backup."""
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('delete_status', 0)
            zone_domain = data.get('selectedZone', '').strip()
            ids_to_remove = data.get('ids', [])
            if not zone_domain:
                final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': 'Zone is required.', 'deleted_records': []})
                return HttpResponse(final_json)
            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zone_domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson()
            self.loadCFKeys()
            params = {'name': zone_domain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)
            zones = cf.zones.get(params=params)
            if not zones:
                final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': 'Zone not found.', 'deleted_records': []})
                return HttpResponse(final_json)
            zone_id = sorted(zones, key=lambda v: v['name'])[0]['id']
            if not ids_to_remove:
                valid_hostnames = self._get_valid_hostnames_for_zone(zone_domain)
                zone_lower = zone_domain.lower()
                host_record_types = ('A', 'AAAA', 'CNAME')
                page = 1
                per_page = 100
                while True:
                    dns_records = cf.zones.dns_records.get(zone_id, params={'per_page': per_page, 'page': page})
                    if not dns_records:
                        break
                    for dns_record in dns_records:
                        rec_type = (dns_record.get('type') or '').strip().upper()
                        if rec_type not in host_record_types:
                            continue
                        name = (dns_record.get('name') or '').strip()
                        if not name:
                            continue
                        fqdn = name.lower().rstrip('.')
                        if fqdn not in valid_hostnames:
                            ids_to_remove.append(dns_record.get('id'))
                    if len(dns_records) < per_page:
                        break
                    page += 1
            deleted = []
            for rec_id in ids_to_remove:
                try:
                    rec = cf.zones.dns_records.get(zone_id, rec_id)
                    ttl = 'AUTO' if rec.get('ttl') == 1 else rec.get('ttl', 3600)
                    deleted.append({
                        'id': rec_id,
                        'type': rec.get('type'),
                        'name': rec.get('name'),
                        'content': rec.get('content'),
                        'priority': rec.get('priority') or 0,
                        'ttl': ttl,
                        'proxy': rec.get('proxied', False),
                    })
                    cf.zones.dns_records.delete(zone_id, rec_id)
                except BaseException as e:
                    final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': str(e), 'deleted_records': deleted})
                    return HttpResponse(final_json)
            final_json = json.dumps({'status': 1, 'delete_status': 1, 'error_message': '', 'deleted_records': deleted}, default=str)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': str(msg), 'deleted_records': []})
            return HttpResponse(final_json)

    def fixDNSRecordsCloudFlare(self, userID=None, data=None):
        """Ensure all panel domains/subdomains for the zone have A (and AAAA if available) in CloudFlare. No duplicates."""
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('fix_status', 0)
            zone_domain = data.get('selectedZone', '').strip()
            if not zone_domain:
                final_json = json.dumps({'status': 0, 'fix_status': 0, 'error_message': 'Zone is required.', 'added': 0, 'skipped': 0})
                return HttpResponse(final_json)
            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zone_domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson()
            valid_hostnames = self._get_valid_hostnames_for_zone(zone_domain)
            if not valid_hostnames:
                final_json = json.dumps({'status': 1, 'fix_status': 1, 'error_message': '', 'added': 0, 'skipped': 0})
                return HttpResponse(final_json)
            self.loadCFKeys()
            params = {'name': zone_domain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)
            zones = cf.zones.get(params=params)
            if not zones:
                final_json = json.dumps({'status': 0, 'fix_status': 0, 'error_message': 'Zone not found.', 'added': 0, 'skipped': 0})
                return HttpResponse(final_json)
            zone_id = sorted(zones, key=lambda v: v['name'])[0]['id']
            existing = set()
            page = 1
            per_page = 100
            while True:
                try:
                    dns_records = cf.zones.dns_records.get(zone_id, params={'per_page': per_page, 'page': page})
                except BaseException as e:
                    final_json = json.dumps({'status': 0, 'fix_status': 0, 'error_message': str(e), 'added': 0, 'skipped': 0})
                    return HttpResponse(final_json)
                if not dns_records:
                    break
                for rec in dns_records:
                    n = (rec.get('name') or '').lower().rstrip('.')
                    t = (rec.get('type') or '').strip().upper()
                    if n and t in ('A', 'AAAA', 'CNAME'):
                        existing.add((n, t))
                if len(dns_records) < per_page:
                    break
                page += 1
            server_ip = None
            try:
                server_ip = ACLManager.GetServerIP()
            except Exception:
                pass
            server_ipv6 = None
            try:
                server_ipv6 = ACLManager.GetServerIPv6()
            except Exception:
                pass
            ttl = 3600
            added = 0
            skipped = 0
            for hostname in valid_hostnames:
                name_lower = hostname.lower().rstrip('.')
                if (name_lower, 'A') not in existing and server_ip:
                    try:
                        DNS.createDNSRecordCloudFlare(cf, zone_id, hostname, 'A', server_ip, 0, ttl)
                        existing.add((name_lower, 'A'))
                        added += 1
                    except BaseException as e:
                        final_json = json.dumps({'status': 0, 'fix_status': 0, 'error_message': str(e), 'added': added, 'skipped': skipped})
                        return HttpResponse(final_json)
                elif (name_lower, 'A') in existing:
                    skipped += 1
                if server_ipv6 and (name_lower, 'AAAA') not in existing:
                    try:
                        DNS.createDNSRecordCloudFlare(cf, zone_id, hostname, 'AAAA', server_ipv6, 0, ttl)
                        existing.add((name_lower, 'AAAA'))
                        added += 1
                    except BaseException as e:
                        pass
                elif (name_lower, 'AAAA') in existing:
                    skipped += 1
            final_json = json.dumps({'status': 1, 'fix_status': 1, 'error_message': '', 'added': added, 'skipped': skipped}, default=str)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_json = json.dumps({'status': 0, 'fix_status': 0, 'error_message': str(msg), 'added': 0, 'skipped': 0})
            return HttpResponse(final_json)

    def updateDNSRecordCloudFlare(self, userID=None, data=None):
        """Update an existing CloudFlare DNS record (name, type, ttl, content, priority, proxied)."""
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('update_status', 0)

            zone_domain = data['selectedZone']
            record_id = data['id']
            name = (data.get('name') or '').strip()
            record_type = (data.get('recordType') or data.get('type') or '').strip()
            content = (data.get('content') or '').strip()
            ttl_val = data.get('ttl')
            priority = data.get('priority', 0)
            proxied = data.get('proxied', False)

            if not name or not record_type or not content:
                final_json = json.dumps({'status': 0, 'update_status': 0, 'error_message': 'Name, type and content are required.'})
                return HttpResponse(final_json)

            try:
                ttl_int = int(ttl_val) if ttl_val not in (None, '', 'AUTO') else 1
            except (ValueError, TypeError):
                ttl_int = 1
            if ttl_int < 0:
                ttl_int = 1
            elif ttl_int > 86400 and ttl_int != 1:
                ttl_int = 86400

            try:
                priority_int = int(priority) if priority not in (None, '') else 0
            except (ValueError, TypeError):
                priority_int = 0

            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zone_domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson()

            self.loadCFKeys()
            params = {'name': zone_domain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)
            zones = cf.zones.get(params=params)
            zone_list = sorted(zones, key=lambda v: v['name'])
            if not zone_list:
                final_json = json.dumps({'status': 0, 'update_status': 0, 'error_message': 'Zone not found.'})
                return HttpResponse(final_json)
            zone_id = zone_list[0]['id']

            update_data = {'name': name, 'type': record_type, 'content': content, 'ttl': ttl_int, 'priority': priority_int}
            if record_type in ['A', 'CNAME']:
                update_data['proxied'] = bool(proxied)

            cf.zones.dns_records.put(zone_id, record_id, data=update_data)
            final_dic = {'status': 1, 'update_status': 1, 'error_message': 'None'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'update_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addDNSRecordCloudFlare(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('add_status', 0)

            zoneDomain = data['selectedZone']
            recordType = data['recordType']
            recordName = data['recordName']
            ttl = int(data['ttl'])
            if ttl < 0:
                raise ValueError("TTL: The item must be greater than 0")
            elif ttl > 86400:
                raise ValueError("TTL: The item must be lesser than 86401")

            admin = Administrator.objects.get(pk=userID)
            self.admin = admin
            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            ## Get zone

            self.loadCFKeys()

            params = {'name': zoneDomain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)

            try:
                zones = cf.zones.get(params=params)
            except BaseException as e:
                final_json = json.dumps({'status': 0, 'delete_status': 0, 'error_message': str(e), "data": '[]'})
                return HttpResponse(final_json)

            for zone in sorted(zones, key=lambda v: v['name']):
                zone = zone['id']

                value = ""

                if recordType == "A":

                    recordContentA = data['recordContentA']  ## IP or pointing value

                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain

                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentA, 0, ttl)

                elif recordType == "MX":

                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain

                    recordContentMX = data['recordContentMX']
                    priority = data['priority']

                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentMX, priority, ttl)

                elif recordType == "AAAA":

                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain

                    recordContentAAAA = data['recordContentAAAA']  ## IP or pointing value

                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentAAAA, 0, ttl)

                elif recordType == "CNAME":

                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain

                    recordContentCNAME = data['recordContentCNAME']  ## IP or pointing value

                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentCNAME, 0, ttl)

                elif recordType == "SPF":

                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain

                    recordContentSPF = data['recordContentSPF']  ## IP or pointing value

                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentSPF, 0, ttl)

                elif recordType == "TXT":

                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain

                    recordContentTXT = data['recordContentTXT']  ## IP or pointing value

                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentTXT, 0, ttl)

                elif recordType == "SOA":

                    recordContentSOA = data['recordContentSOA']

                    DNS.createDNSRecordCloudFlare(cf, zone, recordName, recordType, recordContentSOA, 0, ttl)

                elif recordType == "NS":

                    recordContentNS = data['recordContentNS']

                    if recordContentNS == "@":
                        recordContentNS = "ns1." + zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?',
                               recordContentNS, M | I):
                        recordContentNS = recordContentNS
                    else:
                        recordContentNS = recordContentNS + "." + zoneDomain

                    DNS.createDNSRecordCloudFlare(cf, zone, recordName, recordType, recordContentNS, 0, ttl)

                elif recordType == "SRV":

                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain

                    recordContentSRV = data['recordContentSRV']
                    priority = data['priority']

                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentSRV, priority, ttl)

                elif recordType == "CAA":
                    if recordName == "@":
                        value = zoneDomain
                    ## re.match
                    elif match(r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', recordName,
                               M | I):
                        value = recordName
                    else:
                        value = recordName + "." + zoneDomain
                    recordContentCAA = data['recordContentCAA']  ## IP or pointing value
                    DNS.createDNSRecordCloudFlare(cf, zone, value, recordType, recordContentCAA, 0, ttl)

                final_dic = {'status': 1, 'add_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def syncCF(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('add_status', 0)

            zoneDomain = data['selectedZone']

            admin = Administrator.objects.get(pk=userID)
            self.admin = admin

            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            ## Get zone

            dns = DNS()

            status, error = dns.cfTemplate(zoneDomain, admin)

            if status == 1:
                final_dic = {'status': 1, 'error_message': 'None'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 0, 'error_message': error}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)


    def enableProxy(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            zoneDomain = data['selectedZone']
            name = data['name']
            value = data['value']

            admin = Administrator.objects.get(pk=userID)
            self.admin = admin

            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            self.loadCFKeys()

            params = {'name': zoneDomain, 'per_page': 50}
            cf = CloudFlare.CloudFlare(email=self.email, token=self.key)

            zones = cf.zones.get(params=params)
            if not zones:
                final_dic = {'status': 0, 'delete_status': 0, 'error_message': 'Zone not found'}
                return HttpResponse(json.dumps(final_dic), status=400)

            zone = zones[0]
            zone_id = zone['id']

            params = {'name': name}
            dns_records = cf.zones.dns_records.get(zone_id, params=params)

            if value == True:
                new_r_proxied_flag = False
            else:
                new_r_proxied_flag = True

            for dns_record in dns_records:
                r_name = dns_record['name']
                r_type = dns_record['type']
                r_content = dns_record['content']
                r_ttl = dns_record['ttl']
                r_proxied = dns_record['proxied']

                if r_proxied == new_r_proxied_flag:
                    continue

                dns_record_id = dns_record['id']
                new_dns_record = {
                    'type': r_type,
                    'name': r_name,
                    'content': r_content,
                    'ttl': r_ttl,
                    'proxied': new_r_proxied_flag
                }
                cf.zones.dns_records.put(zone_id, dns_record_id, data=new_dns_record)

                final_dic = {'status': 1, 'delete_status': 1, 'error_message': "None"}
                return HttpResponse(json.dumps(final_dic))

            final_dic = {'status': 1, 'delete_status': 1, 'error_message': "None"}
            return HttpResponse(json.dumps(final_dic))

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installPowerDNS(self):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

                command = 'systemctl stop systemd-resolved'
                ProcessUtilities.executioner(command, 'root', True)
                command = 'systemctl disable systemd-resolved.service'
                ProcessUtilities.executioner(command, 'root', True)

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.ubuntu20:

                command = 'DEBIAN_FRONTEND=noninteractive apt-get -y purge pdns-server pdns-backend-mysql -y'
                ProcessUtilities.executioner(command, 'root', True)
            else:
                command = 'yum -y erase pdns pdns-backend-mysql'
                ProcessUtilities.executioner(command, 'root', True)


            #### new install

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                try:
                    os.rename('/etc/resolv.conf', 'etc/resolved.conf')
                except OSError as e:
                    if e.errno != errno.EEXIST and e.errno != errno.ENOENT:
                        logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], "[ERROR] Unable to rename /etc/resolv.conf to install PowerDNS: " +
                                                 str(e) + "[404]")
                        return 0
                    try:
                        os.remove('/etc/resolv.conf')
                    except OSError as e1:
                        logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                                  "[ERROR] Unable to remove existing /etc/resolv.conf to install PowerDNS: " +
                            str(e1) + "[404]")
                        return 0


            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                # Update package list first
                command = "DEBIAN_FRONTEND=noninteractive apt-get update"
                ProcessUtilities.executioner(command, 'root', True)
                
                command = "DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server pdns-backend-mysql"
                result = ProcessUtilities.executioner(command, 'root', True)
                
                # Ensure service is stopped after installation for configuration
                command = 'systemctl stop pdns || true'
                ProcessUtilities.executioner(command, 'root', True)
                
                return 1
            else:
                command = 'yum -y install pdns pdns-backend-mysql'

            ProcessUtilities.executioner(command, 'root', True)

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile('[ERROR] ' + str(msg) + " [installPowerDNS]")
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '[ERROR] ' + str(msg) + " [installPowerDNS][404]")
            return 0

    def installPowerDNSConfigurations(self, mysqlPassword):
        try:

            ### let see if this is needed the chdir
            cwd = os.getcwd()
            os.chdir('/usr/local/CyberCP/install')
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                dnsPath = "/etc/pdns/pdns.conf"
            else:
                dnsPath = "/etc/powerdns/pdns.conf"
                # Ensure directory exists for Ubuntu
                dnsDir = os.path.dirname(dnsPath)
                if not os.path.exists(dnsDir):
                    try:
                        os.makedirs(dnsDir, mode=0o755)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise

            import shutil
            # Backup existing config if it exists
            if os.path.exists(dnsPath):
                try:
                    shutil.move(dnsPath, dnsPath + '.bak')
                except:
                    os.remove(dnsPath)
            
            shutil.copy("dns-one/pdns.conf", dnsPath)
            
            # Verify the file was copied and has MySQL backend configuration
            try:
                with open(dnsPath, "r") as f:
                    content = f.read()
                    if not content or "launch=gmysql" not in content:
                        writeToFile.writeToFile("PowerDNS config incomplete, attempting to fix...")
                        logging.InstallLog.writeToFile("PowerDNS config incomplete, fixing...")
                        
                        # Directly write the essential MySQL configuration
                        mysql_config = """# PowerDNS MySQL Backend Configuration
launch=gmysql
gmysql-host=localhost
gmysql-port=3306
gmysql-user=cyberpanel
gmysql-password=""" + mysqlPassword + """
gmysql-dbname=cyberpanel

# Basic PowerDNS settings
daemon=no
guardian=no
setgid=pdns
setuid=pdns
"""
                        # Write complete config
                        with open(dnsPath, "w") as f:
                            f.write(mysql_config)
                        
                        writeToFile.writeToFile("MySQL backend configuration written directly")
            except Exception as e:
                writeToFile.writeToFile("Warning: Could not verify config content: " + str(e))
                # Continue anyway as the file copy might have worked

            data = open(dnsPath, "r").readlines()

            writeDataToFile = open(dnsPath, "w")

            dataWritten = "gmysql-password=" + mysqlPassword + "\n"

            for items in data:
                if items.find("gmysql-password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            if self.remotemysql == 'ON':
                command = "sed -i 's|gmysql-host=localhost|gmysql-host=%s|g' %s" % (self.mysqlhost, dnsPath)
                ProcessUtilities.executioner(command, 'root', True)

                command = "sed -i 's|gmysql-port=3306|gmysql-port=%s|g' %s" % (self.mysqlport, dnsPath)
                ProcessUtilities.executioner(command, 'root', True)

            # Set proper permissions for PowerDNS config
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                # Ensure pdns user/group exists
                command = 'id -u pdns &>/dev/null || useradd -r -s /usr/sbin/nologin pdns'
                ProcessUtilities.executioner(command, 'root', True)
                
                command = 'chown root:pdns %s' % dnsPath
                ProcessUtilities.executioner(command, 'root', True)
                
                command = 'chmod 640 %s' % dnsPath
                ProcessUtilities.executioner(command, 'root', True)

            return 1
        except IOError as msg:
            logging.CyberCPLogFileWriter.writeToFile('[ERROR] ' + str(msg) + " [installPowerDNSConfigurations]")
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '[ERROR] ' + str(msg) + " [installPowerDNSConfigurations][404]")
            return 0

    def startPowerDNS(self):

        ############## Start PowerDNS ######################

        command = 'systemctl enable pdns'
        ProcessUtilities.executioner(command)

        # Give PowerDNS time to read configuration
        import time
        time.sleep(2)

        command = 'systemctl start pdns'
        result = ProcessUtilities.executioner(command)
        
        # Check if service started successfully
        command = 'systemctl is-active pdns'
        output = ProcessUtilities.outputExecutioner(command)
        
        if output.strip() != 'active':
            logging.CyberCPLogFileWriter.writeToFile('[ERROR] PowerDNS failed to start. Service status: ' + output)
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '[ERROR] PowerDNS service failed to start properly [404]')
            return 0

        return 1

    def ResetDNSConfigurations(self):
        try:

            ### Check if remote or local mysql

            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(ProcessUtilities.outputExecutioner('cat %s' % (passFile)))

                self.mysqluser = jsonData['mysqluser']
                self.mysqlpassword = jsonData['mysqlpassword']
                self.mysqlport = jsonData['mysqlport']
                self.mysqlhost = jsonData['mysqlhost']
                self.remotemysql = 'ON'

                if self.mysqlhost.find('rds.amazon') > -1:
                    self.RDS = 1

                ## Also set localhost to this server

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddressLocal = ipData.split('\n', 1)[0]

                self.LOCALHOST = ipAddressLocal
            except BaseException as msg:
                self.remotemysql = 'OFF'

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('%s. [setupConnection:75]' % (str(msg)))

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Removing and re-installing DNS..,5')

            if self.installPowerDNS() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'installPowerDNS failed. [404].')
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Resetting configurations..,40')

            import sys
            sys.path.append('/usr/local/CyberCP')
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            from CyberCP import settings

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Configurations reset..,70')

            if self.installPowerDNSConfigurations(settings.DATABASES['default']['PASSWORD']) == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'installPowerDNSConfigurations failed. [404].')
                return 0

            if self.startPowerDNS() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'startPowerDNS failed. [404].')
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Fixing permissions..,90')

            ACLManager.fixPermissions()
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Completed [200].')

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel')
    parser.add_argument('function', help='Specify a function to call!')
    parser.add_argument('--tempStatusPath', help='Path of temporary status file.')

    args = parser.parse_args()

    if args.function == "ResetDNSConfigurations":
        extraArgs = {'tempStatusPath': args.tempStatusPath}
        ftp = DNSManager(extraArgs)
        ftp.ResetDNSConfigurations()

if __name__ == "__main__":
    main()