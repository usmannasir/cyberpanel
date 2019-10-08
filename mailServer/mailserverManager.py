#!/usr/local/CyberCP/bin/python2
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.shortcuts import render,redirect
from django.http import HttpResponse
from models import Domains,EUsers
from loginSystem.views import loadLoginPage
import plogical.CyberCPLogFileWriter as logging
import json
import shlex
import subprocess
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.mailUtilities import mailUtilities
import thread
from dns.models import Domains as dnsDomains
from dns.models import Records as dnsRecords
from mailServer.models import Forwardings
from plogical.acl import ACLManager
import os
from plogical.dnsUtilities import DNS
from loginSystem.models import Administrator
from plogical.processUtilities import ProcessUtilities
import bcrypt

class MailServerManager:

    def __init__(self, request = None):
        self.request = request

    def loadEmailHome(self):
        try:
            val = self.request.session['userID']
            return render(self.request, 'mailServer/index.html')
        except KeyError:
            return redirect(loadLoginPage)

    def createEmailAccount(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createEmail') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/postfix'):
                return render(self.request, "mailServer/createEmailAccount.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)
            websitesName = websitesName + ACLManager.findChildDomains(websitesName)

            return render(self.request, 'mailServer/createEmailAccount.html',
                          {'websiteList': websitesName, "status": 1})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))


    def listEmails(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listEmails') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/postfix'):
                return render(self.request, "mailServer/listEmails.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)
            websitesName = websitesName + ACLManager.findChildDomains(websitesName)

            return render(self.request, 'mailServer/listEmails.html',
                          {'websiteList': websitesName, "status": 1})
        except BaseException, msg:
            return redirect(loadLoginPage)

    def submitEmailCreation(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createEmail') == 0:
                return ACLManager.loadErrorJson('createEmailStatus', 0)

            data = json.loads(self.request.body)
            domainName = data['domain']
            userName = data['username']
            password = data['passwordByPass']


            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()


            ## Create email entry

            result = mailUtilities.createEmailAccount(domainName, userName, password)

            if result[0] == 1:
                data_ret = {'status': 1, 'createEmailStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            else:
                data_ret = {'status': 0, 'createEmailStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'createEmailStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteEmailAccount(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteEmail') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/postfix'):
                return render(self.request, "mailServer/deleteEmailAccount.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)
            websitesName = websitesName + ACLManager.findChildDomains(websitesName)

            return render(self.request, 'mailServer/deleteEmailAccount.html',
                          {'websiteList': websitesName, "status": 1})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

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
                dic = {'id': count, 'email': items.email}
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

        except BaseException, msg:
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

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(eUser.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            mailUtilities.deleteEmailAccount(email)
            data_ret = {'status': 1, 'deleteEmailStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'deleteEmailStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def emailForwarding(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'emailForwarding') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/postfix'):
                return render(self.request, "mailServer/emailForwarding.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)
            websitesName = websitesName + ACLManager.findChildDomains(websitesName)

            return render(self.request, 'mailServer/emailForwarding.html', {'websiteList': websitesName, "status": 1})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def fetchCurrentForwardings(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'emailForwarding') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            emailAddress = data['emailAddress']

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


        except BaseException, msg:
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

            eUser = EUsers.objects.get(email=source)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(eUser.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            for items in Forwardings.objects.filter(destination=destination, source=source):
                items.delete()

            data_ret = {'status': 1, 'deleteForwardingStatus': 1, 'error_message': "None",
                        'successMessage': 'Successfully deleted!'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
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

            eUser = EUsers.objects.get(email=source)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(eUser.emailOwner.domainOwner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if Forwardings.objects.filter(source=source, destination=destination).count() > 0:
                data_ret = {'status': 0, 'createStatus': 0,
                            'error_message': "You have already forwared to this destination."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if Forwardings.objects.filter(source=source).count() == 0:
                forwarding = Forwardings(source=source, destination=source)
                forwarding.save()

            forwarding = Forwardings(source=source, destination=destination)
            forwarding.save()

            data_ret = {'status': 1, 'createStatus': 1, 'error_message': "None", 'successMessage': 'Successfully Created!'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
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

            records = emailDomain.eusers_set.all()

            json_data = "["
            checker = 0

            for items in records:
                dic = {'email': items.email,
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    #######

    def changeEmailAccountPassword(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'changeEmailPassword') == 0:
                return ACLManager.loadError()

            if not os.path.exists('/home/cyberpanel/postfix'):
                return render(self.request, "mailServer/changeEmailPassword.html", {"status": 0})

            websitesName = ACLManager.findAllSites(currentACL, userID)
            websitesName = websitesName + ACLManager.findChildDomains(websitesName)

            return render(self.request, 'mailServer/changeEmailPassword.html',
                          {'websiteList': websitesName, "status": 1})
        except BaseException, msg:
            return HttpResponse(str(msg))

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
                password = bcrypt.hashpw(str(password), bcrypt.gensalt())
                password = '{CRYPT}%s' % (password)
                emailDB.password = password
            else:
                password = bcrypt.hashpw(str(password), bcrypt.gensalt())
                password = '{CRYPT}%s' % (password)
                emailDB.password = password

            emailDB.save()


            data_ret = {'status': 1, 'passChangeStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'passChangeStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    #######

    def dkimManager(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'dkimManager') == 0:
                return ACLManager.loadError()

            openDKIMInstalled = 1

            websitesName = ACLManager.findAllSites(currentACL, userID)
            websitesName = websitesName + ACLManager.findChildDomains(websitesName)

            return render(self.request, 'mailServer/dkimManager.html',
                          {'websiteList': websitesName, 'openDKIMInstalled': openDKIMInstalled})

        except BaseException, msg:
            return HttpResponse(str(msg))

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
                path = "/etc/opendkim/keys/" + domainName + "/default.txt"
                command = "sudo cat " + path
                output = ProcessUtilities.outputExecutioner(command, 'opendkim')
                leftIndex = output.index('(') + 2
                rightIndex = output.rindex(')') - 1

                path = "/etc/opendkim/keys/" + domainName + "/default.private"
                command = "sudo cat " + path
                privateKey = ProcessUtilities.outputExecutioner(command, 'opendkim')

                data_ret = {'status': 1, 'fetchStatus': 1, 'keysAvailable': 1, 'publicKey': output[leftIndex:rightIndex],
                            'privateKey': privateKey, 'dkimSuccessMessage': 'Keys successfully fetched!',
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            except BaseException, msg:
                data_ret = {'status': 1, 'fetchStatus': 1, 'keysAvailable': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
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

            execPath = "/usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
            execPath = execPath + " generateKeys --domain " + domainName
            output = ProcessUtilities.outputExecutioner(execPath)

            admin = Administrator.objects.get(pk=userID)
            DNS.dnsTemplate(domainName, admin)

            if output.find("1,None") > -1:
                import tldextract

                extractDomain = tldextract.extract(domainName)
                topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix

                zone = dnsDomains.objects.get(name=topLevelDomain)
                zone.save()

                path = "/etc/opendkim/keys/" + domainName + "/default.txt"
                command = "sudo cat " + path
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

        except BaseException, msg:
            data_ret = {'status': 0, 'generateStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installOpenDKIM(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'dkimManager') == 0:
                return ACLManager.loadErrorJson('installOpenDKIM', 0)
            thread.start_new_thread(mailUtilities.installOpenDKIM, ('Install', 'openDKIM'))
            final_json = json.dumps({'installOpenDKIM': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException, msg:
            final_dic = {'installOpenDKIM': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installStatusOpenDKIM(self):
        try:
            command = "sudo cat " + mailUtilities.installLogPath
            installStatus = subprocess.check_output(shlex.split(command))

            if installStatus.find("[200]") > -1:

                execPath = "/usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
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

        except BaseException, msg:
            final_dic = {'abort': 1, 'installed': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)