# -*- coding: utf-8 -*-

from django.shortcuts import HttpResponse, redirect
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import os
import json
import shlex

from plogical.httpProc import httpProc
from plogical.mailUtilities import mailUtilities
from plogical.acl import ACLManager
from .models import PDNSStatus, SlaveServers
from .serviceManager import ServiceManager
from plogical.processUtilities import ProcessUtilities
from .application_detection import managed_apps_os_support
from .application_page_meta import (
    build_manage_applications_page_data,
    get_application_meta_response_dict,
)
# Create your views here.

def managePowerDNS(request):
    data = {}
    data['status'] = 1

    try:
        pdnsStatus = PDNSStatus.objects.get(pk=1)
    except:
        pdnsStatus = PDNSStatus(type='NATIVE', serverStatus=1)
        pdnsStatus.save()

    if pdnsStatus.type == 'MASTER':
        counter = 1

        for items in SlaveServers.objects.all():

            if counter == 1:
                data['slaveServer'] = items.slaveServer
                data['slaveServerIP'] = items.slaveServerIP
            else:
                data['slaveServer%s' % (str(counter))] = items.slaveServer
                data['slaveServerIP%s' % (str(counter))] = items.slaveServerIP

            counter = counter + 1
    else:
        data['slaveServerNS'] = pdnsStatus.masterServer
        data['masterServerIP'] = pdnsStatus.masterIP

    # UI shows Default/MASTER/SLAVE; DB may store NATIVE for default mode
    if pdnsStatus.type in ('MASTER', 'SLAVE'):
        data['dnsMode'] = pdnsStatus.type
    else:
        data['dnsMode'] = 'Default'
    data['pdnsEnabled'] = 1 if int(pdnsStatus.serverStatus or 0) == 1 else 0

    proc = httpProc(request, 'manageServices/managePowerDNS.html',
                    data, 'admin')
    return proc.render()

def managePostfix(request):
    proc = httpProc(request, 'manageServices/managePostfix.html',
                    {"status": 1}, 'admin')
    return proc.render()

def managePureFtpd(request):
    proc = httpProc(request, 'manageServices/managePureFtpd.html',
                    {"status": 1}, 'admin')
    return proc.render()

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
                        if pdns.type in ('MASTER', 'SLAVE'):
                            data_ret['dnsMode'] = pdns.type
                        else:
                            data_ret['dnsMode'] = 'Default'
                        #data_ret['slaveIPData'] = pdns.also_notify
                    except:
                        PDNSStatus(serverStatus=1).save()
                        data_ret['installCheck'] = 1
                        data_ret['dnsMode'] = 'Default'
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

                    servicePath = '/home/cyberpanel/powerdns'
                    if status == True:
                        writeToFile = open(servicePath, 'w+')
                        writeToFile.close()

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

                        try:
                            os.remove(servicePath)
                        except:
                            pass


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

def manageApplications(request):
    services, application_meta_bootstrap_json = build_manage_applications_page_data(
        '8', '4', allow_cold_fetch=False
    )

    proc = httpProc(
        request,
        'manageServices/applications.html',
        {
            'services': services,
            'application_meta_bootstrap_json': application_meta_bootstrap_json,
        },
        'admin',
    )
    return proc.render()


def applicationMeta(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson()

        data = {}
        if request.method == 'POST':
            data = json.loads(request.body)

        requested_major = str(data.get('esMajor', '8'))
        if requested_major not in ('7', '8', '9'):
            requested_major = '8'

        requested_rmq_stream = str(data.get('rabbitmqStream', '4')).strip()
        if requested_rmq_stream not in ('3', '4'):
            requested_rmq_stream = '4'

        response_data = get_application_meta_response_dict(
            requested_major, requested_rmq_stream
        )

        return HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            content_type='application/json; charset=utf-8',
        )

    except BaseException as msg:
        return HttpResponse(
            json.dumps({'status': 0, 'error_message': str(msg)}, ensure_ascii=False),
            content_type='application/json; charset=utf-8',
        )

def removeInstall(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:
            data = json.loads(request.body)

            status = data['status']
            appName = data['appName']
            version = str(data.get('version', 'latest')).strip() or 'latest'
            esMajor = str(data.get('esMajor', '8')).strip() or '8'
            if esMajor not in ('7', '8', '9'):
                esMajor = '8'
            rabbitmqStream = str(data.get('rabbitmqStream', '4')).strip() or '4'
            if rabbitmqStream not in ('3', '4'):
                rabbitmqStream = '4'
            confirmAction = bool(data.get('confirmAction', False))

            support = managed_apps_os_support()
            if not support['supported']:
                data_ret = {'status': 0, 'error_message': support['reason']}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if status in ('Removing', 'Upgrading') and not confirmAction:
                data_ret = {'status': 0, 'error_message': 'Action confirmation is required.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if appName == 'Elasticsearch':
                if status == 'Installing':
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app Elasticsearch --action install --version {0} --esMajor {1}'.format(
                        shlex.quote(version), shlex.quote(esMajor)
                    )
                elif status == 'Upgrading':
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app Elasticsearch --action upgrade --version {0} --esMajor {1}'.format(
                        shlex.quote(version), shlex.quote(esMajor)
                    )
                else:
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app Elasticsearch --action remove'
            elif appName == 'Redis':
                if status == 'Installing':
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app Redis --action install --version {0}'.format(
                        shlex.quote(version)
                    )
                elif status == 'Upgrading':
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app Redis --action upgrade --version {0}'.format(
                        shlex.quote(version)
                    )
                else:
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app Redis --action remove'
            elif appName == 'RabbitMQ':
                if status == 'Installing':
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app RabbitMQ --action install --version {0} --rabbitmqStream {1}'.format(
                        shlex.quote(version), shlex.quote(rabbitmqStream)
                    )
                elif status == 'Upgrading':
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app RabbitMQ --action upgrade --version {0} --rabbitmqStream {1}'.format(
                        shlex.quote(version), shlex.quote(rabbitmqStream)
                    )
                else:
                    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/manageServices/serviceManager.py --app RabbitMQ --action remove'
            else:
                data_ret = {'status': 0, 'error_message': 'Unknown application selected.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ProcessUtilities.popenExecutioner(command)
            data_ret = {'status': 1}
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
