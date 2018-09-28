from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import json
from django.shortcuts import HttpResponse

class secMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                for key, value in data.iteritems():
                    if type(value) == int or type(value) == bool or key == 'configData':
                        continue
                    if value.find(';') > -1 or value.find('&&') > -1 or value.find('|') > -1 or value.find('...') > -1:
                        logging.writeToFile(request.body)
                        return HttpResponse('Error')
                    if key.find(';') > -1 or key.find('&&') > -1 or key.find('|') > -1 or key.find('...') > -1:
                        logging.writeToFile(request.body)
                        return HttpResponse('Error')
            except BaseException, msg:
                logging.writeToFile(str(msg))
                response = self.get_response(request)
                return response
        response = self.get_response(request)
        return response
