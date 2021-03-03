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
            from loginSystem.models import Administrator
            from plogical.acl import ACLManager
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

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

            self.data.update(currentACL)

            return render(self.request, self.templateName, self.data)
        except BaseException as msg:
            templateName = 'baseTemplate/error.html'
            return render(self.request, templateName, {'error_message': str(msg)})

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




