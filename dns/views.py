# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
import json
from plogical.dnsUtilities import DNS
from loginSystem.models import Administrator
import os
from loginSystem.views import loadLoginPage
from models import Domains,Records

# Create your views here.

def loadDNSHome(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        return render(request,'dns/index.html',{"type":admin.type})
    except KeyError:
        return redirect(loadLoginPage)

def createNameserver(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")

        return render(request,"dns/createNameServer.html")
    except KeyError:
        return redirect(loadLoginPage)



def NSCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                admin = Administrator.objects.get(pk=val)

                data = json.loads(request.body)
                domainForNS = data['domainForNS']
                ns1 = data['ns1']
                ns2 = data['ns2']
                firstNSIP = data['firstNSIP']
                secondNSIP = data['secondNSIP']

                if Domains.objects.filter(name=domainForNS).count() == 0:
                    newZone = Domains(admin=admin,name=domainForNS, type="NATIVE")
                    newZone.save()

                    content = "ns1." + domainForNS + " hostmaster." + domainForNS + " 1 10800 3600 604800 3600"

                    soaRecord = Records(domainOwner=newZone,
                                        domain_id=newZone.id,
                                        name=domainForNS,
                                        type="SOA",
                                        content=content,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1)
                    soaRecord.save()

                    ## NS1

                    record = Records(domainOwner=newZone,
                                        domain_id=newZone.id,
                                        name=domainForNS,
                                        type="NS",
                                        content=ns1,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1)
                    record.save()



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
                                     name=domainForNS,
                                     type="NS",
                                     content=ns2,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()


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

                else:

                    newZone = Domains.objects.get(name=domainForNS)

                    ## NS1

                    record = Records(domainOwner=newZone,
                                     domain_id=newZone.id,
                                     name=domainForNS,
                                     type="NS",
                                     content=ns1,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

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
                                     name=domainForNS,
                                     type="NS",
                                     content=ns2,
                                     ttl=3600,
                                     prio=0,
                                     disabled=0,
                                     auth=1)
                    record.save()

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



        except BaseException, msg:
            final_dic = {'NSCreation': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    except KeyError, msg:
        final_dic = {'NSCreation': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def createDNSZone(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        return render(request,'dns/createDNSZone.html')
    except KeyError:
        return redirect(loadLoginPage)

def zoneCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                admin = Administrator.objects.get(pk=val)

                data = json.loads(request.body)
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



        except BaseException,msg:

            final_dic = {'zoneCreation': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)

    except KeyError,msg:
        final_dic = {'zoneCreation': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def addDeleteDNSRecords(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)
        domainsList = []

        domains = Domains.objects.all()

        for items in domains:
            domainsList.append(items.name)


        return render(request, 'dns/addDeleteDNSRecords.html',{"domainsList":domainsList})

    except KeyError:
        return redirect(loadLoginPage)

def getCurrentRecordsForDomain(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                zoneDomain = data['selectedZone']

                domain = Domains.objects.get(name=zoneDomain)

                records = Records.objects.filter(domain_id=domain.id)

                json_data = "["
                checker = 0

                for items in records:
                    if items.type == "SOA":
                        continue
                    dic = {'id': items.id,
                           'type': items.type,
                           'name': items.name,
                           'content': items.content,
                           'priority': items.prio
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)


                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None","data":json_data})
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def addDNSRecord(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                zoneDomain = data['selectedZone']
                recordType = data['recordType']
                recordName = data['recordName']



                admin = Administrator.objects.get(pk=val)

                zone = Domains.objects.get(name=zoneDomain)
                value = recordName+"."+zoneDomain

                if recordType == "A":
                    recordContentA = data['recordContentA']  ## IP or ponting value
                    if recordName == "@":
                        value = zoneDomain
                    record = Records(   domainOwner=zone,
                                        domain_id=zone.id,
                                        name=value,
                                        type="A",
                                        content=recordContentA,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1  )
                    record.save()
                elif recordType == "MX":
                    recordContentMX = recordType = data['recordContentMX']
                    record = Records(domainOwner=zone,
                                     domain_id=zone.id,
                                     name=zoneDomain,
                                     type="MX",
                                     content=value,
                                     ttl=3600,
                                     prio=recordContentMX,
                                     disabled=0,
                                     auth=1)
                    record.save()
                elif recordType == "AAAA":
                    recordContentAAAA = data['recordContentAAAA']  ## IP or ponting value
                    if recordName == "@":
                        value = zoneDomain
                    record = Records(   domainOwner=zone,
                                        domain_id=zone.id,
                                        name=value,
                                        type="AAAA",
                                        content=recordContentAAAA,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1  )
                    record.save()

                elif recordType == "CNAME":
                    recordName = data['recordName']
                    recordContentCNAME = data['recordContentCNAME']  ## IP or ponting value
                    record = Records(   domainOwner=zone,
                                        domain_id=zone.id,
                                        name=value,
                                        type="CNAME",
                                        content=recordContentCNAME,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1  )
                    record.save()


                elif recordType == "SPF":
                    if recordName == "@":
                        value = zoneDomain
                    recordContentSPF = data['recordContentSPF']  ## IP or ponting value
                    record = Records(   domainOwner=zone,
                                        domain_id=zone.id,
                                        name=value,
                                        type="SPF",
                                        content=recordContentSPF,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1  )
                    record.save()


                elif recordType == "TXT":
                    if recordName == "@":
                        value = zoneDomain
                    recordContentTXT = data['recordContentTXT']  ## IP or ponting value
                    record = Records(   domainOwner=zone,
                                        domain_id=zone.id,
                                        name=value,
                                        type="TXT",
                                        content=recordContentTXT,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1  )
                    record.save()


                final_dic = {'add_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)



        except BaseException,msg:
            final_dic = {'add_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'add_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def deleteDNSRecord(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                id = data['id']

                delRecord = Records.objects.get(id=id)
                delRecord.delete()

                final_dic = {'delete_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'delete_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def deleteDNSZone(request):

    try:
        val = request.session['userID']

        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)
        domainsList = []

        domains = Domains.objects.all()

        for items in domains:
            domainsList.append(items.name)


        return render(request, 'dns/deleteDNSZone.html',{"domainsList":domainsList})

    except KeyError:
        return redirect(loadLoginPage)


def submitZoneDeletion(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                zoneDomain = data['zoneDomain']

                delZone = Domains.objects.get(name=zoneDomain)
                delZone.delete()

                final_dic = {'delete_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'delete_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)




