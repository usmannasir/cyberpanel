#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django

from plogical.httpProc import httpProc

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.http import HttpResponse
import json
import shlex
import plogical.CyberCPLogFileWriter as logging
from plogical.tuning import tuning
from loginSystem.views import loadLoginPage
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities
from websiteFunctions.models import Websites, ChildDomains


class tuningManager:
    def loadTuningHome(self, request, userID):
        proc = httpProc(request, 'tuning/index.html',
                        None, 'admin')
        return proc.render()

    def liteSpeedTuning(self, request, userID):
        proc = httpProc(request, 'tuning/liteSpeedTuning.html',
                        None, 'admin')
        return proc.render()

    def phpTuning(self, request, userID):
        currentACL = ACLManager.loadedACL(userID)
        # Nothing is prepared for a user the page is refused to.
        if currentACL['admin'] != 1:
            return httpProc(request, 'tuning/phpTuning.html', None, 'admin').render()
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            websitesName = ACLManager.findAllSites(currentACL, userID)
            OLS = 1
            proc = httpProc(request, 'tuning/phpTuning.html',
                            {'websiteList': websitesName, 'OLS': OLS}, 'admin')
            return proc.render()
        else:
            OLS = 0
            proc = httpProc(request, 'tuning/phpTuning.html',
                            {'OLS': OLS}, 'admin')
            return proc.render()

    def tuneLitespeed(self, userID, data):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            status = data['status']
            if status == "fetch":

                json_data = json.dumps(tuning.fetchTuningDetails())

                data_ret = {'fetch_status': 1, 'error_message': "None", "tuning_data": json_data,
                            'tuneStatus': 0}

                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            else:
                if data.get('maxConn') is None:
                    data_ret = {'fetch_status': 1, 'error_message': "Provide Max Connections", 'tuneStatus': 0}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                if data.get('maxSSLConn') is None:
                    data_ret = {'fetch_status': 1, 'error_message': "Provide Max SSL Connections",
                                'tuneStatus': 0}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                if data.get('keepAlive') is None:
                    data_ret = {'fetch_status': 1, 'error_message': "Provide Keep Alive", 'tuneStatus': 0}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                if data.get('inMemCache') is None:
                    data_ret = {'fetch_status': 1, 'error_message': "Provide Cache Size in memory",
                                'tuneStatus': 0}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                if not data.get('gzipCompression'):
                    data_ret = {'fetch_status': 1, 'error_message': "Provide Enable GZIP Compression",
                                'tuneStatus': 0}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                # Whole numbers, a size and one of two words; the worker
                # checks the same again.
                maxConn, maxSSLConn, connTime, keepAlive, inMemCache, gzipCompression = tuning.checkedServerTuning(
                    data['maxConn'], data['maxSSLConn'], data['connTime'], data['keepAlive'],
                    data['inMemCache'], data['gzipCompression'])

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/tuning.py"
                execPath = execPath + " saveTuningDetails --maxConn " + shlex.quote(maxConn) + " --maxSSLConn " + shlex.quote(maxSSLConn) \
                           + " --connTime " + shlex.quote(connTime) + " --keepAlive " + shlex.quote(keepAlive) \
                           + " --inMemCache " + shlex.quote(inMemCache) + " --gzipCompression " + shlex.quote(gzipCompression)
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'fetch_status': 1, 'error_message': "None", 'tuneStatus': 1}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)
                else:
                    data_ret = {'fetch_status': 1, 'error_message': "None", 'tuneStatus': 0}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

        except BaseException as msg:
            data_ret = {'fetch_status': 0, 'error_message': str(msg), 'tuneStatus': 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def tunePHP(self, userID, data):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            status = data['status']
            domainSelection = data.get('domainSelection')
            
            # Check if domainSelection is None or 'null' string
            if domainSelection is None or domainSelection == 'null' or domainSelection == '':
                data_ret = {'fetch_status': 0, 'error_message': "Please select a domain/PHP version first", 'tuneStatus': 0}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)
            
            # The selection becomes part of a path and of the worker's command
            # line: on OpenLiteSpeed it is a website of this server, written
            # as it is stored; on LiteSpeed Enterprise a LiteSpeed PHP.
            domainSelection = tuning.phpTuningTarget(domainSelection)
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                site = Websites.objects.filter(domain=domainSelection).first() or \
                    ChildDomains.objects.filter(domain=domainSelection).first()
                if site is None:
                    raise ValueError('Invalid domain name.')
                domainSelection = site.domain

            if status == "fetch":

                json_data = json.dumps(tuning.fetchPHPDetails(domainSelection))

                data_ret = {'fetch_status': 1, 'error_message': "None", "tuning_data": json_data,
                            'tuneStatus': 0}

                final_json = json.dumps(data_ret)

                return HttpResponse(final_json)

            else:
                maxConns, initTimeout, persistConn, memSoftLimit, memHardLimit, procSoftLimit, procHardLimit = \
                    tuning.checkedPHPTuning(data['maxConns'], data['initTimeout'], data['persistConn'],
                                            data['memSoftLimit'], data['memHardLimit'],
                                            data['procSoftLimit'], data['procHardLimit'])

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/tuning.py"
                execPath = execPath + " tunePHP --virtualHost " + shlex.quote(domainSelection) + " --initTimeout " + shlex.quote(initTimeout) \
                           + " --maxConns " + shlex.quote(maxConns) + " --memSoftLimit " + shlex.quote(memSoftLimit) \
                           + " --memHardLimit " + shlex.quote(memHardLimit) + " --procSoftLimit " + shlex.quote(procSoftLimit) \
                           + " --procHardLimit " + shlex.quote(procHardLimit) + " --persistConn " + shlex.quote(persistConn)

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'tuneStatus': 1, 'fetch_status': 0, 'error_message': "None"}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)
                else:
                    data_ret = {'fetch_status': 0, 'error_message': output, 'tuneStatus': 0}
                    logging.CyberCPLogFileWriter.writeToFile(output + " [tunePHP]]")
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'fetch_status': 0, 'error_message': str(msg), 'tuneStatus': 0}
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [tunePHP]]")
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)