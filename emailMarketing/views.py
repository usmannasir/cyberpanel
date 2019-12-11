# -*- coding: utf-8 -*-

from django.shortcuts import redirect
from loginSystem.views import loadLoginPage
from .emailMarketingManager import EmailMarketingManager
# Create your views here.


def emailMarketing(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.emailMarketing()
    except KeyError:
        return redirect(loadLoginPage)

def fetchUsers(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.fetchUsers()
    except KeyError:
        return redirect(loadLoginPage)

def enableDisableMarketing(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.enableDisableMarketing()
    except KeyError:
        return redirect(loadLoginPage)

def createEmailList(request, domain):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request, domain)
        return emm.createEmailList()
    except KeyError:
        return redirect(loadLoginPage)

def submitEmailList(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.submitEmailList()
    except KeyError:
        return redirect(loadLoginPage)

def manageLists(request, domain):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request, domain)
        return emm.manageLists()
    except KeyError:
        return redirect(loadLoginPage)

def fetchEmails(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.fetchEmails()
    except KeyError:
        return redirect(loadLoginPage)

def deleteList(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.deleteList()
    except KeyError:
        return redirect(loadLoginPage)

def emailVerificationJob(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.emailVerificationJob()
    except KeyError:
        return redirect(loadLoginPage)

def deleteEmail(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.deleteEmail()
    except KeyError:
        return redirect(loadLoginPage)

def manageSMTP(request, domain):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request, domain)
        return emm.manageSMTP()
    except KeyError:
        return redirect(loadLoginPage)

def saveSMTPHost(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.saveSMTPHost()
    except KeyError:
        return redirect(loadLoginPage)

def fetchSMTPHosts(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.fetchSMTPHosts()
    except KeyError:
        return redirect(loadLoginPage)

def smtpHostOperations(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.smtpHostOperations()
    except KeyError:
        return redirect(loadLoginPage)

def composeEmailMessage(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.composeEmailMessage()
    except KeyError:
        return redirect(loadLoginPage)

def saveEmailTemplate(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.saveEmailTemplate()
    except KeyError:
        return redirect(loadLoginPage)

def sendEmails(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.sendEmails()
    except KeyError:
        return redirect(loadLoginPage)

def templatePreview(request, templateName):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request, templateName)
        return emm.templatePreview()
    except KeyError:
        return redirect(loadLoginPage)

def fetchJobs(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.fetchJobs()
    except KeyError:
        return redirect(loadLoginPage)

def startEmailJob(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.startEmailJob()
    except KeyError:
        return redirect(loadLoginPage)

def deleteTemplate(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.deleteTemplate()
    except KeyError:
        return redirect(loadLoginPage)

def deleteJob(request):
    try:
        userID = request.session['userID']
        emm = EmailMarketingManager(request)
        return emm.deleteJob()
    except KeyError:
        return redirect(loadLoginPage)


def remove(request, listName, emailAddress):
    try:
        emm = EmailMarketingManager(request)
        return emm.remove(listName, emailAddress)
    except KeyError:
        return redirect(loadLoginPage)