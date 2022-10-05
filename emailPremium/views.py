# -*- coding: utf-8 -*-
import os
import time

from django.shortcuts import redirect
from django.http import HttpResponse

from loginSystem.models import Administrator
from mailServer.models import Domains, EUsers
from plogical.applicationInstaller import ApplicationInstaller
from websiteFunctions.models import Websites
from loginSystem.views import loadLoginPage
import plogical.CyberCPLogFileWriter as logging
import json
from .models import DomainLimits, EmailLimits
from math import ceil
from postfixSenderPolicy.client import cacheClient
from plogical.mailUtilities import mailUtilities
from plogical.virtualHostUtilities import virtualHostUtilities
from random import randint
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities
from plogical.httpProc import httpProc
from cloudAPI.cloudManager import CloudManager


## Email Policy Server

def emailPolicyServer(request):
    proc = httpProc(request, 'emailPremium/policyServer.html',
                    None, 'admin')
    return proc.render()


def fetchPolicyServerStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                command = 'sudo cat /etc/postfix/main.cf'
                output = ProcessUtilities.outputExecutioner(command).split('\n')

                installCheck = 0

                for items in output:
                    if items.find('check_policy_service unix:/var/log/policyServerSocket') > -1:
                        installCheck = 1
                        break

                data_ret = {'status': 1, 'error_message': 'None', 'installCheck': installCheck}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def savePolicyServerStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                data = json.loads(request.body)

                policServerStatus = data['policServerStatus']

                install = '0'

                if policServerStatus == True:
                    install = "1"

                ## save configuration data

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " savePolicyServerStatus --install " + install
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'status': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'status': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


## Email Policy Server configs

def listDomains(request):
    websites = DomainLimits.objects.all()

    ## Check if Policy Server is installed.

    command = 'sudo cat /etc/postfix/main.cf'
    output = ProcessUtilities.outputExecutioner(command).split('\n')

    installCheck = 0

    for items in output:
        if items.find('check_policy_service unix:/var/log/policyServerSocket') > -1:
            installCheck = 1
            break

    if installCheck == 0:
        proc = httpProc(request, 'emailPremium/listDomains.html', {"installCheck": installCheck}, 'admin')
        return proc.render()

    ###

    pages = float(len(websites)) / float(10)
    pagination = []

    if pages <= 1.0:
        pages = 1
        pagination.append('<li><a href="\#"></a></li>')
    else:
        pages = ceil(pages)
        finalPages = int(pages) + 1

        for i in range(1, finalPages):
            pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

    proc = httpProc(request, 'emailPremium/listDomains.html',
                    {"pagination": pagination, "installCheck": installCheck}, 'admin')
    return proc.render()


def getFurtherDomains(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        try:

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                    status = data['page']
                    pageNumber = int(status)

                except BaseException as msg:
                    status = str(msg)

            finalPageNumber = ((pageNumber * 10)) - 10
            endPageNumber = finalPageNumber + 10
            websites = Websites.objects.all()[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0

            for items in websites:
                try:
                    domain = Domains.objects.get(domainOwner=items)
                    domainLimits = DomainLimits.objects.get(domain=domain)

                    dic = {'domain': items.domain, 'emails': domain.eusers_set.all().count(),
                           'monthlyLimit': domainLimits.monthlyLimit, 'monthlyUsed': domainLimits.monthlyUsed,
                           'status': domainLimits.limitStatus}

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)
                except BaseException as msg:
                    try:
                        domain = Domains.objects.get(domainOwner=items)
                    except:
                        domain = Domains(domainOwner=items, domain=items.domain)
                        domain.save()

                    domainLimits = DomainLimits(domain=domain)
                    domainLimits.save()

                    dic = {'domain': items.domain, 'emails': domain.eusers_set.all().count(),
                           'monthlyLimit': domainLimits.monthlyLimit, 'monthlyUsed': domainLimits.monthlyUsed,
                           'status': domainLimits.limitStatus}

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_dic = {'listWebSiteStatus': 1, 'error_message': "None", "data": json_data}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            dic = {'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError as msg:
        dic = {'listWebSiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def enableDisableEmailLimits(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                operationVal = data['operationVal']
                domainName = data['domainName']

                domain = Domains.objects.get(domain=domainName)

                domainLimits = DomainLimits.objects.get(domain=domain)
                domainLimits.limitStatus = operationVal
                domainLimits.save()

                command = 'cyberpanelCleaner purgeLimitDomain ' + domainName + ' ' + str(operationVal)
                cacheClient.handleCachePurgeRequest(command)

                dic = {'status': 1, 'error_message': 'None'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError as msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def emailLimits(request, domain):
    if Websites.objects.filter(domain=domain).exists():
        website = Websites.objects.get(domain=domain)
        domainEmail = Domains.objects.get(domainOwner=website)
        domainLimits = DomainLimits.objects.get(domain=domainEmail)

        Data = {}
        Data['domain'] = domain
        Data['monthlyLimit'] = domainLimits.monthlyLimit
        Data['monthlyUsed'] = domainLimits.monthlyUsed
        Data['emailAccounts'] = domainEmail.eusers_set.count()

        if domainLimits.limitStatus == 1:
            Data['limitsOn'] = 1
            Data['limitsOff'] = 0
        else:
            Data['limitsOn'] = 0
            Data['limitsOff'] = 1

        ## Pagination for emails

        pages = float(Data['emailAccounts']) / float(10)
        pagination = []

        if pages <= 1.0:
            pages = 1
            pagination.append('<li><a href="\#"></a></li>')
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

        Data['pagination'] = pagination

        proc = httpProc(request, 'emailPremium/emailLimits.html', Data, 'admin')
        return proc.render()
    else:
        proc = httpProc(request, 'emailPremium/emailLimits.html', {"error": 1, "domain": "This domain does not exists"},
                        'admin')
        return proc.render()


def changeDomainLimit(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                newLimit = data['newLimit']
                domainName = data['domainName']

                domain = Domains.objects.get(domain=domainName)

                domainLimits = DomainLimits.objects.get(domain=domain)
                domainLimits.monthlyLimit = newLimit
                domainLimits.save()

                command = 'cyberpanelCleaner updateDomainLimit ' + domainName + ' ' + str(newLimit)
                cacheClient.handleCachePurgeRequest(command)

                dic = {'status': 1, 'error_message': 'None'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError as msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def getFurtherEmail(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                status = data['page']
                domainName = data['domainName']
                pageNumber = int(status)

                finalPageNumber = ((pageNumber * 10)) - 10
                endPageNumber = finalPageNumber + 10
                domain = Domains.objects.get(domain=domainName)
                emails = domain.eusers_set.all()[finalPageNumber:endPageNumber]

                json_data = "["
                checker = 0

                for item in emails:

                    try:
                        emailLts = EmailLimits.objects.get(email=item)

                        dic = {'email': item.email, 'monthlyLimit': emailLts.monthlyLimits,
                               'monthlyUsed': emailLts.monthlyUsed, 'hourlyLimit': emailLts.hourlyLimit,
                               'hourlyUsed': emailLts.hourlyUsed, 'status': emailLts.limitStatus}

                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)
                    except BaseException as msg:
                        logging.CyberCPLogFileWriter.writeToFile(str(msg))

                json_data = json_data + ']'
                final_dic = {'status': 1, 'error_message': "None", "data": json_data}
                final_json = json.dumps(final_dic)

                return HttpResponse(final_json)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def enableDisableIndividualEmailLimits(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                operationVal = data['operationVal']
                emailAddress = data['emailAddress']

                email = EUsers.objects.get(email=emailAddress)
                emailtLts = EmailLimits.objects.get(email=email)
                emailtLts.limitStatus = operationVal
                emailtLts.save()

                command = 'cyberpanelCleaner purgeLimit ' + emailAddress + ' ' + str(operationVal)
                cacheClient.handleCachePurgeRequest(command)

                dic = {'status': 1, 'error_message': 'None'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError as msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def emailPage(request, emailAddress):
    Data = {}
    Data['emailAddress'] = emailAddress

    email = EUsers.objects.get(email=emailAddress)
    logEntries = email.emaillogs_set.all().count()

    pages = float(logEntries) / float(10)
    pagination = []

    if pages <= 1.0:
        pages = 1
        pagination.append('<li><a href="\#"></a></li>')
    else:
        pages = ceil(pages)
        finalPages = int(pages) + 1

        for i in range(1, finalPages):
            pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

    Data['pagination'] = pagination

    proc = httpProc(request, 'emailPremium/emailPage.html', Data, 'admin')
    return proc.render()


def getEmailStats(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                emailAddress = data['emailAddress']

                email = EUsers.objects.get(email=emailAddress)
                emailLTS = EmailLimits.objects.get(email=email)

                final_dic = {'status': 1, 'error_message': "None", "monthlyLimit": emailLTS.monthlyLimits,
                             'monthlyUsed': emailLTS.monthlyUsed, 'hourlyLimit': emailLTS.hourlyLimit,
                             'hourlyUsed': emailLTS.hourlyUsed,
                             'limitStatus': emailLTS.limitStatus, 'logsStatus': emailLTS.emailLogs}

                final_json = json.dumps(final_dic)

                return HttpResponse(final_json)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def enableDisableIndividualEmailLogs(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                operationVal = data['operationVal']
                emailAddress = data['emailAddress']

                email = EUsers.objects.get(email=emailAddress)
                emailtLts = EmailLimits.objects.get(email=email)
                emailtLts.emailLogs = operationVal
                emailtLts.save()

                command = 'cyberpanelCleaner purgeLog ' + emailAddress + ' ' + str(operationVal)
                cacheClient.handleCachePurgeRequest(command)

                dic = {'status': 1, 'error_message': 'None'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError as msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def changeDomainEmailLimitsIndividual(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                emailAddress = data['emailAddress']
                monthlyLimit = data['monthlyLimit']
                hourlyLimit = data['hourlyLimit']

                ## Limits Check

                if monthlyLimit < hourlyLimit:
                    dic = {'status': 0, 'error_message': 'Monthly limit should be greater then hourly limit.'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                domainName = emailAddress.split('@')[1]
                dbDomain = Domains.objects.get(domain=domainName)

                domainLimit = DomainLimits.objects.get(domain=dbDomain)

                allEmails = dbDomain.eusers_set.all()
                currentEmailConsumption = 0

                for email in allEmails:
                    emailLTS = EmailLimits.objects.get(email=email)
                    currentEmailConsumption = emailLTS.monthlyLimits + currentEmailConsumption

                allowedLimit = domainLimit.monthlyLimit - currentEmailConsumption

                if monthlyLimit > allowedLimit:
                    dic = {'status': 0,
                           'error_message': 'You can not set this monthly limit, first increase limits for this domain.'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                ## Limits Check End

                email = EUsers.objects.get(email=emailAddress)
                emailLTS = EmailLimits.objects.get(email=email)

                emailLTS.monthlyLimits = monthlyLimit
                emailLTS.hourlyLimit = hourlyLimit

                emailLTS.save()

                command = 'cyberpanelCleaner purgeLimitEmail ' + emailAddress + ' ' + str(monthlyLimit) + ' ' + str(
                    hourlyLimit)
                cacheClient.handleCachePurgeRequest(command)

                dic = {'status': 1, 'error_message': 'None'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError as msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def getEmailLogs(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                status = data['page']
                emailAddress = data['emailAddress']
                pageNumber = int(status)

                finalPageNumber = ((pageNumber * 10)) - 10
                endPageNumber = finalPageNumber + 10
                email = EUsers.objects.get(email=emailAddress)
                logEntries = email.emaillogs_set.all()[finalPageNumber:endPageNumber]

                json_data = "["
                checker = 0

                for item in logEntries:

                    dic = {'id': item.id, 'source': emailAddress, 'destination': item.destination,
                           'time': item.timeStamp}

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_dic = {'status': 1, 'error_message': "None", "data": json_data}
                final_json = json.dumps(final_dic)

                return HttpResponse(final_json)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def flushEmailLogs(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                emailAddress = data['emailAddress']

                email = EUsers.objects.get(email=emailAddress)

                for logEntry in email.emaillogs_set.all():
                    logEntry.delete()

                dic = {'status': 1, 'error_message': 'None'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError as msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


### SpamAssassin

def spamAssassinHome(request):
    checkIfSpamAssassinInstalled = 0

    if mailUtilities.checkIfSpamAssassinInstalled() == 1:
        checkIfSpamAssassinInstalled = 1

    proc = httpProc(request, 'emailPremium/SpamAssassin.html',
                    {'checkIfSpamAssassinInstalled': checkIfSpamAssassinInstalled}, 'admin')
    return proc.render()


def installSpamAssassin(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
            execPath = execPath + " installSpamAssassin"
            ProcessUtilities.popenExecutioner(execPath)

            final_json = json.dumps({'status': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def installStatusSpamAssassin(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                command = "sudo cat " + mailUtilities.spamassassinInstallLogPath
                installStatus = ProcessUtilities.outputExecutioner(command)

                if installStatus.find("[200]") > -1:

                    execPath = "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin  && /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                    execPath = execPath + " configureSpamAssassin"
                    output = ProcessUtilities.outputExecutioner(execPath, 'root')

                    if output.find("1,None") > -1:

                        import os
                        if os.path.exists(mailUtilities.mailScannerInstallLogPath):
                            os.remove(mailUtilities.mailScannerInstallLogPath)

                        final_json = json.dumps({
                            'error_message': "None",
                            'requestStatus': installStatus,
                            'abort': 1,
                            'installed': 1,
                        })
                        return HttpResponse(final_json)
                    else:
                        final_json = json.dumps({
                            'error_message': "Failed to install SpamAssassin configurations.",
                            'requestStatus': installStatus,
                            'abort': 1,
                            'installed': 0,
                        })
                        return HttpResponse(final_json)

                elif installStatus.find("[404]") > -1:

                    final_json = json.dumps({
                        'abort': 1,
                        'installed': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    return HttpResponse(final_json)

                else:
                    final_json = json.dumps({
                        'abort': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'abort': 1, 'installed': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abort': 1, 'installed': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def fetchSpamAssassinSettings(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        try:
            if request.method == 'POST':

                report_safe = 0
                required_hits = '5.0'
                rewrite_header = 'Subject [SPAM]'
                required_score = '5'

                confPath = "/etc/mail/spamassassin/local.cf"

                if mailUtilities.checkIfSpamAssassinInstalled() == 1:

                    command = "sudo cat " + confPath

                    data = ProcessUtilities.outputExecutioner(command).splitlines()

                    # logging.CyberCPLogFileWriter.writeToFile(str(data))

                    for items in data:
                        if items.find('report_safe ') > -1:
                            if items.find('0') > -1:
                                report_safe = 0
                                continue
                            else:
                                report_safe = 1
                        if items.find('rewrite_header ') > -1:
                            tempData = items.split(' ')
                            rewrite_header = ''
                            counter = 0
                            for headerData in tempData:
                                if counter == 0:
                                    counter = counter + 1
                                    continue
                                rewrite_header = rewrite_header + headerData.strip('\n') + ' '
                            continue
                        if items.find('required_score ') > -1:
                            required_score = items.split(' ')[1].strip('\n')
                            continue
                        if items.find('required_hits ') > -1:
                            required_hits = items.split(' ')[1].strip('\n')
                            continue

                    final_dic = {'fetchStatus': 1,
                                 'installed': 1,
                                 'report_safe': report_safe,
                                 'rewrite_header': rewrite_header,
                                 'required_score': required_score,
                                 'required_hits': required_hits,
                                 }

                else:
                    final_dic = {'fetchStatus': 1,
                                 'installed': 0}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        return redirect(loadLoginPage)


def saveSpamAssassinConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('saveStatus', 0)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)

                report_safe = data['report_safe']
                required_hits = data['required_hits']
                rewrite_header = data['rewrite_header']
                required_score = data['required_score']

                if report_safe == True:
                    report_safe = "report_safe 1"
                else:
                    report_safe = "report_safe 0"

                required_hits = "required_hits " + required_hits
                rewrite_header = "rewrite_header " + rewrite_header
                required_score = "required_score " + required_score

                ## writing data temporary to file

                tempConfigPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                confPath = open(tempConfigPath, "w")

                confPath.writelines(report_safe + "\n")
                confPath.writelines(required_hits + "\n")
                confPath.writelines(rewrite_header + "\n")
                confPath.writelines(required_score + "\n")

                confPath.close()

                ## save configuration data

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " saveSpamAssassinConfigs --tempConfigPath " + tempConfigPath
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'saveStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'saveStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def mailQueue(request):
    proc = httpProc(request, 'emailPremium/mailQueue.html',
                    None, 'admin')
    return proc.render()


def fetchMailQueue(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)

        json_data = "["
        checker = 0

        queues = ProcessUtilities.outputExecutioner('postqueue -j').split('\n')

        for queue in queues:
            if checker == 0:
                json_data = json_data + queue
                checker = 1
            else:
                json_data = json_data + ',' + queue

        json_data = json_data.rstrip(',') + ']'
        final_dic = {'status': 1, 'error_message': "None", "data": json_data}
        final_json = json.dumps(final_dic)

        return HttpResponse(final_json)


    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def fetchMessage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:

            data = json.loads(request.body)
            id = data['id']

            command = 'postcat -vq %s' % (id)
            emailMessageContent = ProcessUtilities.outputExecutioner(command)

            dic = {'status': 1, 'error_message': 'None', 'emailMessageContent': emailMessageContent}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def flushQueue(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:

            command = 'postqueue -f'
            ProcessUtilities.executioner(command)

            dic = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def delete(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:

            data = json.loads(request.body)
            type = data['type']

            if type == 'all':
                command = 'postsuper -d ALL'
            else:
                command = 'postsuper -d ALL deferred'

            ProcessUtilities.executioner(command)

            dic = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


## MailScanner

def MailScanner(request):
    checkIfMailScannerInstalled = 0

    ipFile = "/etc/cyberpanel/machineIP"
    f = open(ipFile)
    ipData = f.read()
    ipAddress = ipData.split('\n', 1)[0]

    if mailUtilities.checkIfMailScannerInstalled() == 1:
        checkIfMailScannerInstalled = 1

    proc = httpProc(request, 'emailPremium/MailScanner.html',
                    {'checkIfMailScannerInstalled': checkIfMailScannerInstalled, 'ipAddress': ipAddress}, 'admin')
    return proc.render()


def installMailScanner(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:

            ### Check selinux

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sestatus'
                result = ProcessUtilities.outputExecutioner(command)

                if result.find('disabled') == -1:
                    final_json = json.dumps(
                        {'status': 0, 'error_message': "Disable selinux before installing MailScanner."})
                    return HttpResponse(final_json)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
            execPath = execPath + " installMailScanner"
            ProcessUtilities.popenExecutioner(execPath)

            final_json = json.dumps({'status': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def installStatusMailScanner(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        try:
            if request.method == 'POST':

                command = "sudo cat " + mailUtilities.mailScannerInstallLogPath
                installStatus = ProcessUtilities.outputExecutioner(command)

                if installStatus.find("[200]") > -1:

                    final_json = json.dumps({
                        'error_message': "None",
                        'requestStatus': installStatus,
                        'abort': 1,
                        'installed': 1,
                    })
                    return HttpResponse(final_json)

                elif installStatus.find("[404]") > -1:

                    final_json = json.dumps({
                        'abort': 1,
                        'installed': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    return HttpResponse(final_json)

                else:
                    final_json = json.dumps({
                        'abort': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'abort': 1, 'installed': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abort': 1, 'installed': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


###Rspamd

def Rspamd(request):
    url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
    data = {
        "name": "email-debugger",
        "IP": ACLManager.GetServerIP()
    }

    import requests
    response = requests.post(url, data=json.dumps(data))
    Status = response.json()['status']

    if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
        checkIfRspamdInstalled = 0

        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        if mailUtilities.checkIfRspamdInstalled() == 1:
            checkIfRspamdInstalled = 1

        proc = httpProc(request, 'emailPremium/Rspamd.html',
                        {'checkIfRspamdInstalled': checkIfRspamdInstalled, 'ipAddress': ipAddress}, 'admin')
        return proc.render()
    else:
        return redirect("https://cyberpanel.net/cyberpanel-addons")

def installRspamd(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "email-debugger",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
            try:

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " installRspamd"
                ProcessUtilities.popenExecutioner(execPath)

                final_json = json.dumps({'status': 1, 'error_message': "None"})
                return HttpResponse(final_json)
            except BaseException as msg:
                final_dic = {'status': 0, 'error_message': str(msg)}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
    except KeyError:
        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def installStatusRspamd(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                command = "sudo cat " + mailUtilities.RspamdInstallLogPath
                installStatus = ProcessUtilities.outputExecutioner(command)

                if installStatus.find("[200]") > -1:

                    final_json = json.dumps({
                        'error_message': "None",
                        'requestStatus': installStatus,
                        'abort': 1,
                        'installed': 1,
                    })
                    cmd = 'rm -f %s'%mailUtilities.RspamdInstallLogPath
                    ProcessUtilities.executioner(cmd)
                    return HttpResponse(final_json)


                elif installStatus.find("[404]") > -1:

                    final_json = json.dumps({
                        'abort': 1,
                        'installed': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    cmd = 'rm -f %s' % mailUtilities.RspamdInstallLogPath
                    ProcessUtilities.executioner(cmd)
                    return HttpResponse(final_json)

                else:
                    final_json = json.dumps({
                        'abort': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'abort': 1, 'installed': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abort': 1, 'installed': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def fetchRspamdSettings(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "email-debugger",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
            try:
                if request.method == 'POST':

                    enabled = True
                    action = ''
                    max_Size = ''
                    scan_mime_parts = True
                    log_clean = True
                    Server = ''
                    CLAMAV_VIRUS = ''

                    confPath = "/etc/rspamd/local.d/antivirus.conf"
                    postfixpath = "/etc/postfix/main.cf"

                    if mailUtilities.checkIfRspamdInstalled() == 1:

                        command = "sudo cat " + confPath

                        data = ProcessUtilities.outputExecutioner(command).splitlines()

                        for items in data:
                            if items.find('enabled ') > -1:
                                if items.find('enabled = true') < 0:
                                    enabled = False
                                    continue
                                else:
                                    enabled = True
                            if items.find('action =') > -1:
                                tempData = items.split(' ')
                                # logging.CyberCPLogFileWriter.writeToFile(str(tempData) + "action")
                                try:
                                    a = tempData[4]
                                except:
                                    a = tempData[2]
                                ac = a.split('"')
                                action = ac[1]
                            if items.find('max_size') > -1:
                                tempData = items.split(' ')
                                max = tempData[4]
                                max_Size = max.rstrip(";")

                            if items.find('scan_mime_parts ') > -1:
                                if items.find('scan_mime_parts = true') < 0:
                                    scan_mime_parts = False
                                    continue
                                else:
                                    scan_mime_parts = True
                            if items.find('log_clean  ') > -1:
                                if items.find('scan_mime_parts = true') < 0:
                                    log_clean = False
                                    continue
                                else:
                                    log_clean = True
                            if items.find('servers =') > -1:
                                tempData = items.split(' ')
                                Ser = tempData[4]
                                x = Ser.rstrip(";")
                                y = x.split('"')
                                Server = y[1]
                            if items.find('CLAMAV_VIRUS =') > -1:
                                tempData = items.split(' ')
                                CLAMAV = tempData[6]
                                i = CLAMAV.rstrip(";")
                                j = i.split('"')
                                CLAMAV_VIRUS = j[1]

                        ###postfix
                        smtpd_milters = ""
                        non_smtpd_milters = ""
                        command = "sudo cat " + postfixpath

                        postdata = ProcessUtilities.outputExecutioner(command).splitlines()
                        for i in postdata:
                            if i.find('smtpd_milters=') > -1 and i.find('non_smtpd_milters') < 0:
                                tempData = i.split(' ')
                                x = tempData[0]
                                y = x.split('=')
                                smtpd_milters = y[1]
                            if i.find('non_smtpd_milters=') > -1:
                                tempData = i.split(' ')
                                x = tempData[0]
                                y = x.split('=')
                                non_smtpd_milters = y[1]

                        ###Redis
                        Redispath = "/etc/rspamd/local.d/redis.conf"
                        read_servers = ''
                        write_servers = ''
                        command = "sudo cat " + Redispath

                        postdata = ProcessUtilities.outputExecutioner(command).splitlines()

                        for i in postdata:
                            if i.find('write_servers =') > -1:
                                tempData = i.split(' ')
                                # logging.CyberCPLogFileWriter.writeToFile(str(tempData) + "redis")
                                write = tempData[2]
                                i = write.rstrip(";")
                                j = i.split('"')
                                write_servers = j[1]
                                # logging.CyberCPLogFileWriter.writeToFile(str(write_servers) + "write_servers")

                            if i.find('read_servers =') > -1:
                                tempData = i.split(' ')
                                # logging.CyberCPLogFileWriter.writeToFile(str(tempData) + "redis2")
                                read = tempData[2]
                                i = read.rstrip(";")
                                j = i.split('"')
                                read_servers = j[1]
                                # logging.CyberCPLogFileWriter.writeToFile(str(read_servers) + "read_servers")

                        #ClamAV configs

                        clamav_Debug = True
                        LogFile = ''
                        TCPAddr = ''
                        TCPSocket = ''

                        if  ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                            clamavconfpath = '/etc/clamd.d/scan.conf'
                        elif ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                            clamavconfpath = "/etc/clamav/clamd.conf"

                        command = "sudo cat " + clamavconfpath
                        data = ProcessUtilities.outputExecutioner(command).splitlines()
                        for items in data:
                            if items.find('TCPSocket') > -1:
                                tempData = items.split(' ')
                                TCPSocket = tempData[1]
                            if items.find('TCPAddr') > -1:
                                tempData = items.split(' ')
                                TCPAddr = tempData[1]
                            if items.find('LogFile') > -1:
                                tempData = items.split(' ')
                                LogFile = tempData[1]
                            if items.find('Debug') > -1:
                                if items.find('Debug true') < 0:
                                    clamav_Debug = False
                                    continue
                                else:
                                    clamav_Debug = True


                        final_dic = {'fetchStatus': 1,
                                     'installed': 1,
                                     'enabled': enabled,
                                     'action': action,
                                     'max_Size': max_Size,
                                     'scan_mime_parts': scan_mime_parts,
                                     'log_clean ': log_clean,
                                     'Server': Server,
                                     'CLAMAV_VIRUS': CLAMAV_VIRUS,
                                     'smtpd_milters': smtpd_milters,
                                     'non_smtpd_milters': non_smtpd_milters,
                                     'read_servers': read_servers,
                                     'write_servers': write_servers,
                                     'clamav_Debug': clamav_Debug,
                                     'LogFile': LogFile,
                                     'TCPAddr': TCPAddr,
                                     'TCPSocket': TCPSocket,

                                     }


                    else:
                        final_dic = {'fetchStatus': 1,
                                     'installed': 0}

                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            except BaseException as msg:
                final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
    except KeyError:
        return redirect(loadLoginPage)

def saveRspamdConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('saveStatus', 0)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                tempfilepath = "/home/cyberpanel/tempfilerspamdconfigs"
                json_object = json.dumps(data, indent=4)
                writeDataToFile = open(tempfilepath, "w")
                writeDataToFile.write(json_object)
                writeDataToFile.close()

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " changeRspamdConfig "
                output = ProcessUtilities.outputExecutioner(execPath)

                data_ret = {'saveStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)

def savepostfixConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('saveStatus', 0)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                tempfilepath = "/home/cyberpanel/tempfilepostfixconfigs"
                json_object = json.dumps(data, indent=4)
                writeDataToFile = open(tempfilepath, "w")
                writeDataToFile.write(json_object)
                writeDataToFile.close()

                # status, msg = mailUtilities.changeRspamdConfig(request.body)
                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " changePostfixConfig "
                output = ProcessUtilities.outputExecutioner(execPath)

                data_ret = {'saveStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)

def saveRedisConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('saveStatus', 0)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                tempfilepath = "/home/cyberpanel/saveRedisConfigurations"
                json_object = json.dumps(data, indent=4)
                writeDataToFile = open(tempfilepath, "w")
                writeDataToFile.write(json_object)
                writeDataToFile.close()

                # status, msg = mailUtilities.changeRspamdConfig(request.body)
                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " changeRedisxConfig "
                output = ProcessUtilities.outputExecutioner(execPath)

                data_ret = {'saveStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)

def saveclamavConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('saveStatus', 0)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                tempfilepath = "/home/cyberpanel/saveclamavConfigurations"
                json_object = json.dumps(data, indent=4)
                writeDataToFile = open(tempfilepath, "w")
                writeDataToFile.write(json_object)
                writeDataToFile.close()

                # status, msg = mailUtilities.changeRspamdConfig(request.body)
                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " changeclamavConfig"
                output = ProcessUtilities.outputExecutioner(execPath)

                data_ret = {'saveStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        return redirect(loadLoginPage)

def unistallRspamd(request):
    try:
        logging.CyberCPLogFileWriter.writeToFile("unistallRspamd...1")
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()


        try:

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
            execPath = execPath + " uninstallRspamd"
            ProcessUtilities.popenExecutioner(execPath)


            final_json = json.dumps({'status': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)


    except KeyError:

        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}

        final_json = json.dumps(final_dic)

        return HttpResponse(final_json)

def uninstallStatusRspamd(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                command = "sudo cat " + mailUtilities.RspamdUnInstallLogPath
                installStatus = ProcessUtilities.outputExecutioner(command)

                if installStatus.find("[200]") > -1:

                    final_json = json.dumps({
                        'error_message': "None",
                        'requestStatus': installStatus,
                        'abort': 1,
                        'installed': 1,
                    })
                    cmd = 'rm -f %s' % mailUtilities.RspamdUnInstallLogPath
                    ProcessUtilities.executioner(cmd)
                    return HttpResponse(final_json)


                elif installStatus.find("[404]") > -1:

                    final_json = json.dumps({
                        'abort': 1,
                        'installed': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    cmd = 'rm -f %s' % mailUtilities.RspamdUnInstallLogPath
                    ProcessUtilities.executioner(cmd)
                    return HttpResponse(final_json)

                else:
                    final_json = json.dumps({
                        'abort': 0,
                        'error_message': "None",
                        'requestStatus': installStatus,
                    })
                    return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'abort': 1, 'installed': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abort': 1, 'installed': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def FetchRspamdLog(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        fileName = "/var/log/rspamd/rspamd.log"
        try:
            command = "sudo tail -100 " + fileName
            fewLinesOfLogFile = ProcessUtilities.outputExecutioner(command)
            status = {"status": 1, "logstatus": 1, "logsdata": fewLinesOfLogFile}
            final_json = json.dumps(status)
            return HttpResponse(final_json)
        except:
            status = {"status": 1, "logstatus": 1, "logsdata": 'Emtpy File.'}
            final_json = json.dumps(status)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abort': 1, 'installed': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def RestartRspamd(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            command = "systemctl restart rspamd"
            ProcessUtilities.executioner(command)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'systemctl start clamd@scan'
            else:
                command = "systemctl restart clamav-daemon"

            ProcessUtilities.executioner(command)

            dic = {'status': 1, 'error_message': 'None',}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except KeyError:
        dic = {'status': 0, 'error_message': str("Not Logged In, please refresh the page or login again.")}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


##Email Debugger

def EmailDebugger(request):
    url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
    data = {
        "name": "email-debugger",
        "IP": ACLManager.GetServerIP()
    }

    import requests
    response = requests.post(url, data=json.dumps(data))
    Status = response.json()['status']

    if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)

        proc = httpProc(request, 'emailPremium/EmailDebugger.html',
                        {'websiteList': websitesName}, 'admin')
        return proc.render()
    else:
        return redirect("https://cyberpanel.net/cyberpanel-addons")

def RunServerLevelEmailChecks(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        if ACLManager.CheckForPremFeature('email-debugger'):
            ob = CloudManager()
            res = ob.RunServerLevelEmailChecks()
            return res
        else:
            dic = {'status': 0, 'error_message': 'Kindly purchase email debugger Add-on'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


def ResetEmailConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        if ACLManager.CheckForPremFeature('email-debugger'):
            ob = CloudManager()
            res = ob.ResetEmailConfigurations()
            return res
        else:
            dic = {'status': 0, 'error_message': 'Kindly purchase email debugger Add-on'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def statusFunc(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        if ACLManager.CheckForPremFeature('email-debugger'):
            ob = CloudManager(json.loads(request.body))
            res = ob.statusFunc()
            return res
        else:
            dic = {'status': 0, 'error_message': 'Kindly purchase email debugger Add-on'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def ReadReport(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        if ACLManager.CheckForPremFeature('email-debugger'):
            try:
                ob = CloudManager(json.loads(request.body))
                res = ob.ReadReport()
                Result = json.loads(res.content)
                status = Result['status']
                #fetch Ip
                IP = ACLManager.GetServerIP()
                if status == 1:
                    def CheckPort(port):
                        import socket
                        # Create a TCP socket
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            s.settimeout(1)
                            s.connect((IP, port))
                            return 1
                        except socket.error as e:
                            return 0
                        finally:
                            s.close()

                    report = {}

                    if CheckPort(25):
                        report['Port25'] = 'Open'
                    else:
                        report['Port25'] = 'Closed, mail will not go through.'

                    if CheckPort(587):
                        report['Port587'] = 'Open'
                    else:
                        report['Port587'] = 'Closed, mail will not go through.'

                    if CheckPort(465):
                        report['Port465'] = 'Open'
                    else:
                        report['Port465'] = 'Closed, mail will not go through.'

                    if CheckPort(110):
                        report['Port110'] = 'Open'
                    else:
                        report['Port110'] = 'Closed, POP3 will not work.'

                    if CheckPort(143):
                        report['Port143'] = 'Open'
                    else:
                        report['Port143'] = 'Closed, IMAP will not work.'

                    if CheckPort(993):
                        report['Port993'] = 'Open'
                    else:
                        report['Port993'] = 'Closed, IMAP will not work.'

                    if CheckPort(995):
                        report['Port995'] = 'Open'
                    else:
                        report['Port995'] = 'Closed, POP3 will not work.'

                    report['serverHostName'] = IP
                    finalResult = Result
                    finalResult['report'] = report

                    final_json = json.dumps(finalResult)
                    return HttpResponse(final_json)
                else:
                    return 0 , Result
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile("Result....3:" + str(msg))
        else:
            dic = {'status': 0, 'error_message': 'Kindly purchase email debugger Add-on'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except KeyError:
        return redirect(loadLoginPage)

def debugEmailForSite(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        if ACLManager.CheckForPremFeature('email-debugger'):
            ob = CloudManager(json.loads(request.body))
            res = ob.debugEmailForSite()
            return res
        else:
            dic = {'status': 0, 'error_message': 'Kindly purchase email debugger Add-on'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except KeyError:
        return redirect(loadLoginPage)

def fixMailSSL(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        admin = Administrator.objects.get(pk=userID)
        if ACLManager.CheckForPremFeature('email-debugger'):
            cm = CloudManager(json.loads(request.body), admin)
            res = cm.fixMailSSL(request)
            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile("Result....3:" + str(res.content))
            return res
        else:
            dic = {'status': 0, 'error_message': 'Kindly purchase email debugger Add-on'}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except KeyError:
        return redirect(loadLoginPage)
