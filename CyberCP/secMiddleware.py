from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import json
from django.shortcuts import HttpResponse

class secMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST':
            try:
                #logging.writeToFile(request.body)
                data = json.loads(request.body)
                for key, value in data.iteritems():
                    if request.path.find('gitNotify') > -1:
                        break
                    if type(value) == str or type(value) == unicode:
                        pass
                    else:
                        continue
                    if key == 'emailMessage' or key == 'configData' or key == 'rewriteRules' or key == 'modSecRules' or key == 'recordContentTXT' or key == 'SecAuditLogRelevantStatus' or key == 'fileContent':
                        continue
                    if value.find(';') > -1 or value.find('&&') > -1 or value.find('|') > -1 or value.find('...') > -1:
                        logging.writeToFile(request.body)
                        final_dic = {'error_message': "Data supplied is not accepted.",
                                     "errorMessage": "Data supplied is not accepted."}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
                    if key.find(';') > -1 or key.find('&&') > -1 or key.find('|') > -1 or key.find('...') > -1:
                        logging.writeToFile(request.body)
                        final_dic = {'error_message': "Data supplied is not accepted.", "errorMessage": "Data supplied is not accepted."}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
            except BaseException, msg:
                logging.writeToFile(str(msg))
                response = self.get_response(request)
                return response
        response = self.get_response(request)
        return response
