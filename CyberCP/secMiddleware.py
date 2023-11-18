# coding=utf-8
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import json
from django.shortcuts import HttpResponse, render
import re
from loginSystem.models import Administrator

class secMiddleware:

    HIGH = 0
    LOW = 1

    def get_client_ip(request):
        ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if ip is None:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            uID = request.session['userID']
            admin = Administrator.objects.get(pk=uID)
            ipAddr = get_client_ip(request)

            if ipAddr.find('.') > -1:
                if request.session['ipAddr'] == ipAddr or admin.securityLevel == secMiddleware.LOW:
                    pass
                else:
                    del request.session['userID']
                    del request.session['ipAddr']
                    logging.writeToFile(get_client_ip(request))
                    final_dic = {'error_message': "Session reuse detected, IPAddress logged.",
                                 "errorMessage": "Session reuse detected, IPAddress logged."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            else:
                ipAddr = get_client_ip(request).split(':')[:3]
                if request.session['ipAddr'] == ipAddr or admin.securityLevel == secMiddleware.LOW:
                    pass
                else:
                    del request.session['userID']
                    del request.session['ipAddr']
                    logging.writeToFile(get_client_ip(request))
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
                for key, value in data.items():
                    if request.path.find('gitNotify') > -1:
                        break
                    if type(value) == str or type(value) == bytes:
                        pass
                    elif type(value) == list:
                        for items in value:
                            if items.find('- -') > -1 or items.find('\n') > -1 or items.find(';') > -1 or items.find(
                                    '&&') > -1 or items.find('|') > -1 or items.find('...') > -1 \
                                    or items.find("`") > -1 or items.find("$") > -1 or items.find(
                                "(") > -1 or items.find(")") > -1 \
                                    or items.find("'") > -1 or items.find("[") > -1 or items.find(
                                "]") > -1 or items.find("{") > -1 or items.find("}") > -1 \
                                    or items.find(":") > -1 or items.find("<") > -1 or items.find(">") > -1:
                                logging.writeToFile(request.body)
                                final_dic = {
                                    'error_message': "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >.",
                                    "errorMessage": "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                                final_json = json.dumps(final_dic)
                                return HttpResponse(final_json)
                    else:
                        continue

                    if key == 'backupDestinations':
                        if re.match('^[a-z|0-9]+:[a-z|0-9|\.]+\/?[A-Z|a-z|0-9|\.]*$', value) == None and value != 'local':
                            logging.writeToFile(request.body)
                            final_dic = {'error_message': "Data supplied is not accepted.",
                                         "errorMessage": "Data supplied is not accepted."}
                            final_json = json.dumps(final_dic)
                            return HttpResponse(final_json)

                    if request.build_absolute_uri().find(
                            'api/remoteTransfer') > -1 or request.build_absolute_uri().find(
                            'api/verifyConn') > -1 or request.build_absolute_uri().find(
                            'webhook') > -1 or request.build_absolute_uri().find(
                            'saveSpamAssassinConfigurations') > -1 or request.build_absolute_uri().find(
                            'docker') > -1 or request.build_absolute_uri().find(
                            'cloudAPI') > -1 or request.build_absolute_uri().find(
                            'verifyLogin') > -1 or request.build_absolute_uri().find('submitUserCreation') > -1:
                        continue
                    if key == 'CLAMAV_VIRUS' or key == "Rspamdserver" or key == 'smtpd_milters' or key == 'non_smtpd_milters' or key == 'key' or key == 'cert' or key == 'recordContentAAAA' or key == 'backupDestinations' or key == 'ports' \
                            or key == 'imageByPass' or key == 'passwordByPass' or key == 'cronCommand' \
                            or key == 'emailMessage' or key == 'configData' or key == 'rewriteRules' \
                            or key == 'modSecRules' or key == 'recordContentTXT' or key == 'SecAuditLogRelevantStatus' \
                            or key == 'fileContent' or key == 'commands' or key == 'gitHost' or key == 'ipv6' or key == 'contentNow':
                        continue
                    if value.find('- -') > -1 or value.find('\n') > -1 or value.find(';') > -1 or value.find(
                            '&&') > -1 or value.find('|') > -1 or value.find('...') > -1 \
                            or value.find("`") > -1 or value.find("$") > -1 or value.find("(") > -1 or value.find(
                        ")") > -1 \
                            or value.find("'") > -1 or value.find("[") > -1 or value.find("]") > -1 or value.find(
                        "{") > -1 or value.find("}") > -1 \
                            or value.find(":") > -1 or value.find("<") > -1 or value.find(">") > -1:
                        logging.writeToFile(request.body)
                        final_dic = {
                            'error_message': "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >.",
                            "errorMessage": "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
                    if key.find(';') > -1 or key.find('&&') > -1 or key.find('|') > -1 or key.find('...') > -1 \
                            or key.find("`") > -1 or key.find("$") > -1 or key.find("(") > -1 or key.find(")") > -1 \
                            or key.find("'") > -1 or key.find("[") > -1 or key.find("]") > -1 or key.find(
                        "{") > -1 or key.find("}") > -1 \
                            or key.find(":") > -1 or key.find("<") > -1 or key.find(">") > -1:
                        logging.writeToFile(request.body)
                        final_dic = {'error_message': "Data supplied is not accepted.",
                                     "errorMessage": "Data supplied is not accepted following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)

            except BaseException as msg:
                logging.writeToFile(str(msg))
                response = self.get_response(request)
                return response
        # else:
        #     try:
        #         if request.path.find('cloudAPI/') > -1 or request.path.find('api/') > -1:
        #             pass
        #         else:
        #             uID = request.session['userID']
        #     except:
        #         return render(request, 'loginSystem/login.html', {})

        response = self.get_response(request)

        response['X-XSS-Protection'] = "1; mode=block"
        response['X-Frame-Options'] = "sameorigin"
        response['Content-Security-Policy'] = "script-src 'self' https://www.jsdelivr.com"
        response['Content-Security-Policy'] = "connect-src *;"
        response['Content-Security-Policy'] = "font-src 'self' 'unsafe-inline' https://www.jsdelivr.com https://fonts.googleapis.com"
        response['Content-Security-Policy'] = "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://www.jsdelivr.com https://cdnjs.cloudflare.com https://maxcdn.bootstrapcdn.com https://cdn.jsdelivr.net"
        #response['Content-Security-Policy'] = "default-src 'self' cyberpanel.cloud *.cyberpanel.cloud"
        response['X-Content-Type-Options'] = "nosniff"
        response['Referrer-Policy'] = "same-origin"

        return response
