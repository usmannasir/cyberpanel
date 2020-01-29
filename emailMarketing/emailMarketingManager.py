from django.shortcuts import render, HttpResponse, redirect
from plogical.acl import ACLManager
from loginSystem.views import loadLoginPage
import json
from random import randint
import time
from .models import EmailMarketing, EmailLists, EmailsInList, EmailJobs
from websiteFunctions.models import Websites
from .emailMarketing import emailMarketing as EM
from math import ceil
import smtplib
from .models import SMTPHosts, EmailTemplate
from loginSystem.models import Administrator
from .emACL import emACL

class EmailMarketingManager:

    def __init__(self, request = None, domain = None):
        self.request = request
        self.domain = domain

    def emailMarketing(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(self.request, 'emailMarketing/emailMarketing.html')
        except KeyError as msg:
            return redirect(loadLoginPage)

    def fetchUsers(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            allUsers = ACLManager.findAllUsers()
            disabledUsers = EmailMarketing.objects.all()
            disabled = []
            for items in disabledUsers:
                disabled.append(items.userName)

            json_data = "["
            checker = 0
            counter = 1

            for items in allUsers:
                if items in disabled:
                    status = 0
                else:
                    status = 1

                dic = {'id': counter, 'userName': items, 'status': status}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'
            data_ret = {"status": 1, 'data': json_data}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def enableDisableMarketing(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)
            userName = data['userName']

            try:
                disableMarketing = EmailMarketing.objects.get(userName=userName)
                disableMarketing.delete()
            except:
                enableMarketing = EmailMarketing(userName=userName)
                enableMarketing.save()

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def createEmailList(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadError()

            return render(self.request, 'emailMarketing/createEmailList.html', {'domain': self.domain})
        except KeyError as msg:
            return redirect(loadLoginPage)

    def submitEmailList(self):
        try:

            data = json.loads(self.request.body)

            extraArgs = {}
            extraArgs['domain'] = data['domain']
            extraArgs['path'] = data['path']
            extraArgs['listName'] = data['listName'].replace(' ', '')
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(data['domain'], admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            em = EM('createEmailList', extraArgs)
            em.start()

            time.sleep(2)

            data_ret = {"status": 1, 'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def manageLists(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadError()

            listNames = emACL.getEmailsLists(self.domain)

            return render(self.request, 'emailMarketing/manageLists.html', {'listNames': listNames, 'domain': self.domain})
        except KeyError as msg:
            return redirect(loadLoginPage)

    def fetchEmails(self):
        try:

            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            listName = data['listName']
            recordstoShow = int(data['recordstoShow'])
            page = int(data['page'])

            finalPageNumber = ((page * recordstoShow)) - recordstoShow
            endPageNumber = finalPageNumber + recordstoShow

            emailList = EmailLists.objects.get(listName=listName)
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif emailList.owner.id != userID:
                return ACLManager.loadErrorJson()

            emails = emailList.emailsinlist_set.all()

            ## Pagination value

            pages = float(len(emails)) / float(recordstoShow)
            pagination = []
            counter = 1

            if pages <= 1.0:
                pages = 1
                pagination.append(counter)
            else:
                pages = ceil(pages)
                finalPages = int(pages) + 1

                for i in range(1, finalPages):
                    pagination.append(counter)
                    counter = counter + 1

            ## Pagination value

            emails = emails[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0
            counter = 1

            for items in emails:

                dic = {'id': items.id, 'email': items.email, 'verificationStatus': items.verificationStatus,
                       'dateCreated': items.dateCreated}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'
            data_ret = {"status": 1, 'data': json_data, 'pagination': pagination}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteList(self):
        try:

            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            listName = data['listName']

            delList = EmailLists.objects.get(listName=listName)
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] == 1:
                pass
            elif delList.owner.id != userID:
                return ACLManager.loadErrorJson()

            delList.delete()

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def emailVerificationJob(self):
        try:

            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)
            extraArgs = {}
            extraArgs['listName'] = data['listName']

            delList = EmailLists.objects.get(listName=extraArgs['listName'])
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] == 1:
                pass
            elif delList.owner.id != userID:
                return ACLManager.loadErrorJson()

            em = EM('verificationJob', extraArgs)
            em.start()

            time.sleep(2)

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteEmail(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            id = data['id']

            delEmail = EmailsInList.objects.get(id=id)

            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] == 1:
                pass
            elif delEmail.owner.owner.id != userID:
                return ACLManager.loadErrorJson()

            delEmail.delete()

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def manageSMTP(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadError()

            website = Websites.objects.get(domain=self.domain)
            emailLists = website.emaillists_set.all()
            listNames = []

            for items in emailLists:
                listNames.append(items.listName)
            return render(self.request, 'emailMarketing/manageSMTPHosts.html', {'listNames': listNames, 'domain': self.domain})
        except KeyError as msg:
            return redirect(loadLoginPage)

    def saveSMTPHost(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()


            data = json.loads(self.request.body)

            smtpHost = data['smtpHost']
            smtpPort = data['smtpPort']
            smtpUserName = data['smtpUserName']
            smtpPassword = data['smtpPassword']

            if SMTPHosts.objects.count() == 0:
                admin = Administrator.objects.get(userName='admin')
                defaultHost = SMTPHosts(owner=admin, host='localhost', port=25, userName='None', password='None')
                defaultHost.save()

            try:
                verifyLogin = smtplib.SMTP(str(smtpHost), int(smtpPort))
                verifyLogin.login(str(smtpUserName), str(smtpPassword))

                admin = Administrator.objects.get(pk=userID)

                newHost = SMTPHosts(owner=admin, host=smtpHost, port=smtpPort, userName=smtpUserName,
                                    password=smtpPassword)
                newHost.save()

            except smtplib.SMTPHeloError:
                data_ret = {"status": 0, 'error_message': 'The server did not reply properly to the HELO greeting.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except smtplib.SMTPAuthenticationError:
                data_ret = {"status": 0, 'error_message': 'Username and password combination not accepted.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except smtplib.SMTPException:
                data_ret = {"status": 0, 'error_message': 'No suitable authentication method was found.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def fetchSMTPHosts(self):
        try:

            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                allHosts = SMTPHosts.objects.all()
            else:
                admin = Administrator.objects.get(pk=userID)
                allHosts = admin.smtphosts_set.all()

            json_data = "["
            checker = 0
            counter = 1

            for items in allHosts:

                dic = {'id': items.id, 'owner': items.owner.userName, 'host': items.host, 'port': items.port,
                       'userName': items.userName}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'
            data_ret = {"status": 1, 'data': json_data}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def smtpHostOperations(self):
        try:

            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            id = data['id']
            operation = data['operation']

            if operation == 'delete':
                delHost = SMTPHosts.objects.get(id=id)
                currentACL = ACLManager.loadedACL(userID)
                if currentACL['admin'] == 1:
                    pass
                elif delHost.owner.id != userID:
                    return ACLManager.loadErrorJson()
                delHost.delete()
                data_ret = {"status": 1, 'message': 'Successfully deleted.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                try:
                    verifyHost = SMTPHosts.objects.get(id=id)
                    verifyLogin = smtplib.SMTP(str(verifyHost.host), int(verifyHost.port))
                    verifyLogin.login(str(verifyHost.userName), str(verifyHost.password))

                    data_ret = {"status": 1, 'message': 'Login successful.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                except smtplib.SMTPHeloError:
                    data_ret = {"status": 0, 'error_message': 'The server did not reply properly to the HELO greeting.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                except smtplib.SMTPAuthenticationError:
                    data_ret = {"status": 0, 'error_message': 'Username and password combination not accepted.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                except smtplib.SMTPException:
                    data_ret = {"status": 0, 'error_message': 'No suitable authentication method was found.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def composeEmailMessage(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            return render(self.request, 'emailMarketing/composeMessages.html')
        except KeyError as msg:
            return redirect(loadLoginPage)

    def saveEmailTemplate(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            name = data['name']
            subject = data['subject']
            fromName = data['fromName']
            fromEmail = data['fromEmail']
            replyTo = data['replyTo']
            emailMessage = data['emailMessage']

            admin = Administrator.objects.get(pk=userID)
            newTemplate = EmailTemplate(owner=admin, name=name.replace(' ', ''), subject=subject, fromName=fromName, fromEmail=fromEmail,
                                        replyTo=replyTo, emailMessage=emailMessage)
            newTemplate.save()

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def sendEmails(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            currentACL = ACLManager.loadedACL(userID)
            templateNames = emACL.allTemplates(currentACL, admin)
            hostNames = emACL.allSMTPHosts(currentACL, admin)
            listNames = emACL.allEmailsLists(currentACL, admin)


            Data = {}
            Data['templateNames'] = templateNames
            Data['hostNames'] = hostNames
            Data['listNames'] = listNames
            return render(self.request, 'emailMarketing/sendEmails.html', Data)
        except KeyError as msg:
            return redirect(loadLoginPage)

    def templatePreview(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)
            template = EmailTemplate.objects.get(name=self.domain)
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif template.owner != admin:
                return ACLManager.loadError()

            return HttpResponse(template.emailMessage)
        except KeyError as msg:
            return redirect(loadLoginPage)

    def fetchJobs(self):
        try:

            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)
            selectedTemplate = data['selectedTemplate']

            template = EmailTemplate.objects.get(name=selectedTemplate)
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif template.owner != admin:
                return ACLManager.loadErrorJson()

            allJobs = EmailJobs.objects.filter(owner=template)

            json_data = "["
            checker = 0
            counter = 1

            for items in allJobs:

                dic = {'id': items.id,
                       'date': items.date,
                       'host': items.host,
                       'totalEmails': items.totalEmails,
                       'sent': items.sent,
                       'failed': items.failed}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

                counter = counter + 1

            json_data = json_data + ']'
            data_ret = {"status": 1, 'data': json_data}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def startEmailJob(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)
            data = json.loads(self.request.body)

            extraArgs = {}
            extraArgs['selectedTemplate'] = data['selectedTemplate']
            extraArgs['listName'] = data['listName']
            extraArgs['host'] = data['host']
            try:
                extraArgs['verificationCheck'] = data['verificationCheck']
            except:
                extraArgs['verificationCheck'] = False
            try:
                extraArgs['unsubscribeCheck'] = data['unsubscribeCheck']
            except:
                extraArgs['unsubscribeCheck'] = False

            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + data['selectedTemplate'] + '_pendingJob'

            currentACL = ACLManager.loadedACL(userID)
            template = EmailTemplate.objects.get(name=extraArgs['selectedTemplate'])

            if currentACL['admin'] == 1:
                pass
            elif template.owner != admin:
                return ACLManager.loadErrorJson()

            em = EM('startEmailJob', extraArgs)
            em.start()

            time.sleep(2)

            data_ret = {"status": 1, 'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteTemplate(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)
            data = json.loads(self.request.body)

            selectedTemplate = data['selectedTemplate']

            delTemplate = EmailTemplate.objects.get(name=selectedTemplate)
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif delTemplate.owner != admin:
                return ACLManager.loadErrorJson()
            delTemplate.delete()

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteJob(self):
        try:
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            if emACL.checkIfEMEnabled(admin.userName) == 0:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)
            id = data['id']
            delJob = EmailJobs(id=id)
            delJob.delete()
            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)


    def remove(self, listName, emailAddress):
        try:
            eList = EmailLists.objects.get(listName=listName)
            removeEmail = EmailsInList.objects.get(owner=eList, email=emailAddress)
            removeEmail.verificationStatus = 'REMOVED'
            removeEmail.save()
        except:
            pass

        return HttpResponse('Email Address Successfully removed from the list.')