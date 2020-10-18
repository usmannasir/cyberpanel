from django.shortcuts import HttpResponse
import json
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from websiteFunctions.models import Websites
from random import randint
from django.core.files.storage import FileSystemStorage
from plogical.acl import ACLManager
from filemanager.models import Trash


class FileManager:
    modes = {'php': 'application/x-httpd-php', 'javascript': 'javascript', 'python': 'text/x-python'}

    def __init__(self, request, data):
        self.request = request
        self.data = data

    @staticmethod
    def findMode(fileName):

        if fileName.endswith('.php'):
            return FileManager.modes['php']
        elif fileName.endswith('js'):
            return FileManager.modes['javascript']
        elif fileName.endswith('.py'):
            return FileManager.modes['python']

    @staticmethod
    def findModeFiles(mode):

        if mode == 'application/x-httpd-php':
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/javascript/javascript.min.js"
            integrity="sha512-e3U/84Fo+2ZAnRhLkjStm2hYnkmZ/NRmeesZ/GHjDhcLh35eYTQxsfSeDppx6Se5aX0N6mrygH7tr4wugWsPeQ=="
            crossorigin="anonymous"></script>  
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/javascript-hint.min.js"
            integrity="sha512-PPI9W6pViVZfJ5uvmYZsHbPwf7T+voS0OpohIrN8Q4CRCCa6JK39JJ0R16HHmyV7EQR8MTa+O56CpWjfKOxl0A=="
            crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/css/css.min.js"
            integrity="sha512-DG+5u//fVN9kpDgTGe78IJhJW8e5+tlrPaMgNqcrzyPXsn+GPaF2T62+X3ds7SuhFR9Qeb7XZ6kMD8X09FeJhA=="
            crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/xml/xml.min.js"
            integrity="sha512-k1HnoY9EXahEfPz7kq/lD9DltloKH9OrB9XNKYoUQrNz9epe5F4mQP5PfuIfeRfoXHkNrE0gF3Mx4LhC5BVl9Q=="
            crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/htmlmixed/htmlmixed.min.js"
            integrity="sha512-p15qsXPrhaUkH+/RPE6QzCmxUAPkCRw89ityx+tWC1lAYI6Et2L0UpN+iqifxUdt+ss1FQ+9CuzxpBeT9mR3/w=="
            crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/clike/clike.min.js" integrity="sha512-HT3t3u7HfQ7USbSZa0Tk5caEnUfO8s58OWqMBwm96xaZAbA17rpnXXHDefR8ixVmSSVssbOv3W3OMh6mNX/XuQ==" crossorigin="anonymous"></script>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/anyword-hint.min.js" integrity="sha512-wdYOcbX/zcS4tP3HEDTkdOI5UybyuRxJMQzDQIRcafRLY/oTDWyXO+P8SzuajQipcJXkb2vHcd1QetccSFAaVw==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/css-hint.min.js" integrity="sha512-iXuwWkAmdAUNuO5rUtzmJZ/LoeJoSG8ZeQVdcUBCkV0dxfe7bxfzQMKCwQ6uNNs0FZ9jmSrN/jzJX7G1bOs4Nw==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/html-hint.min.js" integrity="sha512-aGi2Yn9VkLP9HiwiMXfkY7KQoGfwDW6JiGUtPhiPJAL9J7+rwwPVWUtUYvHW+xp3yJ7F0UhTPoPumUZv3+E/Rg==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/sql-hint.min.js" integrity="sha512-zVNOyYBOmDcGRo9/Tz+rYW8vjhAO4D/jqbj9+IIb1xWMU1ROyNWPCeWcOoBTquOBBmdiue78xJg5kkdWzsZJog==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/xml-hint.min.js" integrity="sha512-XtLGFClKrm3hNY3bS01LPiIkF64i9CnlxCqj5O+TSQq7UW8kFhFIc3kOR3bJ98h4ThxFaKdJA9PpQC76LvD/oQ==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/php/php.min.js"
            integrity="sha512-m8sosGXUwyH6Ppzoy+CoQ/r5zAwZRGdNFUgGH81E3RDQkFnAsE4cP1I3tokvZwgMsDZB5mHxs+7egAgvhaCcMw=="
            crossorigin="anonymous"></script>
"""
        elif mode == 'javascript':
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/show-hint.min.js"
            integrity="sha512-ge9uKCpgPmuJY2e2zPXhpYCZfyb1/R7KOOfMZ3SzSX3ZayWpINs3sHnI8LGEHUf6UOFX/D03FVHgR36uRL8/Vw=="
            crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/javascript/javascript.min.js"
            integrity="sha512-e3U/84Fo+2ZAnRhLkjStm2hYnkmZ/NRmeesZ/GHjDhcLh35eYTQxsfSeDppx6Se5aX0N6mrygH7tr4wugWsPeQ=="
            crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/javascript-hint.min.js"
            integrity="sha512-PPI9W6pViVZfJ5uvmYZsHbPwf7T+voS0OpohIrN8Q4CRCCa6JK39JJ0R16HHmyV7EQR8MTa+O56CpWjfKOxl0A=="
            crossorigin="anonymous"></script>
"""
        elif mode == 'text/x-python':
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/python/python.min.js" integrity="sha512-DS+asaww1mE0V/N6YGVgoNIRj+yXB9hAV68vM6rVeWs0G+OyMd24LKrnS4Z+g26rgghU7qvGeEnRVUArV7nVog==" crossorigin="anonymous"></script>
 """

    @staticmethod
    def findThemeFile(theme):
        return '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/theme/%s.min.css" />' % (theme)

    def ajaxPre(self, status, errorMessage):
        final_dic = {'status': status, 'error_message': errorMessage, 'uploadStatus': status}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    def returnPathEnclosed(self, path):
        return "'" + path + "'"

    def changeOwner(self, path):
        domainName = self.data['domainName']
        website = Websites.objects.get(domain=domainName)

        if path.find('..') > -1:
            return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

        command = "chown -R " + website.externalApp + ':' + website.externalApp + ' ' + self.returnPathEnclosed(path)
        ProcessUtilities.executioner(command, website.externalApp)

    def listForTable(self):
        try:
            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            pathCheck = '/home/%s' % (domainName)

            if self.data['completeStartingPath'].find(pathCheck) == -1 or self.data['completeStartingPath'].find(
                    '..') > -1:
                return self.ajaxPre(0, 'Not allowed to browse this path, going back home!')

            command = "ls -la --group-directories-first " + self.returnPathEnclosed(
                self.data['completeStartingPath'])
            output = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()

            counter = 0
            for items in output:
                try:
                    currentFile = items.split(' ')
                    currentFile = [a for a in currentFile if a != '']
                    if currentFile[-1] == '.' or currentFile[-1] == '..' or currentFile[0] == 'total':
                        continue

                    if len(currentFile) > 9:
                        fileName = currentFile[8:]
                        currentFile[-1] = " ".join(fileName)

                    dirCheck = 0
                    if currentFile[0][0] == 'd':
                        dirCheck = 1

                    size = str(int(int(currentFile[4]) / float(1024)))
                    lastModified = currentFile[5] + ' ' + currentFile[6] + ' ' + currentFile[7]
                    finalData[str(counter)] = [currentFile[-1], currentFile[-1], lastModified, size, currentFile[0],
                                               dirCheck]
                    counter = counter + 1
                except BaseException as msg:
                    logging.writeToFile(str(msg))

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def list(self):
        try:
            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            command = "ls -la --group-directories-first " + self.returnPathEnclosed(
                self.data['completeStartingPath'])
            output = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()

            counter = 0
            for items in output:
                try:
                    currentFile = items.split(' ')
                    currentFile = [a for a in currentFile if a != '']

                    if currentFile[-1] == '.' or currentFile[-1] == '..' or currentFile[0] == 'total':
                        continue

                    if len(currentFile) > 9:
                        fileName = currentFile[8:]
                        currentFile[-1] = " ".join(fileName)

                    dirCheck = False
                    if currentFile[0][0] == 'd':
                        dirCheck = True

                    finalData[str(counter)] = [currentFile[-1],
                                               self.data['completeStartingPath'] + '/' + currentFile[-1], dirCheck]
                    counter = counter + 1
                except:
                    continue

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def createNewFile(self):
        try:
            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)
            homePath = '/home/%s' % (domainName)

            if self.data['fileName'].find('..') > -1 or self.data['fileName'].find(homePath) == -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            command = "touch " + self.returnPathEnclosed(self.data['fileName'])
            ProcessUtilities.executioner(command, website.externalApp)

            self.changeOwner(self.returnPathEnclosed(self.data['fileName']))

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def createNewFolder(self):
        try:
            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            homePath = '/home/%s' % (domainName)

            if self.data['folderName'].find('..') > -1 or self.data['folderName'].find(homePath) == -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            command = "mkdir " + self.returnPathEnclosed(self.data['folderName'])
            ProcessUtilities.executioner(command, website.externalApp)

            self.changeOwner(self.returnPathEnclosed(self.data['folderName']))

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteFolderOrFile(self):
        try:
            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']

            try:
                skipTrash = self.data['skipTrash']
            except:
                skipTrash = False

            website = Websites.objects.get(domain=domainName)
            self.homePath = '/home/%s' % (domainName)

            for item in self.data['fileAndFolders']:

                if (self.data['path'] + '/' + item).find('..') > -1 or (self.data['path'] + '/' + item).find(
                        self.homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if skipTrash:
                    command = 'rm -rf ' + self.returnPathEnclosed(self.data['path'] + '/' + item)
                    ProcessUtilities.executioner(command, website.externalApp)
                else:
                    trashPath = '%s/.trash' % (self.homePath)

                    command = 'mkdir %s' % (trashPath)
                    ProcessUtilities.executioner(command, website.externalApp)

                    Trash(website=website, originalPath=self.returnPathEnclosed(self.data['path']),
                          fileName=self.returnPathEnclosed(item)).save()

                    command = 'mv %s %s' % (self.returnPathEnclosed(self.data['path'] + '/' + item), trashPath)
                    ProcessUtilities.executioner(command, website.externalApp)

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def restore(self):
        try:
            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']

            try:
                skipTrash = self.data['skipTrash']
            except:
                skipTrash = False

            website = Websites.objects.get(domain=domainName)
            self.homePath = '/home/%s' % (domainName)

            for item in self.data['fileAndFolders']:

                if (self.data['path'] + '/' + item).find('..') > -1 or (self.data['path'] + '/' + item).find(
                        self.homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                trashPath = '%s/.trash' % (self.homePath)

                tItem = Trash.objects.get(website=website, fileName=self.returnPathEnclosed(item))

                command = 'mv %s %s' % (self.returnPathEnclosed(trashPath + '/' + item), tItem.originalPath)
                ProcessUtilities.executioner(command, website.externalApp)

                tItem.delete()

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def copy(self):
        try:

            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            homePath = '/home/%s' % (domainName)

            if self.data['newPath'].find('..') > -1 or self.data['newPath'].find(homePath) == -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            if len(self.data['fileAndFolders']) == 1:

                if (self.data['basePath'] + '/' + self.data['fileAndFolders'][0]).find('..') > -1 or (
                        self.data['basePath'] + '/' + self.data['fileAndFolders'][0]).find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'yes| cp -Rf %s %s' % (
                    self.returnPathEnclosed(self.data['basePath'] + '/' + self.data['fileAndFolders'][0]),
                    self.data['newPath'])
                ProcessUtilities.executioner(command, website.externalApp)
                self.changeOwner(self.data['newPath'])
                json_data = json.dumps(finalData)
                return HttpResponse(json_data)

            command = 'mkdir ' + self.returnPathEnclosed(self.data['newPath'])
            ProcessUtilities.executioner(command, website.externalApp)

            for item in self.data['fileAndFolders']:
                if (self.data['basePath'] + '/' + item).find('..') > -1 or (self.data['basePath'] + '/' + item).find(
                        homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = '%scp -Rf ' % ('yes |') + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + item) + ' ' + self.returnPathEnclosed(self.data['newPath'])
                ProcessUtilities.executioner(command, website.externalApp)

            self.changeOwner(self.data['newPath'])

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def move(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            homePath = '/home/%s' % (domainName)

            command = 'mkdir ' + self.returnPathEnclosed(self.data['newPath'])
            ProcessUtilities.executioner(command, website.externalApp)

            for item in self.data['fileAndFolders']:

                if (self.data['basePath'] + '/' + item).find('..') > -1 or (self.data['basePath'] + '/' + item).find(
                        homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if (self.data['newPath'] + '/' + item).find('..') > -1 or (self.data['newPath'] + '/' + item).find(
                        homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'mv ' + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + item) + ' ' + self.returnPathEnclosed(
                    self.data['newPath'] + '/' + item)
                ProcessUtilities.executioner(command, website.externalApp)

            self.changeOwner(self.data['newPath'])

            self.fixPermissions(domainName)

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def rename(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            homePath = '/home/%s' % (domainName)

            if (self.data['basePath'] + '/' + self.data['existingName']).find('..') > -1 or (
                    self.data['basePath'] + '/' + self.data['existingName']).find(homePath) == -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            if (self.data['newFileName']).find('..') > -1 or (self.data['basePath']).find(homePath) == -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            command = 'mv ' + self.returnPathEnclosed(
                self.data['basePath'] + '/' + self.data['existingName']) + ' ' + self.returnPathEnclosed(
                self.data['basePath'] + '/' + self.data['newFileName'])
            ProcessUtilities.executioner(command, website.externalApp)

            self.changeOwner(self.data['basePath'] + '/' + self.data['newFileName'])

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def readFileContents(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            pathCheck = '/home/%s' % (domainName)

            if self.data['fileName'].find(pathCheck) == -1 or self.data['fileName'].find('..') > -1:
                return self.ajaxPre(0, 'Not allowed.')

            command = 'cat ' + self.returnPathEnclosed(self.data['fileName'])
            finalData['fileContents'] = ProcessUtilities.outputExecutioner(command, website.externalApp)

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def writeFileContents(self):
        try:

            finalData = {}
            finalData['status'] = 1
            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            self.data['home'] = '/home/%s' % (self.data['domainName'])

            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            writeToFile = open(tempPath, 'wb')
            writeToFile.write(self.data['fileContent'].encode('utf-8'))
            writeToFile.close()

            command = 'ls -la %s' % (self.data['fileName'])
            output = ProcessUtilities.outputExecutioner(command)

            if output.find('lrwxrwxrwx') > -1 and output.find('->') > -1:
                return self.ajaxPre(0, 'File exists and is symlink.')

            if ACLManager.commandInjectionCheck(self.data['fileName']) == 1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            if self.data['fileName'].find(self.data['home']) == -1 or self.data['fileName'].find('..') > -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            command = 'mv ' + tempPath + ' ' + self.returnPathEnclosed(self.data['fileName'])
            ProcessUtilities.executioner(command)

            command = 'chown %s:%s %s' % (website.externalApp, website.externalApp, self.data['fileName'])
            ProcessUtilities.executioner(command)

            self.changeOwner(self.data['fileName'])

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def upload(self):
        try:

            finalData = {}
            finalData['uploadStatus'] = 1
            finalData['answer'] = 'File transfer completed.'

            myfile = self.request.FILES['file']
            fs = FileSystemStorage()

            try:
                filename = fs.save(myfile.name, myfile)
                finalData['fileName'] = fs.url(filename)
            except BaseException as msg:
                logging.writeToFile('%s. [375:upload]' % (str(msg)))

            pathCheck = '/home/%s' % (self.data['domainName'])

            if ACLManager.commandInjectionCheck(self.data['completePath'] + '/' + myfile.name) == 1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            if (self.data['completePath'] + '/' + myfile.name).find(pathCheck) == -1 or (
                    (self.data['completePath'] + '/' + myfile.name)).find('..') > -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            command = 'mv ' + self.returnPathEnclosed(
                '/home/cyberpanel/media/' + myfile.name) + ' ' + self.returnPathEnclosed(
                self.data['completePath'] + '/' + myfile.name)
            ProcessUtilities.executioner(command)

            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            command = 'chown %s:%s %s' % (website.externalApp, website.externalApp,
                                          self.returnPathEnclosed(self.data['completePath'] + '/' + myfile.name))
            ProcessUtilities.executioner(command)

            self.changeOwner(self.returnPathEnclosed(self.data['completePath'] + '/' + myfile.name))

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def extract(self):
        try:

            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            homePath = '/home/%s' % (domainName)

            if self.data['extractionLocation'].find('..') > -1 or self.data['extractionLocation'].find(homePath) == -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            if self.data['fileToExtract'].find('..') > -1 or self.data['fileToExtract'].find(homePath) == -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            if self.data['extractionType'] == 'zip':
                command = 'unzip -o ' + self.returnPathEnclosed(
                    self.data['fileToExtract']) + ' -d ' + self.returnPathEnclosed(self.data['extractionLocation'])
            else:
                command = 'tar -xf ' + self.returnPathEnclosed(
                    self.data['fileToExtract']) + ' -C ' + self.returnPathEnclosed(self.data['extractionLocation'])

            ProcessUtilities.executioner(command, website.externalApp)

            self.fixPermissions(domainName)

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def compress(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            if self.data['compressionType'] == 'zip':
                compressedFileName = self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['compressedFileName'] + '.zip')
                command = 'zip -r ' + compressedFileName + ' '
            else:
                compressedFileName = self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['compressedFileName'] + '.tar.gz')
                command = 'tar -czvf ' + compressedFileName + ' '

            homePath = '/home/%s' % (domainName)

            for item in self.data['listOfFiles']:

                if (self.data['basePath'] + item).find('..') > -1 or (self.data['basePath'] + item).find(
                        homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = '%s%s ' % (command, self.returnPathEnclosed(item))

            finalCommand = 'cd %s && %s' % (self.data['basePath'], command)

            ProcessUtilities.executioner(finalCommand, website.externalApp)

            self.changeOwner(self.data['compressedFileName'])

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def changePermissions(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            if self.data['recursive'] == 1:
                command = 'chmod -R ' + self.data['newPermissions'] + ' ' + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['permissionsPath'])
            else:
                command = 'chmod ' + self.data['newPermissions'] + ' ' + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['permissionsPath'])

            ProcessUtilities.executioner(command, website.externalApp)

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fixPermissions(self, domainName):

        website = Websites.objects.get(domain=domainName)
        externalApp = website.externalApp

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            groupName = 'nobody'
        else:
            groupName = 'nogroup'

        command = 'chown -R %s:%s /home/%s/public_html/*' % (externalApp, externalApp, domainName)
        ProcessUtilities.popenExecutioner(command)

        command = 'chown -R %s:%s /home/%s/public_html/.[^.]*' % (externalApp, externalApp, domainName)
        ProcessUtilities.popenExecutioner(command)

        command = "chown root:%s /home/" % (groupName) + domainName + "/logs"
        ProcessUtilities.popenExecutioner(command)

        command = "find %s -type d -exec chmod 0755 {} \;" % ("/home/" + domainName + "/public_html")
        ProcessUtilities.popenExecutioner(command)

        command = "find %s -type f -exec chmod 0644 {} \;" % ("/home/" + domainName + "/public_html")
        ProcessUtilities.popenExecutioner(command)

        command = 'chown %s:%s /home/%s/public_html' % (externalApp, groupName, domainName)
        ProcessUtilities.executioner(command)

        command = 'chmod 750 /home/%s/public_html' % (domainName)
        ProcessUtilities.executioner(command)

        for childs in website.childdomains_set.all():
            command = "find %s -type d -exec chmod 0755 {} \;" % (childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = "find %s -type f -exec chmod 0644 {} \;" % (childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chown -R %s:%s %s/*' % (externalApp, externalApp, childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chown -R %s:%s %s/.[^.]*' % (externalApp, externalApp, childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chmod 755 %s' % (childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chown %s:%s %s' % (externalApp, groupName, childs.path)
            ProcessUtilities.popenExecutioner(command)
