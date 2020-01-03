import threading as multi
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from django.shortcuts import render
import os
from serverStatus.serverStatusUtil import ServerStatusUtil
import json
from django.shortcuts import HttpResponse
from math import ceil
from websiteFunctions.models import Websites
from CLManager.models import CLPackages


class CLManagerMain(multi.Thread):

    def __init__(self, request=None, templateName=None, function=None, data=None):
        multi.Thread.__init__(self)
        self.request = request
        self.templateName = templateName
        self.function = function
        self.data = data

    def run(self):
        try:
            if self.function == 'submitCageFSInstall':
                self.submitCageFSInstall()
            elif self.function == 'enableOrDisable':
                self.enableOrDisable()

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.run]')

    def renderC(self):

        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        data = {}
        data['CL'] = 0
        data['activatedPath'] = 0
        data['ipAddress'] = ipAddress
        CLPath = '/etc/sysconfig/cloudlinux'
        activatedPath = '/home/cyberpanel/cloudlinux'

        if os.path.exists(CLPath):
            data['CL'] = 1

        if os.path.exists(activatedPath):
            data['activatedPath'] = 1

        if data['CL']  == 0:
            return render(self.request, 'CLManager/notAvailable.html', data)
        elif data['activatedPath']  == 0:
            return render(self.request, 'CLManager/notAvailable.html', data)
        else:
            return render(self.request, 'CLManager/cloudLinux.html', data)

    def submitCageFSInstall(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          'Not authorized to install container packages. [404].',
                                                          1)
                return 0

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/CLManager/CageFS.py"
            execPath = execPath + " --function submitCageFSInstall"
            ProcessUtilities.outputExecutioner(execPath)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    def findWebsitesJson(self, currentACL, userID, pageNumber):
        finalPageNumber = ((pageNumber * 10)) - 10
        endPageNumber = finalPageNumber + 10
        websites = ACLManager.findWebsiteObjects(currentACL, userID)[finalPageNumber:endPageNumber]

        json_data = "["
        checker = 0

        command = '/usr/sbin/cagefsctl --list-enabled'
        Enabled = ProcessUtilities.outputExecutioner(command)

        for items in websites:
            if Enabled.find(items.externalApp) > -1:
                status = 1
            else:
                status = 0
            dic = {'domain': items.domain, 'externalApp': items.externalApp, 'status': status}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def websitePagination(self, currentACL, userID):
        websites = ACLManager.findAllSites(currentACL, userID)

        pages = float(len(websites)) / float(10)
        pagination = []

        if pages <= 1.0:
            pages = 1
            pagination.append('<li><a href="\#"></a></li>')
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

        return pagination

    def getFurtherAccounts(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            pageNumber = int(data['page'])
            json_data = self.findWebsitesJson(currentACL, userID, pageNumber)
            pagination = self.websitePagination(currentACL, userID)

            cageFSPath = '/home/cyberpanel/cagefs'

            if os.path.exists(cageFSPath):
                default = 'On'
            else:
                default = 'Off'

            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data,
                         'pagination': pagination, 'default': default}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def enableOrDisable(self):
        try:
            websites = Websites.objects.all()
            if self.data['mode'] == 1:
                for items in websites:
                    command = '/usr/sbin/cagefsctl --enable %s' % (items.externalApp)
                    ProcessUtilities.executioner(command)
            else:
                for items in websites:
                    command = '/usr/sbin/cagefsctl --disable %s' % (items.externalApp)
                    ProcessUtilities.executioner(command)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    def fetchPackages(self, currentACL):

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        json_data = "["
        checker = 0

        for items in CLPackages.objects.all():
            dic = {'name': items.name, 'SPEED': items.speed, 'VMEM': items.vmem, 'PMEM': items.pmem, 'IO': items.io, 'IOPS': items.iops, 'EP': items.ep,
                   'NPROC': items.nproc, 'inodessoft': items.inodessoft, 'inodeshard': items.inodeshard}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        final_dic = {'status': 1, 'error_message': "None", "data": json_data}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

