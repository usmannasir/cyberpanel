import os
import re
import secrets
import shlex
import sys

from django.shortcuts import HttpResponse
import json
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from websiteFunctions.models import Websites
from random import randint
from django.core.files.storage import FileSystemStorage
from plogical.acl import ACLManager
from filemanager.rootEntitlements import require_root_entitlement, root_entitlement_required
from plogical.archiveExtractionJobs import (
    build_archive_extraction_command,
    create_archive_extraction_job,
    get_archive_extraction_status,
)
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
    def editorTheme(theme):
        # The name comes from the address and is written into the page as markup.
        if isinstance(theme, str) and re.fullmatch(r'[a-z0-9-]{1,40}', theme):
            return theme
        return 'cobalt'

    @staticmethod
    def findThemeFile(theme):
        return '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.58.1/theme/%s.min.css" />' % (
            FileManager.editorTheme(theme))

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
        return "'" + str(path).replace("'", "'\"'\"'") + "'"

    @staticmethod
    def safeUploadPath(path):
        # Upload paths are shell-quoted by returnPathEnclosed. Permit common
        # literal filename punctuation without relaxing the shared command gate.
        value = str(path)
        if any(character in value for character in ('\x00', '\r', '\n')):
            return False
        for character in ("'", '(', ')'):
            value = value.replace(character, '')
        return ACLManager.commandInjectionCheck(value) != 1

    def validPermissions(self, permissions):
        try:
            permissions = str(permissions)
            return len(permissions) in (3, 4) and all(ch in '01234567' for ch in permissions)
        except:
            return False

    def pathInside(self, path, root):
        try:
            real_path = os.path.realpath(path)
            real_root = os.path.realpath(root)
            return os.path.commonpath([real_path, real_root]) == real_root
        except:
            return False

    def notInside(self, path, root):
        # Returns True when `path` is NOT safely contained within `root`.
        # Rejects literal '..' and, after resolving symlinks/'..', any path that
        # escapes `root`. This fixes the previous substring check which could be
        # bypassed via symlinks or a non-prefix match of the home path.
        if '..' in str(path):
            return True
        return not self.pathInside(path, root)

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
    
    
    @root_entitlement_required
    def listForTable(self):
        try:
            finalData = {}
            finalData['status'] = 1

            try:

                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)

                pathCheck = '/home/%s' % (domainName)

                if self.notInside(self.data['completeStartingPath'], pathCheck):
                    return self.ajaxPre(0, 'Not allowed to browse this path, going back home!')

                command = "ls -la --group-directories-first " + self.returnPathEnclosed(
                    self.data['completeStartingPath'])
                output = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()

            except:
                require_root_entitlement(self.data)
                pathCheck = '/'

                if self.notInside(self.data['completeStartingPath'], pathCheck):
                    return self.ajaxPre(0, 'Not allowed to browse this path, going back home!')

                command = "ls -la --group-directories-first " + self.returnPathEnclosed(
                    self.data['completeStartingPath'])
                output = ProcessUtilities.outputExecutioner(command).splitlines()

            counter = 0
            for items in output:
                try:
                    currentFile = items.split(' ')
                    currentFile = [a for a in currentFile if a != '']

                    if currentFile[-1] == '.' or currentFile[-1] == '..' or currentFile[0] == 'total' or currentFile[-1].startswith('mail.'):
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

    @root_entitlement_required
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
                require_root_entitlement(self.data)
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

    @root_entitlement_required
    def createNewFile(self):
        try:
            finalData = {}
            finalData['status'] = 1

            try:
                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)
                homePath = '/home/%s' % (domainName)

                if self.notInside(self.data['fileName'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "touch " + self.returnPathEnclosed(self.data['fileName'])
                ProcessUtilities.executioner(command, website.externalApp)
                self.changeOwner(self.data['fileName'])
            except:
                require_root_entitlement(self.data)
                homePath = '/'

                if self.notInside(self.data['fileName'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "touch " + self.returnPathEnclosed(self.data['fileName'])
                ProcessUtilities.executioner(command)
                self.changeOwner(self.data['fileName'])

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    @root_entitlement_required
    def createNewFolder(self):
        try:
            finalData = {}
            finalData['status'] = 1
            try:
                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)

                homePath = '/home/%s' % (domainName)

                if self.notInside(self.data['folderName'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "mkdir " + self.returnPathEnclosed(self.data['folderName'])
                ProcessUtilities.executioner(command, website.externalApp)

                self.changeOwner(self.data['folderName'])
            except:
                require_root_entitlement(self.data)
                homePath = '/'

                if self.notInside(self.data['folderName'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = "mkdir " + self.returnPathEnclosed(self.data['folderName'])
                ProcessUtilities.executioner(command)

                self.changeOwner(self.data['folderName'])


            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    @root_entitlement_required
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

                # The probe file sits in the customer's own home, where its name
                # can be a link: touch only the name itself, as the site's own user.
                command = 'touch -h %s' % (self.returnPathEnclosed(self.homePath + '/hello.txt'))
                result = ProcessUtilities.outputExecutioner(command, website.externalApp)

                if result.find('No such file or directory') > -1:
                    RemoveOK = 0

                    command = 'chattr -R -i %s' % (self.returnPathEnclosed(self.homePath))
                    ProcessUtilities.executioner(command)

                else:
                    command = 'rm -f %s' % (self.returnPathEnclosed(self.homePath + '/hello.txt'))
                    ProcessUtilities.executioner(command, website.externalApp)


                for item in self.data['fileAndFolders']:

                    if self.notInside(self.data['path'] + '/' + item, self.homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    if skipTrash:
                        command = 'rm -rf ' + self.returnPathEnclosed(self.data['path'] + '/' + item)
                        ProcessUtilities.executioner(command, website.externalApp)
                    else:
                        trashPath = '%s/.trash' % (self.homePath)

                        command = 'mkdir %s' % (self.returnPathEnclosed(trashPath))
                        ProcessUtilities.executioner(command, website.externalApp)

                        Trash(website=website, originalPath=self.returnPathEnclosed(self.data['path']),
                              fileName=self.returnPathEnclosed(item)).save()

                        command = 'mv %s %s' % (
                            self.returnPathEnclosed(self.data['path'] + '/' + item),
                            self.returnPathEnclosed(trashPath))
                        ProcessUtilities.executioner(command, website.externalApp)

                if RemoveOK == 0:
                    command = 'chattr -R +i %s' % (self.returnPathEnclosed(self.homePath))
                    ProcessUtilities.executioner(command)
            except:
                require_root_entitlement(self.data)
                try:
                    skipTrash = self.data['skipTrash']
                except:
                    skipTrash = False


                self.homePath = '/'

                RemoveOK = 1

                command = 'touch %s' % (self.returnPathEnclosed(self.homePath + '/hello.txt'))
                result = ProcessUtilities.outputExecutioner(command)

                if result.find('No such file or directory') > -1:
                    RemoveOK = 0

                    command = 'chattr -R -i %s' % (self.returnPathEnclosed(self.homePath))
                    ProcessUtilities.executioner(command)

                else:
                    command = 'rm -f %s' % (self.returnPathEnclosed(self.homePath + '/hello.txt'))
                    ProcessUtilities.executioner(command)

                for item in self.data['fileAndFolders']:

                    if self.notInside(self.data['path'] + '/' + item, self.homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    if skipTrash:
                        command = 'rm -rf ' + self.returnPathEnclosed(self.data['path'] + '/' + item)
                        ProcessUtilities.executioner(command)


                if RemoveOK == 0:
                    command = 'chattr -R +i %s' % (self.returnPathEnclosed(self.homePath))
                    ProcessUtilities.executioner(command)

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    @root_entitlement_required
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

                if self.notInside(self.data['path'] + '/' + item, self.homePath):
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

    @root_entitlement_required
    def copy(self):
        try:

            finalData = {}
            finalData['status'] = 1

            domainName = self.data['domainName']
            try:
                website = Websites.objects.get(domain=domainName)

                homePath = '/home/%s' % (domainName)

                if self.notInside(self.data['newPath'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if len(self.data['fileAndFolders']) == 1:

                    if self.notInside(self.data['basePath'] + '/' + self.data['fileAndFolders'][0], homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = 'yes| cp -Rf %s %s' % (
                        self.returnPathEnclosed(self.data['basePath'] + '/' + self.data['fileAndFolders'][0]),
                        self.returnPathEnclosed(self.data['newPath']))
                    ProcessUtilities.executioner(command, website.externalApp)
                    self.changeOwner(self.data['newPath'])
                    json_data = json.dumps(finalData)
                    return HttpResponse(json_data)

                command = 'mkdir ' + self.returnPathEnclosed(self.data['newPath'])
                ProcessUtilities.executioner(command, website.externalApp)

                for item in self.data['fileAndFolders']:
                    if self.notInside(self.data['basePath'] + '/' + item, homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = '%scp -Rf ' % ('yes |') + self.returnPathEnclosed(
                        self.data['basePath'] + '/' + item) + ' ' + self.returnPathEnclosed(self.data['newPath'])
                    ProcessUtilities.executioner(command, website.externalApp)

                self.changeOwner(self.data['newPath'])
            except:


                require_root_entitlement(self.data)
                homePath = '/'

                if self.notInside(self.data['newPath'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if len(self.data['fileAndFolders']) == 1:

                    if self.notInside(self.data['basePath'] + '/' + self.data['fileAndFolders'][0], homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = 'yes| cp -Rf %s %s' % (
                        self.returnPathEnclosed(self.data['basePath'] + '/' + self.data['fileAndFolders'][0]),
                        self.returnPathEnclosed(self.data['newPath']))
                    ProcessUtilities.executioner(command,)
                    self.changeOwner(self.data['newPath'])
                    json_data = json.dumps(finalData)
                    return HttpResponse(json_data)

                command = 'mkdir ' + self.returnPathEnclosed(self.data['newPath'])
                ProcessUtilities.executioner(command)

                for item in self.data['fileAndFolders']:
                    if self.notInside(self.data['basePath'] + '/' + item, homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = '%scp -Rf ' % ('yes |') + self.returnPathEnclosed(
                        self.data['basePath'] + '/' + item) + ' ' + self.returnPathEnclosed(self.data['newPath'])
                    ProcessUtilities.executioner(command)

                self.changeOwner(self.data['newPath'])

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    @root_entitlement_required
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

                    if self.notInside(self.data['basePath'] + '/' + item, homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    if self.notInside(self.data['newPath'] + '/' + item, homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = 'mv ' + self.returnPathEnclosed(
                        self.data['basePath'] + '/' + item) + ' ' + self.returnPathEnclosed(
                        self.data['newPath'] + '/' + item)
                    ProcessUtilities.executioner(command, website.externalApp)

                #self.changeOwner(self.data['newPath'])

                #self.fixPermissions(domainName)
            except:


                require_root_entitlement(self.data)
                homePath = '/'

                command = 'mkdir ' + self.returnPathEnclosed(self.data['newPath'])
                ProcessUtilities.executioner(command)

                for item in self.data['fileAndFolders']:

                    if self.notInside(self.data['basePath'] + '/' + item, homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    if self.notInside(self.data['newPath'] + '/' + item, homePath):
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

    @root_entitlement_required
    def rename(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            try:
                website = Websites.objects.get(domain=domainName)

                homePath = '/home/%s' % (domainName)

                if self.notInside(self.data['basePath'] + '/' + self.data['existingName'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if '..' in str(self.data['newFileName']) or self.notInside(self.data['basePath'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'mv ' + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['existingName']) + ' ' + self.returnPathEnclosed(
                    self.data['basePath'] + '/' + self.data['newFileName'])
                ProcessUtilities.executioner(command, website.externalApp)

                self.changeOwner(self.data['basePath'] + '/' + self.data['newFileName'])
            except:
                require_root_entitlement(self.data)
                homePath = '/'

                if self.notInside(self.data['basePath'] + '/' + self.data['existingName'], homePath):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if '..' in str(self.data['newFileName']) or self.notInside(self.data['basePath'], homePath):
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

    @root_entitlement_required
    def readFileContents(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data.get('domainName', '')
            if domainName:
                try:
                    website = Websites.objects.get(domain=domainName)
                except Websites.DoesNotExist:
                    return self.ajaxPre(0, 'Not allowed.')
                pathCheck = '/home/%s' % (domainName)
            else:
                pathCheck = '/'

            pythonPath = '/usr/local/CyberCP/bin/python'
            if not os.path.exists(pythonPath):
                pythonPath = sys.executable
            readScript = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'plogical',
                'safeFileRead.py',
            )
            command = '%s %s --allowed-root %s --file %s' % (
                shlex.quote(pythonPath),
                shlex.quote(readScript),
                shlex.quote(pathCheck),
                shlex.quote(self.data['fileName']),
            )
            websiteUser = website.externalApp if domainName else None
            readStatus, fileContents = ProcessUtilities.outputExecutioner(
                command,
                websiteUser,
                shell=False,
                retRequired=True,
            )
            if readStatus != 1:
                if fileContents.strip() == 'CYBERPANEL_FILE_TOO_LARGE':
                    return self.ajaxPre(0, 'Files larger than 4 MiB cannot be opened in the editor. Download the file to inspect it locally.')
                return self.ajaxPre(0, 'Not allowed.')
            finalData['fileContents'] = fileContents


            # Ensure proper UTF-8 encoding in JSON response
            json_data = json.dumps(finalData, ensure_ascii=False)
            return HttpResponse(json_data, content_type='application/json; charset=utf-8')

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    @root_entitlement_required
    def writeFileContents(self):
        try:

            finalData = {}
            finalData['status'] = 1
            try:
                self.data['home'] = '/home/%s' % (self.data['domainName'])

                ACLManager.CreateSecureDir()
                tempPath = '%s/%s' % ('/usr/local/CyberCP/tmp', secrets.token_hex(16))

                domainName = self.data['domainName']
                website = Websites.objects.get(domain=domainName)

                if not self.pathInside(self.data['fileName'], self.data['home']):
                    return self.ajaxPre(0, 'Not allowed.')

                writeToFile = os.fdopen(os.open(
                    tempPath, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb')
                writeToFile.write(self.data['fileContent'].encode('utf-8'))
                writeToFile.close()

                command = 'chown %s:%s %s' % (website.externalApp, website.externalApp, tempPath)
                ProcessUtilities.executioner(command)

                command = 'cp %s %s' % (tempPath, self.returnPathEnclosed(self.data['fileName']))
                ProcessUtilities.executioner(command, website.externalApp)

                os.remove(tempPath)
            except:
                require_root_entitlement(self.data)
                if self.data.get('domainName', '') != '':
                    return self.ajaxPre(0, 'Not allowed.')

                self.data['home'] = '/'

                if self.data['fileName'].find('..') > -1 or not self.data['fileName'].startswith('/'):
                    return self.ajaxPre(0, 'Not allowed.')

                ACLManager.CreateSecureDir()
                tempPath = '%s/%s' % ('/usr/local/CyberCP/tmp', secrets.token_hex(16))
                writeToFile = os.fdopen(os.open(
                    tempPath, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb')
                writeToFile.write(self.data['fileContent'].encode('utf-8'))
                writeToFile.close()

                command = 'cp %s %s' % (tempPath, self.returnPathEnclosed(self.data['fileName']))
                ProcessUtilities.executioner(command)

                os.remove(tempPath)


            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    @root_entitlement_required
    def upload(self):
        try:

            finalData = {}
            finalData['uploadStatus'] = 1
            finalData['answer'] = 'File transfer completed.'

            ACLManager.CreateSecureDir()
            UploadPath = '/usr/local/CyberCP/tmp/'

            ## Random file name

            # An unguessable name in the shared temporary directory: another
            # customer must not be able to name, read or receive this file.
            RanddomFileName = secrets.token_hex(16)

            myfile = self.request.FILES['file']
            fs = FileSystemStorage()

            try:
                filename = fs.save(RanddomFileName, myfile)
                finalData['fileName'] = fs.url(filename)
            except BaseException as msg:
                logging.writeToFile('%s. [375:upload]' % (str(msg)))
                return self.ajaxPre(0, 'The uploaded file could not be stored.')

            # Copy exactly the file that was stored, under the name it was given.
            RanddomFileName = os.path.basename(filename)



            domainName = self.data['domainName']
            try:
                pathCheck = '/home/%s' % (self.data['domainName'])
                website = Websites.objects.get(domain=domainName)

                command = 'ls -la %s' % (self.returnPathEnclosed(self.data['completePath']))
                result = ProcessUtilities.outputExecutioner(command, website.externalApp)
                #
                if result.find('->') > -1:
                    return self.ajaxPre(0, "Symlink attack.")

                if not self.safeUploadPath(self.data['completePath'] + '/' + myfile.name):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if self.notInside(self.data['completePath'] + '/' + myfile.name, pathCheck):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'cp ' + self.returnPathEnclosed(
                    UploadPath + RanddomFileName) + ' ' + self.returnPathEnclosed(
                    self.data['completePath'] + '/' + myfile.name)
                ProcessUtilities.executioner(command, website.externalApp)

                self.changeOwner(self.data['completePath'] + '/' + myfile.name)
                try:
                    os.remove(UploadPath + RanddomFileName)
                except:
                    pass
            except:
                require_root_entitlement(self.data)
                pathCheck = '/'
                command = 'ls -la %s' % (self.returnPathEnclosed(self.data['completePath']))
                result = ProcessUtilities.outputExecutioner(command)
                logging.writeToFile("upload file res %s" % result)
                if not self.safeUploadPath(self.data['completePath'] + '/' + myfile.name):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                if self.notInside(self.data['completePath'] + '/' + myfile.name, pathCheck):
                    return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                command = 'cp ' + self.returnPathEnclosed(
                    UploadPath + RanddomFileName) + ' ' + self.returnPathEnclosed(
                    self.data['completePath'] + '/' + myfile.name)
                ProcessUtilities.executioner(command)

                self.changeOwner(self.data['completePath'] + '/' + myfile.name)
                try:
                    os.remove(UploadPath + RanddomFileName)
                except:
                    pass



            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))
        finally:
            # Whatever happened, the stored copy does not stay behind.
            try:
                os.remove(UploadPath + RanddomFileName)
            except:
                pass

    @root_entitlement_required
    def extract(self):
        try:

            finalData = {}
            finalData['status'] = 1

            domainName = self.data.get('domainName', '')
            websiteUser = None
            if domainName:
                try:
                    website = Websites.objects.get(domain=domainName)
                except Websites.DoesNotExist:
                    return self.ajaxPre(0, 'Not allowed.')
                homePath = '/home/%s' % (domainName)
                websiteUser = website.externalApp
            else:
                homePath = '/'

            if self.notInside(self.data['extractionLocation'], homePath):
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')
            if self.notInside(self.data['fileToExtract'], homePath):
                return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

            extractionType = self.data['extractionType']
            if extractionType not in ('zip', 'tar', 'tar.gz', 'tgz'):
                return self.ajaxPre(0, 'Unsupported archive type.')

            pythonPath = '/usr/local/CyberCP/bin/python'
            if not os.path.exists(pythonPath):
                pythonPath = sys.executable
            jobToken, statusPath = create_archive_extraction_job(
                self.request.session['userID'],
                domainName,
            )
            command = build_archive_extraction_command(
                token=jobToken,
                status_path=statusPath,
                allowed_root=homePath,
                archive_path=self.data['fileToExtract'],
                destination=self.data['extractionLocation'],
                archive_type=extractionType,
                run_as=websiteUser,
                python_path=pythonPath,
            )
            result = ProcessUtilities.executioner(command)
            if result != 1:
                return self.ajaxPre(0, 'Archive extraction could not be started.')

            finalData['job'] = jobToken
            finalData['state'] = 'queued'
            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def extractionStatus(self):
        try:
            domainName = self.data.get('domainName', '')
            status = get_archive_extraction_status(
                self.data.get('job', ''),
                self.request.session['userID'],
                domainName,
            )
            status['status'] = 1
            return HttpResponse(json.dumps(status))
        except PermissionError:
            return self.ajaxPre(0, 'Archive extraction job is not available.')
        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [FileManager.extractionStatus]')
            return self.ajaxPre(0, 'Archive extraction status is not available.')

    @root_entitlement_required
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

                    if self.notInside(self.data['basePath'] + item, homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')

                    command = '%s%s ' % (command, self.returnPathEnclosed(item))

                finalCommand = 'cd %s && %s' % (self.returnPathEnclosed(self.data['basePath']), command)

                ProcessUtilities.executioner(finalCommand, website.externalApp)

                self.changeOwner(self.data['compressedFileName'])
            except:
                require_root_entitlement(self.data)
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

                    if self.notInside(self.data['basePath'] + item, homePath):
                        return self.ajaxPre(0, 'Not allowed to move in this path, please choose location inside home!')
                    command = '%s%s ' % (command, self.returnPathEnclosed(item))

                finalCommand = 'cd %s && %s' % (self.returnPathEnclosed(self.data['basePath']), command)

                res = ProcessUtilities.outputExecutioner(finalCommand, "root")
                logging.writeToFile("compress file res %s"%res)

                self.changeOwner(self.data['compressedFileName'])

            json_data = json.dumps(finalData)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    @root_entitlement_required
    def changePermissions(self):
        try:

            finalData = {}
            finalData['status'] = 1
            domainName = self.data['domainName']
            website = Websites.objects.get(domain=domainName)

            if not self.validPermissions(self.data['newPermissions']):
                return self.ajaxPre(0, 'Invalid permissions.')

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
        # Everything repaired here sits inside the website's own home, which its
        # user can rename or replace with a link at any moment. So privileged
        # commands only ever take ownership without following links, modes are set
        # by the site user itself, and the top directories are changed through
        # their own descriptors.

        website = Websites.objects.get(domain=domainName)
        externalApp = website.externalApp

        def repair(command, user=None):
            success, output = ProcessUtilities.outputExecutioner(
                command, user=user, shell=False, retRequired=True)
            if success != 1:
                logging.writeToFile('Permission repair command failed: %s' % output)
                raise RuntimeError('Permission repair failed. Check the panel log before retrying.')

        def setDirectoryOwner(allowedRoot, directory, group, mode=None):
            command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/secureDirectoryOwner.py' \
                      ' --allowed-root %s --directory %s --user %s --group %s' % (
                          self.returnPathEnclosed(allowedRoot), self.returnPathEnclosed(directory),
                          self.returnPathEnclosed(externalApp), self.returnPathEnclosed(group))
            if mode is not None:
                command = '%s --mode %s' % (command, mode)
            repair(command)

        def repairTree(path):
            argument = self.returnPathEnclosed(path)

            # Ownership first, with privilege and without following links. After
            # this the whole tree belongs to the site user. Recurse the directory
            # itself instead of a "path/*" shell glob: commands that run as root go
            # through subprocess with shell=False, so a glob was handed to chown
            # literally and left restored files owned by root (#1735).
            repair('chown -R -P %s:%s %s' % (externalApp, externalApp, argument))

            # Modes are set by the site user: a path it swapped for a link can then
            # reach nothing that user could not change already.
            repair('chmod 750 %s' % argument, externalApp)
            repair("find %s -mindepth 1 -type d -exec chmod 0755 {} +" % argument, externalApp)
            repair("find %s -type f -exec chmod 0644 {} +" % argument, externalApp)

            # Keep the document root restricted: owner, web server group, 750.
            setDirectoryOwner(homePath, path, groupName, '750')

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            groupName = 'nobody'
        else:
            groupName = 'nogroup'

        ### symlink checks

        homePath = '/home/%s' % domainName
        publicHtmlPath = '%s/public_html' % homePath

        command = 'ls -la %s' % self.returnPathEnclosed(homePath)
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('->') > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Symlink attack."})
            return HttpResponse(final_json)

        # Set home directory ownership
        setDirectoryOwner('/home', homePath, externalApp)

        ### Sym link checks

        command = 'ls -la %s' % self.returnPathEnclosed(publicHtmlPath)
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('->') > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Symlink attack."})
            return HttpResponse(final_json)

        repairTree(publicHtmlPath)

        # Child domains, including document roots outside public_html
        for childs in website.childdomains_set.all():
            childPath = childs.path

            command = 'ls -la %s' % self.returnPathEnclosed(childPath)
            result = ProcessUtilities.outputExecutioner(command)

            if result.find('->') > -1:
                final_json = json.dumps(
                    {'status': 0, 'logstatus': 0,
                     'error_message': "Symlink attack."})
                return HttpResponse(final_json)

            repairTree(childPath)
