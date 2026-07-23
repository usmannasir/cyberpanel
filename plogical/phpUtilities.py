import sys
sys.path.append('/usr/local/CyberCP')
from plogical import CyberCPLogFileWriter as logging
import subprocess
import shlex
import _thread
from plogical import installUtilities
import argparse
import os
from plogical.mailUtilities import mailUtilities
from plogical.processUtilities import ProcessUtilities
from ApachController.ApacheVhosts import ApacheVhost

import json
from django.urls import reverse

class phpUtilities:

    installLogPath = "/home/cyberpanel/phpExtensionRequestLog"

    @staticmethod
    def installPHPExtension(extension,extensions):
        try:

            mailUtilities.checkHome()

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo yum install ' + extension + ' -y'
            else:
                command = 'sudo apt-get install ' + extension + ' -y'

            cmd = shlex.split(command)

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo rpm --nodeps -e  ' + extension + ' -v'
            else:
                command = 'sudo apt-get remove -y  ' + extension

            cmd = shlex.split(command)

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

                phpService = ApacheVhost.DecideFPMServiceName(phpVers)

                command = f"systemctl restart {phpService}"
                ProcessUtilities.normalExecutioner(command)

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                phpService = f'php{phpVers}-php-fpm'
            else:
                phpService = f"php{phpVers.split('/')[3]}-fpm"

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

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

            phpPath = ApacheVhost.DecidePHPPath('86', virtualHostName)
            if os.path.exists(phpPath):
                centOSPHP = 'php86'
                ubuntuPHP = 'php8.6'

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

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            command = f'grep -Eo "/usr/local/lsws/lsphp[0-9]+/bin/lsphp" {vhFile}'
            result = ProcessUtilities.outputExecutioner(command, None, True).rstrip('\n')

            result = result.rsplit("lsphp", 1)[0] + "php"
            return result

        else:
            command = f'grep -Po "php\\d+" {vhFile} | head -n 1'
            result = ProcessUtilities.outputExecutioner(command, None, True).rstrip('\n')
            result = f'/usr/local/lsws/ls{result}/bin/lsphp'
            result = result.rsplit("lsphp", 1)[0] + "php"
            return result

    ## Map OLS/LSWS vhost handler path to panel label (e.g. lsphp85 -> "PHP 8.5").
    ## Fast: reads the LiteSpeed/OLS vhost only; does not spawn php -v and does not
    ## depend on GetPHPVersionFromFile (which prefers leftover Apache PHP-FPM confs).
    @staticmethod
    def GetPHPSelectionFromVhostFile(vhFile):
        try:
            if not vhFile or not os.path.exists(vhFile):
                return ''
            import re
            with open(vhFile, 'r', errors='ignore') as fh:
                text = fh.read()
            match = re.search(r'/usr/local/lsws/lsphp(\d{2,3})/bin/lsphp', text)
            if not match:
                # Enterprise AddHandler style: application/x-httpd-php85
                match = re.search(r'x-httpd-php(\d{2,3})', text)
            if not match:
                return ''
            digits = match.group(1)
            if len(digits) == 2:
                return 'PHP %s.%s' % (digits[0], digits[1])
            if len(digits) >= 3:
                return 'PHP %s.%s' % (digits[0], digits[1:])
            return ''
        except BaseException:
            return ''

    ## returns something like PHP 8.2
    @staticmethod
    def WrapGetPHPVersionFromFileToGetVersionWithPHP(vhFile):
        result = phpUtilities.GetPHPVersionFromFile(vhFile)

        if os.path.exists(ProcessUtilities.debugPath):
            logging.CyberCPLogFileWriter.writeToFile(result)

        command = result + " -v 2>/dev/null | awk '/^PHP/ {print $2}'"
        php_version = ProcessUtilities.outputExecutioner(command, None, True).rstrip('\n')[:3]

        return f"PHP {php_version}"

    @staticmethod
    def FindIfSaidPHPIsAvaiableOtherwiseMaketheNextOneAvailableToUse(vhFile, phpVersion):
        if vhFile != None:
            virtualHostName = vhFile.split('/')[6]
            result = phpUtilities.GetPHPVersionFromFile(vhFile, virtualHostName)

            if os.path.exists(result):
                return phpVersion
            else:
                from managePHP.phpManager import PHPManager
                return PHPManager.findPHPVersions()[-2]
        else:
            from managePHP.phpManager import PHPManager
            php = PHPManager.getPHPString(phpVersion)
            finalPath = f'/usr/local/lsws/lsphp{php}/bin/php'
            if os.path.exists(finalPath):
                return phpVersion
            else:
                from managePHP.phpManager import PHPManager
                return PHPManager.findPHPVersions()[-2]


    @staticmethod
    def InstallSaidPHP(php):
        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or  ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
            command = f'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp{php}*'
        else:
            # Enhanced dependency handling for RHEL-based systems
            # First try to install required dependencies
            dependency_packages = [
                'libmemcached', 'libmemcached-devel', 'libmemcached-libs',
                'gd', 'gd-devel', 'libgd',
                'c-client', 'c-client-devel',
                'oniguruma', 'oniguruma-devel',
                'libicu', 'libicu-devel',
                'aspell', 'aspell-devel',
                'pspell', 'pspell-devel'
            ]
            
            # Install dependencies first
            for dep in dependency_packages:
                try:
                    dep_command = f'dnf install -y {dep} --skip-broken'
                    ProcessUtilities.executioner(dep_command, None, True)
                except:
                    pass  # Continue if dependency installation fails
            
            # Install PHP with better error handling
            command = f'dnf install lsphp{php}* --exclude *imagick* -y --skip-broken --nobest'

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