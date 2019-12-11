# -*- coding: utf-8 -*-


from django.shortcuts import render
from django.shortcuts import HttpResponse, redirect
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import os
import json
from plogical.mailUtilities import mailUtilities
from plogical.acl import ACLManager
from .models import PDNSStatus, SlaveServers
from .serviceManager import ServiceManager
from plogical.processUtilities import ProcessUtilities
# Create your views here.


def managePowerDNS(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()
        try:
            return render(request, 'manageServices/managePowerDNS.html', {"status": 1})

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def managePostfix(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()
        try:

            return render(request, 'manageServices/managePostfix.html', {"status": 1})

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def managePureFtpd(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()
        try:
            return render(request, 'manageServices/managePureFtpd.html', {"status": 1})
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def fetchStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                mailUtilities.checkHome()

                data = json.loads(request.body)
                service = data['service']

                if service == 'powerdns':
                    data_ret = {}
                    data_ret['status'] = 1

                    try:
                        pdns = PDNSStatus.objects.get(pk=1)
                        data_ret['installCheck'] = pdns.serverStatus
                        #data_ret['slaveIPData'] = pdns.also_notify
                    except:
                        PDNSStatus(serverStatus=1).save()
                        data_ret['installCheck'] = 1
                        #data_ret['slaveIPData'] = ''

                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                elif service == 'postfix':
                    if os.path.exists('/home/cyberpanel/postfix'):
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 1}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 0}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                elif service == 'pureftpd':
                    if os.path.exists('/home/cyberpanel/pureftpd'):
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 1}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 0}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def saveStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            if request.method == 'POST':

                data = json.loads(request.body)

                status = data['status']
                service = data['service']

                mailUtilities.checkHome()

                if service == 'powerdns':

                    if status == True:

                        pdns = PDNSStatus.objects.get(pk=1)
                        pdns.serverStatus = 1
                        pdns.type = data['dnsMode']


                        if data['dnsMode'] == 'SLAVE':
                            pdns.masterServer = data['slaveServerNS']
                            pdns.masterIP = data['masterServerIP']
                            pdns.save()
                        elif data['dnsMode'] == 'MASTER':
                            pdns.masterServer = 'NONE'
                            pdns.masterIP = 'NONE'
                            pdns.save()

                            for items in SlaveServers.objects.all():
                                items.delete()

                            slaveServer = SlaveServers(slaveServer=data['slaveServer'],
                                                       slaveServerIP=data['slaveServerIP'])
                            slaveServer.save()

                            try:
                                slaveServer = SlaveServers(slaveServer=data['slaveServer2'], slaveServerIP=data['slaveServerIP2'])
                                slaveServer.save()
                            except:
                                pass

                            try:
                                slaveServer = SlaveServers(slaveServer=data['slaveServer3'], slaveServerIP=data['slaveServerIP3'])
                                slaveServer.save()
                            except:
                                pass
                        else:
                            pdns.save()

                        if data['dnsMode'] != 'Default':
                            data['type'] = data['dnsMode']

                            sm = ServiceManager(data)
                            sm.managePDNS()

                        command = 'sudo systemctl enable pdns'
                        ProcessUtilities.executioner(command)

                        command = 'sudo systemctl restart pdns'
                        ProcessUtilities.executioner(command)

                    else:

                        pdns = PDNSStatus.objects.get(pk=1)
                        pdns.serverStatus = 0
                        pdns.save()

                        command = 'sudo systemctl stop pdns'
                        ProcessUtilities.executioner(command)

                        command = 'sudo systemctl disable pdns'
                        ProcessUtilities.executioner(command)


                elif service == 'postfix':

                    servicePath = '/home/cyberpanel/postfix'
                    if status == True:
                        writeToFile = open(servicePath, 'w+')
                        writeToFile.close()
                        command = 'sudo systemctl start postfix'
                        ProcessUtilities.executioner(command)
                    else:
                        command = 'sudo systemctl stop postfix'
                        ProcessUtilities.executioner(command)

                        command = 'sudo systemctl disable postfix'
                        ProcessUtilities.executioner(command)

                        try:
                            os.remove(servicePath)
                        except:
                            pass

                elif service == 'pureftpd':
                    if os.path.exists("/etc/lsb-release"):
                        serviceName = 'pure-ftpd-mysql'
                    else:
                        serviceName = 'pure-ftpd'

                    servicePath = '/home/cyberpanel/pureftpd'
                    if status == True:
                        writeToFile = open(servicePath, 'w+')
                        writeToFile.close()
                        command = 'sudo systemctl start ' + serviceName
                        ProcessUtilities.executioner(command)
                    else:
                        command = 'sudo systemctl stop ' + serviceName
                        ProcessUtilities.executioner(command)

                        command = 'sudo systemctl disable ' + serviceName
                        ProcessUtilities.executioner(command)

                        try:
                            os.remove(servicePath)
                        except:
                            pass

                data_ret = {'status': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)