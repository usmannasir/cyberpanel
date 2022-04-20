import os

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
    modes = {'php': 'application/x-httpd-php', 'javascript': 'javascript', 'python': 'text/x-python',
             'html': 'text/html', 'go': 'text/x-go', 'css': 'text/css', 'java': 'text/x-java', 'perl': 'text/x-perl',
             'scss': 'text/x-sass'}

    def __init__(self, request, data):
        self.request = request
        self.data = data

    @staticmethod
    def findMode(fileName):
        if fileName.endswith('.php'):
            return FileManager.modes['php']
        elif fileName.endswith('.js'):
            return FileManager.modes['javascript']
        elif fileName.endswith('.py'):
            return FileManager.modes['python']
        elif fileName.endswith('.html'):
            return FileManager.modes['html']
        elif fileName.endswith('.go'):
            return FileManager.modes['go']
        elif fileName.endswith('.css'):
            return FileManager.modes['css']
        elif fileName.endswith('.pl') or fileName.endswith('.PL'):
            return FileManager.modes['perl']
        elif fileName.endswith('.java'):
            return FileManager.modes['java']
        elif fileName.endswith('.scss'):
            return FileManager.modes['scss']
        else:
            return ""


    @staticmethod
    def findModeFiles(mode):

        if mode == FileManager.modes['php']:
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
        elif mode == FileManager.modes['javascript']:
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
        elif mode == FileManager.modes['python']:
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/python/python.min.js" integrity="sha512-DS+asaww1mE0V/N6YGVgoNIRj+yXB9hAV68vM6rVeWs0G+OyMd24LKrnS4Z+g26rgghU7qvGeEnRVUArV7nVog==" crossorigin="anonymous"></script>
 """
        elif mode == FileManager.modes['html']:
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
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/anyword-hint.min.js" integrity="sha512-wdYOcbX/zcS4tP3HEDTkdOI5UybyuRxJMQzDQIRcafRLY/oTDWyXO+P8SzuajQipcJXkb2vHcd1QetccSFAaVw==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/css-hint.min.js" integrity="sha512-iXuwWkAmdAUNuO5rUtzmJZ/LoeJoSG8ZeQVdcUBCkV0dxfe7bxfzQMKCwQ6uNNs0FZ9jmSrN/jzJX7G1bOs4Nw==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/html-hint.min.js" integrity="sha512-aGi2Yn9VkLP9HiwiMXfkY7KQoGfwDW6JiGUtPhiPJAL9J7+rwwPVWUtUYvHW+xp3yJ7F0UhTPoPumUZv3+E/Rg==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/sql-hint.min.js" integrity="sha512-zVNOyYBOmDcGRo9/Tz+rYW8vjhAO4D/jqbj9+IIb1xWMU1ROyNWPCeWcOoBTquOBBmdiue78xJg5kkdWzsZJog==" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/addon/hint/xml-hint.min.js" integrity="sha512-XtLGFClKrm3hNY3bS01LPiIkF64i9CnlxCqj5O+TSQq7UW8kFhFIc3kOR3bJ98h4ThxFaKdJA9PpQC76LvD/oQ==" crossorigin="anonymous"></script>
"""
        elif mode == FileManager.modes['go']:
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/go/go.min.js" integrity="sha512-DxeIplahS44UYHUdqtsLJ21g5xHilhuP7Y4i+NSsD7J4ow+LXIXLHsjvEpMqcTSg15rkaqBRIXEETAjq3yb5Cw==" crossorigin="anonymous"></script>
"""
        elif mode == FileManager.modes['css']:
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/css/css.min.js" integrity="sha512-DG+5u//fVN9kpDgTGe78IJhJW8e5+tlrPaMgNqcrzyPXsn+GPaF2T62+X3ds7SuhFR9Qeb7XZ6kMD8X09FeJhA==" crossorigin="anonymous"></script>
"""
        elif mode == FileManager.modes['java']:
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/clike/clike.min.js" integrity="sha512-HT3t3u7HfQ7USbSZa0Tk5caEnUfO8s58OWqMBwm96xaZAbA17rpnXXHDefR8ixVmSSVssbOv3W3OMh6mNX/XuQ==" crossorigin="anonymous"></script>
"""
        elif mode == FileManager.modes['perl']:
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/perl/perl.min.js" integrity="sha512-6rKFA1mIjmFqxMM/b0dtjQOWFRAoqKCmhb7/6u2KohJcP4poKbrUI08Yf5GXsK+rkCr2dQnppV7gMe2a0HGQBQ==" crossorigin="anonymous"></script>        
"""
        elif mode == FileManager.modes['scss']:
            return """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/mode/sass/sass.min.js" integrity="sha512-lFZETu8ovGFrFbFWAJnwgJrRcQ06C0BhjySIpBFPUatL/vqFz/mZIvXhlLtbOwbvRCp+XcLCmTEigKOJPN+YhA==" crossorigin="anonymous"></script>
"""
        else:
            return ''

    @staticmethod
    def findThemeFile(theme):
        return '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/theme/%s.min.css" />' % (theme)

    @staticmethod
    def findAdditionalOptions(mode):
        if mode == 'text/x-python':
            return """<select ng-model="optionValue" ng-change="additionalOptions()">
                <option>Python 2</option>
                <option>Python 3</option>
            </select>
"""
        else:
            return ""

    def ajaxPre(self, status, errorMessage):
        final_dic = {'status': status, 'error_message': errorMessage, 'uploadStatus': status}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    def returnPathEnclosed(self, path):
        return "'" + path + "'"

    def changeOwner(self, path):
        try:
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            if path.find('..') > -1:
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            command = "chown -R " + website.externalApp + ':' + website.externalApp + ' ' + self.returnPathEnclosed(path)
            ProcessUtilities.executioner(command, website.externalApp)
        except:
            print("Permisson not changed")

    def listForTable(self):
        try:
            finalData = {}
            finalData['status'] = 1

            try:

                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)

                pathCheck = '/home/%s' % (domainName)

                if self.data['completeStartingPath'].find(pathCheck) == -1 or self.data['completeStartingPath'].find(
                        '..') > -1:
                    return self.ajaxPre(0, 'Not allowed to browse this path, going back home!')

                command = "ls -la --group-directories-first " + self.returnPathEnclosed(
                    self.data['completeStartingPath'])
                output = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()

            except:
                pathCheck = '/'

                if self.data['completeStartingPath'].find(pathCheck) == -1 or self.data['completeStartingPath'].find(
                        '..') > -1:
                    return self.ajaxPre(0, 'Not allowed to browse this path, going back home!')

                command = "ls -la --group-directories-first " + self.returnPathEnclosed(
                    self.data['completeStartingPath'])
                output = ProcessUtilities.outputExecutioner(command).splitlines()

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
            try:
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
            except:
                command = "ls -la --group-directories-first " + self.returnPathEnclosed(
                    self.data['completeStartingPath'])
                output = ProcessUtilities.outputExecutioner(command).splitlines()

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

            try:
                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)
                homePath = '/home/%s' % (domainName)

                if self.data['fileName'].find('..') > -1 or self.data['fileName'].find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "touch " + self.returnPathEnclosed(self.data['fileName'])
                ProcessUtilities.executioner(command, website.externalApp)
                self.changeOwner(self.returnPathEnclosed(self.data['fileName']))
            except:
                homePath = '/'

                if self.data['fileName'].find('..') > -1 or self.data['fileName'].find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "touch " + self.returnPathEnclosed(self.data['fileName'])
                ProcessUtilities.executioner(command)
                self.changeOwner(self.returnPathEnclosed(self.data['fileName']))

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def createNewFolder(self):
        try:
            finalData = {}
            finalData['status'] = 1
            try:
                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)

                homePath = '/home/%s' % (domainName)

                if self.data['folderName'].find('..') > -1 or self.data['folderName'].find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "mkdir " + self.returnPathEnclosed(self.data['folderName'])
                ProcessUtilities.executioner(command, website.externalApp)

                self.changeOwner(self.returnPathEnclosed(self.data['folderName']))
            except:
                homePath = '/'

                if self.data['folderName'].find('..') > -1 or self.data['folderName'].find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "mkdir " + self.returnPathEnclosed(self.data['folderName'])
                ProcessUtilities.executioner(command)

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
                try:
                    skipTrash = self.data['skipTrash']
                except:
                    skipTrash = False

                website = Websites.objects.get(domain=domainName)
                self.homePath = '/home/%s' % (domainName)

                RemoveOK = 1

                command = 'touch %s/hello.txt' % (self.homePath)
                result = ProcessUtilities.outputExecutioner(command)

                if result.find('No such file or directory') > -1:
                    RemoveOK = 0

                    command = 'chattr -R -i %s' % (self.homePath)
                    ProcessUtilities.executioner(command)

                else:
                    command = 'rm -f %s/hello.txt' % (self.homePath)
                    ProcessUtilities.executioner(command)


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

                if RemoveOK == 0:
                    command = 'chattr -R +i %s' % (self.homePath)
                    ProcessUtilities.executioner(command)
            except:
                try:
                    skipTrash = self.data['skipTrash']
                except:
                    skipTrash = False


                self.homePath = '/'

                RemoveOK = 1

                command = 'touch %s/hello.txt' % (self.homePath)
                result = ProcessUtilities.outputExecutioner(command)

                if result.find('No such file or directory') > -1:
                    RemoveOK = 0

                    command = 'chattr -R -i %s' % (self.homePath)
                    ProcessUtilities.executioner(command)

                else:
                    command = 'rm -f %s/hello.txt' % (self.homePath)
                    ProcessUtilities.executioner(command)

                for item in self.data['fileAndFolders']:

                    if (self.data['path'] + '/' + item).find('..') > -1 or (self.data['path'] + '/' + item).find(
                            self.homePath) == -1:
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    if skipTrash:
                        command = 'rm -rf ' + self.returnPathEnclosed(self.data['path'] + '/' + item)
                        ProcessUtilities.executioner(command)


                if RemoveOK == 0:
                    command = 'chattr -R +i %s' % (self.homePath)
                    ProcessUtilities.executioner(command)

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
            try:
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
            except:


                homePath = '/'

                if self.data['newPath'].find('..') > -1 or self.data['newPath'].find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if len(self.data['fileAndFolders']) == 1:

                    if (self.data['basePath'] + '/' + self.data['fileAndFolders'][0]).find('..') > -1 or (
                            self.data['basePath'] + '/' + self.data['fileAndFolders'][0]).find(homePath) == -1:
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = 'yes| cp -Rf %s %s' % (
                        self.returnPathEnclosed(self.data['basePath'] + '/' + self.data['fileAndFolders'][0]),
                        self.data['newPath'])
                    ProcessUtilities.executioner(command,)
                    self.changeOwner(self.data['newPath'])
                    json_data = json.dumps(finalData)
                    return HttpResponse(json_data)

                command = 'mkdir ' + self.returnPathEnclosed(self.data['newPath'])
                ProcessUtilities.executioner(command)

                for item in self.data['fileAndFolders']:
                    if (self.data['basePath'] + '/' + item).find('..') > -1 or (
                            self.data['basePath'] + '/' + item).find(
                            homePath) == -1:
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = '%scp -Rf ' % ('yes |') + self.returnPathEnclosed(
                        self.data['basePath'] + '/' + item) + ' ' + self.returnPathEnclosed(self.data['newPath'])
                    ProcessUtilities.executioner(command)

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
            try:
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

                #self.changeOwner(self.data['newPath'])

                #self.fixPermissions(domainName)
            except:


                homePath = '/'

                command = 'mkdir ' + self.returnPathEnclosed(self.data['newPath'])
                ProcessUtilities.executioner(command)

                for item in self.data['fileAndFolders']:

                    if (self.data['basePath'] + '/' + item).find('..') > -1 or (
                            self.data['basePath'] + '/' + item).find(
                            homePath) == -1:
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    if (self.data['newPath'] + '/' + item).find('..') > -1 or (self.data['newPath'] + '/' + item).find(
                            homePath) == -1:
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = 'mv ' + self.returnPathEnclosed(
                        self.data['basePath'] + '/' + item) + ' ' + self.returnPathEnclosed(
                        self.data['newPath'] + '/' + item)
                    ProcessUtilities.executioner(command)

                self.changeOwner(self.data['newPath'])


            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def rename(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            try:
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
            except:
                homePath = '/'

                if (self.data['basePath'] + '/' + self.data['existingName']).find('..') > -1 or (
                        self.data['basePath'] + '/' + self.data['existingName']).find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if (self.data['newFileName']).find('..') > -1 or (self.data['basePath']).find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'mv ' + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['existingName']) + ' ' + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['newFileName'])
                ProcessUtilities.executioner(command)

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
            try:
                website = Websites.objects.get(domain=domainName)

                pathCheck = '/home/%s' % (domainName)

                if self.data['fileName'].find(pathCheck) == -1 or self.data['fileName'].find('..') > -1:
                    return self.ajaxPre(0, 'Not allowed.')

                command = 'cat ' + self.returnPathEnclosed(self.data['fileName'])
                finalData['fileContents'] = ProcessUtilities.outputExecutioner(command, website.externalApp)
            except:
                pathCheck = '/'

                if self.data['fileName'].find(pathCheck) == -1 or self.data['fileName'].find('..') > -1:
                    return self.ajaxPre(0, 'Not allowed.')

                command = 'cat ' + self.returnPathEnclosed(self.data['fileName'])
                finalData['fileContents'] = ProcessUtilities.outputExecutioner(command)


            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def writeFileContents(self):
        try:

            finalData = {}
            finalData['status'] = 1
            try:
                self.data['home'] = '/home/%s' % (self.data['domainName'])

                ACLManager.CreateSecureDir()
                tempPath = '%s/%s' % ('/usr/local/CyberCP/tmp', str(randint(1000, 9999)))

                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)

                writeToFile = open(tempPath, 'wb')
                writeToFile.write(self.data['fileContent'].encode('utf-8'))
                writeToFile.close()

                command = 'chown %s:%s %s' % (website.externalApp, website.externalApp, tempPath)
                ProcessUtilities.executioner(command)

                command = 'cp %s %s' % (tempPath, self.returnPathEnclosed(self.data['fileName']))
                ProcessUtilities.executioner(command, website.externalApp)

                os.remove(tempPath)
            except:
                self.data['home'] = '/'

                ACLManager.CreateSecureDir()
                tempPath = '%s/%s' % ('/usr/local/CyberCP/tmp', str(randint(1000, 9999)))
                writeToFile = open(tempPath, 'wb')
                writeToFile.write(self.data['fileContent'].encode('utf-8'))
                writeToFile.close()

                command = 'cp %s %s' % (tempPath, self.returnPathEnclosed(self.data['fileName']))
                ProcessUtilities.executioner(command)

                os.remove(tempPath)


            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def upload(self):
        try:

            finalData = {}
            finalData['uploadStatus'] = 1
            finalData['answer'] = 'File transfer completed.'

            ACLManager.CreateSecureDir()
            UploadPath = '/usr/local/CyberCP/tmp/'

            ## Random file name

            RanddomFileName = str(randint(1000, 9999))

            myfile = self.request.FILES['file']
            fs = FileSystemStorage()

            try:
                filename = fs.save(RanddomFileName, myfile)
                finalData['fileName'] = fs.url(filename)
            except BaseException as msg:
                logging.writeToFile('%s. [375:upload]' % (str(msg)))



            domainName = self.data['domainName']
            try:
                pathCheck = '/home/%s' % (self.data['domainName'])
                website = Websites.objects.get(domain=domainName)

                command = 'ls -la %s' % (self.data['completePath'])
                result = ProcessUtilities.outputExecutioner(command, website.externalApp)
                #
                if result.find('->') > -1:
                    return self.ajaxPre(0, "Symlink attack.")

                if ACLManager.commandInjectionCheck(self.data['completePath'] + '/' + myfile.name) == 1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if (self.data['completePath'] + '/' + myfile.name).find(pathCheck) == -1 or (
                        (self.data['completePath'] + '/' + myfile.name)).find('..') > -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'cp ' + self.returnPathEnclosed(
                    UploadPath + RanddomFileName) + ' ' + self.returnPathEnclosed(
                    self.data['completePath'] + '/' + myfile.name)
                ProcessUtilities.executioner(command, website.externalApp)

                self.changeOwner(self.returnPathEnclosed(self.data['completePath'] + '/' + myfile.name))
                try:
                    os.remove(UploadPath + RanddomFileName)
                except:
                    pass
            except:
                pathCheck = '/'
                command = 'ls -la %s' % (self.data['completePath'])
                result = ProcessUtilities.outputExecutioner(command)
                logging.writeToFile("upload file res %s" % result)
                if ACLManager.commandInjectionCheck(self.data['completePath'] + '/' + myfile.name) == 1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if (self.data['completePath'] + '/' + myfile.name).find(pathCheck) == -1 or (
                        (self.data['completePath'] + '/' + myfile.name)).find('..') > -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'cp ' + self.returnPathEnclosed(
                    UploadPath + RanddomFileName) + ' ' + self.returnPathEnclosed(
                    self.data['completePath'] + '/' + myfile.name)
                ProcessUtilities.executioner(command)

                self.changeOwner(self.returnPathEnclosed(self.data['completePath'] + '/' + myfile.name))
                try:
                    os.remove(UploadPath + RanddomFileName)
                except:
                    pass



            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            try:
                os.remove(UploadPath + RanddomFileName)
            except:
                pass
            return self.ajaxPre(0, str(msg))

    def extract(self):
        try:

            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']

            try:

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

                #self.fixPermissions(domainName)
            except:

                homePath = '/'

                if self.data['extractionLocation'].find('..') > -1 or self.data['extractionLocation'].find(
                        homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if self.data['fileToExtract'].find('..') > -1 or self.data['fileToExtract'].find(homePath) == -1:
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if self.data['extractionType'] == 'zip':
                    command = 'unzip -o ' + self.returnPathEnclosed(
                        self.data['fileToExtract']) + ' -d ' + self.returnPathEnclosed(self.data['extractionLocation'])
                else:
                    command = 'tar -xf ' + self.returnPathEnclosed(
                        self.data['fileToExtract']) + ' -C ' + self.returnPathEnclosed(self.data['extractionLocation'])

                ProcessUtilities.executioner(command)


            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def compress(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            try:
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
            except:
                if self.data['compressionType'] == 'zip':
                    compressedFileName = self.returnPathEnclosed(
                        self.data['basePath'] + '/' + self.data['compressedFileName'] + '.zip')
                    command = 'zip -r ' + compressedFileName + ' '
                else:
                    compressedFileName = self.returnPathEnclosed(
                        self.data['basePath'] + '/' + self.data['compressedFileName'] + '.tar.gz')
                    command = 'tar -czvf ' + compressedFileName + ' '

                homePath = '/'

                for item in self.data['listOfFiles']:

                    if (self.data['basePath'] + item).find('..') > -1 or (self.data['basePath'] + item).find(
                            homePath) == -1:
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')
                    command = '%s%s ' % (command, self.returnPathEnclosed(item))

                finalCommand = 'cd %s && %s' % (self.data['basePath'], command)

                res = ProcessUtilities.outputExecutioner(finalCommand, "root")
                logging.writeToFile("compress file res %s"%res)

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

        ### symlink checks

        command = 'ls -la /home/%s' % domainName
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('->') > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Symlink attack."})
            return HttpResponse(final_json)

        command = 'chown %s:%s /home/%s' % (website.externalApp, website.externalApp, domainName)
        ProcessUtilities.popenExecutioner(command)

        ### Sym link checks

        command = 'ls -la /home/%s/public_html/' % domainName
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('->') > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Symlink attack."})
            return HttpResponse(final_json)

        command = 'chown -R -P %s:%s /home/%s/public_html/*' % (externalApp, externalApp, domainName)
        ProcessUtilities.popenExecutioner(command)

        command = 'chown -R -P %s:%s /home/%s/public_html/.[^.]*' % (externalApp, externalApp, domainName)
        ProcessUtilities.popenExecutioner(command)

        # command = "chown root:%s /home/" % (groupName) + domainName + "/logs"
        # ProcessUtilities.popenExecutioner(command)

        command = "find %s -type d -exec chmod 0755 {} \;" % ("/home/" + domainName + "/public_html")
        ProcessUtilities.popenExecutioner(command)

        command = "find %s -type f -exec chmod 0644 {} \;" % ("/home/" + domainName + "/public_html")
        ProcessUtilities.popenExecutioner(command)

        command = 'chown %s:%s /home/%s/public_html' % (externalApp, groupName, domainName)
        ProcessUtilities.executioner(command)

        command = 'chmod 750 /home/%s/public_html' % (domainName)
        ProcessUtilities.executioner(command)

        for childs in website.childdomains_set.all():
            command = 'ls -la %s' % childs.path
            result = ProcessUtilities.outputExecutioner(command)

            if result.find('->') > -1:
                final_json = json.dumps(
                    {'status': 0, 'logstatus': 0,
                     'error_message': "Symlink attack."})
                return HttpResponse(final_json)


            command = "find %s -type d -exec chmod 0755 {} \;" % (childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = "find %s -type f -exec chmod 0644 {} \;" % (childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chown -R -P %s:%s %s/*' % (externalApp, externalApp, childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chown -R -P %s:%s %s/.[^.]*' % (externalApp, externalApp, childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chmod 755 %s' % (childs.path)
            ProcessUtilities.popenExecutioner(command)

            command = 'chown %s:%s %s' % (externalApp, groupName, childs.path)
            ProcessUtilities.popenExecutioner(command)
