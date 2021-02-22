# -*- coding: utf-8 -*-

from django.shortcuts import render, HttpResponse
import json

class httpProc:
    def __init__(self, request, templateName, data = None):
        self.request = request
        self.templateName = templateName
        self.data = data


    def render(self):
        try:
            from loginSystem.models import Administrator
            from plogical.acl import ACLManager
            userID = self.request.session['userID']
            admin = Administrator.objects.get(pk=userID)

            ###

            if self.data == None:
                self.data = {}

            self.data.update(ACLManager.loadedACL(userID))
            return render(self.request, self.templateName, self.data)

        except BaseException as msg:
            templateName = 'UserManagement/login.html'
            return render(self.request, templateName)

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




