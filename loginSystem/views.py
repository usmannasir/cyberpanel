# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
from models import Administrator
from plogical import hashPassword
import json
from packages.models import Package
from firewall.models import FirewallRules
from baseTemplate.models import version
from plogical.getSystemInformation import SystemInformation
from django.utils.translation import LANGUAGE_SESSION_KEY
import CyberCP.settings as settings
from models import ACL
from plogical.acl import ACLManager
# Create your views here.

def verifyLogin(request):
    try:
        userID = request.session['userID']
        data = {'userID' : userID, 'loginStatus': 1, 'error_message':"None"}
        json_data = json.dumps(data)
        return HttpResponse(json_data)
    except KeyError:
        username = "not logged in"
        password = ""

        try:
            if request.method == "POST":
                data = json.loads(request.body)

                username = data['username']
                password = data['password']

                try:
                    if data['languageSelection'] == "English":
                        user_Language = "en"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Chinese":
                        user_Language = "cn"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Bulgarian":
                        user_Language = "br"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Portuguese":
                        user_Language = "pt"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Japanese":
                        user_Language = "ja"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Bosnian":
                        user_Language = "bs"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Greek":
                        user_Language = "gr"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Russian":
                        user_Language = "ru"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Turkish":
                        user_Language = "tr"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Spanish":
                        user_Language = "es"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "French":
                        user_Language = "fr"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Polish":
                        user_Language = "pl"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                    elif data['languageSelection'] == "Vietnamese":
                        user_Language = "vi"
                        request.session[LANGUAGE_SESSION_KEY] = user_Language
                        request.COOKIES['django_language'] = user_Language
                        settings.LANGUAGE_CODE = user_Language
                except:
                    request.session[LANGUAGE_SESSION_KEY] = "en"
                    request.COOKIES['django_language'] = "en"
                    settings.LANGUAGE_CODE = "en"


            admin = Administrator.objects.get(userName=username)

            if hashPassword.check_password(admin.password, password):

                request.session['userID'] = admin.pk
                data = {'userID': admin.pk, 'loginStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

            else:
                data = {'userID': 0, 'loginStatus': 0, 'error_message': "wrong-password"}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

        except BaseException,msg:
            data = {'userID': 0, 'loginStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

def loadLoginPage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        cpuRamDisk = SystemInformation.cpuRamDisk()

        if currentACL['admin'] == 1:
            admin = 1
        else:
            admin = 0

        finaData = {"admin": admin, 'ramUsage': cpuRamDisk['ramUsage'], 'cpuUsage': cpuRamDisk['cpuUsage'],
                    'diskUsage': cpuRamDisk['diskUsage']}

        return render(request, 'baseTemplate/homePage.html', finaData)
    except KeyError:

        numberOfAdministrator = Administrator.objects.count()
        password = hashPassword.hash_password('1234567')

        if numberOfAdministrator == 0:
            ACLManager.createDefaultACLs()
            acl = ACL.objects.get(name='admin')

            token = hashPassword.generateToken('admin', '1234567')

            email = 'usman@cyberpersons.com'
            admin = Administrator(userName="admin", password=password, type=1,email=email,
                                  firstName="Cyber",lastName="Panel", acl=acl, token=token)
            admin.save()

            vers = version(currentVersion="1.7", build=7)
            vers.save()

            package = Package(admin=admin, packageName="Default", diskSpace=1000,
                                  bandwidth=1000, ftpAccounts=1000, dataBases=1000,
                                  emailAccounts=1000,allowedDomains=20)
            package.save()

            newFWRule = FirewallRules(name="panel", proto="tcp", port="8090")
            newFWRule.save()

            newFWRule = FirewallRules(name="http", proto="tcp", port="80")
            newFWRule.save()

            newFWRule = FirewallRules(name="https", proto="tcp", port="443")
            newFWRule.save()

            newFWRule = FirewallRules(name="ftp", proto="tcp", port="21")
            newFWRule.save()

            newFWRule = FirewallRules(name="smtp", proto="tcp", port="25")
            newFWRule.save()

            newFWRule = FirewallRules(name="smtps", proto="tcp", port="587")
            newFWRule.save()

            newFWRule = FirewallRules(name="ssmtp", proto="tcp", port="465")
            newFWRule.save()

            newFWRule = FirewallRules(name="pop3", proto="tcp", port="110")
            newFWRule.save()

            newFWRule = FirewallRules(name="imap", proto="tcp", port="143")
            newFWRule.save()

            newFWRule = FirewallRules(name="simap", proto="tcp", port="993")
            newFWRule.save()

            newFWRule = FirewallRules(name="dns", proto="udp", port="53")
            newFWRule.save()

            newFWRule = FirewallRules(name="dnstcp", proto="tcp", port="53")
            newFWRule.save()

            newFWRule = FirewallRules(name="ftptls", proto="tcp", port="40110-40210")
            newFWRule.save()

            return render(request, 'loginSystem/login.html', {})
        else:
            return render(request, 'loginSystem/login.html', {})

def logout(request):
    try:
        del request.session['userID']
        return render(request, 'loginSystem/login.html', {})
    except:
        return render(request,'loginSystem/login.html',{})
