# -*- coding: utf-8 -*-

from django.shortcuts import render, HttpResponse
import json

class httpProc:
    def __init__(self, request, templateName, data = None, function = None):
        self.request = request
        self.templateName = templateName
        self.data = data
        self.function = function


    def render(self):
        try:
            userID = self.request.session['userID']
            try:
                from loginSystem.models import Administrator
                from plogical.acl import ACLManager

                currentACL = ACLManager.loadedACL(userID)
                admin = Administrator.objects.get(pk=userID)

                ### Permissions Check

                if self.function != None:
                    if not currentACL['admin']:
                        if not currentACL[self.function]:
                            templateName = 'baseTemplate/error.html'
                            return render(self.request, templateName, {'error_message': 'You are not authorized to access %s' % (self.function)})

                ###

                if self.data == None:
                    self.data = {}

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddress = ipData.split('\n', 1)[0]
                self.data['ipAddress'] = ipAddress
                self.data['fullName'] = '%s %s' % (admin.firstName, admin.lastName)

                ### Load Custom CSS
                try:
                    from baseTemplate.models import CyberPanelCosmetic
                    cosmetic = CyberPanelCosmetic.objects.get(pk=1)
                    self.data['cosmetic'] = cosmetic
                except:
                    try:
                        from baseTemplate.models import CyberPanelCosmetic
                        cosmetic = CyberPanelCosmetic()
                        cosmetic.save()
                        self.data['cosmetic'] = cosmetic
                    except:
                        pass

                ACLManager.GetServiceStatus(self.data)

                self.data.update(currentACL)

                return render(self.request, self.templateName, self.data)
            except BaseException as msg:
                templateName = 'baseTemplate/error.html'
                return render(self.request, templateName, {'error_message': str(msg)})
        except:
            from loginSystem.views import loadLoginPage
            from django.shortcuts import redirect
            return redirect(loadLoginPage)

    def renderPre(self):
        if self.data == None:
            return render(self.request, self.templateName)
        else:
            return render(self.request, self.templateName, self.data)

    def ajaxPre(self, status, errorMessage, success = None):
        final_dic = {'status': status, 'error_message': errorMessage, 'success': success}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    def ajax(self, status, errorMessage, data = None):
        if data == None:
            finalDic = {'status': status, 'error_message': errorMessage}
            finalJson = json.dumps(finalDic)
            return HttpResponse(finalJson)
        else:
            finalDic = {}
            finalDic['status'] = status
            finalDic['error_message'] = errorMessage

            for key, value in data.items():
                finalDic[key] = value

            finalJson = json.dumps(finalDic)
            return HttpResponse(finalJson)

    @staticmethod
    def AJAX(status, errorMessage, success = None):
        final_dic = {'status': status, 'error_message': errorMessage, 'success': success}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)




