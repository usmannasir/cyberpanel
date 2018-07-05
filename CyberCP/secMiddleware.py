from django.conf import settings
from django.shortcuts import HttpResponse
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

class secMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST':
            if request.body.find(';') > -1 or request.body.find('&&') > -1 or request.body.find('|') > -1 or request.body.find('...') > -1:
                logging.writeToFile('Bad Input on.')
        response = self.get_response(request)
        return response