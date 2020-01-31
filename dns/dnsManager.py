#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.shortcuts import render
from django.http import HttpResponse
import json
from plogical.dnsUtilities import DNS
from loginSystem.models import Administrator
import os
from .models import Domains,Records
from re import match,I,M
from plogical.mailUtilities import mailUtilities
from plogical.acl import ACLManager

class DNSManager:
    defaultNameServersPath = '/home/cyberpanel/defaultNameservers'

    def loadDNSHome(self, request = None, userID = None):
        try:
            admin = Administrator.objects.get(pk=userID)
            return render(request, 'dns/index.html', {"type": admin.type})
        except BaseException as msg:
            return HttpResponse(str(msg))

    def createNameserver(self, request = None, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createNameServer') == 0:
                return ACLManager.loadError()

            mailUtilities.checkHome()

            if os.path.exists('/home/cyberpanel/powerdns'):
                return render(request, "dns/createNameServer.html", {"status": 1})
            else:
                return render(request, "dns/createNameServer.html", {"status": 0})

        except BaseException as msg:
            return HttpResponse(str(msg))

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
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createDNSZone') == 0:
                return ACLManager.loadError()

            if os.path.exists('/home/cyberpanel/powerdns'):
                return render(request, 'dns/createDNSZone.html', {"status": 1})
            else:
                return render(request, 'dns/createDNSZone.html', {"status": 0})
        except BaseException as msg:
                return HttpResponse(str(msg))

    def zoneCreation(self, userID = None, data = None):
        try:
            admin = Administrator.objects.get(pk=userID)

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createDNSZone') == 0:
                return ACLManager.loadErrorJson('zoneCreation', 0)

            zoneDomain = data['zoneDomain']

            newZone = Domains(admin=admin, name=zoneDomain, type="NATIVE")
            newZone.save()

            content = "ns1." + zoneDomain + " hostmaster." + zoneDomain + " 1 10800 3600 604800 3600"

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
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'addDeleteRecords') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/powerdns'):
                return render(request, 'dns/addDeleteDNSRecords.html', {"status": 0})

            domainsList = ACLManager.findAllDomains(currentACL, userID)

            return render(request, 'dns/addDeleteDNSRecords.html', {"domainsList": domainsList, "status": 1})

        except BaseException as msg:
            return HttpResponse(str(msg))

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

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnershipZone(zoneDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            zone = Domains.objects.get(name=zoneDomain)
            value = ""

            if recordType == "A":

                recordContentA = data['recordContentA']  ## IP or ponting value

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

                recordContentAAAA = data['recordContentAAAA']  ## IP or ponting value

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

                recordContentCNAME = data['recordContentCNAME']  ## IP or ponting value

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

                recordContentSPF = data['recordContentSPF']  ## IP or ponting value

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

                recordContentTXT = data['recordContentTXT']  ## IP or ponting value

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
                recordContentCAA = data['recordContentCAA']  ## IP or ponting value
                DNS.createDNSRecord(zone, value, recordType, recordContentCAA, 0, ttl)

            final_dic = {'status': 1, 'add_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_message': str(msg)}
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

        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteZone') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/powerdns'):
                return render(request, 'dns/addDeleteDNSRecords.html', {"status": 0})

            domainsList = ACLManager.findAllDomains(currentACL, userID)

            return render(request, 'dns/deleteDNSZone.html', {"domainsList": domainsList, "status": 1})

        except BaseException as msg:
            return HttpResponse(str(msg))

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

        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/powerdns'):
                return render(request, 'dns/addDeleteDNSRecords.html', {"status": 0})

            data = {}
            data['domainsList'] = ACLManager.findAllDomains(currentACL, userID)
            data['status'] = 1

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

            return render(request, 'dns/configureDefaultNameServers.html', data)

        except BaseException as msg:
            return HttpResponse(str(msg))


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


            final_dic = {'status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)