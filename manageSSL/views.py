#!/usr/local/CyberCP/bin/python
import os
import sys
import django

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from django.shortcuts import render, HttpResponse
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.sslReconcile import SSLReconcile
from plogical.sslUtilities import sslUtilities
from loginSystem.models import Administrator
import json


def sslReconcile(request):
    """SSL Reconciliation interface"""
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)

        # Principal admin (userName == 'admin') always allowed
        if getattr(admin, 'userName', None) == 'admin':
            return render(request, 'manageSSL/sslReconcile.html', {
                'acls': currentACL,
                'admin': admin
            })
        # Allow if has sslReconcile, or full admin, or manageSSL permission
        if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
            if currentACL.get('admin') != 1 and currentACL.get('manageSSL') != 1:
                return ACLManager.loadErrorJson('sslReconcile', 0)

        return render(request, 'manageSSL/sslReconcile.html', {
            'acls': currentACL,
            'admin': admin
        })

    except KeyError:
        data_ret = {
            'status': 0,
            'errorMessage': 'Session expired or not logged in. Please log in again.',
            'error_message': 'Session expired or not logged in. Please log in again.',
            'sslReconcile': 0
        }
        return HttpResponse(json.dumps(data_ret))
    except BaseException as msg:
        logging.writeToFile(str(msg) + " [sslReconcile]")
        return ACLManager.loadErrorJson('sslReconcile', 0)


def reconcileAllSSL(request):
    """Reconcile SSL for all domains"""
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)

        if getattr(admin, 'userName', None) != 'admin':
            if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
                if currentACL.get('admin') != 1 and currentACL.get('manageSSL') != 1:
                    return ACLManager.loadErrorJson('sslReconcile', 0)

        # Run SSL reconciliation
        success = SSLReconcile.reconcile_all()
        
        if success:
            data_ret = {'reconcileStatus': 1, 'error_message': "SSL reconciliation completed successfully"}
        else:
            data_ret = {'reconcileStatus': 0, 'error_message': "SSL reconciliation failed. Check logs for details."}

        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except KeyError:
        data_ret = {'reconcileStatus': 0, 'error_message': 'Session expired or not logged in. Please log in again.'}
        return HttpResponse(json.dumps(data_ret))
    except BaseException as msg:
        logging.writeToFile(str(msg) + " [reconcileAllSSL]")
        data_ret = {'reconcileStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def reconcileDomainSSL(request):
    """Reconcile SSL for a specific domain"""
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)

        if getattr(admin, 'userName', None) != 'admin':
            if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
                if currentACL.get('admin') != 1 and currentACL.get('manageSSL') != 1:
                    return ACLManager.loadErrorJson('sslReconcile', 0)

        domain = request.POST.get('domain')
        if not domain:
            data_ret = {'reconcileStatus': 0, 'error_message': "Domain not specified"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        # Run SSL reconciliation for specific domain
        success = SSLReconcile.reconcile_domain(domain)
        
        if success:
            data_ret = {'reconcileStatus': 1, 'error_message': f"SSL reconciliation completed for {domain}"}
        else:
            data_ret = {'reconcileStatus': 0, 'error_message': f"SSL reconciliation failed for {domain}. Check logs for details."}

        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except KeyError:
        data_ret = {'reconcileStatus': 0, 'error_message': 'Session expired or not logged in. Please log in again.'}
        return HttpResponse(json.dumps(data_ret))
    except BaseException as msg:
        logging.writeToFile(str(msg) + " [reconcileDomainSSL]")
        data_ret = {'reconcileStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def fixACMEContexts(request):
    """Fix ACME challenge contexts for all domains"""
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)

        if getattr(admin, 'userName', None) != 'admin':
            if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
                if currentACL.get('admin') != 1 and currentACL.get('manageSSL') != 1:
                    return ACLManager.loadErrorJson('sslReconcile', 0)

        from websiteFunctions.models import Websites
        
        fixed_count = 0
        failed_domains = []
        
        for website in Websites.objects.all():
            if sslUtilities.fix_acme_challenge_context(website.domain):
                fixed_count += 1
            else:
                failed_domains.append(website.domain)
        
        if failed_domains:
            data_ret = {
                'reconcileStatus': 1, 
                'error_message': f"Fixed ACME contexts for {fixed_count} domains. Failed: {', '.join(failed_domains)}"
            }
        else:
            data_ret = {
                'reconcileStatus': 1, 
                'error_message': f"Fixed ACME contexts for {fixed_count} domains successfully"
            }

        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except KeyError:
        data_ret = {'reconcileStatus': 0, 'error_message': 'Session expired or not logged in. Please log in again.'}
        return HttpResponse(json.dumps(data_ret))
    except BaseException as msg:
        logging.writeToFile(str(msg) + " [fixACMEContexts]")
        data_ret = {'reconcileStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


# -*- coding: utf-8 -*-

from plogical.httpProc import httpProc
from websiteFunctions.models import Websites, ChildDomains
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from django.http import HttpResponse
import json
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities


# Create your views here.

def loadSSLHome(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    proc = httpProc(request, 'manageSSL/index.html',
                    currentACL, 'admin')
    return proc.render()


def manageSSL(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    websitesName = ACLManager.findAllSites(currentACL, userID)
    proc = httpProc(request, 'manageSSL/manageSSL.html',
                    {'websiteList': websitesName}, 'manageSSL')
    return proc.render()


def v2ManageSSL(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    websitesName = ACLManager.findAllSites(currentACL, userID)

    data = {}

    if ACLManager.CheckForPremFeature('all'):
        data['PremStat'] = 1
    else:
        data['PremStat'] = 0

    if request.method == 'POST':
        SAVED_CF_Key = request.POST.get('SAVED_CF_Key')
        SAVED_CF_Email = request.POST.get('SAVED_CF_Email')
        from plogical.dnsUtilities import DNS
        DNS.ConfigureCloudflareInAcme(SAVED_CF_Key, SAVED_CF_Email)
        data['SaveSuccess'] = 1

    RetStatus, SAVED_CF_Key, SAVED_CF_Email = ACLManager.FetchCloudFlareAPIKeyFromAcme()
    from plogical.dnsUtilities import DNS
    DNS.ConfigurePowerDNSInAcme()

    data['SAVED_CF_Key'] = SAVED_CF_Key
    data['SAVED_CF_Email'] = SAVED_CF_Email
    data['websiteList'] = websitesName

    proc = httpProc(request, 'manageSSL/v2ManageSSL.html',
                    data, 'manageSSL')
    return proc.render()


def v2IssueSSL(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        try:
            if ACLManager.CheckForPremFeature('all'):
                if request.method == 'POST':
                    currentACL = ACLManager.loadedACL(userID)

                    if currentACL['admin'] == 1:
                        pass
                    elif currentACL['manageSSL'] == 1:
                        pass
                    else:
                        return ACLManager.loadErrorJson('SSL', 0)

                    data = json.loads(request.body)
                    virtualHost = data['virtualHost']

                    if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                        pass
                    else:
                        return ACLManager.loadErrorJson()

                    try:
                        website = ChildDomains.objects.get(domain=virtualHost)
                        adminEmail = website.master.adminEmail
                        path = website.path
                    except:
                        website = Websites.objects.get(domain=virtualHost)
                        adminEmail = website.adminEmail
                        path = "/home/" + virtualHost + "/public_html"

                    ## ssl issue

                    execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                    execPath = execPath + " issueSSLv2 --virtualHostName " + virtualHost + " --administratorEmail " + adminEmail + " --path " + path + " --force 1"
                    output = ProcessUtilities.outputExecutioner(execPath)

                    if output.find("1,") > -1:
                        ## ssl issue ends

                        website.ssl = 1
                        website.save()

                        # Extract detailed logs from output
                        logs = output.split("1,", 1)[1] if "1," in output else output

                        data_ret = {'status': 1, "SSL": 1,
                                    'error_message': "None", 'sslLogs': logs, 'fullOutput': output}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        # Parse error details from output
                        error_message = output
                        detailed_error = "SSL issuance failed"

                        # Check for common ACME errors
                        if "Rate limit" in output or "rate limit" in output:
                            detailed_error = "Let's Encrypt rate limit exceeded. Please wait before retrying."
                        elif "DNS problem" in output or "NXDOMAIN" in output:
                            detailed_error = "DNS validation failed. Please ensure your domain points to this server."
                        elif "Connection refused" in output or "Connection timeout" in output:
                            detailed_error = "Could not connect to ACME server. Check your firewall settings."
                        elif "Unauthorized" in output or "authorization" in output:
                            detailed_error = "Domain authorization failed. Verify domain ownership and DNS settings."
                        elif "CAA record" in output:
                            detailed_error = "CAA record prevents issuance. Check your DNS CAA records."
                        elif "Challenge failed" in output or "challenge failed" in output:
                            detailed_error = "ACME challenge failed. Ensure port 80 is accessible and .well-known path is not blocked."
                        elif "Invalid response" in output:
                            detailed_error = "Invalid response from ACME challenge. Check your web server configuration."
                        else:
                            # Try to extract the actual error message
                            if "0," in output:
                                error_parts = output.split("0,", 1)
                                if len(error_parts) > 1:
                                    detailed_error = error_parts[1].strip()

                        data_ret = {'status': 0, "SSL": 0,
                                    'error_message': detailed_error,
                                    'sslLogs': output,
                                    'fullOutput': output,
                                    'technicalDetails': error_message}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {'status': 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def issueSSL(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        try:
            if request.method == 'POST':
                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['manageSSL'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('SSL', 0)

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                try:
                    website = ChildDomains.objects.get(domain=virtualHost)
                    adminEmail = website.master.adminEmail
                    path = website.path
                except:
                    website = Websites.objects.get(domain=virtualHost)
                    adminEmail = website.adminEmail
                    path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " issueSSL --virtualHostName " + virtualHost + " --administratorEmail " + adminEmail + " --path " + path + " --force 1"
                output = ProcessUtilities.outputExecutioner(execPath) or ''

                # python-cloudflare 2.20.* may print PendingDeprecationWarning to stderr,
                # which is merged into this string. Prefer an explicit success token.
                ssl_ok = ('1,None' in output)
                if not ssl_ok:
                    cleaned = '\n'.join(
                        line for line in output.splitlines()
                        if 'PendingDeprecationWarning' not in line
                        and 'Python package \'cloudflare\'' not in line
                        and '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' not in line
                    ).strip()
                    data_ret = {'status': 0, "SSL": 0,
                                'error_message': cleaned or output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                ## ssl issue ends

                website.ssl = 1
                website.save()

                data_ret = {'status': 1, "SSL": 1,
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {'status': 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def sslForHostName(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    websitesName = ACLManager.findAllSites(currentACL, userID, 1)
    proc = httpProc(request, 'manageSSL/sslForHostName.html',
                    {'websiteList': websitesName}, 'hostnameSSL')
    return proc.render()


def obtainHostNameSSL(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['hostnameSSL'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('SSL', 0)

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                try:
                    website = Websites.objects.get(domain=virtualHost)
                    path = "/home/" + virtualHost + "/public_html"
                except:
                    website = ChildDomains.objects.get(domain=virtualHost)
                    path = website.path

                admin = Administrator.objects.get(pk=userID)

                if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                ## ssl issue

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " issueSSLForHostName --virtualHostName " + virtualHost + " --path " + path
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {"status": 1, "SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {"status": 0, "SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                    ## ssl issue ends

        except BaseException as msg:
            data_ret = {"status": 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"status": 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def sslForMailServer(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)

    websitesName = ACLManager.findAllSites(currentACL, userID)
    websitesName = websitesName + ACLManager.findChildDomains(websitesName)

    proc = httpProc(request, 'manageSSL/sslForMailServer.html',
                    {'websiteList': websitesName}, 'mailServerSSL')
    return proc.render()


def obtainMailServerSSL(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['mailServerSSL'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('SSL', 0)

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                admin = Administrator.objects.get(pk=userID)
                if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " issueSSLForMailServer --virtualHostName " + virtualHost + " --path " + path
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {"status": 1, "SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {"status": 0, "SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                    ## ssl issue ends


        except BaseException as msg:
            data_ret = {"status": 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError as msg:
        data_ret = {"status": 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def getSSLDetails(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        try:
            if request.method == 'POST':
                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['manageSSL'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('SSL', 0)

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                try:
                    website = ChildDomains.objects.get(domain=virtualHost)
                except:
                    website = Websites.objects.get(domain=virtualHost)

                try:
                    import OpenSSL
                    from datetime import datetime
                    filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % (virtualHost)
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                           open(filePath, 'rb').read())
                    expireData = x509.get_notAfter().decode('ascii')
                    finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')

                    now = datetime.now()
                    diff = finalDate - now

                    data_ret = {
                        'status': 1,
                        'hasSSL': True,
                        'days': str(diff.days),
                        'authority': x509.get_issuer().get_components()[1][1].decode('utf-8'),
                        'expiryDate': finalDate.strftime('%Y-%m-%d %H:%M:%S')
                    }

                    if data_ret['authority'] == 'Denial':
                        data_ret['authority'] = 'SELF-SIGNED SSL'

                except BaseException as msg:
                    data_ret = {
                        'status': 1,
                        'hasSSL': False,
                        'error_message': str(msg)
                    }

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {'status': 0, 'error_message': 'Not logged in'}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)