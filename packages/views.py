# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
from loginSystem.views import loadLoginPage
from loginSystem.models import Administrator
import json
from .models import Package
import plogical.CyberCPLogFileWriter as logging

# Create your views here.


def packagesHome(request):
    try:
        val = request.session['userID']
    except KeyError:
        return redirect(loadLoginPage)

    return render(request,'packages/index.html',{})



def createPacakge(request):

    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

    except KeyError:
        return redirect(loadLoginPage)

    return render(request,'packages/createPackage.html',{"admin":admin.userName})


def deletePacakge(request):

    try:
        val = request.session['userID']
        try:

            admin = Administrator.objects.get(pk=val)

            if admin.type == 1:
                packages = Package.objects.all()
            else:
                packages = Package.objects.filter(admin=admin)

            packageList = []
            for items in packages:
                packageList.append(items.packageName)

        except BaseException,msg:
            logging.writeToFile(str(msg))
            return HttpResponse("Please see CyberCP Main Log File")

    except KeyError:
        return redirect(loadLoginPage)

    return render(request,'packages/deletePackage.html',{"packageList" : packageList})



def submitPackage(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                packageName = data['packageName']
                packageSpace = int(data['diskSpace'])
                packageBandwidth = int(data['bandwidth'])
                packageDatabases = int(data['dataBases'])
                ftpAccounts = int(data['ftpAccounts'])
                emails = int(data['emails'])


                admin = Administrator.objects.get(pk=request.session['userID'])

                packageName = admin.userName+"_"+packageName

                package = Package(admin=admin, packageName=packageName, diskSpace=packageSpace,
                                  bandwidth=packageBandwidth, ftpAccounts=ftpAccounts, dataBases=packageDatabases,emailAccounts=emails)

                package.save()

                data_ret = {'saveStatus': 1,'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        return redirect(loadLoginPage)



def submitDelete(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                packageName = data['packageName']

                delPackage = Package.objects.get(packageName=packageName)
                delPackage.delete()

                data_ret = {'deleteStatus': 1,'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'deleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def modifyPackage(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

            if admin.type == 1:
                packages = Package.objects.all()
            else:
                packages = Package.objects.filter(admin=admin)

            packageList = []
            for items in packages:
                packageList.append(items.packageName)

        except BaseException,msg:
            logging.writeToFile(str(msg))
            return HttpResponse("Please see CyberCP Main Log File")

    except KeyError:
        packages = Package.objects.all()

        packageList = []
        for items in packages:
            packageList.append(items.packageName)
        return render(request,'packages/modifyPackage.html',{"packList" : packageList})

    return render(request,'packages/modifyPackage.html',{"packList" : packageList})


def submitModify(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                packageName = data['packageName']

                modifyPack = Package.objects.get(packageName=packageName)

                diskSpace = modifyPack.diskSpace
                bandwidth = modifyPack.bandwidth
                ftpAccounts = modifyPack.ftpAccounts
                dataBases = modifyPack.dataBases
                emails = modifyPack.emailAccounts

                data_ret = {'emails':emails,'modifyStatus': 1,'error_message': "None",
                            "diskSpace":diskSpace,"bandwidth":bandwidth,"ftpAccounts":ftpAccounts,"dataBases":dataBases}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'modifyStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        data_ret = {'modifyStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def saveChanges(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                packageName = data['packageName']

                modifyPack = Package.objects.get(packageName=packageName)

                modifyPack.diskSpace = data['diskSpace']
                modifyPack.bandwidth = data['bandwidth']
                modifyPack.ftpAccounts = data['ftpAccounts']
                modifyPack.dataBases = data['dataBases']
                modifyPack.emailAccounts = data['emails']
                modifyPack.save()

                data_ret = {'saveStatus': 1,'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        data_ret = {'saveStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
