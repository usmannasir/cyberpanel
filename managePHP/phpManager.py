from plogical.processUtilities import ProcessUtilities
import json
import re
from django.shortcuts import HttpResponse
from random import randint
from .models import *
from xml.etree import ElementTree
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

class PHPManager:

    @staticmethod
    def findPHPVersions():
        distro = ProcessUtilities.decideDistro()
        if distro == ProcessUtilities.centos:
            if distro == ProcessUtilities.cent8:
                return ['PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4']
            return ['PHP 5.3', 'PHP 5.4', 'PHP 5.5', 'PHP 5.6', 'PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4']
        else:
            return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4']

    @staticmethod
    def getPHPString(phpVersion):

        if phpVersion == "PHP 5.3":
            php = "53"
        elif phpVersion == "PHP 5.4":
            php = "54"
        elif phpVersion == "PHP 5.5":
            php = "55"
        elif phpVersion == "PHP 5.6":
            php = "56"
        elif phpVersion == "PHP 7.0":
            php = "70"
        elif phpVersion == "PHP 7.1":
            php = "71"
        elif phpVersion == "PHP 7.2":
            php = "72"
        elif phpVersion == "PHP 7.3":
            php = "73"
        elif phpVersion == "PHP 7.4":
            php = "74"

        return php

    @staticmethod
    def FindPHPFPMPath(phpVersion):
        if phpVersion == "PHP 5.3":
            return "/opt/remi/php54/root/etc/php.ini"
        elif phpVersion == "PHP 5.4":
            return "/opt/remi/php54/root/etc/php.ini"
        elif phpVersion == "PHP 5.5":
            return "/opt/remi/php55/root/etc/php.ini"
        elif phpVersion == "PHP 5.6":
            return "/etc/opt/remi/php56/php.ini"
        elif phpVersion == "PHP 7.0":
            return "/etc/opt/remi/php70/php.ini"
        elif phpVersion == "PHP 7.1":
            return "/etc/opt/remi/php71/php.ini"
        elif phpVersion == "PHP 7.2":
            return "/etc/opt/remi/php72/php.ini"
        elif phpVersion == "PHP 7.3":
            return "/etc/opt/remi/php73/php.ini"

    @staticmethod
    def getCurrentPHPConfig(phpVersion):
        allow_url_fopen = "0"
        display_errors = "0"
        file_uploads = "0"
        allow_url_include = "0"
        memory_limit = ""
        max_execution_time = ""
        upload_max_filesize = ""
        max_input_time = ""

        command = "sudo cat " + PHPManager.FindPHPFPMPath(phpVersion)

        data = ProcessUtilities.outputExecutioner(command).split('\n')

        for items in data:
            if items.find("allow_url_fopen") > -1 and items.find("=") > -1:
                if items.find("On") > -1:
                    allow_url_fopen = "1"
            if items.find("display_errors") > -1 and items.find("=") > -1:
                if items.find("On") > -1:
                    display_errors = "1"
            if items.find("file_uploads") > -1 and items.find("=") > -1:
                if items.find("On") > -1:
                    file_uploads = "1"
            if items.find("allow_url_include") > -1 and items.find("=") > -1:
                if items.find("On") > -1:
                    allow_url_include = "1"
            if items.find("memory_limit") > -1 and items.find("=") > -1:
                memory_limit = re.findall(r"[A-Za-z0-9_]+", items)[1]
            if items.find("max_execution_time") > -1 and items.find("=") > -1:
                max_execution_time = re.findall(r"[A-Za-z0-9_]+", items)[1]
            if items.find("upload_max_filesize") > -1 and items.find("=") > -1:
                upload_max_filesize = re.findall(r"[A-Za-z0-9_]+", items)[1]
            if items.find("max_input_time") > -1 and items.find("=") > -1:
                max_input_time = re.findall(r"[A-Za-z0-9_]+", items)[1]
            if items.find("post_max_size") > -1 and items.find("=") > -1:
                post_max_size = re.findall(r"[A-Za-z0-9_]+", items)[1]

        final_dic = {'fetchStatus': 1,
                     'allow_url_fopen': allow_url_fopen,
                     'display_errors': display_errors,
                     'file_uploads': file_uploads,
                     'allow_url_include': allow_url_include,
                     'memory_limit': memory_limit,
                     'max_execution_time': max_execution_time,
                     'upload_max_filesize': upload_max_filesize,
                     'max_input_time': max_input_time,
                     'post_max_size': post_max_size,
                     'status': 1}

        final_json = json.dumps(final_dic)

        return HttpResponse(final_json)

    @staticmethod
    def savePHPConfigBasic(data):
        phpVersion = data['phpVersion']
        allow_url_fopen = data['allow_url_fopen']
        display_errors = data['display_errors']
        file_uploads = data['file_uploads']
        allow_url_include = data['allow_url_include']
        memory_limit = data['memory_limit']
        max_execution_time = data['max_execution_time']
        upload_max_filesize = data['upload_max_filesize']
        max_input_time = data['max_input_time']
        post_max_size = data['post_max_size']

        if allow_url_fopen == True:
            allow_url_fopen = "allow_url_fopen = On"
        else:
            allow_url_fopen = "allow_url_fopen = Off"

        if display_errors == True:
            display_errors = "display_errors = On"
        else:
            display_errors = "display_errors = Off"

        if file_uploads == True:
            file_uploads = "file_uploads = On"
        else:
            file_uploads = "file_uploads = Off"

        if allow_url_include == True:
            allow_url_include = "allow_url_include = On"
        else:
            allow_url_include = "allow_url_include = Off"

        path = PHPManager.FindPHPFPMPath(phpVersion)
        command = "sudo cat " + path
        data = ProcessUtilities.outputExecutioner(command).splitlines()

        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        writeToFile = open(tempStatusPath, 'w')

        for items in data:
            if items.find("allow_url_fopen") > -1 and items.find("=") > -1:
                writeToFile.writelines(allow_url_fopen + "\n")
            elif items.find("display_errors") > -1 and items.find("=") > -1:
                writeToFile.writelines(display_errors + "\n")
            elif items.find("file_uploads") > -1 and items.find("=") > -1 and not items.find(
                    "max_file_uploads") > -1:
                writeToFile.writelines(file_uploads + "\n")
            elif items.find("allow_url_include") > -1 and items.find("=") > -1:
                writeToFile.writelines(allow_url_include + "\n")

            elif items.find("memory_limit") > -1 and items.find("=") > -1:
                writeToFile.writelines("memory_limit = " + memory_limit + "\n")

            elif items.find("max_execution_time") > -1 and items.find("=") > -1:
                writeToFile.writelines("max_execution_time = " + max_execution_time + "\n")

            elif items.find("upload_max_filesize") > -1 and items.find("=") > -1:
                writeToFile.writelines("upload_max_filesize = " + upload_max_filesize + "\n")

            elif items.find("max_input_time") > -1 and items.find("=") > -1:
                writeToFile.writelines("max_input_time = " + max_input_time + "\n")
            elif items.find("post_max_size") > -1 and items.find("=") > -1:
                writeToFile.writelines("post_max_size = " + post_max_size + "\n")
            else:
                writeToFile.writelines(items + '\n')

        writeToFile.close()

        command = "sudo mv %s %s" % (tempStatusPath, path)
        ProcessUtilities.executioner(command)

        php = PHPManager.getPHPString(phpVersion)

        command = "systemctl stop php%s-php-fpm" % (php)
        ProcessUtilities.executioner(command)

        command = "systemctl start php%s-php-fpm" % (php)
        ProcessUtilities.executioner(command)

        final_dic = {'status': 1}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    @staticmethod
    def fetchPHPSettingsAdvance(phpVersion):
        command = "sudo cat " + PHPManager.FindPHPFPMPath(phpVersion)
        data = ProcessUtilities.outputExecutioner(command)
        final_dic = {'fetchStatus': 1,
                     'configData': data,
                     'status': 1}

        final_json = json.dumps(final_dic)

        return HttpResponse(final_json)

    @staticmethod
    def savePHPConfigAdvance(data):
        phpVersion = data['phpVersion']
        configData = data['configData']

        path = PHPManager.FindPHPFPMPath(phpVersion)

        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        writeToFile = open(tempStatusPath, 'w')
        writeToFile.write(configData)
        writeToFile.close()

        command = "sudo mv %s %s" % (tempStatusPath, path)
        ProcessUtilities.executioner(command)

        php = PHPManager.getPHPString(phpVersion)

        command = "systemctl stop php%s-php-fpm" % (php)
        ProcessUtilities.executioner(command)

        command = "systemctl start php%s-php-fpm" % (php)
        ProcessUtilities.executioner(command)

        final_dic = {'status': 1}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    @staticmethod
    def fetchPHPExtensions(data):

        if ApachePHP.objects.all().count() == 0:
            phpfilePath = '/usr/local/CyberCP/ApachController/phpApache.xml'

            for items in ['54', '55', '56', '70', '71', '72', '73']:
                phpvers = ApachePHP(phpVers='php' + items)
                phpvers.save()

                php = ElementTree.parse(phpfilePath)
                phpExtensions = php.findall('extension')

                for extension in phpExtensions:
                    extensionName = extension.find('extensionName').text % (items)
                    extensionDescription = extension.find('extensionDescription').text
                    status = int(extension.find('status').text)

                    phpExtension = installedPackagesApache(phpVers=phpvers,
                                                     extensionName=extensionName,
                                                     description=extensionDescription,
                                                     status=status)

                    phpExtension.save()

        phpVers = "php" + PHPManager.getPHPString(data['phpVersion'])

        phpVersion = ApachePHP.objects.get(phpVers=phpVers)

        records = phpVersion.installedpackagesapache_set.all()

        json_data = "["
        checker = 0

        for items in records:

            if items.status == 0:
                status = "Not-Installed"
            else:
                status = "Installed"

            dic = {'id': items.id,
                   'phpVers': items.phpVers.phpVers,
                   'extensionName': items.extensionName,
                   'description': items.description,
                   'status': status
                   }

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'
        final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)




