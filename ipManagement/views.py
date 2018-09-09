# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render, HttpResponse,redirect
from loginSystem.models import Administrator
from CyberTronAPI.CyberTronLogger import CyberTronLogger as logging
from loginSystem.views import loadLoginPage
import json
from .models import IPPool, IPAddresses
from inspect import stack
from plogical.aclVMM import vmmACLManager
from plogical.acl import ACLManager
from hypervisor.models import HyberVisors
from vpsManagement.models import VPS
# Create your views here.

def listIPHome(request):
    try:
        userID = request.session['userID']
        try:
            return render(request, 'ipManagement/indexVMM.html', )
        except BaseException, msg:
            logging.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def createIPPool(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'createIPPool') == 0:
                return ACLManager.loadError()

            hvNames = vmmACLManager.findHyperVisorNames(currentACL, userID)

            data = {'hvNames': hvNames}
            return render(request, 'ipManagement/createIPPool.html', data)
        except BaseException, msg:
            logging.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def submitIPPoolCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                poolName = data['poolName']
                poolGateway = data['poolGateway']
                poolNetmask = data['poolNetmask']
                poolStartingIP = data['poolStartingIP']
                poolEndingIP = data['poolEndingIP']
                hvName = data['hvName']

                hv = HyberVisors.objects.get(hypervisorName=hvName)

                newIPPool = IPPool(poolName=poolName, gateway=poolGateway, netmask=poolNetmask, hv=hv)
                newIPPool.save()

                ## Adding IPs -- Getting 192.168.100. from 192.168.100.100

                index = poolStartingIP.rindex('.')
                ipValue = poolStartingIP[:index + 1]

                ## Calculating range and adding to database.

                startingValue = int(poolStartingIP.split('.')[-1])
                endingValue = int(poolEndingIP.split('.')[-1])

                for ips in range(startingValue, endingValue + 1):
                    newIPAddress = IPAddresses(pool=newIPPool, ipAddr=ipValue + str(ips))
                    newIPAddress.save()


                data_ret = {"success": 1, 'error_message': "None", 'successMessage' : 'Pool successfully created.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"success": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"success": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def listIPPools(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

            poolNames = []

            if admin.type == 1:
                ipPools = IPPool.objects.all()

            for pool in ipPools:
                poolNames.append(pool.poolName)


            return render(request, 'ipManagement/listIPPools.html', {'ipPools' : poolNames})
        except BaseException, msg:
            logging.writeToFile(str(msg), "Error", stack()[0][3])
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def fetchIPsInPool(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                poolName = data['poolName']

                pool = IPPool.objects.get(poolName=poolName)

                ipAddresses = pool.ipaddresses_set.all()

                json_data = "["
                checker = 0

                for ips in ipAddresses:

                    if ips.used == 0:
                        used = 'Not Assigned'
                    else:
                        vps = VPS.objects.get(ipAddr=ips)
                        used = vps.hostName

                    dic = {
                           'id': ips.id,
                           'ipAddr': ips.ipAddr,
                           'used': used,
                           'macAddress': ips.macAddress,
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'



                data_ret = {"success": 1, 'error_message': "None", 'successMessage' : 'Records successfully fetched.', "data" : json_data}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"success": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"success": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitNewMac(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                macIP = data['macIP']
                newMac = data['newMac']

                ip = IPAddresses.objects.get(ipAddr=macIP)
                ip.macAddress = newMac
                ip.save()


                data_ret = {"success": 1, 'error_message': "None", 'successMessage' : 'MAC Address successfully updated.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"success": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"success": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def deleteIP(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                id = data['id']

                ip = IPAddresses.objects.get(id=id)


                if ip.used == 0:
                    ip.delete()
                    data_ret = {"success": 1, 'error_message': "None",
                                'successMessage': 'IP Address successfully deleted.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {"success": 0, 'error_message': "IP is used by a VPS.",
                                }
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"success": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"success": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def deletePool(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                poolName = data['poolName']

                delPool = IPPool.objects.get(poolName=poolName)
                delPool.delete()

                data_ret = {"success": 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"success": 0,
                        'error_message': 'One or more IPs inside this pool is assigned to a VPS.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError, msg:
        data_ret = {"success": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def addSingleIP(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                poolName = data['poolName']
                newIP = data['newIP']

                relatedPool = IPPool.objects.get(poolName=poolName)

                newIPAddress = IPAddresses(pool=relatedPool, ipAddr=newIP)
                newIPAddress.save()

                data_ret = {"success": 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"success": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError, msg:
        data_ret = {"success": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def addMultipleIP(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                poolName = data['poolName']
                startingIP = data['startingIP']
                endingIP = data['endingIP']

                relatedPool = IPPool.objects.get(poolName=poolName)

                index = startingIP.rindex('.')
                ipValue = startingIP[:index + 1]

                ## Calculating range and adding to database.

                startingValue = int(startingIP.split('.')[-1])
                endingValue = int(endingIP.split('.')[-1])

                for ips in range(startingValue, endingValue + 1):
                    newIPAddress = IPAddresses(pool=relatedPool, ipAddr=ipValue + str(ips))
                    newIPAddress.save()

                data_ret = {"success": 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"success": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError, msg:
        data_ret = {"success": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
