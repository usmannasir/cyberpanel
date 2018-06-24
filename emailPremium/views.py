# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
from mailServer.models import Domains, EUsers
# Create your views here.
from loginSystem.models import Administrator
from websiteFunctions.models import Websites
from loginSystem.views import loadLoginPage
import plogical.CyberCPLogFileWriter as logging
import json
from .models import DomainLimits, EmailLimits, EmailLogs
from math import ceil
from postfixSenderPolicy.client import cacheClient


# Create your views here.

def listDomains(request):
    try:
        val = request.session['userID']

        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = Websites.objects.all()
            else:
                websites = Websites.objects.filter(admin=admin)


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


            return render(request,'emailPremium/listDomains.html',{"pagination":pagination})

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def getFurtherDomains(request):
    try:
        val = request.session['userID']

        try:

            admin = Administrator.objects.get(pk=request.session['userID'])

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                    status = data['page']
                    pageNumber = int(status)

                except BaseException, msg:
                    status = str(msg)


            if admin.type == 1:
                finalPageNumber = ((pageNumber * 10))-10
                endPageNumber = finalPageNumber + 10
                websites = Websites.objects.all()[finalPageNumber:endPageNumber]

            else:
                finalPageNumber = ((pageNumber * 10)) - 10
                endPageNumber = finalPageNumber + 10
                websites = Websites.objects.filter(admin=admin)[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0

            for items in websites:

                try:
                    domain = Domains.objects.get(domainOwner=items)
                    domainLimits = DomainLimits.objects.get(domain=domain)

                    dic = {'domain': items.domain, 'emails': domain.eusers_set.all().count(),
                           'monthlyLimit': domainLimits.monthlyLimit, 'monthlyUsed': domainLimits.monthlyUsed,
                           'status':domainLimits.limitStatus}

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data +',' + json.dumps(dic)
                except BaseException, msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg))

            json_data = json_data + ']'
            final_dic = {'listWebSiteStatus': 1, 'error_message': "None", "data": json_data}
            final_json = json.dumps(final_dic)


            return HttpResponse(final_json)

        except BaseException,msg:
            dic = {'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'listWebSiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def enableDisableEmailLimits(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                admin = Administrator.objects.get(pk=request.session['userID'])
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

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def emailLimits(request,domain):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)


        if Websites.objects.filter(domain=domain).exists():
            if admin.type == 1:
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


                return render(request, 'emailPremium/emailLimits.html', Data)
            else:
                return render(request, 'emailPremium/emailLimits.html',
                                {"error": 1, "domain": "You do not own this domain."})

        else:
            return render(request, 'emailPremium/emailLimits.html', {"error":1,"domain": "This domain does not exists"})
    except KeyError:
        return redirect(loadLoginPage)

def changeDomainLimit(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                admin = Administrator.objects.get(pk=request.session['userID'])
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

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def getFurtherEmail(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                admin = Administrator.objects.get(pk=request.session['userID'])
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
                               'hourlyUsed':emailLts.hourlyUsed,'status': emailLts.limitStatus}

                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data +',' + json.dumps(dic)
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(str(msg))

                json_data = json_data + ']'
                final_dic = {'status': 1, 'error_message': "None", "data": json_data}
                final_json = json.dumps(final_dic)


                return HttpResponse(final_json)

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def enableDisableIndividualEmailLimits(request):
    try:
        val = request.session['userID']
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

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError,msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def emailPage(request, emailAddress):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

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

        return render(request, 'emailPremium/emailPage.html', Data)
    except KeyError:
        return redirect(loadLoginPage)

def getEmailStats(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                admin = Administrator.objects.get(pk=request.session['userID'])
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

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def enableDisableIndividualEmailLogs(request):
    try:
        val = request.session['userID']
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

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError,msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def changeDomainEmailLimitsIndividual(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                admin = Administrator.objects.get(pk=request.session['userID'])
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
                    dic = {'status': 0, 'error_message': 'You can not set this monthly limit, first increase limits for this domain.'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                ## Limits Check End

                email = EUsers.objects.get(email=emailAddress)
                emailLTS = EmailLimits.objects.get(email=email)

                emailLTS.monthlyLimits = monthlyLimit
                emailLTS.hourlyLimit = hourlyLimit

                emailLTS.save()

                command = 'cyberpanelCleaner purgeLimitEmail ' + emailAddress + ' ' + str(monthlyLimit) + ' ' + str(hourlyLimit)
                cacheClient.handleCachePurgeRequest(command)

                dic = {'status': 1, 'error_message': 'None'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def getEmailLogs(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                admin = Administrator.objects.get(pk=request.session['userID'])
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

                    dic = {'id': item.id, 'source': emailAddress, 'destination':item.destination,
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

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def flushEmailLogs(request):
    try:
        val = request.session['userID']
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

        except BaseException,msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    except KeyError,msg:
        dic = {'statusa': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)