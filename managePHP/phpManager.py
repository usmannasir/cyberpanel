import os.path

from plogical.processUtilities import ProcessUtilities
import json
import re
from django.shortcuts import HttpResponse
from random import randint
from .models import *
from xml.etree import ElementTree

class PHPManager:

    @staticmethod
    def findPHPVersions():
        """
        Comprehensive PHP version detection that checks multiple locations and methods
        """
        try:
            finalPHPVersions = []
            
            # Method 1: Check /usr/local/lsws directory (LiteSpeed PHP)
            try:
                result = ProcessUtilities.outputExecutioner('ls -la /usr/local/lsws')
                lsphp_lines = [line for line in result.split('\n') if 'lsphp' in line]

                if os.path.exists(ProcessUtilities.debugPath):
                    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                    logging.writeToFile(f'Found PHP lines in findPHPVersions: {lsphp_lines}')

                # Parse lsphp directories
                for line in lsphp_lines:
                    try:
                        parts = line.split()
                        if len(parts) >= 9:
                            for part in parts:
                                if part.startswith('lsphp') and part != 'lsphp':
                                    version_part = part[5:]  # Remove 'lsphp' prefix
                                    if len(version_part) >= 2:
                                        major = version_part[0]
                                        minor = version_part[1:]
                                        formatted_version = f'PHP {major}.{minor}'
                                        
                                        # Validate the PHP installation
                                        phpString = PHPManager.getPHPString(formatted_version)
                                        php_path = f"/usr/local/lsws/lsphp{phpString}/bin/php"
                                        lsphp_path = f"/usr/local/lsws/lsphp{phpString}/bin/lsphp"
                                        
                                        if os.path.exists(php_path) or os.path.exists(lsphp_path):
                                            if formatted_version not in finalPHPVersions:
                                                finalPHPVersions.append(formatted_version)
                    except (IndexError, ValueError):
                        continue
            except Exception as e:
                if os.path.exists(ProcessUtilities.debugPath):
                    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                    logging.writeToFile(f'Error checking /usr/local/lsws: {str(e)}')

            # Method 2: Check system-wide PHP installations
            try:
                # Check for system PHP versions
                system_php_versions = ['7.4', '8.0', '8.1', '8.2', '8.3', '8.4', '8.5']
                for version in system_php_versions:
                    formatted_version = f'PHP {version}'
                    if formatted_version not in finalPHPVersions:
                        # Check if this version exists in system
                        try:
                            phpString = PHPManager.getPHPString(formatted_version)
                            php_path = f"/usr/local/lsws/lsphp{phpString}/bin/php"
                            lsphp_path = f"/usr/local/lsws/lsphp{phpString}/bin/lsphp"
                            
                            if os.path.exists(php_path) or os.path.exists(lsphp_path):
                                finalPHPVersions.append(formatted_version)
                        except:
                            continue
            except Exception as e:
                if os.path.exists(ProcessUtilities.debugPath):
                    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                    logging.writeToFile(f'Error checking system PHP: {str(e)}')

            # Method 3: Check package manager for available PHP versions
            try:
                # Try to detect available PHP packages
                if ProcessUtilities.decideDistro() in [ProcessUtilities.centos, ProcessUtilities.cent8]:
                    # For CentOS/RHEL/AlmaLinux
                    command = "yum list available | grep lsphp | grep -E 'lsphp[0-9]+' | head -20"
                else:
                    # For Ubuntu/Debian
                    command = "apt list --installed | grep lsphp | grep -E 'lsphp[0-9]+' | head -20"
                
                result = ProcessUtilities.outputExecutioner(command)
                if result and result.strip():
                    for line in result.split('\n'):
                        if 'lsphp' in line:
                            # Extract version from package name
                            import re
                            match = re.search(r'lsphp(\d+)(\d+)', line)
                            if match:
                                major = match.group(1)
                                minor = match.group(2)
                                formatted_version = f'PHP {major}.{minor}'
                                
                                if formatted_version not in finalPHPVersions:
                                    # Validate installation
                                    try:
                                        phpString = PHPManager.getPHPString(formatted_version)
                                        php_path = f"/usr/local/lsws/lsphp{phpString}/bin/php"
                                        lsphp_path = f"/usr/local/lsws/lsphp{phpString}/bin/lsphp"
                                        
                                        if os.path.exists(php_path) or os.path.exists(lsphp_path):
                                            finalPHPVersions.append(formatted_version)
                                    except:
                                        continue
            except Exception as e:
                if os.path.exists(ProcessUtilities.debugPath):
                    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                    logging.writeToFile(f'Error checking package manager: {str(e)}')

            # Method 4: Fallback to checking common PHP versions
            if not finalPHPVersions:
                fallback_versions = ['PHP 7.4', 'PHP 8.0', 'PHP 8.1', 'PHP 8.2', 'PHP 8.3', 'PHP 8.4', 'PHP 8.5']
                for version in fallback_versions:
                    try:
                        phpString = PHPManager.getPHPString(version)
                        php_path = f"/usr/local/lsws/lsphp{phpString}/bin/php"
                        lsphp_path = f"/usr/local/lsws/lsphp{phpString}/bin/lsphp"
                        if os.path.exists(php_path) or os.path.exists(lsphp_path):
                            finalPHPVersions.append(version)
                    except:
                        continue

            # Sort versions (newest first)
            def version_sort_key(version):
                try:
                    # Extract version number for sorting
                    version_num = version.replace('PHP ', '').split('.')
                    major = int(version_num[0])
                    minor = int(version_num[1]) if len(version_num) > 1 else 0
                    return (major, minor)
                except:
                    return (0, 0)
            
            finalPHPVersions.sort(key=version_sort_key, reverse=True)

            if os.path.exists(ProcessUtilities.debugPath):
                from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
                logging.writeToFile(f'Final PHP versions found: {finalPHPVersions}')

            return finalPHPVersions if finalPHPVersions else ['PHP 7.4', 'PHP 8.0', 'PHP 8.1', 'PHP 8.2', 'PHP 8.3', 'PHP 8.4', 'PHP 8.5']

        except BaseException as msg:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            logging.writeToFile(f'Error while finding php versions on system: {str(msg)}')
            return ['PHP 7.4', 'PHP 8.0', 'PHP 8.1', 'PHP 8.2', 'PHP 8.3', 'PHP 8.4', 'PHP 8.5']

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
        phpVersion = phpVersion.split()
        php = phpVersion[1].replace(".", "")

        return php

    @staticmethod
    def validatePHPInstallation(phpVersion):
        """
        Validate that a PHP installation is properly configured and accessible
        Returns: (is_valid, error_message, php_path)
        """
        try:
            php = PHPManager.getPHPString(phpVersion)
            php_path = f'/usr/local/lsws/lsphp{php}/bin/php'
            lsphp_path = f'/usr/local/lsws/lsphp{php}/bin/lsphp'
            
            # Check if PHP binary exists
            if os.path.exists(php_path):
                return True, None, php_path
            elif os.path.exists(lsphp_path):
                return True, None, lsphp_path
            else:
                # Try alternative locations
                alternative_paths = [
                    f'/usr/local/lsws/lsphp{php}/bin/lsphp',
                    '/usr/bin/php',
                    '/usr/local/bin/php'
                ]
                
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        return True, None, alt_path
                
                return False, f'PHP {phpVersion} binary not found. Please install or check PHP installation.', None
                
        except Exception as e:
            return False, f'Error validating PHP installation: {str(e)}', None

    @staticmethod
    def fixPHPConfiguration(phpVersion):
        """
        Attempt to fix common PHP configuration issues
        """
        try:
            php = PHPManager.getPHPString(phpVersion)
            php_dir = f'/usr/local/lsws/lsphp{php}'
            
            # Check if PHP directory exists
            if not os.path.exists(php_dir):
                return False, f'PHP directory {php_dir} does not exist'
            
            # Check for missing php binary and create symlink if needed
            php_binary = f'{php_dir}/bin/php'
            lsphp_binary = f'{php_dir}/bin/lsphp'
            
            if not os.path.exists(php_binary) and os.path.exists(lsphp_binary):
                # Create symlink from lsphp to php
                import subprocess
                subprocess.run(['ln', '-sf', 'lsphp', 'php'], cwd=f'{php_dir}/bin')
                return True, 'PHP binary symlink created successfully'
            
            return True, 'PHP configuration appears to be correct'
            
        except Exception as e:
            return False, f'Error fixing PHP configuration: {str(e)}'

    @staticmethod
    def getLatestPHPVersion():
        """
        Get the latest available PHP version from the system
        Returns: (latest_version, all_versions)
        """
        try:
            all_versions = PHPManager.findPHPVersions()
            
            if not all_versions:
                return None, []
            
            # Sort versions to get the latest
            def version_sort_key(version):
                try:
                    version_num = version.replace('PHP ', '').split('.')
                    major = int(version_num[0])
                    minor = int(version_num[1]) if len(version_num) > 1 else 0
                    return (major, minor)
                except:
                    return (0, 0)
            
            sorted_versions = sorted(all_versions, key=version_sort_key, reverse=True)
            latest_version = sorted_versions[0]
            
            return latest_version, all_versions
            
        except Exception as e:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            logging.writeToFile(f'Error getting latest PHP version: {str(e)}')
            return None, []

    @staticmethod
    def getRecommendedPHPVersion():
        """
        Get the recommended PHP version for new installations
        Priority: 8.3 (recommended), 8.2, 8.4, 8.5, 8.1, 8.0, 7.4
        """
        try:
            all_versions = PHPManager.findPHPVersions()
            
            if not all_versions:
                return 'PHP 8.3'  # Default recommendation
            
            # Priority order for recommendations
            recommended_order = ['PHP 8.3', 'PHP 8.2', 'PHP 8.4', 'PHP 8.5', 'PHP 8.1', 'PHP 8.0', 'PHP 7.4']
            
            for recommended in recommended_order:
                if recommended in all_versions:
                    return recommended
            
            # If none of the recommended versions are available, return the latest
            latest, _ = PHPManager.getLatestPHPVersion()
            return latest if latest else 'PHP 8.3'
            
        except Exception as e:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            logging.writeToFile(f'Error getting recommended PHP version: {str(e)}')
            return 'PHP 8.3'

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

        command = "cat " + PHPManager.FindPHPFPMPath(phpVersion)

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

        if allow_url_fopen:
            allow_url_fopen = "allow_url_fopen = On"
        else:
            allow_url_fopen = "allow_url_fopen = Off"

        if display_errors:
            display_errors = "display_errors = On"
        else:
            display_errors = "display_errors = Off"

        if file_uploads:
            file_uploads = "file_uploads = On"
        else:
            file_uploads = "file_uploads = Off"

        if allow_url_include:
            allow_url_include = "allow_url_include = On"
        else:
            allow_url_include = "allow_url_include = Off"

        path = PHPManager.FindPHPFPMPath(phpVersion)
        command = "cat " + path
        data = ProcessUtilities.outputExecutioner(command).splitlines()

        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        writeToFile = open(tempStatusPath, 'w')

        # Track which directives we've found and replaced
        found_directives = {
            'allow_url_fopen': False,
            'display_errors': False,
            'file_uploads': False,
            'allow_url_include': False,
            'memory_limit': False,
            'max_execution_time': False,
            'upload_max_filesize': False,
            'max_input_time': False,
            'post_max_size': False
        }

        for items in data:
            if items.find("allow_url_fopen") > -1 and items.find("=") > -1:
                writeToFile.writelines(allow_url_fopen + "\n")
                found_directives['allow_url_fopen'] = True
            elif items.find("display_errors") > -1 and items.find("=") > -1:
                writeToFile.writelines(display_errors + "\n")
                found_directives['display_errors'] = True
            elif items.find("file_uploads") > -1 and items.find("=") > -1 and not items.find(
                    "max_file_uploads") > -1:
                writeToFile.writelines(file_uploads + "\n")
                found_directives['file_uploads'] = True
            elif items.find("allow_url_include") > -1 and items.find("=") > -1:
                writeToFile.writelines(allow_url_include + "\n")
                found_directives['allow_url_include'] = True
            elif items.find("memory_limit") > -1 and items.find("=") > -1:
                writeToFile.writelines("memory_limit = " + memory_limit + "\n")
                found_directives['memory_limit'] = True
            elif items.find("max_execution_time") > -1 and items.find("=") > -1:
                writeToFile.writelines("max_execution_time = " + max_execution_time + "\n")
                found_directives['max_execution_time'] = True
            elif items.find("upload_max_filesize") > -1 and items.find("=") > -1:
                writeToFile.writelines("upload_max_filesize = " + upload_max_filesize + "\n")
                found_directives['upload_max_filesize'] = True
            elif items.find("max_input_time") > -1 and items.find("=") > -1:
                writeToFile.writelines("max_input_time = " + max_input_time + "\n")
                found_directives['max_input_time'] = True
            elif items.find("post_max_size") > -1 and items.find("=") > -1:
                writeToFile.writelines("post_max_size = " + post_max_size + "\n")
                found_directives['post_max_size'] = True
            else:
                writeToFile.writelines(items + '\n')

        # Add any missing directives at the end of the file
        missing_directives = []
        if not found_directives['allow_url_fopen']:
            missing_directives.append(allow_url_fopen)
        if not found_directives['display_errors']:
            missing_directives.append(display_errors)
        if not found_directives['file_uploads']:
            missing_directives.append(file_uploads)
        if not found_directives['allow_url_include']:
            missing_directives.append(allow_url_include)
        if not found_directives['memory_limit']:
            missing_directives.append("memory_limit = " + memory_limit)
        if not found_directives['max_execution_time']:
            missing_directives.append("max_execution_time = " + max_execution_time)
        if not found_directives['upload_max_filesize']:
            missing_directives.append("upload_max_filesize = " + upload_max_filesize)
        if not found_directives['max_input_time']:
            missing_directives.append("max_input_time = " + max_input_time)
        if not found_directives['post_max_size']:
            missing_directives.append("post_max_size = " + post_max_size)

        if missing_directives:
            writeToFile.writelines("\n; Added by CyberPanel PHP Config Manager\n")
            for directive in missing_directives:
                writeToFile.writelines(directive + "\n")

        writeToFile.close()

        command = "mv %s %s" % (tempStatusPath, path)
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

        path = PHPManager.FindPHPFPMPath(phpVersion)

        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        writeToFile = open(tempStatusPath, 'w')
        writeToFile.write(configData)
        writeToFile.close()

        command = "mv %s %s" % (tempStatusPath, path)
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
