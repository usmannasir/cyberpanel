import os.path
import shlex
import tempfile

from plogical.processUtilities import ProcessUtilities
import json
import re
from django.shortcuts import HttpResponse
from random import randint
from .models import *
from .phpConfig import apply_basic_php_settings, checked_basic_php_settings, matches_directive
from xml.etree import ElementTree

class PHPManager:

    @staticmethod
    def findPHPVersions():
        # distro = ProcessUtilities.decideDistro()
        # if distro == ProcessUtilities.centos:
        #     return ['PHP 5.3', 'PHP 5.4', 'PHP 5.5', 'PHP 5.6', 'PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
        # elif distro == ProcessUtilities.cent8:
        #     return ['PHP 7.1','PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
        # elif distro == ProcessUtilities.ubuntu20:
        #     return ['PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
        # else:
        #     return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1', 'PHP 8.2', 'PHP 8.3', 'PHP 8.4', 'PHP 8.5']

        try:

            # Run the shell command and capture the output
            result = ProcessUtilities.outputExecutioner('ls -la /usr/local/lsws')

            # Get the lines containing 'lsphp' in the output
            lsphp_lines = [line for line in result.split('\n') if 'lsphp' in line]


            if os.path.exists(ProcessUtilities.debugPath):
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f'Found PHP lines in findPHPVersions: {lsphp_lines}')


            # Extract the version from the lines and format it as 'PHP x.y'
            php_versions = ['PHP ' + line.split()[8][5] + '.' + line.split()[8][6:] for line in lsphp_lines]

            finalPHPVersions = []
            for php in php_versions:
                try:
                    phpString = PHPManager.getPHPString(php)
                except ValueError:
                    # Not an lsphp<digits> directory (a copy such as lsphp74.bak).
                    continue

                if os.path.exists("/usr/local/lsws/lsphp" + str(phpString) + "/bin/lsphp"):
                    finalPHPVersions.append(php)

            if os.path.exists(ProcessUtilities.debugPath):
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f'Found PHP versions in findPHPVersions: {finalPHPVersions}')

            # Now php_versions contains the formatted PHP versions
            return finalPHPVersions
        except BaseException as msg:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            logging.writeToFile(f'Error while finding php versions on system: {str(msg)}')
            return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1', 'PHP 8.2', 'PHP 8.3', 'PHP 8.4', 'PHP 8.5']

    @staticmethod
    def findApachePHPVersions():
        # distro = ProcessUtilities.decideDistro()
        # if distro == ProcessUtilities.centos:
        #     return ['PHP 5.3', 'PHP 5.4', 'PHP 5.5', 'PHP 5.6', 'PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
        # elif distro == ProcessUtilities.cent8:
        #     return ['PHP 7.1','PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
        # elif distro == ProcessUtilities.ubuntu20:
        #     return ['PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1']
        # else:
        #     return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1', 'PHP 8.2', 'PHP 8.3', 'PHP 8.4', 'PHP 8.5']

        try:

            # Run the shell command and capture the output
            from ApachController.ApacheController import ApacheController as ApachController
            result = ProcessUtilities.outputExecutioner(f'ls -la {ApachController.phpBasepath}')

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

                # Get the lines containing 'lsphp' in the output
                lsphp_lines = [line for line in result.split('\n') if 'php' in line]

                if os.path.exists(ProcessUtilities.debugPath):
                    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                    logging.writeToFile(f'Found PHP lines in findApachePHPVersions: {lsphp_lines}')

                # Extract the version from the lines and format it as 'PHP x.y'
                # Extract and format PHP versions
                php_versions = []
                for entry in lsphp_lines:
                    # Find substring starting with 'php' and extract the version part
                    version = entry.split('php')[1]
                    # Format version as PHP X.Y
                    formatted_version = f"PHP {version[0]}.{version[1]}"
                    php_versions.append(formatted_version)
            else:

                lsphp_lines = [line for line in result.split('\n')]

                if os.path.exists(ProcessUtilities.debugPath):
                    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                    logging.writeToFile(f'Found PHP lines in findApachePHPVersions: {lsphp_lines}')

                # Extract the version from the lines and format it as 'PHP x.y'
                # Extract and format PHP versions
                php_versions = []
                for entry in lsphp_lines:
                    # Find substring starting with 'php' and extract the version part
                    try:
                        version = entry.split('.')
                        # Format version as PHP X.Y
                        formatted_version = f"PHP {version[-2][-1]}.{version[-1]}"
                        if formatted_version != 'PHP  .':
                            php_versions.append(formatted_version)
                    except:
                        pass




            if os.path.exists(ProcessUtilities.debugPath):
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f'Found PHP versions in findApachePHPVersions: {php_versions}')

            # Now php_versions contains the formatted PHP versions
            return php_versions
        except BaseException as msg:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            logging.writeToFile(f'Error while finding php versions on system: {str(msg)}')
            return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3', 'PHP 7.4', 'PHP 8.0', 'PHP 8.1', 'PHP 8.2', 'PHP 8.3', 'PHP 8.4', 'PHP 8.5']

    @staticmethod
    def getPHPString(phpVersion):
        # Ex: "PHP 5.3" type string, return Ex: "53" type string
        # The result becomes part of paths and command lines, also for
        # selections read back from the database, so it is digits or nothing.
        phpVersion = phpVersion.split()
        php = phpVersion[1].replace(".", "")
        if re.fullmatch(r'[0-9]{2,3}', php) is None:
            raise ValueError('Invalid PHP version selected.')

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
        # Only the versions above are managed through this interface; there
        # is no file to read or replace for anything else.
        raise ValueError('This PHP version is not managed here.')

    @staticmethod
    def installPHPIni(path, content):
        """Put new content in place of a managed php.ini, as a file of root.

        The content waits for the privileged helper in a file of its own in
        the panel's directory, which is removed whatever happens.
        """
        descriptor, tempStatusPath = tempfile.mkstemp(dir='/home/cyberpanel', prefix='phpini.')
        try:
            with os.fdopen(descriptor, 'w') as writeToFile:
                writeToFile.write(content)

            command = "install -o root -g root -m 644 -- %s %s" % (shlex.quote(tempStatusPath), shlex.quote(path))
            ProcessUtilities.executioner(command)
        finally:
            try:
                os.remove(tempStatusPath)
            except OSError:
                pass


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
        post_max_size = ""

        command = "cat " + PHPManager.FindPHPFPMPath(phpVersion)

        data = ProcessUtilities.outputExecutioner(command).split('\n')

        # Only a line that assigns a directive is read, the same lines a
        # save replaces; a comment that mentions one is not.
        for items in data:
            if matches_directive(items, "allow_url_fopen"):
                if items.find("On") > -1:
                    allow_url_fopen = "1"
            if matches_directive(items, "display_errors"):
                if items.find("On") > -1:
                    display_errors = "1"
            if matches_directive(items, "file_uploads"):
                if items.find("On") > -1:
                    file_uploads = "1"
            if matches_directive(items, "allow_url_include"):
                if items.find("On") > -1:
                    allow_url_include = "1"
            if matches_directive(items, "memory_limit"):
                memory_limit = re.findall(r"[+-]?[A-Za-z0-9_]+", items)[1]
            if matches_directive(items, "max_execution_time"):
                max_execution_time = re.findall(r"[+-]?[A-Za-z0-9_]+", items)[1]
            if matches_directive(items, "upload_max_filesize"):
                upload_max_filesize = re.findall(r"[A-Za-z0-9_]+", items)[1]
            if matches_directive(items, "max_input_time"):
                max_input_time = re.findall(r"[+-]?[A-Za-z0-9_]+", items)[1]
            if matches_directive(items, "post_max_size"):
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

        # The same checks as the PHP settings page: each of the nine values is
        # one word of its own kind, and only lines that assign a directive
        # are replaced. An unknown version stops here, before anything is read.
        path = PHPManager.FindPHPFPMPath(phpVersion)
        settings = checked_basic_php_settings({
            'allow_url_fopen': bool(allow_url_fopen), 'display_errors': bool(display_errors),
            'file_uploads': bool(file_uploads), 'allow_url_include': bool(allow_url_include),
            'memory_limit': memory_limit, 'max_execution_time': max_execution_time,
            'upload_max_filesize': upload_max_filesize, 'max_input_time': max_input_time,
            'post_max_size': post_max_size})

        command = "cat " + path
        current = ProcessUtilities.outputExecutioner(command)

        PHPManager.installPHPIni(path, apply_basic_php_settings(current, settings))

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
        command = "cat " + PHPManager.FindPHPFPMPath(phpVersion)
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

        # An unknown version stops here, before anything is written.
        path = PHPManager.FindPHPFPMPath(phpVersion)
        if not isinstance(configData, str):
            raise ValueError('Invalid PHP configuration.')

        PHPManager.installPHPIni(path, configData)

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
