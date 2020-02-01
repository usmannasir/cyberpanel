# -*- coding: utf-8 -*-


from django.shortcuts import render
from .models import Administrator
from plogical import hashPassword
import json
from packages.models import Package
from firewall.models import FirewallRules
from baseTemplate.models import version
from plogical.getSystemInformation import SystemInformation
from .models import ACL
from plogical.acl import ACLManager
from django.views.decorators.csrf import ensure_csrf_cookie
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from django.conf import settings
from django.http import HttpResponse
from django.utils import translation
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
                    elif data['languageSelection'] == "Chinese":
                        user_Language = "cn"
                    elif data['languageSelection'] == "Bulgarian":
                        user_Language = "br"
                    elif data['languageSelection'] == "Portuguese":
                        user_Language = "pt"
                    elif data['languageSelection'] == "Japanese":
                        user_Language = "ja"
                    elif data['languageSelection'] == "Bosnian":
                        user_Language = "bs"
                    elif data['languageSelection'] == "Greek":
                        user_Language = "gr"
                    elif data['languageSelection'] == "Russian":
                        user_Language = "ru"
                    elif data['languageSelection'] == "Turkish":
                        user_Language = "tr"
                    elif data['languageSelection'] == "Spanish":
                        user_Language = "es"
                    elif data['languageSelection'] == "French":
                        user_Language = "fr"
                    elif data['languageSelection'] == "Polish":
                        user_Language = "pl"
                    elif data['languageSelection'] == "Vietnamese":
                        user_Language = "vi"
                    elif data['languageSelection'] == "Italian":
                        user_Language = "it"
                    elif data['languageSelection'] == "German":
                        user_Language = "de"

                    translation.activate(user_Language)
                    response = HttpResponse()
                    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_Language)
                except:
                    user_Language = 'en'
                    translation.activate(user_Language)
                    response = HttpResponse()
                    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_Language)


            admin = Administrator.objects.get(userName=username)

            if admin.state == 'SUSPENDED':
                data = {'userID': 0, 'loginStatus': 0, 'error_message': 'Account currently suspended.'}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, password):

                request.session['userID'] = admin.pk

                ipAddr = request.META.get('REMOTE_ADDR')

                if ipAddr.find(':') > -1:
                    ipAddr = ipAddr.split(':')[:3]
                    request.session['ipAddr'] = ''.join(ipAddr)
                else:
                    request.session['ipAddr'] = request.META.get('REMOTE_ADDR')

                request.session.set_expiry(43200)
                data = {'userID': admin.pk, 'loginStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data)
                response.write(json_data)
                return response

            else:
                data = {'userID': 0, 'loginStatus': 0, 'error_message': "wrong-password"}
                json_data = json.dumps(data)
                response.write(json_data)
                return response

        except BaseException as msg:
            data = {'userID': 0, 'loginStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data)
            return HttpResponse(json_data)

@ensure_csrf_cookie
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
        noOfRules = FirewallRules.objects.count()

        if noOfRules == 0:
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

            newFWRule = FirewallRules(name="POP3S", proto="tcp", port="995")
            newFWRule.save()

            newFWRule = FirewallRules(name="quic", proto="udp", port="443")
            newFWRule.save()

        if numberOfAdministrator == 0:
            ACLManager.createDefaultACLs()
            acl = ACL.objects.get(name='admin')

            token = hashPassword.generateToken('admin', '1234567')

            email = 'usman@cyberpersons.com'
            admin = Administrator(userName="admin", password=password, type=1,email=email,
                                  firstName="Cyber",lastName="Panel", acl=acl, token=token)
            admin.save()

            vers = version(currentVersion="1.9", build=4)
            vers.save()

            package = Package(admin=admin, packageName="Default", diskSpace=1000,
                                  bandwidth=1000, ftpAccounts=1000, dataBases=1000,
                                  emailAccounts=1000,allowedDomains=20)
            package.save()
            return render(request, 'loginSystem/login.html', {})
        else:
            return render(request, 'loginSystem/login.html', {})

@ensure_csrf_cookie
def logout(request):
    try:
        del request.session['userID']
        return render(request, 'loginSystem/login.html', {})
    except:
        return render(request,'loginSystem/login.html',{})
