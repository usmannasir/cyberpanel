# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
from loginSystem.views import loadLoginPage
from loginSystem.models import Administrator
import json
from plogical import hashPassword
from plogical import CyberCPLogFileWriter as logging

# Create your views here.

def loadUserHome(request):
    try:
        val = request.session['userID']
        try:

            admin = Administrator.objects.get(pk=val)

            return render(request, 'userManagment/index.html',{"type":admin.type})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def viewProfile(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        AdminData = {}

        AdminData['userName'] = admin.userName
        AdminData['firstName'] = admin.firstName
        AdminData['lastName'] = admin.lastName
        AdminData['userAccountsLimit'] = admin.initUserAccountsLimit
        AdminData['websitesLimit'] = admin.initWebsitesLimit
        AdminData['email'] = admin.email
        AdminData['typeNumeric'] = admin.type

        if admin.type == 1:
            AdminData['type'] = "root"
        elif admin.type == 2:
            AdminData['type'] = "Reseller"
        else:
            AdminData['type'] = "User"

        return render(request, 'userManagment/userProfile.html',AdminData)
    except KeyError:
        return redirect(loadLoginPage)


def createUser(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

        try:
            adminType = admin.type

            return render(request, 'userManagment/createUser.html',{"adminType":adminType})

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("Look for errors in CyberCP Main Log File")

    except KeyError:
        return redirect(loadLoginPage)


def submitUserCreation(request):
    try:
        val = request.session['userID']
        try:

            currentAdmin = Administrator.objects.get(pk=val)

            childUsers = Administrator.objects.filter(owner=currentAdmin.pk).count()

            if currentAdmin.type == 1:
                pass

            else:
                if currentAdmin.initWebsitesLimit == 0:
                    pass

                elif currentAdmin.initUserAccountsLimit == childUsers:
                    data_ret = {'createStatus': 0,
                                'error_message': "Reached Maximum User Creation Limit"}

                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)
                else:
                    pass


            if request.method == 'POST':
                data = json.loads(request.body)
                firstName = data['firstName']
                lastName = data['lastName']
                email = data['email']
                userName = data['userName']
                password = data['password']

                password = hashPassword.hash_password(password)

                accountType = data['accountType']

                if accountType == "Admin":

                    newAdmin = Administrator(firstName=firstName,
                                            lastName=lastName,
                                            email=email,
                                            type=1,
                                            userName=userName,
                                            password=password,
                                            initWebsitesLimit=0,
                                            owner=currentAdmin.pk
                                            )
                    newAdmin.save()
                    currentAdmin.save()

                    data_ret = {'createStatus': 1,
                                'error_message': "None"}

                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                elif accountType == "Normal User":

                    newAdmin = Administrator(firstName=firstName,
                                            lastName=lastName,
                                            email=email,
                                            type=3,
                                            userName=userName,
                                            password=password,
                                            initWebsitesLimit=0,
                                            owner=currentAdmin.pk
                                            )
                    newAdmin.save()
                    currentAdmin.save()

                    data_ret = {'createStatus': 1,
                                'error_message': "None"}

                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)
                else:
                    websitesLimit = data['websitesLimit']
                    userAccountsLimit = 0

                    newAdmin = Administrator(firstName=firstName,
                                             lastName=lastName,
                                             email=email,
                                             type=2,
                                             userName=userName,
                                             password=password,
                                             initWebsitesLimit=websitesLimit,
                                             initUserAccountsLimit=userAccountsLimit,
                                             owner=currentAdmin.pk
                                             )
                    newAdmin.save()
                    currentAdmin.save()

                    data_ret = {'createStatus': 1,
                                'error_message': "None"}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

        except BaseException, msg:
            data_ret = {'createStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'createStatus': 0, 'error_message': "Not logged in as admin",}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def modifyUsers(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)
        adminNames = []

        if admin.type == 1:
            admins = Administrator.objects.all()
            adminType = 1
            for items in admins:
                adminNames.append(items.userName)
        elif admin.type == 2:
            admins = Administrator.objects.filter(owner=admin.pk)
            adminType = 2
            for items in admins:
                adminNames.append(items.userName)
        else:
            adminType = 3
            adminNames.append(admin.userName)

        return render(request, 'userManagment/modifyUser.html',{"acctNames":adminNames,"adminType":adminType})
    except KeyError:
        return redirect(loadLoginPage)

def fetchUserDetails(request):
    try:
        val = request.session['userID']
        try:

            currentAdmin = Administrator.objects.get(pk=val)

            if request.method == 'POST':
                data = json.loads(request.body)
                accountUsername = data['accountUsername']

                user = Administrator.objects.get(userName=accountUsername)

                firstName = user.firstName
                lastName = user.lastName
                email = user.email

                if user.type == 1:
                    accountType = "Administrator"
                elif user.type == 2:
                    accountType = "Reseller"
                else:
                    accountType = "Normal User"


                userAccountsLimit = user.initUserAccountsLimit
                websitesLimit = user.initWebsitesLimit

                userDetails = {"firstName":firstName,
                               "lastName": lastName,
                               "email": email,
                               "accountType": accountType,
                               "userAccountsLimit": userAccountsLimit,
                               "websitesLimit": websitesLimit}

                data_ret = {'fetchStatus': 1, 'error_message': 'None',"userDetails":userDetails}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



        except BaseException, msg:
            data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'fetchStatus': 0, 'error_message': "Not logged in as admin",}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def saveModifications(request):
    try:
        val = request.session['userID']
        try:

            if request.method == 'POST':
                data = json.loads(request.body)
                accountUsername = data['accountUsername']
                firstName = data['firstName']
                lastName = data['lastName']
                email = data['email']

                admin = Administrator.objects.get(pk=val)
                user = Administrator.objects.get(userName=accountUsername)

                password = hashPassword.hash_password(data['password'])

                if admin.type != 1:
                    if admin != user:
                        data_ret = {'saveStatus': 1, 'error_message': 'Not enough privileges'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)


                if user.type == 1:
                    userAccountsLimit = 0
                    websitesLimit = 0

                    user.firstName = firstName
                    user.lastName = lastName
                    user.email = email
                    user.password = password
                    user.initWebsitesLimit = websitesLimit
                    user.initUserAccountsLimit = userAccountsLimit
                    user.type = 1

                    user.save()

                    data_ret = {'saveStatus': 1, 'error_message': 'None'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)



                if data['accountType'] == "Reseller":
                    userAccountsLimit = 0
                    websitesLimit = 0

                    user.firstName = firstName
                    user.lastName = lastName
                    user.email = email
                    user.password = password
                    user.initWebsitesLimit = websitesLimit
                    user.initUserAccountsLimit = userAccountsLimit
                    user.type = 2

                    user.save()

                elif data['accountType'] == "Normal User":

                    user.firstName = firstName
                    user.lastName = lastName
                    user.email = email
                    user.password = password
                    user.initWebsitesLimit = 0
                    user.type = 3

                    user.save()
                else:
                    userAccountsLimit = 0
                    websitesLimit = 0

                    user.firstName = firstName
                    user.lastName = lastName
                    user.email = email
                    user.password = password
                    user.initWebsitesLimit = websitesLimit
                    user.initUserAccountsLimit = userAccountsLimit
                    user.type = 1

                    user.save()

                data_ret = {'saveStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



        except BaseException, msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'saveStatus': 0, 'error_message': "Not logged in as admin",}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def deleteUser(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

        if admin.type == 1:
            admins = Administrator.objects.all()
            adminNames = []
            for items in admins:
                if not items.userName == "admin":
                    adminNames.append(items.userName)
        else:
            admins = Administrator.objects.filter(owner=admin.pk)
            adminNames = []
            for items in admins:
                adminNames.append(items.userName)

        return render(request, 'userManagment/deleteUser.html',{"acctNames":adminNames})
    except KeyError:
        return redirect(loadLoginPage)

def submitUserDeletion(request):
    try:
        val = request.session['userID']
        try:

            if request.method == 'POST':
                data = json.loads(request.body)
                accountUsername = data['accountUsername']

                admin = Administrator.objects.get(pk=val)

                if admin.type == 1:
                    user = Administrator.objects.get(userName=accountUsername)
                    user.delete()

                    data_ret = {'deleteStatus': 1, 'error_message': 'None'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'deleteStatus': 1, 'error_message': 'Not enough privileges'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)



        except BaseException, msg:
            data_ret = {'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError:
        data_ret = {'deleteStatus': 0, 'error_message': "Not logged in as admin",}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
