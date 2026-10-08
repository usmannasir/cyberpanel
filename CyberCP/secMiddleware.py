# coding=utf-8
import os.path

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from django.shortcuts import HttpResponse, render
import json
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

        ######

        from plogical.processUtilities import ProcessUtilities
        FinalURL = request.build_absolute_uri().split('?')[0]

        from urllib.parse import urlparse
        pathActual = urlparse(FinalURL).path

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'Path vs the final url : {pathActual}')
            logging.writeToFile(FinalURL)

        if pathActual == "/backup/localInitiate" or  pathActual == '/' or pathActual == '/verifyLogin' or pathActual == '/logout' or pathActual.startswith('/api')\
                or pathActual.endswith('/webhook') or pathActual.startswith('/cloudAPI') or pathActual.endswith('/gitNotify'):
            pass
        else:
            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'Request needs session : {pathActual}')
            try:
                val = request.session['userID']
            except:
                if bool(request.body):
                    final_dic = {
                        'error_message': "This request need session.",
                        "errorMessage": "This request need session."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    from django.shortcuts import redirect
                    from loginSystem.views import loadLoginPage
                    return redirect(loadLoginPage)

        # if os.path.exists(ProcessUtilities.debugPath):
        #     logging.writeToFile(f'Final actual URL without QS {FinalURL}')

        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile(f'Request method {request.method.lower()}')

        ##########################

        try:
            uID = request.session['userID']
            admin = Administrator.objects.get(pk=uID)
            ipAddr = secMiddleware.get_client_ip(request)

            if ipAddr.find('.') > -1:
                if request.session['ipAddr'] == ipAddr or admin.securityLevel == secMiddleware.LOW:
                    pass
                else:
                    del request.session['userID']
                    del request.session['ipAddr']
                    logging.writeToFile(secMiddleware.get_client_ip(request))
                    final_dic = {'error_message': "Session reuse detected, IPAddress logged.",
                                 "errorMessage": "Session reuse detected, IPAddress logged."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            else:
                ipAddr = secMiddleware.get_client_ip(request).split(':')[:3]
                if request.session['ipAddr'] == ipAddr or admin.securityLevel == secMiddleware.LOW:
                    pass
                else:
                    del request.session['userID']
                    del request.session['ipAddr']
                    logging.writeToFile(secMiddleware.get_client_ip(request))
                    final_dic = {'error_message': "Session reuse detected, IPAddress logged.",
                                 "errorMessage": "Session reuse detected, IPAddress logged."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
        except:
            pass


        if bool(request.body):
            try:

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile('Request body detected.. scanning')
                    logging.writeToFile(str(request.body))

                # logging.writeToFile(request.body)
                try:
                    data = json.loads(request.body.decode('utf-8'))
                except:
                    data = request.POST

                for key, value in data.items():
                    valueAlreadyChecked = 0

                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.writeToFile(f'Key being scanned {str(key)}')
                        logging.writeToFile(f'Value being scanned {str(value)}')

                    if request.path.find('gitNotify') > -1:
                        break

                    if isinstance(value, (str, bytes)):
                        pass
                    elif isinstance(value, list):
                        valueAlreadyChecked = 1
                        if os.path.exists(ProcessUtilities.debugPath):
                            logging.writeToFile(f'Item type detected as list')
                        for item in value:
                            if isinstance(item, (str, bytes)):
                                if item.find('- -') > -1 or item.find('\n') > -1 or item.find(';') > -1 or item.find(
                                        '&&') > -1 or item.find('|') > -1 or item.find('...') > -1 \
                                        or item.find("`") > -1 or item.find("$") > -1 or item.find(
                                    "(") > -1 or item.find(")") > -1 \
                                        or item.find("'") > -1 or item.find("[") > -1 or item.find(
                                    "]") > -1 or item.find("{") > -1 or item.find("}") > -1 \
                                        or item.find(":") > -1 or item.find("<") > -1 or item.find(
                                    ">") > -1 or item.find("&") > -1:
                                    logging.writeToFile(request.body)
                                    final_dic = {
                                        'error_message': "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >.",
                                        "errorMessage": "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                                    final_json = json.dumps(final_dic)
                                    return HttpResponse(final_json)
                    else:
                        continue

                    if key == 'backupDestinations':
                        if isinstance(value, str) and re.match('^[a-z0-9]+:[a-z0-9\.]+/?[A-Za-z0-9\.]*$', value) is None and value != 'local':
                            logging.writeToFile(request.body)
                            final_dic = {'error_message': "Data supplied is not accepted.",
                                         "errorMessage": "Data supplied is not accepted."}
                            final_json = json.dumps(final_dic)
                            return HttpResponse(final_json)

                    if FinalURL.find(
                            'api/remoteTransfer') > -1 or FinalURL.find(
                        'api/verifyConn') > -1 or FinalURL.find(
                        'webhook') > -1 or FinalURL.find(
                        'saveSpamAssassinConfigurations') > -1 or FinalURL.find(
                        'docker') > -1 or FinalURL.find(
                        'cloudAPI') > -1 or FinalURL.find(
                        'verifyLogin') > -1 or FinalURL.find('submitUserCreation') > -1:
                        continue
                    if key == 'MainDashboardCSS' or key == 'ownerPassword' or key == 'scriptUrl' or key == 'CLAMAV_VIRUS' or key == "Rspamdserver" or key == 'smtpd_milters' \
                            or key == 'non_smtpd_milters' or key == 'key' or key == 'cert' or key == 'recordContentAAAA' or key == 'backupDestinations'\
                            or key == 'ports' \
                            or key == 'imageByPass' or key == 'passwordByPass' or key == 'PasswordByPass' or key == 'cronCommand' \
                            or key == 'emailMessage' or key == 'configData' or key == 'rewriteRules' \
                            or key == 'modSecRules' or key == 'recordContentTXT' or key == 'SecAuditLogRelevantStatus' \
                            or key == 'fileContent' or key == 'commands' or key == 'gitHost' or key == 'ipv6' or key == 'contentNow':
                        continue

                    if valueAlreadyChecked == 0 and isinstance(value, (str, bytes)):
                        if value.find('- -') > -1 or value.find('\n') > -1 or value.find(';') > -1 or value.find(
                                '&&') > -1 or value.find('|') > -1 or value.find('...') > -1 \
                                or value.find("`") > -1 or value.find("$") > -1 or value.find("(") > -1 or value.find(
                            ")") > -1 \
                                or value.find("'") > -1 or value.find("[") > -1 or value.find("]") > -1 or value.find(
                            "{") > -1 or value.find("}") > -1 \
                                or value.find(":") > -1 or value.find("<") > -1 or value.find(">") > -1 or value.find(
                            "&") > -1:
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
                            or key.find(":") > -1 or key.find("<") > -1 or key.find(">") > -1 or key.find("&") > -1:
                        logging.writeToFile(request.body)
                        final_dic = {'error_message': "Data supplied is not accepted.",
                                     "errorMessage": "Data supplied is not accepted following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)

            except BaseException as msg:
                final_dic = {'error_message': f"Error: {str(msg)}",
                             "errorMessage": f"Error: {str(msg)}"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
        else:
            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile('Request does not have a body.')
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
        response[
            'Content-Security-Policy'] = "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://www.jsdelivr.com https://cdnjs.cloudflare.com https://maxcdn.bootstrapcdn.com https://cdn.jsdelivr.net"
        # response['Content-Security-Policy'] = "default-src 'self' cyberpanel.cloud *.cyberpanel.cloud"
        response['X-Content-Type-Options'] = "nosniff"
        response['Referrer-Policy'] = "same-origin"



        return response
