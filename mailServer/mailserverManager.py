#!/usr/local/CyberCP/bin/python
# coding=utf-8
import os.path
import sys
import django
from plogical.httpProc import httpProc
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.http import HttpResponse
try:
    from .models import Domains,EUsers
    from loginSystem.views import loadLoginPage
except:
    pass
import plogical.CyberCPLogFileWriter as logging
import json
import shlex
import subprocess
try:
    from plogical.virtualHostUtilities import virtualHostUtilities
    from plogical.mailUtilities import mailUtilities
except:
    pass
import _thread
try:
    from dns.models import Domains as dnsDomains
    from dns.models import Records as dnsRecords
    from mailServer.models import Forwardings, Pipeprograms
    from plogical.acl import ACLManager
    from plogical.dnsUtilities import DNS
    from loginSystem.models import Administrator
    from websiteFunctions.models import Websites
except:
    pass
import os
from plogical.processUtilities import ProcessUtilities
import bcrypt
import threading as multi
import argparse

class MailServerManager(multi.Thread):

    def __init__(self, request = None, function = None, extraArgs = None):
        multi.Thread.__init__(self)
        self.request = request
        self.function = function
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.function == 'RunServerLevelEmailChecks':
                self.RunServerLevelEmailChecks()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [MailServerManager.run]')

    def loadEmailHome(self):
        proc = httpProc(self.request, 'mailServer/index.html',
                        None, 'createEmail')
        return proc.render()

    def createEmailAccount(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/postfix'):
            proc = httpProc(self.request, 'mailServer/createEmailAccount.html',
                            {"status": 0}, 'createEmail')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)
        websitesName = websitesName + ACLManager.findChildDomains(websitesName)

        proc = httpProc(self.request, 'mailServer/createEmailAccount.html',
                        {'websiteList': websitesName, "status": 1}, 'createEmail')
        return proc.render()

    def listEmails(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/postfix'):
            proc = httpProc(self.request, 'mailServer/listEmails.html',
                            {"status": 0}, 'listEmails')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)
        websitesName = websitesName + ACLManager.findChildDomains(websitesName)

        proc = httpProc(self.request, 'mailServer/listEmails.html',
                        {'websiteList': websitesName, "status": 1}, 'listEmails')
        return proc.render()

    def submitEmailCreation(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createEmail') == 0:
                return ACLManager.loadErrorJson('createEmailStatus', 0)

            data = json.loads(self.request.body)
            domainName = data['domain']
            userName = data['username'].lower()
            password = data['passwordByPass']


            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()


            ## Create email entry

            result = mailUtilities.createEmailAccount(domainName, userName.lower(), password)

            if result[0] == 1:
                data_ret = {'status': 1, 'createEmailStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            else:
                data_ret = {'status': 0, 'createEmailStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'createEmailStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteEmailAccount(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/postfix'):
            proc = httpProc(self.request, 'mailServer/deleteEmailAccount.html',
                            {"status": 0}, 'deleteEmail')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)
        websitesName = websitesName + ACLManager.findChildDomains(websitesName)

        proc = httpProc(self.request, 'mailServer/deleteEmailAccount.html',
                        {'websiteList': websitesName, "status": 1}, 'deleteEmail')
        return proc.render()

    def getEmailsForDomain(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteEmail') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            domain = data['domain']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            try:
                domain = Domains.objects.get(domain=domain)
            except:
                final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': "No email accounts exists!"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            emails = domain.eusers_set.all()

            if emails.count() == 0:
                final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': "No email accounts exists!"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            json_data = "["
            checker = 0
            count = 1
            for items in emails:
                dic = {'id': count, 'email': items.email, 'DiskUsage': '%sMB' % items.DiskUsage}
                count = count + 1

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_dic = {'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)

        except BaseException as msg:
            data_ret = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitEmailDeletion(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteEmail') == 0:
                return ACLManager.loadErrorJson('deleteEmailStatus', 0)

            data = json.loads(self.request.body)
            email = data['email']

            eUser = EUsers.objects.get(email=email)

            emailOwnerDomain = eUser.emailOwner

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(eUser.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            mailUtilities.deleteEmailAccount(email)

            if emailOwnerDomain.eusers_set.all().count() == 0:
                emailOwnerDomain.delete()

            data_ret = {'status': 1, 'deleteEmailStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'deleteEmailStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fixMailSSL(self, data = None):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if data == None:
                data = json.loads(self.request.body)
                selectedDomain = data['selectedDomain']
            else:
                selectedDomain = data['websiteName']


            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(selectedDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            website = Websites.objects.get(domain=selectedDomain)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = '%s setupAutoDiscover --virtualHostName %s --websiteOwner %s' % (execPath, selectedDomain, website.admin.userName)

            ProcessUtilities.executioner(execPath)

            data_ret = {'status': 1,  'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def emailForwarding(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/postfix'):
            proc = httpProc(self.request, 'mailServer/emailForwarding.html',
                            {"status": 0}, 'emailForwarding')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)
        websitesName = websitesName + ACLManager.findChildDomains(websitesName)

        proc = httpProc(self.request, 'mailServer/emailForwarding.html',
                        {'websiteList': websitesName, "status": 1}, 'emailForwarding')
        return proc.render()

    def fetchCurrentForwardings(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'emailForwarding') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            emailAddress = data['emailAddress']
            forwardingOption = data['forwardingOption']

            if forwardingOption != "Pipe to program":
                eUser = EUsers.objects.get(email=emailAddress)

                admin = Administrator.objects.get(pk=userID)
                if ACLManager.checkOwnership(eUser.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                currentForwardings = Forwardings.objects.filter(source=emailAddress)

                json_data = "["
                checker = 0
                id = 1
                for items in currentForwardings:
                    if items.source == items.destination:
                        continue
                    dic = {'id': id,
                           'source': items.source,
                           'destination': items.destination}

                    id = id + 1

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_dic = {'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data}
                final_json = json.dumps(final_dic)

                return HttpResponse(final_json)
            else:

                currentForwardings = Pipeprograms.objects.filter(source=emailAddress)

                json_data = "["
                checker = 0
                id = 1
                for items in currentForwardings:
                    if items.source == items.destination:
                        continue
                    dic = {'id': id,
                           'source': items.source,
                           'destination': items.destination}

                    id = id + 1

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_dic = {'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data}
                final_json = json.dumps(final_dic)

                return HttpResponse(final_json)


        except BaseException as msg:
            data_ret = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitForwardDeletion(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'emailForwarding') == 0:
                return ACLManager.loadErrorJson('deleteForwardingStatus', 0)

            data = json.loads(self.request.body)
            destination = data['destination']
            source = data['source']
            forwardingOption = data['forwardingOption']

            eUser = EUsers.objects.get(email=source)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(eUser.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if forwardingOption == 'Forward to email':
                for items in Forwardings.objects.filter(destination=destination, source=source):
                    items.delete()
            else:
                for items in Pipeprograms.objects.filter(destination=destination, source=source):
                    items.delete()

                    ## Delete Email PIPE
                    sourceusername = source.split("@")[0]
                    virtualfilter = '%s FILTER %spipe:dummy' % (source, sourceusername)
                    command = "sed -i 's/^" + source + ".*//g' /etc/postfix/script_filter"
                    ProcessUtilities.executioner(command)
                    command = "sed -i 's/^" + sourceusername + "pipe.*//g' /etc/postfix/master.cf"
                    ProcessUtilities.executioner(command)

                    #### Hashing filter Reloading Postfix
                    command = "postmap /etc/postfix/script_filter"
                    ProcessUtilities.executioner(command)
                    command = "postfix reload"
                    ProcessUtilities.executioner(command)
                    ##


            data_ret = {'status': 1, 'deleteForwardingStatus': 1, 'error_message': "None",
                        'successMessage': 'Successfully deleted!'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'deleteForwardingStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitEmailForwardingCreation(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'emailForwarding') == 0:
                return ACLManager.loadErrorJson('createStatus', 0)

            data = json.loads(self.request.body)
            source = data['source']
            destination = data['destination']
            forwardingOption = data['forwardingOption']

            eUser = EUsers.objects.get(email=source)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(eUser.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if Forwardings.objects.filter(source=source, destination=destination).count() > 0:
                data_ret = {'status': 0, 'createStatus': 0,
                            'error_message': "You have already forwarded to this destination."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if forwardingOption == 'Forward to email':
                if Forwardings.objects.filter(source=source).count() == 0:
                    forwarding = Forwardings(source=source, destination=source)
                    forwarding.save()

                forwarding = Forwardings(source=source, destination=destination)
                forwarding.save()
            else:
                forwarding = Pipeprograms(source=source, destination=destination)
                forwarding.save()

                ## Create Email PIPE filter
                ## example@domain.com FILTER support:dummy
                sourceusername = source.split("@")[0]
                virtualfilter = '%s FILTER %spipe:dummy' % (source, sourceusername)
                command = "echo '" + virtualfilter + "' >> /etc/postfix/script_filter"
                ProcessUtilities.executioner(command)

                ## support unix - n n - - pipe flags=Rq user=domain argv=/usr/bin/php -q /home/domain.com/public_html/ticket/api/pipe.php
                ## Find Unix file owner of provided pipe
                domainName = source.split("@")[1]
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
                pipeowner = externalApp
                ## Add Filter pipe to postfix /etc/postfix/master.cf
                filterpipe = '%spipe unix - n n - - pipe flags=Rq user=%s  argv=%s -f  $(sender) -- $(recipient)' % (sourceusername, pipeowner, destination)
                command = "echo '" + filterpipe + "' >> /etc/postfix/master.cf"
                ProcessUtilities.executioner(command)
                ## Add Check Recipient Hash to postfix /etc/postfix/main.cf
                command = "sed -i 's|^smtpd_recipient_restrictions =.*|smtpd_recipient_restrictions = permit_mynetworks, permit_sasl_authenticated, reject_unauth_destination, check_recipient_access hash:/etc/postfix/script_filter, permit|' /etc/postfix/main.cf"
                ProcessUtilities.executioner(command)

                #### Hashing filter Reloading Postfix
                command = "postmap /etc/postfix/script_filter"
                ProcessUtilities.executioner(command)
                command = "postfix reload"
                ProcessUtilities.executioner(command)
                ##



            data_ret = {'status': 1, 'createStatus': 1, 'error_message': "None", 'successMessage': 'Successfully Created!'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'createStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchEmails(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listEmails') == 0:
                return ACLManager.loadErrorJson('status', 0)

            data = json.loads(self.request.body)
            selectedDomain = data['selectedDomain']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(selectedDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()
            try:

                emailDomain = Domains.objects.get(domain=selectedDomain)
            except:
                raise BaseException('No emails exist for this domain.')

            postfixMapPath = '/etc/postfix/vmail_ssl.map'

            if os.path.exists(postfixMapPath):

                postfixMapData = open(postfixMapPath, 'r').read()

                if postfixMapData.find(selectedDomain) == -1:
                    mailConfigured = 0
                else:
                    mailConfigured = 1
            else:
                mailConfigured = 0

            records = emailDomain.eusers_set.all()

            json_data = "["
            checker = 0

            for items in records:
                dic = {'email': items.email,
                       'DiskUsage': '%sMB' % items.DiskUsage
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'fetchStatus': 1,'serverHostname': 'mail.%s' % (selectedDomain), 'mailConfigured': mailConfigured, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    #######

    def changeEmailAccountPassword(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/postfix'):
            proc = httpProc(self.request, 'mailServer/changeEmailPassword.html',
                            {"status": 0}, 'changeEmailPassword')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)
        websitesName = websitesName + ACLManager.findChildDomains(websitesName)

        proc = httpProc(self.request, 'mailServer/changeEmailPassword.html',
                        {'websiteList': websitesName, "status": 1}, 'changeEmailPassword')
        return proc.render()

    def submitPasswordChange(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'changeEmailPassword') == 0:
                return ACLManager.loadErrorJson('passChangeStatus', 0)

            data = json.loads(self.request.body)
            email = data['email']
            password = data['passwordByPass']

            emailDB = EUsers.objects.get(email=email)

            admin = Administrator.objects.get(pk=userID)
            try:
                if ACLManager.checkOwnership(emailDB.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()
            except:
                if ACLManager.checkOwnership(emailDB.emailOwner.childOwner.domain, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

            CentOSPath = '/etc/redhat-release'
            if os.path.exists(CentOSPath):
                password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                password = '{CRYPT}%s' % (password.decode())
                emailDB.password = password
            else:
                password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                password = '{CRYPT}%s' % (password.decode())
                emailDB.password = password

            emailDB.save()


            data_ret = {'status': 1, 'passChangeStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'passChangeStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    #######

    def dkimManager(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        openDKIMInstalled = 1

        websitesName = ACLManager.findAllSites(currentACL, userID)
        websitesName = websitesName + ACLManager.findChildDomains(websitesName)

        proc = httpProc(self.request, 'mailServer/dkimManager.html',
                        {'websiteList': websitesName, 'openDKIMInstalled': openDKIMInstalled}, 'dkimManager')
        return proc.render()

    def fetchDKIMKeys(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'dkimManager') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            domainName = data['domainName']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            try:

                command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.6/site-packages/tldextract/.suffix_cache'
                ProcessUtilities.executioner(command)

                command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
                ProcessUtilities.executioner(command)

                import tldextract

                extractDomain = tldextract.extract(domainName)
                domainName = extractDomain.domain + '.' + extractDomain.suffix

                path = "/etc/opendkim/keys/" + domainName + "/default.txt"
                command = "sudo cat " + path
                output = ProcessUtilities.outputExecutioner(command, 'opendkim')
                leftIndex = output.index('(') + 2
                rightIndex = output.rindex(')') - 1

                path = "/etc/opendkim/keys/" + domainName + "/default.private"
                command = "sudo cat " + path
                privateKey = ProcessUtilities.outputExecutioner(command, 'opendkim')

                DNS.createDKIMRecords(domainName)

                data_ret = {'status': 1, 'fetchStatus': 1, 'keysAvailable': 1, 'publicKey': output[leftIndex:rightIndex],
                            'privateKey': privateKey, 'dkimSuccessMessage': 'Keys successfully fetched!',
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            except BaseException as msg:
                data_ret = {'status': 1, 'fetchStatus': 1, 'keysAvailable': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def generateDKIMKeys(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'dkimManager') == 0:
                return ACLManager.loadErrorJson('generateStatus', 0)

            data = json.loads(self.request.body)
            domainName = data['domainName']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
            execPath = execPath + " generateKeys --domain " + domainName
            output = ProcessUtilities.outputExecutioner(execPath)

            admin = Administrator.objects.get(pk=userID)
            DNS.dnsTemplate(domainName, admin)

            if output.find("1,None") > -1:

                command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.6/site-packages/tldextract/.suffix_cache'
                ProcessUtilities.executioner(command)

                command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
                ProcessUtilities.executioner(command)

                import tldextract

                extractDomain = tldextract.extract(domainName)
                topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix

                zone = dnsDomains.objects.get(name=topLevelDomain)
                zone.save()

                path = "/etc/opendkim/keys/" + domainName + "/default.txt"
                command = "cat " + path
                output = ProcessUtilities.outputExecutioner(command)
                leftIndex = output.index('(') + 2
                rightIndex = output.rindex(')') - 1

                DNS.createDKIMRecords(domainName)

                record = dnsRecords(domainOwner=zone,
                                    domain_id=zone.id,
                                    name="default._domainkey." + domainName,
                                    type="TXT",
                                    content=output[leftIndex:rightIndex],
                                    ttl=3600,
                                    prio=0,
                                    disabled=0,
                                    auth=1)
                record.save()

                data_ret = {'status': 1, 'generateStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            else:
                data_ret = {'status': 0, 'generateStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'generateStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installOpenDKIM(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'dkimManager') == 0:
                return ACLManager.loadErrorJson('installOpenDKIM', 0)
            _thread.start_new_thread(mailUtilities.installOpenDKIM, ('Install', 'openDKIM'))
            final_json = json.dumps({'installOpenDKIM': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'installOpenDKIM': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installStatusOpenDKIM(self):
        try:
            command = "sudo cat " + mailUtilities.installLogPath
            installStatus = subprocess.check_output(shlex.split(command)).decode("utf-8")

            if installStatus.find("[200]") > -1:

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
                execPath = execPath + " configureOpenDKIM"

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    pass
                else:
                    final_json = json.dumps({
                        'error_message': "Failed to install OpenDKIM configurations.",
                        'requestStatus': installStatus,
                        'abort': 1,
                        'installed': 0,
                    })
                    return HttpResponse(final_json)

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

    #######

    def checkIfMailServerSSLIssued(self):
        postfixPath = '/etc/postfix/main.cf'

        postFixData = ProcessUtilities.outputExecutioner('cat %s' % (postfixPath))

        if postFixData.find('myhostname = server.example.com') > -1:
            return 0
        else:
            try:

                postFixLines = ProcessUtilities.outputExecutioner('cat %s' % (postfixPath)).splitlines()

                for items in postFixLines:
                    if items.find('myhostname') > -1 and items[0] != '#':
                        self.mailHostName = items.split('=')[1].strip(' ')
                        self.MailSSL = 1
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile('%s. [checkIfMailServerSSLIssued:864]' % (str(msg)))

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            command = 'openssl s_client -connect %s:465' % (ipAddress)
            result = ProcessUtilities.outputExecutioner(command)

            if result.find('18 (self signed certificate)') > -1:
                return 0
            else:
                return 1

    def RunServerLevelEmailChecks(self):
        try:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Checking if MailServer SSL issued..,10')

            reportFile = self.extraArgs['reportFile']

            report = {}
            report['MailSSL'] = self.checkIfMailServerSSLIssued()

            writeToFile = open(reportFile, 'w')
            writeToFile.write(json.dumps(report))
            writeToFile.close()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Completed [200].')

        except BaseException as msg:
            final_dic = {'installOpenDKIM': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def install_postfix_dovecot(self):
        try:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'yum remove postfix -y'
                ProcessUtilities.executioner(command)
            elif ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                command = 'apt-get -y remove postfix'
                ProcessUtilities.executioner(command)

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Re-installing postfix..,10')

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'yum install --enablerepo=gf-plus -y postfix3 postfix3-ldap postfix3-mysql postfix3-pcre'
            elif ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

                command = 'dnf --nogpg install -y https://mirror.ghettoforge.org/distributions/gf/el/8/gf/x86_64/gf-release-8-11.gf.el8.noarch.rpm'
                ProcessUtilities.executioner(command)

                command = 'dnf install --enablerepo=gf-plus postfix3 postfix3-mysql -y'
                ProcessUtilities.executioner(command)
            else:
                command = 'apt-get install -y debconf-utils'
                ProcessUtilities.executioner(command)
                file_name = 'pf.unattend.text'
                pf = open(file_name, 'w')
                pf.write('postfix postfix/mailname string ' + str(socket.getfqdn() + '\n'))
                pf.write('postfix postfix/main_mailer_type string "Internet Site"\n')
                pf.close()
                command = 'debconf-set-selections ' + file_name
                ProcessUtilities.executioner(command)

                command = 'apt-get -y install postfix'
                # os.remove(file_name)

            ProcessUtilities.executioner(command)
            
            import socket
            # We are going to leverage postconfig -e to edit the settings for hostname
            command = '"postconf -e "myhostname = %s"' % (str(socket.getfqdn()))
            ProcessUtilities.executioner(command)
            command = '"postconf -e "myhostname = %s"' % (str(socket.getfqdn()))
            ProcessUtilities.executioner(command)

            # We are explicitly going to use sed to set the hostname default from "myhostname = server.example.com"
            # to the fqdn from socket if the default is still found
            postfix_main = '/etc/postfix/main.cf'
            command = "sed -i 's|server.example.com|%s|g' %s" % (str(socket.getfqdn()), postfix_main)
            ProcessUtilities.executioner(command)
            
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Re-installing Dovecot..,15')

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                pass
            else:
                command = 'apt-get -y install dovecot-imapd dovecot-pop3d postfix-mysql'

            ProcessUtilities.executioner(command)

            ##

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'yum --enablerepo=gf-plus -y install dovecot23 dovecot23-mysql'
            elif ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'dnf install --enablerepo=gf-plus dovecot23 dovecot23-mysql -y'
            else:
                command = 'apt-get -y install dovecot-mysql'

            ProcessUtilities.executioner(command)

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:

                command = 'curl https://repo.dovecot.org/DOVECOT-REPO-GPG | gpg --import'
                subprocess.call(command, shell=True)

                command = 'gpg --export ED409DA1 > /etc/apt/trusted.gpg.d/dovecot.gpg'
                subprocess.call(command, shell=True)

                debPath = '/etc/apt/sources.list.d/dovecot.list'
                writeToFile = open(debPath, 'w')
                writeToFile.write('deb https://repo.dovecot.org/ce-2.3-latest/ubuntu/bionic bionic main\n')
                writeToFile.close()

                try:
                    command = 'apt update -y'
                    subprocess.call(command, shell=True)
                except:
                    pass

                try:
                    command = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical sudo apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" --only-upgrade install dovecot-mysql -y'
                    subprocess.call(command, shell=True)

                    command = 'dpkg --configure -a'
                    subprocess.call(command, shell=True)

                    command = 'apt --fix-broken install -y'
                    subprocess.call(command, shell=True)

                    command = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical sudo apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" --only-upgrade install dovecot-mysql -y'
                    subprocess.call(command, shell=True)
                except:
                    pass

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Postfix/dovecot reinstalled.,40')

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], '%s [install_postfix_dovecot][404]' % (str(msg)), 10)
            return 0

        return 1

    def setup_email_Passwords(self, mysqlPassword):
        try:


            mysql_virtual_domains = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_email2email.cf"
            dovecotmysql = "/usr/local/CyberCP/install/email-configs-one/dovecot-sql.conf.ext"

            ### update password:

            data = open(dovecotmysql, "r").readlines()

            writeDataToFile = open(dovecotmysql, "w")

            dataWritten = "connect = host=localhost dbname=cyberpanel user=cyberpanel password=" + mysqlPassword + " port=3306\n"

            for items in data:
                if items.find("connect") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_domains, "r").readlines()

            writeDataToFile = open(mysql_virtual_domains, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_forwardings, "r").readlines()

            writeDataToFile = open(mysql_virtual_forwardings, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_mailboxes, "r").readlines()

            writeDataToFile = open(mysql_virtual_mailboxes, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_email2email, "r").readlines()

            writeDataToFile = open(mysql_virtual_email2email, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            if self.remotemysql == 'ON':
                command = "sed -i 's|host=localhost|host=%s|g' %s" % (self.mysqlhost, dovecotmysql)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|port=3306|port=%s|g' %s" % (self.mysqlport, dovecotmysql)
                ProcessUtilities.executioner(command)

                ##

                command = "sed -i 's|localhost|%s:%s|g' %s" % (self.mysqlhost, self.mysqlport, mysql_virtual_domains)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_forwardings)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_mailboxes)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_email2email)
                ProcessUtilities.executioner(command)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '%s [setup_email_Passwords][404]' % (str(msg)), 10)
            return 0

        return 1

    def centos_lib_dir_to_ubuntu(self, filename, old, new):
        try:
            fd = open(filename, 'r')
            lines = fd.readlines()
            fd.close()
            fd = open(filename, 'w')
            centos_prefix = old
            ubuntu_prefix = new
            for line in lines:
                index = line.find(centos_prefix)
                if index != -1:
                    line = line[:index] + ubuntu_prefix + line[index + len(centos_prefix):]
                fd.write(line)
            fd.close()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '%s [centos_lib_dir_to_ubuntu][404]' % (str(msg)), 10)

    def setup_postfix_dovecot_config(self):
        try:

            mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
            main = "/etc/postfix/main.cf"
            master = "/etc/postfix/master.cf"
            dovecot = "/etc/dovecot/dovecot.conf"
            dovecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"

            if os.path.exists(mysql_virtual_domains):
                os.remove(mysql_virtual_domains)

            if os.path.exists(mysql_virtual_forwardings):
                os.remove(mysql_virtual_forwardings)

            if os.path.exists(mysql_virtual_mailboxes):
                os.remove(mysql_virtual_mailboxes)

            if os.path.exists(mysql_virtual_email2email):
                os.remove(mysql_virtual_email2email)

            if os.path.exists(main):
                os.remove(main)

            if os.path.exists(master):
                os.remove(master)

            if os.path.exists(dovecot):
                os.remove(dovecot)

            if os.path.exists(dovecotmysql):
                os.remove(dovecotmysql)

            ###############Getting SSL

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/postfix/key.pem -out /etc/postfix/cert.pem'
            ProcessUtilities.executioner(command)

            ##

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/dovecot/key.pem -out /etc/dovecot/cert.pem'
            ProcessUtilities.executioner(command)

            # Cleanup config files for ubuntu
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                self.centos_lib_dir_to_ubuntu("/usr/local/CyberCP/install/email-configs-one/master.cf", "/usr/libexec/", "/usr/lib/")
                self.centos_lib_dir_to_ubuntu("/usr/local/CyberCP/install/email-configs-one/main.cf", "/usr/libexec/postfix",
                                              "/usr/lib/postfix/sbin")


            ########### Copy config files
            import shutil

            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_domains.cf", "/etc/postfix/mysql-virtual_domains.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_forwardings.cf",
                        "/etc/postfix/mysql-virtual_forwardings.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_mailboxes.cf", "/etc/postfix/mysql-virtual_mailboxes.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_email2email.cf",
                        "/etc/postfix/mysql-virtual_email2email.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/main.cf", main)
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/master.cf", master)
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/dovecot.conf", dovecot)
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/dovecot-sql.conf.ext", dovecotmysql)


            ######################################## Permissions

            command = 'chmod o= /etc/postfix/mysql-virtual_domains.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_forwardings.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_mailboxes.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_email2email.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= ' + main
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= ' + master
            ProcessUtilities.executioner(command)

            #######################################

            command = 'chgrp postfix /etc/postfix/mysql-virtual_domains.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_forwardings.cf'
            ProcessUtilities.executioner(command)
            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_mailboxes.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_email2email.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix ' + main
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix ' + master
            ProcessUtilities.executioner(command)

            ######################################## users and groups

            command = 'groupadd -g 5000 vmail'
            ProcessUtilities.executioner(command)

            ##

            command = 'useradd -g vmail -u 5000 vmail -d /home/vmail -m'
            ProcessUtilities.executioner(command)

            ######################################## Further configurations

            # hostname = socket.gethostname()

            ################################### Restart postix

            command = 'systemctl enable postfix.service'
            ProcessUtilities.executioner(command)

            ##

            command = 'systemctl start postfix.service'
            ProcessUtilities.executioner(command)

            ######################################## Permissions

            command = 'chgrp dovecot /etc/dovecot/dovecot-sql.conf.ext'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/dovecot/dovecot-sql.conf.ext'
            ProcessUtilities.executioner(command)

            ################################### Restart dovecot

            command = 'systemctl enable dovecot.service'
            ProcessUtilities.executioner(command)

            ##

            command = 'systemctl start dovecot.service'
            ProcessUtilities.executioner(command)

            ##

            command = 'systemctl restart  postfix.service'
            ProcessUtilities.executioner(command)

            ## changing permissions for main.cf

            command = "chmod 755 " + main
            ProcessUtilities.executioner(command)

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                command = "mkdir -p /etc/pki/dovecot/private/"
                ProcessUtilities.executioner(command)

                command = "mkdir -p /etc/pki/dovecot/certs/"
                ProcessUtilities.executioner(command)

                command = "mkdir -p /etc/opendkim/keys/"
                ProcessUtilities.executioner(command)

                command = "sed -i 's/auth_mechanisms = plain/#auth_mechanisms = plain/g' /etc/dovecot/conf.d/10-auth.conf"
                ProcessUtilities.executioner(command)

                ## Ubuntu 18.10 ssl_dh for dovecot 2.3.2.1

                if ProcessUtilities.ubuntu:
                    dovecotConf = '/etc/dovecot/dovecot.conf'

                    data = open(dovecotConf, 'r').readlines()
                    writeToFile = open(dovecotConf, 'w')
                    for items in data:
                        if items.find('ssl_key = <key.pem') > -1:
                            writeToFile.writelines(items)
                            writeToFile.writelines('ssl_dh = </usr/share/dovecot/dh.pem\n')
                        else:
                            writeToFile.writelines(items)
                    writeToFile.close()

                command = "systemctl restart dovecot"
                ProcessUtilities.executioner(command)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '%s [setup_postfix_dovecot_config][404]' % (
                                                          str(msg)), 10)
            return 0

        return 1

    def configureOpenDKIM(self):
        try:

            ## Configure OpenDKIM specific settings

            openDKIMConfigurePath = "/etc/opendkim.conf"

            configData = """
Mode	sv
Canonicalization	relaxed/simple
KeyTable	refile:/etc/opendkim/KeyTable
SigningTable	refile:/etc/opendkim/SigningTable
ExternalIgnoreList	refile:/etc/opendkim/TrustedHosts
InternalHosts	refile:/etc/opendkim/TrustedHosts
"""

            writeToFile = open(openDKIMConfigurePath, 'a')
            writeToFile.write(configData)
            writeToFile.close()

            ## Configure postfix specific settings

            postfixFilePath = "/etc/postfix/main.cf"

            configData = """
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = $smtpd_milters
milter_default_action = accept
"""

            writeToFile = open(postfixFilePath, 'a')
            writeToFile.write(configData)
            writeToFile.close()

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                data = open(openDKIMConfigurePath, 'r').readlines()
                writeToFile = open(openDKIMConfigurePath, 'w')
                for items in data:
                    if items.find('Socket') > -1 and items.find('local:') and items[0] != '#':
                        writeToFile.writelines('Socket  inet:8891@localhost\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

            #### Restarting Postfix and OpenDKIM

            command = "systemctl start opendkim"
            ProcessUtilities.executioner(command)

            command = "systemctl enable opendkim"
            ProcessUtilities.executioner(command)

            ##

            command = "systemctl restart postfix"
            ProcessUtilities.executioner(command)

            return 1

        except BaseException as msg:
            return 0

    def fixCyberPanelPermissions(self):

        ###### fix Core CyberPanel permissions
        command = "find /usr/local/CyberCP -type d -exec chmod 0755 {} \;"
        ProcessUtilities.executioner(command)

        command = "find /usr/local/CyberCP -type f -exec chmod 0644 {} \;"
        ProcessUtilities.executioner(command)

        command = "chmod -R 755 /usr/local/CyberCP/bin"
        ProcessUtilities.executioner(command)

        ## change owner

        command = "chown -R root:root /usr/local/CyberCP"
        ProcessUtilities.executioner(command)

        ########### Fix LSCPD

        command = "find /usr/local/lscp -type d -exec chmod 0755 {} \;"
        ProcessUtilities.executioner(command)

        command = "find /usr/local/lscp -type f -exec chmod 0644 {} \;"
        ProcessUtilities.executioner(command)

        command = "chmod -R 755 /usr/local/lscp/bin"
        ProcessUtilities.executioner(command)

        command = "chmod -R 755 /usr/local/lscp/fcgi-bin"
        ProcessUtilities.executioner(command)

        command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp"
        ProcessUtilities.executioner(command)

        ## change owner

        command = "chown -R root:root /usr/local/lscp"
        ProcessUtilities.executioner(command)

        command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/data"
        ProcessUtilities.executioner(command)

        command = "chmod 700 /usr/local/CyberCP/cli/cyberPanel.py"
        ProcessUtilities.executioner(command)

        command = "chmod 700 /usr/local/CyberCP/plogical/upgradeCritical.py"
        ProcessUtilities.executioner(command)

        command = "chmod 755 /usr/local/CyberCP/postfixSenderPolicy/client.py"
        ProcessUtilities.executioner(command)

        command = "chmod 640 /usr/local/CyberCP/CyberCP/settings.py"
        ProcessUtilities.executioner(command)

        command = "chown root:cyberpanel /usr/local/CyberCP/CyberCP/settings.py"
        ProcessUtilities.executioner(command)

        files = ['/etc/yum.repos.d/MariaDB.repo', '/etc/pdns/pdns.conf', '/etc/systemd/system/lscpd.service',
                 '/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                 '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                 '/etc/dovecot/dovecot.conf', '/usr/local/lsws/conf/httpd_config.xml',
                 '/usr/local/lsws/conf/modsec.conf', '/usr/local/lsws/conf/httpd.conf']

        for items in files:
            command = 'chmod 644 %s' % (items)
            ProcessUtilities.executioner(command)

        impFile = ['/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                   '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                   '/etc/dovecot/dovecot.conf', '/etc/pdns/pdns.conf', '/etc/pure-ftpd/db/mysql.conf',
                   '/etc/powerdns/pdns.conf']

        for items in impFile:
            command = 'chmod 600 %s' % (items)
            ProcessUtilities.executioner(command)

        command = 'chmod 640 /etc/postfix/*.cf'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/postfix/main.cf'
        subprocess.call(command, shell=True)

        command = 'chmod 640 /etc/dovecot/*.conf'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/dovecot/dovecot.conf'
        subprocess.call(command, shell=True)

        command = 'chmod 640 /etc/dovecot/dovecot-sql.conf.ext'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/postfix/dynamicmaps.cf'
        subprocess.call(command, shell=True)

        fileM = ['/usr/local/lsws/FileManager/', '/usr/local/CyberCP/install/FileManager',
                 '/usr/local/CyberCP/serverStatus/litespeed/FileManager', '/usr/local/lsws/Example/html/FileManager']

        for items in fileM:
            try:
                import shutil
                shutil.rmtree(items)
            except:
                pass

        command = 'chmod 755 /etc/pure-ftpd/'
        subprocess.call(command, shell=True)

        command = 'chmod +x /usr/local/CyberCP/plogical/renew.py'
        ProcessUtilities.executioner(command)

        command = 'chmod +x /usr/local/CyberCP/CLManager/CLPackages.py'
        ProcessUtilities.executioner(command)

        clScripts = ['/usr/local/CyberCP/CLScript/panel_info.py', '/usr/local/CyberCP/CLScript/CloudLinuxPackages.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxUsers.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py'
            , '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py', '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxDB.py', '/usr/local/CyberCP/CLScript/UserInfo.py']

        for items in clScripts:
            command = 'chmod +x %s' % (items)
            ProcessUtilities.executioner(command)

        command = 'chmod 600 /usr/local/CyberCP/plogical/adminPass.py'
        ProcessUtilities.executioner(command)

        command = 'chmod 600 /etc/cagefs/exclude/cyberpanelexclude'
        ProcessUtilities.executioner(command)

        command = "find /usr/local/CyberCP/ -name '*.pyc' -delete"
        ProcessUtilities.executioner(command)

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.cent8:

            command = 'chown root:pdns /etc/pdns/pdns.conf'
            ProcessUtilities.executioner(command)

            command = 'chmod 640 /etc/pdns/pdns.conf'
            ProcessUtilities.executioner(command)
        else:
            command = 'chown root:pdns /etc/powerdns/pdns.conf'
            ProcessUtilities.executioner(command)

            command = 'chmod 640 /etc/powerdns/pdns.conf'
            ProcessUtilities.executioner(command)

        command = 'chmod 640 /usr/local/lscp/cyberpanel/logs/access.log'
        ProcessUtilities.executioner(command)

        ###

    def ResetEmailConfigurations(self):
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

            ###

            self.checkIfMailServerSSLIssued()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Removing and re-installing postfix/dovecot..,5')

            if self.install_postfix_dovecot() == 0:
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Resetting configurations..,40')

            import sys
            sys.path.append('/usr/local/CyberCP')
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            from CyberCP import settings

            if self.setup_email_Passwords(settings.DATABASES['default']['PASSWORD']) == 0:
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Configurations reset..,70')

            if self.setup_postfix_dovecot_config() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'setup_postfix_dovecot_config failed. [404].')
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Restoreing OpenDKIM configurations..,70')

            if self.configureOpenDKIM() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'configureOpenDKIM failed. [404].')
                return 0


            if self.MailSSL:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Setting up Mail Server SSL if any..,75')
                from plogical.virtualHostUtilities import virtualHostUtilities
                virtualHostUtilities.issueSSLForMailServer(self.mailHostName, '/home/%s/public_html' % (self.mailHostName))

            from websiteFunctions.models import ChildDomains
            from plogical.virtualHostUtilities import virtualHostUtilities
            for websites in Websites.objects.all():
                try:
                    child = ChildDomains.objects.get(domain='mail.%s' % (websites.domain))
                    logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                              'Creating mail domain for %s..,80' % (websites.domain))
                    virtualHostUtilities.setupAutoDiscover(1, '/dev/null', websites.domain, websites.admin)
                except:
                    pass

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Fixing permissions..,90')

            self.fixCyberPanelPermissions()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Completed [200].')

        except BaseException as msg:
            final_dic = {'installOpenDKIM': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def debugEmailForSite(self, websiteName):

        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        try:
            import socket
            siteIPAddr = socket.gethostbyname('mail.%s' % (websiteName))

            if siteIPAddr != ipAddress:
                return 0, 'mail.%s does not point to %s.' % (websiteName, ipAddress)
        except:
            return 0, 'mail.%s does not point to %s.' % (websiteName, ipAddress)

        command = 'openssl s_client -connect mail.%s:993' % (websiteName)
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('18 (self signed certificate)') > -1:
            return 0, 'No valid SSL on port 993.'
        else:
            return 1, 'All checks are OK.'

def main():

    parser = argparse.ArgumentParser(description='CyberPanel')
    parser.add_argument('function', help='Specifiy a function to call!')
    parser.add_argument('--tempStatusPath', help='Path of temporary status file.')

    args = parser.parse_args()

    if args.function == "ResetEmailConfigurations":
        extraArgs = {'tempStatusPath': args.tempStatusPath}
        background = MailServerManager(None, 'ResetEmailConfigurations', extraArgs)
        background.ResetEmailConfigurations()

if __name__ == "__main__":
    main()
