# -*- coding: utf-8 -*-


from django.shortcuts import render,redirect
from django.http import HttpResponse
from mailServer.models import Domains, EUsers
# Create your views here.
from loginSystem.models import Administrator
from websiteFunctions.models import Websites
from loginSystem.views import loadLoginPage
import plogical.CyberCPLogFileWriter as logging
import json
from .models import DomainLimits, EmailLimits
from math import ceil
from postfixSenderPolicy.client import cacheClient
import _thread
from plogical.mailUtilities import mailUtilities
from plogical.virtualHostUtilities import virtualHostUtilities
from random import randint
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities

# Create your views here.

## Email Policy Server

def emailPolicyServer(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        return render(request, 'emailPremium/policyServer.html')

    except KeyError:
        return redirect(loadLoginPage)

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


                data_ret = {'status': 1, 'error_message': 'None', 'installCheck' : installCheck}
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
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        try:
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
                return render(request, 'emailPremium/listDomains.html', {"installCheck": installCheck})

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


            return render(request,'emailPremium/listDomains.html',{"pagination":pagination, "installCheck": installCheck})

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

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
                           'status':domainLimits.limitStatus}

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data +',' + json.dumps(dic)
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

def emailLimits(request,domain):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()


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

            return render(request, 'emailPremium/emailLimits.html', Data)
        else:
            return render(request, 'emailPremium/emailLimits.html', {"error":1,"domain": "This domain does not exists"})
    except KeyError:
        return redirect(loadLoginPage)

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
                               'hourlyUsed':emailLts.hourlyUsed,'status': emailLts.limitStatus}

                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data +',' + json.dumps(dic)
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
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

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
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        checkIfSpamAssassinInstalled = 0

        if mailUtilities.checkIfSpamAssassinInstalled() == 1:
            checkIfSpamAssassinInstalled = 1

        return render(request, 'emailPremium/SpamAssassin.html',{'checkIfSpamAssassinInstalled': checkIfSpamAssassinInstalled})

    except KeyError:
        return redirect(loadLoginPage)

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

                if installStatus.find("[200]")>-1:

                    execPath = "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin  && /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                    execPath = execPath + " configureSpamAssassin"
                    output = ProcessUtilities.outputExecutioner(execPath)

                    if output.find("1,None") > -1:
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
                                             'abort':1,
                                             'installed':0,
                                             'error_message': "None",
                                             'requestStatus': installStatus,
                                             })
                    return HttpResponse(final_json)

                else:
                    final_json = json.dumps({
                                             'abort':0,
                                             'error_message': "None",
                                             'requestStatus': installStatus,
                                             })
                    return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'abort':1,'installed':0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abort':1,'installed':0, 'error_message': "Not Logged In, please refresh the page or login again."}
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


        return render(request,'managePHP/editPHPConfig.html')
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
