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
import json


def sslReconcile(request):
    """SSL Reconciliation interface"""
    try:
        currentACL = ACLManager.loadedACL(request.user.pk)
        admin = ACLManager.loadedAdmin(request.user.pk)

        if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
            return ACLManager.loadErrorJson('sslReconcile', 0)

        return render(request, 'manageSSL/sslReconcile.html', {
            'acls': currentACL,
            'admin': admin
        })

    except BaseException as msg:
        logging.writeToFile(str(msg) + " [sslReconcile]")
        return ACLManager.loadErrorJson('sslReconcile', 0)


def reconcileAllSSL(request):
    """Reconcile SSL for all domains"""
    try:
        currentACL = ACLManager.loadedACL(request.user.pk)
        admin = ACLManager.loadedAdmin(request.user.pk)

        if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
            return ACLManager.loadErrorJson('sslReconcile', 0)

        # Run SSL reconciliation
        success = SSLReconcile.reconcile_all()
        
        if success:
            data_ret = {'reconcileStatus': 1, 'error_message': "SSL reconciliation completed successfully"}
        else:
            data_ret = {'reconcileStatus': 0, 'error_message': "SSL reconciliation failed. Check logs for details."}

        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        logging.writeToFile(str(msg) + " [reconcileAllSSL]")
        data_ret = {'reconcileStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def reconcileDomainSSL(request):
    """Reconcile SSL for a specific domain"""
    try:
        currentACL = ACLManager.loadedACL(request.user.pk)
        admin = ACLManager.loadedAdmin(request.user.pk)

        if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
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

    except BaseException as msg:
        logging.writeToFile(str(msg) + " [reconcileDomainSSL]")
        data_ret = {'reconcileStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def fixACMEContexts(request):
    """Fix ACME challenge contexts for all domains"""
    try:
        currentACL = ACLManager.loadedACL(request.user.pk)
        admin = ACLManager.loadedAdmin(request.user.pk)

        if ACLManager.currentContextPermission(currentACL, 'sslReconcile') == 0:
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

    except BaseException as msg:
        logging.writeToFile(str(msg) + " [fixACMEContexts]")
        data_ret = {'reconcileStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)