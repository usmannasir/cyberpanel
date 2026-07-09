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

        # Debug logging removed for performance

        # Define webhook pattern for secure matching
        import re
        webhook_pattern = re.compile(r'^/websites/[^/]+/(webhook|gitNotify)/?$')
        
        if pathActual == "/backup/localInitiate" or  pathActual == '/' or pathActual == '/verifyLogin' or pathActual == '/logout' or pathActual.startswith('/api')\
                or webhook_pattern.match(pathActual) or pathActual.startswith('/cloudAPI'):
            pass
        else:
            # Session check logging removed
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

        # Request method logging removed

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
                ipAddr = ':'.join(secMiddleware.get_client_ip(request).split(':')[:3])
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

                # Body scanning logging removed

                # Skip validation entirely for webhook endpoints
                # Webhook URLs are: /websites/<domain>/webhook or /websites/<domain>/gitNotify
                # Use the same webhook pattern defined above
                if webhook_pattern.match(pathActual):
                    response = self.get_response(request)
                    return response

                # logging.writeToFile(request.body)
                try:
                    data = json.loads(request.body)
                except:
                    data = request.POST

                # Skip the input character validation for the webmail app.
                # All webmail input (message bodies, subjects, recipient names,
                # search queries, sieve rules, contacts) is free-form text that is
                # handled exclusively through Python IMAP/SMTP/Sieve libraries and
                # never reaches a shell, so the command-injection character checks
                # only produce false positives (e.g. an email reply containing ;,
                # |, $ or backticks). See issue #1813. Note: this only skips input
                # validation -- the request still falls through to the response
                # path below where the security headers (nosniff, X-Frame-Options,
                # CSP, Referrer-Policy) are applied.
                webmailRequest = pathActual.startswith('/webmail/')

                for key, value in ({} if webmailRequest else data).items():
                    valueAlreadyChecked = 0

                    # Key/value scanning logging removed

                    # Skip validation for ports key to allow port ranges with colons
                    # but only for CSF modifyPorts endpoint
                    if key == 'ports' and pathActual == '/firewall/modifyPorts':
                        # Validate that ports only contain numbers, commas, and colons
                        if type(value) == str:
                            import re
                            # Allow only: digits, commas, colons, and whitespace
                            if re.match(r'^[\d,:,\s]+$', value):
                                continue
                            else:
                                logging.writeToFile(f"Invalid port format in CSF configuration: {value}")
                                final_dic = {
                                    'error_message': "Invalid port format. Only numbers, commas, and colons are allowed for port ranges.",
                                    "errorMessage": "Invalid port format. Only numbers, commas, and colons are allowed for port ranges."}
                                final_json = json.dumps(final_dic)
                                return HttpResponse(final_json)
                        continue
                    elif key == 'ports':
                        # For other endpoints, ports key continues to skip validation
                        continue
                    
                    # Allow protocol parameter for CSF modifyPorts endpoint
                    if key == 'protocol' and pathActual == '/firewall/modifyPorts':
                        # Validate protocol values
                        if value in ['TCP_IN', 'TCP_OUT', 'UDP_IN', 'UDP_OUT']:
                            continue
                        else:
                            logging.writeToFile(f"Invalid protocol in CSF configuration: {value}")
                            final_dic = {
                                'error_message': "Invalid protocol. Only TCP_IN, TCP_OUT, UDP_IN, UDP_OUT are allowed.",
                                "errorMessage": "Invalid protocol. Only TCP_IN, TCP_OUT, UDP_IN, UDP_OUT are allowed."}
                            final_json = json.dumps(final_dic)
                            return HttpResponse(final_json)

                    if type(value) == str or type(value) == bytes:
                        pass
                    elif type(value) == list:
                        valueAlreadyChecked = 1
                        # List type logging removed
                        for items in value:
                            if isinstance(items, str) and (items.find('- -') > -1 or items.find('\n') > -1 or items.find(';') > -1 or items.find(
                                    '&&') > -1 or items.find('|') > -1 or items.find('...') > -1 \
                                    or items.find("`") > -1 or items.find("$") > -1 or items.find(
                                "(") > -1 or items.find(")") > -1 \
                                    or items.find("'") > -1 or items.find("[") > -1 or items.find(
                                "]") > -1 or items.find("{") > -1 or items.find("}") > -1 \
                                    or items.find(":") > -1 or items.find("<") > -1 or items.find(
                                ">") > -1 or items.find("&") > -1):
                                logging.writeToFile(request.body)
                                final_dic = {
                                    'error_message': "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >.",
                                    "errorMessage": "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                                final_json = json.dumps(final_dic)
                                return HttpResponse(final_json)
                    else:
                        continue

                    if key == 'backupDestinations':
                        if re.match('^[a-z|0-9]+:[a-z|0-9|\.]+\/?[A-Z|a-z|0-9|\.]*$',
                                    value) == None and value != 'local':
                            logging.writeToFile(request.body)
                            final_dic = {'error_message': "Data supplied is not accepted.",
                                         "errorMessage": "Data supplied is not accepted."}
                            final_json = json.dumps(final_dic)
                            return HttpResponse(final_json)

                    # Allow JSON structure characters for API endpoints but keep security checks for dangerous characters
                    isAPIEndpoint = (pathActual.find('api/remoteTransfer') > -1 or pathActual.find('api/verifyConn') > -1 or 
                                   pathActual.find('saveSpamAssassinConfigurations') > -1 or 
                                   pathActual.find('docker') > -1 or pathActual.find('cloudAPI') > -1 or 
                                   pathActual.find('verifyLogin') > -1 or pathActual.find('submitUserCreation') > -1 or 
                                   pathActual.find('/api/') > -1 or pathActual.find('aiscanner/scheduled-scans') > -1)
                    
                    if isAPIEndpoint:
                        # Skip validation for fields that contain legitimate code/scripts
                        if key == 'content' or key == 'fileContent' or key == 'configData' or key == 'rewriteRules' or key == 'modSecRules' or key == 'contentNow' or key == 'emailMessage':
                            continue

                        # For API endpoints, still check for the most dangerous command injection characters
                        if isinstance(value, (str, bytes)) and (value.find('- -') > -1 or value.find('\n') > -1 or value.find(';') > -1 or
                            value.find('&&') > -1 or value.find('||') > -1 or value.find('|') > -1 or
                            value.find('...') > -1 or value.find("`") > -1 or value.find("$") > -1 or
                            value.find('../') > -1 or value.find('../../') > -1):
                            logging.writeToFile(request.body)
                            final_dic = {
                                'error_message': "API request contains potentially dangerous characters: `;`, `&&`, `||`, `|`, `` ` ``, `$`, `../` are not allowed.",
                                "errorMessage": "API request contains potentially dangerous characters."
                            }
                            final_json = json.dumps(final_dic)
                            return HttpResponse(final_json)
                        continue
                    if key == 'MainDashboardCSS' or key == 'ownerPassword' or key == 'scriptUrl' or key == 'CLAMAV_VIRUS' or key == "Rspamdserver" or key == 'smtpd_milters' \
                            or key == 'non_smtpd_milters' or key == 'key' or key == 'cert' or key == 'recordContentAAAA' or key == 'backupDestinations'\
                            or key == 'ports' \
                            or key == 'imageByPass' or key == 'passwordByPass' or key == 'PasswordByPass' or key == 'cronCommand' \
                            or key == 'emailMessage' or key == 'configData' or key == 'rewriteRules' \
                            or key == 'modSecRules' or key == 'recordContentTXT' or key == 'SecAuditLogRelevantStatus' \
                            or key == 'fileContent' or key == 'commands' or key == 'gitHost' or key == 'ipv6' or key == 'contentNow' \
                            or key == 'time_of_day' or key == 'notification_emails' or key == 'domains' or key == 'content':
                        continue

                    # Skip validation for API endpoints that need JSON structure characters
                    if not isAPIEndpoint and valueAlreadyChecked == 0:
                        # Only check string values, skip lists and other types
                        if (type(value) == str or type(value) == bytes) and (value.find('- -') > -1 or value.find('\n') > -1 or value.find(';') > -1 or value.find(
                                '&&') > -1 or value.find('|') > -1 or value.find('...') > -1 \
                                or value.find("`") > -1 or value.find("$") > -1 or value.find("(") > -1 or value.find(
                            ")") > -1 \
                                or value.find("'") > -1 or value.find("[") > -1 or value.find("]") > -1 or value.find(
                            "{") > -1 or value.find("}") > -1 \
                                or value.find(":") > -1 or value.find("<") > -1 or value.find(">") > -1 or value.find(
                            "&") > -1):
                            logging.writeToFile(request.body)
                            final_dic = {
                                'error_message': "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >.",
                                "errorMessage": "Data supplied is not accepted, following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                            final_json = json.dumps(final_dic)
                            return HttpResponse(final_json)
                    # Skip key validation for API endpoints that need JSON structure characters
                    if not isAPIEndpoint and (key.find(';') > -1 or key.find('&&') > -1 or key.find('|') > -1 or key.find('...') > -1 \
                            or key.find("`") > -1 or key.find("$") > -1 or key.find("(") > -1 or key.find(")") > -1 \
                            or key.find("'") > -1 or key.find("[") > -1 or key.find("]") > -1 or key.find(
                        "{") > -1 or key.find("}") > -1 \
                            or key.find(":") > -1 or key.find("<") > -1 or key.find(">") > -1 or key.find("&") > -1):
                        logging.writeToFile(request.body)
                        final_dic = {'error_message': "Data supplied is not accepted.",
                                     "errorMessage": "Data supplied is not accepted following characters are not allowed in the input ` $ & ( ) [ ] { } ; : ‘ < >."}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)

            except BaseException as msg:
                final_dic = {'error_message': f"Error: {str(msg)}",
                             "errorMessage":  f"Error: {str(msg)}"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
        else:
            # No body logging removed
            pass
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
