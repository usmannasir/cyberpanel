import sys
sys.path.append('/usr/local/CyberCP')
from plogical import CyberCPLogFileWriter as logging
import re
import subprocess
import shlex
import _thread
from plogical import installUtilities
import argparse
import os
from plogical.mailUtilities import mailUtilities
from plogical.processUtilities import ProcessUtilities
from ApachController.ApacheVhosts import ApacheVhost
from managePHP.phpConfig import is_php_package
from managePHP.phpConfig import fpm_service_for_ini, matches_directive

import json
from django.urls import reverse

class phpUtilities:

    installLogPath = "/home/cyberpanel/phpExtensionRequestLog"

    @staticmethod
    def packageCommand(action, extension):
        """The package manager's argument list that installs or removes one PHP package.

        The name is checked again here and is one argument after `--`, so it
        can add neither a second package nor an option.
        """
        if not is_php_package(extension):
            raise ValueError('Invalid PHP extension name.')

        rpmFamily = ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8

        if action == 'install':
            if rpmFamily:
                return ['sudo', 'yum', 'install', '-y', '--', extension]
            return ['sudo', 'apt-get', 'install', '-y', '--', extension]

        if action == 'remove':
            if rpmFamily:
                return ['sudo', 'rpm', '--nodeps', '-e', '-v', '--', extension]
            return ['sudo', 'apt-get', 'remove', '-y', '--', extension]

        raise ValueError('Unsupported package action.')

    @staticmethod
    def refuseExtensionRequest(message):
        # The page polls this log; the line ends its wait.
        writeToFile = open(phpUtilities.installLogPath, 'w')
        writeToFile.writelines(message + "\n")
        writeToFile.close()
        logging.CyberCPLogFileWriter.writeToFile("[Invalid PHP extension name]")
        return 0

    @staticmethod
    def installPHPExtension(extension,extensions):
        try:

            mailUtilities.checkHome()

            if not is_php_package(extension):
                return phpUtilities.refuseExtensionRequest("Can not be installed.")

            cmd = phpUtilities.packageCommand('install', extension)

            try:
                with open(phpUtilities.installLogPath, 'w') as f:
                    subprocess.call(cmd, stdout=f)

                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("PHP Extension Installed.\n")
                writeToFile.close()

                installUtilities.installUtilities.reStartLiteSpeed()

                return 1
            except:
                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("Can not be installed.\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                installUtilities.installUtilities.reStartLiteSpeed()
                return 0
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installPHPExtension]")

    @staticmethod
    def unInstallPHPExtension(extension,extensions):
        try:

            mailUtilities.checkHome()

            if not is_php_package(extension):
                return phpUtilities.refuseExtensionRequest("Can not un-install Extension.")

            cmd = phpUtilities.packageCommand('remove', extension)

            try:

                with open(phpUtilities.installLogPath, 'w') as f:
                    subprocess.call(cmd, stdout=f)

                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("PHP Extension Removed.\n")
                writeToFile.close()
                installUtilities.installUtilities.reStartLiteSpeed()
                return 1
            except:
                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("Can not un-install Extension.\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                installUtilities.installUtilities.reStartLiteSpeed()
                return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[unInstallPHPExtension]")

    @staticmethod
    def initiateInstall(extension):
        try:
            _thread.start_new_thread(phpUtilities.installPHPExtension, (extension, extension))
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateInstall]")

    @staticmethod
    def initiateRemoval(extension):
        try:
            _thread.start_new_thread(phpUtilities.unInstallPHPExtension, (extension, extension))
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateRestore]")

    @staticmethod
    def savePHPConfigBasic(phpVers,allow_url_fopen,display_errors,file_uploads,allow_url_include,memory_limit,max_execution_time,upload_max_filesize,max_input_time,post_max_size, apache):
        try:
            serverLevelPHPRestart = '/usr/local/lsws/admin/tmp/.lsphp_restart.txt'


            command = 'touch %s' % (serverLevelPHPRestart)
            ProcessUtilities.executioner(command)

            from ApachController.ApacheVhosts import ApacheVhost
            path = ApacheVhost.DecidePHPPathforManager(int(apache), phpVers)

            data = open(path, 'r').readlines()

            writeToFile = open(path, 'w')

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
                elif matches_directive(items, "memory_limit"):
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
                    writeToFile.writelines(items)

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

            installUtilities.installUtilities.reStartLiteSpeed()

            if int(apache) == 1:

                ProcessUtilities.normalExecutioner(ApacheVhost.fpmServiceCommand('restart', phpVers))

            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [savePHPConfigBasic]")
            print("0,"+str(msg))

    @staticmethod
    def savePHPConfigAdvance(phpVers,tempPath):
        try:

            serverLevelPHPRestart = '/usr/local/lsws/admin/tmp/.lsphp_restart.txt'
            command = 'touch %s' % (serverLevelPHPRestart)
            ProcessUtilities.executioner(command)

            phpINI = open(phpVers, 'w')
            phpINI.write(open(tempPath, "r").read())
            phpINI.close()

            if os.path.exists(serverLevelPHPRestart):
                os.remove(serverLevelPHPRestart)

            installUtilities.installUtilities.reStartLiteSpeed()

            phpService = fpm_service_for_ini(phpVers)
            if phpService is not None:
                command = f"systemctl restart {phpService}"
                if ProcessUtilities.normalExecutioner(command) != 1:
                    raise RuntimeError(
                        f"PHP configuration saved, but restarting {phpService} failed.")

            print("1,None")
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [savePHPConfigAdvance]")
            print("0,"+str(msg))

    @staticmethod
    def GetStagingInJson(stagings):
        try:

            json_data = "["
            checker = 0
            counter = 1

            for staging in stagings:
                dic = { 'id': staging.wpsite.id ,'name': staging.wpsite.title, 'Domain': staging.wpsite.owner.domain, 'path':  staging.wpsite.path,
                       #'url': reverse('WPHome', args=[staging.wpsite.owner.ProjectOwner.ProjectOwner.id, staging.wpsite.owner.ProjectOwner.id, staging.wpsite.id]),
                       'deleteURL': '%s?ID=%s&DeleteID=%s' % (reverse('WPHome'), staging.owner.id, staging.id)
                       }
                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)
                counter = counter + 1

            json_data = json_data + ']'
            return json_data
        except BaseException as msg:
            return msg

    @staticmethod
    def GetPHPVersionFromFile(vhFile, domainName=None):

        if domainName == None:
            # Your file path
            file_path = vhFile

            # Split the path by '/'
            path_parts = file_path.split('/')

            # Find the index of 'vhosts' in the path
            vhosts_index = path_parts.index('vhosts')

            # Extract the domain
            domainName = path_parts[vhosts_index + 1]

        finalConfPath = ApacheVhost.configBasePath + domainName + '.conf'

        if os.path.exists('/usr/local/CyberCP/debug'):
            logging.CyberCPLogFileWriter.writeToFile(f'Apache conf file in GetPHPVersionFromFile {finalConfPath}')

        virtualHostName = domainName
        if os.path.exists(finalConfPath):


            ######

            phpPath = ApacheVhost.DecidePHPPath('54', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php54'
                ubuntuPHP = 'php5.4'


            phpPath = ApacheVhost.DecidePHPPath('55', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php55'
                ubuntuPHP = 'php5.5'



            phpPath = ApacheVhost.DecidePHPPath('56', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php56'
                ubuntuPHP = 'php5.6'


            phpPath = ApacheVhost.DecidePHPPath('70', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php70'
                ubuntuPHP = 'php7.0'


            phpPath = ApacheVhost.DecidePHPPath('71', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php71'
                ubuntuPHP = 'php7.1'


            phpPath = ApacheVhost.DecidePHPPath('72', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php72'
                ubuntuPHP = 'php7.2'


            phpPath = ApacheVhost.DecidePHPPath('73', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php73'
                ubuntuPHP = 'php7.3'


            phpPath = ApacheVhost.DecidePHPPath('74', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php74'
                ubuntuPHP = 'php7.4'


            phpPath = ApacheVhost.DecidePHPPath('80', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php80'
                ubuntuPHP = 'php8.0'


            phpPath = ApacheVhost.DecidePHPPath('81', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php81'
                ubuntuPHP = 'php8.1'


            phpPath = ApacheVhost.DecidePHPPath('82', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php82'
                ubuntuPHP = 'php8.2'


            phpPath = ApacheVhost.DecidePHPPath('83', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php83'
                ubuntuPHP = 'php8.3'


            phpPath = ApacheVhost.DecidePHPPath('84', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php84'
                ubuntuPHP = 'php8.4'


            phpPath = ApacheVhost.DecidePHPPath('85', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php85'
                ubuntuPHP = 'php8.5'



            ######

            ### not using below 2 lines in favor of code above
            #command = f'grep -Eo -m 1 "php[0-9]+" {finalConfPath} | sed -n "1p"'
            #php_version = ProcessUtilities.outputExecutioner(command, None, True).rstrip('\n')

            # Input string
            #php_version = "php73"

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = f'/opt/remi/{centOSPHP}/root/bin/php'
                return command
            else:
                # Insert a period between '7' and '3' to convert it to 'php7.3'
                converted_version = ubuntuPHP

                # Output the result
                print(converted_version)

                result = f'/usr/bin/{converted_version}'
                #result = result.rsplit("lsphp", 1)[0] + "php"
                return result

        if os.path.exists('/usr/local/CyberCP/debug'):
            logging.CyberCPLogFileWriter.writeToFile(f'VHFile in GetPHPVersion {vhFile}')

        # The file is read with a fixed pattern and only the digits of its
        # first match are used: the returned path is built here, whatever
        # else the file holds.
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            command = 'grep -Eo "/usr/local/lsws/lsphp[0-9]+/bin/lsphp" ' + shlex.quote(vhFile)
            result = ProcessUtilities.outputExecutioner(command, None, True)
            match = re.search(r'/usr/local/lsws/lsphp([0-9]{2,3})/bin/lsphp', str(result or ''))
            if match is None:
                return 'php'
            return '/usr/local/lsws/lsphp%s/bin/php' % match.group(1)

        else:
            command = 'grep -Po "php\\d+" ' + shlex.quote(vhFile) + ' | head -n 1'
            result = ProcessUtilities.outputExecutioner(command, None, True)
            match = re.search(r'php([0-9]{2,3})(?![0-9])', str(result or ''))
            if match is None:
                return '/usr/local/lsws/ls/bin/php'
            return '/usr/local/lsws/lsphp%s/bin/php' % match.group(1)

    # The three places a website's PHP command can be: LiteSpeed PHP, Remi
    # (Apache backend, RPM family) and the distribution's PHP (Debian, Ubuntu).
    PHP_COMMAND_PATHS = (
        re.compile(r'/usr/local/lsws/lsphp([0-9])([0-9]{1,2})/bin/php'),
        re.compile(r'/opt/remi/php([0-9])([0-9]{1,2})/root/bin/php'),
        re.compile(r'/usr/bin/php([0-9])\.([0-9]{1,2})'),
    )

    ## returns something like PHP 8.2
    @staticmethod
    def WrapGetPHPVersionFromFileToGetVersionWithPHP(vhFile):
        # The version is read from the digits in the path of the website's PHP
        # command. Nothing found in a website's configuration is run.
        result = phpUtilities.GetPHPVersionFromFile(vhFile)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.CyberCPLogFileWriter.writeToFile(result)

        for shape in phpUtilities.PHP_COMMAND_PATHS:
            match = shape.fullmatch(str(result))
            if match is not None:
                return 'PHP %s.%s' % match.groups()

        return 'PHP '

    @staticmethod
    def FindIfSaidPHPIsAvaiableOtherwiseMaketheNextOneAvailableToUse(vhFile, phpVersion):
        # Preserve the requested version. Callers must surface an unavailable
        # runtime instead of silently changing the website to another PHP.
        if vhFile != None:
            virtualHostName = vhFile.split('/')[6]
            result = phpUtilities.GetPHPVersionFromFile(vhFile, virtualHostName)

            if os.path.exists(result):
                return phpVersion
            else:
                return phpVersion
        else:
            from managePHP.phpManager import PHPManager
            php = PHPManager.getPHPString(phpVersion)
            finalPath = f'/usr/local/lsws/lsphp{php}/bin/php'
            if os.path.exists(finalPath):
                return phpVersion
            else:
                return phpVersion


    @staticmethod
    def InstallSaidPHP(php):
        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or  ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
            command = f'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp{php}*'
        else:
            command = f'dnf install lsphp{php}* --exclude lsphp73-pecl-zip --exclude *imagick* -y --skip-broken'


        ProcessUtilities.executioner(command, None, True)



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--phpVers', help='Domain name!')
    parser.add_argument('--allow_url_fopen', help='Max Connections for PHP!')
    parser.add_argument('--display_errors', help='Initial Request Timeout (secs) for PHP!')
    parser.add_argument("--file_uploads", help="Persistent Connection for PHP!")
    parser.add_argument("--allow_url_include", help="Memory Soft Limit (bytes) for PHP!")
    parser.add_argument("--memory_limit", help="Process Hard Limit for PHP!")
    parser.add_argument("--max_execution_time", help="Memory Hard Limit (bytes) for PHP!")
    parser.add_argument("--upload_max_filesize", help="Process Soft Limit for PHP!")
    parser.add_argument("--max_input_time", help="Process Hard Limit for PHP!")
    parser.add_argument("--post_max_size", help="Process Hard Limit for PHP!")
    parser.add_argument("--extension", help="Process Hard Limit for PHP!")
    parser.add_argument("--apache", help="Editing apache!")

    ## Litespeed Tuning Arguments

    parser.add_argument("--tempPath", help="Temporary path to file where PHP is storing data!")


    args = parser.parse_args()

    if args.function == "savePHPConfigBasic":
        phpUtilities.savePHPConfigBasic(args.phpVers, args.allow_url_fopen, args.display_errors, args.file_uploads, args.allow_url_include, args.memory_limit,
                                        args.max_execution_time, args.upload_max_filesize, args.max_input_time, args.post_max_size, args.apache)
    elif args.function == "savePHPConfigAdvance":
        phpUtilities.savePHPConfigAdvance(args.phpVers, args.tempPath)

    elif args.function == "installPHPExtension":
        phpUtilities.installPHPExtension(args.extension, args.extension)

    elif args.function == "unInstallPHPExtension":
        phpUtilities.unInstallPHPExtension(args.extension, args.extension)




if __name__ == "__main__":
    main()
