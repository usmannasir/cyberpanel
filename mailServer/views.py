# -*- coding: utf-8 -*-


from django.shortcuts import redirect
from django.http import HttpResponse
from loginSystem.views import loadLoginPage
import json
from .mailserverManager import MailServerManager
from .pluginManager import pluginManager

def loadEmailHome(request):
    try:
        msM = MailServerManager(request)
        return msM.loadEmailHome()
    except KeyError:
        return redirect(loadLoginPage)

def createEmailAccount(request):
    try:
        msM = MailServerManager(request)
        return msM.createEmailAccount()
    except KeyError:
        return redirect(loadLoginPage)

def listEmails(request):
    try:
        msM = MailServerManager(request)
        return msM.listEmails()
    except KeyError:
        return redirect(loadLoginPage)


def fetchEmails(request):
    try:
        msM = MailServerManager(request)
        return msM.fetchEmails()
    except KeyError:
        return redirect(loadLoginPage)

def submitEmailCreation(request):
    try:

        result = pluginManager.preSubmitEmailCreation(request)
        if result != 200:
            return result

        msM = MailServerManager(request)
        coreResult = msM.submitEmailCreation()

        result = pluginManager.postSubmitEmailCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def deleteEmailAccount(request):
    try:
        msM = MailServerManager(request)
        return msM.deleteEmailAccount()
    except KeyError:
        return redirect(loadLoginPage)

def getEmailsForDomain(request):
    try:
        msM = MailServerManager(request)
        return msM.getEmailsForDomain()
    except KeyError as msg:
        data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitEmailDeletion(request):
    try:

        result = pluginManager.preSubmitEmailDeletion(request)
        if result != 200:
            return result

        msM = MailServerManager(request)
        coreResult = msM.submitEmailDeletion()

        result = pluginManager.postSubmitEmailDeletion(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError as msg:
        data_ret = {'deleteEmailStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def emailForwarding(request):
    try:
        msM = MailServerManager(request)
        return msM.emailForwarding()
    except KeyError:
        return redirect(loadLoginPage)

def fetchCurrentForwardings(request):
    try:
        msM = MailServerManager(request)
        return msM.fetchCurrentForwardings()
    except KeyError as msg:
        data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitForwardDeletion(request):
    try:

        result = pluginManager.preSubmitForwardDeletion(request)
        if result != 200:
            return result

        msM = MailServerManager(request)
        coreResult = msM.submitForwardDeletion()

        result = pluginManager.postSubmitForwardDeletion(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError as msg:
        data_ret = {'deleteEmailStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitEmailForwardingCreation(request):
    try:

        result = pluginManager.preSubmitEmailForwardingCreation(request)
        if result != 200:
            return result

        msM = MailServerManager(request)
        coreResult = msM.submitEmailForwardingCreation()

        result = pluginManager.postSubmitEmailForwardingCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError as msg:
        data_ret = {'createStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

#######

def changeEmailAccountPassword(request):
    try:
        msM = MailServerManager(request)
        return msM.changeEmailAccountPassword()
    except KeyError:
        return redirect(loadLoginPage)

def submitPasswordChange(request):
    try:

        result = pluginManager.preSubmitPasswordChange(request)
        if result != 200:
            return result

        msM = MailServerManager(request)
        coreResult = msM.submitPasswordChange()

        result = pluginManager.postSubmitPasswordChange(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError as msg:
        data_ret = {'passChangeStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

#######

def dkimManager(request):
    try:
        msM = MailServerManager(request)
        return msM.dkimManager()
    except KeyError:
        return redirect(loadLoginPage)

def fetchDKIMKeys(request):
    try:
        msM = MailServerManager(request)
        return msM.fetchDKIMKeys()
    except KeyError as msg:
        data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def generateDKIMKeys(request):
    try:

        result = pluginManager.preGenerateDKIMKeys(request)
        if result != 200:
            return result

        msM = MailServerManager(request)
        coreResult = msM.generateDKIMKeys()

        result = pluginManager.postGenerateDKIMKeys(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except BaseException as msg:
        data_ret = {'generateStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def installOpenDKIM(request):
    try:
        msM = MailServerManager(request)
        return msM.installOpenDKIM()
    except KeyError:
        final_dic = {'installOpenDKIM': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def installStatusOpenDKIM(request):
    try:
        msM = MailServerManager()
        return msM.installStatusOpenDKIM()
    except KeyError:
        final_dic = {'abort':1,'installed':0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


