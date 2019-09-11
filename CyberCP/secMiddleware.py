from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import json
from django.shortcuts import HttpResponse

class secMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            uID = request.session['userID']
            ipAddr = request.META.get('REMOTE_ADDR')

            if ipAddr.find('.') > -1:
                if request.session['ipAddr'] == ipAddr:
                    pass
                else:
                    del request.session['userID']
                    del request.session['ipAddr']
                    logging.writeToFile(request.META.get('REMOTE_ADDR'))
                    final_dic = {'error_message': "Session reuse detected, IPAddress logged.",
                                 "errorMessage": "Session reuse detected, IPAddress logged."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            else:
                ipAddr = request.META.get('REMOTE_ADDR').split(':')[:3]

                if request.session['ipAddr'] == ipAddr:
                    pass
                else:
                    del request.session['userID']
                    del request.session['ipAddr']
                    logging.writeToFile(request.META.get('REMOTE_ADDR'))
                    final_dic = {'error_message': "Session reuse detected, IPAddress logged.",
                                 "errorMessage": "Session reuse detected, IPAddress logged."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
        except:
            pass
        if request.method == 'POST':
            try:
                #logging.writeToFile(request.body)
                data = json.loads(request.body)
                for key, value in data.iteritems():
                    if request.path.find('gitNotify') > -1:
                        break

                    # if request.path.find('users') > -1 or request.path.find('firewall') > -1 or request.path.find('servicesAction') > -1 or request.path.find('sslForHostName') > -1:
                    #     logging.writeToFile(request.body)
                    #     final_dic = {'error_message': "Data supplied is not accepted.",
                    #                  "errorMessage": "Data supplied is not accepted."}
                    #     final_json = json.dumps(final_dic)
                    #     return HttpResponse(final_json)

                    if type(value) == str or type(value) == unicode:
                        pass
                    else:
                        continue

                    if request.build_absolute_uri().find('saveSpamAssassinConfigurations') > -1 or request.build_absolute_uri().find('docker') > -1 or request.build_absolute_uri().find('cloudAPI') > -1 or request.build_absolute_uri().find('filemanager') > -1 or request.build_absolute_uri().find('verifyLogin') > -1 or request.build_absolute_uri().find('submitUserCreation') > -1:
                        continue
                    if key == 'ports' or key == 'imageByPass' or key == 'passwordByPass' or key == 'cronCommand' or key == 'emailMessage' or key == 'configData' or key == 'rewriteRules' or key == 'modSecRules' or key == 'recordContentTXT' or key == 'SecAuditLogRelevantStatus' or key == 'fileContent':
                        continue
                    if value.find(';') > -1 or value.find('&&') > -1 or value.find('|') > -1 or value.find('...') > -1 \
                            or value.find("`") > -1 or value.find("$") > -1 or value.find("(") > -1 or value.find(")") > -1 \
                            or value.find("'") > -1 or value.find("[") > -1 or value.find("]") > -1 or value.find("{") > -1 or value.find("}") > -1\
                            or value.find(":") > -1 or value.find("<") > -1 or value.find(">") > -1:
                        logging.writeToFile(request.body)
                        final_dic = {'error_message': "Data supplied is not accepted.",
                                     "errorMessage": "Data supplied is not accepted."}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
                    if key.find(';') > -1 or key.find('&&') > -1 or key.find('|') > -1 or key.find('...') > -1 \
                            or key.find("`") > -1 or key.find("$") > -1 or key.find("(") > -1 or key.find(")") > -1 \
                            or key.find("'") > -1 or key.find("[") > -1 or key.find("]") > -1 or key.find("{") > -1 or key.find("}") > -1\
                            or key.find(":") > -1 or key.find("<") > -1 or key.find(">") > -1:
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
